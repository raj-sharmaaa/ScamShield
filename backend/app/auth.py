"""JWT verification and provider identity normalization for Firebase, Supabase and Clerk."""
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from .config import settings


@dataclass(frozen=True)
class Identity:
    provider: str
    subject: str
    email: str | None = None


class AuthenticationError(ValueError):
    pass


def _provider_config() -> dict[str, dict[str, Any]]:
    providers: dict[str, dict[str, Any]] = {}
    if settings.firebase_project_id:
        issuer = f"https://securetoken.google.com/{settings.firebase_project_id}"
        providers["firebase"] = {
            "issuer": issuer,
            "audience": settings.firebase_project_id,
            "jwks": "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com",
        }
    if settings.supabase_url:
        base = settings.supabase_url.rstrip("/")
        providers["supabase"] = {
            "issuer": f"{base}/auth/v1",
            "audience": "authenticated",
            "jwks": f"{base}/auth/v1/.well-known/jwks.json",
        }
    if settings.clerk_issuer and settings.clerk_jwks_url:
        providers["clerk"] = {
            "issuer": settings.clerk_issuer.rstrip("/"),
            "audience": None,
            "jwks": settings.clerk_jwks_url,
        }
    return providers


@lru_cache(maxsize=8)
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True, timeout=5)


def configured_providers() -> list[str]:
    return sorted(_provider_config())


def verify_identity_token(token: str) -> Identity:
    if not token or len(token) > 20_000:
        raise AuthenticationError("A valid identity token is required.")
    try:
        unverified = jwt.decode(token, options={"verify_signature": False, "verify_exp": False, "verify_aud": False})
        issuer = unverified.get("iss")
        provider_config = next(
            ((name, config) for name, config in _provider_config().items() if issuer == config["issuer"]),
            None,
        )
        if provider_config is None:
            raise AuthenticationError("This identity provider is not configured or its issuer is not allowed.")
        provider, config = provider_config
        signing_key = _jwks_client(config["jwks"]).get_signing_key_from_jwt(token).key
        options = {"require": ["exp", "iat", "sub"], "verify_aud": config["audience"] is not None}
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            issuer=config["issuer"],
            audience=config["audience"],
            options=options,
            leeway=30,
        )
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise AuthenticationError("The identity token has no subject.")
        email = claims.get("email")
        return Identity(provider=provider, subject=subject, email=email if isinstance(email, str) else None)
    except AuthenticationError:
        raise
    except Exception as exc:
        raise AuthenticationError("The identity token is invalid, expired, or could not be verified.") from exc
