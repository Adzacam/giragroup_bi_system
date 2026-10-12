from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


class LogAuditoriaNlp(Base):
    __tablename__ = "log_auditoria_nlp"

    id_log = Column(Integer, primary_key=True, index=True)
    texto_original = Column(String(500), nullable=False)
    prediccion_beto = Column(String(200))
    confianza_ia = Column(Numeric(5, 4))
    correccion_humana = Column(String(200), nullable=False)
    usuario_auditor = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
