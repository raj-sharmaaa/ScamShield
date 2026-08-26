from app.repository import ScanRepository
from app.analyzer import analyze


def test_repository_persists_history_and_stats(tmp_path) -> None:
    repository = ScanRepository(f'sqlite:///{tmp_path}/test.db')
    content = 'Urgent: send your password and gift card payment now'
    analysis = analyze(content, 'Message')
    repository.save_scan(content, analysis)
    history = repository.history()
    stats = repository.stats()
    assert history[0].id == analysis.id
    assert stats.total_scans == 1
    assert stats.high_risk == 1
