from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from guest_management.core.security import hash_session_id

from guest_management.services.auth_session_service import (
    AuthSessionService,
)


TEST_USER_ID = "554208ae-d98e-4803-8e9b-0bb9625a6861"


@pytest.fixture
def repository():
    return Mock()


@pytest.fixture
def auth_repository():
    return Mock()


@pytest.fixture
def service(repository, auth_repository):
    return AuthSessionService(
        repository=repository,
        auth_repository=auth_repository,
    )


def test_create_session_encrypts_tokens_and_returns_opaque_id(
    service,
    repository,
):
    repository.create.return_value = {
        "id": 1,
    }

    session_id = service.create_session(
        user_id=TEST_USER_ID,
        access_token="access-token",
        refresh_token="refresh-token",
    )

    assert session_id
    assert len(session_id) > 40

    call = repository.create.call_args.kwargs

    assert call["user_id"] == TEST_USER_ID
    assert call["session_id_hash"]
    assert call["session_id_hash"] != session_id
    assert call["access_token_ciphertext"] != "access-token"
    assert call["refresh_token_ciphertext"] != "refresh-token"
    assert isinstance(call["expires_at"], datetime)


def test_create_session_rejects_missing_user(service):
    with pytest.raises(ValueError):
        service.create_session(
            user_id="",
            access_token="access-token",
            refresh_token="refresh-token",
        )


def test_create_session_rejects_missing_access_token(service):
    with pytest.raises(ValueError):
        service.create_session(
            user_id=TEST_USER_ID,
            access_token="",
            refresh_token="refresh-token",
        )


def test_create_session_rejects_missing_refresh_token(service):
    with pytest.raises(ValueError):
        service.create_session(
            user_id=TEST_USER_ID,
            access_token="access-token",
            refresh_token="",
        )


def test_get_session_metadata_returns_metadata_without_tokens(
    service,
    repository,
):
    session_id = f"session-{uuid4().hex}"

    repository.get_active_metadata.return_value = {
        "id": 10,
        "session_id_hash": hash_session_id(session_id),
        "user_id": TEST_USER_ID,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "last_used_at": datetime.now(timezone.utc),
        "revoked_at": None,
    }

    result = service.get_session_metadata(session_id)

    assert result is not None
    assert result["user_id"] == TEST_USER_ID
    assert result["id"] == 10
    assert "access_token" not in result
    assert "refresh_token" not in result

    repository.get_active_metadata.assert_called_once_with(
        hash_session_id(session_id)
    )
    repository.touch.assert_called_once_with(
        hash_session_id(session_id)
    )


def test_get_session_metadata_returns_none_for_unknown_session(
    service,
    repository,
):
    repository.get_active_metadata.return_value = None

    result = service.get_session_metadata(
        f"unknown-{uuid4().hex}"
    )

    assert result is None
    repository.touch.assert_not_called()


def test_get_session_metadata_does_not_touch_when_disabled(
    service,
    repository,
):
    session_id = f"session-{uuid4().hex}"

    repository.get_active_metadata.return_value = {
        "id": 10,
        "session_id_hash": hash_session_id(session_id),
        "user_id": TEST_USER_ID,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "last_used_at": datetime.now(timezone.utc),
        "revoked_at": None,
    }

    result = service.get_session_metadata(
        session_id,
        touch=False,
    )

    assert result is not None
    assert result["user_id"] == TEST_USER_ID
    repository.touch.assert_not_called()


def test_get_session_returns_decrypted_tokens(
    service,
    repository,
):
    from guest_management.core.security import (
        encrypt_session_token,
        hash_session_id,
    )

    session_id = f"session-{uuid4().hex}"

    repository.get_active.return_value = {
        "id": 10,
        "session_id_hash": hash_session_id(session_id),
        "user_id": TEST_USER_ID,
        "access_token_ciphertext": encrypt_session_token(
            "access-token"
        ),
        "refresh_token_ciphertext": encrypt_session_token(
            "refresh-token"
        ),
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "last_used_at": datetime.now(timezone.utc),
        "revoked_at": None,
    }

    result = service.get_session(session_id)

    assert result is not None
    assert result["user_id"] == TEST_USER_ID
    assert result["access_token"] == "access-token"
    assert result["refresh_token"] == "refresh-token"
    repository.touch.assert_called_once()


def test_get_session_returns_none_for_unknown_session(
    service,
    repository,
):
    repository.get_active.return_value = None

    result = service.get_session("unknown-session")

    assert result is None
    repository.touch.assert_not_called()


