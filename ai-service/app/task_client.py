import httpx
from app.config import TASK_SERVICE_URL

async def create_task(payload: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{TASK_SERVICE_URL}/tasks",
            json=payload
        )

    if response.status_code >= 400:
        return {
            "error": True,
            "status_code": response.status_code,
            "details": response.json()
        }

    return {
        "error": False,
        "data": response.json()
    }