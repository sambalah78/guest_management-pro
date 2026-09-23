from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from guest_management.auth_api import (
    SESSION_COOKIE_SECURE,
    api,
)


client = TestClient(api)


def test_auth_health():
    response = client.get("/api/auth/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_create_auth_session_sets_secure_httponly_cookie():
    authentication = {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "user": {
            "id": "user-123",
            "email": "admin@example.com",
            "role": "ADMIN",
            "is_active": True,
        },
    }

    with (
        patch(
            "guest_management.auth_api.AuthRepository"
        ) as repository_class,
        patch(
            "guest_management.auth_api.AuthSessionService"
        ) as session_service_class,
    ):
        repository = repository_class.return_value

        repository.sign_in_with_password.return_value = authentication

        session_service = session_service_class.return_value
        session_service.create_session.return_value = (
            "opaque-session-id"
        )

        response = client.post(
            "/api/auth/session",
            json={
                "email": " ADMIN@example.com ",
                "password": "correct-password",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "user": authentication["user"],
    }

    repository.sign_in_with_password.assert_called_once_with(
        "admin@example.com",
        "correct-password",
    )

    session_service.create_session.assert_called_once_with(
        user_id="user-123",
        access_token="access-token",
        refresh_token="refresh-token",
    )

    set_cookie = response.headers["set-cookie"]

    assert "eventlah_session=opaque-session-id" in set_cookie
    assert "HttpOnly" in set_cookie

    if SESSION_COOKIE_SECURE:
        assert "Secure" in set_cookie
    else:
        assert "Secure" not in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie

    # Supabase credentials must never be returned to the browser.
    assert "access-token" not in response.text
    assert "refresh-token" not in response.text


def test_create_auth_session_rejects_invalid_credentials():
    with patch(
        "guest_management.auth_api.AuthRepository"
    ) as repository_class:
        repository = repository_class.return_value

        repository.sign_in_with_password.side_effect = PermissionError(
            "invalid credentials"
        )

        response = client.post(
            "/api/auth/session",
            json={
                "email": "admin@example.com",
                "password": "wrong-password",
            },
        )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password."
    }


def test_create_auth_session_rejects_empty_email():
    response = client.post(
        "/api/auth/session",
        json={
            "email": "",
            "password": "password",
        },
    )

    assert response.status_code == 422


def test_create_auth_session_does_not_expose_internal_error():
    with patch(
        "guest_management.auth_api.AuthRepository"
    ) as repository_class:
        repository = repository_class.return_value

        repository.sign_in_with_password.side_effect = RuntimeError(
            "database credentials leaked here"
        )

        response = client.post(
            "/api/auth/session",
            json={
                "email": "admin@example.com",
                "password": "password",
            },
        )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Authentication service error."
    }

    assert "database credentials leaked here" not in response.text


def test_logout_revokes_session_and_clears_cookie():
    with patch(
        "guest_management.auth_api.AuthSessionService"
    ) as session_service_class:
        session_service = session_service_class.return_value

        response = client.post(
            "/api/auth/session/logout",
            cookies={
                "eventlah_session": "opaque-session-id",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    session_service.revoke_session.assert_called_once_with(
        "opaque-session-id"
    )

    set_cookie = response.headers["set-cookie"]

    assert "eventlah_session=" in set_cookie
    assert "Max-Age=0" in set_cookie
    assert "HttpOnly" in set_cookie

    if SESSION_COOKIE_SECURE:
        assert "Secure" in set_cookie
    else:
        assert "Secure" not in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie


def test_logout_without_cookie_still_clears_cookie():
    with patch(
        "guest_management.auth_api.AuthSessionService"
    ) as session_service_class:
        session_service = session_service_class.return_value

        response = client.post(
            "/api/auth/session/logout"
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    session_service.revoke_session.assert_not_called()

    set_cookie = response.headers["set-cookie"]

    assert "eventlah_session=" in set_cookie
    assert "Max-Age=0" in set_cookie
    assert "HttpOnly" in set_cookie

    if SESSION_COOKIE_SECURE:
        assert "Secure" in set_cookie
    else:
        assert "Secure" not in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie

def test_create_auth_session_rejects_foreign_origin():
    with patch(
        "guest_management.auth_api.AuthRepository"
    ) as repository_class:
        response = client.post(
            "/api/auth/session",
            headers={"Origin": "https://attacker.example"},
            json={
                "email": "admin@example.com",
                "password": "correct-password",
            },
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid request origin."}
    repository_class.return_value.sign_in_with_password.assert_not_called()


def test_create_auth_session_allows_missing_origin():
    authentication = {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "user": {
            "id": "user-123",
            "email": "admin@example.com",
            "role": "ADMIN",
            "is_active": True,
        },
    }

    with (
        patch(
            "guest_management.auth_api.AuthRepository"
        ) as repository_class,
        patch(
            "guest_management.auth_api.AuthSessionService"
        ) as session_service_class,
    ):
        repository = repository_class.return_value
        repository.sign_in_with_password.return_value = authentication

        session_service = session_service_class.return_value
        session_service.create_session.return_value = "opaque-session-id"

        response = client.post(
            "/api/auth/session",
            json={
                "email": "admin@example.com",
                "password": "correct-password",
            },
        )

    assert response.status_code == 200


def test_logout_rejects_foreign_origin():
    with patch(
        "guest_management.auth_api.AuthSessionService"
    ) as session_service_class:
        response = client.post(
            "/api/auth/session/logout",
            headers={"Origin": "https://attacker.example"},
            cookies={
                "eventlah_session": "opaque-session-id",
            },
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid request origin."}
    session_service_class.return_value.revoke_session.assert_not_called()


def test_logout_allows_missing_origin():
    with patch(
        "guest_management.auth_api.AuthSessionService"
    ) as session_service_class:
        response = client.post(
            "/api/auth/session/logout",
            cookies={
                "eventlah_session": "opaque-session-id",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    session_service_class.return_value.revoke_session.assert_called_once_with(
        "opaque-session-id"
    )
