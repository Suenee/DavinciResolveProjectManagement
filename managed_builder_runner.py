#!/usr/bin/env python3
from __future__ import annotations
import managed_builder
import timeline_audio

_original_create_initial_timeline = managed_builder.create_initial_timeline


def _create_initial_timeline_with_audio(mp, master, shoot, timeline_name):
    timeline = _original_create_initial_timeline(mp, master, shoot, timeline_name)
    return timeline_audio.configure(timeline)


managed_builder.create_initial_timeline = _create_initial_timeline_with_audio

if __name__ == '__main__':
    raise SystemExit(managed_builder.main())
