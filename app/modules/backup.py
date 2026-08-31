"""Versioned WinBoost snapshots and rollback support."""

from __future__ import annotations

import base64
import datetime
import json
import logging
import os
import re
import winreg
from pathlib import Path
from typing import Any, Callable

from modules.winshell import run_cmd, run_ps, run_ps_json


logger = logging.getLogger("winboost")
BACKUP_DIR = Path(os.environ.get("APPDATA", ".")) / "WinBoost" / "backups"
GUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b")

HIVE_NAMES = {
    winreg.HKEY_LOCAL_MACHINE: "HKLM",
    winreg.HKEY_CURRENT_USER: "HKCU",
    winreg.HKEY_CLASSES_ROOT: "HKCR",
}
HIVE_VALUES = {name: hive for hive, name in HIVE_NAMES.items()}
EFFECT_KEYS = ("registry", "services", "tasks", "power", "appx", "dns")


def normalize_effects(effects: dict | None = None) -> dict:
    """Return a copy containing every supported effect section."""
    effects = effects or {}
    return {
        "registry": list(effects.get("registry") or []),
        "services": list(effects.get("services") or []),
        "tasks": list(effects.get("tasks") or []),
        "power": bool(effects.get("power", False)),
        "appx": list(effects.get("appx") or []),
        "dns": bool(effects.get("dns", False)),
    }


def merge_effects(*items: dict) -> dict:
    """Merge action effects while removing duplicate concrete targets."""
    merged = normalize_effects()
    seen_registry: set[str] = set()
    for item in items:
        normalized = normalize_effects(item)
        for entry in normalized["registry"]:
            token = json.dumps(entry, sort_keys=True, default=int)
            if token not in seen_registry:
                merged["registry"].append(entry)
                seen_registry.add(token)
        for section in ("services", "tasks", "appx"):
            for value in normalized[section]:
                if value not in merged[section]:
                    merged[section].append(value)
        merged["power"] = merged["power"] or normalized["power"]
        merged["dns"] = merged["dns"] or normalized["dns"]
    return merged


def _ensure_backup_dir() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _json_registry_value(value: Any) -> tuple[Any, str | None]:
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii"), "base64"
    return value, None


def _restore_registry_value(entry: dict) -> Any:
    value = entry.get("value")
    if entry.get("value_encoding") == "base64" and isinstance(value, str):
        return base64.b64decode(value)
    return value


def read_current_value(hive: int, path: str, name: str) -> dict:
    """Read one registry value, retaining enough information to restore absence."""
    try:
        with winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ) as key:
            value, reg_type = winreg.QueryValueEx(key, name)
        value, encoding = _json_registry_value(value)
        result = {"value": value, "type": reg_type, "exists": True}
        if encoding:
            result["value_encoding"] = encoding
        return result
    except OSError:
        return {"value": None, "type": None, "exists": False}


def _enum_registry_values(hive: int, path: str) -> list[dict]:
    entries: list[dict] = []
    try:
        with winreg.OpenKeyEx(hive, path, 0, winreg.KEY_READ) as key:
            index = 0
            while True:
                try:
                    name, _, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                entries.append({"hive": hive, "path": path, "name": name})
                index += 1
    except OSError:
        pass
    return entries


def _expand_registry_targets(targets: list[dict]) -> list[dict]:
    expanded: list[dict] = []
    for target in targets:
        dynamic = target.get("dynamic")
        if dynamic == "tcp_interfaces":
            base = target.get("path", r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces")
            names = target.get("names", ["TcpAckFrequency", "TCPNoDelay"])
            try:
                with winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, base, 0, winreg.KEY_READ) as key:
                    index = 0
                    while True:
                        try:
                            subkey = winreg.EnumKey(key, index)
                        except OSError:
                            break
                        expanded.extend(
                            {"hive": winreg.HKEY_LOCAL_MACHINE, "path": f"{base}\\{subkey}", "name": name}
                            for name in names
                        )
                        index += 1
            except OSError:
                pass
        elif dynamic == "registry_values":
            expanded.extend(_enum_registry_values(target["hive"], target["path"]))
        else:
            expanded.append(target)

    unique: list[dict] = []
    seen: set[tuple[int, str, str]] = set()
    for target in expanded:
        token = (int(target["hive"]), target["path"], target["name"])
        if token not in seen:
            unique.append(target)
            seen.add(token)
    return unique


