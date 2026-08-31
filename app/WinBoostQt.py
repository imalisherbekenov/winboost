import sys
import os
import datetime
import threading
import ctypes
import psutil
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QFrame, QLabel, QPushButton, QStackedWidget, QScrollArea,
    QProgressBar, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QSizePolicy, QSpacerItem, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread, QSize, QRect
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QIcon

# Add modules path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules import ALL_MODULES
from modules.analyzer import analyze_system, format_analysis
from modules.backup import create_backup, restore_backup, list_backups
from modules.startup import scan_startup_items, disable_startup_item

# Constants
ACCENT = "#3B82F6"
ACCENT2 = "#8B5CF6"
GREEN = "#10B981"
YELLOW = "#F59E0B"
RED = "#EF4444"
BG_CARD = "#151A23"
TEXT_DIM = "#94A3B8"
BORDER = "#1E293B"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def elevate():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)

class Signals(QObject):
    log = Signal(str, str)  # msg, level
    status = Signal(str, str)  # msg, color
    progress = Signal(float)

class CircularProgressBar(QWidget):
    def __init__(self, size=200, thickness=15, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.value = 0
        self.thickness = thickness
        self.color = QColor(ACCENT)
        self.bg_color = QColor(BORDER)
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._update_pulse)
        self.pulse_angle = 90
        self.is_pulsing = False

    def set_value(self, val):
        self.is_pulsing = False
        self.pulse_timer.stop()
        self.value = max(0, min(100, val))
        self.update()

    def start_pulse(self):
        self.is_pulsing = True
        self.pulse_timer.start(30)

    def _update_pulse(self):
        self.pulse_angle = (self.pulse_angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        offset = self.thickness / 2 + 1
        rect = self.rect().adjusted(offset, offset, -offset, -offset)
        painter.setPen(QPen(self.bg_color, self.thickness, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, 0, 360 * 16)
        painter.setPen(QPen(self.color, self.thickness, Qt.SolidLine, Qt.RoundCap))
        if self.is_pulsing:
            painter.drawArc(rect, self.pulse_angle * 16, -60 * 16)
        else:
            span = -int(self.value * 3.6 * 16)
            painter.drawArc(rect, 90 * 16, span)
        if not self.is_pulsing:
            painter.setPen(QColor("#FFFFFF"))
            fs = int(self.width() * 0.22)
            painter.setFont(QFont("Segoe UI", fs, QFont.Bold))
            painter.drawText(self.rect(), Qt.AlignCenter, f"{int(self.value)}%")

class AnalysisWorker(QThread):
    progress = Signal(str, int, int)
    finished = Signal(dict, list)
    error = Signal(str)

    def run(self):
        try:
            def _cb(name, num, total):
                self.progress.emit(name, num, total)
            info = analyze_system(progress_cb=_cb)
            lines = format_analysis(info)
            self.finished.emit(info, lines)
        except Exception as e:
            self.error.emit(str(e))

class ActionWorker(QThread):
    log = Signal(str, str)
    status = Signal(str, str)
    finished = Signal(str)

    def __init__(self, actions, label="Action"):
        super().__init__()
        self.actions = actions
        self.label = label

    def run(self):
        total = len(self.actions)
        for i, (name, action) in enumerate(self.actions, 1):
            self.status.emit(f"{self.label}: {name} ({i}/{total})", YELLOW)
            self.log.emit(f"→ {name}", "dim")
            try:
                action()
            except Exception as e:
                self.log.emit(f"Ошибка в {name}: {e}", "err")
        self.finished.emit(f"✅ {self.label} завершён!")

class MonitorWorker(QThread):
    stats = Signal(dict)

    def run(self):
        while True:
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('C:').percent
                net = psutil.net_io_counters()
                self.stats.emit({
                    "cpu": cpu, "ram": ram, "disk": disk,
                    "net_sent": net.bytes_sent, "net_recv": net.bytes_recv
                })
            except Exception: pass
            self.msleep(500)

class WinBoostApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WinBoost 2.2 | PySide6 Edition")
        self.resize(1150, 820)
        self.setMinimumSize(1000, 750)
        self.signals = Signals()
        self.signals.log.connect(self._append_log)
        self.signals.status.connect(self._set_status)
        self._expert_checks = []
        self._wizard_vars = {}
        self._init_ui()
        self.monitor = MonitorWorker()
        self.monitor.stats.connect(self._update_monitor_ui)
        self.monitor.start()
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

    def _update_monitor_ui(self, data):
        if hasattr(self, 'cpu_bar'):
            self.cpu_bar.set_value(data['cpu'])
            self.ram_bar.set_value(data['ram'])
            self.disk_bar.set_value(data['disk'])
            sent = data['net_sent'] / (1024*1024)
            recv = data['net_recv'] / (1024*1024)
            self.net_label.setText(f"↑ {sent:.1f} MB  ↓ {recv:.1f} MB")

    def _init_ui(self):
        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget); self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = QFrame(); self.sidebar.setObjectName("sidebar"); self.sidebar.setFixedWidth(260); self.sidebar.setStyleSheet(f"background-color: {BG_CARD}; border-right: 1px solid {BORDER};")
        self.sidebar_layout = QVBoxLayout(self.sidebar); self.sidebar_layout.setContentsMargins(15, 40, 15, 20)
        self.logo = QLabel("WB."); self.logo.setStyleSheet(f"color: {ACCENT}; font-size: 32px; font-weight: bold; margin-left: 5px;"); self.sidebar_layout.addWidget(self.logo)
        self.sub_logo = QLabel("SYSTEM OPTIMIZER"); self.sub_logo.setStyleSheet(f"color: {TEXT_DIM}; font-size: 9px; font-weight: bold; letter-spacing: 1px; margin-left: 5px;"); self.sidebar_layout.addWidget(self.sub_logo)
        self.sidebar_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Fixed))
        self.nav_btns = []
        nav_items = [("🏠  Главная", 0), ("🧙  Мастер", 1), ("🔍  Анализ", 2), ("⚙️  Эксперт", 3), ("🚀  Автозагрузка", 4), ("💾  Бэкапы", 5), ("📋  Лог", 6)]
        for text, idx in nav_items:
            btn = QPushButton(text); btn.setObjectName("nav_btn"); btn.setCheckable(True); btn.setFixedHeight(45); btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("font-size: 13px; text-align: left; padding-left: 15px;")
            btn.clicked.connect(lambda checked=False, i=idx: self._nav_to(i))
            self.sidebar_layout.addWidget(btn); self.nav_btns.append(btn)
        self.nav_btns[0].setChecked(True); self.sidebar_layout.addStretch()
        
        self.theme_label = QLabel("Тема"); self.theme_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;"); self.sidebar_layout.addWidget(self.theme_label)
        self.theme_combo = QComboBox(); self.theme_combo.addItems(["Dark", "Light", "System"]); self.sidebar_layout.addWidget(self.theme_combo)
        self.main_layout.addWidget(self.sidebar)
        
        self.content_container = QWidget(); self.content_layout = QVBoxLayout(self.content_container); self.content_layout.setContentsMargins(0, 0, 0, 0); self.content_layout.setSpacing(0)
        self.stack = QStackedWidget(); self.content_layout.addWidget(self.stack)
        
        self.status_bar = QFrame(); self.status_bar.setFixedHeight(30); self.status_bar.setStyleSheet(f"background-color: #080D1A; border-top: 1px solid {BORDER};")
        self.status_layout = QHBoxLayout(self.status_bar); self.status_layout.setContentsMargins(15, 0, 15, 0)
        self.ver_label = QLabel("WinBoost 2.2"); self.ver_label.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-family: Consolas;"); self.status_layout.addWidget(self.ver_label)
        admin_text = "[ADMIN]" if is_admin() else "[NO ADMIN]"; admin_color = GREEN if is_admin() else YELLOW
        self.admin_label = QLabel(admin_text); self.admin_label.setStyleSheet(f"color: {admin_color}; font-weight: bold; font-family: Consolas;"); self.status_layout.addWidget(self.admin_label)
        self.status_layout.addStretch(); self.status_msg = QLabel("Готов"); self.status_msg.setStyleSheet(f"color: {TEXT_DIM}; font-family: Consolas;"); self.status_layout.addWidget(self.status_msg)
        self.clock_label = QLabel("--:--:--"); self.clock_label.setStyleSheet(f"color: {TEXT_DIM}; font-family: Consolas;"); self.status_layout.addWidget(self.clock_label)
        self.content_layout.addWidget(self.status_bar); self.main_layout.addWidget(self.content_container); self._init_pages()

    def _init_pages(self):
        self.page_home = QWidget(); self._build_home(self.page_home); self.stack.addWidget(self.page_home)
        self.page_wizard = QWidget(); self._build_wizard(self.page_wizard); self.stack.addWidget(self.page_wizard)
        self.page_analysis = QWidget(); self._build_analysis(self.page_analysis); self.stack.addWidget(self.page_analysis)
        self.page_expert = QWidget(); self._build_expert(self.page_expert); self.stack.addWidget(self.page_expert)
        self.page_startup = QWidget(); self._build_startup(self.page_startup); self.stack.addWidget(self.page_startup)
        self.page_backups = QWidget(); self._build_backups(self.page_backups); self.stack.addWidget(self.page_backups)
        self.page_log = QWidget(); self._build_log(self.page_log); self.stack.addWidget(self.page_log)

    def _build_home(self, page):
        layout = QVBoxLayout(page); layout.setContentsMargins(40, 40, 40, 40)
        header = QHBoxLayout(); title_vbox = QVBoxLayout()
        title = QLabel("Настройте Windows под себя"); title.setStyleSheet(f"color: {ACCENT}; font-size: 32px; font-weight: bold;")
        subtitle = QLabel("Пошаговый и безопасный способ улучшить производительность."); subtitle.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px;")
        title_vbox.addWidget(title); title_vbox.addWidget(subtitle); header.addLayout(title_vbox); header.addStretch()
        
        stats_panel = QFrame(); stats_panel.setStyleSheet(f"background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px;"); stats_panel.setFixedWidth(420); sp_layout = QHBoxLayout(stats_panel)
        def _mini_stat(label):
            vbox = QVBoxLayout(); lbl = QLabel(label); lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px; font-weight: bold; margin-bottom: 5px;")
            bar = CircularProgressBar(size=70, thickness=6)
            vbox.addWidget(lbl, 0, Qt.AlignCenter); vbox.addWidget(bar, 0, Qt.AlignCenter); return vbox, bar
        v_cpu, self.cpu_bar = _mini_stat("CPU"); v_ram, self.ram_bar = _mini_stat("RAM"); v_disk, self.disk_bar = _mini_stat("DISK")
        sp_layout.addLayout(v_cpu); sp_layout.addLayout(v_ram); sp_layout.addLayout(v_disk); header.addWidget(stats_panel); layout.addLayout(header)
        
        layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Fixed)); self.net_label = QLabel("Сеть: --"); self.net_label.setStyleSheet(f"color: {TEXT_DIM}; font-family: Consolas; font-size: 12px;"); layout.addWidget(self.net_label, 0, Qt.AlignRight); layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))
        
        grid = QHBoxLayout(); cards = [("🧙 Мастер", "Пошаговая настройка\nдля новичков", 1, ACCENT2), ("🔍 Анализ", "Проверить систему\nи получить оценку", 2, ACCENT), ("⚡ Быстрая", "Только безопасные\nнастройки", -1, GREEN), ("💾 Бэкапы", "Откатить изменения\nиз снимка", 5, YELLOW)]
        for name, desc, idx, color in cards:
            card = QFrame(); card.setCursor(Qt.PointingHandCursor); card.setStyleSheet(f"QFrame {{ background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; min-height: 180px; }} QFrame:hover {{ border-color: {color}; }}")
            clayout = QVBoxLayout(card); clayout.setContentsMargins(20, 20, 20, 20)
            cname = QLabel(name); cname.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold; border: none;"); clayout.addWidget(cname)
            cdesc = QLabel(desc); cdesc.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; border: none;"); cdesc.setWordWrap(True); clayout.addWidget(cdesc); clayout.addStretch()
            cbtn = QPushButton("Открыть →"); cbtn.setCursor(Qt.PointingHandCursor); cbtn.setStyleSheet(f"QPushButton {{ background-color: {color}; color: #000; font-weight: bold; border-radius: 8px; padding: 10px; }} QPushButton:hover {{ background-color: white; }}")
            if idx == 1: cbtn.clicked.connect(lambda: self._nav_to(1))
            elif idx == 2: cbtn.clicked.connect(lambda: self._nav_to(2))
            elif idx == 5: cbtn.clicked.connect(lambda: self._nav_to(5))
            else: cbtn.clicked.connect(self._quick_optimize)
            clayout.addWidget(cbtn); grid.addWidget(card)
        layout.addLayout(grid); layout.addStretch()

    def _build_wizard(self, page):
        layout = QVBoxLayout(page); layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel("🧙 Мастер оптимизации"); title.setStyleSheet(f"color: {ACCENT2}; font-size: 28px; font-weight: bold;"); layout.addWidget(title)
        subtitle = QLabel("Ответьте на вопросы — мы подберём настройки под вас"); subtitle.setStyleSheet(f"color: {TEXT_DIM}; font-size: 15px;"); layout.addWidget(subtitle)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame); scroll_content = QWidget(); scroll_layout = QVBoxLayout(scroll_content); scroll.setWidget(scroll_content)
        questions = [("usage", "Для чего вы используете ПК?", ["🎮 Игры", "💼 Работа", "🌐 Сёрфинг", "🎬 Создание контента"]), ("risk", "Готовы к агрессивным настройкам?", ["✅ Да, макс. производительность", "⚠ Только безопасные"])]
        for key, qtext, options in questions:
            qbox = QFrame(); qbox.setStyleSheet(f"background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; margin-bottom: 15px;"); qbox_layout = QVBoxLayout(qbox); qbox_layout.addWidget(QLabel(qtext))
            combo = QComboBox(); combo.addItems(options); qbox_layout.addWidget(combo); self._wizard_vars[key] = combo; scroll_layout.addWidget(qbox)
        layout.addWidget(scroll); run_btn = QPushButton("🚀 Применить рекомендации"); run_btn.setFixedHeight(50); run_btn.setStyleSheet(f"background-color: {ACCENT2}; color: white; font-weight: bold; border-radius: 12px;"); run_btn.clicked.connect(self._run_wizard); layout.addWidget(run_btn)

    def _build_analysis(self, page):
        layout = QVBoxLayout(page); layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel("🔍 Анализ системы"); title.setStyleSheet(f"color: {ACCENT}; font-size: 28px; font-weight: bold;"); layout.addWidget(title)
        subtitle = QLabel("Глубокое сканирование: железо, службы, приватность, диски, сеть"); subtitle.setStyleSheet(f"color: {TEXT_DIM}; font-size: 15px;"); layout.addWidget(subtitle)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Fixed))
        self.analysis_frame = QFrame(); self.analysis_frame.setStyleSheet(f"background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px;"); af_layout = QVBoxLayout(self.analysis_frame); af_layout.setAlignment(Qt.AlignCenter); af_layout.setContentsMargins(30, 30, 30, 30)
        self.progress_circle = CircularProgressBar(size=220); af_layout.addWidget(self.progress_circle)
        self.stage_label = QLabel("Нажмите 'Начать' для глубокого анализа..."); self.stage_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 16px; margin-top: 20px;"); af_layout.addWidget(self.stage_label, 0, Qt.AlignCenter)
        layout.addWidget(self.analysis_frame); self.start_scan_btn = QPushButton("▶ Начать глубокий анализ"); self.start_scan_btn.setFixedHeight(55); self.start_scan_btn.setStyleSheet(f"QPushButton {{ background-color: {ACCENT}; color: #000; font-size: 18px; font-weight: bold; border-radius: 12px; margin: 20px 0; }} QPushButton:hover {{ background-color: white; }}"); self.start_scan_btn.clicked.connect(self._run_analysis); layout.addWidget(self.start_scan_btn); layout.addStretch()

    def _build_expert(self, page):
        layout = QVBoxLayout(page); layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel("⚙️ Экспертный режим"); title.setStyleSheet(f"color: {ACCENT}; font-size: 28px; font-weight: bold;"); layout.addWidget(title)
        subtitle = QLabel("Выберите нужные твики вручную. Все изменения создают точку восстановления."); subtitle.setStyleSheet(f"color: {TEXT_DIM}; font-size: 14px; margin-bottom: 20px;"); layout.addWidget(subtitle)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame); scroll_content = QWidget(); scroll_layout = QVBoxLayout(scroll_content); scroll.setWidget(scroll_content)
        
        # Custom Checkbox Style: Tik/Cross
        cb_style = f"""
            QCheckBox {{ color: white; font-size: 14px; font-weight: 500; spacing: 10px; }}
            QCheckBox::indicator {{ width: 22px; height: 22px; border-radius: 6px; border: 2px solid {BORDER}; background-color: {BG_CARD}; }}
            QCheckBox::indicator:unchecked {{ 
                image: none;
                background-color: {BG_CARD};
                border: 2px solid {RED};
            }}
            QCheckBox::indicator:unchecked:hover {{ background-color: #2D1A1A; }}
            QCheckBox::indicator:checked {{ 
                background-color: {GREEN};
                border: 2px solid {GREEN};
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjQiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
            }}
            QCheckBox::indicator:unchecked {{
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNFRjQ0NDQiIHN0cm9rZS13aWR0aD0iNCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48bGluZSB4MT0iMTgiIHkxPSI2IiB4Mj0iNiIgeTI9IjE4Ij48L2xpbmU+PGxpbmUgeDE9IjYiIHkxPSI2IiB4Mj0iMTgiIHkyPSIxOCI+PC9saW5lPjwvc3ZnPg==);
            }}
        """

        for mod in ALL_MODULES:
            try:
                cat = mod.get_category(self._log_ok, self._log_err, self._log_info)
                group = QFrame(); group.setStyleSheet(f"background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; margin-bottom: 20px;"); glayout = QVBoxLayout(group)
                hdr = QLabel(cat["title"]); hdr.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {ACCENT}; border: none; margin-bottom: 10px;"); glayout.addWidget(hdr)
                for name, desc, action, icon, risk in cat["actions"]:
                    row = QFrame(); row.setStyleSheet("border: none; background: transparent;"); row_layout = QHBoxLayout(row); row_layout.setContentsMargins(0, 5, 0, 5)
                    cb = QCheckBox(f"{icon} {name}"); cb.setStyleSheet(cb_style); cb.setToolTip(desc); row_layout.addWidget(cb)
                    desc_lbl = QLabel(desc); desc_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px; font-style: italic;"); row_layout.addWidget(desc_lbl, 1, Qt.AlignRight); glayout.addWidget(row); self._expert_checks.append((cb, action, name))
                scroll_layout.addWidget(group)
            except Exception as e: print(f"Error loading module {mod}: {e}")
        layout.addWidget(scroll); h = QHBoxLayout(); apply_btn = QPushButton("▶ Применить выбранные"); apply_btn.setFixedHeight(50); apply_btn.setStyleSheet(f"background-color: {ACCENT}; color: #000; font-weight: bold; border-radius: 12px; font-size: 16px;"); apply_btn.clicked.connect(self._run_expert); h.addWidget(apply_btn)
        undo_btn = QPushButton("↩ Отменить последнее"); undo_btn.setFixedHeight(50); undo_btn.setStyleSheet(f"background-color: {BG_CARD}; color: {YELLOW}; font-weight: bold; border-radius: 12px; font-size: 16px;"); undo_btn.clicked.connect(self._undo_last); h.addWidget(undo_btn); layout.addLayout(h)

    def _build_startup(self, page):
        layout = QVBoxLayout(page); layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel("🚀 Автозагрузка"); title.setStyleSheet(f"color: {ACCENT}; font-size: 28px; font-weight: bold;"); layout.addWidget(title)
        self.startup_table = QTableWidget(0, 4); self.startup_table.setHorizontalHeaderLabels(["Имя", "Путь", "Риск", "Действие"]); self.startup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); layout.addWidget(self.startup_table)
        refresh_btn = QPushButton("Обновить"); refresh_btn.clicked.connect(self._refresh_startup); layout.addWidget(refresh_btn); self._refresh_startup()

    def _build_backups(self, page):
        layout = QVBoxLayout(page); layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel("💾 Бэкапы"); title.setStyleSheet(f"color: {ACCENT2}; font-size: 28px; font-weight: bold;"); layout.addWidget(title)
        self.backup_list = QTableWidget(0, 3); self.backup_list.setHorizontalHeaderLabels(["Дата", "Метка", "Действие"]); self.backup_list.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); layout.addWidget(self.backup_list)
        refresh_btn = QPushButton("Обновить"); refresh_btn.clicked.connect(self._refresh_backups); layout.addWidget(refresh_btn); self._refresh_backups()

    def _build_log(self, page):
        layout = QVBoxLayout(page); layout.setContentsMargins(40, 40, 40, 40)
        title = QLabel("📋 Полный лог"); title.setStyleSheet(f"color: {ACCENT}; font-size: 28px; font-weight: bold;"); layout.addWidget(title)
        self.log_view = QTextEdit(); self.log_view.setReadOnly(True); self.log_view.setStyleSheet(f"QTextEdit {{ background-color: {BG_CARD}; border: 1px solid {BORDER}; border-radius: 12px; color: {TEXT_DIM}; font-family: 'Consolas'; font-size: 13px; padding: 15px; }}"); layout.addWidget(self.log_view)
        btn_layout = QHBoxLayout(); clear_btn = QPushButton("Очистить"); clear_btn.clicked.connect(self.log_view.clear); btn_layout.addWidget(clear_btn); btn_layout.addStretch(); layout.addLayout(btn_layout)

    def _nav_to(self, idx):
        for i, btn in enumerate(self.nav_btns): btn.setChecked(i == idx)
        self.stack.setCurrentIndex(idx)

    def _update_clock(self): self.clock_label.setText(datetime.datetime.now().strftime("%H:%M:%S"))
    def _set_status(self, msg, color=TEXT_DIM): self.status_msg.setText(msg); self.status_msg.setStyleSheet(f"color: {color}; font-family: Consolas;")
    def _log_ok(self, m): self.signals.log.emit(m, "ok")
    def _log_err(self, m): self.signals.log.emit(m, "err")
    def _log_info(self, m): self.signals.log.emit(m, "dim")
    def _append_log(self, msg, level="info"):
        color = "#FFFFFF"
        if level == "ok": color = GREEN
        elif level == "err": color = RED
        elif level == "dim": color = TEXT_DIM
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_view.append(f"<font color='{TEXT_DIM}'>[{ts}]</font> <font color='{color}'>{msg}</font>")

    def _run_analysis(self):
        self.start_scan_btn.setEnabled(False); self.progress_circle.start_pulse()
        self.worker = AnalysisWorker(); self.worker.progress.connect(lambda n, v, t: (self.stage_label.setText(f"[{v}/{t}] {n}"), self.progress_circle.set_value(v/t*100)))
        self.worker.finished.connect(self._analysis_done); self.worker.start()

    def _analysis_done(self, info, lines):
        self.progress_circle.set_value(100); self.start_scan_btn.setEnabled(True); self.start_scan_btn.setText("▶ Начать заново"); self._set_status("Анализ завершён", GREEN)
        results_page = QWidget(); results_layout = QVBoxLayout(results_page); results_layout.setContentsMargins(40, 40, 40, 40)
        hdr_layout = QHBoxLayout(); hdr = QLabel("🔍 Результаты анализа"); hdr.setStyleSheet(f"color: {ACCENT}; font-size: 28px; font-weight: bold;"); hdr_layout.addWidget(hdr); hdr_layout.addStretch()
        back_btn = QPushButton("← Назад"); back_btn.setFixedSize(100, 36); back_btn.setStyleSheet(f"background-color: {BG_CARD}; color: white; border-radius: 8px;"); back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2)); hdr_layout.addWidget(back_btn); results_layout.addLayout(hdr_layout)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame); scroll_content = QWidget(); scroll_layout = QVBoxLayout(scroll_content); scroll.setWidget(scroll_content)
        for text, category in lines:
            if not text: line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background-color: {BORDER}; margin: 10px 0;"); scroll_layout.addWidget(line); continue
            color = TEXT_DIM
            if category == "header": color = ACCENT
            elif category == "good": color = GREEN
            elif category == "warn": color = YELLOW
            elif category == "score": color = ACCENT2
            lbl = QLabel(text); lbl.setWordWrap(True); font_size = 15 if category == "header" else 13; lbl.setStyleSheet(f"color: {color}; font-family: 'Consolas'; font-size: {font_size}px;"); scroll_layout.addWidget(lbl)
        results_layout.addWidget(scroll); idx = self.stack.addWidget(results_page); self.stack.setCurrentIndex(idx)

    def _run_wizard(self):
        actions = []; usage = self._wizard_vars["usage"].currentText(); risk = "aggressive" if "Да" in self._wizard_vars["risk"].currentText() else "safe"
        tracked = []
        for mod in ALL_MODULES:
            try:
                cat = mod.get_category(self._log_ok, self._log_err, self._log_info)
                tracked.extend(cat.get("tracked_keys", []))
                for name, desc, action, icon, act_risk in cat["actions"]:
                    if risk == "safe" and act_risk != "blue": continue
                    actions.append((name, action))
            except Exception: pass
        if tracked: create_backup(tracked, label="wizard")
        self.action_worker = ActionWorker(actions, "Wizard"); self.action_worker.log.connect(self._append_log); self.action_worker.status.connect(self._set_status); self.action_worker.finished.connect(self._on_action_finished); self.action_worker.start()

    def _run_expert(self):
        selected = [(name, act) for cb, act, name in self._expert_checks if cb.isChecked()]
        if not selected: self._set_status("Ничего не выбрано", YELLOW); return
        create_backup([], label="expert_batch")
        self.action_worker = ActionWorker(selected, "Expert"); self.action_worker.log.connect(self._append_log); self.action_worker.status.connect(self._set_status); self.action_worker.finished.connect(self._on_action_finished); self.action_worker.start()

    def _on_action_finished(self, msg): self._set_status(msg, GREEN); self._refresh_backups()

    def _quick_optimize(self):
        actions = []
        for mod in ALL_MODULES:
            try:
                cat = mod.get_category(self._log_ok, self._log_err, self._log_info)
                for name, desc, action, icon, risk in cat["actions"]:
                    if risk == "blue": actions.append((name, action))
            except Exception: pass
        if not actions: self._set_status("Нет безопасных действий", YELLOW); return
        self.action_worker = ActionWorker(actions, "Quick"); self.action_worker.log.connect(self._append_log); self.action_worker.status.connect(self._set_status); self.action_worker.finished.connect(self._on_action_finished); self.action_worker.start()

    def _undo_last(self):
        backups = list_backups()
        if not backups: self._set_status("Нет бэкапов для отката", RED); return
        latest = backups[0]["file"]; self._log_info(f"Откат к {backups[0]['timestamp']}..."); threading.Thread(target=lambda: restore_backup(latest, self._log_info)).start()

    def _refresh_startup(self):
        try:
            items = scan_startup_items(); self.startup_table.setRowCount(len(items))
            for i, it in enumerate(items):
                self.startup_table.setItem(i, 0, QTableWidgetItem(it["name"])); self.startup_table.setItem(i, 1, QTableWidgetItem(it["location"])); self.startup_table.setItem(i, 2, QTableWidgetItem("Безопасно" if it["safe_to_disable"] else "Внимание"))
                btn = QPushButton("Отключить"); btn.clicked.connect(lambda _, item=it: threading.Thread(target=lambda: disable_startup_item(item, self._log_ok, self._log_err, self._log_info)).start()); self.startup_table.setCellWidget(i, 3, btn)
        except Exception: pass

    def _refresh_backups(self):
        try:
            backups = list_backups(); self.backup_list.setRowCount(len(backups))
            for i, bk in enumerate(backups):
                self.backup_list.setItem(i, 0, QTableWidgetItem(bk["timestamp"])); self.backup_list.setItem(i, 1, QTableWidgetItem(bk["label"]))
                btn = QPushButton("Восстановить"); btn.clicked.connect(lambda _, fp=bk["file"]: threading.Thread(target=lambda: restore_backup(fp, self._log_info)).start()); self.backup_list.setCellWidget(i, 2, btn)
        except Exception: pass

if __name__ == "__main__":
    elevate()
    app = QApplication(sys.argv)
    app.setStyleSheet(f"QMainWindow {{ background-color: #0B0E14; }} #nav_btn {{ text-align: left; padding-left: 15px; border: none; border-radius: 8px; color: #F8FAFC; font-weight: bold; margin: 2px 0; }} #nav_btn:checked {{ background-color: {BG_CARD}; color: {ACCENT}; }} #nav_btn:hover {{ background-color: {BORDER}; }}")
    try:
        from qt_material import apply_stylesheet
        apply_stylesheet(app, theme='dark_blue.xml')
    except ImportError: pass
    window = WinBoostApp(); window.show(); sys.exit(app.exec())
