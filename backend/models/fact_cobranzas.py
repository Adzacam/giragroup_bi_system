from sqlalchemy import Column, Integer, Numeric, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


class FactCobranzasProyectadas(Base):
    __tablename__ = "fact_cobranzas_proyectadas"

    id_hecho_cobro = Column(Integer, primary_key=True, index=True)
    id_estudiante = Column(Integer, ForeignKey("dim_estudiante.id_estudiante", ondelete="CASCADE"))
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="CASCADE"))
    monto_esperado = Column(Numeric(10, 2))
    estado_pago = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
