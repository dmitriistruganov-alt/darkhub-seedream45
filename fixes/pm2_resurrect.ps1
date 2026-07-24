# pm2_resurrect.ps1 — поднять все PM2 процессы Agent Office
# Запуск: .\fixes\pm2_resurrect.ps1
# Безопасно: только pm2 resurrect + проверка критических процессов

param([switch]$Force)

$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent $PSScriptRoot
# Resolve agent_office path (may be sibling of repo or inside it)
$AO_CANDIDATES = @(
    (Join-Path $env:USERPROFILE "agent_office"),
    (Join-Path $Root "agent_office"),
    (Join-Path (Split-Path -Parent $Root) "agent_office")
)
$AO = ($AO_CANDIDATES | Where-Object { Test-Path $_ } | Select-Object -First 1)

function OK($t)   { Write-Host "  ✅ $t" -ForegroundColor Green }
function WARN($t) { Write-Host "  ⚠️  $t" -ForegroundColor Yellow }
function ERR($t)  { Write-Host "  ❌ $t" -ForegroundColor Red }
function LOG($t)  { Write-Host "[pm2] $t" -ForegroundColor Cyan }

LOG "PM2 Resurrect — Agent Office"

# ─── Шаг 1: pm2 resurrect ────────────────────────────────────────────────────
LOG "Шаг 1: pm2 resurrect (восстановление сохранённого состояния)"
$resurrect = pm2 resurrect 2>&1
if ($LASTEXITCODE -eq 0) {
    OK "pm2 resurrect выполнен"
} else {
    WARN "pm2 resurrect вернул: $resurrect"
}
Start-Sleep -Seconds 3

# ─── Шаг 2: проверить критические процессы ────────────────────────────────────
LOG "Шаг 2: Проверка критических процессов"
$critical = @(
    @{name="brain-мост";     script="brain_server_v2.py"; dir="agent_office"; interp="python"},
    @{name="daily-monitor";  script="";                   dir="";             interp=""},
    @{name="free-llm-sync";  script="";                   dir="";             interp=""},
    @{name="git-backup";     script="";                   dir="";             interp=""}
)

$pm2List = pm2 jlist 2>$null | ConvertFrom-Json
foreach ($proc in $critical) {
    $found = $pm2List | Where-Object { $_.name -eq $proc.name }
    if (-not $found) {
        if ($proc.script -and $proc.name -eq "brain-мост") {
            WARN "$($proc.name) не найден в PM2"
            if ($Force) {
                $scriptPath = if ($AO) { Join-Path $AO "brain_server_v2.py" } else { "" }
                if (-not $scriptPath -or -not (Test-Path $scriptPath)) {
                    $scriptPath = Join-Path $Root "fixes\brain_server_v2.py"
                }
                if (Test-Path $scriptPath) {
                    Push-Location (Split-Path $scriptPath)
                    pm2 start $scriptPath --name "brain-мост" --interpreter python
                    Pop-Location
                    OK "brain-мост запущен принудительно"
                } else {
                    ERR "brain_server_v2.py не найден! Запусти .\fixes\deploy.ps1"
                }
            } else {
                WARN "  Запусти: .\fixes\deploy.ps1  (или -Force для авто-старта)"
            }
        } else {
            WARN "$($proc.name) — не в PM2 (нужно настроить вручную)"
        }
    } else {
        $st = $found.pm2_env.status
        if ($st -eq "online") {
            OK "$($proc.name) online"
        } elseif ($st -in @("stopped", "errored", "dead")) {
            WARN "$($proc.name) — $st, перезапускаем..."
            pm2 restart $proc.name
            Start-Sleep -Seconds 2
            $refound = pm2 jlist 2>$null | ConvertFrom-Json | Where-Object { $_.name -eq $proc.name }
            if ($refound.pm2_env.status -eq "online") { OK "$($proc.name) перезапущен" }
            else { ERR "$($proc.name) не удалось поднять — проверь: pm2 logs $($proc.name)" }
        } else {
            WARN "$($proc.name) — статус: $st"
        }
    }
}

# ─── Шаг 3: health monitor ────────────────────────────────────────────────────
LOG "Шаг 3: Проверка health-monitor"
$hmFound = $pm2List | Where-Object { $_.name -eq "health-monitor" }
if (-not $hmFound) {
    $hmPath = if ($AO) { Join-Path $AO "fixes\health_monitor.py" } else { "" }
    if (-not $hmPath -or -not (Test-Path $hmPath)) { $hmPath = Join-Path $Root "fixes\health_monitor.py" }
    if (Test-Path $hmPath) {
        pm2 start $hmPath --name "health-monitor" --interpreter python
        OK "health-monitor запущен"
    } else {
        WARN "health_monitor.py не найден — запусти deploy.ps1 сначала"
    }
} else {
    $hmSt = $hmFound.pm2_env.status
    if ($hmSt -ne "online") {
        pm2 restart "health-monitor"
        OK "health-monitor перезапущен"
    } else {
        OK "health-monitor online"
    }
}

# ─── Шаг 4: pm2 save ──────────────────────────────────────────────────────────
LOG "Шаг 4: pm2 save"
pm2 save
OK "Конфиг PM2 сохранён"

# ─── Шаг 5: итог ──────────────────────────────────────────────────────────────
LOG ""
$finalList = pm2 jlist 2>$null | ConvertFrom-Json
$onlineCount = ($finalList | Where-Object { $_.pm2_env.status -eq "online" }).Count
$totalCount  = $finalList.Count
LOG "ИТОГ: $onlineCount / $totalCount процессов online"
LOG ""
LOG "Мониторинг: pm2 monit"
LOG "Логи:       pm2 logs --lines 50"
LOG "Статус:     .\fixes\full_status.ps1"
