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
Today's date is {today}. Current time is {now_time}.

---
INTENT HIERARCHY:
1. CREATE_TASK: User wants to initiate a new work item.
   - Example: "Assign [Task] to [User] by [Date]"
2. UPDATE_STATUS: Changing state (e.g., "Mark task 101 as done").
3. REASSIGN_TASK: Moving an existing task to a new owner.

---
EXTRACTION RULES:
- **title**: A concise 3-5 word summary of the action (e.g., "Develop Login Module").
- **description**: A cleaned-up version of the task requirements. Remove conversational filler like 'Hey', 'Can you', or 'I will'.
- **assignee_name**: Extract the specific name or identifier (e.g., "MEMBER1", "Prasad").
- **priority**: Infer from keywords like "urgent", "asap", "whenever" (Defaults to MEDIUM).
- **due_date_text**: Extract the exact temporal phrase (e.g., "next Friday", "EOD tomorrow").

---
OUTPUT REQUIREMENTS:
- Return ONLY raw JSON. No markdown blocks (```json), no conversational filler.
- If a field is missing, return null.

Strict JSON schema:
{{
  "intent": "CREATE_TASK" | "UPDATE_STATUS" | "REASSIGN_TASK" | null,
  "title": string | null,
  "description": string | null,
  "assignee_name": string | null,
  "priority": "LOW" | "MEDIUM" | "HIGH",
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
