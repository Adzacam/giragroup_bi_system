# Ronda 10 — datos para cerrar la tesis (cifras de ejecuciones reales)

## Tabla única de cifras
| Cifra | Valor | Evidencia |
|---|---|---|
| pytest | 475 passed, 0 failed, 11 skipped, 7 xfailed (ronda 9: 464) | pytest_junit.xml, pytest_completo_final.txt |
| Cobertura global | 60,8 % (8.049 de 13.249 sentencias) | cobertura.json |
| Cobertura de los 22 archivos clave, ponderada | 58,3 % (3.832 de 6.571) | cobertura_por_modulo.json |
| Cobertura de `forecasting_holtwinters` | 52 % → 95,8 % (9 pruebas nuevas) | cobertura_por_modulo.json |
| Holt-Winters, MAPE medio de origen móvil (12 orígenes, h = 1..6) | actual 21,49 ± 9,54 → amortiguado **16,88 ± 8,64** (adoptado) | holtwinters_origen_movil.json |
| Lote 1.387: directo / HITL / staging | 1.353 (97,55 %) / 34 (2,45 %) / 0; dos corridas idénticas | lote_1387_uploads_data_arquitectura_b.json |
| Lote 1.387: excepciones detectadas | 562 entidades en 268 de 1.387 registros; **0 habrían entrado al DW sin control** | idem, bloque `excepciones` |
| Prueba de formato Google Forms (35 filas) | directo 35 / HITL 0 / staging 0 | prueba_formato_Inscripciones_Google_Forms_TEST.json |
| Prueba de formato Moodle (35 filas) | directo 35 / HITL 0 / staging 0 | prueba_formato_Reporte_Aula_Virtual_Moodle_TEST.json |
| `fact_rendimiento_academico` con `incumplimiento_actividades_pct` > 0 | 0 de 22.618 (todas con 0,00; todas del archivo ARCA) | consulta al DW real |
| DW real: `fact_rendimiento_academico` / `fact_situacion_financiera` | 22.618 / 10.483 filas (559 y 3 en revisión) | foto_dw_real_ronda10.txt |
| Staging pendiente | 1.044: CI_NOMBRE_DISCORDANTE 756, BAJA_CONFIANZA_IA 288 | idem |
| F1 micro gold_510: arquitectura B / BETO solo (C) | 100,00 % / 97,57 % | f1_beto_fp32_gold_510.json |
| F1 micro layouts_5: arquitectura B / BETO solo (C) | 31,58 % (relajado 71,64 %) / 24,68 % (relajado 69,23 %) | f1_beto_fp32_layouts_5.json |

## 1. Cobertura por archivo y módulo funcional (una corrida)
`cobertura_por_modulo.json`. Sentencias, no cubiertas y %:
| Módulo | Archivo | Sent. | Sin cubrir | % |
|---|---|---|---|---|
| **Infraestructura y RBAC: 87,4 %** (76/87) | core/security.py | 87 | 11 | 87,4 |
| **Ingesta: 61,3 %** (360/587) | services/ingestion_service.py | 587 | 227 | 61,3 |
| **PLN y resolución: 69,7 %** (518/743) | semantic/ner_engine.py | 301 | 108 | 64,1 |
| | semantic/indice_confianza.py | 70 | 47 | 32,9 |
| | services/confianza_service.py | 87 | 38 | 56,3 |
| | normalization/fk_resolver.py | 89 | 11 | 87,6 |
| | normalization/fuzzy_normalizer.py | 71 | 12 | 83,1 |
| | normalization/person_resolver.py | 125 | 9 | 92,8 |
| **API, alertas y pronóstico: 57,2 %** (1.135/1.984) | services/dw_loader.py | 870 | 483 | 44,5 |
| | routers/pipeline.py | 269 | 173 | 35,7 |
| | services/alert_engine.py | 71 | 6 | 91,5 |
| | services/financial_rules_engine.py | 85 | 2 | 97,6 |
| | services/risk_service.py | 337 | 19 | 94,4 |
| | analytics/forecasting_holtwinters.py | 71 | 3 | 95,8 |
| | analytics/forecasting_ols.py | 28 | 0 | 100,0 |
| | services/forecast_service.py | 253 | 163 | 35,6 |
| **Plataforma, CMI y HITL: 55,0 %** (1.743/3.170) | routers/dataops.py | 2.176 | 1.234 | 43,3 |
| | services/bandeja_grupos.py | 149 | 7 | 95,3 |
| | services/revision_hechos.py | 210 | 25 | 88,1 |
| | services/kpi_service.py | 374 | 121 | 67,6 |
| | routers/reportes.py | 261 | 40 | 84,7 |