def _capture_registry(targets: list[dict]) -> list[dict]:
    result = []
    for target in _expand_registry_targets(targets):
        hive = target["hive"]
        result.append(
            {
                "hive": HIVE_NAMES.get(hive, str(int(hive))),
                "hive_int": int(hive),
                "path": target["path"],
                "name": target["name"],
                **read_current_value(hive, target["path"], target["name"]),
            }
        )
    return result


def _capture_services(names: list[str]) -> list[dict]:
    services = []
    for name in names:
        safe_name = name.replace("'", "''")
        script = (
            f'Get-CimInstance Win32_Service -Filter "Name=\'{safe_name}\'" '
            "-ErrorAction SilentlyContinue | Select-Object Name,StartMode,State"
        )
        ok, rows, _ = run_ps_json(script)
        if ok:
            for row in rows:
                services.append(
                    {
                        "name": row.get("Name", name),
                        "start_mode": row.get("StartMode"),
                        "state": row.get("State"),
                    }
                )
    return services


def _split_task_name(name: str) -> tuple[str, str]:
    normalized = "\\" + name.lstrip("\\")
    path, _, task_name = normalized.rpartition("\\")
    return (path + "\\") if path else "\\", task_name


def _capture_tasks(names: list[str]) -> list[dict]:
    tasks = []
    for full_name in names:
        task_path, task_name = _split_task_name(full_name)
        script = (
            f"Get-ScheduledTask -TaskPath {_ps_quote(task_path)} -TaskName {_ps_quote(task_name)} "
            "-ErrorAction SilentlyContinue | Select-Object TaskPath,TaskName,State"
        )
        ok, rows, _ = run_ps_json(script)
        if ok:
            for row in rows:
                name = f"{row.get('TaskPath', task_path)}{row.get('TaskName', task_name)}"
                tasks.append({"name": name, "state": str(row.get("State", ""))})
    return tasks


def _capture_power(enabled: bool) -> dict:
    if not enabled:
        return {}
    _, stdout, stderr = run_cmd(["powercfg", "/getactivescheme"])
    match = GUID_RE.search(f"{stdout}\n{stderr}")
    return {"active_guid": match.group(0)} if match else {}


def _capture_appx(names: list[str]) -> list[dict]:
    packages = []
    for name in names:
        script = (
            f"Get-AppxPackage -Name {_ps_quote('*' + name + '*')} -AllUsers -ErrorAction SilentlyContinue | "
            "Select-Object Name,PackageFullName"
        )
        ok, rows, _ = run_ps_json(script)
        if ok:
            packages.extend(
                {
                    "name": row.get("Name", name),
                    "package_full_name": row.get("PackageFullName", ""),
                }
                for row in rows
            )
    return packages


def _capture_dns(enabled: bool) -> list[dict]:
    if not enabled:
        return []
    script = r"""
Get-DnsClientServerAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | ForEach-Object {
    $adapter = Get-NetAdapter -InterfaceIndex $_.InterfaceIndex -ErrorAction SilentlyContinue
    $staticServers = $null
    if ($adapter) {
        $regPath = 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\' + $adapter.InterfaceGuid
        $staticServers = (Get-ItemProperty -LiteralPath $regPath -Name NameServer -ErrorAction SilentlyContinue).NameServer
    }
    [pscustomobject]@{
        InterfaceIndex = $_.InterfaceIndex
        InterfaceAlias = $_.InterfaceAlias
        ServerAddresses = @($_.ServerAddresses)
        Dhcp = [string]::IsNullOrWhiteSpace([string]$staticServers)
    }
}
"""
    ok, rows, _ = run_ps_json(script)
    if not ok:
        return []
    result = []
    for row in rows:
        servers = row.get("ServerAddresses") or []
        if isinstance(servers, str):
            servers = [servers]
        result.append(
            {
                "if_index": row.get("InterfaceIndex"),
                "if_alias": row.get("InterfaceAlias", ""),
                "servers": servers,
                "dhcp": bool(row.get("Dhcp", False)),
            }
        )
    return result


