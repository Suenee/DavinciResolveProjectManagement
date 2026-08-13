#!/usr/bin/env python3
"""Create and prepare a DaVinci Resolve project from a production folder."""

from __future__ import annotations

import argparse
import configparser
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Iterable

APP_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = APP_DIR / "config.ini"
EXAMPLE_CONFIG = APP_DIR / "config.example.ini"
OPTIONAL_MEDIA_DIRS = ("IMAGES", "PHOTOS", "AUDIO")
DATE_PREFIX_RE = re.compile(r"^\d{8}\s+")

PROGRAM_DATA = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
PROGRAM_FILES = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
RESOLVE_MODULE = PROGRAM_DATA / "Blackmagic Design" / "DaVinci Resolve" / "Support" / "Developer" / "Scripting" / "Modules" / "DaVinciResolveScript.py"
FUSIONSCRIPT_CANDIDATES = (
    PROGRAM_FILES / "Blackmagic Design" / "DaVinci Resolve" / "fusionscript.dll",
    PROGRAM_FILES / "Blackmagic Design" / "DaVinci Resolve" / "Fusion" / "fusionscript.dll",
)


class BuilderError(RuntimeError):
    pass


def load_config(config_path: Path) -> tuple[Path, str]:
    if not config_path.exists():
        if config_path == DEFAULT_CONFIG and EXAMPLE_CONFIG.exists():
            shutil.copy2(EXAMPLE_CONFIG, config_path)
            print(f"Created local configuration: {config_path}")
        else:
            raise BuilderError(f"Configuration file does not exist: {config_path}")

    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    if not parser.has_option("Paths", "ProjectRoot"):
        raise BuilderError("Missing [Paths] ProjectRoot in configuration.")

    project_root_raw = parser.get("Paths", "ProjectRoot").strip()
    if not project_root_raw:
        raise BuilderError("[Paths] ProjectRoot must not be empty.")

    resolve_folder = parser.get("DaVinciResolve", "ResolveProjectFolder", fallback="").strip()
    return Path(project_root_raw), resolve_folder


def import_resolve_module():
    try:
        import DaVinciResolveScript as dvr_script  # type: ignore
        return dvr_script
    except ImportError:
        modules_dir = RESOLVE_MODULE.parent
        if modules_dir.exists():
            sys.path.insert(0, str(modules_dir))
        try:
            import DaVinciResolveScript as dvr_script  # type: ignore
            return dvr_script
        except ImportError as exc:
            raise BuilderError(
                "DaVinci Resolve scripting module was not found. Expected it under "
                f"{modules_dir}."
            ) from exc


def connect_to_resolve():
    dvr_script = import_resolve_module()
    resolve = dvr_script.scriptapp("Resolve")
    if resolve is None:
        raise BuilderError(
            "Cannot connect to DaVinci Resolve. Run: run.cmd --diagnose"
        )
    return resolve


def is_resolve_running() -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Resolve.exe", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return "Resolve.exe" in result.stdout
    except Exception:
        return False


def diagnose() -> int:
    print("=== DaVinci Resolve scripting diagnostics ===")
    print(f"Python executable : {sys.executable}")
    print(f"Python version    : {sys.version.split()[0]}")
    print(f"Platform          : {sys.platform}")
    print(f"Resolve.exe       : {'RUNNING' if is_resolve_running() else 'NOT DETECTED'}")
    print(f"API module        : {RESOLVE_MODULE}")
    print(f"API module exists : {'YES' if RESOLVE_MODULE.is_file() else 'NO'}")

    found_fusion = False
    for candidate in FUSIONSCRIPT_CANDIDATES:
        exists = candidate.is_file()
        found_fusion = found_fusion or exists
        print(f"fusionscript.dll  : {candidate} -> {'YES' if exists else 'NO'}")

    try:
        dvr_script = import_resolve_module()
        print(f"Module import     : OK ({getattr(dvr_script, '__file__', 'unknown path')})")
    except Exception as exc:
        print(f"Module import     : FAILED: {type(exc).__name__}: {exc}")
        return 1

    try:
        resolve = dvr_script.scriptapp("Resolve")
        if resolve is None:
            print("scriptapp Resolve : FAILED (returned None)")
            print()
            if not is_resolve_running():
                print("LIKELY CAUSE: Resolve.exe was not detected as running.")
            elif not found_fusion:
                print("LIKELY CAUSE: fusionscript.dll was not found in expected locations.")
            else:
                print("Resolve is running and the API files exist, but scriptapp() still returned None.")
                print("This points to the Resolve scripting bridge/runtime rather than config.ini.")
            return 2

        print("scriptapp Resolve : OK")
        try:
            version = resolve.GetVersionString()
            print(f"Resolve version   : {version}")
        except Exception as exc:
            print(f"Resolve version   : unavailable ({exc})")

        try:
            pm = resolve.GetProjectManager()
            print(f"Project Manager   : {'OK' if pm is not None else 'FAILED'}")
        except Exception as exc:
            print(f"Project Manager   : FAILED: {exc}")
            return 3

        print()
        print("DIAGNOSTICS PASSED")
        return 0
    except Exception as exc:
        print(f"scriptapp Resolve : EXCEPTION: {type(exc).__name__}: {exc}")
        return 4


