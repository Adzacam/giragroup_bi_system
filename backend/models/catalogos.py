from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint, Text
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
    tipo_escala = Column(String(20), default="CENTESIMAL_100")

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


class CatEtiquetaClasificacion(CatalogBase):
    __tablename__ = "cat_etiqueta_clasificacion"

    id_etiqueta = Column(Integer, primary_key=True, index=True)
    categoria = Column(String(50), nullable=False, index=True)
    subtipo = Column(String(50), index=True)
    palabra_clave = Column(String(100), nullable=False, unique=True)
    ambito = Column(String(30), default="AMBOS")
    peso = Column(Integer, default=1)


class CatMapeoColumna(CatalogBase):
    __tablename__ = "cat_mapeo_columna"

    id_mapeo = Column(Integer, primary_key=True, index=True)
    campo_canonico = Column(String(50), nullable=False, index=True)
    alias_columna = Column(String(100), nullable=False, unique=True)
    tipo_entidad = Column(String(50), nullable=False)


class CatGuiaTextoPlano(CatalogBase):
    __tablename__ = "cat_guia_texto_plano"

    id_guia = Column(Integer, primary_key=True, index=True)
    subtipo = Column(String(50), nullable=False, unique=True)
    descripcion = Column(String(255))
    plantilla_texto = Column(Text, nullable=False)
    campos_requeridos = Column(Text)
    prioridad = Column(Integer, default=1)


class CatConceptoFinanciero(CatalogBase):
    __tablename__ = "cat_concepto_financiero"

    id_concepto = Column(Integer, primary_key=True, index=True)
    codigo_canonico = Column(String(50), nullable=False, unique=True, index=True)
    nombre_canonico = Column(String(100), nullable=False, unique=True)
    tipo_movimiento = Column(String(30), nullable=False)  # INGRESO | EGRESO | SALDO | AJUSTE
    categoria_contable = Column(String(50))               # COBRANZA | OPERATIVO | DOCENTE | CONVENIO
    descripcion = Column(String(255))

    equivalencias = relationship("CatHistoricoEquivalencia", back_populates="concepto", cascade="all, delete-orphan")


class CatHistoricoEquivalencia(CatalogBase):
    __tablename__ = "cat_historico_equivalencia"

    id_equivalencia = Column(Integer, primary_key=True, index=True)
    id_concepto = Column(Integer, ForeignKey("cat_concepto_financiero.id_concepto", ondelete="CASCADE"), nullable=False)
    termino_origen = Column(String(150), nullable=False, index=True)
    periodo_historico = Column(String(50), default="TODOS")
    confianza_mapeo = Column(Numeric(5, 4), default=0.9500)
    fuente_referencia = Column(String(100))

    concepto = relationship("CatConceptoFinanciero", back_populates="equivalencias")


class CatCategoriaFinanciera(CatalogBase):
    __tablename__ = "cat_categoria_financiera"

    id_categoria_fin = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), nullable=False, unique=True, index=True)
    nombre_categoria = Column(String(100), nullable=False)
    tipo_flujo = Column(String(30), nullable=False, default="INGRESO")


class CatInstitucion(CatalogBase):
    __tablename__ = "cat_institucion"

    id_institucion = Column(Integer, primary_key=True, index=True)
    nombre_institucion = Column(String(100), nullable=False, unique=True, index=True)
    sigla = Column(String(30))
    tipo_escala_default = Column(String(20), default="CENTESIMAL_100")


class CatAliasModulo(CatalogBase):
    __tablename__ = "cat_alias_modulo"

    id_alias = Column(Integer, primary_key=True, index=True)
    id_modulo = Column(Integer, ForeignKey("cat_modulo.id_modulo", ondelete="CASCADE"), nullable=False)
    id_programa = Column(Integer, ForeignKey("cat_programa.id_programa", ondelete="CASCADE"), nullable=False)
    alias_texto = Column(String(255), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("id_programa", "alias_texto", name="uq_cat_alias_modulo_prog_alias"),
    )


class CatAliasDocente(CatalogBase):
    __tablename__ = "cat_alias_docente"

    id_alias = Column(Integer, primary_key=True, index=True)
    id_docente = Column(Integer, ForeignKey("cat_docente.id_docente", ondelete="CASCADE"), nullable=False)
    alias_texto = Column(String(255), nullable=False, unique=True, index=True)


class CatAliasPrograma(CatalogBase):
    __tablename__ = "cat_alias_programa"

    id_alias = Column(Integer, primary_key=True, index=True)
    id_programa = Column(Integer, ForeignKey("cat_programa.id_programa", ondelete="CASCADE"), nullable=False)
    alias_texto = Column(String(255), nullable=False, unique=True, index=True)


class CatAliasFinanciero(CatalogBase):
    __tablename__ = "cat_alias_financiero"

    id_alias = Column(Integer, primary_key=True, index=True)
    id_categoria_fin = Column(Integer, ForeignKey("cat_categoria_financiera.id_categoria_fin", ondelete="CASCADE"), nullable=False)
    alias_texto = Column(String(255), nullable=False, unique=True, index=True)


