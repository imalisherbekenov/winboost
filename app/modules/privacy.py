"""
WinBoost — Privacy Module
Cortana, Timeline, Advertising ID, Wi-Fi Sense, Location, Feedback, Telemetry
Reconstructed from original bytecode + enhanced with backup support.
"""
import winreg
from modules.backup import merge_effects
from modules.registry import set_reg_value, set_multi_reg
from modules.winshell import run_cmd


def _command_error(stdout: str, stderr: str) -> str:
    return (stderr or stdout).strip() or "команда завершилась с ошибкой без описания"

def disable_telemetry(log_success, log_error, log_info):
    """Disable Microsoft telemetry (DiagTrack, dmwappushservice, DataCollection)."""
    log_info("Отключение телеметрии Microsoft...")
    try:
        services_ok = True
        for svc in ("DiagTrack", "dmwappushservice"):
            config_ok, config_out, config_error = run_cmd(
                ["sc.exe", "config", svc, "start=", "disabled"]
            )
            stop_ok, stop_out, stop_error = run_cmd(["sc.exe", "stop", svc])
            if not config_ok:
                services_ok = False
                log_error(f"Не удалось отключить автозапуск {svc}: {_command_error(config_out, config_error)}")
            if not stop_ok:
                services_ok = False
                log_error(f"Не удалось остановить {svc}: {_command_error(stop_out, stop_error)}")

        registry_ok = set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
            "AllowTelemetry", 0
        )
        if not registry_ok:
            log_error("Не удалось записать политику телеметрии в реестр (требуются права администратора).")
        if services_ok and registry_ok:
            log_success("Телеметрия отключена.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_cortana(log_success, log_error, log_info):
    """Disable Cortana voice assistant."""
    log_info("Отключение Cortana...")
    try:
        changed = set_multi_reg(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
            {
                "AllowCortana": (winreg.REG_DWORD, 0),
                "AllowCortanaAboveLock": (winreg.REG_DWORD, 0),
                "AllowSearchToUseLocation": (winreg.REG_DWORD, 0),
            },
        )
        if changed == 3:
            log_success("Cortana отключена.")
        else:
            log_error(f"Настройки Cortana применены не полностью: {changed}/3.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_timeline(log_success, log_error, log_info):
    """Disable Timeline and Activity History."""
    log_info("Отключение Timeline и Activity History...")
    try:
        changed = set_multi_reg(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\System",
            {
                "EnableActivityFeed": (winreg.REG_DWORD, 0),
                "PublishUserActivities": (winreg.REG_DWORD, 0),
                "UploadUserActivities": (winreg.REG_DWORD, 0),
            },
        )
        if changed == 3:
            log_success("Timeline и Activity History отключены.")
        else:
            log_error(f"Настройки Timeline применены не полностью: {changed}/3.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_advertising_id(log_success, log_error, log_info):
    """Disable Advertising ID tracking."""
    log_info("Отключение Advertising ID...")
    try:
        user_ok = set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
            "Enabled", 0
        )
        policy_ok = set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo",
            "DisabledByGroupPolicy", 1
        )
        if user_ok and policy_ok:
            log_success("Advertising ID отключён.")
        else:
            log_error("Настройки Advertising ID применены не полностью.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_wifi_sense(log_success, log_error, log_info):
    """Disable Wi-Fi Sense auto-connect."""
    log_info("Отключение Wi-Fi Sense...")
    try:
        changed = set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\WcmSvc\wifinetworkmanager\config",
            "AutoConnectAllowedOEM", 0
        )
        if changed:
            log_success("Wi-Fi Sense отключён.")
        else:
            log_error("Не удалось записать настройку Wi-Fi Sense в реестр.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_location_tracking(log_success, log_error, log_info):
    """Disable Windows location tracking."""
    log_info("Отключение отслеживания местоположения...")
    try:
        changed = set_multi_reg(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors",
            {
                "DisableLocation": (winreg.REG_DWORD, 1),
                "DisableWindowsLocationProvider": (winreg.REG_DWORD, 1),
                "DisableLocationScripting": (winreg.REG_DWORD, 1),
            },
        )
        if changed == 3:
            log_success("Отслеживание местоположения отключено.")
        else:
            log_error(f"Настройки геолокации применены не полностью: {changed}/3.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_feedback(log_success, log_error, log_info):
    """Disable feedback prompts."""
    log_info("Отключение запросов обратной связи...")
    try:
        changed = set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Siuf\Rules",
            "NumberOfSIUFInPeriod", 0
        )
        if changed:
            log_success("Запросы обратной связи отключены.")
        else:
            log_error("Не удалось записать настройку Feedback в реестр.")
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
    log_info("Применение набора настроек приватности завершено; результаты указаны выше.")

TELEMETRY_EFFECTS = {
    "registry": [{"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "name": "AllowTelemetry"}],
    "services": ["DiagTrack", "dmwappushservice"],
}
CORTANA_EFFECTS = {"registry": [
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\Windows Search", "name": name}
    for name in ("AllowCortana", "AllowCortanaAboveLock", "AllowSearchToUseLocation")
]}
TIMELINE_EFFECTS = {"registry": [
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\System", "name": name}
    for name in ("EnableActivityFeed", "PublishUserActivities", "UploadUserActivities")
]}
ADVERTISING_EFFECTS = {"registry": [
    {"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "name": "Enabled"},
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo", "name": "DisabledByGroupPolicy"},
]}
WIFI_SENSE_EFFECTS = {"registry": [
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Microsoft\WcmSvc\wifinetworkmanager\config", "name": "AutoConnectAllowedOEM"}
]}
LOCATION_EFFECTS = {"registry": [
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors", "name": name}
    for name in ("DisableLocation", "DisableWindowsLocationProvider", "DisableLocationScripting")
]}
FEEDBACK_EFFECTS = {"registry": [
    {"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Siuf\Rules", "name": "NumberOfSIUFInPeriod"}
]}

def get_category(log_success, log_error, log_info):
    return {
        "title": "🔒 Приватность",
        "desc": "Защита личных данных и отключение слежки Windows",
        "actions": [
            {"name": "Отключить телеметрию", "desc": "DiagTrack, сбор данных", "run": lambda: disable_telemetry(log_success, log_error, log_info), "icon": "🛡️", "risk": "red", "irreversible": False, "effects": TELEMETRY_EFFECTS},
            {"name": "Отключить Cortana", "desc": "Голосовой помощник", "run": lambda: disable_cortana(log_success, log_error, log_info), "icon": "🤖", "risk": "yellow", "irreversible": False, "effects": CORTANA_EFFECTS},
            {"name": "Отключить Timeline", "desc": "История действий", "run": lambda: disable_timeline(log_success, log_error, log_info), "icon": "📋", "risk": "yellow", "irreversible": False, "effects": TIMELINE_EFFECTS},
            {"name": "Отключить Advertising ID", "desc": "Рекламный трекинг", "run": lambda: disable_advertising_id(log_success, log_error, log_info), "icon": "📡", "risk": "blue", "irreversible": False, "effects": ADVERTISING_EFFECTS},
            {"name": "Отключить Wi-Fi Sense", "desc": "Авто-подключение", "run": lambda: disable_wifi_sense(log_success, log_error, log_info), "icon": "📶", "risk": "blue", "irreversible": False, "effects": WIFI_SENSE_EFFECTS},
            {"name": "Отключить геолокацию", "desc": "Отслеживание местоположения", "run": lambda: disable_location_tracking(log_success, log_error, log_info), "icon": "📍", "risk": "yellow", "irreversible": False, "effects": LOCATION_EFFECTS},
            {"name": "Отключить Feedback", "desc": "Запросы обратной связи", "run": lambda: disable_feedback(log_success, log_error, log_info), "icon": "💬", "risk": "blue", "irreversible": False, "effects": FEEDBACK_EFFECTS},
            {
                "name": "🔒 Применить ВСЁ",
                "desc": "Все настройки приватности",
                "run": lambda: apply_all_privacy(log_success, log_error, log_info),
                "icon": "🔒",
                "risk": "red",
                "irreversible": False,
                "effects": merge_effects(TELEMETRY_EFFECTS, CORTANA_EFFECTS, TIMELINE_EFFECTS, ADVERTISING_EFFECTS, WIFI_SENSE_EFFECTS, LOCATION_EFFECTS, FEEDBACK_EFFECTS),
            },
        ],
    }
