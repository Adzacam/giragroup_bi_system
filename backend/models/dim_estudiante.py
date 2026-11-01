from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from core.database import Base


class DimEstudiante(Base):
    __tablename__ = "dim_estudiante"
    id_estudiante = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(200), nullable=False)
    ci = Column(String(50))
    ci_numero = Column(String(30), index=True)
    ci_complemento = Column(String(10))
    codigo_estudiante = Column(String(50))
    id_temporal = Column(String(100), index=True)
    identidad_verificada = Column(Boolean, default=False)
    id_institucion = Column(Integer, ForeignKey("cat_institucion.id_institucion", ondelete="SET NULL"), nullable=True)
    programa_origen = Column(String(200))
    genero = Column(String(20))
    ciudad = Column(String(100))
    nivel_academico = Column(String(100))
    edad = Column(Integer)
    ocupacion = Column(String(100))
    estado_civil = Column(String(50))
    deprecado = Column(Boolean, default=False)
    fusionado_en = Column(Integer, ForeignKey("dim_estudiante.id_estudiante", ondelete="SET NULL"), nullable=True)