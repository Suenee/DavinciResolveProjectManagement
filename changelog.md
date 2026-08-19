# Changelog

## 1.09 - 19.08.2026

- Added a project browser shown when no project name is supplied and reused for ambiguous project searches.
- Added live case-insensitive search with immediate filtering and automatic preselection of the best visible result.
- Added the `Projekt` menu with `Nový...`, `Otevřít...`, `Nastavení...`, and `Konec`.
- Added two-step project-name confirmation. The application proposes the current date and next series number while respecting a valid user-supplied `YYYYMMDD` prefix and explicit series number.
- Added duplicate project-name validation before any project directory is created.
- Added external-media folder import with an option to move media into the standard project structure or leave it in place for a one-time Resolve project workflow.
- Added safety preflight before media moves: destination writability and free-space checks are performed before transfer starts.
- Same-volume moves use filesystem rename/move semantics and do not require duplicate free space.
- Cross-volume moves use copy-to-temporary, size verification, atomic destination rename, and source deletion only after successful verification.
- Added a byte-based progress bar for media moves.
- Added a GUI editor for user-facing `config.ini` settings while keeping internal runtime state hidden.
- `run.cmd` can now be started without a project-name argument.
- `upgrade.cmd` validates the new project-browser module.

## 1.08 - 18.08.2026

- Added opt-in intro/jingle detection based on a reference audio fingerprint instead of DaVinci Resolve Scene Cut Detection.
- Added `[IntroDetection]` configuration with reference folder `D:\WORK\INTRO`, a 120-second search window, confidence threshold, sample rate, and envelope resolution.
- Existing-project update dialog can again enable `Vystřihnout znělku` and select a specific reference intro file from the configured folder.
- Fingerprints use a normalized short-time RMS audio envelope and normalized correlation, making matching tolerant of ordinary level changes and re-encoding.
- Reference fingerprints are cached under `runtime\intro_fingerprints` and automatically invalidated when the source file changes.
- Only audio is decoded for matching; video frames are not analyzed.
- A match below the configured confidence threshold performs no edit and is logged as rejected.
- A successful match routes the intro audio to the existing clean AUDIO track without Voice Isolation and creates an explicit video edit at the end of the matched intro.
- Added automatic NumPy and FFmpeg dependency checks/installations to `upgrade.cmd`.
- New projects remain conservative: fingerprint intro routing is currently triggered only when explicitly selected in the existing-project update workflow.

## 1.07 - 18.08.2026

- Disabled automatic intro/jingle detection and routing because DaVinci Resolve Scene Cut Detection proved unreliable for this workflow.
- New timelines now only enable Voice Isolation on source audio tracks and add one empty clean audio track without Voice Isolation.
- Removed the `Vystřihnout znělku` option from the existing-project update dialog so the unreliable feature cannot be triggered accidentally.
- Kept the experimental intro-detection module in the repository for reference, but it is no longer part of the runtime path.

## 1.06 - 18.08.2026

- Fixed multi-monitor positioning for application dialogs when DaVinci Resolve is on a monitor with negative virtual-screen coordinates.
- Dialog geometry now uses explicit signed coordinates such as `-1920+200` instead of invalid `+-1920+200` forms.
- Removed Win32 owner reassignment from dialog Z-order handling so Windows cannot relocate the Tk window after geometry is applied.
- Dialogs are hidden during initial Tk creation and shown only after their final Resolve-relative position is calculated.
- Restored a compact update-dialog row height by reducing status-symbol font size and removing extra row padding while retaining colored diagnostics.
