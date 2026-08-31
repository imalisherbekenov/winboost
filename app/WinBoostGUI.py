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
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any

import dearpygui.dearpygui as dpg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import ALL_MODULES
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

ACCENT = (59, 130, 246, 255)
ACCENT2 = (139, 92, 246, 255)
GREEN = (16, 185, 129, 255)
YELLOW = (245, 158, 11, 255)
RED = (239, 68, 68, 255)
BLUE = (59, 130, 246, 255)

RISK_COLORS = {"red": RED, "yellow": YELLOW, "blue": BLUE}
RISK_LABELS = {"red": "КРАСНЫЙ", "yellow": "ЖЁЛТЫЙ", "blue": "СИНИЙ"}

PALETTE = {
    "dark": {
        "bg": (11, 14, 20, 255),
        "card": (21, 26, 35, 255),
        "card2": (31, 38, 51, 255),
        "text": (248, 250, 252, 255),
        "dim": (148, 163, 184, 255),
        "border": (30, 41, 59, 255),
    },
    "light": {
        "bg": (245, 247, 250, 255),
        "card": (255, 255, 255, 255),
        "card2": (226, 232, 240, 255),
        "text": (15, 23, 42, 255),
        "dim": (100, 116, 139, 255),
        "border": (203, 213, 225, 255),
    },
}

PAGE_NAMES = ("home", "wizard", "analysis", "expert", "startup", "backups", "log")


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


