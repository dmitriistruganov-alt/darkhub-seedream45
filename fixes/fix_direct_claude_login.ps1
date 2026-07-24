# fix_direct_claude_login.ps1
# ПРИЧИНА: settings.json содержит apiKeyHelper → возвращает sk-or-... (OpenRouter)
#          Этот ключ перекрывает claude.ai сессию → "connectors disabled"
# РЕШЕНИЕ: убрать apiKeyHelper + ANTHROPIC_BASE_URL → Claude Code работает через браузерный логин
# Запуск: .\fixes\fix_direct_claude_login.ps1

$ErrorActionPreference = "SilentlyContinue"
$S = "$env:USERPROFILE\.claude\settings.json"

function OK($t)  { Write-Host "  [OK]  $t" -ForegroundColor Green }
function ERR($t) { Write-Host "  [ERR] $t" -ForegroundColor Red }
function INF($t) { Write-Host "  [..]  $t" -ForegroundColor Gray }
function SEC($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }

SEC "ДИАГНОСТИКА"
if (-not (Test-Path $S)) { ERR "settings.json не найден"; exit 1 }

$raw  = Get-Content $S -Raw
$json = $raw | ConvertFrom-Json

$hasApiKeyHelper = ($null -ne $json.apiKeyHelper) -or ($raw -match "apiKeyHelper")
$hasBaseUrl      = ($null -ne $json.env) -and ($null -ne $json.env.ANTHROPIC_BASE_URL)
$hasApiKey       = ($null -ne $json.env) -and ($null -ne $json.env.ANTHROPIC_API_KEY)
$hasDiscovery    = ($null -ne $json.env) -and ($null -ne $json.env.CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY)

INF "apiKeyHelper:             $(if ($hasApiKeyHelper) { 'ЕСТЬ (перекрывает claude.ai)' } else { 'нет' })"
INF "env.ANTHROPIC_BASE_URL:   $(if ($hasBaseUrl) { $json.env.ANTHROPIC_BASE_URL } else { 'нет' })"
INF "env.ANTHROPIC_API_KEY:    $(if ($hasApiKey) { 'ЕСТЬ (маскируется)' } else { 'нет' })"
INF "GATEWAY_MODEL_DISCOVERY:  $(if ($hasDiscovery) { 'ЕСТЬ (баг root-cause)' } else { 'нет' })"
INF "model:                    $(if ($json.model) { $json.model } else { 'нет' })"

SEC "ИСПРАВЛЕНИЕ"
$backup = "$S.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $S $backup -Force
INF "Backup: $backup"

# Убрать apiKeyHelper — главная причина подмены ключа
if ($json.PSObject.Properties["apiKeyHelper"]) {
    $json.PSObject.Properties.Remove("apiKeyHelper")
    OK "apiKeyHelper удалён (больше не подставляет sk-or-...)"
}

# Убрать ANTHROPIC_BASE_URL из env — больше не перенаправлять на CCR
if ($json.env -and $json.env.PSObject.Properties["ANTHROPIC_BASE_URL"]) {
    $json.env.PSObject.Properties.Remove("ANTHROPIC_BASE_URL")
    OK "env.ANTHROPIC_BASE_URL удалён (прямое подключение к Anthropic)"
}

# Убрать ANTHROPIC_API_KEY из env если он там есть (OpenRouter ключ)
if ($json.env -and $json.env.PSObject.Properties["ANTHROPIC_API_KEY"]) {
    $orKey = $json.env.ANTHROPIC_API_KEY
    if ($orKey -and ($orKey.StartsWith("sk-or-") -or $orKey.StartsWith("sk-or-v1"))) {
        $json.env.PSObject.Properties.Remove("ANTHROPIC_API_KEY")
        OK "env.ANTHROPIC_API_KEY (OpenRouter sk-or-...) удалён"
    } else {
        INF "env.ANTHROPIC_API_KEY оставлен (не OpenRouter формат)"
    }
}

# Убрать CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY — root cause 400 ошибок
if ($json.env -and $json.env.PSObject.Properties["CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY"]) {
    $json.env.PSObject.Properties.Remove("CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY")
    OK "CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY удалён (вызывал 400 у всех провайдеров)"
}

# Убрать системные env переменные
$sysBase = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_BASE_URL", "User")
if ($sysBase) {
    [System.Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $null, "User")
    OK "Системная ANTHROPIC_BASE_URL (User) очищена: $sysBase"
}
$env:ANTHROPIC_BASE_URL = $null

# Убрать системный ANTHROPIC_API_KEY если это OR ключ
$sysKey = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")
if ($sysKey -and $sysKey.StartsWith("sk-or-")) {
    [System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $null, "User")
    OK "Системный ANTHROPIC_API_KEY (OpenRouter) очищен из User scope"
}

# Установить правильную модель
if (-not $json.model -or $json.model -match "qwen|openrouter|llama|nemotron|gemma") {
    $json.model = "claude-sonnet-5"
    OK "model → claude-sonnet-5"
}

# Сохранить
$json | ConvertTo-Json -Depth 20 | Set-Content $S -Encoding UTF8
OK "settings.json сохранён"

SEC "ИТОГОВЫЙ settings.json (ключевые поля)"
$final = Get-Content $S -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
Write-Host "  model:         $($final.model)"
Write-Host "  apiKeyHelper:  $(if ($final.PSObject.Properties['apiKeyHelper']) { $final.apiKeyHelper } else { '(удалён)' })"
if ($final.env) {
    Write-Host "  env.BASE_URL:  $(if ($final.env.PSObject.Properties['ANTHROPIC_BASE_URL']) { $final.env.ANTHROPIC_BASE_URL } else { '(удалён)' })"
    Write-Host "  env.API_KEY:   $(if ($final.env.PSObject.Properties['ANTHROPIC_API_KEY']) { 'есть' } else { '(удалён)' })"
    Write-Host "  env.DISCOVERY: $(if ($final.env.PSObject.Properties['CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY']) { 'есть' } else { '(удалён)' })"
}

SEC "ПРОВЕРКА АВТОРИЗАЦИИ"
Write-Host ""
Write-Host "  Запускай:" -ForegroundColor Green
Write-Host "    claude auth status" -ForegroundColor White
Write-Host ""
Write-Host "  Если 'not logged in' — войди через браузер:" -ForegroundColor Yellow
Write-Host "    claude" -ForegroundColor White
Write-Host "    # Выбери 'Login with Claude.ai' → откроется браузер" -ForegroundColor Gray
Write-Host ""
Write-Host "  После входа claude.ai connectors включатся автоматически." -ForegroundColor Green
Write-Host ""
