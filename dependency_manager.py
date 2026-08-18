#!/usr/bin/env python3
from __future__ import annotations
import json
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


def main():
    if len(sys.argv) < 3:
        return 2
    cmd, name = sys.argv[1], sys.argv[2]
    if cmd == 'owned':
        return 0 if owned(name) else 1
    if cmd == 'unmark':
        unmark(name); return 0
    if cmd == 'mark' and len(sys.argv) >= 5:
        mark(name, sys.argv[3], sys.argv[4]); return 0
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
