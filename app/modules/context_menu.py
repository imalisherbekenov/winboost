"""
WinBoost — Context Menu Manager
Enable/Disable third-party context menu entries.
"""
import winreg
import logging
import os
from modules.winshell import run_ps

logger = logging.getLogger("winboost")

# Common locations for context menu handlers
LOCATIONS = [
    (winreg.HKEY_CLASSES_ROOT, r"*\shellex\ContextMenuHandlers", "Файлы"),
    (winreg.HKEY_CLASSES_ROOT, r"Directory\shellex\ContextMenuHandlers", "Папки"),
    (winreg.HKEY_CLASSES_ROOT, r"Drive\shellex\ContextMenuHandlers", "Диски"),
]

HIVE_NAMES = {
    winreg.HKEY_CLASSES_ROOT: "HKEY_CLASSES_ROOT",
    winreg.HKEY_CURRENT_USER: "HKEY_CURRENT_USER",
    winreg.HKEY_LOCAL_MACHINE: "HKEY_LOCAL_MACHINE",
}


def _read_default_value(hive: int, path: str) -> str:
    try:
        with winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, "")
        return str(value).strip()
    except OSError:
        return ""


def _handler_server(hive: int, path: str, key_name: str) -> str:
    clsid = _read_default_value(hive, path)
    if not clsid.startswith("{"):
        clsid = key_name.removeprefix("-")
    if not clsid.startswith("{"):
        return ""
    server = _read_default_value(
        winreg.HKEY_CLASSES_ROOT,
        rf"CLSID\{clsid}\InprocServer32",
    )
    return os.path.expandvars(server)


def _is_third_party(server: str) -> bool:
    if not server:
        return False
    windows_dir = os.path.normcase(os.path.abspath(os.environ.get("WINDIR", r"C:\Windows")))
    server_path = os.path.normcase(os.path.abspath(server.strip('"')))
    try:
        return os.path.commonpath([windows_dir, server_path]) != windows_dir
    except ValueError:
        return True


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

def list_context_menu_items():
    """Scan registry for context menu items."""
    items = []
    for hive, path, group in LOCATIONS:
        try:
            with winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name = winreg.EnumKey(key, i)
                        item_path = f"{path}\\{name}"
                        server = _handler_server(hive, item_path, name)
                        items.append({
                            "name": name,
                            "hive": hive,
                            "path": item_path,
                            "group": group,
                            "enabled": not name.startswith("-"),
                            "server": server,
                            "third_party": _is_third_party(server),
                        })
                        i += 1
                    except OSError:
                        break
        except OSError:
            pass
    return items

def toggle_context_item(item_path: str, hive: int, name: str, enable: bool, log_success, log_error, log_info):
    """Toggle a context menu item by renaming its registry key."""
    # This is a common trick: prefix with '-' to disable
    parent_path = "\\".join(item_path.split("\\")[:-1])
    old_name = item_path.split("\\")[-1]
    
    if enable and old_name.startswith("-"):
        new_name = old_name[1:]
    elif not enable and not old_name.startswith("-"):
        new_name = f"-{old_name}"
    else:
        log_info(f"Элемент {old_name} уже в нужном состоянии.")
        return True

    try:
        # Renaming keys in registry requires creating new and deleting old or using Win32 API
        # For simplicity in this script, we use a PowerShell command to rename the key
        hive_name = HIVE_NAMES.get(hive)
        if not hive_name:
            log_error(f"Неподдерживаемый раздел реестра: {hive}")
            return False
        key_path = f"Registry::{hive_name}\\{parent_path}\\{old_name}"
        target_path = f"Registry::{hive_name}\\{parent_path}\\{new_name}"
        ps_cmd = (
            f"Rename-Item -LiteralPath {_ps_quote(key_path)} "
            f"-NewName {_ps_quote(new_name)} -ErrorAction Stop; "
            f"if (-not (Test-Path -LiteralPath {_ps_quote(target_path)})) {{ "
            "throw 'Переименованный ключ не найден' }"
        )
        ok, stdout, error = run_ps(ps_cmd)
        if ok:
            log_success(f"Элемент {'включен' if enable else 'выключен'}: {new_name}")
            return True
        else:
            reason = (error or stdout).strip() or "PowerShell завершился без описания ошибки"
            log_error(f"Ошибка переименования: {reason}")
    except Exception as e:
        log_error(f"Ошибка переименования: {e}")
    return False

def get_context_menu_report(log_success, log_error, log_info):
    """Report third-party shell extensions without changing the registry."""
    log_info("Сканирование контекстного меню (только отчёт)...")
    items = [item for item in list_context_menu_items() if item["third_party"]]
    for _, _, group in LOCATIONS:
        grouped = [item for item in items if item["group"] == group]
        log_info(f"{group}: {len(grouped)}")
        for item in grouped:
            state = "включён" if item["enabled"] else "отключён"
            log_info(f"    ↳ {item['name']} ({state}) — {item['server']}")
    log_success(f"Отчёт готов. Сторонних обработчиков: {len(items)}.")

def get_category(log_success, log_error, log_info):
    return {
        "title": "🖱️ Контекстное меню",
        "desc": "Управление пунктами правой кнопки мыши",
        "actions": [
            {"name": "Отчёт контекстного меню", "desc": "Сканирование без изменений", "run": lambda: get_context_menu_report(log_success, log_error, log_info), "icon": "📊", "risk": "blue", "irreversible": False, "effects": {}},
        ]
    }