La asignación de archivos a módulos es mía (el enunciado no la fija): `ner_engine` e `indice_confianza` van en PLN; `dw_loader` y `routers/pipeline` en API.

## 2. Holt-Winters
a) `tests/test_holtwinters_cobertura.py`: motor nativo NumPy, respaldo si falla statsmodels, ausencia de statsmodels, índices de periodo y fecha, huecos, cotas a cero y validaciones. 52 % → 95,8 %.

b y c) Origen móvil sobre la serie mensual de inscritos de `fact_marketing` (DW real, 43 meses, 2022-11 a 2026-05; los dos primeros meses son de arranque). Orígenes: los últimos 12 meses; h = 1..6 truncado a los meses con dato real (los 5 últimos orígenes tienen menos de 6 pasos). MAPE por origen y luego media ± DE (n-1) entre orígenes:
| Modelo | MAPE medio ± DE | MAPE agrupado (todos los pasos) |
|---|---|---|
| Actual (aditivo, tendencia sin amortiguar) | 21,49 ± 9,54 | 23,07 |
| **HW amortiguado** | **16,88 ± 8,64** | 19,16 |
| HW sobre log(1+y) | 64,06 ± 24,35 | 67,03 |
| SARIMA pequeño por AIC (cuadrícula de 48 órdenes por origen; casi siempre (1,0,1)(0,1,1)12) | 18,52 ± 10,37 | 19,82 |
| Referencia: naive estacional (no era candidato) | 14,07 ± 6,63 | 15,42 |

Decisión: el amortiguado mejora el MAPE medio del actual (−4,6 puntos), así que se adoptó (`damped_trend=True`). Lectura honesta: la DE entre orígenes (≈ 9) es del tamaño de la mejora y los orígenes se solapan, así que la ventaja no es concluyente; además el naive estacional supera a los cuatro modelos, lo que indica que con 43 meses la tendencia aporta poco. La banda ±1,96·RMSE sigue siendo constante en h (hallazgo HW-IC, sin cambios).

## 3. Excepciones del lote 1.387 (reemplazan «107 de 1.414»)
El lote se evalúa con el arnés `reejecutar_lote_1387_uploads_data.py` (lectura, cascada A/B, BETO y resolución de personas contra el DW real). Cifras de 2 corridas idénticas. Una «excepción» es una entidad que el arnés no deja pasar como persona o como hecho normal:
| Regla | Entidades | Registros | Destino |
|---|---|---|---|
| ETIQUETA_LIKERT («5/Totalmente de acuerdo» leído como persona) | 283 | 110 | descarte por regla |
| CORREO_NO_ES_NOMBRE | 139 | 139 | descarte por regla |
| COLUMNA_DE_COMENTARIO | 87 | 87 | descarte por regla |
| PER_SIN_FORMA_NOMBRE | 48 | 48 | log (`log_inconsistencias`, 48 filas DESCARTADO) y descarte; 26 hechos se quedaron sin persona y van a HITL |
| PERSONA_SIN_COINCIDENCIA | 5 | 5 | HITL |
| **Total** | **562** | **268** | descarte 509 · log+descarte 48 · HITL 5 |

Habrían ingresado sin control: **0** (se verificó: toda excepción que exigía HITL tiene su registro fuera de la banda directo). Límite: las tres reglas de descarte (Likert, correo, comentario) no escriben fila en `log_inconsistencias`; el descarte está en el código, no en el log. El total difiere de «107 de 1.414» porque aquella cifra no está en el repositorio y no la pude reproducir. El lote da 1.353/34 (antes 1.354/33) porque el arnés compara contra el DW vivo, que creció desde la ronda 6.

## 4. Distribución por archivo del lote 1.387 (Gráfico 4.3)
| Archivo | Registros | Directo | HITL | Staging |
|---|---|---|---|---|
| Base centralizada Académica ARCA | 450 | 448 (99,56 %) | 2 (0,44 %) | 0 |
| BD Cobranzas | 350 | 349 (99,71 %) | 1 (0,29 %) | 0 |
| TBL_INSCRITOS | 250 | 248 (99,20 %) | 2 (0,80 %) | 0 |
| Evaluación Docente y Unifranz | 150 | 137 (91,33 %) | 13 (8,67 %) | 0 |
| Experiencia Docente 2.0 | 110 | 95 (86,36 %) | 15 (13,64 %) | 0 |
| BD Egresos | 53 | 53 (100 %) | 0 | 0 |
| EJECUTADO VS META | 24 | 23 (95,83 %) | 1 (4,17 %) | 0 |
Staging es 0 en todos: el arnés del lote no deriva a staging (una persona sin candidatos se crea como miembro nuevo).

