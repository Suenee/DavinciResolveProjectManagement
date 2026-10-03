# Changelog

## 1.38 - 03.10.2026

- Added diagnostic instrumentation around the blocking DaVinci Resolve `GetMediaPool()` API call without changing the workflow behavior.
- An independent daemon heartbeat logs `MEDIA_POOL_GET_WAIT` after 1, 2, 5, 10, 20, 30, 60, 120 and 300 seconds while the native API call remains blocked, then every 300 seconds.
- `MEDIA_POOL_GET_RETURN` records the actual elapsed call time when Resolve returns; exceptions are recorded as `MEDIA_POOL_GET_ERROR`.
- Added `PROJECT_CURRENT_DIAGNOSTIC` immediately before the Media Pool call to compare the project object returned by project creation with Resolve's current project and record both project names.
- The diagnostic does not yet impose a timeout or change Resolve behavior; it is intended to isolate the hang before implementing a permanent recovery strategy.

## 1.37 - 30.09.2026

- Preserve the configured Windows path representation when setting the DaVinci Resolve DELIVERY target.
- Mapped project roots such as `N:\\...` are now passed to Resolve as mapped-drive paths instead of being expanded to their UNC backing path.
- Removed `Path.resolve()` from DELIVERY target creation and readiness comparison.
- Added `DELIVERY_TARGET` diagnostics recording the project path and the exact target path passed to Resolve.
- Audited remaining `Path.resolve()` uses: application-local paths and fingerprint cache identity remain intentional; the same-volume filesystem check may canonicalize paths internally but does not pass the result to Resolve.


## 1.36 - 30.09.2026

- Added ordered project automation profiles in `config.ini`; the first matching `Match` regular expression selects the workflow.
- Optional title image, intro, end credits, and Silence Trim layers are now controlled per profile instead of running for every new project.
- Added a News profile for `Zprávy z Exopolitiky`: title image and end credits enabled, `UFO Disclosure.mp4` selected as the default intro, and Silence Trim set to `ask`.
- Added a Channeling profile with all four optional layers disabled.
- Added a safe Default profile with all optional layers disabled.
- Boolean profile layers use `0` / `1`; Intro accepts `0`, `ask`, or a filename, and SilenceTrim accepts `0`, `1`, or `ask`.
- Added `PROFILE_MATCH` and `PROFILE_LAYERS` runtime diagnostics.
- Replaced the obsolete example `IntroMapping` rules with profile-controlled intro selection.
- Updated the example configuration to use named `IntroPaths` instead of the legacy single intro folder.
- Updated Settings to display the active named intro-path configuration without recreating the obsolete single-folder key.
- Fixed the Settings Logging section to always use the literal `[Logging]` configuration section regardless of UI language.
- Added `project_profiles.py` and `project_paths.py` to updater Python syntax verification.
- Removed the legacy global Silence Trim Enabled switch; profile `SilenceTrim` is now the sole workflow enablement control while `[SilenceTrim]` keeps only analysis parameters.

## 1.35 - 30.09.2026

- Fixed title-image matching so technical `MM-NN-` filename prefixes are ignored when comparing an image with the project name.
- The full project subject remains significant for matching, e.g. `Channeling 6` is compared with the title-image subject rather than interpreting `05-20-` as project metadata.
- Removed filesystem modification time from title-image ranking.
- Ambiguous title-image matches now require user selection instead of silently choosing one candidate.
- Candidate presentation uses filename Z-A as the deterministic tie order.
- Added an explicit localized `No title image` choice. It is distinct from closing the dialog.
- Closing title/intro selection or pressing Escape now means Back rather than accepting the default selection.
- Repaired two regressions introduced during the interrupted 1.34 update: the missing named-intro-path import/workflow indentation and main-browser exit state initialization.

## 1.34 - 30.09.2026

