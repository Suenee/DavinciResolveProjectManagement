$ErrorActionPreference = 'Stop'
$Repo = $env:DRPM_REPO
$TargetBranch = if ($env:DRPM_BRANCH) { $env:DRPM_BRANCH } else { 'main' }
$RunnerRevision = '1.22-dependency-discovery'
$TargetVersion = 'unknown'
$CurrentVersion = 'unknown'
if (-not $Repo) { $Repo = Split-Path -Parent $MyInvocation.MyCommand.Path }
$Repo = [System.IO.Path]::GetFullPath($Repo).TrimEnd('\')
$LogDir = Join-Path $Repo 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir 'upgrade.log'
$Phase = 'SELF-UPDATE'
$Warnings = 0
$FinalStatus = $null
Set-Content -LiteralPath $Log -Value '' -Encoding UTF8
Start-Transcript -LiteralPath $Log -Append | Out-Null

function Info([string]$Text) { Write-Host $Text -ForegroundColor Gray }
function Ok([string]$Text) { Write-Host $Text -ForegroundColor Green }
function Warn([string]$Text) { $script:Warnings++; Write-Host "WARNING: $Text" -ForegroundColor Yellow }
function Fail([string]$Text) { Write-Host "ERROR: $Text" -ForegroundColor Red; throw $Text }
function Set-Phase([string]$Name) { $script:Phase=$Name; Info "--- $Name ---" }
function Run-Native([string]$Exe,[string[]]$NativeArgs,[switch]$AllowFailure) {
    $oldPreference=$ErrorActionPreference
    $ErrorActionPreference='Continue'
    try { & $Exe @NativeArgs; $code=$LASTEXITCODE }
    finally { $ErrorActionPreference=$oldPreference }
    if ($code -ne 0 -and -not $AllowFailure) { Fail "$Exe failed with exit code $code" }
    return $code
}
function Invoke-Git([string[]]$GitArgs,[switch]$AllowFailure) { return Run-Native 'git.exe' $GitArgs -AllowFailure:$AllowFailure }
function Find-Python {
    foreach ($name in @('python.exe','python3.exe')) {
        $cmd=Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) {
            $oldPreference=$ErrorActionPreference;$ErrorActionPreference='Continue'
            try { & $cmd.Source --version *> $null; $code=$LASTEXITCODE } finally { $ErrorActionPreference=$oldPreference }
            if ($code -eq 0) { return $cmd.Source }
        }
    }
    foreach ($p in @("$env:LOCALAPPDATA\Programs\Python\Python313\python.exe","$env:LOCALAPPDATA\Programs\Python\Python314\python.exe")) { if (Test-Path $p) { return $p } }
    return $null
}
function Find-FFmpeg {
    $cmd=Get-Command 'ffmpeg.exe' -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($link in @("$env:LOCALAPPDATA\Microsoft\WinGet\Links\ffmpeg.exe","$env:ProgramFiles\WinGet\Links\ffmpeg.exe")) {
        if (Test-Path $link) { return $link }
    }
    foreach ($root in @("$env:LOCALAPPDATA\Microsoft\WinGet\Packages","$env:ProgramFiles\WinGet\Packages")) {
        if (-not (Test-Path $root)) { continue }
        $candidate=Get-ChildItem -LiteralPath $root -Filter ffmpeg.exe -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '[\\/]Gyan\.FFmpeg[^\\/]*[\\/]' } |
            Select-Object -First 1
        if ($candidate) { return $candidate.FullName }
    }
    return $null
}
function Mark-Dependency([string]$Python,[string]$Name,[string]$Kind,[string]$Package) {
    $dm=Join-Path $Repo 'dependency_manager.py'
    if (Test-Path $dm) { Run-Native $Python @($dm,'mark',$Name,$Kind,$Package) | Out-Null }
}

