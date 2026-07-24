# fix_ccr_routes.ps1 — Исправить маршруты claude-code-router
# Проблема: longContext → kimi-k2 (платная на OpenRouter) → 400
# recall_hook.py делает все промпты >40k → всё идёт в longContext → падает
# Решение: longContext → groq (128k, бесплатный)
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

SEC "ТЕКУЩИЕ МАРШРУТЫ"
$cfg = Get-Content $CCR_CONFIG -Raw | ConvertFrom-Json
$r = $cfg.Router
INFO "default:              $($r.default)"
INFO "background:           $($r.background)"
INFO "think:                $($r.think)"
INFO "longContext:          $($r.longContext)"
INFO "longContextThreshold: $($r.longContextThreshold)"

SEC "ИСПРАВЛЕНИЕ"

$backup = "$CCR_CONFIG.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $CCR_CONFIG $backup -Force
INFO "Backup: $backup"

$changed = $false

# Проверить longContext — kimi-k2 без :free = платная
if ($r.longContext -match "kimi-k2" -and $r.longContext -notmatch ":free") {
    $cfg.Router.longContext = "groq,llama-3.3-70b-versatile"
    OK "longContext: kimi-k2 (платная) → groq,llama-3.3-70b-versatile (128k, бесплатный)"
    $changed = $true
}

# Проверить longContext — qwen3 (стала платной 22.07)
if ($r.longContext -match "qwen3-235b-a22b:free") {
    $cfg.Router.longContext = "groq,llama-3.3-70b-versatile"
    OK "longContext: qwen3:free (платная) → groq,llama-3.3-70b-versatile"
    $changed = $true
}

# Если default падает — проверить groq
# Groq llama-3.3-70b — 128k контекст, стабильный
if ($r.default -notmatch "groq|cerebras|sambanova") {
    $cfg.Router.default = "groq,llama-3.3-70b-versatile"
    OK "default → groq,llama-3.3-70b-versatile"
    $changed = $true
}

# Если ничего не менялось но ошибка есть — принудительно обновить
if (-not $changed) {
    WARN "Явных проблем в конфиге не найдено — принудительно устанавливаем надёжные маршруты"
    $cfg.Router.default    = "groq,llama-3.3-70b-versatile"
    $cfg.Router.background = "cerebras,llama-3.3-70b"
    $cfg.Router.longContext = "groq,llama-3.3-70b-versatile"
    $changed = $true
    OK "default + longContext → groq | background → cerebras"
}

if ($changed) {
    $cfg | ConvertTo-Json -Depth 10 | Set-Content $CCR_CONFIG -Encoding UTF8
    OK "Конфиг сохранён"
}

SEC "ТЕСТ GROQ"
$groqProvider = $cfg.Providers | Where-Object { $_.name -eq "groq" }
if ($groqProvider -and $groqProvider.api_key) {
    $body = '{"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
    try {
        $resp = Invoke-RestMethod `
            -Uri "https://api.groq.com/openai/v1/chat/completions" `
            -Method POST `
            -Headers @{Authorization="Bearer $($groqProvider.api_key)"; "Content-Type"="application/json"} `
            -Body $body `
            -TimeoutSec 15 `
            -ErrorAction Stop
        OK "Groq API работает — ответ: $($resp.choices[0].message.content)"
    } catch {
        $errMsg = $_.Exception.Message
        if ($errMsg -match "401") {
            ERR "Groq API ключ не действителен (401). Нужен новый ключ с console.groq.com"
        } elseif ($errMsg -match "429") {
            WARN "Groq rate limit (429) — попробуй через минуту или смени на cerebras"
        } else {
            ERR "Groq ошибка: $errMsg"
            WARN "Переключаем на cerebras как запасной..."
            $cfg.Router.default    = "cerebras,llama-3.3-70b"
            $cfg.Router.longContext = "sambanova,Meta-Llama-3.1-405B-Instruct"
            $cfg | ConvertTo-Json -Depth 10 | Set-Content $CCR_CONFIG -Encoding UTF8
            OK "Fallback: default→cerebras, longContext→sambanova"
        }
    }
} else {
    WARN "Groq провайдер не найден в конфиге — пропускаем тест"
}

SEC "ПЕРЕЗАПУСК РОУТЕРА"
ccr stop 2>$null
Start-Sleep -Seconds 2
ccr start 2>$null
Start-Sleep -Seconds 3

# Проверить что роутер запустился
$listening = netstat -ano | Select-String ":345" | Where-Object { $_ -match "LISTENING" }
if ($listening) {
    OK "Роутер запущен: $($listening[0].ToString().Trim())"
} else {
    ERR "Роутер не слушает ни на одном порту из 345x"
}

SEC "ИТОГ"
Write-Host ""
Write-Host "  Обновлённые маршруты:" -ForegroundColor Cyan
$newCfg = Get-Content $CCR_CONFIG -Raw | ConvertFrom-Json
$newCfg.Router | Format-List
Write-Host ""
Write-Host "  Запусти: claude" -ForegroundColor Green
Write-Host ""
Write-Host "  Если ошибка повторится — проверь логи: ccr logs" -ForegroundColor Yellow
Write-Host ""