def test_get_session_does_not_touch_when_disabled(
    service,
    repository,
):
    from guest_management.core.security import (
        encrypt_session_token,
        hash_session_id,
    )

    session_id = f"session-{uuid4().hex}"

    repository.get_active.return_value = {
        "id": 10,
        "session_id_hash": hash_session_id(session_id),
        "user_id": TEST_USER_ID,
        "access_token_ciphertext": encrypt_session_token(
            "access-token"
        ),
        "refresh_token_ciphertext": encrypt_session_token(
            "refresh-token"
        ),
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "last_used_at": datetime.now(timezone.utc),
        "revoked_at": None,
    }

    result = service.get_session(
        session_id,
        touch=False,
    )

    assert result is not None
    repository.touch.assert_not_called()


def test_get_session_returns_none_for_tampered_ciphertext(
    service,
    repository,
):
    session_id = f"session-{uuid4().hex}"

    repository.get_active.return_value = {
        "id": 10,
        "session_id_hash": "hash",
        "user_id": TEST_USER_ID,
        "access_token_ciphertext": "tampered",
        "refresh_token_ciphertext": "tampered",
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "last_used_at": datetime.now(timezone.utc),
        "revoked_at": None,
    }

    result = service.get_session(session_id)

    assert result is None
    repository.touch.assert_not_called()


def test_revoke_session_hashes_session_id(
    service,
    repository,
):
    repository.revoke.return_value = True

    session_id = f"session-{uuid4().hex}"

    result = service.revoke_session(session_id)

    assert result is True

    hashed = repository.revoke.call_args.args[0]

    assert hashed != session_id
    assert len(hashed) == 64


def test_revoke_all_for_user(service, repository):
    repository.revoke_all_for_user.return_value = 3

    result = service.revoke_all_for_user(TEST_USER_ID)

    assert result == 3
    repository.revoke_all_for_user.assert_called_once_with(
        TEST_USER_ID
    )


def test_refresh_session_updates_encrypted_tokens(
    service,
    repository,
    auth_repository,
):
    from guest_management.core.security import (
        encrypt_session_token,
        hash_session_id,
    )

    session_id = f"session-{uuid4().hex}"

    repository.get_active.return_value = {
        "id": 10,
        "session_id_hash": hash_session_id(session_id),
        "user_id": TEST_USER_ID,
        "access_token_ciphertext": encrypt_session_token(
            "old-access-token"
        ),
        "refresh_token_ciphertext": encrypt_session_token(
            "old-refresh-token"
        ),
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "last_used_at": datetime.now(timezone.utc),
        "revoked_at": None,
    }

    auth_repository.refresh_session.return_value = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "user": {
            "id": TEST_USER_ID,
            "email": "test@example.com",
        },
    }

    repository.update_tokens.return_value = True

    result = service.refresh_session(session_id)

    assert result is not None
    assert result["access_token"] == "new-access-token"
    assert result["refresh_token"] == "new-refresh-token"
    assert result["user_id"] == TEST_USER_ID

    auth_repository.refresh_session.assert_called_once_with(
        "old-refresh-token"
    )

    call = repository.update_tokens.call_args.kwargs

    assert call["session_id_hash"] == hash_session_id(session_id)
    assert call["access_token_ciphertext"] != "new-access-token"
    assert call["refresh_token_ciphertext"] != "new-refresh-token"


def test_refresh_session_revokes_when_refresh_fails(
    service,
    repository,
    auth_repository,
):
    from guest_management.core.security import (
        encrypt_session_token,
        hash_session_id,
    )

    session_id = f"session-{uuid4().hex}"

    repository.get_active.return_value = {
        "id": 10,
        "session_id_hash": hash_session_id(session_id),
        "user_id": TEST_USER_ID,
        "access_token_ciphertext": encrypt_session_token(
            "old-access-token"
        ),
        "refresh_token_ciphertext": encrypt_session_token(
            "old-refresh-token"
        ),
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "last_used_at": datetime.now(timezone.utc),
        "revoked_at": None,
    }

    auth_repository.refresh_session.return_value = None

    result = service.refresh_session(session_id)

    assert result is None
    repository.revoke.assert_called_once_with(
        hash_session_id(session_id)
    )


def test_refresh_session_returns_none_when_update_fails(
    service,
    repository,
    auth_repository,
):
    from guest_management.core.security import (
        encrypt_session_token,
        hash_session_id,
    )

    session_id = f"session-{uuid4().hex}"

    repository.get_active.return_value = {
        "id": 10,
        "session_id_hash": hash_session_id(session_id),
        "user_id": TEST_USER_ID,
        "access_token_ciphertext": encrypt_session_token(
            "old-access-token"
        ),
        "refresh_token_ciphertext": encrypt_session_token(
            "old-refresh-token"
        ),
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        "last_used_at": datetime.now(timezone.utc),
        "revoked_at": None,
    }

    auth_repository.refresh_session.return_value = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "user": {
            "id": TEST_USER_ID,
        },
    }

    repository.update_tokens.return_value = False

    result = service.refresh_session(session_id)

    assert result is None