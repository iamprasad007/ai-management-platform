from datetime import datetime, timedelta, timezone
import parsedatetime as pdt


def parse_due_date(text: str, offset_minutes: int = 0):

    if not text:
        return None

    text_norm = text.lower().strip()

    user_now = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)

    # -------- RANGE HANDLING --------

    if text_norm == "today":
        start = user_now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        return {
            "dueStart": start.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "dueEnd": end.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }

    if text_norm == "tomorrow":
        start = (user_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        return {
            "dueStart": start.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "dueEnd": end.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }

    if text_norm in ["this week", "this_week"]:
        weekday = user_now.weekday()
        start = (user_now - timedelta(days=weekday)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=7)

        return {
            "dueStart": start.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "dueEnd": end.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }

    if text_norm in ["next week", "next_week"]:
        weekday = user_now.weekday()

        start_of_this_week = (user_now - timedelta(days=weekday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        start = start_of_this_week + timedelta(days=7)
        end = start + timedelta(days=7)

        return {
            "dueStart": start.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "dueEnd": end.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }

    if text_norm == "overdue":
        return {
            "dueEnd": user_now.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }

    # -------- NORMAL DATE PARSING --------

    cal = pdt.Calendar()

    time_struct, parse_status = cal.parse(text, sourceTime=user_now.replace(tzinfo=None))

    if parse_status == 0:
        return None

    parsed_naive = datetime(*time_struct[:6])

    if parse_status == 1:
        parsed_naive = parsed_naive.replace(hour=23, minute=59, second=59)

    user_tz = timezone(timedelta(minutes=offset_minutes))
    parsed_user_tz = parsed_naive.replace(tzinfo=user_tz)

    utc_dt = parsed_user_tz.astimezone(timezone.utc)

    if utc_dt < datetime.now(timezone.utc):
        if parse_status == 2:
            utc_dt += timedelta(days=1)
        elif utc_dt.date() < datetime.now(timezone.utc).date():
            return None

    return {
        "dueDate": utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    }