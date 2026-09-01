"""
WinBoost — Startup Manager Module
Scan, list, and disable unnecessary startup programs.
"""
import winreg
import base64
import json

from modules.winshell import run_cmd

# Registry locations where startup items live
STARTUP_LOCATIONS = [
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM Run"),
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU RunOnce"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM RunOnce"),
]

# Known safe-to-disable startup item names (case-insensitive exact match)
SAFE_TO_DISABLE = [
    "onedrive", "skype", "spotify", "discord", "steam", "epicgames",
    "teams", "zoom", "adobe", "creative cloud", "ccleaner", "itunes",
    "helperservice",
    "googleupdate", "microsoftedge", "msedge",
]

# NEVER disable these — critical system components
NEVER_DISABLE = [
    "securityhealth", "windows defender", "windowssecurity",
    "realtek", "nvidia", "amd", "intel", "ctfmon", "explorer",
    "igfx", "rthdvcpl",
]

DISABLED_STARTUP_PATH = r"Software\WinBoost\DisabledStartup"
_SAFE_NAMES = frozenset(name.casefold() for name in SAFE_TO_DISABLE)
_NEVER_MARKERS = tuple(name.casefold() for name in NEVER_DISABLE)


def _classification(name: str) -> tuple[bool, bool]:
    normalized = name.casefold()
    entry_name = normalized.rsplit("\\", 1)[-1]
    critical = any(marker in normalized for marker in _NEVER_MARKERS)
    return entry_name in _SAFE_NAMES and not critical, critical


def _json_registry_value(value):
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii"), "base64"
    return value, None


def _stored_registry_value(data: dict):
    value = data["value"]
    if data.get("value_encoding") == "base64":
        return base64.b64decode(value)
    return value


def scan_startup_items() -> list[dict]:
    """Scan all startup entries and return structured list."""
    items = []
    for hive, path, location in STARTUP_LOCATIONS:
        try:
            key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ)
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    is_safe, is_critical = _classification(name)
                    items.append({
                        "name": name,
                        "value": str(value),
                        "location": location,
                        "hive": hive,
                        "path": path,
                        "safe_to_disable": is_safe and not is_critical,
                        "critical": is_critical,
                    })
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except OSError:
            pass

    # Also scan Task Scheduler for common bloat
    try:
        ok, stdout, _ = run_cmd(["schtasks", "/query", "/fo", "CSV", "/nh"], timeout=15)
        for line in stdout.strip().splitlines() if ok else []:
            parts = line.strip().strip('"').split('","')
            if len(parts) >= 2:
                task_name = parts[0].strip('"')
                is_safe, is_critical = _classification(task_name)
                if is_safe or is_critical:
                    items.append({
                        "name": task_name,
                        "value": "Scheduled Task",
                        "location": "Task Scheduler",
                        "hive": None,
                        "path": None,
                        "safe_to_disable": is_safe,
                        "critical": is_critical,
                    })
    except Exception:
        pass

    return items


def disable_startup_item(item: dict, log_success, log_error, log_info):
    """Disable a specific startup entry."""
    if item["critical"]:
        log_error(f"⛔ Нельзя отключить системный элемент: {item['name']}")
        return False

    name = item["name"]

    if item["location"] == "Task Scheduler":
        try:
            ok, stdout, error = run_cmd(["schtasks", "/Change", "/TN", name, "/DISABLE"], timeout=10)
            if ok:
                log_success(f"Задача отключена: {name}")
                return True
            else:
                reason = (error or stdout).strip() or "команда завершилась без описания"
                log_error(f"Ошибка отключения {name}: {reason}")
        except Exception as e:
            log_error(f"Ошибка: {e}")
        return False

    try:
        hive = item["hive"]
        path = item["path"]
        with winreg.OpenKeyEx(hive, path, 0, winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
            value, value_type = winreg.QueryValueEx(key, name)
            stored_value, encoding = _json_registry_value(value)
            backup = {
                "name": name,
                "value": stored_value,
                "type": value_type,
                "hive": int(hive),
                "path": path,
            }
            if encoding:
                backup["value_encoding"] = encoding
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER, DISABLED_STARTUP_PATH, 0, winreg.KEY_SET_VALUE
            ) as backup_key:
                winreg.SetValueEx(backup_key, name, 0, winreg.REG_SZ, json.dumps(backup, ensure_ascii=False))
            winreg.DeleteValue(key, name)
        log_success(f"Удалён из автозагрузки: {name}")
        return True
    except Exception as e:
        log_error(f"Ошибка удаления {name}: {e}")
        return False


