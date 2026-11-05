"""
populate_catalogos.py — Generador del seed de giragroup_catalog_db desde uploads/data

Regla: todo valor del catálogo proviene de un archivo fuente; si la fuente no trae
el dato, se guarda NULL. No se generan cifras, metas ni sinónimos inventados.

Fuentes (solo columnas no personales):
- Base centralizada Académica ARCA (1).xlsx
    IBP        → programas (POS, nombre, versión, escuela, inversión, punto de equilibrio,
                 horas, modalidad, tipo)
    MODULOS    → módulos por programa (nro, nombre, horas, pago docente) y docentes
                 (nombre, grado, tipo; sin celular ni e-mail)
    CRITERIOS  → estados académico / reprobado / ARCA
- PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx
    Programas Notificados → completa programas (costo, punto de equilibrio, duración,
                 estado, origen, diseño curricular) y agrega los que ARCA no tiene
- BD Techos.xlsx → instituciones con convenio y sus programas (techos académicos)
- EJECUTADO VS META.xlsx [EJECUTADO] → metas mensuales por categoría y EBITDA meta
  (lo ejecutado NO se siembra: proviene de la ingesta hacia el DW)
- Cabeceras y valores de todos los libros → equivalencias de conceptos financieros
  y enriquecimiento del mapeo de columnas usado como guía de ingesta / BETO.

Salida: db/seeds/seed_catalogos.sql = datos generados + seed_catalogos_config.sql
(configuración curada: etiquetas de clasificación, mapeo base y plantillas).

Uso:
    python db/seeds/populate_catalogos.py                 # solo genera el SQL
    python db/seeds/populate_catalogos.py --load          # genera y aplica (upsert)
    python db/seeds/populate_catalogos.py --load --reset  # vacía el catálogo y recarga
"""

from __future__ import annotations

import argparse
import difflib
import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import openpyxl

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SEEDS_DIR = Path(__file__).resolve().parent
DIR_DATOS = BASE_DIR / "uploads" / "data"

ARCHIVO_ARCA = "Base centralizada Académica ARCA (1).xlsx"
ARCHIVO_PLANIF = "PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx"
ARCHIVO_TECHOS = "BD Techos.xlsx"
ARCHIVO_METAS = "EJECUTADO VS META.xlsx"
ARCHIVO_COBRANZAS = "BD Cobranzas.xlsx"

# Tablas que se vacían con --reset (stg_entidad_no_resuelta es trabajo operativo: no se toca)
TABLAS_CATALOGO = [
    "cat_convenio_programa", "cat_institucion_convenio", "cat_historico_equivalencia",
    "cat_concepto_financiero", "cat_modulo", "cat_programa", "cat_docente", "cat_escuela",
    "cat_tipo_programa", "cat_modalidad", "cat_estado_academico", "cat_estado_reprobado",
    "cat_estado_arca", "cat_tipo_cartera", "ref_metas_gestion", "cat_categoria_financiera",
    "cat_etiqueta_clasificacion", "cat_mapeo_columna", "cat_guia_texto_plano",
]


# ── Utilidades ────────────────────────────────────────────────────────────────

def limpiar_texto(val: Any) -> str:
    return re.sub(r"\s+", " ", str(val)).strip() if val is not None else ""


def clave(val: Any) -> str:
    """Clave de comparación: sin tildes, mayúsculas, sin puntuación redundante."""
    txt = unicodedata.normalize("NFKD", limpiar_texto(val))
    txt = "".join(c for c in txt if not unicodedata.combining(c)).upper()
    return re.sub(r"\s+", " ", re.sub(r"[^\w/%() -]", " ", txt)).strip()


def num(val: Any) -> Optional[float]:
    if val is None or isinstance(val, (bool, datetime)):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    txt = str(val).strip().replace("Bs", "").replace(" ", "")
    if not txt:
        return None
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", txt):  # 1.234.567,89
        txt = txt.replace(".", "").replace(",", ".")
    else:
        txt = txt.replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return None


def entero(val: Any) -> Optional[int]:
    n = num(val)
    return int(round(n)) if n is not None else None


def pos_code(val: Any) -> Optional[str]:
    """'4895', 4895.0, 'POS-4895', 'POS 4895' → 'POS-4895'."""
    m = re.search(r"(\d{3,6})", limpiar_texto(val))
    return f"POS-{m.group(1)}" if m else None


_ROMANOS = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
            "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15}
_RE_VERSION = re.compile(r"\bv\s*\.?\s*(\d+|[IVX]{1,5})\b", re.IGNORECASE)


def separar_version(nombre: str, columna: Any = None) -> Tuple[str, Optional[int]]:
    """Separa el sufijo de versión ('v. 28', 'v27', 'v. I - NAL') del nombre canónico."""
    version = None
    m = _RE_VERSION.search(nombre)
    if m:
        tok = m.group(1).upper()
        version = int(tok) if tok.isdigit() else _ROMANOS.get(tok)
        nombre = nombre[:m.start()]
    nombre = re.sub(r"\s*-\s*NAL\b.*$", "", nombre, flags=re.IGNORECASE)
    nombre = re.sub(r"^POS\s*-?\s*\d+\s*[-:]?\s*", "", nombre, flags=re.IGNORECASE)  # 'POS-4244 DIPLOMADO…'
    if version is None:
        version = entero(columna)
    return limpiar_texto(nombre).strip(" -"), version


def sql(val: Any) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return repr(round(val, 4)) if isinstance(val, float) else str(val)
    return "'" + str(val).replace("'", "''") + "'"


def leer_hoja(archivo: str, hoja: str, fila_cabecera: int = 0) -> Tuple[List[str], List[tuple]]:
    ruta = DIR_DATOS / archivo
    if not ruta.exists():
        print(f"  ! No existe {archivo}; se omite.")
        return [], []
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    if hoja not in wb.sheetnames:
        print(f"  ! {archivo} no tiene la hoja '{hoja}'; se omite.")
        return [], []
    filas = list(wb[hoja].iter_rows(values_only=True))
    wb.close()
    if len(filas) <= fila_cabecera:
        return [], []
    cab = [clave(c) for c in filas[fila_cabecera]]
    datos = [f for f in filas[fila_cabecera + 1:] if f and any(v is not None for v in f)]
    return cab, datos


