# Changelog

## 1.32 - 28.09.2026

- Replaced the single `[Paths] ProjectRoot` setting with ordered named project-root candidates. Keys are arbitrary unique labels; values are project root paths.
- The application checks configured paths in INI order and uses the first path that currently exists, allowing the same configuration to work across computers with different drive mappings such as `D:` and `N:`.
- Added shared project-root resolution for the managed workflow, project browser, and standalone Resolve project builder.
- Settings now edits named path rows and requires unique names, complete name/path pairs, and at least one currently available root.
- Existing `ProjectRoot` configurations are migrated automatically to a named `Legacy` entry without losing the configured path.
- Network and mapped-drive paths remain supported.


## 1.31 - 28.09.2026

- Fixed FFmpeg discovery immediately after WinGet installation. The updater no longer assumes the current PowerShell process receives WinGet's updated PATH.
- FFmpeg discovery now checks user and machine WinGet command links and, as a fallback, searches the installed Gyan.FFmpeg package payload for `ffmpeg.exe`.
- This allows dependency installation to complete in the same `upgrade.cmd` run without requiring a new terminal.
- Kept the NumPy availability probe silent on Windows PowerShell 5.1.


## 1.30 - 28.09.2026

- Fixed dependency probing on Windows PowerShell 5.1. A missing optional NumPy module is now tested with native stdout/stderr suppressed, so the expected import failure cannot leak into PowerShell's error stream and interrupt the upgrade before automatic installation.
- NumPy is still installed automatically when the silent probe returns a non-zero exit code.


## 1.29 - 28.09.2026

- Fixed the updater local-change guard for Windows/network-drive checkouts where Git reports tracked CMD/PS1 launchers as modified only because the worktree uses CRLF and repository comparison uses normalized LF.
- Safety checks now ignore end-of-line-only differences while still refusing to overwrite substantive local tracked source changes.
- The updater explicitly reports when it is ignoring EOL normalization differences.


## 1.28 - 28.09.2026

- Fixed the first-run updater guard after a proven fresh bootstrap. On some Windows/network-drive Git configurations, CRLF normalization can make newly checked-out CMD launchers appear modified immediately after checkout.
- `upgrade.cmd` now marks only the fresh-bootstrap path with `DRPM_FRESH_BOOTSTRAP=1`. The PowerShell updater skips the local-change protection only for that first guaranteed-new checkout, then performs the authoritative `reset --hard origin/main`.
- Normal upgrades keep the existing protection against overwriting local tracked source changes.


## 1.27 - 28.09.2026

- Fixed fresh-bootstrap phase zero in `upgrade.cmd`: CMD expanded `%DRPM_BOOT%` before the variable was assigned because assignment and invocation were inside the same parenthesized block.
- Bootstrap setup now runs outside that block, transfers to the temporary copy through an explicit label, propagates its exit code, and removes the temporary launcher afterwards.


## 1.26 - 28.09.2026

- Added an authoritative root `VERSION` file and updated the upgrader to report the installed and target application versions from repository state instead of a duplicated hard-coded application version.
- Reworked `upgrade.cmd` into a temporary bootstrap that supports a fresh directory containing only the downloaded launcher, mapped/network paths, process-scoped Git `safe.directory`, and checkout of `origin/main`.
- The fresh bootstrap removes only the proven untracked `upgrade.cmd` collision before checkout; arbitrary untracked files are never cleaned.
- Renamed the PowerShell Git wrapper to `Invoke-Git` to avoid Windows PowerShell's case-insensitive command-name recursion trap documented by the shared upgrade protocol.
- Added the optional Silence Trim layer to Settings with configurable 30 s edge search, -40 dBFS threshold, 0.20 s minimum stable sound, 0.75 s pre-speech space, and 1.00 s post-speech space.
- New Resolve projects ask whether edge silence should be removed only when Silence Trim is enabled. The question is presented after title-image and intro selection.
- When selected, the workflow analyzes only the beginning and end of each SHOOTING source and creates two timelines: an untouched `RAW` timeline and an `EDIT` timeline assembled from source in/out ranges.
- The EDIT timeline uses Resolve MediaPool `AppendToTimeline` source ranges, so source media remains untouched and edit points retain source handles for manual correction.
- Internal speech pauses are never removed. Unsafe or unanalyzable clips fall back to their full source range.
- Added per-clip silence-analysis and applied-range diagnostics to the application log.


