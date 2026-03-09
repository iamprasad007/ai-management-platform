from fastapi import FastAPI
from app.models import AIRequest
from app.user_client import resolve_user_from_prompt
from app.task_client import create_task, find_task_by_title, update_task, query_tasks
from app.llm_client import extract_with_llm
from app.utils import parse_due_date


app = FastAPI()

async def handle_create_task(req: AIRequest, llm_data):

    title = llm_data.get("title")
    due_text = llm_data.get("due_date_text")

    user_id, matched_name = await resolve_user_from_prompt(
        req.prompt,
        req.creatorId
    )

    if user_id:
        llm_data["assignee_name"] = matched_name

    missing = []

    if not title:
        missing.append("title")

    if not user_id:
        missing.append("assignee")

    due_result = parse_due_date(due_text, req.timezone_offset) if due_text else None

    due_date_iso = None
    if isinstance(due_result, dict):
        due_date_iso = due_result.get("dueDate")

    if not due_date_iso:
        missing.append("due_date")

    if missing:
        return {
            "status": "INCOMPLETE",
            "missing_fields": missing,
            "llm_output": llm_data
        }

    task_payload = {
        "title": title,
        "description": llm_data.get("description") or req.prompt,
        "creatorId": req.creatorId,
        "assigneeId": user_id,
        "priority": llm_data.get("priority"),
        "dueDate": due_date_iso
    }

    task_payload = {k: v for k, v in task_payload.items() if v is not None}

    print("TASK PAYLOAD:", task_payload)

    created = await create_task(task_payload)

    if created.get("error"):
        return {
            "status": "FAILED",
            "details": created["details"]
        }

    return {
        "status": "CREATED",
        "task": created["data"]
    }


async def handle_update_task(req: AIRequest, llm_data):

    title = llm_data.get("title")

    if not title:
        return {
            "status": "INCOMPLETE",
            "missing_fields": ["title"],
            "llm_output": llm_data
        }

    task = await find_task_by_title(title)

    if not task:
        return {
            "status": "NOT_FOUND",
            "details": f"Task '{title}' not found"
        }

    update_payload = {}

    if llm_data.get("status"):
        update_payload["status"] = llm_data["status"]

    if llm_data.get("priority"):
        update_payload["priority"] = llm_data["priority"]

    if llm_data.get("due_date_text"):
        due_result = parse_due_date(
            llm_data["due_date_text"],
            req.timezone_offset
        )
        if due_result and "dueDate" in due_result:
            update_payload["dueDate"] = due_result["dueDate"]

    if llm_data.get("assignee_name"):
        user_id, _ = await resolve_user_from_prompt(
            req.prompt,
            req.creatorId
        )
        if user_id:
            update_payload["assigneeId"] = user_id

    if not update_payload:
        return {
            "status": "INCOMPLETE",
            "missing_fields": ["update_fields"],
            "llm_output": llm_data
        }

    updated = await update_task(task["id"], update_payload)

    if updated.get("error"):
        return {
            "status": "FAILED",
            "details": updated["details"]
        }

    return {
        "status": "UPDATED",
        "task": updated["data"]
    }

async def handle_get_task(req: AIRequest, llm_data):

    filters = {}

    title = llm_data.get("title")
    due_text = llm_data.get("due_date_text")

    # Only apply title filter if it's likely a real task name
    if title and not due_text:
        filters["title"] = title

    if llm_data.get("status"):
        filters["status"] = llm_data["status"]

    if llm_data.get("priority"):
        filters["priority"] = llm_data["priority"]

    # Resolve assignee
    user_id, matched_name = await resolve_user_from_prompt(
        req.prompt,
        req.creatorId
    )

    if user_id:
        filters["assigneeId"] = user_id

    # Date filters
    if due_text:
        due_filter = parse_due_date(due_text, req.timezone_offset)

        if due_filter:
            filters.update(due_filter)

    print("FINAL FILTERS:", filters)

    result = await query_tasks(**filters)

    if result.get("error"):
        return {
            "status": "FAILED",
            "details": result["details"]
        }

    tasks = result["data"]

    if not tasks:
        return {
            "status": "NO_RESULTS",
            "filters": filters
        }

    return {
        "status": "SUCCESS",
        "count": len(tasks),
        "tasks": tasks
    }

INTENT_HANDLERS = {
    "CREATE_TASK": handle_create_task,
    "UPDATE_TASK": handle_update_task,
    "GET_TASK": handle_get_task,
}

@app.post("/ai/process")
async def ai_process(req: AIRequest):
    try:
        llm_data = await extract_with_llm(req.prompt)
    except Exception as e:
        return {
            "status": "LLM_TIMEOUT",
            "error": str(e)
        }

    print("LLM EXTRACTED DATA:", llm_data)

    intent = llm_data.get("intent")

    handler = INTENT_HANDLERS.get(intent)

    if not handler:
        return {
            "status": "UNSUPPORTED_INTENT",
            "llm_output": llm_data
        }

    return await handler(req, llm_data)


