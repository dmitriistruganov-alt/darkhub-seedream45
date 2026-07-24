"""
mcp_server.py — MCP-сервер поверх brain_server_v2.
Открывает brain_server_v2 как MCP-инструменты для Claude Desktop.

Установка в claude_desktop_config.json:
{
  "mcpServers": {
    "brain": {
      "command": "python",
      "args": ["C:/Users/18186/agent_office/fixes/mcp_server.py"],
      "env": {"BRAIN_PORT": "9999"}
    }
  }
}

Запуск напрямую для теста:
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}}}' | python fixes/mcp_server.py
"""
import os, sys, json, requests, logging

logging.basicConfig(level=logging.WARNING, stream=sys.stderr,
                    format='%(asctime)s [mcp_brain] %(message)s')
log = logging.getLogger("mcp_brain")

BRAIN = f"http://localhost:{os.environ.get('BRAIN_PORT', 9999)}"

TOOLS = [
    {
        "name": "brain_free",
        "description": "Спросить у бесплатного LLM (pool из 10 OpenRouter/Groq/Poolside моделей)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":     {"type": "string", "description": "Запрос"},
                "max_tokens": {"type": "integer", "default": 2048},
                "system":     {"type": "string",  "description": "Системный промпт (опционально)"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "brain_code",
        "description": "Генерация кода через Poolside Laguna / Nvidia Nemotron (coding-оптимизированный пул)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":     {"type": "string", "description": "Задача для кодинга"},
                "max_tokens": {"type": "integer", "default": 4096},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "brain_code_review",
        "description": "Ревью кода — ищет баги, проблемы безопасности, улучшения",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Код для ревью"},
                "lang": {"type": "string", "description": "Язык (python, js, etc.)", "default": "python"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "brain_pipeline",
        "description": "Цепочка промптов — каждый шаг получает результат предыдущего через {prev}",
        "inputSchema": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Список шагов (промптов), каждый следующий может использовать {prev}",
                },
            },
            "required": ["steps"],
        },
    },
    {
        "name": "brain_memory_save",
        "description": "Сохранить информацию в долгосрочную память Agent Office",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key":   {"type": "string", "description": "Ключ записи"},
                "value": {"type": "string", "description": "Значение (текст, JSON, etc.)"},
                "tags":  {"type": "array",  "items": {"type": "string"}, "description": "Теги (опционально)"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "brain_memory_search",
        "description": "Поиск по долгосрочной памяти Agent Office",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "brain_status",
        "description": "Полный статус системы Agent Office: PM2, сервисы, мёртвые модели",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "brain_grok",
        "description": "Вызов xAI Grok напрямую (требует XAI_API_KEY)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":     {"type": "string"},
                "model":      {"type": "string", "default": "grok-3"},
                "max_tokens": {"type": "integer", "default": 2048},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "brain_gemini",
        "description": "Вызов Google Gemini (требует GEMINI_API_KEY)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt":     {"type": "string"},
                "model":      {"type": "string", "default": "gemini-2.5-pro"},
                "max_tokens": {"type": "integer", "default": 2048},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "brain_obsidian_search",
        "description": "Поиск по Obsidian vault (1373+ заметок)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "brain_hy3_search",
        "description": "Гибридный поиск HY3: Qdrant + memory.json + Obsidian vault",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос"},
            },
            "required": ["query"],
        },
    },
]

TOOL_TO_ROUTE = {
    "brain_free":           ("free_brain",      "POST"),
    "brain_code":           ("codex",           "POST"),
    "brain_code_review":    ("code_review",     "POST"),
    "brain_pipeline":       ("pipeline",        "POST"),
    "brain_memory_save":    ("memory_save",     "POST"),
    "brain_memory_search":  ("memory_search",   "POST"),
    "brain_status":         ("status",          "GET"),
    "brain_grok":           ("grok",            "POST"),
    "brain_gemini":         ("gemini",          "POST"),
    "brain_obsidian_search":("obsidian_search", "POST"),
    "brain_hy3_search":     ("hy3",             "POST"),
}

TOOL_RENAME = {
    "brain_free":  {"prompt": "prompt", "max_tokens": "max_tokens", "system": "system"},
    "brain_code":  {"prompt": "prompt", "max_tokens": "max_tokens"},
}


def call_brain(route: str, method: str, args: dict) -> str:
    url = f"{BRAIN}/{route}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=30)
        else:
            r = requests.post(url, json=args, timeout=60)
        data = r.json()
        if isinstance(data, dict):
            if data.get("text"):
                model = data.get("model", "")
                return f"[{model}]\n{data['text']}" if model else data["text"]
            if data.get("results"):
                items = data["results"]
                return json.dumps(items, ensure_ascii=False, indent=2)[:4000]
            return json.dumps(data, ensure_ascii=False, indent=2)[:4000]
        return str(data)[:4000]
    except Exception as e:
        return f"Ошибка brain_server_v2: {e}\nПроверь: pm2 logs brain-мост"


def handle_request(req: dict) -> dict:
    method = req.get("method", "")
    req_id = req.get("id")

    def resp(result):
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def err(code, msg):
        return {"jsonrpc": "2.0", "id": req_id,
                "error": {"code": code, "message": msg}}

    if method == "initialize":
        return resp({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "brain-мост MCP", "version": "2.0"},
        })

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return resp({"tools": TOOLS})

    if method == "tools/call":
        params   = req.get("params", {})
        tool     = params.get("name", "")
        args     = params.get("arguments", {})

        if tool not in TOOL_TO_ROUTE:
            return err(-32601, f"Неизвестный инструмент: {tool}")

        route, http_method = TOOL_TO_ROUTE[tool]
        result_text = call_brain(route, http_method, args)
        return resp({
            "content": [{"type": "text", "text": result_text}],
            "isError": False,
        })

    if method == "ping":
        return resp({})

    return err(-32601, f"Неизвестный метод: {method}")


def main():
    log.warning("brain-мост MCP запущен (stdio transport)")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            }) + "\n")
            sys.stdout.flush()
            continue

        result = handle_request(req)
        if result is not None:
            sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
