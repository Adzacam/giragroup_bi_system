"""
backend/services/bandeja_grupos.py
----------------------------------
Agrupa los casos pendientes de la bandeja HITL por (motivo, valor normalizado) para aprobarlos de una vez.
- CI_NOMBRE_DISCORDANTE: el CI del caso.  - HOMONIMIA: el nombre sin títulos ni acentos.
- BAJA_CONFIANZA_IA y otros: la forma de la línea (encabezados sin valores, dígitos como '#'); sin encabezados, el texto normalizado.
"""
import re
import unicodedata
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models.fact_financiero import FactSituacionFinanciera
from models.fact_rendimiento import FactRendimientoAcademico
from models.staging_entidad import StagingEntidadNoResuelta
from services.dataops_privacy import texto_publico

MOTIVOS_INFORMATIVOS = frozenset({"HOJA_IGNORADA", "SIN_INFORMACION"})

MOTIVOS_CATALOGO = {
    "HOJA_IGNORADA": "Hoja ignorada por regla de lectura (solo informativo)",
    "NOTA_FUERA_DE_RANGO": "Nota fuera de rango (debe estar entre 0 y 100)",
    "RESPUESTA_EN_COLUMNA_EQUIVOCADA": "Respuesta en columna equivocada (escala cruzada)",
    "CUOTAS_NEGATIVAS": "Cuotas en mora negativas en la fuente (ajustadas a 0)",
    "CONFLICTO_META": "Conflicto de meta entre fuentes (resuelto por prioridad)",
    "CONFLICTO_FUENTES": "Conflicto entre fuentes (resuelto por prioridad)",
    "VALOR_FUERA_DE_CATALOGO": "Valor fuera de catálogo o vocabulario",
    "PUNTUACION_FUERA_DE_ESCALA": "Puntuación fuera de escala",
    "ESCALA_NO_INFERIBLE": "Escala de evaluación no inferible",
    "DESACUERDO_REGLA_BETO": "Las reglas y BETO no coinciden en la persona",
    "RELACION_INCOHERENTE": "Relación incoherente entre entidades y catálogo",
}

EXPLICACION_MOTIVOS = {
    "HOJA_IGNORADA": ("Regla de lectura por contenido y visibilidad", "Hoja oculta, auxiliar, resumen o sin tabla de datos"),
    "NOTA_FUERA_DE_RANGO": ("Rango válido de nota académica", "0 ≤ nota ≤ 100"),
    "RESPUESTA_EN_COLUMNA_EQUIVOCADA": ("Correspondencia de etiqueta con la escala de la pregunta", "Etiqueta perteneciente al diccionario de la columna"),
    "CUOTAS_NEGATIVAS": ("Validación de cuotas en mora", "cuotas_impagas ≥ 0 (negativos ajustados a 0)"),
    "CONFLICTO_META": ("Prioridad por tipo de fuente (RENTABILIDAD > EGRESOS)", "Diferencia entre fuentes > 0,02 Bs"),
    "CONFLICTO_FUENTES": ("Prioridad por tipo de fuente (RENTABILIDAD > EGRESOS)", "Diferencia entre fuentes > 0,02 Bs"),
    "VALOR_FUERA_DE_CATALOGO": ("Validación contra vocabulario canónico del catálogo", "Valor reconocido en cat_* o diccionario YAML"),
    "PUNTUACION_FUERA_DE_ESCALA": ("Rango válido de puntuación de encuesta", "1 ≤ puntuación ≤ escala_max (5 o 10)"),
    "ESCALA_NO_INFERIBLE": ("Detección de escala máxima de encuesta", "Cabecera o ≥ 1 respuesta numérica en [1, 10]"),
    "CI_NOMBRE_DISCORDANTE": ("Cruce de cédula exacta vs nombre en catálogo", "Similitud de nombre < 85 %"),
    "HOMONIMIA": ("Detección de homónimos por similitud de nombre", "Similitud ≥ 90 % sin CI exacta"),
    "CI_DUDOSA": ("Validación de formato y longitud de cédula", "Cédula numérica válida (5–10 dígitos)"),
    "CI_ILEGIBLE": ("Validación de formato y longitud de cédula", "Cédula numérica válida (5–10 dígitos)"),
    "BAJA_CONFIANZA_IA": ("Compuerta de confianza de lectura BETO", "Confianza ≥ 0,85 para aceptación directa"),
    "BAJA_CONFIANZA": ("Compuerta de confianza de lectura BETO", "Confianza ≥ 0,85 para aceptación directa"),
    "HECHO_EN_REVISION": ("Validación de integridad de hecho cargado", "Campos obligatorios completos y estado en catálogo"),
    "POS_NO_EN_DIM_MODULO": ("Resolución de programa/módulo contra catálogo", "Similitud ≥ 80 % con dim_modulo"),
    "FECHA_INSCRIPCION_INVALIDA": ("Validación de fecha de inscripción", "Fecha válida dentro del rango académico"),
    "FILA_SIN_IDENTIDAD": ("Cascada de identidad (CI → Encabezado → Fuzzy → Regex → BETO)", "Al menos estudiante o CI identificable"),
    "DESACUERDO_REGLA_BETO": ("Control de calidad regla vs BETO (QC)", "La regla encontró una persona donde BETO etiquetó O"),
    "RELACION_INCOHERENTE": ("Validación de relaciones antes de insertar al DW", "Coherencia entre estudiante, programa, módulo, docente, pago y fecha"),
}


