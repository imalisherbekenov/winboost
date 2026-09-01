"""
WinBoost — Updates & Tasks Optimizer
Control Windows Updates and Telemetry Scheduled Tasks.
"""
import winreg
from modules.registry import set_reg_value
from modules.winshell import run_cmd


TELEMETRY_TASKS = [
    r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser",
    r"\Microsoft\Windows\Application Experience\ProgramDataUpdater",
    r"\Microsoft\Windows\Application Experience\StartupAppTask",
    r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator",
    r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip",
    r"\Microsoft\Windows\Autochk\Proxy",
    r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector",
]

def disable_auto_drivers(log_success, log_error, log_info):
    """Disable automatic driver updates via Windows Update."""
    log_info("Отключение автоматической установки драйверов...")
    try:
        policy_ok = set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate",
            "ExcludeWUDriversInQualityUpdate", 1
        )
        search_ok = set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching",
            "SearchOrderConfig", 0
        )
        if policy_ok and search_ok:
            log_success("Автоматическая установка драйверов отключена.")
        else:
            log_error("Настройки автоустановки драйверов применены не полностью.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_telemetry_tasks(log_success, log_error, log_info):
    """Disable hidden telemetry and diagnostic tasks in Task Scheduler."""
    log_info("Отключение телеметрических задач...")
    count = 0
    for task in TELEMETRY_TASKS:
        ok, stdout, error = run_cmd(["schtasks", "/Change", "/TN", task, "/DISABLE"])
        if ok:
            count += 1
        else:
            reason = (error or stdout).strip() or "команда завершилась без описания"
            log_error(f"Не удалось отключить задачу {task}: {reason}")
    if count:
        log_success(f"Фактически отключено {count}/{len(TELEMETRY_TASKS)} задач телеметрии.")
    else:
        log_error("Не удалось отключить ни одной задачи телеметрии.")

def pause_updates(log_success, log_error, log_info):
    """Pause Windows Updates by setting a far date (registry tweak)."""
    log_info("Приостановка обновлений Windows...")
    try:
        # Set pause start time to a very long time ago or just set a flag
        # This is a complex area, simplified here
        changed = set_reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\WindowsUpdate\UX\Settings", "PauseUpdatesExpiryTime", "2099-12-31T23:59:59Z", winreg.REG_SZ)
        if changed:
            log_success("Обновления приостановлены до 2099 года.")
        else:
            log_error("Не удалось записать срок приостановки обновлений в реестр.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def get_category(log_success, log_error, log_info):
    return {
        "title": "🔄 Обновления и Задачи",
        "desc": "Контроль обновлений и фоновых задач",
        "actions": [
            {
                "name": "Отключить авто-драйверы",
                "desc": "Не обновлять драйверы через WU",
                "run": lambda: disable_auto_drivers(log_success, log_error, log_info),
                "icon": "stop",
                "risk": "yellow",
                "irreversible": False,
                "effects": {"registry": [
                    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate", "name": "ExcludeWUDriversInQualityUpdate"},
                    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching", "name": "SearchOrderConfig"},
                ]},
            },
            {"name": "Отключить задачи телеметрии", "desc": "Задачи Application Experience и CEIP", "run": lambda: disable_telemetry_tasks(log_success, log_error, log_info), "icon": "chart", "risk": "red", "irreversible": False, "effects": {"tasks": TELEMETRY_TASKS}},
            {"name": "Пауза обновлений", "desc": "Приостановить до 2099 года", "run": lambda: pause_updates(log_success, log_error, log_info), "icon": "pause", "risk": "yellow", "irreversible": False, "effects": {"registry": [{"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Microsoft\WindowsUpdate\UX\Settings", "name": "PauseUpdatesExpiryTime"}]}},
        ]
    }
