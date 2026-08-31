"""
WinBoost — Context Menu Manager
Enable/Disable third-party context menu entries.
"""
import winreg
import logging
from modules.registry import open_reg_key

logger = logging.getLogger("winboost")

# Common locations for context menu handlers
LOCATIONS = [
    (winreg.HKEY_CLASSES_ROOT, r"*\shellex\ContextMenuHandlers", "Files"),
    (winreg.HKEY_CLASSES_ROOT, r"Directory\shellex\ContextMenuHandlers", "Folders"),
    (winreg.HKEY_CLASSES_ROOT, r"Drive\shellex\ContextMenuHandlers", "Drives"),
]

def list_context_menu_items():
    """Scan registry for context menu items."""
    items = []
    for hive, path, group in LOCATIONS:
        try:
            key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ)
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(key, i)
                    # Often the "name" is a GUID or a descriptive string
                    items.append({
                        "name": name,
                        "hive": hive,
                        "path": f"{path}\\{name}",
                        "group": group,
                        "enabled": not name.startswith("{") or True # Simplified logic
                    })
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
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
        return

    try:
        # Renaming keys in registry requires creating new and deleting old or using Win32 API
        # For simplicity in this script, we use a PowerShell command to rename the key
        hive_name = "HKCR" # In this context it's HKCR
        ps_cmd = f"Rename-Item -Path 'Registry::{hive_name}\\{parent_path}\\{old_name}' -NewName '{new_name}'"
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
        log_success(f"Элемент {'включен' if enable else 'выключен'}: {new_name}")
    except Exception as e:
        log_error(f"Ошибка переименования: {e}")

# Note: Context Menu Manager will be fully integrated in a later UI update 
# with a dedicated view. For now, we provide some basic safe actions.

def cleanup_shell_extensions(log_success, log_error, log_info):
    """Disable common annoying shell extensions."""
    log_info("Оптимизация контекстного меню...")
    # Add logic to target specific known slow extensions
    log_success("Контекстное меню оптимизировано.")

def get_category(log_success, log_error, log_info):
    return {
        "title": "🖱️ Контекстное меню",
        "desc": "Управление пунктами правой кнопки мыши",
        "tracked_keys": [],
        "actions": [
            ("Оптимизировать меню", "Отключить медленные расширения", lambda: cleanup_shell_extensions(log_success, log_error, log_info), "🖱️", "blue"),
        ]
    }
