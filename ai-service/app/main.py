from fastapi import FastAPI
from app.models import AIRequest
from app.extractor import extract
from app.validator import validate
from app.user_client import resolve_user_from_prompt
from app.task_client import create_task
from app.llm_client import extract_with_llm
from app.llm_validator import validate_llm_output
from app.utils import parse_due_date


app = FastAPI()


@app.post("/ai/create-task")
async def ai_create_task(req: AIRequest):

    # Extract structured data from prompt
    # extracted = extract(req.prompt)

    #Fetch structured data from LLM
    llm_data = await extract_with_llm(req.prompt)


    # Resolve assignee dynamically from prompt
    user_id, matched_name = await resolve_user_from_prompt(req.prompt)

    if not user_id:
        return {
            "status": "INCOMPLETE",
            "missing_fields": ["assignee"],
            "extracted_data": extracted.dict()
        }

    # Validate remaining required fields
    missing = validate(extracted)

    if missing:
        return {
            "status": "INCOMPLETE",
            "missing_fields": missing,
            "extracted_data": extracted.dict()
        }

    # Create task payload
    task_payload = {
        "title": extracted.title,
        "description": extracted.description,
        "creatorId": req.creatorId,
        "assigneeId": user_id,
        "priority": extracted.priority or "MEDIUM",
        "dueDate": extracted.due_date_iso
    }

    # Call task-service
    result = await create_task(task_payload)

    if result["error"]:
        return {
            "status": "FAILED",
            "error_code": result["details"].get("code"),
            "message": result["details"].get("message")
        }

    return {
        "status": "CREATED",
        "task": result["data"]
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

    missing = validate_llm_output(llm_data)

    if missing:
        return {
            "status": "INCOMPLETE",
            "missing_fields": missing,
            "llm_output": llm_data
        }

    intent = llm_data.get("intent")

    if intent == "CREATE_TASK":

        title = llm_data.get("title")
        assignee_name = llm_data.get("assignee_name")
        due_text = llm_data.get("due_date_text")

        missing = []

        if not title:
            missing.append("title")

        if not assignee_name:
            missing.append("assignee")

        # Convert due date BEFORE checking missing
        due_date_iso = parse_due_date(due_text) if due_text else None
        if not due_date_iso:
            missing.append("due_date")

        if missing:
            return {
                "status": "INCOMPLETE",
                "missing_fields": missing,
                "llm_output": llm_data
            }

        # Resolve assignee AFTER basic validation
        user_id, _ = await resolve_user_from_prompt(req.prompt)
        if not user_id:
            return {
                "status": "INCOMPLETE",
                "missing_fields": ["assignee"],
                "llm_output": llm_data
            }

        task_payload = {
            "title": title,
            "description": llm_data.get("description") or req.prompt,
            "creatorId": req.creatorId,
            "assigneeId": user_id,
            "priority": llm_data.get("priority") or "MEDIUM",
            "dueDate": due_date_iso
        }

        print("TASK PAYLOAD:", task_payload)

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


    return {
        "status": "UNSUPPORTED_INTENT",
        "llm_output": llm_data
    }
