"""WinBoost GUI v2.2 — Dear PyGui"""
import dearpygui.dearpygui as dpg
import threading, ctypes, sys, os, datetime, time, tkinter.filedialog as filedialog
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from modules import ALL_MODULES
from modules.analyzer import analyze_system, format_analysis
from modules.backup import create_backup, restore_backup, list_backups
from modules.startup import scan_startup_items, disable_startup_item

ACCENT  = (59, 130, 246, 255)
ACCENT2 = (139, 92, 246, 255)
GREEN   = (16, 185, 129, 255)
YELLOW  = (245, 158, 11, 255)
RED     = (239, 68, 68, 255)

PALETTE = {
    "dark":  {"bg":(11,14,20,255),"card":(21,26,35,255),"card2":(31,38,51,255),"text":(248,250,252,255),"dim":(148,163,184,255),"border":(30,41,59,255)},
    "light": {"bg":(245,247,250,255),"card":(255,255,255,255),"card2":(226,232,240,255),"text":(15,23,42,255),"dim":(100,116,139,255),"border":(203,213,225,255)},
}

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()!=0
    except: return False

def elevate():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None,"runas",sys.executable," ".join(sys.argv),None,1)
        sys.exit(0)

def _build_theme(p):
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, p["bg"])
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, p["card"])
            dpg.add_theme_color(dpg.mvThemeCol_Button, p["card2"])
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, p["card2"])
            dpg.add_theme_color(dpg.mvThemeCol_Text, p["text"])
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled, p["dim"])
            dpg.add_theme_color(dpg.mvThemeCol_Border, p["border"])
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, p["card"])
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, p["card"])
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
    return theme

def _apply_theme(name):
    dpg.bind_theme(_build_theme(PALETTE[name]))
    dpg.configure_item("main_win", label=f"WinBoost 2.1  |  {name.upper()}")

class WinBoostApp:
    def __init__(self):
        self._log_lines=[];self._last_backup=None;self._expert_checks=[];self._startup_items=[]
        self._analysis_info={};self._analysis_lines=[];self._queue=[]
    def log_success(self,msg):self._log("[OK] "+msg,"green")
    def log_error(self,msg):self._log("[ERR] "+msg,"red")
    def log_info(self,msg):self._log("[INFO] "+msg,"dim")
    def _log(self,raw,ck):
        ts=datetime.datetime.now().strftime("%H:%M:%S")
        self._log_lines.append((f"{ts}  {raw}",ck))
        if len(self._log_lines)>500:self._log_lines=self._log_lines[-500:]
        self._refresh_log()
    def _refresh_log(self):
        if not dpg.does_item_exist("log_text"):return
        txt="\n".join(l for l,_ in self._log_lines)
        dpg.set_value("log_text",txt)
        dpg.configure_item("log_text",tracked=True)
        dpg.set_yscroll("log_text",99999)

    def _show(self,page):
        self._active_page=page
        for p in ["home","wizard","analysis","expert","startup","backups","log"]:
            dpg.configure_item(f"page_{p}",show=(p==page))
    def _nav_btn(self,label,page,parent):
        def cb():self._show(page)
        dpg.add_button(label=label,callback=cb,parent=parent,width=-1,height=36)
    def _build(self):
        dpg.create_context()
        _apply_theme("dark")
        with dpg.window(tag="main_win",label="WinBoost 2.1",width=1100,height=780,no_close=True,no_resize=False):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=240,height=-1) as sb:
                    dpg.add_text("W B .",color=ACCENT)
                    dpg.add_text("SYSTEM OPTIMIZER",color=PALETTE["dark"]["dim"])
                    dpg.add_spacer(height=20)
                    self._nav_btn("  Главная","home",sb)
                    self._nav_btn("  Мастер","wizard",sb)
                    self._nav_btn("  Анализ","analysis",sb)
                    self._nav_btn("  Эксперт","expert",sb)
                    self._nav_btn("  Автозагрузка","startup",sb)
                    self._nav_btn("  Бэкапы","backups",sb)
                    self._nav_btn("  Лог","log",sb)
                    dpg.add_spacer(height=20)
                    dpg.add_text("Тема",color=PALETTE["dark"]["dim"])
                    dpg.add_combo(["Dark","Light","System"],default_value="Dark",callback=lambda s,a,u:_apply_theme(a.lower() if a!="System" else "dark"),width=-1,parent=sb)
                with dpg.child_window(tag="content",width=-1,height=-1):
                    self._build_home()
                    self._build_wizard()
                    self._build_analysis()
                    self._build_expert()
                    self._build_startup()
                    self._build_backups()
                    self._build_log()
        dpg.create_viewport(title="WinBoost 2.1",width=1100,height=780)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        self._show("home")
        dpg.start_dearpygui()
        dpg.destroy_context()

