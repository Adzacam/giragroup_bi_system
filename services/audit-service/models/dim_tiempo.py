from sqlalchemy import Column, Integer, String
from core.database import Base


class DimTiempo(Base):
    __tablename__ = "dim_tiempo"
    __table_args__ = {"extend_existing": True}

    id_tiempo = Column(Integer, primary_key=True)
    gestion = Column(Integer, nullable=False, default=2026)
    semestre = Column(Integer, nullable=True, default=1)
    mes = Column(Integer, nullable=True, default=5)
    nombre_mes = Column(String(50), nullable=True, default="Mayo")
    periodo_mes = Column(String(20), nullable=True, default="2026-05")