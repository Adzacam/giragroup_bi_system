from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from schemas.notification_schemas import NotificationListResponse, NotificationResponse
from services.notification_service import NotificationService
from core.security import get_current_user

router = APIRouter(prefix="/api/v1/notifications", tags=["Notificaciones"])

@router.get("", response_model=NotificationListResponse)
@router.get("/", response_model=NotificationListResponse, include_in_schema=False)
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notifs = NotificationService.get_user_notifications(db, current_user.id, current_user.role)
    unread = NotificationService.get_unread_count(db, current_user.id, current_user.role)
    
    return NotificationListResponse(
        status="success",
        total=len(notifs),
        unread_count=unread,
        data=notifs
    )

@router.patch("/{notif_id}/read", response_model=NotificationResponse)
def mark_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return NotificationService.mark_as_read(db, notif_id, current_user.id, current_user.role)

@router.post("/mark-all-read")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated = NotificationService.mark_all_as_read(db, current_user.id, current_user.role)
    return {
        "message": "Todas las notificaciones marcadas como leídas",
        "updated_count": updated
    }
