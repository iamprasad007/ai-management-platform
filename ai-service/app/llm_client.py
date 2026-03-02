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

INTENT SELECTION RULES:
- If user is creating or assigning a new task → CREATE_TASK.
- If user is modifying an existing task → UPDATE_TASK.
- If unclear → intent must be null.

EXTRACTION RULES:

TITLE:
CREATE_TASK:
- Extract task title from user input.
- If no clear task title is present, return null.
UPDATE_TASK:
- Extract the phrase referring to the existing task.
- This is usually the noun phrase between action verb and status/priority.
- Example:
  "Mark Login API implementation as completed"
  → title: "Login API implementation"
  "Update priority of Payment Service task to high"
  → title: "Payment Service task"
  "Reassign Backend cleanup to Rahul"
  → title: "Backend cleanup"
- Do NOT summarize or shorten.
- Only return null if no task reference exists.

DESCRIPTION:
- Extract only details explicitly mentioned.
- If none → null.

ASSIGNEE_NAME:
- Extract explicit person identifier if mentioned.
- If none → null.

PRIORITY:
- Map words:
  urgent/asap/high → HIGH
  low/later/whenever → LOW
  normal/medium → MEDIUM
- If not mentioned → null.

DUE_DATE_TEXT:
- Extract exact time phrase if explicitly mentioned.
- If not mentioned → null.

STATUS:
- Only for UPDATE_TASK.
- Map to one of:
  "TODO", "IN_PROGRESS", "COMPLETED", "BLOCKED"
- If not mentioned → null.

STRICT RULES:
- Do NOT invent information.
- Do NOT assume defaults.
- If a field is not explicitly stated, return null.

OUTPUT:
Return ONLY raw JSON.

Schema:
{{
  "intent": "CREATE_TASK" | "UPDATE_TASK" | null,
  "title": string | null,
  "description": string | null,
  "assignee_name": string | null,
  "priority": "LOW" | "MEDIUM" | "HIGH" | null,
  "due_date_text": string | null,
  "status": "TODO" | "IN_PROGRESS" | "COMPLETED" | "BLOCKED" | null
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
