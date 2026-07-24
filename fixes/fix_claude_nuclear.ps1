# fix_claude_nuclear.ps1 — Полное исправление Claude Code (все места где может быть qwen)
# Запуск: .\fixes\fix_claude_nuclear.ps1
# Безопасно — создаёт backup перед каждым изменением

$ErrorActionPreference = "SilentlyContinue"

function OK($t)   { Write-Host "  ✅ $t" -ForegroundColor Green }
function WARN($t) { Write-Host "  ⚠️  $t" -ForegroundColor Yellow }
function ERR($t)  { Write-Host "  ❌ $t" -ForegroundColor Red }
function INFO($t) { Write-Host "     $t" -ForegroundColor Gray }
function SEC($t)  { Write-Host "`n══ $t ══" -ForegroundColor Cyan }

$REPLACEMENT_MODEL = "claude-sonnet-5-20251001"
$BACKUP_SUFFIX     = "_bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Все возможные места где Claude Code хранит конфиги
$CONFIG_FILES = @(
    "$env:USERPROFILE\.claude\settings.json",
    "$env:USERPROFILE\.claude\settings.local.json",
    "$env:APPDATA\Claude\settings.json",
    "$env:APPDATA\Claude\claude_desktop_config.json",
    "$env:LOCALAPPDATA\Claude\settings.json",
    "$env:LOCALAPPDATA\Programs\Claude\resources\app\settings.json"
)

# ─── ФАЗА 1: ДИАГНОСТИКА ────────────────────────────────────────────────────
SEC "ДИАГНОСТИКА"

Write-Host "Ищем все конфиги Claude Code..."
$found_files = @()
foreach ($f in $CONFIG_FILES) {
    if (Test-Path $f) {
        $found_files += $f
        $content = Get-Content $f -Raw
        $hasQwen = $content -match "qwen"
        $icon = if ($hasQwen) { "❌" } else { "✅" }
        Write-Host "  $icon $f" -ForegroundColor (if ($hasQwen) { "Red" } else { "Green" })
        if ($hasQwen) {
            $lines = ($content -split "`n") | Where-Object { $_ -match "qwen" }
            foreach ($l in $lines) {
                INFO "     → $($l.Trim())"
            }
        }
    }
}

