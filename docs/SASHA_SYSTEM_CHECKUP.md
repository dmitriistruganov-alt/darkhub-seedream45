# SASHA SYSTEM CHECKUP
# Снимок системы: 2026-07-22 22:30 | Обновлено: 2026-07-24

Источник: Claude App 2 (локальная сессия на машине Димы).
Этот файл — точная копия состояния всех систем Agent Office.

---

## ИТОГ: СИСТЕМА ЗДОРОВА ✅ (с исправлениями 24.07)

Целевое состояние: **22.07.2026 22:30** — достигнуто.
CPU: **34%** (лимит <70%) ✅

**Исправления 24.07.2026:**
- ✅ brain_server_v2.py — 26 роутов (заменяет мёртвый brain_server.py)
- ✅ qwen/qwen3-235b-a22b:free удалён из пулов (стал платным)
- ✅ Обновлён FREE_POOL: nvidia nemotron / poolside / gemma / gpt-oss
- ✅ OpenRouter + Groq + Poolside Direct в пуле
- ✅ node.py: умный выбор API ключа по провайдеру, gpt-image-1 фикс
- ✅ health_monitor.py — авто-мониторинг и рестарт PM2 процессов
- ✅ telegram_bot.py — управление с телефона
- ✅ openrouter_sync.py — авто-обновление моделей

---

## БЛОК 1 — Git / Облако

| Параметр | Значение |
|----------|---------|
| Репо основной | `dmitriistruganov-alt/agent-office-backup` |
| Ветка основная | `audit/full-digital-human` |
| HEAD | `f04ba6b auto-backup 2026-07-22 22:30` |
| Репо darkHUB | `dmitriistruganov-alt/darkhub-seedream45` |
| Ветка darkHUB | `claude/codex-openai-api-models-x11l8d` |
| Неотправленных | 0 |
| Облако | ✅ в синхроне |

---

## БЛОК 2 — Бот на Aeza (ГЛАВНЫЙ ПРИОРИТЕТ)

| Параметр | Значение |
|----------|---------|
| IP | 91.186.216.97 |
| Пользователь | root |
| SSH ключ | id_ed25519 |
| Сервис | `sasha-chatter.service` |
| Статус | active + enabled (24/7) |
| Аптайм бота | 23 часа |
| RAM | 21 MB |
| Сервер up | 12 дней |
| Load | 0.13 (холодный) |
| Журнал | Чистый, краши отсутствуют |

### Ядро /opt/sasha-core
```
agent_office/
automation/
obsidian_vault/
venv/
.env  (обновлён 22.07)
```

### Флаг чаттера
```
CHATTER_DISABLED = PRESENT
```
Бот молчит по дизайну. **НЕ снимать без команды Димы.**

### LLM движки (Aeza)
- **Чаттер**: Grok (xai) — только с Aeza IP
- **free_brain**: Groq / Cerebras — только с Aeza IP
- **ЗАМЕНА**: После деплоя brain_server_v2 — OpenRouter free pool (10 моделей)

---

## БЛОК 3 — Локальная машина (Windows, C:\Users\18186)

### PM2 процессы: 22/22 online ✅

| Процесс | Статус до | Статус после | Примечание |
|---------|-----------|-------------|-----------|
| daily-monitor | stopped ❌ | online ✅ | — |
| free-llm-sync | stopped ❌ | online ✅ | Нужно обновить модели |
| git-backup (30 мин цикл) | stopped ❌ | online ✅ | Критично! |
| brain-мост | dead (brain_server.py.DEAD) | — | Деплой brain_server_v2! |
| Остальные 19 | online ✅ | online ✅ | — |

### Открытые порты

| Сервис | Порт | Статус |
|--------|------|--------|
| Qdrant | 6333 | ✅ OPEN |
| Ollama | 11434 | ✅ OPEN |
| brain-мост | 9999 | ⚠️ НУЖЕН ДЕПЛОЙ brain_server_v2.py |
| token-compressor | 9988 | ✅ OPEN |
| Hermes | 8642 | ✅ OPEN |
| command-center | 8770 | ✅ OPEN |
| AdsPower API | 50325 | ⚠️ ждёт GUI-логин |

### Ollama
- Статус: ✅ запущен
- Моделей: **5**

---

## БЛОК 4 — Docker-ферма

### Postiz-стек: 4/4 healthy ✅
| Контейнер | Статус |
|-----------|--------|
| postiz | ✅ healthy |
| postgres | ✅ healthy |
| redis | ✅ healthy |
| sasha-postgres | ✅ healthy |

### Намеренно отключены (НЕ поломка)
| Контейнер | Причина |
|-----------|---------|
| Temporal | Durable-фикс перегрева 22.07 — держит CPU холодным |
| n8n (локальный) | Отключён чтобы не плодил окна |

---

## БЛОК 5 — Brain-мост (:9999) — ОБНОВЛЕНО 24.07

**26 роутов (было 15):**

