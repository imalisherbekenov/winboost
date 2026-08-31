"""
WinBoost — Startup Manager Module
Scan, list, and disable unnecessary startup programs.
"""
import winreg
import subprocess
import os

# Registry locations where startup items live
STARTUP_LOCATIONS = [
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM Run"),
    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce", "HKCU RunOnce"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce", "HKLM RunOnce"),
]

# Known safe-to-disable startup items (case-insensitive partial match)
SAFE_TO_DISABLE = [
    "onedrive", "skype", "spotify", "discord", "steam", "epicgames",
    "teams", "zoom", "adobe", "creative cloud", "ccleaner", "itunes",
    "helperservice", "updater", "update", "helper", "tray",
    "googleupdate", "microsoftedge", "msedge",
]

# NEVER disable these — critical system components
NEVER_DISABLE = [
    "securityhealth", "windows defender", "windowssecurity",
    "realtek", "nvidia", "amd", "intel", "ctfmon", "explorer",
    "igfx", "rthdvcpl",
]


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
                    is_safe = any(s in name.lower() or s in str(value).lower() for s in SAFE_TO_DISABLE)
                    is_critical = any(s in name.lower() or s in str(value).lower() for s in NEVER_DISABLE)
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
        r = subprocess.run(
            ["schtasks", "/query", "/fo", "CSV", "/nh"],
            capture_output=True, text=True, timeout=15
        )
        for line in r.stdout.strip().split("\n"):
            parts = line.strip().strip('"').split('","')
            if len(parts) >= 2:
                task_name = parts[0].strip('"')
                if any(s in task_name.lower() for s in SAFE_TO_DISABLE):
                    items.append({
                        "name": task_name,
                        "value": "Scheduled Task",
                        "location": "Task Scheduler",
                        "hive": None,
                        "path": None,
                        "safe_to_disable": True,
                        "critical": False,
                    })
    except Exception:
        pass

    return items


def disable_startup_item(item: dict, log_success, log_error, log_info):
    """Disable a specific startup entry."""
    if item["critical"]:
        log_error(f"⛔ Нельзя отключить системный элемент: {item['name']}")
        return

    name = item["name"]

    if item["location"] == "Task Scheduler":
        try:
            subprocess.run(
                ["schtasks", "/Change", "/TN", name, "/DISABLE"],
                capture_output=True, timeout=10
            )
            log_success(f"Задача отключена: {name}")
        except Exception as e:
            log_error(f"Ошибка: {e}")
        return

    try:
        hive = item["hive"]
        path = item["path"]
        key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
        log_success(f"Удалён из автозагрузки: {name}")
    except Exception as e:
        log_error(f"Ошибка удаления {name}: {e}")


def disable_all_safe(log_success, log_error, log_info):
    """Disable all items flagged as safe_to_disable."""
    log_info("Сканирование автозагрузки...")
    items = scan_startup_items()
    safe = [i for i in items if i["safe_to_disable"]]
    if not safe:
        log_info("Нет элементов для безопасного отключения.")
        return

    log_info(f"Найдено {len(safe)} безопасных элементов для отключения...")
    for item in safe:
        disable_startup_item(item, log_success, log_error, log_info)
    log_success(f"Автозагрузка оптимизирована: отключено {len(safe)} элементов.")


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
        "tracked_keys": [],
        "actions": [
            ("Отчёт автозагрузки", "Сканирование без изменений", lambda: get_startup_report(log_success, log_error, log_info), "📊", "blue"),
            ("Отключить безопасные", "Удалить неважные из автозагрузки", lambda: disable_all_safe(log_success, log_error, log_info), "🧹", "yellow"),
        ],
    }
