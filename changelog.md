# Changelog

## 1.04 - 18.08.2026

- Redesigned the existing-project update dialog for faster visual scanning.
- The window title remains `Aktualizace projektu`; the body now shows only the project name as a bold heading.
- Repository count is centered in the status column and keeps its explanatory tooltip.
- Readiness diagnostics now use larger colored symbols: green `✓` for prepared and red `✕` for not prepared.
- Added a shared Windows UI helper that detects the visible DaVinci Resolve window and makes application dialogs owned by it, keeping them above Resolve without global always-on-top behavior.
- All dialogs routed through the common centering helper inherit the Resolve-relative Z-order behavior.

## 1.03 - 18.08.2026

- Added a single update checklist dialog for existing Resolve projects.
- The dialog shows repository, timeline, Voice Isolation, intro routing, and DELIVERY readiness before any changes are made.
- Repository status shows the number of files missing from the Media Pool, with a tooltip explaining the value.
- Readiness states use `✓` for prepared and `✕` for not prepared.
- Added logical dependencies between timeline creation, Voice Isolation, and intro detection options.
- Existing projects can create another base timeline; name collisions use `(2)`, `(3)`, and subsequent numeric suffixes.
- Repository synchronization and DELIVERY configuration remain independently selectable.
- Cancel performs no project modification.
- Made clean audio track creation idempotent to prevent duplicate AUDIO tracks.
- Intro routing now reuses an existing clean audio track when available.

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
