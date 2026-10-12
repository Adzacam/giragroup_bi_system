from sqlalchemy import Column, Integer, Numeric, String, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from core.database import Base


class FactSituacionFinanciera(Base):
    __tablename__ = "fact_situacion_financiera"

    id_hecho_fin = Column(Integer, primary_key=True, index=True)
    id_estudiante = Column(Integer, ForeignKey("dim_estudiante.id_estudiante", ondelete="CASCADE"))
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo", ondelete="SET NULL"), nullable=True)
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="CASCADE"))
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="SET NULL"), nullable=True)
    monto_deuda = Column(Numeric(10, 2))
    cuotas_impagas = Column(Integer)
    estado_cartera = Column(String(20))
    tipo_alerta = Column(String(20))
    nivel_confianza_ia = Column(Numeric(5, 4))
    requiere_revision = Column(Boolean, default=False)
    fk_estado = Column(String(1), default="A")
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())