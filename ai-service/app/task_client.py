import httpx
from app.config import TASK_SERVICE_URL
from app.user_client import resolve_user_from_prompt


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

async def query_tasks(prompt: str = None, creator_id: str = None, **filters):

    # Resolve assignee from natural language
    if prompt:
        assignee_id, assignee_name = await resolve_user_from_prompt(prompt, creator_id)

        if assignee_id:
            filters["assigneeId"] = assignee_id

    # Remove None values
    params = {k: v for k, v in filters.items() if v is not None}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{TASK_SERVICE_URL}/tasks",
            params=params
        )

    try:
        body = response.json()
    except Exception:
        body = {"message": response.text}

    if response.status_code >= 400:
        return {
            "error": True,
            "status_code": response.status_code,
            "details": body
        }

    return {
        "error": False,
        "data": body
    }