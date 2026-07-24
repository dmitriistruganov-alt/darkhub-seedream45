# fix_ccr_routes.ps1 — Исправить маршруты claude-code-router
# Маршрутизирует ВСЁ через OpenRouter с бесплатными моделями из существующего конфига
# Запуск: .\fixes\fix_ccr_routes.ps1

$ErrorActionPreference = "SilentlyContinue"

function OK($t)   { Write-Host "  [OK]  $t" -ForegroundColor Green }
function WARN($t) { Write-Host "  [!!]  $t" -ForegroundColor Yellow }
function ERR($t)  { Write-Host "  [ERR] $t" -ForegroundColor Red }
function INFO($t) { Write-Host "  [ ]   $t" -ForegroundColor Gray }
function SEC($t)  { Write-Host "`n=== $t ===" -ForegroundColor Cyan }

$CCR_CONFIG = "$env:USERPROFILE\.claude-code-router\config.json"

if (-not (Test-Path $CCR_CONFIG)) {
    ERR "Конфиг не найден: $CCR_CONFIG"
    exit 1
}

SEC "ИСПРАВЛЕНИЕ МАРШРУТОВ"
$cfg = Get-Content $CCR_CONFIG -Raw | ConvertFrom-Json
$backup = "$CCR_CONFIG.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $CCR_CONFIG $backup -Force
INFO "Backup: $backup"

# Проверить что openrouter провайдер есть в конфиге
$orProvider = $cfg.Providers | Where-Object { $_.name -eq "openrouter" }
if (-not $orProvider) {
    ERR "openrouter провайдер не найден в config.json!"
    exit 1
}
OK "openrouter провайдер найден (ключ: $($orProvider.api_key.Substring(0,15))...)"

# Установить все маршруты на OpenRouter бесплатные модели
# Используем модели уже прописанные в openrouter.models[] в конфиге
$cfg.Router.default    = "openrouter,nvidia/nemotron-3-ultra-550b-a55b:free"
$cfg.Router.background = "openrouter,google/gemma-4-31b-it:free"
$cfg.Router.longContext = "openrouter,nvidia/nemotron-3-ultra-550b-a55b:free"
$cfg.Router.think      = "openrouter,deepseek/deepseek-r1:free"

OK "default    → openrouter,nvidia/nemotron-3-ultra-550b-a55b:free"
OK "background → openrouter,google/gemma-4-31b-it:free"
OK "longContext → openrouter,nvidia/nemotron-3-ultra-550b-a55b:free (128k ctx)"
OK "think      → openrouter,deepseek/deepseek-r1:free"

# Убедиться что нужные модели есть в списке openrouter.models
$neededModels = @(
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "openai/gpt-oss-20b:free",
    "deepseek/deepseek-r1:free"
)
$existingModels = @($orProvider.models)
$added = @()
foreach ($m in $neededModels) {
    if ($existingModels -notcontains $m) {
        $existingModels += $m
        $added += $m
    }
}
if ($added.Count -gt 0) {
    # Обновить models в провайдере
    for ($i = 0; $i -lt $cfg.Providers.Count; $i++) {
        if ($cfg.Providers[$i].name -eq "openrouter") {
            $cfg.Providers[$i].models = $existingModels
            break
        }
    }
    OK "Добавлены в openrouter.models: $($added -join ', ')"
}

$cfg | ConvertTo-Json -Depth 10 | Set-Content $CCR_CONFIG -Encoding UTF8
OK "Конфиг сохранён"

SEC "ТЕСТ OPENROUTER API"
$body = '{"model":"nvidia/nemotron-3-ultra-550b-a55b:free","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
try {
    $resp = Invoke-RestMethod `
        -Uri "https://openrouter.ai/api/v1/chat/completions" `
        -Method POST `
        -Headers @{
            Authorization = "Bearer $($orProvider.api_key)"
            "Content-Type" = "application/json"
            "HTTP-Referer" = "http://localhost"
        } `
        -Body $body `
        -TimeoutSec 20 `
        -ErrorAction Stop
    OK "OpenRouter API работает! Ответ: $($resp.choices[0].message.content)"
} catch {
    $msg = $_.Exception.Message
    if ($msg -match "401") {
        ERR "OpenRouter ключ не действителен (401)"
    } elseif ($msg -match "429") {
        WARN "OpenRouter rate limit (429) — подожди минуту"
    } elseif ($msg -match "402") {
        ERR "OpenRouter нет кредитов (402) для этой модели"
    } else {
        ERR "OpenRouter ошибка: $msg"
    }
}

SEC "ПЕРЕЗАПУСК CCR"
ccr stop 2>$null
Start-Sleep -Seconds 2
ccr start 2>$null
Start-Sleep -Seconds 3

$alive = netstat -ano 2>$null | Select-String ":345" | Where-Object { $_ -match "LISTENING" }
if ($alive) {
    OK "CCR запущен: $($alive[0].ToString().Trim())"
} else {
    ERR "CCR не запустился!"
}

SEC "ИТОГ"
Write-Host ""
Write-Host "  Запускай: claude" -ForegroundColor Green
Write-Host ""
