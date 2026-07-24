# fix_ccr_port.ps1 — Исправить порт claude-code-router
# Проблема: ccr перезапустился на 3458, а settings.json ждёт на 3456
# Запуск: .\fixes\fix_ccr_port.ps1

$ErrorActionPreference = "SilentlyContinue"

function OK($t)   { Write-Host "  [OK]  $t" -ForegroundColor Green }
function WARN($t) { Write-Host "  [!!]  $t" -ForegroundColor Yellow }
function ERR($t)  { Write-Host "  [ERR] $t" -ForegroundColor Red }
function INFO($t) { Write-Host "  [ ]   $t" -ForegroundColor Gray }
function SEC($t)  { Write-Host "`n=== $t ===" -ForegroundColor Cyan }

$CCR_CONFIG = "$env:USERPROFILE\.claude-code-router\config.json"
$SETTINGS   = "$env:USERPROFILE\.claude\settings.json"

SEC "ДИАГНОСТИКА ПОРТОВ"

# Прочитать ожидаемый порт из config.json
$expectedPort = 3456
if (Test-Path $CCR_CONFIG) {
    try {
        $cfg = Get-Content $CCR_CONFIG -Raw | ConvertFrom-Json
        if ($cfg.PORT) { $expectedPort = [int]$cfg.PORT }
        OK "config.json PORT = $expectedPort"
    } catch {
        WARN "Не удалось прочитать config.json — используем порт $expectedPort"
    }
} else {
    WARN "config.json не найден: $CCR_CONFIG"
}

# Найти что реально слушает
$ports3456 = netstat -ano | Select-String ":3456 " | Where-Object { $_ -match "LISTENING" }
$ports3458 = netstat -ano | Select-String ":3458 " | Where-Object { $_ -match "LISTENING" }
$portsAny  = netstat -ano | Select-String ":(345[0-9]) " | Where-Object { $_ -match "LISTENING" }

if ($ports3456) {
    OK "Порт 3456 слушает: $($ports3456 -join ' | ')"
} else {
    WARN "Порт 3456 НЕ слушает"
}
if ($ports3458) {
    WARN "Порт 3458 слушает: $($ports3458 -join ' | ')"
}

# Прочитать что в settings.json
$settingsPort = 3456
if (Test-Path $SETTINGS) {
    $sContent = Get-Content $SETTINGS -Raw
    if ($sContent -match '"ANTHROPIC_BASE_URL"\s*:\s*"http://127\.0\.0\.1:(\d+)"') {
        $settingsPort = [int]$Matches[1]
        INFO "settings.json ANTHROPIC_BASE_URL порт = $settingsPort"
    }
}

SEC "ИСПРАВЛЕНИЕ"

# Шаг 1: Остановить ccr
INFO "Останавливаем ccr..."
ccr stop 2>$null
Start-Sleep -Seconds 2

# Шаг 2: Убить все процессы на 3456, 3457, 3458 (чистый старт)
foreach ($port in @(3456, 3457, 3458)) {
    $lines = netstat -ano | Select-String ":$port " | Where-Object { $_ -match "LISTENING" }
    foreach ($line in $lines) {
        if ($line -match "\s+(\d+)\s*$") {
            $pid_ = $Matches[1]
            if ($pid_ -and $pid_ -ne "0") {
                $proc = Get-Process -Id $pid_ -ErrorAction SilentlyContinue
                $procName = if ($proc) { $proc.ProcessName } else { "?" }
                Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue
                OK "Убит процесс PID $pid_ ($procName) на порту :$port"
            }
        }
    }
}
Start-Sleep -Seconds 2

# Шаг 3: Запустить ccr свежо
INFO "Запускаем ccr start..."
ccr start 2>$null
Start-Sleep -Seconds 4

# Шаг 4: Проверить на каком порту запустился
$actualPort = $null
foreach ($port in @(3456, 3457, 3458, 3459, 3460)) {
    $check = netstat -ano | Select-String ":$port " | Where-Object { $_ -match "LISTENING" }
    if ($check) {
        $actualPort = $port
        OK "ccr запущен на порту :$port"
        break
    }
}

