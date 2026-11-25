"""
backend/services/beto_integracion.py
------------------------------------
Uso de BETO (servicio :8006, POST /infer-batch) en el paso ③ y en la bandeja, detrás de flags apagados por defecto
(pipeline/config.py:BETO_FLAGS_POR_DEFECTO):

  BETO_CASCADA_FINAL    opción 1: tras CI_EXACTA → ENCABEZADO → FUZZY → REGEX, solo las líneas cuyo estudiante o docente las reglas no
                        resolvieron pasan a BETO. BETO nunca reemplaza una resolución de reglas (A/B): propone un nombre que se
                        resuelve contra el catálogo con la misma cascada y los mismos umbrales; si no se resuelve, la línea queda como estaba.
  BETO_ACUERDO_QC       opción 2: para cada persona que resolvieron las reglas se comprueba si BETO también ve una persona en ese
                        tramo. Si BETO ve «O» (desacuerdo) la confianza baja un escalón y la línea va a revisión con el motivo
                        DESACUERDO_REGLA_BETO.
  BETO_SUGERENCIA_HITL  opción 3: candidatos ordenados por un score combinado (similitud y probabilidad de BETO), ambos visibles.
                        Solo ordena; nunca aprueba nada.
  BETO_VENTANA          los textos de más de 128 tokens se leen con ventanas deslizantes (lo hace el servicio).

Con los flags apagados nada de este módulo se ejecuta: los llamadores conservan su camino original.
Las entidades de BETO se guardan en cache_beto_entidades por hash del texto y configuración del modelo.
La tabla NO es una migración: se crea sola en el primer uso (DDL_CACHE), solo si algún flag está encendido, para no
cambiar el conteo de 51 tablas de la DW. No existe una «migración 015» (ADW-L7, B5).
"""
import hashlib
import json
import logging
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from pipeline import config as cfg
from pipeline.semantic.indice_confianza import texto_para_indice

logger = logging.getLogger("beto_integracion")

URL_INFER_BATCH = os.getenv("BETO_INFER_BATCH_URL", "http://pipeline:8006/infer-batch")
TIPOS_PERSONA = ("ESTUDIANTE", "DOCENTE")
TIPOS_NO_PERSONA = ("MODULO", "PROGRAMA", "POS")
ETIQUETAS_ACADEMICAS = {"PROGRAMA": "PROGRAMA", "MODULO": "MÓDULO"}
_FUENTES_CON_MODULOS = {"ACTA", "MOODLE", "EVALUACION_DOCENTE"}
_FUENTES_CON_OFERTAS = _FUENTES_CON_MODULOS | {"TECHOS"}
_CONTEXTO_OFERTA = re.compile(r"\bPOS[- ]\d{3,6}\b|\b(?:POS|PROGRAMA|DIPLOMADO|CURSO|MAESTR[IÍ]A)\s*:", re.I)
_CONTEXTO_MODULO = re.compile(r"\bPOS-\d{3,6}-M\d+\b|\bM[ÓO]DULO(?:\s+\d+)?\s*:", re.I)
ACUERDO, DESACUERDO, NO_EVALUABLE, TIPO_DISTINTO = "ACUERDO", "DESACUERDO", "NO_EVALUABLE", "TIPO_DISTINTO"

DDL_CACHE = """CREATE TABLE IF NOT EXISTS public.cache_beto_entidades (
    hash_texto CHAR(64) NOT NULL, configuracion VARCHAR(80) NOT NULL, entidades TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (hash_texto, configuracion))"""


# ── flags ──────────────────────────────────────────────────────────────────────────────────────────────────────
def activo(nombre: str) -> bool:
    """Flag encendido. La variable de entorno del mismo nombre manda; sin ella vale el valor por defecto (apagado)."""
    crudo = os.getenv(nombre)
    if crudo is None:
        return bool(cfg.BETO_FLAGS_POR_DEFECTO.get(nombre, False))
    return crudo.strip().lower() in ("1", "true", "si", "sí", "yes", "on")


def necesita_refinar() -> bool:
    """True si alguna opción que lee las entidades de BETO por línea (1 o 2) está encendida."""
    return any(activo(flag) for flag in ("BETO_CASCADA_FINAL", "BETO_ACUERDO_QC", "BETO_RESCATE_ACADEMICO"))


def stride_ventana() -> int:
    return int(os.getenv("BETO_VENTANA_STRIDE", cfg.BETO_VENTANA_STRIDE))


def texto_para_beto(linea: str) -> str:
    """Texto que se manda a BETO: las primeras 8 celdas (el mismo recorte que el índice) o, con BETO_VENTANA, la línea completa."""
    return (linea or "").strip() if activo("BETO_VENTANA") else texto_para_indice(linea)


def configuracion_modelo() -> str:
    """Parte de la clave de caché que depende del modelo y de cómo se lee: cambiarla invalida las entradas."""
    from services.confianza_service import MODELO
    return f"{MODELO}|ner|" + (f"ventana{cfg.BETO_MAX_LENGTH_TOKENS}+{stride_ventana()}" if activo("BETO_VENTANA") else f"corte{cfg.BETO_MAX_LENGTH_TOKENS}")


# ── entidades y contadores ────────────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class EntidadBeto:
    tipo: str          # ESTUDIANTE | DOCENTE | MODULO | PROGRAMA ...
    texto: str
    start: int
    end: int
    score: float       # probabilidad softmax de BETO (0–1)

    def a_dict(self) -> Dict[str, Any]:
        return {"tipo": self.tipo, "texto": self.texto, "start": self.start, "end": self.end, "score": self.score}

    @staticmethod
    def de_dict(d: Dict[str, Any]) -> "EntidadBeto":
        return EntidadBeto(str(d["tipo"]), str(d["texto"]), int(d["start"]), int(d["end"]), float(d["score"]))


