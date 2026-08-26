import re
from dataclasses import dataclass
from urllib.parse import urlparse

URL_PATTERN = re.compile(r'https?://[^\s)]+|www\.[^\s)]+', re.I)

@dataclass(frozen=True)
class UrlSignal:
    rule_id: str
    label: str
    detail: str
    severity: str
    evidence: str
    recommendation: str


def extract_urls(content: str) -> list[str]:
    return URL_PATTERN.findall(content)


def inspect_urls(content: str) -> list[UrlSignal]:
    signals: list[UrlSignal] = []
    for raw_url in extract_urls(content):
        parsed = urlparse(raw_url if '://' in raw_url else f'https://{raw_url}')
        host = (parsed.hostname or '').lower()
        if host.startswith('xn--'):
            signals.append(UrlSignal('url.punycode', 'Encoded domain name', 'The domain uses internationalized encoding that can hide lookalike characters.', 'medium', host, 'Type the official address manually instead.'))
        if any(part.isdigit() for part in host.split('.')):
            signals.append(UrlSignal('url.numeric_host', 'Numeric link host', 'The destination uses a numeric host rather than a recognizable domain.', 'medium', host, 'Do not open it until the destination is independently verified.'))
        if parsed.username:
            signals.append(UrlSignal('url.at_symbol', 'Deceptive URL structure', 'The URL contains a username before the real host, a common impersonation trick.', 'high', raw_url, 'Ignore the link and navigate to the official site manually.'))
    return signals
