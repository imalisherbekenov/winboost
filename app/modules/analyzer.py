"""
WinBoost — Deep System Analyzer v2
Thorough multi-stage scan: hardware, services, privacy, network,
disk, memory, startup, drivers, power plan, visual effects.
Reports progress via callback for each stage.
"""
import platform
import psutil
import winreg
import os
import time
from typing import Callable, Optional

from modules import winshell


def _read_hardware_cim() -> tuple[dict[str, list[dict]], str, str]:
    """Read CPU, video, and memory data in one CIM call.

    The status differentiates a command error from a successful query that did
    not return any hardware rows.
    """
    script = r"""
@(
    Get-CimInstance Win32_Processor -ErrorAction Stop |
        Select-Object @{Name='Kind';Expression={'CPU'}},Name
    Get-CimInstance Win32_VideoController -ErrorAction Stop |
        Select-Object @{Name='Kind';Expression={'Video'}},Name,DriverVersion,AdapterRAM
    Get-CimInstance Win32_PhysicalMemory -ErrorAction Stop |
        Select-Object @{Name='Kind';Expression={'Memory'}},Speed
)
"""
    ok, rows, error = winshell.run_ps_json(script, timeout=15)
    grouped = {"CPU": [], "Video": [], "Memory": []}
    if not ok:
        return grouped, "error", error.strip() or "Не удалось выполнить CIM-запрос"
    for row in rows:
        kind = row.get("Kind") if isinstance(row, dict) else None
        if kind in grouped:
            grouped[kind].append(row)
    status = "ok" if any(grouped.values()) else "no_data"
    return grouped, status, ""


def _svc_running(name: str) -> bool | None:
    ok, stdout, _ = winshell.run_cmd(["sc.exe", "query", name], timeout=5)
    if not ok:
        return None
    return "RUNNING" in stdout.upper()


def _reg_value(hive, path, name, default=None):
    try:
        key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return val
    except Exception:
        return default


def _count_startup_items() -> int:
    count = 0
    for hive, path in [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
    ]:
        try:
            key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ)
            i = 0
            while True:
                try:
                    winreg.EnumValue(key, i)
                    count += 1
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except OSError:
            pass
    return count


def _fmt_bytes(b: int) -> str:
    if b < 1024**2:
        return f"{b / 1024:.0f} KB"
    elif b < 1024**3:
        return f"{b / (1024**2):.1f} MB"
    else:
        return f"{b / (1024**3):.1f} GB"


