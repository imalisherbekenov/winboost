"""
WinBoost — Privacy Module
Cortana, Timeline, Advertising ID, Wi-Fi Sense, Location, Feedback, Telemetry
Reconstructed from original bytecode + enhanced with backup support.
"""
import winreg
import subprocess
from modules.registry import set_reg_value, set_multi_reg

def disable_telemetry(log_success, log_error, log_info):
    """Disable Microsoft telemetry (DiagTrack, dmwappushservice, DataCollection)."""
    log_info("Отключение телеметрии Microsoft...")
    try:
        for svc in ("DiagTrack", "dmwappushservice"):
            subprocess.run(["sc", "config", svc, "start=", "disabled"], capture_output=True)
            subprocess.run(["sc", "stop", svc], capture_output=True)

        set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
            "AllowTelemetry", 0
        )
        log_success("Телеметрия отключена.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_cortana(log_success, log_error, log_info):
    """Disable Cortana voice assistant."""
    log_info("Отключение Cortana...")
    try:
        set_multi_reg(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
            {
                "AllowCortana": (winreg.REG_DWORD, 0),
                "AllowCortanaAboveLock": (winreg.REG_DWORD, 0),
                "AllowSearchToUseLocation": (winreg.REG_DWORD, 0),
            },
        )
        log_success("Cortana отключена.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_timeline(log_success, log_error, log_info):
    """Disable Timeline and Activity History."""
    log_info("Отключение Timeline и Activity History...")
    try:
        set_multi_reg(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\System",
            {
                "EnableActivityFeed": (winreg.REG_DWORD, 0),
                "PublishUserActivities": (winreg.REG_DWORD, 0),
                "UploadUserActivities": (winreg.REG_DWORD, 0),
            },
        )
        log_success("Timeline и Activity History отключены.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_advertising_id(log_success, log_error, log_info):
    """Disable Advertising ID tracking."""
    log_info("Отключение Advertising ID...")
    try:
        set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
            "Enabled", 0
        )
        set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo",
            "DisabledByGroupPolicy", 1
        )
        log_success("Advertising ID отключён.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_wifi_sense(log_success, log_error, log_info):
    """Disable Wi-Fi Sense auto-connect."""
    log_info("Отключение Wi-Fi Sense...")
    try:
        set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\WcmSvc\wifinetworkmanager\config",
            "AutoConnectAllowedOEM", 0
        )
        log_success("Wi-Fi Sense отключён.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_location_tracking(log_success, log_error, log_info):
    """Disable Windows location tracking."""
    log_info("Отключение отслеживания местоположения...")
    try:
        set_multi_reg(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors",
            {
                "DisableLocation": (winreg.REG_DWORD, 1),
                "DisableWindowsLocationProvider": (winreg.REG_DWORD, 1),
                "DisableLocationScripting": (winreg.REG_DWORD, 1),
            },
        )
        log_success("Отслеживание местоположения отключено.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_feedback(log_success, log_error, log_info):
    """Disable feedback prompts."""
    log_info("Отключение запросов обратной связи...")
    try:
        set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Siuf\Rules",
            "NumberOfSIUFInPeriod", 0
        )
        log_success("Запросы обратной связи отключены.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def apply_all_privacy(log_success, log_error, log_info):
    """Apply all privacy settings at once."""
    log_info("Применение всех настроек приватности...")
    disable_telemetry(log_success, log_error, log_info)
    disable_cortana(log_success, log_error, log_info)
    disable_timeline(log_success, log_error, log_info)
    disable_advertising_id(log_success, log_error, log_info)
    disable_wifi_sense(log_success, log_error, log_info)
    disable_location_tracking(log_success, log_error, log_info)
    disable_feedback(log_success, log_error, log_info)
    log_success("Все настройки приватности применены.")

# --- Registry keys that this module touches (for backup) ---
TRACKED_KEYS = [
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "name": "AllowTelemetry"},
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\Windows Search", "name": "AllowCortana"},
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\Windows Search", "name": "AllowCortanaAboveLock"},
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\System", "name": "EnableActivityFeed"},
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\System", "name": "PublishUserActivities"},
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\System", "name": "UploadUserActivities"},
    {"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "name": "Enabled"},
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo", "name": "DisabledByGroupPolicy"},
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Microsoft\WcmSvc\wifinetworkmanager\config", "name": "AutoConnectAllowedOEM"},
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", "name": "DisableLocation"},
    {"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Siuf\Rules", "name": "NumberOfSIUFInPeriod"},
]

def get_category(log_success, log_error, log_info):
    return {
        "title": "🔒 Приватность",
        "desc": "Защита личных данных и отключение слежки Windows",
        "tracked_keys": TRACKED_KEYS,
        "actions": [
            ("Отключить телеметрию", "DiagTrack, сбор данных", lambda: disable_telemetry(log_success, log_error, log_info), "🛡️", "red"),
            ("Отключить Cortana", "Голосовой помощник", lambda: disable_cortana(log_success, log_error, log_info), "🤖", "yellow"),
            ("Отключить Timeline", "История действий", lambda: disable_timeline(log_success, log_error, log_info), "📋", "yellow"),
            ("Отключить Advertising ID", "Рекламный трекинг", lambda: disable_advertising_id(log_success, log_error, log_info), "📡", "blue"),
            ("Отключить Wi-Fi Sense", "Авто-подключение", lambda: disable_wifi_sense(log_success, log_error, log_info), "📶", "blue"),
            ("Отключить геолокацию", "Отслеживание местоположения", lambda: disable_location_tracking(log_success, log_error, log_info), "📍", "yellow"),
            ("Отключить Feedback", "Запросы обратной связи", lambda: disable_feedback(log_success, log_error, log_info), "💬", "blue"),
            ("🔒 Применить ВСЁ", "Все настройки приватности", lambda: apply_all_privacy(log_success, log_error, log_info), "🔒", "red"),
        ],
    }
