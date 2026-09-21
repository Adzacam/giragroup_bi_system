from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from core.database import get_db
from models.user import User
from models.notification import Notification
from schemas.notification_schemas import NotificationListResponse, NotificationResponse
from core.security import get_current_user

router = APIRouter(prefix="/api/v1/notifications", tags=["Notificaciones"])

@router.get("", response_model=NotificationListResponse)
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notifs = db.query(Notification).filter(
        or_(
            Notification.user_id == current_user.id,
            Notification.role_target == current_user.role
        )
    ).order_by(Notification.created_at.desc()).all()
    
    unread = sum(1 for n in notifs if not n.is_read)
    
    return NotificationListResponse(
        status="success",
        total=len(notifs),
        unread_count=unread,
        data=notifs
    )

@router.patch("/{notif_id}/read", response_model=NotificationResponse)
def mark_read(notif_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificacion no encontrada")
        
    if notif.user_id != current_user.id and notif.role_target != current_user.role:
        raise HTTPException(status_code=403, detail="No tiene acceso a esta notificacion")
        
    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif

@router.post("/mark-all-read")
def mark_all_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Notification).filter(
        or_(
            Notification.user_id == current_user.id,
            Notification.role_target == current_user.role
        ),
        Notification.is_read == False
    ).update({"is_read": True}, synchronize_session=False)
    
    db.commit()
    return {"message": "Todas las notificaciones marcadas como leidas"}
