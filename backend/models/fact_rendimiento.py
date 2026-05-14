from sqlalchemy import Column, Integer, Numeric, Boolean, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base

class FactRendimientoAcademico(Base):
    __tablename__ = "fact_rendimiento_academico"
    id_hecho = Column(Integer, primary_key=True, index=True)
    id_estudiante = Column(Integer, ForeignKey("dim_estudiante.id_estudiante"))
    id_docente = Column(Integer, ForeignKey("dim_docente.id_docente"))
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo"))
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo"))
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento"))
    id_usuario_carga = Column(Integer, ForeignKey("users.id"))
    
    nota_final = Column(Numeric(5, 2))
    porcentaje_asistencia = Column(Numeric(5, 2))
    porcentaje_inasistencia_actividades = Column(Numeric(5, 2))
    promedio_acumulado = Column(Numeric(5, 2))
    nivel_confianza_ia = Column(Numeric(5, 4))
    requiere_revision = Column(Boolean, default=False)
    tipo_alerta = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())