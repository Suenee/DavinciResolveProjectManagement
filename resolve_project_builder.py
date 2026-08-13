#!/usr/bin/env python3
"""Create and prepare a DaVinci Resolve project from a production folder."""

from __future__ import annotations

import argparse
import configparser
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Iterable

APP_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = APP_DIR / "config.ini"
EXAMPLE_CONFIG = APP_DIR / "config.example.ini"
OPTIONAL_MEDIA_DIRS = ("IMAGES", "PHOTOS", "AUDIO")
DATE_PREFIX_RE = re.compile(r"^\d{8}\s+")


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

    resolve_folder = parser.get(
        "DaVinciResolve", "ResolveProjectFolder", fallback=""
    ).strip()

    return Path(project_root_raw), resolve_folder


def import_resolve_module():
    try:
        import DaVinciResolveScript as dvr_script  # type: ignore
        return dvr_script
    except ImportError:
        program_data = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
        modules_dir = (
            program_data
            / "Blackmagic Design"
            / "DaVinci Resolve"
            / "Support"
            / "Developer"
            / "Scripting"
            / "Modules"
        )
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
            "Cannot connect to DaVinci Resolve. Start Resolve Studio and enable "
            "External scripting using Local in Preferences."
        )
    return resolve


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
                f"WARNING: Resolve imported {len(imported)} of {len(files)} files from: "
                f"{source_dir}"
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
    parser.add_argument("project_name", help='Example: "20260810 Zprávy z Exopolitiky 25"')
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to INI configuration file (default: config.ini next to the script).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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
