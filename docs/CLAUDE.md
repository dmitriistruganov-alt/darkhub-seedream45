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

| Провайдер | URL для openai_api_base | Модель |
|-----------|------------------------|--------|
| OpenAI | `https://api.openai.com` | `dall-e-3` / `gpt-image-1` |
| FAL.ai | `https://fal.run` | `fal-ai/flux/schnell` |
| Together AI | `https://api.together.xyz` | FLUX, SDXL |
| Replicate | `https://api.replicate.com` | любая |
| Ollama | `http://localhost:11434` | локальная |

---

## Переменные окружения

```bash
KIE_API_KEY=           # kie.ai Seedream
FAL_KEY=               # FAL.ai
STABILITY_API_KEY=     # Stability AI
OPENAI_API_KEY=        # OpenAI
ANTHROPIC_API_KEY=     # Claude API
GROQ_API_KEY=          # Groq (промпты, бесплатно)
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
```

---

## Важные заметки

- Amazon MWS мёртв с 31.03.2024 — только SP-API
- MidJourney API в 2025 — только enterprise
- FAL.ai FLUX Schnell — лучшее соотношение скорость/цена ($0.01, <1 сек)
- Stability AI 3.5 — самый дешёвый ($0.003/img)
- Ideogram — единственный надёжный для текста на изображении (90-95%)
- OpenHands порт :3002 (чтобы не конфликтовать с Buzz :3000, Langfuse :3001)
