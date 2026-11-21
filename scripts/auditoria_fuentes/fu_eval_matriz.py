"""
FU-B2 · Genera docs/mediciones/fu_eval_matriz_decisiones.csv y .md
consolidando las 62 hojas de uploads/data a partir de fu_l0_hojas.csv y fu_l1_hojas_clasificadas.csv (0 PII).
"""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MED = ROOT / "docs" / "mediciones"

ARCHIVO_INFO = {
    "BD Cobranzas.xlsx": (
        "COBRANZA",
        "fact_situacion_financiera / dim_estudiante",
        "Cartera mapeada por substring MORA; cuotas_impagas desde DIAS_DE_MORA; pagos por año de inicio en lugar de MONTO <MES> <AÑO>; 82.734 fórmulas sin valor",
        "Filas válidas de COBRANZAS 2024 2025: TIPO DE CARTERA, TOTAL CUOTAS EN MORA (>=2 = mora), pagos mensuales MONTO <MES> <AÑO>",
        "Hoja oculta Copia de COBRANZAS (5.478), hojas auxiliares Hoja 4/8/12 (533), columnas (PRELIMINAR), cuotas negativas (-5) -> 0",
        "SÍ: VALOR_FUERA_DE_CATALOGO (estado cartera desconocido), CI_NOMBRE_DISCORDANTE, CI_DUDOSA | NO (informativo): CUOTAS_NEGATIVAS, HOJA_IGNORADA",
    ),
    "Base centralizada Académica ARCA (1).xlsx": (
        "ACTA",
        "fact_rendimiento_academico / dim_modulo / fact_marketing",
        "Notas con texto/CI (13.622.300) y 2.968 ceros por inasistencia; IBP descartada como LINEA_SIN_ENTIDAD; estados sin normalizar; CI con complemento en texto",
        "ACTAS DE NOTAS (8.660), MODULOS (2.030), IBP (748 -> leads/inscritos 2026)",
        "Tabla dinámica 1 / Hoja 8 (vacías), PROGRMAS DE BAJA (1 fila), CRITERIOS (15 filas texto), notas >100 y textos no catálogo -> NULL",
        "SÍ: NOTA_FUERA_DE_RANGO (>100), VALOR_FUERA_DE_CATALOGO (nota texto no catálogo), CI_NOMBRE_DISCORDANTE | NO: HOJA_IGNORADA, INASISTENCIA/EXIMIDO/SIN_NOTA",
    ),
    "[BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx": (
        "EVALUACION_DOCENTE",
        "fact_evaluacion_docente",
        "Celdas combinadas (7.265/1.002), respuestas cruzadas entre columnas (10.751 total doc 40-41), 0/Sin Información promediado",
        "TBL EVALUACION DOCENTE (16.451) y TBL EXPERIENCIA UNIFRANZ (2.539) con escala 1-5/1-10 y diccionario etiquetas",
        "Análisis de Evaluación (129 filas casi vacías, cabecera dispersa), 0/Sin Información -> NULL, duplicados",
        "SÍ: RESPUESTA_EN_COLUMNA_EQUIVOCADA (agrupado), VALOR_FUERA_DE_CATALOGO (agrupado), PUNTUACION_FUERA_DE_ESCALA | NO: SIN_INFORMACION, HOJA_IGNORADA",
    ),
    "Evaluación Docente y Unifranz.xlsx": (
        "EVALUACION_DOCENTE",
        "fact_evaluacion_docente",
        "DIP. EXP DOC. X MODULO (3.250 válidas) descartada entera como LINEA_SIN_ENTIDAD (adaptar_moodle_df); etiquetas sin número",
        "DIP. EXP DOC. X MODULO (52.975 resp.), DIP. EXP UNIFRANZ (285), FINAL EXPERTOCURSO (275)",
        "1.076 filas fantasma (845+231), 0/Sin Información -> NULL, NPS separado",
        "SÍ: RESPUESTA_EN_COLUMNA_EQUIVOCADA (agrupado), VALOR_FUERA_DE_CATALOGO, PUNTUACION_FUERA_DE_ESCALA, ESCALA_NO_INFERIBLE | NO: SIN_INFORMACION",
    ),
    "Experiencia Docente 2.0.xlsx": (
        "EVALUACION_DOCENTE",
        "fact_evaluacion_docente",
        "Clasificado como ACTA/CENTESIMAL_100; doble columna (texto+número) duplicaba hechos 2x; 0/Sin Información cargado (77.902 total)",
        "DIPLOMADOS DOCENTE (14.397) y CURSOS DOCENTE (828) leyendo solo columna numérica",
        "Hojas ocultas CURSOS DOC 1 (994) y DIPLOMADOS DOC 2 (1.476), columnas texto de pares (198.801+11.592), 0/Sin Información -> NULL",
        "SÍ: VALOR_FUERA_DE_CATALOGO (1.255 comentarios cortos agrupados), PUNTUACION_FUERA_DE_ESCALA | NO: SIN_INFORMACION (77.902), HOJA_IGNORADA",
    ),
    "TBL_INSCRITOS.xlsx": (
        "MARKETING",
        "fact_marketing / dim_estudiante",
        "Doble paso por FactMarketing y doble clave carga_fila_origen duplicaba inscritos 2x (30.392 vs 15.196); 5 filas vacías con confianza 0,0000",
        "TBL_INSCRITOS (15.196 inscripciones únicas 1:1)",
        "BAJAS POR DUPLICADOS (oculta, 0 filas), 4 columnas ...L 100% vacías, 5 filas vacías confianza 0,0000",
        "SÍ: CI_DUDOSA, CI_NOMBRE_DISCORDANTE | NO: 5 filas vacías confianza 0,0000 (descartadas), HOJA_IGNORADA",
    ),
    "BD Egresos.xlsx": (
        "EGRESOS",
        "fact_rentabilidad",
        "Diferencias de 100.000 frente a EJECUTADO VS META generaban 10 CONFLICTO_FUENTES pendientes; hoja acumulados con texto Bs",
        "egresos (1.373) y Gestiones (24) para costos/egresos; ejecutado/meta subordinado a RENTABILIDAD",
        "acumulados (12 filas texto Bs...), fecha año 2580 fuera de rango",
        "NO (informativo): CONFLICTO_FUENTES resuelto automáticamente por prioridad RENTABILIDAD > EGRESOS, HOJA_IGNORADA",
    ),
    "EJECUTADO VS META.xlsx": (
        "RENTABILIDAD",
        "fact_rentabilidad",
        "Meta 2024 en celda única anual colocada en dic-2024 (KPI-02=6,25%); mes parcial may-2026 distorsionaba KPI-02; 10 CONFLICTO_FUENTES",
        "EJECUTADO (24 filas): fuente prioritaria para monto_meta y monto_ejecutado; granularidad_meta ANUAL vs MENSUAL",
        "GESTIONES (8 filas texto Bs...), 2 cols sin nombre con residuos -9.3e-10",
        "NO (informativo): CONFLICTO_META / CONFLICTO_FUENTES resuelto por regla (7 múltiplos de 100.000 señalados), HOJA_IGNORADA",
    ),
    "BD Techos.xlsx": (
        "TECHOS",
        "fact_marketing / fact_rentabilidad",
        "40,6% sin id_institucion; fecha inicio 2034; variantes de nombre ECOGUZ",
        "BD Techos (207 filas, alimenta KPI-22)",
        "1.783 filas vacías de cola",
        "SÍ: POS_NO_EN_DIM_MODULO / ENTIDAD_NUEVA si aplica | NO: filas vacías",
    ),
    "PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx": (
        "PLANIFICACION",
        "fact_planificacion_programa / fact_marketing / dim_meta",
        "Hojas ocultas/borradores duplicaban datos; Jun/Dic-2026 con >970 filas fantasma; leads/inscritos (KPI-06) no se extraían",
        "Hojas mensuales Jul-2025..Dic-2026 (ocultas Jul-Dic 2025 rescatadas sin duplicado visible), Programas Notificados (1.045), Informe Gestión (58 metas)",
        "Centralizado_Mensual, borradores (*borrador/*boor), Dashboards, Julio..Diciembre antiguas, Detalle Presupuestado-Proyectad, 3.084 filas fantasma, 8 subtotales",
        "SÍ: HECHO_EN_REVISION si falta fecha/programa | NO: HOJA_IGNORADA (16 hojas ignoradas), subtotales/filas fantasma",
    ),
}


