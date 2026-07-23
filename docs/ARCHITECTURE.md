# Agent Office — System Architecture

Единая архитектура 4 бизнес-проектов: контент-ферма, Etsy, Amazon, TikTok Shop.
Все слои связаны мостами. Ни одного изолированного компонента.

---

## Полная карта системы

```
╔══════════════════════════════════════════════════════════════════════╗
║              LAYER 0 — BROWSER (точка входа)                         ║
║                                                                      ║
║   ZEN BROWSER  (минималистичный, приватный, Arc-подобный)            ║
║   ┌──────────┬─────────┬─────────┬──────────┬─────────┬──────────┐  ║
║   │ComfyUI   │  Buzz   │  n8n    │ Langfuse │  Etsy   │ Amazon   │  ║
║   │:8188     │  :3000  │  :5678  │  :3001   │ Seller  │ Seller   │  ║
║   └────┬─────┴────┬────┴────┬────┴────┬─────┴────┬────┴────┬─────┘  ║
╚════════╪══════════╪═════════╪═════════╪══════════╪═════════╪═════════╝
         │          │         │         │          │         │
         ▼          ▼         │         │          │         │
╔════════════════════════╗    │         │          │         │
║  LAYER 1 — WORKSPACE   ║◀───┘         │          │         │
║  Buzz (Jack Dorsey)    ║              │          │         │
║                        ║              │          │         │
║  AI-агенты как члены   ║              │          │         │
║  команды (Nostr ID)    ║              │          │         │
║                        ║              │          │         │
║  #content-farm         ║              │          │         │
║  #etsy #amazon         ║              │          │         │
║  #tiktok #dev          ║              │          │         │
║  #alerts #budget       ║              │          │         │
╚════════════════════════╝              │          │         │
         │                              │          │         │
         ▼                              ▼          │         │
╔════════════════════════════════════════════╗     │         │
║  LAYER 2 — ORCHESTRATION                   ║     │         │
║                                            ║     │         │
║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ ║     │    │
║  │  CLAUDEXOR   │  │  OPENH ANDS  │  │    HERDR     │ ║     │    │
║  │              │  │              │  │              │ ║     │    │
║  │ • Ротация    │  │ • Автономный │  │ • Терминал   │ ║     │    │
║  │   квот       │  │   AI-разраб. │  │   мультиплек.│ ║     │    │
║  │ • Best-of-N  │  │ • Docker,    │  │ • Несколько  │ ║     │    │
║  │ • Budget caps│  │   self-hosted│  │   агентов    │ ║     │    │
║  │ • MCP server │  │ • Браузер +  │  │   в панелях  │ ║     │    │
║  │ • --max-usd 5│  │   терминал + │  │ • JS плагины │ ║     │    │
║  └──────┬───────┘  │   код        │  │ • Rust-based │ ║     │    │
║         │          │ • Claude API │  └──────┬───────┘ ║     │    │
║         │          └──────┬───────┘         │         ║     │    │
╚═════════╪═════════════════╪═════════════════╪═════════╝     │    │
            │                    │                │         │         │
            ▼                    ▼                ▼         ▼         │
╔═══════════════════════════════════════════════════╗       │
║  LAYER 3 — AUTOMATION PIPELINE                    ║       │
║                                                   ║       │
║  n8n (self-hosted :5678)                          ║       │
║  ┌──────────────────────────────────────────────┐ ║       │
║  │  Триггер → Очередь → Воркер → Хранилище     │ ║       │
║  │  (CSV/cron)  (BullMQ) (Python) (B2/Qdrant)  │ ║       │
║  └──────────────────────────────────────────────┘ ║       │
║                                                   ║       │
║  Redis :6379  ──  BullMQ (job queues)             ║       │
╚═══════════════════════════════════════════════════╝       │
            │                                               │
            ▼                                               ▼
╔═══════════════════════════════════════════════════════════════════╗
║  LAYER 4 — IMAGE GENERATION                                       ║
║                                                                   ║
║  ComfyUI :8188                                                    ║
║  ┌─────────────────────────────────────────────────────────────┐  ║
║  │             darkHUB Node (darkhub-seedream45)               │  ║
║  │                                                             │  ║
║  │  Bridge A: kie.ai          Bridge B: OpenAI-compatible      │  ║
║  │  ┌──────────────────┐      ┌──────────────────────────┐    │  ║
║  │  │ Seedream 4.5 Edit│      │ dall-e-3 / gpt-image-1   │    │  ║
║  │  │ Seedream 4.5 T2I │      │ FAL.ai FLUX Schnell      │    │  ║
║  │  │ Seedream 5.0 Lite│      │ Stability AI 3.5         │    │  ║
║  │  │ (async polling)  │      │ Together AI / Replicate  │    │  ║
║  │  └──────────────────┘      └──────────────────────────┘    │  ║
║  └─────────────────────────────────────────────────────────────┘  ║
╚═══════════════════════════════════════════════════════════════════╝
            │
            ▼
╔═══════════════════════════════════════════════════╗
║  LAYER 5 — LLM / PROMPT ENGINE                    ║
║                                                   ║
║  • Groq (500 tok/s, бесплатно) — промпты, SEO     ║
║  • Cerebras (ultra-fast, бесплатно) — fallback    ║
║  • Poolside Laguna S-2.1 (БЕСПЛАТНО) — coding    ║
║    118B MoE/8B активных, SWE-Bench 78.5%          ║
║    inference.poolside.ai/v1 (OpenAI-compat.)      ║
║  • Ollama (локально) — оффлайн fallback           ║
║  • Claude API (claude-sonnet-5) — листинги        ║
║    Amazon A+, TikTok описания, сложный контент    ║
╚═══════════════════════════════════════════════════╝
            │
            ▼
╔═══════════════════════════════════════════════════╗
║  LAYER 6 — STORAGE & CDN                          ║
║                                                   ║
║  Backblaze B2 ──► Cloudflare CDN ──► imgproxy     ║
║                                                   ║
║  Qdrant (векторная БД)                            ║
║  └─ дедупликация изображений                      ║
║  └─ поиск похожих промптов                        ║
╚═══════════════════════════════════════════════════╝
            │
            ▼
╔═══════════════════════════════════════════════════╗
║  LAYER 7 — OBSERVABILITY                          ║
║                                                   ║
║  • Langfuse — качество промптов, A/B тесты        ║
║  • Helicone — прокси, стоимость токенов           ║
║  • Buzz #alerts — real-time уведомления           ║
║  • Buzz #budget — контроль расходов               ║
╚═══════════════════════════════════════════════════╝
```

