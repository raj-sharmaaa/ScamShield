from app.repository import ScanRepository
from app.analyzer import analyze


def test_repository_persists_user_scoped_history_and_stats(tmp_path) -> None:
    repository = ScanRepository(f'sqlite:///{tmp_path}/test.db')
    user_a = repository.get_or_create_user('firebase', 'firebase-subject-a', 'a@example.com')
    user_b = repository.get_or_create_user('clerk', 'clerk-subject-b', 'b@example.com')
    content = 'Urgent: send your password and gift card payment now'
    analysis = analyze(content, 'Message')
    repository.save_scan(content, analysis, user_a)

    assert repository.history(user_a)[0].id == analysis.id
    assert repository.history(user_b) == []
    assert repository.stats(user_a).total_scans == 1
    assert repository.stats(user_b).total_scans == 0
    repository.close()


def test_identity_links_share_one_internal_user_only_when_explicitly_linked(tmp_path) -> None:
    repository = ScanRepository(f'sqlite:///{tmp_path}/identities.db')
    firebase_user = repository.get_or_create_user('firebase', 'firebase-subject', 'same@example.com')
    supabase_user = repository.get_or_create_user('supabase', 'supabase-subject', 'same@example.com')
    assert firebase_user != supabase_user

    repository.link_identity(firebase_user, 'supabase', 'supabase-subject-2', 'same@example.com')
    assert repository.get_or_create_user('supabase', 'supabase-subject-2', 'same@example.com') == firebase_user

    try:
        repository.link_identity(firebase_user, 'supabase', 'supabase-subject', 'same@example.com')
        assert False, 'An identity already owned by another account must not be merged.'
    except ValueError:
        pass
    repository.close()


def test_postgres_connection_strings_use_psycopg_driver() -> None:
    from app.repository import _database_url

    assert _database_url("postgres://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"
    assert _database_url("postgresql://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"


def test_repository_supports_in_memory_sqlite() -> None:
    repository = ScanRepository("sqlite:///:memory:")
    assert repository.stats('anonymous-user').total_scans == 0
    repository.close()