def open_project_library_folder(project_manager, folder_name: str) -> None:
    if not project_manager.GotoRootFolder():
        raise BuilderError("Cannot switch to the root of the Resolve Project Library.")
    if folder_name and not project_manager.OpenFolder(folder_name):
        raise BuilderError(
            f'Resolve Project Library folder "{folder_name}" was not found. '
            "No folder was created automatically."
        )


def project_exists(project_manager, project_name: str) -> bool:
    projects = project_manager.GetProjectListInCurrentFolder()
    if projects is None:
        raise BuilderError("Cannot read projects in the current Resolve Project Library folder.")
    return project_name in projects


def list_files(directory: Path) -> list[str]:
    return [
        str(entry.resolve())
        for entry in sorted(directory.iterdir(), key=lambda p: p.name.casefold())
        if entry.is_file()
    ]


def list_directories(directory: Path) -> Iterable[Path]:
    return (
        entry
        for entry in sorted(directory.iterdir(), key=lambda p: p.name.casefold())
        if entry.is_dir()
    )


def import_directory_tree(media_pool, parent_bin, source_dir: Path) -> int:
    current_bin = media_pool.AddSubFolder(parent_bin, source_dir.name)
    if current_bin is None:
        raise BuilderError(f'Cannot create Media Pool bin "{source_dir.name}".')
    if not media_pool.SetCurrentFolder(current_bin):
        raise BuilderError(f'Cannot select Media Pool bin "{source_dir.name}".')

    imported_count = 0
    files = list_files(source_dir)
    if files:
        imported = media_pool.ImportMedia(files)
        if imported:
            imported_count += len(imported)
        if imported is None:
            print(f"WARNING: Resolve did not import files from: {source_dir}")
        elif len(imported) != len(files):
            print(
                f"WARNING: Resolve imported {len(imported)} of {len(files)} files from: {source_dir}"
            )

    for child_dir in list_directories(source_dir):
        imported_count += import_directory_tree(media_pool, current_bin, child_dir)
    return imported_count


def make_timeline_name(project_name: str) -> str:
    simplified = DATE_PREFIX_RE.sub("", project_name, count=1).strip()
    return simplified or project_name


def build_project(project_name: str, config_path: Path) -> None:
    project_root, resolve_folder = load_config(config_path)
    filesystem_project = project_root / project_name

    if not filesystem_project.is_dir():
        raise BuilderError(f"Project directory does not exist: {filesystem_project}")

    shooting_dir = filesystem_project / "SHOOTING"
    if not shooting_dir.is_dir():
        raise BuilderError(f"Required SHOOTING directory does not exist: {shooting_dir}")

    resolve = connect_to_resolve()
    project_manager = resolve.GetProjectManager()
    if project_manager is None:
        raise BuilderError("DaVinci Resolve Project Manager API is unavailable.")

    open_project_library_folder(project_manager, resolve_folder)
    if project_exists(project_manager, project_name):
        location = resolve_folder or "Project Library root"
        raise BuilderError(
            f'Resolve project "{project_name}" already exists in "{location}". '
            "Existing projects are never overwritten by V1."
        )

    project = project_manager.CreateProject(project_name)
    if project is None:
        raise BuilderError(f'Failed to create Resolve project "{project_name}".')

    media_pool = project.GetMediaPool()
    if media_pool is None:
        raise BuilderError("Created project does not expose the Media Pool API.")

    master_bin = media_pool.GetRootFolder()
    if master_bin is None:
        raise BuilderError("Cannot access the Master bin.")

    imported_total = import_directory_tree(media_pool, master_bin, shooting_dir)
    for directory_name in OPTIONAL_MEDIA_DIRS:
        source_dir = filesystem_project / directory_name
        if source_dir.is_dir():
            imported_total += import_directory_tree(media_pool, master_bin, source_dir)
            print(f"Added optional directory: {directory_name}")

    timelines_bin = media_pool.AddSubFolder(master_bin, "TIMELINES")
    if timelines_bin is None:
        raise BuilderError('Cannot create Media Pool bin "TIMELINES".')
    if not media_pool.SetCurrentFolder(timelines_bin):
        raise BuilderError('Cannot select Media Pool bin "TIMELINES".')

    timeline_name = make_timeline_name(project_name)
    timeline = media_pool.CreateEmptyTimeline(timeline_name)
    if timeline is None:
        raise BuilderError(f'Cannot create timeline "{timeline_name}".')

    if not project_manager.SaveProject():
        raise BuilderError("Resolve project was created but SaveProject() failed.")

    print()
    print("DONE")
    print(f"Resolve project : {project_name}")
    print(f"Library folder  : {resolve_folder or '(root)'}")
    print(f"Source folder   : {filesystem_project}")
    print(f"Timeline        : {timeline_name}")
    print(f"Imported media  : {imported_total}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a DaVinci Resolve project from an existing production folder."
    )
    parser.add_argument("project_name", nargs="?", help='Example: "20260810 Zprávy z Exopolitiky 25"')
    parser.add_argument("--diagnose", action="store_true", help="Run Resolve scripting diagnostics only.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to INI configuration file (default: config.ini next to the script).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.diagnose:
        return diagnose()

    if not args.project_name:
        print("ERROR: Project name is required unless --diagnose is used.", file=sys.stderr)
        return 2

    project_name = args.project_name.strip()
    if not project_name:
        print("ERROR: Project name must not be empty.", file=sys.stderr)
        return 2

    try:
        build_project(project_name, args.config.resolve())
        return 0
    except BuilderError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
