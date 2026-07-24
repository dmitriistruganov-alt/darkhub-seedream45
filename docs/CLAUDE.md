# Agent Office — Контекст системы

Этот файл читается Claude автоматически в начале каждой сессии.

---

## Владелец

- Email: dmitriistruganov@gmail.com
- GitHub: dmitriistruganov-alt

---

## Система называется: Agent Office

4 бизнес-проекта на единой AI-инфраструктуре.

---

## Четыре бизнес-проекта

### 1. Контент-ферма
Автоматическая массовая генерация AI-изображений, сотни в день.
- Промпты: Groq (бесплатно, 500 tok/s)
- Генерация: FAL.ai FLUX Schnell ($0.01/<1 сек) / Stability AI ($0.003/img)
- Хранение: Backblaze B2 + Cloudflare CDN
- Дедупликация: Qdrant (векторная БД)
- Трекинг: Langfuse
- Оркестрация: n8n + BullMQ/Redis

### 2. Etsy Print-on-Demand
Изображения → Etsy листинги автоматически.
- Мокапы: Dynamic Mockups API (5000+ шаблонов)
- Фулфилмент: Gelato API (POD, прямая интеграция с Etsy)
- SEO: Groq → заголовок + 13 тегов
- Публикация: Etsy API v3

### 3. Amazon Product Listings
Изображения → Amazon A+ листинги автоматически.
- Фон: Photoroom API (белый — обязателен)
- Инфографика: Ideogram API (текст на картинке)
- Контент: Claude API (title 200 chars + bullets + A+)
- Публикация: Amazon SP-API (MWS мёртв с 31.03.2024!)

### 4. TikTok Shop
Контент + видео → TikTok Shop листинги + viral loop.
- Видео: ComfyUI AnimateDiff / Kling AI
- Контент: Claude API (описание + хэштеги)
- Фулфилмент: Gelato API (тот же что Etsy)
- Публикация: TikTok Shop API

---

## Репозитории

| Репо | Назначение |
|------|-----------|
| `agent-office` | Главная архитектура |
| `darkhub-seedream45` | ComfyUI нод для генерации изображений |
| `runpod-gpu-watcher-v2` | Мониторинг GPU на RunPod |
| `flux-stack` | FLUX модели |
| `sashamoon` | — |

---

## Brain Server v2 (замена мёртвого brain_server.py)

**Файл:** `fixes/brain_server_v2.py`
**Порт:** 9999 (совместим с прежним)
**Статус:** ✅ Написан, готов к деплою

### 26 роутов:

| Роут | Описание |
|------|----------|
| `free_brain` | Пул 10 бесплатных LLM с circuit breaker |
| `grok` | xAI Grok API |
| `gemini` | Google Gemini |
| `pollinations` | Pollinations.ai (text + image, БЕЗ ключа) |
| `cloudflare` | Cloudflare Workers AI |
| `orchestrate` | N моделей параллельно → лучший ответ |
| `pipeline` | Цепочка промптов (шаги через {prev}) |
| `code_review` | Авто-ревью кода |
| `codegraph` | Анализ структуры кода |
| `opencode` | Coding-optimized пул |
| `codex` | Code generation |
| `hermes` | Прокси → localhost:8642 |
| `flowise` | Прокси → localhost:3003 |
| `memory_save` | Сохранить в memory.json |
| `memory_search` | Поиск в memory.json |
| `wiki_add` | Добавить в wiki (namespace в memory) |
| `wiki_query` | Поиск в wiki |
| `cognee_add` | Добавить в Cognee (fallback → memory) |
| `cognee_search` | Поиск в Cognee (fallback → memory) |
| `temporal_add` | ОТКЛЮЧЕНО (перегрев) |
| `temporal_search` | ОТКЛЮЧЕНО (перегрев) |
| `memgraph_search` | Поиск в Memgraph (fallback → memory) |
| `obsidian_search` | Поиск в Obsidian vault |
| `hy3` | Гибридный поиск: Qdrant + memory + Obsidian |
| `agent_office` | Статус всех 4 сервисов |
| `status` | Health check всей инфраструктуры |

### Деплой (одна команда):
```powershell
git pull origin claude/codex-openai-api-models-x11l8d
.\fixes\deploy.ps1
```

---

## Free LLM Pool (обновлено 2026-07-24)

**УДАЛЁН:** `qwen/qwen3-235b-a22b:free` — стала платной ~22.07.2026

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

## darkHUB Node (darkhub-seedream45)

ComfyUI нод с двумя бэкендами:
- **kie.ai**: Seedream 4.5 Edit / T2I / 5.0 Lite
- **OpenAI-совместимый**: любой провайдер через `openai_api_base`

**Активная ветка:** `claude/codex-openai-api-models-x11l8d`