## 1.25 - 28.09.2026

- Fixed a regression where launching `run.cmd` again detected the existing instance but could fail to bring its current window to the foreground.
- Single-instance activation now performs a second foreground activation pulse after the initial request, matching the proven delayed activation strategy used elsewhere in the UI.
- Added recovery of the currently visible Tk window when the cached active-window reference is no longer available.
- The active-window reference is cleared when its root window is destroyed instead of retaining a stale Tk object.
- Added `INSTANCE_ACTIVATE_WINDOW_RECOVERED`, `INSTANCE_ACTIVATE_RETRY_RETURN`, and `INSTANCE_ACTIVATE_RETRY_ERROR` diagnostics.

## 1.24 - 28.09.2026

- Successful workflow completion now keeps the 100% progress window visible for five seconds so the final Done state can be read.
- The former Cancel button becomes an active localized close button with a visible countdown: `Close (5s)` through `Close (1s)`.
- Clicking the close button dismisses the completed progress window immediately; otherwise it closes automatically after the countdown.
- The completed progress window is reasserted above Resolve before the countdown starts.
- Cancelled or unsuccessful workflows are not auto-closed by the success countdown.
- Added completion-hold and automatic-close diagnostics to the application log.

## 1.23 - 28.09.2026

- Completed the first full Czech/English UI localization pass using the gettext-based language layer.
- Applying a different language in Settings now immediately refreshes the running project browser, menu, column headings, and subsequent dialogs without restarting DaVinci Resolve.
- Added localized project creation, Settings, project update, intro selection, and title-image selection dialogs.
- Updated application window titles to version 1.23.
- Added active progress-window Z-order protection using the existing Windows foreground helper without leaving the window permanently always-on-top.
- Every workflow stage now records progress/Resolve Z-order snapshots before and after foreground restoration and reasserts the progress window above Resolve.
- After the final Resolve Edit-page/timeline/playhead operation, the progress window is explicitly restored above Resolve again before workflow completion.
- Added `PROGRESS_ZORDER_BEFORE`, `PROGRESS_ZORDER_AFTER`, and `PROGRESS_ZORDER_ERROR` diagnostics so future foreground losses can be verified from the runtime log.

## 1.22 - 28.09.2026

- Added an extensible GNU gettext localization layer with standard per-locale catalogs under `locale/<language>/LC_MESSAGES/`.
- Added `[General] Language = auto`; automatic mode follows the Windows UI language, uses Czech for Czech Windows, and falls back to English for unsupported or undetectable languages.
- Added a UI language selector to Settings. Additional gettext catalogs can be added without changing application workflow logic.
- Added a Cancel button to the workflow progress window. Cancellation is cooperative and is honored at safe workflow/progress checkpoints instead of forcibly terminating Resolve during an API call.
- The Cancel button changes to a disabled cancelling state after the first request, and cancellation is recorded in the application log.
- Progress remains active through the final Resolve UI preparation and reaches completion only after the Edit page, current timeline, and final playhead positioning have been processed.
- Captures the exact timeline start frame of the first SHOOTING item returned by Resolve and uses it as the preferred final playhead target instead of estimating title and intro durations.
- Falls back to the timeline start when a first SHOOTING item position is unavailable.
- Updated application window titles to version 1.22.

## 1.21 - 28.09.2026

