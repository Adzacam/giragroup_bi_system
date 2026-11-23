"""Extracción de entidades de una línea de texto plano (lectura de BETO por reglas y catálogo).

F5C (C-2): cada entidad sale de la columna que tiene su rol por la ESTRUCTURA del encabezado (similitud con las claves
canónicas del rol), nunca por el nombre del archivo. F5C (C-3): cada entidad lleva `confianza` y `origen_confianza`
∈ {BETO, REGLA_ENCABEZADO, REGEX, FUZZY, CI_EXACTA}, calculadas a partir de lo que se midió (similitud del encabezado,
validez del valor, puntaje del catálogo o probabilidad del modelo). El índice de la línea sigue siendo el mínimo.
"""
import re
import threading
from collections import defaultdict
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple
from models.dim_docente import DimDocente
from services.dataops_evaluation_service import NON_PERSON_WORDS, fuzzy_score, strip_accents
from services.extraccion_por_encabezado import es_encabezado_metadato_pos
from services.modulo_validador import validar_nombre_modulo
from services.programa_normalizador import candidato_modulo, es_invalido, normalizar_programa, numero_modulo, partes_pos, titulo_oferta
from pipeline.normalization.person_resolver import resolver_persona
from sqlalchemy import text
from ._comun import NOTA_APROBACION, UMBRAL_INDICE_REGISTRO_DEC

try:
    from rapidfuzz import fuzz as _fuzz
except ImportError:  # pragma: no cover
    _fuzz = None


# =============================================================================
# MOTOR DE EXTRACCIÓN SEMÁNTICA Y RAPIDFUZZ (#4, #5, #7)
# =============================================================================

def _extraccion_cfg() -> dict:
    from pipeline.lector_hojas import cargar_config
    return (cargar_config() or {}).get("extraccion") or {}


def _roles_cfg() -> dict:
    return _extraccion_cfg().get("roles") or {}


# Encabezados y roles cargados desde config/mapeo_fuentes.yaml (M5: sin listas fijas en código).
_ENCABEZADOS_NO_ESTUDIANTE = tuple(_extraccion_cfg().get("no_estudiante") or ())
_PALABRAS_NO_ESTUDIANTE = tuple(_extraccion_cfg().get("palabras_no_estudiante") or ())
_ATRIBUTOS_ESTUDIANTE = tuple(_extraccion_cfg().get("atributos_estudiante") or ())

_ENC_CODIGO_PROGRAMA = tuple(_roles_cfg().get("codigo_programa") or ())
_ENC_NOMBRE_PROGRAMA = tuple(_roles_cfg().get("nombre_programa") or ())
_ENC_MODULO = tuple(_roles_cfg().get("modulo") or ())
_ENC_DOCENTE = tuple(_roles_cfg().get("docente") or ())
_ENC_ESTUDIANTE = tuple(_roles_cfg().get("estudiante") or ())
_ENC_PARTES_NOMBRE = tuple(_roles_cfg().get("partes_nombre") or ())
_ENC_CI = tuple(_roles_cfg().get("ci") or ())
_ENC_CONCEPTO = tuple(_roles_cfg().get("concepto") or ())
_ENC_MONTO = tuple(_roles_cfg().get("monto") or ())
_ENC_MONTO_PAGADO = tuple(_roles_cfg().get("monto_pagado") or ())
_ENC_CUOTAS_IMPAGAS = tuple(_roles_cfg().get("cuotas_impagas") or ())

# Similitud mínima del encabezado con la clave canónica del rol (misma cota del 85 % que la variante de CI y los docentes)
UMBRAL_SIMILITUD_ENCABEZADO = 85.0
# Cota superior de la escala de probabilidad [0, 1]: es el mínimo de un conjunto vacío (línea sin entidades que dudar),
# no una confianza asignada a una entidad.
_COTA_SUPERIOR_ESCALA = 1.0
# Patrón estricto del código de programa (REGEX solo cuenta si el valor pasa este patrón)
_TITULOS_DOCENTE = re.compile(r"^(?:Dr|Dra|MSc|Lic|Ing)\.\s+[A-ZÁÉÍÓÚÑ]")
_PISTA_DOCENTE = re.compile(r"\b(?:docente|profesor|tutor)\b|\b(?:dr|dra|msc|lic|ing)\.\s", re.IGNORECASE)

# Orígenes de la confianza que ve la pantalla
ORIGEN_BETO, ORIGEN_ENCABEZADO, ORIGEN_REGEX, ORIGEN_FUZZY, ORIGEN_CI = "BETO", "REGLA_ENCABEZADO", "REGEX", "FUZZY", "CI_EXACTA"
ORIGENES_CONFIANZA = (ORIGEN_BETO, ORIGEN_ENCABEZADO, ORIGEN_REGEX, ORIGEN_FUZZY, ORIGEN_CI)
# fuente_resolucion histórica (la usan los contadores y la cascada de BETO) para cada origen de confianza
_FUENTE_DE_ORIGEN = {ORIGEN_BETO: "BETO", ORIGEN_ENCABEZADO: "ENCABEZADO", ORIGEN_REGEX: "REGEX", ORIGEN_FUZZY: "FUZZY", ORIGEN_CI: "CI_EXACTA"}


def _es_encabezado_no_estudiante(clave: str) -> bool:
    # 'POS - ACTAS', 'POS-CI'…: identifican el programa (antes 'POS - ACTAS: POS-011' se tomaba como estudiante)
    if any(p in clave for p in _ENCABEZADOS_NO_ESTUDIANTE) or es_encabezado_metadato_pos(clave):
        return True
    palabras = set(_norm_enc(clave).split())
    return any(p in palabras for p in _PALABRAS_NO_ESTUDIANTE)


def _norm_enc(clave: str) -> str:
    """Encabezado sin tildes, en mayúsculas y con la puntuación como espacio ('N° POS' → 'N POS', 'COD_MODULO' → 'COD MODULO')."""
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", strip_accents(clave or "").upper()).split())


def _ratio(a: str, b: str) -> float:
    if _fuzz is not None:
        return float(_fuzz.ratio(a, b))
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio() * 100


@lru_cache(maxsize=8192)
def _similitud_cache(clave: str, canonicas: Tuple[str, ...]) -> float:
    h = _norm_enc(clave)
    return max((_ratio(h, c) for c in canonicas), default=0.0) if h else 0.0


def similitud_encabezado(clave: str, canonicas: Iterable[str]) -> float:
    """Similitud (0-100, RapidFuzz ratio) del encabezado con la clave canónica más parecida del rol."""
    return _similitud_cache(clave or "", tuple(canonicas))


@lru_cache(maxsize=2048)
def _similitud_compuesto_cache(clave: str, canonicas: Tuple[str, ...]) -> float:
    h = _norm_enc(clave)
    if not h:
        return 0.0
    if _fuzz is not None:
        return max(float(_fuzz.token_set_ratio(h, c)) for c in canonicas)
    return max(100.0 * float(set(c.split()) <= set(h.split())) for c in canonicas)


def similitud_encabezado_compuesto(clave: str, canonicas: Iterable[str]) -> float:
    """Encabezados compuestos 'POS - ACTAS', 'POS - IBP': la palabra del rol está entera dentro del encabezado
    (RapidFuzz token_set_ratio). Solo se usa para el código del programa, cuyo valor además debe pasar el patrón POS."""
    return _similitud_compuesto_cache(clave or "", tuple(canonicas))


@lru_cache(maxsize=8192)
def _es_atributo_estudiante(clave: str) -> bool:
    h = _norm_enc(clave)
    return any(a in h for a in _ATRIBUTOS_ESTUDIANTE)


def _columnas_de_rol(labeled: Dict[str, str], canonicas: Iterable[str]) -> List[Tuple[float, str, str]]:
    """Columnas cuyo encabezado tiene el rol (similitud >= umbral), de la más parecida a la menos; nunca un atributo del estudiante."""
    canon = tuple(canonicas)
    salida = []
    for k, v in labeled.items():
        if not v or _es_atributo_estudiante(k):
            continue
        s = similitud_encabezado(k, canon)
        if s >= UMBRAL_SIMILITUD_ENCABEZADO:
            salida.append((s, k, v))
    salida.sort(key=lambda t: -t[0])
    return salida


