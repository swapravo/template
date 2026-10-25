# =============================================================================
# manage.ps1 — App lifecycle manager (PowerShell)
# Usage: .\manage.ps1 [start|restart|reset|backup]
#        Run without arguments for an interactive menu.
# Requires: Docker Desktop with 'docker compose' v2
# =============================================================================

#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('start', 'restart', 'reset', 'backup', '')]
    [string]$Command = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackupDir  = Join-Path $ScriptDir 'backups'
$ComposeFile = Join-Path $ScriptDir 'docker-compose.yml'
$EnvFile     = Join-Path $ScriptDir '.env'

# ── Colour helpers ────────────────────────────────────────────────────────────
function Write-Info    { param([string]$Msg) Write-Host "[INFO]  $Msg" -ForegroundColor Cyan }
function Write-Ok      { param([string]$Msg) Write-Host "[OK]    $Msg" -ForegroundColor Green }
function Write-Warn    { param([string]$Msg) Write-Host "[WARN]  $Msg" -ForegroundColor Yellow }
function Write-Err     { param([string]$Msg) Write-Host "[ERROR] $Msg" -ForegroundColor Red }
function Write-Header  {
    param([string]$Title)
    Write-Host ""
    Write-Host "══════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $Title"                               -ForegroundColor Cyan
    Write-Host "══════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
}

# ── .env loader ───────────────────────────────────────────────────────────────
function Import-DotEnv {
    if (-not (Test-Path $EnvFile)) {
        Write-Err ".env not found. Copy .env.example to .env and fill it in."
        exit 1
    }
    $script:Env = @{}
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^([A-Z_][A-Z0-9_]*)=(.*)$') {
            $script:Env[$Matches[1]] = $Matches[2]
        }
    }
}

# ── Docker pre-flight ─────────────────────────────────────────────────────────
function Assert-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Err "docker not found. Install Docker Desktop and try again."
        exit 1
    }
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "Docker daemon is not running. Start Docker Desktop and try again."
        exit 1
    }
}

# ── Helper: check if a service container is running ───────────────────────────
function Test-ServiceRunning {
    param([string]$Service)
    $output = docker compose -f $ComposeFile ps $Service 2>&1
    return $output -match 'running|Up'
}

# ── 1. Pull latest & start ────────────────────────────────────────────────────
function Invoke-Start {
    Write-Header "Pull latest & start"
    Assert-Docker
    Import-DotEnv

    Write-Info "Pulling latest code from git..."
    git -C $ScriptDir pull --ff-only
    if ($LASTEXITCODE -ne 0) { Write-Err "git pull failed."; exit 1 }

    Write-Info "Building images and starting all services..."
    docker compose -f $ComposeFile up --build -d
    if ($LASTEXITCODE -ne 0) { Write-Err "docker compose up failed."; exit 1 }

    Write-Ok "All services started. Streaming logs (Ctrl+C to detach)..."
    Write-Host ""
    docker compose -f $ComposeFile logs -f
}

# ── 2. Restart ────────────────────────────────────────────────────────────────
function Invoke-Restart {
    Write-Header "Restart"
    Assert-Docker

    Write-Info "Restarting all services..."
    docker compose -f $ComposeFile restart
    if ($LASTEXITCODE -ne 0) { Write-Err "docker compose restart failed."; exit 1 }

    Write-Ok "All services restarted. Streaming logs (Ctrl+C to detach)..."
    Write-Host ""
    docker compose -f $ComposeFile logs -f
}

# ── 3. Reset (remove volumes) ─────────────────────────────────────────────────
function Invoke-Reset {
    Write-Header "Reset — Volume Wipe"
    Assert-Docker

    Write-Warn "This will DESTROY all data volumes (database, redis, file storage)."
    Write-Warn "This action is IRREVERSIBLE."
    Write-Host ""
    $confirm = Read-Host "Type 'yes' to confirm"

    if ($confirm -ne 'yes') {
        Write-Info "Aborted — no changes made."
        return
    }

    Write-Info "Stopping and removing containers + volumes..."
    docker compose -f $ComposeFile down --volumes --remove-orphans
    if ($LASTEXITCODE -ne 0) { Write-Err "docker compose down failed."; exit 1 }

    Write-Ok "Volumes removed. To start fresh run:  .\manage.ps1 start"
}

