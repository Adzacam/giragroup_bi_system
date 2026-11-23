"""Identidad de familia, oferta POS y módulo académico."""

from dataclasses import dataclass
import re
import unicodedata


_POS = re.compile(r"(?<![\w-])POS\s*[-–—:]?\s*(?P<pos>[0-9]{3,6})(?:\s*-\s*M\s*(?P<mod>[0-9]+))?(?![\w-])", re.I)
_VERSION = re.compile(r"\bv(?:(?:\s*\.\s*|\s+)(?P<separada>\d+|[IVX]{1,6})|(?P<compacta>\d+))\b", re.I)
_EDICION = re.compile(r"\b(\d+)\s*(?:RA|DA|TA|RO|DO|TO)\b\.?\s*(?:EDICI[ÓO]N\b)?", re.I)
_ALCANCE = re.compile(r"(?:\s*[-–—]\s*|\s+)NAL\s*$", re.I)
_NUMERO_MODULO = re.compile(r"^M[ÓO]DULO\s+(?:N(?:\.?[°º]|O?\.|O|[ÚU]MERO)\s*)?(\d+)\b", re.I)
_INVALIDO = re.compile(r"\bundefined\b|\bPOS\s*-\s*-", re.I)
_ROMANO = {"I": 1, "V": 5, "X": 10}

# Variantes ortográficas verificadas en ambas bases por POS en CF-L0.
ALIAS_FAMILIAS = {
    "CURSO: FORMACION DE OFICIALES DE CREDITO": "CURSO FORMACIÓN DE OFICIALES DE CRÉDITO",  # POS-4967
    "DIPLOMADO EN BUSINES INTELLIGENCE": "DIPLOMADO EN BUSINESS INTELLIGENCE",  # POS-5024
    "DIPLOMADO EN MARKETING ANALITICS": "DIPLOMADO EN MARKETING ANALYTICS",  # POS-5203
    "DIPLOMADO EN CUIDADOS PALIATIVOS GERITRICOS": "DIPLOMADO EN CUIDADOS PALIATIVOS GERIÁTRICOS",  # POS-5204
}


def clave_nombre(texto: str | None) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto or "") if not unicodedata.combining(c))
    return " ".join(sin_tildes.upper().split())


def es_invalido(texto: str | None) -> bool:
    return bool(_INVALIDO.search(texto or ""))


def partes_pos(codigo: str | None) -> tuple[str | None, int | None]:
    """Separa únicamente un código POS completo, incluido su sufijo de módulo."""
    m = _POS.fullmatch((codigo or "").strip())
    return (f"POS-{m['pos']}", int(m['mod']) if m['mod'] else None) if m else (None, None)


def codigo_modulo(pos: str, numero: int) -> str:
    return f"{pos}-M{numero:02d}"


def codigo_dimension(codigo: str | None) -> str | None:
    """Conserva los códigos institucionales ajenos a POS y excluye centinelas."""
    codigo = (codigo or "").strip()
    if es_invalido(codigo) or codigo.upper() == "MOD-GEN":
        return None
    base, nro = partes_pos(codigo)
    if base:
        return codigo_modulo(base, nro) if nro is not None else base
    if re.match(r"^POS\b", codigo, re.I):
        return None
    return codigo or None


def numero_modulo(nombre: str | None) -> int | None:
    m = _NUMERO_MODULO.match((nombre or "").strip())
    return int(m[1]) if m else None


@dataclass(frozen=True)
class ProgramaNormalizado:
    nombre: str | None
    pos_code: str | None
    version: int | None
    edicion: int | None
    alcance: str | None
    raw: str | None

    @property
    def clave_familia(self) -> str:
        return clave_nombre(self.nombre)

    @property
    def tiene_marcadores(self) -> bool:
        return any(valor is not None for valor in (self.pos_code, self.version, self.edicion, self.alcance))


def normalizar_programa(raw: str | None) -> ProgramaNormalizado:
    texto = raw or ""
    codigos = {f"POS-{m['pos']}" for m in _POS.finditer(texto)}
    pos = next(iter(codigos)) if len(codigos) == 1 else None
    if es_invalido(texto):
        return ProgramaNormalizado(None, pos, None, None, None, raw)
    texto = _POS.sub(" ", texto)

    # La edición ordinal puede ir antes de «Jornada» o al final del título.
    edicion = _EDICION.search(texto)
    texto = _EDICION.sub(" ", texto)
    alcance = _ALCANCE.search(texto)
    texto = _ALCANCE.sub(" ", texto).strip(" -–—:.,")
    version = _VERSION.search(texto)
    valor = (version['separada'] or version['compacta']).upper() if version else ""
    if valor.isdigit():
        nro_version = int(valor)
    else:
        romanos = [_ROMANO[c] for c in valor]
        nro_version = sum(-v if v < s else v for v, s in zip(romanos, romanos[1:] + [0])) if romanos else None
    nombre = " ".join(_VERSION.sub(" ", texto).replace("\u200b", "").split()).strip(" -–—:.,")
    nombre = ALIAS_FAMILIAS.get(clave_nombre(nombre), nombre)
    return ProgramaNormalizado(nombre or None, pos, nro_version, int(edicion[1]) if edicion else None,
                               "NAL" if alcance else None, raw)


def titulo_oferta(nombre_modulo: str | None, programa: str | None, codigo: str | None) -> bool:
    if partes_pos(codigo)[1] is not None or numero_modulo(nombre_modulo) is not None:
        return False
    if partes_pos(nombre_modulo)[0] is not None:
        return partes_pos(nombre_modulo) == (partes_pos(codigo)[0], None)
    nombre = normalizar_programa(nombre_modulo)
    familia = normalizar_programa(programa).clave_familia
    return bool(familia and nombre.clave_familia == familia)


def normalizar_campos_modulo(nombre: str, programa: str | None, codigo: str | None,
                             nombre_catalogo: str | None = None) -> tuple[str, str | None, str | None]:
    """Limpia un título de oferta inequívoco y conserva el nombre de la asignatura."""
    fuente = normalizar_programa(programa)
    catalogo = normalizar_programa(nombre_catalogo)
    familia = fuente.nombre
    if catalogo.nombre and (not familia or catalogo.clave_familia == fuente.clave_familia):
        familia = catalogo.nombre
    if (familia and normalizar_programa(nombre).tiene_marcadores
            and (titulo_oferta(nombre, programa, codigo) or titulo_oferta(nombre, familia, codigo))):
        nombre = familia
    return nombre, familia, codigo_dimension(codigo)


def candidato_modulo(nombre: str | None, programa: str | None, codigo: str | None,
                     modulos: list[tuple[int, str, int]]) -> tuple[int | None, str]:
    """Busca número o nombre canónico en los módulos de una sola oferta."""
    pos, nro_codigo = partes_pos(codigo)
    if not pos:
        return None, "SIN_POS_VALIDO"
    if titulo_oferta(nombre, programa, codigo):
        return None, "OFERTA_COMPLETA"
    nro_nombre = numero_modulo(nombre)
    if nro_codigo is not None and nro_nombre is not None and nro_codigo != nro_nombre:
        return None, "NUMEROS_CONTRADICTORIOS"
    numero = nro_codigo if nro_codigo is not None else nro_nombre
    clave = clave_nombre(nombre)
    candidatos = {id_ for nro, titulo, id_ in modulos if nro == numero or (clave and clave_nombre(titulo) == clave)}
    if len(candidatos) != 1:
        return None, "AMBIGUO" if candidatos else "SIN_CANDIDATO"
    return candidatos.pop(), "VINCULADO"
