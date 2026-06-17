# darkHUB — System Architecture

Единая архитектура: ComfyUI нод для генерации изображений с двойным бэкендом,
доступный через Zen Browser как нативный браузерный слой.

---

## Обзор системы

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                            USER INTERFACE LAYER                              ║
║                                                                              ║
║   ┌────────────────────────────────────────────────────────────────────┐    ║
║   │                        ZEN BROWSER                                  │    ║
║   │                                                                      │    ║
║   │  ┌─────────────┐   ┌──────────────────┐   ┌─────────────────────┐  │    ║
║   │  │ ComfyUI Tab │   │  kie.ai Dashboard│   │  OpenAI/Provider UI │  │    ║
║   │  │ :8188       │   │  api.kie.ai      │   │  platform.openai.com│  │    ║
║   │  └──────┬──────┘   └────────┬─────────┘   └──────────┬──────────┘  │    ║
║   │         │                   │                          │             │    ║
║   │    [Split View]        [Monitoring]              [API Keys]          │    ║
║   └─────────┼───────────────────┼──────────────────────────┼────────────┘    ║
╚═════════════╪═══════════════════╪══════════════════════════╪═════════════════╝
              │ HTTP/WS           │ REST                     │ REST
              │ localhost         │                          │
╔═════════════╪═══════════════════╧══════════════════════════╧═════════════════╗
║             ▼            COMFYUI EXECUTION LAYER                             ║
║   ┌─────────────────────────────────────────────────────────────────────┐   ║
║   │                      ComfyUI  :8188                                  │   ║
║   │                                                                       │   ║
║   │   Workflow Graph                                                      │   ║
║   │   ┌─────────────┐   ┌───────────────────────────────────────────┐   │   ║
║   │   │ Load Image  ├──▶│         darkHUB Seedream 4.5 Studio       │   │   ║
║   │   │ (optional)  │   │         DarkHubFreepikStudio               │   │   ║
║   │   └─────────────┘   │                                            │   │   ║
║   │   ┌─────────────┐   │  inputs:  prompt, model, aspect_ratio,    │   │   ║
║   │   │  Text Input ├──▶│           seed, num_images, api_key,      │   │   ║
║   │   │  (prompt)   │   │           openai_api_base, openai_model   │   │   ║
║   │   └─────────────┘   │                                            │   │   ║
║   │                      │  outputs: images, task_id, status,        │   │   ║
║   │                      │           urls_json, summary              │   │   ║
║   │                      └──────────────────┬────────────────────────┘   │   ║
║   │                                         │                             │   ║
║   │                          ┌──────────────▼───────────────┐            │   ║
║   │                          │  Router: openai_api_base?    │            │   ║
║   │                          └───────┬──────────────┬───────┘            │   ║
║   └───────────────────────────────── │ ─────────────│────────────────────┘   ║
╚══════════════════════════════════════╪══════════════╪═════════════════════════╝
                                       │              │
                        empty          │              │  set
                   ╔══════════╗        │              │       ╔══════════════════╗
                   ║ BRIDGE A ║        ▼              ▼       ║    BRIDGE B      ║
                   ╚══════════╝                               ╚══════════════════╝
╔══════════════════════════════════╗      ╔═══════════════════════════════════════╗
║         kie.ai BACKEND           ║      ║     OpenAI-COMPATIBLE BACKEND         ║
║                                  ║      ║                                        ║
║  POST /api/v1/jobs/createTask    ║      ║  POST {base_url}/v1/images/generations║
║        ↓ async                   ║      ║                                        ║
║  GET  /api/v1/jobs/getTaskDetail ║      ║  Providers:                           ║
║       ↓ poll every 3s            ║      ║  • api.openai.com  (DALL-E 3)         ║
║                                  ║      ║  • api.openai.com  (gpt-image-1)      ║
║  Models:                         ║      ║  • api.together.xyz (Flux, SDXL)      ║
║  • seedream/4.5-edit             ║      ║  • fal.run          (any FAL model)   ║
║  • seedream/4.5   (T2I)          ║      ║  • api.replicate.com                  ║
║  • seedream/5.0-lite             ║      ║  • localhost:1234   (self-hosted)      ║
║                                  ║      ║                                        ║
║  Auth: Bearer KIE_API_KEY        ║      ║  Auth: Bearer OPENAI_API_KEY          ║
╚══════════════════════════════════╝      ╚═══════════════════════════════════════╝
```

---

## Компоненты и мосты

### 1. Zen Browser — UI Layer

**Роль:** единая точка входа для всей системы.

| Функция | Детали |
|---------|--------|
| ComfyUI Web UI | открывается на `localhost:8188` в выделенной вкладке |
| Мониторинг API | `api.kie.ai` дашборд + `platform.openai.com` — параллельные вкладки |
| Split View | ComfyUI слева + результаты / логи справа |
| Приватность | без телеметрии — API ключи не утекают через браузер |
| Profiles | отдельный профиль для dev-среды darkHUB |

**Мост Zen → ComfyUI:**
```
Zen Browser
    │  HTTP GET  localhost:8188
    ▼