| Категория | Роуты |
|----------|-------|
| LLM | free_brain, grok, gemini, pollinations, cloudflare |
| Мульти | orchestrate, pipeline |
| Код | code_review, codegraph, opencode, codex |
| Прокси | hermes, flowise |
| Память | memory_save, memory_search, wiki_add, wiki_query |
| Cognee | cognee_add, cognee_search |
| Temporal | temporal_add ⛔, temporal_search ⛔ (отключены) |
| Граф | memgraph_search, hy3 |
| Система | obsidian_search, agent_office, status |

**Деплой:**
```powershell
git pull origin claude/codex-openai-api-models-x11l8d
.\fixes\deploy.ps1
```

**Тест после деплоя:**
```powershell
curl http://localhost:9999/
curl -X POST http://localhost:9999/free_brain -d '{"prompt":"hello"}'
```

---

## БЛОК 6 — 7 систем памяти

| # | Система | Состояние | Данные |
|---|---------|-----------|--------|
| 1 | Claude Memory | ✅ | 119 записей |
| 2 | Obsidian | ✅ | 1373 заметки + Fans 1296 |
| 3 | Qdrant | ✅ | 8 коллекций |
| 4 | MF0-1984 | ✅ | — |
| 5 | Hermes Kanban | ✅ | — |
| 6 | agent_office JSON | ✅ | — |
| 7 | MCP | ✅ | 18 серверов |

---

## БЛОК 7 — Telegram Bot (НОВОЕ 24.07)

```
Файл: fixes/telegram_bot.py
PM2:  pm2 start fixes/telegram_bot.py --name tg-agent-bot --interpreter python
Переменные:
  TELEGRAM_BOT_TOKEN = (от @BotFather)
  TELEGRAM_ALLOWED_IDS = ваш Telegram ID

Команды:
  /status, /brain <вопрос>, /dead, /revive, /code, /pipeline, /pm2
```

---

## БЛОК 8 — Температура / CPU

| Параметр | Значение | Лимит |
|----------|---------|-------|
| CPU | 34% | <70% ✅ |
| Перегрев | Нет | — |
| Фикс | Temporal OFF + software throttle | Держит ✅ |

---

## БЛОК 9 — Mодели LLM (обновлено 24.07)

**Удалены (стали платными):**
- ~~qwen/qwen3-235b-a22b:free~~ → платная с 22.07.2026

**Актуальный пул (FREE_POOL в brain_server_v2.py):**
| Модель | Провайдер | Ключ |
|--------|-----------|------|
| nvidia/nemotron-3-ultra-550b-a55b:free | OpenRouter | OPENROUTER_API_KEY |
| nvidia/nemotron-3-super-120b-a12b:free | OpenRouter | OPENROUTER_API_KEY |
| poolside/laguna-s-2.1:free | OpenRouter | OPENROUTER_API_KEY |
| poolside/laguna-xs-2.1:free | OpenRouter | OPENROUTER_API_KEY |
| poolside/laguna-m.1:free | OpenRouter | OPENROUTER_API_KEY |
| google/gemma-4-31b-it:free | OpenRouter | OPENROUTER_API_KEY |
| google/gemma-4-26b-a4b-it:free | OpenRouter | OPENROUTER_API_KEY |
| openai/gpt-oss-20b:free | OpenRouter | OPENROUTER_API_KEY |
| meta-llama/llama-3.3-70b-versatile | Groq | GROQ_API_KEY |
| poolside/laguna-s-2.1 | Poolside Direct | POOLSIDE_API_KEY |

---

## НЕ-БЛОКЕРЫ (не восстанавливать программно)

| Проблема | Тип | Действие |
|---------|-----|----------|
| Железо-перегрев | Физика (кулеры/термопаста/БП) | Руками |
| AdsPower :50325 | Ждёт GUI-логин | Открыть AdsPower вручную |
| CHATTER_DISABLED | Дизайн | Снимать только по команде |
| Temporal контейнер | Отключён намеренно | НЕ запускать |

---

## Репозитории системы Agent Office

| Репо | Ветка | Назначение |
|------|-------|-----------|
| `agent-office-backup` | `audit/full-digital-human` | Главная система |
| `darkhub-seedream45` | `claude/codex-openai-api-models-x11l8d` | ComfyUI darkHUB нод + fixes |
| `runpod-gpu-watcher-v2` | main | GPU мониторинг |
| `flux-stack` | main | FLUX модели |
| `sashamoon` | main | — |

---

## Деплой всех исправлений (24.07.2026)

```powershell
# Шаг 1: Синхронизировать репо
git pull origin claude/codex-openai-api-models-x11l8d

# Шаг 2: Починить Claude Code если падает на qwen3
.\fixes\fix_claude_settings.ps1

# Шаг 3: Деплой brain_server_v2 + обновление моделей
.\fixes\deploy.ps1

# Шаг 4: Запустить health monitor
pm2 start fixes/health_monitor.py --name health-monitor --interpreter python

# Шаг 5: Запустить Telegram бот (нужен TELEGRAM_BOT_TOKEN в .env)
pm2 start fixes/telegram_bot.py --name tg-agent-bot --interpreter python

# Шаг 6: Проверить модели
python fixes/openrouter_sync.py --dry-run

# Шаг 7: Сохранить PM2 конфиг
pm2 save
```

---

*Составлено: 2026-07-23 | Обновлено: 2026-07-24 | Claude Cloud + Claude Code*