- Replaced the console-only workflow progress with a visible Tk progress window that reports Resolve startup, media import progress, timeline/audio/delivery/save stages, and completion.
- Fixed Settings parsing for literal percent placeholders such as `%Y` by disabling ConfigParser interpolation and preserving key case.
- Added guarded Settings-menu diagnostics with a full traceback in the application log instead of allowing GUI callback failures to terminate silently.
- Changed still-image insertion to a clean Resolve-API experiment: set a documented MediaPoolItem video Mark In/Out range for the requested duration, then use plain `AppendToTimeline([item])`.
- Added immediate duration readback from the returned TimelineItem. Requested and actual frame counts plus a verification result are logged; no generated video, image sequence, or FFmpeg workaround is used.
- Removed the previous assumption that still-image `startFrame`/`endFrame` clipInfo values control timeline duration.
- After project work is saved, Resolve is explicitly returned to the Edit page, the created/current timeline is activated, and its playhead is moved to the timeline start timecode.
- Added logging of the final Edit-page, current-timeline, and playhead reset results.
- Updated application window titles to version 1.21.

## 1.20 - 28.09.2026

- Added detailed single-instance activation diagnostics when `run.cmd` is started while the application is already running.
- Logs the secondary-instance detection, activation signal delivery/receipt, activation API result, and failures.
- Added native Windows Z-order snapshots immediately before activation and shortly afterwards.
- Z-order diagnostics record visible top-level windows in native top-to-bottom order, including HWND, PID, process, title, TOPMOST state, foreground state, and explicit application/Resolve markers.
- Logs the measured application and DaVinci Resolve Z-order indexes so Resolve-specific foreground behavior can be diagnosed from real runtime evidence.
- Fixed the centralized `DavinciResolveProjectManagement.log` path constant used by runtime logging.


## 1.19 - 28.09.2026

- Added application version 1.19 to the project browser, settings, new-project, project-update, intro-selection, and title-image-selection window titles for immediate runtime verification.
- Redesigned Settings into a compact two-column layout with grouped Project, DaVinci Resolve, DELIVERY, Logging, Timeline, Timeline Assets, and Intro sections.
- Exposed the new Timeline Assets configuration in Settings, including the `%Y` title path, title/end-credit durations, candidate count, automatic-match threshold, year-boundary tolerance, and end-credit filename.
- Added validation that the configured title path retains the explicit `%Y` placeholder.
- Hardened Windows foreground handling with transient dialog ownership where available, a short Tk topmost pulse, native `BringWindowToTop`, and a delayed second activation attempt.
- Dialogs return to normal non-topmost behavior after activation and are not kept globally always-on-top.

## 1.18 - 28.09.2026

- Added configurable timeline title-image discovery under `[TimelineAssets]` using a `%Y` year placeholder in `TitlesRoot`.
- Title matching normalizes project/file names, ranks candidates by name similarity and recency, automatically accepts a clear high-confidence match, and otherwise offers the configured TOP candidate count plus file browsing and Skip.
- Title selection runs before intro selection and imports the selected image into `Master/IMAGES`.
- Added automatic yearly end-credit discovery using `EndCreditsFile`; the current year is preferred and the latest available previous year is used as fallback.
- Added configurable New Year boundary tolerance so adjacent year directories are considered around the year transition.
- End credits are imported into `Master/IMAGES`.
- New initial timeline order is: selected title still, selected intro, SHOOTING media, end-credits still.
- Title and end-credit still durations are explicitly appended in timeline frames using configurable durations (defaults: 20 and 25 seconds) rather than relying on Resolve's global still-duration preference.
- Missing or Resolve-rejected optional image assets are logged and skipped without aborting project initialization.

## 1.17 - 28.09.2026

- Consolidated all application logs under the repository-root `logs/` directory.
- Renamed the application runtime log to `logs/DavinciResolveProjectManagement.log`.
- Logging mode `single` truncates that application log at the beginning of a new session; mode `all` appends subsequent sessions to the same application log.
- Moved the updater transcript to `logs/upgrade.log`.
- Upgrade migration removes obsolete repository-root `upgrade.log` and legacy `logs/latest.log` / `logs/history.log` files.

