from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from core.database import Base

class FactSituacionFinanciera(Base):
    __tablename__ = "fact_situacion_financiera"
    id_hecho_fin = Column(Integer, primary_key=True, index=True)
    id_estudiante = Column(Integer, ForeignKey("dim_estudiante.id_estudiante"))
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo"))
    monto_deuda = Column(Numeric(10, 2))
    cuotas_impagas = Column(Integer)
    estado_cartera = Column(String(20))
    tipo_alerta = Column(String(20))