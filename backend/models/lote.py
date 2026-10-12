from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from core.database import Base


class Lote(Base):
    __tablename__ = "lote"

    id_lote = Column(Integer, primary_key=True, index=True)
    institucion = Column(String(100), nullable=False)
    periodo = Column(String(30), nullable=False)
    estado = Column(String(30), default="PROCESADO")
    total_archivos = Column(Integer, default=0)
    creado_en = Column(DateTime, server_default=func.now())
