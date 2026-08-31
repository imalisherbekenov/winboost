"""
WinBoost — System Optimization Module
Telemetry, services, power plan, visual effects, bloatware removal.
"""
import winreg
import re
from modules.privacy import disable_telemetry
from modules.registry import set_reg_value
from modules.winshell import run_cmd, run_ps

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
        run_ps(
            f"Get-AppxPackage -Name '*{app}*' -AllUsers -ErrorAction SilentlyContinue | "
            "Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue"
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
            run_cmd(["sc.exe", "config", svc, "start=", "disabled"])
            run_cmd(["sc.exe", "stop", svc])
        names = ", ".join(n for _, n in services)
        log_success(f"Отключены: {names}")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def enable_ultimate_performance(log_success, log_error, log_info):
    log_info("Активация 'Максимальная производительность'...")
    try:
        ok, stdout, error = run_cmd(
            ["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-aa00-03f14749eb61"]
        )
        match = re.search(r"([a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12})", stdout, re.I)
        if match:
            run_cmd(["powercfg", "-setactive", match.group(1)])
            log_success("План 'Максимальная производительность' активирован.")
        else:
            log_error(error.strip() or "Не удалось найти GUID (возможно не поддерживается ОС).")
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

def get_category(log_success, log_error, log_info):
    return {
        "title": "⚙️ Оптимизация системы",
        "desc": "Телеметрия, службы, электропитание и деблоат",
        "actions": [
            {
                "name": "Отключить телеметрию",
                "desc": "DiagTrack и сбор данных",
                "run": lambda: disable_telemetry(log_success, log_error, log_info),
                "icon": "🛡️",
                "risk": "red",
                "irreversible": False,
                "effects": {
                    "registry": [{"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "name": "AllowTelemetry"}],
                    "services": ["DiagTrack", "dmwappushservice"],
                },
            },
            {
                "name": "Деблоат UWP",
                "desc": "Удалить ~18 мусорных приложений",
                "run": lambda: remove_bloatware(log_success, log_error, log_info),
                "icon": "🧨",
                "risk": "red",
                "irreversible": True,
                "effects": {"appx": [
                    "Microsoft.BingWeather", "Microsoft.GetHelp", "Microsoft.Getstarted",
                    "Microsoft.Messaging", "Microsoft.Microsoft3DViewer", "Microsoft.MicrosoftOfficeHub",
                    "Microsoft.MicrosoftSolitaireCollection", "Microsoft.MixedReality.Portal",
                    "Microsoft.OneConnect", "Microsoft.People", "Microsoft.Print3D", "Microsoft.SkypeApp",
                    "Microsoft.WindowsFeedbackHub", "Microsoft.ZuneVideo", "Microsoft.ZuneMusic",
                    "king.com.CandyCrushSaga", "king.com.CandyCrushSodaSaga", "Microsoft.Xbox.TCUI",
                    "Microsoft.XboxGameOverlay",
                ]},
            },
            {
                "name": "Отключить тяжёлые службы",
                "desc": "SysMain, WSearch, Fax, Геолокация",
                "run": lambda: optimize_services(log_success, log_error, log_info),
                "icon": "⏹️",
                "risk": "yellow",
                "irreversible": False,
                "effects": {"services": ["Fax", "SysMain", "WSearch", "MapsBroker", "lfsvc"]},
            },
            {
                "name": "Макс. производительность",
                "desc": "Скрытый план электропитания",
                "run": lambda: enable_ultimate_performance(log_success, log_error, log_info),
                "icon": "⚡",
                "risk": "blue",
                "irreversible": False,
                "effects": {"power": True},
            },
            {
                "name": "Отключить визуальные эффекты",
                "desc": "Тени, анимации, прозрачность",
                "run": lambda: disable_visual_effects(log_success, log_error, log_info),
                "icon": "🖥️",
                "risk": "blue",
                "irreversible": False,
                "effects": {"registry": [{"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "name": "VisualFXSetting"}]},
            },
        ],
    }