# Дополнительный поиск
$extra_search = Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter "settings.json" `
    -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match "claude|Claude" }
foreach ($f in $extra_search) {
    if ($found_files -notcontains $f.FullName) {
        $content = Get-Content $f.FullName -Raw
        if ($content -match "qwen") {
            ERR "Найден доп. файл с qwen: $($f.FullName)"
            $found_files += $f.FullName
        }
    }
}

# Переменные среды
SEC "ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ (ищем qwen)"
$qwen_envs = @()
$all_envs = [System.Environment]::GetEnvironmentVariables()
foreach ($key in $all_envs.Keys) {
    $val = $all_envs[$key]
    if ($val -match "qwen" -or $key -match "qwen") {
        ERR "Env: $key = $($val.Substring(0, [Math]::Min(60, $val.Length)))..."
        $qwen_envs += $key
    }
}
if ($qwen_envs.Count -eq 0) { OK "Переменных среды с qwen не найдено" }

# Проверка ANTHROPIC_BASE_URL
$base_url = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_BASE_URL")
if ($base_url) {
    if ($base_url -match "qwen|openrouter|localhost:9999") {
        WARN "ANTHROPIC_BASE_URL = $base_url"
        WARN "Если это кастомный роутер → он может падать на qwen3"
    } else {
        INFO "ANTHROPIC_BASE_URL = $base_url"
    }
} else {
    OK "ANTHROPIC_BASE_URL не задана (стандартный Anthropic API)"
}

# ─── ФАЗА 2: ИСПРАВЛЕНИЕ ─────────────────────────────────────────────────────
SEC "ИСПРАВЛЕНИЕ"

foreach ($f in $found_files) {
    $content = Get-Content $f -Raw
    if (-not ($content -match "qwen")) { continue }

    Write-Host "Исправляю: $f" -ForegroundColor Yellow

    # Backup
    Copy-Item $f "$f$BACKUP_SUFFIX" -Force
    INFO "Backup: $f$BACKUP_SUFFIX"

    # Попытка через JSON
    try {
        $json = $content | ConvertFrom-Json

        # Заменить в поле model
        if ($json.model -match "qwen") {
            $json.model = $REPLACEMENT_MODEL
            OK "  model: qwen → $REPLACEMENT_MODEL"
        }

        # Убрать qwen из любых массивов
        foreach ($field in @("fallbackModels", "models", "fallbacks", "modelFallbacks",
                             "allowedModels", "enabledModels", "customModels")) {
            if ($json.$field -is [array]) {
                $before = $json.$field.Count
                $json.$field = @($json.$field | Where-Object { $_ -notmatch "qwen" })
                if ($json.$field.Count -ne $before) {
                    OK "  $field: удалено qwen ($before → $($json.$field.Count))"
                }
            }
        }

        # Проверить mcpServers на qwen (очень маловероятно но вдруг)
        if ($json.mcpServers) {
            foreach ($svc in $json.mcpServers.PSObject.Properties) {
                $svcStr = $svc.Value | ConvertTo-Json
                if ($svcStr -match "qwen") {
                    WARN "  MCP сервис '$($svc.Name)' содержит qwen — проверь вручную"
                }
            }
        }

        $json | ConvertTo-Json -Depth 20 | Set-Content $f -Encoding UTF8
        OK "Файл обновлён через JSON"
    }
    catch {
        # Если JSON сломан — заменяем строково
        WARN "JSON парсинг не удался, делаем строковую замену"
        $fixed = $content -replace '"qwen/qwen3-235b-a22b:free"', "`"$REPLACEMENT_MODEL`""
        $fixed = $fixed -replace '"qwen/[^"]*"', "`"$REPLACEMENT_MODEL`""
        $fixed | Set-Content $f -Encoding UTF8
        OK "Строковая замена выполнена"
    }
}

# ─── ФАЗА 3: ОЧИСТКА КЭША ────────────────────────────────────────────────────
SEC "ОЧИСТКА КЭША CLAUDE CODE"

$cache_dirs = @(
    "$env:APPDATA\Claude\Cache",
    "$env:LOCALAPPDATA\Claude\Cache",
    "$env:USERPROFILE\.claude\.cache"
)
foreach ($d in $cache_dirs) {
    if (Test-Path $d) {
        # Удаляем только файлы кэша, не конфиги
        $cache_files = Get-ChildItem $d -File | Where-Object { $_.Extension -in @(".cache", ".tmp", ".log") }
        if ($cache_files.Count -gt 0) {
            $cache_files | Remove-Item -Force
            OK "Очищен кэш: $d ($($cache_files.Count) файлов)"
        } else {
            INFO "Кэш пустой или нет временных файлов: $d"
        }
    }
}

# ─── ФАЗА 4: СОЗДАНИЕ ЧИСТЫХ SETTINGS ───────────────────────────────────────
SEC "ПРОВЕРКА ГЛАВНОГО settings.json"
$mainSettings = "$env:USERPROFILE\.claude\settings.json"
if (Test-Path $mainSettings) {
    $content = Get-Content $mainSettings -Raw
    if ($content -match "qwen") {
        ERR "ВСEЩЁ содержит qwen после исправления — ручная перезапись!"
        # Ядерный вариант — полная перезапись минимальным корректным конфигом
        $minimalConfig = @{
            "`$schema" = "https://json.schemastore.org/claude-code-settings.json"
        } | ConvertTo-Json
        Copy-Item $mainSettings "$mainSettings.EMERGENCY_BAK" -Force
        $minimalConfig | Set-Content $mainSettings -Encoding UTF8
        OK "Перезаписан минимальным конфигом (backup: $mainSettings.EMERGENCY_BAK)"
    } else {
        OK "settings.json чист"
        # Показать структуру (только ключи, без значений)
        try {
            $j = $content | ConvertFrom-Json
            INFO "Ключи в settings.json: $($j.PSObject.Properties.Name -join ', ')"
        } catch {}
    }
}

# ─── ФАЗА 5: ИТОГ + КОМАНДЫ ─────────────────────────────────────────────────
SEC "ИТОГ"

Write-Host ""
Write-Host "Если Claude Code всё ещё не запускается — выполни:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Убрать ANTHROPIC_BASE_URL если он мешает:" -ForegroundColor Cyan
Write-Host '     [System.Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", $null, "User")'
Write-Host ""
Write-Host "  2. Проверить что ANTHROPIC_API_KEY установлен:" -ForegroundColor Cyan
Write-Host '     echo $env:ANTHROPIC_API_KEY  # должен быть sk-ant-...'
Write-Host ""
Write-Host "  3. Перезапустить Claude Code:" -ForegroundColor Cyan
Write-Host "     Закрыть все окна Claude Code → открыть заново"
Write-Host ""
Write-Host "  4. Если совсем не запускается — сбросить конфиг:" -ForegroundColor Cyan
Write-Host '     Remove-Item "$env:USERPROFILE\.claude\settings.json" -Force'
Write-Host "     # (конфиг будет создан заново при следующем запуске)"
Write-Host ""
Write-Host "  5. Проверить версию Claude Code:" -ForegroundColor Cyan
Write-Host "     claude --version"
Write-Host ""
