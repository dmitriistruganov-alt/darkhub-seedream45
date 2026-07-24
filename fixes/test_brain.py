"""
test_brain.py — smoke tests for brain_server_v2.py (все 26 роутов)
Тестирует только структуру ответов, не реальные LLM вызовы.

Запуск:
  python fixes/test_brain.py               # localhost:9999
  python fixes/test_brain.py 127.0.0.1:9999
  python fixes/test_brain.py --verbose
"""
import sys, json, time
import urllib.request, urllib.error

VERBOSE = "--verbose" in sys.argv
args_no_flags = [a for a in sys.argv[1:] if not a.startswith("--")]
BASE = f"http://{args_no_flags[0] if args_no_flags else 'localhost:9999'}"

GREEN = "\033[92m"
RED   = "\033[91m"
YELL  = "\033[93m"
CYAN  = "\033[96m"
RST   = "\033[0m"
PASS  = f"{GREEN}PASS{RST}"
FAIL  = f"{RED}FAIL{RST}"
SKIP  = f"{YELL}SKIP{RST}"

results = []
_skipped = 0


def get(path, timeout=10):
    try:
        with urllib.request.urlopen(f"{BASE}/{path}", timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def post(path, data, timeout=20):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BASE}/{path}", data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def check(label, cond, detail="", warn=False):
    icon = PASS if cond else (SKIP if warn else FAIL)
    results.append(True if cond else (None if warn else False))
    line = f"  [{icon}] {label}"
    if detail and (VERBOSE or not cond): line += f" — {detail}"
    print(line)


def section(t):
    print(f"\n{CYAN}─── {t} ───{RST}")


# ─── Connect ──────────────────────────────────────────────────────────────────
print(f"\n{CYAN}brain_server_v2 smoke tests @ {BASE}{RST}")
t0 = time.time()

# ─── GET endpoints ────────────────────────────────────────────────────────────
section("GET / (root)")
code, body = get("")
check("returns 200", code == 200, f"got {code}")
check("has 'routes' list", isinstance(body.get("routes"), list))
check("has 26 routes", len(body.get("routes", [])) == 26,
      f"got {len(body.get('routes', []))}")
check("free_pool_alive is int", isinstance(body.get("free_pool_alive"), int))

section("GET /status")
code, body = get("status")
check("returns 200", code == 200, f"got {code}")
check("has 'ok' key", body.get("ok") is True)
check("has 'checks' dict", isinstance(body.get("checks"), dict))
check("has 'ts' timestamp", bool(body.get("ts")))

section("GET /dead")
code, body = get("dead")
check("returns 200", code == 200)
check("has 'dead' list", isinstance(body.get("dead"), list))

section("GET /revive/<name>")
code, body = get("revive/test-model")
check("returns 200", code == 200)
check("has 'revived' field", "revived" in body)

section("GET /unknown → 404")
code, _ = get("this_route_does_not_exist")
check("unknown GET returns 404", code == 404)

# ─── OPTIONS (CORS) ───────────────────────────────────────────────────────────
section("OPTIONS / (CORS)")
req = urllib.request.Request(f"{BASE}/", method="OPTIONS")
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        check("returns 200", r.status == 200)
except Exception as e:
    check("OPTIONS /", False, str(e))

# ─── POST / with route field ──────────────────────────────────────────────────
section("POST / with route= field")
code, body = post("", {"route": "status"})
check("route=status → 200", code == 200, f"got {code}")
check("route=status returns ok=True", body.get("ok") is True)
code2, body2 = post("", {"route": "nonexistent"})
check("route=nonexistent → 404", code2 == 404)

# ─── Memory routes ────────────────────────────────────────────────────────────
section("POST /memory_save + /memory_search")
_, ms = post("memory_save", {"key": "test_smoke_42", "value": "hello agent office"})
check("memory_save: has 'ok'", "ok" in ms, str(ms)[:80])
_, mr = post("memory_search", {"query": "test_smoke_42"})
check("memory_search: has 'results' or 'error'", "results" in mr or "error" in mr)

section("POST /wiki_add + /wiki_query")
_, wa = post("wiki_add", {"key": "test_wiki", "value": "wiki test entry"})
check("wiki_add: has 'ok'", "ok" in wa, str(wa)[:80])
_, wq = post("wiki_query", {"query": "test_wiki"})
check("wiki_query: has 'results' or 'error'", "results" in wq or "error" in wq)

# ─── LLM routes (structural only — no actual API calls) ───────────────────────
section("POST /free_brain (no API keys expected → structured error OK)")
_, fb = post("free_brain", {"prompt": "ping"})
check("free_brain: has 'ok'", "ok" in fb, str(fb)[:80])
check("free_brain: ok=True OR has 'tried'/'error'",
      fb.get("ok") or "tried" in fb or "error" in fb)

section("POST /grok (no keys → graceful error)")
_, gr = post("grok", {"prompt": "ping"})
check("grok: has 'ok'", "ok" in gr)
if not gr.get("ok"):
    check("grok: has 'error' when no key", "error" in gr)

