# fix_claude_settings.ps1 — исправить Claude Code после qwen3:free стал платным
# Подтверждённая причина: provider=openrouter, model=qwen/qwen3-235b-a22b:free → 404
# Запуск: .\fixes\fix_claude_settings.ps1
#
# Логика выбора пути:
#   1. Если ANTHROPIC_API_KEY начинается с sk-ant- → переключить на прямой Anthropic API
#   2. Если только OpenRouter (sk-or-) → заменить qwen3 на рабочую бесплатную модель
#   3. Если ключей нет → только убрать qwen3 и сообщить о проблеме

$ErrorActionPreference = "SilentlyContinue"

function OK($t)   { Write-Host "  [OK]  $t" -ForegroundColor Green }
function WARN($t) { Write-Host "  [!!]  $t" -ForegroundColor Yellow }
function ERR($t)  { Write-Host "  [ERR] $t" -ForegroundColor Red }
function INFO($t) { Write-Host "  [..]  $t" -ForegroundColor Gray }
function SEC($t)  { Write-Host "`n=== $t ===" -ForegroundColor Cyan }

# Рабочие бесплатные модели OpenRouter (проверено 22.07.2026)
$FREE_MODELS_OR = @(
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "meta-llama/llama-4-maverick:free",
    "google/gemma-4-31b-it:free",
    "poolside/laguna-m.1:free"
)
$DEFAULT_FREE_MODEL = $FREE_MODELS_OR[0]   # nvidia nemotron ultra — самая мощная бесплатная

$SettingsFile = "$env:USERPROFILE\.claude\settings.json"

SEC "ДИАГНОСТИКА"

# ─── Прочитать настройки ───────────────────────────────────────────────────────
if (-not (Test-Path $SettingsFile)) {
    WARN "settings.json не найден — Claude Code создаст его сам"
    Write-Host "`nЕсли Claude Code не запускается без settings.json:"
    Write-Host "  claude config set model claude-sonnet-5"
    exit 0
}

$content = Get-Content $SettingsFile -Raw
try {
    $json = $content | ConvertFrom-Json
} catch {
    ERR "settings.json повреждён — перезаписываем минимальным конфигом"
    Copy-Item $SettingsFile "$SettingsFile.broken_$(Get-Date -Format 'yyyyMMdd_HHmmss')" -Force
    '{"$schema":"https://json.schemastore.org/claude-code-settings.json"}' | Set-Content $SettingsFile -Encoding UTF8
    OK "settings.json сброшен. Перезапусти Claude Code."
    exit 0
}

# Текущее состояние
$currentModel  = $json.model
$currentApiUrl = if ($json.apiUrl) { $json.apiUrl } elseif ($json.customApiUrl) { $json.customApiUrl } elseif ($json.baseUrl) { $json.baseUrl } else { $json.anthropicBaseUrl }
$hasQwen       = $content -match "qwen"
$hasOpenRouter = ($currentApiUrl -match "openrouter") -or ($env:ANTHROPIC_BASE_URL -match "openrouter")

INFO "Текущая модель:  $(if ($currentModel) { $currentModel } else { '(не задана)' })"
INFO "API URL:         $(if ($currentApiUrl) { $currentApiUrl } else { '(не задан)' })"
INFO "ANTHROPIC_BASE_URL: $(if ($env:ANTHROPIC_BASE_URL) { $env:ANTHROPIC_BASE_URL } else { '(не задана)' })"
INFO "Содержит qwen:   $hasQwen"
INFO "Провайдер:       $(if ($hasOpenRouter) { 'OpenRouter' } else { 'Anthropic Direct / Неизвестен' })"

# ─── Определить ключи ──────────────────────────────────────────────────────────
SEC "ОПРЕДЕЛЕНИЕ API КЛЮЧЕЙ"

$antKey = $env:ANTHROPIC_API_KEY
if (-not $antKey) {
    $antKey = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")
}
# Попробовать из .env файлов
if (-not $antKey) {
    $envFiles = @(
        (Join-Path $env:USERPROFILE "agent_office\.env"),
        (Join-Path $env:USERPROFILE ".env"),
        ".\.env"
    )
    foreach ($ef in $envFiles) {
        if (Test-Path $ef) {
            $line = Get-Content $ef | Where-Object { $_ -match "^ANTHROPIC_API_KEY=" } | Select-Object -First 1
            if ($line) { $antKey = $line -replace "^ANTHROPIC_API_KEY=", "" ; break }
        }
    }
}

