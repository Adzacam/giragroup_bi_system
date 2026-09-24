from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