def _build_theme(palette: dict[str, tuple[int, int, int, int]]) -> int | str:
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, palette["bg"])
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, palette["card"])
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, palette["card"])
            dpg.add_theme_color(dpg.mvThemeCol_Button, palette["card2"])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, palette["card2"])
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, palette["border"])
            dpg.add_theme_color(dpg.mvThemeCol_Text, palette["text"])
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, palette["dim"])
            dpg.add_theme_color(dpg.mvThemeCol_Border, palette["border"])
            dpg.add_theme_color(dpg.mvThemeCol_Header, palette["card2"])
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, palette["card"])
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, palette["card"])
            dpg.add_theme_color(dpg.mvThemeCol_TableHeaderBg, palette["card2"])
            dpg.add_theme_color(dpg.mvThemeCol_TableBorderStrong, palette["border"])
            dpg.add_theme_color(dpg.mvThemeCol_TableBorderLight, palette["border"])
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 9, 7)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 9, 9)
    return theme


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
        self._theme_name = "dark"
        self._font_path = ""
        self._title_font: int | str = 0
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

    def _load_font(self) -> None:
        windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        candidates = (
            windows_dir / "Fonts" / "segoeui.ttf",
            windows_dir / "Fonts" / "arial.ttf",
        )
        font_path = next((path for path in candidates if path.exists()), None)
        if font_path is None:
            raise FileNotFoundError("Не найден системный шрифт с поддержкой кириллицы")
        self._font_path = str(font_path)
        with dpg.font_registry():
            with dpg.font(self._font_path, 17) as font:
                # DPG 2.3 builds ranges automatically, but explicit hints retain
                # compatibility with earlier 2.x builds and document the contract.
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)
                    dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
                    dpg.add_font_range(0x0400, 0x052F)
            self._title_font = dpg.add_font(self._font_path, 25)
        dpg.bind_font(font)

    def _build(self) -> None:
        dpg.create_context()
        try:
            self._load_font()
            self._themes = {name: _build_theme(p) for name, p in PALETTE.items()}
            dpg.bind_theme(self._themes["dark"])
            with dpg.window(tag="main_win", label=APP_TITLE, no_close=True):
                with dpg.group(horizontal=True):
                    self._build_sidebar()
                    with dpg.child_window(
                        tag="content", width=-1, height=-1, border=False
                    ):
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
            )
            dpg.setup_dearpygui()
            dpg.set_primary_window("main_win", True)
            dpg.show_viewport()
            self._show("home")
            self._append_log("info", f"Интерфейс запущен. Шрифт: {self._font_path}")
            self._begin_worker("Создание первичного снимка", self._worker_baseline)
            while dpg.is_dearpygui_running():
                self._drain_events()
                dpg.render_dearpygui_frame()
        finally:
            dpg.destroy_context()

    def _build_sidebar(self) -> None:
        with dpg.child_window(tag="sidebar", width=230, height=-1, border=False):
            dpg.add_text("W I N B O O S T", color=ACCENT)
            dpg.add_text("SYSTEM OPTIMIZER", color=PALETTE["dark"]["dim"])
            dpg.add_separator()
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
            dpg.add_spacer(height=14)
            dpg.add_separator()
            dpg.add_text("Тема")
            dpg.add_combo(
                ("Тёмная", "Светлая"),
                default_value="Тёмная",
                width=-1,
                callback=self._switch_theme,
            )
            dpg.add_spacer(height=10)
            dpg.add_text("ГОТОВО", tag="status_text", color=GREEN, wrap=205)

    def _nav_btn(self, label: str, page: str) -> None:
        dpg.add_button(
            label=label,
            callback=self._navigate,
            user_data=page,
            width=-1,
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

    def _switch_theme(self, sender: Any, app_data: str, user_data: Any) -> None:
        self._theme_name = "light" if app_data == "Светлая" else "dark"
        dpg.bind_theme(self._themes[self._theme_name])

    def _page(self, tag: str) -> None:
        dpg.add_child_window(tag=tag, width=-1, height=-1, border=False, show=False)

    def _heading(self, title: str, subtitle: str, color: tuple[int, ...] = ACCENT) -> None:
        title_item = dpg.add_text(title, color=color)
        dpg.bind_item_font(title_item, self._title_font)
        dpg.add_text(subtitle, wrap=850)
        dpg.add_separator()

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
            dpg.add_text(admin_text, color=GREEN if is_admin() else RED)
            dpg.add_spacer(height=18)
            with dpg.group(horizontal=True):
                self._home_card(
                    "Мастер",
                    "Ответьте на два вопроса — мы соберём подходящий набор.",
                    "Открыть",
                    self._open_page_callback,
                    "wizard",
                    ACCENT2,
                )
                self._home_card(
                    "Анализ",
                    "Проверьте систему и получите подробный цветной отчёт.",
                    "Запустить",
                    self._open_page_callback,
                    "analysis",
                    ACCENT,
                )
                self._home_card(
                    "Быстрая оптимизация",
                    "Только действия с синим уровнем риска — сначала проверка.",
                    "Проверить",
                    self._quick_optimize,
                    None,
                    GREEN,
                )
                self._home_card(
                    "Бэкапы",
                    "Просмотрите снимки и восстановите выбранное состояние.",
                    "Открыть",
                    self._open_page_callback,
                    "backups",
                    YELLOW,
                )

    def _home_card(
        self,
        title: str,
        desc: str,
        button: str,
        callback: Callable[..., None],
        user_data: Any,
        color: tuple[int, ...],
    ) -> None:
        with dpg.child_window(width=213, height=235):
            dpg.add_text(title, color=color, wrap=190)
            dpg.add_spacer(height=8)
            dpg.add_text(desc, wrap=190)
            dpg.add_spacer(height=12)
            dpg.add_button(
                label=button,
                width=-1,
                height=38,
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
                ACCENT2,
            )
            dpg.add_spacer(height=8)
            with dpg.child_window(height=145):
                dpg.add_text("Для чего вы чаще всего используете ПК?")
                dpg.add_combo(
                    ("Игры", "Работа", "Сёрфинг", "Создание контента"),
                    default_value="Игры",
                    tag="wizard_usage",
                    width=420,
                )
            with dpg.child_window(height=145):
                dpg.add_text("Готовы к агрессивным настройкам?")
                dpg.add_radio_button(
                    ("Нет, только безопасный режим", "Да, максимум производительности"),
                    default_value="Нет, только безопасный режим",
                    tag="wizard_risk",
                )
                dpg.add_text("Безопасный режим включает только синий уровень риска.", color=BLUE)
            dpg.add_spacer(height=10)
            dpg.add_button(
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
            dpg.add_progress_bar(tag="analysis_progress", default_value=0.0, width=-1)
            dpg.add_text("Нажмите «Начать анализ».", tag="analysis_stage", wrap=850)
            dpg.add_button(
                label="Начать глубокий анализ",
                tag="analysis_start",
                callback=self._start_analysis,
                width=280,
                height=45,
            )
            dpg.add_separator()
            with dpg.child_window(tag="analysis_results", height=-1):
                dpg.add_text("Результаты появятся здесь.")

    def _start_analysis(self, sender: Any, app_data: Any, user_data: Any) -> None:
        if not self._begin_worker("Анализ системы", self._worker_analysis):
            return
        dpg.configure_item("analysis_start", enabled=False)
        dpg.set_value("analysis_progress", 0.0)
        dpg.set_value("analysis_stage", "Подготовка анализа...")

    def _build_expert(self) -> None:
        self._page("page_expert")
        with dpg.group(parent="page_expert"):
            self._heading(
                "Экспертный режим",
                "Все 10 категорий и 56 действий. Цвет показывает уровень риска.",
            )
            with dpg.child_window(height=-88):
                for category_index, category in enumerate(self._categories):
                    with dpg.collapsing_header(
                        label=f"{category['title']} — {category['desc']}",
                        default_open=category_index == 0,
                    ):
                        for action_index, action in enumerate(category["actions"]):
                            tag = f"expert_{category_index}_{action_index}"
                            with dpg.group(horizontal=True):
                                dpg.add_text(
                                    RISK_LABELS[action["risk"]],
                                    color=RISK_COLORS[action["risk"]],
                                )
                                dpg.add_checkbox(label=action["name"], tag=tag)
                            dpg.add_text(action["desc"], wrap=790)
                            self._expert_checks.append((tag, action))
                        dpg.add_spacer(height=6)
            dpg.add_button(
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
                dpg.add_button(
                    label="Сканировать",
                    callback=self._refresh_startup,
                    width=180,
                    height=40,
                )
                dpg.add_text("Список ещё не загружен", tag="startup_status")
            with dpg.child_window(tag="startup_table_container", height=-1):
                dpg.add_text("Нажмите «Сканировать».")

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
            dpg.add_text("Элементы автозагрузки не найдены.", parent="startup_table_container")
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
                    dpg.add_text(item["name"], wrap=180)
                    dpg.add_text(item["value"], wrap=300)
                    dpg.add_text(item["location"], wrap=140)
                    if item["critical"]:
                        dpg.add_text("Критический", color=RED)
                    elif item["safe_to_disable"]:
                        dpg.add_text("Можно отключить", color=GREEN)
                    else:
                        dpg.add_text("Проверьте", color=YELLOW)
                    with dpg.group(horizontal=True):
                        dpg.add_button(
                            label="Отключить",
                            enabled=not item["critical"],
                            callback=self._startup_disable,
                            user_data=index,
                            width=100,
                        )
            for item in disabled_items:
                with dpg.table_row():
                    dpg.add_text(item["name"], wrap=180)
                    dpg.add_text(item["value"], wrap=300)
                    dpg.add_text(item["location"], wrap=140)
                    dpg.add_text("Отключён", color=YELLOW)
                    dpg.add_button(
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
                ACCENT2,
            )
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Обновить",
                    callback=self._refresh_backups,
                    width=160,
                    height=38,
                )
                dpg.add_text("Список ещё не загружен", tag="backups_status")
            with dpg.child_window(tag="backups_table_container", height=330):
                dpg.add_text("Загрузка...")
            dpg.add_text("Результат восстановления", color=ACCENT2)
            with dpg.child_window(tag="backup_restore_details", height=-1):
                dpg.add_text("Восстановление ещё не запускалось.")

    def _refresh_backups(self, sender: Any = None, app_data: Any = None, user_data: Any = None) -> None:
        if self._begin_worker("Чтение списка бэкапов", self._worker_list_backups):
            dpg.set_value("backups_status", "Обновление...")

    def _render_backups_table(self) -> None:
        dpg.delete_item("backups_table_container", children_only=True)
        if not self._backups:
            dpg.add_text("Бэкапы не найдены.", parent="backups_table_container")
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
                    dpg.add_text(backup.get("timestamp") or "—")
                    dpg.add_text(backup.get("label") or "Без метки")
                    dpg.add_text("BASELINE" if baseline else backup.get("kind", "change"), color=GREEN if baseline else ACCENT)
                    dpg.add_text(str(backup.get("entries_count", 0)))
                    dpg.add_button(
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
        dpg.add_text(summary, parent="backup_restore_details", color=GREEN, wrap=820)
        skipped = result.get("skipped", [])
        if skipped:
            dpg.add_text(
                f"Пропущено: {len(skipped)}",
                parent="backup_restore_details",
                color=YELLOW,
            )
            for item in skipped:
                dpg.add_text(
                    f"— {item}",
                    parent="backup_restore_details",
                    color=YELLOW,
                    wrap=820,
                )
        else:
            dpg.add_text("Пропущенных элементов нет.", parent="backup_restore_details")

    def _build_log(self) -> None:
        self._page("page_log")
        with dpg.group(parent="page_log"):
            self._heading("Лог", "Фактический ход анализа, применения и восстановления.")
            dpg.add_button(label="Очистить", callback=self._clear_log, width=140)
            with dpg.child_window(tag="log_lines", height=-1):
                pass

    def _clear_log(self, sender: Any, app_data: Any, user_data: Any) -> None:
        self._log_lines.clear()
        self._log_items.clear()
        dpg.delete_item("log_lines", children_only=True)

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
            color = {"success": GREEN, "error": RED, "info": PALETTE["dark"]["dim"]}.get(level, BLUE)
            item = dpg.add_text(
                f"{timestamp}  {message}", parent="log_lines", color=color, wrap=850
            )
            self._log_items.append(item)
            self._scroll_log_pending = True

    def _build_review(self) -> None:
        self._page("page_review")
        with dpg.group(parent="page_review"):
            self._heading(
                "Проверка перед применением",
                "Оставьте только нужные пункты. Цвет — уровень риска; изменения ещё не начались.",
                ACCENT2,
            )
            dpg.add_text("Выбранные действия", color=ACCENT)
            with dpg.child_window(tag="review_regular", height=185):
                dpg.add_text("Список пуст.")
            dpg.add_text("Необратимые действия", color=RED)
            dpg.add_text(
                "Внимание: автоматический откат этих действий невозможен.",
                color=RED,
                wrap=850,
            )
            with dpg.child_window(tag="review_irreversible", height=105):
                dpg.add_text("Необратимых действий нет.")
            dpg.add_text("Что попадёт в бэкап", color=ACCENT2)
            dpg.add_text("—", tag="review_summary", wrap=850)
            dpg.add_text("", tag="review_status", wrap=850)
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Применить",
                    tag="review_apply",
                    callback=self._apply_review,
                    width=210,
                    height=46,
                )
                dpg.add_button(
                    label="Отмена",
                    tag="review_cancel",
                    callback=self._cancel_review,
                    width=160,
                    height=46,
                )

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
        for index, action in enumerate(actions):
            parent = "review_irreversible" if action["irreversible"] else "review_regular"
            if action["irreversible"]:
                irreversible_count += 1
            else:
                regular_count += 1
            with dpg.group(horizontal=True, parent=parent):
                dpg.add_text(
                    RISK_LABELS[action["risk"]],
                    color=RISK_COLORS[action["risk"]],
                )
                check = dpg.add_checkbox(
                    label=action["name"],
                    default_value=True,
                    callback=self._review_toggle,
                    user_data=index,
                )
                self._review_checks.append(check)
            dpg.add_text(action["desc"], parent=parent, wrap=790)
        if not regular_count:
            dpg.add_text("Обычных действий нет.", parent="review_regular")
        if not irreversible_count:
            dpg.add_text("Необратимых действий нет.", parent="review_irreversible")
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
        dpg.configure_item("review_apply", enabled=bool(selected) and not self._busy)

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
                self._busy = False
                self._busy_name = ""
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
        dpg.set_value("analysis_stage", "Анализ завершён")
        dpg.delete_item("analysis_results", children_only=True)
        colors = {
            "header": ACCENT,
            "good": GREEN,
            "warn": YELLOW,
            "info": PALETTE["dark"]["dim"],
            "score": ACCENT2,
        }
        for text, category in lines:
            if not text:
                dpg.add_separator(parent="analysis_results")
            else:
                dpg.add_text(
                    text,
                    parent="analysis_results",
                    color=colors.get(category, PALETTE["dark"]["dim"]),
                    wrap=820,
                )


if __name__ == "__main__":
    elevate()
    WinBoostApp()._build()