def es_fila_vacia_sin_confianza(texto: Optional[str], nivel_confianza: Optional[float]) -> bool:
    """Descarta filas vacías con confianza 0,0000 (p. ej. 5 filas vacías del doc 44)."""
    if nivel_confianza is None or float(nivel_confianza) > 0.0:
        return False
    t = (texto or "").strip()
    if not t:
        return True
    celdas = [c.strip() for c in t.split("|") if c.strip()]
    for c in celdas:
        _, sep, val = c.partition(":")
        contenido = val.strip() if sep else c
        if contenido and re.search(r"[A-Za-z0-9ÁÉÍÓÚÑáéíóúñ]", contenido):
            return False
    return True


def explicacion_motivo(
    motivo: Optional[str],
    texto: Optional[str] = None,
    score_fuzzy: Optional[float] = None,
    nivel_confianza: Optional[float] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Explicación estructurada sin PII (regla, umbral, valor_enmascarado) vía dataops_privacy.py."""
    m = (motivo or "REVISION_GENERAL").upper()
    regla, umbral = EXPLICACION_MOTIVOS.get(
        m, ("Regla de validación DataOps", "Cumplimiento de catálogo y esquema")
    )
    if m == "CI_NOMBRE_DISCORDANTE" and score_fuzzy is not None:
        umbral = f"Similitud {float(score_fuzzy):.1f} % < 85 %"
    elif m in ("BAJA_CONFIANZA_IA", "BAJA_CONFIANZA") and nivel_confianza is not None:
        umbral = f"Confianza {float(nivel_confianza):.2f} < 0,85"
    bruto = texto or (payload.get("ejemplo") if isinstance(payload, dict) else "") or ""
    valor_enmascarado = texto_publico(str(bruto))[:240] if bruto else "Sin valor registrado"
    return {
        "regla": regla,
        "umbral": umbral,
        "valor_enmascarado": valor_enmascarado,
    }


def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t or "") if unicodedata.category(c) != "Mn")


def valor_normalizado(motivo: Optional[str], texto: Optional[str]) -> str:
    t = (texto or "").strip()
    m = (motivo or "").upper()
    if m == "CI_NOMBRE_DISCORDANTE":
        ci = re.search(r"CI:\s*([0-9A-Za-z\-]+)", t)
        return ci.group(1).upper() if ci else _sin_acentos(t).lower()[:80]
    if m == "HOMONIMIA":
        from pipeline.normalization.person_resolver import quitar_titulos
        return quitar_titulos(t)[:80]
    if m == "VALOR_FUERA_DE_CATALOGO":
        return re.sub(r"\d+", "#", _sin_acentos(t).lower())[:120]
    celdas = [c.strip() for c in t.split("|") if c.strip()]
    hdrs = [c.partition(": ")[0] for c in celdas if ": " in c]
    base = " | ".join(hdrs) if hdrs else " | ".join(celdas)
    return re.sub(r"\d+", "#", _sin_acentos(base).lower())[:120]


def clave_grupo(
    motivo: Optional[str],
    texto: Optional[str],
    score_fuzzy: Optional[float] = None,
    id_documento: Optional[int] = None,
) -> str:
    m_up = (motivo or "").upper()
    if m_up == "CI_NOMBRE_DISCORDANTE" and (score_fuzzy is not None or id_documento is not None):
        codigo, _ = banda_discordancia(score_fuzzy)
        if id_documento is not None:
            return f"CI_NOMBRE_DISCORDANTE::doc{id_documento}::{codigo}"
        return f"CI_NOMBRE_DISCORDANTE::{codigo}"
    return f"{m_up}::{valor_normalizado(motivo, texto)}"


# ADW-L8 / F12: 748 discordancias de nombre de una sola fuente (ARCA) tenían 720 CI distintas, así que agrupar por CI no
# agrupaba nada. El patrón de triage es la banda de similitud (casi_igual >= 60, parcial 30-59, muy_distinto < 30).
PATRONES_DISCORDANCIA = (
    (30, "muy_distinto", "Nombre muy distinto (similitud < 30)"),
    (60, "parcial", "Nombre parcialmente distinto (30 a 59)"),
    (101, "casi_igual", "Nombre casi igual (60 o más)"),
)


def banda_discordancia(score_fuzzy) -> tuple[str, str]:
    if score_fuzzy is None:
        return ("casi_igual", "Nombre casi igual (60 o más)")
    val = float(score_fuzzy)
    for tope, codigo, etiqueta in PATRONES_DISCORDANCIA:
        if val < tope:
            return (codigo, etiqueta)
    return (PATRONES_DISCORDANCIA[-1][1], PATRONES_DISCORDANCIA[-1][2])


def patron_discordancia(score_fuzzy) -> str:
    if score_fuzzy is None:
        return "Sin similitud calculada"
    return banda_discordancia(score_fuzzy)[1]


def grupos_pendientes(db: Session, doc_ids: Optional[List[int]] = None, limite: int = 500) -> Dict[str, Any]:
    """Grupos de casos de staging pendientes: [{clave, motivo, valor, n, ejemplo, ids}] por tamaño; total de casos y de grupos."""
    q = db.query(
        StagingEntidadNoResuelta.id_staging,
        StagingEntidadNoResuelta.motivo,
        StagingEntidadNoResuelta.texto_original,
        StagingEntidadNoResuelta.score_fuzzy,
        StagingEntidadNoResuelta.nivel_confianza,
        StagingEntidadNoResuelta.id_documento,
    ).filter(
        StagingEntidadNoResuelta.resuelto == False  # noqa: E712
    )
    if doc_ids is not None:
        q = q.filter(StagingEntidadNoResuelta.id_documento.in_(list(doc_ids)))
    grupos: Dict[str, Dict[str, Any]] = {}
    n_casos = 0
    patrones: Dict[str, Dict[str, Any]] = {}
    reglas_resumen: Dict[str, Dict[str, Any]] = {}
    descartadas_vacias = 0
    for id_stg, motivo, texto, score, conf, id_doc in q.order_by(StagingEntidadNoResuelta.id_staging).yield_per(200):
        m_up = (motivo or "").upper()
        if m_up in MOTIVOS_INFORMATIVOS:
            continue
        if es_fila_vacia_sin_confianza(texto, conf):
            descartadas_vacias += 1
            continue
        n_casos += 1
        k = clave_grupo(motivo, texto, score_fuzzy=score, id_documento=id_doc)
        g = grupos.setdefault(k, {
            "clave": k,
            "motivo": motivo,
            "valor": valor_normalizado(motivo, texto),
            "n": 0,
            "ejemplo": texto_publico(texto or "")[:160],
            "ids": [],
            "id_documento": id_doc,
            "explicacion": explicacion_motivo(motivo, texto, score_fuzzy=score, nivel_confianza=conf),
        })
        g["n"] += 1
        if m_up == "CI_NOMBRE_DISCORDANTE":
            codigo_pat, etiqueta = banda_discordancia(score)
            g.setdefault("patron", etiqueta)
            g.setdefault("patron_codigo", codigo_pat)
            pat = patrones.setdefault(codigo_pat, {
                "codigo": codigo_pat,
                "motivo": "CI_NOMBRE_DISCORDANTE",
                "patron": etiqueta,
                "n": 0,
                "grupos": set(),
            })
            pat["n"] += 1
            pat["grupos"].add(k)
        reg = reglas_resumen.setdefault(m_up, {"motivo": m_up, "n": 0, "grupos": set()})
        reg["n"] += 1
        reg["grupos"].add(k)
        if len(g["ids"]) < 50:
            g["ids"].append(id_stg)
    for k, g in _grupos_hechos(db, doc_ids).items():
        n_casos += g["n"]
        g.setdefault("explicacion", explicacion_motivo("HECHO_EN_REVISION", g.get("ejemplo")))
        grupos[k] = g
        reg = reglas_resumen.setdefault("HECHO_EN_REVISION", {"motivo": "HECHO_EN_REVISION", "n": 0, "grupos": set()})
        reg["n"] += g["n"]
        reg["grupos"].add(k)
    ordenados = sorted(grupos.values(), key=lambda g: -g["n"])
    lista_patrones = sorted(({**p, "grupos": len(p["grupos"])} for p in patrones.values()), key=lambda p: -p["n"])
    lista_reglas = sorted(({**r, "grupos": len(r["grupos"])} for r in reglas_resumen.values()), key=lambda r: -r["n"])
    return {
        "total_casos": n_casos,
        "total_grupos": len(ordenados),
        "grupos": ordenados[:limite],
        "patrones": lista_patrones,
        "reglas_resumen": lista_reglas,
        "descartadas_vacias": descartadas_vacias,
    }


def motivo_estado(aca, tut, arca) -> str:
    """OK, ESTADO_FUERA_DE_CATALOGO o COMBINACION_INVALIDA según el catálogo vigente de estados de acta."""
    from services.catalogo_estados import reglas_estado
    from pipeline.normalization.quality_rules import canonizar_estado, validar_combinacion_estados
    r = reglas_estado()
    ca, oka = canonizar_estado(aca, r.academicos)
    ct, okt = canonizar_estado(tut, r.tutoria)
    car, okar = canonizar_estado(arca, r.arca)
    if not (oka and okt and okar):
        return "ESTADO_FUERA_DE_CATALOGO"
    return "OK" if validar_combinacion_estados(ca, ct, car, r.combinaciones)[0] else "COMBINACION_INVALIDA"


def _faltan_aca(h) -> str:
    return ",".join(f for f, falta in (("estudiante", not h[2]), ("modulo", not h[3]), ("nota", h[4] is None), ("fecha", not h[5])) if falta) or "ninguno"


def _grupos_hechos(db: Session, doc_ids: Optional[List[int]] = None) -> Dict[str, Dict[str, Any]]:
    """Hechos en revisión agrupados por (área, documento, campos faltantes, estados de acta): un grupo = una misma situación."""
    out: Dict[str, Dict[str, Any]] = {}
    q = db.query(FactRendimientoAcademico.id_hecho_aca, FactRendimientoAcademico.id_documento, FactRendimientoAcademico.id_estudiante,
                 FactRendimientoAcademico.id_modulo, FactRendimientoAcademico.nota_final, FactRendimientoAcademico.id_tiempo,
                 FactRendimientoAcademico.estado_academico, FactRendimientoAcademico.estado_arca,
                 FactRendimientoAcademico.estado_tutoria).filter(
        FactRendimientoAcademico.requiere_revision == True)  # noqa: E712
    if doc_ids is not None:
        q = q.filter(FactRendimientoAcademico.id_documento.in_(list(doc_ids)))
    for h in q.all():
        me = motivo_estado(h[6], h[8], h[7])
        v = f"academico|doc{h[1]}|falta:{_faltan_aca(h)}|{h[6]}|{h[8]}|{h[7]}|estado:{me}"
        accion = ("MAPEAR_ESTADO" if me != "OK" else "APROBAR" if _faltan_aca(h) == "ninguno"
                  else "CORREGIR_FECHA" if _faltan_aca(h) == "fecha" else "MANUAL")
        g = out.setdefault(f"HECHO_EN_REVISION::{v}", {"clave": f"HECHO_EN_REVISION::{v}", "motivo": "HECHO_EN_REVISION", "valor": v, "n": 0,
                                                      "ejemplo": f"HECHO-ACA-{h[0]}", "ids": [], "un_clic": accion == "APROBAR", "accion_grupo": accion})
        g["n"] += 1
        if len(g["ids"]) < 50:
            g["ids"].append(f"HECHO-ACA-{h[0]}")
    q = db.query(FactSituacionFinanciera.id_hecho_fin, FactSituacionFinanciera.id_documento, FactSituacionFinanciera.id_estudiante,
                 FactSituacionFinanciera.id_tiempo, FactSituacionFinanciera.monto_deuda).filter(FactSituacionFinanciera.requiere_revision == True)  # noqa: E712
    if doc_ids is not None:
        q = q.filter(FactSituacionFinanciera.id_documento.in_(list(doc_ids)))
    for h in q.all():
        faltan = ",".join(f for f, falta in (("estudiante", not h[2]), ("fecha", not h[3]), ("monto", h[4] is None)) if falta) or "ninguno"
        v = f"financiero|doc{h[1]}|falta:{faltan}"
        g = out.setdefault(f"HECHO_EN_REVISION::{v}", {"clave": f"HECHO_EN_REVISION::{v}", "motivo": "HECHO_EN_REVISION", "valor": v, "n": 0,
                                                      "ejemplo": f"HECHO-FIN-{h[0]}", "ids": [], "un_clic": faltan == "ninguno",
                                                      "accion_grupo": "APROBAR" if faltan == "ninguno" else "CORREGIR_FECHA" if faltan == "fecha" else "MANUAL"})
        g["n"] += 1
        if len(g["ids"]) < 50:
            g["ids"].append(f"HECHO-FIN-{h[0]}")
    from services.revision_hechos import _q_eval
    for id_doc, id_mod, _, _, _ in _q_eval(db, doc_ids).all():
        v = f'evaluacion|doc{id_doc or 0}|mod{id_mod or 0}'
        clave = f'HECHO_EN_REVISION::{v}'
        out[clave] = {'clave': clave, 'motivo': 'HECHO_EN_REVISION', 'valor': v, 'n': 1,
                      'ejemplo': 'Evaluación docente pendiente de vinculación o fecha.',
                      'ids': [f'HECHO-EVA-{id_doc or 0}-{id_mod or 0}'], 'accion_grupo': 'MANUAL', 'un_clic': False}
    return out


def ids_del_grupo(db: Session, clave: str, doc_ids: Optional[List[int]] = None) -> List[Any]:
    motivo = clave.split("::", 1)[0]
    if motivo.upper() in MOTIVOS_INFORMATIVOS:
        return []
    if motivo == "HECHO_EN_REVISION":
        g = _grupos_hechos(db, doc_ids).get(clave)
        if not g:
            return []
        # los ids del grupo (todos, no solo los 50 de muestra) se recuperan con la misma regla
        return _ids_hechos(db, clave, doc_ids)
    q = db.query(
        StagingEntidadNoResuelta.id_staging,
        StagingEntidadNoResuelta.motivo,
        StagingEntidadNoResuelta.texto_original,
        StagingEntidadNoResuelta.nivel_confianza,
        StagingEntidadNoResuelta.score_fuzzy,
        StagingEntidadNoResuelta.id_documento,
    ).filter(
        StagingEntidadNoResuelta.resuelto == False, StagingEntidadNoResuelta.motivo == motivo)  # noqa: E712
    if doc_ids is not None:
        q = q.filter(StagingEntidadNoResuelta.id_documento.in_(list(doc_ids)))
    return [
        i for i, m, t, conf, score, id_doc in q.order_by(StagingEntidadNoResuelta.id_staging).all()
        if not es_fila_vacia_sin_confianza(t, conf) and clave_grupo(m, t, score_fuzzy=score, id_documento=id_doc) == clave
    ]


def _ids_hechos(db: Session, clave: str, doc_ids: Optional[List[int]]) -> List[str]:
    v = clave.split("::", 1)[1]
    ids = []
    if v.startswith('evaluacion|'):
        grupo = _grupos_hechos(db, doc_ids).get(clave)
        return grupo['ids'] if grupo else []
    if v.startswith("academico"):
        q = db.query(FactRendimientoAcademico.id_hecho_aca, FactRendimientoAcademico.id_documento, FactRendimientoAcademico.id_estudiante,
                     FactRendimientoAcademico.id_modulo, FactRendimientoAcademico.nota_final, FactRendimientoAcademico.id_tiempo,
                     FactRendimientoAcademico.estado_academico, FactRendimientoAcademico.estado_arca,
                     FactRendimientoAcademico.estado_tutoria).filter(FactRendimientoAcademico.requiere_revision == True)  # noqa: E712
        if doc_ids is not None:
            q = q.filter(FactRendimientoAcademico.id_documento.in_(list(doc_ids)))
        ids = [f"HECHO-ACA-{h[0]}" for h in q.all()
               if f"academico|doc{h[1]}|falta:{_faltan_aca(h)}|{h[6]}|{h[8]}|{h[7]}|estado:{motivo_estado(h[6], h[8], h[7])}" == v]
    else:
        q = db.query(FactSituacionFinanciera.id_hecho_fin, FactSituacionFinanciera.id_documento, FactSituacionFinanciera.id_estudiante,
                     FactSituacionFinanciera.id_tiempo, FactSituacionFinanciera.monto_deuda).filter(FactSituacionFinanciera.requiere_revision == True)  # noqa: E712
        if doc_ids is not None:
            q = q.filter(FactSituacionFinanciera.id_documento.in_(list(doc_ids)))
        for h in q.all():
            faltan = ",".join(f for f, falta in (("estudiante", not h[2]), ("fecha", not h[3]), ("monto", h[4] is None)) if falta) or "ninguno"
            if f"financiero|doc{h[1]}|falta:{faltan}" == v:
                ids.append(f"HECHO-FIN-{h[0]}")
    return ids


def mapear_estado_grupo(db: Session, clave: str, doc_ids: Optional[List[int]], canonico: Optional[str] = None) -> Dict[str, Any]:
    """Acción de grupo 'mapear a estado canónico' (grupos de hechos con estado fuera de catálogo o combinación no admitida).
    - COMBINACION_INVALIDA: se agrega la combinación (academico, tutoria, arca) a cat_combinacion_estado.
    - ESTADO_FUERA_DE_CATALOGO: con `canonico` (nombre del estado del catálogo) se reescribe el estado del grupo; sin él, el valor
      se agrega al catálogo cat_estado_* correspondiente.
    Después se invalida la caché del catálogo y se aprueban los hechos del grupo (requiere_revision = False)."""
    from core.database import CatalogSessionLocal
    from models.catalogos import CatCombinacionEstado, CatEstadoAcademico, CatEstadoArca, CatEstadoReprobado
    from services.catalogo_estados import invalidar_cache
    partes = clave.split("::", 1)[1].split("|")
    aca, tut, arca, motivo = partes[3], partes[4], partes[5], partes[6].split(":", 1)[1]
    ids = [int(i.replace("HECHO-ACA-", "")) for i in _ids_hechos(db, clave, doc_ids)]
    if motivo == "OK" or not ids:
        return {"mapeados": 0, "motivo": motivo}
    cdb = CatalogSessionLocal()
    try:
        def _id(modelo, col_id, col_nom, valor, crear):
            fila = cdb.query(modelo).filter(getattr(modelo, col_nom) == valor).first()
            if fila is None and crear:
                fila = modelo(**{col_nom: valor})
                cdb.add(fila)
                cdb.flush()
            return getattr(fila, col_id) if fila is not None else None
        if motivo == "COMBINACION_INVALIDA":
            ia = _id(CatEstadoAcademico, "id_estado_academico", "nombre_estado", aca, False)
            it = _id(CatEstadoReprobado, "id_estado_reprobado", "nombre_detalle", tut, False)
            ir = _id(CatEstadoArca, "id_estado_arca", "nombre_arca", arca, False)
            existe = cdb.query(CatCombinacionEstado).filter_by(id_estado_academico=ia, id_estado_reprobado=it, id_estado_arca=ir).first()
            if existe is None:
                cdb.add(CatCombinacionEstado(id_estado_academico=ia, id_estado_reprobado=it, id_estado_arca=ir, activo=True))
            elif not existe.activo:
                existe.activo = True
            accion = f"combinación ({aca}, {tut}, {arca}) agregada a cat_combinacion_estado"
        else:
            campos = (("estado_academico", aca, CatEstadoAcademico, "id_estado_academico", "nombre_estado"),
                      ("estado_tutoria", tut, CatEstadoReprobado, "id_estado_reprobado", "nombre_detalle"),
                      ("estado_arca", arca, CatEstadoArca, "id_estado_arca", "nombre_arca"))
            accion = []
            for campo, valor, modelo, cid, cnom in campos:
                if valor and cdb.query(modelo).filter(getattr(modelo, cnom) == valor).first() is None:
                    if canonico:
                        db.query(FactRendimientoAcademico).filter(FactRendimientoAcademico.id_hecho_aca.in_(ids)).update(
                            {campo: canonico}, synchronize_session=False)
                        accion.append(f"{campo}: '{valor}' -> '{canonico}'")
                    else:
                        cdb.add(modelo(**{cnom: valor}))
                        accion.append(f"'{valor}' agregado a catálogo de {campo}")
            accion = "; ".join(accion)
        cdb.commit()
    finally:
        cdb.close()
    invalidar_cache()
    db.query(FactRendimientoAcademico).filter(FactRendimientoAcademico.id_hecho_aca.in_(ids)).update(
        {"requiere_revision": False}, synchronize_session=False)
    db.commit()
    return {"mapeados": len(ids), "motivo": motivo, "accion": accion}
