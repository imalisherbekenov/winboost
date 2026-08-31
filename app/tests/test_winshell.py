import json

from modules import backup
from modules.winshell import run_cmd, run_ps_json


def test_run_cmd_reads_active_power_scheme_guid():
    ok, stdout, stderr = run_cmd(["powercfg", "/getactivescheme"])

    assert ok, stderr
    assert backup.GUID_RE.search(stdout)


def test_run_cmd_decodes_non_ascii_console_output():
    ok, stdout, stderr = run_cmd(["cmd.exe", "/d", "/c", "echo Тест"])

    assert ok, stderr
    assert stdout.strip()


def test_run_ps_json_preserves_cyrillic():
    ok, rows, stderr = run_ps_json('@{ name = "Тест" } | ConvertTo-Json')

    assert ok, stderr
    assert json.loads(rows[0])["name"] == "Тест"
