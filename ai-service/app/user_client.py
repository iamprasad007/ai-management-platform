import httpx
import re
from app.config import USER_SERVICE_URL

async def resolve_user_from_prompt(prompt: str):
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        response = await client.get(f"{USER_SERVICE_URL}/users")
        response.raise_for_status()
        users = response.json()

    for user in users:
        pattern = r"\b" + re.escape(user["name"]) + r"\b"
        if re.search(pattern, prompt, re.IGNORECASE):
            return user["id"], user["name"]

    return None, None
