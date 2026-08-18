#!/usr/bin/env python3
from __future__ import annotations
import ctypes
import os
from ctypes import wintypes

if os.name == 'nt':
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    GWLP_HWNDPARENT = -8
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010


def _process_name(pid):
    if os.name != 'nt':
        return ''
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ''
    try:
        size = wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value)
        return ''
    finally:
        kernel32.CloseHandle(handle)


def find_resolve_window():
    if os.name != 'nt':
        return None
    found = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @EnumWindowsProc
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if _process_name(pid.value).casefold() == 'resolve.exe':
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(callback, 0)
    return found[0] if found else None


def place_above_resolve(root):
    """Keep a Tk top-level directly above visible DaVinci Resolve without global always-on-top."""
    try:
        root.update_idletasks()
        root.lift()
        if os.name != 'nt':
            return False
        resolve_hwnd = find_resolve_window()
        if not resolve_hwnd:
            return False
        hwnd = int(root.winfo_id())
        if not hwnd or hwnd == resolve_hwnd:
            return False
        setter = getattr(user32, 'SetWindowLongPtrW', user32.SetWindowLongW)
        setter(hwnd, GWLP_HWNDPARENT, resolve_hwnd)
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        root.lift()
        return True
    except Exception:
        return False
