# darkHUB — Контекст проекта

Этот файл читается Claude автоматически в начале каждой сессии.

---

## Владелец

- Email: dmitriistruganov@gmail.com
- GitHub: dmitriistruganov-alt

---

## Четыре бизнес-проекта

### 1. Контент-ферма
Автоматическая массовая генерация AI-изображений.
- Генерация сотен картинок в день по расписанию/CSV
- Промпты через Groq/Ollama (бесплатно)
- Изображения через FAL.ai / kie.ai / Stability AI ($0.003–0.01/img)
- Хранение в Backblaze B2 + Cloudflare CDN
- Дедупликация через Qdrant (векторная БД)
- Трекинг качества промптов через Langfuse
- Оркестрация через n8n + BullMQ/Redis

### 2. Etsy — Print-on-Demand
Изображения из контент-фермы → Etsy листинги автоматически.
- Мокапы: Dynamic Mockups API (5000+ шаблонов)
- Фулфилмент: Gelato API (печать + отгрузка, прямая интеграция с Etsy)
- SEO: Groq генерирует заголовок + 13 тегов под алгоритм Etsy
- Публикация: Etsy API v3 (авто-листинг)
- Мониторинг позиций: Closo / Nembol

### 3. Amazon — Product Listings
Изображения → листинги Amazon с A+ контентом автоматически.
- Фон: Photoroom API (белый фон — обязателен для Amazon)
- Инфографика: Ideogram API (текст на картинке, характеристики)
- Контент: Claude API генерирует title (200 chars) + bullets + A+ content
- Публикация: Amazon SP-API (MWS мёртв с 31.03.2024 — только SP-API!)
- Мониторинг: Feedvisor / SellerAI

### 4. TikTok Shop — Social Commerce
Изображения + короткие видео → TikTok Shop листинги автоматически.
- Видео: ComfyUI AnimateDiff / Kling AI для product videos
- Контент: Claude API генерирует описание + хэштеги под TikTok алгоритм
- Фулфилмент: Gelato API (тот же, что Etsy — PrintOnDemand)
- Публикация: TikTok Shop API (Content API + Product API)
- Быстрее viral loop: контент-ферма → TikTok → продажи за часы, не дни

---

## Текущий репозиторий

**darkhub-seedream45** — ComfyUI custom node для генерации изображений.

### Что реализовано
- `node.py` — основной нод `DarkHubFreepikStudio`
- Два бэкенда: kie.ai (Seedream 4.5/5.0) и любой OpenAI-совместимый API
- Поля: `openai_api_base` + `openai_model` — вставь любой провайдер без изменения кода
- 5 reference images для редактирования
- `ARCHITECTURE.md` — полная архитектура системы с диаграммами

### Модели kie.ai
- `seedream/4.5-edit` — редактирование изображений
- `seedream/4.5` — text-to-image
- `seedream/5.0-lite` — облегчённая версия

### OpenAI-совместимые провайдеры (вставить в openai_api_base)
| Провайдер | URL | Модель |
|-----------|-----|--------|
| OpenAI | `https://api.openai.com` | `dall-e-3` / `gpt-image-1` |
| FAL.ai | `https://fal.run` | `fal-ai/flux/schnell` |
| Together AI | `https://api.together.xyz` | FLUX, SDXL |
| Replicate | `https://api.replicate.com` | любая |
| Ollama local | `http://localhost:11434` | любая локальная |

---

## Используемый браузер

**Zen Browser** — минималистичный, приватный, Arc-подобный.
- Используется как UI layer для всей системы
- Вкладки: ComfyUI (:8188) + kie.ai dashboard + provider UIs
- Split View для мониторинга параллельных процессов

---

## Ключевые инструменты оркестрации

### Buzz (Jack Dorsey / Block)
- Открытый workspace: Slack + GitHub в одном, протокол Nostr
- AI агенты — полноправные члены команды (не боты, а коллеги)
- Каналы: #content-farm #etsy #amazon #tiktok #dev #alerts #budget
- Apache 2.0, self-hosted: `github.com/buzzapp/buzz`

### Claudexor (AI Orchestrator)
- Мульти-агентная оркестрация Claude Code / Codex
- Ротация квот между API ключами (не тратим один ключ)
- Best-of-N: запускает промпт на N провайдерах, берёт лучший
- Budget caps: `--max-usd 5` — жёсткий лимит расходов за сессию
- MCP server mode — подключается к любому MCP-совместимому клиенту
- `github.com/razzant/claudexor`

---

## Переменные окружения

```bash
KIE_API_KEY=           # kie.ai (Seedream)
OPENAI_API_KEY=        # OpenAI или любой совместимый провайдер
FAL_KEY=               # FAL.ai (FLUX Schnell — самый быстрый)
GROQ_API_KEY=          # Groq (500 tok/s, бесплатно)
ANTHROPIC_API_KEY=     # Claude API (листинги Amazon/TikTok)
LANGFUSE_SECRET_KEY=   # Трекинг качества промптов
HELICONE_API_KEY=      # Прокси для мониторинга токенов/затрат
B2_KEY_ID=             # Backblaze B2
B2_APP_KEY=            # Backblaze B2
ETSY_API_KEY=          # Etsy API v3
TIKTOK_SHOP_API_KEY=   # TikTok Shop API
AMAZON_SP_API_KEY=     # Amazon SP-API (не MWS!)
GELATO_API_KEY=        # Gelato (POD фулфилмент)
```

---

## Активная ветка разработки

`claude/codex-openai-api-models-x11l8d`

---

## Важные заметки

- Amazon MWS мёртв с 31.03.2024 — использовать только SP-API
- MidJourney API в 2025 — только enterprise, без публичного доступа
- Для bulk-скидок: Google Batch API даёт 50% off, Stability AI — по договорённости
- Лучшее соотношение цена/скорость: FAL.ai FLUX Schnell ($0.01, <1 сек)
- Дешевейший: Stability AI 3.5 ($0.003/img)
- Текст на изображениях: только Ideogram (90-95% точность)
