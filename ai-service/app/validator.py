def validate(extracted):
    missing = []

    if not extracted.title:
        missing.append("title")

    if not extracted.due_date_iso:
        missing.append("due_date")

    return missing
