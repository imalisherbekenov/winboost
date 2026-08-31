"""
WinBoost — Network Optimization Module
DNS provider switch, TCP autotune, MTU, Nagle global, QoS, NIC power management.
"""
import winreg
from modules.registry import set_reg_value
from modules.winshell import run_cmd, run_ps


def set_dns_cloudflare(log_success, log_error, log_info):
    """Set DNS to Cloudflare 1.1.1.1 / 1.0.0.1 on all active interfaces."""
    log_info("Установка DNS → Cloudflare (1.1.1.1)...")
    try:
        ok, _, error = run_ps(
            "Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' } | "
            "ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex "
            "-ServerAddresses ('1.1.1.1','1.0.0.1') }",
            timeout=15,
        )
        if ok:
            log_success("DNS установлен: 1.1.1.1 / 1.0.0.1 (Cloudflare)")
        else:
            log_error(f"Ошибка: {error.strip()}")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def set_dns_google(log_success, log_error, log_info):
    """Set DNS to Google 8.8.8.8 / 8.8.4.4 on all active interfaces."""
    log_info("Установка DNS → Google (8.8.8.8)...")
    try:
        ok, _, error = run_ps(
            "Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' } | "
            "ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex "
            "-ServerAddresses ('8.8.8.8','8.8.4.4') }",
            timeout=15,
        )
        if ok:
            log_success("DNS установлен: 8.8.8.8 / 8.8.4.4 (Google)")
        else:
            log_error(f"Ошибка: {error.strip()}")
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
        command_ok, _, _ = run_cmd(cmd, timeout=10)
        if command_ok:
            ok += 1
    log_success(f"TCP настроен ({ok}/{len(cmds)} параметров).")


def optimize_mtu(log_success, log_error, log_info):
    """Find optimal MTU and set it on the active adapter."""
    log_info("Оптимизация MTU...")
    try:
        # Test common MTU sizes
        best_mtu = 1500
        for mtu in [1500, 1492, 1480, 1472, 1464]:
            ok, stdout, _ = run_cmd(["ping", "-f", "-l", str(mtu), "-n", "1", "1.1.1.1"], timeout=5)
            if ok and "фрагментац" not in stdout.lower() and "fragment" not in stdout.lower():
                best_mtu = mtu + 28  # add IP + ICMP headers
                break

        run_ps(
            f"Get-NetAdapter -Physical | Where-Object {{ $_.Status -eq 'Up' }} | "
            f"ForEach-Object {{ Set-NetAdapterAdvancedProperty -Name $_.Name "
            f"-DisplayName 'Jumbo*' -RegistryValue '{best_mtu}' -ErrorAction SilentlyContinue; "
            f"netsh interface ipv4 set subinterface $_.ifIndex mtu={best_mtu} store=persistent }}",
            timeout=15,
        )
        log_success(f"MTU установлен: {best_mtu}")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def disable_nic_power_save(log_success, log_error, log_info):
    """Disable power management on network adapters (prevents disconnects)."""
    log_info("Отключение энергосбережения сетевых адаптеров...")
    try:
        run_ps(
            "Get-NetAdapter -Physical | ForEach-Object { "
            "Disable-NetAdapterPowerManagement -Name $_.Name -ErrorAction SilentlyContinue }",
            timeout=15,
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


def get_category(log_success, log_error, log_info):
    return {
        "title": "🌐 Сеть",
        "desc": "DNS, TCP, MTU, QoS, энергосбережение NIC",
        "actions": [
            {"name": "DNS → Cloudflare", "desc": "1.1.1.1 / 1.0.0.1", "run": lambda: set_dns_cloudflare(log_success, log_error, log_info), "icon": "☁️", "risk": "blue", "irreversible": False, "effects": {"dns": True}},
            {"name": "DNS → Google", "desc": "8.8.8.8 / 8.8.4.4", "run": lambda: set_dns_google(log_success, log_error, log_info), "icon": "🔍", "risk": "blue", "irreversible": False, "effects": {"dns": True}},
            {"name": "TCP Autotune", "desc": "RSS, timestamps, initialRTO", "run": lambda: optimize_tcp_autotune(log_success, log_error, log_info), "icon": "⚡", "risk": "yellow", "irreversible": False, "effects": {}},
            {"name": "Оптимизация MTU", "desc": "Авто-определение лучшего MTU", "run": lambda: optimize_mtu(log_success, log_error, log_info), "icon": "📐", "risk": "yellow", "irreversible": False, "effects": {}},
            {"name": "Отключить QoS throttle", "desc": "Снять 20% bandwidth limit", "run": lambda: disable_qos_throttle(log_success, log_error, log_info), "icon": "🚦", "risk": "blue", "irreversible": False, "effects": {"registry": [{"hive": winreg.HKEY_LOCAL_MACHINE, "path": r"SOFTWARE\Policies\Microsoft\Windows\Psched", "name": "NonBestEffortLimit"}]}},
            {"name": "Отключить NIC Power Save", "desc": "Не усыплять адаптеры", "run": lambda: disable_nic_power_save(log_success, log_error, log_info), "icon": "🔋", "risk": "blue", "irreversible": False, "effects": {}},
        ],
    }
