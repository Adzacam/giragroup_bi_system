# AVISO AL CHAT 3 — cifras que cambian por la auditoría ADW (2026-11-21)
**Estado: NO CONGELADO.** ADW no recongela `docs/fuente_verdad_tesis.md` todavía: faltan FU-L3 a FU-L9 (inscritos y KPI-06, ARCA y deserción, encuestas, metas y recarga completa). Cuando la recarga termine, los 23 KPI cambiarán y se congelan una sola vez.

## Ya cambió en el código (con evidencia)
| Cifra | Antes | Ahora | Fuente / archivo |
|---|---|---|---|
| Pendiente OLS anual (E-09, J2-04) | +2.436.141,68 Bs/año | +2.360.251,66 Bs/año | `docs/mediciones/adw_da8_forecast_antes.json` / `_despues.json` |
| CAGR histórico (E-09, J2-04) | 26,76 % | 22,85 % | idem |
| Meta anual 2026 | 16.894.995 Bs | 17.973.400 Bs | idem (DA8: todas las categorías) |
| Recaudado acumulado 2026 | 5.309.447,68 Bs | 5.695.043,78 Bs | idem |
| Avance de meta 2026 | 31,4 % | 31,7 % (= KPI-13) | idem |
| RMSE Caso 3 (Holt-Winters metas) | 252.859,49 | 297.317,61 | idem |
| Calidad NLP del módulo pipeline | ≈ 99,6 % | 92,87 % | `CIERRE_ADW_L5.md` |

## Valores que NO han cambiado aún en la DW viva (los 23 KPI)
`docs/mediciones/adw_l9_comparacion_l0.csv`: 92 de 92 celdas iguales a L0. Cambiarán con la recarga (KPI-05, 15, 04 por mora DA3; KPI-06; KPI-16; KPI-07, 08; KPI-19, 20; KPI-21; KPI-02 de 2024 → sin dato).

## Correcciones a lo que la auditoría afirmaba
- C1 (tareas BETO del lote 1 en ERROR): era contaminación de pytest, ya corregida.
- B5 (caché BETO sin migración 015): premisa falsa; la tabla se crea sola y los flags van apagados.
- «Reservas lleno» en marketing: es 0 en todas las gestiones.
- Las 5 filas BAJA_CONFIANZA del doc 44 no son vacías (índice 0,0000).
- Serie predictiva: la pantalla usa N = 33 y la DW tiene 43 meses; el invariante dice N = 40 (por revisar antes de congelar).
