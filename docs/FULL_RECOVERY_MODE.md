# FULL SYSTEM RECOVERY MODE
# Agent Office — Absolute Infrastructure Reconstruction
# Владелец: Дмитрий Стругanov (dmitriistruganov@gmail.com)
# Дата снимка: 2026-07-22 22:30

---

## ИНСТРУКЦИЯ ДЛЯ CLAUDE В НАЧАЛЕ КАЖДОЙ СЕССИИ

Если ты читаешь это — запусти ПОЛНОЕ ВОССТАНОВЛЕНИЕ.
Не кодируй. Не отвечай на вопросы. Сначала восстанови всё.

```
МАШИНА: Windows, C:\Users\18186
AEZA VPS: 91.186.216.97 (root, id_ed25519)
РЕПО: dmitriistruganov-alt/agent-office-backup
ВЕТКА: audit/full-digital-human
HEAD: f04ba6b auto-backup 2026-07-22 22:30
```

---

## ФАЗА 1 — ИНВЕНТАРИЗАЦИЯ МАШИНЫ

### Что искать на диске
```
C:\Users\18186\
├── .claude/          # Claude Code конфиги, память, настройки
├── .config/          # Конфиги приложений
├── AppData\Roaming\  # MCP серверы, расширения
├── Documents\        # Проекты, воркспейсы
├── agent_office\     # Главная папка системы
├── obsidian_vault\   # 1373 заметки (НЕ в git)
├── automation\       # Скрипты автоматизации
└── .ssh\             # Ключи (id_ed25519 для Aeza)
```

### Команды инвентаризации
```powershell
# PM2 статус
pm2 list
pm2 logs --lines 50

# Docker
docker ps -a
docker images
docker volume ls

# Порты
netstat -ano | findstr "LISTENING"

# Python окружения
pip list
conda env list

# Node
npm list -g

# Ollama модели
ollama list

# Claude MCP
cat %APPDATA%\Claude\claude_desktop_config.json
```

---

## ФАЗА 2 — ИЗВЕСТНОЕ СОСТОЯНИЕ СИСТЕМЫ (22.07.2026 22:30)

### PM2 — 22 процесса (все должны быть online)
| Процесс | Порт | Статус цели |
|---------|------|-------------|
| daily-monitor | — | ✅ online |
| free-llm-sync | — | ✅ online |
| git-backup | — | ✅ online (30 мин цикл) |
| brain-мост | 9999 | ✅ online |
| token-compressor | 9988 | ✅ online |
| Hermes | 8642 | ✅ online |
| command-center | 8770 | ✅ online |
| Qdrant | 6333 | ✅ online |
| Ollama | 11434 | ✅ online |
| + 13 других | — | ✅ online |

**Если упали — поднять:**
```bash
pm2 resurrect
pm2 start daily-monitor
pm2 start free-llm-sync
pm2 start git-backup
pm2 save
```

### Docker контейнеры
| Контейнер | Статус цели | Примечание |
|-----------|-------------|-----------|
| postiz | ✅ healthy | Запускать |
| postgres | ✅ healthy | Запускать |
| redis | ✅ healthy | Запускать |
| sasha-postgres | ✅ healthy | Запускать |
| Temporal | ⛔ OFF | НЕ запускать (фикс перегрева) |
| n8n (локал) | ⛔ OFF | НЕ запускать |

```bash
docker start postiz postgres redis sasha-postgres
```

### Открытые порты (обязательно)
```
6333  - Qdrant
11434 - Ollama
9999  - brain-мост (15 роутов)
9988  - token-compressor
8642  - Hermes
8770  - command-center
8188  - ComfyUI
50325 - AdsPower API (ручной логин GUI)
```

---

## ФАЗА 3 — AEZA BOT

```bash
ssh -i ~/.ssh/id_ed25519 root@91.186.216.97

# Проверить сервис
systemctl status sasha-chatter.service
journalctl -u sasha-chatter.service -n 50

# Ядро
ls /opt/sasha-core/
cat /opt/sasha-core/.env

# Флаг молчания
ls /opt/sasha-core/CHATTER_DISABLED
# Если файл ЕСТЬ — бот молчит (это нормально)
# Если файла НЕТ — бот пишет (опасно без команды Димы)

# Перезапуск если нужно
systemctl restart sasha-chatter.service
```

**Структура ядра:**
```
/opt/sasha-core/
├── agent_office/
├── automation/
├── obsidian_vault/
├── venv/
└── .env
```

**LLM движки:**
- Чаттер: Grok (xai) — только с Aeza IP
- free_brain: Groq / Cerebras — только с Aeza IP

---

## ФАЗА 4 — MCP СЕРВЕРЫ (18 шт)

**Конфиг:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Проверить наличие:**
- filesystem MCP
- github MCP
- memory MCP
- browser MCP
- docker MCP
- postgres MCP
- qdrant MCP
- slack/buzz MCP
- и другие 10+

