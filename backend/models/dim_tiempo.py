from sqlalchemy import Boolean, Column, Date, Integer, String
from core.database import Base


class DimTiempo(Base):
    __tablename__ = "dim_tiempo"
    __table_args__ = {"extend_existing": True}

    id_tiempo = Column(Integer, primary_key=True)
    gestion = Column(Integer, nullable=False)
    semestre = Column(Integer, nullable=True)
    mes = Column(Integer, nullable=True)
    nombre_mes = Column(String(50), nullable=True)
    periodo_mes = Column(String(20), nullable=True)
    fecha = Column(Date, nullable=True)
    trimestre = Column(Integer, nullable=True)
    semana_iso = Column(Integer, nullable=True)
    dia_mes = Column(Integer, nullable=True)
    dia_semana = Column(Integer, nullable=True)
    nombre_dia = Column(String(20), nullable=True)
    es_fin_semana = Column(Boolean, nullable=True)
