import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import uuid4

from .schemas import Analysis, Finding, ScanType

@dataclass(frozen=True)
class Rule:
    rule_id: str
    pattern: re.Pattern[str]
    label: str
    detail: str
    severity: str
    points: int
    recommendation: str

RULES = (
    Rule('pressure.urgency', re.compile(r'\b(urgent|immediately|act now|last warning|within \d+ hours?)\b', re.I), 'Urgency language', 'Pushes you to act before you can verify the request.', 'high', 24, 'Pause. Contact the organisation through a known channel.'),
    Rule('identity.credentials', re.compile(r'\b(password|passcode|one[- ]time|otp|verification code|login)\b', re.I), 'Credential request', 'Legitimate teams rarely ask for secrets over chat or email.', 'high', 28, 'Never share passwords or one-time codes with a message sender.'),
    Rule('payment.unusual', re.compile(r'\b(gift card|crypto|bitcoin|wire transfer|send money|payment)\b', re.I), 'Unusual payment request', 'Payment methods are difficult to reverse and commonly used by scammers.', 'high', 25, 'Do not pay. Verify the request using a separate contact method.'),
    Rule('offer.too_good', re.compile(r'\b(free|winner|won|reward|prize|claim)\b', re.I), 'Too-good-to-be-true offer', 'Unexpected rewards are a common lure for harvesting information.', 'medium', 14, 'Treat unexpected prizes as suspicious until independently verified.'),
    Rule('link.shortened', re.compile(r'\b(bit\.ly|tinyurl\.com|t\.co|goo\.gl|shorturl)\b', re.I), 'Shortened link', 'The final destination is hidden until the link is opened.', 'medium', 18, 'Expand and inspect the destination before opening it.'),
    Rule('pressure.fear', re.compile(r'\b(verify|suspend|locked|unusual activity|security alert)\b', re.I), 'Fear-based framing', 'Threats about account access create pressure and bypass skepticism.', 'medium', 16, 'Open the official app or type the organisation URL yourself.'),
    Rule('sender.suspicious_tld', re.compile(r'@[\w.-]+\.(ru|cn|top|xyz|click)\b', re.I), 'Suspicious sender domain', 'The sender domain has signals associated with disposable infrastructure.', 'high', 22, 'Check the exact sender domain for lookalike spelling.'),
)

TEST_CASES = [
    {'id': 'delivery-fee', 'title': 'Missed delivery fee', 'scan_type': 'Message', 'content': 'Your parcel is waiting. Pay a small delivery fee immediately at https://bit.ly/parcel-help.', 'expected_verdict': 'High risk', 'tags': ['delivery', 'payment', 'shortened link']},
    {'id': 'account-lock', 'title': 'Account lock warning', 'scan_type': 'Email', 'content': 'Urgent: your account is locked. Verify your password within 24 hours at https://bit.ly/secure-login.', 'expected_verdict': 'High risk', 'tags': ['credential theft', 'urgency']},
    {'id': 'invoice', 'title': 'Routine invoice', 'scan_type': 'Email', 'content': 'Hi, your monthly invoice is ready in the customer portal. You can sign in from the official app.', 'expected_verdict': 'Safe', 'tags': ['benign']},
    {'id': 'prize-bait', 'title': 'Prize bait', 'scan_type': 'Message', 'content': 'Congratulations! You won a free reward. Claim your prize now by sending the one-time code.', 'expected_verdict': 'High risk', 'tags': ['prize', 'otp']},
]

def _evidence(pattern: re.Pattern[str], content: str) -> str | None:
    match = pattern.search(content)
    if not match:
        return None
    start = max(0, match.start() - 32)
    end = min(len(content), match.end() + 32)
    return content[start:end].strip()

def _url_findings(content: str) -> list[Finding]:
    findings: list[Finding] = []
    for raw_url in re.findall(r'https?://[^\s)]+|www\.[^\s)]+', content, re.I):
        parsed = urlparse(raw_url if '://' in raw_url else f'https://{raw_url}')
        host = (parsed.hostname or '').lower()
        if host.startswith('xn--') or any(part.isdigit() for part in host.split('.')):
            findings.append(Finding(rule_id='url.host_anomaly', label='Unusual link host', detail='The destination uses an encoded or numeric host that deserves verification.', severity='medium', evidence=host, recommendation='Do not open it. Visit the organisation through a known bookmark.'))
        if parsed.username:
            findings.append(Finding(rule_id='url.at_symbol', label='Deceptive URL structure', detail='The URL contains a username before the real host, a common impersonation trick.', severity='high', evidence=raw_url, recommendation='Ignore the link and navigate to the official site manually.'))
    return findings

def analyze(content: str, scan_type: ScanType) -> Analysis:
    findings = [Finding(rule_id=rule.rule_id, label=rule.label, detail=rule.detail, severity=rule.severity, evidence=_evidence(rule.pattern, content), recommendation=rule.recommendation) for rule in RULES if rule.pattern.search(content)]
    findings.extend(_url_findings(content))
    score = min(99, max(4, sum(next(rule.points for rule in RULES if rule.rule_id == finding.rule_id) if finding.rule_id in {rule.rule_id for rule in RULES} else 16 for finding in findings) + (8 if re.search(r'https?://|www\.', content, re.I) else 0)))
    verdict = 'High risk' if score >= 65 else 'Caution' if score >= 30 else 'Safe'
    summary = {'High risk': 'This looks designed to create urgency and get something valuable from you.', 'Caution': 'A few patterns deserve a closer look before you reply or click.', 'Safe': 'No strong scam patterns detected. Still verify unexpected requests independently.'}[verdict]
    return Analysis(id=str(uuid4()), score=score, verdict=verdict, summary=summary, scan_type=scan_type, findings=findings, confidence=min(98, 78 + len(findings) * 5), created_at=datetime.now(timezone.utc), engine='scamshield-rules-v1')
