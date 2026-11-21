# CIERRE ADW-DA8 (continuación de L5) — 2026-11-20
Rama / commit: beto-integracion · commit `adw(DA8): …` (ver `git log`); solo mis archivos
Decisión (Lean, 2026-11-20): **meta y recaudación cuentan todas las categorías (PROGRAMAS + TECHOS_CERRADOS)**, como el CMI.
Hecho (máx. 10 líneas):
- `forecast_service.py` (`_SQL_META_VS_EJECUTADO`) y `pipeline/analytics/time_series_extractor.py` (`META_MENSUAL_PROGRAMAS`, `META_ANUAL`) ya no filtran por `PROGRAMAS`. La serie mensual toma por mes lo ejecutado si el mes tiene algún dato ejecutado y, si no, la meta (nunca mezcla ejecutado de una categoría con meta de otra). La clave `META_MENSUAL_PROGRAMAS` conserva su nombre.
- El avance de la meta anual de Recaudación y Metas pasa de 31,4 % a **31,7 %**, igual al KPI-13 del CMI.
- Pruebas nuevas en `tests/adw/test_l5_motor_unico.py`: el pronóstico suma todas las categorías y su avance coincide con el KPI-13; ninguna consulta de metas vuelve a filtrar solo PROGRAMAS.
- DA8 registrada en `PLAN_AUDITORIA_DW.md`.
Antes → después (copia tmpfs; `adw_da8_forecast_antes.json` / `_despues.json`):
| Cifra | Antes | Después |
|---|---|---|
| Meta anual 2026 (Bs) | 16.894.995 | 17.973.400 |
| Recaudado acumulado 2026 (Bs) | 5.309.447,68 | 5.695.043,78 |
| Avance de la meta | 31,4 % | 31,7 % |
| Pendiente anual OLS (Bs/año) | 2.436.141,68 | 2.360.251,66 |
| Cierre anual proyectado OLS (Bs) | 15.183.417,34 | 16.162.057,78 |
| CAGR histórico | 26,76 % | 22,85 % |
| RMSE, Caso 3 (Holt-Winters mensual) | 252.859,49 | 297.317,61 |
No hecho y por qué:
- No se tocó `riesgos.py` (Alertas) ni `bi.vw_riesgo_estudiante`; sigue pendiente decidir su base.
- No se actualizó el documento de tesis (no se toca desde este repositorio).
- No se verificó en el navegador (sesión caducada).
- Hecho en línea por el chat de desarrollo, no delegado.
Invariantes cambiados: no (Holt-Winters m = 12 con hold-out de 6 meses y OLS anual solo descriptiva intactos). **Cambian cifras del pronóstico financiero** que pudieran estar congeladas: ver tabla y recongelar en L9.
Pruebas: 12 failed / 1.003 passed / 12 skipped / 7 xfailed · cobertura 73 %. De los 12: 6 son los de L0; 6 son de trabajo simultáneo de FU en el mismo árbol (`dw_loader.py`, `cobranza_canonica.py`, `mapeo_fuentes`): 3 de `test_f3_2_kpi15`, 2 de `test_dataops_integridad` y `test_fu_l0_perfil`. Ninguno toca metas ni pronóstico. `tests/adw`, `tests/sprint4` y `tests/sprint6/test_seguridad_y_resiliencia_api.py`: 121 passed.
Servicios reconstruidos + estado de docker compose ps: `api` reconstruida (incluye el código de FU que estaba en el árbol en ese momento); los 9 servicios `Up`.
Cambios de esquema o API: ninguno de forma; `GET /forecast/analitica-macro` cambia valores (ver tabla).
Cifras nuevas: ver tabla (archivos `docs/mediciones/adw_da8_forecast_*.json`).
Impacto en el documento (sección o tabla): cualquier cifra del Caso 3 y Caso 4 del pronóstico financiero (pendiente OLS, CAGR, RMSE, cierre proyectado, meta y recaudado 2026) y el avance de meta 31,4 % → 31,7 %.
Riesgos abiertos:
- Las cifras anteriores pueden estar en la fuente de verdad (`docs/fuente_verdad_tesis.md`) como CONGELADO: avisar al chat 3 antes de L9.
- Compartir árbol con FU: la imagen de `api` incluye cambios de FU sin commit.
Pendiente para el chat 4: figuras del pronóstico financiero (si existen) deben regenerarse tras L9.