def col(cab: List[str], *prefijos: str) -> Optional[int]:
    for p in prefijos:
        p = clave(p)
        for i, h in enumerate(cab):
            if h.startswith(p):
                return i
    return None


def celda(fila: tuple, i: Optional[int]) -> Any:
    return fila[i] if i is not None and i < len(fila) else None


class Canonizador:
    """Elige la grafía más frecuente para cada clave (p. ej. 'Tecnología' vs 'TECNOLOGÍA')."""

    def __init__(self, alias: Optional[Dict[str, str]] = None):
        self.formas: Dict[str, Counter] = defaultdict(Counter)
        self.alias = {clave(k): clave(v) for k, v in (alias or {}).items()}

    def k(self, val: Any) -> str:
        c = clave(val)
        return self.alias.get(c, c)

    def agregar(self, val: Any) -> Optional[str]:
        txt = limpiar_texto(val)
        if not txt:
            return None
        self.formas[self.k(txt)][txt] += 1
        return self.k(txt)

    def nombre(self, k: Optional[str]) -> Optional[str]:
        if not k or k not in self.formas:
            return None
        # Prioridad: grafía que coincide con la clave canónica (no un alias), luego con
        # tildes/minúsculas (más legible) y por último la más frecuente
        return max(self.formas[k].items(),
                   key=lambda kv: (clave(kv[0]) == k, kv[0] != kv[0].upper(), kv[1]))[0]

    def todos(self) -> List[str]:
        return sorted(self.nombre(k) for k in self.formas)


# ── Extracción ────────────────────────────────────────────────────────────────