def main() -> None:
    l0 = {(r["archivo"], r["hoja"]): r for r in csv.DictReader((MED / "fu_l0_hojas.csv").open(encoding="utf-8"))}
    l1 = list(csv.DictReader((MED / "fu_l1_hojas_clasificadas.csv").open(encoding="utf-8")))

    out_rows = []
    for r in l1:
        arch, hoja = r["archivo"], r["hoja"]
        p0 = l0.get((arch, hoja), {})
        tipo_canon, tabla_dw, falla, si_ins, no_ins, rev_hum = ARCHIVO_INFO[arch]
        dec = r["decision"]
        if dec == "ignorar":
            si_hoja = "NO (hoja ignorada)"
            no_hoja = f"{r['regla']}: {r['motivo']} (filas_raw={p0.get('n_filas_datos', 0)})"
            rev_hoja = "NO va a bandeja pendiente: registrada como HOJA_IGNORADA (informativo)"
        else:
            si_hoja = f"{r['filas_leidas']} filas -> {tabla_dw} ({si_ins})"
            no_hoja = f"fantasma={r['filas_fantasma_cortadas']}, subtotales={r['subtotales_cortados']}; {no_ins}"
            rev_hoja = rev_hum
        out_rows.append({
            "archivo": arch,
            "hoja": hoja,
            "estado_visibilidad": r["estado"],
            "tipo_fuente_canonico": tipo_canon,
            "decision_hoja": dec,
            "regla_hoja": r["regla"],
            "filas_raw": p0.get("n_filas_datos", "0"),
            "filas_leidas": r["filas_leidas"],
            "filas_fantasma_cortadas": r["filas_fantasma_cortadas"],
            "subtotales_cortados": r["subtotales_cortados"],
            "formulas_sin_valor": r["formulas_sin_valor"],
            "falla_pipeline_beto": falla,
            "si_debe_insertarse": si_hoja,
            "no_debe_insertarse": no_hoja,
            "revision_humana_si_vs_no": rev_hoja,
        })

    csv_path = MED / "fu_eval_matriz_decisiones.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    md_lines = [
        "# Matriz de Evaluación de `uploads/data` (FU-B2)",
        "",
        "Consolidado de solo lectura sobre las **62 hojas** de los **10 libros** de `uploads/data` (evidencias `fu_l0`..`fu_l6`, 0 PII).",
        "",
        "- **Total hojas:** 62 (`36 usar`, `26 ignorar`) · **Filas leídas:** 78.005 · **Filas fantasma cortadas (usadas):** 3.084 · **Subtotales cortados (usadas):** 8.",
        "- **Criterio de revisión humana:** van a bandeja pendiente únicamente casos accionables (`CI_NOMBRE_DISCORDANTE`, `CI_DUDOSA`, `HOMONIMIA`, `NOTA_FUERA_DE_RANGO`, `RESPUESTA_EN_COLUMNA_EQUIVOCADA`, `VALOR_FUERA_DE_CATALOGO` agrupado, `PUNTUACION_FUERA_DE_ESCALA`, `ESCALA_NO_INFERIBLE`); quedan **fuera de bandeja pendiente** (solo informativo o descartado): `HOJA_IGNORADA`, `SIN_INFORMACION` (77.902), `CONFLICTO_FUENTES`/`CONFLICTO_META` resuelto por regla (10), `CUOTAS_NEGATIVAS` corregido a 0 y las 5 filas vacías con confianza `0,0000` (doc 44).",
        "",
        "## Resumen por tipo de fuente y archivo",
        "",
        "| Archivo | Tipo | Hojas (Usar/Ignorar) | Qué falla en pipeline/BETO | Qué SÍ se inserta | Qué NO se inserta | Qué SÍ vs NO va a revisión humana |",
        "|---|---|---|---|---|---|---|",
    ]
    by_arch = defaultdict(list)
    for r in out_rows:
        by_arch[r["archivo"]].append(r)
    for arch, items in by_arch.items():
        n_u = sum(1 for x in items if x["decision_hoja"] == "usar")
        n_i = sum(1 for x in items if x["decision_hoja"] == "ignorar")
        tipo, _, falla, si_ins, no_ins, rev = ARCHIVO_INFO[arch]
        md_lines.append(f"| `{arch}` | {tipo} | {len(items)} ({n_u}/{n_i}) | {falla} | {si_ins} | {no_ins} | {rev} |")

    md_lines += [
        "",
        "## Detalle por hoja (62 hojas)",
        "",
        "| Archivo | Hoja | Estado | Decisión | Regla | Leídas | Fantasma | Subtotales | Revisión humana |",
        "|---|---|---|---|---|---:|---:|---:|---|",
    ]
    for r in out_rows:
        md_lines.append(
            f"| `{r['archivo']}` | {r['hoja']} | {r['estado_visibilidad']} | {r['decision_hoja']} | {r['regla_hoja']} | "
            f"{r['filas_leidas']} | {r['filas_fantasma_cortadas']} | {r['subtotales_cortados']} | {r['revision_humana_si_vs_no']} |"
        )

    (MED / "fu_eval_matriz_decisiones.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print("Wrote", len(out_rows), "rows to fu_eval_matriz_decisiones.csv and .md")


if __name__ == "__main__":
    main()
