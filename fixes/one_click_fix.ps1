# one_click_fix.ps1 — ОДИН СКРИПТ ВОССТАНАВЛИВАЕТ ВСЁ
# Запуск из корня репо: .\fixes\one_click_fix.ps1
# Делает всё: Claude Code, brain_server_v2, PM2, MCP, health monitor, startup

param(
    [switch]$DryRun,
    [switch]$SkipDeploy,
    [switch]$SkipStartup
)

$ErrorActionPreference = "SilentlyContinue"
$Root  = Split-Path -Parent $PSScriptRoot
$Fixes = $PSScriptRoot
$StartTime = Get-Date

function HEADER($t) { Write-Host "`n$('═' * 60)" -ForegroundColor Cyan; Write-Host "  $t" -ForegroundColor Cyan; Write-Host $('═' * 60) -ForegroundColor Cyan }
function OK($t)     { Write-Host "  [OK]  $t" -ForegroundColor Green }
function WARN($t)   { Write-Host "  [!!]  $t" -ForegroundColor Yellow }
function ERR($t)    { Write-Host "  [ERR] $t" -ForegroundColor Red }
function LOG($t)    { Write-Host "  [ ]   $t" -ForegroundColor Gray }

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         AGENT OFFICE — ONE CLICK FIX                    ║" -ForegroundColor Cyan
Write-Host "║   Восстановление всей системы одной командой             ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
if ($DryRun) { Write-Host "  [DRY RUN MODE — ничего не меняется]" -ForegroundColor Yellow }
Write-Host ""

$steps_ok   = @()
$steps_warn = @()
$steps_err  = @()

# ─── БЛОК 1: GIT PULL ─────────────────────────────────────────────────────────
HEADER "БЛОК 1: Git Pull"
$branch = git branch --show-current 2>$null
LOG "Текущая ветка: $branch"
if (-not $DryRun) {
    $pullResult = git pull origin $branch 2>&1
    if ($LASTEXITCODE -eq 0) { OK "git pull OK — $($pullResult[-1])"; $steps_ok += "git pull" }
    else { WARN "git pull: $pullResult"; $steps_warn += "git pull (не критично)" }
} else { WARN "DryRun — пропускаем git pull" }

# ─── БЛОК 2: CLAUDE CODE ───────────────────────────────────────────────────────
HEADER "БЛОК 2: Починить Claude Code + CCR порт"
LOG "Исправляем порт claude-code-router (ccr) ..."
if (-not $DryRun) {
    & "$Fixes\fix_ccr_port.ps1"
    $steps_ok += "CCR port fix"
} else { WARN "DryRun — пропускаем fix_ccr_port" }

LOG "Запускаем fix_claude_settings.ps1 ..."
if (-not $DryRun) {
    & "$Fixes\fix_claude_settings.ps1"
    $steps_ok += "Claude Code settings"
} else { WARN "DryRun — пропускаем fix_claude_settings" }

LOG "Очищаем ANTHROPIC_BASE_URL если она ведёт в OpenRouter ..."
if (-not $DryRun) {
    $baseUrl = $env:ANTHROPIC_BASE_URL
    if ($baseUrl -match "openrouter") {
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $null, "User")
        $env:ANTHROPIC_BASE_URL = $null
        OK "ANTHROPIC_BASE_URL убрана (была OpenRouter URL)"
    } elseif ($baseUrl) {
        WARN "ANTHROPIC_BASE_URL = $baseUrl (не менялась — не openrouter)"
    } else {
        OK "ANTHROPIC_BASE_URL не задана (норма для прямого Anthropic API)"
    }
}

# ─── БЛОК 3: ДЕПЛОЙ BRAIN SERVER ──────────────────────────────────────────────
if (-not $SkipDeploy) {
    HEADER "БЛОК 3: Деплой brain_server_v2 + сервисы"
    if (-not $DryRun) {
        & "$Fixes\deploy.ps1"
        if ($LASTEXITCODE -eq 0) { $steps_ok += "deploy.ps1"; OK "Деплой завершён" }
        else { $steps_warn += "deploy.ps1 (смотри вывод выше)"; WARN "Деплой завершён с предупреждениями" }
    } else { WARN "DryRun — пропускаем deploy.ps1" }
} else {
    LOG "БЛОК 3: Пропущен (--SkipDeploy)"
}

# ─── БЛОК 4: STARTUP ЗАДАЧИ ────────────────────────────────────────────────────
if (-not $SkipStartup) {
    HEADER "БЛОК 4: Задачи автозапуска (Task Scheduler)"
    if (-not $DryRun) {
        & "$Fixes\setup_windows_startup.ps1"
        $steps_ok += "startup tasks"
        OK "Задачи планировщика настроены"
    } else { WARN "DryRun — пропускаем setup_windows_startup" }
} else {
    LOG "БЛОК 4: Пропущен (--SkipStartup)"
}

