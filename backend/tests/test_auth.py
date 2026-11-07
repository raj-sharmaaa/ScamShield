from types import SimpleNamespace

import jwt
import pytest

import app.auth as auth
from app.auth import AuthenticationError


def test_enabled_providers_are_derived_from_backend_configuration(monkeypatch) -> None:
    monkeypatch.setattr(auth, "settings", SimpleNamespace(
        firebase_project_id="scamshield-demo",
        supabase_url="https://project.supabase.co",
        clerk_issuer="https://clerk.example.com",
        clerk_jwks_url="https://clerk.example.com/.well-known/jwks.json",
    ))
    assert auth.configured_providers() == ["clerk", "firebase", "supabase"]


def test_unknown_token_issuer_is_rejected_before_key_lookup(monkeypatch) -> None:
    monkeypatch.setattr(auth, "settings", SimpleNamespace(
        firebase_project_id="",
        supabase_url="",
        clerk_issuer="",
        clerk_jwks_url="",
    ))
    token = jwt.encode(
        {"iss": "https://untrusted.example", "sub": "attacker", "iat": 1, "exp": 9_999_999_999},
        "not-a-provider-key",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        auth.verify_identity_token(token)
