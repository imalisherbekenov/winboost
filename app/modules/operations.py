"""Review helpers and an interruptible, snapshot-first execution pipeline.

This module deliberately has no Windows or UI imports, so failure paths can be
tested without changing a host's settings.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
from pathlib import Path
from threading import Event
from typing import Callable

PROFILES = {
    "Повседневный": {"system_opt", "privacy", "startup", "context_menu"},
    "Игровой": {"system_opt", "gaming", "network", "cs2_opt"},
    "Приватность": {"privacy"},
}


def profile_actions(actions: list[dict], profile: str) -> list[dict]:
    """Presets never opt into destructive or elevated-risk changes."""
    return [a for a in actions if a.get("module") in PROFILES[profile]
            and a.get("risk") in ("blue", "green") and not a.get("irreversible")]


def matches_action(action: dict, query: str = "", risk: str = "Все") -> bool:
    text = " ".join(str(action.get(key, "")) for key in ("name", "desc", "category"))
    return (query.strip().casefold() in text.casefold()
            and (risk == "Все" or (risk == "Низкий риск" and action["risk"] in ("blue", "green"))
                 or (risk == "Требует внимания" and action["risk"] in ("yellow", "red"))))


def write_report(path: Path, report: dict) -> str:
    """Replace atomically; a failed write cannot truncate an existing report."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".winboost-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, indent=2, default=str)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return str(path)


def execute_plan(actions: list[dict], *, snapshot: Callable[[], str],
                 cancel: Event, progress: Callable[[str, int, int], None],
                 error_count: Callable[[], int] = lambda: 0) -> dict:
    """Complete the current action on stop, then skip the remaining actions.

    A snapshot exception propagates BEFORE any action is invoked. Older modules
    return None and report failures through callbacks; count those as failures.
    """
    if not actions:
        raise ValueError("План не содержит действий")
    report = {"version": "4.0", "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "backup": None, "actions": [], "succeeded": 0, "failed": 0, "skipped": 0}
    if not cancel.is_set():
        report["backup"] = snapshot()
    for index, action in enumerate(actions, 1):
        row = {"name": action["name"], "module": action.get("module", ""),
               "irreversible": bool(action.get("irreversible"))}
        if cancel.is_set():
            row["status"] = "skipped"
            report["skipped"] += 1
        else:
            progress(action["name"], index, len(actions))
            before = error_count()
            try:
                result = action["run"]()
                failed = result is False or error_count() > before
                row["status"] = "failed" if failed else "succeeded"
                if failed:
                    row["error"] = "Действие сообщило об ошибке; подробности в журнале."
            except Exception as exc:
                row["status"] = "failed"
                row["error"] = str(exc)
            report[row["status"]] += 1
        report["actions"].append(row)
    report["cancelled"] = bool(report["skipped"])
    return report
