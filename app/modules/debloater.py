"""
WinBoost — Windows Debloater Module
Remove pre-installed UWP apps (bloatware) using PowerShell.
"""
import logging

from modules.winshell import run_ps_json

logger = logging.getLogger("winboost")

# List of common bloatware apps to target
BLOATWARE_APPS = [
    ("3D Builder", "Microsoft.3DBuilder"),
    ("Bing News", "Microsoft.BingNews"),
    ("Bing Weather", "Microsoft.BingWeather"),
    ("Get Help", "Microsoft.GetHelp"),
    ("Get Started", "Microsoft.Getstarted"),
    ("Microsoft Office Hub", "Microsoft.MicrosoftOfficeHub"),
    ("Microsoft Solitaire Collection", "Microsoft.MicrosoftSolitaireCollection"),
    ("OneNote", "Microsoft.Office.OneNote"),
    ("People", "Microsoft.People"),
    ("Skype App", "Microsoft.SkypeApp"),
    ("Xbox App", "Microsoft.XboxApp"),
    ("Xbox Game Overlay", "Microsoft.XboxGameOverlay"),
    ("Xbox Identity Provider", "Microsoft.XboxIdentityProvider"),
    ("Xbox Speech To Text", "Microsoft.XboxSpeechToTextOverlay"),
    ("Your Phone", "Microsoft.YourPhone"),
    ("Print 3D", "Microsoft.Print3D"),
    ("Mixed Reality Portal", "Microsoft.MixedReality.Portal"),
]


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def remove_uwp_package(package_name: str) -> tuple[int, int, str]:
    """Remove matching packages for all users and report before/after counts."""
    pattern = _ps_quote(f"*{package_name}*")
    script = f"""
$before = @(Get-AppxPackage -Name {pattern} -AllUsers -ErrorAction Stop)
if ($before.Count -gt 0) {{
    $before | ForEach-Object {{
        Remove-AppxPackage -Package $_.PackageFullName -AllUsers -ErrorAction Stop
    }}
}}
$after = @(Get-AppxPackage -Name {pattern} -AllUsers -ErrorAction Stop)
[pscustomobject]@{{Before=$before.Count;After=$after.Count}}
"""
    ok, rows, error = run_ps_json(script, timeout=30)
    if not ok:
        return 0, 0, error.strip() or "PowerShell не смог удалить пакет"
    if not rows or not isinstance(rows[0], dict):
        return 0, 0, "PowerShell не вернул результат проверки пакета"
    try:
        before = int(rows[0].get("Before", 0))
        after = int(rows[0].get("After", 0))
    except (TypeError, ValueError):
        return 0, 0, "PowerShell вернул некорректный результат проверки пакета"
    return before, after, ""

def uninstall_uwp_app(app_name: str, package_name: str, log_success, log_error, log_info):
    """Uninstall a specific UWP app via PowerShell."""
    log_info(f"Удаление {app_name}...")
    try:
        before, after, error = remove_uwp_package(package_name)
        actual_removed = max(0, before - after)
        if error:
            log_error(f"Ошибка удаления {app_name}: {error}")
            return False
        if before == 0:
            log_error(f"Приложение {app_name} не найдено; удаление не выполнялось.")
            return False
        if actual_removed == 0:
            log_error(f"Приложение {app_name} найдено, но удалить его не удалось.")
            return False
        if after:
            log_error(f"{app_name}: удалено {actual_removed}, осталось пакетов: {after}.")
            return False
        log_success(f"Приложение {app_name} удалено (пакетов: {actual_removed}).")
        return True
    except Exception as e:
        log_error(f"Ошибка: {e}")
        return False

def uninstall_all_bloat(log_success, log_error, log_info):
    """Uninstall all predefined bloatware apps."""
    log_info("Запуск массового удаления блоатвара...")
    success_count = 0
    for name, package in BLOATWARE_APPS:
        if uninstall_uwp_app(name, package, log_success, log_error, log_info):
            success_count += 1
    if success_count:
        log_success(f"Массовое удаление: полностью удалено приложений: {success_count}.")
    else:
        log_error("Массовое удаление не удалило ни одного приложения.")

def get_category(log_success, log_error, log_info):
    actions = []
    for name, package in BLOATWARE_APPS:
        actions.append({
            "name": f"Удалить {name}",
            "desc": f"Полное удаление пакета {package}",
            "run": lambda n=name, p=package: uninstall_uwp_app(n, p, log_success, log_error, log_info),
                "icon": "trash",
            "risk": "yellow",
            "irreversible": True,
            "effects": {"appx": [package]},
        })
    
    actions.append({
        "name": "🗑️ Удалить ВЕСЬ блоатвар",
        "desc": "Массовое удаление всех перечисленных приложений",
        "run": lambda: uninstall_all_bloat(log_success, log_error, log_info),
            "icon": "trash",
        "risk": "red",
        "irreversible": True,
        "effects": {"appx": [package for _, package in BLOATWARE_APPS]},
    })

    return {
        "title": "📦 Деблоатер (Приложения)",
        "desc": "Удаление встроенных приложений Windows",
        "actions": actions
    }
