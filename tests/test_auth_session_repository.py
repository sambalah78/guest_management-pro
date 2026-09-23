from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from guest_management.core.security import (
    encrypt_session_token,
    hash_session_id,
)
from guest_management.repositories.auth_session_repository import (
    AuthSessionRepository,
)
from guest_management.database import engine


TEST_USER_ID = "554208ae-d98e-4803-8e9b-0bb9625a6861"


@pytest.fixture
def repository():
    return AuthSessionRepository()


@pytest.fixture
def cleanup_sessions():
    session_hashes = []

    yield session_hashes

    if not session_hashes:
        return

    placeholders = ", ".join(
        f":session_{index}"
        for index in range(len(session_hashes))
    )

    params = {
        f"session_{index}": value
        for index, value in enumerate(session_hashes)
    }

    with engine.begin() as conn:
        conn.execute(
            __import__("sqlalchemy").text(
                f"""
                DELETE FROM auth_sessions
                WHERE session_id_hash IN ({placeholders})
                """
            ),
            params,
        )


def _create_test_session(repository, session_hashes, *, expires_at=None):
    session_id_hash = hash_session_id(
        f"test-session-{uuid4().hex}"
    )

    session_hashes.append(session_id_hash)

    return repository.create(
        session_id_hash=session_id_hash,
        user_id=TEST_USER_ID,
        access_token_ciphertext=encrypt_session_token(
            f"access-token-{uuid4().hex}"
        ),
        refresh_token_ciphertext=encrypt_session_token(
            f"refresh-token-{uuid4().hex}"
        ),
        expires_at=(
            expires_at
            if expires_at is not None
            else datetime.now(timezone.utc) + timedelta(hours=1)
        ),
    )


def test_create_session(repository, cleanup_sessions):
    session = _create_test_session(
        repository,
        cleanup_sessions,
    )

    assert session["id"] is not None
    assert session["session_id_hash"]
    assert str(session["user_id"]) == TEST_USER_ID
    assert session["access_token_ciphertext"]
    assert session["refresh_token_ciphertext"]
    assert session["expires_at"] is not None
    assert session["revoked_at"] is None


def test_get_active_returns_active_session(
    repository,
    cleanup_sessions,
):
    session = _create_test_session(
        repository,
        cleanup_sessions,
    )

    result = repository.get_active(
        session["session_id_hash"]
    )

    assert result is not None
    assert result["id"] == session["id"]
    assert result["session_id_hash"] == session["session_id_hash"]
    assert str(result["user_id"]) == TEST_USER_ID


def test_get_active_metadata_returns_session_without_credentials(
    repository,
    cleanup_sessions,
):
    session = _create_test_session(
        repository,
        cleanup_sessions,
    )

    result = repository.get_active_metadata(
        session["session_id_hash"]
    )

    assert result is not None
    assert result["id"] == session["id"]
    assert result["session_id_hash"] == session["session_id_hash"]
    assert str(result["user_id"]) == TEST_USER_ID
    assert result["expires_at"] is not None

    # The metadata query must not expose encrypted credentials.
    assert "access_token_ciphertext" not in result
    assert "refresh_token_ciphertext" not in result


def test_get_active_rejects_unknown_session(repository):
    result = repository.get_active(
        hash_session_id(f"unknown-{uuid4().hex}")
    )

    assert result is None