ComfyUI Web UI (React SPA)
    │  WebSocket  ws://localhost:8188/ws
    ▼
ComfyUI Python backend
    │  Python call
    ▼
DarkHubFreepikStudio.generate()
```

---

### 2. ComfyUI Node — Execution Layer

**Роль:** граф-процессор, связывает UI с API бэкендами.

```
Inputs (from graph)          DarkHubFreepikStudio            Outputs
─────────────────────        ──────────────────────        ──────────────
prompt ──────────────▶ ┌─────────────────────────┐ ──▶ images (tensor)
model  ──────────────▶ │  _tensor_to_b64()        │ ──▶ task_id
aspect_ratio ────────▶ │  _b64_to_tensor()        │ ──▶ status
reference_image_1..5 ▶ │  _url_to_tensor()        │ ──▶ image_urls_json
openai_api_base ─────▶ │  _generate_openai()      │ ──▶ task_json
openai_model ────────▶ │                          │ ──▶ summary
api_key ─────────────▶ └──────────┬───────────────┘
                                   │
                          ┌────────▼─────────┐
                          │  openai_api_base  │
                          │  empty?           │
                          └────┬─────────┬───┘
                               │ yes     │ no
                               ▼         ▼
                          kie.ai    _generate_openai()
                          backend
```

---

### 3. Bridge A — kie.ai (async polling)

**Протокол:** REST + long-poll

```
Node                     kie.ai API
────                     ──────────
POST /api/v1/jobs/createTask
  body: { model, input: { prompt, aspect_ratio, seed, image_urls } }
  ──────────────────────────────────────────────────────────▶
                         { code: 200, data: { taskId: "xyz" } }
  ◀──────────────────────────────────────────────────────────

loop (every 3s, up to timeout):
  GET /api/v1/jobs/getTaskDetail?taskId=xyz
  ──────────────────────────────────────────────────────────▶
                         { data: { status: "COMPLETED",
                                   output: { images: ["url"] } } }
  ◀──────────────────────────────────────────────────────────

GET image_url  ──────────────────────────────────────────▶
               ◀──────────────────────────── binary image data

convert to tensor → return to ComfyUI graph
```

**Env vars:**
```
KIE_API_KEY=<ваш ключ>   # приоритет над полем api_key в ноде
```

---

### 4. Bridge B — OpenAI-Compatible (single request)

**Протокол:** REST, синхронный

```
Node                     Any OpenAI-Compatible Provider
────                     ─────────────────────────────
POST {openai_api_base}/v1/images/generations
  body: {
    model:           openai_model (dall-e-3 / gpt-image-1 / ...)
    prompt:          prompt
    n:               num_images
    size:            OPENAI_SIZE_MAP[aspect_ratio]
    response_format: "b64_json"
    quality:         openai_quality  (если не "auto")
    style:           openai_style    (если задан)
    seed:            seed            (если fixed)
  }
  ──────────────────────────────────────────────────────────▶
                         {
                           data: [
                             { b64_json: "..." },
                             { b64_json: "..." }
                           ]
                         }
  ◀──────────────────────────────────────────────────────────

