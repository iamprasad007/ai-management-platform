import re
from datetime import datetime, timedelta
from dateutil import parser
from app.models import ExtractedTask


WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def parse_relative_date(text: str):
    text = text.lower()
    today = datetime.utcnow()

    # --- in X days ---
    match = re.search(r"in (\d+) day", text)
    if match:
        days = int(match.group(1))
        due = today + timedelta(days=days)
        return due.replace(hour=0, minute=0, second=0, microsecond=0)

    # --- by Monday ---
    for day_name, day_num in WEEKDAYS.items():
        if f"by {day_name}" in text or day_name in text:
            days_ahead = day_num - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            due = today + timedelta(days=days_ahead)
            return due.replace(hour=0, minute=0, second=0, microsecond=0)

    # --- explicit date ---
    try:
        parsed = parser.parse(text, fuzzy=True)
        if parsed > today:
            return parsed.replace(hour=0, minute=0, second=0, microsecond=0)
    except Exception:
        pass

    return None


def extract(prompt: str) -> ExtractedTask:
    prompt_lower = prompt.lower()

    extracted = ExtractedTask()
    extracted.description = prompt

    # --- Title ---
    extracted.title = prompt.split(" to ")[0].strip().capitalize()

    # --- Assignee name detection ---
    name_match = re.search(r"to ([A-Z][a-z]+)", prompt)
    if name_match:
        extracted.assignee_name = name_match.group(1)

    # --- Priority ---
    if "urgent" in prompt_lower:
        extracted.priority = "HIGH"
    elif "low priority" in prompt_lower:
        extracted.priority = "LOW"
    else:
        extracted.priority = "MEDIUM"

    # --- Due date ---
    due = parse_relative_date(prompt)
    if due:
        extracted.due_date_iso = due.isoformat() + "Z"
        extracted.due_date_text = due.strftime("%Y-%m-%d")

    return extracted
