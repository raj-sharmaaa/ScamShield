from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .analyzer import TEST_CASES
from .ai_explainer import ai_is_configured
from .auth import AuthenticationError, Identity, configured_providers, verify_identity_token
from .config import settings
from .metrics import metrics
from .repository import ScanRepository
from .rate_limit import RedisSlidingWindowLimiter, SlidingWindowLimiter
from .services import analyze_content
from .schemas import Analysis, AnalyzeRequest, AuthCompleteLinkRequest, AuthLinkIntentRequest, HistoryItem, ReportRequest, Stats, TestCase

repository = ScanRepository(settings.database_url)
rate_limiter = RedisSlidingWindowLimiter(settings.redis_url, settings.rate_limit_per_minute) if settings.redis_url else SlidingWindowLimiter(settings.rate_limit_per_minute)
bearer = HTTPBearer(auto_error=False)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title=settings.app_name, version='0.2.0', description='Explainable scam and phishing detection API.', lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=['GET', 'POST'],
    allow_headers=['Content-Type', 'Authorization'],
)


@app.middleware('http')
async def limit_requests(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        client = request.client.host if request.client else 'unknown'
        if not rate_limiter.allow(client):
            return JSONResponse(status_code=429, content={'detail': 'Rate limit exceeded. Try again in a minute.'})
    return await call_next(request)


def _identity(credentials: HTTPAuthorizationCredentials | None) -> tuple[Identity, str] | None:
    if credentials is None:
        return None
    try:
        identity = verify_identity_token(credentials.credentials)
        user_id = repository.get_or_create_user(identity.provider, identity.subject, identity.email)
        return identity, user_id
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> tuple[Identity, str] | None:
    return _identity(credentials)


def require_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> tuple[Identity, str]:
    result = _identity(credentials)
    if result is None:
        raise HTTPException(status_code=401, detail='Sign in to access your personal ScamShield data.')
    return result


@app.get('/health')
def health() -> dict[str, object]:
    return {
        'status': 'ok',
        'service': settings.app_name,
        'engine': 'scamshield-rules-v1',
        'ai_explanation': 'enabled' if ai_is_configured() else 'fallback',
        'auth_providers': configured_providers(),
    }


@app.get('/metrics')
def get_metrics() -> dict[str, int]:
    return metrics.snapshot()


@app.get('/api/v1/auth/providers')
def get_auth_providers() -> dict[str, list[str]]:
    return {'providers': configured_providers()}


@app.post('/api/v1/auth/session')
def create_session(user: Annotated[tuple[Identity, str], Depends(require_user)]) -> dict[str, str | None]:
    identity, user_id = user
    return {'user_id': user_id, 'provider': identity.provider, 'email': identity.email}


@app.post('/api/v1/auth/link-intent')
def create_link_intent(
    payload: AuthLinkIntentRequest,
    user: Annotated[tuple[Identity, str], Depends(require_user)],
) -> dict[str, object]:
    _, user_id = user
    return {
        'link_intent': repository.create_link_intent(user_id, payload.provider),
        'expires_in': 600,
    }


@app.post('/api/v1/auth/complete-link')
def complete_link(payload: AuthCompleteLinkRequest) -> dict[str, str]:
    try:
        linked = verify_identity_token(payload.identity_token)
        if linked.provider != payload.provider:
            raise HTTPException(status_code=400, detail='The selected provider does not match the supplied token.')
        user_id = repository.complete_link_intent(
            payload.link_intent, linked.provider, linked.subject, linked.email
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {'status': 'linked', 'provider': linked.provider, 'user_id': user_id}


@app.post('/api/v1/analyze', response_model=Analysis, status_code=status.HTTP_200_OK)
def create_analysis(
    payload: AnalyzeRequest,
    user: Annotated[tuple[Identity, str] | None, Depends(optional_user)],
) -> Analysis:
    analysis = analyze_content(payload.content, payload.scan_type)
    if payload.save_result and user is not None:
        repository.save_scan(payload.content, analysis, user[1])
    return analysis


@app.get('/api/v1/history', response_model=list[HistoryItem])
def get_history(
    user: Annotated[tuple[Identity, str], Depends(require_user)],
    limit: int = 20,
) -> list[HistoryItem]:
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail='limit must be between 1 and 100')
    return repository.history(user[1], limit)


@app.get('/api/v1/stats', response_model=Stats)
def get_stats(
    user: Annotated[tuple[Identity, str], Depends(require_user)],
) -> Stats:
    return repository.stats(user[1])


@app.get('/api/v1/test-cases', response_model=list[TestCase])
def get_test_cases() -> list[TestCase]:
    return [TestCase(**test_case) for test_case in TEST_CASES]


@app.post('/api/v1/reports', status_code=status.HTTP_202_ACCEPTED)
def report_analysis(
    payload: ReportRequest,
    user: Annotated[tuple[Identity, str], Depends(require_user)],
) -> dict[str, str]:
    repository.save_report(payload, user[1])
    return {'status': 'received', 'message': 'Thanks. Your report will help improve the detector.'}
