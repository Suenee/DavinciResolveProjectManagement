#!/usr/bin/env python3
"""Independent DRPM workflow supervisor; never imports the Resolve scripting API."""
from __future__ import annotations
import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

APP = Path(__file__).resolve().parent
CHILD_FLAG = 'DRPM_SUPERVISED_CHILD'

def run(script, arguments):
    env = os.environ.copy()
    env[CHILD_FLAG] = '1'
    flags = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
    child = subprocess.Popen([sys.executable, str(script), *arguments],
                             cwd=str(APP), env=env, creationflags=flags)
    import resolve_lifecycle as life
    life.log('SUPERVISOR_CHILD_STARTED', pid=child.pid)
    root = tk.Tk()
    root.title('DRPM — Supervisor')
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=16)
    frame.pack()
    status = tk.StringVar(value='Workflow is running in an isolated process.')
    ttk.Label(frame, textvariable=status, width=55).pack(pady=(0, 10))
    ttk.Label(frame, text='Cancelling stops DRPM only, not DaVinci Resolve.').pack(pady=(0, 10))
    start = time.monotonic()
    cancelled = [False]
    finished = [False]
    def cancel():
        if child.poll() is not None:
            root.destroy()
            return
        if not messagebox.askyesno('Stop DRPM', 'Stop the DRPM worker? DaVinci Resolve will remain open.\nThe current project may be incomplete.', parent=root):
            return
        cancelled[0] = True
        life.log('SUPERVISOR_CANCEL_REQUESTED', pid=child.pid)
        child.terminate()
        try:
            child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
        life.log('SUPERVISOR_CHILD_STOPPED', pid=child.pid, returncode=child.returncode)
        root.destroy()
    ttk.Button(frame, text='Stop DRPM worker', command=cancel).pack()
    root.protocol('WM_DELETE_WINDOW', cancel)
    # Remain unobtrusive during normal short operations, then expose a
    # reliable recovery control independent of a blocked Resolve API call.
    root.withdraw()
    def poll():
        rc = child.poll()
        if rc is not None:
            finished[0] = True
            life.log('SUPERVISOR_CHILD_EXITED', pid=child.pid, returncode=rc)
            root.destroy()
            return
        elapsed = time.monotonic() - start
        if elapsed >= 20 and not root.winfo_viewable():
            root.deiconify()
            root.lift()
        status.set('DRPM worker active for %d seconds (PID %d).' % (elapsed, child.pid))
        root.after(500, poll)
    root.after(500, poll)
    root.mainloop()
    if child.poll() is None:
        # A window manager may close the supervisor unexpectedly.
        # Never leave an unmonitored worker running after its owner exits.
        child.terminate()
        try: child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
    return 130 if cancelled[0] else (child.returncode if child.returncode is not None else 1)
