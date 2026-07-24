"""
test_brain.py — smoke tests for brain_server_v2.py
Run against a live server: python fixes/test_brain.py [host:port]
Default: localhost:9999
"""
import sys, json
import urllib.request, urllib.error

BASE = f"http://{sys.argv[1] if len(sys.argv) > 1 else 'localhost:9999'}"

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

results = []


def get(path):
    try:
        with urllib.request.urlopen(f"{BASE}/{path}", timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{BASE}/{path}", data=body,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            body_err = json.loads(e.read())
        except Exception:
            body_err = {}
        return e.code, body_err
    except Exception as e:
        return 0, {"error": str(e)}


def check(label, cond, detail=""):
    status = PASS if cond else FAIL
    results.append(cond)
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))


# ─── Tests ──────────────────────────────────────────────────────────────────
print(f"\nTesting brain_server_v2 @ {BASE}\n")

# GET /
code, body = get("")
check("GET / returns 200", code == 200, f"code={code}")
check("GET / has routes list", "routes" in body)

# GET /status
code, body = get("status")
check("GET /status returns 200", code == 200, f"code={code}")
check("GET /status has checks", "checks" in body)

# GET /dead
code, body = get("dead")
check("GET /dead returns 200", code == 200)

# POST /memory_save
code, body = post("memory_save", {"key": "test_key", "value": "test_value_42"})
check("POST /memory_save — no 404", code != 404, f"code={code}")
check("POST /memory_save ok or graceful error", "ok" in body)

# POST /memory_search
code, body = post("memory_search", {"query": "test_key"})
check("POST /memory_search — no 404", code != 404, f"code={code}")
check("POST /memory_search returns results or error", "results" in body or "error" in body)

# POST / with route field
code, body = post("", {"route": "status"})
check("POST / with route=status — no 404", code != 404, f"code={code}")
check("POST / with route=status returns ok", body.get("ok") is True)

# POST /free_brain (won't succeed without keys, but should not 404)
code, body = post("free_brain", {"prompt": "ping"})
check("POST /free_brain — no 404", code != 404, f"code={code}")
check("POST /free_brain returns structured response", "ok" in body, str(body)[:80])

# OPTIONS (CORS)
req = urllib.request.Request(f"{BASE}/", method="OPTIONS")
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        check("OPTIONS / returns 200", r.status == 200)
except Exception as e:
    check("OPTIONS /", False, str(e))

# ─── Summary ────────────────────────────────────────────────────────────────
passed = sum(results)
total  = len(results)
print(f"\n{'='*40}")
print(f"Results: {passed}/{total} passed")
if passed == total:
    print(f"[{PASS}] All tests passed — brain_server_v2 is healthy")
else:
    print(f"[{FAIL}] {total - passed} test(s) failed")
sys.exit(0 if passed == total else 1)
