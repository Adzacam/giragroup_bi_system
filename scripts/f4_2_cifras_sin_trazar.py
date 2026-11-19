# -*- coding: utf-8 -*-
"""
scripts/f4_2_cifras_sin_trazar.py
=================================
Tarea F4-2 de PLAN_F4.md:
Auditoría y dictamen de cifras sin trazar para Gráficos 3.5, 4.5 y 4.6.
Genera docs/mediciones/f4_cifras_sin_trazar.json.
"""

import json
import pathlib

auditoria = {
    "fecha": "2026-11-18",
    "tarea": "F4-2",
    "descripcion": "Auditoría de figuras con cifras potenciales sin respaldo estricto en la SFV",
    "analisis": [
        {
            "figura": "Gráfico 3.5 (OLS matrícula mensual N = 33)",
            "archivo_f3": "docs/figuras/f3/grafico_3_5_ols_matricula.png",
            "cifras_revisadas": {
                "n_observaciones": 33,
                "pendiente": "+3,6541 est./mes",
                "intercepto": 329.72,
                "r2": 0.1921,
                "p_valor": 0.0107
            },
            "busqueda_en_docs_mediciones": {
                "encontrado": False,
                "detalle": "No existe ningún archivo en docs/mediciones/ con los valores 3.6541, 329.72 ni 0.1921. Los valores se calcularon al vuelo en scripts/graficos_tesis_v2.py desde data/reproducibilidad/graficos/inscritos.csv."
            },
            "busqueda_en_sfv": {
                "encontrado": False,
                "detalle": "Citaba erróneamente 'E-14' en la SFV, pero la Sección E de docs/fuente_verdad_tesis.md solo abarca de E-01 a E-11. No existe trazabilidad en la SFV para OLS de matrícula N=33."
            },
            "estado_invariante": "Invariante declara 'OLS mensual N = 40; OLS anual solo descriptiva' (recaudación).",
            "veredicto": "retirar",
            "accion": "El Gráfico 3.5 se retira de la entrega oficial de figuras de F4. No se incluye en FIGURAS_F4.md como figura activa y se documenta en la sección de figuras retiradas."
        },
        {
            "figura": "Gráfico 4.5 (Tiempo de consolidación semilogarítmico)",
            "archivo_f3": "docs/figuras/f3/grafico_4_5_tiempo_consolidacion_semilog.png",
            "cifras_revisadas": {
                "pretest_manual": "600,0 min (8-12 h)",
                "maquina_vacia_s": "424,29 s (7,07 min)",
                "klm_w_medido_s": "320,6 s (5,34 min)",
                "total_postest_s": "744,89 s (12,41 min)",
                "reduccion_pct": "-97,9 % (Δ = -587,59 min)"
            },
            "busqueda_en_docs_mediciones": {
                "encontrado": True,
                "detalle": "Postest medido 100% trazado en docs/mediciones/f3v_b7_corridas.json (resumen.vacia_maquina_s, resumen.vacia_mas_klm_s) y docs/mediciones/f3v_klm.json (W_medido.klm_s)."
            },
            "busqueda_en_sfv": {
                "encontrado": True,
                "detalle": "Postest en SFV A-23, A-26, A-27. Pretest manual (600,0 min) respaldado en SFV J2-15 con etiqueta DATO_DE_LEAN."
            },
            "veredicto": "trazada",
            "accion": "Se conserva en la entrega con pie aclaratorio de que el pretest constituye un dato de línea base institucional (SFV J2-15)."
        },
        {
            "figura": "Gráfico 4.6 (Evaluación Likert pretest vs postest)",
            "archivo_f3": "docs/figuras/f3/grafico_4_6_evaluacion_likert_pre_post.png",
            "cifras_revisadas": {
                "muestra_participantes": "N = 10",
                "dimensiones": 9,
                "media_global_pretest": 1.89,
                "media_global_postest": 4.62
            },
            "busqueda_en_docs_mediciones": {
                "encontrado": True,
                "detalle": "Mencionada en docs/mediciones/f3r_mapa_j.json (J2-14)."
            },
            "busqueda_en_sfv": {
                "encontrado": True,
                "detalle": "Respaldada en docs/fuente_verdad_tesis.md ítem J2-14 con etiqueta DATO_DE_LEAN (Evaluación humana externa fuera del código)."
            },
            "veredicto": "trazada",
            "accion": "Se conserva en la entrega con nota explícita indicando que proviene de la evaluación de usabilidad externa de Lean (J2-14)."
        }
    ],
    "resumen_decisiones": {
        "figuras_conservadas": 2,
        "figuras_retiradas": 1,
        "lista_retiradas": ["Gráfico 3.5 (OLS de matrícula mensual N = 33)"]
    }
}

out_path = pathlib.Path("docs/mediciones/f4_cifras_sin_trazar.json")
out_path.write_text(json.dumps(auditoria, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[OK] Generado {out_path}.")
