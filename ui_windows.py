#!/usr/bin/env python3
from __future__ import annotations
import ctypes
import os
from ctypes import wintypes

if os.name == 'nt':
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010
    HWND_TOP = 0
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
    candidates = []
    enum_proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @enum_proc
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if _process_name(pid.value).casefold() != 'resolve.exe':
            return True
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            width = rect.right - rect.left
            height = rect.bottom - rect.top
            if width > 400 and height > 300:
                candidates.append((width * height, hwnd, rect.left, rect.top, rect.right, rect.bottom))
        return True

    user32.EnumWindows(callback, 0)
    if not candidates:
        return None
    candidates.sort(reverse=True, key=lambda x: x[0])
    return candidates[0][1]


def _geometry(root, x, y):
    root.update_idletasks()
    width = max(1, root.winfo_reqwidth())
    height = max(1, root.winfo_reqheight())
    # Explicit sign formatting is required for monitors with negative virtual-screen coordinates.
    root.geometry(f'{width}x{height}{int(x):+d}{int(y):+d}')
    root.update_idletasks()
    return width, height


def center_over_resolve(root):
    """Center a Tk top-level over visible Resolve, including monitors with negative coordinates."""
    root.update_idletasks()
    width = max(1, root.winfo_reqwidth())
    height = max(1, root.winfo_reqheight())
    resolve_hwnd = find_resolve_window() if os.name == 'nt' else None
    if resolve_hwnd:
        rect = wintypes.RECT()
        if user32.GetWindowRect(resolve_hwnd, ctypes.byref(rect)):
            x = rect.left + ((rect.right - rect.left) - width) // 2
            y = rect.top + ((rect.bottom - rect.top) - height) // 2
            _geometry(root, x, y)
            return resolve_hwnd
    x = (root.winfo_screenwidth() - width) // 2
    y = (root.winfo_screenheight() - height) // 2
    _geometry(root, x, y)
    return None


def place_above_resolve(root, resolve_hwnd=None):
    """Raise the dialog in the normal Z-order without making it globally always-on-top."""
    try:
        root.update_idletasks()
        root.deiconify()
        root.lift()
        if os.name != 'nt':
            return False
        resolve_hwnd = resolve_hwnd or find_resolve_window()
        if not resolve_hwnd:
            return False
        hwnd = int(root.winfo_id())
        if not hwnd or hwnd == resolve_hwnd:
            return False
        # Do not change GWLP_HWNDPARENT: that can let Windows reposition a Tk window.
        user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        root.lift()
        return True
    except Exception:
        return False


def center_and_place_above_resolve(root):
    # Hide the initial Tk top-left placement so the user only sees the final geometry.
    try:
        root.withdraw()
    except Exception:
        pass
    root.update_idletasks()
    resolve_hwnd = center_over_resolve(root)
    root.deiconify()
    place_above_resolve(root, resolve_hwnd)
