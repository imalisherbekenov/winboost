"""
WinBoost — Cleanup Module (Enhanced)
Temp files, Prefetch, DNS cache, Browser caches, Recycle Bin, Windows Update cache.
Tracks freed disk space for each operation.
"""
import subprocess
import os
import shutil
import glob
import ctypes

from modules.winshell import run_cmd


def _get_size(path: str) -> int:
    """Get total size of a file or directory in bytes."""
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def _fmt_size(bytes_val: int) -> str:
    """Format bytes as human-readable string."""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 ** 2:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1024 ** 3:
        return f"{bytes_val / (1024 ** 2):.1f} MB"
    else:
        return f"{bytes_val / (1024 ** 3):.2f} GB"


def clean_temp(log_success, log_error, log_info):
    """Clean user and system temp directories with size tracking."""
    log_info("Очистка временных файлов...")
    dirs = [
        os.environ.get("TEMP", ""),
        os.environ.get("TMP", ""),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Temp"),
    ]
    total_files = 0
    total_bytes = 0
    for d in dirs:
        if not d or not os.path.isdir(d):
            continue
        for item in os.listdir(d):
            path = os.path.join(d, item)
            try:
                size = _get_size(path)
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                total_files += 1
                total_bytes += size
            except Exception:
                pass
    log_success(f"Удалено: {total_files} элементов ({_fmt_size(total_bytes)})")


def clean_prefetch(log_success, log_error, log_info):
    """Clean Windows Prefetch files."""
    log_info("Очистка Prefetch...")
    pf = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Prefetch")
    count = 0
    total_bytes = 0
    if os.path.isdir(pf):
        for f in glob.glob(os.path.join(pf, "*.pf")):
            try:
                total_bytes += os.path.getsize(f)
                os.remove(f)
                count += 1
            except Exception:
                pass
    log_success(f"Prefetch: удалено {count} файлов ({_fmt_size(total_bytes)})")


def flush_dns(log_success, log_error, log_info):
    """Flush DNS resolver cache."""
    log_info("Сброс DNS-кэша...")
    try:
        ok, _, error = run_cmd(["ipconfig", "/flushdns"])
        if ok:
            log_success("DNS-кэш очищен.")
        else:
            log_error(f"Ошибка: {error.strip()}")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def clean_browser_caches(log_success, log_error, log_info):
    """Clean Chrome, Edge, Firefox, and Opera caches."""
    log_info("Очистка кэша браузеров...")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    appdata = os.environ.get("APPDATA", "")

    cache_paths = [
        # Chrome
        os.path.join(localappdata, r"Google\Chrome\User Data\Default\Cache"),
        os.path.join(localappdata, r"Google\Chrome\User Data\Default\Code Cache"),
        os.path.join(localappdata, r"Google\Chrome\User Data\Default\GPUCache"),
        # Edge
        os.path.join(localappdata, r"Microsoft\Edge\User Data\Default\Cache"),
        os.path.join(localappdata, r"Microsoft\Edge\User Data\Default\Code Cache"),
        # Firefox (profile-independent)
        os.path.join(localappdata, r"Mozilla\Firefox\Profiles"),
        # Opera
        os.path.join(appdata, r"Opera Software\Opera Stable\Cache"),
    ]

    total_bytes = 0
    total_items = 0

    for cache_dir in cache_paths:
        if not os.path.isdir(cache_dir):
            continue

        # Special handling for Firefox — search for cache2 inside profiles
        if "Firefox" in cache_dir and "Profiles" in cache_dir:
            for profile in os.listdir(cache_dir):
                ff_cache = os.path.join(cache_dir, profile, "cache2")
                if os.path.isdir(ff_cache):
                    size = _get_size(ff_cache)
                    shutil.rmtree(ff_cache, ignore_errors=True)
                    total_bytes += size
                    total_items += 1
            continue

        size = _get_size(cache_dir)
        try:
            shutil.rmtree(cache_dir, ignore_errors=True)
            total_bytes += size
            total_items += 1
        except Exception:
            pass

    log_success(f"Кэш браузеров: очищено {total_items} директорий ({_fmt_size(total_bytes)})")


