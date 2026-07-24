# setup_windows_startup.ps1 — регистрация PM2 автостарта при входе в Windows
# Запуск с правами администратора: .\fixes\setup_windows_startup.ps1
#
# Делает:
#   1. pm2 startup (если поддерживается — через NSSM или systemd on WSL)
#   2. Регистрирует Task Scheduler задачу pm2_resurrect при логине
#   3. Регистрирует ежедневную задачу для openrouter_sync (обновление моделей)
#   4. Добавляет MCP brain в Claude Desktop config (если найден)

param(
    [switch]$Uninstall,
    [switch]$DryRun
)

$ErrorActionPreference = "SilentlyContinue"
$Root  = Split-Path -Parent $PSScriptRoot
$Fixes = $PSScriptRoot

function LOG($t)  { Write-Host "[setup] $t" -ForegroundColor Cyan }
function OK($t)   { Write-Host "  ✅ $t" -ForegroundColor Green }
function WARN($t) { Write-Host "  ⚠️  $t" -ForegroundColor Yellow }
function ERR($t)  { Write-Host "  ❌ $t" -ForegroundColor Red }

# ─── Detect agent_office ─────────────────────────────────────────────────────
$AO = @(
    (Join-Path $env:USERPROFILE "agent_office"),
    (Join-Path $Root "agent_office")
) | Where-Object { Test-Path $_ } | Select-Object -First 1

LOG "Root:          $Root"
LOG "agent_office:  $(if ($AO) { $AO } else { 'NOT FOUND' })"
LOG "DryRun:        $DryRun"
LOG ""

# ─── Uninstall mode ──────────────────────────────────────────────────────────
if ($Uninstall) {
    LOG "Удаление задач планировщика..."
    foreach ($task in @("AgentOffice-PM2-Resurrect", "AgentOffice-OpenRouter-Sync", "AgentOffice-Health-Check")) {
        Unregister-ScheduledTask -TaskName $task -Confirm:$false 2>$null
        if ($LASTEXITCODE -eq 0) { OK "Удалена: $task" }
    }
    LOG "Готово. PM2 процессы не тронуты."
    exit 0
}

# ─── Task 1: PM2 Resurrect при входе ─────────────────────────────────────────
LOG "TASK 1: PM2 Resurrect при входе в систему"
$resurrectScript = Join-Path $Fixes "pm2_resurrect.ps1"
if (-not (Test-Path $resurrectScript)) {
    WARN "pm2_resurrect.ps1 не найден: $resurrectScript"
} else {
    $action  = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$resurrectScript`""
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
                    -StartWhenAvailable -DontStopIfGoingOnBatteries

    if ($DryRun) {
        WARN "DryRun — would register: AgentOffice-PM2-Resurrect"
    } else {
        Register-ScheduledTask -TaskName "AgentOffice-PM2-Resurrect" `
            -Action $action -Trigger $trigger -Settings $settings `
            -Description "Agent Office: pm2 resurrect при входе" `
            -RunLevel Highest -Force 2>$null
        if ($LASTEXITCODE -eq 0) { OK "AgentOffice-PM2-Resurrect зарегистрирован" }
        else { WARN "Не удалось зарегистрировать — возможно нужны права администратора" }
    }
}

