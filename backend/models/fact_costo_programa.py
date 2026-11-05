from sqlalchemy import Column, Integer, Numeric, Boolean, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from core.database import Base


class FactCostoPrograma(Base):
    """
    Costos de un programa (grano: un POS). fact_rentabilidad es mensual por categoría y su llave única
    (id_categoria, id_tiempo) no admite un monto por programa; este hecho guarda egreso, ingreso y
    rentabilidad de cada POS para cruzarlos con inscritos, notas y cobranzas del mismo programa.
    """
    __tablename__ = "fact_costo_programa"

    id_hecho_costo = Column(Integer, primary_key=True, index=True)
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo", ondelete="CASCADE"), nullable=False, unique=True)
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="SET NULL"))
    egreso_anterior = Column(Numeric(14, 2))
    egreso_real = Column(Numeric(14, 2))
    ingreso = Column(Numeric(14, 2))
    rentabilidad = Column(Numeric(14, 2))
    requiere_revision = Column(Boolean, default=False)
    motivo_revision = Column(String(300))
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
