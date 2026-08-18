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
    setter = getattr(user32, 'SetWindowLongPtrW', user32.SetWindowLongW)
    setter.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    setter.restype = ctypes.c_void_p
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    user32.SetWindowPos.restype = wintypes.BOOL


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
    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @enum_proc
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.IsIconic(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if _process_name(pid.value).casefold() == 'resolve.exe':
            rect = wintypes.RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                width = rect.right - rect.left
                height = rect.bottom - rect.top
                if width > 400 and height > 300:
                    found.append(hwnd)
                    return False
        return True

    user32.EnumWindows(callback, 0)
    return found[0] if found else None


def center_over_resolve(root):
    """Center a Tk top-level over the visible DaVinci Resolve window, or screen if Resolve GUI is absent."""
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    resolve_hwnd = find_resolve_window() if os.name == 'nt' else None
    if resolve_hwnd:
        rect = wintypes.RECT()
        if user32.GetWindowRect(resolve_hwnd, ctypes.byref(rect)):
            x = rect.left + max(0, ((rect.right - rect.left) - width) // 2)
            y = rect.top + max(0, ((rect.bottom - rect.top) - height) // 2)
            root.geometry(f'{width}x{height}+{x}+{y}')
            return resolve_hwnd
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    return None


def place_above_resolve(root, resolve_hwnd=None):
    """Keep a Tk top-level above visible DaVinci Resolve without global always-on-top."""
    try:
        root.update_idletasks()
        root.lift()
        if os.name != 'nt':
            return False
        resolve_hwnd = resolve_hwnd or find_resolve_window()
        if not resolve_hwnd:
            return False
        hwnd = int(root.winfo_id())
        if not hwnd or hwnd == resolve_hwnd:
            return False
        setter(hwnd, GWLP_HWNDPARENT, ctypes.c_void_p(int(resolve_hwnd)))
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        root.lift()
        return True
    except Exception:
        return False


def center_and_place_above_resolve(root):
    resolve_hwnd = center_over_resolve(root)
    place_above_resolve(root, resolve_hwnd)
