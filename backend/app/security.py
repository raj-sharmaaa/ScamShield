import hashlib
import hmac
import secrets


def content_fingerprint(content: str) -> str:
    """Create a non-reversible identifier for abuse reports and deduplication."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:24]


def safe_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode('utf-8'), right.encode('utf-8'))


def create_request_id() -> str:
    return secrets.token_urlsafe(12)
