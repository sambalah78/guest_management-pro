import asyncio

import guest_management.state.auth_state as auth_state_module
from guest_management.state.auth_state import AuthState


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

    return state


def run_async_event(event):
    results = []

    async def runner():
        result = event

        if hasattr(result, "__aiter__"):
            async for item in result:
                results.append(item)
        elif hasattr(result, "__await__"):
            value = await result
            if value is not None:
                results.append(value)
        elif result is not None:
            results.append(result)

    asyncio.run(runner())
    return results


# ---------------------------------------------------------------------------
# Local authentication state
# ---------------------------------------------------------------------------


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


def test_clear_auth_state_removes_local_authentication_state():
    state = make_state()

    state.is_authenticated = True
    state.user_id = "user-123"
    state.user_email = "user@example.com"
    state.user = make_user()
    state.auth_error = "old error"

    state._clear_auth_state()

    assert state.is_authenticated is False
    assert state.user_id == ""
    assert state.user_email == ""
    assert state.user == {}
    assert state.auth_error == ""


def test_auth_state_has_no_browser_token_fields():
    state = make_state()

    assert not hasattr(state, "access_token")
    assert not hasattr(state, "refresh_token")


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


# ---------------------------------------------------------------------------
# Login validation
# ---------------------------------------------------------------------------


def test_login_rejects_missing_email():
    state = make_state()
    state.username = ""
    state.password = "password"

    result = state.login()

    assert state.auth_error == "Please enter your email address."
    assert state.is_authenticated is False
    assert state.is_loading is False
    assert result is not None


def test_login_rejects_missing_password():
    state = make_state()
    state.username = "USER@EXAMPLE.COM"
    state.password = ""

    result = state.login()

    assert state.auth_error == "Please enter your password."
    assert state.is_authenticated is False
    assert state.is_loading is False
    assert result is not None


# ---------------------------------------------------------------------------
# Browser -> server login flow
# ---------------------------------------------------------------------------


def test_login_calls_server_session_endpoint(monkeypatch):
    state = make_state()
    state.username = "  USER@EXAMPLE.COM  "
    state.password = "secret-password"

    captured = {}

    def fake_call_script(script, callback=None):
        captured["script"] = script
        captured["callback"] = callback
        return "LOGIN_EVENT"

    monkeypatch.setattr(
        auth_state_module.rx,
        "call_script",
        fake_call_script,
    )

    result = state.login()

    assert result == "LOGIN_EVENT"
    assert state.is_loading is True

    script = captured["script"]

    assert "/api/auth/session" in script
    assert "fetch(" in script
    assert '"POST"' in script
    assert '"Content-Type": "application/json"' in script
    assert "credentials" in script
    assert '"include"' in script
    # Credentials are supplied through the generated request body. Do not
    # assert literal credential values in generated JavaScript.
    assert "body:" in script
    assert "secret-password" in script
    assert captured["callback"] == AuthState.handle_login_result


def test_handle_login_result_success_applies_user_and_clears_password():
    state = make_state()

    state.username = "user@example.com"
    state.password = "secret-password"
    state.is_loading = True

    user = make_user(
        email="user@example.com",
        role="ADMIN",
    )

    result = state.handle_login_result(
        {
            "ok": True,
            "status": 200,
            "data": {
                "ok": True,
                "user": user,
            },
        }
    )

    assert result is not None
    assert state.user_id == "user-123"
    assert state.user_email == "user@example.com"
    assert state.is_authenticated is True
    assert state.auth_checked is True
    assert state.password == ""
    assert state.auth_error == ""
    assert state.is_loading is False


def test_handle_login_result_rejects_missing_user():
    state = make_state()
    state.password = "secret-password"
    state.is_loading = True

    state.handle_login_result(
        {
            "ok": True,
            "status": 200,
            "data": {
                "ok": True,
                "user": None,
            },
        }
    )

    assert state.is_authenticated is False
    assert state.user_id == ""
    assert state.password == ""
    assert state.is_loading is False
    assert "profile could not be found" in state.auth_error.lower()


def test_handle_login_result_handles_invalid_credentials():
    state = make_state()
    state.password = "secret-password"
    state.is_loading = True

    state.handle_login_result(
        {
            "ok": False,
            "status": 401,
            "data": {
                "detail": "Invalid credentials.",
            },
        }
    )

    assert state.is_authenticated is False
    assert state.password == ""
    assert state.is_loading is False
    assert state.auth_error == "Invalid credentials."


def test_handle_login_result_handles_server_error():
    state = make_state()
    state.password = "secret-password"
    state.is_loading = True

    state.handle_login_result(
        {
            "ok": False,
            "status": 500,
            "data": {
                "detail": "Internal server error.",
            },
        }
    )

    assert state.is_authenticated is False
    assert state.password == ""
    assert state.is_loading is False
    assert state.auth_error != ""


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


def test_logout_calls_server_logout_endpoint(monkeypatch):
    state = make_state()
    state._apply_user(make_user())
    state.auth_checked = True

    captured = {}

    def fake_call_script(script, callback=None):
        captured["script"] = script
        captured["callback"] = callback
        return "LOGOUT_EVENT"

    monkeypatch.setattr(
        auth_state_module.rx,
        "call_script",
        fake_call_script,
    )

    result = state.logout()

    assert result == "LOGOUT_EVENT"

    script = captured["script"]

    assert "/api/auth/session/logout" in script
    assert "fetch(" in script
    assert '"POST"' in script
    assert "credentials" in script
    assert '"include"' in script
    assert captured["callback"] == AuthState.handle_logout_result

    # The API request is asynchronous. Local authentication state is cleared
    # by handle_logout_result() after the browser callback completes.
    assert state.is_authenticated is True
    assert state.user_id == "user-123"
    assert state.user_email == "user@example.com"
    assert state.user == make_user()
    assert state.auth_checked is True


