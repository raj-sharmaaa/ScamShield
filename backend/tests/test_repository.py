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


def test_postgres_connection_strings_use_psycopg_driver() -> None:
    from app.repository import _database_url

    assert _database_url("postgres://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"
    assert _database_url("postgresql://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"


def test_repository_supports_in_memory_sqlite() -> None:
    repository = ScanRepository("sqlite:///:memory:")
    assert repository.stats().total_scans == 0
    repository.close()