@dataclass
class Contadores:
    """Resumen de una pasada (lectura o consolidación) con BETO. Se suma entre archivos con sumar()."""
    lineas_totales: int = 0
    residuales_enviadas: int = 0
    residuales_academicas_enviadas: int = 0
    lineas_academicas_rescatadas: int = 0
    lineas_academicas_ambiguas: int = 0
    resueltas_por_beto: int = 0
    a_hitl: int = 0
    tiempo_beto_s: float = 0.0
    peticiones: int = 0
    textos_inferidos: int = 0
    textos_en_cache: int = 0
    comparadas_acuerdo: int = 0
    acuerdos: int = 0
    desacuerdos: int = 0
    no_evaluables: int = 0
    tipo_distinto: int = 0
    desacuerdos_por_archivo_y_tipo: Dict[str, int] = field(default_factory=dict)

    def tasa_acuerdo(self) -> Optional[float]:
        return round(self.acuerdos / self.comparadas_acuerdo, 4) if self.comparadas_acuerdo else None

    def sumar(self, otro: "Contadores") -> None:
        for k, v in otro.__dict__.items():
            if k == "desacuerdos_por_archivo_y_tipo":
                for c, n in v.items():
                    self.desacuerdos_por_archivo_y_tipo[c] = self.desacuerdos_por_archivo_y_tipo.get(c, 0) + n
            elif isinstance(v, (int, float)):
                setattr(self, k, getattr(self, k) + v)

    def como_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        d["tiempo_beto_s"] = round(self.tiempo_beto_s, 3)
        d["tasa_acuerdo"] = self.tasa_acuerdo()
        return d


# ── caché y cliente ───────────────────────────────────────────────────────────────────────────────────────────
def hash_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class CacheMemoria:
    """Misma interfaz que CacheEntidades, en memoria (pruebas)."""

    def __init__(self):
        self.datos: Dict[Tuple[str, str], str] = {}

    def leer(self, hashes: Sequence[str], configuracion: str) -> Dict[str, List[EntidadBeto]]:
        return {h: [EntidadBeto.de_dict(e) for e in json.loads(self.datos[(h, configuracion)])] for h in hashes if (h, configuracion) in self.datos}

    def guardar(self, nuevos: Dict[str, List[EntidadBeto]], configuracion: str) -> None:
        for h, ents in nuevos.items():
            self.datos.setdefault((h, configuracion), json.dumps([e.a_dict() for e in ents]))


class CacheEntidades:
    """cache_beto_entidades en giragroup_catalog_db (CATALOG_DATABASE_URL, sin tocar las 51 tablas DW de giragroup_db)."""
    LOTE_SQL = 2000
    _tabla_lista = False

    def __init__(self, session_factory: Optional[Callable[[], Any]] = None):
        self._session_factory = session_factory

    def _nueva_sesion(self):
        if self._session_factory is not None:
            return self._session_factory()
        from core.database import CatalogSessionLocal
        return CatalogSessionLocal()

    def _asegurar(self, db) -> None:
        if not CacheEntidades._tabla_lista:
            from sqlalchemy import text
            db.execute(text(DDL_CACHE))
            db.commit()
            CacheEntidades._tabla_lista = True

    def leer(self, hashes: Sequence[str], configuracion: str) -> Dict[str, List[EntidadBeto]]:
        from sqlalchemy import bindparam, text
        if not hashes:
            return {}
        out: Dict[str, List[EntidadBeto]] = {}
        db = self._nueva_sesion()
        try:
            self._asegurar(db)
            q = text("SELECT hash_texto, entidades FROM public.cache_beto_entidades WHERE configuracion = :c AND hash_texto IN :h").bindparams(
                bindparam("h", expanding=True))
            for i in range(0, len(hashes), self.LOTE_SQL):
                for h, e in db.execute(q, {"c": configuracion, "h": list(hashes[i:i + self.LOTE_SQL])}):
                    out[str(h).strip()] = [EntidadBeto.de_dict(x) for x in json.loads(e)]
        finally:
            db.close()
        return out

    def guardar(self, nuevos: Dict[str, List[EntidadBeto]], configuracion: str) -> None:
        from sqlalchemy import text
        if not nuevos:
            return
        db = self._nueva_sesion()
        try:
            self._asegurar(db)
            stmt = text(
                "INSERT INTO public.cache_beto_entidades (hash_texto, configuracion, entidades) "
                "VALUES (:h, :c, :e) ON CONFLICT DO NOTHING"
            )
            filas = [{"h": h, "c": configuracion, "e": json.dumps([e.a_dict() for e in ents])} for h, ents in nuevos.items()]
            for i in range(0, len(filas), self.LOTE_SQL):
                db.execute(stmt, filas[i:i + self.LOTE_SQL])
            db.commit()
        finally:
            db.close()


def _post_infer_batch(lote: List[str]) -> List[List[EntidadBeto]]:
    """POST /infer-batch del servicio BETO; devuelve, por texto, las entidades que BETO emitió (antes de reglas y catálogo)."""
    cuerpo: Dict[str, Any] = {"textos": lote}
    if activo("BETO_VENTANA"):
        cuerpo.update({"ventana": True, "stride": stride_ventana(), "max_length": cfg.BETO_MAX_LENGTH_TOKENS})
    req = urllib.request.Request(URL_INFER_BATCH, data=json.dumps(cuerpo).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=cfg.BETO_TIMEOUT_SEG) as resp:
        datos = json.loads(resp.read().decode("utf-8"))
    if datos.get("status") != "success":
        raise RuntimeError(datos.get("detail") or "El servicio BETO no respondió con éxito")
    salida = []
    for r in datos["resultados"]:
        salida.append([EntidadBeto(str(e["type"]), str(e["text"]), int(e["start"]), int(e["end"]), float(e["score"]))
                       for e in (r.get("entidades_beto") or [])])
    return salida