---

## Четыре бизнес-проекта

### Проект 1 — Контент-ферма
**Цель:** автоматическая массовая генерация AI-изображений, сотни в день.

```
Groq (промпты) → darkHUB Node (ComfyUI) → Qdrant (деdup) → Backblaze B2
     ↑                                                            ↓
   n8n (расписание/CSV)                               Cloudflare CDN
```

| Компонент | Сервис | Стоимость |
|-----------|--------|-----------|
| Промпты | Groq | Бесплатно |
| Генерация | FAL.ai FLUX Schnell | $0.01/<1 сек |
| Генерация (дешевле) | Stability AI 3.5 | $0.003/img |
| Хранение | Backblaze B2 | $0.006/GB |
| CDN | Cloudflare | Бесплатно |
| Деdup | Qdrant | Self-hosted |

---

### Проект 2 — Etsy Print-on-Demand
**Цель:** изображения → листинги Etsy автоматически.

```
Контент-ферма → Dynamic Mockups → Gelato (POD) → Etsy API v3
                                       ↑
                              Groq (SEO: заголовок + 13 тегов)
```

| Компонент | Сервис |
|-----------|--------|
| Мокапы | Dynamic Mockups API (5000+ шаблонов) |
| Фулфилмент | Gelato API (прямая интеграция с Etsy) |
| SEO | Groq → заголовок + 13 тегов |
| Публикация | Etsy API v3 |
| Мониторинг | Closo / Nembol |

---

### Проект 3 — Amazon Product Listings
**Цель:** изображения → листинги Amazon с A+ контентом.

```
Контент-ферма → Photoroom (белый фон) → Ideogram (инфографика)
                                              ↓
                          Claude API (title + bullets + A+) → SP-API
```

