import re
import httpx
from app.config import USER_SERVICE_URL


async def resolve_user_from_prompt(prompt: str, creator_id: str = None):

    # Handle self references
    self_refs = [r"\bme\b", r"\bmyself\b", r"\bi\b", r"\bmy\b"]
    if any(re.search(ref, prompt, re.IGNORECASE) for ref in self_refs):
        return creator_id, "Self"

    # Extract possible name
    match = re.search(r"(?:for|to)\s+([A-Za-z]+)", prompt, re.IGNORECASE)
    if not match:
        return None, None

    name = match.group(1)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{USER_SERVICE_URL}/users/search",
                params={"q": name}
            )
            response.raise_for_status()
            users = response.json()

            if users:
                return users[0]["id"], users[0]["name"]

    except Exception as e:
        print(f"User search error: {e}")

    return None, None