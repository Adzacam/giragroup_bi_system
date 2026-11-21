"""
backend/services/encuesta_canonica.py
-------------------------------------
FU-L5 · Lectura de una fila de encuesta (evaluación docente y experiencia institucional) por contenido, sin nombres de
archivo, de hoja ni índices de columna. El diccionario de etiquetas, las escalas y los motivos salen del catálogo
`config/mapeo_fuentes.yaml` (espejo `pipeline/mapeo_fuentes.json`), sección `tipos_fuente.EVALUACION_DOCENTE`.

Reglas (decisión DA1 de Lean, 2026-11-20):
- Cuenta solo `puntuacion` en [1, escala_max]. Un 0, «Sin Información» o un número fuera de escala es NULL (sin respuesta),
  nunca 0. El NPS (pregunta de recomendación 0-10) va aparte: allí el 0 es un puntaje válido.
- Escala por columna: la pista de la cabecera («escala del 1 al 10») gana; si no, los números sueltos (sin etiqueta) de la
  columna deciden entre 1-5 y 1-10; una etiqueta «n/Etiqueta» es siempre de 1-5. Si no se puede inferir, la columna queda sin
  respuesta con el motivo ESCALA_NO_INFERIBLE.
- Dos columnas por pregunta (texto «n/Etiqueta» y número): se lee solo la numérica; la otra no suma una segunda respuesta.
- Etiqueta sin número: se lleva a número con el diccionario (`vocabularios.etiquetas`); una etiqueta desconocida queda NULL
  (VALOR_FUERA_DE_CATALOGO).
- Respuesta cruzada: una etiqueta de otra familia (satisfacción en una pregunta de acuerdo), una etiqueta de 1-5 en una pregunta
  de 1-10 o un texto de otra pregunta dentro de una columna puntuada queda NULL (RESPUESTA_EN_COLUMNA_EQUIVOCADA).
- Las columnas calculadas (promedios) no son respuestas.
- Los avisos son agregados y no publican el valor (puede ser un texto con datos personales): solo etiquetas del diccionario o
  la forma del texto («<texto de N caracteres>»).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple

TIPO = "EVALUACION_DOCENTE"

# Clases de una celda ya interpretada
PUNTUADA = "PUNTUADA"
COMENTARIO = "COMENTARIO"
SIN_INFORMACION = "SIN_INFORMACION"
FUERA_DE_ESCALA = "FUERA_DE_ESCALA"
CRUZADA = "CRUZADA"
FUERA_DE_CATALOGO = "FUERA_DE_CATALOGO"
ESCALA_NO_INFERIBLE = "ESCALA_NO_INFERIBLE"
CLASES_SIN_RESPUESTA = (SIN_INFORMACION, FUERA_DE_ESCALA, CRUZADA, FUERA_DE_CATALOGO, ESCALA_NO_INFERIBLE)

# Tipos de valor crudo de una celda
VACIO, SIN_INFO, NUMERO, N_ETIQUETA, ETIQUETA, TEXTO = "VACIO", "SIN_INFO", "NUMERO", "N_ETIQUETA", "ETIQUETA", "TEXTO"

COMODIN = "*"   # familia de las etiquetas que valen para cualquier pregunta («Neutral»)

_RE_NUMERO = re.compile(r"^\s*(\d{1,3}(?:[.,]\d+)?)\s*$")
_RE_N_ETIQUETA = re.compile(r"^\s*(\d{1,2}(?:[.,]\d+)?)\s*[/\-–:.)]\s*(.+?)\s*$")
_MAX_LARGO_ETIQUETA = 30
_MAX_PALABRAS_ETIQUETA = 3

_DEFECTOS = {
    "min_proporcion_puntuada": 0.5, "min_celdas_perfil": 3, "escala_por_defecto": 5,
    "min_proporcion_numeros_sueltos": 0.5, "min_proporcion_mayor_a_5": 0.2,
    "maximo_admitido": 10, "min_proporcion_sobre_maximo": 0.05, "puntuacion_minima": 1, "nps_minimo": 0,
}


# ── Catálogo ──────────────────────────────────────────────────────────

def _config() -> dict:
    from pipeline.lector_hojas import cargar_config
    return cargar_config()


def _definicion() -> dict:
    return ((_config().get("tipos_fuente") or {}).get(TIPO)) or {}


def _encuesta() -> dict:
    return _definicion().get("encuesta") or {}


def _normalizar(texto: Any) -> str:
    from pipeline.lector_hojas import normalizar
    return normalizar(texto)


def _mayusculas(texto: Any) -> str:
    """Cabecera como la entrega `campos_por_encabezado`: mayúsculas, sin acentos y con espacios colapsados."""
    import unicodedata
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", str(texto or "")) if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.upper().split())


def motivo(clave: str, por_defecto: str) -> str:
    return (((_encuesta().get("calidad") or {}).get(clave)) or {}).get("motivo") or por_defecto


def estado_aviso(motivo_codigo: str) -> str:
    """PENDIENTE (lo revisa una persona) o REGISTRADO (informativo) según el catálogo."""
    for espec in (_encuesta().get("calidad") or {}).values():
        if (espec or {}).get("motivo") == motivo_codigo:
            return (espec or {}).get("estado") or "PENDIENTE"
    return "PENDIENTE"


@lru_cache(maxsize=1)
def _diccionario() -> Dict[str, Any]:
    """{'etiquetas': {texto normalizado: (número, familias)}, 'sin_info': set, 'vacios': set, 'familias': [..]}."""
    voc = _definicion().get("vocabularios") or {}
    etiquetas: Dict[str, Tuple[int, frozenset]] = {}
    familias: List[str] = []
    for familia, numeros in (voc.get("etiquetas") or {}).items():
        familias.append(familia)
        for numero, textos in (numeros or {}).items():
            for t in textos or []:
                clave = _normalizar(t)
                previo = etiquetas.get(clave)
                etiquetas[clave] = (int(previo[0]) if previo else int(numero), (previo[1] if previo else frozenset()) | {familia})
    for numero, textos in ((voc.get("comodin")) or {}).items():
        for t in textos or []:
            etiquetas[_normalizar(t)] = (int(numero), frozenset({COMODIN}))
    solas_familias = set(voc.get("etiquetas_solas") or familias)
    solas = {t for t, (_, fams) in etiquetas.items() if COMODIN in fams or fams & solas_familias}
    return {
        "etiquetas": etiquetas,
        "solas": frozenset(solas),
        "sin_info": frozenset(_normalizar(t) for t in (voc.get("sin_informacion") or [])),
        "vacios": frozenset(_normalizar(t) for t in (voc.get("texto_vacio") or [])),
        "familias": familias,
    }


@lru_cache(maxsize=1)
def _patrones() -> Dict[str, Any]:
    enc = _encuesta()
    pares = enc.get("pares") or {}
    esc = enc.get("escala") or {}
    return {
        "prefijo": re.compile(pares["prefijo_pregunta"]) if pares.get("prefijo_pregunta") else None,
        "marcadores": [re.compile(p) for p in (pares.get("marcadores_numericos") or [])],
        "derivadas": [re.compile(p) for p in (enc.get("columnas_derivadas") or [])],
        "escala_cabecera": [(re.compile(e["patron"]), int(e["escala"])) for e in (esc.get("cabecera") or []) if e.get("patron")],
        "tipo_nps": tuple(enc.get("tipo_pregunta", {}).get("nps") or ()),
        "tipo_docente": tuple(enc.get("tipo_pregunta", {}).get("docente") or ()),
        "tipo_institucional": tuple(enc.get("tipo_pregunta", {}).get("institucional") or ()),
        "no_mapear": frozenset(_mayusculas(x) for x in (_definicion().get("no_mapear") or [])),
    }


def recargar_catalogo() -> None:
    """Vacía las memorias (tras editar el catálogo o en pruebas)."""
    _diccionario.cache_clear()
    _patrones.cache_clear()
    leer_valor.cache_clear()


# ── Valor de una celda ────────────────────────────────────────────────

@dataclass(frozen=True)
class Valor:
    """Lectura de una celda, antes de saber de qué columna viene."""
    tipo: str
    numero: Optional[float] = None
    etiqueta: Optional[str] = None            # texto normalizado de la etiqueta
    familias: frozenset = frozenset()          # familias del diccionario a las que pertenece la etiqueta
    conocida: bool = True                      # la etiqueta está en el diccionario
    largo: int = 0                             # caracteres del texto original (para describir un TEXTO sin publicarlo)
    palabras: int = 0


def _a_numero(texto: str) -> float:
    return float(texto.replace(",", "."))


@lru_cache(maxsize=32768)
def leer_valor(texto: Any) -> Valor:
    """Clasifica una celda: VACIO, SIN_INFO, NUMERO, N_ETIQUETA («5/Totalmente de acuerdo»), ETIQUETA o TEXTO."""
    if texto is None:
        return Valor(VACIO)
    t = str(texto).strip()
    if not t or t.lower() == "nan":
        return Valor(VACIO)
    d = _diccionario()
    norma = _normalizar(t)
    if norma in d["vacios"]:
        return Valor(VACIO)
    m = _RE_NUMERO.match(t)
    if m:
        return Valor(NUMERO, numero=_a_numero(m.group(1)))
    m = _RE_N_ETIQUETA.match(t)
    if m and re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", m.group(2)):
        numero, etq = _a_numero(m.group(1)), _normalizar(m.group(2))
        if etq in d["sin_info"]:
            return Valor(SIN_INFO, numero=numero, etiqueta=etq)
        info = d["etiquetas"].get(etq)
        if info:
            return Valor(N_ETIQUETA, numero=numero, etiqueta=etq, familias=info[1])
        if len(etq) <= _MAX_LARGO_ETIQUETA and len(etq.split()) <= _MAX_PALABRAS_ETIQUETA:
            return Valor(N_ETIQUETA, numero=numero, etiqueta=etq, conocida=False)
    if norma in d["sin_info"]:
        return Valor(SIN_INFO, etiqueta=norma)
    info = d["etiquetas"].get(norma) if norma in d["solas"] else None
    if info:
        return Valor(ETIQUETA, numero=float(info[0]), etiqueta=norma, familias=info[1])
    return Valor(TEXTO, largo=len(t), palabras=len(t.split()))


def parece_etiqueta_desconocida(v: Valor) -> bool:
    """Un texto corto (hasta 3 palabras) en una columna puntuada es una etiqueta que falta en el diccionario; uno largo,
    la respuesta de otra pregunta."""
    return v.tipo == TEXTO and v.largo <= _MAX_LARGO_ETIQUETA and 0 < v.palabras <= _MAX_PALABRAS_ETIQUETA


def es_valor_likert(v: Valor) -> bool:
    """Número con etiqueta del diccionario o etiqueta sola del diccionario (señal de contenido de una encuesta)."""
    return (v.tipo == N_ETIQUETA and v.conocida) or v.tipo == ETIQUETA


def forma_texto(v: Valor) -> str:
    """Descripción publicable de un texto libre: nunca el texto."""
    return f"<texto de {v.largo} caracteres>"


# ── Cabeceras: identidad, derivadas, pares y tipo ─────────────────────

def _es_identidad(cab: str) -> bool:
    from services.extraccion_por_encabezado import _es_columna_identidad
    return _es_columna_identidad(cab) or cab in _patrones()["no_mapear"]


def _parece_pregunta(cab: str) -> bool:
    from services.extraccion_por_encabezado import _parece_pregunta
    return _parece_pregunta(cab)


@lru_cache(maxsize=4096)
def es_columna_derivada(cab: str) -> bool:
    """Columna calculada (promedio de las respuestas): no es una respuesta."""
    return any(p.search(cab) for p in _patrones()["derivadas"])


@lru_cache(maxsize=4096)
def descomponer_cabecera(cab: str) -> Tuple[str, str, bool]:
    """(clave de par, cabecera canónica, lleva marcador numérico). Dos columnas con la misma clave de par son el texto y el
    número de una misma pregunta. La canónica es la cabecera sin el marcador («A 1. N°¿La/El…» → «A 1. ¿La/El…»)."""
    p = _patrones()
    prefijo = p["prefijo"].match(cab).group(0) if p["prefijo"] and p["prefijo"].match(cab) else ""
    resto = cab[len(prefijo):]
    marcada = False
    for mk in p["marcadores"]:
        m = mk.match(resto)
        if m:
            resto, marcada = resto[m.end():], True
            break
    return _normalizar(resto), (prefijo + resto).strip(), marcada


@lru_cache(maxsize=4096)
def pregunta_de_cabecera(cab: str) -> str:
    """Texto de la pregunta (cabecera canónica, sin el marcador de la columna numérica)."""
    return descomponer_cabecera(cab)[1] or cab


def tipo_pregunta(cab: str, defecto_hoja: Optional[str] = None) -> str:
    """NPS (recomendación), DOCENTE o INSTITUCIONAL (KPI-19 / KPI-20), por palabras clave del catálogo. Una pregunta sin palabra
    clave toma el tipo por defecto de su hoja."""
    p = _patrones()
    if any(w in cab for w in p["tipo_nps"]):
        return "NPS"
    if any(w in cab for w in p["tipo_docente"]):
        return "DOCENTE"
    if any(w in cab for w in p["tipo_institucional"]):
        return "INSTITUCIONAL"
    return defecto_hoja or (_encuesta().get("tipo_pregunta") or {}).get("defecto") or "DOCENTE"


def _escala_de_cabecera(cab: str) -> Optional[int]:
    norma = _normalizar(cab)
    for patron, escala in _patrones()["escala_cabecera"]:
        if patron.search(norma):
            return escala
    return None


# ── Perfil de columnas ────────────────────────────────────────────────

@dataclass
class PerfilColumna:
    clase: str                       # PUNTUADA | COMENTARIO
    escala: Optional[int] = None     # 5, 10 o None (no inferible)
    familia: Optional[str] = None    # familia de etiquetas dominante
    n_llenas: int = 0
    n_puntuadas: int = 0
    n_numeros_sueltos: int = 0
    n_etiquetas: int = 0


@dataclass
class PerfilEncuesta:
    columnas: Dict[str, PerfilColumna] = field(default_factory=dict)
    defecto_tipo: str = "DOCENTE"
    n_filas: int = 0


@dataclass
class _Acum:
    llenas: int = 0
    sin_info: int = 0
    puntuadas: int = 0
    textos: int = 0
    sueltos: Counter = field(default_factory=Counter)
    etiquetas: int = 0
    familias: Counter = field(default_factory=Counter)
    con_familia: float = 0.0


def perfilar(lineas: Iterable[Dict[str, str]]) -> PerfilEncuesta:
    """Perfil por columna de un bloque de encuesta, con los valores de todas sus filas (clase, escala y familia de etiquetas)."""
    acum: Dict[str, _Acum] = {}
    ignoradas: Dict[str, bool] = {}
    n_filas = 0
    for campos in lineas:
        n_filas += 1
        for cab, val in campos.items():
            ign = ignoradas.get(cab)
            if ign is None:
                ign = ignoradas[cab] = bool(_es_identidad(cab) or es_columna_derivada(cab))
            if ign:
                continue
            v = leer_valor(val)
            if v.tipo == VACIO:
                continue
            a = acum.setdefault(cab, _Acum())
            if v.tipo == SIN_INFO:
                a.sin_info += 1   # «0/Sin Información» no dice si la columna es de puntuación o de comentarios
                continue
            a.llenas += 1
            if v.tipo == TEXTO:
                a.textos += 1
                continue
            a.puntuadas += 1
            if v.tipo == NUMERO:
                a.sueltos[v.numero] += 1
            elif v.tipo in (N_ETIQUETA, ETIQUETA):
                a.etiquetas += 1
                fams = v.familias - {COMODIN}
                if fams:
                    for f in fams:
                        a.familias[f] += 1.0 / len(fams)
                    a.con_familia += 1.0
    minimo_celdas = int(_encuesta().get("min_celdas_perfil", _DEFECTOS["min_celdas_perfil"]))
    min_prop = float(_encuesta().get("min_proporcion_puntuada", _DEFECTOS["min_proporcion_puntuada"]))
    perfil = PerfilEncuesta(n_filas=n_filas)
    for cab, a in acum.items():
        if a.llenas < minimo_celdas:
            continue
        if a.puntuadas / a.llenas >= min_prop:
            bare_solo = a.etiquetas == 0 and a.puntuadas == sum(a.sueltos.values())
            if bare_solo and not _parece_pregunta(cab):
                continue   # una columna de números sin forma de pregunta (edad, horas, número de orden) no es una pregunta
            perfil.columnas[cab] = PerfilColumna(
                clase=PUNTUADA, escala=_inferir_escala(cab, a), familia=_familia_dominante(a),
                n_llenas=a.llenas, n_puntuadas=a.puntuadas, n_numeros_sueltos=sum(a.sueltos.values()), n_etiquetas=a.etiquetas)
        elif _parece_pregunta(cab):
            perfil.columnas[cab] = PerfilColumna(clase=COMENTARIO, n_llenas=a.llenas, n_puntuadas=a.puntuadas)
    enc_tipo = _encuesta().get("tipo_pregunta") or {}
    docentes = _patrones()["tipo_docente"]
    puntuadas = [c for c, pc in perfil.columnas.items() if pc.clase == PUNTUADA]
    if puntuadas and not any(w in c for c in puntuadas for w in docentes):
        perfil.defecto_tipo = enc_tipo.get("defecto_hoja_sin_docente") or "INSTITUCIONAL"
    else:
        perfil.defecto_tipo = enc_tipo.get("defecto") or "DOCENTE"
    return perfil


def _familia_dominante(a: _Acum) -> Optional[str]:
    if not a.familias or a.con_familia < 3:
        return None
    familia, peso = a.familias.most_common(1)[0]
    return familia if peso >= 0.5 * a.con_familia else None


def _inferir_escala(cab: str, a: _Acum) -> Optional[int]:
    """Escala de la columna: la pista de la cabecera; si no, los números sueltos; las etiquetas «n/Etiqueta» son de 1-5."""
    hint = _escala_de_cabecera(cab)
    if hint:
        return hint
    por_defecto = int(_encuesta().get("escala", {}).get("por_defecto", _DEFECTOS["escala_por_defecto"]))
    esc = _encuesta().get("escala") or {}
    n_sueltos = sum(a.sueltos.values())
    if not n_sueltos:
        return por_defecto
    maximo = int(esc.get("maximo_admitido", _DEFECTOS["maximo_admitido"]))
    sobre_maximo = sum(c for v, c in a.sueltos.items() if v > maximo)
    if sobre_maximo / n_sueltos >= float(esc.get("min_proporcion_sobre_maximo", _DEFECTOS["min_proporcion_sobre_maximo"])):
        return None   # 0-100 u otra escala: no es 1-5 ni 1-10
    dominan_sueltos = n_sueltos / max(1, n_sueltos + a.etiquetas) >= float(
        esc.get("min_proporcion_numeros_sueltos", _DEFECTOS["min_proporcion_numeros_sueltos"]))
    mayores_a_5 = sum(c for v, c in a.sueltos.items() if v > por_defecto)
    if dominan_sueltos and mayores_a_5 / n_sueltos >= float(esc.get("min_proporcion_mayor_a_5", _DEFECTOS["min_proporcion_mayor_a_5"])):
        return maximo
    return por_defecto


# ── Respuestas de una fila ────────────────────────────────────────────

@dataclass
class Respuesta:
    cabecera: str                         # cabecera canónica de la pregunta
    clase: str
    puntuacion: Optional[float] = None
    escala_max: Optional[int] = None
    comentario: Optional[str] = None
    tipo_pregunta: str = "DOCENTE"
    aviso: Optional[Tuple[str, str, str]] = None   # (motivo, pregunta, ejemplo publicable)
    par_evitado: bool = False             # la segunda columna del par (texto) no suma otra respuesta


def _aviso(clave: str, por_defecto: str, cab: str, ejemplo: str) -> Tuple[str, str, str]:
    return (motivo(clave, por_defecto), cab, ejemplo)


def _minimo(tipo: str, escala: Optional[int]) -> float:
    if tipo == "NPS" and escala == 10:
        return float((_encuesta().get("nps") or {}).get("minimo", _DEFECTOS["nps_minimo"]))
    return float(_encuesta().get("puntuacion_minima", _DEFECTOS["puntuacion_minima"]))


def _interpretar(cab: str, valor: Any, perfil: Optional[PerfilEncuesta], cab_canonica: Optional[str] = None) -> Optional[Respuesta]:
    v = leer_valor(valor)
    if v.tipo == VACIO:
        return None
    canon = cab_canonica or pregunta_de_cabecera(cab)
    defecto = perfil.defecto_tipo if perfil is not None else None
    tipo = tipo_pregunta(canon, defecto)
    col = perfil.columnas.get(cab) if perfil is not None else None
    texto = str(valor).strip()

    if col is not None and col.clase == COMENTARIO:
        if v.tipo == SIN_INFO:
            return None
        return Respuesta(canon, COMENTARIO, comentario=texto, tipo_pregunta=tipo)
    if v.tipo == SIN_INFO:
        return Respuesta(canon, SIN_INFORMACION, tipo_pregunta=tipo,
                         aviso=_aviso("sin_informacion", "SIN_INFORMACION", canon, "sin información"))
    if col is None:
        return _interpretar_sin_perfil(canon, cab, v, texto, tipo)

    escala = col.escala
    if escala is None:
        return Respuesta(canon, ESCALA_NO_INFERIBLE, tipo_pregunta=tipo,
                         aviso=_aviso("escala_no_inferible", "ESCALA_NO_INFERIBLE", canon, "números fuera de 1-5 y 1-10"))
    if v.tipo == TEXTO:
        if parece_etiqueta_desconocida(v):
            return Respuesta(canon, FUERA_DE_CATALOGO, escala_max=escala, tipo_pregunta=tipo,
                             aviso=_aviso("valor_fuera_de_catalogo", "VALOR_FUERA_DE_CATALOGO", canon, forma_texto(v)))
        return Respuesta(canon, CRUZADA, escala_max=escala, tipo_pregunta=tipo,
                         aviso=_aviso("respuesta_cruzada", "RESPUESTA_EN_COLUMNA_EQUIVOCADA", canon, forma_texto(v)))
    aviso = None
    if v.tipo in (N_ETIQUETA, ETIQUETA):
        cruzada = escala == 10 or (
            v.familias and COMODIN not in v.familias and col.familia is not None and col.familia not in v.familias)
        if cruzada:
            return Respuesta(canon, CRUZADA, escala_max=escala, tipo_pregunta=tipo,
                             aviso=_aviso("respuesta_cruzada", "RESPUESTA_EN_COLUMNA_EQUIVOCADA", canon, v.etiqueta or "etiqueta"))
        if not v.conocida:
            aviso = _aviso("valor_fuera_de_catalogo", "VALOR_FUERA_DE_CATALOGO", canon, f"<etiqueta de {len(v.etiqueta or '')} caracteres>")
    return _validar_numero(canon, v.numero, escala, tipo, aviso)


def _validar_numero(canon: str, n: Optional[float], escala: int, tipo: str, aviso) -> Respuesta:
    """DA1: solo vale [1, escala]; un 0 es «sin información» (salvo en el NPS 0-10); lo demás es fuera de escala."""
    if n is None:
        return Respuesta(canon, FUERA_DE_ESCALA, escala_max=escala, tipo_pregunta=tipo,
                         aviso=_aviso("fuera_de_escala", "PUNTUACION_FUERA_DE_ESCALA", canon, "sin número"))
    minimo = _minimo(tipo, escala)
    if n == 0 and minimo > 0:
        return Respuesta(canon, SIN_INFORMACION, escala_max=escala, tipo_pregunta=tipo,
                         aviso=_aviso("sin_informacion", "SIN_INFORMACION", canon, "0"))
    if not (minimo <= n <= escala):
        return Respuesta(canon, FUERA_DE_ESCALA, escala_max=escala, tipo_pregunta=tipo,
                         aviso=_aviso("fuera_de_escala", "PUNTUACION_FUERA_DE_ESCALA", canon, f"número fuera de {int(minimo)}-{escala}"))
    return Respuesta(canon, PUNTUADA, puntuacion=float(n), escala_max=escala, tipo_pregunta=tipo, aviso=aviso)


def _interpretar_sin_perfil(canon: str, cab: str, v: Valor, texto: str, tipo: str) -> Optional[Respuesta]:
    """Una sola fila, sin el perfil de su hoja (revisión de un caso, rutas heredadas): la cabecera y la celda deciden."""
    if v.tipo in (N_ETIQUETA, ETIQUETA):
        return _validar_numero(canon, v.numero, 5, tipo,
                               None if v.conocida else _aviso("valor_fuera_de_catalogo", "VALOR_FUERA_DE_CATALOGO", canon,
                                                              f"<etiqueta de {len(v.etiqueta or '')} caracteres>"))
    if v.tipo == NUMERO:
        if not _parece_pregunta(cab):
            return None
        escala = _escala_de_cabecera(cab) or (10 if (tipo == "NPS" or v.numero > 5) else 5)
        return _validar_numero(canon, v.numero, escala, tipo, None)
    if v.tipo == TEXTO and _parece_pregunta(cab):
        return Respuesta(canon, COMENTARIO, comentario=texto, tipo_pregunta=tipo)
    return None


def leer_fila(campos: Dict[str, str], perfil: Optional[PerfilEncuesta] = None) -> List[Respuesta]:
    """Respuestas de una fila de encuesta {cabecera: valor}, una por pregunta (las dos columnas de un par cuentan una vez)."""
    grupos: Dict[str, List[str]] = {}
    for cab, valor in campos.items():
        if valor is None or _es_identidad(cab) or es_columna_derivada(cab):
            continue
        clave = descomponer_cabecera(cab)[0] or cab
        grupos.setdefault(clave, []).append(cab)
    respuestas: List[Respuesta] = []
    for cabs in grupos.values():
        cabs_con_valor = [c for c in cabs if leer_valor(campos[c]).tipo != VACIO]
        if len(cabs_con_valor) == 2:
            r = _interpretar_par(cabs_con_valor, campos, perfil)
            if r is not None:
                respuestas.append(r)
            continue
        for cab in cabs_con_valor:
            r = _interpretar(cab, campos[cab], perfil)
            if r is not None:
                respuestas.append(r)
    return respuestas


def _interpretar_par(cabs: List[str], campos: Dict[str, str], perfil: Optional[PerfilEncuesta]) -> Optional[Respuesta]:
    """Columna de texto y columna numérica de la misma pregunta: manda la numérica (el texto es la misma respuesta escrita)."""
    marcadas = [c for c in cabs if descomponer_cabecera(c)[2]]
    sueltas = [c for c in cabs if leer_valor(campos[c]).tipo == NUMERO]
    if marcadas:
        c_num = marcadas[0]
    elif sueltas:
        c_num = sueltas[0]
    else:   # dos columnas sin marcador ni número: no es el par texto + número; cada una cuenta
        out = [r for r in (_interpretar(c, campos[c], perfil) for c in cabs) if r is not None]
        return out[0] if out else None
    c_txt = next(c for c in cabs if c != c_num)
    canon = pregunta_de_cabecera(c_txt)
    r = _interpretar(c_num, campos[c_num], perfil, cab_canonica=canon)
    if r is None:
        return None
    r.par_evitado = True
    vt = leer_valor(campos[c_txt])
    col_txt = perfil.columnas.get(c_txt) if perfil is not None else None
    # La etiqueta escrita puede delatar una respuesta cruzada (etiqueta de otra familia en la columna de texto)
    if (r.clase == PUNTUADA and vt.tipo in (N_ETIQUETA, ETIQUETA) and vt.familias and COMODIN not in vt.familias
            and col_txt is not None and col_txt.familia is not None and col_txt.familia not in vt.familias):
        return Respuesta(canon, CRUZADA, escala_max=r.escala_max, tipo_pregunta=r.tipo_pregunta, par_evitado=True,
                         aviso=_aviso("respuesta_cruzada", "RESPUESTA_EN_COLUMNA_EQUIVOCADA", canon, vt.etiqueta or "etiqueta"))
    return r


def valor_es_respuesta_likert(valor: Any) -> bool:
    """La celda trae una respuesta tipo Likert (número con etiqueta o etiqueta del diccionario): no es el dato de una columna
    de identificación (un «módulo» que dice «4/De acuerdo»)."""
    return es_valor_likert(leer_valor(valor))


# ── Perfil desde el texto de staging ──────────────────────────────────

_CACHE_PERFIL: Dict[Any, PerfilEncuesta] = {}


def perfil_de_texto(texto: str, clave: Any = None) -> PerfilEncuesta:
    """Perfil de un bloque a partir del texto serializado de staging («ENCABEZADO: valor | …» por línea). `clave` (p. ej. el id
    del bloque) evita recalcular en una revisión caso por caso."""
    if clave is not None and clave in _CACHE_PERFIL:
        return _CACHE_PERFIL[clave]
    from services.extraccion_por_encabezado import campos_por_encabezado
    lineas = (campos_por_encabezado([c.strip() for c in l.split("|")]) for l in (texto or "").splitlines() if l.strip())
    perfil = perfilar(lineas)
    if clave is not None:
        if len(_CACHE_PERFIL) >= 8:
            _CACHE_PERFIL.pop(next(iter(_CACHE_PERFIL)))
        _CACHE_PERFIL[clave] = perfil
    return perfil


# ── Clasificación de una hoja por su contenido ────────────────────────

def hoja_es_encuesta(filas: Iterable[Iterable[Any]], max_filas: int = 80) -> bool:
    """La hoja es una encuesta si varias columnas traen respuestas tipo Likert («5/Totalmente de acuerdo», «Satisfecho»…):
    se decide por los valores, no por el nombre del libro ni de la hoja. `filas` son las filas de celdas (incluida la cabecera)."""
    cfg = _encuesta().get("clasificacion") or {}
    min_cols = int(cfg.get("min_columnas_likert", 4))
    min_prop = float(cfg.get("min_proporcion_likert", 0.5))
    por_col_likert: Counter = Counter()
    por_col_llenas: Counter = Counter()
    for i, fila in enumerate(filas):
        if i >= max_filas:
            break
        for j, celda in enumerate(fila):
            v = leer_valor(celda)
            if v.tipo == VACIO:
                continue
            por_col_llenas[j] += 1
            if es_valor_likert(v):
                por_col_likert[j] += 1
    columnas = [j for j, n in por_col_likert.items() if n >= 3 and n / max(1, por_col_llenas[j]) >= min_prop]
    return len(columnas) >= min_cols
