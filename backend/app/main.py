from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .analyzer import TEST_CASES
from .ai_explainer import ai_is_configured
from .config import settings
from .metrics import metrics
from .repository import ScanRepository
from .rate_limit import SlidingWindowLimiter
from .services import analyze_content
from .schemas import Analysis, AnalyzeRequest, HistoryItem, ReportRequest, Stats, TestCase

repository = ScanRepository(settings.database_url)
rate_limiter = SlidingWindowLimiter(settings.rate_limit_per_minute)

@asynccontextmanager
async def lifespan(_: FastAPI):
    yield

app = FastAPI(title=settings.app_name, version='0.1.0', description='Explainable scam and phishing detection API.', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=True, allow_methods=['GET', 'POST'], allow_headers=['*'])

@app.middleware('http')
async def limit_requests(request: Request, call_next):
    if request.url.path.startswith('/api/'):
        client = request.client.host if request.client else 'unknown'
        if not rate_limiter.allow(client):
            return JSONResponse(status_code=429, content={'detail': 'Rate limit exceeded. Try again in a minute.'})
    return await call_next(request)

@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok', 'service': settings.app_name, 'engine': 'scamshield-rules-v1', 'ai_explanation': 'enabled' if ai_is_configured() else 'fallback'}

@app.get('/metrics')
def get_metrics() -> dict[str, int]:
    return metrics.snapshot()

@app.post('/api/v1/analyze', response_model=Analysis, status_code=status.HTTP_200_OK)
def create_analysis(payload: AnalyzeRequest) -> Analysis:
    analysis = analyze_content(payload.content, payload.scan_type)
    if payload.save_result:
        repository.save_scan(payload.content, analysis)
    return analysis

@app.get('/api/v1/history', response_model=list[HistoryItem])
def get_history(limit: int = 20) -> list[HistoryItem]:
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail='limit must be between 1 and 100')
    return repository.history(limit)

@app.get('/api/v1/stats', response_model=Stats)
def get_stats() -> Stats:
    return repository.stats()

@app.get('/api/v1/test-cases', response_model=list[TestCase])
def get_test_cases() -> list[TestCase]:
    return [TestCase(**test_case) for test_case in TEST_CASES]

@app.post('/api/v1/reports', status_code=status.HTTP_202_ACCEPTED)
def report_analysis(payload: ReportRequest) -> dict[str, str]:
    repository.save_report(payload)
    return {'status': 'received', 'message': 'Thanks. Your report will help improve the detector.'}
