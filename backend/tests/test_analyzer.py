from app.analyzer import analyze
from app.url_inspector import extract_urls, inspect_urls


def test_analyzer_assigns_stable_rule_ids() -> None:
    result = analyze('Urgent: verify your password and send a gift card payment now', 'Message')
    assert result.verdict == 'High risk'
    assert all(finding.rule_id for finding in result.findings)


def test_url_inspector_does_not_fetch_urls() -> None:
    assert extract_urls('Visit https://example.com now') == ['https://example.com']
    signals = inspect_urls('Visit https://user@example.com now')
    assert signals[0].rule_id == 'url.at_symbol'


def test_safe_content_has_a_low_score() -> None:
    result = analyze('The meeting is confirmed for tomorrow at 10am.', 'Message')
    assert result.verdict == 'Safe'
    assert result.score < 30