| Компонент | Сервис | Примечание |
|-----------|--------|------------|
| Фон | Photoroom API | Белый — обязателен |
| Инфографика | Ideogram API | Текст на картинке |
| Контент | Claude API | 200 chars title + bullets |
| Публикация | Amazon SP-API | MWS мёртв с 31.03.2024! |
| Мониторинг | Feedvisor / SellerAI | |

---

### Проект 4 — TikTok Shop
**Цель:** контент → TikTok Shop листинги + viral loop.

```
Контент-ферма → AnimateDiff/Kling (видео) → TikTok Shop API
                                                    ↑
                              Claude API (описание + хэштеги)
                                        ↑
                                   Gelato (POD, тот же что Etsy)
```

| Компонент | Сервис |
|-----------|--------|
| Видео | ComfyUI AnimateDiff / Kling AI |
| Контент | Claude API |
| Фулфилмент | Gelato API |
| Публикация | TikTok Shop API |

---

## OpenHands — автономный AI-разработчик

```
╔══════════════════════════════════════════════════════╗
║              OPENH ANDS  (self-hosted Docker)        ║
║                                                      ║
║  Браузер  +  Терминал  +  Редактор кода              ║
║     ↓             ↓            ↓                     ║
║  Веб-скрапинг  Bash/Python  Правка файлов            ║
║                                                      ║
║  ┌─────────────────────────────────────────────┐     ║
║  │  Задача (issue/промпт)                      │     ║
║  │       ↓                                     │     ║
║  │  Claude API (планирование)                  │     ║
║  │       ↓                                     │     ║
║  │  Выполнение (код → тест → фикс → PR)        │     ║
║  └─────────────────────────────────────────────┘     ║
║                                                      ║
║  Использование в системе:                            ║
║  • Автоматическое написание n8n workflows            ║
║  • Фикс багов в darkHUB node по issue из Buzz        ║
║  • Генерация новых ComfyUI нодов                     ║
║  • Обновление листингов при изменении API            ║
╚══════════════════════════════════════════════════════╝

Установка:
  docker pull ghcr.io/all-hands-ai/openhands:main
  docker run -it --rm \
    -e SANDBOX_RUNTIME_CONTAINER_IMAGE=docker.all-hands.dev/all-hands-ai/runtime:0.40-nikolaik \
    -e LOG_ALL_EVENTS=true \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v ~/.openhands-state:/.openhands-state \
    -p 3002:3000 \
    --add-host host.docker.internal:host-gateway \
    ghcr.io/all-hands-ai/openhands:main

Подключение к Claude API:
  ANTHROPIC_API_KEY=sk-ant-...
  Модель: claude-sonnet-5
  Порт: :3002 (в Zen Browser рядом с ComfyUI)
```

---

## herdr — терминальный мультиплексор агентов

```
╔══════════════════════════════════════════════════════╗
║              HERDR (терминальный мультиплексор)      ║
║              github.com/ogulcancelik/herdr            ║
║                                                      ║
║  Запуск нескольких AI-агентов в панелях терминала    ║
║                                                      ║
║  ┌──────────────────────────────────────────────┐    ║
║  │  Панель 1: Claude Code (основной)            │    ║
║  │  Панель 2: OpenHands (автономный разраб.)    │    ║
║  │  Панель 3: Claudexor (оркестратор квот)      │    ║
║  │  Панель N: любой агент...                    │    ║
║  └──────────────────────────────────────────────┘    ║
║                                                      ║
║  JS plugin ecosystem:                                ║
║  • herdr-ops — управление workspace/tabs/panes       ║
║    через естественный язык                           ║
║  • Git worktrees интеграция                          ║
║                                                      ║
║  Использование в Agent Office:                       ║
║  • Параллельный запуск Claude Code + OpenHands       ║
║  • Отдельные панели для каждого проекта              ║
║    (content-farm / etsy / amazon / tiktok)           ║
║  • Мониторинг PM2 процессов рядом с агентами         ║
╚══════════════════════════════════════════════════════╝

Установка:
  cargo install herdr
  # или бинарник со страницы releases

Команды:
  herdr                 # запуск мультиплексора
  herdr new <name>      # новый workspace
  herdr split           # разделить панель
```

---

## Claude Security — проверка безопасности на PR

