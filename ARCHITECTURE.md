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
