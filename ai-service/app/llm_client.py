import httpx
import json
from datetime import datetime
from app.config import GROQ_API_KEY

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"
GROQ_API_KEY = GROQ_API_KEY


def build_system_prompt(user_prompt: str) -> str:
    today = datetime.utcnow().date().isoformat()
    now_time = datetime.utcnow().strftime("%H:%M UTC")

    return f"""
System: Backend Task Extractor. Today: {today}, Time: {now_time}.
Rules: 
1. Intents: CREATE_TASK (new), UPDATE_TASK (modifying existing), or null.
2. Title: Extracted name/reference. No summarization. Null if missing.
3. Priority: Map [urgent/asap/high] -> HIGH, [low/later] -> LOW, [normal/medium] -> MEDIUM.
4. Status (Update only): Map to [TODO, IN_PROGRESS, COMPLETED]. 
5. Extraction: No defaults. Null for any field (desc, assignee, due_date_text) not explicitly stated.
6. Edge Cases: Include relative time phrases (e.g., "by tomorrow") in due_date_text.

Output: Raw JSON only. No text/reasoning.

Schema:
{{
  "intent": "CREATE_TASK"|"UPDATE_TASK"|null,
  "title": string|null,
  "description": string|null,
  "assignee_name": string|null,
  "priority": "LOW"|"MEDIUM"|"HIGH"|null,
  "due_date_text": string|null,
  "status": "TODO"|"IN_PROGRESS"|"COMPLETED"|null
}}

User Input: "{user_prompt}"
"""

client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))


async def extract_with_llm(prompt: str):
    response = await client.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "user", "content": build_system_prompt(prompt)}
            ],
            "temperature": 0,
            "include_reasoning": False
        }
    )

    print("LLM RAW RESPONSE:", response.text)
    response.raise_for_status()

    data = response.json()

    raw = data["choices"][0]["message"]["content"]

    return safe_parse_json(raw)



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