def extraer(dir_datos: Path = DIR_DATOS) -> Dict[str, Any]:
    global DIR_DATOS
    DIR_DATOS = Path(dir_datos)

    # 'Tecnologia e Ingeniería' (ARCA) es la misma escuela que 'Tecnología' (Planificación/Techos)
    escuelas = Canonizador({"TECNOLOGIA E INGENIERIA": "TECNOLOGIA"})
    tipos = Canonizador()
    modalidades = Canonizador()
    programas: Dict[str, Dict[str, Any]] = {}
    docentes: Dict[str, Dict[str, Any]] = {}
    modulos: Dict[Tuple[str, int], Dict[str, Any]] = {}
    estados = {"academico": Canonizador(), "reprobado": Canonizador(), "arca": Canonizador()}

    def programa(pc: str) -> Dict[str, Any]:
        return programas.setdefault(pc, {"pos_code": pc, "fuentes": set()})

    # 1. ARCA · IBP ───────────────────────────────────────────────────────────
    print(f"Leyendo {ARCHIVO_ARCA} …")
    cab, filas = leer_hoja(ARCHIVO_ARCA, "IBP")
    i_pos, i_nom, i_ver = col(cab, "POS - IBP"), col(cab, "NOMBRE DEL PROGRAMA"), col(cab, "VERSION")
    i_esc, i_inv, i_pe = col(cab, "ESCUELA"), col(cab, "INVERSION"), col(cab, "PUNTO EQUILIBRIO")
    i_hrs, i_mod, i_tipo = col(cab, "HORAS CLASE"), col(cab, "MODALIDAD"), col(cab, "TIPO DE PROGRAMA")
    i_est = col(cab, "ESTADO PROGRAMA")
    for f in filas:
        pc, nombre_raw = pos_code(celda(f, i_pos)), limpiar_texto(celda(f, i_nom))
        if not pc or not nombre_raw:
            continue
        nombre, version = separar_version(nombre_raw, celda(f, i_ver))
        p = programa(pc)
        p.update({
            "nombre_programa": nombre, "version": version, "nombre_completo_raw": nombre_raw,
            "escuela": escuelas.agregar(celda(f, i_esc)),
            "tipo": tipos.agregar(limpiar_texto(celda(f, i_tipo)).upper()),
            "modalidad": modalidades.agregar(limpiar_texto(celda(f, i_mod)).upper()),
            "inversion_base": num(celda(f, i_inv)) or None,
            "punto_equilibrio": entero(celda(f, i_pe)) or None,
            "horas_totales": entero(celda(f, i_hrs)) or None,
            "estado_programa": limpiar_texto(celda(f, i_est)) or None,
        })
        p["fuentes"].add("ARCA")

    # 2. ARCA · MODULOS (+ docentes sin datos de contacto) ─────────────────────
    cab, filas = leer_hoja(ARCHIVO_ARCA, "MODULOS")
    i_pos, i_doc, i_tdoc = col(cab, "POS - MODULO"), col(cab, "DOCENTE"), col(cab, "TIPO DE DOCENTE")
    i_nro, i_hrs, i_pago, i_grado = col(cab, "MODULO"), col(cab, "HRS MODULO"), col(cab, "PAGO DOCENTE"), col(cab, "GRADO ACADEMICO")
    i_nmod = col(cab, "NOMBRE DEL PROGRAMA")  # en esta hoja la columna contiene el nombre del módulo
    i_tipo = col(cab, "TIPO DE PROGRAMA")
    for f in filas:
        nom_doc = limpiar_texto(celda(f, i_doc))
        if nom_doc and len(nom_doc) > 3:
            d = docentes.setdefault(clave(nom_doc), {"nombre_completo": nom_doc, "grado": Counter(), "tipo": Counter()})
            if celda(f, i_grado):
                d["grado"][limpiar_texto(celda(f, i_grado))] += 1
            if celda(f, i_tdoc):
                d["tipo"][limpiar_texto(celda(f, i_tdoc)).upper()] += 1
        pc, nro, nombre_mod = pos_code(celda(f, i_pos)), entero(celda(f, i_nro)), limpiar_texto(celda(f, i_nmod))
        if not pc or nro is None or not nombre_mod:
            continue
        if pc not in programas:  # módulo de un programa sin fila IBP: se registra con lo que trae la hoja
            p = programa(pc)
            p.setdefault("tipo", tipos.agregar(limpiar_texto(celda(f, i_tipo)).upper()))
            p["fuentes"].add("ARCA_MODULOS")
        modulos[(pc, nro)] = {
            "pos_code": pc, "nro_modulo": nro, "nombre_modulo": nombre_mod,
            "horas_modulo": num(celda(f, i_hrs)), "pago_docente_base": num(celda(f, i_pago)),
        }

    # 3. ARCA · CRITERIOS ──────────────────────────────────────────────────────
    cab, filas = leer_hoja(ARCHIVO_ARCA, "CRITERIOS")
    for f in filas:
        for k, i in (("academico", col(cab, "ESTADO ACADEMICO")), ("reprobado", col(cab, "ESTADO REPROBADO")),
                     ("arca", col(cab, "ESTADO ARCA"))):
            estados[k].agregar(celda(f, i))

    # 4. PLANIFICACIÓN · Programas Notificados ─────────────────────────────────
    print(f"Leyendo {ARCHIVO_PLANIF} …")
    cab, filas = leer_hoja(ARCHIVO_PLANIF, "Programas Notificados")
    i_pos, i_esc, i_tipo, i_prog = col(cab, "POS"), col(cab, "ESCUELA"), col(cab, "TIPO DE PROGRAMA"), col(cab, "PROGRAMA")
    i_ver, i_dur, i_costo = col(cab, "VERSION"), col(cab, "DURACION DEL PROGRAMA"), col(cab, "COSTO PROGRAMA")
    i_pe, i_est, i_ori, i_dis = col(cab, "PUNTO DE EQUILIBRIO"), col(cab, "ESTADO DEL PROGRAMA"), col(cab, "CATEGORIA DE ORIGEN"), col(cab, "DISENO CURRICULAR")
    i_ini = col(cab, "FECHA INICIO")
    for f in sorted(filas, key=lambda r: celda(r, i_ini) if isinstance(celda(r, i_ini), datetime) else datetime.min):
        pc, nombre_raw = pos_code(celda(f, i_pos)), limpiar_texto(celda(f, i_prog))
        if not pc or not nombre_raw:
            continue
        nombre, version = separar_version(nombre_raw, celda(f, i_ver))
        p = programa(pc)
        nuevo = "nombre_programa" not in p
        if nuevo:
            p.update({"nombre_programa": nombre, "version": version, "nombre_completo_raw": nombre_raw})
        p["escuela"] = p.get("escuela") or escuelas.agregar(celda(f, i_esc))
        p["tipo"] = p.get("tipo") or tipos.agregar(limpiar_texto(celda(f, i_tipo)).upper())
        p["inversion_base"] = p.get("inversion_base") or num(celda(f, i_costo)) or None
        p["punto_equilibrio"] = p.get("punto_equilibrio") or entero(celda(f, i_pe)) or None
        # Atributos de seguimiento: la notificación más reciente prevalece
        for campo, i in (("duracion_meses", i_dur),):
            p[campo] = num(celda(f, i)) or p.get(campo)
        for campo, i in (("estado_programa", i_est), ("origen_programa", i_ori), ("diseno_curricular", i_dis)):
            p[campo] = limpiar_texto(celda(f, i)) or p.get(campo)
        p["fuentes"].add("PLANIFICACION")

    # 5. BD Techos · convenios ─────────────────────────────────────────────────
    print(f"Leyendo {ARCHIVO_TECHOS} …")
    cab, filas = leer_hoja(ARCHIVO_TECHOS, "BD Techos")
    i_inst, i_pos, i_prog, i_esc = col(cab, "INSITUCION", "INSTITUCION"), col(cab, "POS"), col(cab, "PROGRAMA"), col(cab, "ESCUELA")
    instituciones: Dict[str, Dict[str, Any]] = {}

    def k_inst(nombre: str) -> str:
        k = clave(nombre)
        k = re.sub(r"\b(S\s*R\s*L|SRL|LTDA|S\s*A)\b", "", k)
        k = re.sub(r"[^A-Z0-9 ]", "", k)
        return re.sub(r"\s+", " ", k).strip()

    for f in filas:
        nombre_inst = limpiar_texto(celda(f, i_inst))
        if not nombre_inst:
            continue
        k = k_inst(nombre_inst)
        # Fusiona grafías con error de captura ('OACHING CONSULTING…' ≈ 'COACHING CONSULTING…')
        similar = difflib.get_close_matches(k, list(instituciones), n=1, cutoff=0.9)
        k = similar[0] if similar else k
        inst = instituciones.setdefault(k, {"formas": Counter(), "programas": set()})
        inst["formas"][nombre_inst] += 1
        pc, nombre_raw = pos_code(celda(f, i_pos)), limpiar_texto(celda(f, i_prog))
        if pc:
            p = programa(pc)
            if "nombre_programa" not in p and nombre_raw:
                nombre, version = separar_version(nombre_raw)
                tipo_txt = next((t for t in ("DIPLOMADO", "PROGRAMA EXPERTO", "CURSO") if clave(nombre_raw).startswith(t)), None)
                p.update({"nombre_programa": nombre, "version": version, "nombre_completo_raw": nombre_raw,
                          "tipo": tipos.agregar(tipo_txt) if tipo_txt else None,
                          "origen_programa": "Techo académico (convenio)"})
            p["escuela"] = p.get("escuela") or escuelas.agregar(celda(f, i_esc))
            p["fuentes"].add("BD_TECHOS")
            inst["programas"].add(pc)

    # 6. Metas (solo planificado) ──────────────────────────────────────────────
    print(f"Leyendo {ARCHIVO_METAS} …")
    cab, filas = leer_hoja(ARCHIVO_METAS, "EJECUTADO")
    i_cat, i_mes = col(cab, "CATEGORIA"), col(cab, "MES NUMERICO")
    metas_cols = {a: col(cab, f"META POR CATEGORIA {a}") for a in (2024, 2025, 2026)}
    ebitda_cols = {a: col(cab, f"EBITDA META {a}") for a in (2024, 2025, 2026)}
    metas = []
    for f in filas:
        cat, mes = limpiar_texto(celda(f, i_cat)).upper(), entero(celda(f, i_mes))
        if not cat or not mes or not 1 <= mes <= 12:
            continue
        for anio in (2024, 2025, 2026):
            meta, ebitda = num(celda(f, metas_cols[anio])), num(celda(f, ebitda_cols[anio]))
            if meta is None and ebitda is None:
                continue
            metas.append({
                "gestion": anio, "mes": mes, "categoria": cat, "meta": meta, "ebitda_meta": ebitda,
                "fuente": f"{ARCHIVO_METAS} [EJECUTADO] META POR CATEGORIA {anio}",
            })
    # Una columna anual con valor en menos de 3 meses no es una serie mensual
    # (p. ej. 2024 TECHOS/CERRADOS solo trae un total en diciembre): se descarta ese monto.
    meses_con_meta = Counter((m["gestion"], m["categoria"]) for m in metas if m["meta"] is not None)
    for m in metas:
        n_meses = meses_con_meta[(m["gestion"], m["categoria"])]
        if m["meta"] is not None and n_meses < 3:
            print(f"  · Meta {m['gestion']} {m['categoria']} mes {m['mes']} = {m['meta']:,.0f} descartada "
                  f"(la columna no es mensual: {n_meses} mes(es) con dato)")
            m["meta"] = None
    metas = [m for m in metas if m["meta"] is not None or m["ebitda_meta"] is not None]

    # 7. Carteras: reglas de clasificación validadas con los días de mora reales ─
    print(f"Leyendo {ARCHIVO_COBRANZAS} …")
    cab, filas = leer_hoja(ARCHIVO_COBRANZAS, "COBRANZAS 2024 2025")
    i_car, i_dias = col(cab, "TIPO DE CARTERA"), col(cab, "DIAS DE MORA")
    observado: Dict[str, List[int]] = defaultdict(list)
    for f in filas:
        car, dias = clave(celda(f, i_car)), entero(celda(f, i_dias))
        if car and dias is not None:
            observado[car].append(dias)

    return {
        "escuelas": escuelas, "tipos": tipos, "modalidades": modalidades, "estados": estados,
        "programas": programas, "docentes": docentes, "modulos": list(modulos.values()),
        "instituciones": instituciones, "metas": metas, "carteras_observadas": observado,
    }


