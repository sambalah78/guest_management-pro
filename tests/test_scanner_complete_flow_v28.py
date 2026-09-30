from pathlib import Path
import ast
import re

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "guest_management/state/scanner_state.py"
DASHBOARD = ROOT / "guest_management/pages/dashboard.py"
GUEST = ROOT / "guest_management/pages/scanner_guest.py"
APP = ROOT / "guest_management/guest_management.py"


def read(path):
    return path.read_text(encoding="utf-8")


def scanner_class(source):
    tree = ast.parse(source)
    return next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ScannerState"
    )


def method_node(source, name):
    cls = scanner_class(source)
    return next(
        node for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def test_start_scan_consumes_async_generator():
    fn = method_node(read(STATE), "handle_high_volume_scan")
    assert any(isinstance(node, ast.AsyncFor) for node in ast.walk(fn))
    assert not any(
        isinstance(node, ast.Await)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "attr", "") == "_process_checkin"
        for node in ast.walk(fn)
    )


def test_pin_login_redirects_to_scanner_guest():
    source = read(STATE)
    assert 'rx.redirect(f"/scanner-guest/{self.current_event_id}")' in source


def test_scanner_guest_requires_session():
    source = read(STATE)
    assert "async def scanner_guest_on_load" in source
    assert 'rx.redirect(\n                f"/scanner-login/{self.current_event_id}"' in source


def test_manual_checkin_exists():
    source = read(STATE)
    assert "async def handle_manual_checkin" in source
    assert "manual=True" in source


def test_admin_scanner_actions_exist():
    source = read(DASHBOARD)
    for marker in (
        "ScannerState.reveal_scanner_pin(",
        "ScannerState.hide_scanner_pin",
        "ScannerState.open_scanner_login",
        "ScannerState.activate_scanner(",
        "ScannerState.deactivate_scanner(",
        "ScannerState.remove_scanner(",
        "Copy Link",
        "Remove Station",
        "SCANNER PIN",
    ):
        assert marker in source


def test_scanner_guest_is_scanner_only():
    source = read(GUEST).lower()
    assert "dashboard" not in source
    assert "scanner station access token" not in source
    assert "manual check-in" in source
    assert "start scan" in source
    assert "scan next guest" in source


def test_scanner_guest_route_uses_session_loader():
    source = read(APP)
    assert (
        'route="/scanner-guest/[event_id]",\n'
        '    on_load=ScannerState.scanner_guest_on_load'
    ) in source
