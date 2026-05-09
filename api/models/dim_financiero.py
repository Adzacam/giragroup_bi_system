from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from api.database import Base

class DimFinanciero(Base):
    __tablename__ = "dim_financiero"

    id_financiero = Column(Integer, primary_key=True, index=True)
    id_estudiante = Column(Integer, ForeignKey("dim_estudiante.id_estudiante"))
    cuotas_impagas = Column(Integer)
    monto_deuda = Column(Numeric(10, 2))
    estado_cartera = Column(String(20))
    fecha_registro = Column(DateTime(timezone=True), server_default=func.now())