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


def test_provider_linking_requires_one_time_intent(tmp_path) -> None:
    repository = ScanRepository(f'sqlite:///{tmp_path}/identities.db')
    firebase_user = repository.get_or_create_user('firebase', 'firebase-subject', 'same@example.com')
    unrelated_supabase_user = repository.get_or_create_user('supabase', 'unrelated-supabase-subject', 'same@example.com')
    assert firebase_user != unrelated_supabase_user

    intent = repository.create_link_intent(firebase_user, 'supabase')
    linked_user = repository.complete_link_intent(intent, 'supabase', 'linked-supabase-subject', 'same@example.com')
    assert linked_user == firebase_user
    assert repository.get_or_create_user('supabase', 'linked-supabase-subject', 'same@example.com') == firebase_user

    try:
        repository.complete_link_intent(intent, 'supabase', 'another-subject')
        assert False, 'A link intent must only be used once.'
    except ValueError:
        pass

    wrong_provider_intent = repository.create_link_intent(firebase_user, 'supabase')
    try:
        repository.complete_link_intent(wrong_provider_intent, 'clerk', 'wrong-provider-subject')
        assert False, 'A link intent must be restricted to its selected provider.'
    except ValueError:
        pass
    repository.close()


def test_provider_identity_cannot_be_taken_from_another_user(tmp_path) -> None:
    repository = ScanRepository(f'sqlite:///{tmp_path}/identity-conflict.db')
    owner = repository.get_or_create_user('supabase', 'existing-subject')
    other = repository.get_or_create_user('firebase', 'other-subject')
    intent = repository.create_link_intent(other, 'supabase')
    try:
        repository.complete_link_intent(intent, 'supabase', 'existing-subject')
        assert False, 'An identity already owned by another user must not be reassigned.'
    except ValueError:
        pass
    assert repository.get_or_create_user('supabase', 'existing-subject') == owner
    repository.close()


def test_postgres_connection_strings_use_psycopg_driver() -> None:
    from app.repository import _database_url

    assert _database_url("postgres://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"
    assert _database_url("postgresql://user:pass@host/db") == "postgresql+psycopg://user:pass@host/db"


def test_repository_supports_in_memory_sqlite() -> None:
    repository = ScanRepository("sqlite:///:memory:")
    assert repository.stats('anonymous-user').total_scans == 0
    repository.close()
