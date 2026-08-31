from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from core.database import CatalogBase


class CatEscuela(CatalogBase):
    __tablename__ = "cat_escuela"

    id_escuela = Column(Integer, primary_key=True, index=True)
    nombre_escuela = Column(String(100), nullable=False, unique=True)
    sigla = Column(String(20))

    programas = relationship("CatPrograma", back_populates="escuela")


class CatTipoPrograma(CatalogBase):
    __tablename__ = "cat_tipo_programa"

    id_tipo_programa = Column(Integer, primary_key=True, index=True)
    nombre_tipo = Column(String(100), nullable=False, unique=True)

    programas = relationship("CatPrograma", back_populates="tipo_programa")


class CatModalidad(CatalogBase):
    __tablename__ = "cat_modalidad"

    id_modalidad = Column(Integer, primary_key=True, index=True)
    nombre_modalidad = Column(String(100), nullable=False, unique=True)

    programas = relationship("CatPrograma", back_populates="modalidad")


class CatPrograma(CatalogBase):
    __tablename__ = "cat_programa"

    id_programa = Column(Integer, primary_key=True, index=True)
    pos_code = Column(String(50), nullable=False, unique=True, index=True)
    nombre_programa = Column(String(255), nullable=False, index=True)
    version = Column(Integer, default=1)
    nombre_completo_raw = Column(String(300))
    id_escuela = Column(Integer, ForeignKey("cat_escuela.id_escuela"))
    id_tipo_programa = Column(Integer, ForeignKey("cat_tipo_programa.id_tipo_programa"))
    id_modalidad = Column(Integer, ForeignKey("cat_modalidad.id_modalidad"))
    inversion_base = Column(Numeric(12, 2), default=0.00)
    punto_equilibrio = Column(Integer, default=0)
    horas_totales = Column(Integer, default=0)

    escuela = relationship("CatEscuela", back_populates="programas")
    tipo_programa = relationship("CatTipoPrograma", back_populates="programas")
    modalidad = relationship("CatModalidad", back_populates="programas")
    modulos = relationship("CatModulo", back_populates="programa", cascade="all, delete-orphan")


class CatDocente(CatalogBase):
    __tablename__ = "cat_docente"

    id_docente = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(200), nullable=False, unique=True, index=True)
    email = Column(String(150))
    celular = Column(String(50))
    grado_academico = Column(String(100))
    tipo_docente = Column(String(50), default="TITULAR")


class CatModulo(CatalogBase):
    __tablename__ = "cat_modulo"

    id_modulo = Column(Integer, primary_key=True, index=True)
    id_programa = Column(Integer, ForeignKey("cat_programa.id_programa", ondelete="CASCADE"), nullable=False)
    nro_modulo = Column(Integer, nullable=False)
    nombre_modulo = Column(String(255), nullable=False)
    horas_modulo = Column(Numeric(6, 2), default=0)
    pago_docente_base = Column(Numeric(10, 2), default=0)

    programa = relationship("CatPrograma", back_populates="modulos")

    __table_args__ = (
        UniqueConstraint("id_programa", "nro_modulo", name="uq_cat_modulo_programa_nro"),
    )


class CatEstadoAcademico(CatalogBase):
    __tablename__ = "cat_estado_academico"

    id_estado_academico = Column(Integer, primary_key=True, index=True)
    nombre_estado = Column(String(100), nullable=False, unique=True)


class CatEstadoReprobado(CatalogBase):
    __tablename__ = "cat_estado_reprobado"

    id_estado_reprobado = Column(Integer, primary_key=True, index=True)
    nombre_detalle = Column(String(100), nullable=False, unique=True)


class CatEstadoArca(CatalogBase):
    __tablename__ = "cat_estado_arca"

    id_estado_arca = Column(Integer, primary_key=True, index=True)
    nombre_arca = Column(String(100), nullable=False, unique=True)


class CatTipoCartera(CatalogBase):
    __tablename__ = "cat_tipo_cartera"

    id_cartera = Column(Integer, primary_key=True, index=True)
    nombre_cartera = Column(String(100), nullable=False, unique=True)
    dias_mora_min = Column(Integer, nullable=False)
    dias_mora_max = Column(Integer, nullable=False)
    descripcion = Column(String(255))


class RefMetasGestion(CatalogBase):
    __tablename__ = "ref_metas_gestion"

    id_meta = Column(Integer, primary_key=True, index=True)
    gestion = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    categoria = Column(String(100), nullable=False)
    monto_meta_ingreso = Column(Numeric(14, 2), default=0)
    monto_ejecutado = Column(Numeric(14, 2), default=0)
    ebitda_meta_pct = Column(Numeric(6, 4))
    ebitda_ejecutado_pct = Column(Numeric(6, 4))

    __table_args__ = (
        UniqueConstraint("gestion", "mes", "categoria", name="uq_ref_metas_gestion_mes_cat"),
    )
