"""
env_check.py — проверка наличия всех API ключей и переменных Agent Office.
Кроссплатформенный: работает на Windows (agent_office) и Linux (Aeza VPS).
НИКОГДА не выводит значения ключей — только EXISTS/MISSING.

Запуск:
  python fixes/env_check.py
  python fixes/env_check.py --json
  python fixes/env_check.py --load-env  # загружает .env перед проверкой
"""
import os
import sys
import json
import argparse
import pathlib

REQUIRED = [
    # Генерация изображений
    ("KIE_API_KEY",              "kie.ai Seedream",             True),
    ("FAL_KEY",                  "FAL.ai FLUX",                 True),
    ("OPENAI_API_KEY",           "OpenAI",                      True),
    # LLM
    ("ANTHROPIC_API_KEY",        "Claude API",                  True),
    ("GROQ_API_KEY",             "Groq (бесплатные промпты)",   True),
    ("OPENROUTER_API_KEY",       "OpenRouter free pool",        True),
    ("POOLSIDE_API_KEY",         "Poolside Laguna (бесплатно)", True),
    ("XAI_API_KEY",              "xAI Grok",                    True),
    ("GEMINI_API_KEY",           "Google Gemini",               False),
    # Хранение
    ("B2_KEY_ID",                "Backblaze B2 Key ID",         True),
    ("B2_APP_KEY",               "Backblaze B2 App Key",        True),
    ("B2_BUCKET",                "Backblaze B2 Bucket",         False),
    # Маркетплейсы
    ("ETSY_API_KEY",             "Etsy API v3",                 True),
    ("AMAZON_SP_API_KEY",        "Amazon SP-API",               True),
    ("TIKTOK_SHOP_API_KEY",      "TikTok Shop API",             True),
    ("GELATO_API_KEY",           "Gelato POD",                  True),
    # Инструменты
    ("DYNAMIC_MOCKUPS_API_KEY",  "Dynamic Mockups",             False),
    ("PHOTOROOM_API_KEY",        "Photoroom",                   False),
    ("IDEOGRAM_API_KEY",         "Ideogram",                    False),
    # Мониторинг
    ("LANGFUSE_SECRET_KEY",      "Langfuse",                    False),
    ("LANGFUSE_PUBLIC_KEY",      "Langfuse Public",             False),
    ("HELICONE_API_KEY",         "Helicone",                    False),
    # Cloudflare Workers AI
    ("CF_ACCOUNT_ID",            "Cloudflare Account ID",       False),
    ("CF_API_TOKEN",             "Cloudflare API Token",        False),
    # Telegram bot
    ("TELEGRAM_BOT_TOKEN",       "Telegram Bot",                False),
    ("TELEGRAM_ALLOWED_IDS",     "Telegram Allowed IDs",        False),
    # Инфраструктура
    ("REDIS_URL",                "Redis",                       False),
    ("QDRANT_URL",               "Qdrant",                      False),
    ("OBSIDIAN_VAULT",           "Obsidian Vault Path",         False),
    ("BRAIN_PORT",               "Brain Server Port",           False),
]

ENV_FILES = [
    pathlib.Path.home() / "agent_office" / ".env",
    pathlib.Path.home() / "AppData" / "Local" / "agent_office" / ".env",
    pathlib.Path(__file__).parent.parent.parent / "agent_office" / ".env",
    pathlib.Path(__file__).parent.parent / ".env",
    pathlib.Path(".env"),
    pathlib.Path("/opt/sasha-core/.env"),  # Aeza VPS
]


def load_dotenv_manual(path: pathlib.Path):
    """Простая загрузка .env без зависимостей."""
    if not path.exists():
        return 0
    loaded = 0
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
                loaded += 1
    return loaded


def check():
    results = {"exists": [], "missing_required": [], "missing_optional": []}
    for key, desc, required in REQUIRED:
        val = os.environ.get(key, "")
        if val:
            results["exists"].append({"key": key, "desc": desc, "required": required})
        elif required:
            results["missing_required"].append({"key": key, "desc": desc})
        else:
            results["missing_optional"].append({"key": key, "desc": desc})
    return results


def print_results(results: dict, env_loaded: list):
    GREEN  = "\033[92m"
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    RESET  = "\033[0m"

    if env_loaded:
        print(f"{CYAN}Загружены .env:{RESET} {', '.join(str(p) for p in env_loaded)}")
        print()

    exists  = results["exists"]
    missing = results["missing_required"]
    optional = results["missing_optional"]

    print(f"{CYAN}═══ API Ключи Agent Office ═══{RESET}")
    print()

    print(f"{GREEN}НАЙДЕНЫ ({len(exists)}):{RESET}")
    for r in exists:
        star = " *" if r["required"] else ""
        print(f"  ✅ {r['key']:<30} {r['desc']}{star}")

    if missing:
        print()
        print(f"{RED}ОТСУТСТВУЮТ — КРИТИЧНО ({len(missing)}):{RESET}")
        for r in missing:
            print(f"  ❌ {r['key']:<30} {r['desc']}")

    if optional:
        print()
        print(f"{YELLOW}ОТСУТСТВУЮТ — НЕ КРИТИЧНО ({len(optional)}):{RESET}")
        for r in optional:
            print(f"  ⚠️  {r['key']:<30} {r['desc']}")

    print()
    total = len(exists) + len(missing) + len(optional)
    pct = round(len(exists) / total * 100) if total else 0
    if not missing:
        print(f"{GREEN}✅ Все обязательные ключи найдены! {len(exists)}/{total} ({pct}%){RESET}")
    else:
        print(f"{RED}❌ Отсутствуют {len(missing)} обязательных ключа!{RESET}")
        print(f"   Добавь в agent_office/.env и перезапусти")

    print()
    print("ПРАВИЛО БЕЗОПАСНОСТИ: значения ключей НЕ выводились.")


def main():
    parser = argparse.ArgumentParser(description="Agent Office API key checker")
    parser.add_argument("--json",     action="store_true", help="Вывод в JSON")
    parser.add_argument("--load-env", action="store_true", help="Загрузить .env файлы перед проверкой")
    parser.add_argument("--env-file", default="",          help="Конкретный .env файл для загрузки")
    args = parser.parse_args()

    loaded = []
    if args.env_file:
        p = pathlib.Path(args.env_file)
        n = load_dotenv_manual(p)
        if n: loaded.append(p)
    elif args.load_env:
        for p in ENV_FILES:
            n = load_dotenv_manual(p)
            if n: loaded.append(p)

    results = check()

    if args.json:
        print(json.dumps({
            "exists_count":   len(results["exists"]),
            "missing_critical": [r["key"] for r in results["missing_required"]],
            "missing_optional": [r["key"] for r in results["missing_optional"]],
            "all_critical_ok": len(results["missing_required"]) == 0,
        }, ensure_ascii=False, indent=2))
    else:
        print_results(results, loaded)

    sys.exit(0 if not results["missing_required"] else 1)


if __name__ == "__main__":
    main()
