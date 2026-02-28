from datetime import datetime, timedelta, timezone
import parsedatetime as pdt

def parse_due_date(text: str, offset_minutes: int = 0) -> str | None:
    if not text:
        return None

    cal = pdt.Calendar()
    
    # 1. Calculate User's Local Time
    # Server is UTC, so we apply the offset to see what time it is for the user.
    user_now = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    
    # 2. Parse relative to User's Time
    # We remove tzinfo temporarily because parsedatetime works with naive datetimes
    time_struct, parse_status = cal.parse(text, sourceTime=user_now.replace(tzinfo=None))

    if parse_status == 0:
        return None

    parsed_naive = datetime(*time_struct[:6])

    # 3. Handle Date-only vs Date-Time
    if parse_status == 1: # User said "Friday" -> set to end of their day
        parsed_naive = parsed_naive.replace(hour=23, minute=59, second=59)
    
    # 4. Convert User's parsed time back to UTC
    # First, treat parsed_naive as the user's local time
    user_tz = timezone(timedelta(minutes=offset_minutes))
    parsed_user_tz = parsed_naive.replace(tzinfo=user_tz)
    
    # Convert to UTC
    utc_dt = parsed_user_tz.astimezone(timezone.utc)

    # 5. Future Check (against UTC now)
    if utc_dt < datetime.now(timezone.utc):
        if parse_status == 2: # "at 2pm" (and it's 3pm), move to tomorrow
            utc_dt += timedelta(days=1)
        elif utc_dt.date() < datetime.now(timezone.utc).date():
            return None

    return utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')