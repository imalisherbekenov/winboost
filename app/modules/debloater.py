"""
WinBoost — Windows Debloater Module
Remove pre-installed UWP apps (bloatware) using PowerShell.
"""
import logging

from modules.winshell import run_ps

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

def uninstall_uwp_app(app_name: str, package_name: str, log_success, log_error, log_info):
    """Uninstall a specific UWP app via PowerShell."""
    log_info(f"Удаление {app_name}...")
    try:
        ok, _, error = run_ps(f"Get-AppxPackage *{package_name}* | Remove-AppxPackage")
        if ok:
            log_success(f"Приложение {app_name} удалено.")
        else:
            log_error(f"Ошибка удаления {app_name}: {error.strip()}")
    except Exception as e:
        log_error(f"Ошибка: {e}")

def uninstall_all_bloat(log_success, log_error, log_info):
    """Uninstall all predefined bloatware apps."""
    log_info("Запуск массового удаления блоатвара...")
    for name, package in BLOATWARE_APPS:
        uninstall_uwp_app(name, package, log_success, log_error, log_info)
    log_success("✅ Массовое удаление завершено.")

def get_category(log_success, log_error, log_info):
    actions = []
    for name, package in BLOATWARE_APPS:
        actions.append({
            "name": f"Удалить {name}",
            "desc": f"Полное удаление пакета {package}",
            "run": lambda n=name, p=package: uninstall_uwp_app(n, p, log_success, log_error, log_info),
            "icon": "🗑️",
            "risk": "yellow",
            "irreversible": True,
            "effects": {"appx": [package]},
        })
    
    actions.append({
        "name": "🗑️ Удалить ВЕСЬ блоатвар",
        "desc": "Массовое удаление всех перечисленных приложений",
        "run": lambda: uninstall_all_bloat(log_success, log_error, log_info),
        "icon": "🚀",
        "risk": "red",
        "irreversible": True,
        "effects": {"appx": [package for _, package in BLOATWARE_APPS]},
    })

    return {
        "title": "📦 Деблоатер (Приложения)",
        "desc": "Удаление встроенных приложений Windows",
        "actions": actions
    }
