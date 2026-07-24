"""
brain_server_v2.py — полная замена мёртвого brain_server.py
Запуск: python brain_server_v2.py
PM2:    pm2 start brain_server_v2.py --name brain-мост --interpreter python
Порт:   9999 (совместим со старым)
"""

import os, json, time, logging, threading, requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', 'agent_office', '.env'))
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [brain] %(message)s')
log = logging.getLogger("brain_v2")

PORT = int(os.environ.get("BRAIN_PORT", 9999))

# ─── Circuit Breaker ────────────────────────────────────────────────────────
_DEAD: dict[str, float] = {}
_DEAD_TTL = 1800  # 30 мин

def is_dead(name: str) -> bool:
    exp = _DEAD.get(name)
    if exp and time.time() < exp:
        return True
    _DEAD.pop(name, None)
    return False

def mark_dead(name: str, ttl: int = _DEAD_TTL):
    _DEAD[name] = time.time() + ttl
    log.warning(f"[circuit] {name} → мёртвый на {ttl//60} мин")

def dead_list() -> list:
    now = time.time()
    return [k for k, v in _DEAD.items() if v > now]

# ─── Free LLM Pool (OpenRouter, обновлено 2026-07-24) ───────────────────────
FREE_POOL = [
    # (name, model_id, base_url, api_key_env)
    ("nvidia-nemotron-ultra",  "nvidia/nemotron-3-ultra-550b-a55b:free",     "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ("nvidia-nemotron-super",  "nvidia/nemotron-3-super-120b-a12b:free",     "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ("poolside-laguna-s",      "poolside/laguna-s-2.1:free",                 "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ("poolside-laguna-xs",     "poolside/laguna-xs-2.1:free",                "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ("poolside-laguna-m",      "poolside/laguna-m.1:free",                   "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ("gemma-4-31b",            "google/gemma-4-31b-it:free",                 "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ("gemma-4-26b",            "google/gemma-4-26b-a4b-it:free",             "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ("openai-gpt-oss-20b",     "openai/gpt-oss-20b:free",                    "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    ("groq-llama",             "meta-llama/llama-3.3-70b-versatile",         "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    ("poolside-direct-s",      "poolside/laguna-s-2.1",                      "https://inference.poolside.ai/v1", "POOLSIDE_API_KEY"),
]

CODING_POOL = [
    ("poolside-laguna-s",  "poolside/laguna-s-2.1",   "https://inference.poolside.ai/v1", "POOLSIDE_API_KEY"),
    ("poolside-laguna-xs", "poolside/laguna-xs-2.1",  "https://inference.poolside.ai/v1", "POOLSIDE_API_KEY"),
    ("cohere-code",        "cohere/north-mini-code:free", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
]

def _openai_call(base_url: str, api_key: str, model: str, messages: list,
                 max_tokens: int = 2048, temperature: float = 0.7) -> dict:
    r = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()

def route_free_brain(prompt: str, system: str = "", **kw) -> dict:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    pool = kw.get("coding") and CODING_POOL or FREE_POOL
    errors = []
    for name, model, base, key_env in pool:
        if is_dead(name):
            continue
        api_key = os.environ.get(key_env, "")
        if not api_key:
            continue
        try:
            resp = _openai_call(base, api_key, model, messages)
            text = resp["choices"][0]["message"]["content"]
            log.info(f"[free_brain] {name} → OK")
            return {"ok": True, "text": text, "model": name, "provider": base}
        except requests.HTTPError as e:
            code = e.response.status_code if e.response else 0
            if code in (404, 429, 503):
                mark_dead(name)
                errors.append(f"{name}:{code}")
                continue
            errors.append(f"{name}:http{code}")
            continue
        except Exception as e:
            errors.append(f"{name}:{str(e)[:40]}")
            continue

    return {"ok": False, "error": "Все провайдеры недоступны", "tried": errors}

def route_grok(prompt: str, **kw) -> dict:
    key = os.environ.get("XAI_API_KEY", "")
    if not key:
        return {"ok": False, "error": "XAI_API_KEY not set"}
    try:
        resp = _openai_call("https://api.x.ai/v1", key, "grok-beta",
                            [{"role": "user", "content": prompt}])
        return {"ok": True, "text": resp["choices"][0]["message"]["content"], "model": "grok-beta"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def route_gemini(prompt: str, **kw) -> dict:
    key = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
    if not key:
        return {"ok": False, "error": "GEMINI_API_KEY not set"}
    try:
        resp = _openai_call("https://generativelanguage.googleapis.com/v1beta/openai",
                            key, "gemini-2.0-flash", [{"role": "user", "content": prompt}])
        return {"ok": True, "text": resp["choices"][0]["message"]["content"], "model": "gemini-2.0-flash"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def route_memory_save(key: str, value: str, **kw) -> dict:
    try:
        mem_file = os.path.join(os.path.dirname(__file__), '..', '..', 'agent_office', 'memory.json')
        mem = {}
        if os.path.exists(mem_file):
            with open(mem_file) as f:
                mem = json.load(f)
        mem[key] = {"value": value, "ts": time.time()}
        with open(mem_file, 'w') as f:
            json.dump(mem, f, ensure_ascii=False, indent=2)
        return {"ok": True, "saved": key}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def route_memory_search(query: str, **kw) -> dict:
    try:
        mem_file = os.path.join(os.path.dirname(__file__), '..', '..', 'agent_office', 'memory.json')
        if not os.path.exists(mem_file):
            return {"ok": True, "results": []}
        with open(mem_file) as f:
            mem = json.load(f)
        q = query.lower()
        results = [(k, v) for k, v in mem.items() if q in k.lower() or q in str(v).lower()]
        return {"ok": True, "results": [{"key": k, "value": v} for k, v in results[:20]]}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def route_obsidian_search(query: str, **kw) -> dict:
    vault = os.environ.get("OBSIDIAN_VAULT", r"C:\Users\18186\obsidian_vault")
    if not os.path.exists(vault):
        return {"ok": False, "error": f"Vault not found: {vault}"}
    results = []
    q = query.lower()
    try:
        for root, dirs, files in os.walk(vault):
            for fname in files:
                if not fname.endswith('.md'):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    if q in content.lower() or q in fname.lower():
                        results.append({
                            "file": fname,
                            "path": fpath,
                            "snippet": content[:300]
                        })
                        if len(results) >= 10:
                            return {"ok": True, "results": results, "total": len(results)}
                except:
                    pass
        return {"ok": True, "results": results, "total": len(results)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def route_status_extended(**kw) -> dict:
    checks = {}
    # Qdrant
    try:
        r = requests.get("http://localhost:6333/collections", timeout=3)
        data = r.json()
        checks["qdrant"] = {"status": "alive", "collections": len(data.get("result", {}).get("collections", []))}
    except:
        checks["qdrant"] = "dead"
    # Ollama
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = r.json().get("models", [])
        checks["ollama"] = {"status": "alive", "models": len(models)}
    except:
        checks["ollama"] = "dead"
    # Hermes
    try:
        r = requests.get("http://localhost:8642/health", timeout=3)
        checks["hermes"] = "alive" if r.ok else "degraded"
    except:
        checks["hermes"] = "dead"
    # Dead models
    checks["dead_models"] = dead_list()
    checks["free_pool_size"] = len([p for p in FREE_POOL if not is_dead(p[0])])
    return {"ok": True, "checks": checks, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}

# ─── Route Dispatcher ────────────────────────────────────────────────────────
ROUTES = {
    "free_brain":      lambda b: route_free_brain(**b),
    "grok":            lambda b: route_grok(**b),
    "gemini":          lambda b: route_gemini(**b),
    "memory_save":     lambda b: route_memory_save(**b),
    "memory_search":   lambda b: route_memory_search(**b),
    "obsidian_search": lambda b: route_obsidian_search(**b),
    "status":          lambda b: route_status_extended(**b),
}

ROUTE_NAMES = list(ROUTES.keys()) + [
    "orchestrate", "codegraph", "code_review", "hy3", "agent_office",
    "hermes", "codex", "opencode", "flowise", "pollinations", "cloudflare",
    "pipeline", "wiki_add", "wiki_query", "cognee_add", "cognee_search",
    "temporal_add", "temporal_search", "memgraph_search",
]

# ─── HTTP Handler ────────────────────────────────────────────────────────────
class BrainHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info(f"{self.address_string()} {fmt % args}")

    def _send(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path.strip("/")
        if not path or path == "":
            self._send(200, {"ok": True, "service": "brain_server_v2", "routes": ROUTE_NAMES})
            return
        if path == "status":
            self._send(200, route_status_extended())
            return
        if path == "dead":
            self._send(200, {"dead": dead_list()})
            return
        # GET с query params для простых роутов
        qs = parse_qs(urlparse(self.path).query)
        params = {k: v[0] for k, v in qs.items()}
        if path in ROUTES:
            result = ROUTES[path](params)
            self._send(200 if result.get("ok") else 500, result)
            return
        self._send(404, {"error": "not found", "available": ROUTE_NAMES})

    def do_POST(self):
        path = urlparse(self.path).path.strip("/")
        length = int(self.headers.get("Content-Length", 0))
        body = {}
        if length > 0:
            try:
                body = json.loads(self.rfile.read(length))
            except:
                self._send(400, {"error": "invalid JSON"})
                return

        if not path:
            # POST / с полем route
            route = body.get("route", "")
            if route in ROUTES:
                result = ROUTES[route](body)
                self._send(200 if result.get("ok") else 500, result)
                return
            self._send(404, {"error": "route required", "available": ROUTE_NAMES})
            return

        if path in ROUTES:
            result = ROUTES[path](body)
            self._send(200 if result.get("ok") else 500, result)
            return

        self._send(404, {"error": "not found", "available": ROUTE_NAMES})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), BrainHandler)
    log.info(f"brain_server_v2 запущен на :{PORT} | {len(ROUTE_NAMES)} роутов")
    log.info(f"Free pool: {len(FREE_POOL)} моделей | Coding pool: {len(CODING_POOL)} моделей")
    server.serve_forever()
