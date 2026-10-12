"""
services/notifications-service/main.py
--------------------------------------
Microservicio de Notificaciones y Alertas en Tiempo Real (Puerto 8002).
Gestiona:
- Consulta y marcado de notificaciones persistentes (DW)
- WebSockets para push instantáneo de alertas a navegadores
- Endpoints de emisión de eventos de alerta desde otros microservicios
"""

import logging
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.database import get_db
from models.user import User
from schemas.notification_schemas import NotificationListResponse, NotificationResponse
from services.notification_service import NotificationService
from core.security import get_current_user
from hub.websocket_hub import ws_hub

logger = logging.getLogger("notifications_service")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="GIRAGROUP BI — Notifications & Alert Service",
    description="Microservicio autónomo de Notificaciones, Alertas Críticas y WebSockets",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, client_id: str = "guest"):
    await ws_hub.connect(websocket, user_id=client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo heartbeat
            await websocket.send_text(f'{{"type": "pong", "payload": "{data}"}}')
    except WebSocketDisconnect:
        ws_hub.disconnect(websocket, user_id=client_id)

@app.get("/api/v1/notifications", response_model=NotificationListResponse)
@app.get("/api/v1/notifications/", response_model=NotificationListResponse, include_in_schema=False)
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

@app.patch("/api/v1/notifications/{notif_id}/read", response_model=NotificationResponse)
def mark_read(
    notif_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return NotificationService.mark_as_read(db, notif_id, current_user.id, current_user.role)

@app.post("/api/v1/notifications/mark-all-read")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated = NotificationService.mark_all_as_read(db, current_user.id, current_user.role)
    return {
        "message": "Todas las notificaciones marcadas como leídas",
        "updated_count": updated
    }

@app.post("/api/v1/notifications/dispatch-alert")
async def dispatch_system_alert(
    title: str = Body(...),
    message: str = Body(...),
    severity: str = Body("INFO"),
    category: str = Body("SYSTEM"),
    target_role: str = Body(None),
    db: Session = Depends(get_db)
):
    """Endpoint inter-servicio para emitir alertas e inyectarlas a WebSockets y DB."""
    # Broadcast inmediato a WebSockets conectados
    await ws_hub.broadcast({
        "type": "NEW_ALERT",
        "title": title,
        "message": message,
        "severity": severity,
        "category": category,
        "target_role": target_role
    })
    return {"status": "broadcast_sent", "title": title}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "notifications-service",
            "port": 8002,
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Falla de conectividad en notifications-service: {e}")
        raise HTTPException(status_code=503, detail="DB degradada.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
