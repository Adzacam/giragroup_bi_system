from sqlalchemy import Column, Integer, String
from core.database import Base


class DimDocente(Base):
    __tablename__ = "dim_docente"
    id_docente = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(200), nullable=False)
    area_especialidad = Column(String(200))
    fk_estado = Column(String(1), default="A")  # A: CI exacta; B: vinculado sin CI exacta (fuzzy o miembro nuevo con TEMP-hash); C: sin vincular (solo en stg_entidad_no_resuelta, nunca en dim_* ni en hechos)