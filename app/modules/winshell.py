"""Quiet, consistent wrappers for Windows command-line tools."""

from __future__ import annotations

import json
import subprocess
from typing import Any, Sequence


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _failure(exc: Exception) -> tuple[bool, str, str]:
    stdout = getattr(exc, "stdout", "") or ""
    stderr = getattr(exc, "stderr", "") or str(exc)
    return False, str(stdout), str(stderr)


def run_ps(script: str, timeout: int = 20) -> tuple[bool, str, str]:
    """Run PowerShell. Returns ``(ok, stdout, stderr)``."""
    args = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]
    try:
        result = subprocess.run(
            args,
            creationflags=CREATE_NO_WINDOW,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _failure(exc)
    stderr = result.stderr or ""
    return result.returncode == 0 and not stderr.strip(), result.stdout or "", stderr


def run_ps_json(script: str, timeout: int = 20) -> tuple[bool, list[Any], str]:
    """Run PowerShell, parse compressed JSON output, and normalize it to a list."""
    wrapped = f"$WinBoostResult = & {{ {script} }}; $WinBoostResult | ConvertTo-Json -Depth 4 -Compress"
    ok, stdout, stderr = run_ps(wrapped, timeout=timeout)
    if not ok:
        return False, [], stderr
    if not stdout.strip():
        return True, [], ""
    try:
        value = json.loads(stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        return False, [], f"Invalid PowerShell JSON output: {exc}"
    if value is None:
        return True, [], ""
    return True, value if isinstance(value, list) else [value], ""


def run_cmd(args: Sequence[str], timeout: int = 20) -> tuple[bool, str, str]:
    """Run a non-PowerShell command without displaying a console window."""
    try:
        result = subprocess.run(
            list(args),
            creationflags=CREATE_NO_WINDOW,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return _failure(exc)
    stderr = result.stderr or ""
    return result.returncode == 0 and not stderr.strip(), result.stdout or "", stderr
