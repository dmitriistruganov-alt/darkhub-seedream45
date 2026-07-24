# deploy.ps1 — One-click deploy всех исправлений Agent Office (Windows / PowerShell 5+)
# Запуск из корня репо: .\fixes\deploy.ps1
# Dry-run:              .\fixes\deploy.ps1 -DryRun
param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$Root  = Split-Path -Parent $PSScriptRoot
$AO    = Join-Path $Root "agent_office"
$Fixes = $PSScriptRoot

function Log($msg) { Write-Host "[deploy] $msg" -ForegroundColor Cyan }
function OK($msg)  { Write-Host "  OK  $msg"    -ForegroundColor Green }
function WARN($msg){ Write-Host "  WARN $msg"   -ForegroundColor Yellow }
function ERR($msg) { Write-Host "  ERR $msg"    -ForegroundColor Red; exit 1 }

if (-not (Test-Path $AO)) {
    ERR "agent_office не найден: $AO — запускай из корня репо"
}

Log "Root:   $Root"
Log "AO:     $AO"
Log "DryRun: $DryRun"
Log ""

# ─── Step 1: brain_server_v2.py ──────────────────────────────────────────────
Log "STEP 1: brain_server_v2.py"
$src  = Join-Path $Fixes "brain_server_v2.py"
$dest = Join-Path $AO    "brain_server_v2.py"
if ($DryRun) { WARN "DryRun — would copy → $dest" }
else { Copy-Item $src $dest -Force; OK "Скопирован → $dest" }

# ─── Step 2: circuit_breaker.py ──────────────────────────────────────────────
Log "STEP 2: circuit_breaker.py"
$cbSrc = Join-Path $Fixes "circuit_breaker.py"
$coreDir = Join-Path $AO "core"
$cbDest = if (Test-Path $coreDir) { Join-Path $coreDir "circuit_breaker.py" } else { Join-Path $AO "circuit_breaker.py" }
if ($DryRun) { WARN "DryRun — would copy → $cbDest" }
else { Copy-Item $cbSrc $cbDest -Force; OK "Скопирован → $cbDest" }

# ─── Step 3: update_models.py ────────────────────────────────────────────────
Log "STEP 3: update_models.py — обновить модели"
$updateScript = Join-Path $Fixes "update_models.py"
if ($DryRun) { python $updateScript --dry-run }
else { python $updateScript; OK "Конфиг моделей обновлён" }

# ─── Step 4: Удалить старый brain_server процесс ─────────────────────────────
Log "STEP 4: Остановить старый brain_server"
$pm2List = pm2 jlist 2>$null | ConvertFrom-Json -ErrorAction SilentlyContinue
if ($pm2List) {
    $oldBrain = $pm2List | Where-Object { $_.name -eq "brain-мост" }
    if ($oldBrain) {
        $status = $oldBrain.pm2_env.status
        if ($status -ne "online" -or $DryRun) {
            if (-not $DryRun) {
                pm2 delete "brain-мост" 2>$null
                OK "Удалён старый brain-мост (статус: $status)"
            }
        }
    }
}

# ─── Step 5: PM2 — brain_server_v2 ───────────────────────────────────────────
Log "STEP 5: PM2 — регистрация brain_server_v2"
$brainRunning = pm2 list 2>$null | Select-String "brain-мост" | Select-String "online"
if ($brainRunning) {
    if ($DryRun) { WARN "DryRun — would: pm2 restart brain-мост" }
    else { pm2 restart "brain-мост"; OK "brain-мост перезапущен" }
} else {
    if ($DryRun) { WARN "DryRun — would: pm2 start brain_server_v2.py" }
    else {
        Set-Location $AO
        pm2 start brain_server_v2.py --name "brain-мост" --interpreter python
        Set-Location $Root
        OK "brain-мост запущен через PM2"
    }
}

