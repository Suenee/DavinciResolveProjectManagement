# Upgrade Protocol

This repository follows the shared Windows upgrade protocol used by the related project family. `upgrade.cmd` is intentionally only a small bootstrap launcher; `upgrade.ps1` is the authoritative upgrade runner.

## User workflow

Normally run only:

```cmd
upgrade.cmd
```

The launcher fetches the current `upgrade.ps1` from `origin/main` into a temporary file and executes that runner. This prevents a running batch file from being replaced while `cmd.exe` is still reading it.

## Required behavior

The runner must:

- target the explicit `main` branch and verify `HEAD == origin/main` after synchronization;
- refuse to destroy tracked local modifications;
- leave untracked runtime/user data untouched;
- preserve and migrate `config.ini` rather than overwrite it;
- install required dependencies automatically and remove only obsolete dependencies previously installed by this project;
- validate Python sources before reporting success;
- keep application logs in repository-root `logs/`;
- keep single-run upgrade diagnostics in repository-root `upgrade.log`;
- always finish `upgrade.log` with exactly one status line:
  - `STATUS: SUCCESS - phase=COMPLETE`
  - `STATUS: WARNING - phase=COMPLETE`
  - `STATUS: FAILED - phase=<PHASE>`
- return a non-zero process exit code on failure.

## Line endings

Windows launch scripts are controlled by `.gitattributes`:

```gitattributes
*.cmd text eol=crlf
*.bat text eol=crlf
*.ps1 text eol=crlf
```

Do not reconstruct or rewrite running CMD launchers through PowerShell text pipelines. Git semantics, not raw byte hashes, are authoritative when checking whether tracked files are modified.

## Runtime data

The following data must survive upgrades and remain untracked:

- `config.ini`
- `runtime/`
- `logs/`
- `upgrade.log`

Legacy `runtime/logs/` content is migrated by `upgrade.ps1` into root `logs/`. Filename collisions are preserved under a timestamped migrated name rather than overwritten.

## Dependencies

The authoritative dependency list currently contains Python, NumPy, and FFmpeg. `dependency_manager.py` records only dependencies installed by this project. Cleanup must never uninstall a dependency merely because it exists on the computer; it may uninstall only a dependency explicitly recorded as project-owned.

## Upgrade phases

Stable phases are used in diagnostics: `SELF-UPDATE`, `MIGRATION`, `DEPENDENCIES`, `CONFIGURATION`, `VERIFY`, and `COMPLETE`.

On any failure, stop in the current phase, preserve user/runtime data, write the failure to `upgrade.log`, and return non-zero.

## Known traps

Do not reintroduce these failure patterns:

- a large label-heavy `upgrade.cmd`;
- self-overwriting the currently executing CMD file;
- `CMD -> PowerShell -> CMD` updater chains;
- broad `git clean -fd`;
- `git reset --hard` as routine synchronization;
- stashing untracked runtime data;
- treating harmless native stderr output as failure when the native exit code is zero;
- comparing CRLF working-tree bytes directly with Git blob bytes;
- overwriting existing user configuration;
- reporting success before required source/dependency verification has completed.

When a new updater defect is discovered, add its recognizable symptom, root cause, and prevention rule here so the same class of failure is not repeated.

## Network-share ownership and local commit protection

**Symptom:** `upgrade.cmd` succeeds from a mapped drive but a subsequent
`git add` reports `fatal: detected dubious ownership` for the underlying UNC path.

**Cause:** A process-local `GIT_CONFIG_COUNT`/`safe.directory` exception
does not persist for manual Git commands; mapped paths may resolve to UNC.

**Rule:** During bootstrap, determine the canonical checkout path using a
one-off Git trust override and persist *only that exact path* in the user's
global `safe.directory` configuration. Never use `safe.directory=*`.
Do not treat a successful updater run as proof that manual Git works.

**Local work:** Upgrades must never use routine `git reset --hard`. Block
staged/substantive tracked changes and use `git merge --ff-only` after
fetching. Reject local-only commits and diverged branches rather than
discarding them. Untracked assets such as `assets/DRPM.png` must remain
untouched. If an untracked file collides with an incoming tracked file,
stop and ask the user to resolve it.

**Diagnostics:** The single-run upgrade log belongs at repository-root
`upgrade.log`; application logs remain under `logs/`.
