from datetime import datetime
import parsedatetime as pdt


def parse_due_date(text: str) -> str | None:
    if not text:
        return None

    cal = pdt.Calendar()
    time_struct, parse_status = cal.parse(text)

    if parse_status == 0:
        return None

    parsed = datetime(*time_struct[:6])

    # If parsed date is in the past, assume future intent
    now = datetime.utcnow()
    if parsed < now:
        return None

    return parsed.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