section("POST /gemini (no keys → graceful error)")
_, ge = post("gemini", {"prompt": "ping"})
check("gemini: has 'ok'", "ok" in ge)

section("POST /pollinations (no key needed)")
_, po = post("pollinations", {"prompt": "test", "mode": "text"})
check("pollinations: has 'ok'", "ok" in po, str(po)[:80])

section("POST /cloudflare (no keys → graceful error)")
_, cf = post("cloudflare", {"prompt": "ping"})
check("cloudflare: has 'ok'", "ok" in cf)

# ─── Orchestrate / Pipeline ───────────────────────────────────────────────────
section("POST /orchestrate + /pipeline")
_, oc = post("orchestrate", {"prompt": "ping", "n": 1})
check("orchestrate: has 'ok'", "ok" in oc, str(oc)[:80])

_, pl = post("pipeline", {"steps": ["step1", "step2"]})
check("pipeline: has 'ok'", "ok" in pl, str(pl)[:80])

# ─── Code routes ──────────────────────────────────────────────────────────────
section("POST /code_review + /codegraph + /opencode + /codex")
for route, body_data in [
    ("code_review",  {"code": "x = 1", "lang": "python"}),
    ("codegraph",    {"path": "test.py", "query": "summarize"}),
    ("opencode",     {"prompt": "write hello world"}),
    ("codex",        {"prompt": "write hello world"}),
]:
    _, r = post(route, body_data)
    check(f"{route}: has 'ok'", "ok" in r, str(r)[:60])

# ─── Service proxies ──────────────────────────────────────────────────────────
section("POST /hermes + /flowise (local services may be down → graceful)")
for route, body_data in [
    ("hermes",  {"prompt": "test"}),
    ("flowise", {}),
]:
    _, r = post(route, body_data)
    check(f"{route}: has 'ok'", "ok" in r, str(r)[:60], warn=True)

# ─── Cognee / Temporal / Memgraph ─────────────────────────────────────────────
section("POST /cognee_add + /cognee_search (fallback to memory)")
_, ca = post("cognee_add", {"text": "cognee test"})
check("cognee_add: has 'ok'", "ok" in ca)
_, cs = post("cognee_search", {"query": "cognee test"})
check("cognee_search: has 'ok'", "ok" in cs)

section("POST /temporal_add + /temporal_search (должны быть отключены)")
_, ta = post("temporal_add", {"event": "test"})
check("temporal_add: disabled (ok=False)", ta.get("ok") is False,
      f"expected disabled, got: {str(ta)[:80]}")
_, ts = post("temporal_search", {"query": "test"})
check("temporal_search: disabled (ok=False)", ts.get("ok") is False)

section("POST /memgraph_search (fallback to memory)")
_, mg = post("memgraph_search", {"query": "test"})
check("memgraph_search: has 'ok'", "ok" in mg)

# ─── Search routes ────────────────────────────────────────────────────────────
section("POST /obsidian_search + /hy3")
_, ob = post("obsidian_search", {"query": "test"})
check("obsidian_search: has 'ok'", "ok" in ob, str(ob)[:60], warn=True)
_, hy = post("hy3", {"query": "test"})
check("hy3: has 'ok'", "ok" in hy, str(hy)[:60])

# ─── Agent Office / Status via POST ──────────────────────────────────────────
section("POST /agent_office + /status")
_, ao = post("agent_office", {})
check("agent_office: has 'ok'", "ok" in ao)
check("agent_office: has 'agent_office' dict", "agent_office" in ao)
_, st = post("status", {})
check("status: has 'ok'", "ok" in st)

# ─── All 26 routes reachable ──────────────────────────────────────────────────
section("All 26 routes: GET / lists them all")
ALL_ROUTES = [
    "free_brain", "grok", "gemini", "pollinations", "cloudflare",
    "orchestrate", "pipeline", "code_review", "codegraph", "opencode", "codex",
    "hermes", "flowise", "memory_save", "memory_search", "wiki_add", "wiki_query",
    "cognee_add", "cognee_search", "temporal_add", "temporal_search",
    "memgraph_search", "hy3", "obsidian_search", "agent_office", "status",
]
_, root = get("")
listed = set(root.get("routes", []))
for route in ALL_ROUTES:
    check(f"route '{route}' listed", route in listed)

# ─── Summary ──────────────────────────────────────────────────────────────────
elapsed = round(time.time() - t0, 1)
true_results = [r for r in results if r is True]
false_results = [r for r in results if r is False]
warn_results  = [r for r in results if r is None]

print(f"\n{'='*50}")
print(f"Time: {elapsed}s | Tests: {len(results)} total")
print(f"  {GREEN}PASS: {len(true_results)}{RST}  "
      f"{RED}FAIL: {len(false_results)}{RST}  "
      f"{YELL}SKIP/WARN: {len(warn_results)}{RST}")

if not false_results:
    print(f"\n[{PASS}] brain_server_v2 полностью работоспособен ({len(true_results)} тестов)")
else:
    print(f"\n[{FAIL}] {len(false_results)} тест(ов) провалились")
    print("Проверь: pm2 logs brain-мост")

sys.exit(0 if not false_results else 1)
