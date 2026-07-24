# fix_claude_settings.ps1 — убирает qwen3 из .claude/settings.json
# Проблема: qwen/qwen3-235b-a22b:free стала платной ~22.07.2026
# Эффект: Claude Code перестаёт падать в cascade Fable→Sonnet→Haiku
# Запуск: .\fixes\fix_claude_settings.ps1

$SettingsFile = "$env:USERPROFILE\.claude\settings.json"
if (-not (Test-Path $SettingsFile)) {
    Write-Host "  WARN: $SettingsFile не найден" -ForegroundColor Yellow
    exit 0
}

$backup = "$SettingsFile.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item $SettingsFile $backup
Write-Host "  backup → $backup" -ForegroundColor Cyan

$content = Get-Content $SettingsFile -Raw
$json    = $content | ConvertFrom-Json

# 1. Убрать qwen3 из любых model/fallback полей
$qwenPattern = 'qwen/qwen3-235b-a22b:free'
$replaced = $false

# 2. Если есть поле "model" — проверить и заменить
if ($json.model -match "qwen") {
    $json.model = "claude-sonnet-5"
    $replaced = $true
    Write-Host "  Заменил model: qwen → claude-sonnet-5" -ForegroundColor Green
}

# 3. Убрать из массивов fallbacks/models если есть
foreach ($field in @("fallbackModels", "models", "fallbacks", "modelFallbacks")) {
    if ($json.$field) {
        $before = $json.$field.Count
        $json.$field = @($json.$field | Where-Object { $_ -notmatch "qwen" })
        if ($json.$field.Count -ne $before) {
            $replaced = $true
            Write-Host "  Удалил qwen из $field ($before → $($json.$field.Count) элементов)" -ForegroundColor Green
        }
    }
}

# 4. Сохранить
if ($replaced) {
    $json | ConvertTo-Json -Depth 10 | Set-Content $SettingsFile -Encoding UTF8
    Write-Host "  OK: $SettingsFile обновлён" -ForegroundColor Green
} else {
    Write-Host "  INFO: qwen3 не найден в настройках (возможно уже исправлено)" -ForegroundColor Yellow
}

# 5. Дополнительно — проверить OpenRouter ключ и рабочие модели
Write-Host ""
Write-Host "Проверка OpenRouter:" -ForegroundColor Cyan
$orKey = $env:OPENROUTER_API_KEY
if (-not $orKey) {
    $orKey = (Get-Content "$env:USERPROFILE\AppData\Local\agent_office\.env" -ErrorAction SilentlyContinue |
              Select-String "OPENROUTER_API_KEY" | ForEach-Object { $_ -replace "^OPENROUTER_API_KEY=", "" })
}

if ($orKey) {
    try {
        $resp = Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/models" `
            -Headers @{Authorization = "Bearer $orKey"} -TimeoutSec 10
        $free = $resp.data | Where-Object { $_.id -match ":free$" } | Select-Object -First 10
        Write-Host "  Доступные бесплатные модели (первые 10):" -ForegroundColor Green
        $free | ForEach-Object { Write-Host "    $($_.id)" }
    } catch {
        Write-Host "  Не удалось проверить OpenRouter: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  OPENROUTER_API_KEY не найден — пропускаем проверку" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Готово. Перезапусти Claude Code." -ForegroundColor Green