def _build_snapshot(effects: dict, label: str, kind: str, timestamp: str | None = None) -> dict:
    normalized = normalize_effects(effects)
    timestamp = timestamp or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return {
        "version": 2,
        "timestamp": timestamp,
        "label": label,
        "kind": kind,
        "registry": _capture_registry(normalized["registry"]),
        "services": _capture_services(normalized["services"]),
        "tasks": _capture_tasks(normalized["tasks"]),
        "power": _capture_power(normalized["power"]),
        "appx": _capture_appx(normalized["appx"]),
        "dns": _capture_dns(normalized["dns"]),
    }


def _write_snapshot(path: Path, snapshot: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, ensure_ascii=False)
    logger.info("Backup saved: %s", path)
    return str(path)


def capture(effects: dict, label: str, kind: str = "change") -> str:
    """Capture all state described by an action's effects."""
    backup_dir = _ensure_backup_dir()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", label).strip("_") or "manual"
    filepath = backup_dir / f"winboost_backup_{safe_label}_{timestamp}.json"
    suffix = 2
    while filepath.exists():
        filepath = backup_dir / f"winboost_backup_{safe_label}_{timestamp}_{suffix}.json"
        suffix += 1
    return _write_snapshot(filepath, _build_snapshot(effects, label, kind, timestamp))


def _log(log_fn: Callable | None, message: str) -> None:
    if log_fn:
        log_fn(message)


def _restore_registry(entries: list[dict], result: dict, log_fn: Callable | None) -> None:
    for entry in entries:
        hive = entry.get("hive_int") or HIVE_VALUES.get(entry.get("hive"))
        if hive is None:
            result["skipped"].append(f"Unknown registry hive for {entry.get('path')}\\{entry.get('name')}")
            continue
        path, name = entry["path"], entry["name"]
        try:
            if entry.get("exists", False):
                with winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, name, 0, entry["type"], _restore_registry_value(entry))
                _log(log_fn, f"Restored registry: {path}\\{name}")
            else:
                try:
                    with winreg.OpenKeyEx(hive, path, 0, winreg.KEY_SET_VALUE) as key:
                        winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
                _log(log_fn, f"Removed registry value created after snapshot: {path}\\{name}")
            result["registry"] += 1
        except OSError as exc:
            result["skipped"].append(f"Registry {path}\\{name}: {exc}")


def _restore_services(entries: list[dict], result: dict, log_fn: Callable | None) -> None:
    start_modes = {"Auto": "auto", "Automatic": "auto", "Manual": "demand", "Disabled": "disabled"}
    for entry in entries:
        name = entry["name"]
        mode = start_modes.get(entry.get("start_mode"))
        if not mode:
            result["skipped"].append(f"Service {name}: unsupported start mode {entry.get('start_mode')}")
            continue
        ok, _, error = run_cmd(["sc.exe", "config", name, "start=", mode])
        state_cmd = "start" if str(entry.get("state", "")).lower() == "running" else "stop"
        state_ok, _, state_error = run_cmd(["sc.exe", state_cmd, name])
        if ok and state_ok:
            result["services"] += 1
            _log(log_fn, f"Restored service: {name}")
        else:
            result["skipped"].append(f"Service {name}: {(error or state_error).strip()}")


def _restore_tasks(entries: list[dict], result: dict, log_fn: Callable | None) -> None:
    for entry in entries:
        task_path, task_name = _split_task_name(entry["name"])
        command = "Disable-ScheduledTask" if str(entry.get("state", "")).lower() == "disabled" else "Enable-ScheduledTask"
        script = (
            f"{command} -TaskPath {_ps_quote(task_path)} -TaskName {_ps_quote(task_name)} "
            "-ErrorAction Stop | Out-Null"
        )
        ok, _, error = run_ps(script)
        if ok:
            result["tasks"] += 1
            _log(log_fn, f"Restored scheduled task: {entry['name']}")
        else:
            result["skipped"].append(f"Task {entry['name']}: {error.strip()}")


