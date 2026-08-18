# Changelog

## 1.02 - 18.08.2026

- Added automatic intro/jingle detection for newly-created timelines when `SHOOTING` has no `SET xx` folders.
- Scene Cut Detection runs only on a temporary duplicate timeline so the final timeline is not destructively cut by analysis.
- The segment between the first and second detected cuts is treated as the intro candidate only when the second cut occurs within the configurable first 60 seconds.
- Intro audio is routed to the clean audio track without Voice Isolation; remaining source audio stays on Voice Isolation tracks.
- Added safe fallback behavior: ambiguous detection or failed reconstruction leaves the original timeline unchanged and records the reason in the runtime log.
- Added `[Timeline] AutoDetectIntro` and `IntroMaxEndSeconds` configuration.
- Confirmed repository housekeeping already ignores `__pycache__`, `*.pyc`, and `runtime/`.

## 1.01 - 18.08.2026

- Added automatic Voice Isolation configuration for all source audio tracks on the first newly-created timeline.
- Added one additional empty audio track with Voice Isolation explicitly disabled.
- Added configurable Voice Isolation amount and clean-track creation under the new `[Timeline]` section.
- Existing timelines remain untouched during later media synchronization.

## 1.00 - 18.08.2026

- Added managed DaVinci Resolve headless lifecycle with GUI handoff, recovery, and runtime logging.
- Added case-insensitive project folder resolution with interactive selection and sortable creation-date list.
- Added create-or-sync behavior for existing Resolve projects.
- Added Deliver preset configuration with project-specific DELIVERY target folder.
- Added automatic initial timeline population from SHOOTING media.
- SHOOTING root files are ordered by Windows creation time; subfolders are processed by case-insensitive folder name, with files inside each folder ordered by creation time.
- Existing timelines are never modified during later media synchronization.