# ── Carteras: reglas institucionales (nombres = valores reales de BD Cobranzas) ─
REGLAS_CARTERA = [
    ("Cartera Vigente", 0, 90, "Regla de clasificación: 0 a 90 días de mora"),
    ("Cartera en Mora", 91, 180, "Regla de clasificación: 91 a 180 días de mora"),
    ("Cartera Previsionable", 181, 360, "Regla de clasificación: 181 a 360 días de mora"),
    ("Cartera Incobrable", 361, 99999, "Regla de clasificación: más de 360 días de mora"),
    ("Cartera Cerrada", -1, -1, "Obligación cancelada (sin saldo pendiente)"),
]


# ── Conceptos financieros: vocabulario canónico + equivalencias observadas ──────
CONCEPTOS = [
    # código, nombre, movimiento, categoría contable, descripción, patrón sobre el término observado
    ("FIN-CUOTA-01", "CUOTA", "INGRESO", "COBRANZA", "Pago fraccionado del costo del programa",
     r"^(CUOTAS?|CUOTA \d.*|C[1-8]|CUOTA POSTGRADO|CANTIDAD DE CUOTAS|TOTAL DE CUOTAS|NRO CUOTA.*)$"),
    ("FIN-MAT-01", "MATRICULA", "INGRESO", "COBRANZA", "Derecho de inscripción o matrícula",
     r"^(MATRICULA.*|MONTO (DE )?INSCRIPCION)$"),
    ("FIN-CONTADO-01", "CONTADO", "INGRESO", "COBRANZA", "Pago total al contado del programa",
     r"^(CONTADO|PAGO AL CONTADO|TP AL CONTADO.*|TOTAL PROYECTADO AL CONTADO.*)$"),
    ("FIN-REINC-01", "REINCORPORACION", "INGRESO", "COBRANZA", "Reincorporación de un participante",
     r"^REINCORPORACION$"),
    ("FIN-DESC-01", "DESCUENTO", "AJUSTE", "COBRANZA", "Descuento aplicado al costo del programa",
     r"^(DESCUENTO.*|CP CON DESCUENTO.*|COSTO PROGRAMA CON DESCUENT.*|COSTO DEL PROGRAMA AL \d+%.*)$"),
    ("FIN-MORA-01", "MORA", "SALDO", "COBRANZA", "Días o estado de atraso en el pago",
     r"^(DIAS DE MORA|DIAS DE PAGO PENDIENTE|SALDO MORA|CARTERA EN MORA)$"),
    ("FIN-DEUDA-01", "DEUDA_TOTAL", "SALDO", "COBRANZA", "Saldo pendiente de cobro",
     r"^(DEUDA TOTAL|MONTO A COBRAR.*|SALDO( PENDIENTE)?)$"),
    ("FIN-PAGADO-01", "TOTAL_PAGADO", "INGRESO", "COBRANZA", "Monto efectivamente pagado o facturado",
     r"^(TOTAL PAGADO|MONTO PAGADO|MONTO EN BS|TOTAL INGRESOS|INGRESO)$"),
    ("FIN-COSTO-01", "COSTO_PROGRAMA", "INGRESO", "OPERATIVO", "Precio de lista del programa",
     r"^(COSTO (DEL )?PROGRAMA|INVERSION DEL PROGRAMA)$"),
    ("FIN-EGR-REAL-01", "EGRESO_REAL", "EGRESO", "OPERATIVO", "Egreso real del programa",
     r"^(EGRESO REAL( DOLARES)?|GASTOS PROGRAMA)$"),
    ("FIN-EGR-ANT-01", "EGRESO_ANTERIOR", "EGRESO", "OPERATIVO", "Egreso presupuestado/anterior del programa",
     r"^EGRESO ANTERIOR( DOLARES)?$"),
    ("FIN-RENT-01", "RENTABILIDAD", "SALDO", "OPERATIVO", "Ingreso menos egreso del programa",
     r"^RENTABILIDAD( DOLARES)?$"),
    ("FIN-HON-DOC-01", "HONORARIO_DOCENTE", "EGRESO", "DOCENTE", "Pago al docente por módulo",
     r"^(PAGO DOCENTE|HONORARIOS?( DOCENTE)?)$"),
    ("FIN-TECHO-01", "TECHO_CONVENIO", "INGRESO", "CONVENIO", "Ingreso por techos académicos / programas cerrados",
     r"^(POR TECHOS/CERRADOS|TECHOS/CERRADOS|TECHO|INGRESO PROYECTADO TECHOS.*|GESTION TECHO)$"),
    ("FIN-PE-01", "PUNTO_EQUILIBRIO", "SALDO", "OPERATIVO", "Inscritos mínimos para cubrir costos",
     r"^PUNTO (DE )?EQUILIBRIO$"),
    ("FIN-META-PROG-01", "META_PROGRAMAS", "INGRESO", "METAS", "Meta de ingreso por programas regulares",
     r"^(META POR CATEGORIA \d{4}|META \d{4}( 2DO SEMESTRE)?|META \(PROGRAMAS.*|POR PROGRAMAS|PROGRAMAS)$"),
    ("FIN-EBITDA-01", "EBITDA", "SALDO", "METAS", "Margen EBITDA meta/ejecutado",
     r"^EBITDA (META|EJECUTADO) \d{4}$"),
]

