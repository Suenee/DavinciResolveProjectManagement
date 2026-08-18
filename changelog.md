# Changelog

## 1.00 - 18.08.2026

- Added managed DaVinci Resolve headless lifecycle with GUI handoff, recovery, and runtime logging.
- Added case-insensitive project folder resolution with interactive selection and sortable creation-date list.
- Added create-or-sync behavior for existing Resolve projects.
- Added Deliver preset configuration with project-specific DELIVERY target folder.
- Added automatic initial timeline population from SHOOTING media.
- SHOOTING root files are ordered by Windows creation time; subfolders are processed by case-insensitive folder name, with files inside each folder ordered by creation time.
- Existing timelines are never modified during later media synchronization.