class ClienteBeto:
    """Entidades de BETO por texto con caché. `post` y `cache` son inyectables (pruebas)."""

    def __init__(self, cache=None, post: Optional[Callable[[List[str]], List[List[EntidadBeto]]]] = None,
                 configuracion: Optional[str] = None, contadores: Optional[Contadores] = None):
        # DD7: usar caché en memoria por defecto, o CacheEntidades en giragroup_catalog_db si BETO_CACHE_PERSISTENTE está activo
        if cache is not None:
            self.cache = cache
        elif activo("BETO_CACHE_PERSISTENTE"):
            self.cache = CacheEntidades()
        else:
            self.cache = CacheMemoria()
        self.post = post or _post_infer_batch
        self.configuracion = configuracion or configuracion_modelo()
        self.contadores = contadores or Contadores()

    def entidades(
        self,
        textos: Iterable[str],
        on_latido: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Optional[List[EntidadBeto]]]:
        """{texto: entidades}. None si el servicio falló para ese texto (no se cachea y el llamador no cambia nada)."""
        distintos = list(dict.fromkeys(t for t in textos if t))
        hashes = {t: hash_texto(t) for t in distintos}
        try:
            en_cache = self.cache.leer(list(hashes.values()), self.configuracion)
        except Exception as e:
            logger.warning("Caché de entidades BETO no disponible (%s); se infiere sin caché.", e)
            en_cache = {}
        resultado: Dict[str, Optional[List[EntidadBeto]]] = {t: en_cache.get(h) for t, h in hashes.items()}
        faltan = [t for t in distintos if resultado[t] is None]
        self.contadores.textos_en_cache += len(distintos) - len(faltan)
        if faltan:
            # Ordenar por longitud minimiza el padding por lote (hasta 128 tokens) en el servidor BETO
            faltan_ord = sorted(faltan, key=len)
            lotes = [faltan_ord[i:i + cfg.BETO_LOTE_TEXTOS] for i in range(0, len(faltan_ord), cfg.BETO_LOTE_TEXTOS)]
            t0 = time.perf_counter()
            respuestas = []
            with ThreadPoolExecutor(max_workers=min(cfg.BETO_PETICIONES_SIMULTANEAS, len(lotes))) as pool:
                for idx_lote, ents_lote in enumerate(pool.map(self._pedir, lotes), start=1):
                    respuestas.append(ents_lote)
                    if on_latido is not None:
                        on_latido(idx_lote, len(lotes))
            self.contadores.tiempo_beto_s += time.perf_counter() - t0
            nuevos: Dict[str, List[EntidadBeto]] = {}
            for lote, ents_lote in zip(lotes, respuestas):
                self.contadores.peticiones += 1
                if ents_lote is None:
                    continue
                for t, ents in zip(lote, ents_lote):
                    resultado[t] = ents
                    nuevos[hashes[t]] = ents
                    self.contadores.textos_inferidos += 1
            try:
                self.cache.guardar(nuevos, self.configuracion)
            except Exception as e:
                logger.warning("No se pudo guardar la caché de entidades BETO (%s).", e)
        return resultado

    def _pedir(self, lote: List[str]) -> Optional[List[List[EntidadBeto]]]:
        try:
            res = self.post(lote)
            if len(res) != len(lote):
                raise RuntimeError("el servicio devolvió un número distinto de resultados")
            return res
        except Exception as e:
            logger.warning("Servicio BETO no disponible (%s); %d textos quedan sin lectura de BETO.", e, len(lote))
            return None


# ── lectura de una línea ──────────────────────────────────────────────────────────────────────────────────────
class ResultadoLinea:
    """Lo que devuelve la extracción de una línea más lo que añadió BETO."""
    __slots__ = ("ents", "score", "req_rev", "acuerdo", "degradada_por_acuerdo", "promovida_por_beto", "beto_ents")

    def __init__(self, ents, score, req_rev):
        self.ents, self.score, self.req_rev = ents, score, req_rev
        self.acuerdo: Optional[str] = None            # ACUERDO | DESACUERDO | NO_EVALUABLE | TIPO_DISTINTO (opción 2)
        self.degradada_por_acuerdo = False             # el desacuerdo bajó la confianza de pase directo a revisión
        self.promovida_por_beto = False                # la persona la resolvió BETO con el catálogo (opción 1)
        self.beto_ents: Optional[List[EntidadBeto]] = None

    @property
    def tupla(self):
        return self.ents, self.score, self.req_rev


def entidad(ents: Sequence[Dict[str, Any]], etiqueta: str) -> Optional[Dict[str, Any]]:
    return next((e for e in ents if e.get("label") == etiqueta), None)


def persona_sin_resolver(ents: Sequence[Dict[str, Any]], etiqueta: str) -> bool:
    """Opción 1: la línea tiene (o debería tener) una persona de ese tipo y las reglas no la resolvieron contra el catálogo."""
    e = entidad(ents, etiqueta)
    if etiqueta == "ESTUDIANTE":
        return e is None or bool(e.get("es_nuevo_perfil"))
    return e is not None and bool(e.get("es_nuevo_perfil"))   # docente: solo si había candidato y no se resolvió


def academico_sin_resolver(ents: Sequence[Dict[str, Any]], tipo: str) -> bool:
    previa = entidad(ents, ETIQUETAS_ACADEMICAS[tipo])
    return previa is None or not previa.get("matchedCanonical")


_RE_COL_PROGRAMA_ESTRUCTURADA = re.compile(
    r"^(?:POS(?:\s*[-–]\s*\w+)?|N°?\s*POS|PROGRAMA|NOMBRE\s+(?:DEL\s+)?PROGRAMA|CURSO|COURSE|"
    r"DIPLOMADO|MAESTRIA|MAESTRÍA|OFERTA|PROYECTO\s*\(POS\)|COD(?:IGO)?\s*PROGRAMA|PROGRAMA\s*[-–]?\s*POS)$",
    re.IGNORECASE,
)
_RE_COL_MODULO_ESTRUCTURADA = re.compile(
    r"^(?:M[ÓO]DULO(?:\s*\d{1,2})?|N(?:RO|°|º)?\s*M[ÓO]DULO|MATERIA|ASIGNATURA|COD(?:IGO)?[_\s]*M[ÓO]DULO|"
    r"POS\s*[-–]\s*M[ÓO]DULO|NOMBRE\s+(?:DEL\s+)?M[ÓO]DULO)$",
    re.IGNORECASE,
)


