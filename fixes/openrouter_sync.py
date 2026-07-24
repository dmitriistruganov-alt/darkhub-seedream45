"""
openrouter_sync.py — авто-обновление пула бесплатных моделей с OpenRouter API.
Запуск: python fixes/openrouter_sync.py [--dry-run] [--update-server]

Алгоритм:
1. Запросить GET https://openrouter.ai/api/v1/models
2. Отфильтровать модели с :free суффиксом и pricing.prompt == "0"
3. Сравнить с текущим FREE_POOL в brain_server_v2.py
4. Вывести отчёт (добавленные / удалённые модели)
5. Опционально обновить brain_server_v2.py и перезапустить через PM2
"""
import os, sys, re, json, requests, subprocess
from pathlib import Path
from dotenv import load_dotenv

for _env in [
    Path.home() / "agent_office" / ".env",
    Path("/opt/sasha-core/.env"),
    Path(__file__).parent.parent.parent / "agent_office" / ".env",
    Path(__file__).parent.parent / ".env",
    Path(".env"),
]:
    if _env.exists():
        load_dotenv(_env)
        break
load_dotenv()

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
SERVER_FILE    = Path(__file__).parent / "brain_server_v2.py"

# Models to NEVER include regardless of :free status (known bad actors)
BLOCKLIST = {
    "qwen/qwen3-235b-a22b",     # стала платной 22.07.2026
    "qwen/qwen3-235b-a22b:free",
    "openai/o1-mini:free",      # rate limits too aggressive
}

# Always include these even if API doesn't show :free (direct arrangements)
ALWAYS_INCLUDE = [
    ("groq-llama",      "meta-llama/llama-3.3-70b-versatile", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    ("poolside-direct", "poolside/laguna-s-2.1",              "https://inference.poolside.ai/v1", "POOLSIDE_API_KEY"),
]


def fetch_free_models(api_key: str) -> list[dict]:
    """Fetch all free models from OpenRouter."""
    if not api_key:
        print("WARN: OPENROUTER_API_KEY not set — skipping OpenRouter fetch")
        return []
    try:
        r = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        r.raise_for_status()
        models = r.json().get("data", [])
        free = []
        for m in models:
            mid = m.get("id", "")
            pricing = m.get("pricing", {})
            prompt_price = float(pricing.get("prompt", "1") or "1")
            is_free = mid.endswith(":free") or prompt_price == 0.0
            if is_free and mid not in BLOCKLIST:
                free.append({
                    "id":      mid,
                    "name":    m.get("name", mid),
                    "context": m.get("context_length", 0),
                })
        return free
    except Exception as e:
        print(f"ERROR fetching OpenRouter models: {e}")
        return []


def current_pool_ids() -> set[str]:
    """Extract current model IDs from brain_server_v2.py FREE_POOL."""
    if not SERVER_FILE.exists():
        return set()
    src = SERVER_FILE.read_text(encoding="utf-8")
    return set(re.findall(r'"([^"]+:free)"', src))


def priority_name(model_id: str) -> str:
    """Generate a short name from model ID."""
    parts = model_id.replace(":free", "").split("/")
    provider = parts[0].split("-")[0][:10]
    model    = parts[-1][:25]
    return f"{provider}-{model}".lower().replace(".", "-")


def build_new_pool(free_models: list[dict]) -> list[tuple]:
    """Build updated FREE_POOL list, prioritizing known good models."""
    PRIORITY_PREFIXES = [
        "nvidia/nemotron",
        "poolside/laguna",
        "google/gemma-4",
        "openai/gpt-oss",
        "meta-llama",
        "google/gemma",
        "mistralai",
        "cohere",
    ]
    ordered = []
    remaining = list(free_models)

    for prefix in PRIORITY_PREFIXES:
        for m in remaining[:]:
            if m["id"].startswith(prefix):
                ordered.append(m)
                remaining.remove(m)

    ordered.extend(remaining[:15 - len(ordered)])
    pool = []
    for m in ordered[:15]:
        name = priority_name(m["id"])
        pool.append((name, m["id"], "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"))

    return pool + ALWAYS_INCLUDE


def update_server_file(new_pool: list[tuple], dry: bool):
    """Patch FREE_POOL in brain_server_v2.py."""
    src = SERVER_FILE.read_text(encoding="utf-8")

    pool_lines = "\n".join(
        f'    ("{name}", "{mid}", "{base}", "{key}"),'
        for name, mid, base, key in new_pool
    )
    new_block = f"FREE_POOL = [\n    # (name, model_id, base_url, api_key_env)\n{pool_lines}\n]"

    updated = re.sub(
        r'FREE_POOL = \[.*?\]',
        new_block,
        src,
        flags=re.DOTALL,
    )

    if updated == src:
        print("  INFO: FREE_POOL not found or unchanged")
        return

    if dry:
        print("\n[DRY RUN] Would update FREE_POOL:")
        for entry in new_pool:
            print(f"  {entry[1]}")
        return

    bak = SERVER_FILE.with_suffix(".py.bak_sync")
    bak.write_text(src, encoding="utf-8")
    SERVER_FILE.write_text(updated, encoding="utf-8")
    print(f"  Обновлён {SERVER_FILE}")
    print(f"  Backup: {bak}")


def restart_server():
    try:
        r = subprocess.run(["pm2", "restart", "brain-мост"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            print("  PM2: brain-мост перезапущен")
        else:
            print(f"  PM2 restart failed: {r.stderr[:200]}")
    except Exception as e:
        print(f"  PM2 restart error: {e}")


def main():
    dry          = "--dry-run" in sys.argv
    update_srv   = "--update-server" in sys.argv

    print(f"openrouter_sync {'[DRY RUN]' if dry else ''}")
    print(f"OpenRouter key: {'SET' if OPENROUTER_KEY else 'MISSING'}")

    free_models  = fetch_free_models(OPENROUTER_KEY)
    current_ids  = current_pool_ids()
    new_ids      = {m["id"] for m in free_models}

    added   = new_ids - current_ids
    removed = current_ids - new_ids - {m.replace(":free", "") for m in BLOCKLIST}

    print(f"\nТекущий пул:  {len(current_ids)} моделей")
    print(f"OpenRouter:   {len(free_models)} бесплатных")
    print(f"Добавить:     {len(added)}")
    print(f"Удалить:      {len(removed)}")

    if added:
        print("\n  + Новые модели:")
        for mid in sorted(added)[:10]:
            print(f"    {mid}")

    if removed:
        print("\n  - Удалить (стали платными):")
        for mid in sorted(removed):
            print(f"    {mid}")

    if not free_models:
        print("\nНет данных от OpenRouter — ничего не меняем")
        return

    new_pool = build_new_pool(free_models)
    print(f"\nНовый пул ({len(new_pool)} моделей):")
    for name, mid, base, _ in new_pool:
        print(f"  {name:30} {mid}")

    if update_srv:
        print("\nОбновляем brain_server_v2.py...")
        update_server_file(new_pool, dry)
        if not dry:
            restart_server()
    else:
        print("\n[INFO] Запусти с --update-server чтобы применить изменения")

    # Save report to brain memory
    if not dry:
        try:
            report = {
                "added":   list(added),
                "removed": list(removed),
                "pool":    [m[1] for m in new_pool],
            }
            requests.post("http://localhost:9999/memory_save",
                          json={"key": "openrouter_sync/last", "value": json.dumps(report)},
                          timeout=5)
        except Exception:
            pass


if __name__ == "__main__":
    main()
