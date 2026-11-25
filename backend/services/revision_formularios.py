"""
backend/services/revision_formularios.py
----------------------------------------
Definición centralizada de formularios dinámicos (campos_correccion), explicación
contextual (motivo_detalle) y validación estricta (HTTP 422) por categoría × motivo
para la bandeja de revisión humana (W-4 / D-W6).

Fuente de verdad: docs/mediciones/f3w_matriz_formularios.md
"""

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from fastapi import HTTPException

from services.dataops_evaluation_service import enmascarar_ci


def _campo(
    name: str,
    label: str,
    tipo: str = "text",
    required: bool = True,
    options: Optional[List[str]] = None,
) -> Dict[str, Any]:
    desc: Dict[str, Any] = {
        "name": name,
        "label": label,
        "type": tipo,
        "required": required,
    }
    if options is not None:
        desc["options"] = list(options)
    return desc


# Catálogo reutilizable de descriptores de campo
_C = {
    "nombre_completo": lambda req=True: _campo("nombre_completo", "Nombre completo", "text", req),
    "ci_opcional": lambda req=False: _campo("ci_opcional", "Cédula (opcional)", "text", req),
    "ci_corregido": lambda req=True: _campo("ci_corregido", "Cédula corregida", "text", req),
    "confirmar_identidad": lambda req=True: _campo(
        "confirmar_identidad",
        "Confirmar identidad",
        "select",
        req,
        options=["Sí, es la misma persona", "No, es otra persona"],
    ),
    "modulo_resuelto": lambda req=True: _campo("modulo_resuelto", "Módulo", "text", req),
    "nota_final": lambda req=True: _campo("nota_final", "Nota sobre 100", "number", req),
    "mes": lambda req=True: _campo("mes", "Mes", "number", req),
    "gestion": lambda req=True: _campo("gestion", "Gestión", "number", req),
    "programa": lambda req=True: _campo("programa", "Programa", "text", req),
    "numero_modulo": lambda req=True: _campo("numero_modulo", "Número de módulo", "number", req),
    "docente_resuelto": lambda req=True: _campo("docente_resuelto", "Docente", "text", req),
    "escala_respuesta": lambda req=True: _campo(
        "escala_respuesta",
        "Escala de respuesta",
        "select",
        req,
        options=["1 a 5", "1 a 10"],
    ),
    "codigo_pos": lambda req=True: _campo("codigo_pos", "Código POS", "text", req),
    "programa_resuelto": lambda req=True: _campo("programa_resuelto", "Programa", "text", req),
    "fecha_inscripcion": lambda req=True: _campo("fecha_inscripcion", "Fecha de inscripción", "date", req),
    "monto_deuda": lambda req=True: _campo("monto_deuda", "Monto de deuda", "number", req),
    "cuotas_impagas": lambda req=True: _campo("cuotas_impagas", "Cuotas impagas", "number", req),
    "categoria_financiera": lambda req=True: _campo("categoria_financiera", "Categoría financiera", "text", req),
    "institucion": lambda req=True: _campo("institucion", "Institución", "text", req),
    "clave_convenio": lambda req=True: _campo("clave_convenio", "Clave de convenio", "text", req),
    "monto_convenio": lambda req=True: _campo("monto_convenio", "Monto de convenio", "number", req),
    "justificacion": lambda req=True: _campo("justificacion", "Justificación", "text", req),
}


def _lista(*specs: Tuple[str, bool]) -> List[Dict[str, Any]]:
    return [_C[nombre](req) for nombre, req in specs]


