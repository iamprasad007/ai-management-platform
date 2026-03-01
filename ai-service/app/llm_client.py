import httpx
import json
from datetime import datetime

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL = "qwen2.5:7b-instruct"


def build_system_prompt(user_prompt: str) -> str:
    today = datetime.utcnow().date().isoformat()
    now_time = datetime.utcnow().strftime("%H:%M UTC")

    return f"""
You are a backend task extraction engine.
Today is {today}. Current time is {now_time}.

INTENTS:
1. CREATE_TASK - Create a new task.
2. UPDATE_TASK - Modify an existing task (status, priority, assignee, due date).


EXTRACTION RULES:

TITLE:
- CREATE_TASK → Generate short 3-5 word task summary.
- UPDATE_TASK → Extract the exact task name mentioned. Do NOT summarize.
  Example: "Mark UI Development as done" → title: "UI Development"

DESCRIPTION:
- Clean task details. Remove filler words.

ASSIGNEE_NAME:
- Extract explicit person identifier if mentioned.

PRIORITY:
- Extract explicit priority words if mentioned.
- If no priority mentioned, return null.

DUE_DATE_TEXT:
- Extract exact time phrase (e.g., "next Friday", "EOD tomorrow").

STATUS:
- Only for UPDATE_TASK.
- Extract values like done, completed, in progress, blocked.

OUTPUT:
Return ONLY raw JSON (no markdown, no explanation).
Missing fields must be null.

Schema:
{{
  "intent": "CREATE_TASK" | "UPDATE_TASK" | null,
  "title": string | null,
  "description": string | null,
  "assignee_name": string | null,
  "priority": "LOW" | "MEDIUM" | "HIGH" | null,
  "due_date_text": string | null,
  "status": string | null
}}

User Input: "{user_prompt}"
"""




async def extract_with_llm(prompt: str):
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client:
        response = await client.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": build_system_prompt(prompt),
                "stream": False,
                "format": "json",        # forces JSON mode
                "options": {
                    "temperature": 0     # deterministic output
                }
            }
        )

        response.raise_for_status()

        data = response.json()

        # In JSON mode, Ollama already returns parsed JSON inside "response"
        raw = data.get("response")

        if isinstance(raw, dict):
            return raw

        if isinstance(raw, str):
            return safe_parse_json(raw)

        raise ValueError("Unexpected LLM response format")


def safe_parse_json(raw_text: str):
    """
    Defensive parser for malformed output.
    Attempts to extract first JSON object.
    """
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw_text[start:end+1])
        raise ValueError("LLM returned invalid JSON")
