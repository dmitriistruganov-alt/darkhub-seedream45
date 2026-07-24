"""
telegram_bot.py — Telegram бот для управления Agent Office с телефона.
PM2: pm2 start fixes/telegram_bot.py --name tg-agent-bot --interpreter python

Переменные окружения:
  TELEGRAM_BOT_TOKEN = токен от @BotFather
  TELEGRAM_ALLOWED_IDS = 123456789,987654321  (ваши Telegram user ID)
  BRAIN_PORT = 9999  (порт brain_server_v2)

Команды:
  /status    — полный статус системы
  /brain текст — спросить у свободного LLM
  /dead      — список мёртвых моделей
  /revive модель — оживить модель
  /code код  — code review
  /pipeline шаг1|шаг2 — запустить pipeline
  /pm2       — список PM2 процессов
  /help      — список команд
"""
import os, sys, json, time, logging, threading, requests
from pathlib import Path

# Load .env from multiple locations (agent_office/.env, VPS, etc.)
_HERE = Path(__file__).resolve().parent
for _env in [
    Path.home() / "agent_office" / ".env",
    Path("/opt/sasha-core/.env"),
    _HERE.parent / ".env",
    _HERE / ".env",
    Path(".env"),
]:
    if _env.exists():
        try:
            from dotenv import load_dotenv as _ld; _ld(str(_env))
        except ImportError:
            # Manual fallback if python-dotenv not installed
            with open(_env, encoding="utf-8", errors="ignore") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _k, _, _v = _line.partition("=")
                        if _k.strip() and _k.strip() not in os.environ:
                            os.environ[_k.strip()] = _v.strip().strip('"').strip("'")
        break

logging.basicConfig(level=logging.INFO, format='%(asctime)s [tg] %(message)s')
log = logging.getLogger("tg_bot")

TOKEN       = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED_IDS = {int(x) for x in os.environ.get("TELEGRAM_ALLOWED_IDS", "").split(",") if x.strip().isdigit()}
BRAIN       = f"http://localhost:{os.environ.get('BRAIN_PORT', 9999)}"
API_BASE    = f"https://api.telegram.org/bot{TOKEN}"

_offset = 0


def _tg(method: str, **kw) -> dict:
    try:
        r = requests.post(f"{API_BASE}/{method}", json=kw, timeout=30)
        return r.json()
    except Exception as e:
        log.error(f"TG error {method}: {e}")
        return {}


def send(chat_id: int, text: str, parse_mode: str = "HTML"):
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            _tg("sendMessage", chat_id=chat_id, text=text[i:i+4000], parse_mode=parse_mode)
            time.sleep(0.3)
    else:
        _tg("sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode)


def brain_call(route: str, **kw) -> dict:
    try:
        r = requests.post(f"{BRAIN}/{route}", json=kw, timeout=60)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def handle_status(chat_id: int):
    res = brain_call("status")
    if not res.get("ok"):
        send(chat_id, f"❌ Brain offline: {res.get('error', '?')}")
        return
    c = res.get("checks", {})
    lines = [f"<b>🔍 Статус системы</b>  {res.get('ts', '')}"]
    for key, val in c.items():
        if isinstance(val, dict):
            st = val.get("status", "?")
            icon = "✅" if st == "alive" else "❌"
            extra = ""
            if "collections" in val:
                extra = f" ({val['collections']} collections)"
            elif "models" in val:
                extra = f" ({val['models']} models)"
            elif "flows" in val:
                extra = f" ({val['flows']} flows)"
            lines.append(f"{icon} {key}: {st}{extra}")
        elif isinstance(val, list):
            if val:
                lines.append(f"☠️ dead_models: {', '.join(val)}")
        elif isinstance(val, int):
            lines.append(f"📊 {key}: {val}")
        else:
            icon = "✅" if val == "alive" else "❌"
            lines.append(f"{icon} {key}: {val}")
    send(chat_id, "\n".join(lines))


def handle_brain(chat_id: int, prompt: str):
    send(chat_id, "⏳ Думаю...")
    res = brain_call("free_brain", prompt=prompt)
    if res.get("ok"):
        model = res.get("model", "?")
        text  = res.get("text", "")
        send(chat_id, f"<b>🧠 [{model}]</b>\n{text[:3800]}")
    else:
        send(chat_id, f"❌ {res.get('error', 'Ошибка')}\nПробовали: {res.get('tried', [])}")


def handle_dead(chat_id: int):
    try:
        r = requests.get(f"{BRAIN}/dead", timeout=5)
        dead = r.json().get("dead", [])
        if dead:
            send(chat_id, f"☠️ Мёртвые модели ({len(dead)}):\n" + "\n".join(f"• {d}" for d in dead))
        else:
            send(chat_id, "✅ Все модели живые")
    except Exception as e:
        send(chat_id, f"❌ Ошибка: {e}")


def handle_revive(chat_id: int, model: str):
    try:
        r = requests.get(f"{BRAIN}/revive/{model}", timeout=5)
        if r.ok:
            send(chat_id, f"✅ Оживил: {model}")
        else:
            send(chat_id, f"❌ {r.text[:200]}")
    except Exception as e:
        send(chat_id, f"❌ {e}")


def handle_code(chat_id: int, code: str):
    send(chat_id, "⏳ Анализирую код...")
    res = brain_call("code_review", code=code, lang="python")
    if res.get("ok"):
        send(chat_id, f"<b>📋 Code Review</b>\n{res.get('text', '')[:3800]}")
    else:
        send(chat_id, f"❌ {res.get('error', 'Ошибка')}")


def handle_pipeline(chat_id: int, steps_str: str):
    steps = [s.strip() for s in steps_str.split("|") if s.strip()]
    if not steps:
        send(chat_id, "❌ Формат: /pipeline шаг1|шаг2|шаг3")
        return
    send(chat_id, f"⏳ Pipeline из {len(steps)} шагов...")
    res = brain_call("pipeline", steps=steps)
    if res.get("ok"):
        send(chat_id, f"<b>✅ Pipeline завершён</b>\n{res.get('final', '')[:3800]}")
    else:
        send(chat_id, f"❌ {res.get('error', 'Ошибка')}")


def handle_pm2(chat_id: int):
    import subprocess
    try:
        r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=15)
        procs = json.loads(r.stdout)
        lines = ["<b>📦 PM2 процессы</b>"]
        for p in procs:
            st = p["pm2_env"]["status"]
            icon = "✅" if st == "online" else "❌"
            lines.append(f"{icon} {p['name']} ({st})")
        send(chat_id, "\n".join(lines))
    except Exception as e:
        send(chat_id, f"❌ PM2 ошибка: {e}")


