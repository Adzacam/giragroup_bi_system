from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from core.database import Base

class StagingRegistroCrudo(Base):
    __tablename__ = "staging_registros_crudos"

    id = Column(Integer, primary_key=True, index=True)
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="CASCADE"), index=True)
    hoja = Column(String(200), nullable=True)
    bloque_id = Column(Integer, nullable=True)
    categoria = Column(String(50), nullable=True)
    texto_plano = Column(Text, nullable=True)
    n_filas = Column(Integer, nullable=True)
    fila_inicio = Column(Integer, nullable=True)
    fila_fin = Column(Integer, nullable=True)
    es_ruido = Column(Boolean, default=False)
    requiere_revision = Column(Boolean, default=False)
    score_confianza = Column(Numeric(5, 4), default=1.0)
    resuelto = Column(Boolean, default=False)
    resuelto_por = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resuelto_en = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
