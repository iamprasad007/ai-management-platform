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

async def find_task_by_title(title: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{TASK_SERVICE_URL}/tasks",
            params={"title": title}
        )

    if response.status_code >= 400:
        return None

    tasks = response.json()
    return tasks[0] if tasks else None


async def update_task(task_id: str, payload: dict):
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{TASK_SERVICE_URL}/tasks/{task_id}",
            json=payload
        )

    # Try to parse JSON safely
    try:
        body = response.json()
    except Exception:
        body = {"message": response.text}

    if response.status_code >= 400:
        return {
            "error": True,
            "details": body,
            "status_code": response.status_code
        }

    return {
        "error": False,
        "data": body
    }

