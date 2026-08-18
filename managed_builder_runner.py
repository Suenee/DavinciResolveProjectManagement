#!/usr/bin/env python3
from __future__ import annotations
import managed_builder
import project_update

_base_create_initial_timeline=managed_builder.create_initial_timeline
project_update.set_timeline_creator(_base_create_initial_timeline)
managed_builder.build=project_update.build

if __name__=='__main__':
 raise SystemExit(managed_builder.main())
