#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent
STATE = APP / 'runtime' / 'managed_dependencies.json'


def load_state():
    try:
        data = json.loads(STATE.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(data):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def mark(name, kind, package):
    data = load_state()
    data[name] = {'kind': kind, 'package': package, 'installed_by_project': True}
    save_state(data)


def unmark(name):
    data = load_state()
    data.pop(name, None)
    save_state(data)


def owned(name):
    item = load_state().get(name, {})
    return bool(item.get('installed_by_project'))


def uninstall(name, item):
    kind = str(item.get('kind', '')).casefold()
    package = str(item.get('package', '')).strip()
    if not package:
        return False
    print(f'Removing no-longer-required project dependency: {name} ({package})...')
    if kind == 'pip':
        cmd = [sys.executable, '-m', 'pip', 'uninstall', '-y', package]
    elif kind == 'winget':
        cmd = ['winget', 'uninstall', '--id', package, '--exact', '--silent', '--accept-source-agreements']
    else:
        print(f'WARNING: Unknown dependency manager {kind!r}; keeping {name}.')
        return False
    try:
        result = subprocess.run(cmd, check=False)
    except OSError as exc:
        print(f'WARNING: Could not remove {name}: {exc}')
        return False
    if result.returncode != 0:
        print(f'WARNING: Removal of {name} failed with exit code {result.returncode}; keeping ownership record.')
        return False
    print(f'Removed: {name}')
    return True


def cleanup(required):
    required = {x.casefold() for x in required}
    data = load_state()
    changed = False
    for name, item in list(data.items()):
        if name.casefold() in required or not item.get('installed_by_project'):
            continue
        if uninstall(name, item):
            data.pop(name, None)
            changed = True
    if changed:
        save_state(data)
    return 0


def main():
    if len(sys.argv) < 2:
        return 2
    cmd = sys.argv[1]
    if cmd == 'cleanup':
        return cleanup(sys.argv[2:])
    if len(sys.argv) < 3:
        return 2
    name = sys.argv[2]
    if cmd == 'owned':
        return 0 if owned(name) else 1
    if cmd == 'unmark':
        unmark(name); return 0
    if cmd == 'mark' and len(sys.argv) >= 5:
        mark(name, sys.argv[3], sys.argv[4]); return 0
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
