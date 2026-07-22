# darkHUB — System Architecture

Единая архитектура трёх бизнес-проектов: контент-ферма, Etsy, Amazon, TikTok Shop.
Все слои связаны мостами. Ни одного изолированного компонента.

---

## Полная карта системы

```
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                         LAYER 0 — BROWSER (точка входа)                          ║
║                                                                                   ║
║   ZEN BROWSER  (минималистичный, приватный, Arc-подобный)                        ║
║   ┌───────────┬──────────────┬────────────┬────────────┬───────────┬──────────┐  ║
║   │ComfyUI    │  Buzz        │   n8n      │  Langfuse  │  Etsy     │ Amazon   │  ║
║   │:8188      │  :3000       │   :5678    │  :3001     │  Seller   │ Seller   │  ║
║   └─────┬─────┴──────┬───────┴──────┬─────┴─────┬──────┴─────┬─────┴────┬─────┘  ║
╚═════════╪════════════╪══════════════╪═══════════╪════════════╪══════════╪═════════╝
          │            │              │           │            │          │
          ▼            ▼              │           │            │          │
╔═════════════════════════════════╗   │           │            │          │
║  LAYER 1 — WORKSPACE (Buzz)     ║◀──┘           │            │          │
║                                 ║               │            │          │
║  Jack Dorsey / Block / Apache   ║               │            │          │
║  AI-агенты как полноправные     ║               │            │          │
║  сотрудники (Nostr-идентичность)║               │            │          │
║                                 ║               │            │          │
║  #content-farm  ← агент пишет  ║               │            │          │
║  #etsy          ← листинги     ║               │            │          │
║  #amazon        ← SP-API статус║               │            │          │
║  #tiktok        ← видео/продажи║               │            │          │
║  #dev           ← Claude Code  ║               │            │          │
║  #alerts        ← бюджет/ошибки║               │            │          │
║                                 ║               │            │          │
║  Интеграции: Claude Code,       ║               │            │          │
║  Codex, Block goose             ║               │            │          │
╚════════════════╤════════════════╝               │            │          │
                 │                                │            │          │
                 ▼                                │            │          │
╔═══════════════════════════════════╗             │            │          │
║  LAYER 2 — ORCHESTRATION          ║             │            │          │
║           (Claudexor)             ║             │            │          │
║                                   ║             │            │          │
║  • Quota rotation между аккаунтами║             │            │          │
║  • Best-of-N: запустить промпт   ║             │            │          │
║    на 3 провайдерах → взять лучший║             │            │          │
║  • Budget caps --max-usd $5.00   ║             │            │          │
║  • MCP сервер для Claude Code    ║             │            │          │
║  • Аудит каждого действия агента ║             │            │          │
╚═══════════════╤═══════════════════╝             │            │          │
                │                                 │            │          │
                ▼                                 ▼            │          │
╔══════════════════════════════════════════════════════════╗   │          │
║         LAYER 3 — AUTOMATION (n8n + BullMQ)              ║◀──┘          │
║                                                          ║              │
║  n8n :5678  (визуальные пайплайны, self-hosted)          ║              │
║  ┌─────────────────────────────────────────────────┐     ║              │
║  │ Trigger: расписание / CSV / RSS / webhook        │     ║              │
║  │     ↓                                            │     ║              │
║  │ Groq/Ollama: сгенерировать промпт из темы        │     ║              │
║  │     ↓                                            │     ║              │
║  │ BullMQ + Redis: поставить в очередь              │     ║              │
║  │     ↓  (параллельно N воркеров)                  │     ║              │
║  │ darkHUB Node × N: генерация изображений          │     ║              │
║  │     ↓                                            │     ║              │
║  │ Qdrant: дедупликация + сохранение вектора        │     ║              │
║  │     ↓                                            │     ║              │
║  │ Backblaze B2: сохранить файл                     │     ║              │
║  │     ↓                                            │     ║              │
║  │ Buzz #content-farm: отчёт агента                 │     ║              │
║  └─────────────────────────────────────────────────┘     ║              │
╚══════════════════════════╤═══════════════════════════════╝              │
                           │                                               │
                           ▼                                               │
╔══════════════════════════════════════════════════════════════════════╗   │
║              LAYER 4 — IMAGE GENERATION                               ║   │
║                                                                       ║   │
║   ComfyUI :8188                                                       ║   │
║   └── darkHUB Node (DarkHubFreepikStudio)                            ║   │
║                │                                                      ║   │
║       ┌────────▼────────┐                                             ║   │
║       │ Router          │  openai_api_base пустой → kie.ai           ║   │
║       │ (openai_api_    │  openai_api_base задан  → OpenAI-compat    ║   │
║       │  base empty?)   │                                             ║   │
║       └──────┬──────────┘                                             ║   │
║              │                                                        ║   │
║   ┌──────────┴────────────────────────────────────────┐              ║   │
║   │                                                    │              ║   │
║   ▼  BRIDGE A                            BRIDGE B ▼   │              ║   │
║ ┌─────────────────────┐         ┌─────────────────────────────────┐  ║   │
║ │   kie.ai (Seedream) │         │   OpenAI-Compatible Providers   │  ║   │
║ │                     │         │                                 │  ║   │
║ │ • seedream/4.5-edit │         │ FAL.ai      $0.01  <1 сек      │  ║   │
║ │ • seedream/4.5 T2I  │         │ Stability   $0.003  3-5 сек    │  ║   │
║ │ • seedream/5.0-lite │         │ Together AI $0.015  2-3 сек    │  ║   │
║ │                     │         │ GPT-Image-1 $0.005  10-20 сек  │  ║   │
║ │ async: createTask   │         │ Ideogram    $0.06   текст      │  ║   │
║ │        poll 3s      │         │ BFL FLUX    $0.01   2-4 сек    │  ║   │
║ │        getTaskDetail│         │                                 │  ║   │
║ └─────────────────────┘         └─────────────────────────────────┘  ║   │
╚══════════════════════════════════════════════════════════════════════╝   │
                           │                                               │
                           ▼                                               │
╔══════════════════════════════════════════════════════════════════════╗   │
║              LAYER 5 — LLM / PROMPT ENGINE                            ║   │
║                                                                       ║   │
║  Groq      api.groq.com        500 tok/s  бесплатно 30 req/min       ║   │
║  ├── генерация промптов для image gen                                 ║   │
║  ├── SEO заголовки + теги для Etsy                                   ║   │
║  └── bullets + описания для Amazon                                   ║   │
║                                                                       ║   │
║  Ollama    localhost:11434      нулевая стоимость токенов             ║   │
║  ├── llava / llama3.2-vision   (анализ изображений)                  ║   │
║  └── mistral / qwen            (черновики промптов)                  ║   │
║                                                                       ║   │
║  Claude API  api.anthropic.com  $3/M tokens                          ║   │
║  ├── Amazon A+ content (финальный текст)                             ║   │
║  ├── title 200 chars + bullets                                       ║   │
║  └── Brand Story                                                     ║   │
╚══════════════════════════════════════════════════════════════════════╝
                           │
                           ▼
╔══════════════════════════════════════════════════════════════════════╗
║              LAYER 6 — STORAGE & CDN                                  ║
║                                                                       ║
║  Backblaze B2   $0.006/GB    ← хранение всех изображений             ║
║       │                                                               ║
║  Cloudflare CDN  бесплатный egress из B2                             ║
║       │                                                               ║
║  imgproxy  :8080   on-the-fly ресайз для каждой платформы:           ║
║  ├── Etsy:   2000×2000px                                             ║
║  ├── Amazon: 1000×1000px (белый фон)                                 ║
║  └── TikTok: 9:16 вертикальный                                       ║
║                                                                       ║
║  Qdrant  (self-hosted)  ← векторное хранилище                        ║
║  ├── дедупликация изображений                                        ║
║  └── поиск похожих промптов                                          ║
╚══════════════════════════════════════════════════════════════════════╝
                           │
          ┌────────────────┼────────────────────────┐
          │                │                         │
          ▼                ▼                         ▼
╔══════════════╗  ╔══════════════════╗  ╔═══════════════════════╗
║  ПРОЕКТ 1    ║  ║  ПРОЕКТ 2 + 4    ║  ║  ПРОЕКТ 3             ║
║  КОНТЕНТ     ║  ║  ETSY +          ║  ║  AMAZON               ║
║  ФЕРМА       ║  ║  TIKTOK SHOP     ║  ║                       ║
╠══════════════╣  ╠══════════════════╣  ╠═══════════════════════╣
║              ║  ║                  ║  ║                       ║
║  → B2        ║  ║ Dynamic Mockups  ║  ║ Photoroom API         ║
║  → Qdrant    ║  ║ (5000+ шаблонов) ║  ║ (белый фон)           ║
║  → Langfuse  ║  ║      ↓           ║  ║      ↓                ║
║  → Buzz      ║  ║ Gelato API       ║  ║ Ideogram API          ║
║    #content  ║  ║ (POD + отгрузка) ║  ║ (текст на картинке)   ║
║              ║  ║      ↓           ║  ║      ↓                ║
║              ║  ║ Groq → SEO       ║  ║ Claude API            ║
║              ║  ║ (13 тегов Etsy)  ║  ║ (A+ content)          ║
║              ║  ║      ↓           ║  ║      ↓                ║
║              ║  ║ Etsy API v3      ║  ║ Amazon SP-API         ║
║              ║  ║ TikTok Shop API  ║  ║ (не MWS!)             ║
║              ║  ║      ↓           ║  ║      ↓                ║
║              ║  ║ Nembol           ║  ║ Feedvisor /           ║
║              ║  ║ (синк платформ)  ║  ║ SellerAI              ║
╚══════════════╝  ╚══════════════════╝  ╚═══════════════════════╝
          │                │                         │
          └────────────────┼─────────────────────────┘
                           │
                           ▼
╔══════════════════════════════════════════════════════════════════════╗
║              LAYER 7 — OBSERVABILITY                                  ║
║                                                                       ║
║  Langfuse  (self-hosted)                                             ║
║  ├── трекинг каждого запроса: промпт → модель → результат            ║
║  ├── A/B тест промптов                                               ║
║  └── дашборд: какие промпты дают лучшие CTR на Etsy/Amazon          ║
║                                                                       ║
║  Helicone  oai.helicone.ai  (proxy перед OpenAI API)                ║
║  ├── автоматический трекинг токенов и стоимости                     ║
║  └── openai_api_base: https://oai.helicone.ai                       ║
║                                                                       ║
║  Buzz #alerts  (реалтайм нотификации агентов)                       ║
║  ├── бюджет превышен → стоп                                          ║
║  └── API ошибка → retry / fallback провайдер                         ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Компоненты — детали

### Buzz (Communication Layer)

**Роль:** единое рабочее пространство где люди и AI-агенты работают вместе.

| Канал | Кто пишет | Что |
|-------|-----------|-----|
| `#content-farm` | content-agent | "сгенерировано 47 img, потрачено $0.47" |
| `#etsy` | etsy-agent | "опубликован листинг #1234, views: 0→12" |
| `#amazon` | amazon-agent | "листинг ASIN B0X... создан, статус: active" |
| `#tiktok` | tiktok-agent | "видео загружено, 0 продаж пока" |
| `#dev` | Claude Code | коммиты, PR, code review |
| `#alerts` | все агенты | ошибки, превышение бюджета |

