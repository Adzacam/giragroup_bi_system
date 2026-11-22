# CIERRE FU-L6 — 2026-11-21
Rama / commit: beto-integracion (ver `git log`, commit `fu(L6)`)

Hecho (máx. 10 líneas):
- DA4: cada meta lleva su granularidad `MENSUAL` / `ANUAL`, decidida por la forma de la fuente (por categoría y año: una celda con meta es ANUAL, dos o más es MENSUAL; no depende del año). La meta anual no se copia a ningún mes (se guarda en el mes de su celda con `granularidad_meta = 'ANUAL'` y las vistas la excluyen de la meta mensual). Una fila sin bandera (NULL) se lee como MENSUAL.
- KPI-02 solo usa meta mensual: 2024 → «sin dato» (motivo «La fuente solo trae meta anual.»); 2023 → «sin dato» (motivo propio «No hay meta cargada para esta gestión.»). KPI-03, 13 y 14 usan mensual de meses cerrados + meta anual completa (sin prorrateo).
- DA-FU3: la prioridad por tipo de fuente sale de `prioridad_fuentes` del YAML (RENTABILIDAD > EGRESOS para meta y ejecutado). Los 10 `CONFLICTO_FUENTES` quedan `RESUELTO_REGLA`, severidad baja, con los dos valores y la diferencia, fuera de la bandeja de pendientes. El resultado no depende del orden de llegada (probado en ambos órdenes; en la tmpfs invertida: mismos 10 conflictos, `fact_rentabilidad` idéntica). Un hueco (vacío o 0) de la fuente prioritaria lo llena la otra, sin conflicto.
- Mes parcial: el mes de corte sale del contenido (último mes con ejecutado de toda la fuente = 2026-05) y KPI-02, 03 y 12 solo usan meses cerrados (diciembre exento).
- Columnas «año» y serie salen de la sección nueva `metas` del YAML (+ espejo JSON), no de regex fijas. `metas_canonica.py`, `metas_cobertura.py` (motivo «sin dato» del KPI-02 en `/cmi`), `forecast_service` (la serie mensual de metas excluye la anual).
- Migración 026 (columna `granularidad_meta`; redefine `bi.vw_cmi_valores` desde la 025 y `vw_metas_mensual`, que añade `meta_anual`). Idempotente, sin DROP; 51 tablas + 10 vistas bi; `db/schema.sql`, modelo y `esquema_opcional` actualizados.
- Recarga real de los libros de metas en tmpfs (`fu_l6_pg_tmpfs`, 55441) y comparación sin PII.

No hecho y por qué:
- La 026 NO está aplicada en la DW viva ni en `backend/core/migraciones.py`; `api` y `pipeline` no se reconstruyeron (decisión de Lean: esperar FU-L9). Orden al aplicar: 022, 023, 024, 025, 026. Hasta recargar el libro de metas, la DW viva sigue con granularidad NULL (= MENSUAL) y KPI-02 2024 sigue en 6,25 %.
- Prioridad EGRESOS > RENTABILIDAD para egresos y costos por programa: solo está en el YAML; el lote no trae una segunda fuente que genere conflicto.
- No se actualizó `docs/fuente_verdad_tesis.md` ni el docx (recongelado en FU-L9).

Invariantes cambiados: no (cascada, umbrales y snapshot intactos; 51 tablas y 10 vistas bi sin cambio)

Pruebas: 1.328 colectadas / 1.284 passed / 10 failed / 27 skipped / 7 xfailed · cobertura 76 % (sentencias; backend + pipeline). `tests/fu_l6`: 45 de 45 (8 de la migración 026 en PostgreSQL tmpfs, con transacción que siempre se revierte).
- 6 fallas de entorno: 4 BETO (falta `seqeval`), `test_f2_b8_intervalos` y Holt-Winters (`statsmodels`).
- 4 fallas de `tests/sprint4/test_auth_and_rbac.py` (esperaban 401/400 y reciben 403). No son de FU-L6: el archivo pasa solo (17/17) y con `tests/fu_l6` (62/62), y falla (4 de 24) en cuanto corren antes `tests/fu_l7` y `tests/fu_l8`, que otra sesión commiteó; esos tests contaminan el estado de la app. Hay que corregirlo en FU-L7/L8.