decode base64 → tensor → return to ComfyUI graph
```

**Env vars:**
```
OPENAI_API_KEY=<ваш ключ>   # или любого совместимого провайдера
```

**Примеры конфигурации:**

| Провайдер | openai_api_base | openai_model |
|-----------|----------------|--------------|
| OpenAI | `https://api.openai.com` | `dall-e-3` |
| OpenAI | `https://api.openai.com` | `gpt-image-1` |
| Together AI | `https://api.together.xyz` | `black-forest-labs/FLUX.1-schnell` |
| FAL.ai | `https://fal.run` | `fal-ai/flux/schnell` |
| Replicate | `https://api.replicate.com` | `stability-ai/sdxl` |
| Ollama (local) | `http://localhost:11434` | `llava` |
| LM Studio | `http://localhost:1234` | `любая локальная` |

---

## Потоки данных

### Поток 1: Text-to-Image (kie.ai)

```
[Zen Browser] ──HTTP──▶ [ComfyUI :8188] ──▶ [Node: prompt+model]
                                                      │
                                          [kie.ai createTask]
                                                      │
                                          [poll getTaskDetail]
                                                      │
                                          [download image URL]
                                                      │
                                          [tensor → ComfyUI graph]
                                                      │
                              [Zen Browser] ◀──HTTP── [ComfyUI result]
```

### Поток 2: Image Editing (kie.ai с reference)

```
[Zen Browser: Load Image] ──▶ [ComfyUI: Load Image Node]
                                          │
                                          ▼ IMAGE tensor
                              [Node: reference_image_1..5]
                                          │
                              [_tensor_to_b64() → data:image/jpeg;base64,...]
                                          │
                              [kie.ai: input.image_urls=[...]]
                                          │
                              [edited image → tensor]
                                          │
                              [Zen Browser: preview result]
```

### Поток 3: OpenAI Provider

```
[Zen Browser] ──▶ [ComfyUI] ──▶ [Node: openai_api_base set]
                                          │
                              [_generate_openai()]
                                          │
                              [POST /v1/images/generations]
                                          │
                              [decode b64_json → tensor]
                                          │
                              [Zen Browser: preview result]
```

---

## Переменные окружения

```bash
# kie.ai backend
KIE_API_KEY=your_kie_ai_key

# OpenAI-compatible providers
OPENAI_API_KEY=your_openai_key

# ComfyUI (опционально)
COMFYUI_PORT=8188
```

---

## Зависимости

```
Python 3.10+
├── torch          — тензоры ComfyUI
├── numpy          — конвертация массивов
├── Pillow (PIL)   — обработка изображений
└── requests       — HTTP клиент для API

ComfyUI (runtime)
└── darkhub-seedream45/   ← этот пакет
    ├── __init__.py        — регистрация нода
    └── node.py            — вся логика

Browser
└── Zen Browser            — UI layer
    ├── Tab: localhost:8188 (ComfyUI)
    ├── Tab: api.kie.ai     (мониторинг)
    └── Tab: provider UI    (ключи / лимиты)
```

---

## Быстрый старт

```bash
# 1. Клонировать в custom_nodes ComfyUI
cd ComfyUI/custom_nodes
git clone https://github.com/dmitriistruganov-alt/darkhub-seedream45

# 2. Задать API ключи
export KIE_API_KEY=your_key_here
# или для OpenAI-совместимых:
export OPENAI_API_KEY=your_key_here

# 3. Запустить ComfyUI
cd ComfyUI && python main.py

# 4. Открыть в Zen Browser
# New Tab → localhost:8188
# Добавить Split View с api.kie.ai или platform.openai.com
```

---

## Расширение системы

Добавить новый провайдер (любой OpenAI-совместимый API):

1. Вставить ноду `darkHUB Seedream 4.5 Studio` в граф
2. Заполнить `openai_api_base` → URL провайдера
3. Заполнить `openai_model` → название модели
4. Задать `api_key` или env var
5. Готово — никаких изменений в коде не нужно

Добавить kie.ai модель (нужен PR):
- Добавить строку в `MODELS` и `MODEL_MAP` в `node.py`

---

## Экосистема сервисов — максимальная производительность

```
╔════════════════════════════════════════════════════════════════════════╗
║               ПОЛНАЯ КАРТА СЕРВИСОВ СИСТЕМЫ darkHUB                   ║
╠══════════════════╦═════════════════════╦══════════════════════════════╣
║  УСКОРЕНИЕ       ║  ЭКОНОМИЯ ТОКЕНОВ   ║  АВТОМАТИЗАЦИЯ               ║
║  ГЕНЕРАЦИИ       ║  И КЭШИРОВАНИЕ      ║  И ОРКЕСТРАЦИЯ               ║
╚══════════════════╩═════════════════════╩══════════════════════════════╝
```

