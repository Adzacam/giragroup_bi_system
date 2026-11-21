"""ADW L0-2/L0-3: escribe adw_l0_cifras_web.csv y adw_l0_cruce_web_dw.csv.
Las cifras visibles se transcribieron de las capturas de docs/mediciones/adw_l0_capturas/ (sesión del 2026-11-20).
Uso: python -I scripts/auditoria_dw/generar_l0_web.py <web_kpi.txt con lineas gestion|codigo|estado|valor>"""
import csv
import sys

kpi = [l.rstrip("\n").split("|") for l in open(sys.argv[1], encoding="utf-8") if l.strip()]
rows = [("CMI", "Perspectivas estratégicas", g, k, f"valor={v}; estado={e}") for g, k, e, v in kpi]
rows += [("CMI", "Perspectivas estratégicas", g, "ÍNDICE", x) for g, x in [
    ("2026", "32,4 Crítico (Fin 28 · EyM 20 · PI 20 · AyC 60)"),
    ("2025", "65,7 En alerta (68 · 60 · 60 · 73,3)"),
    ("2024", "60,9 En alerta (52 · 60 · 60 · 73,3)"),
    ("2023", "20 Crítico (20 · — · — · —)")]]
rows += [
    ("CMI", "Analítica predictiva", "2026", "Serie longitudinal", "N = 33 meses (2023-09 – 2026-05)"),
    ("CMI", "Analítica predictiva", "2026", "Inscritos proyectados 6 M", "4812 (IC 95 %: 3641–5983)"),
    ("CMI", "Analítica predictiva", "2026", "MAPE hold-out 6 M / RMSE", "14,06 % / 99,57"),
    ("CMI", "Analítica predictiva", "2026", "Cumplimiento proyectado del mes (dic-2026)", "136 %"),
    ("CMI", "Analítica predictiva", "2026", "Avance de la meta anual", "31,4 %"),
    ("Académico", "Alertas tempranas (/academico/rendimiento)", "2024-2026", "Matrícula activa auditada", "10.327 alumnos"),
    ("Académico", "Alertas tempranas", "2024-2026", "Riesgo académico (promedio ≤ 70)", "1.363 (13,2 %)"),
    ("Académico", "Alertas tempranas", "2024-2026", "Riesgo deserción (incumplimiento > 30 %)", "0 (0,0 %)"),
    ("Académico", "Alertas tempranas", "2024-2026", "Riesgo financiero (mora ≥ 2 cuotas)", "1.440 alumnos · Bs 903.179"),
    ("Académico", "Alertas tempranas", "2024-2026", "Alerta crítica (2 o más reglas)", "107 (A+F = 107; D+F = 0; A+D = 0)"),
    ("Académico", "Alertas tempranas", "2024-2026", "Registros en alerta", "2.696"),
    ("Académico", "Desempeño docente", "todas", "Docentes registrados", "100 (lista 1–5 de 100)"),
    ("Académico", "Desempeño docente", "todas", "Evaluaciones registradas", "67.109"),
    ("Académico", "Desempeño docente", "todas", "Satisfacción estudiantil", "3,28"),
    ("Académico", "Desempeño docente", "todas", "Primer docente de la lista (DOC-111)", "Nombre = texto de un comentario; ★ 1,75 (24)"),
    ("Académico", "Catálogo curricular", "todas", "Módulos registrados / calidad curricular", "4.319 / 100 % con código POS canónico"),
    ("Académico", "Catálogo curricular", "todas", "Primeras filas", "Módulos llamados «0», «1» y «2025-06-24 17:59:00» (MOD-GEN)"),
    ("Académico", "Proyección de alumnos", "todas", "Tendencia OLS / MAPE / RMSE", "7,2687 al/mes / 14,06 % / 99,57"),
    ("Financiero", "Recaudación", "2026", "Recaudación neta registrada", "Bs 5.309.447,68"),
    ("Financiero", "Recaudación", "2026", "Cartera vencida exigible", "Bs 4.832.610,08"),
    ("Financiero", "Recaudación", "2026", "Cumplimiento presupuestario", "31,4 %"),
    ("Financiero", "Cartera y mora", "todas", "Estudiantes en mora (≥ 2 cuotas)", "1.440 (13,9 % de la matrícula auditada)"),
    ("Financiero", "Cartera y mora", "todas", "Saldo exigible en mora", "Bs 903.179,09"),
    ("Financiero", "Cartera y mora", "todas", "Recaudación consolidada DW", "Bs 0"),
    ("Financiero", "Metas", "2026", "Meta global de gestión", "Bs 16.894.995"),
    ("Financiero", "Metas", "2026", "Recaudación acumulada / desviación presupuestaria", "Bs 5.309.448 (31,4 %) / Bs -11.585.547"),
    ("Financiero", "Metas", "2026", "Programas en meta / viables", "25 / 25"),
    ("Financiero", "Proyección", "2026", "Meta mes actual / cierre proyectado HW / meta anual", "Bs 99.196 / Bs 134.951 (12 %) / Bs 16.894.995"),
    ("DataOps", "Carga de archivos", "todas", "Historial de lotes", "3 lotes (#36 y #35 En revisión; #1 Consolidado); columna «Registros» = 0 en los tres"),
    ("DataOps", "Revisión lote 35", "2024-2026", "Casos pendientes (paso ③)", "1.403"),
    ("DataOps", "Lectura de BETO lote 1", "2025", "Registros del lote / Analizados", "1.721 / 0"),
    ("Auditoría", "Trazabilidad", "todas", "Total eventos / lotes / alertas críticas / 2FA", "400 / 205 lotes / 0 / 0 logs"),
    ("Reportes", "Centro de reportes", "todas", "Exportaciones registradas", "0 eventos"),
]
with open("docs/mediciones/adw_l0_cifras_web.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["modulo", "pantalla", "gestion", "cifra", "valor_visible"])
    w.writerows(rows)

D = "adw_l0_cruce_dw_valores.csv"
cruce = [
    ("CMI", "23 KPI × 4 gestiones (92 celdas)", "varios", "valor de bi.vw_cmi_scorecard", "IGUAL en 92/92", "adw_l0_cruce_kpi_web_dw.csv", "El CMI lee la vista; las incoherencias nacen aguas arriba (A1–A12)", "—"),
    ("CMI", "Serie de la analítica predictiva", "N = 33 (2023-09–2026-05)", "fact_marketing con inscritos > 0: 43 meses (2022-11–2026-05); desde 2023-01: 41", "DIFIERE", "invariante CLAUDE.md: OLS mensual N = 40", "Tres cifras distintas de N; verificar cuál se congeló", "A22 · 🟠"),
    ("CMI", "Avance de la meta anual (predictiva)", "31,4 %", "KPI-13 = 31,7 % (5.695.043,78 / 17.973.400); 31,42 % solo con PROGRAMAS", "DIFIERE", "adw_l0_rentabilidad.csv", "La web financiera usa solo la categoría PROGRAMAS; el CMI suma PROGRAMAS + TECHOS_CERRADOS", "B3/A21 · 🔴"),
    ("Académico", "Alertas · matrícula activa auditada", "10.327", "10.327 = estudiantes distintos con hecho académico o financiero (todas las gestiones)", "IGUAL en valor, falsa en nombre", D, "No es matrícula activa; KPI-21 da 3.773 (2024) y 3.571 (2025)", "A16 · 🟠"),
    ("Académico", "Alertas · riesgo académico", "1.363", "1.385 en bi.vw_riesgo_estudiante (regla A)", "DIFIERE", D, "Filtros de periodo distintos o motor distinto (KPIService)", "B3 · 🟠"),
    ("Académico", "Alertas · riesgo deserción", "0", "0 (asistencia NULL e incumplimiento 0)", "IGUAL, pero 0 por falta de dato", "adw_l0_academico.csv", "Mismo origen que A2", "A2 · 🔴"),
    ("Académico", "Alertas · riesgo financiero", "1.440 · Bs 903.179", "249 alumnos / Bs 260.904 (vista); 1.431 alumnos con ≥ 2 cuotas", "DIFIERE", D, "Tres conteos de la misma regla", "B3 · 🔴"),
    ("Académico", "Alertas · alerta crítica", "107", "78 (k_reglas ≥ 2 en la vista) = KPI-17 2025", "DIFIERE", D, "Pantalla y CMI se contradicen", "B3 · 🔴"),
    ("Académico", "Docente · docentes", "100", "dim_docente 689; 450 con evaluaciones válidas", "DIFIERE", D, "La lista muestra 100 de 689 o filtra sin avisar", "A19 · 🟠"),
    ("Académico", "Docente · evaluaciones registradas", "67.109", "449.586 con puntuación ≥ 1 (715.217 filas)", "DIFIERE", "adw_l0_evaluacion.csv", "Contador no reproducible; revisar KPIService", "A19 · 🟠"),
    ("Académico", "Docente · satisfacción", "3,28", "4,088 (media de las puntuaciones válidas en escala 5)", "DIFIERE", D, "Incluye los 0 de A1", "A1 · 🔴"),
    ("Académico", "Docente · nombre DOC-111", "un comentario completo", "43 docentes con nombre de más de 60 caracteres", "CONFIRMADO", D, "Textos de comentarios entraron como docentes en dim_docente", "A14 · 🔴"),
    ("Académico", "Catálogo · calidad curricular", "100 % con código POS canónico", "4.319 con pos_code, pero 634 son MOD-GEN* y 3 tienen nombre numérico o fecha", "DIFIERE", D, "La métrica no mide lo que dice; el catálogo tiene entradas basura", "A15 · 🟠"),
    ("Financiero", "Recaudación neta", "Bs 5.309.447,68", "5.309.447,68 solo con PROGRAMAS; 5.695.043,78 con todas las categorías", "IGUAL solo con PROGRAMAS", "adw_l0_rentabilidad.csv", "Alcance distinto al del CMI", "A21 · 🟠"),
    ("Financiero", "Cartera vencida exigible", "Bs 4.832.610,08", "= deuda total de todas las gestiones y estados (4.832.610,08); mora o previsionable 4.317.472,24; con ≥ 2 cuotas 529.816,81", "IGUAL a la deuda total: mal etiquetada", "adw_l0_cartera.csv", "No es cartera vencida", "A17 · 🔴"),
    ("Financiero", "Cartera · estudiantes en mora ≥ 2", "1.440", "1.431 estudiantes distintos", "DIFIERE (9)", D, "Filas frente a alumnos", "A3 · 🟠"),
    ("Financiero", "Cartera · saldo en mora", "Bs 903.179,09", "Bs 529.816,81 (suma de monto_deuda de filas con ≥ 2 cuotas)", "DIFIERE", D, "Probable deuda total de esos alumnos; confirmar en L4", "A3 · 🟠"),
    ("Financiero", "Cartera · recaudación consolidada DW", "Bs 0", "monto_pagado = 26.172.122,73 en 10.733 filas", "DIFIERE", D, "Tarjeta rota o leyendo una fuente vacía", "A18 · 🔴"),
    ("Financiero", "Metas · meta global 2026", "Bs 16.894.995", "17.973.400 con todas las categorías; 16.894.995 solo PROGRAMAS", "IGUAL solo con PROGRAMAS", "adw_l0_rentabilidad.csv", "Igual que A21", "A21 · 🟠"),
    ("Financiero", "Metas · desviación presupuestaria", "Bs -11.585.547", "= ejecutado − meta anual completa (5.309.448 − 16.894.995)", "IGUAL a esa resta", "adw_l0_rentabilidad.csv", "Compara 5 meses con 12; «déficit» engañoso", "A4 · 🟠"),
    ("Financiero", "Metas · programas en meta", "25 / 25", "No existe en la DW (viabilidad de programas, no meta)", "NO CRUZABLE", "—", "Etiqueta confusa", "— · 🟡"),
    ("DataOps", "Historial de lotes · Registros", "0 en los 3 lotes", "lote 1 = 1.721 registros; lotes 35 y 36 con datos", "DIFIERE", "adw_l0_tareas.csv", "Columna vacía", "— · 🟡"),
    ("DataOps", "Revisión lote 35 · pendientes", "1.403", "1.403 en stg_entidad_no_resuelta (lote 35); 1.413 en total = KPI-18", "IGUAL", "adw_l0_staging.csv", "Coherente", "—"),
    ("DataOps", "Lectura de BETO · lote 1", "Analizados 0 con 1.721 registros", "tarea 2 procesó 1.721; tareas 45, 47 y 49 en ERROR", "DIFIERE", "adw_l0_tareas.csv", "Efecto visible de C1 y D3", "C1 · 🔴"),
    ("Auditoría", "Origen documental y lotes", "205 lotes", "lote = 3; dim_origen_documental = 10", "DIFIERE", D, "El contador no sale de las tablas de lote", "A23 · 🟠"),
    ("Auditoría", "Seguridad & 2FA", "0 logs", "no verificable en esta DW (el servicio de autenticación tiene su base)", "NO CRUZABLE", "—", "Se inició sesión con 2FA hoy y el contador sigue en 0", "A24 · 🟡"),
    ("Auditoría", "Eventos «Revelación de NOMBRE/CI/CORREO»", "registrados como «Resolución HITL: Validación de Entidad»", "log_auditoria_nlp 12.336 = 12.332 + 4 revelaciones", "CONFIRMADO", D, "Mezcla revelaciones de PII con resoluciones HITL (ligado a D2)", "D2 · 🟠"),
    ("Reportes", "Bitácora de exportaciones", "0 eventos", "sin tabla equivalente consultada", "NO CRUZABLE", "—", "Sin hallazgo", "—"),
]
with open("docs/mediciones/adw_l0_cruce_web_dw.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["modulo", "cifra_web", "valor_web", "valor_dw", "resultado", "evidencia", "comentario", "hallazgo"])
    w.writerows(cruce)
print(len(rows), "cifras;", len(cruce), "cruces;", sum(1 for c in cruce if c[4].startswith("DIFIERE")), "difieren")
