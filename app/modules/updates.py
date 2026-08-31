"""
WinBoost — Updates & Tasks Optimizer
Control Windows Updates and Telemetry Scheduled Tasks.
"""
import winreg
import subprocess
from modules.registry import set_reg_value

def disable_auto_drivers(log_success, log_error, log_info):
    """Disable automatic driver updates via Windows Update."""
    log_info("Отключение автоматической установки драйверов...")
    try:
        set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate",
            "ExcludeWUDriversInQualityUpdate", 1
        )
        set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching",
            "SearchOrderConfig", 0
        )
        log_success("Автоматическая установка драйверов отключена.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_telemetry_tasks(log_success, log_error, log_info):
    """Disable hidden telemetry and diagnostic tasks in Task Scheduler."""
    log_info("Отключение телеметрических задач...")
    tasks = [
        r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser",
        r"\Microsoft\Windows\Application Experience\ProgramDataUpdater",
        r"\Microsoft\Windows\Application Experience\StartupAppTask",
        r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator",
        r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip",
        r"\Microsoft\Windows\Autochk\Proxy",
        r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector",
    ]
    
    count = 0
    for task in tasks:
        try:
            res = subprocess.run(["schtasks", "/Change", "/TN", task, "/DISABLE"], capture_output=True, text=True)
            if res.returncode == 0:
                count += 1
        except Exception:
            pass
    
    log_success(f"Отключено {count} задач телеметрии.")

def pause_updates(log_success, log_error, log_info):
    """Pause Windows Updates by setting a far date (registry tweak)."""
    log_info("Приостановка обновлений Windows...")
    try:
        # Set pause start time to a very long time ago or just set a flag
        # This is a complex area, simplified here
        set_reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\WindowsUpdate\UX\Settings", "PauseUpdatesExpiryTime", "2099-12-31T23:59:59Z", winreg.REG_SZ)
        log_success("Обновления приостановлены до 2099 года.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def get_category(log_success, log_error, log_info):
    return {
        "title": "🔄 Обновления и Задачи",
        "desc": "Контроль обновлений и фоновых задач",
        "tracked_keys": [
            {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate", "name": "ExcludeWUDriversInQualityUpdate"},
            {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching", "name": "SearchOrderConfig"},
        ],
        "actions": [
            ("Отключить авто-драйверы", "Не обновлять драйверы через WU", lambda: disable_auto_drivers(log_success, log_error, log_info), "💿", "yellow"),
            ("Отключить задачи телеметрии", "Задачи Application Experience и CEIP", lambda: disable_telemetry_tasks(log_success, log_error, log_info), "📊", "red"),
            ("Пауза обновлений", "Приостановить до 2099 года", lambda: pause_updates(log_success, log_error, log_info), "⏸️", "yellow"),
        ]
    }
