# DaVinci Resolve Project Management

Automation tool for creating and preparing DaVinci Resolve projects from predefined production folders, including bins, media import, and initial timelines.

## Installation / update

Run `upgrade.cmd` after cloning or downloading the repository. It updates a Git checkout when possible, installs Python automatically when it is missing, creates the local `config.ini` on first run, checks for the DaVinci Resolve scripting module, and validates the Python source.

Python installation uses `winget` first. If that is unavailable or unsuccessful, `upgrade.cmd` downloads the official Python installer from python.org and installs it for the current Windows user.

## Run

```cmd
run.cmd "20260810 Zprávy z Exopolitiky 25"
```

DaVinci Resolve Studio must be running with local external scripting enabled.