### Блок 1 — Ускорение инференса (Bridge: Inference Speed)

```
darkHUB Node
    │
    ├── FAL.ai          fal.run              ← самый быстрый serverless GPU
    │   openai_api_base: https://fal.run     latency: ~1-3s / image
    │   Модели: FLUX.1-schnell, SD3, Kling
    │
    ├── Together AI     api.together.xyz     ← дешевле OpenAI в 5-10x
    │   Модели: FLUX, SDXL, Playground v3
    │
    ├── Replicate       api.replicate.com    ← холодный старт, но 1000+ моделей
    │   Модели: любые huggingface модели
    │
    ├── Fireworks AI    api.fireworks.ai     ← быстрый + дешёвый
    │   Модели: SDXL, playground
    │
    └── Modal.com       (serverless GPU)     ← запуск своих моделей
        Деплой любого diffusion model без инфраструктуры
```

### Блок 2 — Экономия токенов и кэширование (Bridge: Token Economy)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    СТРАТЕГИИ ЭКОНОМИИ ТОКЕНОВ                        │
│                                                                       │
│  1. Prompt Caching (Claude API)                                      │
│     ─────────────────────────                                        │
│     cache_control: {"type": "ephemeral"}                            │
│     Экономия: до 90% стоимости на повторных запросах                │
│     Работает с: системными промптами, few-shot примерами            │
│                                                                       │
│  2. Ollama (локальный)    localhost:11434                            │
│     ─────────────────────────────────                                │
│     Нулевая стоимость токенов для:                                  │
│     • генерации промптов                                             │
│     • классификации изображений                                      │
│     • авто-теггинга результатов                                      │
│     Модели: llava, llama3.2-vision, mistral                         │
│                                                                       │
│  3. LM Studio          localhost:1234                                │
│     ──────────────────────────────                                   │
│     Drag-drop загрузка GGUF моделей                                 │
│     OpenAI-compatible сервер из коробки                             │
│     Лучше для: Qwen2-VL (vision + text)                             │
│                                                                       │
│  4. vLLM (self-hosted)   localhost:8000                              │
│     ──────────────────────────────────                               │
│     Максимальная скорость: PagedAttention, continuous batching      │
│     Для: высоконагруженных автоматизаций                            │
│                                                                       │
│  5. Groq               api.groq.com                                 │
│     ────────────────────────────────                                 │
│     LPU-чипы: 500-800 tokens/sec                                    │
│     Лучший для: быстрой генерации промптов к изображениям           │
│     Бесплатный tier: 30 req/min                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Блок 3 — Автоматизация и оркестрация (Bridge: Automation)

```
┌──────────────┐     ┌──────────────────────────────────────────────┐
│  n8n         │     │  AUTOMATION FLOW EXAMPLE                     │
│  (self-host) │     │                                              │
│  :5678       │     │  Trigger: новый текст / расписание           │
│              │     │      ↓                                        │
│  Webhook ────┼────▶│  Groq: сгенерировать промпт из темы          │
│  Schedule    │     │      ↓                                        │
│  Gmail/Slack │     │  darkHUB Node: сгенерировать изображение     │
└──────────────┘     │      ↓                                        │
                     │  Webhook: отправить результат в Slack/TG     │
┌──────────────┐     └──────────────────────────────────────────────┘
│  ComfyUI API │
│  (HTTP)      │     ┌──────────────────────────────────────────────┐
│              │     │  PROGRAMMATIC COMFYUI (без UI)               │
│  POST        │     │                                              │
│  /prompt     │     │  import requests                             │
│              │     │  requests.post("localhost:8188/prompt",      │
│  GET         │     │    json={"prompt": workflow_dict})           │
│  /history    │     │                                              │
└──────────────┘     │  Использовать для: batch processing,         │
                     │  scheduled generation, CI/CD pipelines       │
                     └──────────────────────────────────────────────┘
```