# Columnas cuyos VALORES son términos financieros (además de todas las cabeceras)
VALORES_FINANCIEROS = [
    (ARCHIVO_COBRANZAS, "COBRANZAS 2024 2025", 0, "TIPO DE INSCRIPCION"),
    (ARCHIVO_COBRANZAS, "COBRANZAS 2024 2025", 0, "TIPO DE CARTERA"),
    ("BD Egresos.xlsx", "Gestiones", 0, "TIPO DE INGRESO"),
    ("BD Egresos.xlsx", "egresos", 0, "TIPO DE PROGRAMA"),
    (ARCHIVO_METAS, "EJECUTADO", 0, "CATEGORIA"),
]

# Mapeo de cabeceras observadas → campo canónico de ingesta (tipo de entidad NER)
REGLAS_COLUMNA = [
    ("CI", "CI", r"^(CI|C I|CEDULA.*|CARNET.*|NRO DOCUMENTO|DOC.? IDENTIDAD.*|CODIGO ESTUDIANTE O NIT)$"),
    ("PATERNO", "ESTUDIANTE", r"^(APELLIDO )?PATERNO$"),
    ("MATERNO", "ESTUDIANTE", r"^(APELLIDO )?MATERNO$"),
    ("ESTUDIANTE", "ESTUDIANTE", r"^(NOMBRES?|NOMBRE COMPLETO|ESTUDIANTE.*|ALUMNO|PARTICIPANTE.*|RAZON SOCIAL)$"),
    ("POS", "POS", r"^(POS|N POS|NRO POS|POS - \w+|PROYECTO \(POS\)|POS\+IBP|POS \+ IBP)$"),
    ("PROGRAMA", "PROGRAMA", r"^(PROGRAMA|NOMBRE DEL PROGRAMA|CARRERA)$"),
    ("MODULO", "MODULO", r"^(MODULO( \d+)?|NOMBRE (DEL )?MODULO|MATERIA|ASIGNATURA)$"),
    ("DOCENTE", "DOCENTE", r"^(DOCENTE|NOMBRE DOCENTE|PROFESOR|FACILITADOR)$"),
    ("NOTA", "NOTA", r"^(NOTA.*|CALIFICACION.*|PROMEDIO.*)$"),
    ("MONTO", "MONTO", r"^(MONTO.*|IMPORTE.*|COSTO PROGRAMA|DEUDA TOTAL|TOTAL INGRESOS|INGRESO|EGRESO REAL)$"),
    ("FECHA", "FECHA", r"^FECHA.*$"),
    ("FACTURA", "FACTURA", r"^(N (DE )?FACTURA|NUMERO (DE )?FACTURA|NRO FACTURA)$"),
    ("ESTADO", "OTRO", r"^ESTADO.*$"),
    ("ASESOR", "OTRO", r"^ASESOR.*$"),
]


def observar_terminos(dir_datos: Path) -> Tuple[Dict[str, Counter], Dict[str, Counter]]:
    """Cabeceras (fila con más textos entre las 15 primeras) y valores de columnas financieras.

    Devuelve {termino_normalizado: Counter(fuente)} para cabeceras y para valores.
    """
    cabeceras: Dict[str, Counter] = defaultdict(Counter)
    formas: Dict[str, Counter] = defaultdict(Counter)
    for ruta in sorted(Path(dir_datos).glob("*.xlsx")):
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
        for ws in wb.worksheets:
            primeras = []
            for i, r in enumerate(ws.iter_rows(values_only=True)):
                primeras.append(r)
                if i >= 14:
                    break
            if not primeras:
                continue
            fila = max(primeras, key=lambda r: sum(1 for c in r if isinstance(c, str) and c.strip()))
            for c in fila:
                if isinstance(c, str) and c.strip() and len(c.strip()) <= 80:
                    k = clave(c)
                    cabeceras[k][f"{ruta.name} [{ws.title}]"] += 1
                    formas[k][limpiar_texto(c)] += 1
        wb.close()

    valores: Dict[str, Counter] = defaultdict(Counter)
    for archivo, hoja, fila_cab, columna in VALORES_FINANCIEROS:
        cab, filas = leer_hoja(archivo, hoja, fila_cab)
        i = col(cab, columna)
        for f in filas:
            v = limpiar_texto(celda(f, i))
            if v:
                k = clave(v)
                valores[k][f"{archivo} [{hoja}] {columna}"] += 1
                formas[k][v] += 1
    observar_terminos.formas = formas  # grafía original más frecuente por clave
    return cabeceras, valores


