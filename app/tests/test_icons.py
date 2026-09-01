import dearpygui.dearpygui as dpg
import pytest

from icons import GLYPHS, draw_glyph


def test_draw_every_glyph_without_a_window():
    dpg.create_context()
    try:
        with dpg.window(show=False):
            for name in sorted(GLYPHS):
                with dpg.drawlist(width=24, height=24) as parent:
                    draw_glyph(name, parent)
    finally:
        dpg.destroy_context()


def test_unknown_glyph_has_clear_error():
    dpg.create_context()
    try:
        with dpg.window(show=False):
            with dpg.drawlist(width=24, height=24) as parent:
                with pytest.raises(ValueError, match="Unknown glyph 'typo'"):
                    draw_glyph("typo", parent)
    finally:
        dpg.destroy_context()
