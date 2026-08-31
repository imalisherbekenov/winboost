"""
WinBoost — System Optimization Module
Telemetry, services, power plan, visual effects, bloatware removal.
"""
import winreg
import subprocess
import re
from modules.registry import set_reg_value

def disable_telemetry(log_success, log_error, log_info):
    log_info("Отключение телеметрии Microsoft...")
    try:
        for svc in ("DiagTrack", "dmwappushservice"):
            subprocess.run(["sc", "config", svc, "start=", "disabled"], capture_output=True)
            subprocess.run(["sc", "stop", svc], capture_output=True)
        set_reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0)
        log_success("Телеметрия отключена.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def remove_bloatware(log_success, log_error, log_info):
    log_info("Удаление мусорных UWP-приложений...")
    apps = [
        "Microsoft.BingWeather", "Microsoft.GetHelp", "Microsoft.Getstarted",
        "Microsoft.Messaging", "Microsoft.Microsoft3DViewer",
        "Microsoft.MicrosoftOfficeHub", "Microsoft.MicrosoftSolitaireCollection",
        "Microsoft.MixedReality.Portal", "Microsoft.OneConnect", "Microsoft.People",
        "Microsoft.Print3D", "Microsoft.SkypeApp", "Microsoft.WindowsFeedbackHub",
        "Microsoft.ZuneVideo", "Microsoft.ZuneMusic",
        "king.com.CandyCrushSaga", "king.com.CandyCrushSodaSaga",
        "Microsoft.Xbox.TCUI", "Microsoft.XboxGameOverlay",
    ]
    removed = 0
    for app in apps:
        subprocess.run(
            ["PowerShell", "-NoProfile", "-Command",
             f"Get-AppxPackage -Name '*{app}*' -AllUsers -ErrorAction SilentlyContinue | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue"],
            capture_output=True,
        )
        removed += 1
    log_success(f"Деблоат завершён. Обработано: {removed} приложений.")

def optimize_services(log_success, log_error, log_info):
    log_info("Отключение тяжёлых служб...")
    try:
        services = [
            ("Fax", "Факс"), ("SysMain", "SuperFetch"), ("WSearch", "Windows Search"),
            ("MapsBroker", "Загрузчик карт"), ("lfsvc", "Геолокация"),
        ]
        for svc, name in services:
            subprocess.run(["sc", "config", svc, "start=", "disabled"], capture_output=True)
            subprocess.run(["sc", "stop", svc], capture_output=True)
        names = ", ".join(n for _, n in services)
        log_success(f"Отключены: {names}")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def enable_ultimate_performance(log_success, log_error, log_info):
    log_info("Активация 'Максимальная производительность'...")
    try:
        result = subprocess.run(
            ["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-aa00-03f14749eb61"],
            capture_output=True, text=True,
        )
        match = re.search(r"([a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12})", result.stdout)
        if match:
            subprocess.run(["powercfg", "-setactive", match.group(1)], capture_output=True)
            log_success("План 'Максимальная производительность' активирован.")
        else:
            log_error("Не удалось найти GUID (возможно не поддерживается ОС).")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_visual_effects(log_success, log_error, log_info):
    log_info("Отключение визуальных эффектов...")
    try:
        set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
            "VisualFXSetting", 2
        )
        log_success("Визуальные эффекты переключены на 'Лучшее быстродействие'.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

TRACKED_KEYS = [
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "name": "AllowTelemetry"},
    {"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "name": "VisualFXSetting"},
]

def get_category(log_success, log_error, log_info):
    return {
        "title": "⚙️ Оптимизация системы",
        "desc": "Телеметрия, службы, электропитание и деблоат",
        "tracked_keys": TRACKED_KEYS,
        "actions": [
            ("Отключить телеметрию", "DiagTrack и сбор данных", lambda: disable_telemetry(log_success, log_error, log_info), "🛡️", "red"),
            ("Деблоат UWP", "Удалить ~18 мусорных приложений", lambda: remove_bloatware(log_success, log_error, log_info), "🧨", "red"),
            ("Отключить тяжёлые службы", "SysMain, WSearch, Fax, Геолокация", lambda: optimize_services(log_success, log_error, log_info), "⏹️", "yellow"),
            ("Макс. производительность", "Скрытый план электропитания", lambda: enable_ultimate_performance(log_success, log_error, log_info), "⚡", "blue"),
            ("Отключить визуальные эффекты", "Тени, анимации, прозрачность", lambda: disable_visual_effects(log_success, log_error, log_info), "🖥️", "blue"),
        ],
    }
