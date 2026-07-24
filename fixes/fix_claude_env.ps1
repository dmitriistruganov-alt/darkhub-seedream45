# fix_claude_env.ps1 — убрать ANTHROPIC_BASE_URL и сбросить Claude Code к стандартному API
# Запуск: .\fixes\fix_claude_env.ps1
# Причина проблемы: ANTHROPIC_BASE_URL указывает на OpenRouter/кастомный роутер с qwen3

$ErrorActionPreference = "SilentlyContinue"

function OK($t)   { Write-Host "  OK  $t" -ForegroundColor Green }
function WARN($t) { Write-Host "  WARN $t" -ForegroundColor Yellow }
function INFO($t) { Write-Host "  ... $t" -ForegroundColor Gray }

Write-Host ""
Write-Host "=== FIX CLAUDE BASE URL ===" -ForegroundColor Cyan
Write-Host ""

# 1. Проверить текущее значение
$current = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_BASE_URL", "User")
$currentMachine = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_BASE_URL", "Machine")
$currentProcess = $env:ANTHROPIC_BASE_URL

Write-Host "Текущий ANTHROPIC_BASE_URL:" -ForegroundColor Yellow
Write-Host "  User scope:    $(if ($current) { $current } else { '(не задан)' })"
Write-Host "  Machine scope: $(if ($currentMachine) { $currentMachine } else { '(не задан)' })"
Write-Host "  Process:       $(if ($currentProcess) { $currentProcess } else { '(не задан)' })"

# 2. Убрать из всех уровней
if ($current) {
    [System.Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $null, "User")
    OK "Убран из User scope"
}
if ($currentMachine) {
    try {
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $null, "Machine")
        OK "Убран из Machine scope"
    } catch {
        WARN "Machine scope требует прав администратора — запусти от Admin"
    }
}
$env:ANTHROPIC_BASE_URL = $null
OK "Убран из текущего процесса"

# 3. Проверить что ANTHROPIC_API_KEY рабочий
Write-Host ""
Write-Host "Проверка ANTHROPIC_API_KEY..." -ForegroundColor Cyan
$apiKey = $env:ANTHROPIC_API_KEY
if (-not $apiKey) {
    $apiKey = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")
}
if ($apiKey) {
    if ($apiKey.StartsWith("sk-ant-")) {
        OK "ANTHROPIC_API_KEY выглядит корректно (sk-ant-...)"
    } elseif ($apiKey.StartsWith("sk-or-")) {
        WARN "ANTHROPIC_API_KEY начинается с sk-or- (это OpenRouter ключ, не Anthropic!)"
        WARN "Нужен настоящий Anthropic ключ: https://console.anthropic.com/settings/keys"
    } else {
        WARN "ANTHROPIC_API_KEY: неизвестный формат — $($apiKey.Substring(0,10))..."
    }
} else {
    WARN "ANTHROPIC_API_KEY не найден — Claude Code требует его для работы"
    WARN "Установи: `$env:ANTHROPIC_API_KEY = 'sk-ant-...'"
}

# 4. Сбросить settings.json до минимума
Write-Host ""
Write-Host "Сброс settings.json..." -ForegroundColor Cyan
$settingsFile = "$env:USERPROFILE\.claude\settings.json"
if (Test-Path $settingsFile) {
    $content = Get-Content $settingsFile -Raw
    # Backup
    Copy-Item $settingsFile "$settingsFile.bak_$(Get-Date -Format 'yyyyMMddHHmmss')" -Force
    # Убрать model, apiUrl, customApiKey, baseUrl из JSON
    try {
        $j = $content | ConvertFrom-Json
        $keys_to_clean = @("model","apiUrl","customApiKey","baseUrl","apiBase","openaiBaseUrl",
                           "anthropicBaseUrl","customBaseUrl","provider","fallbackModels")
        foreach ($k in $keys_to_clean) {
            if ($j.PSObject.Properties[$k]) {
                $val = $j.$k
                if ($val -match "qwen|openrouter|9999|localhost") {
                    $j.PSObject.Properties.Remove($k)
                    OK "Удалено из settings.json: $k = $($val -replace '(?<=.{20}).*', '...')"
                }
            }
        }
        $j | ConvertTo-Json -Depth 20 | Set-Content $settingsFile -Encoding UTF8
        OK "settings.json очищен"
    } catch {
        WARN "JSON сломан — перезаписываем минимальным конфигом"
        '{"$schema":"https://json.schemastore.org/claude-code-settings.json"}' | Set-Content $settingsFile -Encoding UTF8
        OK "settings.json сброшен до минимума"
    }
} else {
    INFO "settings.json не найден — Claude Code создаст его сам при первом запуске"
}

# 5. Проверить .env файлы на ANTHROPIC_BASE_URL
Write-Host ""
Write-Host "Проверка .env файлов..." -ForegroundColor Cyan
$env_files = @(
    "$env:USERPROFILE\agent_office\.env",
    "$env:USERPROFILE\.env",
    ".\..\.env",
    ".\.env"
)
foreach ($ef in $env_files) {
    if (Test-Path $ef) {
        $lines = Get-Content $ef
        $has_base_url = $lines | Where-Object { $_ -match "^ANTHROPIC_BASE_URL=" }
        if ($has_base_url) {
            WARN ".env файл содержит ANTHROPIC_BASE_URL: $ef"
            WARN "  → $has_base_url"
            WARN "  Закомментируй строку: # ANTHROPIC_BASE_URL=..."
            # Автоматически закомментировать
            $fixed = $lines | ForEach-Object {
                if ($_ -match "^ANTHROPIC_BASE_URL=") { "# $_ (закомментировано fix_claude_env.ps1)" }
                else { $_ }
            }
            Copy-Item $ef "$ef.bak" -Force
            $fixed | Set-Content $ef -Encoding UTF8
            OK "  Закомментировано в $ef"
        } else {
            OK "$ef — ANTHROPIC_BASE_URL не найден"
        }
    }
}

# 6. Финал
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "ГОТОВО. Перезапусти Claude Code." -ForegroundColor Green
Write-Host ""
Write-Host "Если всё ещё не работает — запусти в PowerShell:" -ForegroundColor Yellow
Write-Host '  claude --version' -ForegroundColor White
Write-Host '  claude  ' -ForegroundColor White
Write-Host ""
Write-Host "Если ошибка типа 'API key invalid':" -ForegroundColor Yellow
Write-Host '  claude config set apiKey sk-ant-ВАШ_КЛЮЧ' -ForegroundColor White
