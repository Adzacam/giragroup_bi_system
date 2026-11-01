from sqlalchemy import Column, Integer, Numeric, Boolean, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


class FactRendimientoAcademico(Base):
    __tablename__ = "fact_rendimiento_academico"
    __table_args__ = (
        {"schema": "public"},
    )

    id_hecho_aca = Column("id_hecho_aca", Integer, primary_key=True, index=True)
    id_estudiante = Column(Integer, ForeignKey("dim_estudiante.id_estudiante", ondelete="CASCADE"))
    id_docente = Column(Integer, ForeignKey("dim_docente.id_docente", ondelete="SET NULL"))
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo", ondelete="CASCADE"))
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="CASCADE"))
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="SET NULL"))
    id_usuario_carga = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    nota_final = Column(Numeric(5, 2))
    asistencia_pct = Column("asistencia_pct", Numeric(5, 2))
    incumplimiento_actividades_pct = Column(Numeric(5, 2), server_default="0.00")
    nivel_confianza_ia = Column(Numeric(5, 4))
    requiere_revision = Column(Boolean, default=False)
    fk_estado = Column(String(1), default="A")
    estado_academico = Column(String(50))
    tipo_alerta = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def id_hecho(self):
        return self.id_hecho_aca

    @id_hecho.setter
    def id_hecho(self, value):
        self.id_hecho_aca = value

    @property
    def porcentaje_asistencia(self):
        return self.asistencia_pct

    @porcentaje_asistencia.setter
    def porcentaje_asistencia(self, value):
        self.asistencia_pct = value