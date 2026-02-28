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
    user_id, matched_name = await resolve_user_from_prompt(req.prompt, req.creatorId)

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

    # Handle other intents or unsupported ones
    return {
        "status": "UNSUPPORTED_INTENT",
        "llm_output": llm_data
    }