def forma(k: str) -> str:
    f = getattr(observar_terminos, "formas", {}).get(k)
    return f.most_common(1)[0][0] if f else k


# ── Generación SQL ────────────────────────────────────────────────────────────

def generar_sql(cat: Dict[str, Any], ruta_salida: Path, ruta_config: Path) -> Dict[str, int]:
    L: List[str] = [
        "-- =============================================================================",
        "-- SEMILLA DE CATÁLOGOS INSTITUCIONALES · giragroup_catalog_db",
        f"-- Generado por db/seeds/populate_catalogos.py desde uploads/data ({datetime.now():%Y-%m-%d %H:%M})",
        "-- Todo valor proviene de un archivo fuente; sin dato en la fuente → NULL.",
        "-- =============================================================================",
        "",
    ]
    esc, tip, mod, est = cat["escuelas"], cat["tipos"], cat["modalidades"], cat["estados"]
    cuenta: Dict[str, int] = Counter()

    def ins(seccion: str, linea: str):
        L.append(linea)
        cuenta[seccion] += 1

    L.append("-- 1. Escuelas")
    for n in esc.todos():
        ins("escuelas", f"INSERT INTO public.cat_escuela (nombre_escuela) VALUES ({sql(n)}) ON CONFLICT (nombre_escuela) DO NOTHING;")
    L += ["", "-- 2. Tipos de Programa"]
    for n in tip.todos():
        ins("tipos", f"INSERT INTO public.cat_tipo_programa (nombre_tipo) VALUES ({sql(n)}) ON CONFLICT (nombre_tipo) DO NOTHING;")
    L += ["", "-- 3. Modalidades"]
    for n in mod.todos():
        ins("modalidades", f"INSERT INTO public.cat_modalidad (nombre_modalidad) VALUES ({sql(n)}) ON CONFLICT (nombre_modalidad) DO NOTHING;")

    L += ["", "-- 4. Criterios y Estados (ARCA · CRITERIOS)"]
    for n in est["academico"].todos():
        ins("estados", f"INSERT INTO public.cat_estado_academico (nombre_estado) VALUES ({sql(n)}) ON CONFLICT (nombre_estado) DO NOTHING;")
    for n in est["reprobado"].todos():
        ins("estados", f"INSERT INTO public.cat_estado_reprobado (nombre_detalle) VALUES ({sql(n)}) ON CONFLICT (nombre_detalle) DO NOTHING;")
    for n in est["arca"].todos():
        ins("estados", f"INSERT INTO public.cat_estado_arca (nombre_arca) VALUES ({sql(n)}) ON CONFLICT (nombre_arca) DO NOTHING;")

    L += ["", "-- 5. Clasificación de Carteras (reglas; nombres según BD Cobranzas)"]
    for nombre, mn, mx, desc in REGLAS_CARTERA:
        ins("carteras",
            f"INSERT INTO public.cat_tipo_cartera (nombre_cartera, dias_mora_min, dias_mora_max, descripcion) "
            f"VALUES ({sql(nombre)}, {mn}, {mx}, {sql(desc)}) ON CONFLICT (nombre_cartera) DO UPDATE SET "
            f"dias_mora_min = EXCLUDED.dias_mora_min, dias_mora_max = EXCLUDED.dias_mora_max, descripcion = EXCLUDED.descripcion;")

    L += ["", "-- 6. Docentes (ARCA · MODULOS; sin celular ni e-mail)"]
    for d in sorted(cat["docentes"].values(), key=lambda x: x["nombre_completo"]):
        grado = d["grado"].most_common(1)[0][0] if d["grado"] else None
        tipo = d["tipo"].most_common(1)[0][0] if d["tipo"] else None
        ins("docentes",
            f"INSERT INTO public.cat_docente (nombre_completo, grado_academico, tipo_docente) "
            f"VALUES ({sql(d['nombre_completo'])}, {sql(grado)}, {sql(tipo)}) ON CONFLICT (nombre_completo) DO UPDATE SET "
            f"grado_academico = EXCLUDED.grado_academico, tipo_docente = EXCLUDED.tipo_docente, email = NULL, celular = NULL;")

    L += ["", "-- 7. Programas (ARCA · IBP + Planificación · Programas Notificados + BD Techos)"]
    for p in sorted(cat["programas"].values(), key=lambda x: x["pos_code"]):
        if not p.get("nombre_programa"):
            continue
        ins("programas",
            "INSERT INTO public.cat_programa (pos_code, nombre_programa, version, nombre_completo_raw, "
            "id_escuela, id_tipo_programa, id_modalidad, inversion_base, punto_equilibrio, horas_totales, "
            "duracion_meses, estado_programa, origen_programa, diseno_curricular, fuente_datos) VALUES ("
            f"{sql(p['pos_code'])}, {sql(p['nombre_programa'])}, {p.get('version') or 1}, {sql(p.get('nombre_completo_raw'))}, "
            f"(SELECT id_escuela FROM public.cat_escuela WHERE nombre_escuela = {sql(esc.nombre(p.get('escuela')))}), "
            f"(SELECT id_tipo_programa FROM public.cat_tipo_programa WHERE nombre_tipo = {sql(tip.nombre(p.get('tipo')))}), "
            f"(SELECT id_modalidad FROM public.cat_modalidad WHERE nombre_modalidad = {sql(mod.nombre(p.get('modalidad')))}), "
            f"{sql(p.get('inversion_base'))}, {sql(p.get('punto_equilibrio'))}, {sql(p.get('horas_totales'))}, "
            f"{sql(p.get('duracion_meses'))}, {sql(p.get('estado_programa'))}, {sql(p.get('origen_programa'))}, "
            f"{sql(p.get('diseno_curricular'))}, {sql('+'.join(sorted(p['fuentes'])))}) "
            "ON CONFLICT (pos_code) DO UPDATE SET nombre_programa = EXCLUDED.nombre_programa, version = EXCLUDED.version, "
            "nombre_completo_raw = EXCLUDED.nombre_completo_raw, id_escuela = EXCLUDED.id_escuela, "
            "id_tipo_programa = EXCLUDED.id_tipo_programa, id_modalidad = EXCLUDED.id_modalidad, "
            "inversion_base = EXCLUDED.inversion_base, punto_equilibrio = EXCLUDED.punto_equilibrio, "
            "horas_totales = EXCLUDED.horas_totales, duracion_meses = EXCLUDED.duracion_meses, "
            "estado_programa = EXCLUDED.estado_programa, origen_programa = EXCLUDED.origen_programa, "
            "diseno_curricular = EXCLUDED.diseno_curricular, fuente_datos = EXCLUDED.fuente_datos;")

    L += ["", "-- 8. Módulos por Programa (ARCA · MODULOS)"]
    for m in sorted(cat["modulos"], key=lambda x: (x["pos_code"], x["nro_modulo"])):
        ins("modulos",
            f"INSERT INTO public.cat_modulo (id_programa, nro_modulo, nombre_modulo, horas_modulo, pago_docente_base) "
            f"SELECT id_programa, {m['nro_modulo']}, {sql(m['nombre_modulo'])}, {sql(m['horas_modulo'])}, {sql(m['pago_docente_base'])} "
            f"FROM public.cat_programa WHERE pos_code = {sql(m['pos_code'])} "
            "ON CONFLICT (id_programa, nro_modulo) DO UPDATE SET nombre_modulo = EXCLUDED.nombre_modulo, "
            "horas_modulo = EXCLUDED.horas_modulo, pago_docente_base = EXCLUDED.pago_docente_base;")

    L += ["", "-- 9. Instituciones con convenio y sus programas (BD Techos)"]
    for inst in sorted(cat["instituciones"].values(), key=lambda x: -sum(x["formas"].values())):
        nombre = inst["formas"].most_common(1)[0][0]
        variantes = " | ".join(sorted(inst["formas"]))
        ins("convenios",
            f"INSERT INTO public.cat_institucion_convenio (nombre_institucion, variantes_origen, fuente_referencia) "
            f"VALUES ({sql(nombre)}, {sql(variantes)}, {sql(ARCHIVO_TECHOS + ' [BD Techos]')}) "
            "ON CONFLICT (nombre_institucion) DO UPDATE SET variantes_origen = EXCLUDED.variantes_origen;")
        for pc in sorted(inst["programas"]):
            ins("convenio_programa",
                "INSERT INTO public.cat_convenio_programa (id_convenio, id_programa) "
                f"SELECT c.id_convenio, p.id_programa FROM public.cat_institucion_convenio c, public.cat_programa p "
                f"WHERE c.nombre_institucion = {sql(nombre)} AND p.pos_code = {sql(pc)} ON CONFLICT DO NOTHING;")

    L += ["", "-- 10. Metas de Gestión (solo planificado; lo ejecutado llega por ingesta)"]
    for mt in cat["metas"]:
        ins("metas",
            "INSERT INTO public.ref_metas_gestion (gestion, mes, categoria, monto_meta_ingreso, monto_ejecutado, "
            "ebitda_meta_pct, ebitda_ejecutado_pct, fuente_referencia) "
            f"VALUES ({mt['gestion']}, {mt['mes']}, {sql(mt['categoria'])}, {sql(mt['meta'])}, NULL, "
            f"{sql(mt['ebitda_meta'])}, NULL, {sql(mt['fuente'])}) ON CONFLICT (gestion, mes, categoria) DO UPDATE SET "
            "monto_meta_ingreso = EXCLUDED.monto_meta_ingreso, monto_ejecutado = NULL, ebitda_meta_pct = EXCLUDED.ebitda_meta_pct, "
            "ebitda_ejecutado_pct = NULL, fuente_referencia = EXCLUDED.fuente_referencia;")

    L += ["", "-- 11. Categorías financieras (valores de EJECUTADO VS META · CATEGORIA)"]
    for categoria in sorted({mt["categoria"] for mt in cat["metas"]}):
        ins("categorias",
            "INSERT INTO public.cat_categoria_financiera (codigo, nombre_categoria, tipo_flujo) "
            f"VALUES ({sql(re.sub(r'[^A-Z0-9]+', '_', clave(categoria)).strip('_'))}, {sql(categoria)}, 'INGRESO') "
            "ON CONFLICT (codigo) DO UPDATE SET nombre_categoria = EXCLUDED.nombre_categoria;")

    # 12. Conceptos financieros con equivalencias observadas
    cabeceras, valores = observar_terminos(DIR_DATOS)
    observados: Dict[str, Counter] = defaultdict(Counter)
    for fuente_map in (cabeceras, valores):
        for k, fuentes in fuente_map.items():
            observados[k].update(fuentes)
    L += ["", "-- 12. Conceptos financieros y equivalencias OBSERVADAS en uploads/data",
          "--     (termino_origen = cabecera o valor literal; fuente = primer libro/hoja donde aparece)"]
    for codigo, nombre, movimiento, categoria, desc, patron in CONCEPTOS:
        rx = re.compile(patron)
        terminos = sorted(k for k in observados if rx.match(k))
        if not terminos:
            print(f"  · {codigo} sin evidencia en las fuentes: no se siembra.")
            continue
        ins("conceptos",
            "INSERT INTO public.cat_concepto_financiero (codigo_canonico, nombre_canonico, tipo_movimiento, categoria_contable, descripcion) "
            f"VALUES ({sql(codigo)}, {sql(nombre)}, {sql(movimiento)}, {sql(categoria)}, {sql(desc)}) "
            "ON CONFLICT (codigo_canonico) DO UPDATE SET nombre_canonico = EXCLUDED.nombre_canonico, "
            "tipo_movimiento = EXCLUDED.tipo_movimiento, categoria_contable = EXCLUDED.categoria_contable, descripcion = EXCLUDED.descripcion;")
        for k in terminos:
            fuente, _ = observados[k].most_common(1)[0]
            n_fuentes = len(observados[k])
            fuente_txt = fuente if n_fuentes == 1 else f"{fuente} (+{n_fuentes - 1})"
            ins("equivalencias",
                "INSERT INTO public.cat_historico_equivalencia (id_concepto, termino_origen, periodo_historico, confianza_mapeo, fuente_referencia) "
                f"SELECT id_concepto, {sql(forma(k)[:150])}, 'TODOS', 1.0, {sql(fuente_txt[:100])} FROM public.cat_concepto_financiero "
                f"WHERE codigo_canonico = {sql(codigo)} AND NOT EXISTS (SELECT 1 FROM public.cat_historico_equivalencia e "
                f"WHERE e.termino_origen = {sql(forma(k)[:150])} AND e.id_concepto = cat_concepto_financiero.id_concepto);")

    # 13-15. Configuración curada + mapeo de columnas enriquecido con cabeceras reales
    config = ruta_config.read_text(encoding="utf-8")
    m_map = re.search(r"(INSERT INTO public\.cat_mapeo_columna[^\n]*VALUES\s*)(.*?)(\n\s*ON CONFLICT[^;]*;|;)", config, re.DOTALL)
    if m_map:
        base = {clave(a): (c, a, t) for c, a, t in re.findall(r"\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", m_map.group(2))}
        nuevos = 0
        for k in sorted(cabeceras):
            if k in base or not k:
                continue
            for campo, entidad, patron in REGLAS_COLUMNA:
                if re.match(patron, k):
                    base[k] = (campo, forma(k).lower(), entidad)
                    nuevos += 1
                    break
        cuenta["mapeo_columnas_observadas"] = nuevos
        filas = ",\n".join(f"    ({sql(c)}, {sql(a)}, {sql(t)})" for c, a, t in
                           sorted(base.values(), key=lambda x: (x[0], x[1])))
        # alias_columna es UNIQUE: se deduplica por texto exacto
        vistos, unicas = set(), []
        for linea in filas.split(",\n"):
            alias = re.findall(r"'((?:[^']|'')*)'", linea)[1]
            if alias not in vistos:
                vistos.add(alias)
                unicas.append(linea)
        config = config[:m_map.start(2)] + ",\n".join(unicas) + config[m_map.end(2):]

    L += ["", config]
    ruta_salida.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"-> {ruta_salida.relative_to(BASE_DIR)} generado")
    return dict(cuenta)


