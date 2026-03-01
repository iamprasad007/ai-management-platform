from pydantic import BaseModel
from typing import Optional


class AIRequest(BaseModel):
    prompt: str
    creatorId: str
    timezone_offset: int = 330 # Offset in minutes (e.g., 330 for IST)


class ExtractedTask(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_name: Optional[str] = None
    priority: Optional[str] = "MEDIUM"
    due_date_text: Optional[str] = None
    due_date_iso: Optional[str] = None
