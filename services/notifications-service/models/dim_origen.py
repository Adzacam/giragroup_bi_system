from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from core.database import Base

class DimOrigenDocumental(Base):
    __tablename__ = "dim_origen_documental"
    id_documento = Column(Integer, primary_key=True, index=True)
    tipo_documento = Column(String(10))
    nombre_archivo = Column(String(500))
    fecha_procesamiento = Column(DateTime(timezone=True), server_default=func.now())