# DaVinci Resolve Project Management

Automation tool for creating, preparing, and safely updating DaVinci Resolve projects from predefined production folders, including bins, media import, initial timelines, and managed headless Resolve lifecycle.

## Installation / update

Run `upgrade.cmd` after cloning or downloading the repository. It updates a Git checkout when possible, installs Python automatically when it is missing, creates the local `config.ini` on first run, checks for the DaVinci Resolve scripting module, and validates all runtime Python sources.

Python installation uses `winget` first. If that is unavailable or unsuccessful, `upgrade.cmd` downloads the official Python installer from python.org and installs it for the current Windows user.

## Create or update a project

```cmd
run.cmd "20260810 Zprávy z Exopolitiky 25"
```

The project name lookup is case-insensitive. The initial YYYYMMDD prefix may be omitted. If several filesystem projects match, a centered selection window shows the project names and their real Windows creation times, newest first.

If the Resolve project does not exist, it is created normally. If it already exists, the tool opens it and compares filesystem media with Media Pool file paths. Existing media is never imported again. If new files are detected, the user is asked whether they should be added to the existing project. Saying No leaves the project unchanged.

If Resolve is not running, the tool starts it automatically with `-nogui`, waits for the scripting API, prepares or updates the project, saves it, and closes only the headless instance that was started by this tool.

The console shows live progress. Resolve startup uses an estimated percentage. Actual startup times are stored locally per Windows computer in `runtime/startup_history.ini`; the estimate learns from recent starts. `StartupTimeout` remains only a safety timeout. Media import uses real file counts for progress whenever possible.

If a managed headless start fails, the tool safely cleans up only its own process and makes one recovery attempt instead of leaving a broken headless Resolve running.

Keep the managed headless instance alive temporarily:

```cmd
run.cmd "20260810 Zprávy z Exopolitiky 25" --alive
```

`--alive` keeps Resolve available for `AliveTimeout` seconds after the job. The default is 900 seconds (15 minutes).

Keep the managed headless instance running without an idle timeout:

```cmd
run.cmd "20260810 Zprávy z Exopolitiky 25" --persistent
```

## Open Resolve GUI

Use the managed launcher:

```cmd
resolve.cmd
```

If Resolve is not running, it starts the normal GUI. If a headless instance owned by this tool is idle, it performs a controlled handoff to GUI. If a project job is still running, a small progress window is shown with `Makám za tebe…`; after the job finishes the launcher switches Resolve to GUI. An idle headless handoff shows `Už běžím…` with the sprinting snail.

The lifecycle manager never intentionally closes a Resolve instance that it did not start itself.

## Diagnostics

```cmd
diagnose.cmd
```

Diagnostics are independent of the project-name arguments used by the managed builder. They check the Python runtime, Resolve process, scripting API module, `fusionscript.dll`, `scriptapp("Resolve")`, Resolve version, and Project Manager API.
