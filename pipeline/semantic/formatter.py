import os
import re
from typing import Any, Dict, List, Optional, Tuple

from pipeline.config import SEED_CATALOGOS_SQL_PATH
from pipeline.normalization.catalog_repository import obtener_catalogo_repositorio, CatalogRepository


class CatalogoGazetteer:
    """
    Fachada y gazetteer para resolución léxica de catálogos canónicos.
    Delega en CatalogRepository (singleton) para garantizar una única fuente de verdad.
    """

    def __init__(self, ruta_seed_sql: Optional[Any] = None):
        self.repo: CatalogRepository = obtener_catalogo_repositorio(ruta_seed_sql or SEED_CATALOGOS_SQL_PATH)
        self.programas: Dict[str, Dict[str, Any]] = {
            pos: {
                "pos_code": pos,
                "nombre_programa": meta["nombre"],
                "version": meta.get("version", 1),
            }
            for pos, meta in self.repo.programas_meta.items()
        }
        self.docentes: set = self.repo.docentes_set

    def normalizar_pos(self, val: Any) -> Optional[str]:
        """Convierte valores como '5308', 'POS 5308', 'POS-5308', 5308.0 a 'POS-5308'."""
        return self.repo.normalizar_pos(val)

    def resolver_programa(self, pos_code: Optional[str]) -> Tuple[str, str]:
        """Retorna (codigo_pos_limpio, nombre_oficial_o_fallback)."""
        if not pos_code:
            return ("", "")
        norm = self.normalizar_pos(pos_code) or str(pos_code).upper()
        if norm in self.programas:
            return (norm, self.programas[norm]["nombre_programa"])
        return (norm, norm)

    def buscar_por_pos(self, pos_code: Optional[str]) -> Optional[Dict[str, Any]]:
        """Busca y retorna la información de un programa por su código POS."""
        if not pos_code:
            return None
        norm = self.normalizar_pos(pos_code) or str(pos_code).strip().upper()
        return self.programas.get(norm)

    def buscar_por_alias(self, texto: Optional[str]) -> Optional[Dict[str, Any]]:
        """Busca un programa en el catálogo por coincidencia de subcadena o título."""
        if not texto or len(str(texto).strip()) < 4:
            return None
        t_norm = str(texto).strip().lower()
        for prog in self.programas.values():
            nom = prog.get("nombre_programa", "").lower()
            if t_norm in nom or nom in t_norm:
                return {
                    "id": prog.get("pos_code"),
                    "pos": prog.get("pos_code"),
                    "nombre": prog.get("nombre_programa")
                }
        return None

    def es_docente_conocido(self, nombre: Optional[str]) -> bool:
        """Verifica si el nombre de docente coincide con la semilla de catálogo."""
        return self.repo.es_docente_conocido(nombre)


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


def detectar_subtipo_bloque(header_cols: List[str], categoria: str = "generico", gazetteer: Optional[CatalogoGazetteer] = None) -> str:
    """Determina la semántica interna de la hoja a partir de las etiquetas y reglas de cat_etiqueta_clasificacion."""
    if gazetteer is None:
        gazetteer = obtener_gazetteer()
    return gazetteer.repo.detectar_subtipo_con_catalogo(header_cols, categoria)


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