if (-not $actualPort) {
    ERR "ccr не запустился ни на одном порту! Пробуем pm2..."
    # Попытка через PM2
    $pm2List = pm2 jlist 2>$null | ConvertFrom-Json -ErrorAction SilentlyContinue
    $ccrProc = $pm2List | Where-Object { $_.name -match "ccr|claude-code-router" }
    if ($ccrProc) {
        pm2 restart $ccrProc.name 2>$null
        Start-Sleep -Seconds 4
        # Повторная проверка
        foreach ($port in @(3456, 3457, 3458)) {
            $check = netstat -ano | Select-String ":$port " | Where-Object { $_ -match "LISTENING" }
            if ($check) { $actualPort = $port; OK "ccr запущен на порту :$port (PM2)"; break }
        }
    }
}

if (-not $actualPort) {
    ERR "ccr не удалось запустить. Проверь вручную: ccr start"
    exit 1
}

# Шаг 5: Если порт не совпадает с settings.json — обновить settings.json
if ($actualPort -ne $settingsPort) {
    WARN "Рассинхрон: ccr на :$actualPort, settings.json ждёт :$settingsPort"
    WARN "Обновляем settings.json → порт :$actualPort"

    $backup = "$SETTINGS.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $SETTINGS $backup -Force
    INFO "Backup: $backup"

    $sJson = Get-Content $SETTINGS -Raw
    # Заменить порт в ANTHROPIC_BASE_URL
    $sJson = $sJson -replace "http://127\.0\.0\.1:$settingsPort", "http://127.0.0.1:$actualPort"
    $sJson | Set-Content $SETTINGS -Encoding UTF8
    OK "settings.json: порт $settingsPort → $actualPort"
} elseif ($actualPort -eq $settingsPort) {
    OK "Порт совпадает — settings.json не нужно менять (:$actualPort)"
}

# Шаг 6: Если actualPort != expectedPort — обновить config.json тоже
if ($actualPort -ne $expectedPort) {
    WARN "config.json PORT ($expectedPort) != реальный порт ($actualPort)"
    WARN "Это не должно происходить. Проверь config.json вручную:"
    WARN "  $CCR_CONFIG"
}

# Шаг 7: Тест router
SEC "ТЕСТ РОУТЕРА"
Start-Sleep -Seconds 2
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$actualPort" -TimeoutSec 5 -ErrorAction Stop
    OK "Router отвечает на :$actualPort — HTTP $($resp.StatusCode)"
} catch {
    # Пробуем POST /v1/models (claude-code-router endpoint)
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$actualPort/v1/models" -TimeoutSec 5 -ErrorAction Stop
        OK "Router /v1/models на :$actualPort — HTTP $($resp.StatusCode)"
    } catch {
        WARN "Router не отвечает на :$actualPort (может нормально для этого эндпоинта)"
    }
}

SEC "ИТОГ"
Write-Host ""
if ($actualPort) {
    OK "ccr работает на порту :$actualPort"
    if ($actualPort -ne $settingsPort) {
        OK "settings.json обновлён на порт :$actualPort"
    }
    Write-Host ""
    Write-Host "  Теперь запусти Claude Code:" -ForegroundColor Green
    Write-Host "    claude" -ForegroundColor White
    Write-Host ""
    Write-Host "  Если ошибка продолжается — проверь логи роутера:" -ForegroundColor Yellow
    Write-Host "    ccr logs" -ForegroundColor White
    Write-Host "    pm2 logs claude-code-router" -ForegroundColor White
} else {
    ERR "ccr не запущен. Ручная диагностика:"
    Write-Host "    ccr --version" -ForegroundColor White
    Write-Host "    ccr start" -ForegroundColor White
    Write-Host "    netstat -ano | findstr '345'" -ForegroundColor White
}
Write-Host ""
