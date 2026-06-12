from sqlalchemy import Column, Integer, Numeric, Boolean, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


class FactRendimientoAcademico(Base):
    __tablename__ = "fact_rendimiento_academico"
    __table_args__ = (
        {"schema": "public"},
    )

    id_hecho_aca = Column(Integer, primary_key=True, index=True)
    id_estudiante = Column(Integer, ForeignKey("dim_estudiante.id_estudiante", ondelete="CASCADE"))
    id_docente = Column(Integer, ForeignKey("dim_docente.id_docente", ondelete="SET NULL"))
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo", ondelete="CASCADE"))
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="CASCADE"))
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="SET NULL"))
    id_usuario_carga = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    nota_final = Column(Numeric(5, 2))
    asistencia_pct = Column(Numeric(5, 2))
    incumplimiento_actividades_pct = Column(Numeric(5, 2), server_default="0.00")
    nivel_confianza_ia = Column(Numeric(5, 4))
    requiere_revision = Column(Boolean, default=False)
    estado_academico = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())