Servicios reconstruidos + estado de docker compose ps: ninguno (ver «No hecho»). `fu_l6_pg_tmpfs` (127.0.0.1:55441) queda levantada con `giragroup_db` (snapshot + 014, 016–026 + recarga de los libros de metas), `dw_l6_inverso` (orden inverso) y `catalogo_copia`.

Cambios de esquema o API: migración 026 (solo tmpfs): `fact_rentabilidad.granularidad_meta`, `bi.vw_cmi_valores` y `bi.vw_metas_mensual` redefinidas; motivo «sin dato» del KPI-02 en `/cmi`.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- `fact_rentabilidad` + `dim_meta` fuente = DW tmpfs | 187 de 187 iguales (129 + 58, 0 diferencias; 31 con las dos fuentes distintas, se carga la prioritaria) | fu_l6_metas_fuente_vs_dw.csv, fu_l6_resumen.json
- Granularidad de metas | 2024: una celda ANUAL (10.719.694, diciembre) · 2025 y 2026: MENSUAL · 2023: sin meta | fu_l6_metas_fuente_vs_dw.csv
- `CONFLICTO_FUENTES` resueltos por regla / pendientes | 10 / 0; 7 diferencias exactas de 100.000 (meta PROGRAMAS, abril–octubre 2025) marcadas para avisar al área financiera; 1 de 39.724 (meta, diciembre) y 2 en el ejecutado de marzo 2025 | fu_l6_conflictos_metas.csv
- KPI-02 (DW viva → tmpfs) | 2023: sin dato · 2024: 6,25 → sin dato · 2025: 157,48 → 157,48 · 2026: 15,28 → 100,99 (abril, cerrado) | fu_l6_kpi_antes_despues.csv
- KPI-03 | 2024: 102,26 → 102,26 · 2025: 110,54 → 110,54 · 2026: 85,76 → 109,07 | fu_l6_kpi_antes_despues.csv
- KPI-12 | 2024: 17,60 → 17,60 · 2025: 28,10 → 28,10 · 2026: −1,21 → 20,61 | fu_l6_kpi_antes_despues.csv
- KPI-13 / KPI-14 | sin cambio (13: 102,26 / 110,54 / 31,69 · 14: 0 / 0 / 12.278.356,22) | fu_l6_kpi_antes_despues.csv

Impacto en el documento (sección o tabla): KPI-02 por gestión (2024 y 2023 «sin dato»; 2026 con mes cerrado), KPI-03 y KPI-12 de 2026, conflictos de metas entre fuentes. No se tocan hasta el recongelado de FU-L9.

Riesgos abiertos:
- **Extensión mía, no pedida por Lean:** KPI-03 y KPI-12 también excluyen el mes parcial (en 2026 dependían de mayo, 252.233 Bs). Es la causa de que KPI-03 2026 pase de 85,76 a 109,07 y KPI-12 de −1,21 a 20,61. Reversible en la 026; Lean debe confirmarla o quitarla antes de FU-L9.
- DA-FU3 depende del tipo de fuente guardado en el documento: sugerir un tipo equivocado para el libro de Egresos lo dejó como RENTABILIDAD por contenido y entonces no hay regla (conflicto PENDIENTE). Con el tipo EGRESOS explícito funciona. Falta afinar la detección EGRESOS vs RENTABILIDAD en `ingestion_service` (no se tocó: sus pesos afectan a otros libros).
- Los caminos de corrección manual (`revision.py`, `pipeline.py`) llaman a `registros_rentabilidad` sin perfil: no marcan granularidad y conservan la de la fila.
- Deudas fuera de alcance: `pipeline/analytics/seed_historical_facts.py` (semilla antigua) no marca granularidad; los modelos copiados en `services/audit-service` y `notifications-service` no tienen la columna.
- Otra sesión commiteó `CIERRE_FU_L6.md` (FU-B1) y los CSV de L6 antes que este cierre (commits `9db47fe`, `7864bd3`) y parte del código de L6 (`routers/cmi.py`, en `afcf41f`). Este cierre reemplaza a aquel (decía «sin cambios de esquema»).
- No se commitean: `output/fu_l6_recarga_*.json` (restos de corridas), `backend/core/database.py`, `tests/sprint4/test_forecasting.py` y el resto del árbol de otras sesiones.

Pendiente para el chat 4: ninguno hasta FU-L9.