# ─── Task 2: Ежедневное обновление OpenRouter моделей ────────────────────────
LOG "TASK 2: OpenRouter Sync — ежедневно в 06:00"
$syncScript = Join-Path $Fixes "openrouter_sync.py"
if (-not (Test-Path $syncScript)) {
    WARN "openrouter_sync.py не найден: $syncScript"
} else {
    $syncAction  = New-ScheduledTaskAction -Execute "python" `
        -Argument "`"$syncScript`" --update-server"
    $syncTrigger = New-ScheduledTaskTrigger -Daily -At "06:00"
    $syncSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
                        -StartWhenAvailable

    if ($DryRun) {
        WARN "DryRun — would register: AgentOffice-OpenRouter-Sync"
    } else {
        Register-ScheduledTask -TaskName "AgentOffice-OpenRouter-Sync" `
            -Action $syncAction -Trigger $syncTrigger -Settings $syncSettings `
            -Description "Agent Office: обновление free model pool из OpenRouter" `
            -Force 2>$null
        if ($LASTEXITCODE -eq 0) { OK "AgentOffice-OpenRouter-Sync зарегистрирован (ежедневно 06:00)" }
        else { WARN "Не удалось зарегистрировать OpenRouter-Sync" }
    }
}

# ─── Task 3: Health check каждые 15 мин ──────────────────────────────────────
LOG "TASK 3: Health check (каждые 15 мин) — опционально"
$hmScript = if ($AO) { Join-Path $AO "fixes\health_monitor.py" } else { Join-Path $Fixes "health_monitor.py" }
if (-not (Test-Path $hmScript)) { $hmScript = Join-Path $Fixes "health_monitor.py" }
if (Test-Path $hmScript) {
    $hmAction = New-ScheduledTaskAction -Execute "python" `
        -Argument "`"$hmScript`" --once"
    $hmTrigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) `
                    -Once -At (Get-Date)
    $hmSettings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

    if ($DryRun) {
        WARN "DryRun — would register: AgentOffice-Health-Check"
    } else {
        Register-ScheduledTask -TaskName "AgentOffice-Health-Check" `
            -Action $hmAction -Trigger $hmTrigger -Settings $hmSettings `
            -Description "Agent Office: health check каждые 15 мин" `
            -Force 2>$null
        if ($LASTEXITCODE -eq 0) { OK "AgentOffice-Health-Check зарегистрирован (каждые 15 мин)" }
        else { WARN "Не удалось зарегистрировать Health-Check" }
    }
} else {
    WARN "health_monitor.py не найден, пропускаем"
}

# ─── MCP Config для Claude Desktop ───────────────────────────────────────────
LOG "MCP: brain → Claude Desktop"
$claudeConfig = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
$mcpScript    = Join-Path $Fixes "mcp_server.py"

if (-not (Test-Path $mcpScript)) {
    WARN "mcp_server.py не найден: $mcpScript"
} elseif (-not (Test-Path $claudeConfig)) {
    WARN "Claude Desktop config не найден: $claudeConfig"
    WARN "Добавь вручную в $claudeConfig:"
    Write-Host @"
{
  "mcpServers": {
    "brain": {
      "command": "python",
      "args": ["$($mcpScript.Replace('\', '\\'))"],
      "env": {"BRAIN_PORT": "9999"}
    }
  }
}
"@
} else {
    $configContent = Get-Content $claudeConfig -Raw | ConvertFrom-Json
    if ($null -eq $configContent.mcpServers) {
        $configContent | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value @{}
    }
    $brainEntry = @{
        command = "python"
        args    = @($mcpScript)
        env     = @{BRAIN_PORT = "9999"}
    }
    if (-not $configContent.mcpServers.brain) {
        if ($DryRun) {
            WARN "DryRun — would add brain MCP to claude_desktop_config.json"
        } else {
            $configContent.mcpServers | Add-Member -MemberType NoteProperty -Name "brain" -Value $brainEntry -Force
            $configContent | ConvertTo-Json -Depth 10 | Set-Content $claudeConfig -Encoding UTF8
            OK "brain MCP добавлен в Claude Desktop — перезапусти Claude Desktop"
        }
    } else {
        OK "brain MCP уже настроен в Claude Desktop"
    }
}

# ─── pm2 startup (native) ────────────────────────────────────────────────────
LOG "pm2 startup (нативный автозапуск через pm2)"
if (-not $DryRun) {
    $startupResult = pm2 startup 2>&1
    if ($startupResult -match "sudo|command") {
        WARN "pm2 startup требует дополнительных шагов. Выполни команду выше вручную."
    } else {
        OK "pm2 startup выполнен"
    }
}

# ─── Итог ─────────────────────────────────────────────────────────────────────
LOG ""
LOG "════════════════════════════════════════════"
LOG "Setup$(if ($DryRun) { ' [DRY RUN]' } else { ' COMPLETED ✅' })"
LOG ""
LOG "Зарегистрированные задачи:"
LOG "  - AgentOffice-PM2-Resurrect   (при входе)"
LOG "  - AgentOffice-OpenRouter-Sync (ежедневно 06:00)"
LOG "  - AgentOffice-Health-Check    (каждые 15 мин)"
LOG ""
LOG "Проверить: Get-ScheduledTask | Where-Object { \$_.TaskName -match 'AgentOffice' }"
LOG "Удалить:   .\fixes\setup_windows_startup.ps1 -Uninstall"