def restore_startup_item(name, log_success, log_error, log_info):
    """Restore a registry startup item saved by :func:`disable_startup_item`."""
    log_info(f"Восстановление элемента автозагрузки: {name}...")
    try:
        with winreg.OpenKeyEx(
            winreg.HKEY_CURRENT_USER, DISABLED_STARTUP_PATH, 0, winreg.KEY_QUERY_VALUE
        ) as backup_key:
            raw, _ = winreg.QueryValueEx(backup_key, name)
        data = json.loads(raw)
        with winreg.CreateKeyEx(int(data["hive"]), data["path"], 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, data["name"], 0, int(data["type"]), _stored_registry_value(data))
        log_success(f"Восстановлен в автозагрузке: {name}")
        return True
    except Exception as e:
        log_error(f"Ошибка восстановления {name}: {e}")
        return False


def disable_all_safe(log_success, log_error, log_info):
    """Disable all items flagged as safe_to_disable."""
    log_info("Сканирование автозагрузки...")
    items = scan_startup_items()
    safe = [i for i in items if i["safe_to_disable"]]
    if not safe:
        log_info("Нет элементов для безопасного отключения.")
        return

    log_info(f"Найдено {len(safe)} безопасных элементов для отключения...")
    disabled = sum(
        bool(disable_startup_item(item, log_success, log_error, log_info))
        for item in safe
    )
    if disabled:
        log_success(f"Автозагрузка оптимизирована: фактически отключено {disabled}/{len(safe)} элементов.")
    else:
        log_error("Не удалось отключить ни одного элемента автозагрузки.")


def get_startup_report(log_success, log_error, log_info):
    """Log a detailed report of startup items without changing anything."""
    log_info("Сканирование автозагрузки (только отчёт)...")
    items = scan_startup_items()
    critical = [i for i in items if i["critical"]]
    safe = [i for i in items if i["safe_to_disable"]]
    other = [i for i in items if not i["critical"] and not i["safe_to_disable"]]

    log_info(f"Всего элементов: {len(items)}")
    log_info(f"  🟢 Безопасно отключить: {len(safe)}")
    log_info(f"  🔴 Критические (не трогаем): {len(critical)}")
    log_info(f"  🟡 Прочие: {len(other)}")

    for item in safe:
        log_info(f"    ↳ {item['name']} ({item['location']})")
    log_success("Отчёт готов.")


def get_category(log_success, log_error, log_info):
    return {
        "title": "🚀 Автозагрузка",
        "desc": "Сканирование и отключение лишних программ",
        "actions": [
            {"name": "Отчёт автозагрузки", "desc": "Сканирование без изменений", "run": lambda: get_startup_report(log_success, log_error, log_info), "icon": "chart", "risk": "blue", "irreversible": False, "effects": {}},
            {
                "name": "Отключить безопасные",
                "desc": "Удалить неважные из автозагрузки",
                "run": lambda: disable_all_safe(log_success, log_error, log_info),
                "icon": "stop",
                "risk": "yellow",
                "irreversible": False,
                "effects": {"registry": [
                    {"hive": hive, "path": path, "dynamic": "registry_values"}
                    for hive, path, _ in STARTUP_LOCATIONS
                ]},
            },
        ],
    }
