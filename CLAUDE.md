# darkHUB — Контекст проекта

Этот файл читается Claude автоматически в начале каждой сессии.

---

## Владелец

- Email: dmitriistruganov@gmail.com
- GitHub: dmitriistruganov-alt

---

## Три бизнес-проекта

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

## Переменные окружения

```bash
KIE_API_KEY=       # kie.ai (Seedream)
OPENAI_API_KEY=    # OpenAI или любой совместимый провайдер
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
