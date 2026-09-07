"""
pipeline/semantic/formatter.py — GIRA-40 Conversión a Texto Plano Estructurado para BETO

Convierte el contenido tabulado de output/sprint2_documentos.jsonl en oraciones semánticas
estructuradas con contexto sintáctico para que el modelo BETO mantenga atención contextual
(attention masks).

Incluye:
1. CatalogoGazetteer: Inyección de pistas léxicas y resolución de códigos POS a nombres oficiales.
2. Identificación de subtipos documentales (actas de notas, evaluación docente, cobranzas, etc.).
3. Generación de oraciones semánticas con límites estrictos de tokens (< 512 tokens BETO).
4. Trazabilidad exacta de spans con character offsets [start, end].
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple


class CatalogoGazetteer:
    """Carga y mantiene en memoria los catálogos canónicos para resolver códigos y nombres."""

    def __init__(self, ruta_seed_sql: str = "db/seeds/seed_catalogos.sql"):
        self.programas: Dict[str, Dict[str, Any]] = {}
        self.docentes: set = set()
        self._cargar_desde_seed(ruta_seed_sql)

    def _cargar_desde_seed(self, ruta_sql: str) -> None:
        if not os.path.exists(ruta_sql):
            return

        with open(ruta_sql, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                # 1. Programas: INSERT INTO public.cat_programa ... VALUES ('POS-XXXX', 'NOMBRE', ...)
                if "INSERT INTO public.cat_programa" in line:
                    m = re.search(
                        r"VALUES\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*(\d+)",
                        line,
                        re.IGNORECASE,
                    )
                    if m:
                        pos_code = m.group(1).strip().upper()
                        nombre = m.group(2).strip()
                        version = int(m.group(3))
                        self.programas[pos_code] = {
                            "pos_code": pos_code,
                            "nombre_programa": nombre,
                            "version": version,
                        }

                # 2. Docentes: INSERT INTO public.cat_docente ... VALUES ('NOMBRE', ...)
                elif "INSERT INTO public.cat_docente" in line:
                    m = re.search(
                        r"VALUES\s*\(\s*'([^']+)'",
                        line,
                        re.IGNORECASE,
                    )
                    if m:
                        doc_nom = m.group(1).strip()
                        self.docentes.add(doc_nom)

    def normalizar_pos(self, val: Any) -> Optional[str]:
        """Convierte valores como '5308', 'POS 5308', 'POS-5308', 5308.0 a 'POS-5308'."""
        if val is None:
            return None
        txt = str(val).strip()
        if not txt or txt.lower() in ("nan", "null", "none"):
            return None

        # Si termina en .0 (flotante convertido a str)
        if txt.endswith(".0"):
            txt = txt[:-2]

        m = re.search(r"(\d{4,5})", txt)
        if m:
            return f"POS-{m.group(1)}"

        m_pos = re.search(r"(POS[-\s]?[A-Za-z0-9\-]+)", txt, re.IGNORECASE)
        if m_pos:
            cod = m_pos.group(1).upper().replace(" ", "-")
            if not cod.startswith("POS-"):
                cod = "POS-" + cod[3:].lstrip("-")
            return cod

        return None

    def resolver_programa(self, pos_code: Optional[str]) -> Tuple[str, str]:
        """Retorna (codigo_pos_limpio, nombre_oficial_o_fallback)."""
        if not pos_code:
            return ("", "")
        norm = self.normalizar_pos(pos_code) or pos_code.upper()
        if norm in self.programas:
            return (norm, self.programas[norm]["nombre_programa"])
        return (norm, norm)


_GAZETTEER_GLOBAL: Optional[CatalogoGazetteer] = None


def obtener_gazetteer() -> CatalogoGazetteer:
    """Singleton para reutilizar el catálogo en memoria."""
    global _GAZETTEER_GLOBAL
    if _GAZETTEER_GLOBAL is None:
        _GAZETTEER_GLOBAL = CatalogoGazetteer()
    return _GAZETTEER_GLOBAL


def limpiar_texto_celda(val: Any) -> str:
    """Elimina caracteres de control y normaliza espacios en blanco."""
    if val is None:
        return ""
    txt = str(val)
    # Eliminar caracteres de control nulos o no imprimibles
    txt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def registrar_span(oracion: str, tipo: str, valor: str, entidades: List[Dict[str, Any]]) -> None:
    """Busca el valor dentro de la oración y registra su offset exacto [start, end]."""
    if not valor or not valor.strip():
        return
    val = valor.strip()
    # Buscar ocurrencia
    idx = oracion.find(val)
    if idx != -1:
        # Evitar solapamientos idénticos si ya fue registrado
        for e in entidades:
            if e["start"] == idx and e["end"] == idx + len(val):
                return
        entidades.append({
            "tipo": tipo,
            "valor": val,
            "start": idx,
            "end": idx + len(val)
        })


def detectar_subtipo_bloque(header_cols: List[str], categoria: str) -> str:
    """Determina la semántica interna de la hoja a partir de las columnas del encabezado."""
    hdr_norm = " ".join([c.lower() for c in header_cols])

    # 1. Evaluación Docente
    if any(k in hdr_norm for k in ("explica", "docente mostró", "estilo de enseñanza", "evaluación docente", "1. ¿la/el", "recomiende el presente")):
        return "EVALUACION_DOCENTE"

    # 2. Actas de Notas
    if any(k in hdr_norm for k in ("actas", "acta de notas")) or (("módulo 1" in hdr_norm or "modulo 1" in hdr_norm) and ("aprobado" in hdr_norm or "paterno" in hdr_norm or "cédula" in hdr_norm)):
        return "ACTAS_NOTAS"

    # 3. Inscripciones (Comercial)
    if categoria == "comercial" or any(k in hdr_norm for k in ("marca temporal", "numeroproyecto", "inscrito", "tbl_inscritos")):
        return "INSCRIPCIONES"

    # 4. Cobranzas / Facturación
    if any(k in hdr_norm for k in ("fecha de facturación", "n° de factura", "razón social", "cuota postgrado", "monto cobrado", "cobranzas", "factura")):
        return "COBRANZAS"

    # 5. Docente / Módulo
    if any(k in hdr_norm for k in ("tipo de docente", "fecha inicio", "pago docente", "pos - modulo")):
        return "DOCENTE_MODULO"

    if categoria == "financiero":
        return "FINANCIERO_GENERICO"
    if categoria == "academico":
        return "ACADEMICO_GENERICO"
    return "GENERICO"


def extraer_pos_de_fila(row_dict: Dict[str, str], gazetteer: CatalogoGazetteer) -> Tuple[str, str]:
    """Localiza el código POS en la fila y lo resuelve con el catálogo."""
    # 1. Buscar valor con patrón explícito POS-XXXX
    for v in row_dict.values():
        if "@" in v or ":" in v:
            continue
        m = re.search(r"POS[-\s]?(\d{4,5})", v, re.IGNORECASE)
        if m:
            cod = f"POS-{m.group(1)}"
            return gazetteer.resolver_programa(cod)

    # 2. Buscar por columna con nombre 'pos' o 'proyecto'
    for k, v in row_dict.items():
        if any(x in k.lower() for x in ("pos", "proyecto")) and "@" not in v and ":" not in v:
            digits = re.findall(r"\b(\d{4,5})\b", v)
            for d in digits:
                # Excluir años típicos (2020-2035)
                if not (2020 <= int(d) <= 2035):
                    cod = f"POS-{d}"
                    return gazetteer.resolver_programa(cod)

    return ("", "")


def extraer_ci_de_fila(row_dict: Dict[str, str]) -> str:
    """Extrae el CI de la fila evitando confusiones con emails o fechas."""
    for k, v in row_dict.items():
        kl = k.lower()
        if any(c in kl for c in ("ci", "cédula", "cedula", "identidad", "nit")):
            clean_ci = v.split(".")[0] if v.replace(".", "", 1).isdigit() else v
            if clean_ci and len(clean_ci) >= 5 and "@" not in clean_ci and ":" not in clean_ci:
                return clean_ci
    return ""


def formatear_fila_actas_notas(
    row_dict: Dict[str, str],
    gazetteer: CatalogoGazetteer,
    metadatos: Dict[str, Any]
) -> Tuple[str, List[Dict[str, Any]]]:
    """Genera oración contextual para actas de notas académicas."""
    cod_pos, nom_prog = extraer_pos_de_fila(row_dict, gazetteer)
    ci = extraer_ci_de_fila(row_dict)

    paterno = ""
    materno = ""
    nombres = ""
    estado = ""
    notas: List[Tuple[str, str]] = []

    for k, v in row_dict.items():
        kl = k.lower()
        if "paterno" in kl and "@" not in v:
            paterno = v
        elif "materno" in kl and "@" not in v:
            materno = v
        elif "nombre" in kl and "programa" not in kl and "@" not in v:
            nombres = v
        elif "estado" in kl and v:
            if not estado:
                estado = v
        elif any(m in kl for m in ("módulo", "modulo", "nota")) and v:
            val_limpio = v.split(".")[0] if v.replace(".", "", 1).isdigit() else v
            if val_limpio.isdigit() or val_limpio in ("Aprobado", "Reprobado", "Abandono"):
                notas.append((k, val_limpio))

    partes_nombre = [p for p in (nombres, paterno, materno) if p]
    nombre_completo = " ".join(partes_nombre).strip()
    if not nombre_completo:
        nombre_completo = "Estudiante no especificado"

    partes_oracion = []
    if nom_prog and cod_pos and nom_prog != cod_pos:
        partes_oracion.append(f"En el programa {nom_prog} (código {cod_pos})")
    elif cod_pos:
        partes_oracion.append(f"En el programa con código {cod_pos}")
    else:
        partes_oracion.append("En el programa académico")

    partes_oracion.append(f", el estudiante {nombre_completo}")

    if ci:
        partes_oracion.append(f" (CI {ci})")

    if notas:
        notas_str = ", ".join([f"{n[0]}: {n[1]}" for n in notas[:5]])
        partes_oracion.append(f" registró las calificaciones {notas_str}")

    if estado:
        partes_oracion.append(f", con estado académico {estado}")

    partes_oracion.append(".")
    oracion = "".join(partes_oracion)

    entidades: List[Dict[str, Any]] = []
    if nom_prog and nom_prog != cod_pos:
        registrar_span(oracion, "PROGRAMA", nom_prog, entidades)
    if cod_pos:
        registrar_span(oracion, "POS", cod_pos, entidades)
    if nombre_completo and nombre_completo != "Estudiante no especificado":
        registrar_span(oracion, "ESTUDIANTE", nombre_completo, entidades)
    if ci:
        registrar_span(oracion, "CI", ci, entidades)
    if estado:
        registrar_span(oracion, "ESTADO", estado, entidades)

    for _, n_val in notas[:5]:
        registrar_span(oracion, "NOTA", n_val, entidades)

    return oracion, entidades


def formatear_fila_evaluacion_docente(
    row_dict: Dict[str, str],
    gazetteer: CatalogoGazetteer,
    metadatos: Dict[str, Any]
) -> Tuple[str, List[Dict[str, Any]]]:
    """Genera oración para respuestas de evaluación docente."""
    cod_pos, nom_prog = extraer_pos_de_fila(row_dict, gazetteer)

    estudiante = ""
    modulo = ""
    fecha = ""
    calificaciones = []

    for k, v in row_dict.items():
        kl = k.lower()
        if ("nombre completo" in kl or "estudiante" in kl) and "@" not in v and not estudiante:
            estudiante = v
        elif ("módulo" in kl or "modulo" in kl) and v.isdigit():
            modulo = v
        elif "fecha" in kl and ":" in v:
            fecha = v
        elif ("1." in kl or "2." in kl or "docente" in kl) and v:
            calificaciones.append(v)

    if not estudiante:
        estudiante = "Participante"

    partes = ["En la evaluación docente"]
    if nom_prog and cod_pos and nom_prog != cod_pos:
        partes.append(f" del programa {nom_prog} (código {cod_pos})")
    elif cod_pos:
        partes.append(f" del código {cod_pos}")

    if modulo:
        partes.append(f", módulo {modulo}")

    partes.append(f", el estudiante {estudiante}")

    if fecha:
        partes.append(f" emitió su evaluación en fecha {fecha}")

    if calificaciones:
        resumen_calif = "; ".join(calificaciones[:3])
        partes.append(f" con respuestas: {resumen_calif}")

    partes.append(".")
    oracion = "".join(partes)

    entidades: List[Dict[str, Any]] = []
    if nom_prog and nom_prog != cod_pos:
        registrar_span(oracion, "PROGRAMA", nom_prog, entidades)
    if cod_pos:
        registrar_span(oracion, "POS", cod_pos, entidades)
    if estudiante and estudiante != "Participante":
        registrar_span(oracion, "ESTUDIANTE", estudiante, entidades)
    if modulo:
        registrar_span(oracion, "MODULO", modulo, entidades)
    if fecha:
        registrar_span(oracion, "FECHA", fecha, entidades)

    return oracion, entidades


def formatear_fila_cobranzas(
    row_dict: Dict[str, str],
    gazetteer: CatalogoGazetteer,
    metadatos: Dict[str, Any]
) -> Tuple[str, List[Dict[str, Any]]]:
    """Genera oración para transacciones financieras, cobranzas y facturación."""
    cod_pos, nom_prog = extraer_pos_de_fila(row_dict, gazetteer)
    ci = extraer_ci_de_fila(row_dict)

    estudiante = ""
    fecha = ""
    factura = ""
    monto = ""
    concepto = ""

    for k, v in row_dict.items():
        kl = k.lower()
        if any(x in kl for x in ("razón social", "cliente")):
            if not estudiante and "@" not in v: estudiante = v
        elif "nombre" in kl and "programa" not in kl:
            if not estudiante and "@" not in v: estudiante = v
        elif "fecha" in kl and not fecha:
            fecha = v
        elif "factura" in kl and v.replace(".", "").isdigit():
            factura = v
        elif any(x in kl for x in ("monto", "total", "saldo", "pago")) and not monto:
            # Debe ser numérico
            clean_num = v.replace(".", "").replace(",", "").strip()
            if clean_num.isdigit():
                monto = v
        elif "concepto" in kl and not concepto:
            concepto = v

    partes = ["Se registró cobranza"]
    if monto:
        partes.append(f" por un monto de {monto} Bs")

    if fecha:
        partes.append(f" en fecha {fecha}")

    if estudiante:
        partes.append(f" para el cliente {estudiante}")

    if ci:
        partes.append(f" (CI/NIT {ci})")

    if nom_prog and cod_pos and nom_prog != cod_pos:
        partes.append(f" correspondiente al programa {nom_prog} (código {cod_pos})")
    elif cod_pos:
        partes.append(f" en el programa {cod_pos}")

    if factura:
        partes.append(f" bajo factura N° {factura}")

    if concepto:
        partes.append(f" por concepto de {concepto}")

    partes.append(".")
    oracion = "".join(partes)

    entidades: List[Dict[str, Any]] = []
    if monto:
        registrar_span(oracion, "MONTO", monto, entidades)
    if fecha:
        registrar_span(oracion, "FECHA", fecha, entidades)
    if estudiante:
        registrar_span(oracion, "CLIENTE", estudiante, entidades)
    if ci:
        registrar_span(oracion, "CI", ci, entidades)
    if nom_prog and nom_prog != cod_pos:
        registrar_span(oracion, "PROGRAMA", nom_prog, entidades)
    if cod_pos:
        registrar_span(oracion, "POS", cod_pos, entidades)
    if factura:
        registrar_span(oracion, "FACTURA", factura, entidades)

    return oracion, entidades


def formatear_fila_inscripciones(
    row_dict: Dict[str, str],
    gazetteer: CatalogoGazetteer,
    metadatos: Dict[str, Any]
) -> Tuple[str, List[Dict[str, Any]]]:
    """Genera oración para registros comerciales de inscripción."""
    cod_pos, nom_prog = extraer_pos_de_fila(row_dict, gazetteer)
    ci = extraer_ci_de_fila(row_dict)

    nombres = ""
    paterno = ""
    materno = ""
    fecha = ""
    asesor = ""

    for k, v in row_dict.items():
        kl = k.lower()
        if "paterno" in kl and "@" not in v:
            paterno = v
        elif "materno" in kl and "@" not in v:
            materno = v
        elif "nombre" in kl and "programa" not in kl and "@" not in v:
            nombres = v
        elif any(x in kl for x in ("marca temporal", "fecha")):
            if not fecha: fecha = v
        elif "asesor" in kl:
            asesor = v

    partes_nom = [p for p in (nombres, paterno, materno) if p]
    postulante = " ".join(partes_nom).strip() if partes_nom else "Postulante"

    partes = []
    if fecha:
        partes.append(f"En fecha {fecha}, se registró la inscripción del postulante {postulante}")
    else:
        partes.append(f"Se registró la inscripción del postulante {postulante}")

    if ci:
        partes.append(f" (CI {ci})")

    if nom_prog and cod_pos and nom_prog != cod_pos:
        partes.append(f" en el programa {nom_prog} (código {cod_pos})")
    elif cod_pos:
        partes.append(f" en el programa con código {cod_pos}")

    if asesor:
        partes.append(f" asesorado por {asesor}")

    partes.append(".")
    oracion = "".join(partes)

    entidades: List[Dict[str, Any]] = []
    if fecha:
        registrar_span(oracion, "FECHA", fecha, entidades)
    if postulante and postulante != "Postulante":
        registrar_span(oracion, "ESTUDIANTE", postulante, entidades)
    if ci:
        registrar_span(oracion, "CI", ci, entidades)
    if nom_prog and nom_prog != cod_pos:
        registrar_span(oracion, "PROGRAMA", nom_prog, entidades)
    if cod_pos:
        registrar_span(oracion, "POS", cod_pos, entidades)
    if asesor:
        registrar_span(oracion, "ASESOR", asesor, entidades)

    return oracion, entidades


def formatear_fila_generica(
    row_dict: Dict[str, str],
    gazetteer: CatalogoGazetteer,
    metadatos: Dict[str, Any]
) -> Tuple[str, List[Dict[str, Any]]]:
    """Fallback estructurado para cualquier fila que no encaje en un subtipo exacto."""
    hoja = metadatos.get("hoja", "Datos")
    elementos = []
    entidades: List[Dict[str, Any]] = []

    pos_encontrado = None
    for k, v in row_dict.items():
        if not v:
            continue
        # Check POS
        if any(x in k.lower() for x in ("pos", "proyecto")):
            pos_norm = gazetteer.normalizar_pos(v)
            if pos_norm:
                pos_encontrado = pos_norm

        elementos.append(f"{k}: {v}")

    resumen = ", ".join(elementos[:8])
    oracion = f"Registro en hoja {hoja}: {resumen}."

    if pos_encontrado:
        registrar_span(oracion, "POS", pos_encontrado, entidades)

    return oracion, entidades


def formatear_documento(
    doc_json: Dict[str, Any],
    max_filas: Optional[int] = None,
    gazetteer: Optional[CatalogoGazetteer] = None
) -> List[Dict[str, Any]]:
    """
    Función principal de GIRA-40.
    Toma un documento de sprint2_documentos.jsonl y genera una lista de oraciones semánticas.
    """
    if gazetteer is None:
        gazetteer = obtener_gazetteer()

    texto_plano = doc_json.get("texto_plano", "")
    categoria = doc_json.get("categoria", "generico")
    archivo = doc_json.get("archivo", "")
    hoja = doc_json.get("hoja", "")
    bloque_id = doc_json.get("bloque_id", 0)

    if not texto_plano.strip():
        return []

    lineas = [l.strip() for l in texto_plano.split("\n") if l.strip()]
    if len(lineas) == 0:
        return []

    # Fila 0 es header
    header_cols = [limpiar_texto_celda(c) for c in lineas[0].split(" | ")]
    data_lines = lineas[1:]

    # Si solo hay 1 fila (ej. título o bloque ruido), generar oración sintética corta
    if len(data_lines) == 0:
        oracion_corta = f"Sección {lineas[0]} en hoja {hoja} del archivo {archivo}."
        return [{
            "oracion": oracion_corta,
            "categoria": categoria,
            "subtipo": "TITULO_SECCION",
            "metadatos_origen": {"archivo": archivo, "hoja": hoja, "bloque_id": bloque_id, "fila_idx": 0},
            "entidades_pistas": [],
            "n_tokens_aprox": len(oracion_corta.split())
        }]

    subtipo = detectar_subtipo_bloque(header_cols, categoria)
    oraciones_resultado: List[Dict[str, Any]] = []

    limite = len(data_lines) if max_filas is None else min(len(data_lines), max_filas)

    for idx in range(limite):
        row_raw = data_lines[idx]
        vals = [limpiar_texto_celda(c) for c in row_raw.split(" | ")]

        # Mapear columnas a valores
        row_dict: Dict[str, str] = {}
        for c_idx, col_name in enumerate(header_cols):
            if c_idx < len(vals):
                row_dict[col_name] = vals[c_idx]
            else:
                row_dict[col_name] = ""

        metadatos_fila = {
            "archivo": archivo,
            "hoja": hoja,
            "bloque_id": bloque_id,
            "fila_idx": idx + 1
        }

        # Seleccionar serializador
        if subtipo == "ACTAS_NOTAS":
            oracion, entidades = formatear_fila_actas_notas(row_dict, gazetteer, metadatos_fila)
        elif subtipo == "EVALUACION_DOCENTE":
            oracion, entidades = formatear_fila_evaluacion_docente(row_dict, gazetteer, metadatos_fila)
        elif subtipo == "COBRANZAS":
            oracion, entidades = formatear_fila_cobranzas(row_dict, gazetteer, metadatos_fila)
        elif subtipo == "INSCRIPCIONES":
            oracion, entidades = formatear_fila_inscripciones(row_dict, gazetteer, metadatos_fila)
        else:
            oracion, entidades = formatear_fila_generica(row_dict, gazetteer, metadatos_fila)

        # Garantizar límite seguro de longitud (< 512 tokens)
        # Si la oración excede 1500 caracteres, truncarla ordenadamente en el último punto o coma
        if len(oracion) > 1500:
            oracion = oracion[:1490].rsplit(" ", 1)[0] + "..."
            # Revalidar spans que hayan quedado fuera
            entidades = [e for e in entidades if e["end"] <= len(oracion)]

        n_tokens_aprox = int(len(oracion.split()) * 1.3) + 2

        oraciones_resultado.append({
            "oracion": oracion,
            "categoria": categoria,
            "subtipo": subtipo,
            "metadatos_origen": metadatos_fila,
            "entidades_pistas": entidades,
            "n_tokens_aprox": n_tokens_aprox
        })

    return oraciones_resultado
