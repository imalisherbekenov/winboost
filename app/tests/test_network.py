from modules import network


def test_optimize_mtu_converts_payload_to_mtu(monkeypatch):
    commands = []

    def fake_run_cmd(args, timeout=20):
        commands.append(args)
        if args[0] == "ping":
            assert args[3] == "1472"
            return True, "Reply from 1.1.1.1: bytes=1472 time=10ms TTL=57", ""
        if args[-1] == "subinterfaces":
            output = "\n".join([
                "   MTU  MediaSenseState   Bytes In  Bytes Out  Interface",
                "------  ---------------  ---------  ---------  ---------",
                "  1500                1       1000       2000  Ethernet",
            ])
            return True, output, ""
        return True, "Ok.", ""

    monkeypatch.setattr(network, "run_cmd", fake_run_cmd)
    successes = []
    errors = []

    network.optimize_mtu(successes.append, errors.append, lambda *_: None)

    assert errors == []
    assert any("MTU установлен: 1500" in message for message in successes)
    set_commands = [args for args in commands if "set" in args]
    assert len(set_commands) == 1
    assert "mtu=1500" in set_commands[0]
    assert all("mtu=1528" not in args for args in commands)


def test_optimize_mtu_rejects_fragmentation_text_even_with_zero_exit(monkeypatch):
    payloads = []

    def fake_run_cmd(args, timeout=20):
        if args[0] == "ping":
            payload = int(args[3])
            payloads.append(payload)
            if payload == 1472:
                return True, "Packet needs to be fragmented but DF set.", ""
            return True, f"Reply from 1.1.1.1: bytes={payload} TTL=57", ""
        if args[-1] == "subinterfaces":
            return True, "1492  1  0  0  Wi-Fi", ""
        return True, "Ok.", ""

    monkeypatch.setattr(network, "run_cmd", fake_run_cmd)
    successes = []

    network.optimize_mtu(successes.append, lambda *_: None, lambda *_: None)

    assert payloads[:2] == [1472, 1464]
    assert any("MTU установлен: 1492" in message for message in successes)