## 5. Google Forms y Moodle
a) De los 10 archivos del ciclo, solo **TBL_INSCRITOS.xlsx** tiene evidencia de Google Forms: su primera columna es `MARCA TEMPORAL` seguida de los campos del formulario (hojas TBL_INSCRITOS y BAJAS POR DUPLICADOS). Los archivos de evaluación (Evaluación Docente y Unifranz, Experiencia Docente 2.0, [BBDD] ANTIGUO RESPUESTAS) tienen las columnas `Nombre completo del usuario`, `Grupos`, `Dirección de correo`, que son de una actividad de Moodle, no de Google Forms. Es una inferencia por las cabeceras: los .xlsx están anonimizados y no traen metadatos de origen.
b) **Prueba de formato** (no son datos de producción), cada archivo por separado con `/api/v1/pipeline/process` sobre un clon del DW: Google Forms, 35 filas → directo 35 / HITL 0 / staging 0 (las 35 filas van a `fact_marketing`: +34 filas, +35 inscritos); Moodle, 35 filas → directo 35 / HITL 0 / staging 0 (35 filas en `fact_rendimiento_academico`: 31 aprobados, 4 reprobados). Los clones se eliminaron.
c) `incumplimiento_actividades_pct` no es nulo en las 22.618 filas de `fact_rendimiento_academico`, pero porque la columna tiene valor por defecto 0,00: **ninguna** tiene un valor mayor que cero. Todas vienen del archivo Base centralizada Académica ARCA. La alerta de deserción (umbral > 30 %) **no tiene datos reales**. El CSV de Moodle de prueba tampoco alimenta la columna (queda en 0,00).

## 6. Umbrales de RapidFuzz
`umbrales_rapidfuzz.md`: personas con CI exacta; sin CI, score = máx(token_sort, token_set) ≥ 0,92 con bloqueo módulo → programa → dimensión, apellido obligatorio y ≥ 2 tokens en común; en la carga, variante de nombre ≥ 85, homónimos ≥ 90, docente ≥ 85 y módulo ≥ 80.

## 7. Foto del DW real
`foto_dw_real_ronda10.txt`: `fact_rendimiento_academico` 22.618 filas (559 en revisión), `fact_situacion_financiera` 10.483 (3 en revisión); staging pendiente 1.044 (CI_NOMBRE_DISCORDANTE 756, BAJA_CONFIANZA_IA 288).

## 8. F1 micro (fp32, código final)
| Conjunto | Modo | Precisión | Recall | F1 micro | F1 relajado |
|---|---|---|---|---|---|
| gold_510 | A (reglas) | 1,0000 | 1,0000 | 1,0000 | 1,0000 |
| gold_510 | **B (final)** | 1,0000 | 1,0000 | **1,0000** | 1,0000 |
| gold_510 | **C (BETO solo)** | 0,9691 | 0,9824 | **0,9757** | 0,9912 |
| layouts_5 | A | 0,9167 | 0,1528 | 0,2619 | 0,2857 |
| layouts_5 | **B (final)** | 0,3000 | 0,3333 | **0,3158** | 0,7164 |
| layouts_5 | **C (BETO solo)** | 0,2317 | 0,2639 | **0,2468** | 0,6923 |
Reproduce los valores de la ronda 6. En gold_510 las reglas resuelven todas las entidades (fuente BETO 0 en A y B), por eso 100 %: no mide a BETO; BETO solo da 97,57 %. layouts_5 es el conjunto adverso (5 diseños no vistos).

## 9. Pruebas
475 pasadas (suites: sprint1 16, sprint2 32, sprint3 120, sprint4 23, loops 9, readiness 39 con 21 pasadas, 11 omitidas y 7 xfail, transversales 254); 0 fallidas. Cambio en una aserción, con motivo: `test_banda_95_se_ensancha_con_el_horizonte` (xfail estricto) dio un XPASS falso tras adoptar el amortiguado, porque comparaba anchos de banda iguales con ruido de coma flotante de 1e-14; ahora compara los anchos redondeados a 2 decimales. El defecto que documenta (banda constante) sigue y la prueba vuelve a xfail.

## Límites
Tiempo de revisión humana no medido (sin cambios). El lote 1.387 depende del estado del DW vivo. Quedan sin commit `scripts/diccionario_datos_csv.py`, `docs/evidencias/diccionario_datos.csv` y `diccionario_datos.csv` de la raíz (cambios anteriores, no revisados).