def analyze_system(progress_cb: Optional[Callable] = None) -> dict:
    """
    Run deep multi-stage system analysis.
    progress_cb(stage_name: str, stage_num: int, total_stages: int)
    """
    info = {}
    total_stages = 10

    # Prime psutil's non-blocking CPU counter. Its first result is always
    # meaningless, so intentionally discard it and read again after CIM work.
    try:
        psutil.cpu_percent(interval=None)
    except Exception:
        pass

    def _progress(name, num):
        if progress_cb:
            progress_cb(name, num, total_stages)

    # ═══ Stage 1: CPU ═══
    _progress("Сканирование процессора...", 1)
    hardware, cim_status, cim_error = _read_hardware_cim()
    info["cim_status"] = cim_status
    info["cim_error"] = cim_error
    cpu_names = [str(row.get("Name", "")).strip() for row in hardware["CPU"]]
    cpu_names = [name for name in cpu_names if name]
    info["cpu_name"] = cpu_names[0] if cpu_names else (platform.processor() or "Н/Д")
    try:
        info["cpu_cores"] = psutil.cpu_count(logical=False)
    except Exception:
        info["cpu_cores"] = None
    try:
        info["cpu_threads"] = psutil.cpu_count(logical=True)
    except Exception:
        info["cpu_threads"] = None
    info["cpu_freq_mhz"] = None
    try:
        freq = psutil.cpu_freq()
        if freq:
            info["cpu_freq_mhz"] = int(freq.current)
    except Exception:
        pass
    try:
        info["cpu_usage"] = psutil.cpu_percent()
    except Exception:
        info["cpu_usage"] = None

    # ═══ Stage 2: GPU ═══
    _progress("Сканирование видеокарты...", 2)
    video = hardware["Video"][0] if hardware["Video"] else {}
    info["gpu_name"] = str(video.get("Name") or "Н/Д")
    info["gpu_driver"] = str(video.get("DriverVersion") or "Н/Д")
    info["gpu_vram"] = video.get("AdapterRAM")
    try:
        vram_bytes = int(info["gpu_vram"])
        info["gpu_vram_fmt"] = _fmt_bytes(vram_bytes)
    except (ValueError, TypeError):
        info["gpu_vram_fmt"] = "Н/Д"

    # ═══ Stage 3: RAM ═══
    _progress("Сканирование оперативной памяти...", 3)
    try:
        mem = psutil.virtual_memory()
        info["ram_total_gb"] = round(mem.total / (1024**3), 1)
        info["ram_used_gb"] = round(mem.used / (1024**3), 1)
        info["ram_usage_pct"] = mem.percent
    except Exception:
        info["ram_total_gb"] = None
        info["ram_used_gb"] = None
        info["ram_usage_pct"] = None
    ram_speeds = [row.get("Speed") for row in hardware["Memory"] if row.get("Speed")]
    info["ram_speed"] = max(ram_speeds) if ram_speeds else "Н/Д"
    try:
        swap = psutil.swap_memory()
        info["swap_total_gb"] = round(swap.total / (1024**3), 1)
        info["swap_used_pct"] = swap.percent
    except Exception:
        info["swap_total_gb"] = None
        info["swap_used_pct"] = None

    # ═══ Stage 4: Disk ═══
    _progress("Сканирование дисков...", 4)
    info["disks"] = []
    info["disks_available"] = True
    try:
        partitions = psutil.disk_partitions(all=False)
    except Exception:
        partitions = []
        info["disks_available"] = False
    for part in partitions:
        try:
            usage = psutil.disk_usage(part.mountpoint)
            info["disks"].append({
                "mount": part.mountpoint,
                "fs": part.fstype,
                "total_gb": round(usage.total / (1024**3), 1),
                "used_gb": round(usage.used / (1024**3), 1),
                "free_gb": round(usage.free / (1024**3), 1),
                "pct": usage.percent,
            })
        except Exception:
            info["disks"].append({
                "mount": part.mountpoint,
                "fs": part.fstype,
                "total_gb": None,
                "used_gb": None,
                "free_gb": None,
                "pct": None,
            })

    # ═══ Stage 5: OS & Uptime ═══
    _progress("Сканирование системы...", 5)
    info["os_name"] = platform.platform()
    info["os_build"] = platform.version()
    uptime_h = None
    try:
        boot_time = psutil.boot_time()
        uptime_sec = time.time() - boot_time
        uptime_h = int(uptime_sec // 3600)
        uptime_m = int((uptime_sec % 3600) // 60)
        info["uptime"] = f"{uptime_h}ч {uptime_m}мин"
    except Exception:
        info["uptime"] = None
    try:
        info["process_count"] = len(psutil.pids())
    except Exception:
        info["process_count"] = None

    # ═══ Stage 6: Services ═══
    _progress("Проверка служб Windows...", 6)
    services_to_check = [
        ("DiagTrack", "Телеметрия"),
        ("dmwappushservice", "WAP Push"),
        ("SysMain", "SuperFetch"),
        ("WSearch", "Windows Search"),
        ("Fax", "Факс"),
        ("MapsBroker", "Загрузчик карт"),
        ("lfsvc", "Геолокация"),
        ("bthserv", "Bluetooth"),
        ("wuauserv", "Windows Update"),
        ("RemoteRegistry", "Удалённый реестр"),
    ]
    info["services"] = {}
    for svc_id, svc_name in services_to_check:
        running = _svc_running(svc_id)
        info["services"][svc_id] = {"name": svc_name, "running": running}

    # ═══ Stage 7: Privacy ═══
    _progress("Проверка настроек приватности...", 7)
    privacy_checks = {
        "telemetry_off": _reg_value(winreg.HKEY_LOCAL_MACHINE,
                                     r"SOFTWARE\Policies\Microsoft\Windows\DataCollection",
                                     "AllowTelemetry", default=1) == 0,
        "cortana_off": _reg_value(winreg.HKEY_LOCAL_MACHINE,
                                   r"SOFTWARE\Policies\Microsoft\Windows\Windows Search",
                                   "AllowCortana", default=1) == 0,
        "advertising_off": _reg_value(winreg.HKEY_CURRENT_USER,
                                       r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo",
                                       "Enabled", default=1) == 0,
        "timeline_off": _reg_value(winreg.HKEY_LOCAL_MACHINE,
                                    r"SOFTWARE\Policies\Microsoft\Windows\System",
                                    "EnableActivityFeed", default=1) == 0,
        "location_off": _reg_value(winreg.HKEY_LOCAL_MACHINE,
                                    r"SOFTWARE\Policies\Microsoft\Windows\LocationAndSensors",
                                    "DisableLocation", default=0) == 1,
        "feedback_off": _reg_value(winreg.HKEY_CURRENT_USER,
                                    r"Software\Microsoft\Siuf\Rules",
                                    "NumberOfSIUFInPeriod", default=1) == 0,
    }
    info["privacy"] = privacy_checks
    info["privacy_score"] = int(sum(privacy_checks.values()) / len(privacy_checks) * 100)

    # ═══ Stage 8: Startup & Performance ═══
    _progress("Проверка автозагрузки и производительности...", 8)
    info["startup_count"] = _count_startup_items()
    info["visual_fx"] = _reg_value(winreg.HKEY_CURRENT_USER,
                                    r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
                                    "VisualFXSetting", default=0)
    info["game_mode"] = _reg_value(winreg.HKEY_CURRENT_USER,
                                    r"Software\Microsoft\GameBar",
                                    "AutoGameModeEnabled", default=0) == 1
    info["game_dvr_off"] = _reg_value(winreg.HKEY_CURRENT_USER,
                                       r"System\GameConfigStore",
                                       "GameDVR_Enabled", default=1) == 0

    # ═══ Stage 9: Network ═══
    _progress("Проверка сетевых настроек...", 9)
    try:
        net_io = psutil.net_io_counters()
        info["net_sent_gb"] = round(net_io.bytes_sent / (1024**3), 2)
        info["net_recv_gb"] = round(net_io.bytes_recv / (1024**3), 2)
    except Exception:
        info["net_sent_gb"] = None
        info["net_recv_gb"] = None
    info["net_adapters"] = []
    info["net_adapters_available"] = True
    try:
        stats = psutil.net_if_stats()
        for name, stat in stats.items():
            if stat.isup and name != "Loopback Pseudo-Interface 1":
                speed = f"{stat.speed} Mbps" if stat.speed > 0 else "Н/Д"
                info["net_adapters"].append({"name": name, "speed": speed})
    except Exception:
        info["net_adapters_available"] = False

    # ═══ Stage 10: Power Plan ═══
    _progress("Проверка плана электропитания...", 10)
    ok, stdout, _ = winshell.run_cmd(["powercfg", "/getactivescheme"], timeout=5)
    info["power_plan"] = stdout.strip().split("(")[-1].rstrip(")") if ok and stdout.strip() else "Н/Д"

    # ═══ Calculate Scores ═══
    # Bottleneck
    if info["cpu_cores"] is not None and info["cpu_cores"] <= 4:
        info["bottleneck"] = "CPU (мало ядер)"
    elif info["ram_total_gb"] is not None and info["ram_total_gb"] < 8:
        info["bottleneck"] = "RAM (мало памяти)"
    elif info["cpu_cores"] is not None and info["ram_total_gb"] is not None:
        info["bottleneck"] = "GPU (графика)"
    else:
        info["bottleneck"] = "N/A"

    # Optimization score (0-100)
    opt = 0
    if info["services"]["DiagTrack"]["running"] is False:
        opt += 15
    if info["services"]["SysMain"]["running"] is False:
        opt += 10
    if info["services"]["WSearch"]["running"] is False:
        opt += 10
    if info["services"]["Fax"]["running"] is False:
        opt += 5
    if info["services"]["RemoteRegistry"]["running"] is False:
        opt += 5
    if info["visual_fx"] == 2:
        opt += 15
    if info["game_mode"]:
        opt += 10
    if info["game_dvr_off"]:
        opt += 10
    if info["startup_count"] <= 5:
        opt += 15
    elif info["startup_count"] <= 10:
        opt += 8
    if "Максимальная" in info.get("power_plan", "") or "Ultimate" in info.get("power_plan", ""):
        opt += 10
    info["optimization_score"] = min(100, opt)

    # Boost potential
    boost = max(0, 30 - info["optimization_score"] * 30 // 100)
    info["boost_potential"] = boost

    # Stability
    stability = 50
    if info["ram_usage_pct"] is not None and info["ram_usage_pct"] < 70:
        stability += 15
    if info["cpu_usage"] is not None and info["cpu_usage"] < 50:
        stability += 10
    for d in info["disks"]:
        if d["pct"] is not None and d["pct"] < 85:
            stability += 5
    if uptime_h is not None and uptime_h < 72:
        stability += 10
    info["stability_score"] = min(100, stability)

    return info


def format_analysis(info: dict) -> list[tuple[str, str]]:
    """
    Format analysis results as list of (text, category) tuples.
    Categories: 'header', 'good', 'warn', 'info', 'score'
    """
    lines = []

    def display(value, unit=""):
        unavailable = value is None or str(value).strip() in {"", "N/A", "Н/Д", "unavailable"}
        if unavailable:
            return "недоступно"
        separator = "" if unit == "%" else " "
        return f"{value}{separator}{unit}" if unit else str(value)

    # Hardware
    lines.append(("═══ АППАРАТНОЕ ОБЕСПЕЧЕНИЕ ═══", "header"))
    lines.append((f"  CPU:  {info['cpu_name']}", "info"))
    lines.append((f"        {display(info['cpu_cores'], 'ядер')} / {display(info['cpu_threads'], 'потоков')}, "
                  f"{display(info['cpu_freq_mhz'], 'MHz')}, загрузка: {display(info['cpu_usage'], '%')}", "info"))
    lines.append((f"  GPU:  {info['gpu_name']}", "info"))
    lines.append((f"        Драйвер: {info['gpu_driver']}, VRAM: {info['gpu_vram_fmt']}", "info"))
    lines.append((f"  RAM:  {display(info['ram_total_gb'], 'GB')} (использование: {display(info['ram_usage_pct'], '%')})", "info"))
    lines.append((f"        Частота: {display(info['ram_speed'], 'MHz')}, PageFile: {display(info['swap_total_gb'], 'GB')}", "info"))
    lines.append((f"  OS:   {info['os_name']}", "info"))
    lines.append((f"        Uptime: {display(info['uptime'])}, Процессов: {display(info['process_count'])}", "info"))

    # Disks
    lines.append(("", "info"))
    lines.append(("═══ ДИСКИ ═══", "header"))
    if not info.get("disks_available", True):
        lines.append(("  Данные о дисках: unavailable", "info"))
    for d in info["disks"]:
        status = "info" if d["pct"] is None else ("warn" if d["pct"] > 85 else "good")
        lines.append((f"  {d['mount']}  {display(d['used_gb'], 'GB')}/{display(d['total_gb'], 'GB')} "
                      f"({display(d['pct'], '%')})  [{d['fs']}]", status))

    # Services
    lines.append(("", "info"))
    lines.append(("═══ СЛУЖБЫ ═══", "header"))
    for svc_id, svc_data in info["services"].items():
        running = svc_data["running"]
        icon = "?" if running is None else ("⚠" if running else "✓")
        status = "info" if running is None else ("warn" if running else "good")
        state = "Н/Д" if running is None else ("АКТИВНА" if running else "отключена")
        lines.append((f"  {icon} {svc_data['name']} ({svc_id}): {state}", status))

    # Privacy
    lines.append(("", "info"))
    lines.append(("═══ ПРИВАТНОСТЬ ═══", "header"))
    priv_labels = {
        "telemetry_off": "Телеметрия",
        "cortana_off": "Cortana",
        "advertising_off": "Advertising ID",
        "timeline_off": "Timeline",
        "location_off": "Геолокация",
        "feedback_off": "Feedback",
    }
    for key, label in priv_labels.items():
        disabled = info["privacy"].get(key, False)
        icon = "✓" if disabled else "⚠"
        status = "good" if disabled else "warn"
        state = "отключена" if disabled else "АКТИВНА"
        lines.append((f"  {icon} {label}: {state}", status))

    # Performance
    lines.append(("", "info"))
    lines.append(("═══ ПРОИЗВОДИТЕЛЬНОСТЬ ═══", "header"))
    lines.append((f"  Автозагрузка: {info['startup_count']} элементов", "warn" if info["startup_count"] > 8 else "good"))
    vfx = {0: "Не настроено", 1: "Лучший вид", 2: "Лучшее быстродействие", 3: "Пользовательское"}
    lines.append((f"  Визуальные эффекты: {vfx.get(info['visual_fx'], 'Н/Д')}", "good" if info["visual_fx"] == 2 else "warn"))
    lines.append((f"  Game Mode: {'включён' if info['game_mode'] else 'выключен'}", "good" if info["game_mode"] else "warn"))
    lines.append((f"  Game DVR: {'отключён' if info['game_dvr_off'] else 'АКТИВЕН'}", "good" if info["game_dvr_off"] else "warn"))
    lines.append((f"  План питания: {info['power_plan']}", "info"))
    lines.append((f"  Упор: {info['bottleneck']}", "info"))

    # Network
    lines.append(("", "info"))
    lines.append(("═══ СЕТЬ ═══", "header"))
    if not info.get("net_adapters_available", True):
        lines.append(("  Сетевые адаптеры: unavailable", "info"))
    for adapter in info.get("net_adapters", []):
        lines.append((f"  {adapter['name']}: {adapter['speed']}", "info"))
    lines.append((f"  Трафик: ↑{display(info['net_sent_gb'], 'GB')} / ↓{display(info['net_recv_gb'], 'GB')}", "info"))

    return lines