# Matriz exacta de docs/mediciones/f3w_matriz_formularios.md (13 combinaciones)
MATRIZ_FORMULARIOS: Dict[Tuple[str, str], List[Dict[str, Any]]] = {
    ("academico", "CI_NOMBRE_DISCORDANTE"): _lista(
        ("nombre_completo", True),
        ("ci_opcional", False),
        ("confirmar_identidad", True),
        ("justificacion", True),
    ),
    ("academico", "BAJA_CONFIANZA_IA"): _lista(
        ("nombre_completo", True),
        ("modulo_resuelto", True),
        ("nota_final", True),
        ("mes", True),
        ("gestion", True),
        ("justificacion", True),
    ),
    ("academico", "HOMONIMIA"): _lista(
        ("nombre_completo", True),
        ("ci_opcional", False),
        ("programa", True),
        ("justificacion", True),
    ),
    ("academico", "CI_DUDOSA"): _lista(
        ("ci_corregido", True),
        ("nombre_completo", True),
        ("justificacion", True),
    ),
    ("evaluacion_docente", "BAJA_CONFIANZA_IA"): _lista(
        ("programa", True),
        ("numero_modulo", True),
        ("docente_resuelto", True),
        ("escala_respuesta", True),
        ("justificacion", True),
    ),
    ("evaluacion_docente", "HOMONIMIA"): _lista(
        ("nombre_completo", True),
        ("ci_opcional", False),
        ("programa", True),
        ("numero_modulo", True),
        ("justificacion", True),
    ),
    ("admision", "POS_NO_EN_DIM_MODULO"): _lista(
        ("codigo_pos", True),
        ("programa_resuelto", True),
        ("modulo_resuelto", True),
        ("justificacion", True),
    ),
    ("admision", "CI_DUDOSA"): _lista(
        ("ci_corregido", True),
        ("nombre_completo", True),
        ("justificacion", True),
    ),
    ("admision", "FECHA_INSCRIPCION_INVALIDA"): _lista(
        ("fecha_inscripcion", True),
        ("justificacion", True),
    ),
    ("financiero", "CI_DUDOSA"): _lista(
        ("ci_corregido", True),
        ("nombre_completo", True),
        ("monto_deuda", True),
        ("cuotas_impagas", True),
        ("justificacion", True),
    ),
    ("rentabilidad", "CI_NOMBRE_DISCORDANTE"): _lista(
        ("nombre_completo", True),
        ("ci_opcional", False),
        ("categoria_financiera", True),
        ("justificacion", True),
    ),
    ("rentabilidad", "HOMONIMIA"): _lista(
        ("nombre_completo", True),
        ("ci_opcional", False),
        ("justificacion", True),
    ),
    ("marketing", "*"): _lista(
        ("institucion", True),
        ("clave_convenio", True),
        ("monto_convenio", True),
        ("justificacion", True),
    ),
}

# Formularios para hechos cargados con requiere_revision=True (revision_hechos.py)
_FORMULARIOS_HECHO: Dict[str, List[Dict[str, Any]]] = {
    "academico": MATRIZ_FORMULARIOS[("academico", "BAJA_CONFIANZA_IA")],
    "financiero": _lista(
        ("nombre_completo", True),
        ("monto_deuda", True),
        ("cuotas_impagas", True),
        ("mes", True),
        ("gestion", True),
        ("justificacion", True),
    ),
    "evaluacion_docente": _lista(
        ("docente_resuelto", True),
        ("mes", True),
        ("gestion", True),
        ("justificacion", True),
    ),
}

# Marketing (TBL_INSCRITOS) con motivo de identidad: pide identidad, no campos de convenio.
_MOTIVOS_IDENTIDAD_MARKETING = {
    "CI_DUDOSA": MATRIZ_FORMULARIOS[("admision", "CI_DUDOSA")],
    "CI_NOMBRE_DISCORDANTE": MATRIZ_FORMULARIOS[("academico", "CI_NOMBRE_DISCORDANTE")],
    "HOMONIMIA": MATRIZ_FORMULARIOS[("rentabilidad", "HOMONIMIA")],
}

_SINONIMOS_MOTIVO = {
    "CI_ILEGIBLE": "CI_DUDOSA",
    "BAJA_CONFIANZA": "BAJA_CONFIANZA_IA",
    "NOTA_FUERA_ESCALA": "BAJA_CONFIANZA_IA",
    "NOTA_INVALIDA": "BAJA_CONFIANZA_IA",
}

_ALIASES_POR_CAMPO = {
    "nombre_completo": ("estudiante_resuelto", "texto_editado"),
    "ci_opcional": ("ci_corregida",),
    "ci_corregido": ("ci_corregida",),
    "justificacion": ("nota_auditor",),
}

_CAMPOS_CONTROL = {
    "accion", "aprobacion_en_bloque", "motivo_descarte",
    "id_estudiante_candidato", "id_modulo_destino", "valor_canonico", "recordar_sinonimo",
    "pregunta_destino", "valor_corregido", "ci_numero", "ci_complemento",
    "entidad_tipo", "entidad_texto", "fuente_prioritaria",
}


def normalizar_categoria(categoria: Optional[str]) -> str:
    cat = (categoria or "academico").strip().lower()
    if cat == "academica":
        return "academico"
    if cat == "financiera":
        return "financiero"
    if cat == "comercial":
        return "admision"
    return cat


def _motivo_canonico(motivo: Optional[str]) -> str:
    m = (motivo or "REVISION_GENERAL").strip().upper()
    return _SINONIMOS_MOTIVO.get(m, m)


