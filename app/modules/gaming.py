"""
WinBoost — Gaming Optimization Module
CPU priority, mouse acceleration, Nagle, Game Mode, Game Bar.
"""
import winreg
import os
from modules.registry import set_reg_value, set_multi_reg

def optimize_cpu_priority(log_success, log_error, log_info, game_exe="game.exe"):
    """Set CPU priority to High for a game executable."""
    log_info(f"Установка приоритета CPU для {game_exe}...")
    try:
        set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            rf"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\{game_exe}\PerfOptions",
            "CpuPriorityClass", 3
        )
        log_success(f"Приоритет CPU для {game_exe} — High.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_mouse_acceleration(log_success, log_error, log_info):
    """Disable mouse acceleration (enhance pointer precision)."""
    log_info("Отключение акселерации мыши...")
    try:
        set_multi_reg(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Mouse",
            {
                "MouseSpeed": (winreg.REG_SZ, "0"),
                "MouseThreshold1": (winreg.REG_SZ, "0"),
                "MouseThreshold2": (winreg.REG_SZ, "0"),
            },
        )
        log_success("Акселерация мыши отключена.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def optimize_nagle(log_success, log_error, log_info):
    """Disable Nagle's algorithm for lower network latency."""
    log_info("Отключение алгоритма Нейгла...")
    try:
        base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        key = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, base, 0, winreg.KEY_READ)
        i = 0
        while True:
            try:
                subkey_name = winreg.EnumKey(key, i)
                set_reg_value(winreg.HKEY_LOCAL_MACHINE, f"{base}\\{subkey_name}", "TcpAckFrequency", 1)
                set_reg_value(winreg.HKEY_LOCAL_MACHINE, f"{base}\\{subkey_name}", "TCPNoDelay", 1)
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
        log_success("Алгоритм Нейгла отключён (сетевая задержка снижена).")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def disable_game_bar(log_success, log_error, log_info):
    """Disable Xbox Game Bar and overlay."""
    log_info("Отключение Xbox Game Bar...")
    try:
        set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR",
            "AppCaptureEnabled", 0
        )
        set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"System\GameConfigStore",
            "GameDVR_Enabled", 0
        )
        log_success("Xbox Game Bar отключён.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def enable_game_mode(log_success, log_error, log_info):
    """Enable Windows Game Mode."""
    log_info("Включение Game Mode...")
    try:
        set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\GameBar",
            "AllowAutoGameMode", 1
        )
        set_reg_value(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\GameBar",
            "AutoGameModeEnabled", 1
        )
        log_success("Game Mode активирован.")
    except Exception as e:
        log_error(f"Ошибка: {e}")

TRACKED_KEYS = [
    {"hive": winreg.HKEY_CURRENT_USER, "path": r"Control Panel\Mouse", "name": "MouseSpeed"},
    {"hive": winreg.HKEY_CURRENT_USER, "path": r"Control Panel\Mouse", "name": "MouseThreshold1"},
    {"hive": winreg.HKEY_CURRENT_USER, "path": r"Control Panel\Mouse", "name": "MouseThreshold2"},
    {"hive": winreg.HKEY_CURRENT_USER, "path": r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR", "name": "AppCaptureEnabled"},
    {"hive": winreg.HKEY_CURRENT_USER, "path": r"System\GameConfigStore", "name": "GameDVR_Enabled"},
    {"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\GameBar", "name": "AllowAutoGameMode"},
]

def get_category(log_success, log_error, log_info):
    return {
        "title": "🎮 Игры",
        "desc": "Общая оптимизация для игр, сеть и ввод",
        "tracked_keys": TRACKED_KEYS,
        "actions": [
            ("Отключить акселерацию мыши", "Точный ввод без ускорения", lambda: disable_mouse_acceleration(log_success, log_error, log_info), "🖱️", "yellow"),
            ("Отключить Nagle", "Снижение сетевой задержки", lambda: optimize_nagle(log_success, log_error, log_info), "🌐", "yellow"),
            ("Отключить Game Bar", "Xbox Game Bar и оверлей", lambda: disable_game_bar(log_success, log_error, log_info), "🎮", "yellow"),
            ("Включить Game Mode", "Приоритет для игр", lambda: enable_game_mode(log_success, log_error, log_info), "🚀", "blue"),
        ],
    }