$orKey = $env:OPENROUTER_API_KEY
if (-not $orKey) {
    $orKey = [System.Environment]::GetEnvironmentVariable("OPENROUTER_API_KEY", "User")
}

$isAnthropic  = $antKey -and $antKey.StartsWith("sk-ant-")
$isOpenRouter = $orKey  -and $orKey.StartsWith("sk-or-")
# Иногда OpenRouter ключ хранится в ANTHROPIC_API_KEY (для прозрачного проксирования)
$apiKeyIsOR   = $antKey -and $antKey.StartsWith("sk-or-")

if ($isAnthropic) {
    OK "ANTHROPIC_API_KEY: реальный Anthropic ключ (sk-ant-...)"
} elseif ($apiKeyIsOR) {
    WARN "ANTHROPIC_API_KEY: это OpenRouter ключ (sk-or-...)! Установлен для проксирования."
    $isOpenRouter = $true
} elseif ($antKey) {
    WARN "ANTHROPIC_API_KEY: неизвестный формат — $($antKey.Substring(0,[Math]::Min(10,$antKey.Length)))..."
} else {
    WARN "ANTHROPIC_API_KEY не найден"
}

if ($isOpenRouter) {
    OK "OPENROUTER_API_KEY: доступен (sk-or-...)"
}

# ─── ВЫБОР СТРАТЕГИИ ──────────────────────────────────────────────────────────
SEC "ИСПРАВЛЕНИЕ"

$backup = "$SettingsFile.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $SettingsFile $backup -Force
INFO "Backup: $backup"

$changed = $false

if ($isAnthropic -and -not $apiKeyIsOR) {
    # === ПУТЬ 1: Переключить на прямой Anthropic API ===
    Write-Host "`n  Стратегия: ANTHROPIC DIRECT API" -ForegroundColor Cyan
    Write-Host "  Причина: есть реальный Anthropic ключ → уходим от OpenRouter" -ForegroundColor Gray

    # Убрать поля OpenRouter
    $fieldsToRemove = @("apiUrl","customApiUrl","baseUrl","anthropicBaseUrl","customBaseUrl",
                        "openaiBaseUrl","provider","customApiKey","apiBase")
    foreach ($f in $fieldsToRemove) {
        if ($json.PSObject.Properties[$f]) {
            $val = $json.$f
            $json.PSObject.Properties.Remove($f)
            OK "  Убрано из settings.json: $f"
            $changed = $true
        }
    }

    # Убрать qwen из model
    if ($json.model -match "qwen" -or $json.model -match "openrouter") {
        $json.model = "claude-sonnet-5"
        OK "  model → claude-sonnet-5 (Anthropic Direct)"
        $changed = $true
    }

    # Убрать ANTHROPIC_BASE_URL из системы
    if ($env:ANTHROPIC_BASE_URL -match "openrouter") {
        [System.Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $null, "User")
        $env:ANTHROPIC_BASE_URL = $null
        OK "  ANTHROPIC_BASE_URL убрана из системы (была OpenRouter URL)"
    }

} elseif ($isOpenRouter -or $apiKeyIsOR -or $hasOpenRouter) {
    # === ПУТЬ 2: Остаться на OpenRouter, но сменить модель ===
    Write-Host "`n  Стратегия: OPENROUTER + РАБОЧАЯ БЕСПЛАТНАЯ МОДЕЛЬ" -ForegroundColor Cyan
    Write-Host "  Причина: OpenRouter ключ / URL. qwen3 стал платным → меняем модель." -ForegroundColor Gray
    Write-Host "  Новая модель: $DEFAULT_FREE_MODEL" -ForegroundColor White

    # Заменить модель
    if ($json.model -match "qwen" -or $json.model -match "qwen3") {
        $json.model = $DEFAULT_FREE_MODEL
        OK "  model: qwen/qwen3-235b-a22b:free → $DEFAULT_FREE_MODEL"
        $changed = $true
    } elseif (-not $json.model) {
        $json.model = $DEFAULT_FREE_MODEL
        OK "  model (не задана) → $DEFAULT_FREE_MODEL"
        $changed = $true
    }

    # Убрать qwen из fallback массивов
    foreach ($field in @("fallbackModels", "models", "fallbacks", "modelFallbacks",
                         "allowedModels", "enabledModels")) {
        if ($json.$field -is [array]) {
            $before = $json.$field.Count
            $json.$field = @($json.$field | Where-Object { $_ -notmatch "qwen" })
            if ($json.$field.Count -ne $before) {
                OK "  $field: удалено qwen ($before → $($json.$field.Count) элементов)"
                $changed = $true
            }
        }
    }

    # Если ANTHROPIC_BASE_URL не задана — добавить OpenRouter URL в settings
    if (-not $currentApiUrl -and ($env:ANTHROPIC_BASE_URL -match "openrouter")) {
        INFO "  ANTHROPIC_BASE_URL уже через OpenRouter — ок"
    }

} else {
    # === ПУТЬ 3: Нет известных ключей — просто убрать qwen ===
    Write-Host "`n  Стратегия: УБРАТЬ QWEN (ключи не найдены)" -ForegroundColor Yellow

    if ($json.model -match "qwen") {
        # Убрать model вообще — Claude Code будет использовать дефолт
        $json.PSObject.Properties.Remove("model")
        OK "  Поле model удалено (Claude Code выберет дефолт при запуске)"
        $changed = $true
    }

    WARN "  API ключи не найдены. Claude Code может потребовать ключ при запуске:"
    WARN "    claude config set apiKey sk-ant-ВАШ_КЛЮЧ"
    WARN "  Или установи переменную:"
    WARN "    `$env:ANTHROPIC_API_KEY = 'sk-ant-...'"
}

