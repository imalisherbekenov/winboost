import json
import os
import winreg

import pytest

from modules import backup


TEST_KEY = r"Software\WinBoostTest"


def _clear_test_key():
    try:
        with winreg.OpenKeyEx(
            winreg.HKEY_CURRENT_USER,
            TEST_KEY,
            0,
            winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE,
        ) as key:
            while True:
                try:
                    name, _, _ = winreg.EnumValue(key, 0)
                except OSError:
                    break
                winreg.DeleteValue(key, name)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, TEST_KEY)
    except FileNotFoundError:
        pass


@pytest.fixture
def test_registry_key():
    _clear_test_key()
    try:
        key = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, TEST_KEY, 0, winreg.KEY_SET_VALUE
        )
    except PermissionError:
        pytest.skip("This environment blocks writes to the isolated HKCU test key")
    with key:
        winreg.SetValueEx(key, "Existing", 0, winreg.REG_SZ, "original")
    yield TEST_KEY
    _clear_test_key()


@pytest.fixture
def isolated_backup_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "BACKUP_DIR", tmp_path)
    return tmp_path


def test_registry_round_trip_existing_and_absent(test_registry_key, isolated_backup_dir):
    effects = {"registry": [
        {"hive": winreg.HKEY_CURRENT_USER, "path": test_registry_key, "name": "Existing"},
        {"hive": winreg.HKEY_CURRENT_USER, "path": test_registry_key, "name": "CreatedLater"},
    ]}
    snapshot_path = backup.capture(effects, "round-trip")

    with winreg.OpenKeyEx(
        winreg.HKEY_CURRENT_USER, test_registry_key, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, "Existing", 0, winreg.REG_SZ, "changed")
        winreg.SetValueEx(key, "CreatedLater", 0, winreg.REG_DWORD, 42)

    result = backup.restore(snapshot_path)

    with winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, test_registry_key, 0, winreg.KEY_READ) as key:
        assert winreg.QueryValueEx(key, "Existing") == ("original", winreg.REG_SZ)
        with pytest.raises(FileNotFoundError):
            winreg.QueryValueEx(key, "CreatedLater")
    assert result["registry"] == 2


def test_capture_with_effects_populates_snapshot(isolated_backup_dir):
    path = backup.capture(
        {"registry": [{
            "hive": winreg.HKEY_CURRENT_USER,
            "path": TEST_KEY,
            "name": "Existing",
        }]},
        "non-empty",
    )

    with open(path, encoding="utf-8") as handle:
        snapshot = json.load(handle)

    assert snapshot["registry"]
    assert snapshot["registry"][0]["name"] == "Existing"


def test_ensure_baseline_does_not_overwrite(isolated_backup_dir, monkeypatch):
    expected = {
        "version": 2,
        "timestamp": "fixed",
        "label": "expert",
        "kind": "baseline",
        "registry": [],
        "services": [],
        "tasks": [],
        "power": {},
        "appx": [],
        "dns": [],
    }
    monkeypatch.setattr(backup, "_build_snapshot", lambda *args, **kwargs: expected)

    path = backup.ensure_baseline()
    old_time = 1_600_000_000
    os.utime(path, (old_time, old_time))
    before_mtime = os.stat(path).st_mtime_ns
    before_content = open(path, "rb").read()

    assert backup.ensure_baseline() == path
    assert os.stat(path).st_mtime_ns == before_mtime
    assert open(path, "rb").read() == before_content


def test_restore_legacy_version_one_file(tmp_path):
    legacy_path = tmp_path / "legacy.json"
    legacy_path.write_text(json.dumps({
        "timestamp": "legacy",
        "label": "old",
        "entries": [{
            "hive": "HKCU",
            "hive_int": int(winreg.HKEY_CURRENT_USER),
            "path": TEST_KEY,
            "name": "MissingLegacyValue",
            "value": None,
            "type": None,
            "exists": False,
        }],
    }), encoding="utf-8")

    result = backup.restore(str(legacy_path))

    assert result["registry"] == 1
