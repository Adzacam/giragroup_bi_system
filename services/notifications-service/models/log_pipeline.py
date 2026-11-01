from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from core.database import Base

class LogPipelineIngesta(Base):
    __tablename__ = "log_pipeline_ingesta"

    id = Column(Integer, primary_key=True, index=True)
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="CASCADE"), index=True)
    etapa = Column(String(50), nullable=False)
    nivel = Column(String(10), nullable=False) # INFO, WARN, ERROR, SUCCESS
    modulo = Column(String(100), nullable=True)
    mensaje = Column(Text, nullable=False)
    tiempo_ms = Column(Integer, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
