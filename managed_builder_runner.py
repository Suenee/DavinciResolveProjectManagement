#!/usr/bin/env python3
from __future__ import annotations
import managed_builder
import project_update
import project_update_dialog
import ui_windows

_base_create_initial_timeline=managed_builder.create_initial_timeline


def _center_above_resolve(root):
 ui_windows.center_and_place_above_resolve(root)


managed_builder.center=_center_above_resolve
project_update.ask=project_update_dialog.ask
project_update.set_timeline_creator(_base_create_initial_timeline)
managed_builder.build=project_update.build

if __name__=='__main__':
 raise SystemExit(managed_builder.main())
