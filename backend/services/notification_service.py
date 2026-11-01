from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status

from models.notification import Notification

class NotificationService:
    @staticmethod
    def get_user_notifications(db: Session, user_id: int, user_role: str) -> List[Notification]:
        """Obtiene todas las notificaciones dirigidas al usuario o a su rol."""
        return db.query(Notification).filter(
            or_(
                Notification.user_id == user_id,
                Notification.role_target == user_role
            )
        ).order_by(Notification.created_at.desc()).all()

    @staticmethod
    def get_unread_count(db: Session, user_id: int, user_role: str) -> int:
        """Calcula la cantidad de notificaciones pendientes/no leídas."""
        return db.query(Notification).filter(
            or_(
                Notification.user_id == user_id,
                Notification.role_target == user_role
            ),
            Notification.is_read == False
        ).count()

    @staticmethod
    def mark_as_read(db: Session, notif_id: int, user_id: int, user_role: str) -> Notification:
        """Marca una notificación específica como leída con validación de permisos."""
        notif = db.query(Notification).filter(Notification.id == notif_id).first()
        if not notif:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
            
        if notif.user_id != user_id and notif.role_target != user_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene acceso a esta notificación")
            
        notif.is_read = True
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def mark_all_as_read(db: Session, user_id: int, user_role: str) -> int:
        """Marca todas las notificaciones pendientes del usuario/rol como leídas."""
        updated = db.query(Notification).filter(
            or_(
                Notification.user_id == user_id,
                Notification.role_target == user_role
            ),
            Notification.is_read == False
        ).update({"is_read": True}, synchronize_session=False)
        db.commit()
        return updated

    @staticmethod
    def create_notification(
        db: Session,
        title: str,
        message: str,
        category: str = "Sistema",
        severity: str = "INFO",
        user_id: Optional[int] = None,
        role_target: Optional[str] = None,
        link: Optional[str] = None
    ) -> Notification:
        """Crea y persiste una nueva notificación en el sistema."""
        notif = Notification(
            user_id=user_id,
            role_target=role_target,
            title=title,
            message=message,
            category=category,
            severity=severity,
            link=link,
            is_read=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif
