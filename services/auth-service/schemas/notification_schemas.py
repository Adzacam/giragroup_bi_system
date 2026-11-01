from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    category: str
    severity: str
    is_read: bool
    link: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationListResponse(BaseModel):
    status: str
    total: int
    unread_count: int
    data: List[NotificationResponse]
