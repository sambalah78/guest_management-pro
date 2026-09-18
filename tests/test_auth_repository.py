from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from guest_management.repositories.auth_repository import AuthRepository


def make_user(
    *,
    user_id="user-123",
    email="user@example.com",
):
    return SimpleNamespace(
        id=user_id,
        email=email,
        phone=None,
        role=None,
        created_at=None,
        updated_at=None,
        user_metadata={},
        app_metadata={},
    )


def make_session(
    *,
    access_token="access-token",
    refresh_token="refresh-token",
):
    return SimpleNamespace(
        access_token=access_token,
        refresh_token=refresh_token,
    )


def make_auth_response(
    *,
    user=None,
    session=None,
):
    return SimpleNamespace(
        user=user,
        session=session,
    )


def make_profile(
    *,
    user_id="user-123",
    email="user@example.com",
    role="ADMIN",
    is_active=True,
):
    return {
        "id": user_id,
        "email": email,
        "name": "Test User",
        "picture_url": "",
        "role": role,
        "is_active": is_active,
    }


def test_get_supabase_client_requires_url():
    repo = AuthRepository()

    with patch(
        "guest_management.repositories.auth_repository.settings"
    ) as mocked_settings:
        mocked_settings.supabase_url = ""
        mocked_settings.supabase_anon_key = "anon-key"

        with pytest.raises(
            RuntimeError,
            match="SUPABASE_URL is not configured",
        ):
            repo._get_supabase_client()


def test_get_supabase_client_requires_anon_key():
    repo = AuthRepository()

    with patch(
        "guest_management.repositories.auth_repository.settings"
    ) as mocked_settings:
        mocked_settings.supabase_url = "https://example.supabase.co"
        mocked_settings.supabase_anon_key = ""

        with pytest.raises(
            RuntimeError,
            match="SUPABASE_ANON_KEY is not configured",
        ):
            repo._get_supabase_client()


def test_get_supabase_client_uses_anon_key():
    repo = AuthRepository()

    fake_client = MagicMock()

    with patch(
        "guest_management.repositories.auth_repository.settings"
    ) as mocked_settings:
        mocked_settings.supabase_url = "https://example.supabase.co"
        mocked_settings.supabase_anon_key = "anon-key"

        with patch(
            "guest_management.repositories.auth_repository.create_client",
            return_value=fake_client,
        ) as create_client:
            result = repo._get_supabase_client()

    assert result is fake_client
    create_client.assert_called_once_with(
        "https://example.supabase.co",
        "anon-key",
    )


def test_get_supabase_server_client_requires_secret_key():
    repo = AuthRepository()

    with patch(
        "guest_management.repositories.auth_repository.settings"
    ) as mocked_settings:
        mocked_settings.supabase_url = "https://example.supabase.co"
        mocked_settings.supabase_secret_key = ""

        with pytest.raises(
            RuntimeError,
            match="SUPABASE_SECRET_KEY is not configured",
        ):
            repo._get_supabase_server_client()


def test_get_supabase_server_client_uses_service_role_key():
    repo = AuthRepository()

    fake_client = MagicMock()

    with patch(
        "guest_management.repositories.auth_repository.settings"
    ) as mocked_settings:
        mocked_settings.supabase_url = "https://example.supabase.co"
        mocked_settings.supabase_secret_key = "service-role-key"

        with patch(
            "guest_management.repositories.auth_repository.create_client",
            return_value=fake_client,
        ) as create_client:
            result = repo._get_supabase_server_client()

    assert result is fake_client
    create_client.assert_called_once_with(
        "https://example.supabase.co",
        "service-role-key",
    )


def test_sign_in_with_password_returns_normalized_session():
    repo = AuthRepository()

    client = MagicMock()

    auth_user = make_user(
        email="USER@EXAMPLE.COM",
    )

    client.auth.sign_in_with_password.return_value = (
        make_auth_response(
            user=auth_user,
            session=make_session(),
        )
    )

    profile = make_profile(
        email="user@example.com",
    )

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ), patch.object(
        repo,
        "get_user",
        return_value=profile,
    ) as get_user:
        result = repo.sign_in_with_password(
            "  USER@EXAMPLE.COM  ",
            "password",
        )

    assert result == {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "user": profile,
    }

    client.auth.sign_in_with_password.assert_called_once_with(
        {
            "email": "user@example.com",
            "password": "password",
        }
    )

    get_user.assert_called_once_with("user-123")