### Блок 4 — Самообучение и файнтюнинг (Bridge: Self-Learning)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PIPELINE САМООБУЧЕНИЯ                             │
│                                                                       │
│  Шаг 1: Сбор данных                                                 │
│  ─────────────────                                                   │
│  darkHUB генерирует → task_json содержит метаданные                 │
│  Сохранять: prompt + seed + model + результат (хорошо/плохо)        │
│                                                                       │
│  Шаг 2: Датасет                                                      │
│  ─────────────                                                       │
│  Hugging Face Hub  huggingface.co                                   │
│  • datasets push: prompt-результат пары                             │
│  • private repo с вашими лучшими промптами                          │
│  • версионирование датасета                                         │
│                                                                       │
│  Шаг 3: Файнтюнинг                                                   │
│  ─────────────────                                                   │
│  Together AI Fine-tuning API                                        │
│  POST api.together.xyz/v1/fine-tunes                                │
│  Модели: поддерживает LoRA на FLUX и SDXL                           │
│                                                                       │
│  Replicate Fine-tuning                                              │
│  replicate.com/training  ← drag-drop FLUX LoRA обучение            │
│                                                                       │
│  FAL.ai Training                                                    │
│  fal.run/models/fal-ai/flux-lora-fast-training                     │
│  ~20 мин / LoRA на ваши изображения                                 │
│                                                                       │
│  Шаг 4: Интеграция обученной модели                                 │
│  ──────────────────────────────────                                 │
│  openai_api_base: https://fal.run                                   │
│  openai_model:    ваш-username/your-lora-model                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Блок 5 — Мониторинг и наблюдаемость (Bridge: Observability)

```
darkHUB Node
    │  summary + task_json outputs
    ▼
┌──────────────────────────────────────────────────────────────┐
│  Langfuse (self-hosted или cloud)                             │
│  • трекинг каждого запроса: промпт, модель, стоимость         │
│  • A/B тест промптов                                          │
│  • дашборд качества генерации                                 │
│  Интеграция: отправлять task_json через webhook               │
│                                                               │
│  Helicone     helicone.ai                                     │
│  • proxy перед OpenAI API (прозрачный)                        │
│  • автоматический трекинг токенов и стоимости                │
│  openai_api_base: https://oai.helicone.ai                    │
│  + Helicone-Auth header                                       │
│                                                               │
│  Weights & Biases   wandb.ai                                 │
│  • логирование изображений + промптов                        │
│  • сравнение моделей визуально                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Полная карта мостов

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                         ЕДИНАЯ СИСТЕМА darkHUB                            ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  ZEN BROWSER ──────────────────────────────────────────────────────┐     ║
║      │                                                               │     ║
║      │ localhost:8188                                                │     ║
║      ▼                                                               │     ║
║  COMFYUI ──── darkHUB Node                                          │     ║
║                    │                                                 │     ║
║         ┌──────────┼──────────────────────────┐                    │     ║
║         │          │                           │                    │     ║
║         ▼          ▼                           ▼                    │     ║
║     kie.ai    FAL / Together            Ollama (local)             │     ║
║    (Seedream)  / OpenAI / etc          LM Studio (local)          │     ║
║         │          │                      (промпт-генерация)      │     ║
║         └──────────┘                           │                    │     ║
║              │                                 │                    │     ║
║              ▼                                 ▼                    │     ║
║         Результат ◀──────── Groq (быстрый LLM для промптов) ◀─────┘     ║
║              │                                                            ║
║              ├──▶ Hugging Face Hub (датасет / LoRA модели)               ║
║              ├──▶ n8n / автоматизация (webhook триггеры)                 ║
║              ├──▶ Helicone (мониторинг токенов и стоимости)              ║
║              └──▶ Langfuse (трекинг качества генерации)                  ║
║                                                                            ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Приоритетный план внедрения

| Приоритет | Сервис | Цель | Сложность |
|-----------|--------|------|-----------|
| 🔴 1 | **Ollama** (localhost) | бесплатная генерация промптов | 15 мин |
| 🔴 2 | **Groq** | мгновенная генерация промптов | 5 мин |
| 🟡 3 | **FAL.ai** | самая быстрая генерация картинок | 5 мин |
| 🟡 4 | **Helicone** | мониторинг стоимости токенов | 10 мин |
| 🟢 5 | **n8n** | автоматизация batch-генерации | 1 час |
| 🟢 6 | **Hugging Face** | сохранение датасетов | 30 мин |
| 🔵 7 | **FAL LoRA training** | своя стилевая модель | 2-3 часа |
| 🔵 8 | **Langfuse** | полный observability | 2 часа |
