from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


class DimOrigenDocumental(Base):
    __tablename__ = "dim_origen_documental"

    id_documento = Column(Integer, primary_key=True, index=True)
    id_lote = Column(Integer, ForeignKey("lote.id_lote", ondelete="SET NULL"), nullable=True, index=True)
    tipo_documento = Column(String(50))
    tipo_fuente = Column(String(30), nullable=True)  # 'ACTA', 'COBRANZA', 'ADMISION', 'MOODLE'
    tipo_escala = Column(String(20), nullable=True, default=None)  # 'CENTESIMAL_100', 'DECIMAL_10', 'VIGESIMAL_20' o NULL
    nombre_archivo = Column(String(500))
    institucion = Column(String(100), nullable=True)
    periodo = Column(String(30), nullable=True)
    hash_sha256 = Column(String(64), nullable=True, index=True)
    fecha_procesamiento = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def fecha_ingesta(self):
        return self.fecha_procesamiento