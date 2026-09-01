"""
WinBoost — Gaming Optimization Module
CPU priority, mouse acceleration, Nagle, Game Mode, Game Bar.
"""
import winreg
from modules.registry import set_reg_value, set_multi_reg

def disable_mouse_acceleration(log_success, log_error, log_info):
    """Disable mouse acceleration (enhance pointer precision)."""
    log_info("Отключение акселерации мыши...")
    try:
        changed = set_multi_reg(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Mouse",
            {
                "MouseSpeed": (winreg.REG_SZ, "0"),
                "MouseThreshold1": (winreg.REG_SZ, "0"),
                "MouseThreshold2": (winreg.REG_SZ, "0"),
            },
        )
        if changed == 3:
            log_success("Акселерация мыши отключена.")
        else:
            log_error(f"Настройки мыши применены не полностью: {changed}/3.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def optimize_nagle(log_success, log_error, log_info):
    """Disable Nagle's algorithm for lower network latency."""
    log_info("Отключение алгоритма Нейгла...")
    try:
        base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        key = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, base, 0, winreg.KEY_READ)
        i = 0
        changed = 0
        failed = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(key, i)
                ack_ok = set_reg_value(winreg.HKEY_LOCAL_MACHINE, f"{base}\\{subkey_name}", "TcpAckFrequency", 1)
                delay_ok = set_reg_value(winreg.HKEY_LOCAL_MACHINE, f"{base}\\{subkey_name}", "TCPNoDelay", 1)
                if ack_ok and delay_ok:
                    changed += 1
                else:
                    failed += 1
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
        if changed:
            log_success(f"Алгоритм Нейгла отключён на интерфейсах: {changed}.")
        if failed:
            log_error(f"Не удалось полностью настроить интерфейсов: {failed}.")
        if not changed:
            log_error("Не удалось настроить ни одного сетевого интерфейса.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_game_bar(log_success, log_error, log_info):
    """Disable Xbox Game Bar and overlay."""
    log_info("Отключение Xbox Game Bar...")
    try:
        capture_ok = set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR",
            "AppCaptureEnabled", 0
        )
        dvr_ok = set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"System\GameConfigStore",
            "GameDVR_Enabled", 0
        )
        if capture_ok and dvr_ok:
            log_success("Xbox Game Bar отключён.")
        else:
            log_error("Настройки Xbox Game Bar применены не полностью.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def enable_game_mode(log_success, log_error, log_info):
    """Enable Windows Game Mode."""
    log_info("Включение Game Mode...")
    try:
        allow_ok = set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\GameBar",
            "AllowAutoGameMode", 1
        )
        mode_ok = set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\GameBar",
            "AutoGameModeEnabled", 1
        )
        if allow_ok and mode_ok:
            log_success("Game Mode активирован.")
        else:
            log_error("Настройки Game Mode применены не полностью.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def get_category(log_success, log_error, log_info):
    return {
        "title": "🎮 Игры",
        "desc": "Общая оптимизация для игр, сеть и ввод",
        "actions": [
            {
                "name": "Отключить акселерацию мыши",
                "desc": "Точный ввод без ускорения",
                "run": lambda: disable_mouse_acceleration(log_success, log_error, log_info),
                "icon": "cursor",
                "risk": "yellow",
                "irreversible": False,
                "effects": {"registry": [
                    {"hive": winreg.HKEY_CURRENT_USER, "path": r"Control Panel\Mouse", "name": name}
                    for name in ("MouseSpeed", "MouseThreshold1", "MouseThreshold2")
                ]},
            },
            {
                "name": "Отключить Nagle",
                "desc": "Снижение сетевой задержки",
                "run": lambda: optimize_nagle(log_success, log_error, log_info),
                "icon": "globe",
                "risk": "yellow",
                "irreversible": False,
                "effects": {"registry": [{
                    "hive": winreg.HKEY_LOCAL_MACHINE,
                    "path": r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces",
                    "dynamic": "tcp_interfaces",
                    "names": ["TcpAckFrequency", "TCPNoDelay"],
                }]},
            },
            {
                "name": "Отключить Game Bar",
                "desc": "Xbox Game Bar и оверлей",
                "run": lambda: disable_game_bar(log_success, log_error, log_info),
                "icon": "gamepad",
                "risk": "yellow",
                "irreversible": False,
                "effects": {"registry": [
                    {"hive": winreg.HKEY_CURRENT_USER, "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR", "name": "AppCaptureEnabled"},
                    {"hive": winreg.HKEY_CURRENT_USER, "path": r"System\GameConfigStore", "name": "GameDVR_Enabled"},
                ]},
            },
            {
                "name": "Включить Game Mode",
                "desc": "Приоритет для игр",
                "run": lambda: enable_game_mode(log_success, log_error, log_info),
                "icon": "bolt",
                "risk": "blue",
                "irreversible": False,
                "effects": {"registry": [
                    {"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\GameBar", "name": name}
                    for name in ("AllowAutoGameMode", "AutoGameModeEnabled")
                ]},
            },
        ],
    }