# ── Carga ─────────────────────────────────────────────────────────────────────

def cargar(ruta_sql: Path, reset: bool) -> None:
    from sqlalchemy import create_engine, text

    url = os.getenv("CATALOG_DATABASE_URL")
    if not url:
        raise SystemExit("Defina CATALOG_DATABASE_URL (p. ej. postgresql+psycopg2://user:pass@localhost:5433/giragroup_catalog_db)")
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    schema = (BASE_DIR / "db" / "schema_catalogos.sql").read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(schema)
        if reset:
            conn.exec_driver_sql("TRUNCATE " + ", ".join(f"public.{t}" for t in TABLAS_CATALOGO) + " RESTART IDENTITY CASCADE")
            print("-> Catálogo vaciado (stg_entidad_no_resuelta se conserva)")
        conn.exec_driver_sql(ruta_sql.read_text(encoding="utf-8"))
        totales = conn.execute(text(
            "SELECT 'programas', count(*) FROM cat_programa UNION ALL SELECT 'modulos', count(*) FROM cat_modulo "
            "UNION ALL SELECT 'docentes', count(*) FROM cat_docente UNION ALL SELECT 'convenios', count(*) FROM cat_institucion_convenio "
            "UNION ALL SELECT 'metas', count(*) FROM ref_metas_gestion UNION ALL SELECT 'conceptos', count(*) FROM cat_concepto_financiero "
            "UNION ALL SELECT 'equivalencias', count(*) FROM cat_historico_equivalencia")).fetchall()
    print("-> Cargado en giragroup_catalog_db:", ", ".join(f"{k}={v}" for k, v in totales))