try {
    Set-Location $Repo
    Info "=== DaVinci Resolve Project Management upgrade ==="
    if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { Fail 'Git was not found.' }
    $startCommit = (& git.exe rev-parse HEAD 2>$null)
    try {
        $localVersionFile=Join-Path $Repo 'VERSION'
        if (Test-Path $localVersionFile) { $CurrentVersion=(Get-Content -LiteralPath $localVersionFile -Raw).Trim() }
    } catch {}
    try {
        $remoteVersion=(& git.exe show "origin/${TargetBranch}:VERSION" 2>$null)
        if ($LASTEXITCODE -eq 0 -and $remoteVersion) { $TargetVersion=($remoteVersion | Select-Object -First 1).Trim() }
    } catch {}
    if ($TargetVersion -eq 'unknown') { Fail "Cannot determine target application version from origin/${TargetBranch}:VERSION" }
    Info "Application: DaVinci Resolve Project Management"
    if ($CurrentVersion -eq $TargetVersion) { Info ("Current:     {0} / Target: {1} - already current" -f $CurrentVersion,$TargetVersion) }
    else { Info ("Current:     {0}" -f $CurrentVersion); Info ("Target:      {0}" -f $TargetVersion) }
    Info "Updater:     $RunnerRevision"
    Info "Branch:      $TargetBranch"
    Info "Date/time: $(Get-Date -Format 'dd.MM.yyyy HH:mm:ss.fff')"
    Info "Repository: $Repo"
    Info "Starting commit: $startCommit"
    Info "Runner architecture: CMD bootstrap -> temporary authoritative PowerShell runner"


    Set-Phase 'SELF-UPDATE'
    if ($env:DRPM_FRESH_BOOTSTRAP -eq '1') {
        Info 'Fresh bootstrap confirmed by launcher; local-change guard is not applicable before the first authoritative reset.'
    } else {
        # Windows/network checkouts may report tracked CMD/PS1 files as dirty only
        # because the worktree has CRLF while Git compares normalized LF content.
        # Ignore end-of-line whitespace for the safety decision, but keep blocking
        # any substantive local source modification.
        $unstaged=Run-Native 'git.exe' @('diff','--ignore-space-at-eol','--quiet') -AllowFailure
        if ($unstaged -ne 0) {
            $names=@(& git.exe diff --ignore-space-at-eol --name-only)
            $nonBootstrap=@($names | Where-Object { $_ -and $_ -notin @('upgrade.cmd','upgrade.ps1','.gitattributes') })
            if ($nonBootstrap.Count -gt 0) { Fail "Local tracked source files contain substantive changes: $($nonBootstrap -join ', ')" }
            Warn 'Only bootstrap files differ locally; remote tracked state will be authoritative.'
        } else {
            $rawUnstaged=Run-Native 'git.exe' @('diff','--quiet') -AllowFailure
            if ($rawUnstaged -ne 0) { Info 'Ignoring worktree differences caused only by end-of-line normalization.' }
        }
        $staged=Run-Native 'git.exe' @('diff','--cached','--quiet') -AllowFailure
        if ($staged -ne 0) { Fail 'Local staged source changes exist. Commit/revert them before upgrade.' }
    }

    Invoke-Git @('fetch','origin',$TargetBranch) | Out-Null
    $currentBranch=(& git.exe branch --show-current).Trim()
    if ($currentBranch -ne $TargetBranch) {
        $checkout=Run-Native 'git.exe' @('checkout',$TargetBranch) -AllowFailure
        if ($checkout -ne 0) { Invoke-Git @('checkout','-B',$TargetBranch,"origin/$TargetBranch") | Out-Null }
    }
    Invoke-Git @('reset','--hard',"origin/$TargetBranch") | Out-Null
    $head=(& git.exe rev-parse HEAD).Trim();$remote=(& git.exe rev-parse "origin/$TargetBranch").Trim()
    if ($head -ne $remote) { Fail "Repository verification failed: HEAD != origin/$TargetBranch" }
    Ok "Repository synchronized: $head"

    Set-Phase 'MIGRATION'
    $oldLogs=Join-Path $Repo 'runtime\logs'; $newLogs=Join-Path $Repo 'logs'
    New-Item -ItemType Directory -Force -Path $newLogs | Out-Null
    if (Test-Path $oldLogs) {
        foreach ($file in Get-ChildItem -LiteralPath $oldLogs -File -ErrorAction SilentlyContinue) {
            $dest=Join-Path $newLogs $file.Name
            if (Test-Path $dest) { $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'; $dest=Join-Path $newLogs ("migrated-$stamp-"+$file.Name) }
            Move-Item -LiteralPath $file.FullName -Destination $dest
        }
        if (-not (Get-ChildItem -LiteralPath $oldLogs -Force -ErrorAction SilentlyContinue)) { Remove-Item -LiteralPath $oldLogs -Force }
        Ok 'Application logs migrated to repository-root logs\.'
    }

    Set-Phase 'DEPENDENCIES'
    $python=Find-Python
    $pythonInstalled=$false
    if (-not $python) {
        if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { Fail 'Python is missing and WinGet is unavailable.' }
        Run-Native 'winget.exe' @('install','--id','Python.Python.3.13','--exact','--scope','user','--silent','--accept-package-agreements','--accept-source-agreements') | Out-Null
        $python=Find-Python; $pythonInstalled=$true
    }
    if (-not $python) { Fail 'Python could not be located after installation.' }
    Info "Python: $python"; Run-Native $python @('--version') | Out-Null
    if ($pythonInstalled) { Mark-Dependency $python 'python' 'winget' 'Python.Python.3.13' }
    $dm=Join-Path $Repo 'dependency_manager.py'
    if (Test-Path $dm) { Run-Native $python @($dm,'cleanup','python','numpy','ffmpeg') | Out-Null }
    # Probe optional Python modules without leaking an expected traceback to
    # PowerShell 5.1's native stderr/error stream.
    $oldPreference=$ErrorActionPreference;$ErrorActionPreference='Continue'
    try {
        & $python -c "import numpy" *> $null
        $numpyCode=$LASTEXITCODE
    } finally { $ErrorActionPreference=$oldPreference }
    if ($numpyCode -ne 0) {
        Run-Native $python @('-m','ensurepip','--upgrade') | Out-Null
        Run-Native $python @('-m','pip','install','--disable-pip-version-check','--upgrade','numpy') | Out-Null
        Mark-Dependency $python 'numpy' 'pip' 'numpy'
    }
    $ffmpeg=Find-FFmpeg
    if (-not $ffmpeg) {
        if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) { Fail 'FFmpeg is missing and WinGet is unavailable.' }
        $code=Run-Native 'winget.exe' @('install','--id','Gyan.FFmpeg','--exact','--silent','--accept-package-agreements','--accept-source-agreements') -AllowFailure
        $pkg='Gyan.FFmpeg'
        if ($code -ne 0) { Run-Native 'winget.exe' @('install','--id','Gyan.FFmpeg.Essentials','--exact','--silent','--accept-package-agreements','--accept-source-agreements') | Out-Null; $pkg='Gyan.FFmpeg.Essentials' }
        # WinGet portable packages may be installed successfully while the
        # current process still has the old PATH. Find-FFmpeg also searches the
        # package payload directly instead of requiring a shell restart.
        $ffmpeg=Find-FFmpeg
        if ($ffmpeg) { Mark-Dependency $python 'ffmpeg' 'winget' $pkg }
    }
    if (-not $ffmpeg) { Fail 'FFmpeg could not be located after installation. WinGet may have installed the package, but neither its command alias nor package payload was found.' }
    Info "FFmpeg: $ffmpeg"

    Set-Phase 'CONFIGURATION'
    $example=Join-Path $Repo 'config.example.ini'; if (-not (Test-Path $example)) { Fail 'config.example.ini is missing.' }
    Run-Native $python @((Join-Path $Repo 'config_migrate.py')) | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $Repo 'runtime'),(Join-Path $Repo 'runtime\intro_fingerprints'),$newLogs | Out-Null

    Set-Phase 'VERIFY'
    $sources=@('resolve_project_builder.py','managed_builder.py','managed_builder_runner.py','project_browser.py','project_update.py','project_update_dialog.py','ui_windows.py','timeline_audio.py','intro_fingerprint.py','intro_match_routing.py','intro_detection.py','resolve_lifecycle.py','resolve_gui.py','config_migrate.py','dependency_manager.py','verified_import.py','timeline_assets.py','silence_trim.py','project_paths.py','project_profiles.py','i18n.py')
    $existing=@(); foreach($s in $sources){$p=Join-Path $Repo $s;if(Test-Path $p){$existing+=$p}else{Warn "Optional/expected source missing: $s"}}
    Run-Native $python (@('-m','py_compile')+$existing) | Out-Null
    $smoke="import sys;sys.path.insert(0,r'$Repo');import i18n;assert i18n.resolve_language('en')=='en';assert i18n.resolve_language('cs')=='cs';import managed_builder,project_update,project_browser"
    Run-Native $python @('-c',$smoke) | Out-Null
    $dvr="$env:PROGRAMDATA\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\DaVinciResolveScript.py"
    if (Test-Path $dvr) { Ok 'DaVinci Resolve scripting module found.' } else { Warn "DaVinci Resolve scripting module not found at $dvr" }

    Set-Phase 'COMPLETE'
    Write-Host ''
    Write-Host '==============================================' -ForegroundColor Green
    Write-Host 'UPGRADE SUCCESSFUL' -ForegroundColor Green
    Write-Host "DaVinci Resolve Project Management v$TargetVersion" -ForegroundColor Green
    Write-Host '==============================================' -ForegroundColor Green
    if ($Warnings -gt 0) { $FinalStatus='STATUS: WARNING - phase=COMPLETE' } else { $FinalStatus='STATUS: SUCCESS - phase=COMPLETE' }
}
catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    $FinalStatus="STATUS: FAILED - phase=$Phase"
}
finally {
    try { Stop-Transcript | Out-Null } catch {}
    if (-not $FinalStatus) { $FinalStatus="STATUS: FAILED - phase=$Phase" }
    Add-Content -LiteralPath $Log -Value $FinalStatus -Encoding UTF8
    if ($FinalStatus -like 'STATUS: FAILED*') { Write-Host $FinalStatus -ForegroundColor Red } elseif ($FinalStatus -like 'STATUS: WARNING*') { Write-Host $FinalStatus -ForegroundColor Yellow } else { Write-Host $FinalStatus -ForegroundColor Green }
}
if ($FinalStatus -like 'STATUS: FAILED*') { exit 1 } else { exit 0 }
