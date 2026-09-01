"""WinBoost desktop interface built with Dear PyGui 2.3."""

from __future__ import annotations

import ctypes
import datetime as dt
import logging
import os
import queue
import subprocess
import sys
import threading
import time
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import dearpygui.dearpygui as dpg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import ALL_MODULES
from icons import draw_glyph
from modules.analyzer import analyze_system, format_analysis
from modules.backup import capture, ensure_baseline, list_backups, merge_effects
from modules.backup import restore as restore_backup
from modules.logsetup import setup_logging
from modules.startup import (
    disable_startup_item,
    restore_startup_item,
    scan_startup_items,
)


APP_TITLE = "WinBoost 3.0"
WINDOW_WIDTH = 1180
WINDOW_HEIGHT = 800

VOID = (0, 0, 0, 255)
TRANSPARENT = (0, 0, 0, 0)
HAIRLINE = (41, 45, 48, 255)
WHITE = (255, 255, 255, 255)
BONE = (240, 240, 240, 255)
MUTED = (161, 164, 165, 255)
IRON = (110, 114, 122, 255)

# Semantic color is reserved for risk and status data. Violet belongs only to
# technical/log text; it is deliberately not a general UI accent.
LOG_TECHNICAL = (146, 129, 247, 255)
GREEN = (58, 211, 137, 255)
YELLOW = (255, 202, 22, 255)
RED = (255, 149, 146, 255)
BLUE = GREEN
ACCENT = WHITE
ACCENT2 = MUTED

RISK_COLORS = {"red": RED, "yellow": YELLOW, "blue": GREEN, "green": GREEN}
RISK_LABELS = {
    "red": "ВЫСОКИЙ РИСК",
    "yellow": "ОСТОРОЖНО",
    "blue": "БЕЗОПАСНО",
    "green": "БЕЗОПАСНО",
}

PALETTE = {
    "dark": {
        "bg": VOID,
        "card": VOID,
        "card2": TRANSPARENT,
        "text": BONE,
        "dim": MUTED,
        "border": HAIRLINE,
    }
}

PAGE_NAMES = ("home", "wizard", "analysis", "expert", "startup", "backups", "log")


def _resource_path(*parts: str) -> Path:
    """Return an asset path for source runs and PyInstaller onefile builds."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root.joinpath(*parts)


def _display_text(value: Any) -> str:
    """Remove emoji glyphs unavailable in Dear PyGui's single-font atlas."""
    return "".join(
        char
        for char in str(value)
        if not (
            0x2600 <= ord(char) <= 0x27BF
            or 0x1F000 <= ord(char) <= 0x1FAFF
            or ord(char) in (0x200D, 0xFE0F)
        )
    ).strip()


def plural(n: int, one: str, few: str, many: str) -> str:
    """Return the Russian noun form matching *n*."""
    remainder_100 = abs(n) % 100
    if 11 <= remainder_100 <= 14:
        return many
    remainder_10 = abs(n) % 10
    if remainder_10 == 1:
        return one
    if 2 <= remainder_10 <= 4:
        return few
    return many


