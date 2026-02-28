import re
import httpx
from app.config import USER_SERVICE_URL

async def resolve_user_from_prompt(prompt: str, creator_id: str = None):
    
    # 1. Handle Self-References (I, me, myself, my)
    # \b ensures we match whole words only
    self_refs = [r"\bme\b", r"\bmyself\b", r"\bi\b", r"\bmy\b"]
    if any(re.search(ref, prompt, re.IGNORECASE) for ref in self_refs):
        return creator_id, "Self"

    # 2. Fetch User List from Microservice
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.get(f"{USER_SERVICE_URL}/users")
            response.raise_for_status()
            users = response.json()
    except Exception as e:
        print(f"Error fetching users: {e}")
        return None, None

    # 3. Match against Database Names
    for user in users:
        # Match name as a whole word to avoid partial matches
        pattern = r"\b" + re.escape(user["name"]) + r"\b"
        if re.search(pattern, prompt, re.IGNORECASE):
            return user["id"], user["name"]

    return None, None