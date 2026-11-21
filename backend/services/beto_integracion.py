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
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from pipeline import config as cfg
from pipeline.semantic.indice_confianza import texto_para_indice

logger = logging.getLogger("beto_integracion")

URL_INFER_BATCH = os.getenv("BETO_INFER_BATCH_URL", "http://pipeline:8006/infer-batch")
TIPOS_PERSONA = ("ESTUDIANTE", "DOCENTE")
TIPOS_NO_PERSONA = ("MODULO", "PROGRAMA", "POS")
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
    return activo("BETO_CASCADA_FINAL") or activo("BETO_ACUERDO_QC")


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
    """cache_beto_entidades (se crea en el primer uso, sin migración). Si la base no responde, el cliente sigue sin caché."""
    LOTE_SQL = 2000
    _tabla_lista = False

    def _asegurar(self, db) -> None:
        if not CacheEntidades._tabla_lista:
            from sqlalchemy import text
            db.execute(text(DDL_CACHE))
            db.commit()
            CacheEntidades._tabla_lista = True

    def leer(self, hashes: Sequence[str], configuracion: str) -> Dict[str, List[EntidadBeto]]:
        from sqlalchemy import bindparam, text
        from core.database import SessionLocal
        out: Dict[str, List[EntidadBeto]] = {}
        db = SessionLocal()
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
        from core.database import SessionLocal
        if not nuevos:
            return
        db = SessionLocal()
        try:
            self._asegurar(db)
            for h, ents in nuevos.items():
                db.execute(text("INSERT INTO public.cache_beto_entidades (hash_texto, configuracion, entidades) VALUES (:h, :c, :e) "
                                "ON CONFLICT DO NOTHING"), {"h": h, "c": configuracion, "e": json.dumps([e.a_dict() for e in ents])})
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
        self.cache = cache if cache is not None else CacheEntidades()
        self.post = post or _post_infer_batch
        self.configuracion = configuracion or configuracion_modelo()
        self.contadores = contadores or Contadores()

    def entidades(self, textos: Iterable[str]) -> Dict[str, Optional[List[EntidadBeto]]]:
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
            lotes = [faltan[i:i + cfg.BETO_LOTE_TEXTOS] for i in range(0, len(faltan), cfg.BETO_LOTE_TEXTOS)]
            t0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=min(cfg.BETO_PETICIONES_SIMULTANEAS, len(lotes))) as pool:
                respuestas = list(pool.map(self._pedir, lotes))
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


def persona_resuelta_por_reglas(e: Optional[Dict[str, Any]]) -> bool:
    return bool(e) and bool(e.get("matchedCanonical")) and (e.get("fuente_resolucion") in ("CI_EXACTA", "ENCABEZADO", "FUZZY"))


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
                   excluir_celda=None) -> List[Optional[ResultadoLinea]]:
    """
    Extracción de las líneas de un bloque con las opciones 1 y 2. `extraer(linea, est_beto=None, doc_beto=None)` es la extracción
    por reglas (extract_entities_from_line); `omitir(linea)` marca las filas que no se evalúan (ruido). Devuelve un ResultadoLinea por
    línea (None para las omitidas). La opción 1 repite la extracción solo de las residuales, con el nombre propuesto por BETO.
    """
    cascada, acuerdo = activo("BETO_CASCADA_FINAL"), activo("BETO_ACUERDO_QC")
    base: List[Optional[ResultadoLinea]] = []
    for linea in lineas:
        if omitir and omitir(linea):
            base.append(None)
            continue
        base.append(ResultadoLinea(*extraer(linea)))
    contadores.lineas_totales += sum(1 for r in base if r is not None)

    necesita: Dict[int, str] = {}   # índice → texto para BETO
    for i, r in enumerate(base):
        if r is None:
            continue
        con_persona = tipo_fuente in cfg.BETO_TIPOS_FUENTE_CON_PERSONA
        residual = cascada and con_persona and (persona_sin_resolver(r.ents, "ESTUDIANTE") or persona_sin_resolver(r.ents, "DOCENTE"))
        comparable = acuerdo and (persona_resuelta_por_reglas(entidad(r.ents, "ESTUDIANTE")) or persona_resuelta_por_reglas(entidad(r.ents, "DOCENTE")))
        if residual or comparable:
            necesita[i] = texto_para_beto(lineas[i])
            contadores.residuales_enviadas += int(bool(residual))
    leidas = cliente.entidades(necesita.values()) if necesita else {}

    for i, texto in necesita.items():
        r, linea = base[i], lineas[i]
        ents_beto = leidas.get(texto)
        r.beto_ents = ents_beto
        if ents_beto is None:   # el servicio falló: la línea sigue como la dejaron las reglas
            contadores.a_hitl += int(cascada and (persona_sin_resolver(r.ents, "ESTUDIANTE") or persona_sin_resolver(r.ents, "DOCENTE")))
            continue
        if cascada and tipo_fuente in cfg.BETO_TIPOS_FUENTE_CON_PERSONA:
            _aplicar_cascada(r, linea, texto, ents_beto, extraer, contadores, excluir_celda)
        if acuerdo:
            _aplicar_acuerdo(r, texto, ents_beto, contadores, _clave_metrica(archivo, tipo_fuente))
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


def _aplicar_acuerdo(r: ResultadoLinea, texto: str, ents_beto, contadores: Contadores, clave: str) -> None:
    veredictos = []
    for etiqueta in ("ESTUDIANTE", "DOCENTE"):
        e = entidad(r.ents, etiqueta)
        if persona_resuelta_por_reglas(e):
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
    def sugerir(nombre: str, candidatos: Optional[Sequence[Dict[str, Any]]] = None, texto: Optional[str] = None) -> List[Dict[str, Any]]:
        cands = list(candidatos) if candidatos else candidatos_por_similitud(nombre, personas)
        if not cands:
            return []
        ents = cliente.entidades([texto]).get(texto) if texto else None
        return sugerencias_ordenadas(nombre, cands, ents, tipo)
    return sugerir
