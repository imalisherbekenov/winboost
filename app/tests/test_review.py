"""Real Dear PyGui context, no viewport and no Windows mutations."""
import dearpygui.dearpygui as dpg
import pytest

from WinBoostGUI import WinBoostApp, _build_theme


@pytest.fixture
def review_app():
    dpg.create_context()
    app = WinBoostApp()
    app._load_font()
    app._themes = _build_theme()
    with dpg.window(tag="test_window"):
        app._build_review()
    yield app
    dpg.destroy_context()


def test_irreversible_selection_requires_acknowledgment(review_app):
    app = review_app
    risky = next(a for a in app._all_actions if a["irreversible"])
    regular = next(a for a in app._all_actions if not a["irreversible"])
    app._open_review([regular, risky], "test", "home")
    assert app._selected_review_actions() == [regular]
    dpg.set_value(app._review_checks[1], True)
    app._update_review_summary()
    assert not dpg.get_item_configuration("review_apply")["enabled"]
    assert dpg.get_item_configuration("review_ack")["show"]
    dpg.set_value("review_ack", True)
    app._update_review_summary()
    assert dpg.get_item_configuration("review_apply")["enabled"]
    app._open_review([risky], "next", "home")
    assert not dpg.get_value("review_ack")
    assert not dpg.get_item_configuration("review_apply")["enabled"]


def test_busy_review_cannot_replace_running_plan(review_app):
    app = review_app
    actions = app._all_actions[:2]
    app._open_review(actions, "original", "home")
    app._busy = True
    app._open_review(app._all_actions[2:5], "replacement", "home")
    assert app._review_actions == actions
    assert app._review_label == "original"


def test_search_keeps_selection_and_empty_state_visible():
    dpg.create_context()
    try:
        app = WinBoostApp()
        app._load_font()
        app._themes = _build_theme()
        with dpg.window():
            app._build_expert()
        check, _ = app._expert_checks[0]
        dpg.set_value(check, True)
        dpg.set_value("expert_search", "xyz_no_such_action")
        app._filter_expert()
        assert dpg.get_item_configuration("expert_empty")["show"]
        assert dpg.get_value(check)
        assert "Выбрано: 1" in dpg.get_value("expert_count")
        app._clear_expert()
        assert not dpg.get_value(check)
    finally:
        dpg.destroy_context()