**Мосты brain-мост :9999 (15 роутов):**
```
agent_office · codex · hermes · free_brain · grok · gemini
flowise · pollinations · cloudflare · hy3 · ...
```

---

## ФАЗА 5 — 7 СИСТЕМ ПАМЯТИ

| # | Система | Где | Данных |
|---|---------|-----|--------|
| 1 | Claude Memory | %APPDATA%\Claude\ | 119 записей |
| 2 | Obsidian | obsidian_vault\ | 1373 + Fans 1296 |
| 3 | Qdrant | :6333 | 8 коллекций |
| 4 | MF0-1984 | agent_office\ | — |
| 5 | Hermes Kanban | :8642 | — |
| 6 | agent_office JSON | agent_office\ | — |
| 7 | MCP | claude_desktop_config | 18 серверов |

**Проверить Qdrant:**
```bash
curl http://localhost:6333/collections
```

**Obsidian НЕ в git** — только локально + Aeza копия.

---

## ФАЗА 6 — КОМФYUI

```
Путь: C:\...\ComfyUI\
Порт: :8188
```

**Проверить:**
- Custom nodes установлены
- Модели на месте (models\checkpoints\, models\loras\)
- darkHUB нод (репо darkhub-seedream45)
- API доступен: http://localhost:8188/queue

**darkHUB нод:**
```
Репо: darkhub-seedream45
Ветка: claude/codex-openai-api-models-x11l8d
Два бэкенда: kie.ai + OpenAI-compatible
```

---

## ФАЗА 7 — ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ / КЛЮЧИ

**НИКОГДА не печатать ключи — только проверить наличие:**

```powershell
# Проверить .env файлы (не выводить значения)
Get-ChildItem -Recurse -Filter ".env" | Select-Object FullName
Get-ChildItem -Recurse -Filter "*.env" | Select-Object FullName

# Проверить переменные среды
[System.Environment]::GetEnvironmentVariables() | Select-Object -First 5
```

**Ожидаемые ключи (только проверить EXISTS/MISSING):**
```
KIE_API_KEY          - kie.ai
FAL_KEY              - FAL.ai
ANTHROPIC_API_KEY    - Claude API
GROQ_API_KEY         - Groq
XAI_API_KEY          - Grok (xai)
OPENAI_API_KEY       - OpenAI
B2_KEY_ID            - Backblaze B2
B2_APP_KEY           - Backblaze B2
ETSY_API_KEY         - Etsy
AMAZON_SP_API_KEY    - Amazon SP-API
TIKTOK_SHOP_API_KEY  - TikTok Shop
GELATO_API_KEY       - Gelato
LANGFUSE_SECRET_KEY  - Langfuse
HELICONE_API_KEY     - Helicone
```

---

## ФАЗА 8 — CPU / ТЕМПЕРАТУРА

**Лимит: CPU < 70%**

```powershell
# Текущая загрузка
Get-WmiObject -Class Win32_Processor | Select-Object LoadPercentage

# Если > 70% — проверить что жрёт
Get-Process | Sort-Object CPU -Descending | Select-Object -First 10
```

**Temporal держим ВЫКЛЮЧЕННЫМ** — это главная причина перегрева.

---

## ФАЗА 9 — ОБЛАКО / GITHUB

```bash
# Проверить синхрон
git status
git log --oneline -5
git remote -v

# Должно быть:
# origin = github.com/dmitriistruganov-alt/agent-office-backup
# ветка = audit/full-digital-human
# HEAD = f04ba6b (22.07.2026 22:30)
```

---

## ФАЗА 10 — ФИНАЛЬНЫЙ ОТЧЁТ (заполнить после проверки)

```
[ ] PM2: ___/22 online
[ ] Docker: ___/4 healthy (Temporal/n8n OFF)
[ ] Aeza bot: active/inactive
[ ] CHATTER_DISABLED: present/missing
[ ] Brain-мост :9999: ok/fail
[ ] Qdrant :6333: ___ коллекций
[ ] Ollama :11434: ___ моделей
[ ] MCP серверов: ___/18
[ ] ComfyUI :8188: ok/fail
[ ] CPU: ___%
[ ] Git sync: ok/fail
[ ] Ключи: ___/14 найдено
```

---

## ПРАВИЛА ВОССТАНОВЛЕНИЯ

```
❌ НИКОГДА не удалять
❌ НИКОГДА не перезаписывать без проверки
❌ НИКОГДА не ротировать ключи
❌ НИКОГДА не очищать кэши
❌ НИКОГДА не пересоздавать конфиги
❌ НИКОГДА не трогать базы данных

✅ Сначала проверить существование
✅ Потом поднять если упало
✅ Потом зафиксировать статус
✅ Потом продолжить прерванную работу
```

---

*Этот файл: darkhub-seedream45/docs/FULL_RECOVERY_MODE.md*
*Сессионный отчёт: obsidian_vault/Сессии/2026-07-22-Восстановление-полное.md*
*Claude Memory: recovery-verified-jul22.md*