def campos_para_caso(categoria: Optional[str], motivo: Optional[str]) -> List[Dict[str, Any]]:
    """Devuelve la lista de descriptores {name, label, type, required, options?} para (categoria, motivo)."""
    cat = normalizar_categoria(categoria)
    mot = _motivo_canonico(motivo)

    if cat == "marketing":
        if mot in _MOTIVOS_IDENTIDAD_MARKETING:
            return [dict(c) for c in _MOTIVOS_IDENTIDAD_MARKETING[mot]]
        return [dict(c) for c in MATRIZ_FORMULARIOS[("marketing", "*")]]
    if mot == "HECHO_EN_REVISION" and cat in _FORMULARIOS_HECHO:
        return [dict(c) for c in _FORMULARIOS_HECHO[cat]]
    if (cat, mot) in MATRIZ_FORMULARIOS:
        return [dict(c) for c in MATRIZ_FORMULARIOS[(cat, mot)]]

    # Fallback por categoría cuando el motivo es genérico o heredado (ej. REVISION_GENERAL)
    fallbacks = {
        "academico": MATRIZ_FORMULARIOS[("academico", "BAJA_CONFIANZA_IA")],
        "evaluacion_docente": MATRIZ_FORMULARIOS[("evaluacion_docente", "BAJA_CONFIANZA_IA")],
        "admision": MATRIZ_FORMULARIOS[("admision", "CI_DUDOSA")],
        "financiero": MATRIZ_FORMULARIOS[("financiero", "CI_DUDOSA")],
        "rentabilidad": MATRIZ_FORMULARIOS[("rentabilidad", "CI_NOMBRE_DISCORDANTE")],
        "marketing": MATRIZ_FORMULARIOS[("marketing", "*")],
    }
    return [dict(c) for c in fallbacks.get(cat, MATRIZ_FORMULARIOS[("academico", "BAJA_CONFIANZA_IA")])]


def _campos_permitidos_revision_general(categoria: str) -> set[str]:
    """Unión de campos válidos para una categoría cuando el caso no tiene un motivo específico de la matriz."""
    permitidos = set(_CAMPOS_CONTROL)
    for (cat_m, _), campos in MATRIZ_FORMULARIOS.items():
        if cat_m == categoria:
            for c in campos:
                permitidos.add(c["name"])
                permitidos.update(_ALIASES_POR_CAMPO.get(c["name"], ()))
    if categoria in _FORMULARIOS_HECHO:
        for c in _FORMULARIOS_HECHO[categoria]:
            permitidos.add(c["name"])
            permitidos.update(_ALIASES_POR_CAMPO.get(c["name"], ()))
    # Campos técnicos heredados de la categoría
    extras_cat = {
        "academico": {"nota_final", "modulo_resuelto", "fecha", "mes", "gestion"},
        "evaluacion_docente": {"docente_resuelto", "modulo_resuelto", "puntuacion", "escala_max", "comentario", "fecha"},
        "rentabilidad": {"monto_ejecutado", "monto_meta", "categoria_financiera", "modulo_resuelto", "fecha"},
        "marketing": {"institucion", "clave_convenio", "monto_convenio", "estudiante_resuelto", "modulo_resuelto", "fecha"},
        "admision": {"estudiante_resuelto", "ci_corregida", "modulo_resuelto", "fecha_inscripcion", "fecha"},
        "financiero": {"estudiante_resuelto", "ci_corregida", "monto_deuda", "monto_pagado", "cuotas_impagas", "concepto", "fecha"},
    }
    permitidos.update(extras_cat.get(categoria, set()))
    return permitidos


def validar_payload_correccion(
    categoria: Optional[str],
    motivo: Optional[str],
    payload: Dict[str, Any],
) -> None:
    """
    Valida que el payload de resolve_review_item no incluya campos que no correspondan
    al motivo/categoría del caso. Rechaza con HTTP 422 ante campos inválidos.
    """
    if not isinstance(payload, dict):
        return
    accion = str(payload.get("accion") or "APROBAR").upper()
    if "DESCARTAR" in accion:
        return

    cat = normalizar_categoria(categoria)
    mot_raw = (motivo or "").strip().upper()
    mot = _motivo_canonico(mot_raw) if mot_raw else ""

    es_especifico = (
        (cat == "marketing" and bool(mot) and mot != "REVISION_GENERAL")
        or mot == "HECHO_EN_REVISION"
        or (cat, mot) in MATRIZ_FORMULARIOS
    )

    if es_especifico:
        campos = campos_para_caso(cat, mot)
        permitidos = set(_CAMPOS_CONTROL)
        for c in campos:
            permitidos.add(c["name"])
            permitidos.update(_ALIASES_POR_CAMPO.get(c["name"], ()))
    else:
        permitidos = _campos_permitidos_revision_general(cat)

    invalidos = [
        k for k, v in payload.items()
        if k not in permitidos and v not in (None, "")
    ]
    if invalidos:
        etiqueta_mot = mot or "REVISION_GENERAL"
        raise HTTPException(
            status_code=422,
            detail=(
                f"Los siguientes campos no corresponden al motivo {etiqueta_mot} "
                f"en {cat}: {', '.join(sorted(invalidos))}."
            ),
        )


