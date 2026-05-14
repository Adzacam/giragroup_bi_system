from sqlalchemy import Column, Integer, String
from core.database import Base

class DimEstudiante(Base):
    __tablename__ = "dim_estudiante"
    id_estudiante = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(200), nullable=False)
    codigo_estudiante = Column(String(50))