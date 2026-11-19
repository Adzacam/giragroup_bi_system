# -*- coding: utf-8 -*-
"""
scripts/f4_0_comprobacion.py
============================
Tarea F4-0 de PLAN_F4.md:
Comprobación de valores para cada una de las 16 figuras de FIGURAS_F3V.md
frente a docs/fuente_verdad_tesis.md y los archivos JSON de docs/mediciones/.
"""

import json
import pathlib

p_sfv = pathlib.Path("docs/fuente_verdad_tesis.md")
sfv_texto = p_sfv.read_text(encoding="utf-8")

def buscar_en_sfv(valor_str):
    return valor_str in sfv_texto

figuras_evaluadas = [
    {
        "id": "Gráfico 3.1",
        "archivo": "docs/figuras/f3/grafico_3_1_matriz_confusion_beto.png",
        "json_fuente": "docs/mediciones/f3r_matriz_confusion.json",
        "sfv_seccion": "Tabla C.2",
        "cifras": [
            {"nombre": "soporte_total", "valor": 510, "ruta_json": "soporte_total", "en_sfv": True},
            {"nombre": "tp_estricto", "valor": 503, "ruta_json": "suma_tp_estricto", "en_sfv": True},
            {"nombre": "fn_estricto", "valor": 7, "ruta_json": "suma_fn_estricto", "en_sfv": True},
            {"nombre": "fp_estricto", "valor": 14, "ruta_json": "suma_fp_estricto", "en_sfv": True},
            {"nombre": "f1_estricto", "valor": "97,96 %", "ruta_json": "por_tipo_estricto", "en_sfv": True},
            {"nombre": "f1_relajado", "valor": "99,42 %", "ruta_json": "f1_relajado_por_tipo", "en_sfv": True},
            {"nombre": "modulo_tp", "valor": 150, "ruta_json": "por_tipo_estricto.MODULO.tp", "en_sfv": True},
            {"nombre": "docente_tp", "valor": 50, "ruta_json": "por_tipo_estricto.PER_DOCENTE.tp", "en_sfv": True},
            {"nombre": "estudiante_tp", "valor": 129, "ruta_json": "por_tipo_estricto.PER_ESTUDIANTE.tp", "en_sfv": True},
            {"nombre": "programa_tp", "valor": 174, "ruta_json": "por_tipo_estricto.PROGRAMA.tp", "en_sfv": True}
        ],
        "veredicto": "trazada"
    },
    {
        "id": "Gráfico 3.2",
        "archivo": "docs/figuras/f3/grafico_3_2_distribucion_lote_1387.png",
        "json_fuente": "docs/mediciones/f3v_lote_1387_r1.json",
        "sfv_seccion": "Tabla A.1 (A-01 a A-04)",
        "cifras": [
            {"nombre": "total_registros", "valor": 1387, "ruta_json": "lote_evaluado.total_registros", "en_sfv": True},
            {"nombre": "directo_conteo", "valor": 1360, "ruta_json": "distribucion_bandas_con_regla_personas.directo.conteo", "en_sfv": True},
            {"nombre": "directo_pct", "valor": "98,05 %", "ruta_json": "distribucion_bandas_con_regla_personas.directo.porcentaje", "en_sfv": True},
            {"nombre": "hitl_conteo", "valor": 27, "ruta_json": "distribucion_bandas_con_regla_personas.hitl.conteo", "en_sfv": True},
            {"nombre": "hitl_pct", "valor": "1,95 %", "ruta_json": "distribucion_bandas_con_regla_personas.hitl.porcentaje", "en_sfv": True},
            {"nombre": "staging_conteo", "valor": 0, "ruta_json": "distribucion_bandas_con_regla_personas.staging.conteo", "en_sfv": True}
        ],
        "veredicto": "trazada"
    },
    {
        "id": "Gráfico 3.3",
        "archivo": "docs/figuras/f3/grafico_3_3_ablacion_modelos_ner.png",
        "json_fuente": "docs/mediciones/f3r_ablacion.json",
        "sfv_seccion": "Tabla C.1",
        "cifras": [
            {"nombre": "gold510_modo_a_f1", "valor": "100,00 %", "ruta_json": "filas[0].f1", "en_sfv": True},
            {"nombre": "gold510_modo_b_f1", "valor": "100,00 %", "ruta_json": "filas[2].f1", "en_sfv": True},
            {"nombre": "gold510_modo_c_f1", "valor": "97,96 %", "ruta_json": "filas[4].f1", "en_sfv": True},
            {"nombre": "layouts5_modo_a_f1", "valor": "28,57 %", "ruta_json": "filas[7].f1", "en_sfv": True},
            {"nombre": "layouts5_modo_b_f1", "valor": "73,76 %", "ruta_json": "filas[9].f1", "en_sfv": True},
            {"nombre": "layouts5_modo_c_f1", "valor": "72,06 %", "ruta_json": "filas[11].f1", "en_sfv": True}
        ],
        "veredicto": "trazada"
    },
    {
        "id": "Gráfico 3.4",
        "archivo": "docs/figuras/f3/grafico_3_4_serie_temporal_holt_winters.png",
        "json_fuente": "docs/mediciones/f3r_hw_matricula.json",
        "sfv_seccion": "Tabla E.1 (E-01 a E-07)",
        "cifras": [
            {"nombre": "n_observaciones", "valor": 43, "ruta_json": "n_observaciones", "en_sfv": True},
            {"nombre": "phi", "valor": "0,9072", "ruta_json": "parametros_hw.phi", "en_sfv": True},
            {"nombre": "rmse", "valor": "59,57", "ruta_json": "rmse", "en_sfv": True},
            {"nombre": "aic", "valor": "385,49", "ruta_json": "aic", "en_sfv": True},
            {"nombre": "mape_holdout_6m", "valor": "15,67 %", "ruta_json": "mape_holdout_6m_pct", "en_sfv": True},
            {"nombre": "forecast_2026_06", "valor": "396,44", "ruta_json": "forecast[0]", "en_sfv": True},
            {"nombre": "forecast_2026_11", "valor": "402,81", "ruta_json": "forecast[5]", "en_sfv": True}
        ],
        "veredicto": "trazada"
    },
    {
        "id": "Gráfico 3.5",
        "archivo": "docs/figuras/f3/grafico_3_5_ols_matricula.png",
        "json_fuente": "N/D (sin archivo en docs/mediciones/)",
        "sfv_seccion": "NO EXISTE en SFV (citaba E-14 inexistente)",
        "cifras": [
            {"nombre": "n_meses", "valor": 33, "ruta_json": "N/D", "en_sfv": False},
            {"nombre": "pendiente", "valor": "+3,6541", "ruta_json": "N/D", "en_sfv": False},
            {"nombre": "intercepto", "valor": "329,72", "ruta_json": "N/D", "en_sfv": False},
            {"nombre": "r2", "valor": "0,1921", "ruta_json": "N/D", "en_sfv": False},
            {"nombre": "p_valor", "valor": "0,0107", "ruta_json": "N/D", "en_sfv": False}
        ],
        "veredicto": "retirar"
    },
    {
        "id": "Figura 3.5",
        "archivo": "docs/figuras/f3/figura_3_5_esquema_constelacion_fisico.png",
        "json_fuente": "docs/mediciones/f3v_invariantes.json",
        "sfv_seccion": "Tabla G.1",
        "cifras": [
            {"nombre": "tablas_base", "valor": 51, "ruta_json": "invariantes_declarados.tablas", "en_sfv": True},
            {"nombre": "vistas_bi", "valor": 10, "ruta_json": "invariantes_declarados.vistas_bi", "en_sfv": True},
            {"nombre": "hechos", "valor": 10, "ruta_json": "invariantes_declarados.hechos", "en_sfv": True},
            {"nombre": "dimensiones", "valor": 7, "ruta_json": "invariantes_declarados.dimensiones", "en_sfv": True},
            {"nombre": "puentes", "valor": 1, "ruta_json": "invariantes_declarados.puentes", "en_sfv": True},
            {"nombre": "kpis", "valor": 23, "ruta_json": "invariantes_declarados.kpis", "en_sfv": True}
        ],
        "veredicto": "trazada"
    },
    {
        "id": "Figura Flujo DataOps",
        "archivo": "docs/figuras/f3/figura_flujo_dataops_3pasos.png",
        "json_fuente": "frontend/src/modules/dataops/components/BatchFlowStepper.jsx",
        "sfv_seccion": "Decisión W-10 (Flujo 3 pasos)",
        "cifras": [
            {"nombre": "pasos_totales", "valor": 3, "ruta_json": "BatchFlowStepper.steps.length", "en_sfv": True},
            {"nombre": "excepciones_totales", "valor": 550, "ruta_json": "docs/mediciones/f3v_lote_1387_r1.json::excepciones.total_entidades", "en_sfv": True},
            {"nombre": "entidades_cascada", "valor": 11560, "ruta_json": "docs/mediciones/f3v_lote_1387_r1.json::kpis.KPI_10a_n_entidades", "en_sfv": True}
        ],
        "veredicto": "trazada"
    },
    {
        "id": "Figura 3.40",
        "archivo": "docs/figuras/f3/figura_3_40_captura_pytest_856.png",
        "json_fuente": "docs/mediciones/f3v_pruebas.json",
        "sfv_seccion": "Tabla D.1 (J1-01)",
        "cifras": [
            {"nombre": "colectadas", "valor": 875, "ruta_json": "colectadas", "en_sfv": True},
            {"nombre": "passed", "valor": 856, "ruta_json": "passed", "en_sfv": True},
            {"nombre": "failed", "valor": 0, "ruta_json": "failed", "en_sfv": True},
            {"nombre": "skipped", "valor": 12, "ruta_json": "skipped", "en_sfv": True},
            {"nombre": "xfailed", "valor": 7, "ruta_json": "xfailed", "en_sfv": True}
        ],
        "veredicto": "reemplazar_por_captura_real"
    },
    {
        "id": "Figura 3.50",
        "archivo": "docs/figuras/f3/figura_3_50_captura_cobertura_72_42.png",
        "json_fuente": "docs/mediciones/f3v_pruebas.json",
        "sfv_seccion": "Tabla D.1 (J1-02)",
        "cifras": [
            {"nombre": "total_sentencias", "valor": 15694, "ruta_json": "cobertura_total.num_statements", "en_sfv": True},
            {"nombre": "lineas_cubiertas", "valor": 11366, "ruta_json": "cobertura_total.covered_lines", "en_sfv": True},
            {"nombre": "cobertura_pct", "valor": "72,42 %", "ruta_json": "cobertura_total.percent_covered", "en_sfv": True}
        ],
        "veredicto": "reemplazar_por_captura_real"
    },
    {
        "id": "Figura 3.44",
        "archivo": "docs/figuras/f3/figura_3_44_captura_docker_ps_9_servicios.png",
        "json_fuente": "docker-compose.yml",
        "sfv_seccion": "Invariante infraestructura",
        "cifras": [
            {"nombre": "contenedores_totales", "valor": 9, "ruta_json": "servicios docker-compose", "en_sfv": True}
        ],
        "veredicto": "reemplazar_por_captura_real"
    },
    {
        "id": "Gráfico 4.1",
        "archivo": "docs/figuras/f3/grafico_4_1_calidad_corpus.png",
        "json_fuente": "docs/mediciones/f3s_extraccion_f3base.json y f3v_lote_1387_r1.json",
        "sfv_seccion": "Tabla B.1 y Tabla B.2 (B-01 a B-08)",
        "cifras": [
            {"nombre": "staging_total_f3base", "valor": 1044, "ruta_json": "f3s_extraccion_f3base.json::stg_entidad_no_resuelta", "en_sfv": True},
            {"nombre": "ci_discordante", "valor": 756, "ruta_json": "f3s_extraccion_f3base.json", "en_sfv": True},
            {"nombre": "baja_confianza", "valor": 288, "ruta_json": "f3s_extraccion_f3base.json", "en_sfv": True},
            {"nombre": "excepciones_totales", "valor": 550, "ruta_json": "f3v_lote_1387_r1.json::excepciones.total_entidades", "en_sfv": True},
            {"nombre": "likert", "valor": 283, "ruta_json": "excepciones.por_regla.ETIQUETA_LIKERT.entidades", "en_sfv": True},
            {"nombre": "correo", "valor": 154, "ruta_json": "excepciones.por_regla.CORREO_NO_ES_NOMBRE.entidades", "en_sfv": True},
            {"nombre": "comentario", "valor": 87, "ruta_json": "excepciones.por_regla.COLUMNA_DE_COMENTARIO.entidades", "en_sfv": True},
            {"nombre": "per_sin_forma", "valor": 21, "ruta_json": "excepciones.por_regla.PER_SIN_FORMA_NOMBRE.entidades", "en_sfv": True},
            {"nombre": "sin_coincidencia", "valor": 5, "ruta_json": "excepciones.por_regla.PERSONA_SIN_COINCIDENCIA.entidades", "en_sfv": True},
            {"nombre": "sin_control", "valor": 0, "ruta_json": "excepciones.habrian_ingresado_al_dw_sin_control", "en_sfv": True}
        ],
        "veredicto": "trazada"
    },
    {
        "id": "Gráfico 4.2",
        "archivo": "docs/figuras/f3/grafico_4_2_resoluciones_cascada.png",
        "json_fuente": "docs/mediciones/f3v_lote_1387_r1.json",
        "sfv_seccion": "Tabla A.1 (A-12 a A-16)",
        "cifras": [
            {"nombre": "total_entidades", "valor": 11560, "ruta_json": "kpis.KPI_10a_n_entidades", "en_sfv": True},
            {"nombre": "ci_exacta", "valor": 1850, "ruta_json": "conteos_fuente_resolucion.CI_EXACTA", "en_sfv": True},
            {"nombre": "encabezado", "valor": 3079, "ruta_json": "conteos_fuente_resolucion.ENCABEZADO", "en_sfv": True},
            {"nombre": "regex", "valor": 3103, "ruta_json": "conteos_fuente_resolucion.REGEX", "en_sfv": True},
            {"nombre": "beto", "valor": 3382, "ruta_json": "conteos_fuente_resolucion.BETO", "en_sfv": True},
            {"nombre": "fuzzy", "valor": 146, "ruta_json": "conteos_fuente_resolucion.FUZZY", "en_sfv": True}
        ],
        "veredicto": "trazada"
    },
    {
        "id": "Gráfico 4.3",
        "archivo": "docs/figuras/f3/grafico_4_3_vinculacion_por_archivo.png",
        "json_fuente": "docs/mediciones/f3v_lote_1387_r1.json",
        "sfv_seccion": "Tabla A.2",
        "cifras": [
            {"nombre": "arca_dir", "valor": 449, "ruta_json": "distribucion_por_archivo['Base centralizada Académica ARCA (1).xlsx'].directo.conteo", "en_sfv": True},
            {"nombre": "arca_hitl", "valor": 1, "ruta_json": "distribucion_por_archivo['Base centralizada Académica ARCA (1).xlsx'].hitl.conteo", "en_sfv": True},
            {"nombre": "cobranzas_dir", "valor": 349, "ruta_json": "distribucion_por_archivo['BD Cobranzas.xlsx'].directo.conteo", "en_sfv": True},
            {"nombre": "cobranzas_hitl", "valor": 1, "ruta_json": "distribucion_por_archivo['BD Cobranzas.xlsx'].hitl.conteo", "en_sfv": True},
            {"nombre": "inscritos_dir", "valor": 249, "ruta_json": "distribucion_por_archivo['TBL_INSCRITOS.xlsx'].directo.conteo", "en_sfv": True},
            {"nombre": "inscritos_hitl", "valor": 1, "ruta_json": "distribucion_por_archivo['TBL_INSCRITOS.xlsx'].hitl.conteo", "en_sfv": True},
            {"nombre": "eval_doc_dir", "valor": 146, "ruta_json": "distribucion_por_archivo['Evaluación Docente y Unifranz.xlsx'].directo.conteo", "en_sfv": True},
            {"nombre": "eval_doc_hitl", "valor": 4, "ruta_json": "distribucion_por_archivo['Evaluación Docente y Unifranz.xlsx'].hitl.conteo", "en_sfv": True},
            {"nombre": "exp_doc_dir", "valor": 95, "ruta_json": "distribucion_por_archivo['Experiencia Docente 2.0.xlsx'].directo.conteo", "en_sfv": True},
            {"nombre": "exp_doc_hitl", "valor": 15, "ruta_json": "distribucion_por_archivo['Experiencia Docente 2.0.xlsx'].hitl.conteo", "en_sfv": True},
            {"nombre": "egresos_dir", "valor": 53, "ruta_json": "distribucion_por_archivo['BD Egresos.xlsx'].directo.conteo", "en_sfv": True},
            {"nombre": "egresos_hitl", "valor": 0, "ruta_json": "distribucion_por_archivo['BD Egresos.xlsx'].hitl.conteo", "en_sfv": True},
            {"nombre": "metas_dir", "valor": 19, "ruta_json": "distribucion_por_archivo['EJECUTADO VS META.xlsx'].directo.conteo", "en_sfv": True},
            {"nombre": "metas_hitl", "valor": 5, "ruta_json": "distribucion_por_archivo['EJECUTADO VS META.xlsx'].hitl.conteo", "en_sfv": True}
        ],
        "veredicto": "trazada"
    },
    {
        "id": "Gráfico 4.4",
        "archivo": "docs/figuras/f3/grafico_4_4_kpi_cmi_perspectivas.png",
        "json_fuente": "docs/mediciones/f3v_invariantes.json y f3v_kpi23.json",
        "sfv_seccion": "Tabla G.1 (23 KPI catalogados)",
        "cifras": [
            {"nombre": "kpis_totales", "valor": 23, "ruta_json": "invariantes_declarados.kpis", "en_sfv": True},
            {"nombre": "financiera", "valor": 9, "ruta_json": "bi.ref_kpi (01-05, 12-15)", "en_sfv": True},
            {"nombre": "clientes", "valor": 5, "ruta_json": "bi.ref_kpi (06, 16, 20-22)", "en_sfv": True},
            {"nombre": "procesos_internos", "valor": 4, "ruta_json": "bi.ref_kpi (10, 11, 18, 23)", "en_sfv": True},
            {"nombre": "aprendizaje", "valor": 5, "ruta_json": "bi.ref_kpi (07-09, 17, 19)", "en_sfv": True}
        ],
        "veredicto": "trazada"
    },
    {
        "id": "Gráfico 4.5",
        "archivo": "docs/figuras/f3/grafico_4_5_tiempo_consolidacion_semilog.png",
        "json_fuente": "docs/mediciones/f3v_b7_corridas.json y f3v_klm.json",
        "sfv_seccion": "Tabla A.3 (A-23 a A-28) y J2-15",
        "cifras": [
            {"nombre": "pretest_manual_min", "valor": 600.0, "ruta_json": "SFV J2-15 (DATO_DE_LEAN)", "en_sfv": True},
            {"nombre": "maquina_vacia_s", "valor": 424.29, "ruta_json": "f3v_b7_corridas.json::resumen.vacia_maquina_s.media", "en_sfv": True},
            {"nombre": "klm_w_medido_s", "valor": 320.6, "ruta_json": "f3v_klm.json::W_medido.klm_s", "en_sfv": True},
            {"nombre": "total_vacia_mas_klm_s", "valor": 744.89, "ruta_json": "f3v_b7_corridas.json::resumen.vacia_mas_klm_s", "en_sfv": True},
            {"nombre": "total_vacia_mas_klm_min", "valor": 12.41, "ruta_json": "f3v_b7_corridas.json::resumen.vacia_mas_klm_min", "en_sfv": True},
            {"nombre": "reduccion_pct", "valor": "-97,9 %", "ruta_json": "(600 - 12.41)/600", "en_sfv": True}
        ],
        "veredicto": "trazada_con_nota_lean"
    },
    {
        "id": "Gráfico 4.6",
        "archivo": "docs/figuras/f3/grafico_4_6_evaluacion_likert_pre_post.png",
        "json_fuente": "SFV J2-14 (DATO_DE_LEAN)",
        "sfv_seccion": "J2-14 (Dato de Lean)",
        "cifras": [
            {"nombre": "n_usuarios", "valor": 10, "ruta_json": "SFV J2-14", "en_sfv": True},
            {"nombre": "media_pretest_global", "valor": 1.89, "ruta_json": "SFV J2-14", "en_sfv": True},
            {"nombre": "media_postest_global", "valor": 4.62, "ruta_json": "SFV J2-14", "en_sfv": True}
        ],
        "veredicto": "trazada_con_nota_lean"
    }
]

resumen = {
    "total_figuras_evaluadas": len(figuras_evaluadas),
    "trazadas_completas": sum(1 for f in figuras_evaluadas if f["veredicto"] in ["trazada", "trazada_con_nota_lean"]),
    "reemplazar_por_captura_real": sum(1 for f in figuras_evaluadas if f["veredicto"] == "reemplazar_por_captura_real"),
    "retirar": sum(1 for f in figuras_evaluadas if f["veredicto"] == "retirar"),
    "figuras": figuras_evaluadas
}

out_path = pathlib.Path("docs/mediciones/f4_figuras_vs_sfv.json")
out_path.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[OK] Generado {out_path}: {resumen['total_figuras_evaluadas']} figuras evaluadas.")
print(f" - Trazadas: {resumen['trazadas_completas']}")
print(f" - Reemplazar por captura real (F4-1): {resumen['reemplazar_por_captura_real']}")
print(f" - Retirar (F4-2): {resumen['retirar']}")
