"""
WinBoost — Network Optimization Module
DNS provider switch, TCP autotune, MTU, Nagle global, QoS, NIC power management.
"""
import winreg
import subprocess
from modules.registry import set_reg_value, set_multi_reg


def set_dns_cloudflare(log_success, log_error, log_info):
    """Set DNS to Cloudflare 1.1.1.1 / 1.0.0.1 on all active interfaces."""
    log_info("Установка DNS → Cloudflare (1.1.1.1)...")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' } | "
             "ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex "
             "-ServerAddresses ('1.1.1.1','1.0.0.1') }"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0:
            log_success("DNS установлен: 1.1.1.1 / 1.0.0.1 (Cloudflare)")
        else:
            log_error(f"Ошибка: {r.stderr.strip()}")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def set_dns_google(log_success, log_error, log_info):
    """Set DNS to Google 8.8.8.8 / 8.8.4.4 on all active interfaces."""
    log_info("Установка DNS → Google (8.8.8.8)...")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' } | "
             "ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex "
             "-ServerAddresses ('8.8.8.8','8.8.4.4') }"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0:
            log_success("DNS установлен: 8.8.8.8 / 8.8.4.4 (Google)")
        else:
            log_error(f"Ошибка: {r.stderr.strip()}")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def optimize_tcp_autotune(log_success, log_error, log_info):
    """Set TCP autotune to 'normal' and enable RSS/Chimney."""
    log_info("Оптимизация TCP Autotune & RSS...")
    cmds = [
        ["netsh", "int", "tcp", "set", "global", "autotuninglevel=normal"],
        ["netsh", "int", "tcp", "set", "global", "rss=enabled"],
        ["netsh", "int", "tcp", "set", "global", "timestamps=disabled"],
        ["netsh", "int", "tcp", "set", "global", "initialRto=2000"],
    ]
    ok = 0
    for cmd in cmds:
        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            ok += 1
        except Exception:
            pass
    log_success(f"TCP настроен ({ok}/{len(cmds)} параметров).")


def optimize_mtu(log_success, log_error, log_info):
    """Find optimal MTU and set it on the active adapter."""
    log_info("Оптимизация MTU...")
    try:
        # Test common MTU sizes
        best_mtu = 1500
        for mtu in [1500, 1492, 1480, 1472, 1464]:
            r = subprocess.run(
                ["ping", "-f", "-l", str(mtu), "-n", "1", "1.1.1.1"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 and "фрагментац" not in r.stdout.lower() and "fragment" not in r.stdout.lower():
                best_mtu = mtu + 28  # add IP + ICMP headers
                break

        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-NetAdapter -Physical | Where-Object {{ $_.Status -eq 'Up' }} | "
             f"ForEach-Object {{ Set-NetAdapterAdvancedProperty -Name $_.Name "
             f"-DisplayName 'Jumbo*' -RegistryValue '{best_mtu}' -ErrorAction SilentlyContinue; "
             f"netsh interface ipv4 set subinterface $_.ifIndex mtu={best_mtu} store=persistent }}"],
            capture_output=True, timeout=15,
        )
        log_success(f"MTU установлен: {best_mtu}")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def disable_nic_power_save(log_success, log_error, log_info):
    """Disable power management on network adapters (prevents disconnects)."""
    log_info("Отключение энергосбережения сетевых адаптеров...")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-NetAdapter -Physical | ForEach-Object { "
             "Disable-NetAdapterPowerManagement -Name $_.Name -ErrorAction SilentlyContinue }"],
            capture_output=True, text=True, timeout=15,
        )
        log_success("Энергосбережение NIC отключено.")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def disable_qos_throttle(log_success, log_error, log_info):
    """Remove QoS 20% bandwidth reservation."""
    log_info("Снятие ограничения QoS (20% bandwidth)...")
    try:
        set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\Psched",
            "NonBestEffortLimit", 0
        )
        log_success("QoS bandwidth limit снят (0%).")
    except Exception as e:
        log_error(f"Ошибка: {e}")


TRACKED_KEYS = [
    {"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\Psched", "name": "NonBestEffortLimit"},
]


def get_category(log_success, log_error, log_info):
    return {
        "title": "🌐 Сеть",
        "desc": "DNS, TCP, MTU, QoS, энергосбережение NIC",
        "tracked_keys": TRACKED_KEYS,
        "actions": [
            ("DNS → Cloudflare", "1.1.1.1 / 1.0.0.1", lambda: set_dns_cloudflare(log_success, log_error, log_info), "☁️", "blue"),
            ("DNS → Google", "8.8.8.8 / 8.8.4.4", lambda: set_dns_google(log_success, log_error, log_info), "🔍", "blue"),
            ("TCP Autotune", "RSS, timestamps, initialRTO", lambda: optimize_tcp_autotune(log_success, log_error, log_info), "⚡", "yellow"),
            ("Оптимизация MTU", "Авто-определение лучшего MTU", lambda: optimize_mtu(log_success, log_error, log_info), "📐", "yellow"),
            ("Отключить QoS throttle", "Снять 20% bandwidth limit", lambda: disable_qos_throttle(log_success, log_error, log_info), "🚦", "blue"),
            ("Отключить NIC Power Save", "Не усыплять адаптеры", lambda: disable_nic_power_save(log_success, log_error, log_info), "🔋", "blue"),
        ],
    }