# ── 4. Backup ─────────────────────────────────────────────────────────────────
function Invoke-Backup {
    Write-Header "Backup"
    Assert-Docker
    Import-DotEnv

    $Timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
    $Dest = Join-Path $BackupDir $Timestamp
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null

    Write-Info "Backup destination: $Dest"
    Write-Host ""

    # ── PostgreSQL ──────────────────────────────────────────────────────────
    Write-Info "Dumping PostgreSQL (pg_dumpall)..."
    if (Test-ServiceRunning 'postgres') {
        $pgUser = if ($script:Env.ContainsKey('POSTGRES_USER')) { $script:Env['POSTGRES_USER'] } else { 'postgres' }
        $pgDump = Join-Path $Dest 'postgres.sql'
        docker compose -f $ComposeFile exec -T postgres pg_dumpall -U $pgUser | Out-File -FilePath $pgDump -Encoding UTF8
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "PostgreSQL → $pgDump"
        } else {
            Write-Warn "pg_dumpall failed — check postgres container logs."
        }
    } else {
        Write-Warn "postgres container is not running — skipping DB backup."
    }

    # ── Redis ───────────────────────────────────────────────────────────────
    Write-Info "Snapshotting Redis (BGSAVE)..."
    if (Test-ServiceRunning 'redis') {
        docker compose -f $ComposeFile exec -T redis redis-cli BGSAVE | Out-Null
        Start-Sleep -Seconds 2
        $rdbDest = Join-Path $Dest 'redis.rdb'
        docker compose -f $ComposeFile cp redis:/data/dump.rdb $rdbDest 2>&1 | Out-Null
        if (Test-Path $rdbDest) {
            Write-Ok "Redis → $rdbDest"
        } else {
            Write-Warn "Could not copy Redis RDB (may not exist if redis has no data yet)."
        }
    } else {
        Write-Warn "redis container is not running — skipping Redis backup."
    }

    # ── .env ────────────────────────────────────────────────────────────────
    Write-Info "Backing up .env..."
    Copy-Item $EnvFile (Join-Path $Dest '.env')
    Write-Ok ".env → $(Join-Path $Dest '.env')"

    # ── Manifest ──────────────────────────────────────────────────────────────
    $gitCommit = (git -C $ScriptDir rev-parse HEAD 2>&1) -join ''
    $gitBranch = (git -C $ScriptDir rev-parse --abbrev-ref HEAD 2>&1) -join ''
    @(
        "Backup created at: $Timestamp",
        "Git commit: $gitCommit",
        "Git branch: $gitBranch"
    ) | Out-File (Join-Path $Dest 'manifest.txt') -Encoding UTF8

    Write-Host ""
    Write-Ok "Backup complete → $Dest"
    Write-Host ""
    Get-ChildItem $Dest | Format-Table Name, Length, LastWriteTime -AutoSize
}

# ── Interactive menu ──────────────────────────────────────────────────────────
function Show-Menu {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║         App Manager                  ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  " -NoNewline; Write-Host "1)" -ForegroundColor Green  -NoNewline; Write-Host " Pull latest & start"
    Write-Host "  " -NoNewline; Write-Host "2)" -ForegroundColor Yellow -NoNewline; Write-Host " Restart"
    Write-Host "  " -NoNewline; Write-Host "3)" -ForegroundColor Red    -NoNewline; Write-Host " Reset  " -NoNewline; Write-Host "(destroys all data volumes)" -ForegroundColor Red
    Write-Host "  " -NoNewline; Write-Host "4)" -ForegroundColor Cyan   -NoNewline; Write-Host " Backup"
    Write-Host "  5) Exit"
    Write-Host ""
    $choice = Read-Host "Choose an option [1-5]"
    switch ($choice) {
        '1' { Invoke-Start   }
        '2' { Invoke-Restart }
        '3' { Invoke-Reset   }
        '4' { Invoke-Backup  }
        '5' { exit 0         }
        default {
            Write-Err "Invalid option: $choice"
            Show-Menu
        }
    }
}

# ── Entry point ───────────────────────────────────────────────────────────────
switch ($Command) {
    'start'   { Invoke-Start   }
    'restart' { Invoke-Restart }
    'reset'   { Invoke-Reset   }
    'backup'  { Invoke-Backup  }
    ''        { Show-Menu      }
}