def test_sign_in_rejects_missing_session():
    repo = AuthRepository()

    client = MagicMock()

    client.auth.sign_in_with_password.return_value = (
        make_auth_response(
            user=make_user(),
            session=None,
        )
    )

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ):
        with pytest.raises(
            RuntimeError,
            match="without a session",
        ):
            repo.sign_in_with_password(
                "user@example.com",
                "password",
            )


def test_sign_in_rejects_missing_supabase_user():
    repo = AuthRepository()

    client = MagicMock()

    client.auth.sign_in_with_password.return_value = (
        make_auth_response(
            user=None,
            session=make_session(),
        )
    )

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ):
        with pytest.raises(
            RuntimeError,
            match="without a user",
        ):
            repo.sign_in_with_password(
                "user@example.com",
                "password",
            )


def test_sign_in_rejects_missing_access_token():
    repo = AuthRepository()

    client = MagicMock()

    client.auth.sign_in_with_password.return_value = (
        make_auth_response(
            user=make_user(),
            session=make_session(
                access_token="",
            ),
        )
    )

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ):
        with pytest.raises(
            RuntimeError,
            match="did not return an access token",
        ):
            repo.sign_in_with_password(
                "user@example.com",
                "password",
            )


def test_sign_in_rejects_missing_eventlah_profile():
    repo = AuthRepository()

    client = MagicMock()

    client.auth.sign_in_with_password.return_value = (
        make_auth_response(
            user=make_user(),
            session=make_session(),
        )
    )

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ), patch.object(
        repo,
        "get_user",
        return_value=None,
    ):
        with pytest.raises(
            PermissionError,
            match="does not have an active EventLah user profile",
        ):
            repo.sign_in_with_password(
                "user@example.com",
                "password",
            )


def test_sign_in_rejects_inactive_eventlah_profile():
    repo = AuthRepository()

    client = MagicMock()

    client.auth.sign_in_with_password.return_value = (
        make_auth_response(
            user=make_user(),
            session=make_session(),
        )
    )

    inactive_profile = make_profile(
        is_active=False,
    )

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ), patch.object(
        repo,
        "get_user",
        return_value=inactive_profile,
    ):
        with pytest.raises(
            PermissionError,
            match="account is inactive",
        ):
            repo.sign_in_with_password(
                "user@example.com",
                "password",
            )


def test_sign_out_sets_session_and_signs_out_locally():
    repo = AuthRepository()

    client = MagicMock()

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ):
        result = repo.sign_out(
            access_token="access-token",
            refresh_token="refresh-token",
        )

    assert result is None

    client.auth.set_session.assert_called_once_with(
        "access-token",
        "refresh-token",
    )

    client.auth.sign_out.assert_called_once_with(
        {"scope": "local"}
    )


def test_sign_out_does_nothing_without_complete_session():
    repo = AuthRepository()

    with patch.object(
        repo,
        "_get_supabase_client",
    ) as get_client:
        repo.sign_out(
            access_token="",
            refresh_token="refresh-token",
        )

        repo.sign_out(
            access_token="access-token",
            refresh_token="",
        )

    get_client.assert_not_called()


def test_refresh_session_returns_new_session():
    repo = AuthRepository()

    client = MagicMock()

    auth_user = make_user()
    client.auth.refresh_session.return_value = (
        make_auth_response(
            user=auth_user,
            session=make_session(
                access_token="new-access-token",
                refresh_token="new-refresh-token",
            ),
        )
    )

    profile = make_profile()

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ), patch.object(
        repo,
        "get_user",
        return_value=profile,
    ):
        result = repo.refresh_session("old-refresh-token")

    assert result == {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "user": profile,
    }

    client.auth.refresh_session.assert_called_once_with(
        "old-refresh-token",
    )


def test_refresh_session_preserves_old_refresh_token_when_provider_omits_one():
    repo = AuthRepository()

    client = MagicMock()

    client.auth.refresh_session.return_value = (
        make_auth_response(
            user=make_user(),
            session=make_session(
                access_token="new-access-token",
                refresh_token=None,
            ),
        )
    )

    profile = make_profile()

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ), patch.object(
        repo,
        "get_user",
        return_value=profile,
    ):
        result = repo.refresh_session("old-refresh-token")

    assert result["access_token"] == "new-access-token"
    assert result["refresh_token"] == "old-refresh-token"
    assert result["user"] == profile