**Протокол:** Nostr — каждый агент имеет криптографический ключ, все действия подписаны и неизменяемы.

---

### Claudexor (Orchestration Layer)

**Роль:** управляет агентами, квотами и бюджетами.

```
claudexor best-of --providers fal,kie,together \
  --prompt "luxury product photo" \
  --max-usd 0.10
→ запускает на 3 провайдерах параллельно
→ возвращает лучший результат
→ списывает стоимость из бюджета
```

**Quota rotation:**
```
FAL.ai rate limit → автопереключение на Together AI
Together AI limit → Stability AI
Бюджет дня $X исчерпан → стоп + алерт в Buzz #alerts
```

**MCP сервер:** `claudexor mcp serve` → подключить к Claude Code сессии для best-of-N при разработке.

---

### darkHUB Node (Image Generation)

**Файл:** `node.py` — единая точка генерации, два бэкенда.

```python
# Логика роутинга
if openai_api_base.strip():
    → _generate_openai()   # Bridge B: любой OpenAI-совместимый
else:
    → kie.ai pipeline      # Bridge A: async poll
```

**Входы:** prompt, model, aspect_ratio, seed, num_images, reference_image_1..5, openai_api_base, openai_model, openai_quality, openai_style, api_key

**Выходы:** images (tensor), task_id, status, image_urls_json, task_json, summary

