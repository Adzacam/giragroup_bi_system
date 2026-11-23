# PLAN F3Y — 2026-11-19
Objetivo de la fase: medir y congelar los pronósticos que el docx usa y la SFV todavía no tiene: Holt-Winters sobre 33 meses de operación regular (principal), sobre 43 meses (sensibilidad) y naive estacional (referencia), y OLS mensual de recaudación (N = 40).
Entrada: `PLAN_F5.md` (decisiones 1 y 2), SFV congelada en F3V; rama `beto-integracion` `595e40f`. Sin cambios en el código del sistema.

## Decisión de Lean (19-nov)
1. **Holt-Winters principal = 33 meses de operación regular (2023-09 a 2026-05).** Criterio declarado **antes del resultado**: se excluye la fase piloto (2022-11 a 2023-08) porque es un cambio de nivel del arranque, no estacionalidad. Los 43 meses quedan como **sensibilidad** y el naive estacional como **referencia**.
2. **OLS mensual de recaudación (N = 40):** se mide porque es un invariante («OLS mensual N = 40») y el docx la usa.

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| Y-1 | **HW 33 meses.** Sobre la copia del snapshot (sha `14D45F5A…E2EB`, sin cambios), serie `fact_marketing.inscritos` 2023-09 a 2026-05, con el mismo procedimiento de `f3r_hw_matricula.json` (statsmodels, tendencia aditiva amortiguada, m = 12, hold-out de 6 meses, `simulacion_param_aditivo_n1000` para los intervalos). Ajuste de validación con 27 meses → métricas en el hold-out; ajuste de producción con 33 meses → proyección de 6 meses con IC 80/95 | dev-media | — | Y-2, Y-3 | 1) α, β, γ, φ, RMSE, AIC, MAPE y RMSE en el hold-out, cobertura empírica del IC 80/95 y proyección con sus intervalos; 2) la serie usada mes a mes en el JSON; 3) dos corridas con el mismo resultado (semilla fija) | `f3y_hw_33m.json` |
| Y-2 | **Sensibilidad y referencia.** (a) HW 43 meses con el mismo código y las mismas particiones que Y-1, que debe reproducir `f3r_hw_matricula.json` (Δ = 0) o explicar la diferencia (el docx citaba 15,31 % y la SFV 15,67 %). (b) Naive estacional (ŷ_t = y_{t−12}) sobre el mismo hold-out de 6 meses. (c) Tabla comparativa de las tres | dev-media | — | Y-1, Y-3 | 1) 43 meses = SFV o diferencia explicada con archivo:línea; 2) MAPE y RMSE del naive; 3) tabla de 3 filas en el JSON | `f3y_hw_sensibilidad.json` |
| Y-3 | **OLS mensual de recaudación.** `forecasting_ols.py` sobre `fact_rentabilidad` (PROGRAMAS) del snapshot, N = 40 (2023-01 a 2026-04): pendiente, intercepto, R², p, RMSE y MAPE en el hold-out si el script lo calcula | dev-baja | — | Y-1, Y-2 | 1) N = 40 confirmado con la lista de meses; 2) métricas con su ruta en el JSON | `f3y_ols_mensual.json` |
| Y-4 | **SFV.** La Tabla E.1 pasa a HW 33 meses como principal, con filas de sensibilidad (43) y referencia (naive). Se agrega la OLS mensual a la Tabla E.2. Nota metodológica: la exclusión de la fase piloto como criterio previo. `f3_sfv_trazabilidad.json` y `verificar_sfv.py` | dev-media | Y-1…Y-3 | — | 1) `verificar_sfv.py` **0/0/0**; 2) el texto no presenta el 33 como elegido por su MAPE; 3) el naive figura como referencia que supera a HW, como limitación | `f3y_sfv_verificacion.txt` |
| Y-5 | **Figura.** El chat 4 rehace el Gráfico 3.4 con la serie de 33 meses, la proyección y el IC (y los 10 meses piloto en gris, marcados como «fase piloto, fuera del ajuste») | chat 4 | Y-4 | — | cada valor = valor del JSON | `docs/figuras/f4/grafico_3_4_serie_temporal_holt_winters.png` |

## Comandos y control
- Copia del snapshot en tmpfs, como en R3-6; el sha del dump se verifica antes y después. Nada contra la DW viva.
- Script nuevo de medición `scripts/f3y_pronosticos.py`, que solo lee la base. No se cambia `pipeline/analytics/`.
- Si Y-1 da parámetros degenerados (α = β = γ = 0) o un MAPE peor que con 43 meses, **se reporta igual**. El criterio ya está fijado y no se cambia por el resultado.

## Al cerrar
Commit `docs(f3y): pronósticos HW 33/43, naive y OLS mensual` · `CIERRE_F3Y.md` · el chat 1 revisa y re-anuncia «F3 congelado (con F3Y)» al chat 3, que aplica PLAN_F5 con estas cifras.

## PROMPT PARA CHAT 2
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F3Y.md (base `beto-integracion` 595e40f). Solo medición sobre la copia del snapshot; sin cambios en backend/, pipeline/ ni frontend/.
Decisión: HW principal = 33 meses (2023-09 a 2026-05), con la exclusión de la fase piloto como criterio previo; 43 meses como sensibilidad; naive estacional como referencia; OLS mensual de recaudación N = 40.
Orden: Y-1, Y-2 e Y-3 en paralelo → Y-4 (SFV 0/0/0). Y-5 lo hace el chat 4. Escribe CIERRE_F3Y.md.
