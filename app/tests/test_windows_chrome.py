from types import SimpleNamespace

import windows_chrome as chrome


def test_non_windows_is_noop(monkeypatch):
    monkeypatch.setattr(chrome.sys, "platform", "linux")
    chrome.set_app_identity()
    assert chrome.apply_dark_titlebar("WinBoost 4.0") is False


def test_missing_window_is_safe(monkeypatch):
    monkeypatch.setattr(chrome, "_window_for_process", lambda title: None)
    assert chrome.apply_dark_titlebar("WinBoost 4.0") is False


def test_missing_dwm_is_safe(monkeypatch):
    monkeypatch.setattr(chrome, "_window_for_process", lambda title: 123)
    monkeypatch.setattr(chrome.ctypes, "windll", SimpleNamespace())
    assert chrome.apply_dark_titlebar("WinBoost 4.0") is False


def test_rejected_attributes_do_not_refresh_or_crash(monkeypatch):
    monkeypatch.setattr(chrome, "_window_for_process", lambda title: 123)
    def reject(*args):
        return -2147024809
    monkeypatch.setattr(chrome.ctypes, "windll", SimpleNamespace(
        dwmapi=SimpleNamespace(DwmSetWindowAttribute=reject)))
    assert chrome.apply_dark_titlebar("WinBoost 4.0") is False