def hoja_tiene_columnas_academicas(campos_por_linea: Sequence[Dict[str, str]]) -> Tuple[bool, bool]:
    """
    F7-1b: Detecta si la hoja/bloque ya posee columnas estructuradas de PROGRAMA y/o MÓDULO
    inspeccionando los encabezados presentes en las primeras filas. Permite acotar
    `BETO_RESCATE_ACADEMICO` solo a hojas sin columna estructurada.
    """
    tiene_prog = False
    tiene_mod = False
    revisadas = 0
    for campos in campos_por_linea:
        if not campos:
            continue
        for hdr in campos.keys():
            h = str(hdr or "").strip()
            if not tiene_prog and _RE_COL_PROGRAMA_ESTRUCTURADA.match(h):
                tiene_prog = True
            if not tiene_mod and _RE_COL_MODULO_ESTRUCTURADA.match(h):
                tiene_mod = True
        revisadas += 1
        if (tiene_prog and tiene_mod) or revisadas >= 10:
            break
    return tiene_prog, tiene_mod


def _residuales_academicas(
    linea: str,
    ents: Sequence[Dict[str, Any]],
    tipo_fuente: str,
    permitir_programa: bool = True,
    permitir_modulo: bool = True,
) -> list[str]:
    tiene_modulo = bool(entidad(ents, "MÓDULO") or _CONTEXTO_MODULO.search(linea))
    tiene_oferta = bool(entidad(ents, "PROGRAMA") or _CONTEXTO_OFERTA.search(linea))
    campos = {
        "PROGRAMA": permitir_programa and (tiene_oferta or tiene_modulo or tipo_fuente in _FUENTES_CON_OFERTAS),
        "MODULO": permitir_modulo and (tiene_modulo or (tiene_oferta and tipo_fuente in _FUENTES_CON_MODULOS)),
    }
    return [tipo for tipo, esperado in campos.items() if esperado and academico_sin_resolver(ents, tipo)]


def ambiguedad_academica(ents: Sequence[Dict[str, Any]]) -> Optional[str]:
    return next((e["motivoRescateBeto"] for e in ents if e.get("motivoRescateBeto")), None)


def precargar_desde_staging(cliente: ClienteBeto, stg_records: Iterable[Any]) -> int:
    """Precarga en la caché del cliente las entidades `beto_ents` guardadas en `staging_registros_crudos.payload_json` durante el paso ②."""
    precargados: Dict[str, List[EntidadBeto]] = {}
    for s_reg in stg_records:
        p_json = getattr(s_reg, "payload_json", None)
        if not isinstance(p_json, dict):
            continue
        if p_json.get('configuracion_beto') and p_json['configuracion_beto'] != cliente.configuracion:
            continue
        if activo('BETO_RESCATE_ACADEMICO') and p_json.get('configuracion_beto') != cliente.configuracion:
            continue
        for tupla in p_json.get("tuplas") or ():
            if not isinstance(tupla, dict) or "beto_ents" not in tupla:
                continue
            raw_line = tupla.get("raw_line")
            if not raw_line:
                continue
            texto_b = texto_para_beto(raw_line)
            if not texto_b:
                continue
            h_b = hash_texto(texto_b)
            if h_b not in precargados:
                try:
                    precargados[h_b] = [EntidadBeto.de_dict(e) for e in (tupla.get("beto_ents") or ())]
                except Exception:
                    continue
    if precargados:
        try:
            cliente.cache.guardar(precargados, cliente.configuracion)
        except Exception as e:
            logger.warning("No se pudo precargar beto_ents desde staging (%s).", e)
            return 0
    return len(precargados)


def persona_resuelta_por_reglas(
    e: Optional[Dict[str, Any]],
    incluir_ci_exacta: bool = True,
    permitir_sin_padron: bool = False,
    solo_fuzzy: bool = False,
) -> bool:
    if solo_fuzzy:
        fuentes = ("FUZZY",)
    else:
        fuentes = ("CI_EXACTA", "ENCABEZADO", "FUZZY") if incluir_ci_exacta else ("ENCABEZADO", "FUZZY")
    if not e or e.get("es_anonima") or e.get("canonicalId") == "EVALUACION_ANONIMA":
        return False
    fuente = str(e.get("fuente_resolucion") or e.get("origen_confianza") or "").upper()
    if fuente not in fuentes:
        return False
    if e.get("matchedCanonical"):
        return True
    return bool((not solo_fuzzy) and permitir_sin_padron and e.get("token") and fuente == "ENCABEZADO")


def _omitir_ci_exacta_en_acuerdo() -> bool:
    crudo = os.getenv("BETO_ACUERDO_OMITIR_CI_EXACTA", "1")
    return crudo.strip().lower() in ("1", "true", "si", "sí", "yes", "on")


def _acuerdo_solo_fuzzy() -> bool:
    """F6-3b (D-F6-2): acota BETO_ACUERDO_QC exclusivamente a resoluciones FUZZY (nunca veta ENCABEZADO limpio ni CI_EXACTA)."""
    crudo = os.getenv("BETO_ACUERDO_SOLO_FUZZY", "1")
    return crudo.strip().lower() in ("1", "true", "si", "sí", "yes", "on")


def _celda_del_tramo(texto: str, start: int) -> str:
    ini = texto.rfind("|", 0, start) + 1
    fin = texto.find("|", start)
    return texto[ini:fin if fin >= 0 else len(texto)]


