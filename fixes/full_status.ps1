# full_status.ps1 — полная проверка состояния системы Agent Office
# Запуск: .\fixes\full_status.ps1
# Не вносит никаких изменений — только читает

param([switch]$Json)

$ErrorActionPreference = "SilentlyContinue"

$results = @{}

function Section($t) { if (-not $Json) { Write-Host "`n═══ $t ═══" -ForegroundColor Cyan } }
function OK($t)       { if (-not $Json) { Write-Host "  ✅ $t" -ForegroundColor Green } }
function WARN($t)     { if (-not $Json) { Write-Host "  ⚠️  $t" -ForegroundColor Yellow } }
function ERR($t)      { if (-not $Json) { Write-Host "  ❌ $t" -ForegroundColor Red } }
function INFO($t)     { if (-not $Json) { Write-Host "     $t" -ForegroundColor Gray } }

# ─── CPU ─────────────────────────────────────────────────────────────────────
Section "CPU"
$cpu = (Get-WmiObject Win32_Processor | Measure-Object LoadPercentage -Average).Average
$cpuStatus = if ($cpu -lt 50) { "ok" } elseif ($cpu -lt 70) { "warn" } else { "critical" }
$results.cpu = @{ value = $cpu; status = $cpuStatus; limit = 70 }
if ($cpu -lt 50)     { OK "CPU: $cpu% (норма)" }
elseif ($cpu -lt 70) { WARN "CPU: $cpu% (высокая нагрузка, лимит 70%)" }
else                 { ERR "CPU: $cpu% — ПРЕВЫШЕН ЛИМИТ! Проверь процессы" }

# ─── PM2 ─────────────────────────────────────────────────────────────────────
Section "PM2 процессы"
$pm2Raw = pm2 jlist 2>$null
$pm2 = @()
$pm2Online = 0
$pm2Dead = @()
try {
    $pm2 = $pm2Raw | ConvertFrom-Json
    foreach ($p in $pm2) {
        $st = $p.pm2_env.status
        if ($st -eq "online") {
            $pm2Online++
            OK "$($p.name) ($st) up=$($p.pm2_env.pm_uptime)ms restarts=$($p.pm2_env.restart_time)"
        } else {
            $pm2Dead += $p.name
            ERR "$($p.name) — $st"
        }
    }
} catch {
    WARN "pm2 недоступен: $_"
}
$results.pm2 = @{ total = $pm2.Count; online = $pm2Online; dead = $pm2Dead }

# ─── Порты / HTTP сервисы ─────────────────────────────────────────────────────
Section "Порты и сервисы"
$services = @(
    @{name="brain-мост";       port=9999;  path="/";        key="brain"},
    @{name="token-compressor"; port=9988;  path="/";        key="token"},
    @{name="Hermes";           port=8642;  path="/health";  key="hermes"},
    @{name="command-center";   port=8770;  path="/";        key="cc"},
    @{name="Qdrant";           port=6333;  path="/collections"; key="qdrant"},
    @{name="Ollama";           port=11434; path="/api/tags"; key="ollama"},
    @{name="ComfyUI";          port=8188;  path="/queue";   key="comfyui"},
    @{name="Flowise";          port=3003;  path="/api/v1/chatflows"; key="flowise"},
    @{name="n8n (local)";      port=5678;  path="/healthz"; key="n8n"}
)

$svcResults = @{}
foreach ($svc in $services) {
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:$($svc.port)$($svc.path)" `
                    -TimeoutSec 5 -ErrorAction Stop
        OK "$($svc.name) :$($svc.port) — живой"
        $svcResults[$svc.key] = "alive"
    } catch {
        $msg = $_.ToString()
        if ($msg -match "refused|timed out|Cannot connect") {
            ERR "$($svc.name) :$($svc.port) — недоступен"
            $svcResults[$svc.key] = "down"
        } else {
            WARN "$($svc.name) :$($svc.port) — отвечает с ошибкой: $($_.Exception.Message -replace '\n',' ')"
            $svcResults[$svc.key] = "error"
        }
    }
}
$results.services = $svcResults

# ─── Brain-мост детали ────────────────────────────────────────────────────────
Section "Brain-мост детали"
try {
    $brainStatus = Invoke-RestMethod -Uri "http://localhost:9999/status" -TimeoutSec 10
    $deadModels  = (Invoke-RestMethod -Uri "http://localhost:9999/dead" -TimeoutSec 5).dead
    $brainRoot   = Invoke-RestMethod -Uri "http://localhost:9999/" -TimeoutSec 5

    OK "Роутов: $($brainRoot.count)"
    OK "Моделей живых в free pool: $($brainRoot.free_pool_alive)"

    if ($deadModels.Count -gt 0) {
        WARN "Мёртвые модели ($($deadModels.Count)): $($deadModels -join ', ')"
    } else {
        OK "Все модели free pool живые"
    }

    $checks = $brainStatus.checks
    foreach ($k in $checks.Keys) {
        $v = $checks[$k]
        if ($v -is [string]) {
            if ($v -eq "alive") { INFO "  $k`: alive" } else { INFO "  $k`: $v" }
        }
    }
    $results.brain = @{
        routes       = $brainRoot.count
        free_alive   = $brainRoot.free_pool_alive
        dead_models  = $deadModels
    }
} catch {
    ERR "brain-мост не отвечает: $_"
    $results.brain = @{ status = "down" }
}

