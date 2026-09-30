from pathlib import Path
import ast
import re


ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "guest_management" / "state" / "lucky_draw_state.py"
HALL_PATH = ROOT / "guest_management" / "pages" / "lucky_draw_hall.py"
ROUTES_PATH = ROOT / "guest_management" / "guest_management.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _lucky_draw_state_class():
    tree = ast.parse(_source(STATE_PATH))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "LuckyDrawState"
    )


def _method_node(name: str):
    cls = _lucky_draw_state_class()
    return next(
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


def test_display_methods_are_class_methods():
    tree = ast.parse(_source(STATE_PATH))
    cls = _lucky_draw_state_class()

    required = {
        "_lucky_draw_browser_state",
        "broadcast_lucky_draw_state",
        "open_hall_screen",
        "refresh_display_data",
        "_fetch_display_data_from_api",
        "load_lucky_draw_display_data",
        "clear_pre_draw_winners",
        "start_new_draw",
    }
    class_methods = {
        node.name
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert required <= class_methods

    module_level = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert not (required & module_level)


def test_hall_storage_contract_matches_operator_broadcast():
    state = _source(STATE_PATH)
    hall = _source(HALL_PATH)

    assert "eventlah-lucky-draw-state:' + String(state.event_id || '')" in state
    assert "eventlah-lucky-draw-state:' + eventId" in hall
    assert "new BroadcastChannel('eventlah-lucky-draw')" in state
    assert "new BroadcastChannel(channelName)" in hall


def test_open_hall_screen_seeds_state_and_opens_existing_route():
    source = ast.get_source_segment(
        _source(STATE_PATH),
        _method_node("open_hall_screen"),
    )
    assert source is not None
    assert "localStorage.setItem" in source
    assert "BroadcastChannel" in source
    assert "window.open" in source
    assert "/lucky-draw/external-display/{event_id}" in source


def test_hall_dom_contract_exists():
    hall = _source(HALL_PATH)
    assert 'id="eventlah-hall-root"' in hall
    assert 'id="eventlah-hall-event-name"' in hall
    assert 'id="eventlah-hall-wheel"' in hall
    assert 'id="eventlah-hall-winner"' in hall
    assert 'id="eventlah-hall-history"' in hall
    assert "eventlah-lucky-draw-state:" in hall


def test_predraw_initialization_loads_persisted_winners():
    cls = _lucky_draw_state_class()
    method = next(
        node
        for node in cls.body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "initialize_lucky_draw_event"
    )
    source = ast.get_source_segment(_source(STATE_PATH), method)
    assert source is not None
    assert re.search(
        r"load_pre_draw_prizes\(\)\s*\n\s*await self\.load_pre_draw_winners\(\)",
        source,
    )


def test_predraw_clear_uses_current_service_api():
    source = ast.get_source_segment(
        _source(STATE_PATH),
        _method_node("clear_pre_draw_winners"),
    )
    assert source is not None
    assert "delete_for_event(event_id)" in source
    assert "delete_by_event(event_id)" not in source


def test_external_display_route_uses_hall_page():
    routes = _source(ROUTES_PATH)
    assert "lucky_draw_hall.lucky_draw_hall_page" in routes
    assert 'route="/lucky-draw/external-display/[event_id]"' in routes