def construir_motivo_detalle(
    categoria: Optional[str],
    motivo: Optional[str],
    datos: Optional[Dict[str, Any]] = None,
) -> str:
    """Genera una explicación clara del porqué del caso con el dato concreto que lo provoca."""
    datos = datos or {}
    cat = normalizar_categoria(categoria)
    mot = _motivo_canonico(motivo)

    ci_raw = datos.get("ci") or datos.get("ci_enmascarado")
    ci_txt = enmascarar_ci(str(ci_raw)) if ci_raw and "•" not in str(ci_raw) else (str(ci_raw) if ci_raw else "sin CI")
    programa = datos.get("programa") or datos.get("codigo_pos") or datos.get("modulo")
    prog_txt = f" en {programa}" if programa else ""
    conf = datos.get("confianza")
    conf_txt = f"{float(conf):.2f}".replace(".", ",") if conf is not None else "sin dato"
    nombre_raw = datos.get("nombre")
    nombre = "••••" if nombre_raw and str(nombre_raw).strip() else "sin nombre"
    sug_raw = datos.get("sugerencia")
    sugerencia = None
    if sug_raw and str(sug_raw).strip():
        sug_str = str(sug_raw).strip()
        sugerencia = (
            sug_str
            if re.fullmatch(r"(?:Estudiante|Docente|Persona|Asesor)?\s*•+\d*", sug_str, re.I)
            else "••••"
        )
    fecha = datos.get("fecha") or "sin fecha"

    if mot == "CI_NOMBRE_DISCORDANTE":
        if cat == "rentabilidad":
            return f"Discordancia de nombre/CI ({ci_txt}) en la fuente de egresos{prog_txt}."
        sug_txt = f" ({sugerencia})" if sugerencia else ""
        return f"La CI {ci_txt} coincide con una persona del catálogo{sug_txt}, pero el nombre '{nombre}' difiere."

    if mot == "SIN_LECTURA" or (mot == "BAJA_CONFIANZA_IA" and (conf is None or float(conf) <= 0.0)):
        return f"La fila no tiene datos legibles (sin lectura de BETO){prog_txt}."

    if mot == "BAJA_CONFIANZA_IA":
        es_banda_baja = conf is not None and float(conf) < 0.60
        banda_txt = "en la banda baja (< 0,60)" if es_banda_baja else "en la banda de revisión [0,60; 0,85)"
        if cat == "evaluacion_docente":
            rango_txt = "< 0,60" if es_banda_baja else "[0,60; 0,85)"
            return f"Índice probabilístico BETO ({conf_txt}) {rango_txt} en respuestas Likert{prog_txt}."
        return f"Índice probabilístico BETO ({conf_txt}) {banda_txt}{prog_txt}."

    if mot == "HOMONIMIA":
        if cat == "evaluacion_docente":
            return f"Otra persona con el mismo nombre{prog_txt}, {ci_txt}."
        if cat == "rentabilidad":
            return f"Posible homonimia en la fuente de egresos{prog_txt}, {ci_txt}."
        return f"Dos personas con nombre similar (>90 %){prog_txt}, {ci_txt}."

    if mot == "CI_DUDOSA":
        origen = {
            "admision": " en la fuente de inscritos",
            "financiero": " en la fuente de cobranzas",
        }.get(cat, "")
        return f"CI con formato inválido o dudoso ({ci_txt}){origen}."

    if mot == "POS_NO_EN_DIM_MODULO":
        cod = datos.get("codigo_pos") or programa or "sin código"
        return f"Código POS '{cod}' no encontrado en el catálogo de módulos (dim_modulo)."

    if mot == "FECHA_INSCRIPCION_INVALIDA":
        return f"Fecha de inscripción nula o fuera de rango en admisión ({fecha})."

    if cat == "marketing":
        inst = datos.get("institucion") or programa or "convenio"
        return f"Convenio o institución ({inst}) o monto por validar en techos de marketing."

    if mot == "HECHO_EN_REVISION":
        return datos.get("por_que_detuvo") or f"Hecho en {cat} marcado para revisión."

    return datos.get("por_que_detuvo") or f"Caso de {cat} ({mot}) pendiente de verificación."