def _es_encabezado_no_docente(clave: str) -> bool:
    """El docente solo sale de una columna con rol de docente (DOCENTE, PROFESOR, TUTOR, FACILITADOR…). Cualquier otra
    columna con encabezado (ASESOR, COORDINADOR, RESPONSABLE, RAZÓN SOCIAL, correos, comentarios, carrera…) se excluye,
    también para la entidad PER de BETO."""
    if not clave or not clave.strip():
        return False
    return _es_atributo_estudiante(clave) or similitud_encabezado(clave, _ENC_DOCENTE) < UMBRAL_SIMILITUD_ENCABEZADO


# Exclusión de celdas para las propuestas de BETO, por tipo de persona (services/beto_integracion.mejor_propuesta)
def _es_encabezado_no_academico(clave: str) -> bool:
    if _es_atributo_estudiante(clave):
        return True
    otros_roles = (_ENC_ESTUDIANTE, _ENC_PARTES_NOMBRE, _ENC_DOCENTE, _ENC_CI, _ENC_CONCEPTO, _ENC_MONTO)
    return any(similitud_encabezado(clave, rol) >= UMBRAL_SIMILITUD_ENCABEZADO for rol in otros_roles if rol)


EXCLUIR_CELDA_BETO = {"ESTUDIANTE": _es_encabezado_no_estudiante, "DOCENTE": _es_encabezado_no_docente,
                    "PROGRAMA": _es_encabezado_no_academico, "MODULO": _es_encabezado_no_academico}


# ── Validez del valor (1 si el formato se valida; fracción medida cuando el valor es parcialmente válido) ──────────
def _validez_nombre_persona(valor: str) -> float:
    v = (valor or "").strip()
    palabras = v.split()
    return float(2 <= len(palabras) <= 6 and not re.search(r"\d", v) and "@" not in v)


