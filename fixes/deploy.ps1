# deploy.ps1 — One-click deploy of all fixes to agent_office (Windows / PowerShell 5+)
# Run from repo root: .\fixes\deploy.ps1
# Or with dry-run:   .\fixes\deploy.ps1 -DryRun
param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$Root    = Split-Path -Parent $PSScriptRoot
$AO      = Join-Path $Root "agent_office"
$Fixes   = $PSScriptRoot

function Log($msg) { Write-Host "[deploy] $msg" -ForegroundColor Cyan }
function OK($msg)  { Write-Host "  OK  $msg"    -ForegroundColor Green }
function WARN($msg){ Write-Host "  WARN $msg"   -ForegroundColor Yellow }
function ERR($msg) { Write-Host "  ERR $msg"    -ForegroundColor Red }

if (-not (Test-Path $AO)) {
    ERR "agent_office not found at $AO"
    ERR "Run this script from the repository root that contains agent_office/"
    exit 1
}

Log "Root:         $Root"
Log "agent_office: $AO"
Log "DryRun:       $DryRun"
Log ""

# ─── Step 1: Copy brain_server_v2.py ────────────────────────────────────────
$src  = Join-Path $Fixes "brain_server_v2.py"
$dest = Join-Path $AO    "brain_server_v2.py"
Log "STEP 1: Deploy brain_server_v2.py"
if ($DryRun) {
    WARN "DryRun — would copy $src → $dest"
} else {
    Copy-Item $src $dest -Force
    OK "Copied → $dest"
}

# ─── Step 2: Copy circuit_breaker.py ────────────────────────────────────────
$cbSrc  = Join-Path $Fixes "circuit_breaker.py"
$coreDir = Join-Path $AO   "core"
Log "STEP 2: Deploy circuit_breaker.py"
if (Test-Path $coreDir) {
    $cbDest = Join-Path $coreDir "circuit_breaker.py"
    if ($DryRun) {
        WARN "DryRun — would copy $cbSrc → $cbDest"
    } else {
        Copy-Item $cbSrc $cbDest -Force
        OK "Copied → $cbDest"
    }
} else {
    WARN "core/ not found, copying to agent_office root"
    if (-not $DryRun) {
        Copy-Item $cbSrc (Join-Path $AO "circuit_breaker.py") -Force
    }
}

# ─── Step 3: Run update_models.py ───────────────────────────────────────────
Log "STEP 3: Update model config"
$updateScript = Join-Path $Fixes "update_models.py"
if ($DryRun) {
    Log "  DryRun — running update_models.py --dry-run"
    python $updateScript --dry-run
} else {
    python $updateScript
    OK "Model config updated"
}

# ─── Step 4: Kill old brain_server if running ───────────────────────────────
Log "STEP 4: Verify old brain_server processes"
$oldProcs = Get-Process -Name python -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowTitle -match "brain_server" -or (
        (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine -match "brain_server\.py(?!_v2)")
    }
if ($oldProcs) {
    WARN "Found old brain_server process(es): $($oldProcs.Id -join ', ')"
    if (-not $DryRun) {
        $oldProcs | Stop-Process -Force
        OK "Stopped old brain_server"
    }
} else {
    OK "No stale brain_server processes"
}

# ─── Step 5: PM2 — register and start brain_server_v2 ───────────────────────
Log "STEP 5: PM2 — register brain_server_v2"
$pm2Check = pm2 list 2>$null | Select-String "brain"
if ($pm2Check -match "brain-мост") {
    if ($DryRun) {
        WARN "DryRun — would: pm2 restart brain-мост"
    } else {
        pm2 restart "brain-мост"
        OK "Restarted existing PM2 process brain-мост"
    }
} else {
    if ($DryRun) {
        WARN "DryRun — would: pm2 start brain_server_v2.py --name brain-мост --interpreter python"
    } else {
        Set-Location $AO
        pm2 start brain_server_v2.py --name "brain-мост" --interpreter python
        Set-Location $Root
        OK "Started brain-мост via PM2"
    }
}

# ─── Step 6: Resurrect git-backup if stopped ────────────────────────────────
Log "STEP 6: Check git-backup PM2 process"
$gitBak = pm2 list 2>$null | Select-String "git-backup"
if ($gitBak -match "stopped") {
    WARN "git-backup is STOPPED — restarting"
    if (-not $DryRun) {
        pm2 restart git-backup
        OK "git-backup restarted"
    }
} elseif ($gitBak) {
    OK "git-backup is running"
} else {
    WARN "git-backup not found in PM2 list — check manually"
}

# ─── Step 7: pm2 save ───────────────────────────────────────────────────────
Log "STEP 7: pm2 save"
if (-not $DryRun) {
    pm2 save
    OK "PM2 config saved"
}

# ─── Step 8: Health check ────────────────────────────────────────────────────
Log "STEP 8: Health check :9999"
Start-Sleep -Seconds 3
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:9999/status" -TimeoutSec 10
    OK "brain_server_v2 alive: qdrant=$($resp.checks.qdrant.status) ollama=$($resp.checks.ollama.status)"
} catch {
    WARN "Health check failed: $_"
    WARN "Try manually: curl http://localhost:9999/status"
}

Log ""
Log "═══════════════════════════════════════════"
Log "Deploy complete$(if ($DryRun) { ' [DRY RUN — no changes made]' })"
Log ""
Log "Next steps:"
Log "  - Test: curl http://localhost:9999/"
Log "  - Test POST: curl -X POST http://localhost:9999/free_brain -H 'Content-Type: application/json' -d '{\"prompt\":\"hello\"}'"
Log "  - ngrok: ngrok http 9999 (if tunnel needed)"
Log "  - Logs: pm2 logs brain-мост"