### Исправления (23-24.07.2026):
- ✅ Удалён hardcoded demo KIE_API_KEY (`44f4c847...`)
- ✅ Убран несуществующий `WEB_DIRECTORY = "./js"`
- ✅ Добавлен OpenAI-compatible бэкенд (`_generate_openai`)
- ✅ OPENAI_SIZE_MAP, OPENAI_QUALITY, OPENAI_STYLE константы

---

## OpenAI-совместимые провайдеры

| Провайдер | URL для openai_api_base | Модель | Цена |
|-----------|------------------------|--------|------|
| OpenAI | `https://api.openai.com` | `dall-e-3` / `gpt-image-1` | платно |
| FAL.ai | `https://fal.run` | `fal-ai/flux/schnell` | $0.01/img |
| Together AI | `https://api.together.xyz` | FLUX, SDXL | платно |
| Replicate | `https://api.replicate.com` | любая | платно |
| Ollama | `http://localhost:11434` | локальная | бесплатно |
| **Poolside** | `https://inference.poolside.ai/v1` | `poolside/laguna-s-2.1` | **БЕСПЛАТНО** |
| OpenRouter | `https://openrouter.ai/api/v1` | любая (14 ключей в ротации) | по модели |

---

## Переменные окружения

```bash
KIE_API_KEY=           # kie.ai Seedream
FAL_KEY=               # FAL.ai
STABILITY_API_KEY=     # Stability AI
OPENAI_API_KEY=        # OpenAI
ANTHROPIC_API_KEY=     # Claude API
GROQ_API_KEY=          # Groq (промпты, бесплатно)
OPENROUTER_API_KEY=    # OpenRouter (14 ключей в ротации)
POOLSIDE_API_KEY=      # Poolside Laguna S/XS-2.1 (БЕСПЛАТНО)
XAI_API_KEY=           # xAI Grok
GEMINI_API_KEY=        # Google Gemini
CF_ACCOUNT_ID=         # Cloudflare Workers AI
CF_API_TOKEN=          # Cloudflare Workers AI
B2_KEY_ID=             # Backblaze B2
B2_APP_KEY=
B2_BUCKET=
ETSY_API_KEY=          # Etsy API v3
AMAZON_SP_API_KEY=     # Amazon SP-API (не MWS!)
TIKTOK_SHOP_API_KEY=   # TikTok Shop
GELATO_API_KEY=
DYNAMIC_MOCKUPS_API_KEY=
PHOTOROOM_API_KEY=
IDEOGRAM_API_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_PUBLIC_KEY=
HELICONE_API_KEY=
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
OBSIDIAN_VAULT=C:\Users\18186\obsidian_vault
BRAIN_PORT=9999
# Проверять EXISTS/MISSING — НИКОГДА не печатать значения
```

---

## Важные правила безопасности

- **CPU потолок: 70%.** Перед тяжёлыми операциями — `Get-WmiObject Win32_Processor`
- **Temporal контейнер: держать ВЫКЛЮЧЕННЫМ** (причина перегрева)
- **CHATTER_DISABLED.flag на Aeza (91.186.216.97): НЕ трогать** без явной команды Димы
- Amazon MWS мёртв с 31.03.2024 — только SP-API
- НИКОГДА не печатать значения API ключей — только проверять EXISTS/MISSING

---

## Задачи (статус 24.07.2026)

| # | Задача | Статус | Действие |
|---|--------|--------|---------|
| 1 | brain_server_v2.py — 26 роутов | ✅ Написан | `.\fixes\deploy.ps1` |
| 2 | circuit_breaker.py модуль | ✅ Написан | скопировать в `agent_office/core/` |
| 3 | update_models.py — удалить qwen3 | ✅ Написан | `python fixes/update_models.py` |
| 4 | deploy.ps1 одна команда деплоя | ✅ Написан | `.\fixes\deploy.ps1` |
| 5 | fix_claude_settings.ps1 | ✅ Написан | `.\fixes\fix_claude_settings.ps1` |
| 6 | Починить git-backup PM2 | ⏳ Локально | `pm2 restart git-backup && pm2 save` |
| 7 | OpenHuman inference_url проверить | ⏳ Локально | `AppData\Local\OpenHuman\config.toml` |
| 8 | CLAUDE_API_KEY секрет для GitHub | ⏳ Локально | Settings → Secrets → CLAUDE_API_KEY |
| 9 | Laguna XS-2.1 добавить до 28.07 | ✅ В brain_server_v2 | уже в CODING_POOL |
| 10 | Telegram bot MCP | ⏳ Будущее | `mcp-telegram` пакет |

**Не трогать без команды:**
- CHATTER_DISABLED на Aeza (91.186.216.97)
- Temporal контейнер (держать OFF)
- OpenModel.ai ключи (баланс $0, мёртвый провайдер)
