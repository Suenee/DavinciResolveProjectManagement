#!/usr/bin/env python3
"""Independent Media Pool API watchdog. No Resolve API imports or calls."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime

APP = Path(__file__).resolve().parent

def emit(event, **fields):
    line = datetime.now().strftime('%d.%m.%Y %H:%M:%S.%f')[:-3] + ' ' + event
    line += ' ' + json.dumps(fields, ensure_ascii=False, default=str)
    logs = APP / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    for path in (logs / 'media_pool_watchdog.log', logs / 'DavinciResolveProjectManagement.log'):
        with path.open('a', encoding='utf-8') as stream:
            stream.write(line + '\n')
            stream.flush()

def process_alive(pid):
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        exit_code = ctypes.c_ulong()
        return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code))) and exit_code.value == 259
    finally:
        kernel.CloseHandle(handle)

def start(project):
    import uuid
    marker = APP / 'runtime' / ('media_pool_' + uuid.uuid4().hex + '.active')
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(project, encoding='utf-8')
    args = [sys.executable, str(Path(__file__)), str(marker), str(os.getpid()), project]
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    try:
        child = subprocess.Popen(args, cwd=str(APP), creationflags=flags, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return marker, child.pid
    except Exception:
        marker.unlink(missing_ok=True)
        raise

def stop(marker):
    marker.unlink(missing_ok=True)

def watch(marker, parent_pid, project):
    started = time.monotonic()
    emit('MEDIA_POOL_WATCHDOG_STARTED', project=project, parent_pid=parent_pid, watchdog_pid=os.getpid())
    checkpoints = {1, 2, 5, 10, 20, 30, 60, 120, 300}
    for elapsed in range(1, 601):
        time.sleep(1)
        if not marker.exists():
            emit('MEDIA_POOL_WATCHDOG_STOPPED', project=project, elapsed_seconds=elapsed)
            return
        alive = process_alive(parent_pid)
        if elapsed in checkpoints or elapsed > 300 and elapsed % 60 == 0:
            emit('MEDIA_POOL_GET_WAIT', project=project, elapsed_seconds=elapsed,
                 parent_alive=alive, watchdog_pid=os.getpid())
        if not alive:
            emit('MEDIA_POOL_WATCHDOG_PARENT_EXITED', project=project, elapsed_seconds=elapsed)
            marker.unlink(missing_ok=True)
            return
    emit('MEDIA_POOL_WATCHDOG_MAX_DURATION', project=project, seconds=600)
    marker.unlink(missing_ok=True)

if __name__ == '__main__':
    watch(Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
