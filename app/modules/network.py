"""
WinBoost — Network Optimization Module
DNS provider switch, TCP autotune, MTU, Nagle global, QoS, NIC power management.
"""
import re
import winreg
from modules.registry import set_reg_value
from modules.winshell import run_cmd, run_ps


def _command_error(stdout: str, stderr: str) -> str:
    return (stderr or stdout).strip() or "команда завершилась с ошибкой без описания"


def _set_dns(servers: tuple[str, str]) -> tuple[bool, str]:
    quoted = ",".join(f"'{server}'" for server in servers)
    script = f"""
$adapters = @(Get-NetAdapter -Physical -ErrorAction Stop | Where-Object {{ $_.Status -eq 'Up' }})
if ($adapters.Count -eq 0) {{ throw 'Активные физические сетевые адаптеры не найдены' }}
foreach ($adapter in $adapters) {{
    Set-DnsClientServerAddress -InterfaceIndex $adapter.ifIndex -ServerAddresses @({quoted}) -ErrorAction Stop
}}
$verified = @($adapters | Where-Object {{
    $actual = @((Get-DnsClientServerAddress -InterfaceIndex $_.ifIndex -AddressFamily IPv4 -ErrorAction Stop).ServerAddresses)
    ($actual -join ',') -eq ({quoted} -join ',')
}})
if ($verified.Count -ne $adapters.Count) {{ throw 'Не все адаптеры прошли проверку DNS' }}
$verified.Count
"""
    ok, stdout, error = run_ps(script, timeout=15)
    try:
        applied = int(stdout.strip().splitlines()[-1]) if ok else 0
    except (ValueError, IndexError):
        applied = 0
    if ok and applied > 0:
        return True, ""
    return False, error.strip() or "PowerShell не подтвердил применение DNS"


def set_dns_cloudflare(log_success, log_error, log_info):
    """Set DNS to Cloudflare 1.1.1.1 / 1.0.0.1 on all active interfaces."""
    log_info("Установка DNS → Cloudflare (1.1.1.1)...")
    try:
        ok, error = _set_dns(("1.1.1.1", "1.0.0.1"))
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
        ok, error = _set_dns(("8.8.8.8", "8.8.4.4"))
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
        command_ok, stdout, error = run_cmd(cmd, timeout=10)
        if command_ok:
            ok += 1
        else:
            log_error(f"Не применён параметр {' '.join(cmd[4:])}: {_command_error(stdout, error)}")
    if ok:
        log_success(f"TCP настроен: реально применено {ok}/{len(cmds)} параметров.")
    else:
        log_error("Не удалось применить ни одного параметра TCP.")


def _ping_supports_payload(ok: bool, stdout: str) -> bool:
    output = stdout.casefold()
    failure_markers = (
        "fragment",
        "фрагментац",
        "packet needs to be fragmented",
        "request timed out",
        "превышен интервал ожидания",
        "destination host unreachable",
        "заданный узел недоступен",
    )
    return ok and "ttl=" in output and not any(marker in output for marker in failure_markers)


def _active_ipv4_subinterfaces() -> tuple[list[str], str]:
    ok, stdout, error = run_cmd(["netsh", "interface", "ipv4", "show", "subinterfaces"], timeout=10)
    if not ok:
        return [], _command_error(stdout, error)
    interfaces = []
    row_pattern = re.compile(r"^\s*(\d+)\s+(\d+)\s+\d+\s+\d+\s+(.+?)\s*$")
    for line in stdout.splitlines():
        match = row_pattern.match(line)
        if not match:
            continue
        current_mtu, media_state, name = match.groups()
        if int(current_mtu) <= 65535 and media_state == "1":
            interfaces.append(name)
    return interfaces, "" if interfaces else "Активные IPv4-интерфейсы не найдены"


def optimize_mtu(log_success, log_error, log_info):
    """Find optimal MTU and set it on the active adapter."""
    log_info("Оптимизация MTU...")
    try:
        best_mtu = None
        last_ping_error = ""
        for payload in range(1472, 1399, -8):
            ok, stdout, error = run_cmd(
                ["ping", "-f", "-l", str(payload), "-n", "1", "1.1.1.1"],
                timeout=5,
            )
            output = "\n".join(part for part in (stdout, error) if part)
            if _ping_supports_payload(ok, output):
                best_mtu = payload + 28
                break
            last_ping_error = output.strip()
        if best_mtu is None:
            reason = last_ping_error or "ping не вернул ответ с TTL"
            log_error(f"Не удалось определить MTU: {reason}")
            return

        interfaces, error = _active_ipv4_subinterfaces()
        if not interfaces:
            log_error(f"Не удалось применить MTU: {error}")
            return
        applied = 0
        for interface in interfaces:
            ok, stdout, error = run_cmd(
                [
                    "netsh", "interface", "ipv4", "set", "subinterface", interface,
                    f"mtu={best_mtu}", "store=persistent",
                ],
                timeout=10,
            )
            if ok:
                applied += 1
            else:
                log_error(f"MTU для {interface} не установлен: {_command_error(stdout, error)}")
        if applied:
            log_success(f"MTU установлен: {best_mtu} (интерфейсов: {applied}/{len(interfaces)}).")
        else:
            log_error(f"MTU {best_mtu} не удалось применить ни к одному интерфейсу.")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def disable_nic_power_save(log_success, log_error, log_info):
    """Disable power management on network adapters (prevents disconnects)."""
    log_info("Отключение энергосбережения сетевых адаптеров...")
    try:
        ok, stdout, error = run_ps(
            "$adapters = @(Get-NetAdapter -Physical -ErrorAction Stop); "
            "if ($adapters.Count -eq 0) { throw 'Физические адаптеры не найдены' }; "
            "$adapters | ForEach-Object { Disable-NetAdapterPowerManagement -Name $_.Name -ErrorAction Stop }; "
            "$adapters.Count",
            timeout=15,
        )
        if ok and stdout.strip():
            log_success(f"Энергосбережение NIC отключено (адаптеров: {stdout.strip().splitlines()[-1]}).")
        else:
            log_error(f"Ошибка: {error.strip() or 'PowerShell не подтвердил изменение адаптеров'}")
    except Exception as e:
        log_error(f"Ошибка: {e}")


def disable_qos_throttle(log_success, log_error, log_info):
    """Remove QoS 20% bandwidth reservation."""
    log_info("Снятие ограничения QoS (20% bandwidth)...")
    try:
        changed = set_reg_value(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Policies\Microsoft\Windows\Psched",
            "NonBestEffortLimit", 0
        )
        if changed:
            log_success("QoS bandwidth limit снят (0%).")
        else:
            log_error("Не удалось записать параметр QoS в реестр (требуются права администратора).")
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
