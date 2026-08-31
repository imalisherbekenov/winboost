"""
WinBoost — Backup & Restore Engine
Creates registry snapshots before any changes, enables full rollback.
"""
import winreg
import json
import os
import datetime
import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger("winboost")

BACKUP_DIR = Path(os.environ.get("APPDATA", ".")) / "WinBoost" / "backups"

HIVE_NAMES = {
    winreg.HKEY_LOCAL_MACHINE: "HKLM",
    winreg.HKEY_CURRENT_USER: "HKCU",
}

def _ensure_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR

def read_current_value(hive: int, path: str, name: str):
    """Read current registry value, return None if doesn't exist."""
    try:
        key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ)
        value, reg_type = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return {"value": value, "type": reg_type, "exists": True}
    except FileNotFoundError:
        return {"value": None, "type": None, "exists": False}
    except OSError:
        return {"value": None, "type": None, "exists": False}

def create_backup(changes: list[dict], label: str = "manual") -> str:
    """
    Create a backup snapshot before applying changes.
    Each change: {"hive": int, "path": str, "name": str}
    Returns the backup file path.
    """
    _ensure_backup_dir()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"winboost_backup_{label}_{timestamp}.json"
    filepath = BACKUP_DIR / filename

    snapshot = {
        "timestamp": timestamp,
        "label": label,
        "entries": [],
    }

    for change in changes:
        hive = change["hive"]
        path = change["path"]
        name = change["name"]
        current = read_current_value(hive, path, name)
        snapshot["entries"].append({
            "hive": HIVE_NAMES.get(hive, str(hive)),
            "hive_int": hive,
            "path": path,
            "name": name,
            **current,
        })

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    logger.info(f"Backup saved: {filepath}")
    return str(filepath)

def restore_backup(filepath: str, log_fn: Callable | None = None) -> int:
    """Restore settings from a backup file. Returns count of restored values."""
    with open(filepath, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    restored = 0
    for entry in snapshot["entries"]:
        hive = entry["hive_int"]
        path = entry["path"]
        name = entry["name"]

        if not entry["exists"]:
            # Value didn't exist before — try to delete it
            try:
                key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, name)
                winreg.CloseKey(key)
                restored += 1
                if log_fn:
                    log_fn(f"Удалено: {path}\\{name}")
            except OSError:
                pass
        else:
            try:
                key = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, name, 0, entry["type"], entry["value"])
                winreg.CloseKey(key)
                restored += 1
                if log_fn:
                    log_fn(f"Восстановлено: {path}\\{name} = {entry['value']}")
            except OSError as e:
                if log_fn:
                    log_fn(f"Ошибка: {path}\\{name} — {e}")

    return restored

def list_backups() -> list[dict]:
    """List all available backup files."""
    _ensure_backup_dir()
    backups = []
    for f in sorted(BACKUP_DIR.glob("winboost_backup_*.json"), reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            backups.append({
                "file": str(f),
                "label": data.get("label", ""),
                "timestamp": data.get("timestamp", ""),
                "entries_count": len(data.get("entries", [])),
            })
        except Exception:
            pass
    return backups
