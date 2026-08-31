"""
WinBoost GUI — Main Application v2.1
Premium CustomTkinter interface with Wizard + Expert modes.
"""
import customtkinter as ctk
import threading
import ctypes
import sys
import os
import datetime
import time
import tkinter.filedialog as filedialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import ALL_MODULES
from modules.analyzer import analyze_system, format_analysis
from modules.backup import create_backup, restore_backup, list_backups
from modules.startup import scan_startup_items, disable_startup_item

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT = "#3B82F6"    # Cyberpunk Cyan
ACCENT2 = "#8B5CF6"   # Electric Purple
GREEN = "#10B981"
YELLOW = "#F59E0B"
RED = "#EF4444"
BG = "#0B0E14"        # Almost pitch black
BG_CARD = "#151A23"   # Glassmorphism dark card
BG_CARD2 = "#1F2633"  # Lighter element inside card
TEXT_DIM = "#94A3B8"
BORDER = "#1E293B"    # Cyber border
RISK_COLORS = {"red": RED, "yellow": YELLOW, "blue": ACCENT}


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def elevate():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)


class CircularProgressbar(ctk.CTkCanvas):
    def __init__(self, parent, size=150, thickness=12, bg_color=BG_CARD2, fg_color=ACCENT):
        super().__init__(parent, width=size, height=size, bg=BG_CARD, highlightthickness=0)
        self.size = size
        self.thickness = thickness
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.padding = thickness + 2
        self._pulse_id = None
        self._pulse_angle = 90

        # Background ring
        self.create_arc(
            self.padding, self.padding,
            self.size - self.padding, self.size - self.padding,
            start=0, extent=359.9, outline=self.bg_color,
            width=self.thickness, style="arc"
        )
        # Foreground ring
        self.arc = self.create_arc(
            self.padding, self.padding,
            self.size - self.padding, self.size - self.padding,
            start=90, extent=0, outline=self.fg_color,
            width=self.thickness, style="arc"
        )
        # Text in center
        self.text_id = self.create_text(
            self.size / 2, self.size / 2,
            text="0%", fill=self.fg_color, font=("Consolas", 24, "bold")
        )

    def set(self, value):
        self.stop_pulse()
        value = max(0.0, min(1.0, value))
        extent = -int(value * 359.9)
        self.itemconfigure(self.arc, extent=extent, outline=self.fg_color)
        self.itemconfigure(self.text_id, text=f"{int(value * 100)}%", fill=self.fg_color)

    def pulse(self):
        self.stop_pulse()
        self._pulse_angle = (self._pulse_angle + 15) % 360
        self.itemconfigure(self.arc, start=self._pulse_angle, extent=-60, outline=self.fg_color)
        self.itemconfigure(self.text_id, text="", fill=self.fg_color)
        self._pulse_id = self.after(40, self.pulse)

    def stop_pulse(self):
        if self._pulse_id:
            self.after_cancel(self._pulse_id)
            self._pulse_id = None


class WinBoostApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WinBoost 2.1")
        self.geometry("1020x720")
        self.minsize(900, 640)
        self.configure(fg_color=BG)
        self.log_lines: list[str] = []
        self._live_log = None
        self._active_nav_idx = 0
        # IMPORTANT: pack order matters in tkinter!
        # bottom first, then left sidebar, then main fills the rest
        self._build_statusbar()
        self._build_nav()
        self._build_main_container()
        self._show_home()
        self._set_active_nav(0)

    # ── NAV ──
    def _build_nav(self):
        self.nav = ctk.CTkFrame(self, width=220, fg_color=BG_CARD, corner_radius=0)
        self.nav.pack(side="left", fill="y")
        self.nav.pack_propagate(False)

        ctk.CTkLabel(self.nav, text="W B .", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
                      text_color=ACCENT).pack(pady=(36, 4))
        ctk.CTkLabel(self.nav, text="S Y S T E M   O P T I M I Z E R", font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
                      text_color=TEXT_DIM).pack(pady=(0, 40))

        buttons = [
            ("  Главная", self._show_home),
            ("  Мастер", self._show_wizard),
            ("  Анализ", self._show_analysis),
            ("  Эксперт", self._show_expert),
            ("  Автозагрузка", self._show_startup),
            ("  Бэкапы", self._show_backups),
            ("  Лог", self._show_log),
        ]
        self.nav_btns = []
        for idx, (text, cmd) in enumerate(buttons):
            def _make_command(i=idx, c=cmd):
                return lambda: (self._set_active_nav(i), c())
            b = ctk.CTkButton(
                self.nav, text=text, command=_make_command(), anchor="w",
                fg_color="transparent", hover_color=BG_CARD2,
                text_color="#f8fafc", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), height=46, corner_radius=12,
            )
            b.pack(fill="x", padx=16, pady=4)
            self.nav_btns.append(b)

        # Theme switcher at bottom of nav
        theme_frame = ctk.CTkFrame(self.nav, fg_color="transparent")
        theme_frame.pack(side="bottom", fill="x", padx=16, pady=20)
        ctk.CTkLabel(theme_frame, text="Тема", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=TEXT_DIM).pack(anchor="w")
        self.theme_switch = ctk.CTkSegmentedButton(
            theme_frame, values=["Dark", "Light", "System"],
            command=self._change_theme,
            fg_color=BG_CARD2, selected_color=ACCENT, selected_hover_color=ACCENT,
            unselected_color=BG_CARD, unselected_hover_color=BG_CARD2,
            text_color="#f8fafc", font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.theme_switch.pack(fill="x", pady=(6, 0))
        self.theme_switch.set("Dark")

    def _change_theme(self, value: str):
        ctk.set_appearance_mode(value.lower())

    def _set_active_nav(self, idx: int):
        self._active_nav_idx = idx
        for i, b in enumerate(self.nav_btns):
            if i == idx:
                b.configure(fg_color=BG_CARD2, text_color=ACCENT)
            else:
                b.configure(fg_color="transparent", text_color="#f8fafc")

    def _build_main_container(self):
        self.main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.main.pack(fill="both", expand=True)
        self.content = None

    def _build_statusbar(self):
        self.statusbar = ctk.CTkFrame(self, height=32, fg_color="#080d1a", corner_radius=0)
        self.statusbar.pack(side="bottom", fill="x")
        self.statusbar.pack_propagate(False)
        # Version label
        ctk.CTkLabel(self.statusbar, text="WinBoost 2.1", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                      text_color=ACCENT).pack(side="left", padx=(16, 8))
        admin_text = "[ADMIN]" if is_admin() else "[NO ADMIN]"
        admin_color = GREEN if is_admin() else YELLOW
        ctk.CTkLabel(self.statusbar, text=admin_text, font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
                      text_color=admin_color).pack(side="left", padx=4)
        self._status_label = ctk.CTkLabel(self.statusbar, text="Готов", font=ctk.CTkFont(family="Consolas", size=12),
                                           text_color=TEXT_DIM)
        self._status_label.pack(side="right", padx=16)
        self._clock_label = ctk.CTkLabel(self.statusbar, text="", font=ctk.CTkFont(family="Consolas", size=12),
                                          text_color=TEXT_DIM)
        self._clock_label.pack(side="right", padx=8)
        self._update_clock()

    def _update_clock(self):
        self._clock_label.configure(text=datetime.datetime.now().strftime("%H:%M:%S"))
        self.after(1000, self._update_clock)

    def _set_status(self, text, color=TEXT_DIM):
        self._status_label.configure(text=text, text_color=color)

    def _clear_content(self, scrollable=False):
        """Clear content area. Use scrollable=True for pages with lots of content."""
        self._live_log = None
        # Destroy ALL children of main to prevent ghost widgets
        # (CTkScrollableFrame leaves internal canvas/scrollbar behind)
        for widget in self.main.winfo_children():
            widget.destroy()
        self.content = None
        if scrollable:
            self.content = ctk.CTkScrollableFrame(self.main, fg_color=BG, corner_radius=12)
        else:
            self.content = ctk.CTkFrame(self.main, fg_color=BG, corner_radius=12)
        self.content.pack(fill="both", expand=True, padx=32, pady=(24, 16))
        return self.content

    # ── Logging ──
    def _log(self, msg, tag="info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_lines.append(f"[{ts}] [{tag.upper()}] {msg}")

    def log_success(self, msg):
        self._log(msg, "ok"); self._update_log_widget(msg, GREEN); self._set_status(msg, GREEN)

    def log_error(self, msg):
        self._log(msg, "err"); self._update_log_widget(msg, RED); self._set_status(msg, RED)

    def log_info(self, msg):
        self._log(msg, "info"); self._update_log_widget(msg, TEXT_DIM); self._set_status(msg)

    def _update_log_widget(self, msg, color):
        if self._live_log and self._live_log.winfo_exists():
            tag = f"log_{color.replace('#', '')}"
            self._live_log.tag_config(tag, foreground=color)
            self._live_log.configure(state="normal")
            self._live_log.insert("end", f"{msg}\n", tag)
            self._live_log.configure(state="disabled")
            self._live_log.see("end")

    # ── HOME ──
    def _show_home(self):
        c = self._clear_content()
        ctk.CTkLabel(c, text="Настройте Windows под себя",
                     font=ctk.CTkFont(family="Segoe UI", size=36, weight="bold"), text_color=ACCENT).pack(anchor="w", pady=(20, 8))
        ctk.CTkLabel(c, text="Пошаговый и безопасный способ улучшить производительность.",
                     font=ctk.CTkFont(family="Segoe UI", size=16), text_color=TEXT_DIM).pack(anchor="w", pady=(0, 48))

        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", pady=10)
        cards = [
            ("🧙 Мастер", "Пошаговая настройка\nдля новичков", self._show_wizard, ACCENT2),
            ("🔍 Анализ", "Проверить систему\nи получить оценку", self._show_analysis, ACCENT),
            ("⚡ Быстрая", "Только безопасные\nнастройки", self._quick_optimize, GREEN),
            ("💾 Бэкапы", "Откатить изменения\nиз снимка", self._show_backups, YELLOW),
        ]
        for i, (title, desc, cmd, color) in enumerate(cards):
            card = ctk.CTkFrame(row, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
            card.grid(row=0, column=i, padx=12, pady=12, sticky="nsew")
            row.grid_columnconfigure(i, weight=1)
            card.bind("<Enter>", lambda e, c=card, ac=color: c.configure(border_color=ac))
            card.bind("<Leave>", lambda e, c=card: c.configure(border_color=BORDER))
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                         text_color=color).pack(padx=24, pady=(24, 8), anchor="w")
            ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(family="Segoe UI", size=14),
                         text_color=TEXT_DIM, justify="left").pack(padx=24, pady=(0, 24), anchor="w")
            ctk.CTkButton(card, text="Перейти →", command=cmd, fg_color=color,
                          hover_color=BG_CARD2, text_color="#000", height=42,
                          corner_radius=12, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(padx=24, pady=(0, 24), anchor="w")

    # ── WIZARD (Beginner Mode) ──
    def _show_wizard(self):
        c = self._clear_content()
        ctk.CTkLabel(c, text="🧙 Мастер оптимизации",
                     font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=ACCENT2).pack(anchor="w", pady=(10, 8))
        ctk.CTkLabel(c, text="Ответьте на вопросы — мы подберём настройки под вас",
                     font=ctk.CTkFont(family="Segoe UI", size=15), text_color=TEXT_DIM).pack(anchor="w", pady=(0, 32))

        self._wizard_answers = {}

        questions = [
            ("usage", "Для чего вы используете ПК?",
             [("🎮 Игры", "gaming"), ("💼 Работа", "work"), ("🌐 Сёрфинг", "casual"), ("🎬 Создание контента", "creative")]),
            ("level", "Ваш уровень?",
             [("🟢 Новичок", "beginner"), ("🟡 Средний", "medium"), ("🔴 Опытный", "advanced")]),
            ("risk", "Готовы к агрессивным настройкам?",
             [("✅ Да, макс. производительность", "aggressive"), ("⚠ Только безопасные", "safe")]),
        ]

        for qid, question, options in questions:
            frame = ctk.CTkFrame(c, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
            frame.pack(fill="x", pady=12)
            ctk.CTkLabel(frame, text=question, font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")).pack(padx=24, pady=(20, 12), anchor="w")
            var = ctk.StringVar(value=options[0][1])
            self._wizard_answers[qid] = var
            btn_row = ctk.CTkFrame(frame, fg_color="transparent")
            btn_row.pack(fill="x", padx=24, pady=(0, 20))
            for label, value in options:
                ctk.CTkRadioButton(btn_row, text=label, variable=var, value=value,
                                   font=ctk.CTkFont(family="Segoe UI", size=14), radiobutton_width=20, radiobutton_height=20, border_width_checked=6
                                   ).pack(side="left", padx=12)

        ctk.CTkButton(c, text="🚀 Применить рекомендации", command=self._run_wizard,
                      fg_color=ACCENT2, text_color="#fff", height=50, 
                      corner_radius=12, font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")).pack(pady=24, anchor="w")

        self._live_log = ctk.CTkTextbox(c, fg_color=BG_CARD, corner_radius=12, height=180, border_width=1, border_color=BORDER, font=ctk.CTkFont(family="Consolas", size=12), state="disabled")
        self._live_log.pack(fill="x", pady=4)

    def _run_wizard(self):
        usage = self._wizard_answers["usage"].get()
        risk = self._wizard_answers["risk"].get()
        max_risk = "red" if risk == "aggressive" else "blue"

        self._set_status("Wizard: применение...", YELLOW)
        allowed_risks = ["blue"] if max_risk == "blue" else ["blue", "yellow", "red"]

        def _do():
            all_keys = []
            actions_to_run = []

            for mod in ALL_MODULES:
                cat = mod.get_category(self.log_success, self.log_error, self.log_info)
                all_keys.extend(cat.get("tracked_keys", []))
                for (name, desc, action, icon, act_risk) in cat["actions"]:
                    if act_risk in allowed_risks:
                        # Filter by usage
                        mod_name = mod.__name__
                        if usage == "gaming" or mod_name not in ("modules.gaming",):
                            actions_to_run.append((name, action))
                        elif usage in ("work", "casual") and mod_name == "modules.gaming":
                            continue

            if all_keys:
                create_backup(all_keys, label="wizard")
                self.log_info("💾 Автоматический бэкап создан.")

            total = len(actions_to_run)
            for i, (name, action) in enumerate(actions_to_run, 1):
                self.log_info(f"[{i}/{total}] → {name}")
                try:
                    action()
                except Exception as e:
                    self.log_error(f"Ошибка: {e}")
                self.after(0, lambda p=i/total: self._set_status(f"Прогресс: {int(p*100)}%", YELLOW))

            self.log_success(f"✅ Wizard завершён! Применено {total} действий.")
            self.after(0, lambda: self._set_status("Wizard завершён!", GREEN))

        threading.Thread(target=_do, daemon=True).start()

    # ── ANALYSIS ──
    def _show_analysis(self):
        c = self._clear_content()
        ctk.CTkLabel(c, text="🔍 Анализ системы",
                     font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=ACCENT).pack(anchor="w", pady=(10, 8))
        ctk.CTkLabel(c, text="Глубокое сканирование: железо, службы, приватность, диски, сеть",
                     font=ctk.CTkFont(family="Segoe UI", size=15), text_color=TEXT_DIM).pack(anchor="w", pady=(0, 32))

        # Progress area (shown during scan)
        self._scan_progress_frame = ctk.CTkFrame(c, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
        self._scan_progress_frame.pack(fill="x", pady=8, padx=40)
        
        # Center the circular progress bar
        self._scan_progress_bar = CircularProgressbar(self._scan_progress_frame, size=180, thickness=16)
        self._scan_progress_bar.pack(pady=(32, 20))
        
        self._scan_stage_label = ctk.CTkLabel(
            self._scan_progress_frame, text="Нажмите 'Начать' для глубокого анализа...",
            font=ctk.CTkFont(family="Consolas", size=16), text_color=TEXT_DIM)
        self._scan_stage_label.pack(padx=20, pady=(0, 32))

        self._scan_btn = ctk.CTkButton(c, text="▶ Начать глубокий анализ", command=self._run_analysis,
                      fg_color=ACCENT, text_color="#000", height=50,
                      font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), corner_radius=12)
        self._scan_btn.pack(pady=24)

    def _run_analysis(self):
        self._scan_btn.configure(state="disabled", text="⏳ Сканирование...")
        self._scan_stage_label.configure(text="Запуск глубокого анализа...", text_color=YELLOW)
        self._scan_progress_bar.set(0)
        self._scan_progress_bar.pulse()
        self._set_status("Глубокий анализ...", YELLOW)
        self.update()

        def _progress_cb(stage_name, stage_num, total):
            self.after(0, lambda: self._scan_stage_label.configure(
                text=f"[{stage_num}/{total}] {stage_name}", text_color=ACCENT))
            self.after(0, lambda: self._scan_progress_bar.set(stage_num / total))
            self.after(0, lambda: self._set_status(f"Анализ: {stage_name}", YELLOW))

        def _do():
            try:
                info = analyze_system(progress_cb=_progress_cb)
                lines = format_analysis(info)
                self.after(0, lambda: self._display_analysis(info, lines))
            except Exception as e:
                self.after(0, lambda: self._scan_stage_label.configure(
                    text=f"Ошибка: {e}", text_color=RED))
        threading.Thread(target=_do, daemon=True).start()

    def _display_analysis(self, info, lines):
        # Recreate content as scrollable for results
        c = self._clear_content(scrollable=True)

        ctk.CTkLabel(c, text="🔍 Результаты глубокого анализа",
                     font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=ACCENT).pack(anchor="w", pady=(12, 16))

        # Color map for categories
        CAT_COLORS = {
            "header": ACCENT,
            "good": GREEN,
            "warn": YELLOW,
            "info": TEXT_DIM,
            "score": ACCENT2,
        }

        # Results card
        results_frame = ctk.CTkFrame(c, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
        results_frame.pack(fill="x", pady=12)
        for text, category in lines:
            if not text:
                ctk.CTkFrame(results_frame, fg_color=BORDER,
                             height=1).pack(fill="x", padx=24, pady=8)
                continue
            color = CAT_COLORS.get(category, TEXT_DIM)
            font_weight = "bold" if category == "header" else "normal"
            font_size = 15 if category == "header" else 14
            ctk.CTkLabel(results_frame, text=text,
                         font=ctk.CTkFont(family="Consolas", size=font_size, weight=font_weight),
                         text_color=color, anchor="w").pack(fill="x", padx=24, pady=2)

        # Scores
        scores_header = ctk.CTkFrame(c, fg_color="transparent")
        scores_header.pack(fill="x", pady=(24, 12))
        ctk.CTkLabel(scores_header, text="📊 Оценки системы",
                     font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=ACCENT).pack(side="left")
        ctk.CTkButton(scores_header, text="Сохранить отчёт", command=lambda: self._export_analysis(info, lines),
                      fg_color=BG_CARD2, text_color=ACCENT, height=32, corner_radius=8,
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side="right")
        scores = [
            ("Потенциал буста", info["boost_potential"], 30, GREEN),
            ("Оптимизация", info["optimization_score"], 100, ACCENT),
            ("Приватность", info["privacy_score"], 100, YELLOW if info["privacy_score"] < 60 else GREEN),
            ("Устойчивость", info["stability_score"], 100, ACCENT2),
        ]
        for name, val, mx, color in scores:
            row = ctk.CTkFrame(c, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text=f"{name}: {val}{'%' if mx==100 else f'/{mx}%'}",
                         font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"), text_color=color).pack(side="left", padx=20, pady=16)
            bar = ctk.CTkProgressBar(row, width=400, height=12, progress_color=color, fg_color=BG_CARD2)
            bar.set(val / mx)
            bar.pack(side="right", padx=20, pady=16)
        # Recommendations
        recs = []
        if info["services"]["DiagTrack"]["running"]:
            recs.append(("Отключить телеметрию", "DiagTrack / dmwappushservice запущены", self._show_expert))
        if info["services"]["SysMain"]["running"] or info["services"]["WSearch"]["running"]:
            recs.append(("Отключить тяжёлые службы", "SuperFetch / Search запущены", self._show_expert))
        if info["startup_count"] > 8:
            recs.append(("Очистить автозагрузку", f"{info['startup_count']} программ в автозагрузке", self._show_startup))
        if info["privacy_score"] < 60:
            recs.append(("Улучшить приватность", f"Оценка приватности {info['privacy_score']}%", self._show_expert))
        if info.get("visual_fx", 0) != 2:
            recs.append(("Упростить визуальные эффекты", "Включены лишние анимации", self._show_expert))
        if not info.get("game_dvr_off", False):
            recs.append(("Отключить Game Bar", "Оверлей Xbox активен", self._show_expert))
        if info["ram_usage_pct"] > 80:
            recs.append(("Высокая загрузка RAM", f"Используется {info['ram_usage_pct']}%", None))

        if recs:
            ctk.CTkLabel(c, text="⚡ Рекомендации",
                         font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=YELLOW).pack(anchor="w", pady=(24, 12))
            for title, desc, cmd in recs:
                row = ctk.CTkFrame(c, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
                row.pack(fill="x", pady=4)
                ctk.CTkLabel(row, text=title, font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                             text_color=ACCENT).pack(side="left", padx=20, pady=12)
                ctk.CTkLabel(row, text=desc, font=ctk.CTkFont(family="Segoe UI", size=13),
                             text_color=TEXT_DIM).pack(side="left", padx=8, pady=12)
                if cmd:
                    def _make_nav(c=cmd, idx=6 if cmd == self._show_startup else 3):
                        return lambda: (self._set_active_nav(idx), c())
                    ctk.CTkButton(row, text="Перейти →", command=_make_nav(),
                                  fg_color=BG_CARD2, text_color="#f8fafc", height=32,
                                  corner_radius=8, font=ctk.CTkFont(family="Segoe UI", size=13)).pack(side="right", padx=20, pady=12)

        self._set_status("✅ Глубокий анализ завершён", GREEN)

    # ── EXPERT MODE ──
    def _show_expert(self):
        c = self._clear_content(scrollable=True)
        ctk.CTkLabel(c, text="⚙️ Экспертный режим",
                     font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=ACCENT).pack(anchor="w", pady=(10, 8))
        ctk.CTkLabel(c, text="Выберите действия галочками и примените пакетно",
                     font=ctk.CTkFont(family="Segoe UI", size=15), text_color=TEXT_DIM).pack(anchor="w", pady=(0, 24))

        top = ctk.CTkFrame(c, fg_color="transparent")
        top.pack(fill="x", pady=(0, 16))
        self._expert_checks = []
        ctk.CTkButton(top, text="Применить выбранные", command=self._run_expert_selected,
                      fg_color=ACCENT, text_color="#000", height=42, corner_radius=12,
                      font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text="Снять все", command=self._uncheck_all_expert,
                      fg_color=BG_CARD2, text_color="#f8fafc", height=42, corner_radius=12,
                      font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(side="left", padx=(12, 0))
        ctk.CTkButton(top, text="↩ Отменить последнее", command=self._undo_last,
                      fg_color=BG_CARD2, text_color=YELLOW, height=42, corner_radius=12,
                      font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(side="left", padx=(12, 0))

        self._live_log = ctk.CTkTextbox(c, fg_color=BG_CARD, corner_radius=12, height=160, border_width=1, border_color=BORDER, font=ctk.CTkFont(family="Consolas", size=12), state="disabled")

        for mod in ALL_MODULES:
            cat = mod.get_category(self.log_success, self.log_error, self.log_info)
            section = ctk.CTkFrame(c, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
            section.pack(fill="x", pady=12)
            header = ctk.CTkFrame(section, fg_color="transparent")
            header.pack(fill="x", padx=24, pady=(24, 12))
            ctk.CTkLabel(header, text=cat["title"], font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")).pack(side="left")
            ctk.CTkLabel(header, text=cat["desc"], font=ctk.CTkFont(family="Segoe UI", size=14), text_color=TEXT_DIM).pack(side="left", padx=16)

            for (name, desc, action, icon, risk) in cat["actions"]:
                row = ctk.CTkFrame(section, fg_color="transparent")
                row.pack(fill="x", padx=24, pady=8)
                dot_color = RISK_COLORS.get(risk, ACCENT)
                ctk.CTkLabel(row, text="●", text_color=dot_color, font=ctk.CTkFont(size=16), width=24).pack(side="left", padx=(0, 12))
                ctk.CTkLabel(row, text=f"{icon} {name}", font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                             width=300, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=desc, font=ctk.CTkFont(family="Segoe UI", size=14), text_color=TEXT_DIM).pack(side="left", padx=16)

                var = ctk.BooleanVar(value=False)
                self._expert_checks.append((var, action, cat.get("tracked_keys", []), name))
                ctk.CTkCheckBox(row, text="", variable=var, width=24, checkbox_width=20, checkbox_height=20,
                                border_width=2, fg_color=ACCENT, hover_color=BG_CARD2).pack(side="right", padx=(0, 8))

        leg = ctk.CTkFrame(c, fg_color="transparent")
        leg.pack(fill="x", pady=12)
        for label, color in [("● Высокий", RED), ("● Средний", YELLOW), ("● Безопасный", ACCENT)]:
            ctk.CTkLabel(leg, text=label, text_color=color, font=ctk.CTkFont(family="Segoe UI", size=13)).pack(side="left", padx=12)

        ctk.CTkLabel(c, text="📋 Лог", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=ACCENT).pack(anchor="w", pady=(16, 8))
        self._live_log.pack(fill="x", pady=4)

    # ── QUICK OPTIMIZE ──
    def _quick_optimize(self):
        c = self._clear_content(scrollable=True)
        ctk.CTkLabel(c, text="⚡ Быстрая оптимизация",
                     font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=GREEN).pack(anchor="w", pady=(10, 8))
        ctk.CTkLabel(c, text="Только безопасные (синие) настройки",
                     font=ctk.CTkFont(family="Segoe UI", size=15), text_color=TEXT_DIM).pack(anchor="w", pady=(0, 24))

        progress = ctk.CTkProgressBar(c, height=12, progress_color=GREEN, fg_color=BG_CARD2)
        progress.set(0)
        progress.pack(fill="x", pady=8)

        self._live_log = ctk.CTkTextbox(c, fg_color=BG_CARD, corner_radius=12, height=300, border_width=1, border_color=BORDER, font=ctk.CTkFont(family="Consolas", size=12), state="disabled")
        self._live_log.pack(fill="both", expand=True, pady=16)

        def _do():
            all_keys = []
            safe_actions = []
            for mod in ALL_MODULES:
                cat = mod.get_category(self.log_success, self.log_error, self.log_info)
                all_keys.extend(cat.get("tracked_keys", []))
                for (name, desc, action, icon, risk) in cat["actions"]:
                    if risk == "blue":
                        safe_actions.append((name, action))
            if all_keys:
                create_backup(all_keys, label="quick_optimize")
                self.log_info("💾 Бэкап создан.")
            total = len(safe_actions)
            for i, (name, action) in enumerate(safe_actions, 1):
                self.log_info(f"[{i}/{total}] → {name}")
                try:
                    action()
                except Exception as e:
                    self.log_error(f"Ошибка: {e}")
                self.after(0, lambda p=i/total: progress.set(p))
            self.log_success(f"✅ Завершено! Применено {total} действий.")
            self.after(0, lambda: self._set_status("Быстрая оптимизация завершена!", GREEN))

        threading.Thread(target=_do, daemon=True).start()

    # ── STARTUP ──
    def _show_startup(self):
        c = self._clear_content(scrollable=True)
        ctk.CTkLabel(c, text="Автозагрузка",
                     font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=ACCENT).pack(anchor="w", pady=(10, 8))
        ctk.CTkLabel(c, text="Управление программами, запускающимися при старте Windows",
                     font=ctk.CTkFont(family="Segoe UI", size=15), text_color=TEXT_DIM).pack(anchor="w", pady=(0, 24))

        top = ctk.CTkFrame(c, fg_color="transparent")
        top.pack(fill="x", pady=(0, 16))
        ctk.CTkButton(top, text="Отключить все безопасные", command=self._disable_all_safe_startup,
                      fg_color=GREEN, text_color="#000", height=38, corner_radius=12,
                      font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text="Обновить", command=self._show_startup,
                      fg_color=BG_CARD2, text_color="#f8fafc", height=38, corner_radius=12,
                      font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(side="left", padx=(12, 0))

        items_frame = ctk.CTkScrollableFrame(c, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
        items_frame.pack(fill="both", expand=True)

        items = scan_startup_items()
        if not items:
            ctk.CTkLabel(items_frame, text="Элементы автозагрузки не найдены.", text_color=TEXT_DIM,
                         font=ctk.CTkFont(family="Segoe UI", size=15)).pack(pady=40)
            return

        for item in items:
            row = ctk.CTkFrame(items_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)

            if item["critical"]:
                dot_color = RED
                status_text = "Критичный"
            elif item["safe_to_disable"]:
                dot_color = GREEN
                status_text = "Безопасно"
            else:
                dot_color = YELLOW
                status_text = "Внимание"

            ctk.CTkLabel(row, text="●", text_color=dot_color, font=ctk.CTkFont(size=14), width=20).pack(side="left")
            ctk.CTkLabel(row, text=item["name"], font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                         text_color="#f8fafc", width=200, anchor="w").pack(side="left", padx=(0, 12))
            ctk.CTkLabel(row, text=item["location"], font=ctk.CTkFont(family="Consolas", size=12),
                         text_color=TEXT_DIM, width=120).pack(side="left")
            ctk.CTkLabel(row, text=status_text, font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=dot_color).pack(side="left", padx=16)

            if item["safe_to_disable"] and not item["critical"]:
                def _make_disable(it=item):
                    return lambda: threading.Thread(
                        target=lambda: disable_startup_item(it, self.log_success, self.log_error, self.log_info),
                        daemon=True
                    ).start()
                ctk.CTkButton(row, text="Отключить", command=_make_disable(),
                              fg_color="transparent", border_width=1, border_color=BORDER,
                              hover_color=BG_CARD2, text_color="#fff", width=100, height=32,
                              corner_radius=8, font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="right")

    def _disable_all_safe_startup(self):
        def _do():
            from modules.startup import disable_all_safe
            disable_all_safe(self.log_success, self.log_error, self.log_info)
            self.after(0, self._show_startup)
        threading.Thread(target=_do, daemon=True).start()

    # ── BACKUPS ──
    def _show_backups(self):
        c = self._clear_content(scrollable=True)
        ctk.CTkLabel(c, text="💾 Бэкапы и восстановление",
                     font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color=ACCENT2).pack(anchor="w", pady=(10, 8))
        ctk.CTkLabel(c, text="Выберите бэкап для восстановления",
                     font=ctk.CTkFont(family="Segoe UI", size=15), text_color=TEXT_DIM).pack(anchor="w", pady=(0, 32))
        self._live_log = ctk.CTkTextbox(c, fg_color=BG_CARD, corner_radius=12, height=140, border_width=1, border_color=BORDER, font=ctk.CTkFont(family="Consolas", size=12), state="disabled")
        backups = list_backups()
        if not backups:
            ctk.CTkLabel(c, text="Нет доступных бэкапов.", text_color=TEXT_DIM,
                         font=ctk.CTkFont(family="Segoe UI", size=15)).pack(pady=40)
        else:
            for bk in backups:
                row = ctk.CTkFrame(c, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
                row.pack(fill="x", pady=6)
                ctk.CTkLabel(row, text=f"📁 {bk['label']}  |  {bk['timestamp']}  |  {bk['entries_count']} записей",
                             font=ctk.CTkFont(family="Segoe UI", size=14)).pack(side="left", padx=20, pady=16)
                def _make_restore(fp=bk["file"]):
                    def _do():
                        self.log_info(f"Восстановление из {fp}...")
                        n = restore_backup(fp, log_fn=self.log_info)
                        self.log_success(f"Восстановлено {n} записей.")
                    return lambda: threading.Thread(target=_do, daemon=True).start()
                ctk.CTkButton(row, text="↩ Восстановить", command=_make_restore(),
                              fg_color=ACCENT2, text_color="#fff", width=140, height=36,
                              corner_radius=12, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")).pack(side="right", padx=20, pady=16)
        ctk.CTkLabel(c, text="📋 Лог", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=ACCENT).pack(anchor="w", pady=(24, 8))
        self._live_log.pack(fill="x", pady=8)

    # ── LOG ──
    def _show_log(self):
        c = self._clear_content(scrollable=True)
        ctk.CTkLabel(c, text="📋 Полный лог", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
                     text_color=ACCENT).pack(anchor="w", pady=(10, 24))
        log_frame = ctk.CTkScrollableFrame(c, fg_color=BG_CARD, corner_radius=12, border_width=1, border_color=BORDER)
        log_frame.pack(fill="both", expand=True)
        if not self.log_lines:
            ctk.CTkLabel(log_frame, text="Лог пуст.", text_color=TEXT_DIM).pack(padx=24, pady=24)
        else:
            for line in self.log_lines:
                color = GREEN if "[OK]" in line else (RED if "[ERR]" in line else TEXT_DIM)
                ctk.CTkLabel(log_frame, text=line, font=ctk.CTkFont(family="Consolas", size=12),
                             text_color=color, anchor="w").pack(fill="x", padx=16, pady=2)


    def _uncheck_all_expert(self):
        for var, *_ in self._expert_checks:
            var.set(False)

    def _run_expert_selected(self):
        selected = [(a, tk, n) for var, a, tk, n in self._expert_checks if var.get()]
        if not selected:
            self.log_info("Ничего не выбрано.")
            return
        def _do():
            all_keys = []
            for a, tk, n in selected:
                all_keys.extend(tk)
            if all_keys:
                bp = create_backup(all_keys, label="expert_batch")
                self._last_backup = bp
                self.log_info("💾 Бэкап создан перед пакетным применением.")
            total = len(selected)
            for i, (a, tk, n) in enumerate(selected, 1):
                self.log_info(f"[{i}/{total}] → {n}")
                try:
                    a()
                except Exception as e:
                    self.log_error(f"Ошибка в {n}: {e}")
            self.log_success(f"✅ Пакетное применение завершено: {total} действий.")
            self.after(0, lambda: self._set_status("Готово", GREEN))
        threading.Thread(target=_do, daemon=True).start()

    def _undo_last(self):
        if not getattr(self, "_last_backup", None) or not os.path.isfile(self._last_backup):
            self.log_error("Нет бэкапа для отката.")
            return
        def _do():
            n = restore_backup(self._last_backup, log_fn=self.log_info)
            self.log_success(f"↩ Отменено: восстановлено {n} записей.")
        threading.Thread(target=_do, daemon=True).start()


    def _export_analysis(self, info, lines):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"WinBoost_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("========================================\n")
                f.write("   WinBoost — System Analysis Report\n")
                f.write("========================================\n\n")
                f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"OS: {info.get('os_name', 'N/A')}\n")
                f.write(f"CPU: {info.get('cpu_name', 'N/A')}\n")
                f.write(f"RAM: {info.get('ram_total_gb', 'N/A')} GB (used {info.get('ram_usage_pct', 'N/A')}%)\n\n")
                f.write("--- SCAN RESULTS ---\n")
                for text, _ in lines:
                    f.write(f"{text}\n")
                f.write("\n--- SCORES ---\n")
                f.write(f"Boost Potential: {info.get('boost_potential', 'N/A')}\n")
                f.write(f"Optimization:    {info.get('optimization_score', 'N/A')}\n")
                f.write(f"Privacy:         {info.get('privacy_score', 'N/A')}\n")
                f.write(f"Stability:       {info.get('stability_score', 'N/A')}\n")
                f.write("\n--- END ---\n")
            self.log_success(f"Отчёт сохранён: {path}")
        except Exception as e:
            self.log_error(f"Ошибка сохранения отчёта: {e}")


if __name__ == "__main__":
    elevate()
    app = WinBoostApp()
    app.mainloop()
