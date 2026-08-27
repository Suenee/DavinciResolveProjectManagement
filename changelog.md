# Changelog

## 1.11 - 27.08.2026

- Added verified Resolve media import. After batch import, the application checks the Media Pool, retries missing files individually, and stops before later automation if files are still missing.
- Added workflow-stage diagnostics (`RESOLVE_CONNECT`, `PROJECT_OPEN`, `MEDIA_IMPORT`, `MEDIA_VERIFY`, `TIMELINE`, `VOICE_ISOLATION`, `INTRO_MATCH`, `DELIVERY`, `SAVE`, `COMPLETE`).
- Runtime errors now include the exact failed phase and a Python traceback in the application log.
- Moved application logs from `runtime/logs/` to repository-root `logs/`; existing logs are migrated safely during upgrade.
- Replaced the monolithic batch upgrader with the shared project-family architecture: tiny `upgrade.cmd` bootstrap plus authoritative self-updating `upgrade.ps1`.
- `upgrade.cmd` fetches the current runner from `origin/main` into a temporary file before any repository mutation.
- Added repository-root single-run `upgrade.log` with explicit final `SUCCESS`, `WARNING`, or `FAILED` status.
- Added explicit branch synchronization and verification that `HEAD == origin/main`.
- Added safe refusal to overwrite tracked local modifications; untracked runtime/user data is not cleaned or stashed.
- Added `.gitattributes` enforcing CRLF for Windows CMD/BAT/PowerShell scripts.
- Hardened PowerShell native-command handling so harmless stderr output does not become a false failure under Windows PowerShell 5.1.
- Added `UPGRADE.md` documenting the project-specific upgrade protocol and known failure traps.

## 1.10 - 19.08.2026

- Replaced the fixed new-project suggestion list with a temporary autocomplete popup below the project-name field.
- Fixed intro search-window display conversion: internal seconds are now shown as whole minutes (1-5) and converted back to seconds on save.
- Fixed intro confidence display conversion: internal decimal values such as `0.78` are shown as whole percentages such as `78` and converted back on save.
- Added logical UI dependency between `CreateCleanAudioTrack` and its track-name field; the name is disabled when the clean track is disabled.
- Added validation for project root, intro folder, Resolve.exe, Resolve Project Library name, DELIVERY folder name, and required clean-audio track name.
- Project root and intro folder remain selected through the standard Windows folder picker.
- Resolve executable remains read-only and can be found automatically or selected manually; manual selection is validated as `Resolve.exe`.
- Settings are reloaded immediately after saving. Changing `ProjectRoot` refreshes the running project browser without restarting the application.

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