def validar_carteras(observado: Dict[str, List[int]]) -> None:
    print("Validación de reglas de cartera contra DIAS DE MORA reales (BD Cobranzas):")
    for nombre, mn, mx, _ in REGLAS_CARTERA:
        dias = observado.get(clave(nombre), [])
        if not dias:
            print(f"  · {nombre}: sin registros")
            continue
        fuera = sum(1 for d in dias if not (mn <= d <= mx)) if mn >= 0 else None
        extra = f", fuera de regla: {fuera}" if fuera is not None else ""
        print(f"  · {nombre}: n={len(dias)}, días observados {min(dias)}..{max(dias)}{extra}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", default=str(DIR_DATOS))
    ap.add_argument("--load", action="store_true", help="Aplicar el SQL en CATALOG_DATABASE_URL")
    ap.add_argument("--reset", action="store_true", help="Vaciar las tablas de catálogo antes de cargar")
    args = ap.parse_args()

    cat = extraer(Path(args.datos))
    cuenta = generar_sql(cat, SEEDS_DIR / "seed_catalogos.sql", SEEDS_DIR / "seed_catalogos_config.sql")
    print("Resumen:", ", ".join(f"{k}={v}" for k, v in sorted(cuenta.items())))
    validar_carteras(cat["carteras_observadas"])
    if args.load:
        cargar(SEEDS_DIR / "seed_catalogos.sql", args.reset)


if __name__ == "__main__":
    main()