def mejor_propuesta(ents_beto: Sequence[EntidadBeto], tipo: str, texto: str,
                    excluir_celda=None) -> Optional[EntidadBeto]:
    """Entidad de BETO del tipo pedido con mayor probabilidad, fuera de las columnas que no son personas del tipo (asesor, sede…).
    `excluir_celda` es una función encabezado → bool o un dict {tipo: función} (F5C C-2: el docente se excluye de las columnas
    sin rol de docente —ASESOR, COORDINADOR, RAZÓN SOCIAL, correos, comentarios— sin descartar las columnas DOCENTE reales,
    que la exclusión del estudiante sí descartaba)."""
    if isinstance(excluir_celda, dict):
        excluir_celda = excluir_celda.get(tipo)
    candidatas = []
    for e in ents_beto:
        if e.tipo != tipo or len(e.texto.strip()) < 3:
            continue
        celda = _celda_del_tramo(texto, e.start)
        encabezado = celda.split(":", 1)[0] if ":" in celda else ""
        if excluir_celda and encabezado and excluir_celda(encabezado):
            continue
        candidatas.append(e)
    return max(candidatas, key=lambda e: e.score) if candidatas else None


def _tramos_del_nombre(token: str, texto: str) -> Optional[List[Tuple[int, int]]]:
    """Dónde está en el texto el nombre que leyeron las reglas. Entero si aparece tal cual; si las reglas lo armaron con varias columnas
    (NOMBRES + PATERNO + MATERNO) se busca cada palabra por separado. None si alguna palabra no está en el texto."""
    def buscar(cadena: str):
        return re.search(r"(?<!\w)" + re.escape(cadena) + r"(?!\w)", texto, flags=re.IGNORECASE)

    m = buscar(token)
    if m:
        return [(m.start(), m.end())]
    tramos = []
    for palabra in token.split():
        m = buscar(palabra)
        if not m:
            return None
        tramos.append((m.start(), m.end()))
    return tramos or None


def comparar_con_beto(token: str, texto: str, ents_beto: Sequence[EntidadBeto]) -> str:
    """Opción 2: ¿ve BETO una persona en el tramo donde las reglas encontraron `token`?"""
    token = (token or "").strip()
    tramos = _tramos_del_nombre(token, texto) if token else None
    if not tramos:
        return NO_EVALUABLE   # el nombre queda fuera del texto que vio BETO (más allá de las 8 celdas o 128 tokens)
    propios = {i for a, b in tramos for i in range(a, b)}

    def cubierto(tipos):
        marcados = set()
        for e in ents_beto:
            if e.tipo in tipos:
                marcados.update(propios.intersection(range(e.start, e.end)))
        return len(marcados) / max(1, len(propios))

    if cubierto(TIPOS_PERSONA) >= cfg.BETO_SOLAPE_MINIMO_ACUERDO:
        return ACUERDO
    if cubierto(TIPOS_NO_PERSONA) >= cfg.BETO_SOLAPE_MINIMO_ACUERDO:
        return TIPO_DISTINTO
    return DESACUERDO


def bajar_un_escalon(confianza: Optional[float]) -> Optional[float]:
    """Un escalón = de la banda de pase directo (≥ 0,85) a la de revisión [0,60; 0,85). Más abajo no se toca."""
    from pipeline.config import UMBRAL_INDICE_REGISTRO_DEC
    if confianza is None or confianza < UMBRAL_INDICE_REGISTRO_DEC:
        return confianza
    return round(UMBRAL_INDICE_REGISTRO_DEC - cfg.BETO_ESCALON_DESACUERDO_MARGEN, 4)


def _clave_metrica(archivo: Optional[str], tipo_fuente: Optional[str]) -> str:
    return f"{archivo or 'sin_archivo'} | {tipo_fuente or 'sin_tipo'}"


