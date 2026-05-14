from sqlalchemy import Column, Integer, String
from core.database import Base

class DimDocente(Base):
    __tablename__ = "dim_docente"
    id_docente = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(200), nullable=False)
    area_especialidad = Column(String(200))