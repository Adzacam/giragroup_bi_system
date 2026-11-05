from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.sql import func
from core.database import Base


class FactTechoConvenio(Base):
    """
    Convenio con una institución cliente (techo/cerrado) para un programa: monto, inscritos y fechas.
    Grano: una fila de convenio. clave_convenio = hash de (POS, institución canónica, fecha de inicio, monto,
    inscritos): una fila repetida tal cual se une (recargar no duplica) y dos pagos distintos del mismo convenio
    se conservan. La institución se guarda con su nombre canónico (cat_institucion_convenio).
    """
    __tablename__ = "fact_techo_convenio"

    id_hecho_techo = Column(Integer, primary_key=True, index=True)
    id_modulo = Column(Integer, ForeignKey("dim_modulo.id_modulo", ondelete="CASCADE"), nullable=False, index=True)
    id_tiempo = Column(Integer, ForeignKey("dim_tiempo.id_tiempo", ondelete="SET NULL"))
    id_documento = Column(Integer, ForeignKey("dim_origen_documental.id_documento", ondelete="SET NULL"))
    clave_convenio = Column(String(40), nullable=False, unique=True)
    institucion = Column(String(200), nullable=False, index=True)
    id_convenio_catalogo = Column(Integer)  # cat_institucion_convenio está en giragroup_catalog_db (sin FK)
    monto_convenio = Column(Numeric(14, 2))
    n_inscritos = Column(Integer)
    gestion = Column(Integer)
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    requiere_revision = Column(Boolean, default=False)
    motivo_revision = Column(String(300))
    actualizado_en = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
