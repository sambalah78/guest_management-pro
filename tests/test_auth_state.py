import asyncio
from types import SimpleNamespace

import guest_management.state.auth_state as auth_state_module
from guest_management.state.auth_state import AuthState


class FakeAuthService:
    def __init__(
        self,
        *,
        login_result=None,
        current_user=None,
        refresh_result=None,
        login_error=None,
        logout_error=None,
    ):
        self.login_result = login_result
        self.current_user = current_user
        self.refresh_result = refresh_result
        self.login_error = login_error
        self.logout_error = logout_error
        self.login_calls = []
        self.logout_calls = []
        self.refresh_calls = []
        self.current_user_calls = []

    def login(self, email, password):
        self.login_calls.append(
            {
                "email": email,
                "password": password,
            }
        )

        if self.login_error:
            raise self.login_error

        return self.login_result

    def logout(self, access_token, refresh_token):
        self.logout_calls.append(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        )

        if self.logout_error:
            raise self.logout_error

    def get_current_user(self, access_token):
        self.current_user_calls.append(access_token)
        return self.current_user

    def refresh_session(self, refresh_token):
        self.refresh_calls.append(refresh_token)
        return self.refresh_result


def make_user(
    *,
    user_id="user-123",
    email="USER@EXAMPLE.COM",
    role="ADMIN",
    is_active=True,
):
    return {
        "id": user_id,
        "email": email,
        "name": "Test User",
        "role": role,
        "is_active": is_active,
    }


def make_state():
    state = AuthState()

    state.username = ""
    state.password = ""
    state.auth_error = ""
    state.is_authenticated = False
    state.user = {}
    state.user_id = ""
    state.user_email = ""
    state.auth_checked = False
    state.is_loading = False
    state.access_token = ""
    state.refresh_token = ""

    return state


def run_async_event(event):
    results = []

    async def runner():
        result = event

        if hasattr(result, "__aiter__"):
            async for item in result:
                results.append(item)
        else:
            value = await result
            if value is not None:
                results.append(value)

    asyncio.run(runner())
    return results


def test_apply_user_normalizes_user_data():
    state = make_state()

    state._apply_user(
        make_user(
            email="  USER@EXAMPLE.COM  ",
        )
    )

    assert state.user_id == "user-123"
    assert state.user_email == "user@example.com"
    assert state.is_authenticated is True
    assert state.auth_error == ""


def test_apply_user_without_id_is_not_authenticated():
    state = make_state()

    state._apply_user(
        {
            "id": "",
            "email": "user@example.com",
            "role": "ADMIN",
        }
    )

    assert state.is_authenticated is False
    assert state.user_id == ""


def test_clear_auth_state_removes_all_local_authentication_state():
    state = make_state()

    state.access_token = "access-token"
    state.refresh_token = "refresh-token"
    state.is_authenticated = True
    state.user_id = "user-123"
    state.user_email = "user@example.com"
    state.user = make_user()
    state.auth_error = "old error"

    state._clear_auth_state()

    assert state.access_token == ""
    assert state.refresh_token == ""
    assert state.is_authenticated is False
    assert state.user_id == ""
    assert state.user_email == ""
    assert state.user == {}
    assert state.auth_error == ""


def test_is_logged_in_requires_authenticated_user():
    state = make_state()

    assert state.is_logged_in is False

    state.is_authenticated = True
    assert state.is_logged_in is False

    state.user_id = "user-123"
    assert state.is_logged_in is True


def test_is_event_admin_allows_owner_and_admin_only():
    for role in ("OWNER", "ADMIN"):
        state = make_state()
        state._apply_user(make_user(role=role))

        assert state.is_event_admin is True

    for role in ("USER", "GUEST", ""):
        state = make_state()
        state._apply_user(make_user(role=role))

        assert state.is_event_admin is False


def test_is_owner_only_allows_owner():
    state = make_state()
    state._apply_user(make_user(role="OWNER"))
    assert state.is_owner is True

    state = make_state()
    state._apply_user(make_user(role="ADMIN"))
    assert state.is_owner is False


