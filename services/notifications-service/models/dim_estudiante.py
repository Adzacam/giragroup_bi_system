from sqlalchemy import Column, Integer, String
from core.database import Base


class DimEstudiante(Base):
    __tablename__ = "dim_estudiante"
    id_estudiante = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(200), nullable=False)
    codigo_estudiante = Column(String(50))
    genero = Column(String(20))
    ciudad = Column(String(100))
    nivel_academico = Column(String(100))
    edad = Column(Integer)
    ocupacion = Column(String(100))
    estado_civil = Column(String(50))