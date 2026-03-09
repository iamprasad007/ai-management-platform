import httpx
from app.config import GROQ_API_KEY

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-20b"

client = httpx.AsyncClient(timeout=60.0)


TASK_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "task_extraction",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": ["string", "null"],
                    "enum": ["CREATE_TASK", "UPDATE_TASK", "GET_TASK", None] 
                },
                "title": {"type": ["string", "null"]},
                "description": {"type": ["string", "null"]},
                "assignee_name": {"type": ["string", "null"]},
                "priority": {
                    "type": ["string", "null"],
                    "enum": ["LOW", "MEDIUM", "HIGH", None]
                },
                "due_date_text": {"type": ["string", "null"]},
                "status": {
                    "type": ["string", "null"],
                    "enum": ["TODO", "IN_PROGRESS", "COMPLETED", None]
                }
            },
            "required": [
                "intent",
                "title",
                "description",
                "assignee_name",
                "priority",
                "due_date_text",
                "status"
            ],
            "additionalProperties": False
        }
    }
}


import json

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
                {"role": "system", "content": "Extract task management information from user text."},
                {"role": "user", "content": prompt}
            ],
            "response_format": TASK_SCHEMA,
            "temperature": 0
        }
    )

    response.raise_for_status()
    data = response.json()

    raw = data["choices"][0]["message"]["content"]

    return json.loads(raw)  