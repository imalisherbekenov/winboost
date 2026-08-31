"""
WinBoost — Deep System Analyzer v2
Thorough multi-stage scan: hardware, services, privacy, network,
disk, memory, startup, drivers, power plan, visual effects.
Reports progress via callback for each stage.
"""
import subprocess
import platform
import psutil
import winreg
import os
import time
from typing import Callable, Optional


def _get_wmic(query: str) -> str:
    try:
        r = subprocess.run(["wmic"] + query.split(), capture_output=True, text=True, timeout=10)
        lines = [l.strip() for l in r.stdout.strip().split("\n") if l.strip()]
        return lines[1] if len(lines) > 1 else "Н/Д"
    except Exception:
        return "Н/Д"


def _svc_running(name: str) -> bool:
    try:
        r = subprocess.run(["sc", "query", name], capture_output=True, text=True, timeout=5)
        return "RUNNING" in r.stdout
    except Exception:
        return False


def _reg_value(hive, path, name, default=None):
    try:
        key = winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return val
    except Exception:
        return default


def _reg_disabled(hive, path, name) -> bool:
    val = _reg_value(hive, path, name, default=None)
    return val == 0 or val == 1  # disabled = AllowX=0 or DisableX=1


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

    def _progress(name, num):
        if progress_cb:
            progress_cb(name, num, total_stages)
        time.sleep(0.3)  # deliberate pause so user sees each stage

    # ═══ Stage 1: CPU ═══
    _progress("Сканирование процессора...", 1)
    info["cpu_name"] = platform.processor() or _get_wmic("cpu get Name")
    info["cpu_cores"] = psutil.cpu_count(logical=False) or 0
    info["cpu_threads"] = psutil.cpu_count(logical=True) or 0
    info["cpu_freq_mhz"] = 0
    try:
        freq = psutil.cpu_freq()
        if freq:
            info["cpu_freq_mhz"] = int(freq.current)
    except Exception:
        pass
    info["cpu_usage"] = psutil.cpu_percent(interval=1)

    # ═══ Stage 2: GPU ═══
    _progress("Сканирование видеокарты...", 2)
    info["gpu_name"] = _get_wmic("path win32_VideoController get Name")
    info["gpu_driver"] = _get_wmic("path win32_VideoController get DriverVersion")
    info["gpu_vram"] = _get_wmic("path win32_VideoController get AdapterRAM")
    try:
        vram_bytes = int(info["gpu_vram"])
        info["gpu_vram_fmt"] = _fmt_bytes(vram_bytes)
    except (ValueError, TypeError):
        info["gpu_vram_fmt"] = "Н/Д"

    # ═══ Stage 3: RAM ═══
    _progress("Сканирование оперативной памяти...", 3)
    mem = psutil.virtual_memory()
    info["ram_total_gb"] = round(mem.total / (1024**3), 1)
    info["ram_used_gb"] = round(mem.used / (1024**3), 1)
    info["ram_usage_pct"] = mem.percent
    info["ram_speed"] = _get_wmic("memorychip get Speed")
    swap = psutil.swap_memory()
    info["swap_total_gb"] = round(swap.total / (1024**3), 1)
    info["swap_used_pct"] = swap.percent

    # ═══ Stage 4: Disk ═══
    _progress("Сканирование дисков...", 4)
    info["disks"] = []
    for part in psutil.disk_partitions(all=False):
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
            pass

    # ═══ Stage 5: OS & Uptime ═══
    _progress("Сканирование системы...", 5)
    info["os_name"] = platform.platform()
    info["os_build"] = platform.version()
    boot_time = psutil.boot_time()
    uptime_sec = time.time() - boot_time
    uptime_h = int(uptime_sec // 3600)
    uptime_m = int((uptime_sec % 3600) // 60)
    info["uptime"] = f"{uptime_h}ч {uptime_m}мин"
    info["process_count"] = len(psutil.pids())

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
    net_io = psutil.net_io_counters()
    info["net_sent_gb"] = round(net_io.bytes_sent / (1024**3), 2)
    info["net_recv_gb"] = round(net_io.bytes_recv / (1024**3), 2)
    info["net_adapters"] = []
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        for name, stat in stats.items():
            if stat.isup and name != "Loopback Pseudo-Interface 1":
                speed = f"{stat.speed} Mbps" if stat.speed > 0 else "Н/Д"
                info["net_adapters"].append({"name": name, "speed": speed})
    except Exception:
        pass

    # ═══ Stage 10: Power Plan ═══
    _progress("Проверка плана электропитания...", 10)
    try:
        r = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, timeout=5)
        info["power_plan"] = r.stdout.strip().split("(")[-1].rstrip(")") if r.returncode == 0 else "Н/Д"
    except Exception:
        info["power_plan"] = "Н/Д"

    # ═══ Calculate Scores ═══
    # Bottleneck
    if info["cpu_cores"] <= 4:
        info["bottleneck"] = "CPU (мало ядер)"
    elif info["ram_total_gb"] < 8:
        info["bottleneck"] = "RAM (мало памяти)"
    else:
        info["bottleneck"] = "GPU (графика)"

    # Optimization score (0-100)
    opt = 0
    if not info["services"]["DiagTrack"]["running"]:
        opt += 15
    if not info["services"]["SysMain"]["running"]:
        opt += 10
    if not info["services"]["WSearch"]["running"]:
        opt += 10
    if not info["services"]["Fax"]["running"]:
        opt += 5
    if not info["services"]["RemoteRegistry"]["running"]:
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
    if info["ram_usage_pct"] < 70:
        stability += 15
    if info["cpu_usage"] < 50:
        stability += 10
    for d in info["disks"]:
        if d["pct"] < 85:
            stability += 5
    if uptime_h < 72:
        stability += 10
    info["stability_score"] = min(100, stability)

    return info


def format_analysis(info: dict) -> list[tuple[str, str]]:
    """
    Format analysis results as list of (text, category) tuples.
    Categories: 'header', 'good', 'warn', 'info', 'score'
    """
    lines = []

    # Hardware
    lines.append(("═══ АППАРАТНОЕ ОБЕСПЕЧЕНИЕ ═══", "header"))
    lines.append((f"  CPU:  {info['cpu_name']}", "info"))
    lines.append((f"        {info['cpu_cores']} ядер / {info['cpu_threads']} потоков, {info['cpu_freq_mhz']} MHz", "info"))
    lines.append((f"  GPU:  {info['gpu_name']}", "info"))
    lines.append((f"        Драйвер: {info['gpu_driver']}, VRAM: {info['gpu_vram_fmt']}", "info"))
    lines.append((f"  RAM:  {info['ram_total_gb']} GB (использование: {info['ram_usage_pct']}%)", "info"))
    lines.append((f"        Частота: {info['ram_speed']} MHz, PageFile: {info['swap_total_gb']} GB", "info"))
    lines.append((f"  OS:   {info['os_name']}", "info"))
    lines.append((f"        Uptime: {info['uptime']}, Процессов: {info['process_count']}", "info"))

    # Disks
    lines.append(("", "info"))
    lines.append(("═══ ДИСКИ ═══", "header"))
    for d in info["disks"]:
        status = "warn" if d["pct"] > 85 else "good"
        lines.append((f"  {d['mount']}  {d['used_gb']}/{d['total_gb']} GB ({d['pct']}%)  [{d['fs']}]", status))

    # Services
    lines.append(("", "info"))
    lines.append(("═══ СЛУЖБЫ ═══", "header"))
    for svc_id, svc_data in info["services"].items():
        running = svc_data["running"]
        icon = "⚠" if running else "✓"
        status = "warn" if running else "good"
        state = "АКТИВНА" if running else "отключена"
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
    for adapter in info.get("net_adapters", []):
        lines.append((f"  {adapter['name']}: {adapter['speed']}", "info"))
    lines.append((f"  Трафик: ↑{info['net_sent_gb']} GB / ↓{info['net_recv_gb']} GB", "info"))

    return lines