```
Статус: ✅ УСТАНОВЛЕН
Файл: .github/workflows/security.yml
Action: anthropics/claude-code-security-review@main

Триггер: при каждом pull_request
Действие: Claude проверяет diff на уязвимости
          и оставляет комментарий на PR

Для активации нужен секрет в Settings → Secrets:
  CLAUDE_API_KEY = sk-ant-...
```

---

## Все мосты (bridges)

| Откуда | Куда | Протокол | Данные |
|--------|------|----------|--------|
| Buzz #content-farm | n8n | Webhook | Команда запуска |
| n8n | darkHUB Node | ComfyUI API | Промпт + параметры |
| darkHUB Node | kie.ai | REST | Задача генерации |
| darkHUB Node | FAL.ai | OpenAI compat | /v1/images/generations |
| n8n | Backblaze B2 | S3 API | Сохранение изображений |
| n8n | Qdrant | gRPC | Векторы для деdup |
| n8n | Etsy API | REST v3 | Создание листингов |
| n8n | Amazon SP-API | REST | Создание листингов |
| n8n | TikTok Shop API | REST | Создание листингов |
| n8n | Gelato API | REST | Заказ печати |
| Claudexor | Claude API | Anthropic SDK | Оркестрация |
| OpenHands | Claude API | Anthropic SDK | Автономные задачи |
| OpenHands | Buzz | Webhook | Отчёт о выполнении |
| Helicone | Claude API | Прокси | Мониторинг токенов |
| Langfuse | n8n | SDK | Трекинг промптов |
| Buzz #alerts | Telegram/Email | Webhook | Уведомления |

---

## Переменные окружения

```bash
# Image Generation
KIE_API_KEY=
FAL_KEY=
STABILITY_API_KEY=
OPENAI_API_KEY=

# LLM
ANTHROPIC_API_KEY=
GROQ_API_KEY=

# Storage
B2_KEY_ID=
B2_APP_KEY=
B2_BUCKET=

# Marketplaces
ETSY_API_KEY=
AMAZON_SP_API_KEY=
TIKTOK_SHOP_API_KEY=

# Fulfillment
GELATO_API_KEY=
DYNAMIC_MOCKUPS_API_KEY=
PHOTOROOM_API_KEY=
IDEOGRAM_API_KEY=

# Observability
LANGFUSE_SECRET_KEY=
LANGFUSE_PUBLIC_KEY=
HELICONE_API_KEY=

# Infrastructure
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
```

---

## Порты (все в Zen Browser)

| Сервис | Порт | Описание |
|--------|------|----------|
| ComfyUI | :8188 | Генерация изображений |
| Buzz | :3000 | Workspace |
| OpenHands | :3002 | Автономный разработчик |
| n8n | :5678 | Автоматизация |
| Langfuse | :3001 | Промпт трекинг |
| Qdrant | :6333 | Векторная БД |
| Redis | :6379 | Очереди |
| Helicone | прокси | Мониторинг токенов |
| herdr | терминал | Агент-мультиплексор |

---

## Приоритеты внедрения

| # | Задача | Зависит от | Срок |
|---|--------|-----------|------|
| 1 | ComfyUI + darkHUB нод | — | ✅ Готово |
| 1b | Claude Security (PR проверка) | CLAUDE_API_KEY secret | ✅ Установлено |
| 1c | herdr (терминал-мультиплексор) | Rust/cargo | День 1 |
| 2 | OpenHands (Docker) | Docker, Claude API | День 1 |
| 3 | Redis + BullMQ | Docker | День 1 |
| 4 | n8n self-hosted | Docker | День 2 |
| 5 | Buzz workspace | Docker | День 2 |
| 6 | Qdrant | Docker | День 3 |
| 7 | Backblaze B2 | Аккаунт | День 3 |
| 8 | Контент-ферма pipeline | 1-7 | День 4 |
| 9 | Etsy API интеграция | 8 | Неделя 2 |
| 10 | Gelato интеграция | 9 | Неделя 2 |
| 11 | Amazon SP-API | 8 | Неделя 3 |
| 12 | TikTok Shop API | 8 | Неделя 3 |
| 13 | Langfuse + Helicone | 8 | Неделя 3 |
| 14 | Claudexor оркестрация | 8 | Неделя 4 |
| 15 | Buzz #alerts автоматизация | все | Неделя 4 |
