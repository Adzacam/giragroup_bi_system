from sqlalchemy import Column, Integer, String, Date, Boolean
from core.database import Base


class DimTiempo(Base):
    __tablename__ = "dim_tiempo"

    id_tiempo = Column(Integer, primary_key=True)  # YYYYMMDD (ej: 20250315)
    fecha = Column(Date, nullable=False, unique=True, index=True)
    gestion = Column(Integer, nullable=False)
    semestre = Column(Integer, nullable=False)
    trimestre = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    nombre_mes = Column(String(20), nullable=False)
    semana_iso = Column(Integer, nullable=False)
    dia_mes = Column(Integer, nullable=False)
    dia_semana = Column(Integer, nullable=False)  # 1=Lunes ... 7=Domingo
    nombre_dia = Column(String(20), nullable=False)
    es_fin_semana = Column(Boolean, nullable=False)
    periodo_mes = Column(String(7), nullable=False, index=True)  # 'YYYY-MM'