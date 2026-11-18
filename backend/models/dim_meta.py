from sqlalchemy import Column, Integer, String, Numeric, ForeignKey
from core.database import Base


class DimMeta(Base):
    __tablename__ = "dim_meta"

    id_meta = Column(Integer, primary_key=True, index=True)
    categoria = Column(String(50), nullable=False, index=True)
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="CASCADE"), index=True)
    monto_meta = Column(Numeric(14, 2))
    tipo_programa = Column(String(50))
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="CASCADE"), nullable=True, index=True)
    clave_fila_origen = Column(String(64), nullable=True, unique=True)
    celda_origen = Column(String(120), nullable=True)