# ─── Docker ──────────────────────────────────────────────────────────────────
Section "Docker контейнеры"
$expectedUp  = @("postiz", "postgres", "redis", "sasha-postgres")
$expectedOff = @("temporal", "n8n")
try {
    $dockerPs = docker ps --format "{{.Names}}|{{.Status}}" 2>$null
    $running  = @{}
    foreach ($line in $dockerPs) {
        $parts = $line -split "\|"
        if ($parts.Count -eq 2) { $running[$parts[0]] = $parts[1] }
    }
    foreach ($c in $expectedUp) {
        if ($running.ContainsKey($c)) {
            OK "$c — $($running[$c])"
        } else {
            ERR "$c — НЕ запущен (должен быть!)"
        }
    }
    foreach ($c in $expectedOff) {
        $found = $running.Keys | Where-Object { $_ -match $c }
        if ($found) {
            WARN "$c — ЗАПУЩЕН (держим выключенным из-за CPU/перегрева)"
        } else {
            INFO "$c — выключен (норма)"
        }
    }
    $results.docker = @{ running = @($running.Keys); expected_up = $expectedUp; expected_off = $expectedOff }
} catch {
    WARN "docker недоступен: $_"
    $results.docker = @{ status = "unavailable" }
}

# ─── Переменные окружения (только EXISTS/MISSING) ──────────────────────────────
Section "Ключи API (только наличие)"
$keys = @(
    "KIE_API_KEY", "FAL_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY",
    "XAI_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "POOLSIDE_API_KEY",
    "GEMINI_API_KEY", "B2_KEY_ID", "B2_APP_KEY",
    "ETSY_API_KEY", "AMAZON_SP_API_KEY", "TIKTOK_SHOP_API_KEY",
    "GELATO_API_KEY", "LANGFUSE_SECRET_KEY", "HELICONE_API_KEY",
    "TELEGRAM_BOT_TOKEN"
)
$keyStatus = @{}
$missing = @()
foreach ($k in $keys) {
    $val = [System.Environment]::GetEnvironmentVariable($k)
    if (-not $val) {
        # Try loading from .env in common locations
        $envFiles = @(
            "$env:USERPROFILE\agent_office\.env",
            "$env:USERPROFILE\AppData\Local\agent_office\.env",
            ".\..\.env",
            ".\.env"
        )
        foreach ($ef in $envFiles) {
            if (Test-Path $ef) {
                $line = Get-Content $ef | Where-Object { $_ -match "^$k=" } | Select-Object -First 1
                if ($line) { $val = $line -replace "^$k=", ""; break }
            }
        }
    }
    if ($val) {
        $keyStatus[$k] = "EXISTS"
        INFO "$k`: EXISTS"
    } else {
        $keyStatus[$k] = "MISSING"
        $missing += $k
        WARN "$k`: MISSING"
    }
}
$results.keys = $keyStatus
if ($missing.Count -gt 0) { WARN "Отсутствуют: $($missing -join ', ')" }
else { OK "Все $($keys.Count) ключей найдены" }

# ─── Aeza VPS ─────────────────────────────────────────────────────────────────
Section "Aeza VPS (91.186.216.97)"
INFO "Проверка через SSH невозможна из этого скрипта."
INFO "Вручную: ssh -i ~/.ssh/id_ed25519 root@91.186.216.97"
INFO "         systemctl status sasha-chatter.service"
INFO "         ls /opt/sasha-core/CHATTER_DISABLED  (должен БЫТЬ)"
$results.aeza = @{ note = "manual-check-required" }

# ─── Git статус ───────────────────────────────────────────────────────────────
Section "Git репозитории"
$repos = @(
    @{path="$env:USERPROFILE\agent_office";     name="agent-office"},
    @{path="$env:USERPROFILE\darkhub-seedream45"; name="darkhub-seedream45"}
)
$gitResults = @{}
foreach ($r in $repos) {
    if (Test-Path "$($r.path)\.git") {
        Push-Location $r.path
        $branch = git branch --show-current 2>$null
        $ahead  = git rev-list --count "@{upstream}..HEAD" 2>$null
        $status = git status --porcelain 2>$null
        Pop-Location
        if ($ahead -gt 0) { WARN "$($r.name): $ahead коммитов не запушено (ветка: $branch)" }
        else              { OK   "$($r.name): синхронизирован (ветка: $branch)" }
        if ($status)      { WARN "  Несохранённые изменения в $($r.name)" }
        $gitResults[$r.name] = @{ branch=$branch; ahead=$ahead; dirty=($null -ne $status) }
    } else {
        WARN "$($r.name): папка не найдена ($($r.path))"
        $gitResults[$r.name] = @{ status="not_found" }
    }
}
$results.git = $gitResults

# ─── Итог ─────────────────────────────────────────────────────────────────────
Section "ИТОГ"
$criticals = @()
if ($cpu -ge 70)              { $criticals += "CPU > 70%" }
if ($svcResults["brain"] -ne "alive") { $criticals += "brain-мост :9999 down" }
if ($pm2Dead.Count -gt 0)    { $criticals += "PM2 dead: $($pm2Dead -join ',')" }

if ($criticals.Count -eq 0) {
    OK "Система здорова ✅"
    INFO "PM2: $pm2Online / $($pm2.Count) online"
    INFO "CPU: $cpu%"
} else {
    ERR "КРИТИЧЕСКИЕ ПРОБЛЕМЫ:"
    foreach ($c in $criticals) { ERR "  $c" }
}

if ($Json) {
    $results | ConvertTo-Json -Depth 10
}
