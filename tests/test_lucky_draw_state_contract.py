import ast
from pathlib import Path


STATE_PATH = Path(
    "guest_management/state/lucky_draw_state.py"
)

COMPONENT_PATH = Path(
    "guest_management/components/lucky_draw_manager.py"
)

DISPLAY_PATH = Path(
    "guest_management/pages/lucky_draw_display.py"
)

PAGE_PATH = Path(
    "guest_management/pages/lucky_draw.py"
)


def get_state_symbols(path: Path):
    tree = ast.parse(
        path.read_text(encoding="utf-8")
    )

    symbols = set()

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            symbols.add(node.name)

        elif isinstance(node, ast.AnnAssign):
            if isinstance(
                node.target,
                ast.Name,
            ):
                symbols.add(node.target.id)

    return symbols


def get_state_references(path: Path):
    tree = ast.parse(
        path.read_text(encoding="utf-8")
    )

    references = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "LuckyDrawState"
            ):
                references.add(node.attr)

    return references


def test_lucky_draw_state_public_api():
    state_symbols = get_state_symbols(
        STATE_PATH
    )

    references = set()

    for path in (
        COMPONENT_PATH,
        DISPLAY_PATH,
        PAGE_PATH,
    ):
        references.update(
            get_state_references(path)
        )

    missing = sorted(
        references - state_symbols
    )

    assert not missing, (
        "LuckyDrawState API mismatch. "
        f"Missing: {missing}"
    )