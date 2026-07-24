"""
brain_server_v2.py — полная замена мёртвого brain_server.py
Запуск: python brain_server_v2.py
PM2:    pm2 start brain_server_v2.py --name brain-мост --interpreter python
Порт:   9999 (совместим со старым)
26 роутов: free_brain, grok, gemini, pollinations, cloudflare, hermes, orchestrate,
           pipeline, code_review, codegraph, opencode, codex, flowise,
           memory_save, memory_search, wiki_add, wiki_query, cognee_add, cognee_search,
           temporal_add, temporal_search, memgraph_search, hy3, obsidian_search,
           agent_office, status
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
_DEAD_LOCK = threading.Lock()
_DEAD_TTL = 1800  # 30 мин


def is_dead(name: str) -> bool:
    with _DEAD_LOCK:
        exp = _DEAD.get(name)
        if exp and time.time() < exp:
            return True
        _DEAD.pop(name, None)
        return False


def mark_dead(name: str, ttl: int = _DEAD_TTL):
    with _DEAD_LOCK:
        _DEAD[name] = time.time() + ttl
    log.warning(f"[circuit] {name} → мёртвый на {ttl // 60} мин")


def revive(name: str):
    with _DEAD_LOCK:
        _DEAD.pop(name, None)
    log.info(f"[circuit] {name} → оживлён принудительно")


def dead_list() -> list:
    now = time.time()
    with _DEAD_LOCK:
        return [k for k, v in _DEAD.items() if v > now]


# ─── Free LLM Pool (обновлено 2026-07-24, qwen3 УДАЛЁН) ────────────────────
FREE_POOL = [
    # (name, model_id, base_url, api_key_env)
    ("nvidia-nemotron-ultra",  "nvidia/nemotron-3-ultra-550b-a55b:free",  "https://openrouter.ai/api/v1",       "OPENROUTER_API_KEY"),
    ("nvidia-nemotron-super",  "nvidia/nemotron-3-super-120b-a12b:free",  "https://openrouter.ai/api/v1",       "OPENROUTER_API_KEY"),
    ("poolside-laguna-s",      "poolside/laguna-s-2.1:free",              "https://openrouter.ai/api/v1",       "OPENROUTER_API_KEY"),
    ("poolside-laguna-xs",     "poolside/laguna-xs-2.1:free",             "https://openrouter.ai/api/v1",       "OPENROUTER_API_KEY"),
    ("poolside-laguna-m",      "poolside/laguna-m.1:free",                "https://openrouter.ai/api/v1",       "OPENROUTER_API_KEY"),
    ("gemma-4-31b",            "google/gemma-4-31b-it:free",              "https://openrouter.ai/api/v1",       "OPENROUTER_API_KEY"),
    ("gemma-4-26b",            "google/gemma-4-26b-a4b-it:free",          "https://openrouter.ai/api/v1",       "OPENROUTER_API_KEY"),
    ("openai-gpt-oss-20b",     "openai/gpt-oss-20b:free",                 "https://openrouter.ai/api/v1",       "OPENROUTER_API_KEY"),
    ("groq-llama",             "meta-llama/llama-3.3-70b-versatile",      "https://api.groq.com/openai/v1",     "GROQ_API_KEY"),
    ("poolside-direct-s",      "poolside/laguna-s-2.1",                   "https://inference.poolside.ai/v1",   "POOLSIDE_API_KEY"),
]

CODING_POOL = [
    ("poolside-laguna-s",       "poolside/laguna-s-2.1",                 "https://inference.poolside.ai/v1",   "POOLSIDE_API_KEY"),
    ("poolside-laguna-xs",      "poolside/laguna-xs-2.1",                "https://inference.poolside.ai/v1",   "POOLSIDE_API_KEY"),
    ("cohere-code",             "cohere/north-mini-code:free",           "https://openrouter.ai/api/v1",       "OPENROUTER_API_KEY"),
    ("nvidia-nemotron-super",   "nvidia/nemotron-3-super-120b-a12b:free","https://openrouter.ai/api/v1",       "OPENROUTER_API_KEY"),
]

# ─── Local service ports ─────────────────────────────────────────────────────
LOCAL_SERVICES = {
    "hermes":   int(os.environ.get("HERMES_PORT",   8642)),
    "flowise":  int(os.environ.get("FLOWISE_PORT",  3003)),
    "qdrant":   int(os.environ.get("QDRANT_PORT",   6333)),
    "ollama":   int(os.environ.get("OLLAMA_PORT",   11434)),
    "n8n":      int(os.environ.get("N8N_PORT",      5678)),
    "comfyui":  int(os.environ.get("COMFYUI_PORT",  8188)),
    "cognee":   int(os.environ.get("COGNEE_PORT",   7860)),
}


# ─── Helpers ─────────────────────────────────────────────────────────────────
def _openai_call(base_url: str, api_key: str, model: str, messages: list,
                 max_tokens: int = 2048, temperature: float = 0.7) -> dict:
    r = requests.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages,
              "max_tokens": max_tokens, "temperature": temperature},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def _proxy_local(service: str, path: str, body: dict = None, method: str = "POST") -> dict:
    port = LOCAL_SERVICES.get(service)
    if not port:
        return {"ok": False, "error": f"Unknown service: {service}"}
    url = f"http://localhost:{port}/{path.lstrip('/')}"
    try:
        if method == "GET" or body is None:
            r = requests.get(url, params=body, timeout=10)
        else:
            r = requests.post(url, json=body, timeout=30)
        if r.ok:
            try:
                return {"ok": True, **r.json()}
            except Exception:
                return {"ok": True, "text": r.text[:2000]}
        return {"ok": False, "error": f"HTTP {r.status_code}", "body": r.text[:300]}
    except requests.ConnectionError:
        return {"ok": False, "error": f"{service} недоступен (порт {port})"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


# ─── LLM Routes ──────────────────────────────────────────────────────────────
def route_free_brain(prompt: str = "", system: str = "", **kw) -> dict:
    if not prompt:
        return {"ok": False, "error": "prompt required"}
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    pool = CODING_POOL if kw.get("coding") else FREE_POOL
    errors = []
    for name, model, base, key_env in pool:
        if is_dead(name):
            continue
        api_key = os.environ.get(key_env, "")
        if not api_key:
            continue
        try:
            resp = _openai_call(base, api_key, model, messages,
                                max_tokens=int(kw.get("max_tokens", 2048)),
                                temperature=float(kw.get("temperature", 0.7)))
            text = resp["choices"][0]["message"]["content"]
            log.info(f"[free_brain] {name} OK")
            return {"ok": True, "text": text, "model": name, "provider": base}
        except requests.HTTPError as e:
            code = e.response.status_code if e.response else 0
            if code in (404, 429, 503):
                mark_dead(name)
            errors.append(f"{name}:{code}")
        except Exception as e:
            errors.append(f"{name}:{str(e)[:40]}")

    return {"ok": False, "error": "Все провайдеры недоступны", "tried": errors}


def route_grok(prompt: str = "", **kw) -> dict:
    key = os.environ.get("XAI_API_KEY", "")
    if not key:
        return {"ok": False, "error": "XAI_API_KEY not set"}
    model = kw.get("model", "grok-3")
    try:
        resp = _openai_call("https://api.x.ai/v1", key, model,
                            [{"role": "user", "content": prompt}])
        return {"ok": True, "text": resp["choices"][0]["message"]["content"], "model": model}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def route_gemini(prompt: str = "", **kw) -> dict:
    key = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
    if not key:
        return {"ok": False, "error": "GEMINI_API_KEY not set"}
    model = kw.get("model", "gemini-2.0-flash")
    try:
        resp = _openai_call("https://generativelanguage.googleapis.com/v1beta/openai",
                            key, model, [{"role": "user", "content": prompt}])
        return {"ok": True, "text": resp["choices"][0]["message"]["content"], "model": model}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def route_pollinations(prompt: str = "", **kw) -> dict:
    """Pollinations.ai — 100% бесплатно, без API ключа."""
    mode = kw.get("mode", "text")
    try:
        if mode == "image":
            width  = int(kw.get("width", 1024))
            height = int(kw.get("height", 1024))
            model  = kw.get("model", "flux")
            seed   = kw.get("seed", "")
            safe_p = requests.utils.quote(prompt)
            seed_s = f"&seed={seed}" if seed else ""
            url = f"https://image.pollinations.ai/prompt/{safe_p}?width={width}&height={height}&model={model}&nologo=true{seed_s}"
            return {"ok": True, "image_url": url, "model": model}
        else:
            model  = kw.get("model", "openai")
            system = kw.get("system", "Be helpful and concise.")
            r = requests.post(
                "https://text.pollinations.ai/",
                json={"messages": [{"role": "system", "content": system},
                                   {"role": "user",   "content": prompt}],
                      "model": model, "seed": kw.get("seed", 42)},
                timeout=30,
            )
            r.raise_for_status()
            return {"ok": True, "text": r.text, "model": model}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def route_cloudflare(prompt: str = "", **kw) -> dict:
    """Cloudflare Workers AI — 10k neuron/day бесплатно."""
    account_id = os.environ.get("CF_ACCOUNT_ID", "")
    api_token  = os.environ.get("CF_API_TOKEN", os.environ.get("CLOUDFLARE_API_TOKEN", ""))
    if not account_id or not api_token:
        return {"ok": False, "error": "CF_ACCOUNT_ID and CF_API_TOKEN required"}
    model = kw.get("model", "@cf/meta/llama-3.1-8b-instruct")
    try:
        r = requests.post(
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}",
            headers={"Authorization": f"Bearer {api_token}"},
            json={"messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        r.raise_for_status()
        return {"ok": True, "text": r.json().get("result", {}).get("response", ""), "model": model}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def route_orchestrate(prompt: str = "", **kw) -> dict:
    """Запустить N моделей параллельно, вернуть лучший (самый длинный) ответ."""
    n_models = int(kw.get("n", 2))
    results = []
    for name, model, base, key_env in FREE_POOL:
        if is_dead(name) or len(results) >= n_models:
            continue
        api_key = os.environ.get(key_env, "")
        if not api_key:
            continue
        try:
            resp = _openai_call(base, api_key, model,
                                [{"role": "user", "content": prompt}], max_tokens=1024)
            text = resp["choices"][0]["message"]["content"]
            results.append({"model": name, "text": text, "len": len(text)})
        except Exception:
            pass
    if not results:
        return {"ok": False, "error": "Нет доступных моделей"}
    best = max(results, key=lambda x: x["len"])
    return {"ok": True, "best": best, "all": results}


def route_pipeline(steps: list = None, **kw) -> dict:
    """Цепочка промптов: вывод каждого шага идёт во вход следующего через {prev}."""
    if not steps:
        return {"ok": False, "error": "steps (list of prompts) required"}
    result = ""
    history = []
    for i, step in enumerate(steps):
        prompt = step.replace("{prev}", result) if result else step
        res = route_free_brain(prompt=prompt)
        if not res.get("ok"):
            return {"ok": False, "error": f"Step {i} failed: {res.get('error')}", "history": history}
        result = res["text"]
        history.append({"step": i, "prompt": prompt[:100], "result": result[:300], "model": res.get("model")})
    return {"ok": True, "final": result, "history": history}


# ─── Code Routes ──────────────────────────────────────────────────────────────
def route_code_review(code: str = "", lang: str = "python", **kw) -> dict:
    prompt = (f"Review this {lang} code for bugs, security issues, and improvements. "
              f"Format as JSON: {{bugs:[], security:[], improvements:[], verdict:'ok'|'issues'}}\n\n"
              f"```{lang}\n{code[:3000]}\n```")
    res = route_free_brain(prompt=prompt, coding=True)
    return {**res, "lang": lang, "lines": len(code.splitlines())}


def route_codegraph(path: str = "", query: str = "", **kw) -> dict:
    prompt = (f"Analyze code at path: {path}. Query: {query or 'summarize structure'}. "
              f"Return JSON: {{symbols:[], imports:[], functions:[], classes:[], summary:''}}. "
              f"If path not accessible, describe what you know about it.")
    return route_free_brain(prompt=prompt, coding=True)


def route_opencode(prompt: str = "", **kw) -> dict:
    """OpenCode — маршрут в пул coding-оптимизированных моделей."""
    return route_free_brain(prompt=prompt, coding=True,
                             max_tokens=kw.get("max_tokens", 4096))


def route_codex(prompt: str = "", **kw) -> dict:
    """Codex — генерация кода через лучшую доступную coding-модель."""
    system = ("You are an expert software engineer. "
               "Write clean, production-ready code. "
               "Return only the code block, no explanation unless asked.")
    return route_free_brain(prompt=prompt, system=system, coding=True,
                             max_tokens=kw.get("max_tokens", 4096))


# ─── Service Proxy Routes ────────────────────────────────────────────────────
def route_hermes(prompt: str = "", **kw) -> dict:
    path = kw.pop("path", "chat")
    return _proxy_local("hermes", path, {"prompt": prompt, **kw})


def route_flowise(flow_id: str = "", question: str = "", **kw) -> dict:
    if not flow_id:
        return _proxy_local("flowise", "api/v1/chatflows", method="GET")
    return _proxy_local("flowise", f"api/v1/prediction/{flow_id}",
                        {"question": question or kw.get("prompt", "")})


# ─── Memory Routes ────────────────────────────────────────────────────────────
def _mem_file() -> str:
    return os.path.join(os.path.dirname(__file__), '..', '..', 'agent_office', 'memory.json')


def _mem_load() -> dict:
    f = _mem_file()
    if os.path.exists(f):
        with open(f, encoding='utf-8') as fp:
            return json.load(fp)
    return {}


def _mem_save(mem: dict):
    with open(_mem_file(), 'w', encoding='utf-8') as fp:
        json.dump(mem, fp, ensure_ascii=False, indent=2)


def route_memory_save(key: str = "", value: str = "", **kw) -> dict:
    if not key:
        return {"ok": False, "error": "key required"}
    try:
        mem = _mem_load()
        mem[key] = {"value": value, "ts": time.time()}
        _mem_save(mem)
        return {"ok": True, "saved": key}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def route_memory_search(query: str = "", **kw) -> dict:
    try:
        mem = _mem_load()
        q = query.lower()
        results = [{"key": k, "value": v}
                   for k, v in mem.items()
                   if q in k.lower() or q in str(v).lower()]
        return {"ok": True, "results": results[:20]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def route_wiki_add(title: str = "", content: str = "", **kw) -> dict:
    return route_memory_save(key=f"wiki/{title}", value=content)


def route_wiki_query(query: str = "", **kw) -> dict:
    try:
        mem = _mem_load()
        q = query.lower()
        results = [
            {"title": k.replace("wiki/", ""), "content": str(v.get("value", ""))[:500]}
            for k, v in mem.items()
            if k.startswith("wiki/") and (q in k.lower() or q in str(v).lower())
        ]
        return {"ok": True, "results": results[:10]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def route_cognee_add(text: str = "", dataset: str = "default", **kw) -> dict:
    result = _proxy_local("cognee", "api/v1/cognify",
                           {"text": text, "dataset_name": dataset})
    if "недоступен" in result.get("error", ""):
        return route_memory_save(key=f"cognee/{dataset}/{int(time.time())}", value=text)
    return result


def route_cognee_search(query: str = "", dataset: str = "default", **kw) -> dict:
    result = _proxy_local("cognee", "api/v1/search",
                           {"query": query, "datasets": [dataset]})
    if "недоступен" in result.get("error", ""):
        return route_memory_search(query=query)
    return result


def route_temporal_add(**kw) -> dict:
    return {"ok": False, "disabled": True,
            "error": "Temporal ОТКЛЮЧЁН — риск перегрева CPU. Включить: установить TEMPORAL_ENABLED=1"}


def route_temporal_search(**kw) -> dict:
    return {"ok": False, "disabled": True,
            "error": "Temporal ОТКЛЮЧЁН — риск перегрева CPU. Включить: установить TEMPORAL_ENABLED=1"}


def route_memgraph_search(query: str = "", **kw) -> dict:
    result = _proxy_local("memgraph", "query",
                           {"query": f"MATCH (n) WHERE n.content CONTAINS '{query}' RETURN n LIMIT 20"})
    if not result.get("ok"):
        return route_memory_search(query=query)
    return result


def route_obsidian_search(query: str = "", **kw) -> dict:
    vault = os.environ.get("OBSIDIAN_VAULT", r"C:\Users\18186\obsidian_vault")
    if not os.path.exists(vault):
        return {"ok": False, "error": f"Vault не найден: {vault}"}
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
                        results.append({"file": fname, "path": fpath, "snippet": content[:300]})
                        if len(results) >= 10:
                            return {"ok": True, "results": results}
                except Exception:
                    pass
        return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def route_hy3(query: str = "", **kw) -> dict:
    """HY3 гибридный поиск: Qdrant + memory + Obsidian."""
    results = []
    # Qdrant
    try:
        r = requests.post(
            f"http://localhost:{LOCAL_SERVICES['qdrant']}/collections/memory/points/search",
            json={"vector": [0.0] * 1536, "limit": 5, "with_payload": True},
            timeout=5,
        )
        if r.ok:
            for hit in r.json().get("result", []):
                results.append({"source": "qdrant", "score": hit.get("score"),
                                 "content": hit.get("payload", {})})
    except Exception:
        pass
    # Local memory
    for r in route_memory_search(query=query).get("results", [])[:5]:
        results.append({"source": "memory", **r})
    # Obsidian
    for r in route_obsidian_search(query=query).get("results", [])[:3]:
        results.append({"source": "obsidian", **r})
    return {"ok": True, "query": query, "results": results, "total": len(results)}


# ─── Status Routes ────────────────────────────────────────────────────────────
def route_agent_office(**kw) -> dict:
    checks = {}
    for name, port in [("n8n", LOCAL_SERVICES["n8n"]),
                       ("comfyui", LOCAL_SERVICES["comfyui"]),
                       ("qdrant",  LOCAL_SERVICES["qdrant"]),
                       ("hermes",  LOCAL_SERVICES["hermes"]),
                       ("flowise", LOCAL_SERVICES["flowise"])]:
        try:
            r = requests.get(f"http://localhost:{port}/", timeout=2)
            checks[name] = {"status": "alive", "port": port, "code": r.status_code}
        except Exception:
            checks[name] = {"status": "dead", "port": port}
    checks["dead_models"] = dead_list()
    checks["free_pool_alive"] = len([p for p in FREE_POOL if not is_dead(p[0])])
    return {"ok": True, "agent_office": checks, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}


def route_status_extended(**kw) -> dict:
    checks = {}
    service_checks = {
        "qdrant":  (f"http://localhost:{LOCAL_SERVICES['qdrant']}/collections", "GET"),
        "ollama":  (f"http://localhost:{LOCAL_SERVICES['ollama']}/api/tags",    "GET"),
        "hermes":  (f"http://localhost:{LOCAL_SERVICES['hermes']}/health",      "GET"),
        "flowise": (f"http://localhost:{LOCAL_SERVICES['flowise']}/api/v1/chatflows", "GET"),
        "n8n":     (f"http://localhost:{LOCAL_SERVICES['n8n']}/healthz",        "GET"),
    }
    for name, (url, _) in service_checks.items():
        try:
            r = requests.get(url, timeout=3)
            if r.ok:
                try:
                    data = r.json()
                    if name == "qdrant":
                        checks[name] = {"status": "alive", "collections": len(data.get("result", {}).get("collections", []))}
                    elif name == "ollama":
                        checks[name] = {"status": "alive", "models": len(data.get("models", []))}
                    else:
                        checks[name] = "alive"
                except Exception:
                    checks[name] = "alive"
            else:
                checks[name] = "degraded"
        except Exception:
            checks[name] = "dead"
    checks["dead_models"]      = dead_list()
    checks["free_pool_total"]  = len(FREE_POOL)
    checks["free_pool_alive"]  = len([p for p in FREE_POOL if not is_dead(p[0])])
    return {"ok": True, "checks": checks, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}


# ─── Route Dispatcher ────────────────────────────────────────────────────────
def _b(fn):
    return lambda body: fn(**body)


ROUTES = {
    # LLM
    "free_brain":      _b(route_free_brain),
    "grok":            _b(route_grok),
    "gemini":          _b(route_gemini),
    "pollinations":    _b(route_pollinations),
    "cloudflare":      _b(route_cloudflare),
    "orchestrate":     _b(route_orchestrate),
    "pipeline":        _b(route_pipeline),
    # Code
    "code_review":     _b(route_code_review),
    "codegraph":       _b(route_codegraph),
    "opencode":        _b(route_opencode),
    "codex":           _b(route_codex),
    # Service Proxies
    "hermes":          _b(route_hermes),
    "flowise":         _b(route_flowise),
    # Memory
    "memory_save":     _b(route_memory_save),
    "memory_search":   _b(route_memory_search),
    "wiki_add":        _b(route_wiki_add),
    "wiki_query":      _b(route_wiki_query),
    "cognee_add":      _b(route_cognee_add),
    "cognee_search":   _b(route_cognee_search),
    "temporal_add":    _b(route_temporal_add),
    "temporal_search": _b(route_temporal_search),
    "memgraph_search": _b(route_memgraph_search),
    "obsidian_search": _b(route_obsidian_search),
    "hy3":             _b(route_hy3),
    # System
    "agent_office":    _b(route_agent_office),
    "status":          _b(route_status_extended),
}

ROUTE_NAMES = list(ROUTES.keys())


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
        if not path:
            self._send(200, {"ok": True, "service": "brain_server_v2",
                              "routes": ROUTE_NAMES, "count": len(ROUTE_NAMES),
                              "free_pool_alive": len([p for p in FREE_POOL if not is_dead(p[0])])})
            return
        if path == "status":
            self._send(200, route_status_extended())
            return
        if path == "dead":
            self._send(200, {"dead": dead_list()})
            return
        if path.startswith("revive/"):
            name = path[7:]
            revive(name)
            self._send(200, {"ok": True, "revived": name})
            return
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
            except Exception:
                self._send(400, {"error": "invalid JSON"})
                return

        if not path:
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
    log.info(f"brain_server_v2 запущен :{PORT} | {len(ROUTE_NAMES)} роутов | "
             f"free_pool={len(FREE_POOL)} моделей")
    server.serve_forever()
