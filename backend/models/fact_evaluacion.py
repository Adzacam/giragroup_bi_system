from sqlalchemy import Boolean, Column, Integer, Numeric, String, ForeignKey
from core.database import Base


class FactEvaluacionDocente(Base):
    __tablename__ = "fact_evaluacion_docente"

    id_hecho_eval = Column(Integer, primary_key=True, index=True)
    id_docente = Column(Integer, ForeignKey("dim_docente.id_docente", ondelete="CASCADE"))
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo", ondelete="CASCADE"))
    id_estudiante = Column(Integer, ForeignKey("dim_estudiante.id_estudiante", ondelete="SET NULL"))
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="CASCADE"))
    pregunta_bloque = Column(String(500))
    puntuacion = Column(Numeric(4, 2))
    comentario = Column(String(1000))
    tipo_pregunta = Column(String(20))             # DOCENTE / INSTITUCIONAL / NPS
    escala_max = Column(Integer)                   # 5 (Likert) o 10 (NPS); el promedio se lleva a 1-5
    clave_respuesta = Column(String(64), unique=True, index=True)  # idempotencia de la carga
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="SET NULL"))
    requiere_revision = Column(Boolean, default=False)  # docente sin vincular o sin fecha: entra a la bandeja HITL
    motivo_revision = Column(String(300))
