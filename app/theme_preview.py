"""Static Dear PyGui previews for two WinBoost visual directions.

Run without arguments for an interactive A/home preview.  Pass an output
directory to render all four review PNGs and exit::

    python theme_preview.py .\theme_previews

This file is deliberately self-contained and does not import the production
GUI.  It only reads action metadata from ``modules.ALL_MODULES``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import dearpygui.dearpygui as dpg

from modules import ALL_MODULES


VIEWPORT_WIDTH = 1180
VIEWPORT_HEIGHT = 800

RISK_COLORS = {
    "red": (255, 149, 146, 255),
    "yellow": (255, 202, 22, 255),
    "blue": (58, 211, 137, 255),
    "green": (58, 211, 137, 255),
}
RISK_LABELS = {
    "red": "ВЫСОКИЙ РИСК",
    "yellow": "ОСТОРОЖНО",
    "blue": "БЕЗОПАСНО",
    "green": "БЕЗОПАСНО",
}

NAV_ITEMS = (
    "Главная",
    "Мастер",
    "Анализ",
    "Оптимизация",
    "Бэкапы",
    "Лог",
    "Настройки",
)


@dataclass(frozen=True)
class Direction:
    code: str
    name: str
    canvas: tuple[int, int, int, int]
    panel: tuple[int, int, int, int]
    border: tuple[int, int, int, int]
    heading: tuple[int, int, int, int]
    text: tuple[int, int, int, int]
    muted: tuple[int, int, int, int]
    accent: tuple[int, int, int, int]
    button: tuple[int, int, int, int]
    button_hover: tuple[int, int, int, int]
    radius: int
    card_radius: int
    padding: int
    gap: int
    sidebar_width: int
    child_border: int


DIRECTIONS = {
    "A": Direction(
        code="A",
        name="Сайт",
        canvas=(0, 0, 0, 255),
        panel=(0, 0, 0, 255),
        border=(41, 45, 48, 255),
        heading=(255, 255, 255, 255),
        text=(240, 240, 240, 255),
        muted=(161, 164, 165, 255),
        accent=(146, 129, 247, 255),
        button=(0, 0, 0, 0),
        button_hover=(0, 0, 0, 0),
        radius=6,
        card_radius=16,
        padding=24,
        gap=20,
        sidebar_width=242,
        child_border=1,
    ),
    "B": Direction(
        code="B",
        name="Инструмент",
        canvas=(13, 15, 18, 255),
        panel=(22, 25, 29, 255),
        border=(35, 40, 48, 255),
        heading=(230, 232, 235, 255),
        text=(230, 232, 235, 255),
        muted=(139, 146, 157, 255),
        accent=(91, 141, 239, 255),
        button=(28, 33, 41, 255),
        button_hover=(38, 44, 54, 255),
        radius=4,
        card_radius=4,
        padding=14,
        gap=10,
        sidebar_width=218,
        child_border=0,
    ),
}


def _noop(*_args: Any, **_kwargs: Any) -> None:
    """Callback supplied to module metadata factories; actions are never run."""


def _read_actions() -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for module in ALL_MODULES:
        category = module.get_category(_noop, _noop, _noop)
        for source in category["actions"]:
            action = dict(source)
            action["category"] = category["title"]
            actions.append(action)
    return actions


def _font_path(filename: str) -> Path:
    windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    path = windows_dir / "Fonts" / filename
    if not path.exists():
        raise FileNotFoundError(f"Не найден системный шрифт: {path}")
    return path


def _add_font(path: Path, size: int) -> int | str:
    # Dear PyGui 2.3 builds the complete glyph range automatically.  Segoe UI
    # and Consolas both contain Cyrillic; rendered previews verify the result.
    return dpg.add_font(str(path), size)


def _load_fonts() -> dict[str, int | str]:
    segoe = _font_path("segoeui.ttf")
    consolas = _font_path("consola.ttf")
    with dpg.font_registry():
        fonts = {
            "page": _add_font(segoe, 28),
            "section": _add_font(segoe, 19),
            "body": _add_font(segoe, 15),
            "label": _add_font(segoe, 12),
            "mono": _add_font(consolas, 12),
        }
    dpg.bind_font(fonts["body"])
    return fonts


def _theme_color(target: int, color: tuple[int, int, int, int]) -> None:
    dpg.add_theme_color(target, color)


def _build_themes(direction: Direction) -> dict[str, int | str]:
    themes: dict[str, int | str] = {}

    with dpg.theme() as shell:
        with dpg.theme_component(dpg.mvAll):
            _theme_color(dpg.mvThemeCol_WindowBg, direction.canvas)
            _theme_color(dpg.mvThemeCol_ChildBg, direction.canvas)
            _theme_color(dpg.mvThemeCol_PopupBg, direction.panel)
            _theme_color(dpg.mvThemeCol_Border, direction.border)
            _theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0))
            _theme_color(dpg.mvThemeCol_Text, direction.text)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 0, 0)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 0)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 0)
    themes["shell"] = shell

    def surface_theme(background: tuple[int, int, int, int], *, card: bool) -> int | str:
        surface_padding = (
            (20 if direction.code == "A" else 12) if card else direction.padding
        )
        surface_gap = (
            (12 if direction.code == "A" else 8) if card else direction.gap
        )
        with dpg.theme() as theme:
            with dpg.theme_component(dpg.mvAll):
                _theme_color(dpg.mvThemeCol_WindowBg, background)
                _theme_color(dpg.mvThemeCol_ChildBg, background)
                _theme_color(dpg.mvThemeCol_Border, direction.border)
                _theme_color(dpg.mvThemeCol_Text, direction.text)
                _theme_color(dpg.mvThemeCol_FrameBg, direction.canvas if direction.code == "A" else direction.button)
                _theme_color(dpg.mvThemeCol_FrameBgHovered, direction.button_hover)
                _theme_color(dpg.mvThemeCol_FrameBgActive, direction.button_hover)
                _theme_color(dpg.mvThemeCol_CheckMark, direction.accent if direction.code == "B" else direction.heading)
                _theme_color(dpg.mvThemeCol_Button, direction.button)
                _theme_color(dpg.mvThemeCol_ButtonHovered, direction.button_hover)
                _theme_color(dpg.mvThemeCol_ButtonActive, direction.button_hover)
                _theme_color(dpg.mvThemeCol_ScrollbarBg, background)
                _theme_color(dpg.mvThemeCol_ScrollbarGrab, direction.border)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, surface_padding, surface_padding)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, surface_gap, surface_gap)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, direction.padding if direction.code == "A" else 12, 8 if direction.code == "A" else 6)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, direction.radius)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, direction.card_radius)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, direction.child_border)
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, direction.card_radius if card else direction.radius)
        return theme

    themes["canvas"] = surface_theme(direction.canvas, card=False)
    themes["panel"] = surface_theme(direction.panel, card=False)
    themes["card"] = surface_theme(direction.panel, card=True)

    with dpg.theme() as row_theme:
        with dpg.theme_component(dpg.mvAll):
            _theme_color(dpg.mvThemeCol_ChildBg, direction.panel)
            _theme_color(dpg.mvThemeCol_Border, direction.border)
            _theme_color(dpg.mvThemeCol_FrameBg, direction.canvas if direction.code == "A" else direction.button)
            _theme_color(dpg.mvThemeCol_FrameBgHovered, direction.button_hover)
            _theme_color(dpg.mvThemeCol_CheckMark, direction.accent if direction.code == "B" else direction.heading)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 8, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 4, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 5)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, direction.radius)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, direction.child_border)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, direction.card_radius)
    themes["row"] = row_theme

    with dpg.theme() as ghost_button:
        with dpg.theme_component(dpg.mvButton):
            _theme_color(dpg.mvThemeCol_Text, direction.text)
            _theme_color(dpg.mvThemeCol_Button, direction.button)
            _theme_color(dpg.mvThemeCol_ButtonHovered, direction.button_hover)
            _theme_color(dpg.mvThemeCol_ButtonActive, direction.button_hover)
            _theme_color(dpg.mvThemeCol_Border, direction.border)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, direction.radius)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 14, 9 if direction.code == "A" else 7)
    themes["button"] = ghost_button

    with dpg.theme() as hover_button:
        with dpg.theme_component(dpg.mvButton):
            _theme_color(dpg.mvThemeCol_Text, direction.heading)
            _theme_color(dpg.mvThemeCol_Button, direction.button)
            _theme_color(dpg.mvThemeCol_ButtonHovered, direction.button_hover)
            _theme_color(dpg.mvThemeCol_ButtonActive, direction.button_hover)
            _theme_color(dpg.mvThemeCol_Border, direction.heading if direction.code == "A" else direction.accent)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, direction.radius)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 14, 9 if direction.code == "A" else 7)
    themes["button_hover"] = hover_button

    with dpg.theme() as active_button:
        with dpg.theme_component(dpg.mvButton):
            _theme_color(dpg.mvThemeCol_Text, direction.heading if direction.code == "A" else direction.accent)
            _theme_color(dpg.mvThemeCol_Button, direction.button)
            _theme_color(dpg.mvThemeCol_ButtonHovered, direction.button_hover)
            _theme_color(dpg.mvThemeCol_ButtonActive, direction.button_hover)
            _theme_color(dpg.mvThemeCol_Border, direction.heading if direction.code == "A" else direction.accent)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, direction.radius)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 14, 9 if direction.code == "A" else 7)
    themes["button_active"] = active_button

    with dpg.theme() as warning_card:
        with dpg.theme_component(dpg.mvAll):
            _theme_color(dpg.mvThemeCol_ChildBg, direction.panel)
            _theme_color(dpg.mvThemeCol_Border, RISK_COLORS["red"] if direction.code == "A" else direction.border)
            _theme_color(dpg.mvThemeCol_FrameBg, direction.canvas if direction.code == "A" else direction.button)
            _theme_color(dpg.mvThemeCol_CheckMark, direction.accent if direction.code == "B" else direction.heading)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, direction.card_radius)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 8, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 4, 4)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 5)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, direction.radius)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
    themes["warning"] = warning_card
    return themes


def _text(
    value: str,
    fonts: dict[str, int | str],
    font: str = "body",
    color: tuple[int, int, int, int] | None = None,
    *,
    wrap: int = 0,
    parent: int | str = 0,
) -> int | str:
    item = dpg.add_text(value, color=color, wrap=wrap, parent=parent)
    dpg.bind_item_font(item, fonts[font])
    return item


def _button(
    label: str,
    direction: Direction,
    themes: dict[str, int | str],
    buttons: list[int | str],
    *,
    width: int = 0,
    height: int = 0,
    active: bool = False,
) -> int | str:
    item = dpg.add_button(label=label, width=width, height=height)
    dpg.bind_item_theme(item, themes["button_active"] if active else themes["button"])
    if direction.code == "A" and not active:
        buttons.append(item)
    return item


def _bind_surface(item: int | str, themes: dict[str, int | str], surface: str) -> None:
    dpg.bind_item_theme(item, themes[surface])


def _sidebar(
    direction: Direction,
    fonts: dict[str, int | str],
    themes: dict[str, int | str],
    buttons: list[int | str],
    active_nav: str,
) -> None:
    eyebrow_color = direction.accent
    _text("WINBOOST / PREVIEW", fonts, "mono", eyebrow_color)
    _text("Системный помощник", fonts, "section", direction.heading)
    _text(
        f"Направление {direction.code} · {direction.name}",
        fonts,
        "label",
        direction.muted,
    )
    dpg.add_spacer(height=6 if direction.code == "B" else 10)
    for item in NAV_ITEMS:
        nav = _button(
            item,
            direction,
            themes,
            buttons,
            width=-1,
            height=38 if direction.code == "B" else 46,
            active=item == active_nav,
        )
        dpg.bind_item_font(nav, fonts["body"])
    if direction.code == "B":
        dpg.add_spacer(height=8)
        _text("СОСТОЯНИЕ", fonts, "mono", direction.muted)
        _text("[ OK ]  система готова", fonts, "mono", RISK_COLORS["blue"])
        _text("Версия макета 0.1", fonts, "label", direction.muted)


def _status_panel(
    direction: Direction,
    fonts: dict[str, int | str],
    themes: dict[str, int | str],
) -> None:
    height = 64 if direction.code == "A" else 48
    with dpg.child_window(height=height, border=True, no_scrollbar=True) as status:
        _bind_surface(status, themes, "card")
        with dpg.group(horizontal=True):
            _text("[ ADMIN ]", fonts, "mono", RISK_COLORS["blue"])
            _text("Права администратора получены", fonts, "body", direction.text)
            _text("Все функции доступны", fonts, "label", direction.muted)


HOME_CARDS = (
    ("01", "Мастер", "Пошаговая настройка под ваши задачи"),
    ("02", "Анализ", "Проверка системы без внесения изменений"),
    ("03", "Быстрая оптимизация", "Безопасный набор рекомендуемых действий"),
    ("04", "Бэкапы", "Точки восстановления и сохранённые состояния"),
)


def _home_card(
    card: tuple[str, str, str],
    direction: Direction,
    fonts: dict[str, int | str],
    themes: dict[str, int | str],
    buttons: list[int | str],
    *,
    width: int,
    height: int,
) -> None:
    number, title, description = card
    with dpg.child_window(width=width, height=height, border=True, no_scrollbar=True) as panel:
        _bind_surface(panel, themes, "card")
        _text(number, fonts, "mono", direction.accent)
        _text(title, fonts, "section", direction.heading, wrap=max(150, width - direction.padding * 2))
        _text(description, fonts, "body", direction.muted, wrap=max(150, width - direction.padding * 2))
        action = _button(
            "Открыть" if direction.code == "A" else "Запустить",
            direction,
            themes,
            buttons,
            width=-1,
            height=38 if direction.code == "A" else 34,
        )
        dpg.bind_item_font(action, fonts["body"])


def _home(
    direction: Direction,
    fonts: dict[str, int | str],
    themes: dict[str, int | str],
    buttons: list[int | str],
) -> None:
    _text("ГЛАВНАЯ / ОБЗОР", fonts, "mono", direction.accent)
    _text("Добро пожаловать в WinBoost", fonts, "page", direction.heading)
    _text(
        "Выберите сценарий — сначала покажем изменения, затем запросим подтверждение.",
        fonts,
        "body",
        direction.muted,
        wrap=760,
    )
    _status_panel(direction, fonts, themes)
    _text("Быстрые действия", fonts, "section", direction.heading)

    if direction.code == "A":
        for row in (HOME_CARDS[:2], HOME_CARDS[2:]):
            with dpg.group(horizontal=True):
                for card in row:
                    _home_card(
                        card,
                        direction,
                        fonts,
                        themes,
                        buttons,
                        width=425,
                        height=190,
                    )
    else:
        with dpg.group(horizontal=True):
            for card in HOME_CARDS:
                _home_card(
                    card,
                    direction,
                    fonts,
                    themes,
                    buttons,
                    width=218,
                    height=206,
                )
        _text("ПОСЛЕДНЕЕ СОБЫТИЕ", fonts, "mono", direction.muted)
        _text(
            "[12:48:07]  Анализ завершён · найдено 6 рекомендаций",
            fonts,
            "mono",
            direction.accent,
        )


def _action_row(
    action: dict[str, Any],
    direction: Direction,
    fonts: dict[str, int | str],
    themes: dict[str, int | str],
    *,
    warning: bool = False,
) -> None:
    height = 54 if direction.code == "A" else 46
    row_theme = themes["warning" if warning else "row"]
    with dpg.child_window(
        height=height,
        border=True,
        no_scrollbar=True,
        always_use_window_padding=True,
    ) as row_panel:
        _bind_surface(row_panel, themes, "warning" if warning else "row")
        with dpg.table(
            header_row=False,
            borders_innerV=False,
            borders_outerV=False,
            borders_innerH=False,
            borders_outerH=False,
            policy=dpg.mvTable_SizingStretchProp,
        ):
            dpg.add_table_column(width_fixed=True, init_width_or_weight=30)
            dpg.add_table_column(width_stretch=True, init_width_or_weight=1.0)
            dpg.add_table_column(width_fixed=True, init_width_or_weight=150 if direction.code == "A" else 138)
            with dpg.table_row():
                dpg.add_checkbox(default_value=True)
                with dpg.group():
                    _text(str(action["name"]), fonts, "body", direction.text)
                risk = str(action.get("risk", "blue"))
                _text(
                    RISK_LABELS.get(risk, "БЕЗОПАСНО"),
                    fonts,
                    "mono",
                    RISK_COLORS.get(risk, RISK_COLORS["blue"]),
                )


def _review(
    direction: Direction,
    fonts: dict[str, int | str],
    themes: dict[str, int | str],
    buttons: list[int | str],
    all_actions: list[dict[str, Any]],
) -> None:
    limit = 5 if direction.code == "A" else 6
    selected = all_actions[:limit]
    reversible = [action for action in selected if not action.get("irreversible")]
    irreversible = [action for action in selected if action.get("irreversible")]

    _text("МАСТЕР / ШАГ 3 ИЗ 3", fonts, "mono", direction.accent)
    _text("Проверка перед применением", fonts, "page", direction.heading)
    _text(
        "Проверьте выбранные действия. Список можно изменить перед запуском.",
        fonts,
        "body",
        direction.muted,
        wrap=760,
    )
    for action in reversible:
        _action_row(action, direction, fonts, themes)

    _text("Необратимые действия", fonts, "section", RISK_COLORS["red"])
    _text(
        "После применения вернуть эти изменения автоматически не получится.",
        fonts,
        "label",
        direction.muted,
    )
    for action in irreversible:
        _action_row(action, direction, fonts, themes, warning=True)

    summary_height = 48 if direction.code == "A" else 42
    with dpg.child_window(height=summary_height, border=True, no_scrollbar=True) as summary:
        _bind_surface(summary, themes, "card")
        with dpg.group(horizontal=True):
            _text("БЭКАП", fonts, "mono", direction.accent)
            _text("Точка восстановления будет создана до применения", fonts, "body", direction.text)
            _text(f"{len(selected)} действий", fonts, "mono", direction.muted)

    with dpg.group(horizontal=True):
        cancel = _button(
            "Отмена",
            direction,
            themes,
            buttons,
            width=150,
            height=42 if direction.code == "A" else 36,
        )
        apply_button = _button(
            f"Применить · {len(selected)}",
            direction,
            themes,
            buttons,
            width=190,
            height=42 if direction.code == "A" else 36,
            active=True,
        )
        dpg.bind_item_font(cancel, fonts["body"])
        dpg.bind_item_font(apply_button, fonts["body"])


def _build_scene(
    direction_code: str,
    screen: str,
    fonts: dict[str, int | str],
    all_actions: list[dict[str, Any]],
) -> tuple[list[int | str], dict[str, int | str]]:
    direction = DIRECTIONS[direction_code]
    themes = _build_themes(direction)
    buttons: list[int | str] = []

    with dpg.window(
        tag="preview_root",
        no_title_bar=True,
        no_move=True,
        no_resize=True,
        no_collapse=True,
        no_scrollbar=True,
        no_scroll_with_mouse=True,
    ) as root:
        _bind_surface(root, themes, "shell")
        with dpg.group(horizontal=True):
            with dpg.child_window(
                width=direction.sidebar_width,
                height=-1,
                border=direction.code == "A",
                no_scrollbar=True,
            ) as sidebar:
                _bind_surface(sidebar, themes, "panel")
                _sidebar(
                    direction,
                    fonts,
                    themes,
                    buttons,
                    "Главная" if screen == "home" else "Оптимизация",
                )
            with dpg.child_window(width=-1, height=-1, border=False, no_scrollbar=True) as content:
                _bind_surface(content, themes, "canvas")
                # A nested surface applies the direction's content padding before
                # any scene item is laid out (item themes bind after Begin()).
                with dpg.child_window(
                    width=-1,
                    height=-1,
                    border=False,
                    no_scrollbar=True,
                    always_use_window_padding=True,
                ) as padded_content:
                    _bind_surface(padded_content, themes, "canvas")
                    if screen == "home":
                        _home(direction, fonts, themes, buttons)
                    else:
                        _review(direction, fonts, themes, buttons, all_actions)
    dpg.set_primary_window(root, True)
    return buttons, themes


def _refresh_hover_themes(
    buttons: Iterable[int | str], themes: dict[str, int | str]
) -> None:
    for button in buttons:
        target = themes["button_hover"] if dpg.is_item_hovered(button) else themes["button"]
        dpg.bind_item_theme(button, target)


def _run_scene(
    direction_code: str,
    screen: str,
    output_file: Path | None = None,
) -> None:
    # Important: no Dear PyGui function is called before this line.
    dpg.create_context()
    try:
        all_actions = _read_actions()
        fonts = _load_fonts()
        buttons, themes = _build_scene(direction_code, screen, fonts, all_actions)
        dpg.create_viewport(
            title=f"WinBoost — направление {direction_code}",
            width=VIEWPORT_WIDTH,
            height=VIEWPORT_HEIGHT,
            resizable=False,
        )
        dpg.setup_dearpygui()
        dpg.show_viewport()

        if output_file is None:
            while dpg.is_dearpygui_running():
                if direction_code == "A":
                    _refresh_hover_themes(buttons, themes)
                dpg.render_dearpygui_frame()
        else:
            # The framebuffer is empty until the renderer has completed a few frames.
            # Allow the native Windows viewport animation and font atlas upload
            # to settle; early framebuffers can otherwise miss the top-left UI.
            for _ in range(24):
                dpg.render_dearpygui_frame()
            dpg.output_frame_buffer(str(output_file))
            # Framebuffer output is queued by the native renderer.  Keep the
            # context alive long enough for the PNG write to finish before the
            # next capture creates a fresh DPG context.
            for _ in range(10):
                dpg.render_dearpygui_frame()
    finally:
        dpg.destroy_context()


def _capture_all(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve()
    child_environment = os.environ.copy()
    child_environment["PYTHONUTF8"] = "1"
    for direction_code in ("A", "B"):
        for screen in ("home", "review"):
            output_file = output_dir / f"{direction_code}_{screen}.png"
            if output_file.exists():
                output_file.unlink()
            # DPG 2.3 can invalidate an earlier font atlas when several native
            # contexts are created sequentially in one process.  A fresh child
            # process per framebuffer keeps all four captures deterministic.
            subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--capture-one",
                    direction_code,
                    screen,
                    str(output_file),
                ],
                check=True,
                env=child_environment,
            )
            if not output_file.exists() or output_file.stat().st_size == 0:
                raise RuntimeError(f"Не удалось сохранить скриншот: {output_file}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 4 and args[0] == "--capture-one":
        direction_code, screen, output = args[1:]
        if direction_code not in DIRECTIONS or screen not in {"home", "review"}:
            return 2
        _run_scene(direction_code, screen, Path(output).resolve())
        return 0
    if len(args) > 1:
        print("Использование: python theme_preview.py [папка_для_скриншотов]", file=sys.stderr)
        return 2
    if args:
        output_dir = Path(args[0]).expanduser().resolve()
        _capture_all(output_dir)
        print(f"Скриншоты сохранены: {output_dir}")
    else:
        _run_scene("A", "home")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