---

### Четыре бизнес-проекта

```
ПРОЕКТ 1: КОНТЕНТ ФЕРМА
────────────────────────
CSV/расписание → Groq промпт → BullMQ очередь
→ darkHUB Node × N параллельно
→ Qdrant дедуп → B2 хранение → Langfuse трекинг
Цена: ~$40-80/мес при 1000 img/день

ПРОЕКТ 2: ETSY (Print-on-Demand)
──────────────────────────────────
изображение → Dynamic Mockups (мокап на продукте)
→ Gelato (POD фулфилмент + прямая интеграция Etsy)
→ Groq (13 SEO тегов + заголовок)
→ Etsy API v3 (авто-публикация)
→ Closo/Nembol (мониторинг позиций)
Модель: листинг за ~2 мин без ручного труда

ПРОЕКТ 3: AMAZON
──────────────────
изображение → Photoroom (белый фон, обязателен)
→ Ideogram (инфографика с текстом характеристик)
→ Claude API (title 200 chars + bullets + A+ content)
→ Amazon SP-API (createListing)
→ Feedvisor/SellerAI (репрайсинг + мониторинг)
ВАЖНО: MWS мёртв с 31.03.2024 — только SP-API

ПРОЕКТ 4: TIKTOK SHOP
───────────────────────
170M покупателей, 0 комиссии за рекламу для старта
изображение → AI видео (WAN/Kling/Runway)
→ shoppable video (кнопка покупки прямо в видео)
→ TikTok Shop API (листинг продукта)
→ Gelato (тот же POD фулфилмент что Etsy)
→ Buzz #tiktok (мониторинг продаж)
Стек: почти идентичен Etsy, минимум новой работы
```

