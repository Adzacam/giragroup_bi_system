from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


class LogInconsistencia(Base):
    __tablename__ = "log_inconsistencias"

    id_inconsistencia = Column(Integer, primary_key=True, index=True)
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="CASCADE"), nullable=True, index=True)
    fila_origen = Column(Integer, nullable=True)
    campo_afectado = Column(String(100), nullable=False)
    valor_recibido = Column(Text, nullable=True)
    valor_esperado = Column(Text, nullable=True)
    tipo_regla = Column(String(50), nullable=False, index=True)
    severidad = Column(String(20), nullable=False, default="ALTA")
    estado_resolucion = Column(String(30), nullable=False, default="BLOQUEADO", index=True)
    descripcion = Column(Text, nullable=True)
    detectado_en = Column(DateTime, server_default=func.now())
    resuelto_en = Column(DateTime, nullable=True)
    resuelto_por = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
