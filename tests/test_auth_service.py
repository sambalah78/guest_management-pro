from unittest.mock import MagicMock

import pytest

from guest_management.core.exceptions import AuthorizationError
from guest_management.services.auth_service import AuthService


def make_user(
    *,
    role="USER",
    is_active=True,
):
    return {
        "id": "user-123",
        "email": "user@example.com",
        "name": "Test User",
        "role": role,
        "is_active": is_active,
    }


def test_can_manage_events_requires_active_owner_or_admin():
    assert AuthService.can_manage_events(
        make_user(role="OWNER")
    ) is True

    assert AuthService.can_manage_events(
        make_user(role="ADMIN")
    ) is True

    assert AuthService.can_manage_events(
        make_user(role="USER")
    ) is False

    assert AuthService.can_manage_events(
        make_user(role="OWNER", is_active=False)
    ) is False

    assert AuthService.can_manage_events(
        make_user(role="ADMIN", is_active=False)
    ) is False

    assert AuthService.can_manage_events(None) is False


def test_is_owner_requires_active_owner():
    assert AuthService.is_owner(
        make_user(role="OWNER")
    ) is True

    assert AuthService.is_owner(
        make_user(role="ADMIN")
    ) is False

    assert AuthService.is_owner(
        make_user(role="OWNER", is_active=False)
    ) is False

    assert AuthService.is_owner(None) is False


def test_is_admin_requires_active_admin():
    assert AuthService.is_admin(
        make_user(role="ADMIN")
    ) is True

    assert AuthService.is_admin(
        make_user(role="OWNER")
    ) is False

    assert AuthService.is_admin(
        make_user(role="ADMIN", is_active=False)
    ) is False

    assert AuthService.is_admin(None) is False


def test_login_rejects_missing_email():
    repo = MagicMock()
    service = AuthService(repo=repo)

    with pytest.raises(ValueError, match="Email is required"):
        service.login("", "password")

    repo.sign_in_with_password.assert_not_called()


def test_login_rejects_missing_password():
    repo = MagicMock()
    service = AuthService(repo=repo)

    with pytest.raises(ValueError, match="Password is required"):
        service.login("user@example.com", "")

    repo.sign_in_with_password.assert_not_called()


def test_login_normalizes_email_and_returns_session():
    repo = MagicMock()

    user = make_user(role="ADMIN")

    repo.sign_in_with_password.return_value = {
        "user": user,
        "access_token": "access-token",
        "refresh_token": "refresh-token",
    }

    service = AuthService(repo=repo)

    result = service.login(
        "  USER@EXAMPLE.COM  ",
        "password",
    )

    assert result == {
        "user": user,
        "access_token": "access-token",
        "refresh_token": "refresh-token",
    }

    repo.sign_in_with_password.assert_called_once_with(
        email="user@example.com",
        password="password",
    )


def test_login_rejects_missing_user_from_repository():
    repo = MagicMock()

    repo.sign_in_with_password.return_value = {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "user": None,
    }

    service = AuthService(repo=repo)

    with pytest.raises(
        RuntimeError,
        match="no EventLah user profile",
    ):
        service.login(
            "user@example.com",
            "password",
        )


def test_get_current_user_delegates_to_repository():
    repo = MagicMock()

    user = make_user(role="ADMIN")
    repo.get_user_by_access_token.return_value = user

    service = AuthService(repo=repo)

    result = service.get_current_user("access-token")

    assert result == user
    repo.get_user_by_access_token.assert_called_once_with(
        "access-token"
    )


def test_get_current_user_returns_none_without_token():
    repo = MagicMock()
    service = AuthService(repo=repo)

    assert service.get_current_user("") is None
    repo.get_user_by_access_token.assert_not_called()


def test_refresh_session_returns_repository_result():
    repo = MagicMock()

    expected = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "user": make_user(role="OWNER"),
    }

    repo.refresh_session.return_value = expected

    service = AuthService(repo=repo)

    result = service.refresh_session("refresh-token")

    assert result == expected
    repo.refresh_session.assert_called_once_with(
        refresh_token="refresh-token"
    )


def test_refresh_session_returns_none_without_token():
    repo = MagicMock()
    service = AuthService(repo=repo)

    assert service.refresh_session("") is None
    repo.refresh_session.assert_not_called()


def test_logout_delegates_complete_session():
    repo = MagicMock()
    service = AuthService(repo=repo)

    service.logout(
        access_token="access-token",
        refresh_token="refresh-token",
    )

    repo.sign_out.assert_called_once_with(
        access_token="access-token",
        refresh_token="refresh-token",
    )


def test_logout_does_not_call_repository_without_complete_session():
    repo = MagicMock()
    service = AuthService(repo=repo)

    service.logout(
        access_token="",
        refresh_token="refresh-token",
    )

    repo.sign_out.assert_not_called()

    service.logout(
        access_token="access-token",
        refresh_token="",
    )

    repo.sign_out.assert_not_called()
