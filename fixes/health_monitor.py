"""
health_monitor.py — мониторинг всех сервисов Agent Office, автоперезапуск через PM2.
PM2: pm2 start fixes/health_monitor.py --name health-monitor --interpreter python
     --cron "*/5 * * * *"   (каждые 5 минут)
Или как фоновый процесс: pm2 start fixes/health_monitor.py --name health-monitor
                           --interpreter python -- --interval 300
"""
import os, sys, time, json, logging, subprocess, requests
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [health] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent.parent / "health_monitor.log", encoding="utf-8"),
    ]
)
log = logging.getLogger("health_monitor")

INTERVAL = int(os.environ.get("HEALTH_INTERVAL", 300))  # seconds

# ─── Services to monitor ─────────────────────────────────────────────────────
SERVICES = [
    # (name, url, pm2_name)  — pm2_name=None means no auto-restart
    ("brain-мост",      "http://localhost:9999/",                  "brain-мост"),
    ("qdrant",          "http://localhost:6333/collections",        None),          # docker
    ("ollama",          "http://localhost:11434/api/tags",          None),          # own process
    ("hermes",          "http://localhost:8642/health",             "Hermes"),
    ("command-center",  "http://localhost:8770/health",             "command-center"),
    ("token-compressor","http://localhost:9988/health",             "token-compressor"),
]

PM2_PROCESSES = [
    "brain-мост",
    "daily-monitor",
    "free-llm-sync",
    "git-backup",
    "Hermes",
    "command-center",
    "token-compressor",
]

ALERT_WEBHOOK = os.environ.get("HEALTH_ALERT_WEBHOOK", "")   # n8n or custom


def _pm2_restart(name: str) -> bool:
    try:
        r = subprocess.run(["pm2", "restart", name],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            log.info(f"[pm2] {name} перезапущен")
            return True
        log.error(f"[pm2] {name} restart failed: {r.stderr[:200]}")
        return False
    except Exception as e:
        log.error(f"[pm2] {name} restart error: {e}")
        return False


def _pm2_list() -> dict[str, str]:
    """Return {name: status} for all PM2 processes."""
    try:
        r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return {}
        data = json.loads(r.stdout)
        return {p["name"]: p["pm2_env"]["status"] for p in data}
    except Exception as e:
        log.error(f"[pm2] list error: {e}")
        return {}


def _check_http(url: str, timeout: int = 5) -> tuple[bool, str]:
    try:
        r = requests.get(url, timeout=timeout)
        return r.ok, f"HTTP {r.status_code}"
    except requests.ConnectionError:
        return False, "connection refused"
    except Exception as e:
        return False, str(e)[:100]


def _alert(message: str):
    log.warning(f"[ALERT] {message}")
    if ALERT_WEBHOOK:
        try:
            requests.post(ALERT_WEBHOOK,
                          json={"text": f"🚨 health_monitor: {message}",
                                "ts": datetime.now().isoformat()},
                          timeout=10)
        except Exception:
            pass

    # Also try posting to brain-мост memory for persistence
    try:
        requests.post("http://localhost:9999/memory_save",
                      json={"key": f"alert/{int(time.time())}",
                            "value": message},
                      timeout=5)
    except Exception:
        pass


def check_services() -> dict:
    results = {}
    for name, url, pm2_name in SERVICES:
        ok, detail = _check_http(url)
        results[name] = {"ok": ok, "detail": detail, "url": url}
        if not ok:
            log.warning(f"[check] {name} DEAD — {detail}")
            if pm2_name:
                log.info(f"[check] Попытка перезапуска {pm2_name}...")
                restarted = _pm2_restart(pm2_name)
                results[name]["restarted"] = restarted
                if restarted:
                    time.sleep(3)
                    ok2, detail2 = _check_http(url)
                    results[name]["after_restart"] = {"ok": ok2, "detail": detail2}
                    if not ok2:
                        _alert(f"{name} не поднялся после pm2 restart ({detail2})")
                else:
                    _alert(f"{name} упал, pm2 restart не удался")
    return results


def check_pm2() -> dict:
    procs = _pm2_list()
    results = {}
    for name in PM2_PROCESSES:
        status = procs.get(name, "NOT FOUND")
        results[name] = status
        if status in ("stopped", "errored", "NOT FOUND"):
            log.warning(f"[pm2] {name} = {status} — перезапускаем")
            _pm2_restart(name)
            _alert(f"PM2 {name} был {status} — перезапустили")
    return results


def check_brain_models() -> dict:
    try:
        r = requests.get("http://localhost:9999/dead", timeout=5)
        if r.ok:
            dead = r.json().get("dead", [])
            if dead:
                log.warning(f"[brain] Мёртвые модели: {dead}")
            return {"dead": dead, "count": len(dead)}
    except Exception as e:
        return {"error": str(e)}
    return {}


def run_once():
    log.info("─── Health check ───────────────────────────────")
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    service_results = check_services()
    pm2_results     = check_pm2()
    brain_models    = check_brain_models()

    alive  = sum(1 for v in service_results.values() if v["ok"])
    total  = len(service_results)
    dead_m = brain_models.get("count", 0)

    log.info(f"Сервисы: {alive}/{total} | PM2 checked: {len(PM2_PROCESSES)} | "
             f"Мёртвых моделей: {dead_m}")

    report = {
        "ts": ts,
        "services": service_results,
        "pm2":      pm2_results,
        "brain_models": brain_models,
        "summary": f"{alive}/{total} сервисов живые",
    }

    # Save report to brain memory
    try:
        requests.post("http://localhost:9999/memory_save",
                      json={"key": "health/last_check", "value": json.dumps(report)},
                      timeout=5)
    except Exception:
        pass

    return report


def main():
    log.info(f"health_monitor запущен | интервал {INTERVAL}с")
    if "--once" in sys.argv:
        report = run_once()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    while True:
        try:
            run_once()
        except Exception as e:
            log.error(f"Ошибка цикла: {e}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