## 1.16 - 28.09.2026

- Added configurable case-insensitive regular-expression intro mapping in `[IntroMapping]`; intro filenames are INI keys and project-name regular expressions are values.
- Default mappings select `UFO Disclosure.mp4` for `Zprávy z Exopolitiky`, `Spirituality.mp4` for names containing `spirit`, and `Exopolitics.mp4` for other UFO/exopolitics names.
- Mapping rules are evaluated in configuration order; the first matching rule wins.
- Invalid regular expressions are logged and skipped without stopping the workflow.
- If no mapping matches, the application shows the intro files currently present in `IntroDetection.Folder` and also offers `Bez znělky`.
- Missing or Resolve-rejected intro media are now logged and skipped; project initialization continues without the intro.
- Intro selection remains drive-independent through `IntroDetection.Folder`.

## 1.15 - 28.09.2026

- Added call/return diagnostics for Media Pool BIN lookup/creation, current-folder changes, directory synchronization, and media imports so a blocking Resolve API call can be identified from the last log event.
- New projects now explicitly ensure `Master/INTRO` and `Master/IMAGES` exist even when the corresponding project folders contain no media.
- Projects whose name contains `Zprávy z Exopolitiky` import `UFO Disclosure.mp4` from the configured `[IntroDetection] Folder` into `Master/INTRO`.
- The Exopolitics intro path is drive-independent and therefore works with configurations such as `D:\WORK\INTRO` or `N:\WORK\INTRO`.
- The imported `UFO Disclosure.mp4` is inserted as the first clip of the initial timeline, followed by SHOOTING media in the existing deterministic order.
- Missing or rejected Exopolitics intro media now stops initialization with an explicit diagnostic instead of silently creating a timeline without the requested intro.

## 1.14 - 28.09.2026

- Added precise diagnostics around DaVinci Resolve project creation, including entry/return from `CreateProject()`, project-object validation, Media Pool access, and root-folder access.
- Added a recovery path for Resolve builds that create a project but do not return a usable project object: the application re-queries the active Project Library folder and reloads the newly created project before continuing.
- Added explicit hard failures when the created/reloaded project has no accessible Media Pool or Media Pool root, preventing silent partial initialization.
- Media import, verification, timeline creation, Voice Isolation, DELIVERY setup, and save continue only after the project object and Media Pool root have been verified.

## 1.13 - 28.09.2026

- Added single-instance protection for the project-management launcher on Windows.
- Starting `run.cmd` while an existing instance is active now signals that instance to restore and move its current window to the foreground instead of opening a duplicate application instance.
- Reworked Windows foreground activation to restore minimized windows and use a temporary TOPMOST pulse followed by normal Z-order and foreground activation.
- Project windows are not left permanently always-on-top; the TOPMOST state is used only to overcome DaVinci Resolve Z-order when activating the UI.

## 1.12 - 28.09.2026

- Fixed a fatal Windows console progress error where `sys.stdout.flush()` could raise `OSError(22, 'Invalid argument')` and abort project initialization during media import.
- Console progress output is now best-effort and automatically disables itself when stdout is unavailable; workflow execution continues normally.
- Applied the same safe console output path to DaVinci Resolve startup progress.
- Added detailed Media Pool synchronization diagnostics for BIN creation/reuse, requested batch imports, and Resolve-accepted item counts.
- Existing Resolve projects now log whether they are incomplete, including expected/present media counts and timeline, Voice Isolation, and DELIVERY readiness. This makes partially created projects recoverable through the normal update workflow.
- Media verification remains a hard gate: later timeline, Voice Isolation, and DELIVERY automation does not continue until all expected media are present in the Media Pool.
- Upgrade output now clearly shows the application name, installed version, target version, updater revision, target branch, and a final green version banner.

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