def test_handle_logout_result_clears_local_state():
    state = make_state()
    state._apply_user(make_user())
    state.password = "secret"
    state.auth_error = "old error"
    state.is_loading = True

    state.handle_logout_result(
        {
            "ok": True,
            "status": 200,
            "data": {
                "ok": True,
            },
        }
    )

    assert state.is_authenticated is False
    assert state.user_id == ""
    assert state.user_email == ""
    assert state.user == {}
    assert state.password == ""
    assert state.auth_error == ""
    assert state.is_loading is False
    assert state.auth_checked is True


def test_handle_logout_result_clears_local_state_even_when_server_fails():
    state = make_state()
    state._apply_user(make_user())
    state.is_loading = True

    state.handle_logout_result(
        {
            "ok": False,
            "status": 500,
            "data": {
                "detail": "Logout failed.",
            },
        }
    )

    assert state.is_authenticated is False
    assert state.user_id == ""
    assert state.user_email == ""
    assert state.user == {}
    assert state.is_loading is False
    assert state.auth_checked is True


# ---------------------------------------------------------------------------
# Session resolution
# ---------------------------------------------------------------------------


def test_get_valid_user_delegates_to_server_side_session_resolver(monkeypatch):
    state = make_state()
    user = make_user()

    calls = []

    class FakeResolver:
        def get_current_user(self):
            calls.append("get_current_user")
            return user

    monkeypatch.setattr(
        auth_state_module,
        "AuthSessionResolver",
        FakeResolver,
    )

    result = state._get_valid_user()

    assert result == user
    assert calls == ["get_current_user"]


def test_get_valid_user_returns_none_when_no_server_session(monkeypatch):
    state = make_state()

    class FakeResolver:
        def get_current_user(self):
            return None

    monkeypatch.setattr(
        auth_state_module,
        "AuthSessionResolver",
        FakeResolver,
    )

    assert state._get_valid_user() is None


def test_get_valid_user_handles_session_resolution_error(monkeypatch):
    state = make_state()

    class FakeResolver:
        def get_current_user(self):
            raise auth_state_module.AuthSessionResolutionError(
                "Unable to resolve authenticated session."
            )

    monkeypatch.setattr(
        auth_state_module,
        "AuthSessionResolver",
        FakeResolver,
    )

    assert state._get_valid_user() is None


def test_get_valid_user_handles_unexpected_error(monkeypatch):
    state = make_state()

    class FakeResolver:
        def get_current_user(self):
            raise RuntimeError("database exploded")

    monkeypatch.setattr(
        auth_state_module,
        "AuthSessionResolver",
        FakeResolver,
    )

    assert state._get_valid_user() is None


# ---------------------------------------------------------------------------
# Route protection
# ---------------------------------------------------------------------------


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
        "/lucky-draw-display",
        "/lucky-draw-display/18",
    ):
        assert state._is_public_route(path) is False


def test_empty_route_is_public():
    state = make_state()

    assert state._is_public_route("") is True


def test_check_auth_allows_public_route_without_session_lookup(monkeypatch):
    state = make_state()

    monkeypatch.setattr(
        AuthState,
        "_is_public_route",
        lambda self, path: True,
    )

    called = []

    monkeypatch.setattr(
        AuthState,
        "_get_valid_user",
        lambda self: called.append(True),
    )

    results = run_async_event(state.check_auth())

    assert results == []
    assert state.auth_checked is True
    assert called == []


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


# ---------------------------------------------------------------------------
# Session restoration
# ---------------------------------------------------------------------------


def test_check_session_on_load_restores_valid_server_session(monkeypatch):
    state = make_state()

    user = make_user()

    monkeypatch.setattr(
        AuthState,
        "_get_valid_user",
        lambda self: user,
    )

    results = run_async_event(
        state.check_session_on_load()
    )

    assert results == []
    assert state.auth_checked is True
    assert state.is_authenticated is True
    assert state.user_id == "user-123"


def test_check_session_on_load_clears_invalid_server_session(monkeypatch):
    state = make_state()
    state._apply_user(make_user())

    monkeypatch.setattr(
        AuthState,
        "_get_valid_user",
        lambda self: None,
    )

    results = run_async_event(
        state.check_session_on_load()
    )

    assert results == []
    assert state.auth_checked is True
    assert state.is_authenticated is False
    assert state.user_id == ""


def test_ensure_valid_session_returns_true_and_applies_user(monkeypatch):
    state = make_state()

    user = make_user()

    monkeypatch.setattr(
        AuthState,
        "_get_valid_user",
        lambda self: user,
    )

    result = asyncio.run(
        state.ensure_valid_session()
    )

    assert result is True
    assert state.is_authenticated is True
    assert state.user_id == "user-123"


def test_ensure_valid_session_returns_false_and_clears_state(monkeypatch):
    state = make_state()
    state._apply_user(make_user())

    monkeypatch.setattr(
        AuthState,
        "_get_valid_user",
        lambda self: None,
    )

    result = asyncio.run(
        state.ensure_valid_session()
    )

    assert result is False
    assert state.is_authenticated is False
    assert state.user_id == ""


# ---------------------------------------------------------------------------
# Input setters
# ---------------------------------------------------------------------------


def test_set_username_strips_value():
    state = make_state()

    state.set_username("  user@example.com  ")

    assert state.username == "user@example.com"


def test_set_password_preserves_value():
    state = make_state()

    state.set_password("secret")

    assert state.password == "secret"


def test_set_access_token_is_non_persistent_compatibility_noop():
    state = make_state()

    result = state.set_access_token("access-token")

    assert result is None
    assert not hasattr(state, "access_token")
    assert not hasattr(state, "refresh_token")