def test_refresh_session_returns_none_without_token():
    repo = AuthRepository()

    with patch.object(
        repo,
        "_get_supabase_client",
    ) as get_client:
        result = repo.refresh_session("")

    assert result is None
    get_client.assert_not_called()


def test_refresh_session_rejects_missing_profile():
    repo = AuthRepository()

    client = MagicMock()

    client.auth.refresh_session.return_value = (
        make_auth_response(
            user=make_user(),
            session=make_session(),
        )
    )

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ), patch.object(
        repo,
        "get_user",
        return_value=None,
    ):
        result = repo.refresh_session("refresh-token")

    assert result is None


def test_refresh_session_rejects_inactive_profile():
    repo = AuthRepository()

    client = MagicMock()

    client.auth.refresh_session.return_value = (
        make_auth_response(
            user=make_user(),
            session=make_session(),
        )
    )

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ), patch.object(
        repo,
        "get_user",
        return_value=make_profile(
            is_active=False,
        ),
    ):
        result = repo.refresh_session("refresh-token")

    assert result is None


def test_get_user_returns_normalized_profile():
    repo = AuthRepository()

    response = MagicMock()
    response.data = [
        {
            "id": "user-123",
            "email": "  USER@EXAMPLE.COM  ",
            "name": "",
            "picture_url": None,
            "role": "admin",
            "is_active": 1,
        }
    ]

    server_client = MagicMock()
    (
        server_client
        .table.return_value
        .select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = response

    with patch.object(
        repo,
        "_get_supabase_server_client",
        return_value=server_client,
    ):
        result = repo.get_user("user-123")

    assert result["id"] == "user-123"
    assert result["email"] == "user@example.com"
    assert result["name"] == "user@example.com"
    assert result["picture"] == ""
    assert result["role"] == "ADMIN"
    assert result["is_active"] is True


def test_get_user_returns_none_for_missing_user_id():
    repo = AuthRepository()

    with patch.object(
        repo,
        "_get_supabase_server_client",
    ) as get_client:
        result = repo.get_user("")

    assert result is None
    get_client.assert_not_called()


def test_get_user_returns_none_when_profile_does_not_exist():
    repo = AuthRepository()

    response = MagicMock()
    response.data = []

    server_client = MagicMock()
    (
        server_client
        .table.return_value
        .select.return_value
        .eq.return_value
        .limit.return_value
        .execute.return_value
    ) = response

    with patch.object(
        repo,
        "_get_supabase_server_client",
        return_value=server_client,
    ):
        result = repo.get_user("missing-user")

    assert result is None


def test_get_user_by_access_token_returns_profile():
    repo = AuthRepository()

    client = MagicMock()

    auth_user = make_user()

    client.auth.get_user.return_value = SimpleNamespace(
        user=auth_user,
    )

    profile = make_profile()

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ), patch.object(
        repo,
        "get_user",
        return_value=profile,
    ) as get_user:
        result = repo.get_user_by_access_token(
            "access-token",
        )

    assert result == profile

    client.auth.get_user.assert_called_once_with(
        "access-token",
    )

    get_user.assert_called_once_with(
        "user-123",
    )


def test_get_user_by_access_token_returns_none_without_token():
    repo = AuthRepository()

    with patch.object(
        repo,
        "_get_supabase_client",
    ) as get_client:
        result = repo.get_user_by_access_token("")

    assert result is None
    get_client.assert_not_called()


def test_get_user_by_access_token_returns_none_when_supabase_user_missing():
    repo = AuthRepository()

    client = MagicMock()

    client.auth.get_user.return_value = SimpleNamespace(
        user=None,
    )

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ):
        result = repo.get_user_by_access_token(
            "invalid-token",
        )

    assert result is None


def test_get_user_by_access_token_returns_none_when_provider_raises():
    repo = AuthRepository()

    client = MagicMock()
    client.auth.get_user.side_effect = RuntimeError(
        "Supabase unavailable"
    )

    with patch.object(
        repo,
        "_get_supabase_client",
        return_value=client,
    ):
        result = repo.get_user_by_access_token(
            "access-token",
        )

    assert result is None


def test_user_to_dict_accepts_dictionary():
    user = {
        "id": "user-123",
        "email": "user@example.com",
    }

    result = AuthRepository._user_to_dict(user)

    assert result == user


def test_user_to_dict_extracts_supported_attributes():
    user = make_user()

    result = AuthRepository._user_to_dict(user)

    assert result["id"] == "user-123"
    assert result["email"] == "user@example.com"
    assert result["phone"] is None
    assert result["role"] is None
