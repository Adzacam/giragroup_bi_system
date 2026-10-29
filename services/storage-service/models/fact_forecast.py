from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, UniqueConstraint, func
from core.database import Base


class FactForecast(Base):
    __tablename__ = "fact_forecast"

    id_forecast = Column(Integer, primary_key=True, index=True)
    caso_uso = Column(String(50), nullable=False, index=True)
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="CASCADE"), index=True)
    valor_forecast = Column(Numeric(14, 2), nullable=False)
    ic_lower = Column(Numeric(14, 2))
    ic_upper = Column(Numeric(14, 2))
    metodo = Column(String(30), nullable=False, default="HoltWinters")
    horizonte_meses = Column(Integer, nullable=False)
    generado_en = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("caso_uso", "id_tiempo", name="uq_forecast_caso_tiempo"),
    )
