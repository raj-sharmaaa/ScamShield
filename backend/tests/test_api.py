from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_high_risk_analysis_returns_explanations() -> None:
    response = client.post('/api/v1/analyze', json={'type': 'Message', 'content': 'Urgent: send your password and gift card payment now'})
    body = response.json()
    assert response.status_code == 200
    assert body['verdict'] == 'High risk'
    assert body['score'] >= 65
    assert {finding['rule_id'] for finding in body['findings']} >= {'pressure.urgency', 'identity.credentials', 'payment.unusual'}
    assert body['findings'][0]['recommendation']


def test_safe_analysis() -> None:
    response = client.post('/api/v1/analyze', json={'type': 'Email', 'content': 'Your monthly statement is available in the official app', 'save_result': False})
    assert response.status_code == 200
    assert response.json()['verdict'] == 'Safe'


def test_rejects_blank_content() -> None:
    response = client.post('/api/v1/analyze', json={'type': 'URL', 'content': ' '})
    assert response.status_code == 422


def test_public_test_cases() -> None:
    response = client.get('/api/v1/test-cases')
    assert response.status_code == 200
    assert len(response.json()) >= 4


def test_production_history_and_reports_are_disabled_without_auth(monkeypatch) -> None:
    from types import SimpleNamespace
    import app.main as main

    monkeypatch.setattr(main, "settings", SimpleNamespace(
        environment="production",
        allow_unauthenticated_storage=False,
    ))

    assert client.get('/api/v1/history').status_code == 503
    assert client.get('/api/v1/stats').status_code == 503
    report = client.post('/api/v1/reports', json={
        "content": "Suspicious message",
        "reason": "missed_scam",
    })
    assert report.status_code == 503


def test_production_scan_does_not_store_submitted_content(monkeypatch) -> None:
    from types import SimpleNamespace
    import app.main as main

    saved = []
    monkeypatch.setattr(main, "settings", SimpleNamespace(
        environment="production",
        allow_unauthenticated_storage=False,
    ))
    monkeypatch.setattr(main.repository, "save_scan", lambda content, analysis: saved.append(content))

    response = client.post('/api/v1/analyze', json={
        "type": "Message",
        "content": "Please verify your account",
        "save_result": True,
    })

    assert response.status_code == 200
    assert saved == []
