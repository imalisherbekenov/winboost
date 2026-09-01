from pathlib import Path
from types import SimpleNamespace

from modules import analyzer, winshell


def _isolate_system_reads(monkeypatch, cim_result):
    ps_calls = []
    cmd_calls = []

    def fake_run_ps_json(script, timeout=20):
        ps_calls.append(script)
        return cim_result

    def fake_run_cmd(args, timeout=20):
        cmd_calls.append(args)
        return False, "", "mocked"

    monkeypatch.setattr(winshell, "run_ps_json", fake_run_ps_json)
    monkeypatch.setattr(winshell, "run_cmd", fake_run_cmd)
    monkeypatch.setattr(analyzer, "_reg_value", lambda *args, **kwargs: kwargs.get("default"))
    monkeypatch.setattr(analyzer, "_count_startup_items", lambda: 0)
    monkeypatch.setattr(analyzer.platform, "processor", lambda: "Platform fallback CPU")
    monkeypatch.setattr(analyzer.platform, "platform", lambda: "Windows-11-test")
    monkeypatch.setattr(analyzer.platform, "version", lambda: "test-build")

    monkeypatch.setattr(analyzer.psutil, "cpu_count", lambda logical=True: 8 if logical else 4)
    monkeypatch.setattr(analyzer.psutil, "cpu_freq", lambda: SimpleNamespace(current=3200))
    monkeypatch.setattr(analyzer.psutil, "cpu_percent", lambda interval=None: 12.5)
    monkeypatch.setattr(
        analyzer.psutil,
        "virtual_memory",
        lambda: SimpleNamespace(total=16 * 1024**3, used=4 * 1024**3, percent=25),
    )
    monkeypatch.setattr(
        analyzer.psutil,
        "swap_memory",
        lambda: SimpleNamespace(total=2 * 1024**3, percent=0),
    )
    monkeypatch.setattr(analyzer.psutil, "disk_partitions", lambda all=False: [])
    monkeypatch.setattr(analyzer.psutil, "boot_time", lambda: 0)
    monkeypatch.setattr(analyzer.psutil, "pids", lambda: [])
    monkeypatch.setattr(
        analyzer.psutil,
        "net_io_counters",
        lambda: SimpleNamespace(bytes_sent=0, bytes_recv=0),
    )
    monkeypatch.setattr(analyzer.psutil, "net_if_addrs", lambda: {})
    monkeypatch.setattr(analyzer.psutil, "net_if_stats", lambda: {})
    monkeypatch.setattr(analyzer.time, "time", lambda: 3600)
    return ps_calls, cmd_calls


def test_analyze_system_reads_hardware_via_cim(monkeypatch):
    ps_calls, cmd_calls = _isolate_system_reads(
        monkeypatch,
        (
            True,
            [
                {"Kind": "CPU", "Name": "CIM CPU"},
                {
                    "Kind": "Video",
                    "Name": "CIM GPU",
                    "DriverVersion": "1.2.3",
                    "AdapterRAM": 8 * 1024**3,
                },
                {"Kind": "Memory", "Speed": 6000},
            ],
            "",
        ),
    )

    info = analyzer.analyze_system()

    assert len(ps_calls) == 1
    assert "Get-CimInstance" in ps_calls[0]
    assert all(command[0].casefold() != "wmic" for command in cmd_calls)
    assert info["cpu_name"] == "CIM CPU"
    assert info["gpu_name"] == "CIM GPU"
    assert info["ram_speed"] == 6000
    assert info["cim_status"] == "ok"


def test_analyze_system_handles_cim_failure(monkeypatch):
    _isolate_system_reads(monkeypatch, (False, [], "CIM недоступен"))

    info = analyzer.analyze_system()

    assert info["cpu_name"] == "Platform fallback CPU"
    assert info["gpu_name"] == "Н/Д"
    assert info["gpu_driver"] == "Н/Д"
    assert info["gpu_vram_fmt"] == "Н/Д"
    assert info["ram_speed"] == "Н/Д"
    assert info["cim_status"] == "error"
    assert info["cim_error"] == "CIM недоступен"


def test_analyze_system_does_not_sleep(monkeypatch):
    _isolate_system_reads(monkeypatch, (True, [], ""))

    def fail_sleep(*args, **kwargs):
        raise AssertionError("analyze_system must not sleep")

    monkeypatch.setattr(analyzer.time, "sleep", fail_sleep)

    info = analyzer.analyze_system()

    assert info["cim_status"] == "no_data"
    assert Path(analyzer.__file__).read_text(encoding="utf-8").find("time.sleep") == -1


def _raise_runtime_error():
    raise RuntimeError("performance counter unavailable")


def test_analyze_system_handles_unavailable_swap(monkeypatch):
    _isolate_system_reads(monkeypatch, (True, [], ""))
    monkeypatch.setattr(analyzer.psutil, "swap_memory", _raise_runtime_error)

    info = analyzer.analyze_system()

    assert isinstance(info, dict)
    assert info["cpu_name"] == "Platform fallback CPU"
    assert info["ram_total_gb"] == 16.0
    assert info["swap_total_gb"] is None
    pagefile_line = next(text for text, _ in analyzer.format_analysis(info) if "PageFile" in text)
    assert "PageFile: недоступно" in pagefile_line
    assert "недоступно GB" not in pagefile_line


def test_analyze_system_handles_unavailable_virtual_memory(monkeypatch):
    _isolate_system_reads(monkeypatch, (True, [], ""))
    monkeypatch.setattr(analyzer.psutil, "virtual_memory", _raise_runtime_error)

    info = analyzer.analyze_system()

    assert isinstance(info, dict)
    assert info["cpu_usage"] == 12.5
    assert info["ram_total_gb"] is None
    ram_line = next(text for text, _ in analyzer.format_analysis(info) if text.startswith("  RAM:"))
    assert "RAM:  недоступно" in ram_line
    assert "недоступно GB" not in ram_line


def test_analyze_system_handles_unavailable_network_counters(monkeypatch):
    _isolate_system_reads(monkeypatch, (True, [], ""))
    monkeypatch.setattr(analyzer.psutil, "net_io_counters", _raise_runtime_error)

    info = analyzer.analyze_system()

    assert isinstance(info, dict)
    assert info["ram_total_gb"] == 16.0
    assert info["net_sent_gb"] is None
    traffic_line = next(text for text, _ in analyzer.format_analysis(info) if "Трафик:" in text)
    assert "↑недоступно / ↓недоступно" in traffic_line
    assert "недоступно GB" not in traffic_line


def test_cpu_usage_uses_reading_after_nonblocking_warmup(monkeypatch):
    _isolate_system_reads(monkeypatch, (True, [], ""))
    readings = iter([0.0, 37.5])
    intervals = []

    def fake_cpu_percent(interval=None):
        intervals.append(interval)
        return next(readings)

    monkeypatch.setattr(analyzer.psutil, "cpu_percent", fake_cpu_percent)

    info = analyzer.analyze_system()

    assert intervals == [None, None]
    assert info["cpu_usage"] == 37.5


def test_unavailable_ram_does_not_add_stability_points(monkeypatch):
    _isolate_system_reads(monkeypatch, (True, [], ""))
    healthy = analyzer.analyze_system()
    monkeypatch.setattr(analyzer.psutil, "virtual_memory", _raise_runtime_error)

    unavailable = analyzer.analyze_system()

    assert unavailable["stability_score"] < healthy["stability_score"]
