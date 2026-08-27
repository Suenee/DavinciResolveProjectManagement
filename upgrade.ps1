$ErrorActionPreference = 'Stop'
$Repo = $env:DRPM_REPO
$TargetBranch = if ($env:DRPM_BRANCH) { $env:DRPM_BRANCH } else { 'main' }
$RunnerRevision = '1.02-bootstrap-crlf-safe'
$AppVersion = '1.11'
if (-not $Repo) { $Repo = Split-Path -Parent $MyInvocation.MyCommand.Path }
$Repo = [System.IO.Path]::GetFullPath($Repo).TrimEnd('\')
$Log = Join-Path $Repo 'upgrade.log'
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
function Git([string[]]$GitArgs,[switch]$AllowFailure) { return Run-Native 'git.exe' $GitArgs -AllowFailure:$AllowFailure }
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
    $link="$env:LOCALAPPDATA\Microsoft\WinGet\Links\ffmpeg.exe"
    if (Test-Path $link) { return $link }
    return $null
}
function Mark-Dependency([string]$Python,[string]$Name,[string]$Kind,[string]$Package) {
    $dm=Join-Path $Repo 'dependency_manager.py'
    if (Test-Path $dm) { Run-Native $Python @($dm,'mark',$Name,$Kind,$Package) | Out-Null }
}
function Get-TrackedChanges {
    $lines = @(& git.exe status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0) { Fail 'Cannot inspect Git working tree.' }
    return @($lines | Where-Object { $_ -and $_.Trim() })
}
function Get-ChangedPath([string]$StatusLine) {
    if ($StatusLine.Length -lt 4) { return '' }
    $path=$StatusLine.Substring(3).Trim()
    if ($path.StartsWith('"') -and $path.EndsWith('"')) { $path=$path.Trim('"') }
    if ($path -like '* -> *') { $path=($path -split ' -> ')[-1] }
    return $path.Replace('\','/')
}

try {
    Set-Location $Repo
    Info "=== DaVinci Resolve Project Management upgrade ==="
    Info "Application version: $AppVersion"
    Info "Upgrade runner: $RunnerRevision"
    Info "Date/time: $(Get-Date -Format 'dd.MM.yyyy HH:mm:ss.fff')"
    Info "Repository: $Repo"
    Info "Target branch: $TargetBranch"
    $startCommit = (& git.exe rev-parse HEAD 2>$null)
    Info "Starting commit: $startCommit"
    Info "Runner architecture: CMD bootstrap -> temporary authoritative PowerShell runner"

    if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { Fail 'Git was not found.' }
    Git @('fetch','origin',$TargetBranch) | Out-Null

    # Bootstrap files are authoritative remote state. Windows CRLF materialization can make
    # upgrade.cmd/upgrade.ps1 look modified although there is no user change. The shared
    # upgrade protocol explicitly requires us not to let that false dirty state block update.
    $bootstrap=@('upgrade.cmd','upgrade.ps1','.gitattributes')
    $tracked=Get-TrackedChanges
    if ($tracked) {
        $realChanges=@()
        $bootstrapChanges=@()
        foreach($line in $tracked) {
            $path=Get-ChangedPath $line
            if ($bootstrap -contains $path) { $bootstrapChanges += $path } else { $realChanges += $line }
        }
        if ($realChanges.Count -gt 0) {
            Fail "Local tracked changes detected. Upgrade stopped to protect local work.`n$($realChanges -join "`n")"
        }
        if ($bootstrapChanges.Count -gt 0) {
            Warn ("Bootstrap files appear dirty and will be restored from Git semantics: " + (($bootstrapChanges | Sort-Object -Unique) -join ', '))
            # Restore only explicit bootstrap files. Never touch runtime/untracked data.
            foreach($path in ($bootstrapChanges | Sort-Object -Unique)) {
                Git @('restore','--source','HEAD','--worktree','--',$path) | Out-Null
            }
            $remaining=Get-TrackedChanges
            if ($remaining) { Fail "Tracked changes remain after bootstrap normalization.`n$($remaining -join "`n")" }
        }
    }

    $currentBranch = (& git.exe branch --show-current).Trim()
    if ($currentBranch -ne $TargetBranch) { Git @('checkout',$TargetBranch) | Out-Null }
    Git @('merge','--ff-only',"origin/$TargetBranch") | Out-Null
    $head = (& git.exe rev-parse HEAD).Trim(); $remote = (& git.exe rev-parse "origin/$TargetBranch").Trim()
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
    $numpyCode=Run-Native $python @('-c','import numpy') -AllowFailure
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
        $ffmpeg=Find-FFmpeg
        if ($ffmpeg) { Mark-Dependency $python 'ffmpeg' 'winget' $pkg }
    }
    if (-not $ffmpeg) { Fail 'FFmpeg could not be located after installation.' }
    Info "FFmpeg: $ffmpeg"

    Set-Phase 'CONFIGURATION'
    $example=Join-Path $Repo 'config.example.ini'; if (-not (Test-Path $example)) { Fail 'config.example.ini is missing.' }
    Run-Native $python @((Join-Path $Repo 'config_migrate.py')) | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $Repo 'runtime'),(Join-Path $Repo 'runtime\intro_fingerprints'),$newLogs | Out-Null

    Set-Phase 'VERIFY'
    $sources=@('resolve_project_builder.py','managed_builder.py','managed_builder_runner.py','project_browser.py','project_update.py','project_update_dialog.py','ui_windows.py','timeline_audio.py','intro_fingerprint.py','intro_match_routing.py','intro_detection.py','resolve_lifecycle.py','resolve_gui.py','config_migrate.py','dependency_manager.py','verified_import.py')
    $existing=@(); foreach($s in $sources){$p=Join-Path $Repo $s;if(Test-Path $p){$existing+=$p}else{Warn "Optional/expected source missing: $s"}}
    Run-Native $python (@('-m','py_compile')+$existing) | Out-Null
    $dvr="$env:PROGRAMDATA\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules\DaVinciResolveScript.py"
    if (Test-Path $dvr) { Ok 'DaVinci Resolve scripting module found.' } else { Warn "DaVinci Resolve scripting module not found at $dvr" }

    Set-Phase 'COMPLETE'
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
