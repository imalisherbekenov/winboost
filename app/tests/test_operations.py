import json
from threading import Event

import pytest

from modules.operations import execute_plan, matches_action, profile_actions, write_report


def action(run=lambda: True, **kwargs):
    return {"name": "Включить игровой режим", "desc": "Приоритет для игр", "module": "gaming",
            "category": "Игры", "risk": "blue", "irreversible": False, "run": run, **kwargs}


def test_snapshot_failure_prevents_every_mutation():
    called = []
    def fail():
        raise OSError("disk full")
    with pytest.raises(OSError):
        execute_plan([action(lambda: called.append(1))], snapshot=fail,
                     cancel=Event(), progress=lambda *args: None)
    assert called == []


def test_stop_finishes_current_action_and_preserves_snapshot():
    stop = Event()
    calls = []
    def first():
        calls.append("first")
        stop.set()
        return True
    report = execute_plan([action(first), action(lambda: calls.append("second"))],
                          snapshot=lambda: "snapshot.json", cancel=stop, progress=lambda *args: None)
    assert calls == ["first"]
    assert report["backup"] == "snapshot.json"
    assert (report["succeeded"], report["skipped"], report["cancelled"]) == (1, 1, True)


def test_error_callback_with_none_return_is_not_success():
    errors = []
    report = execute_plan([action(lambda: errors.append("access denied"))], snapshot=lambda: "backup",
                          cancel=Event(), progress=lambda *args: None, error_count=lambda: len(errors))
    assert report["failed"] == 1
    assert report["succeeded"] == 0


def test_failures_are_recorded_and_do_not_hide_later_results():
    def fail():
        raise RuntimeError("denied")
    report = execute_plan([action(fail), action(lambda: False), action()], snapshot=lambda: "backup",
                          cancel=Event(), progress=lambda *args: None)
    assert [row["status"] for row in report["actions"]] == ["failed", "failed", "succeeded"]
    assert report["actions"][0]["error"] == "denied"


def test_cancel_before_start_does_not_create_snapshot_or_run():
    stop = Event()
    stop.set()
    report = execute_plan([action(lambda: pytest.fail("must not run"))],
                          snapshot=lambda: pytest.fail("must not snapshot"),
                          cancel=stop, progress=lambda *args: None)
    assert report["skipped"] == 1
    assert report["backup"] is None


def test_presets_exclude_irreversible_and_risky_actions():
    actions = [action(), action(irreversible=True), action(risk="yellow"), action(module="privacy")]
    assert profile_actions(actions, "Игровой") == [actions[0]]
    assert profile_actions(actions, "Приватность") == [actions[3]]


def test_search_cyrillic_case_and_risk_filter():
    assert matches_action(action(), "  ИГРОВОЙ  ", "Низкий риск")
    assert matches_action(action(), "Игры")
    assert not matches_action(action(), "игровой", "Требует внимания")
    assert not matches_action(action(), "несуществующее")


def test_report_roundtrip_and_failed_serialization_preserves_existing(tmp_path):
    path = tmp_path / "reports" / "report.json"
    write_report(path, {"name": "Проверка", "failed": 1})
    assert json.loads(path.read_text(encoding="utf-8"))["name"] == "Проверка"
    cyclic = {}; cyclic["self"] = cyclic
    with pytest.raises(ValueError):
        write_report(path, cyclic)
    assert json.loads(path.read_text(encoding="utf-8"))["failed"] == 1
    assert list(path.parent.glob("*.tmp")) == []
