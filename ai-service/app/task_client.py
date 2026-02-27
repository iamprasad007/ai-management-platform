import httpx
from app.config import TASK_SERVICE_URL

# async def create_task(payload):
#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             f"{TASK_SERVICE_URL}/tasks",
#             json=payload
#         )
#         response.raise_for_status()
#         return response.json()

# async def create_task(payload: dict):
#     async with httpx.AsyncClient() as client:
#         response = await client.post(
#             "http://task-service:8081/tasks",
#             json=payload
#         )

#     if response.status_code >= 400:
#         try:
#             error_data = response.json()
#             return {
#                 "error": True,
#                 "code": error_data.get("code"),
#                 "message": error_data.get("message")
#             }
#         except:
#             return {
#                 "error": True,
#                 "code": "UNKNOWN_ERROR",
#                 "message": response.text
#             }

#     return response.json()

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