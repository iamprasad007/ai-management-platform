import httpx
import json
from datetime import datetime

OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL = "qwen2.5:7b-instruct"


def build_system_prompt(user_prompt: str) -> str:
    today = datetime.utcnow().date().isoformat()

    return f"""
You are a backend task extraction engine.

Today's date is {today} (UTC).

INTENT RULES:

1) CREATE_TASK
   - User is creating a new task
   - Keywords: create, assign, add task, new task, prepare, build, develop
   - Example: "Assign login module to MEMBER1 by Friday"

2) UPDATE_STATUS
   - User is changing status of an existing task
   - Keywords: mark done, complete task, move to in progress, update status

3) REASSIGN_TASK
   - User explicitly says to reassign or change assignee of an EXISTING task
   - Keywords: reassign, change assignee, move task to someone else
   - Must refer to an existing task

If user is creating a task and assigning someone,
the intent is ALWAYS CREATE_TASK.

Return ONLY valid JSON.
Do NOT include markdown.
Do NOT include explanations.

Strict JSON schema:

{{
  "intent": "CREATE_TASK" | "UPDATE_STATUS" | "REASSIGN_TASK" | null,
  "title": string | null,
  "description": string | null,
  "assignee_name": string | null,
  "priority": "LOW" | "MEDIUM" | "HIGH" | null,
  "due_date_text": string | null,
  "status": string | null
}}

User Input:
{user_prompt}
"""



async def extract_with_llm(prompt: str):
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0)) as client:
        response = await client.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": build_system_prompt(prompt),
                "stream": False,
                "format": "json",        # 🔥 forces JSON mode
                "options": {
                    "temperature": 0     # 🔥 deterministic output
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
