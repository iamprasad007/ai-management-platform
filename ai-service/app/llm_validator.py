REQUIRED_FIELDS_CREATE = ["title", "assignee_name", "due_date_text"]

def validate_llm_output(data: dict):
    if not data.get("intent"):
        return ["intent"]

    if data["intent"] == "CREATE_TASK":
        missing = []
        for field in REQUIRED_FIELDS_CREATE:
            if not data.get(field):
                missing.append(field)
        return missing

    return []
