"""
WinBoost — System Optimization Module
Telemetry, services, power plan, visual effects, bloatware removal.
"""
import winreg
import re
from modules.debloater import remove_uwp_package
from modules.privacy import disable_telemetry
from modules.registry import set_reg_value
from modules.winshell import run_cmd


def _command_error(stdout: str, stderr: str) -> str:
    return (stderr or stdout).strip() or "команда завершилась с ошибкой без описания"

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
    removed_apps = 0
    removed_packages = 0
    for app in apps:
        before, after, error = remove_uwp_package(app)
        if error:
            log_error(f"{app}: {error}")
            continue
        if before == 0:
            log_info(f"{app}: пакет не установлен.")
            continue
        removed_for_app = max(0, before - after)
        if removed_for_app:
            removed_packages = removed_packages + removed_for_app
        if after:
            log_error(
                f"{app}: удалено пакетов: {removed_for_app}, осталось после удаления: {after}."
            )
        elif removed_for_app:
            removed_apps = removed_apps + 1
            log_success(f"{app}: полностью удалено пакетов: {removed_for_app}.")
    if removed_packages:
        log_success(
            f"Деблоат завершён. Фактически удалено пакетов: {removed_packages}; "
            f"полностью удалено приложений: {removed_apps}."
        )
    else:
        log_error("Деблоат не удалил ни одного приложения.")

def optimize_services(log_success, log_error, log_info):
    log_info("Отключение тяжёлых служб...")
    try:
        services = [
            ("Fax", "Факс"), ("SysMain", "SuperFetch"), ("WSearch", "Windows Search"),
            ("MapsBroker", "Загрузчик карт"), ("lfsvc", "Геолокация"),
        ]
        disabled_names = []
        for svc, name in services:
            config_ok, config_out, config_error = run_cmd(
                ["sc.exe", "config", svc, "start=", "disabled"]
            )
            stop_ok, stop_out, stop_error = run_cmd(["sc.exe", "stop", svc])
            if config_ok and stop_ok:
                disabled_names.append(name)
            else:
                reasons = []
                if not config_ok:
                    reasons.append(f"config: {_command_error(config_out, config_error)}")
                if not stop_ok:
                    reasons.append(f"stop: {_command_error(stop_out, stop_error)}")
                log_error(f"Служба {name} ({svc}) не отключена: {'; '.join(reasons)}")
        if disabled_names:
            log_success(f"Фактически отключены службы: {', '.join(disabled_names)}")
        else:
            log_error("Не удалось отключить ни одной службы.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def enable_ultimate_performance(log_success, log_error, log_info):
    log_info("Активация 'Максимальная производительность'...")
    try:
        ok, stdout, error = run_cmd(
            ["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-aa00-03f14749eb61"]
        )
        match = re.search(r"([a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12})", stdout, re.I)
        if ok and match:
            active_ok, active_out, active_error = run_cmd(["powercfg", "-setactive", match.group(1)])
            if active_ok:
                log_success("План 'Максимальная производительность' активирован.")
            else:
                log_error(f"Не удалось активировать план: {_command_error(active_out, active_error)}")
        else:
            log_error(_command_error(stdout, error) if not ok else "Не удалось найти GUID (возможно не поддерживается ОС).")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_visual_effects(log_success, log_error, log_info):
    log_info("Отключение визуальных эффектов...")
    try:
        changed = set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
            "VisualFXSetting", 2
        )
        if changed:
            log_success("Визуальные эффекты переключены на 'Лучшее быстродействие'.")
        else:
            log_error("Не удалось записать настройку визуальных эффектов в реестр.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def get_category(log_success, log_error, log_info):
    return {
        "title": "⚙️ Оптимизация системы",
        "desc": "Телеметрия, службы, электропитание и деблоат",
        "actions": [
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
