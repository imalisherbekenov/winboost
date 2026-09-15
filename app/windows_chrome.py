"""Native Windows branding; cosmetic failures must never stop the app."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import os
import sys

_LOG = logging.getLogger(__name__)


def set_app_identity() -> None:
    if sys.platform != "win32":
        return
    try:
        setter = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        setter.argtypes = [wintypes.LPCWSTR]
        setter.restype = ctypes.c_long
        setter("WinBoost.Desktop")
    except (AttributeError, OSError):
        _LOG.debug("Windows app identity unavailable", exc_info=True)


def _window_for_process(title: str) -> int | None:
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    found = []

    @callback_type
    def visit(hwnd, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == os.getpid():
            text = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, text, len(text))
            if text.value == title:
                found.append(hwnd)
                return False
        return True

    user32.EnumWindows(visit, 0)
    return found[0] if found else None


def apply_dark_titlebar(title: str) -> bool:
    if sys.platform != "win32":
        return False
    try:
        hwnd = _window_for_process(title)
        if not hwnd:
            return False
        setter = ctypes.windll.dwmapi.DwmSetWindowAttribute
        setter.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        setter.restype = ctypes.c_long
        # COLORREF stores RGB in the low-to-high bytes, unlike CSS hex colors.
        attributes = [(20, 1), (35, 0x131111), (36, 0xE9F0F3), (34, 0x3F3939)]
        applied = False
        for attribute, value in attributes:
            data = wintypes.DWORD(value)
            result = setter(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data))
            applied |= result == 0
            if result != 0:
                _LOG.debug("DWM attribute %s unavailable: %s", attribute, result)
        if applied:
            refresh = ctypes.windll.user32.SetWindowPos
            refresh.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
            refresh(hwnd, None, 0, 0, 0, 0, 0x0037)
        return applied
    except (AttributeError, OSError):
        _LOG.debug("Native dark title bar unavailable", exc_info=True)
        return False