# ─── Step 6: health_monitor ──────────────────────────────────────────────────
Log "STEP 6: health_monitor.py"
$hmSrc  = Join-Path $Fixes "health_monitor.py"
$hmDest = Join-Path $AO    "fixes\health_monitor.py"
New-Item -ItemType Directory -Path (Split-Path $hmDest) -Force | Out-Null
if (-not $DryRun) {
    Copy-Item $hmSrc $hmDest -Force
    $hmRunning = pm2 list 2>$null | Select-String "health-monitor"
    if (-not $hmRunning) {
        pm2 start $hmDest --name "health-monitor" --interpreter python
        OK "health-monitor запущен"
    } else {
        pm2 restart "health-monitor"
        OK "health-monitor перезапущен"
    }
} else { WARN "DryRun — would deploy health_monitor" }

# ─── Step 7: telegram_bot ────────────────────────────────────────────────────
Log "STEP 7: telegram_bot.py"
$tgToken = $env:TELEGRAM_BOT_TOKEN
if (-not $tgToken) {
    WARN "TELEGRAM_BOT_TOKEN не установлен — telegram_bot пропущен"
    WARN "Установи: \$env:TELEGRAM_BOT_TOKEN = 'токен' и перезапусти"
} else {
    $tgSrc  = Join-Path $Fixes "telegram_bot.py"
    $tgDest = Join-Path $AO    "fixes\telegram_bot.py"
    if (-not $DryRun) {
        Copy-Item $tgSrc $tgDest -Force
        $tgRunning = pm2 list 2>$null | Select-String "tg-agent-bot"
        if (-not $tgRunning) {
            pm2 start $tgDest --name "tg-agent-bot" --interpreter python
        } else {
            pm2 restart "tg-agent-bot"
        }
        OK "tg-agent-bot запущен"
    } else { WARN "DryRun — would deploy telegram_bot" }
}

# ─── Step 8: git-backup ──────────────────────────────────────────────────────
Log "STEP 8: git-backup"
if (-not $DryRun) {
    $gitBak = pm2 list 2>$null | Select-String "git-backup"
    if ($gitBak -match "stopped|errored") {
        pm2 restart git-backup
        OK "git-backup перезапущен"
    } elseif ($gitBak) {
        OK "git-backup уже online"
    } else {
        WARN "git-backup не найден в PM2 — проверь вручную"
    }
}

# ─── Step 9: openrouter_sync dry-run ─────────────────────────────────────────
Log "STEP 9: проверка OpenRouter моделей"
if (-not $DryRun) {
    python (Join-Path $Fixes "openrouter_sync.py") --dry-run 2>$null
}

# ─── Step 10: pm2 save ───────────────────────────────────────────────────────
Log "STEP 10: pm2 save"
if (-not $DryRun) { pm2 save; OK "PM2 конфиг сохранён" }

# ─── Step 11: Health check ───────────────────────────────────────────────────
Log "STEP 11: Health check :9999"
Start-Sleep -Seconds 4
if (-not $DryRun) {
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:9999/" -TimeoutSec 10
        OK "brain_server_v2 ответил: $($resp.count) роутов"
        $resp2 = Invoke-RestMethod -Uri "http://localhost:9999/status" -TimeoutSec 10
        $alive = $resp2.checks.free_pool_alive
        OK "Free pool: $alive моделей живых"
    } catch {
        WARN "Health check не ответил: $_"
        WARN "Проверь: pm2 logs brain-мост"
    }
}

Log ""
Log "════════════════════════════════════════════"
Log "Deploy$(if ($DryRun) { ' [DRY RUN — ничего не изменено]' } else { ' COMPLETED ✅' })"
Log ""
if (-not $DryRun) {
    Log "Тест: curl http://localhost:9999/"
    Log "Тест POST: curl -X POST http://localhost:9999/free_brain -d '{`"prompt`":`"hello`"}'"
    Log "Логи: pm2 logs brain-мост"
    Log "OpenRouter синк: python fixes/openrouter_sync.py --update-server"
}