def test_get_active_rejects_expired_session(
    repository,
    cleanup_sessions,
):
    session = _create_test_session(
        repository,
        cleanup_sessions,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    result = repository.get_active(
        session["session_id_hash"]
    )

    assert result is None


def test_get_active_rejects_revoked_session(
    repository,
    cleanup_sessions,
):
    session = _create_test_session(
        repository,
        cleanup_sessions,
    )

    assert repository.revoke(
        session["session_id_hash"]
    )

    result = repository.get_active(
        session["session_id_hash"]
    )

    assert result is None


def test_touch_updates_last_used_at(
    repository,
    cleanup_sessions,
):
    session = _create_test_session(
        repository,
        cleanup_sessions,
    )

    before = session["last_used_at"]

    assert repository.touch(
        session["session_id_hash"]
    )

    refreshed = repository.get_active(
        session["session_id_hash"]
    )

    assert refreshed is not None
    assert refreshed["last_used_at"] >= before


def test_touch_returns_false_for_unknown_session(repository):
    assert not repository.touch(
        hash_session_id(f"unknown-{uuid4().hex}")
    )


def test_revoke_session(
    repository,
    cleanup_sessions,
):
    session = _create_test_session(
        repository,
        cleanup_sessions,
    )

    assert repository.revoke(
        session["session_id_hash"]
    )

    with engine.connect() as conn:
        row = conn.execute(
            __import__("sqlalchemy").text(
                """
                SELECT revoked_at
                FROM auth_sessions
                WHERE session_id_hash = :session_id_hash
                """
            ),
            {
                "session_id_hash": session["session_id_hash"],
            },
        ).mappings().first()

    assert row is not None
    assert row["revoked_at"] is not None


def test_revoke_is_idempotent(
    repository,
    cleanup_sessions,
):
    session = _create_test_session(
        repository,
        cleanup_sessions,
    )

    assert repository.revoke(
        session["session_id_hash"]
    )

    assert not repository.revoke(
        session["session_id_hash"]
    )


def test_revoke_all_for_user(
    repository,
    cleanup_sessions,
):
    first = _create_test_session(
        repository,
        cleanup_sessions,
    )
    second = _create_test_session(
        repository,
        cleanup_sessions,
    )

    revoked = repository.revoke_all_for_user(
        TEST_USER_ID
    )

    assert revoked >= 2
    assert repository.get_active(
        first["session_id_hash"]
    ) is None
    assert repository.get_active(
        second["session_id_hash"]
    ) is None


def test_count_active_for_user(
    repository,
    cleanup_sessions,
):
    first = _create_test_session(
        repository,
        cleanup_sessions,
    )
    second = _create_test_session(
        repository,
        cleanup_sessions,
    )

    assert repository.count_active_for_user(
        TEST_USER_ID
    ) >= 2

    repository.revoke(
        first["session_id_hash"]
    )

    assert repository.get_active(
        first["session_id_hash"]
    ) is None

    assert repository.get_active(
        second["session_id_hash"]
    ) is not None


def test_count_active_returns_zero_for_unknown_user(
    repository,
):
    assert repository.count_active_for_user(
        str(uuid4())
    ) == 0


def test_delete_expired_removes_old_expired_sessions(
    repository,
    cleanup_sessions,
):
    session = _create_test_session(
        repository,
        cleanup_sessions,
        expires_at=datetime.now(timezone.utc) - timedelta(days=31),
    )

    deleted = repository.delete_expired(
        older_than_days=30
    )

    assert deleted >= 1

    with engine.connect() as conn:
        row = conn.execute(
            __import__("sqlalchemy").text(
                """
                SELECT id
                FROM auth_sessions
                WHERE id = :id
                """
            ),
            {"id": session["id"]},
        ).first()

    assert row is None

    cleanup_sessions.remove(
        session["session_id_hash"]
    )


def test_repository_does_not_modify_token_ciphertext(
    repository,
    cleanup_sessions,
):
    access_ciphertext = encrypt_session_token(
        "access-secret-value"
    )
    refresh_ciphertext = encrypt_session_token(
        "refresh-secret-value"
    )

    session_id_hash = hash_session_id(
        f"test-session-{uuid4().hex}"
    )
    cleanup_sessions.append(session_id_hash)

    session = repository.create(
        session_id_hash=session_id_hash,
        user_id=TEST_USER_ID,
        access_token_ciphertext=access_ciphertext,
        refresh_token_ciphertext=refresh_ciphertext,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    assert session["access_token_ciphertext"] == access_ciphertext
    assert session["refresh_token_ciphertext"] == refresh_ciphertext