def test_login_rejects_missing_email():
    state = make_state()
    state.username = ""
    state.password = "password"

    fake = FakeAuthService()

    auth_service = lambda: fake

    original = auth_state_module.AuthService
    auth_state_module.AuthService = auth_service

    try:
        run_async_event(state.login())
    finally:
        auth_state_module.AuthService = original

    assert state.auth_error == "Please enter your email address."
    assert state.is_authenticated is False
    assert state.is_loading is False
    assert fake.login_calls == []


def test_login_rejects_missing_password():
    state = make_state()
    state.username = "USER@EXAMPLE.COM"
    state.password = ""

    fake = FakeAuthService()

    auth_service = lambda: fake

    original = auth_state_module.AuthService
    auth_state_module.AuthService = auth_service

    try:
        run_async_event(state.login())
    finally:
        auth_state_module.AuthService = original

    assert state.auth_error == "Please enter your password."
    assert state.is_authenticated is False
    assert state.is_loading is False
    assert fake.login_calls == []


def test_login_success_normalizes_email_stores_tokens_and_clears_password():
    state = make_state()
    state.username = "  USER@EXAMPLE.COM  "
    state.password = "secret-password"

    user = make_user(
        email="user@example.com",
        role="ADMIN",
    )

    fake = FakeAuthService(
        login_result={
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "user": user,
        }
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        results = run_async_event(state.login())
    finally:
        auth_state_module.AuthService = original

    assert fake.login_calls == [
        {
            "email": "user@example.com",
            "password": "secret-password",
        }
    ]

    assert state.access_token == "access-token"
    assert state.refresh_token == "refresh-token"
    assert state.user_id == "user-123"
    assert state.user_email == "user@example.com"
    assert state.is_authenticated is True
    assert state.auth_checked is True
    assert state.password == ""
    assert state.auth_error == ""
    assert state.is_loading is False

    assert len(results) == 1


def test_login_rejects_missing_user_in_service_result():
    state = make_state()
    state.username = "user@example.com"
    state.password = "password"

    fake = FakeAuthService(
        login_result={
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "user": None,
        }
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        run_async_event(state.login())
    finally:
        auth_state_module.AuthService = original

    assert "EventLah profile could not be found" in state.auth_error
    assert state.is_authenticated is False
    assert state.access_token == ""
    assert state.refresh_token == ""
    assert state.is_loading is False


def test_login_rejects_missing_access_token():
    state = make_state()
    state.username = "user@example.com"
    state.password = "password"

    fake = FakeAuthService(
        login_result={
            "access_token": "",
            "refresh_token": "refresh-token",
            "user": make_user(),
        }
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        run_async_event(state.login())
    finally:
        auth_state_module.AuthService = original

    assert "no access token was returned" in state.auth_error
    assert state.is_authenticated is False
    assert state.is_loading is False


def test_login_rejects_missing_refresh_token():
    state = make_state()
    state.username = "user@example.com"
    state.password = "password"

    fake = FakeAuthService(
        login_result={
            "access_token": "access-token",
            "refresh_token": "",
            "user": make_user(),
        }
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        run_async_event(state.login())
    finally:
        auth_state_module.AuthService = original

    assert "no refresh token was returned" in state.auth_error
    assert state.is_authenticated is False
    assert state.is_loading is False


def test_login_permission_error_clears_auth_state():
    state = make_state()
    state.username = "user@example.com"
    state.password = "password"

    fake = FakeAuthService(
        login_error=PermissionError("This EventLah account is inactive.")
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        run_async_event(state.login())
    finally:
        auth_state_module.AuthService = original

    assert state.auth_error == ""
    assert state.is_authenticated is False
    assert state.access_token == ""
    assert state.refresh_token == ""
    assert state.is_loading is False


def test_login_value_error_preserves_error_without_authentication():
    state = make_state()
    state.username = "user@example.com"
    state.password = "password"

    fake = FakeAuthService(
        login_error=ValueError("Invalid credentials.")
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        run_async_event(state.login())
    finally:
        auth_state_module.AuthService = original

    assert state.auth_error == "Invalid credentials."
    assert state.is_authenticated is False
    assert state.is_loading is False


def test_login_unexpected_error_uses_generic_message_and_clears_state():
    state = make_state()
    state.username = "user@example.com"
    state.password = "password"

    fake = FakeAuthService(
        login_error=RuntimeError("database exploded")
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        run_async_event(state.login())
    finally:
        auth_state_module.AuthService = original

    assert state.auth_error == ""
    assert state.is_authenticated is False
    assert state.access_token == ""
    assert state.refresh_token == ""
    assert state.is_loading is False


def test_logout_calls_service_and_clears_local_session():
    state = make_state()

    state.access_token = "access-token"
    state.refresh_token = "refresh-token"
    state._apply_user(make_user())

    fake = FakeAuthService()

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        results = state.logout()
    finally:
        auth_state_module.AuthService = original

    assert fake.logout_calls == [
        {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
        }
    ]

    assert state.access_token == ""
    assert state.refresh_token == ""
    assert state.is_authenticated is False
    assert state.user_id == ""
    assert state.user_email == ""
    assert state.user == {}
    assert state.auth_checked is True

    assert len(results) == 3


def test_logout_clears_local_session_when_remote_logout_fails():
    state = make_state()

    state.access_token = "access-token"
    state.refresh_token = "refresh-token"
    state._apply_user(make_user())

    fake = FakeAuthService(
        logout_error=RuntimeError("Supabase unavailable")
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        results = state.logout()
    finally:
        auth_state_module.AuthService = original

    assert state.access_token == ""
    assert state.refresh_token == ""
    assert state.is_authenticated is False
    assert state.user_id == ""
    assert state.user == {}
    assert state.auth_checked is True
    assert len(results) == 3


def test_public_route_detection():
    state = make_state()

    public_routes = (
        "/",
        "/home",
        "/login",
        "/about",
        "/products",
        "/contact",
        "/select-event-type",
        "/health",
        "/stall/18",
        "/scanner/18",
        "/scanner-guest/18",
        "/scanner_guest/18",
        "/checkin/18",
        "/success/18",
        "/already-checked/18",
        "/already_checked/18",
        "/lucky-draw-display/18",
    )

    for path in public_routes:
        assert state._is_public_route(path) is True


def test_protected_route_is_not_public():
    state = make_state()

    for path in (
        "/events",
        "/dashboard",
        "/admin",
        "/settings",
    ):
        assert state._is_public_route(path) is False


def test_empty_route_is_public():
    state = make_state()

    assert state._is_public_route("") is True


def test_get_valid_user_uses_current_access_token():
    state = make_state()
    state.access_token = "access-token"

    user = make_user()

    fake = FakeAuthService(
        current_user=user,
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        result = state._get_valid_user()
    finally:
        auth_state_module.AuthService = original

    assert result == user
    assert fake.current_user_calls == ["access-token"]
    assert fake.refresh_calls == []


def test_get_valid_user_refreshes_when_access_token_is_invalid():
    state = make_state()
    state.access_token = "expired-access-token"
    state.refresh_token = "refresh-token"

    refreshed_user = make_user()

    fake = FakeAuthService(
        current_user=None,
        refresh_result={
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "user": refreshed_user,
        },
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        result = state._get_valid_user()
    finally:
        auth_state_module.AuthService = original

    assert result == refreshed_user
    assert fake.current_user_calls == ["expired-access-token"]
    assert fake.refresh_calls == ["refresh-token"]
    assert state.access_token == "new-access-token"
    assert state.refresh_token == "new-refresh-token"


def test_get_valid_user_returns_none_when_access_token_invalid_and_no_refresh_token():
    state = make_state()
    state.access_token = "expired-access-token"
    state.refresh_token = ""

    fake = FakeAuthService(
        current_user=None,
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        result = state._get_valid_user()
    finally:
        auth_state_module.AuthService = original

    assert result is None
    assert fake.current_user_calls == ["expired-access-token"]
    assert fake.refresh_calls == []


def test_get_valid_user_rejects_incomplete_refresh_result():
    state = make_state()
    state.access_token = "expired-access-token"
    state.refresh_token = "refresh-token"

    fake = FakeAuthService(
        current_user=None,
        refresh_result={
            "access_token": "new-access-token",
            "refresh_token": "",
            "user": make_user(),
        },
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        result = state._get_valid_user()
    finally:
        auth_state_module.AuthService = original

    assert result is None
    assert state.access_token == "expired-access-token"
    assert state.refresh_token == "refresh-token"


def test_check_auth_allows_public_route_without_auth_lookup(monkeypatch):
    state = make_state()

    monkeypatch.setattr(
        AuthState,
        "_is_public_route",
        lambda self, path: True,
    )

    fake = FakeAuthService(
        current_user=make_user(),
    )

    monkeypatch.setattr(
        auth_state_module,
        "AuthService",
        lambda: fake,
    )

    results = run_async_event(state.check_auth())

    assert results == []
    assert state.auth_checked is True
    assert fake.current_user_calls == []


def test_check_auth_redirects_protected_route_when_session_invalid(monkeypatch):
    state = make_state()

    monkeypatch.setattr(
        AuthState,
        "_is_public_route",
        lambda self, path: False,
    )

    monkeypatch.setattr(
        AuthState,
        "_get_valid_user",
        lambda self: None,
    )

    results = run_async_event(state.check_auth())

    assert len(results) == 1
    assert state.auth_checked is True
    assert state.is_authenticated is False
    assert state.user_id == ""


def test_check_auth_applies_valid_user_on_protected_route(monkeypatch):
    state = make_state()

    user = make_user(
        email="USER@EXAMPLE.COM",
        role="OWNER",
    )

    monkeypatch.setattr(
        AuthState,
        "_is_public_route",
        lambda self, path: False,
    )

    monkeypatch.setattr(
        AuthState,
        "_get_valid_user",
        lambda self: user,
    )

    results = run_async_event(state.check_auth())

    assert results == []
    assert state.auth_checked is True
    assert state.is_authenticated is True
    assert state.user_id == "user-123"
    assert state.user_email == "user@example.com"
    assert state.is_owner is True


def test_check_session_on_load_restores_valid_session():
    state = make_state()
    state.access_token = "access-token"

    user = make_user()

    fake = FakeAuthService(
        current_user=user,
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        results = run_async_event(
            state.check_session_on_load()
        )
    finally:
        auth_state_module.AuthService = original

    assert results == []
    assert state.auth_checked is True
    assert state.is_authenticated is True
    assert state.user_id == "user-123"


def test_check_session_on_load_clears_invalid_session_without_redirect():
    state = make_state()
    state.access_token = "expired-token"
    state.refresh_token = ""

    fake = FakeAuthService(
        current_user=None,
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        results = run_async_event(
            state.check_session_on_load()
        )
    finally:
        auth_state_module.AuthService = original

    assert results == []
    assert state.auth_checked is True
    assert state.is_authenticated is False
    assert state.user_id == ""


def test_ensure_valid_session_returns_true_and_applies_user():
    state = make_state()
    state.access_token = "access-token"

    user = make_user()

    fake = FakeAuthService(
        current_user=user,
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        result = asyncio.run(
            state.ensure_valid_session()
        )
    finally:
        auth_state_module.AuthService = original

    assert result is True
    assert state.is_authenticated is True
    assert state.user_id == "user-123"


def test_ensure_valid_session_returns_false_and_clears_state():
    state = make_state()
    state.access_token = "expired-token"

    fake = FakeAuthService(
        current_user=None,
    )

    original = auth_state_module.AuthService
    auth_state_module.AuthService = lambda: fake

    try:
        result = asyncio.run(
            state.ensure_valid_session()
        )
    finally:
        auth_state_module.AuthService = original

    assert result is False
    assert state.is_authenticated is False
    assert state.user_id == ""


def test_set_username_strips_value():
    state = make_state()

    state.set_username("  user@example.com  ")

    assert state.username == "user@example.com"


def test_set_password_preserves_value():
    state = make_state()

    state.set_password("secret")

    assert state.password == "secret"


def test_set_access_token_preserves_compatibility_behavior():
    state = make_state()

    state.set_access_token("access-token")

    assert state.access_token == "access-token"

    state.set_access_token("")

    assert state.access_token == ""
