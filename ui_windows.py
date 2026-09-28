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
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SW_RESTORE = 9
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



def zorder_snapshot(app_hwnd=None,limit=20):
    """Return Windows Z-order diagnostics. EnumWindows enumerates top-level windows from top to bottom."""
    if os.name != 'nt':
        return {'platform':'non-windows'}
    rows=[]
    enum_proc=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    GWL_EXSTYLE=-20; WS_EX_TOPMOST=0x00000008
    foreground=int(user32.GetForegroundWindow() or 0)
    resolve=int(find_resolve_window() or 0)
    @enum_proc
    def callback(hwnd,_):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        length=user32.GetWindowTextLengthW(hwnd);buf=ctypes.create_unicode_buffer(length+1);user32.GetWindowTextW(hwnd,buf,length+1)
        rows.append({'z':len(rows),'hwnd':int(hwnd),'pid':pid.value,'process':_process_name(pid.value),'title':buf.value[:160],
                     'topmost':bool(user32.GetWindowLongW(hwnd,GWL_EXSTYLE)&WS_EX_TOPMOST),
                     'foreground':int(hwnd)==foreground,'app':bool(app_hwnd and int(hwnd)==int(app_hwnd)),'resolve':int(hwnd)==resolve})
        return len(rows)<max(1,limit)
    user32.EnumWindows(callback,0)
    def idx(h):return next((r['z'] for r in rows if h and r['hwnd']==int(h)),None)
    return {'foreground_hwnd':foreground,'app_hwnd':int(app_hwnd or 0),'resolve_hwnd':resolve,
            'app_z':idx(app_hwnd),'resolve_z':idx(resolve),'windows':rows}

def prepare_dialog(root,parent=None):
    try:
        if parent is not None:
            root.transient(parent)
        root.attributes('-topmost', True)
        root.after(350, lambda: root.attributes('-topmost', False) if root.winfo_exists() else None)
    except Exception:
        pass


def activate_window(root):
    """Restore and foreground a Tk window without leaving it globally always-on-top."""
    try:
        root.update_idletasks()
        root.deiconify()
        root.lift()
        if os.name != 'nt':
            root.focus_force()
            return True
        hwnd = int(root.winfo_id())
        if not hwnd:
            return False
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        # A short TOPMOST pulse reliably moves the window above Resolve, then immediately
        # returns it to the normal Z-order so it does not stay above unrelated applications.
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        root.lift()
        root.focus_force()
        return True
    except Exception:
        return False


def place_above_resolve(root, resolve_hwnd=None):
    """Activate the window above Resolve while keeping normal long-term Z-order."""
    return activate_window(root)


def center_and_place_above_resolve(root):
    # Hide the initial Tk top-left placement so the user only sees the final geometry.
    try:
        root.withdraw()
    except Exception:
        pass
    root.update_idletasks()
    resolve_hwnd = center_over_resolve(root)
    root.deiconify()
    prepare_dialog(root)
    place_above_resolve(root, resolve_hwnd)
    try:
        root.after(120, lambda: activate_window(root) if root.winfo_exists() else None)
    except Exception:
        pass