def is_admin() -> bool:
    """Return whether the process has an elevated Windows token."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def elevate() -> None:
    """Restart the script through UAC when administrator rights are missing."""
    if is_admin():
        return
    args = sys.argv[1:] if getattr(sys, "frozen", False) else sys.argv
    params = subprocess.list2cmdline(args)
    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, os.getcwd(), 1
    )
    if result <= 32:
        raise OSError(f"Не удалось запросить права администратора (код {result})")
    raise SystemExit(0)


def _build_theme() -> dict[str, int | str]:
    themes: dict[str, int | str] = {}
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_Button, TRANSPARENT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, TRANSPARENT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, TRANSPARENT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, WHITE)
            dpg.add_theme_color(dpg.mvThemeCol_Text, BONE)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, IRON)
            dpg.add_theme_color(dpg.mvThemeCol_Border, HAIRLINE)
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, TRANSPARENT)
            dpg.add_theme_color(dpg.mvThemeCol_Header, TRANSPARENT)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, TRANSPARENT)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, TRANSPARENT)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBg, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_TableRowBgAlt, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_TableBorderStrong, HAIRLINE)
            dpg.add_theme_color(dpg.mvThemeCol_TableBorderLight, HAIRLINE)
            dpg.add_theme_color(dpg.mvThemeCol_Separator, HAIRLINE)
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram, HAIRLINE)
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogramHovered, MUTED)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, VOID)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, HAIRLINE)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 0)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 16)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 12)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 7)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 10)
    themes["global"] = theme

    def surface(padding: int, spacing: int, rounding: int = 16) -> int | str:
        with dpg.theme() as surface_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, VOID)
                dpg.add_theme_color(dpg.mvThemeCol_Border, HAIRLINE)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, padding, padding)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, spacing, spacing)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, rounding)
        return surface_theme

    themes["sidebar"] = surface(18, 10, 0)
    themes["page"] = surface(16, 10, 0)
    themes["card"] = surface(12, 8, 16)
    themes["row"] = surface(10, 4, 16)
    themes["list"] = surface(0, 4, 0)

    def button(border: tuple[int, int, int, int], text: tuple[int, int, int, int]) -> int | str:
        with dpg.theme() as button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Text, text)
                dpg.add_theme_color(dpg.mvThemeCol_Button, TRANSPARENT)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, TRANSPARENT)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, TRANSPARENT)
                dpg.add_theme_color(dpg.mvThemeCol_Border, border)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 7)
        return button_theme

    themes["button"] = button(HAIRLINE, BONE)
    themes["button_hover"] = button(WHITE, WHITE)
    themes["button_active"] = button(WHITE, WHITE)
    return themes


class WinBoostApp:
    """Dear PyGui application with queue-only communication from workers."""

    def __init__(self) -> None:
        self._events: queue.Queue[tuple[Any, ...]] = queue.Queue()
        try:
            self._logger = setup_logging()
        except OSError:
            # A locked or policy-protected AppData log must not prevent the UI
            # from starting. The normal elevated path still uses setup_logging.
            self._logger = logging.getLogger("winboost")
            self._logger.addHandler(logging.NullHandler())
        self._log_lines: list[tuple[str, str]] = []
        self._log_items: list[int | str] = []
        self._scroll_log_pending = False
        self._themes: dict[str, int | str] = {}
        self._font_path = ""
        self._title_font: int | str = 0
        self._section_font: int | str = 0
        self._body_font: int | str = 0
        self._label_font: int | str = 0
        self._mono_font: int | str = 0
        self._buttons: list[int | str] = []
        self._active_buttons: set[int | str] = set()
        self._nav_indicators: dict[str, int | str] = {}
        self._busy = False
        self._busy_name = ""
        self._active_page = "home"
        self._startup_items: list[dict[str, Any]] = []
        self._disabled_startup_items: dict[str, dict[str, Any]] = {}
        self._backups: list[dict[str, Any]] = []
        self._expert_checks: list[tuple[int | str, dict[str, Any]]] = []
        self._review_actions: list[dict[str, Any]] = []
        self._review_checks: list[int | str] = []
        self._review_source = "home"
        self._review_label = "change"
        self._categories = self._load_categories()
        self._all_actions = [
            action
            for category in self._categories
            for action in category["actions"]
        ]

    # Module callbacks are queue-only because modules invoke them from workers.
    def log_success(self, message: str) -> None:
        self._events.put(("log", "success", str(message)))

    def log_error(self, message: str) -> None:
        self._events.put(("log", "error", str(message)))

    def log_info(self, message: str) -> None:
        self._events.put(("log", "info", str(message)))

    def _load_categories(self) -> list[dict[str, Any]]:
        categories: list[dict[str, Any]] = []
        for module in ALL_MODULES:
            category = module.get_category(
                self.log_success, self.log_error, self.log_info
            )
            actions = []
            for source_action in category["actions"]:
                action = dict(source_action)
                action["name"] = _display_text(source_action["name"])
                action["desc"] = _display_text(source_action["desc"])
                action["effects"] = dict(source_action.get("effects") or {})
                action["category"] = _display_text(category["title"])
                action["module"] = module.__name__.rsplit(".", 1)[-1]
                actions.append(action)
            categories.append(
                {
                    "title": _display_text(category["title"]),
                    "desc": _display_text(category["desc"]),
                    "module": module.__name__.rsplit(".", 1)[-1],
                    "actions": actions,
                }
            )
        return categories

    def _font_candidate(self, bundled_name: str, *fallback_names: str) -> Path:
        bundled = _resource_path("assets", "fonts", bundled_name)
        if bundled.exists():
            return bundled
        windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        candidates = [windows_dir / "Fonts" / name for name in fallback_names]
        fallback = next((path for path in candidates if path.exists()), None)
        if fallback is None:
            raise FileNotFoundError("Не найден системный шрифт с поддержкой кириллицы")
        return fallback

    @staticmethod
    def _add_font(path: Path, size: int) -> int | str:
        # DPG 2.3 builds the complete cmap automatically.
        return dpg.add_font(str(path), size)

    def _load_font(self) -> None:
        regular = self._font_candidate("Inter-Regular.ttf", "segoeui.ttf", "arial.ttf")
        medium = self._font_candidate("Inter-Medium.ttf", "segoeui.ttf", "arial.ttf")
        title = self._font_candidate(
            "Inter-SemiBold.ttf", "seguisb.ttf", "segoeui.ttf", "arial.ttf"
        )
        mono = self._font_candidate(
            "JetBrainsMono-Regular.ttf", "consola.ttf", "segoeui.ttf"
        )
        self._font_path = str(regular)
        with dpg.font_registry():
            # Instrument Serif is bundled for Latin display text but its cmap
            # has no Cyrillic. Russian titles therefore use Inter SemiBold.
            self._title_font = self._add_font(title, 28)
            self._section_font = self._add_font(medium, 19)
            self._body_font = self._add_font(regular, 15)
            self._label_font = self._add_font(regular, 12)
            self._mono_font = self._add_font(mono, 12)
        dpg.bind_font(self._body_font)

    def _bind_font(self, item: int | str, role: str) -> int | str:
        fonts = {
            "title": self._title_font,
            "section": self._section_font,
            "body": self._body_font,
            "label": self._label_font,
            "mono": self._mono_font,
        }
        dpg.bind_item_font(item, fonts[role])
        return item

    def _text(
        self,
        value: str,
        *,
        role: str = "body",
        color: tuple[int, ...] = BONE,
        parent: int | str = 0,
        wrap: int = 0,
        tag: int | str = 0,
    ) -> int | str:
        kwargs: dict[str, Any] = {"color": color, "parent": parent, "wrap": wrap}
        if tag:
            kwargs["tag"] = tag
        return self._bind_font(dpg.add_text(value, **kwargs), role)

    def _button(self, *, active: bool = False, **kwargs: Any) -> int | str:
        item = dpg.add_button(**kwargs)
        self._buttons.append(item)
        if active:
            self._active_buttons.add(item)
        dpg.bind_item_theme(item, self._themes["button_active" if active else "button"])
        self._bind_font(item, "body")
        return item

    def _refresh_button_hover_themes(self) -> None:
        for candidate in dpg.get_all_items():
            if (
                candidate not in self._buttons
                and dpg.get_item_type(candidate).endswith("::mvButton")
            ):
                self._buttons.append(candidate)
                dpg.bind_item_theme(candidate, self._themes["button"])
                self._bind_font(candidate, "body")
        for item in tuple(self._buttons):
            if not dpg.does_item_exist(item):
                self._buttons.remove(item)
                self._active_buttons.discard(item)
                continue
            theme = "button_active" if item in self._active_buttons else (
                "button_hover" if dpg.is_item_hovered(item) else "button"
            )
            dpg.bind_item_theme(item, self._themes[theme])

    def _build(
        self,
        *,
        capture_page: str | None = None,
        capture_path: Path | None = None,
    ) -> None:
        dpg.create_context()
        try:
            self._load_font()
            self._themes = _build_theme()
            dpg.bind_theme(self._themes["global"])
            with dpg.window(
                tag="main_win",
                label=APP_TITLE,
                no_close=True,
                no_title_bar=True,
                no_scrollbar=True,
            ):
                with dpg.group(horizontal=True):
                    self._build_sidebar()
                    with dpg.child_window(
                        tag="content", width=-1, height=-1, border=False,
                        no_scrollbar=True,
                    ) as content:
                        dpg.bind_item_theme(content, self._themes["page"])
                        self._build_home()
                        self._build_wizard()
                        self._build_analysis()
                        self._build_expert()
                        self._build_startup()
                        self._build_backups()
                        self._build_log()
                        self._build_review()

            dpg.create_viewport(
                title=APP_TITLE,
                width=WINDOW_WIDTH,
                height=WINDOW_HEIGHT,
                min_width=980,
                min_height=680,
                resizable=capture_path is None,
            )
            dpg.setup_dearpygui()
            dpg.set_primary_window("main_win", True)
            dpg.show_viewport()
            if capture_page == "review":
                self._open_review(self._all_actions[:6], "capture", "home")
            elif capture_page == "analysis":
                self._show("analysis")
                info = analyze_system()
                self._render_analysis(info, format_analysis(info))
            else:
                self._show(capture_page or "home")
            self._append_log("info", "Интерфейс запущен")
            self._logger.info("Интерфейс запущен. Шрифт: %s", self._font_path)
            if capture_path is None:
                self._begin_worker("Создание первичного снимка", self._worker_baseline)
                while dpg.is_dearpygui_running():
                    self._drain_events()
                    self._refresh_button_hover_themes()
                    dpg.render_dearpygui_frame()
            else:
                for _ in range(60):
                    self._refresh_button_hover_themes()
                    dpg.render_dearpygui_frame()
                    # Pump real-time native frames; an immediate tight loop can
                    # finish before the Windows viewport animation has settled.
                    time.sleep(0.02)
                target_page = capture_page or "home"
                self._show("wizard" if target_page != "wizard" else "home")
                for _ in range(3):
                    dpg.render_dearpygui_frame()
                self._show(target_page)
                for _ in range(12):
                    self._refresh_button_hover_themes()
                    dpg.render_dearpygui_frame()
                    time.sleep(0.02)
                dpg.output_frame_buffer(str(capture_path))
                for _ in range(60):
                    dpg.render_dearpygui_frame()
                time.sleep(0.25)
        finally:
            dpg.destroy_context()

    def _build_sidebar(self) -> None:
        with dpg.child_window(tag="sidebar", width=238, height=-1, border=True) as sidebar:
            dpg.bind_item_theme(sidebar, self._themes["sidebar"])
            with dpg.group(horizontal=True):
                with dpg.drawlist(width=26, height=26):
                    dpg.draw_polyline(
                        ((4, 7), (8.5, 19), (12, 4), (15.5, 19), (20, 7)),
                        color=WHITE,
                        thickness=2,
                    )
                self._text("WinBoost", role="section", color=WHITE)
            self._text("СИСТЕМНЫЙ ПОМОЩНИК", role="mono", color=MUTED)
            dpg.add_spacer(height=6)
            for label, page in (
                ("Главная", "home"),
                ("Мастер", "wizard"),
                ("Анализ", "analysis"),
                ("Эксперт", "expert"),
                ("Автозагрузка", "startup"),
                ("Бэкапы", "backups"),
                ("Лог", "log"),
            ):
                self._nav_btn(label, page)
            dpg.add_spacer(height=12)
            dpg.add_separator()
            self._text("СОСТОЯНИЕ", role="mono", color=MUTED)
            self._text("[ OK ]  СИСТЕМА ГОТОВА", role="mono", color=GREEN)
            self._text(
                "Операций пока нет",
                role="label",
                color=MUTED,
                tag="status_text",
                wrap=190,
            )

    def _nav_btn(self, label: str, page: str) -> None:
        with dpg.group(horizontal=True):
            with dpg.drawlist(width=5, height=38):
                indicator = dpg.draw_line(
                    (2, 4),
                    (2, 34),
                    color=HAIRLINE,
                    thickness=2,
                )
            self._nav_indicators[page] = indicator
            self._button(
                label=label,
                callback=self._navigate,
                user_data=page,
                width=174,
                height=38,
                tag=f"nav_{page}",
            )

    def _navigate(self, sender: Any, app_data: Any, user_data: str) -> None:
        self._show(user_data)
        if user_data == "startup" and not self._startup_items:
            self._refresh_startup()
        elif user_data == "backups":
            self._refresh_backups()

    def _show(self, page: str) -> None:
        self._active_page = page
        for name in (*PAGE_NAMES, "review"):
            tag = f"page_{name}"
            if dpg.does_item_exist(tag):
                dpg.configure_item(tag, show=name == page)
        active_nav = page if page in PAGE_NAMES else self._review_source
        for name, indicator in self._nav_indicators.items():
            dpg.configure_item(indicator, color=WHITE if name == active_nav else HAIRLINE)
            button = f"nav_{name}"
            if dpg.does_item_exist(button):
                if name == active_nav:
                    self._active_buttons.add(button)
                else:
                    self._active_buttons.discard(button)

    def _page(self, tag: str) -> None:
        page = dpg.add_child_window(
            tag=tag,
            width=-1,
            height=-1,
            border=False,
            show=False,
        )
        dpg.bind_item_theme(page, self._themes["page"])

    def _heading(self, title: str, subtitle: str, color: tuple[int, ...] = WHITE) -> None:
        self._text(title, role="title", color=color)
        self._text(subtitle, role="body", color=MUTED, wrap=850)
        dpg.add_spacer(height=2)

    def _build_home(self) -> None:
        self._page("page_home")
        with dpg.group(parent="page_home"):
            self._heading(
                "Настройте Windows под себя",
                "Пошаговая оптимизация с обязательной проверкой каждого изменения.",
            )
            admin_text = (
                "Права администратора: получены"
                if is_admin()
                else "Права администратора: не получены"
            )
            with dpg.child_window(height=54, border=True, no_scrollbar=True) as status_card:
                dpg.bind_item_theme(status_card, self._themes["card"])
                with dpg.group(horizontal=True):
                    self._text("[ ADMIN ]", role="mono", color=GREEN if is_admin() else RED)
                    self._text(admin_text, color=BONE)
            self._text("БЫСТРЫЕ ДЕЙСТВИЯ", role="mono", color=MUTED)
            with dpg.group(horizontal=True):
                self._home_card(
                    "01",
                    "Мастер",
                    "Ответьте на два вопроса — мы соберём подходящий набор.",
                    "Открыть",
                    self._open_page_callback,
                    "wizard",
                )
                self._home_card(
                    "02",
                    "Анализ",
                    "Проверьте систему и получите подробный цветной отчёт.",
                    "Запустить",
                    self._open_page_callback,
                    "analysis",
                )
                self._home_card(
                    "03",
                    "Быстрая оптимизация",
                    "Только безопасные действия — сначала проверка.",
                    "Проверить",
                    self._quick_optimize,
                    None,
                )
                self._home_card(
                    "04",
                    "Бэкапы",
                    "Просмотрите снимки и восстановите выбранное состояние.",
                    "Открыть",
                    self._open_page_callback,
                    "backups",
                )
            self._text("ПОСЛЕДНЕЕ СОБЫТИЕ", role="mono", color=MUTED)
            self._text(
                "Событий пока нет",
                role="mono",
                color=MUTED,
                tag="home_last_event",
                wrap=850,
            )

    def _home_card(
        self,
        number: str,
        title: str,
        desc: str,
        button: str,
        callback: Callable[..., None],
        user_data: Any,
    ) -> None:
        with dpg.child_window(width=211, height=180, border=True, no_scrollbar=True) as card:
            dpg.bind_item_theme(card, self._themes["card"])
            self._text(number, role="mono", color=MUTED)
            self._text(title, role="section", color=WHITE, wrap=184)
            self._text(desc, role="label", color=MUTED, wrap=184)
            self._button(
                label=button,
                width=-1,
                height=34,
                callback=callback,
                user_data=user_data,
            )

    def _open_page_callback(self, sender: Any, app_data: Any, user_data: str) -> None:
        self._show(user_data)
        if user_data == "backups":
            self._refresh_backups()

    def _build_wizard(self) -> None:
        self._page("page_wizard")
        with dpg.group(parent="page_wizard"):
            self._heading(
                "Мастер оптимизации",
                "Ответьте на вопросы. Перед запуском вы сможете исключить любое действие.",
            )
            with dpg.child_window(height=120, border=True, no_scrollbar=True) as usage_card:
                dpg.bind_item_theme(usage_card, self._themes["card"])
                self._text("Для чего вы чаще всего используете ПК?", role="section", color=WHITE)
                dpg.add_combo(
                    ("Игры", "Работа", "Сёрфинг", "Создание контента"),
                    default_value="Игры",
                    tag="wizard_usage",
                    width=420,
                )
            with dpg.child_window(height=150, border=True, no_scrollbar=True) as risk_card:
                dpg.bind_item_theme(risk_card, self._themes["card"])
                self._text("Готовы к агрессивным настройкам?", role="section", color=WHITE)
                dpg.add_radio_button(
                    ("Нет, только безопасный режим", "Да, максимум производительности"),
                    default_value="Нет, только безопасный режим",
                    tag="wizard_risk",
                )
                self._text("Безопасный режим включает только безопасные действия.", role="label", color=GREEN)
            self._button(
                label="Собрать рекомендации",
                callback=self._prepare_wizard,
                width=300,
                height=48,
            )

    def _prepare_wizard(self, sender: Any, app_data: Any, user_data: Any) -> None:
        usage = dpg.get_value("wizard_usage")
        aggressive = dpg.get_value("wizard_risk").startswith("Да")
        module_sets = {
            "Игры": {"system_opt", "privacy", "gaming", "network", "startup", "cleanup", "updates", "cs2_opt"},
            "Работа": {"system_opt", "privacy", "startup", "cleanup", "updates", "context_menu"},
            "Сёрфинг": {"privacy", "network", "startup", "cleanup", "updates"},
            "Создание контента": {"system_opt", "privacy", "network", "startup", "cleanup", "updates"},
        }
        actions = [
            action
            for action in self._all_actions
            if action["module"] in module_sets[usage]
            and (aggressive or action["risk"] == "blue")
        ]
        mode = "агрессивный" if aggressive else "безопасный"
        self._open_review(actions, f"wizard_{usage.lower()}", "wizard")
        self._append_log("info", f"Мастер: сценарий «{usage}», режим {mode}, выбрано {len(actions)}")

    def _build_analysis(self) -> None:
        self._page("page_analysis")
        with dpg.group(parent="page_analysis"):
            self._heading(
                "Анализ системы",
                "Аппаратная часть, службы, приватность, диски, сеть и оценка оптимизации.",
            )
            dpg.add_progress_bar(
                tag="analysis_progress",
                default_value=0.0,
                width=-1,
                show=False,
            )
            self._text("Нажмите «Начать анализ».", color=MUTED, tag="analysis_stage", wrap=850)
            self._button(
                label="Начать глубокий анализ",
                tag="analysis_start",
                callback=self._start_analysis,
                width=280,
                height=45,
            )
            with dpg.child_window(tag="analysis_results", height=-1, border=False):
                self._text("Результаты появятся здесь.", color=MUTED, parent="analysis_results")

    def _start_analysis(self, sender: Any, app_data: Any, user_data: Any) -> None:
        if not self._begin_worker("Анализ системы", self._worker_analysis):
            return
        dpg.configure_item("analysis_start", enabled=False)
        dpg.set_value("analysis_progress", 0.0)
        dpg.show_item("analysis_progress")
        dpg.set_value("analysis_stage", "Подготовка анализа...")

    def _build_expert(self) -> None:
        self._page("page_expert")
        category_count = len(self._categories)
        action_count = len(self._all_actions)
        with dpg.group(parent="page_expert"):
            self._heading(
                "Экспертный режим",
                f"Все {category_count} "
                f"{plural(category_count, 'категория', 'категории', 'категорий')} и "
                f"{action_count} "
                f"{plural(action_count, 'действие', 'действия', 'действий')}. "
                "Цвет показывает уровень риска.",
            )
            # Reserve the complete fixed bottom control panel instead of letting
            # the scrolling catalog consume the page's remaining height.
            expert_bottom_panel_height = 108
            with dpg.child_window(height=-expert_bottom_panel_height, border=False):
                for category_index, category in enumerate(self._categories):
                    with dpg.collapsing_header(
                        label=(
                            f"{category['title']}  ·  {len(category['actions'])} "
                            f"{plural(len(category['actions']), 'действие', 'действия', 'действий')}"
                        ),
                        default_open=category_index == 0,
                    ):
                        self._text(category["desc"], role="label", color=MUTED, wrap=820)
                        for action_index, action in enumerate(category["actions"]):
                            tag = f"expert_{category_index}_{action_index}"
                            with dpg.child_window(height=58, border=True, no_scrollbar=True) as row:
                                dpg.bind_item_theme(row, self._themes["row"])
                                with dpg.table(
                                    header_row=False,
                                    policy=dpg.mvTable_SizingStretchProp,
                                    borders_innerV=False,
                                    borders_outerV=False,
                                ):
                                    dpg.add_table_column(width_fixed=True, init_width_or_weight=30)
                                    dpg.add_table_column(width_fixed=True, init_width_or_weight=28)
                                    dpg.add_table_column(width_stretch=True)
                                    dpg.add_table_column(width_fixed=True, init_width_or_weight=125)
                                    with dpg.table_row():
                                        dpg.add_checkbox(tag=tag)
                                        with dpg.drawlist(width=20, height=20) as glyph_parent:
                                            draw_glyph(
                                                action["icon"],
                                                glyph_parent,
                                                size=20,
                                                color=RISK_COLORS[action["risk"]],
                                            )
                                        self._text(
                                            f"{action['name']}  —  {action['desc']}",
                                            role="label",
                                            color=BONE,
                                            wrap=620,
                                        )
                                        self._text(
                                            RISK_LABELS[action["risk"]],
                                            role="mono",
                                            color=RISK_COLORS[action["risk"]],
                                        )
                            self._expert_checks.append((tag, action))
                        dpg.add_spacer(height=4)
            dpg.add_spacer(height=14)
            self._button(
                label="Проверить выбранные",
                callback=self._prepare_expert,
                width=300,
                height=48,
            )

    def _prepare_expert(self, sender: Any, app_data: Any, user_data: Any) -> None:
        actions = [action for tag, action in self._expert_checks if dpg.get_value(tag)]
        if not actions:
            self._set_status("В Эксперте ничего не выбрано", YELLOW)
            return
        self._open_review(actions, "expert_batch", "expert")

    def _build_startup(self) -> None:
        self._page("page_startup")
        with dpg.group(parent="page_startup"):
            self._heading(
                "Автозагрузка",
                "Критические системные элементы защищены от отключения.",
            )
            with dpg.group(horizontal=True):
                self._button(
                    label="Сканировать",
                    callback=self._refresh_startup,
                    width=180,
                    height=40,
                )
                self._text("Список ещё не загружен", color=MUTED, tag="startup_status")
            with dpg.child_window(tag="startup_table_container", height=-1):
                self._text("Нажмите «Сканировать».", color=MUTED)

    def _refresh_startup(self, sender: Any = None, app_data: Any = None, user_data: Any = None) -> None:
        if self._begin_worker("Сканирование автозагрузки", self._worker_scan_startup):
            dpg.set_value("startup_status", "Сканирование...")

    def _render_startup_table(self) -> None:
        dpg.delete_item("startup_table_container", children_only=True)
        active_names = {item["name"] for item in self._startup_items}
        disabled_items = [
            item
            for name, item in self._disabled_startup_items.items()
            if name not in active_names
        ]
        if not self._startup_items and not disabled_items:
            self._text("Элементы автозагрузки не найдены.", color=MUTED, parent="startup_table_container")
            return
        with dpg.table(
            parent="startup_table_container",
            header_row=True,
            resizable=True,
            policy=dpg.mvTable_SizingStretchProp,
            row_background=True,
            borders_innerH=True,
            borders_outerH=True,
            borders_innerV=True,
            borders_outerV=True,
        ):
            dpg.add_table_column(label="Имя", init_width_or_weight=1.2)
            dpg.add_table_column(label="Значение", init_width_or_weight=2.0)
            dpg.add_table_column(label="Источник", init_width_or_weight=0.9)
            dpg.add_table_column(label="Статус", init_width_or_weight=0.7)
            dpg.add_table_column(label="Действия", init_width_or_weight=1.2)
            for index, item in enumerate(self._startup_items):
                with dpg.table_row():
                    self._text(item["name"], wrap=180)
                    self._text(item["value"], role="mono", color=MUTED, wrap=300)
                    self._text(item["location"], role="mono", color=MUTED, wrap=140)
                    if item["critical"]:
                        self._text("Критический", role="mono", color=RED)
                    elif item["safe_to_disable"]:
                        self._text("Можно отключить", role="mono", color=GREEN)
                    else:
                        self._text("Проверьте", role="mono", color=YELLOW)
                    with dpg.group(horizontal=True):
                        self._button(
                            label="Отключить",
                            enabled=not item["critical"],
                            callback=self._startup_disable,
                            user_data=index,
                            width=100,
                        )
            for item in disabled_items:
                with dpg.table_row():
                    self._text(item["name"], wrap=180)
                    self._text(item["value"], role="mono", color=MUTED, wrap=300)
                    self._text(item["location"], role="mono", color=MUTED, wrap=140)
                    self._text("Отключён", role="mono", color=YELLOW)
                    self._button(
                        label="Вернуть",
                        callback=self._startup_restore,
                        user_data=item["name"],
                        width=100,
                    )

    def _startup_disable(self, sender: Any, app_data: Any, user_data: int) -> None:
        item = self._startup_items[user_data]
        if item["critical"]:
            self._set_status("Критические элементы отключать нельзя", RED)
            return
        self._begin_worker(
            f"Отключение {item['name']}", self._worker_startup_disable, item
        )

    def _startup_restore(self, sender: Any, app_data: Any, user_data: str) -> None:
        self._begin_worker(
            f"Возврат {user_data}", self._worker_startup_restore, user_data
        )

    def _build_backups(self) -> None:
        self._page("page_backups")
        with dpg.group(parent="page_backups"):
            self._heading(
                "Бэкапы",
                "Baseline создаётся один раз. Для каждого применения сохраняется отдельный снимок.",
            )
            with dpg.group(horizontal=True):
                self._button(
                    label="Обновить",
                    callback=self._refresh_backups,
                    width=160,
                    height=38,
                )
                self._text("Список ещё не загружен", color=MUTED, tag="backups_status")
            with dpg.child_window(tag="backups_table_container", height=330):
                self._text("Загрузка...", color=MUTED)
            self._text("Результат восстановления", role="section", color=WHITE)
            with dpg.child_window(tag="backup_restore_details", height=-1):
                self._text("Восстановление ещё не запускалось.", color=MUTED)

    def _refresh_backups(self, sender: Any = None, app_data: Any = None, user_data: Any = None) -> None:
        if self._begin_worker("Чтение списка бэкапов", self._worker_list_backups):
            dpg.set_value("backups_status", "Обновление...")

    def _render_backups_table(self) -> None:
        dpg.delete_item("backups_table_container", children_only=True)
        if not self._backups:
            self._text("Бэкапы не найдены.", color=MUTED, parent="backups_table_container")
            return
        with dpg.table(
            parent="backups_table_container",
            header_row=True,
            resizable=True,
            policy=dpg.mvTable_SizingStretchProp,
            row_background=True,
            borders_innerH=True,
            borders_outerH=True,
        ):
            dpg.add_table_column(label="Дата", init_width_or_weight=1.0)
            dpg.add_table_column(label="Метка", init_width_or_weight=1.4)
            dpg.add_table_column(label="Тип", init_width_or_weight=0.8)
            dpg.add_table_column(label="Секций", init_width_or_weight=0.6)
            dpg.add_table_column(label="Действие", init_width_or_weight=0.8)
            for index, backup in enumerate(self._backups):
                baseline = backup.get("kind") == "baseline" or Path(backup["file"]).name == "baseline.json"
                with dpg.table_row():
                    self._text(backup.get("timestamp") or "—", role="mono", color=MUTED)
                    self._text(backup.get("label") or "Без метки")
                    self._text("BASELINE" if baseline else backup.get("kind", "change"), role="mono", color=GREEN if baseline else MUTED)
                    self._text(str(backup.get("entries_count", 0)), role="mono")
                    self._button(
                        label="Восстановить",
                        callback=self._restore_selected_backup,
                        user_data=index,
                        width=120,
                    )

    def _restore_selected_backup(self, sender: Any, app_data: Any, user_data: int) -> None:
        backup = self._backups[user_data]
        self._begin_worker(
            f"Восстановление {backup.get('label') or Path(backup['file']).name}",
            self._worker_restore,
            backup["file"],
        )

    def _render_restore_result(self, result: dict[str, Any]) -> None:
        dpg.delete_item("backup_restore_details", children_only=True)
        summary = (
            f"Реестр: {result['registry']}  |  Службы: {result['services']}  |  "
            f"Задачи: {result['tasks']}  |  Питание: {result['power']}  |  DNS: {result['dns']}"
        )
        self._text(summary, parent="backup_restore_details", color=GREEN, wrap=820)
        skipped = result.get("skipped", [])
        if skipped:
            self._text(
                f"Пропущено: {len(skipped)}",
                parent="backup_restore_details",
                color=YELLOW,
            )
            for item in skipped:
                self._text(
                    f"— {item}",
                    parent="backup_restore_details",
                    color=YELLOW,
                    wrap=820,
                )
        else:
            self._text("Пропущенных элементов нет.", color=MUTED, parent="backup_restore_details")

    def _build_log(self) -> None:
        self._page("page_log")
        with dpg.group(parent="page_log"):
            self._heading("Лог", "Фактический ход анализа, применения и восстановления.")
            self._button(label="Очистить", callback=self._clear_log, width=140)
            with dpg.child_window(tag="log_lines", height=-1):
                pass

    def _clear_log(self, sender: Any, app_data: Any, user_data: Any) -> None:
        self._log_lines.clear()
        self._log_items.clear()
        dpg.delete_item("log_lines", children_only=True)
        if dpg.does_item_exist("home_last_event"):
            dpg.set_value("home_last_event", "Событий пока нет")
            dpg.configure_item("home_last_event", color=MUTED)

    def _append_log(self, level: str, message: str) -> None:
        timestamp = dt.datetime.now().strftime("%H:%M:%S")
        self._log_lines.append((level, f"{timestamp}  {message}"))
        if level == "error":
            self._logger.error(message)
        else:
            self._logger.info(message)
        if len(self._log_lines) > 500:
            self._log_lines.pop(0)
            if self._log_items:
                old_item = self._log_items.pop(0)
                if dpg.does_item_exist(old_item):
                    dpg.delete_item(old_item)
        if dpg.does_item_exist("log_lines"):
            color = {"success": GREEN, "error": RED, "info": LOG_TECHNICAL}.get(
                level, LOG_TECHNICAL
            )
            item = self._text(
                f"{timestamp}  {message}",
                role="mono",
                parent="log_lines",
                color=color,
                wrap=850,
            )
            self._log_items.append(item)
            self._scroll_log_pending = True
        if dpg.does_item_exist("home_last_event"):
            dpg.set_value("home_last_event", f"[{timestamp}]  {message}")
            dpg.configure_item(
                "home_last_event",
                color={"success": GREEN, "error": RED}.get(level, MUTED),
            )

    def _build_review(self) -> None:
        self._page("page_review")
        with dpg.group(parent="page_review"):
            self._heading(
                "Проверка перед применением",
                "Оставьте только нужные пункты. Цвет — уровень риска; изменения ещё не начались.",
            )
            self._text("ВЫБРАННЫЕ ДЕЙСТВИЯ", role="mono", color=MUTED)
            with dpg.child_window(
                tag="review_regular", height=70, border=False
            ) as regular_list:
                dpg.bind_item_theme(regular_list, self._themes["list"])
                self._text("Список пуст.", color=MUTED)
            with dpg.group(tag="review_irreversible_section", show=False):
                self._text("НЕОБРАТИМЫЕ ДЕЙСТВИЯ", role="mono", color=RED)
                self._text(
                    "Автоматический откат этих действий невозможен.",
                    role="label",
                    color=MUTED,
                    wrap=850,
                )
                with dpg.child_window(
                    tag="review_irreversible", height=60, border=False
                ) as irreversible_list:
                    dpg.bind_item_theme(irreversible_list, self._themes["list"])
                    self._text("Необратимых действий нет.", color=MUTED)
            with dpg.child_window(height=58, border=True, no_scrollbar=True) as summary_card:
                dpg.bind_item_theme(summary_card, self._themes["card"])
                with dpg.group(horizontal=True):
                    self._text("БЭКАП", role="mono", color=MUTED)
                    self._text("—", tag="review_summary", wrap=720)
            self._text("", role="label", color=MUTED, tag="review_status", wrap=850)
            with dpg.group(horizontal=True):
                self._button(
                    label="Отмена",
                    tag="review_cancel",
                    callback=self._cancel_review,
                    width=160,
                    height=42,
                )
                self._button(
                    label="Применить",
                    tag="review_apply",
                    callback=self._apply_review,
                    width=210,
                    height=42,
                    active=True,
                )

    def _review_action_row(
        self,
        action: dict[str, Any],
        index: int,
        parent: int | str,
    ) -> int | str:
        height = self._review_row_height(action)
        with dpg.child_window(
            parent=parent,
            height=height,
            border=True,
            no_scrollbar=True,
        ) as row:
            dpg.bind_item_theme(row, self._themes["row"])
            with dpg.table(
                header_row=False,
                policy=dpg.mvTable_SizingStretchProp,
                borders_innerV=False,
                borders_outerV=False,
            ):
                dpg.add_table_column(width_fixed=True, init_width_or_weight=30)
                dpg.add_table_column(width_fixed=True, init_width_or_weight=28)
                dpg.add_table_column(width_stretch=True)
                dpg.add_table_column(width_fixed=True, init_width_or_weight=130)
                with dpg.table_row():
                    check = dpg.add_checkbox(
                        default_value=True,
                        callback=self._review_toggle,
                        user_data=index,
                    )
                    with dpg.drawlist(width=20, height=20) as glyph_parent:
                        draw_glyph(
                            action["icon"],
                            glyph_parent,
                            size=20,
                            color=RISK_COLORS[action["risk"]],
                        )
                    self._text(
                        f"{action['name']}  —  {action['desc']}",
                        role="label",
                        color=BONE,
                        wrap=620,
                    )
                    self._text(
                        RISK_LABELS[action["risk"]],
                        role="mono",
                        color=RISK_COLORS[action["risk"]],
                    )
        return check

    @staticmethod
    def _review_row_height(action: dict[str, Any]) -> int:
        return 56

    def _open_review(self, actions: list[dict[str, Any]], label: str, source: str) -> None:
        if not actions:
            self._set_status("Нет действий для проверки", YELLOW)
            return
        self._review_actions = actions
        self._review_label = label
        self._review_source = source
        self._review_checks = []
        dpg.delete_item("review_regular", children_only=True)
        dpg.delete_item("review_irreversible", children_only=True)
        regular_count = 0
        irreversible_count = 0
        regular_height = 0
        irreversible_height = 0
        for index, action in enumerate(actions):
            parent = "review_irreversible" if action["irreversible"] else "review_regular"
            if action["irreversible"]:
                irreversible_count += 1
                irreversible_height += self._review_row_height(action) + 4
            else:
                regular_count += 1
                regular_height += self._review_row_height(action) + 4
            self._review_checks.append(self._review_action_row(action, index, parent))
        if not regular_count:
            self._text("Обычных действий нет.", color=MUTED, parent="review_regular")
        if not irreversible_count:
            self._text("Необратимых действий нет.", color=MUTED, parent="review_irreversible")
        dpg.configure_item("review_regular", height=min(360, max(56, regular_height)))
        dpg.configure_item(
            "review_irreversible", height=min(176, max(56, irreversible_height))
        )
        dpg.configure_item("review_irreversible_section", show=bool(irreversible_count))
        dpg.set_value("review_status", "")
        dpg.configure_item("review_cancel", enabled=True)
        self._update_review_summary()
        self._show("review")

    def _review_toggle(self, sender: Any, app_data: Any, user_data: int) -> None:
        self._update_review_summary()

    def _selected_review_actions(self) -> list[dict[str, Any]]:
        return [
            action
            for action, check in zip(self._review_actions, self._review_checks, strict=True)
            if dpg.get_value(check)
        ]

    def _update_review_summary(self) -> None:
        selected = self._selected_review_actions()
        effects = merge_effects(*(action["effects"] for action in selected))
        summary = (
            f"Выбрано: {len(selected)}  |  Ключи реестра: {len(effects['registry'])}  |  "
            f"Службы: {len(effects['services'])}  |  Задачи: {len(effects['tasks'])}  |  "
            f"План питания: {'да' if effects['power'] else 'нет'}  |  "
            f"DNS: {'да' if effects['dns'] else 'нет'}  |  UWP: {len(effects['appx'])}"
        )
        dpg.set_value("review_summary", summary)
        dpg.configure_item(
            "review_apply",
            enabled=bool(selected) and not self._busy,
            label=f"Применить · {len(selected)}",
        )

    def _cancel_review(self, sender: Any, app_data: Any, user_data: Any) -> None:
        if self._busy:
            return
        self._show(self._review_source)

    def _apply_review(self, sender: Any, app_data: Any, user_data: Any) -> None:
        actions = self._selected_review_actions()
        if not actions:
            dpg.set_value("review_status", "Выберите хотя бы одно действие.")
            return
        if self._begin_worker(
            "Применение изменений", self._worker_apply, actions, self._review_label
        ):
            dpg.configure_item("review_apply", enabled=False)
            dpg.configure_item("review_cancel", enabled=False)
            dpg.set_value("review_status", "Создаём бэкап перед изменениями...")

    def _quick_optimize(self, sender: Any, app_data: Any, user_data: Any) -> None:
        actions = [action for action in self._all_actions if action["risk"] == "blue"]
        self._open_review(actions, "quick_optimization", "home")

    def _set_status(self, message: str, color: tuple[int, ...] = ACCENT) -> None:
        if dpg.does_item_exist("status_text"):
            dpg.set_value("status_text", message)
            dpg.configure_item("status_text", color=color)

    def _begin_worker(self, name: str, target: Callable[..., None], *args: Any) -> bool:
        if self._busy:
            self._set_status(f"Уже выполняется: {self._busy_name}", YELLOW)
            return False
        self._busy = True
        self._busy_name = name
        self._set_status(name, ACCENT)
        thread = threading.Thread(
            target=self._worker_guard,
            args=(target, args),
            name=f"WinBoost:{name}",
            daemon=True,
        )
        thread.start()
        return True

    # These worker methods never call Dear PyGui; they communicate via _events.
    def _worker_guard(self, target: Callable[..., None], args: tuple[Any, ...]) -> None:
        try:
            target(*args)
        except Exception as exc:
            self._events.put(("worker_error", self._busy_name, repr(exc)))
        finally:
            self._events.put(("worker_idle",))

    def _worker_baseline(self) -> None:
        path = ensure_baseline()
        self._events.put(("baseline_done", path))

    def _worker_analysis(self) -> None:
        def progress(stage: str, current: int, total: int) -> None:
            self._events.put(("analysis_progress", stage, current, total))

        info = analyze_system(progress_cb=progress)
        self._events.put(("analysis_done", info, format_analysis(info)))

    def _worker_scan_startup(self) -> None:
        self._events.put(("startup_loaded", scan_startup_items()))

    def _worker_startup_disable(self, item: dict[str, Any]) -> None:
        result = disable_startup_item(
            item, self.log_success, self.log_error, self.log_info
        )
        self._events.put(("startup_action_done", "отключение", item, bool(result)))
        self._events.put(("startup_loaded", scan_startup_items()))

    def _worker_startup_restore(self, name: str) -> None:
        result = restore_startup_item(
            name, self.log_success, self.log_error, self.log_info
        )
        self._events.put(("startup_action_done", "возврат", name, bool(result)))
        self._events.put(("startup_loaded", scan_startup_items()))

    def _worker_list_backups(self) -> None:
        self._events.put(("backups_loaded", list_backups()))

    def _worker_restore(self, filepath: str) -> None:
        result = restore_backup(filepath, log_fn=self.log_info)
        self._events.put(("restore_done", filepath, result))
        self._events.put(("backups_loaded", list_backups()))

    def _worker_apply(self, actions: list[dict[str, Any]], label: str) -> None:
        effects = merge_effects(*(action["effects"] for action in actions))
        backup_path = capture(effects, label=label)
        self._events.put(("log", "success", f"Бэкап создан: {backup_path}"))
        succeeded = 0
        failed = 0
        total = len(actions)
        for index, action in enumerate(actions, start=1):
            self._events.put(("apply_progress", action["name"], index, total))
            self._events.put(("log", "info", f"[{index}/{total}] {action['name']}"))
            try:
                result = action["run"]()
                if result is False:
                    failed += 1
                    self._events.put(("log", "error", f"Не выполнено: {action['name']}"))
                else:
                    succeeded += 1
                    self._events.put(("log", "success", f"Завершено: {action['name']}"))
            except Exception as exc:
                failed += 1
                self._events.put(("log", "error", f"Ошибка «{action['name']}»: {exc}"))
        self._events.put(("apply_done", succeeded, failed, backup_path))
        self._events.put(("backups_loaded", list_backups()))

    # Queue dispatch always runs from the Dear PyGui render thread.
    def _drain_events(self) -> None:
        if self._scroll_log_pending and dpg.does_item_exist("log_lines"):
            dpg.set_y_scroll("log_lines", dpg.get_y_scroll_max("log_lines"))
            self._scroll_log_pending = False
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            kind, *payload = event
            if kind == "log":
                self._append_log(payload[0], payload[1])
            elif kind == "worker_idle":
                worker_name = self._busy_name
                self._busy = False
                self._busy_name = ""
                if (
                    worker_name == "Анализ системы"
                    and dpg.does_item_exist("analysis_progress")
                ):
                    dpg.hide_item("analysis_progress")
                if dpg.does_item_exist("analysis_start"):
                    dpg.configure_item("analysis_start", enabled=True)
                if dpg.does_item_exist("review_cancel"):
                    dpg.configure_item("review_cancel", enabled=True)
                if self._active_page == "review":
                    self._update_review_summary()
            elif kind == "worker_error":
                name, error = payload
                self._append_log("error", f"{name}: {error}")
                self._set_status(f"Ошибка: {name}", RED)
                if dpg.does_item_exist("review_status"):
                    dpg.set_value("review_status", f"Ошибка: {error}")
            elif kind == "baseline_done":
                path = payload[0]
                self._append_log("success", f"Первичный снимок готов: {path}")
                self._set_status("Baseline готов", GREEN)
            elif kind == "analysis_progress":
                stage, current, total = payload
                dpg.set_value("analysis_progress", current / max(total, 1))
                dpg.set_value("analysis_stage", f"[{current}/{total}] {stage}")
            elif kind == "analysis_done":
                info, lines = payload
                self._render_analysis(info, lines)
                self._set_status("Анализ завершён", GREEN)
            elif kind == "startup_loaded":
                self._startup_items = payload[0]
                dpg.set_value("startup_status", f"Найдено: {len(self._startup_items)}")
                self._render_startup_table()
            elif kind == "startup_action_done":
                operation, subject, success = payload
                if operation == "отключение":
                    item = subject
                    name = item["name"]
                    if success:
                        self._disabled_startup_items[name] = item
                else:
                    name = subject
                    if success:
                        self._disabled_startup_items.pop(name, None)
                color = GREEN if success else RED
                self._set_status(f"{operation.capitalize()}: {name}", color)
            elif kind == "backups_loaded":
                self._backups = payload[0]
                dpg.set_value("backups_status", f"Снимков: {len(self._backups)}")
                self._render_backups_table()
            elif kind == "restore_done":
                filepath, result = payload
                self._render_restore_result(result)
                self._append_log("success", f"Восстановление завершено: {filepath}")
                self._set_status("Восстановление завершено", GREEN)
            elif kind == "apply_progress":
                action_name, current, total = payload
                dpg.set_value("review_status", f"[{current}/{total}] {action_name}")
            elif kind == "apply_done":
                succeeded, failed, backup_path = payload
                dpg.set_value(
                    "review_status",
                    f"Готово: {succeeded}; ошибок: {failed}. Бэкап: {backup_path}",
                )
                self._set_status(
                    f"Применено: {succeeded}, ошибок: {failed}",
                    GREEN if failed == 0 else YELLOW,
                )

    def _render_analysis(self, info: dict[str, Any], lines: list[tuple[str, str]]) -> None:
        dpg.set_value("analysis_progress", 1.0)
        dpg.hide_item("analysis_progress")
        dpg.set_value("analysis_stage", "Анализ завершён")
        dpg.delete_item("analysis_results", children_only=True)
        colors = {
            "header": WHITE,
            "good": GREEN,
            "warn": YELLOW,
            "info": MUTED,
            "score": WHITE,
        }
        sections: list[tuple[str, list[tuple[str, str]]]] = []
        title = "Сводка"
        rows: list[tuple[str, str]] = []
        for text, category in lines:
            if category == "header":
                if rows:
                    sections.append((title, rows))
                raw_title = text.strip("═ ").title()
                title = {
                    "Аппаратное Обеспечение": "Железо",
                    "Диски": "Диски",
                    "Службы": "Службы",
                    "Приватность": "Приватность",
                    "Производительность": "Производительность",
                    "Сеть": "Сеть",
                }.get(raw_title, raw_title)
                rows = []
            elif text:
                rows.append((_display_text(text).strip(), category))
        if rows:
            sections.append((title, rows))

        for section_title, section_rows in sections:
            height = 50 + max(1, len(section_rows)) * 28
            with dpg.child_window(
                parent="analysis_results",
                height=height,
                border=True,
                no_scrollbar=True,
            ) as card:
                dpg.bind_item_theme(card, self._themes["card"])
                self._text(section_title, role="section", color=WHITE)
                for text, category in section_rows:
                    self._text(
                        text,
                        role="body",
                        color=colors.get(category, MUTED),
                        wrap=790,
                    )


def _capture_all(output_dir: Path) -> None:
    """Capture every production page with DPG's framebuffer mechanism."""
    output_dir.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve()
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    for page in (*PAGE_NAMES, "review"):
        output_file = output_dir / f"{page}.png"
        attempts: list[Path] = []
        for attempt in range(2):
            candidate = output_dir / f".{page}-{attempt}.png"
            if candidate.exists():
                candidate.unlink()
            subprocess.run(
                [sys.executable, str(script), "--capture-one", page, str(candidate)],
                check=True,
                env=environment,
            )
            if not candidate.exists() or candidate.stat().st_size == 0:
                raise RuntimeError(f"Не удалось сохранить скриншот: {candidate}")
            attempts.append(candidate)
            # DPG 2.3/DirectX can keep the just-destroyed font atlas alive for
            # a fraction of a second.  A second independent framebuffer also
            # protects the final set from a partially uploaded font atlas.
            time.sleep(0.35)
        best = max(attempts, key=lambda path: path.stat().st_size)
        if output_file.exists():
            output_file.unlink()
        best.replace(output_file)
        for candidate in attempts:
            if candidate.exists():
                candidate.unlink()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 3 and args[0] == "--capture-one":
        page, output = args[1:]
        if page not in {*PAGE_NAMES, "review"}:
            return 2
        WinBoostApp()._build(
            capture_page=page,
            capture_path=Path(output).resolve(),
        )
        return 0
    if len(args) == 2 and args[0] == "--capture-all":
        _capture_all(Path(args[1]).resolve())
        return 0
    if args:
        print(
            "Использование: python WinBoostGUI.py [--capture-all ПАПКА]",
            file=sys.stderr,
        )
        return 2
    elevate()
    WinBoostApp()._build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
