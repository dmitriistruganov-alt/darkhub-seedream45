# SASHA SYSTEM CHECKUP
# Снимок системы: 2026-07-22 22:30 | Восстановление: 2026-07-23

Источник: Claude App 2 (локальная сессия на машине Димы).
Этот файл — точная копия состояния всех систем Agent Office.

---

## ИТОГ: СИСТЕМА ЗДОРОВА ✅

Целевое состояние: **22.07.2026 22:30** — достигнуто.
CPU: **34%** (лимит <70%) ✅

---

## БЛОК 1 — Git / Облако

| Параметр | Значение |
|----------|---------|
| Репо | `dmitriistruganov-alt/agent-office-backup` |
| Ветка | `audit/full-digital-human` |
| HEAD коммит | `f04ba6b auto-backup 2026-07-22 22:30` |
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
Бот молчит по дизайну. НЕ снимать без команды Димы.

### LLM движки
- **Чаттер**: Grok (xai)
- **free_brain**: Groq / Cerebras (работают только с Aeza IP)

---

## БЛОК 3 — Локальная машина (Windows, C:\Users\18186)

### PM2 процессы: 22/22 online ✅

| Процесс | Статус до | Статус после |
|---------|-----------|-------------|
| daily-monitor | stopped ❌ | online ✅ |
| free-llm-sync | stopped ❌ | online ✅ |
| git-backup (30 мин цикл) | stopped ❌ | online ✅ |
| Остальные 19 | online ✅ | online ✅ |

### Открытые порты

| Сервис | Порт | Статус |
|--------|------|--------|
| Qdrant | 6333 | ✅ OPEN |
| Ollama | 11434 | ✅ OPEN |
| brain-мост | 9999 | ✅ OPEN |
| token-compressor | 9988 | ✅ OPEN |
| Hermes | 8642 | ✅ OPEN |
| command-center | 8770 | ✅ OPEN |
| AdsPower API | 50325 | ⚠️ ждёт GUI-логин (IG/Threads VDS) |

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

## БЛОК 5 — Brain-мост (:9999)

**15 роутов:**
```
agent_office · codex · hermes · free_brain · grok · gemini
flowise · pollinations · cloudflare · hy3 · ...
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

**Примечание:** mythos — устарел, не восстанавливать.

### Obsidian
- Путь: `obsidian_vault/` (в .gitignore — не в git)
- Сессионный отчёт: `Сессии/2026-07-22-Восстановление-полное.md`
- 1373 основных заметок + отдельный раздел Fans (1296)

---

## БЛОК 7 — MCP серверы (18 шт)

Все 18 серверов MCP подключены и работают (список в agent_office JSON на машине).

---

## БЛОК 8 — Температура / CPU

| Параметр | Значение | Лимит |
|----------|---------|-------|
| CPU | 34% | <70% ✅ |
| Перегрев | Нет | — |
| Фикс | Temporal OFF + software throttle | Держит ✅ |

---

## НЕ-БЛОКЕРЫ (не восстанавливать программно)

| Проблема | Тип | Действие |
|---------|-----|----------|
| Железо-перегрев | Физика (кулеры/термопаста/БП) | Руками |
| AdsPower :50325 | Ждёт GUI-логин | Открыть AdsPower вручную |
| CHATTER_DISABLED | Дизайн | Снимать только по команде |

---

## Репозитории системы Agent Office

| Репо | Ветка | Назначение |
|------|-------|-----------|
| `agent-office-backup` | `audit/full-digital-human` | Главная система |
| `darkhub-seedream45` | `claude/codex-openai-api-models-x11l8d` | ComfyUI darkHUB нод |
| `runpod-gpu-watcher-v2` | main | GPU мониторинг |
| `flux-stack` | main | FLUX модели |
| `sashamoon` | main | — |

---

## Как читать этот файл в следующей сессии

1. Открой сессию с `agent-office-backup` (ветка `audit/full-digital-human`)
2. Этот файл лежит в `docs/SASHA_SYSTEM_CHECKUP.md` репо `darkhub-seedream45`
3. Полный отчёт в Obsidian: `Сессии/2026-07-22-Восстановление-полное.md`
4. Claude Memory: `recovery-verified-jul22.md`

---

*Составлено: 2026-07-23 | Claude App 2 (локальная) + Claude Code (облако)*
