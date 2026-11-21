"""
lector_hojas.py — FU-L1
Metadatos y clasificación genérica de hojas de cálculo.

Qué hace, sin depender del nombre del archivo ni de la hoja:
- Lee por hoja, con openpyxl, el estado (visible / hidden / veryHidden), las celdas
  combinadas y las fórmulas (con o sin valor guardado).
- Mide la forma de la hoja sobre el mismo DataFrame que usa la ingesta: cabecera por
  contenido, filas de datos, filas fantasma (formato arrastrado), subtotales, filas casi
  vacías, duplicadas y montos escritos como texto.
- Clasifica cada hoja en «usar» o «ignorar» con su motivo, con las reglas de
  `config/mapeo_fuentes.yaml` (sección `reglas_hoja`). El nombre de la hoja es solo una
  señal más y nunca deja un libro sin hojas usadas.
- Sugiere el tipo de fuente de cada hoja por sus cabeceras (sinónimos del catálogo).

Las reglas se leen del YAML versionado; si el entorno no tiene PyYAML o la carpeta
`config/` (el contenedor de la API solo monta backend/ y pipeline/), se usa el espejo
JSON `pipeline/mapeo_fuentes.json`, que una prueba mantiene igual al YAML.

Sin PII: las cabeceras con correo o con 7 o más dígitos seguidos se enmascaran como
`col_<n>` antes de registrarse o mostrarse.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import unicodedata
import warnings
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parent.parent
RUTA_YAML = RAIZ / "config" / "mapeo_fuentes.yaml"
RUTA_JSON_ESPEJO = Path(__file__).resolve().parent / "mapeo_fuentes.json"
ENV_RUTA_MAPEO = "GIRA_MAPEO_FUENTES"

ESTADOS_VALIDOS = ("visible", "hidden", "veryHidden")
USAR = "usar"
IGNORAR = "ignorar"

PATRON_CORREO = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PATRON_DIGITOS_LARGOS = re.compile(r"\d{7,}")
PATRON_MONTO_TEXTO = re.compile(r"^\s*(bs\.?|\$|usd|us\$)\s*-?\s*[\d.,]+\s*$", re.IGNORECASE)
PATRON_DIGITO = re.compile(r"\d")

# Categoría de staging que corresponde a cada tipo de fuente (misma tabla que ingestion_service).
CATEGORIA_POR_TIPO = {
    "COBRANZA": "financiero",
    "EGRESOS": "rentabilidad",
    "TECHOS": "rentabilidad",
    "RENTABILIDAD": "rentabilidad",
    "EVALUACION_DOCENTE": "evaluacion_docente",
    "MARKETING": "marketing",
    "ADMISION": "marketing",
    "PLANIFICACION": "planificacion",
    "ACTA": "academico",
    "MOODLE": "academico",
}


# ════════════════════════════════════════════════════════════════════
# Configuración (catálogo de mapeo)
# ════════════════════════════════════════════════════════════════════

_CONFIG_CACHE: Dict[str, Any] = {}


def _leer_yaml(ruta: Path) -> Optional[dict]:
    try:
        import yaml  # PyYAML es opcional en el contenedor de la API
    except ImportError:
        return None
    try:
        with open(ruta, encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except (OSError, ValueError) as exc:
        logger.warning("No se pudo leer el catálogo de mapeo '%s': %s", ruta.name, type(exc).__name__)
        return None


def _leer_json(ruta: Path) -> Optional[dict]:
    try:
        with open(ruta, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        logger.warning("No se pudo leer el espejo del catálogo '%s': %s", ruta.name, type(exc).__name__)
        return None


def cargar_config(recargar: bool = False) -> dict:
    """Catálogo de mapeo: variable de entorno > config/mapeo_fuentes.yaml > espejo JSON."""
    if _CONFIG_CACHE and not recargar:
        return _CONFIG_CACHE["config"]
    candidatos: List[Path] = []
    if os.getenv(ENV_RUTA_MAPEO):
        candidatos.append(Path(os.environ[ENV_RUTA_MAPEO]))
    candidatos += [RUTA_YAML, RUTA_JSON_ESPEJO]
    config = None
    for ruta in candidatos:
        if not ruta.exists():
            continue
        config = _leer_json(ruta) if ruta.suffix.lower() == ".json" else _leer_yaml(ruta)
        if config:
            _CONFIG_CACHE["origen"] = ruta.name
            break
    if not config:
        raise RuntimeError("No hay catálogo de mapeo de fuentes (config/mapeo_fuentes.yaml ni pipeline/mapeo_fuentes.json)")
    _CONFIG_CACHE["config"] = config
    return config


def reglas_hoja(config: Optional[dict] = None) -> dict:
    return (config or cargar_config()).get("reglas_hoja") or {}


def reglas_filas(config: Optional[dict] = None) -> dict:
    return (config or cargar_config()).get("filas") or {}


# ════════════════════════════════════════════════════════════════════
# Utilidades de texto
# ════════════════════════════════════════════════════════════════════

def normalizar(texto: Any) -> str:
    """Minúsculas, sin acentos y con espacios colapsados (mismo criterio que el catálogo)."""
    t = unicodedata.normalize("NFKD", str(texto))
    t = t.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", t).strip()


def vacio(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return isinstance(valor, str) and valor.strip() == ""


def dato_sensible(valor: Any) -> bool:
    """Correo o secuencia de 7 o más dígitos (CI, celular): nunca se publica."""
    if vacio(valor):
        return False
    texto = str(valor)
    return bool(PATRON_CORREO.search(texto) or PATRON_DIGITOS_LARGOS.search(texto))


def enmascarar_cabecera(valor: Any, posicion: int) -> str:
    """Cabecera publicable: la vacía o sensible se reemplaza por `col_<posición 1-based>`."""
    if vacio(valor) or dato_sensible(valor):
        return f"col_{posicion}"
    return " ".join(str(valor).split())


def cabecera_segura(valor: str, posicion: int) -> str:
    """La cabecera tal cual (sin tocar espacios ni saltos), salvo que sea sensible: `col_<posición>`."""
    return f"col_{posicion}" if dato_sensible(valor) else valor


def enmascarar_texto(valor: Any) -> str:
    """Texto libre publicable (nombres de hoja en registros): correos y números largos enmascarados."""
    texto = str(valor)
    texto = PATRON_CORREO.sub("<correo>", texto)
    return PATRON_DIGITOS_LARGOS.sub("<numero>", texto)


def _es_texto_numerico(valor: str) -> bool:
    try:
        float(valor.replace(",", "").strip())
        return True
    except ValueError:
        return False


# ════════════════════════════════════════════════════════════════════
# Metadatos por hoja
# ════════════════════════════════════════════════════════════════════

@dataclass
class MetadatosHoja:
    nombre: str
    posicion: int
    estado: str = "visible"
    n_filas: int = 0
    n_columnas: int = 0
    n_combinadas: int = 0
    n_formulas: int = 0
    n_formulas_sin_valor: int = 0               # sin valor guardado o con error (#N/A…): se leen vacías
    fila_cabecera: Optional[int] = None          # índice 0-based en el DataFrame
    cabeceras: List[str] = field(default_factory=list)   # ya enmascaradas
    filas_datos: int = 0
    filas_vacias: int = 0
    filas_fantasma: int = 0
    filas_subtotal: int = 0
    filas_casi_vacias: int = 0
    filas_duplicadas: int = 0
    celdas_datos: int = 0
    celdas_con_digito: int = 0
    celdas_monto_texto: int = 0
    corte_final: Optional[int] = None            # filas desde este índice son fantasma o vacías
    filas_descartadas: List[int] = field(default_factory=list)  # fantasma o subtotal antes del corte
    campos_por_tipo: Dict[str, List[str]] = field(default_factory=dict)
    tipo_sugerido: Optional[str] = None

    def como_dict(self, con_indices: bool = False) -> dict:
        d = asdict(self)
        if not con_indices:
            d.pop("filas_descartadas", None)
        return d


def _detectar_cabecera(filas: List[List[Any]], n_busqueda: int) -> Optional[int]:
    """Fila con más textos distintos no numéricos, ponderada por su proporción (criterio de FU-L0)."""
    mejor_score, mejor_idx = 0.0, None
    for i, fila in enumerate(filas[:n_busqueda]):
        no_vacios = [v for v in fila if not vacio(v)]
        if len(no_vacios) < 2:
            continue
        textos = [str(v).strip() for v in no_vacios if not _es_texto_numerico(str(v))]
        if not textos:
            continue
        score = len({normalizar(t) for t in textos}) * (len(textos) / len(no_vacios))
        if score > mejor_score:
            mejor_score, mejor_idx = score, i
    return mejor_idx


def medir_forma(df: pd.DataFrame, meta: MetadatosHoja, config: Optional[dict] = None) -> MetadatosHoja:
    """Completa los campos de forma de `meta` a partir del DataFrame crudo (header=None, dtype=str)."""
    rf = reglas_filas(config)
    plantilla = {normalizar(v) for v in rf.get("valores_plantilla", [])}
    ordinales = {normalizar(v) for v in rf.get("columnas_ordinales", [])}
    patron_subtotal = re.compile(rf.get("patron_subtotal", r"^(sub\s*)?total(es)?\b"))
    max_largo_subtotal = int(rf.get("max_largo_subtotal", 40))
    prop_casi = float(rf.get("proporcion_casi_vacia", 0.10))
    n_busqueda = int(rf.get("filas_busqueda_cabecera", 40))

    meta.n_filas, meta.n_columnas = int(df.shape[0]), int(df.shape[1])
    if df.empty:
        meta.corte_final = 0
        return meta
    filas = df.to_numpy(dtype=object).tolist()
    h = _detectar_cabecera(filas, n_busqueda)
    meta.fila_cabecera = h
    if h is None:
        meta.cabeceras = []
        cuerpo_desde = 0
    else:
        meta.cabeceras = [enmascarar_cabecera(v, p + 1) for p, v in enumerate(filas[h])]
        cuerpo_desde = h + 1
    cols_ordinales = {p for p, c in enumerate(meta.cabeceras) if normalizar(c) in ordinales}
    umbral_casi = max(1, math.ceil(prop_casi * meta.n_columnas))

    tipos_fila: List[str] = []
    firmas: Dict[Tuple, int] = {}
    for idx in range(cuerpo_desde, len(filas)):
        fila = filas[idx]
        llenas = [(p, v) for p, v in enumerate(fila) if not vacio(v)]
        if not llenas:
            tipos_fila.append("vacia")
            continue
        utiles = [(p, v) for p, v in llenas if p not in cols_ordinales and normalizar(v) not in plantilla]
        if not utiles:
            tipos_fila.append("fantasma")
            continue
        primeros = [str(v).strip() for _, v in utiles[:2]]
        if any(len(t) <= max_largo_subtotal and not _es_texto_numerico(t) and patron_subtotal.search(normalizar(t))
               for t in primeros):
            tipos_fila.append("subtotal")
            continue
        tipos_fila.append("dato")
        meta.filas_datos += 1
        if len(llenas) <= umbral_casi:
            meta.filas_casi_vacias += 1
        firma = tuple(normalizar(v) if isinstance(v, str) else v for v in fila)
        firmas[firma] = firmas.get(firma, 0) + 1
        for _, v in llenas:
            s = str(v)
            meta.celdas_datos += 1
            if PATRON_DIGITO.search(s):
                meta.celdas_con_digito += 1
            if PATRON_MONTO_TEXTO.match(s):
                meta.celdas_monto_texto += 1

    meta.filas_duplicadas = sum(c - 1 for c in firmas.values() if c > 1)
    ultimo_dato = max((i for i, t in enumerate(tipos_fila) if t in ("dato", "subtotal")), default=-1)
    meta.corte_final = cuerpo_desde + ultimo_dato + 1
    for i, t in enumerate(tipos_fila):
        if t == "vacia":
            meta.filas_vacias += 1
        elif t == "fantasma":
            meta.filas_fantasma += 1
            if i < ultimo_dato:
                meta.filas_descartadas.append(cuerpo_desde + i)
        elif t == "subtotal":
            meta.filas_subtotal += 1
            meta.filas_descartadas.append(cuerpo_desde + i)
    return meta


def _contar_combinadas_xml(archivo: zipfile.ZipFile, ruta_xml: str) -> int:
    """Celdas combinadas contadas en el XML de la hoja (el modo de solo lectura de openpyxl no las expone)."""
    try:
        total, cola = 0, b""
        with archivo.open(ruta_xml) as fh:
            while True:
                bloque = fh.read(1 << 20)
                if not bloque:
                    break
                datos = cola + bloque
                total += datos.count(b"<mergeCell ")
                cola = datos[-10:]
                total -= cola.count(b"<mergeCell ")
        return total + cola.count(b"<mergeCell ")
    except (KeyError, OSError):
        return 0


def _metadatos_openpyxl(ruta: str, hojas: Dict[str, pd.DataFrame]) -> Dict[str, MetadatosHoja]:
    """Estado, celdas combinadas y fórmulas (con y sin valor guardado) de cada hoja de un .xlsx."""
    import openpyxl

    metas: Dict[str, MetadatosHoja] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=False)
    try:
        rutas_xml: Dict[str, str] = {}
        try:
            for ws in wb.worksheets:
                rutas_xml[ws.title] = getattr(ws, "_worksheet_path", "") or ""
        except Exception:  # noqa: BLE001 - la ruta interna es solo para contar combinadas
            rutas_xml = {}
        for pos, ws in enumerate(wb.worksheets):
            estado = ws.sheet_state if ws.sheet_state in ESTADOS_VALIDOS else str(ws.sheet_state)
            meta = MetadatosHoja(nombre=ws.title, posicion=pos, estado=estado)
            df = hojas.get(ws.title)
            n_f = n_sin = 0
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                for fila in ws.iter_rows():
                    for celda in fila:
                        if getattr(celda, "data_type", None) != "f":
                            continue
                        n_f += 1
                        r, c = getattr(celda, "row", None), getattr(celda, "column", None)
                        if df is None or r is None or c is None:
                            continue
                        if r - 1 >= df.shape[0] or c - 1 >= df.shape[1] or vacio(df.iat[r - 1, c - 1]):
                            n_sin += 1
            meta.n_formulas, meta.n_formulas_sin_valor = n_f, n_sin
            metas[ws.title] = meta
        ruta_zip = rutas_xml and any(rutas_xml.values())
        if ruta_zip:
            with zipfile.ZipFile(ruta) as zf:
                for titulo, ruta_xml in rutas_xml.items():
                    if ruta_xml and titulo in metas:
                        metas[titulo].n_combinadas = _contar_combinadas_xml(zf, ruta_xml.lstrip("/"))
    finally:
        wb.close()
    return metas


def leer_metadatos(ruta: str, hojas: Dict[str, pd.DataFrame], config: Optional[dict] = None) -> Dict[str, MetadatosHoja]:
    """Metadatos de cada hoja de `hojas` (el dict de DataFrames que devuelve `leer_archivo`)."""
    metas: Dict[str, MetadatosHoja] = {}
    if Path(ruta).suffix.lower() in (".xlsx", ".xlsm"):
        try:
            metas = _metadatos_openpyxl(ruta, hojas)
        except Exception as exc:  # noqa: BLE001 - sin metadatos de libro se sigue con la forma
            logger.warning("Metadatos de libro no disponibles (%s); solo se mide la forma", type(exc).__name__)
            metas = {}
    for pos, (nombre, df) in enumerate(hojas.items()):
        meta = metas.get(nombre) or MetadatosHoja(nombre=nombre, posicion=pos)
        medir_forma(df, meta, config)
        meta.campos_por_tipo = campos_por_tipo(meta.cabeceras, config)
        meta.tipo_sugerido = tipo_sugerido(meta.campos_por_tipo, config)
        metas[nombre] = meta
    # Hojas que openpyxl ve pero pandas no devolvió (no debería pasar): se conservan con forma vacía
    return metas


# ════════════════════════════════════════════════════════════════════
# Tipo de fuente por cabeceras (sinónimos del catálogo)
# ════════════════════════════════════════════════════════════════════

def _coincide(cabecera_norm: str, sinonimo: dict) -> bool:
    if "texto" in sinonimo:
        return cabecera_norm == normalizar(sinonimo["texto"])
    patron = sinonimo.get("patron")
    if not patron or not re.search(patron, cabecera_norm):
        return False
    excluir = sinonimo.get("excluir")
    return not (excluir and re.search(excluir, cabecera_norm))


def campos_por_tipo(cabeceras: Iterable[str], config: Optional[dict] = None) -> Dict[str, List[str]]:
    """{tipo de fuente: [campos canónicos con al menos una cabecera que coincide]}."""
    cfg = config or cargar_config()
    normas = [normalizar(c) for c in cabeceras if c and not re.fullmatch(r"col_\d+", str(c))]
    resultado: Dict[str, List[str]] = {}
    for tipo, definicion in (cfg.get("tipos_fuente") or {}).items():
        no_mapear = {normalizar(x) for x in (definicion.get("no_mapear") or [])}
        encontrados = []
        for campo, espec in (definicion.get("campos") or {}).items():
            sinonimos = (espec or {}).get("sinonimos") or []
            if any(_coincide(c, s) for c in normas if c not in no_mapear for s in sinonimos):
                encontrados.append(campo)
        if encontrados:
            resultado[tipo] = encontrados
    return resultado


def _especificos(campos: Iterable[str], config: Optional[dict] = None) -> List[str]:
    identidad = set((config or cargar_config()).get("campos_identidad") or [])
    return [c for c in campos if c not in identidad]


def tipo_sugerido(campos: Dict[str, List[str]], config: Optional[dict] = None) -> Optional[str]:
    """Tipo con más campos específicos (no de identidad); empate o ninguno: None."""
    puntajes = sorted(((len(_especificos(v, config)), t) for t, v in campos.items()), reverse=True)
    if not puntajes or puntajes[0][0] == 0:
        return None
    if len(puntajes) > 1 and puntajes[1][0] == puntajes[0][0]:
        return None
    return puntajes[0][1]


def tipo_de_hoja_distinto(meta: MetadatosHoja, tipo_documento: Optional[str], config: Optional[dict] = None) -> Optional[str]:
    """
    Tipo de fuente propio de la hoja cuando su contenido no es el del documento.
    Solo se devuelve si la hoja trae al menos `min_campos_especificos` campos del otro tipo y ninguno
    específico del tipo del documento (p. ej. una hoja de planificación con leads e inscritos dentro
    de un libro de actas). Si el tipo del documento no está en el catálogo, no se cambia.
    """
    cfg = config or cargar_config()
    minimo = int(((cfg.get("tipo_por_hoja") or {}).get("min_campos_especificos")) or 2)
    tipos_catalogo = set((cfg.get("tipos_fuente") or {}).keys())
    sug = meta.tipo_sugerido
    if not sug or not tipo_documento or tipo_documento not in tipos_catalogo or sug == tipo_documento:
        return None
    if CATEGORIA_POR_TIPO.get(sug) == CATEGORIA_POR_TIPO.get(tipo_documento):
        return None
    if len(_especificos(meta.campos_por_tipo.get(sug, []), cfg)) < minimo:
        return None
    if _especificos(meta.campos_por_tipo.get(tipo_documento, []), cfg):
        return None
    return sug


# ════════════════════════════════════════════════════════════════════
# Clasificación de hojas
# ════════════════════════════════════════════════════════════════════

@dataclass
class ClasificacionHoja:
    hoja: str
    decision: str
    regla: str
    motivo: str
    estado: str
    filas_datos: int
    aviso: Optional[str] = None

    def como_dict(self) -> dict:
        return asdict(self)


def _proporcion(a: int, b: int) -> float:
    return (a / b) if b else 0.0


def _regla_forma(meta: MetadatosHoja, regla: dict) -> bool:
    """True si la hoja cumple TODAS las condiciones de la regla de forma."""
    condiciones = {
        "max_filas_datos": lambda v: meta.filas_datos <= int(v),
        "min_proporcion_casi_vacias": lambda v: meta.filas_datos > 0 and _proporcion(meta.filas_casi_vacias, meta.filas_datos) >= float(v),
        "min_proporcion_montos_texto": lambda v: _proporcion(meta.celdas_monto_texto, meta.celdas_datos) >= float(v),
        "max_proporcion_celdas_con_digito": lambda v: meta.celdas_datos > 0 and _proporcion(meta.celdas_con_digito, meta.celdas_datos) <= float(v),
        "min_proporcion_duplicadas": lambda v: meta.filas_datos > 0 and _proporcion(meta.filas_duplicadas, meta.filas_datos) > float(v),
        "min_proporcion_cabeceras_vacias": lambda v: bool(meta.cabeceras) and _proporcion(
            sum(1 for c in meta.cabeceras if re.fullmatch(r"col_\d+", c)), len(meta.cabeceras)) >= float(v),
        "max_densidad": lambda v: meta.filas_datos > 0 and _proporcion(
            meta.celdas_datos, meta.filas_datos * max(1, meta.n_columnas)) <= float(v),
    }
    usadas = [k for k in condiciones if k in regla]
    return bool(usadas) and all(condiciones[k](regla[k]) for k in usadas)


def _excepcion(meta: MetadatosHoja, reglas: dict, oculta: bool) -> Optional[dict]:
    """Excepción del catálogo (`excepciones_usar`) que aplica a la hoja; una oculta solo si lo dice."""
    for exc in (reglas.get("excepciones_usar") or []):
        if oculta and not exc.get("aplica_a_ocultas", False):
            continue
        patron = exc.get("hoja_patron")
        if patron and re.search(patron, normalizar(meta.nombre)):
            return exc
    return None


def _clasificar_sola(meta: MetadatosHoja, reglas: dict) -> Tuple[str, str, str, bool]:
    """(decision, regla, motivo, es_debil) de una hoja sin mirar el resto del libro."""
    for r in reglas.get("ignorar_por_estado") or []:
        if meta.estado in (r.get("estados") or []):
            exc = _excepcion(meta, reglas, oculta=True)
            if exc:
                return USAR, "excepcion", exc.get("motivo", "excepción del catálogo"), False
            return IGNORAR, r["id"], r.get("motivo", r["id"]), False
    exc = _excepcion(meta, reglas, oculta=False)
    for r in reglas.get("ignorar_por_forma") or []:
        if _regla_forma(meta, r):
            if exc and r.get("debil", False):  # una excepción no rescata una hoja vacía
                return USAR, "excepcion", exc.get("motivo", "excepción del catálogo"), False
            return IGNORAR, r["id"], r.get("motivo", r["id"]), bool(r.get("debil", False))
    nombre = normalizar(meta.nombre)
    for r in reglas.get("ignorar_por_nombre_senal") or []:
        if re.search(r.get("patron", "$^"), nombre):
            if exc:
                return USAR, "excepcion", exc.get("motivo", "excepción del catálogo"), False
            return IGNORAR, r["id"], f"nombre: {r.get('motivo', r['id'])}", True
    return USAR, "tabla_de_datos", "tabla de datos con cabecera detectada", False


def clasificar_libro(metas: Dict[str, MetadatosHoja], config: Optional[dict] = None) -> Dict[str, ClasificacionHoja]:
    """
    Decisión por hoja. Las reglas débiles (forma dudosa o nombre como señal) solo ignoran la hoja
    si otra hoja del mismo libro se usa: nunca dejan un libro sin datos por su nombre.
    """
    reglas = reglas_hoja(config)
    previas = {n: _clasificar_sola(m, reglas) for n, m in metas.items()}
    hay_usada_fuerte = any(d == USAR for d, _, _, _ in previas.values())
    resultado: Dict[str, ClasificacionHoja] = {}
    for nombre, (decision, regla, motivo, debil) in previas.items():
        meta = metas[nombre]
        aviso = None
        if decision == IGNORAR and debil and not hay_usada_fuerte:
            aviso = f"{motivo}; se usa porque es la única tabla del libro"
            decision, regla, motivo = USAR, "unica_tabla", "única tabla de datos del libro"
        if decision == USAR and meta.n_formulas_sin_valor:
            extra = f"{meta.n_formulas_sin_valor} celdas con fórmula sin valor guardado o con error (se leen vacías)"
            aviso = f"{aviso}; {extra}" if aviso else extra
        resultado[nombre] = ClasificacionHoja(
            hoja=nombre, decision=decision, regla=regla, motivo=motivo,
            estado=meta.estado, filas_datos=meta.filas_datos, aviso=aviso,
        )
    return resultado


# ════════════════════════════════════════════════════════════════════
# API de lectura con metadatos
# ════════════════════════════════════════════════════════════════════

@dataclass
class HojaLeida:
    df: pd.DataFrame
    meta: MetadatosHoja
    clasificacion: ClasificacionHoja

    @property
    def usada(self) -> bool:
        return self.clasificacion.decision == USAR

    def df_recortado(self) -> pd.DataFrame:
        """DataFrame sin la cola de filas fantasma (las posiciones de las filas restantes no cambian)."""
        corte = self.meta.corte_final
        if corte is None or corte >= len(self.df):
            return self.df
        return self.df.iloc[:corte]


def leer_libro(ruta: str, hojas: Dict[str, pd.DataFrame], config: Optional[dict] = None) -> Dict[str, HojaLeida]:
    """Une DataFrames, metadatos y clasificación por hoja, en el orden del libro."""
    metas = leer_metadatos(ruta, hojas, config)
    clasif = clasificar_libro(metas, config)
    return {n: HojaLeida(df=hojas[n], meta=metas[n], clasificacion=clasif[n]) for n in hojas}


def resumen_publico(libro: Dict[str, HojaLeida]) -> List[dict]:
    """Una fila por hoja, sin PII, para logs, vista previa (FU-L8) y mediciones."""
    filas = []
    for nombre, h in libro.items():
        filas.append({
            "hoja": enmascarar_texto(nombre),
            "estado": h.meta.estado,
            "decision": h.clasificacion.decision,
            "regla": h.clasificacion.regla,
            "motivo": h.clasificacion.motivo,
            "aviso": h.clasificacion.aviso,
            "filas_datos": h.meta.filas_datos,
            "filas_fantasma": h.meta.filas_fantasma,
            "filas_subtotal": h.meta.filas_subtotal,
            "formulas": h.meta.n_formulas,
            "formulas_sin_valor": h.meta.n_formulas_sin_valor,
            "tipo_sugerido": h.meta.tipo_sugerido,
        })
    return filas
