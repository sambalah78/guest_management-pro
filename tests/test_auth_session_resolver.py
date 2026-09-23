from unittest.mock import Mock, patch

import pytest

from guest_management.services.auth_session_resolver import (
    AuthSessionResolutionError,
    AuthSessionResolver,
)


@pytest.fixture
def session_service():
    return Mock()


@pytest.fixture
def auth_repository():
    return Mock()


@pytest.fixture
def resolver(session_service, auth_repository):
    return AuthSessionResolver(
        session_service=session_service,
        auth_repository=auth_repository,
    )


def test_no_session_cookie_returns_none(
    resolver,
    session_service,
):
    with patch(
        "guest_management.services.auth_session_resolver.get_session_id",
        return_value=None,
    ):
        assert resolver.get_current_user() is None

    session_service.get_session_metadata.assert_not_called()


def test_invalid_session_returns_none(
    resolver,
    session_service,
):
    session_service.get_session_metadata.return_value = None

    with patch(
        "guest_management.services.auth_session_resolver.get_session_id",
        return_value="valid-looking-session-id",
    ):
        assert resolver.get_current_user() is None

    session_service.get_session_metadata.assert_called_once_with(
        "valid-looking-session-id"
    )


def test_resolves_active_user(
    resolver,
    session_service,
    auth_repository,
):
    session_service.get_session_metadata.return_value = {
        "session_id_hash": "hash",
        "user_id": "user-123",
    }

    auth_repository.get_user.return_value = {
        "id": "user-123",
        "email": "admin@example.com",
        "role": "ADMIN",
        "is_active": True,
    }

    with patch(
        "guest_management.services.auth_session_resolver.get_session_id",
        return_value="session-id",
    ):
        result = resolver.get_current_user()

    assert result == {
        "id": "user-123",
        "email": "admin@example.com",
        "role": "ADMIN",
        "is_active": True,
    }

    auth_repository.get_user.assert_called_once_with("user-123")


def test_inactive_user_returns_none(
    resolver,
    session_service,
    auth_repository,
):
    session_service.get_session_metadata.return_value = {
        "session_id_hash": "hash",
        "user_id": "user-123",
    }

    auth_repository.get_user.return_value = {
        "id": "user-123",
        "email": "admin@example.com",
        "role": "ADMIN",
        "is_active": False,
    }

    with patch(
        "guest_management.services.auth_session_resolver.get_session_id",
        return_value="session-id",
    ):
        assert resolver.get_current_user() is None


def test_missing_user_id_returns_none(
    resolver,
    session_service,
):
    session_service.get_session_metadata.return_value = {
        "session_id_hash": "hash",
        "user_id": None,
    }

    with patch(
        "guest_management.services.auth_session_resolver.get_session_id",
        return_value="session-id",
    ):
        assert resolver.get_current_user() is None


def test_missing_user_profile_returns_none(
    resolver,
    session_service,
    auth_repository,
):
    session_service.get_session_metadata.return_value = {
        "session_id_hash": "hash",
        "user_id": "user-123",
    }

    auth_repository.get_user.return_value = None

    with patch(
        "guest_management.services.auth_session_resolver.get_session_id",
        return_value="session-id",
    ):
        assert resolver.get_current_user() is None


def test_session_service_failure_raises_resolution_error(
    resolver,
    session_service,
):
    session_service.get_session_metadata.side_effect = RuntimeError(
        "database unavailable"
    )

    with patch(
        "guest_management.services.auth_session_resolver.get_session_id",
        return_value="session-id",
    ):
        with pytest.raises(
            AuthSessionResolutionError,
            match="Unable to resolve authenticated session",
        ):
            resolver.get_current_user()


def test_auth_repository_failure_raises_resolution_error(
    resolver,
    session_service,
    auth_repository,
):
    session_service.get_session_metadata.return_value = {
        "session_id_hash": "hash",
        "user_id": "user-123",
    }

    auth_repository.get_user.side_effect = RuntimeError(
        "database unavailable"
    )

    with patch(
        "guest_management.services.auth_session_resolver.get_session_id",
        return_value="session-id",
    ):
        with pytest.raises(
            AuthSessionResolutionError,
            match="Unable to resolve authenticated session",
        ):
            resolver.get_current_user()


def test_require_current_user_returns_user(
    resolver,
):
    expected_user = {
        "id": "user-123",
        "email": "admin@example.com",
        "role": "ADMIN",
        "is_active": True,
    }

    with patch.object(
        resolver,
        "get_current_user",
        return_value=expected_user,
    ):
        assert resolver.require_current_user() == expected_user


def test_require_current_user_raises_when_unauthenticated(
    resolver,
):
    with patch.object(
        resolver,
        "get_current_user",
        return_value=None,
    ):
        with pytest.raises(
            PermissionError,
            match="Authentication required",
        ):
            resolver.require_current_user()