def _validez_texto(valor: str) -> float:
    v = (valor or "").strip()
    return float(len(re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", v)) >= 3)


def _validez_ci(valor: str) -> float:
    """Fracción de caracteres del documento que son dígitos válidos (sin el sufijo de departamento): 1 para '4567890 LP'."""
    v = re.sub(r"\s*(?:LP|SC|CB|OR|PT|TJ|CH|BE|PA)\s*$", "", (valor or "").strip(), flags=re.IGNORECASE).replace(" ", "")
    if not v:
        return float(False)
    digitos = len(re.sub(r"[^0-9]", "", v))
    return round(digitos / len(v), 4) if digitos >= 5 else float(False)


def _validez_codigo_pos(valor: str) -> float:
    pos, numero = partes_pos(valor)
    return float(pos is not None and numero is None)


def _validez_numero(valor) -> float:
    return float(bool(re.search(r"[0-9]+(?:\.[0-9]+)?", str(valor or ""))))


# ── Memo de emparejamiento contra catálogos ──────────────────────────────────
# Evaluar un lote compara cada línea contra todo el catálogo (≈10 000 estudiantes, ≈2 600 módulos). El mejor
# candidato depende solo del texto candidato y del catálogo, así que se calcula una vez por texto distinto.
# El memo vive mientras exista la lista de catálogo de esa evaluación (se guarda una referencia a la lista).
_STOP_TOKENS_EST = ("del", "los", "las", "san")


_MEMO_CATALOGOS: Dict[Tuple[str, int], Dict[Any, Any]] = {}


_MEMO_LOCK = threading.Lock()


_MEMO_MAX_CATALOGOS = 12


def categoria_de_fuente(doc_fuente: str) -> str:
    """Categoría de ruteo de un documento por su tipo de fuente (la misma que usa la consolidación)."""
    return ("financiero" if doc_fuente == "COBRANZA"
            else "rentabilidad" if doc_fuente in ("EGRESOS", "TECHOS", "RENTABILIDAD")
            else "evaluacion_docente" if doc_fuente == "EVALUACION_DOCENTE"
            else "marketing" if doc_fuente == "MARKETING"
            else "admision" if doc_fuente == "ADMISION"
            else "academico")


def fila_sin_entidad(linea: str, doc_fuente: str) -> bool:
    """True si la fila no tiene entidad que enlazar (hoja de estados, catálogo, fila agregada): ruido, no se lee con BETO."""
    from services.extraccion_por_encabezado import campos_por_encabezado, motivo_fila_sin_entidad
    return bool(motivo_fila_sin_entidad(campos_por_encabezado([c.strip() for c in linea.split("|")]), categoria_de_fuente(doc_fuente)))


def _memo_catalogo(tipo: str, catalogo: list) -> Dict[Any, Any]:
    clave = (tipo, id(catalogo))
    with _MEMO_LOCK:
        memo = _MEMO_CATALOGOS.get(clave)
        if memo is None or memo["_ref"] is not catalogo or memo["_len"] != len(catalogo):
            while len(_MEMO_CATALOGOS) >= _MEMO_MAX_CATALOGOS:
                _MEMO_CATALOGOS.pop(next(iter(_MEMO_CATALOGOS)))
            memo = {"_ref": catalogo, "_len": len(catalogo)}
            _MEMO_CATALOGOS[clave] = memo
        return memo


def _docentes_con_contexto(db) -> list:
    """dim_docente + módulos/programas asignados (bridge_modulo_docente) como contexto para filtrar candidatos."""
    docentes = db.query(DimDocente).all()
    try:
        filas = db.execute(text(
            "SELECT b.id_docente, m.nombre_modulo, m.programa FROM bridge_modulo_docente b "
            "JOIN dim_modulo m ON m.id_modulo = b.id_modulo"
        )).fetchall()
    except Exception:
        filas = []
    ctx: Dict[int, set] = {}
    for id_d, mod, prog in filas:
        ctx.setdefault(id_d, set()).update(x for x in (mod, prog) if x)
    for d in docentes:
        d._contextos = sorted(ctx.get(d.id_docente, ()))
    return docentes


def _personas_memo(tipo: str, catalogo: list, memo: dict) -> list:
    """Adapta los objetos ORM de dim_estudiante / dim_docente al formato de person_resolver (una vez por catálogo)."""
    if "personas" not in memo:
        if tipo == "estudiantes":
            memo["personas"] = [
                {"id": e.id_estudiante, "nombre": e.nombre_completo,
                 "ci": getattr(e, "ci_numero", None) or getattr(e, "ci", None),
                 "contextos": [getattr(e, "programa_origen", None)] if getattr(e, "programa_origen", None) else []}
                for e in catalogo
            ]
        else:
            memo["personas"] = [
                {"id": d.id_docente, "nombre": d.nombre_completo, "ci": None,
                 "contextos": list(getattr(d, "_contextos", None) or [])}
                for d in catalogo
            ]
        memo["por_id"] = {p["id"]: o for p, o in zip(memo["personas"], catalogo)}
    return memo["personas"]


def _resolver_persona_cascada(tipo: str, cand: str, catalogo: list, ci: Optional[str], contexto: tuple) -> Tuple[Any, float, str]:
    """Cascada sin cat_docente: (a) CI exacta -> dim; (b) RapidFuzz en la dim con filtro programa/módulo y apellido; (c) None -> HITL."""
    memo = _memo_catalogo(tipo, catalogo)
    clave = ("persona", cand, ci, contexto)
    if clave in memo:
        return memo[clave]
    personas = _personas_memo(tipo, catalogo, memo)
    res = resolver_persona(cand, ci, personas, contexto=contexto)
    if res is None:
        memo[clave] = (None, 0.0, "None")
    else:
        algo = "CI Exact Match" if res["fuente"] == "CI_EXACTA" else "RapidFuzz Fuzzy (apellido + programa/módulo)"
        memo[clave] = (memo["por_id"][res["id"]], round(res["score"] * 100.0, 1), algo)
    return memo[clave]


def _mejor_estudiante(cand: str, estudiantes: list, ci: Optional[str] = None, contexto: tuple = ()) -> Tuple[Any, float, str]:
    return _resolver_persona_cascada("estudiantes", cand, estudiantes, ci, contexto)


def _mejor_docente(cand: str, docentes: list, contexto: tuple = ()) -> Tuple[Any, float, str]:
    return _resolver_persona_cascada("docentes", cand, docentes, None, contexto)


def _modulos_por_oferta(modulos: list) -> dict:
    memo = _memo_catalogo("modulos", modulos)
    if 'por_oferta' not in memo:
        por_oferta = defaultdict(list)
        for modulo in modulos:
            pos, _ = partes_pos(modulo.pos_code)
            if pos:
                por_oferta[pos].append(modulo)
        memo['por_oferta'] = por_oferta
    return memo['por_oferta']


def _mejor_modulo(cand: str, modulos: list, oferta: str | None = None) -> Tuple[Any, float, str]:
    memo = _memo_catalogo("modulos", modulos)
    clave = ("mejor", cand, oferta)
    if clave in memo:
        return memo[clave]
    cand_clean = strip_accents(cand).lower()
    mejor = (None, 0.0, "None")
    candidatos = modulos
    if oferta:
        candidatos = _modulos_por_oferta(modulos).get(oferta, [])
    for m in candidatos:
        score, algo = fuzzy_score(cand, m.nombre_modulo)
        # F5C C-3: el código del módulo dentro del texto es una coincidencia exacta del código (su similitud con el
        # código del catálogo). Se quitaron los alias fijos ('estetica', 'big data', '3'↔'302'…) que daban un puntaje
        # escrito a mano (87,5 / 89 / 91,5 / 93) a cualquier texto con esas palabras.
        codigo = strip_accents(m.pos_code or "").lower()
        m_cod = re.search(r"(?<![\w-])" + re.escape(codigo) + r"(?![\w-])", cand_clean) if codigo else None
        if m_cod:
            s_cod = _ratio(codigo, m_cod.group(0))
            if s_cod > score:
                score, algo = s_cod, "Prefix Code Match"
        if score > mejor[1]:
            mejor = (m, score, algo)
    memo[clave] = mejor
    return mejor


def _mejor_programa(cand: str, modulos: list) -> Tuple[Optional[str], float]:
    """Nombre de programa del catálogo (dim_modulo.programa) más parecido al leído, con su puntaje 0-100."""
    memo = _memo_catalogo("modulos", modulos)
    if "programas" not in memo:
        memo["programas"] = sorted({(getattr(m, "programa", None) or "").strip() for m in modulos} - {""})
    clave = ("programa", cand)
    if clave not in memo:
        mejor: Tuple[Optional[str], float] = (None, 0.0)
        for p in memo["programas"]:
            s, _ = fuzzy_score(cand, p)
            if s > mejor[1]:
                mejor = (p, s)
        memo[clave] = mejor
    return memo[clave]


def _resolver_programa_beto(valor: str, oferta: str | None, modulos: list):
    propuesta = normalizar_programa(valor)
    if es_invalido(valor) or not (propuesta.nombre or propuesta.pos_code):
        return None, 'TITULO_INVALIDO'
    if oferta and propuesta.pos_code and propuesta.pos_code != oferta:
        return None, 'POS_INCOMPATIBLE'
    pos = oferta or propuesta.pos_code
    memo = _memo_catalogo('modulos', modulos)
    if 'ofertas_completas' not in memo:
        por_pos, por_familia = defaultdict(dict), defaultdict(dict)
        for codigo, filas in _modulos_por_oferta(modulos).items():
            for modulo in filas:
                if not titulo_oferta(modulo.nombre_modulo, modulo.programa, modulo.pos_code):
                    continue
                canonico = normalizar_programa(modulo.programa or modulo.nombre_modulo)
                if canonico.nombre:
                    por_pos[codigo].setdefault(canonico.clave_familia, canonico.nombre)
                    por_familia[canonico.clave_familia].setdefault(codigo, canonico.nombre)
        memo['ofertas_completas'] = por_pos, por_familia
    por_pos, por_familia = memo['ofertas_completas']
    if pos and propuesta.nombre:
        nombre = por_pos.get(pos, {}).get(propuesta.clave_familia)
        candidatos = [(pos, nombre)] if nombre else []
    elif pos:
        candidatos = [(pos, nombre) for nombre in por_pos.get(pos, {}).values()]
    else:
        candidatos = list(por_familia.get(propuesta.clave_familia, {}).items())
    if len(candidatos) == 1:
        return candidatos[0], None
    return None, 'AMBIGUO' if candidatos else 'SIN_CANDIDATO'


def _resolver_modulo_beto(valor: str, oferta: str | None, modulos: list):
    valido, rechazo = validar_nombre_modulo(valor)
    if not valido or es_invalido(valor) or valor.upper() == 'MOD-GEN':
        return None, rechazo or 'TITULO_INVALIDO'
    pos, numero = partes_pos(valor)
    if oferta and pos and oferta != pos:
        return None, 'POS_INCOMPATIBLE'
    codigo = valor if numero is not None else (oferta or pos)
    oferta = oferta or pos
    filas = [m for m in _modulos_por_oferta(modulos).get(oferta, ()) if m.id_cat_modulo]
    candidatos = [((partes_pos(m.pos_code)[1] or numero_modulo(m.nombre_modulo) or -1), m.nombre_modulo, m.id_cat_modulo)
                  for m in filas]
    id_cat, motivo = candidato_modulo(valor, None, codigo, candidatos)
    if id_cat is None:
        return None, motivo
    return min((m for m in filas if m.id_cat_modulo == id_cat), key=lambda m: m.id_modulo), None


def _aplicar_rescate_academico(entities, propuestas, modulos, oferta):
    confianzas = {}
    revision = False
    for tipo, label in (("PROGRAMA", "PROGRAMA"), ("MODULO", "MÓDULO")):
        propuesta = propuestas.get(tipo)
        previa = next((e for e in entities if e.get('label') == label), None)
        if propuesta is None or (previa and previa.get('matchedCanonical')):
            continue
        if tipo == 'PROGRAMA':
            resuelto, motivo = _resolver_programa_beto(propuesta['nombre'], oferta, modulos)
            if resuelto:
                oferta, nombre = resuelto
                campos = dict(matchedCanonical=nombre, canonicalId=oferta, posCodigo=oferta, nombrePrograma=propuesta['nombre'])
        else:
            resuelto, motivo = _resolver_modulo_beto(propuesta['nombre'], oferta, modulos)
            if resuelto:
                campos = dict(matchedCanonical=resuelto.nombre_modulo, canonicalId=resuelto.pos_code,
                              idModulo=resuelto.id_modulo)
        if not resuelto:
            if motivo in ('AMBIGUO', 'NUMEROS_CONTRADICTORIOS', 'POS_INCOMPATIBLE'):
                revision = True
                if previa is None:
                    previa = dict(label=label, token=propuesta['nombre'])
                    entities.append(previa)
                previa['motivoRescateBeto'] = motivo
            continue
        medida = _medida(ORIGEN_BETO, probabilidad=propuesta['prob'])
        rescatada = dict(token=propuesta['nombre'], label=label, tag=f'B-{tipo}', conllTag='ORG/CATALOGO',
                         es_nuevo_perfil=False, algorithm='BETO + catálogo institucional', **medida, **campos)
        if previa is not None:
            rescatada['valorPrevio'] = previa.get('token')
            entities[entities.index(previa)] = rescatada
        else:
            entities.append(rescatada)
        confianzas[tipo] = medida
    return confianzas, revision


def _medida(origen: str, similitud: Optional[float] = None, validez: Optional[float] = None,
            catalogo: Optional[float] = None, probabilidad: Optional[float] = None) -> Dict[str, Any]:
    """Confianza de una entidad a partir de lo medido (C-3). Ninguna parte es una constante:
    CI_EXACTA = puntaje de la coincidencia exacta / 100; FUZZY = puntaje RapidFuzz / 100;
    REGLA_ENCABEZADO = similitud del encabezado / 100 × validez del valor (o puntaje del catálogo / 100);
    REGEX = validez del valor con el patrón estricto; BETO = probabilidad del modelo."""
    if origen == ORIGEN_BETO:
        conf = probabilidad
    elif origen in (ORIGEN_CI, ORIGEN_FUZZY):
        conf = catalogo / 100.0 if catalogo is not None else None
    elif origen == ORIGEN_ENCABEZADO:
        factor = catalogo / 100.0 if catalogo is not None else validez
        conf = (similitud / 100.0) * factor if (similitud is not None and factor is not None) else None
    else:  # REGEX
        conf = validez
    detalle = {k: round(v, 4) for k, v in (("similitudEncabezado", similitud / 100.0 if similitud is not None else None),
                                            ("validez", validez),
                                            ("puntajeCatalogo", catalogo / 100.0 if catalogo is not None else None),
                                            ("probabilidadModelo", probabilidad)) if v is not None}
    return {"confianza": round(float(conf), 4) if conf is not None else None, "origen_confianza": origen,
            "fuente_resolucion": _FUENTE_DE_ORIGEN[origen], "detalleConfianza": detalle}


def _coma(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def explicar_confianza(ent: Dict[str, Any]) -> str:
    """Texto llano del origen de la confianza: «Regla por encabezado: similitud 0,96 · valor validado» o «BETO p = 0,73»."""
    origen, det = ent.get("origen_confianza"), ent.get("detalleConfianza") or {}
    if origen == ORIGEN_BETO:
        return f"BETO p = {_coma(det.get('probabilidadModelo', ent.get('confianza') or 0.0))}"
    if origen == ORIGEN_CI:
        return "Cédula exacta en el catálogo"
    if origen == ORIGEN_FUZZY:
        return f"Coincidencia aproximada con el catálogo: {_coma(det.get('puntajeCatalogo', 0.0))}"
    if origen == ORIGEN_ENCABEZADO:
        sim = _coma(det.get("similitudEncabezado", 0.0))
        if "puntajeCatalogo" in det:
            return f"Regla por encabezado: similitud {sim} · catálogo {_coma(det['puntajeCatalogo'])}"
        return f"Regla por encabezado: similitud {sim} · " + ("valor validado" if det.get("validez") == 1 else f"validez {_coma(det.get('validez', 0.0))}")
    return "Patrón: " + ("valor validado" if det.get("validez") == 1 else "valor no validado")


def elemento_confianza(nombre: str, ent: Dict[str, Any]) -> Dict[str, Any]:
    """Explicabilidad por elemento para la lectura (evaluacion.py): índice = confianza medida, con su origen."""
    conf = ent.get("confianza")
    return {
        "elemento": nombre,
        "valor": ent.get("token") if nombre == "Estudiante" else (ent.get("matchedCanonical") or ent.get("token")),
        "indice": int(round(conf * 100)) if conf is not None else None,
        "origen_confianza": ent.get("origen_confianza"),
        "lectura_modelo": int(round(ent["lecturaModelo"] * 100)) if ent.get("origen_confianza") == ORIGEN_BETO and ent.get("lecturaModelo") is not None else None,
        "explicacion": explicar_confianza(ent),
    }


def extract_entities_from_line(
    raw_text: str,
    estudiantes: list,
    docentes: list,
    modulos: list,
    tipo_escala: Optional[str] = "CENTESIMAL_100",
    tipo_fuente: str = "ACTA",
    prob_override: Optional[dict] = None,
    apariciones_lote: int = 1,
    est_beto: Optional[dict] = None,
    doc_beto: Optional[dict] = None,
    academico_beto: Optional[dict] = None,
) -> Tuple[list, float, bool]:
    """
    Extrae y resuelve entidades desde una línea de texto plano:
    1. Rol de cada columna por la estructura de su encabezado (similitud con las claves canónicas), nunca por el archivo.
    2. Resolución contra el catálogo (CI exacta → RapidFuzz) para estudiante, docente, módulo y programa.
    3. Confianza por entidad medida según su origen (C-3) y el índice de la línea = mínimo de las confianzas.
    4. Normalización obligatoria de notas a base 100 según tipo_escala (#16).

    est_beto / doc_beto ({"nombre", "prob"}): nombre que BETO propone para el estudiante o el docente que las reglas no resolvieron
    (services/beto_integracion.py, BETO_CASCADA_FINAL). Solo se usan si no hay una resolución de reglas contra el catálogo
    (umbral 80): BETO nunca reemplaza una resolución A/B. `prob_override` se conserva por compatibilidad de la firma y ya no
    cambia la confianza: una probabilidad de BETO solo cuenta cuando la entidad la resolvió BETO.
    """
    entities = []
    is_dudoso = False
    text_clean = strip_accents(raw_text).lower()

    has_pipes = "|" in raw_text
    chunks = [c.strip() for c in raw_text.split("|") if c.strip()] if has_pipes else []

    labeled_data = {}
    for ch in chunks:
        if ":" in ch:
            k, v = ch.split(":", 1)
            labeled_data[strip_accents(k).upper().strip()] = v.strip()
    sin_columnas = not labeled_data   # texto libre: solo ahí valen los patrones sueltos

    # Texto sin columnas de asesores, docentes, sedes ni contactos, para las búsquedas sueltas
    texto_permitido = " | ".join(
        ch for ch in chunks
        if not (":" in ch and _es_encabezado_no_estudiante(strip_accents(ch.split(":", 1)[0]).upper().strip()))
    ) if chunks else raw_text

    # 1. ESTUDIANTE (etiqueta CoNLL PER sin prefijo docente)
    est_cands: List[Tuple[str, Optional[float], str]] = []   # (valor, similitud del encabezado, origen)
    for k in ["ESTUDIANTE", "ALUMNO", "POSTULANTE", "USER_LMS", "NOMBRE", "NOMBRES_Y_APELLIDOS", "NOMBRE_COMPLETO",
              "NOMBRES Y APELLIDOS", "NOMBRE COMPLETO", "APELLIDOS Y NOMBRES"]:
        if k in labeled_data and labeled_data[k]:
            est_cands.append((labeled_data[k], similitud_encabezado(k, _ENC_ESTUDIANTE), ORIGEN_ENCABEZADO))
            break

    # Nombre repartido en columnas (cobranzas, actas académicas): NOMBRES + PATERNO + MATERNO
    if not est_cands and labeled_data.get("NOMBRES"):
        claves = [k for k in ("NOMBRES", "PATERNO" if labeled_data.get("PATERNO") else "APELLIDO PATERNO",
                              "MATERNO" if labeled_data.get("MATERNO") else "APELLIDO MATERNO") if labeled_data.get(k)]
        est_cands.append((" ".join(labeled_data[k] for k in claves),
                          min(similitud_encabezado(k, _ENC_PARTES_NOMBRE) for k in claves), ORIGEN_ENCABEZADO))

    # Otra columna de nombre completo por la estructura del encabezado ('NOMBRE COMPLETO DEL USUARIO'…)
    if not est_cands:
        cols_est = [c for c in _columnas_de_rol(labeled_data, _ENC_ESTUDIANTE) if not _es_encabezado_no_estudiante(c[1])]
        if cols_est:
            est_cands.append((cols_est[0][2], cols_est[0][0], ORIGEN_ENCABEZADO))

    if not est_cands and chunks:
        for ch in chunks:
            enc = strip_accents(ch.split(":", 1)[0]).upper().strip() if ":" in ch else ""
            if enc:
                continue
            val = ch.strip()
            words = val.split()
            if not re.search(r"\d", val) and "@" not in val and 2 <= len(words) <= 4:
                val_clean = strip_accents(val).lower()
                if not any(w in val_clean for w in NON_PERSON_WORDS):
                    est_cands.append((val, None, ORIGEN_REGEX))

    if not est_cands and sin_columnas:
        m_names = re.findall(r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b", texto_permitido)
        for nm in m_names:
            nm_clean = strip_accents(nm).lower()
            if not any(w in nm_clean for w in NON_PERSON_WORDS):
                est_cands.append((nm, None, ORIGEN_REGEX))

    # Contexto del propio registro (programa / módulo) para filtrar candidatos, y CI para la resolución exacta
    contexto_reg = tuple(
        labeled_data[strip_accents(k).upper()] for k in ("PROGRAMA", "MODULO", "MÓDULO", "NOMBRE PROGRAMA", "NOMBRE_PROGRAMA", "NOMBRE MODULO")
        if labeled_data.get(strip_accents(k).upper())
    )
    ci_previo = next((labeled_data[k] for k in ("CI", "C.I.", "IDNUMBER", "CARNET", "DOCUMENTO", "DOC_IDENTIDAD/CI",
                                                "CI_ESTUDIANTE", "CEDULA DE IDENTIDAD") if labeled_data.get(k)), None)
    best_est, best_est_score, best_est_algo, est_token = None, 0.0, "None", ""
    est_sim, est_origen = (est_cands[0][1], est_cands[0][2]) if est_cands else (None, ORIGEN_REGEX)
    if est_cands:
        est_token = est_cands[0][0]
        for cand, sim_c, origen_c in est_cands:
            e, score, algo = _mejor_estudiante(cand, estudiantes, ci_previo, contexto_reg)
            if e is not None and score > best_est_score:
                best_est_score = score
                best_est_algo = algo
                best_est = e
                est_token, est_sim, est_origen = cand, sim_c, origen_c

    est_por_beto = False
    if est_beto and not (best_est and best_est_score >= 80.0):
        e_b, score_b, algo_b = _mejor_estudiante(est_beto["nombre"], estudiantes, ci_previo, contexto_reg)
        if e_b is not None and score_b >= 80.0:
            best_est, best_est_score, best_est_algo, est_token, est_por_beto = e_b, score_b, algo_b + " · nombre propuesto por BETO", est_beto["nombre"], True

    conf_est = None
    if best_est and best_est_score >= 80.0:
        conf_est = (_medida(ORIGEN_BETO, probabilidad=float(est_beto["prob"])) if est_por_beto
                    else _medida(ORIGEN_CI if "CI Exact" in best_est_algo else ORIGEN_FUZZY, catalogo=best_est_score))
        entities.append({
            "token": est_token,
            "label": "ESTUDIANTE",
            "tag": "B-ESTUDIANTE",
            "conllTag": "PER",
            **conf_est,
            **({"lecturaModelo": round(float(est_beto["prob"]), 4)} if est_por_beto else {}),
            "catalogTable": "Catálogo de Estudiantes",
            "matchedCanonical": best_est.nombre_completo,
            "canonicalId": f"EST-{best_est.id_estudiante}",
            "ci": getattr(best_est, "codigo_estudiante", None) or f"{best_est.id_estudiante}",
            "fuzzScore": round(best_est_score, 1),
            "algorithm": best_est_algo,
            "es_nuevo_perfil": False,
        })
    elif est_token:
        # Perfil nuevo: lo leyó una regla (encabezado o patrón), no BETO
        conf_est = _medida(est_origen, similitud=est_sim, validez=_validez_nombre_persona(est_token))
        entities.append({
            "token": est_token,
            "label": "ESTUDIANTE",
            "tag": "B-ESTUDIANTE",
            "conllTag": "PER",
            **conf_est,
            "catalogTable": "Catálogo de Estudiantes",
            "matchedCanonical": None,
            "canonicalId": "NO_CATALOGADO",
            "ci": None,
            "fuzzScore": 0.0,
            "algorithm": "Sin coincidencia en catálogo (Perfil Nuevo)",
            "es_nuevo_perfil": True,
        })

    # 2. DOCUMENTO / CI
    ci_match, ci_sim = None, None
    for k in ["CI", "C.I.", "IDNUMBER", "CARNET", "DOCUMENTO", "DOC_IDENTIDAD/CI", "CI_ESTUDIANTE", "CEDULA DE IDENTIDAD"]:
        if k in labeled_data and labeled_data[k]:
            ci_match, ci_sim = labeled_data[k], similitud_encabezado(k, _ENC_CI)
            break

    if not ci_match:
        m_ci = re.search(r"\b([0-9]{5,9}\b(?:\s*(?:LP|SC|CB|OR|PT|TJ|CH|BE|PA)\b)?\??)", texto_permitido, re.IGNORECASE)
        if m_ci:
            val_ci = m_ci.group(1).strip()
            if val_ci not in ["2024", "2025", "2026", "2027"]:
                ci_match = val_ci

    if ci_match:
        dudoso_ci = "?" in ci_match or len(re.sub(r"[^0-9]", "", ci_match)) < 5
        validez_ci = _validez_ci(ci_match)
        if dudoso_ci:
            is_dudoso = True
            conf_ci = _medida(ORIGEN_ENCABEZADO if ci_sim is not None else ORIGEN_REGEX, similitud=ci_sim, validez=validez_ci)
            entities.append({
                "token": ci_match,
                "label": "DOCUMENTO / CI",
                "tag": "B-CI",
                "conllTag": "REGLA_CI",
                **conf_ci,
                "catalogTable": "Catálogo de Estudiantes",
                "matchedCanonical": f"{ci_match} (Dudoso: Sufijo ?)",
                "canonicalId": "CI_DUDOSA",
                "fuzzScore": round(validez_ci * 100, 1),
                "algorithm": "Regex Validation Failed (Sufijo ?)",
            })
        else:
            ci_exacta = bool(best_est) and not est_por_beto and "CI Exact" in best_est_algo
            conf_ci = (_medida(ORIGEN_CI, catalogo=best_est_score) if ci_exacta
                       else _medida(ORIGEN_ENCABEZADO if ci_sim is not None else ORIGEN_REGEX, similitud=ci_sim, validez=validez_ci))
            entities.append({
                "token": ci_match,
                "label": "DOCUMENTO / CI",
                "tag": "B-CI",
                "conllTag": "REGLA_CI",
                **conf_ci,
                "catalogTable": "Catálogo de Estudiantes",
                "matchedCanonical": f"{ci_match} (Válido)",
                "canonicalId": getattr(best_est, "codigo_estudiante", "EST-CI") if best_est else "EST-CI",
                "fuzzScore": round((best_est_score if ci_exacta else validez_ci * 100), 1),
                "algorithm": "CI Exact Match" if ci_exacta else "Regex CI Exact Format",
            })
    else:
        # Sin documento: la entidad no se resuelve (validez del valor vacío = 0) y no entra en el índice
        entities.append({
            "token": "No provisto",
            "label": "DOCUMENTO / CI",
            "tag": "B-CI",
            "conllTag": "REGLA_CI",
            **_medida(ORIGEN_REGEX, validez=_validez_ci("")),
            "catalogTable": "Catálogo de Estudiantes",
            "matchedCanonical": "TEMP-ID (Identificador Temporal)",
            "canonicalId": "CI_NO_PROVISTO",
            "fuzzScore": 0.0,
            "algorithm": "Identificación por Nombre / TEMP-ID",
        })

    # 3. DOCENTE (C-2 b): solo de una columna con rol de docente; en texto libre, por patrón ('docente X', 'Dr. X').
    # Antes bastaba una subcadena 'ing.', 'lic.' o 'dr.' en cualquier celda ('coaching.', 'marketing.', 'dr.x@…') para
    # tomar esa celda (CARRERA, CORREO, NOMBRE DEL PROGRAMA…) como docente.
    doc_cands: List[Tuple[str, Optional[float], str]] = []
    cols_doc = _columnas_de_rol(labeled_data, _ENC_DOCENTE)
    if cols_doc:
        s_doc, _, v_doc = cols_doc[0]
        v_doc_s = v_doc.strip()
        if (
            not re.fullmatch(r"POS-?\d*", v_doc_s, re.IGNORECASE)
            and v_doc_s.strip("-_ ./").upper() not in ("", "NA", "N/A", "NONE", "NULL", "SIN DATO", "NINGUNO")
            and len(re.sub(r"[^A-Za-zÁÉÍÓÚÑáéíóúñ]", "", v_doc_s)) >= 3
        ):
            doc_cands.append((v_doc, s_doc, ORIGEN_ENCABEZADO))
    elif sin_columnas:
        for ch in chunks:   # celdas sin encabezado que empiezan con un título
            if _TITULOS_DOCENTE.match(ch):
                doc_cands.append((ch, None, ORIGEN_REGEX))
        if not doc_cands and _PISTA_DOCENTE.search(raw_text):
            m_doc = re.search(
                r"\b(?:con el docente|con la docente|docente|profesor|tutor)\s+((?:Dr\.|MSc\.|Lic\.|Ing\.|Dra\.)?\s*[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b",
                raw_text,
            )
            if m_doc:
                doc_cands.append((m_doc.group(1).strip(), None, ORIGEN_REGEX))
            else:
                m_pref = re.search(
                    r"\b((?:Dr\.|MSc\.|Lic\.|Ing\.|Dra\.)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3})\b",
                    raw_text,
                )
                if m_pref:
                    doc_cands.append((m_pref.group(1).strip(), None, ORIGEN_REGEX))

    best_doc, best_doc_score, best_doc_algo, doc_token = None, 0.0, "None", ""
    doc_sim, doc_origen = (doc_cands[0][1], doc_cands[0][2]) if doc_cands else (None, ORIGEN_REGEX)
    if doc_cands:
        doc_token = doc_cands[0][0]
        for cand, sim_c, origen_c in doc_cands:
            d, score, algo = _mejor_docente(cand, docentes, contexto_reg)
            if d is not None and score > best_doc_score:
                best_doc_score = score
                best_doc_algo = algo
                best_doc = d
                doc_token, doc_sim, doc_origen = cand, sim_c, origen_c
    elif sin_columnas and _PISTA_DOCENTE.search(raw_text):
        # Coincidencia por contexto, solo en texto libre: un docente del catálogo cuyo nombre (con forma de nombre de
        # persona, sin correos ni comentarios) aparece entero en el texto. Puntaje = % de sus palabras presentes.
        palabras_texto = set(re.findall(r"[a-z0-9ñ]+", text_clean))
        for d in docentes:
            if not _validez_nombre_persona(d.nombre_completo or ""):
                continue
            tokens_d = [t for t in re.findall(r"[a-z0-9ñ]+", strip_accents(d.nombre_completo).lower())
                        if t not in ("dr", "msc", "lic", "dra", "ing") and len(t) > 3]
            if len(tokens_d) < 2:
                continue
            score_ctx = 100.0 * sum(1 for t in tokens_d if t in palabras_texto) / len(tokens_d)
            if score_ctx > best_doc_score:
                best_doc, best_doc_score, best_doc_algo, doc_token = d, score_ctx, "Contextual Entity Match", d.nombre_completo
        if best_doc_score < UMBRAL_SIMILITUD_ENCABEZADO:
            best_doc, best_doc_score, best_doc_algo, doc_token = None, 0.0, "None", ""
        else:
            doc_origen = ORIGEN_FUZZY

    doc_por_beto = False
    if doc_beto and not (best_doc and best_doc_score >= 80.0):
        d_b, score_db, algo_db = _mejor_docente(doc_beto["nombre"], docentes, contexto_reg)
        if d_b is not None and score_db >= 80.0:
            best_doc, best_doc_score, best_doc_algo, doc_token, doc_por_beto = d_b, score_db, algo_db + " · nombre propuesto por BETO", doc_beto["nombre"], True

    conf_doc = None
    if best_doc and best_doc_score >= 80.0:
        conf_doc = (_medida(ORIGEN_BETO, probabilidad=float(doc_beto["prob"])) if doc_por_beto
                    else _medida(ORIGEN_FUZZY, catalogo=best_doc_score) if (doc_origen == ORIGEN_FUZZY or doc_sim is None)
                    else _medida(ORIGEN_ENCABEZADO, similitud=doc_sim, catalogo=best_doc_score))
        entities.append({
            "token": doc_token,
            "label": "DOCENTE",
            "tag": "B-DOCENTE",
            "conllTag": "PER",
            **conf_doc,
            **({"lecturaModelo": round(float(doc_beto["prob"]), 4)} if doc_por_beto else {}),
            "catalogTable": "Catálogo de Docentes",
            "matchedCanonical": best_doc.nombre_completo,
            "canonicalId": f"DOC-{best_doc.id_docente}",
            "fuzzScore": round(best_doc_score, 1),
            "algorithm": best_doc_algo,
            "es_nuevo_perfil": False,
        })
    elif doc_token:
        conf_doc = _medida(doc_origen, similitud=doc_sim, validez=_validez_nombre_persona(doc_token))
        entities.append({
            "token": doc_token,
            "label": "DOCENTE",
            "tag": "B-DOCENTE",
            "conllTag": "PER",
            **conf_doc,
            "catalogTable": "Catálogo de Docentes",
            "matchedCanonical": None,
            "canonicalId": "NO_CATALOGADO",
            "fuzzScore": 0.0,
            "algorithm": "Sin coincidencia en catálogo (Perfil Nuevo en Catálogo de Docentes)",
            "es_nuevo_perfil": True,
        })

    # 4. MÓDULO (C-2 c): solo de las columnas de módulo o curso; si la hoja no tiene, de la del nombre del programa.
    # Nunca de un atributo del estudiante (NIVEL ACADÉMICO, CARRERA, INSTITUCIÓN…). En texto libre, por patrón.
    mod_cands: List[Tuple[str, Optional[float], str]] = []
    cod_cols = _columnas_de_rol(labeled_data, _ENC_CODIGO_PROGRAMA) + [
        (similitud_encabezado_compuesto(k, _ENC_CODIGO_PROGRAMA), k, v)
        for k, v in labeled_data.items() if v and es_encabezado_metadato_pos(k) and similitud_encabezado(k, _ENC_CODIGO_PROGRAMA) < UMBRAL_SIMILITUD_ENCABEZADO]
    oferta_modulo = next((partes_pos(v)[0] for _, _, v in cod_cols if _validez_codigo_pos(v)), None)
    cols_mod = _columnas_de_rol(labeled_data, _ENC_MODULO) or _columnas_de_rol(labeled_data, _ENC_NOMBRE_PROGRAMA)
    for s_m, _, v_m in cols_mod:
        if _validez_texto(v_m):
            mod_cands.append((v_m, s_m, ORIGEN_ENCABEZADO))
    if sin_columnas and chunks:
        for ch in chunks:
            if any(k in ch.lower() for k in ["mod", "modulo", "diplomado", "maestria", "gestion", "big data", "estetica", "inteligencia", "especialidad", "proyectos", "auditoria"]):
                mod_cands.append((ch, None, ORIGEN_REGEX))
    elif sin_columnas:
        m_prog_free = re.search(
            r"\b((?:diplomado|maestría|maestria|especialidad|curso|programa|m[oó]dulo)\s+(?:en\s+|de\s+)?[A-ZÁÉÍÓÚÑa-záéíóúñ0-9\s]{3,35}?)(?=\s+(?:con|del?|para|obteniendo|evaluado|\.|\,|$))",
            raw_text,
            re.IGNORECASE,
        )
        if m_prog_free:
            mod_cands.append((m_prog_free.group(1).strip(), None, ORIGEN_REGEX))

    best_mod, best_mod_score, best_mod_algo, mod_token = None, 0.0, "None", ""
    mod_sim, mod_origen = (mod_cands[0][1], mod_cands[0][2]) if mod_cands else (None, ORIGEN_REGEX)
    if mod_cands:
        mod_token = mod_cands[0][0]
        for cand, sim_c, origen_c in mod_cands:
            m, score, algo = _mejor_modulo(cand, modulos, oferta_modulo or normalizar_programa(cand).pos_code)
            if m is not None and score > best_mod_score:
                best_mod_score = score
                best_mod_algo = algo
                best_mod = m
                mod_token, mod_sim, mod_origen = cand, sim_c, origen_c

    conf_mod = None
    if best_mod and best_mod_score >= 80.0:
        conf_mod = (_medida(ORIGEN_ENCABEZADO, similitud=mod_sim, catalogo=best_mod_score) if mod_sim is not None
                    else _medida(ORIGEN_FUZZY, catalogo=best_mod_score))
        entities.append({
            "token": mod_token,
            "label": "MÓDULO",
            "tag": "B-MODULO",
            "conllTag": "MISC/CATALOGO",
            **conf_mod,
            "catalogTable": "Catálogo de Módulos",
            "matchedCanonical": best_mod.nombre_modulo,
            "canonicalId": best_mod.pos_code or f"MOD-{best_mod.id_modulo}",
            "fuzzScore": round(best_mod_score, 1),
            "algorithm": best_mod_algo,
            "es_nuevo_perfil": False,
        })
    elif mod_token:
        # Módulo nuevo: lo leyó una regla; su confianza es la del encabezado y la validez del texto, no de BETO
        conf_mod = _medida(mod_origen, similitud=mod_sim, validez=_validez_texto(mod_token))
        entities.append({
            "token": mod_token,
            "label": "MÓDULO",
            "tag": "B-MODULO",
            "conllTag": "MISC/CATALOGO",
            **conf_mod,
            "catalogTable": "Catálogo de Módulos",
            "matchedCanonical": None,
            "canonicalId": "NO_CATALOGADO",
            "fuzzScore": 0.0,
            "algorithm": "Sin coincidencia en catálogo (Perfil Nuevo en Catálogo de Módulos)",
            "es_nuevo_perfil": True,
        })

    # 5. CONCEPTO FINANCIERO / MONTO / CUOTAS IMPAGAS (Perspectiva Financiera #8, #9)
    monto_val = None
    monto_pagado_val = None
    cuotas_impagas_val = None
    concepto_val, concepto_sim, monto_sim = None, None, None

    for k in _ENC_CONCEPTO:
        if k in labeled_data and labeled_data[k]:
            concepto_val, concepto_sim = labeled_data[k], similitud_encabezado(k, _ENC_CONCEPTO)
            break
    # Alias del catálogo (M5: config/mapeo_fuentes.yaml)
    for k in _ENC_MONTO:
        if k in labeled_data and labeled_data[k]:
            monto_val, monto_sim = labeled_data[k], similitud_encabezado(k, _ENC_MONTO)
            break
    for k in _ENC_MONTO_PAGADO:
        if k in labeled_data and labeled_data[k]:
            monto_pagado_val = labeled_data[k]
            break
    for k in _ENC_CUOTAS_IMPAGAS:
        if k in labeled_data and labeled_data[k]:
            cuotas_impagas_val = labeled_data[k]
            break

    if not monto_val:
        m_monto = re.search(
            r"\b(?:bs\.?|bob|bs)\s*([0-9]+(?:\.[0-9]{1,2})?)\b|\b([0-9]+(?:\.[0-9]{1,2})?)\s*(?:bs\.?|bob|bolivianos)\b",
            raw_text,
            re.IGNORECASE,
        )
        if m_monto:
            monto_val = m_monto.group(1) or m_monto.group(2)

    conf_con = None
    if concepto_val:
        conf_con = _medida(ORIGEN_ENCABEZADO, similitud=concepto_sim, validez=_validez_texto(str(concepto_val)))
        entities.append({
            "token": str(concepto_val),
            "label": "CONCEPTO_FINANCIERO",
            "tag": "B-CONCEPTO_FIN",
            "conllTag": "CATALOGO_FIN",
            **conf_con,
            "catalogTable": "Catálogo de Conceptos Financieros",
            "matchedCanonical": str(concepto_val),
            "canonicalId": "CONCEPTO-GEN",
            "fuzzScore": round(concepto_sim, 1),
            "algorithm": "Encabezado del concepto",
        })

    if monto_val:
        try:
            m_num = float(re.search(r"[0-9]+(?:\.[0-9]+)?", str(monto_val)).group(0))
            entities.append({
                "token": f"{m_num:.2f} Bs.",
                "label": "MONTO",
                "tag": "B-MONTO",
                "conllTag": "REGLA_MONTO",
                **_medida(ORIGEN_ENCABEZADO if monto_sim is not None else ORIGEN_REGEX, similitud=monto_sim, validez=_validez_numero(monto_val)),
                "catalogTable": "Situación Financiera y Cobranzas",
                "matchedCanonical": f"Bs. {m_num:.2f}",
                "canonicalId": "MONTO_VALIDO",
                "valorNumerico": m_num,
                "montoPagado": float(re.search(r"[0-9]+(?:\.[0-9]+)?", str(monto_pagado_val)).group(0)) if (monto_pagado_val and re.search(r"[0-9]+(?:\.[0-9]+)?", str(monto_pagado_val))) else 0.0,
                "cuotasImpagas": int(re.search(r"[0-9]+", str(cuotas_impagas_val)).group(0)) if (cuotas_impagas_val and re.search(r"[0-9]+", str(cuotas_impagas_val))) else 0,
                "fuzzScore": round(monto_sim, 1) if monto_sim is not None else None,
                "algorithm": "Regex Currency Format",
            })
        except Exception:
            pass

    # 5b. PROGRAMA ACADÉMICO (C-2 a): primero la columna del código (POS, NUMEROPROYECTO, N° POS…) con el patrón
    # estricto, luego la del nombre (NOMBRE DEL PROGRAMA, PROGRAMA). CARRERA, NIVEL ACADÉMICO, UNIVERSIDAD/INSTITUTO e
    # INSTITUCIÓN DONDE TRABAJA son atributos del estudiante y nunca son el programa.
    prog_token, prog_codigo, prog_nombre = None, None, None
    conf_prog = None
    for s_c, _, v_c in cod_cols:
        if _validez_codigo_pos(v_c):
            prog_codigo = partes_pos(v_c)[0]
            conf_prog = _medida(ORIGEN_ENCABEZADO, similitud=s_c, validez=_validez_codigo_pos(v_c))
            break
    cols_nom = _columnas_de_rol(labeled_data, _ENC_NOMBRE_PROGRAMA)
    if cols_nom:
        s_n, _, prog_nombre = cols_nom[0]
        if conf_prog is None and _validez_texto(prog_nombre):
            _, s_cat = _mejor_programa(normalizar_programa(prog_nombre).nombre or prog_nombre, modulos) if modulos else (None, None)
            conf_prog = (_medida(ORIGEN_ENCABEZADO, similitud=s_n, catalogo=s_cat) if s_cat is not None and s_cat >= 80.0
                         else _medida(ORIGEN_ENCABEZADO, similitud=s_n, validez=_validez_texto(prog_nombre)))
    if conf_prog is None and sin_columnas:
        m_prog = re.search(r"\b(?:nombre[_\s]+(?:del[_\s]+)?programa|programa|diplomado|maestr[ií]a|pos)\s*:\s*([^|,\n]+)", raw_text, re.IGNORECASE)
        if m_prog:
            prog_nombre = m_prog.group(1).strip()
            conf_prog = _medida(ORIGEN_REGEX, validez=_validez_texto(prog_nombre))
    programa = normalizar_programa(prog_nombre)
    prog_codigo = prog_codigo or programa.pos_code
    prog_token = (prog_codigo or prog_nombre) if conf_prog is not None else None

    if prog_token and (programa.nombre or prog_codigo):
        entities.append({
            "token": str(prog_token),
            "label": "PROGRAMA",
            "tag": "B-PROGRAMA",
            "conllTag": "ORG/CATALOGO",
            **conf_prog,
            "catalogTable": "Catálogo de Programas",
            "matchedCanonical": programa.nombre or prog_codigo,
            "nombrePrograma": prog_nombre,
            "versionPrograma": programa.version,
            "edicionPrograma": programa.edicion,
            "alcancePrograma": programa.alcance,
            "posCodigo": prog_codigo,
            "canonicalId": prog_codigo or "PROG-ADM",
            "fuzzScore": round((conf_prog.get("detalleConfianza", {}).get("similitudEncabezado") or 0.0) * 100, 1),
            "algorithm": "Código del programa (patrón POS)" if prog_codigo else "Nombre del programa por encabezado",
        })

    # 6. CALIFICACIÓN & NORMALIZACIÓN OBLIGATORIA A BASE 100 (#16)
    grade_token, grade_sim = None, None
    if (tipo_fuente or "ACTA").upper() not in ("COBRANZA", "ADMISION"):
        from pipeline.normalization.catalog_repository import obtener_catalogo_repositorio
        _repo_cat = obtener_catalogo_repositorio()
        claves_nota = _repo_cat.sinonimos_campo("nota") or list(labeled_data.keys() & {"NOTA_FINAL", "NOTA"})
        for k in claves_nota:
            if k in labeled_data and labeled_data[k]:
                grade_token, grade_sim = labeled_data[k], similitud_encabezado(k, tuple(claves_nota))
                break

        if not grade_token:
            m_grade = re.search(
                r"\b(?:con\s+la\s+nota\s+de|nota(?:\s+final)?|calificaci[oó]n|puntaje|obteniendo)\s*([0-9]{1,3}(?:\.[0-9]{1,2})?)\b|\b([0-9]{1,3}(?:\.[0-9]{1,2})?)\s*(?:pts|puntos|/100|/10|/20)\b",
                raw_text,
                re.IGNORECASE,
            )
            if m_grade:
                grade_token = m_grade.group(1) or m_grade.group(2)
            elif not chunks:
                m_simple = re.search(r"\b([0-9]{1,3}(?:\.[0-9]{1,2})?)\b", raw_text)
                if m_simple and float(m_simple.group(1)) <= 100:
                    grade_token = m_simple.group(1)

    grade_invalida = False
    grade_num = None
    raw_grade = None
    if grade_token:
        num_str = re.search(r"-?[0-9]+(?:\.[0-9]+)?", str(grade_token))
        if num_str:
            raw_grade = float(num_str.group(0))
            if tipo_escala == "DECIMAL_10":
                if raw_grade < 0.0 or raw_grade > 10.0:
                    grade_invalida = True
                grade_num = round(raw_grade * 10.0, 2)
            elif tipo_escala == "VIGESIMAL_20":
                if raw_grade < 0.0 or raw_grade > 20.0:
                    grade_invalida = True
                grade_num = round(raw_grade * 5.0, 2)
            elif tipo_escala == "CENTESIMAL_100":
                if raw_grade < 0.0 or raw_grade > 100.0:
                    grade_invalida = True
                grade_num = round(raw_grade, 2)
            else:
                grade_num = raw_grade
                grade_invalida = True

            if grade_num < 0.0 or grade_num > 100.0:
                grade_invalida = True

            entities.append({
                "token": str(grade_token),
                "label": "CALIFICACIÓN",
                "tag": "B-VALOR",
                "conllTag": "REGLA_ESCALA",
                # Validez = la nota cae dentro de la escala declarada
                **_medida(ORIGEN_ENCABEZADO if grade_sim is not None else ORIGEN_REGEX, similitud=grade_sim, validez=float(not grade_invalida)),
                "catalogTable": "Evaluación Académica",
                "notaOriginal": raw_grade,
                "notaNormalizada": grade_num,
                "tipoEscala": tipo_escala,
                "matchedCanonical": f"{grade_num:.2f} (Base 100)" if not grade_invalida else f"{raw_grade} (Escala No Declarada o Fuera de Rango)",
                "canonicalId": (
                    "NOTA_APROBADO"
                    if (not grade_invalida and grade_num >= NOTA_APROBACION)
                    else ("NOTA_REPROBADO" if not grade_invalida else ("ESCALA_AMBIGUA" if not tipo_escala else "NOTA_FUERA_ESCALA"))
                ),
                "fuzzScore": round(grade_sim, 1) if grade_sim is not None else None,
                "algorithm": "Explicit Scale Declared" if not grade_invalida else "Unspecified Scale Error",
            })

    # 7. ASISTENCIA / INASISTENCIA (Umbral de Abandono)
    asist_val, asist_sim = None, None
    es_inasistencia = False
    from pipeline.normalization.catalog_repository import obtener_catalogo_repositorio
    _repo_asist = obtener_catalogo_repositorio()
    claves_asist = _repo_asist.sinonimos_campo("asistencia") or list(labeled_data.keys() & {"ASISTENCIA", "INASISTENCIA"})
    for k in claves_asist:
        if k in labeled_data and labeled_data[k]:
            asist_val, asist_sim = labeled_data[k], similitud_encabezado(k, tuple(claves_asist))
            if "INASIST" in k or "FALTA" in k:
                es_inasistencia = True
            break

    if not asist_val:
        m_asist = re.search(
            r"\b([0-9]{1,3}(?:\.[0-9]{1,2})?)\s*%\s*(?:de\s+)?(inasistencia|asistencia|faltas)\b|\b(?:asistencia|inasistencia|asist|inasist)\s*:\s*([0-9]{1,3}(?:\.[0-9]{1,2})?%?)",
            raw_text,
            re.IGNORECASE,
        )
        if m_asist:
            asist_val = m_asist.group(1) or m_asist.group(3)
            palabra = (m_asist.group(2) or "").lower()
            if "inasist" in palabra or "falta" in palabra:
                es_inasistencia = True
            elif not palabra and ("inasist" in raw_text.lower() or "falta" in raw_text.lower()):
                es_inasistencia = True

    if asist_val:
        try:
            m_a_num = float(re.search(r"[0-9]+(?:\.[0-9]+)?", str(asist_val)).group(0))
            asist_pct = 100.0 - m_a_num if es_inasistencia else m_a_num
            inasist_pct = m_a_num if es_inasistencia else 100.0 - m_a_num
            alerta_des = inasist_pct >= 20.0 or asist_pct <= 80.0
            entities.append({
                "token": f"{m_a_num:.0f}% {'inasistencia' if es_inasistencia else 'asistencia'}",
                "label": "ASISTENCIA",
                "tag": "B-ASIST",
                "conllTag": "ASISTENCIA",
                **_medida(ORIGEN_ENCABEZADO if asist_sim is not None else ORIGEN_REGEX, similitud=asist_sim, validez=_validez_numero(asist_val)),
                "catalogTable": "Control de Asistencia",
                "asistenciaPct": asist_pct,
                "inasistenciaPct": inasist_pct,
                "alertaDesercion": alerta_des,
                "matchedCanonical": f"{asist_pct:.0f}% Asistencia",
                "canonicalId": "ASIST_ALERTA_ABANDONO" if alerta_des else "ASIST_OK",
                "fuzzScore": round(asist_sim, 1) if asist_sim is not None else None,
                "algorithm": "Regex Attendance Pattern",
            })
        except Exception:
            pass

    # ─── ÍNDICE DEL REGISTRO & COMPUERTAS DETERMINISTAS ───
    # Agregador sin cambio: el mínimo de las confianzas de estudiante, módulo, docente, programa y concepto (las mismas
    # entidades que antes). Sin ninguna de ellas no hay nada que dude y el mínimo es la cota superior de la escala.
    revision_rescate = False
    if academico_beto:
        oferta = prog_codigo or (partes_pos(best_mod.pos_code)[0] if best_mod and conf_mod else None)
        rescatadas, revision_rescate = _aplicar_rescate_academico(entities, academico_beto, modulos, oferta)
        conf_prog = rescatadas.get('PROGRAMA', conf_prog)
        conf_mod = rescatadas.get('MODULO', conf_mod)
    revision_forzada = is_dudoso or grade_invalida or revision_rescate
    confianzas = [c["confianza"] for c in (conf_est, conf_mod, conf_doc, conf_prog, conf_con)
                  if c is not None and c.get("confianza") is not None]
    score_confianza = round(min(confianzas, default=_COTA_SUPERIOR_ESCALA), 2)

    requiere_revision = revision_forzada or (score_confianza < UMBRAL_INDICE_REGISTRO_DEC)

    return entities, score_confianza, requiere_revision
