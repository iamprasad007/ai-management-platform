from fastapi import FastAPI
from app.models import AIRequest
from app.user_client import resolve_user_from_prompt
from app.task_client import create_task, find_task_by_title, update_task
from app.llm_client import extract_with_llm
from app.utils import parse_due_date


app = FastAPI()


@app.post("/ai/process")
async def ai_process(req: AIRequest):
    try:
        # 1. Fetch structured data from LLM
        llm_data = await extract_with_llm(req.prompt)
    except Exception as e:
        return {
            "status": "LLM_TIMEOUT",
            "error": str(e)
        }

    # 2. Extract initial intent and data
    intent = llm_data.get("intent")
    
    if intent == "CREATE_TASK":
        title = llm_data.get("title")
        due_text = llm_data.get("due_date_text")

        # 3. RESOLVE USER (Handles names AND "me/myself" via req.creatorId)
        user_id, matched_name = await resolve_user_from_prompt(req.prompt, req.creatorId)
        
        # Patch llm_data so validator sees the assignee is found
        if user_id:
            llm_data["assignee_name"] = matched_name

        # 4. VALIDATION LOGIC
        missing = []
        if not title:
            missing.append("title")
        
        # If user_id is missing, the assignee is truly unknown
        if not user_id:
            missing.append("assignee")

        # Convert due date using timezone offset
        due_date_iso = parse_due_date(due_text, req.timezone_offset) if due_text else None
        if not due_date_iso:
            missing.append("due_date")

        # If any fields are still missing after resolution/parsing, return INCOMPLETE
        if missing:
            return {
                "status": "INCOMPLETE",
                "missing_fields": missing,
                "llm_output": llm_data
            }

        # 5. CREATE TASK PAYLOAD
        task_payload = {
            "title": title,
            "description": llm_data.get("description") or req.prompt,
            "creatorId": req.creatorId,
            "assigneeId": user_id,
            "priority": llm_data.get("priority") or "MEDIUM",
            "dueDate": due_date_iso
        }

        print("TASK PAYLOAD:", task_payload)

        # 6. CALL TASK SERVICE
        created = await create_task(task_payload)

        if created.get("error"):
            return {
                "status": "FAILED",
                "error_code": created["details"].get("code"),
                "message": created["details"].get("message"),
                "payload_sent": task_payload
            }

        return {
            "status": "CREATED",
            "task": created["data"]
        }
    
    elif intent == "UPDATE_TASK":

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

        # Status
        if llm_data.get("status"):
            update_payload["status"] = llm_data["status"]

        # Priority
        if llm_data.get("priority"):
            update_payload["priority"] = llm_data["priority"]

        # Due Date
        if llm_data.get("due_date_text"):
            due_iso = parse_due_date(
                llm_data["due_date_text"],
                req.timezone_offset
            )
            if due_iso:
                update_payload["dueDate"] = due_iso

        # Assignee
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


    # Handle other intents or unsupported ones
    return {
        "status": "UNSUPPORTED_INTENT",
        "llm_output": llm_data
    }
