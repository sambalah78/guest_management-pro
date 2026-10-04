from pathlib import Path
import ast

STATE_PATH = Path("guest_management/state/lucky_draw_state.py")


def _state_class():
    source = STATE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "LuckyDrawState")


def _method(name: str):
    node = _state_class()
    return next(
        n for n in node.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
    )


def _method_source(name: str) -> str:
    source = STATE_PATH.read_text(encoding="utf-8")
    node = _method(name)
    return ast.get_source_segment(source, node) or ""


def test_pre_draw_display_launcher_authorizes_event_before_opening():
    fn = _method_source("open_pre_draw_display")
    assert "_authorize_lucky_draw_event" in fn
    assert "/lucky-draw/pre-draw-display?event_id=" in fn
    assert "window.open" in fn


def test_hall_screen_seeds_state_before_popup():
    source = STATE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    method = _method("open_hall_screen")

    return_nodes = [
        node
        for node in ast.walk(method)
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.List)
    ]
    assert return_nodes, "open_hall_screen must return the browser actions as a list"

    actions = return_nodes[-1].value.elts
    assert len(actions) == 2
    assert isinstance(actions[0], ast.Call)
    assert isinstance(actions[0].func, ast.Attribute)
    assert actions[0].func.attr == "broadcast_lucky_draw_state"
    assert isinstance(actions[1], ast.Name)
    assert actions[1].id == "open_script"

    fn = ast.get_source_segment(source, method) or ""
    assert "window.open" in fn