def handle_help(chat_id: int):
    send(chat_id, """<b>🤖 Agent Office Bot</b>

/status — статус всей системы
/brain &lt;вопрос&gt; — спросить у LLM
/code &lt;код&gt; — ревью кода
/pipeline шаг1|шаг2 — цепочка промптов
/dead — мёртвые модели
/revive &lt;модель&gt; — оживить модель
/pm2 — статус PM2 процессов
/help — эта справка

<i>Пример: /brain напиши промпт для генерации портрета</i>""")


def dispatch(chat_id: int, user_id: int, text: str):
    if ALLOWED_IDS and user_id not in ALLOWED_IDS:
        send(chat_id, "⛔ Нет доступа")
        return

    text = text.strip()
    if text.startswith("/status"):
        handle_status(chat_id)
    elif text.startswith("/brain "):
        handle_brain(chat_id, text[7:].strip())
    elif text.startswith("/brain"):
        send(chat_id, "Используй: /brain &lt;вопрос&gt;")
    elif text.startswith("/dead"):
        handle_dead(chat_id)
    elif text.startswith("/revive "):
        handle_revive(chat_id, text[8:].strip())
    elif text.startswith("/code "):
        handle_code(chat_id, text[6:].strip())
    elif text.startswith("/pipeline "):
        handle_pipeline(chat_id, text[10:].strip())
    elif text.startswith("/pm2"):
        handle_pm2(chat_id)
    elif text.startswith("/help") or text == "/start":
        handle_help(chat_id)
    else:
        # Treat non-command messages as brain prompts
        if not text.startswith("/"):
            handle_brain(chat_id, text)
        else:
            send(chat_id, "Неизвестная команда. /help — список команд")


def poll():
    global _offset
    log.info(f"Telegram bot запущен | allowed_ids={ALLOWED_IDS or 'все'}")
    while True:
        try:
            r = requests.get(
                f"{API_BASE}/getUpdates",
                params={"offset": _offset, "timeout": 30, "allowed_updates": ["message"]},
                timeout=35,
            )
            if not r.ok:
                time.sleep(5)
                continue
            updates = r.json().get("result", [])
            for upd in updates:
                _offset = upd["update_id"] + 1
                msg = upd.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                user_id = msg.get("from", {}).get("id")
                text    = msg.get("text", "")
                if chat_id and text:
                    threading.Thread(target=dispatch, args=(chat_id, user_id, text), daemon=True).start()
        except Exception as e:
            log.error(f"Poll error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    if not TOKEN:
        log.error("TELEGRAM_BOT_TOKEN не установлен. Установи в .env: TELEGRAM_BOT_TOKEN=xxx")
        sys.exit(1)
    poll()