def _restore_power(entry: dict, result: dict, log_fn: Callable | None) -> None:
    guid = entry.get("active_guid") if entry else None
    if not guid:
        return
    ok, _, error = run_cmd(["powercfg", "/setactive", guid])
    if ok:
        result["power"] += 1
        _log(log_fn, f"Restored active power plan: {guid}")
    else:
        result["skipped"].append(f"Power plan {guid}: {error.strip()}")


def _restore_dns(entries: list[dict], result: dict, log_fn: Callable | None) -> None:
    for entry in entries:
        index = entry.get("if_index")
        if entry.get("dhcp"):
            script = f"Set-DnsClientServerAddress -InterfaceIndex {int(index)} -ResetServerAddresses -ErrorAction Stop"
        else:
            addresses = ",".join(_ps_quote(str(value)) for value in entry.get("servers", []))
            script = (
                f"Set-DnsClientServerAddress -InterfaceIndex {int(index)} "
                f"-ServerAddresses @({addresses}) -ErrorAction Stop"
            )
        ok, _, error = run_ps(script)
        if ok:
            result["dns"] += 1
            _log(log_fn, f"Restored DNS: {entry.get('if_alias') or index}")
        else:
            result["skipped"].append(f"DNS interface {index}: {error.strip()}")


def restore(filepath: str, log_fn: Callable | None = None) -> dict:
    """Restore a version 2 snapshot, or a legacy registry-only version 1 file."""
    with open(filepath, "r", encoding="utf-8") as handle:
        snapshot = json.load(handle)
    version = snapshot.get("version", 1)
    result = {"registry": 0, "services": 0, "tasks": 0, "power": 0, "dns": 0, "skipped": []}
    if version == 1:
        _restore_registry(snapshot.get("entries", []), result, log_fn)
        return result
    if version != 2:
        raise ValueError(f"Unsupported backup version: {version}")
    _restore_registry(snapshot.get("registry", []), result, log_fn)
    _restore_services(snapshot.get("services", []), result, log_fn)
    _restore_tasks(snapshot.get("tasks", []), result, log_fn)
    _restore_power(snapshot.get("power", {}), result, log_fn)
    _restore_dns(snapshot.get("dns", []), result, log_fn)
    for package in snapshot.get("appx", []):
        result["skipped"].append(
            f"Appx {package.get('name', 'package')} cannot be restored automatically; reinstall it from Microsoft Store."
        )
    return result


def _all_module_effects() -> dict:
    from modules import ALL_MODULES

    effects = []
    no_log = lambda *_: None
    for module in ALL_MODULES:
        category = module.get_category(no_log, no_log, no_log)
        effects.extend(action["effects"] for action in category["actions"])
    return merge_effects(*effects)


def ensure_baseline() -> str:
    """Create the broad baseline once. Existing baseline content is never touched."""
    filepath = _ensure_backup_dir() / "baseline.json"
    if filepath.exists():
        return str(filepath)
    snapshot = _build_snapshot(_all_module_effects(), "expert", "baseline")
    try:
        with filepath.open("x", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2, ensure_ascii=False)
    except FileExistsError:
        pass
    return str(filepath)


def list_backups() -> list[dict]:
    """List version 1 and version 2 backup files, including the baseline."""
    backups = []
    for path in _ensure_backup_dir().glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            version = data.get("version", 1)
            sections = data.get("entries", []) if version == 1 else sum(
                (len(data.get(key, [])) for key in ("registry", "services", "tasks", "appx", "dns")),
                1 if data.get("power") else 0,
            )
            backups.append(
                {
                    "file": str(path),
                    "label": data.get("label", ""),
                    "timestamp": data.get("timestamp", ""),
                    "kind": data.get("kind", "change" if version == 2 else "legacy"),
                    "version": version,
                    "entries_count": len(sections) if isinstance(sections, list) else sections,
                }
            )
        except (OSError, ValueError, TypeError):
            continue
    return sorted(backups, key=lambda item: (item["timestamp"], item["file"]), reverse=True)


# Compatibility for the current GUI until its contract is migrated in Phase 2.
def create_backup(changes: list[dict], label: str = "manual") -> str:
    return capture({"registry": changes}, label)


def restore_backup(filepath: str, log_fn: Callable | None = None) -> int:
    result = restore(filepath, log_fn)
    return sum(result[key] for key in ("registry", "services", "tasks", "power", "dns"))
