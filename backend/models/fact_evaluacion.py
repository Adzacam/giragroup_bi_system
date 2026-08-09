from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
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