- Added ordered named `[IntroPaths]` candidates so intro media can resolve across computers with different drive mappings such as `D:\` and `N:\`.
- Migrates the legacy `IntroDetection.Folder` value into `IntroPaths.Legacy`.
- Intro fingerprint listing and new-project intro selection now use the first currently available intro path.
- Closing or pressing Escape in title/intro selection is no longer interpreted as accepting the default choice; it navigates back in the pre-build wizard.
- Silence Trim now uses a three-way Yes/No/Cancel prompt so Cancel can represent Back instead of silently becoming No.
- Closing the main project browser or choosing Project > Exit now performs an application-level exit and cleans up a Resolve process only when it is owned by DRPM.

## 1.33 - 28.09.2026

- Fixed startup failure in the managed workflow caused by the missing `active_root` import after the multi-root path migration.
- The managed builder now imports the shared project-path resolver used by its configuration loader.

## 1.32 - 28.09.2026

- Replaced the single `[Paths] ProjectRoot` setting with ordered named project-root candidates. Keys are arbitrary unique labels; values are project root paths.
- The application checks configured paths in INI order and uses the first path that currently exists, allowing the same configuration to work across computers with different drive mappings such as `D:\` and `N:\`.
- Added shared project-root resolution for the managed workflow, project browser, and standalone Resolve project builder.
- Settings now edits named path rows and requires unique names, complete name/path pairs, and at least one currently available root.
- Existing `ProjectRoot` configurations are migrated automatically to a named `Legacy` entry without losing the configured path.
- Network and mapped-drive paths remain supported.

## 1.31 - 28.09.2026

- Added optional edge-silence trimming for newly created Resolve projects. The feature is controlled by `[SilenceTrim] Enabled` and is offered after title/intro selection but before Resolve project creation.
- Silence detection analyzes only the beginning and end of each source clip and creates editable Resolve timeline trims; source media is never modified.
- Added configurable detection range, dBFS threshold, minimum sound duration, and natural pre/post-roll spacing.
- Added a Settings group for Silence Trim parameters and persists them in `config.ini`.
- Added NumPy as a managed Python dependency and FFmpeg/ffprobe as managed runtime dependencies for silence analysis.
- `upgrade.cmd` now installs missing Python packages and FFmpeg automatically when possible, then verifies them before continuing.
- Added migration support so existing `config.ini` files receive new Silence Trim keys without losing local settings.

## 1.30 - 27.09.2026

- Keep the progress window visible through the final EDIT/playhead step instead of closing it after the Deliver phase.
- Reassert progress-window topmost state around Resolve page changes, Deliver configuration, save, EDIT return, and playhead positioning.
- Prefer placing the final playhead at the first SHOOTING clip by summing the actual title-still and intro timeline-item durations; fall back to the first timeline item or timeline start if needed.
- Add explicit progress/log stages for Deliver configuration, save, EDIT return, playhead positioning, and completion.
- Add a Cancel button to the progress window. Cancellation is checked at workflow checkpoints and raises `WorkflowCancelled`; the log records `WORKFLOW_CANCEL_REQUESTED` and `WORKFLOW_CANCELLED`.
- Add configurable UI language (`auto`, `cs`, `en`) with Windows locale detection and English fallback.
- Add JSON language libraries under `locales/` so additional translations can be added without changing application code.
- Make Settings language selection immediately switch the running UI language and persist it to `config.ini`.
- Keep the completed progress window visible for 5 seconds; its button shows `Zavřít (%ss)` / `Close (%ss)` countdown and may be closed immediately by the user.
- Fix Settings error handler syntax introduced during localization work.
- Restore repeated `run.cmd` foreground activation by using the hidden main window as the stable IPC target and explicitly restoring/raising the visible project browser on `SHOW`.

## 1.29 - 27.09.2026

- Use Resolve-native still-image duration control via MediaPoolItem `SetMarkInOut()` before `AppendToTimeline()`; remove the ineffective `endFrame` append override.
- Verify the actual appended timeline-item duration and log mismatches explicitly.
- Configure title stills for 20 seconds and end credits for 25 seconds through `[TimelineAssets]` settings.
- Keep title image -> intro -> SHOOTING -> end credits ordering when creating a new timeline.
- Restore Resolve to the Edit page after Deliver configuration and save.
- Position the final timeline playhead at the start of the first SHOOTING clip when the Resolve API exposes a compatible timecode setter; otherwise fall back to timeline start.
- Extend progress reporting through Deliver, Save, Edit-page restore, and playhead positioning.
- Fix Settings crash caused by a missing `filedialog` import.

## 1.28 - 27.09.2026

- Add automatic title-image discovery under a year-aware `TitlesRoot` path using `%Y`, with ±1 year probing within 14 days of New Year.
- Rank title-image candidates by project-name similarity and recency; automatically select only high-confidence matches and otherwise offer the top candidates plus manual browse/skip.
- Add automatic year-aware end-credits lookup under `Credits/endcredits.jpg`, preferring the current year and falling back to the previous year when needed.
- Import selected title images and end credits into `Master/IMAGES`, and selected intros into `Master/INTRO`.
- Build new timelines in the order title image (20 s) -> intro -> SHOOTING media -> end credits (25 s).
- Add configurable timeline asset paths, durations, candidate count, auto-match threshold, and New Year tolerance to `config.ini` and Settings.
- Extend progress reporting and logging for title-image, intro, credits, media import, timeline construction, Deliver setup, and final Edit-page reset.

## 1.27 - 27.09.2026

- Add a dedicated topmost progress window for project creation/update with deterministic foreground reassertion around Resolve page changes.
- Add structured progress checkpoints for Resolve connection, project manager access, project creation, Media Pool access, media import, timeline creation, audio layout, Deliver setup, save, and final Edit-page reset.
- Add diagnostics for Resolve Project Manager and Media Pool calls so hangs can be isolated in the runtime log.

## 1.26 - 27.09.2026

- Restore Windows taskbar icon handling after packaging changes.
- Add an application icon and apply it to the project browser, settings window, and progress dialog when supported.
- Document that launching through `run.cmd` remains supported; the Windows shell may still display the console host icon for the launcher itself.

## 1.25 - 27.09.2026

- Add topmost diagnostics for repeated `run.cmd` activation and Resolve window ordering.
- Log the foreground window, Resolve HWND, app HWND, and progress HWND before and after each foreground pulse.
- On repeated launch, explicitly restore the existing application window and reassert topmost state instead of starting another instance.
- Add version number to the project-browser title for quick runtime verification.
- Expand Settings into grouped two-column layout with additional runtime, timeline, Deliver, intro-detection, and logging controls.

## 1.24 - 27.09.2026

- Move all runtime logs into `logs/` and use the fixed application log name `DavinciResolveProjectManagement.log` instead of `latest.log` or project-derived log names.
- Keep upgrade history in `logs/upgrade.log` and upgrade backup metadata under `logs/upgrade-backup/`.

## 1.23 - 27.09.2026

- Reverse `[IntroMapping]` entries so intro filenames are INI keys and regular expressions are values.
- Allow intro filenames with spaces, for example `UFO Disclosure = ^.*Zprávy\s+z\s+Exopolitiky.*$`.
- Preserve regex characters by disabling ConfigParser interpolation for intro mapping.

## 1.22 - 27.09.2026

- Add configurable `[IntroMapping]` regular-expression routing from project names to default intro files.
- Add automatic fallback to the generic `Exopolitics.mp4` intro for project names matching UFO/exopolitics rules.
- Keep ambiguous intro matches interactive.

## 1.21 - 27.09.2026

- Add Deliver-page completion workflow and deterministic post-run UI reset.
- After configuring Deliver, switch Resolve back to the Edit page and move the timeline playhead to the start.

## 1.20 - 27.09.2026

- Add configurable title-image candidate discovery and end-credit insertion before timeline creation.
- Add title and credit still-duration settings and import them into `Master/IMAGES`.

## 1.19 - 27.09.2026

- Add configurable intro detection and manual selection fallback.
- Import the chosen intro into `Master/INTRO` before creating the timeline.

## 1.18 - 27.09.2026

- Add initial managed DaVinci Resolve project workflow and updater integration.