# ─── Убрать qwen из ЛЮБЫХ оставшихся мест (ядерная чистка) ──────────────────
$allProps = $json.PSObject.Properties.Name
foreach ($prop in $allProps) {
    $val = $json.$prop
    if ($val -is [string] -and $val -match "qwen") {
        WARN "  Найден qwen в '$prop': $($val.Substring(0,[Math]::Min(60,$val.Length)))..."
        # Если это model или url-поле — заменить
        if ($prop -in @("model","customModel","defaultModel","fallbackModel")) {
            $json.$prop = if ($isAnthropic) { "claude-sonnet-5" } else { $DEFAULT_FREE_MODEL }
            OK "  $prop → $($json.$prop)"
            $changed = $true
        }
    }
}

# ─── Сохранить ────────────────────────────────────────────────────────────────
if ($changed) {
    $json | ConvertTo-Json -Depth 20 | Set-Content $SettingsFile -Encoding UTF8
    OK "settings.json сохранён"
} else {
    INFO "settings.json не изменился (qwen3 уже отсутствует или не распознан)"
}

# ─── Итоговый статус settings.json ────────────────────────────────────────────
SEC "ИТОГ"

$final = Get-Content $SettingsFile -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "  Текущий settings.json:" -ForegroundColor White
try {
    $finalKeys = $final.PSObject.Properties | Where-Object { $_.Name -ne '$schema' }
    foreach ($kv in $finalKeys) {
        $v = if ($kv.Value -is [string]) { $kv.Value } else { $kv.Value | ConvertTo-Json -Compress }
        Write-Host "    $($kv.Name) = $v"
    }
} catch {}

Write-Host ""
if ($content -match "qwen") {
    $stillHas = (Get-Content $SettingsFile -Raw) -match "qwen"
    if ($stillHas) {
        ERR "qwen ВСЕ ЕЩЕ присутствует в settings.json!"
        ERR "Запусти: .\fixes\fix_claude_nuclear.ps1"
    } else {
        OK "qwen полностью убран из settings.json"
    }
} else {
    OK "qwen не был обнаружен изначально"
}

Write-Host ""
Write-Host "ГОТОВО. Перезапусти Claude Code:" -ForegroundColor Green
Write-Host "  1. Закрой все окна Claude Code" -ForegroundColor White
Write-Host "  2. Открой заново: claude" -ForegroundColor White
Write-Host ""
if ($isAnthropic) {
    Write-Host "  Если ошибка auth — проверь ключ:" -ForegroundColor Yellow
    Write-Host "    claude config set apiKey sk-ant-..." -ForegroundColor White
} elseif ($isOpenRouter -or $apiKeyIsOR) {
    Write-Host "  Если ошибка модели — попробуй альтернативы:" -ForegroundColor Yellow
    foreach ($m in $FREE_MODELS_OR[1..3]) {
        Write-Host "    claude config set model $m" -ForegroundColor White
    }
}
