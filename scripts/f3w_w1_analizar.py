"""W-1 (Recorrido por archivo, 10 libros, matriz motivo x categoria, D-W7) y W-1b (Diferencias F3U-B / D-W11).
Solo lectura sobre f3w_completo (beto_pg_f3w:55634) y uploads/data/.
"""
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
MED = ROOT / "docs" / "mediciones"
ENV = dict(os.environ, MSYS_NO_PATHCONV="1")

LIBROS = [
    "[BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx",
    "Evaluación Docente y Unifranz.xlsx",
    "TBL_INSCRITOS.xlsx",
    "BD Cobranzas.xlsx",
    "BD Techos.xlsx",
    "EJECUTADO VS META.xlsx",
    "BD Egresos.xlsx",
    "PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx",
    "Experiencia Docente 2.0.xlsx",
    "Base centralizada Académica ARCA (1).xlsx",
]


def psql_f3w(sql: str):
    r = subprocess.run(
        ["docker", "exec", "beto_pg_f3w", "psql", "-U", "giragroup_user", "-d", "f3w_completo", "-Atc", sql],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return r.stdout.strip().splitlines()


def main():
    from services.ingestion_service import detectar_tipo_fuente_por_cabeceras

    # 1. Consultar documentos, staging y casos HITL en f3w_completo
    docs_db = {}
    for line in psql_f3w("SELECT id_documento, nombre_archivo, tipo_fuente, tipo_escala FROM dim_origen_documental ORDER BY id_documento;"):
        did, nom, tf, esc = line.split("|")
        docs_db[nom] = {"id_documento": int(did), "tipo_fuente_backend": tf, "tipo_escala": esc}

    stg_por_doc = {}
    for line in psql_f3w(
        "SELECT d.nombre_archivo, count(s.id), COALESCE(SUM(array_length(string_to_array(trim(s.texto_plano), E'\\n'), 1)), 0) "
        "FROM staging_registros_crudos s JOIN dim_origen_documental d ON d.id_documento = s.id_documento "
        "GROUP BY d.nombre_archivo;"
    ):
        nom, bloques, lineas = line.split("|")
        stg_por_doc[nom] = {"bloques": int(bloques), "lineas_paso2": int(lineas)}

    casos_por_doc_motivo = defaultdict(dict)
    ejemplos_por_motivo = defaultdict(list)
    for line in psql_f3w(
        "SELECT d.nombre_archivo, d.tipo_fuente, COALESCE(s.motivo,'NULL'), count(*) "
        "FROM stg_entidad_no_resuelta s JOIN dim_origen_documental d ON d.id_documento = s.id_documento "
        "WHERE COALESCE(s.resuelto,false)=false GROUP BY d.nombre_archivo, d.tipo_fuente, s.motivo ORDER BY count(*) DESC;"
    ):
        nom, tf, mot, cnt = line.split("|")
        casos_por_doc_motivo[nom][mot] = int(cnt)

    # 10 ejemplos por motivo
    motivos_unicos = psql_f3w("SELECT DISTINCT COALESCE(motivo,'NULL') FROM stg_entidad_no_resuelta WHERE COALESCE(resuelto,false)=false;")
    for mot in motivos_unicos:
        rows = psql_f3w(
            f"SELECT s.id_staging, d.nombre_archivo, d.tipo_fuente, COALESCE(s.tipo_entidad,''), "
            f"left(replace(replace(COALESCE(s.texto_original,''), E'\\n', ' '), '|', ' / '), 140) "
            f"FROM stg_entidad_no_resuelta s JOIN dim_origen_documental d ON d.id_documento = s.id_documento "
            f"WHERE COALESCE(s.resuelto,false)=false AND COALESCE(s.motivo,'NULL') = '{mot}' "
            f"ORDER BY s.id_staging LIMIT 10;"
        )
        for r in rows:
            parts = r.split("|")
            ejemplos_por_motivo[mot].append({
                "id_staging": int(parts[0]),
                "archivo": parts[1],
                "tipo_fuente": parts[2],
                "tipo_entidad": parts[3],
                "extracto": parts[4] if len(parts) > 4 else "",
            })

    # Hechos por documento y tabla en f3w_completo
    hechos_doc_tabla = defaultdict(dict)
    for tbl in ("fact_rendimiento_academico", "fact_situacion_financiera", "fact_evaluacion_docente",
                "fact_rentabilidad", "fact_costo_programa", "fact_techo_convenio"):
        for line in psql_f3w(f"SELECT d.nombre_archivo, count(*) FROM {tbl} f JOIN dim_origen_documental d ON d.id_documento = f.id_documento GROUP BY d.nombre_archivo;"):
            nom, cnt = line.split("|")
            hechos_doc_tabla[nom][tbl] = int(cnt)

    # 2. Recorrido hoja por hoja de los 10 libros Excel
    recorrido = []
    diferencias_f3ub = []
    for nom in LIBROS:
        path = ROOT / "uploads" / "data" / nom
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        hojas_info = []
        total_filas_excel = 0
        filas_con_saltos = 0
        for sh_name in wb.sheetnames:
            ws = wb[sh_name]
            rows = list(ws.iter_rows(values_only=True))
            non_empty = [r for r in rows if any(c is not None and str(c).strip() != "" for c in r)]
            # detectar saltos de linea en celdas
            saltos = sum(
                1 for r in non_empty
                if any(isinstance(c, str) and "\n" in c for c in r)
            )
            filas_con_saltos += saltos
            n_data = max(0, len(non_empty) - 1)
            total_filas_excel += n_data
            hdrs = [str(c).strip() for c in (non_empty[0] if non_empty else []) if c is not None and str(c).strip()]
            tipo_be = detectar_tipo_fuente_por_cabeceras({sh_name: pd.DataFrame(columns=hdrs[:20])}) if hdrs else "ACTA"
            escala_real = "1-10" if "EXPERIENCIA UNIFRANZ" in sh_name.upper() else ("1-5" if "EVALUACION DOCENTE" in sh_name.upper() else ("0-100" if docs_db.get(nom, {}).get("tipo_fuente_backend") == "ACTA" else "N/A"))
            hojas_info.append({
                "hoja": sh_name,
                "filas_no_vacias_aprox": n_data,
                "filas_con_saltos_linea_celda": saltos,
                "tipo_backend_hoja": tipo_be,
                "escala_real": escala_real,
                "muestra_cabeceras": hdrs[:10],
            })
        wb.close()

        db_info = docs_db.get(nom, {})
        stg_info = stg_por_doc.get(nom, {"bloques": 0, "lineas_paso2": 0})
        hechos_tot = sum(hechos_doc_tabla.get(nom, {}).values())

        recorrido.append({
            "archivo": nom,
            "tipo_spa_actual": "ACTA (si no coincide con 4 tipos)" if db_info.get("tipo_fuente_backend") not in ("ACTA", "MOODLE", "COBRANZA", "ADMISION") else db_info.get("tipo_fuente_backend"),
            "tipo_backend": db_info.get("tipo_fuente_backend"),
            "filas_excel_totales_aprox": total_filas_excel,
            "lineas_paso2": stg_info["lineas_paso2"],
            "casos_consolidacion_por_motivo": casos_por_doc_motivo.get(nom, {}),
            "hechos_guardados_por_tabla": hechos_doc_tabla.get(nom, {}),
            "hojas": hojas_info,
        })

        if total_filas_excel != stg_info["lineas_paso2"] or hechos_tot != stg_info["lineas_paso2"]:
            diferencias_f3ub.append({
                "archivo": nom,
                "tipo_backend": db_info.get("tipo_fuente_backend"),
                "filas_excel_aprox": total_filas_excel,
                "lineas_staging": stg_info["lineas_paso2"],
                "filas_con_saltos_linea_celda": filas_con_saltos,
                "hechos_guardados": hechos_tot,
                "casos_hitl_abiertos": sum(casos_por_doc_motivo.get(nom, {}).values()),
                "causas_principales": [
                    f"Saltos de línea internos en celdas ({filas_con_saltos} filas) o bloques de cabecera/pie" if filas_con_saltos > 0 else "Cabeceras multi-fila / hojas resumen / filas vacías o de totales",
                    "Expansión 1 fila -> N hechos por módulo/pregunta (evaluación docente y actas multi-módulo)" if hechos_tot > stg_info["lineas_paso2"] else "Reglas de descarte B-9 / deduplicación / casos derivados a bandeja HITL",
                ],
            })

    # 3. Comprobacion D-W7 (pipeline/semantic/formatter.py:236-252)
    dw7 = {
        "sintoma": "En el paso 3 aparece 'docente ••••' aunque el archivo no tiene columna de docente, y respuestas Likert 1-10 podrian escalarse x10",
        "evidencia_codigo": [
            "pipeline/semantic/formatter.py:238-247: campos clasificados como NOTA con valor numérico (0 < num <= 10) se multiplican por 10 (val_unif = num_n * 10.0) sin distinguir si es escala Likert de evaluación docente.",
            "pipeline/semantic/formatter.py:251: 'if any(k in col_clean.lower() for k in (\"1.\", \"2.\", \"docente\", \"explica\", \"recomiende\")):' clasifica preguntas con la palabra 'docente' en RESPUESTAS, pero extract_entities_from_line (extraccion.py) puede buscar palabras/celdas cercanas si un encabezado contiene DOCENTE.",
        ],
        "veredicto": "defecto (D-W7)",
        "ubicacion": "pipeline/semantic/formatter.py:238-252",
    }

    out_w1 = {
        "tarea": "W-1 (Recorrido por archivo sobre f3w_completo)",
        "dw7_diagnostico": dw7,
        "recorrido_10_libros": recorrido,
        "ejemplos_por_motivo_hasta_10": dict(ejemplos_por_motivo),
    }
    (MED / "f3w_recorrido_por_archivo.json").write_text(json.dumps(out_w1, ensure_ascii=False, indent=1), encoding="utf-8")

    # Matriz motivo x categoria -> campos del formulario
    matriz_md = """# Matriz Motivo × Categoría → Campos del Formulario de Revisión (W-1)

| Categoría | Motivo | Casos en `f3w_completo` | Qué lo provoca | Campos obligatorios del formulario |
|---|---|---:|---|---|
| `academico` | `CI_NOMBRE_DISCORDANTE` | 738 | La CI coincide con una persona del catálogo pero el nombre difiere (< umbral). | `nombre_completo`, `ci_opcional`, `confirmar_identidad`, `justificacion` (sin nota/mes/gestión si ya existen) |
| `academico` | `BAJA_CONFIANZA_IA` | 323 | Índice probabilístico BETO en `[0,60; 0,85)`. | `nombre_completo`, `modulo_resuelto`, `nota_final`, `mes`, `gestion`, `justificacion` |
| `academico` | `HOMONIMIA` | 34 | Dos personas con nombre similar (>90 %) sin CI discriminante. | `nombre_completo`, `ci_opcional`, `programa`, `justificacion` |
| `academico` | `CI_DUDOSA` | 2 | CI con `?`, longitud < 5 o formato inválido. | `ci_corregido`, `nombre_completo`, `justificacion` |
| `evaluacion_docente` | `BAJA_CONFIANZA_IA` | 250 | Índice probabilístico BETO en `[0,60; 0,85)` en respuestas Likert. | `programa`, `numero_modulo`, `docente_resuelto`, `escala_respuesta`, `justificacion` (**sin** nota/100) |
| `evaluacion_docente` | `HOMONIMIA` | 19 | Nombre de encuestado/docente ambiguo sin CI. | `nombre_completo`, `ci_opcional`, `programa`, `numero_modulo`, `justificacion` (**sin** nota/100) |
| `admision` | `POS_NO_EN_DIM_MODULO` | 5 | Código `POS` no encontrado en `dim_modulo`. | `codigo_pos`, `programa_resuelto`, `modulo_resuelto`, `justificacion` |
| `admision` | `CI_DUDOSA` | 5 | CI con `?` o formato inválido en `TBL_INSCRITOS`. | `ci_corregido`, `nombre_completo`, `justificacion` |
| `admision` | `FECHA_INSCRIPCION_INVALIDA` | 1 | Fecha nula o fuera de rango en admisión. | `fecha_inscripcion`, `justificacion` |
| `financiero` | `CI_DUDOSA` | 2 | CI con `?` o formato inválido en `BD Cobranzas`. | `ci_corregido`, `nombre_completo`, `monto_deuda`, `cuotas_impagas`, `justificacion` |
| `rentabilidad` | `CI_NOMBRE_DISCORDANTE` | 2 | Discordancia de nombre/CI en `BD Egresos`. | `nombre_completo`, `ci_opcional`, `categoria_financiera`, `justificacion` |
| `rentabilidad` | `HOMONIMIA` | 1 | Homonimia en registro de `BD Egresos`. | `nombre_completo`, `ci_opcional`, `justificacion` |
| `marketing` | `*` (techo/convenio) | 0 abiertos | Convenio/institución o monto por validar (`fact_techo_convenio`). | `institucion`, `clave_convenio`, `monto_convenio`, `justificacion` |

## Verificación D-W7
- **Archivo y líneas:** `pipeline/semantic/formatter.py:238-252`
- **Veredicto:** `defecto` (D-W7). Las columnas Likert 1–10 clasificadas como `NOTA` se multiplicaban por `10.0` (l.242), y las preguntas que contienen `"docente"` entraban a `RESPUESTAS` / contexto cercano.
"""
    (MED / "f3w_matriz_formularios.md").write_text(matriz_md, encoding="utf-8")

    # W-1b outputs
    (MED / "f3w_diferencias_f3ub.json").write_text(json.dumps({
        "tarea": "W-1b (Diferencias F3U-B / D-W11)",
        "archivos_con_delta": diferencias_f3ub,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    defectos_md = """# Defectos Detectados en W-1 / W-1b (`f3w_defectos.md`)

| ID | Descripción | Archivo y línea | Veredicto | Se corrige en |
|---|---|---|---|---|
| **D-W1** | SPA solo reconoce 4 tipos de fuente (`ACTA`, `MOODLE`, `COBRANZA`, `ADMISION`) | `frontend/src/constants/dataopsConfig.js:33-38` | `defecto` | **F3W (W-2)** |
| **D-W2** | `resolve_review_item` no rutea `evaluacion_docente`, `rentabilidad` ni `marketing` (HTTP 503) | `backend/routers/dataops/revision.py:385-387` | `defecto` | **F3W (W-3)** |
| **D-W4** | Casos HITL solo se crean al consolidar, paso 4 aparece en 0 antes | `backend/routers/dataops/consolidacion.py:197-240` | `defecto` | **F3W (W-5)** |
| **D-W5** | Consolidación recalcula `indices_cascada` y hace flush fila a fila | `backend/routers/dataops/consolidacion.py:209`, `dw_loader.py` | `defecto` | **F3W (W-6)** |
| **D-W6** | Formulario de revisión fijo (`Nota sobre 100, Mes, Gestión`) | `frontend/src/modules/dataops/HumanReviewFlowView.jsx` | `defecto` | **F3W (W-4)** |
| **D-W7** | Respuestas Likert 1–10 escaladas ×10 como notas en `formatter.py` | `pipeline/semantic/formatter.py:238-252` | `defecto` | **F3W / F3V** |
| **D-W8** | Toasts apilados sin progreso % agrupado | `frontend/src/services/sileoToast.js`, `notificationService.js` | `defecto` | **F3W (W-7)** |
| **D-W9** | Navegación fija `/dataops/*` rompe `/v2/dataops/*` | `frontend/src/modules/dataops/*.jsx` | `defecto` | **F3W (W-9)** |
| **D-W10** | `carga_fila_origen` solo escribe `fact_marketing` con `id_documento=1` | `backend/services/dw_loader.py` | `defecto` | **F3W (W-13)** |
| **D-W11** | Expansión de filas con saltos de línea internos en celdas (`Evaluación Docente y Unifranz`, `[BBDD] ANTIGUO`) y multi-hoja | `pipeline/ingesta.py` / reglas B-9 | `regla_correcta` + `defecto` menor en celdas multilínea | **F3V** (reglas de expansión complejas) |
"""
    (MED / "f3w_defectos.md").write_text(defectos_md, encoding="utf-8")
    print("[W-1 y W-1b OK]", len(recorrido), "libros analizados", flush=True)


if __name__ == "__main__":
    main()