def empty_recycle_bin(log_success, log_error, log_info):
    """Empty the Windows Recycle Bin."""
    log_info("Очистка корзины...")
    try:
        # SHEmptyRecycleBin flags: SHERB_NOCONFIRMATION=1, SHERB_NOPROGRESSUI=2, SHERB_NOSOUND=4
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x0007)
        log_success("Корзина очищена.")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def clean_windows_update_cache(log_success, log_error, log_info):
    """Clean Windows Update download cache (SoftwareDistribution)."""
    log_info("Очистка кэша Windows Update...")
    try:
        # Stop Windows Update service
        run_cmd(["net", "stop", "wuauserv"], timeout=15)
        run_cmd(["net", "stop", "bits"], timeout=15)

        dl_path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SoftwareDistribution", "Download")
        total_bytes = 0
        if os.path.isdir(dl_path):
            total_bytes = _get_size(dl_path)
            shutil.rmtree(dl_path, ignore_errors=True)
            os.makedirs(dl_path, exist_ok=True)

        # Restart services
        run_cmd(["net", "start", "wuauserv"], timeout=15)
        run_cmd(["net", "start", "bits"], timeout=15)

        log_success(f"Кэш Windows Update очищен ({_fmt_size(total_bytes)})")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def run_disk_cleanup(log_success, log_error, log_info):
    """Run Windows Disk Cleanup utility."""
    log_info("Запуск очистки диска (cleanmgr)...")
    try:
        subprocess.Popen(["cleanmgr", "/d", "C"], creationflags=0x00000010)
        log_success("cleanmgr запущен.")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def full_cleanup(log_success, log_error, log_info):
    """Run all cleanup operations in sequence."""
    log_info("=== Полная очистка ===")
    clean_temp(log_success, log_error, log_info)
    clean_prefetch(log_success, log_error, log_info)
    flush_dns(log_success, log_error, log_info)
    clean_browser_caches(log_success, log_error, log_info)
    empty_recycle_bin(log_success, log_error, log_info)
    clean_windows_update_cache(log_success, log_error, log_info)
    log_success("✅ Полная очистка завершена!")


def get_category(log_success, log_error, log_info):
    return {
        "title": "🧹 Очистка",
        "desc": "TEMP, Prefetch, DNS, браузеры, корзина, Windows Update",
        "actions": [
            {"name": "Очистить TEMP", "desc": "Удалить временные файлы", "run": lambda: clean_temp(log_success, log_error, log_info), "icon": "🗑️", "risk": "blue", "irreversible": True, "effects": {}},
            {"name": "Очистить Prefetch", "desc": "Файлы предзагрузки", "run": lambda: clean_prefetch(log_success, log_error, log_info), "icon": "📂", "risk": "blue", "irreversible": True, "effects": {}},
            {"name": "Сбросить DNS-кэш", "desc": "ipconfig /flushdns", "run": lambda: flush_dns(log_success, log_error, log_info), "icon": "🌐", "risk": "blue", "irreversible": True, "effects": {}},
            {"name": "Кэш браузеров", "desc": "Chrome, Edge, Firefox, Opera", "run": lambda: clean_browser_caches(log_success, log_error, log_info), "icon": "🌍", "risk": "blue", "irreversible": True, "effects": {}},
            {"name": "Очистить корзину", "desc": "Recycle Bin", "run": lambda: empty_recycle_bin(log_success, log_error, log_info), "icon": "♻️", "risk": "blue", "irreversible": True, "effects": {}},
            {"name": "Кэш Windows Update", "desc": "SoftwareDistribution", "run": lambda: clean_windows_update_cache(log_success, log_error, log_info), "icon": "📦", "risk": "yellow", "irreversible": True, "effects": {}},
            {"name": "Очистка диска", "desc": "cleanmgr", "run": lambda: run_disk_cleanup(log_success, log_error, log_info), "icon": "💿", "risk": "blue", "irreversible": True, "effects": {}},
            {"name": "🧹 Полная очистка", "desc": "Всё вместе", "run": lambda: full_cleanup(log_success, log_error, log_info), "icon": "🚀", "risk": "yellow", "irreversible": True, "effects": {}},
        ],
    }