def formatear_fila_dinamica(
    row_dict: Dict[str, str],
    subtipo: str,
    gazetteer: CatalogoGazetteer,
    metadatos: Dict[str, Any]
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Serializa una fila a texto plano estructurado basándose en las plantillas y mapeos
    almacenados en la base de datos de catálogos (cat_guia_texto_plano y cat_mapeo_columna).
    Elimina la necesidad de codificar funciones manuales para cada subtipo de reporte.
    """
    guia = gazetteer.repo.obtener_guia_texto_plano(subtipo)
    plantilla = guia.get("plantilla_texto", "Registro en hoja {HOJA}: {DETALLES}.")

    # 1. Extraer POS y Programa
    cod_pos, nom_prog = extraer_pos_de_fila(row_dict, gazetteer)

    # 2. Clasificar campos de la fila usando cat_mapeo_columna
    datos_extraidos: Dict[str, Any] = {
        "POS": cod_pos,
        "PROGRAMA": nom_prog if nom_prog and nom_prog != cod_pos else (cod_pos or "programa académico"),
        "HOJA": metadatos.get("hoja", "Datos"),
        "NOTAS": [],
        "RESPUESTAS": [],
        "DETALLES": []
    }

    nombres_partes = {"paterno": "", "materno": "", "nombres": ""}

    for col_orig, val_orig in row_dict.items():
        if not val_orig or not str(val_orig).strip():
            continue
        val_clean = str(val_orig).strip()
        col_clean = str(col_orig).strip()

        mapeo = gazetteer.repo.identificar_columna(col_clean)
        campo = mapeo["campo_canonico"] if mapeo else None

        if campo == "PATERNO":
            nombres_partes["paterno"] = val_clean
        elif campo == "MATERNO":
            nombres_partes["materno"] = val_clean
        elif campo == "ESTUDIANTE":
            if not datos_extraidos.get("ESTUDIANTE"):
                datos_extraidos["ESTUDIANTE"] = val_clean
            else:
                nombres_partes["nombres"] = val_clean
        elif campo == "CI":
            if not datos_extraidos.get("CI"):
                if "@" not in val_clean and ":" not in val_clean:
                    datos_extraidos["CI"] = val_clean.split(".")[0] if val_clean.replace(".", "", 1).isdigit() else val_clean
        elif campo == "MONTO":
            if not datos_extraidos.get("MONTO"):
                clean_num = val_clean.replace(".", "").replace(",", "").strip()
                if clean_num.isdigit():
                    datos_extraidos["MONTO"] = val_clean
        elif campo == "FACTURA":
            if not datos_extraidos.get("FACTURA"):
                datos_extraidos["FACTURA"] = val_clean
        elif campo == "FECHA":
            if not datos_extraidos.get("FECHA"):
                datos_extraidos["FECHA"] = val_clean
        elif campo == "DOCENTE":
            if not datos_extraidos.get("DOCENTE"):
                datos_extraidos["DOCENTE"] = val_clean
        elif campo == "MODULO":
            if not datos_extraidos.get("MODULO"):
                datos_extraidos["MODULO"] = val_clean
        elif campo == "ESTADO":
            if not datos_extraidos.get("ESTADO"):
                datos_extraidos["ESTADO"] = val_clean
        elif campo == "ASISTENCIA_PCT":
            if not datos_extraidos.get("ASISTENCIA_PCT"):
                datos_extraidos["ASISTENCIA_PCT"] = val_clean
        elif campo == "INCUMPLIMIENTO_ACTIVIDADES_PCT":
            if not datos_extraidos.get("INCUMPLIMIENTO_ACTIVIDADES_PCT"):
                datos_extraidos["INCUMPLIMIENTO_ACTIVIDADES_PCT"] = val_clean
        elif campo == "MONTO_DEUDA":
            if not datos_extraidos.get("MONTO_DEUDA"):
                datos_extraidos["MONTO_DEUDA"] = val_clean
        elif campo == "CUOTAS_IMPAGAS":
            if not datos_extraidos.get("CUOTAS_IMPAGAS"):
                datos_extraidos["CUOTAS_IMPAGAS"] = val_clean
        elif campo == "ESTADO_CARTERA":
            if not datos_extraidos.get("ESTADO_CARTERA"):
                datos_extraidos["ESTADO_CARTERA"] = val_clean
        elif campo == "NOTA":
            val_unif = val_clean
            try:
                num_n = float(val_clean.replace(",", "."))
                if 0.0 < num_n <= 10.0:
                    val_unif = str(round(num_n * 10.0, 2))
            except ValueError:
                pass
            datos_extraidos["NOTAS"].append((col_clean, val_unif))
            if not datos_extraidos.get("NOTA_FINAL"):
                datos_extraidos["NOTA_FINAL"] = val_unif
        elif campo == "ASESOR":
            datos_extraidos["ASESOR"] = val_clean
        else:
            if any(k in col_clean.lower() for k in ("1.", "2.", "docente", "explica", "recomiende")):
                datos_extraidos["RESPUESTAS"].append(val_clean)
            datos_extraidos["DETALLES"].append(f"{col_clean}: {val_clean}")

    # Consolidar estudiante
    if not datos_extraidos.get("ESTUDIANTE"):
        nom_comp = " ".join([p for p in (nombres_partes["nombres"], nombres_partes["paterno"], nombres_partes["materno"]) if p]).strip()
        datos_extraidos["ESTUDIANTE"] = nom_comp or ("Cliente" if subtipo == "COBRANZAS" else "Estudiante")

    # Formatear listas
    if datos_extraidos["NOTAS"]:
        datos_extraidos["NOTAS"] = ", ".join([f"{n[0]}: {n[1]}" for n in datos_extraidos["NOTAS"][:5]])
    else:
        datos_extraidos["NOTAS"] = "pendientes"

    if datos_extraidos["RESPUESTAS"]:
        datos_extraidos["RESPUESTAS"] = "; ".join(datos_extraidos["RESPUESTAS"][:3])
    else:
        datos_extraidos["RESPUESTAS"] = "sin observaciones"

    if datos_extraidos["DETALLES"]:
        datos_extraidos["DETALLES"] = ", ".join(datos_extraidos["DETALLES"][:8])
    else:
        datos_extraidos["DETALLES"] = "sin datos adicionales"

    for k in ("POS", "PROGRAMA", "CI", "MONTO", "FACTURA", "FECHA", "DOCENTE", "MODULO", "ESTADO", "ASESOR", "CONCEPTO"):
        if k not in datos_extraidos or not datos_extraidos[k]:
            datos_extraidos[k] = ""

    # Reemplazar placeholders de la plantilla
    oracion = plantilla
    for k, v in datos_extraidos.items():
        if isinstance(v, str):
            oracion = oracion.replace(f"{{{k}}}", v)

    # Limpiar posibles artefactos vacíos
    oracion = re.sub(r"\s*\(\s*(?:código|c\.i\.|ci/nit|ci)?\s*\)", "", oracion, flags=re.IGNORECASE)
    oracion = re.sub(r"\s+bajo factura N°\s*(?:por|$)", " por", oracion)
    oracion = re.sub(r"\s+por concepto de\s*\.", ".", oracion)
    oracion = re.sub(r"\s+asesorado por\s*\.", ".", oracion)
    oracion = re.sub(r"\s*,\s*\.", ".", oracion)
    oracion = re.sub(r"\s+", " ", oracion).strip()
    if not oracion.endswith("."):
        oracion += "."

    # 3. Registrar spans de entidades extraídas
    entidades: List[Dict[str, Any]] = []
    if datos_extraidos.get("PROGRAMA") and datos_extraidos["PROGRAMA"] != cod_pos:
        registrar_span(oracion, "PROGRAMA", datos_extraidos["PROGRAMA"], entidades)
    if cod_pos:
        registrar_span(oracion, "POS", cod_pos, entidades)
    if datos_extraidos.get("ESTUDIANTE") and datos_extraidos["ESTUDIANTE"] not in ("Estudiante", "Cliente", "Postulante"):
        tipo_ent = "CLIENTE" if subtipo == "COBRANZAS" else "ESTUDIANTE"
        registrar_span(oracion, tipo_ent, datos_extraidos["ESTUDIANTE"], entidades)
    if datos_extraidos.get("DOCENTE"):
        registrar_span(oracion, "DOCENTE", datos_extraidos["DOCENTE"], entidades)
    if datos_extraidos.get("CI"):
        registrar_span(oracion, "CI", datos_extraidos["CI"], entidades)
    if datos_extraidos.get("MONTO"):
        registrar_span(oracion, "MONTO", datos_extraidos["MONTO"], entidades)
    if datos_extraidos.get("FACTURA"):
        registrar_span(oracion, "FACTURA", datos_extraidos["FACTURA"], entidades)
    if datos_extraidos.get("FECHA"):
        registrar_span(oracion, "FECHA", datos_extraidos["FECHA"], entidades)
    if datos_extraidos.get("MODULO"):
        registrar_span(oracion, "MODULO", datos_extraidos["MODULO"], entidades)
    if datos_extraidos.get("ESTADO"):
        registrar_span(oracion, "ESTADO", datos_extraidos["ESTADO"], entidades)

    return oracion, entidades


# ── Funciones de compatibilidad directa delegando en formatear_fila_dinamica ──

def formatear_fila_actas_notas(row_dict: Dict[str, str], gazetteer: CatalogoGazetteer, metadatos: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    return formatear_fila_dinamica(row_dict, "ACTAS_NOTAS", gazetteer, metadatos)

def formatear_fila_evaluacion_docente(row_dict: Dict[str, str], gazetteer: CatalogoGazetteer, metadatos: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    return formatear_fila_dinamica(row_dict, "EVALUACION_DOCENTE", gazetteer, metadatos)

def formatear_fila_cobranzas(row_dict: Dict[str, str], gazetteer: CatalogoGazetteer, metadatos: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    return formatear_fila_dinamica(row_dict, "COBRANZAS", gazetteer, metadatos)

def formatear_fila_inscripciones(row_dict: Dict[str, str], gazetteer: CatalogoGazetteer, metadatos: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    return formatear_fila_dinamica(row_dict, "INSCRIPCIONES", gazetteer, metadatos)

def formatear_fila_generica(row_dict: Dict[str, str], gazetteer: CatalogoGazetteer, metadatos: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    return formatear_fila_dinamica(row_dict, "GENERICO", gazetteer, metadatos)


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
            "fila_idx": idx + 1,
            "row_dict": dict(row_dict)
        }

        # Serialización dinámica guiada por catálogo
        oracion, entidades = formatear_fila_dinamica(row_dict, subtipo, gazetteer, metadatos_fila)

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
