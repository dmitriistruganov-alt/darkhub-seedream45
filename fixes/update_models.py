"""
update_models.py — патч конфигурации agent_office для замены мёртвых моделей.

Запуск: python fixes/update_models.py [--dry-run]
Автоматически находит config.py в agent_office/core/ и обновляет FREE_MODELS.

Верифицированные рабочие модели OpenRouter (2026-07-24):
  Платные → удалить: qwen/qwen3-235b-a22b:free (стала платной ~22.07.2026)
  Новые бесплатные: см. NEW_FREE_MODELS ниже
"""
import os, sys, re, json, shutil
from pathlib import Path
from datetime import datetime

# ─── Актуальный пул бесплатных моделей ──────────────────────────────────────
NEW_FREE_MODELS = [
    # (provider_name, openrouter_model_id, notes)
    ("nvidia-nemotron-ultra",  "nvidia/nemotron-3-ultra-550b-a55b:free",   "550B MoE, топ reasoning"),
    ("nvidia-nemotron-super",  "nvidia/nemotron-3-super-120b-a12b:free",   "120B, хорош для кода"),
    ("poolside-laguna-s",      "poolside/laguna-s-2.1:free",               "118B, SWE-bench 78.5%"),
    ("poolside-laguna-xs",     "poolside/laguna-xs-2.1:free",              "XS версия, быстрее"),
    ("poolside-laguna-m",      "poolside/laguna-m.1:free",                 "M, medium coding"),
    ("gemma-4-31b",            "google/gemma-4-31b-it:free",               "Google, 31B"),
    ("gemma-4-26b",            "google/gemma-4-26b-a4b-it:free",           "Google MoE, 26B"),
    ("openai-gpt-oss-20b",    "openai/gpt-oss-20b:free",                  "OpenAI OSS, 20B"),
]

DEAD_MODELS = [
    "qwen/qwen3-235b-a22b:free",   # стала платной ~22.07.2026
    "qwen/qwen3-235b-a22b",        # любые варианты без суффикса
]

GROQ_MODELS = {
    "groq-llama-70b":   "meta-llama/llama-3.3-70b-versatile",
    "groq-compound":    "compound-beta",
}

POOLSIDE_DIRECT = {
    "poolside-direct-s":  "poolside/laguna-s-2.1",
    "poolside-direct-xs": "poolside/laguna-xs-2.1",
}


def find_agent_office() -> Path | None:
    """Locate agent_office directory relative to script or cwd."""
    candidates = [
        Path.home() / "agent_office",                            # C:\Users\18186\agent_office (Windows)
        Path("/opt/sasha-core/agent_office"),                    # Aeza VPS
        Path(__file__).parent.parent.parent / "agent_office",   # sibling of repo
        Path.cwd() / "agent_office",
        Path.cwd().parent / "agent_office",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def find_config(agent_office: Path) -> Path | None:
    for name in ["core/config.py", "config.py", "core/models.py", "models.py"]:
        p = agent_office / name
        if p.exists():
            return p
    return None


def backup(path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = path.with_suffix(f".py.bak_{ts}")
    shutil.copy2(path, bak)
    print(f"  backup → {bak}")
    return bak


def patch_python_config(path: Path, dry: bool):
    src = path.read_text(encoding="utf-8")
    changed = src

    # Remove dead model references
    for dead in DEAD_MODELS:
        escaped = re.escape(dead)
        # remove lines containing the dead model
        changed = re.sub(rf'^\s*.*{escaped}.*\n', '', changed, flags=re.MULTILINE)

    if changed != src:
        print(f"  Удалено упоминаний мёртвых моделей: {src.count(DEAD_MODELS[0])}")

    new_entries = "\n".join(
        f'    "{m_id}",  # {note}' for _, m_id, note in NEW_FREE_MODELS
    )

    # Try to find FREE_MODELS list and append if missing
    if "FREE_MODELS" in changed:
        # Look for the list and add new entries before the closing ]
        pattern = r'(FREE_MODELS\s*=\s*\[)(.*?)(\])'
        m = re.search(pattern, changed, re.DOTALL)
        if m:
            existing = m.group(2)
            # Only add models not already present
            additions = []
            for _, m_id, note in NEW_FREE_MODELS:
                if m_id not in existing:
                    additions.append(f'    "{m_id}",  # {note}')
            if additions:
                new_list = existing.rstrip() + "\n" + "\n".join(additions) + "\n"
                changed = changed[:m.start(2)] + new_list + changed[m.end(2):]
                print(f"  Добавлено {len(additions)} новых моделей в FREE_MODELS")
            else:
                print("  FREE_MODELS уже содержит актуальные модели")
    else:
        print("  FREE_MODELS не найден — добавляем блок в конец файла")
        block = f"""

# ─── Free model pool (updated {datetime.now().strftime('%Y-%m-%d')}) ──────────────────
FREE_MODELS = [
{new_entries}
]
"""
        changed += block

    if dry:
        print("\n[DRY RUN] Изменения НЕ записаны. Diff preview:")
        import difflib
        diff = difflib.unified_diff(src.splitlines(), changed.splitlines(), lineterm="")
        print("\n".join(list(diff)[:60]))
        return

    backup(path)
    path.write_text(changed, encoding="utf-8")
    print(f"  Записано: {path}")


def write_free_brain_patch(agent_office: Path, dry: bool):
    """Write a small patch module that overrides the model list in free_brain.py."""
    target = agent_office / "core" / "free_brain_models.py"
    content = f'''"""
free_brain_models.py — актуальный пул бесплатных моделей (auto-generated {datetime.now().strftime('%Y-%m-%d')}).
Импортируй в free_brain.py:
    from core.free_brain_models import OPENROUTER_FREE, GROQ_MODELS, POOLSIDE_MODELS
"""

OPENROUTER_FREE = [
'''
    for name, m_id, note in NEW_FREE_MODELS:
        content += f'    ("{name}", "{m_id}"),  # {note}\n'
    content += ']\n\n'

    content += 'GROQ_MODELS = {\n'
    for k, v in GROQ_MODELS.items():
        content += f'    "{k}": "{v}",\n'
    content += '}\n\n'

    content += 'POOLSIDE_MODELS = {\n'
    for k, v in POOLSIDE_DIRECT.items():
        content += f'    "{k}": "{v}",\n'
    content += '}\n\n'

    content += '# Circuit-breaker skip list (populated at runtime)\nDEAD_MODELS_STATIC = [\n'
    for d in DEAD_MODELS:
        content += f'    "{d}",\n'
    content += ']\n'

    if dry:
        print(f"\n[DRY RUN] Would write: {target}")
        print(content[:400])
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"  Написан патч: {target}")


def main():
    dry = "--dry-run" in sys.argv
    print(f"update_models.py {'[DRY RUN]' if dry else ''}")

    ao = find_agent_office()
    if not ao:
        print("WARN: agent_office не найден — только запись patch-модуля рядом со скриптом")
        ao = Path(__file__).parent
    else:
        print(f"  agent_office: {ao}")

    config = find_config(ao)
    if config:
        print(f"  config: {config}")
        patch_python_config(config, dry)
    else:
        print("  config.py не найден — пропускаем патч конфига")

    write_free_brain_patch(ao, dry)

    print("\nГотово. Следующие шаги:")
    print("  1. Перезапустить brain_server_v2.py: pm2 restart brain-мост")
    print("  2. Перезапустить free_brain worker: pm2 restart free-brain")
    print("  3. Проверить: curl http://localhost:9999/status")


if __name__ == "__main__":
    main()