---

## Мосты между слоями

| Откуда | Куда | Протокол | Мост |
|--------|------|---------|------|
| Zen Browser | ComfyUI | HTTP/WS localhost:8188 | — |
| Zen Browser | Buzz | HTTP localhost:3000 | — |
| Buzz | Claudexor | MCP / CLI | `claudexor mcp serve` |
| Claudexor | darkHUB Node | ComfyUI API POST /prompt | HTTP |
| n8n | darkHUB Node | ComfyUI API | HTTP POST |
| n8n | Groq | REST | Bearer token |
| darkHUB Node | kie.ai | REST async poll | Bridge A |
| darkHUB Node | FAL/Together/OpenAI | REST sync | Bridge B |
| darkHUB Node | Helicone | REST proxy | oai.helicone.ai |
| результат | B2 | S3-compatible API | boto3 |
| результат | Qdrant | gRPC / REST | qdrant-client |
| результат | Langfuse | REST webhook | task_json |
| B2 | Cloudflare CDN | origin pull | автоматически |
| изображение | Dynamic Mockups | REST | Bearer token |
| изображение | Photoroom | REST | Bearer token |
| мокап | Gelato | REST | Bearer token |
| Gelato | Etsy | прямая интеграция | OAuth2 |
| Gelato | TikTok Shop | прямая интеграция | OAuth2 |
| текст | Amazon SP-API | LWA OAuth2 | SP-API SDK |
| все агенты | Buzz channels | Nostr protocol | WebSocket |

---

## Переменные окружения

```bash
# Image generation
KIE_API_KEY=           # kie.ai (Seedream)
OPENAI_API_KEY=        # OpenAI / Helicone proxy
FAL_KEY=               # FAL.ai
TOGETHER_API_KEY=      # Together AI
STABILITY_API_KEY=     # Stability AI

# LLM
GROQ_API_KEY=          # Groq (промпты, SEO)
ANTHROPIC_API_KEY=     # Claude API (A+ content)

# E-commerce
ETSY_API_KEY=          # Etsy API v3
AMAZON_SP_API_KEY=     # Amazon SP-API
TIKTOK_SHOP_KEY=       # TikTok Shop API
GELATO_API_KEY=        # Gelato POD
PHOTOROOM_API_KEY=     # Photoroom (белый фон)
IDEOGRAM_API_KEY=      # Ideogram (текст на картинке)
DYNAMIC_MOCKUPS_KEY=   # Dynamic Mockups

# Infrastructure
BACKBLAZE_KEY_ID=      # B2 storage
BACKBLAZE_APP_KEY=     # B2 storage
QDRANT_URL=            # Qdrant vector DB
LANGFUSE_SECRET_KEY=   # Langfuse observability
HELICONE_API_KEY=      # Helicone proxy
REDIS_URL=             # BullMQ queue
```

---

## Приоритет внедрения

| # | Сервис | Проект | Время | Цена/мес |
|---|--------|--------|-------|----------|
| 1 | **Groq** | все | 5 мин | $0 |
| 2 | **Ollama** | контент-ферма | 15 мин | $0 |
| 3 | **FAL.ai** | контент-ферма | 5 мин | по факту |
| 4 | **Buzz** | все (workspace) | 30 мин | $0 |
| 5 | **Helicone** | все (мониторинг) | 10 мин | $0 |
| 6 | **n8n** | автоматизация | 1 час | $0-20 |
| 7 | **BullMQ+Redis** | контент-ферма | 1 час | $5-10 |
| 8 | **Backblaze B2** | хранение | 30 мин | $6/TB |
| 9 | **Qdrant** | дедупликация | 30 мин | $0 |
| 10 | **Dynamic Mockups** | Etsy/TikTok | 30 мин | trial |
| 11 | **Gelato** | Etsy/TikTok | 1 час | $0 |
| 12 | **Claudexor** | dev+квоты | 1 час | $0 |
| 13 | **TikTok Shop** | новый проект | 2 часа | $0 |
| 14 | **FAL LoRA** | своя модель | 3 часа | разово |
| 15 | **Langfuse** | полный observ | 2 часа | $0 |