def refinar_lineas(lineas: Sequence[str], extraer: Callable[..., Tuple[list, float, bool]], *, tipo_fuente: str,
                   cliente: ClienteBeto, contadores: Contadores, archivo: Optional[str] = None,
                   omitir: Optional[Callable[[str], bool]] = None,
                   excluir_celda=None,
                   sin_padron: bool = False,
                   permitir_rescate_programa: bool = True,
                   permitir_rescate_modulo: bool = True,
                   on_progreso: Optional[Callable[[int], None]] = None) -> List[Optional[ResultadoLinea]]:
    """
    Extracción de las líneas de un bloque con las opciones 1 y 2. `extraer(linea, est_beto=None, doc_beto=None)` es la extracción
    por reglas (extract_entities_from_line); `omitir(linea)` marca las filas que no se evalúan (ruido). Devuelve un ResultadoLinea por
    línea (None para las omitidas). La opción 1 repite la extracción solo de las residuales, con el nombre propuesto por BETO.
    """
    cascada, acuerdo = activo("BETO_CASCADA_FINAL"), activo("BETO_ACUERDO_QC")
    rescate_academico = activo("BETO_RESCATE_ACADEMICO") and tipo_fuente not in (
        "PLANIFICACION", "ERROR", "RECHAZADO", "DUPLICADO", "SIN_RECONOCER")
    incluir_ci_acuerdo = not _omitir_ci_exacta_en_acuerdo()
    solo_fuzzy_acuerdo = _acuerdo_solo_fuzzy()
    base: List[Optional[ResultadoLinea]] = []
    for idx_l, linea in enumerate(lineas):
        if on_progreso is not None and idx_l > 0 and idx_l % 250 == 0:
            on_progreso(idx_l // 2)
        if omitir and omitir(linea):
            base.append(None)
            continue
        base.append(ResultadoLinea(*extraer(linea)))
    contadores.lineas_totales += sum(1 for r in base if r is not None)

    necesita: Dict[int, str] = {}   # índice → texto para BETO
    academicas = {}
    for i, r in enumerate(base):
        if r is None:
            continue
        con_persona = tipo_fuente in cfg.BETO_TIPOS_FUENTE_CON_PERSONA
        residual = cascada and con_persona and (persona_sin_resolver(r.ents, "ESTUDIANTE") or persona_sin_resolver(r.ents, "DOCENTE"))
        comparable = acuerdo and (
            persona_resuelta_por_reglas(
                entidad(r.ents, "ESTUDIANTE"),
                incluir_ci_exacta=incluir_ci_acuerdo,
                permitir_sin_padron=sin_padron,
                solo_fuzzy=solo_fuzzy_acuerdo,
            )
            or persona_resuelta_por_reglas(
                entidad(r.ents, "DOCENTE"),
                incluir_ci_exacta=incluir_ci_acuerdo,
                permitir_sin_padron=sin_padron,
                solo_fuzzy=solo_fuzzy_acuerdo,
            )
        )
        if rescate_academico and (permitir_rescate_programa or permitir_rescate_modulo) and (
            tipos := _residuales_academicas(
                lineas[i], r.ents, tipo_fuente,
                permitir_programa=permitir_rescate_programa,
                permitir_modulo=permitir_rescate_modulo,
            )
        ):
            academicas[i] = tipos
            contadores.residuales_academicas_enviadas += 1
        if residual or comparable or i in academicas:
            necesita[i] = texto_para_beto(lineas[i])
            contadores.residuales_enviadas += int(bool(residual))
    leidas = (
        cliente.entidades(
            necesita.values(),
            on_latido=(
                lambda done, total: on_progreso(int((len(lineas) * 0.5) + (len(lineas) * 0.4 * done / max(1, total))))
            ) if on_progreso is not None else None,
        )
        if necesita
        else {}
    )

    for i, texto in necesita.items():
        r, linea = base[i], lineas[i]
        ents_beto = leidas.get(texto)
        r.beto_ents = ents_beto
        if ents_beto is None:   # el servicio falló: la línea sigue como la dejaron las reglas
            contadores.a_hitl += int(cascada and (persona_sin_resolver(r.ents, "ESTUDIANTE") or persona_sin_resolver(r.ents, "DOCENTE")))
            continue
        propuestas = {}
        for tipo in academicas.get(i, ()):
            propuesta = mejor_propuesta(ents_beto, tipo, texto, excluir_celda)
            if propuesta and propuesta.score >= cfg.UMBRAL_CONFIANZA_MEDIO:
                propuestas[tipo] = {"nombre": propuesta.texto.strip(), "prob": propuesta.score}
        if propuestas:
            r.ents, r.score, r.req_rev = extraer(linea, academico_beto=propuestas)
            contadores.lineas_academicas_rescatadas += any(
                e.get("label") in ETIQUETAS_ACADEMICAS.values() and e.get("fuente_resolucion") == "BETO" for e in r.ents)
            contadores.lineas_academicas_ambiguas += bool(ambiguedad_academica(r.ents))
        if cascada and tipo_fuente in cfg.BETO_TIPOS_FUENTE_CON_PERSONA:
            extraer_persona = partial(extraer, academico_beto=propuestas) if propuestas else extraer
            _aplicar_cascada(r, linea, texto, ents_beto, extraer_persona, contadores, excluir_celda)
        if acuerdo:
            _aplicar_acuerdo(
                r, texto, ents_beto, contadores, _clave_metrica(archivo, tipo_fuente),
                incluir_ci_exacta=incluir_ci_acuerdo,
                permitir_sin_padron=sin_padron,
                solo_fuzzy=solo_fuzzy_acuerdo,
            )
    return base


def _aplicar_cascada(r: ResultadoLinea, linea: str, texto: str, ents_beto, extraer, contadores: Contadores, excluir_celda) -> None:
    sin_est, sin_doc = persona_sin_resolver(r.ents, "ESTUDIANTE"), persona_sin_resolver(r.ents, "DOCENTE")
    if not (sin_est or sin_doc):
        return
    prop_est = mejor_propuesta(ents_beto, "ESTUDIANTE", texto, excluir_celda) if sin_est else None
    prop_doc = mejor_propuesta(ents_beto, "DOCENTE", texto, excluir_celda) if sin_doc else None
    if not (prop_est or prop_doc):
        contadores.a_hitl += 1
        return
    nuevo = ResultadoLinea(*extraer(
        linea,
        est_beto={"nombre": prop_est.texto.strip(), "prob": prop_est.score} if prop_est else None,
        doc_beto={"nombre": prop_doc.texto.strip(), "prob": prop_doc.score} if prop_doc else None))
    est_ahora, doc_ahora = entidad(nuevo.ents, "ESTUDIANTE"), entidad(nuevo.ents, "DOCENTE")
    promovida = (sin_est and persona_resuelta_por_beto(est_ahora)) or (sin_doc and persona_resuelta_por_beto(doc_ahora))
    if promovida:
        r.ents, r.score, r.req_rev, r.promovida_por_beto = nuevo.ents, nuevo.score, nuevo.req_rev, True
        contadores.resueltas_por_beto += 1
    else:
        contadores.a_hitl += 1


def persona_resuelta_por_beto(e: Optional[Dict[str, Any]]) -> bool:
    return bool(e) and bool(e.get("matchedCanonical")) and e.get("fuente_resolucion") == "BETO"


def _aplicar_acuerdo(r: ResultadoLinea, texto: str, ents_beto, contadores: Contadores, clave: str,
                     incluir_ci_exacta: bool = True, permitir_sin_padron: bool = False,
                     solo_fuzzy: bool = False) -> None:
    veredictos = []
    for etiqueta in ("ESTUDIANTE", "DOCENTE"):
        e = entidad(r.ents, etiqueta)
        if persona_resuelta_por_reglas(e, incluir_ci_exacta=incluir_ci_exacta, permitir_sin_padron=permitir_sin_padron, solo_fuzzy=solo_fuzzy):
            veredictos.append(comparar_con_beto(e.get("token"), texto, ents_beto))
    if not veredictos:
        return
    for v in veredictos:
        if v == NO_EVALUABLE:
            contadores.no_evaluables += 1
            continue
        contadores.comparadas_acuerdo += 1
        if v == ACUERDO:
            contadores.acuerdos += 1
        elif v == TIPO_DISTINTO:
            contadores.tipo_distinto += 1
        else:
            contadores.desacuerdos += 1
            contadores.desacuerdos_por_archivo_y_tipo[clave] = contadores.desacuerdos_por_archivo_y_tipo.get(clave, 0) + 1
    r.acuerdo = (DESACUERDO if DESACUERDO in veredictos else TIPO_DISTINTO if TIPO_DISTINTO in veredictos
                 else ACUERDO if ACUERDO in veredictos else NO_EVALUABLE)
    for etiqueta in ("ESTUDIANTE", "DOCENTE"):
        e = entidad(r.ents, etiqueta)
        if e is not None:
            e["acuerdo_beto"] = r.acuerdo
    if r.acuerdo == DESACUERDO:
        nuevo = bajar_un_escalon(r.score)
        r.degradada_por_acuerdo = nuevo != r.score
        r.score = nuevo
        r.req_rev = True


# ── F6-1: Extractor de Contexto de Hoja (Nivel 1, máx. 1 inferencia BETO por hoja) ───────────────────────────
_MESES_HOJA: Dict[str, int] = {
    "enero": 1, "ene": 1, "febrero": 2, "feb": 2, "marzo": 3, "mar": 3,
    "abril": 4, "abr": 4, "mayo": 5, "may": 5, "junio": 6, "jun": 6,
    "julio": 7, "jul": 7, "agosto": 8, "ago": 8, "septiembre": 9, "setiembre": 9, "sep": 9, "sept": 9,
    "octubre": 10, "oct": 10, "noviembre": 11, "nov": 11, "diciembre": 12, "dic": 12,
}
_RE_GESTION_HOJA = re.compile(r"\b(20(?:1[89]|2[0-9]|3[0-5]))\b")
_RE_MES_HOJA = re.compile(
    r"\b(" + "|".join(sorted(_MESES_HOJA.keys(), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
_RE_FECHA_ISO_HOJA = re.compile(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b")
_RE_FECHA_DMY_HOJA = re.compile(r"\b(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](20\d{2})\b")


def extraer_contexto_hoja(
    nombre_archivo: str = "",
    nombre_hoja: str = "",
    texto_pre_tabla: str = "",
    cliente: Optional[ClienteBeto] = None,
) -> Dict[str, Any]:
    """
    F6-1 (Nivel 1): Ejecuta a lo sumo 1 inferencia BETO + regex de fecha/gestión sobre
    `nombre_archivo + nombre_hoja + filas pre-tabla` (<= 128 tokens) para construir el
    diccionario mínimo `contexto_hoja` (`programa`, `modulo`, `docente`, `gestion`, `mes`, `fecha`).
    No devuelve ni persiste el texto crudo de cabecera.
    """
    partes = []
    if texto_pre_tabla:
        partes.append(str(texto_pre_tabla).strip())
    else:
        if nombre_archivo:
            stem = os.path.splitext(os.path.basename(str(nombre_archivo)))[0]
            partes.append(f"ARCHIVO: {stem}")
        if nombre_hoja:
            partes.append(f"HOJA: {str(nombre_hoja).strip()}")
    texto = " | ".join(p for p in partes if p).strip()
    palabras = texto.split()
    if len(palabras) > 90:
        texto = " ".join(palabras[:90])
    if not texto:
        return {}

    ctx: Dict[str, Any] = {}

    # 1) Regex de fecha, gestión y mes (determinista y < 1 ms)
    m_iso = _RE_FECHA_ISO_HOJA.search(texto)
    m_dmy = _RE_FECHA_DMY_HOJA.search(texto) if not m_iso else None
    if m_iso:
        anio, mes, dia = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        ctx["gestion"] = anio
        ctx["mes"] = mes
        ctx["fecha"] = f"{anio:04d}-{mes:02d}-{dia:02d}"
    elif m_dmy:
        dia, mes, anio = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        ctx["gestion"] = anio
        ctx["mes"] = mes
        ctx["fecha"] = f"{anio:04d}-{mes:02d}-{dia:02d}"
    else:
        # Priorizar fecha/gestión en nombre_hoja antes que en nombre_archivo
        texto_tiempo = f"{nombre_hoja} | {texto}"
        gestiones = [int(g) for g in _RE_GESTION_HOJA.findall(texto_tiempo)]
        if gestiones:
            # Si la hoja menciona un rango (ej. "COBRANZAS 2024 2025"), tomar la gestión más reciente
            ctx["gestion"] = max(gestiones)
        m_mes = _RE_MES_HOJA.search(texto_tiempo)
        if m_mes:
            mes_norm = m_mes.group(1).lower()
            if mes_norm in _MESES_HOJA:
                ctx["mes"] = _MESES_HOJA[mes_norm]
        if ctx.get("gestion") and ctx.get("mes"):
            ctx["fecha"] = f"{ctx['gestion']:04d}-{ctx['mes']:02d}-01"

    # 2) Una sola inferencia BETO (<= 128 tokens) para programa / modulo / docente
    if cliente is not None:
        ents_map = cliente.entidades([texto])
        ents_beto = ents_map.get(texto) or []
        for tipo_ent, clave_ctx in (("PROGRAMA", "programa"), ("MODULO", "modulo"), ("DOCENTE", "docente")):
            prop = mejor_propuesta(ents_beto, tipo_ent, texto)
            if prop and prop.score >= cfg.UMBRAL_CONFIANZA_MEDIO:
                val = prop.texto.strip()
                if val:
                    ctx[clave_ctx] = val

    return ctx


def aplicar_herencia_hoja(
    valores_fila: Dict[str, Any],
    contexto_hoja: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], bool]:
    """
    F6-1: Hereda campos de `contexto_hoja` (`programa`, `modulo`, `docente`, `gestion`, `mes`, `fecha`)
    únicamente cuando faltan en `valores_fila`. Nunca sobrescribe valores explícitos de la fila.
    Retorna `(valores_actualizados, heredado_de_hoja)`.
    """
    salida = dict(valores_fila)
    if not contexto_hoja:
        return salida, False
    heredado = False
    for clave in ("programa", "modulo", "docente", "gestion", "mes", "fecha"):
        actual = salida.get(clave)
        vacio_actual = actual is None or (isinstance(actual, str) and actual.strip() == "")
        val_ctx = contexto_hoja.get(clave)
        if vacio_actual and val_ctx not in (None, ""):
            salida[clave] = val_ctx
            heredado = True
    return salida, heredado


# ── opción 3: sugerencias ordenadas ───────────────────────────────────────────────────────────────────────────
def _similitud(a: str, b: str) -> float:
    from services.sugerencia_hitl import similitud_nombre_completo
    return similitud_nombre_completo(a, b) / 100.0


def sugerencias_ordenadas(nombre_regla: str, candidatos: Sequence[Dict[str, Any]], ents_beto: Optional[Sequence[EntidadBeto]],
                          tipo: str = "ESTUDIANTE") -> List[Dict[str, Any]]:
    """
    Candidatos (dicts con al menos 'nombre') ordenados por score combinado:
        combinado = PESO_SIMILITUD · sim(nombre de la regla, candidato) + PESO_PROBABILIDAD · prob(BETO) · sim(tramo de BETO, candidato)
    Componentes visibles: similitud, probabilidad_beto, similitud_beto, score_combinado. Sin lectura de BETO queda solo la similitud.
    Solo ordena: no aprueba ni elige.
    """
    tramo = None
    if ents_beto:
        propios = [e for e in ents_beto if e.tipo == tipo]
        if propios:   # el tramo de BETO que mejor coincide con el nombre que leyeron las reglas (si ninguno, el más probable)
            tramo = max(propios, key=lambda e: (_similitud(nombre_regla, e.texto), e.score))
    salida = []
    for c in candidatos:
        sim = _similitud(nombre_regla, c["nombre"])
        if tramo is not None:
            sim_beto = _similitud(tramo.texto, c["nombre"])
            comb = cfg.BETO_PESO_SIMILITUD * sim + cfg.BETO_PESO_PROBABILIDAD * tramo.score * sim_beto
            comp = {"probabilidad_beto": round(tramo.score, 4), "similitud_beto": round(sim_beto, 4), "tramo_beto": tramo.texto}
        else:
            comb = sim
            comp = {"probabilidad_beto": None, "similitud_beto": None, "tramo_beto": None}
        salida.append({**c, "similitud": round(sim, 4), **comp, "score_combinado": round(comb, 4)})
    salida.sort(key=lambda s: (-s["score_combinado"], -s["similitud"], str(s["nombre"]), str(s.get("id"))))
    return salida[:cfg.BETO_SUGERENCIAS_MAXIMAS]


def candidatos_por_similitud(nombre: str, personas: Sequence[Any], corte: Optional[float] = None) -> List[Dict[str, Any]]:
    """Personas del catálogo (objetos con id_estudiante/id_docente y nombre_completo) cuyo nombre se parece al leído (token_sort_ratio)."""
    from rapidfuzz import fuzz, process
    from services.dataops_evaluation_service import enmascarar_ci
    if not nombre or not personas:
        return []
    corte = cfg.BETO_SUGERENCIA_CORTE_SIMILITUD if corte is None else corte
    nombres = [getattr(p, "nombre_completo", None) or "" for p in personas]
    salida = []
    for _, _, i in process.extract(nombre, nombres, scorer=fuzz.token_sort_ratio, score_cutoff=corte, limit=cfg.BETO_SUGERENCIAS_MAXIMAS * 3):
        p = personas[i]
        id_p = getattr(p, "id_estudiante", None) or getattr(p, "id_docente", None)
        ci = getattr(p, "ci_numero", None) or getattr(p, "ci", None)
        salida.append({"id": id_p, "nombre": nombres[i], "ci_enmascarado": enmascarar_ci(ci) if ci else None,
                       "programa": getattr(p, "programa_origen", None)})
    return salida


def hacer_sugeridor(cliente: ClienteBeto, personas: Sequence[Any], tipo: str = "ESTUDIANTE") -> Callable[..., List[Dict[str, Any]]]:
    """
    Función (nombre_leido, candidatos|None, texto_para_beto) → sugerencias ordenadas con ambos componentes. Si no se dan candidatos se buscan
    por similitud en `personas`. La lectura de BETO viene de la caché o de /infer-batch; si falla se ordena solo por similitud.
    """
    from rapidfuzz import fuzz, process
    from services.dataops_evaluation_service import enmascarar_ci

    corte_def = cfg.BETO_SUGERENCIA_CORTE_SIMILITUD
    nombres_cache = [getattr(p, "nombre_completo", None) or "" for p in personas]
    meta_cache = [
        {
            "id": getattr(p, "id_estudiante", None) or getattr(p, "id_docente", None),
            "nombre": nombres_cache[idx],
            "ci_enmascarado": enmascarar_ci(ci) if (ci := (getattr(p, "ci_numero", None) or getattr(p, "ci", None))) else None,
            "programa": getattr(p, "programa_origen", None),
        }
        for idx, p in enumerate(personas)
    ]
    sim_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _cands_rapidos(nombre: str) -> List[Dict[str, Any]]:
        if not nombre or not nombres_cache:
            return []
        hit = sim_cache.get(nombre)
        if hit is not None:
            return hit
        encontrados = [
            meta_cache[i]
            for _, _, i in process.extract(
                nombre, nombres_cache, scorer=fuzz.token_sort_ratio,
                score_cutoff=corte_def, limit=cfg.BETO_SUGERENCIAS_MAXIMAS * 3,
            )
        ]
        sim_cache[nombre] = encontrados
        return encontrados

    def sugerir(nombre: str, candidatos: Optional[Sequence[Dict[str, Any]]] = None, texto: Optional[str] = None) -> List[Dict[str, Any]]:
        cands = list(candidatos) if candidatos else _cands_rapidos(nombre)
        if not cands:
            return []
        ents = cliente.entidades([texto]).get(texto) if texto else None
        return sugerencias_ordenadas(nombre, cands, ents, tipo)
    return sugerir