# ─── БЛОК 5: DOCKER ────────────────────────────────────────────────────────────
HEADER "БЛОК 5: Docker контейнеры"
$dockerAvail = docker ps 2>$null
if ($LASTEXITCODE -eq 0) {
    $required = @("postiz", "postgres", "redis", "sasha-postgres")
    $running  = docker ps --format "{{.Names}}" 2>$null
    foreach ($c in $required) {
        if ($running -contains $c) {
            OK "$c — уже запущен"
        } else {
            if (-not $DryRun) {
                docker start $c 2>$null
                if ($LASTEXITCODE -eq 0) { OK "$c — запущен"; $steps_ok += "docker $c" }
                else { WARN "$c — не удалось запустить (возможно не создан)"; $steps_warn += "docker $c" }
            } else { WARN "DryRun — would docker start $c" }
        }
    }
    # Убедиться что temporal и n8n выключены
    $dangerous = @("temporal", "n8n")
    foreach ($c in $dangerous) {
        $found = $running | Where-Object { $_ -match $c }
        if ($found) {
            WARN "$c ЗАПУЩЕН — останавливаем (CPU/перегрев!)"
            if (-not $DryRun) { docker stop $found 2>$null; OK "$found остановлен" }
        } else {
            OK "$c выключен (норма)"
        }
    }
    $steps_ok += "docker"
} else {
    WARN "Docker недоступен или не запущен"
    $steps_warn += "docker"
}

# ─── БЛОК 6: PM2 RESURRECT ────────────────────────────────────────────────────
HEADER "БЛОК 6: PM2 — проверка и воскрешение"
if (-not $DryRun) {
    & "$Fixes\pm2_resurrect.ps1"
    $steps_ok += "pm2 resurrect"
}

# ─── БЛОК 7: ПРОВЕРКА API КЛЮЧЕЙ ──────────────────────────────────────────────
HEADER "БЛОК 7: Проверка ключей"
python "$Fixes\env_check.py" --load-env 2>$null
if ($LASTEXITCODE -eq 0) { $steps_ok += "api keys" }
else { $steps_warn += "api keys (есть отсутствующие)" }

# ─── БЛОК 8: ФИНАЛЬНЫЙ HEALTH CHECK ───────────────────────────────────────────
HEADER "БЛОК 8: Финальный Health Check"
Start-Sleep -Seconds 5
$brainOk = $false
try {
    $br = Invoke-RestMethod -Uri "http://localhost:9999/" -TimeoutSec 8
    OK "brain-мост :9999 — OK ($($br.count) роутов, $($br.free_pool_alive) моделей живых)"
    $brainOk = $true
    $steps_ok += "brain :9999"
} catch {
    ERR "brain-мост :9999 — недоступен!"
    ERR "  Проверь: pm2 logs brain-мост"
    $steps_err += "brain :9999"
}

$qdrantOk = $false
try {
    Invoke-RestMethod -Uri "http://localhost:6333/collections" -TimeoutSec 5 | Out-Null
    OK "Qdrant :6333 — OK"; $qdrantOk = $true; $steps_ok += "qdrant :6333"
} catch { WARN "Qdrant :6333 — недоступен (docker?)" ; $steps_warn += "qdrant :6333" }

try {
    Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 | Out-Null
    OK "Ollama :11434 — OK"; $steps_ok += "ollama :11434"
} catch { WARN "Ollama :11434 — недоступен (не запущен?)" ; $steps_warn += "ollama :11434" }

try {
    Invoke-RestMethod -Uri "http://localhost:8642/health" -TimeoutSec 5 | Out-Null
    OK "Hermes :8642 — OK"; $steps_ok += "hermes :8642"
} catch { WARN "Hermes :8642 — недоступен" ; $steps_warn += "hermes :8642" }

# Проверить CPU
$cpu = (Get-WmiObject Win32_Processor | Measure-Object LoadPercentage -Average).Average
if ($cpu -lt 70) { OK "CPU: $cpu% (в норме)"; $steps_ok += "cpu" }
else { ERR "CPU: $cpu% — ПРЕВЫШЕН ЛИМИТ 70%!"; $steps_err += "cpu > 70%" }

# ─── ФИНАЛЬНЫЙ ОТЧЁТ ──────────────────────────────────────────────────────────
$elapsed = [math]::Round(((Get-Date) - $StartTime).TotalSeconds, 1)

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                  ИТОГ ВОССТАНОВЛЕНИЯ                    ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  Время: ${elapsed}с" -ForegroundColor Gray
Write-Host "║" -ForegroundColor Cyan

if ($steps_ok.Count -gt 0) {
    Write-Host "║  [OK] ($($steps_ok.Count)):" -ForegroundColor Green
    $steps_ok | ForEach-Object { Write-Host "║    ✅ $_" -ForegroundColor Green }
}
if ($steps_warn.Count -gt 0) {
    Write-Host "║  [!!] ($($steps_warn.Count)):" -ForegroundColor Yellow
    $steps_warn | ForEach-Object { Write-Host "║    ⚠️  $_" -ForegroundColor Yellow }
}
if ($steps_err.Count -gt 0) {
    Write-Host "║  [ERR] ($($steps_err.Count)):" -ForegroundColor Red
    $steps_err | ForEach-Object { Write-Host "║    ❌ $_" -ForegroundColor Red }
}

Write-Host "╠══════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
if ($steps_err.Count -eq 0) {
    Write-Host "║  ✅ СИСТЕМА ВОССТАНОВЛЕНА                               ║" -ForegroundColor Green
    Write-Host "║  Перезапусти Claude Code: claude                        ║" -ForegroundColor Green
} else {
    Write-Host "║  ⚠️  ЕСТЬ ПРОБЛЕМЫ — смотри [ERR] выше                  ║" -ForegroundColor Red
    Write-Host "║  pm2 logs brain-мост                                    ║" -ForegroundColor Red
}
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Детальный статус: .\fixes\full_status.ps1" -ForegroundColor Gray
Write-Host "  Telegram бот: нужен TELEGRAM_BOT_TOKEN в .env" -ForegroundColor Gray
Write-Host ""
