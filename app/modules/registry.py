"""
WinBoost — Registry helper utilities
Safe read/write with automatic backup support
"""
import winreg
import logging
from typing import Any, Optional
from contextlib import contextmanager

logger = logging.getLogger("winboost")

HIVE_MAP = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
}

@contextmanager
def open_reg_key(hive: int, path: str, access: int = winreg.KEY_SET_VALUE):
    """Context manager for safely opening and closing registry keys."""
    key = None
    try:
        key = winreg.CreateKeyEx(hive, path, 0, access)
        yield key
    finally:
        if key is not None:
            winreg.CloseKey(key)

def set_reg_value(
    hive: int,
    path: str,
    name: str,
    value: Any,
    reg_type: int = winreg.REG_DWORD,
) -> bool:
    """Set a registry value. Returns True on success."""
    try:
        with open_reg_key(hive, path) as key:
            winreg.SetValueEx(key, name, 0, reg_type, value)
        return True
    except OSError as e:
        logger.error(f"Registry write failed: {path}\\{name} — {e}")
        return False

def get_reg_value(
    hive: int,
    path: str,
    name: str,
    default: Any = None,
) -> Any:
    """Read a registry value. Returns default if key/value doesn't exist."""
    try:
        with open_reg_key(hive, path, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return value
    except (OSError, FileNotFoundError):
        return default

def set_multi_reg(hive: int, path: str, values: dict[str, tuple[int, Any]]) -> int:
    """Set multiple registry values at once. Returns count of successful writes."""
    count = 0
    try:
        with open_reg_key(hive, path) as key:
            for name, (reg_type, value) in values.items():
                try:
                    winreg.SetValueEx(key, name, 0, reg_type, value)
                    count += 1
                except OSError as e:
                    logger.error(f"Failed to set {name}: {e}")
    except OSError as e:
        logger.error(f"Cannot open key {path}: {e}")
    return count
