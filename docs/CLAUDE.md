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
| `agent-office` | Главная архитектура (этот файл) |
| `darkhub-seedream45` | ComfyUI нод для генерации изображений |
| `runpod-gpu-watcher-v2` | Мониторинг GPU на RunPod |
| `flux-stack` | FLUX модели |
| `sashamoon` | — |

---

## Ключевые инструменты

### darkHUB Node (darkhub-seedream45)
ComfyUI нод с двумя бэкендами:
- **kie.ai**: Seedream 4.5 Edit / T2I / 5.0 Lite
- **OpenAI-совместимый**: любой провайдер через `openai_api_base`
- Активная ветка: `claude/codex-openai-api-models-x11l8d`

### OpenHands (новое)
Автономный AI-разработчик, self-hosted Docker.
- Порт: :3002
- Модель: claude-sonnet-5
- Задачи: фикс багов, написание n8n workflows, новые ноды
- `docker pull ghcr.io/all-hands-ai/openhands:main`

### Claudexor
Мульти-агентный оркестратор Claude Code / Codex.
- Ротация квот, best-of-N, budget caps (`--max-usd 5`)
- MCP server mode
- `github.com/razzant/claudexor`

### Buzz (Jack Dorsey / Block)
Open-source workspace, AI-агенты как члены команды.
- Протокол Nostr, Apache 2.0, self-hosted
- Каналы: #content-farm #etsy #amazon #tiktok #dev #alerts #budget

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
POOLSIDE_API_KEY=      # Poolside Laguna S/XS-2.1 — coding модели, БЕСПЛАТНО (добавлен 23.07)
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
# Проверять EXISTS/MISSING — НИКОГДА не печатать значения
```

---

## Важные заметки

- Amazon MWS мёртв с 31.03.2024 — только SP-API
- MidJourney API в 2025 — только enterprise
- FAL.ai FLUX Schnell — лучшее соотношение скорость/цена ($0.01, <1 сек)
- Stability AI 3.5 — самый дешёвый ($0.003/img)
- Ideogram — единственный надёжный для текста на изображении (90-95%)
- OpenHands порт :3002 (чтобы не конфликтовать с Buzz :3000, Langfuse :3001)
- Poolside БЕСПЛАТНО: inference.poolside.ai/v1, модели laguna-s-2.1 / laguna-xs-2.1
- CPU потолок: 70%. Перед тяжёлыми операциями — Get-WmiObject Win32_Processor
- Temporal контейнер: держать ВЫКЛЮЧЕННЫМ (причина перегрева)
- CHATTER_DISABLED.flag на Aeza: НЕ трогать без явной команды Димы

---

## Задачи для локального Claude Code (подхвати при следующем запуске)

Статус проверки: 23.07.2026. Система здорова.

| # | Задача | Файл/место | Приоритет |
|---|--------|-----------|-----------|
| 1 | Починить git-backup в PM2 (статус stopped → online) | `pm2 resurrect && pm2 save` | 🔴 ВЫСОКИЙ |
| 2 | Добавить Poolside в free_brain.py (маршрут "coding") | `agent_office/core/free_brain.py` | 🟡 Средний |
| 3 | Добавить Poolside в ALL_WORKERS пул | `agent_office/core/config.py` | 🟡 Средний |
| 4 | Проверить OpenHuman после смены inference_url на anthropic | `AppData\Local\OpenHuman\config.toml` | 🟡 Средний |
| 5 | /reload-plugins в Claude Code или новая сессия для активации claude-security | сессия Claude Code | 🟢 Низкий |
| 6 | Добавить Laguna XS-2.1 в free_brain (истекает 28.07 — ускорить!) | `free_brain.py` | 🟡 Средний |
| 7 | Проверить Scheduled Tasks: HealTick/DeepCheck/SashaMemoryFeed/TelegramAgentBot | Task Scheduler | 🟡 Средний |
| 8 | Obsidian-mind семантический поиск — спросить Диму нужно ли | — | 🟢 Низкий |

**Не трогать без команды:**
- CHATTER_DISABLED на Aeza (91.186.216.97)
- Temporal контейнер (держать OFF)
- OpenModel.ai ключи (баланс $0, мёртвый провайдер)
