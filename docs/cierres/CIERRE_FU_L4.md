# CIERRE FU-L4 — 2026-11-21
Rama / commit: beto-integracion (ver `git log`, commit `fu(L4)`)

Hecho (máx. 10 líneas):
- `acta_canonica.py`: cada celda de nota produce un RESULTADO canónico por módulo (APROBADO, REPROBADO, INASISTENCIA, EXIMIDO, SIN_NOTA) según el número o el vocabulario del catálogo (`vocabularios.resultado_nota` en el YAML, editable). Un 0 cuenta como INASISTENCIA si el estudiante es Deserción o Abandono o el texto lo indica; si no, es un 0 real (REPROBADO).
- Notas fuera de 0–100 y textos fuera de catálogo: NULL, sin hecho de módulo, a revisión con aviso agregado (`NOTA_FUERA_DE_RANGO`, `VALOR_FUERA_DE_CATALOGO`) sin el valor.
- Estados académicos normalizados por catálogo (mayúsculas y acentos); estado desconocido se guarda tal cual y va a revisión. Campos canónicos nuevos `estado_tutoria` y `estado_arca`; columnas de nota, estado y CI se leen por sinónimos.
- KPI-07 y KPI-08 con las reglas de DA-FU2; KPI-16 (DA2-bis) = Deserción o Abandono sobre la matrícula de la gestión, desde cualquier fuente con el campo canónico; sin estado de fuente → «sin dato», nunca 0.
- CI con complemento: `separar_ci` separa `ci_numero` y `ci_complemento`; antes `4892019-1C` se pegaba como 48920191C y resolvía a otro estudiante. Cascada y umbrales intactos.
- Migración 024: `fact_rendimiento_academico.resultado` (CHECK de 5 valores) y `estado_de_fuente`; redefine `bi.vw_cmi_valores` partiendo de la 022; descripciones de KPI-07, 08 y 16. Idempotente; 51 tablas y 10 vistas bi.
- Recarga del libro de actas en tmpfs (dos copias) y comparación sin PII.

No hecho y por qué:
- La 024 NO está aplicada en la DW viva ni en `backend/core/migraciones.py`; `api` y `pipeline` no se reconstruyeron (decisión de Lean: esperar FU-L9). Orden al aplicar: 022, 023, 024.
- La diferencia fuente–DW no cierra en 0 en 2024: la cascada de identidad dejó 551 casos en staging (318 BAJA_CONFIANZA_IA, 140 CI_NOMBRE_DISCORDANTE, 47 BAJA_CONFIANZA, 43 HOMONIMIA, 3 otros). Con ellos sumados el residuo es de unas decenas en 2024 y pocas en 2025; no se verificó fila por fila. La cascada es invariante y no se tocó.

Invariantes cambiados: no

Pruebas: 1.220 colectadas / 1.194 passed / 6 failed / 13 skipped / 7 xfailed · cobertura 75 % (sentencias; backend + pipeline). `tests/fu_l4`: 71 de 71, con la migración 024 en PostgreSQL tmpfs.
- Las 6 fallas son de entorno: 4 BETO (falta `seqeval`), `test_f2_b8_intervalos` y Holt-Winters (`statsmodels`).

Servicios reconstruidos + estado de docker compose ps: ninguno (ver «No hecho»). Los contenedores siguen con el código de FU-L2. `fu_l4_pg_tmpfs` (127.0.0.1:55439) queda levantada con `giragroup_db` (snapshot + migraciones 014, 016–024 + recarga) y `dw_l4_limpia` (recarga sin estudiantes previos).

Cambios de esquema o API: migración 024 (solo tmpfs); `resultado` y `estado_de_fuente` en `fact_rendimiento_academico`; motivo «sin dato» de KPI-16 en `/cmi`.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Deserción 2024 / 2025 (pares estudiante–programa) fuente → DW limpia | 255 → 219 · 176 → 170 | fu_l4_arca_fuente_vs_dw.csv
- Abandono de tutoría 2024 / 2025 | 204 → 187 · 64 → 61 | fu_l4_arca_fuente_vs_dw.csv
- Hechos de módulo en la DW limpia | 27.731 (22.163 APROBADO, 3.115 REPROBADO, 1.519 INASISTENCIA, 3 EXIMIDO, 16 SIN_NOTA, 915 sin resultado) | fu_l4_arca_fuente_vs_dw.csv
- Notas > 100 a revisión / texto fuera de catálogo | 29 → 27 / 4 → 4 | fu_l4_arca_fuente_vs_dw.csv
- KPI-07 (DW viva → tmpfs limpia) | 2024: 78,83 → 80,72 · 2025: 78,99 → 81,92 | fu_l4_kpi_antes_despues.csv
- KPI-08 | 2024: 85,03 → 80,89 · 2025: 85,62 → 85,74 | fu_l4_kpi_antes_despues.csv
- KPI-16 | 2024: 0,00 → 9,25 · 2025: 0,00 → 6,45 (cálculo independiente sobre la fuente: 10,17 y 6,58) | fu_l4_kpi_antes_despues.csv

Impacto en el documento (sección o tabla): KPI-07, KPI-08 y KPI-16 por gestión. No se tocan hasta el recongelado de FU-L9.

Riesgos abiertos:
- **Decisión de Lean:** KPI-16 incluye Abandono (de ESTADO TUTORÍA) como pide DA2-bis, y da 10,17 % (2024) y 6,58 % (2025). El 6,5 % y 4,5 % del plan corresponden solo a Deserción (medido 5,67 % y 4,81 % sobre la matrícula de la fuente). Falta confirmar qué cifra va al documento.
- `nota_final` queda NULL en INASISTENCIA, EXIMIDO, SIN_NOTA y «Aprobó»; el 0 real se guarda como 0. Efecto lateral: KPI-09 y KPI-17 (`vw_riesgo_estudiante`, sin tocar) dejan de contar los 0 de desertores.
- Las mediciones previas del plan no coinciden con lo medido: 13 filas con CI con complemento o ciudad (no 34) y 9 + 29 nombres con dígito o doble espacio (no 125).
- En la copia que conserva los estudiantes del snapshot, 709 filas quedan bloqueadas por CI_NOMBRE_DISCORDANTE contra nombres antiguos; es comportamiento de la cascada, documentado en `fu_l4_arca_fuente_vs_dw_con_estudiantes_previos.csv`.
- La DW viva sigue con los datos viejos hasta FU-L9: aunque se aplique la 024, `resultado` queda NULL en lo ya cargado.
- Deuda del principio rector: listas fijas de cabeceras en `extraccion_por_encabezado.py` (`_CLAVES_NOTA`, `_CLAVES_ANIO`) y `routers/pipeline.py`.
- El front no muestra aún los avisos nuevos ni el motivo legible (FU-L7 y FU-L8).
- Árbol con cambios de otra sesión sin commitear (`database.py`, `conftest.py`, tests f3v/sprint4/sprint6, scripts de figuras, `scripts/auditoria_dw/_parche_da8.py`, `backend/uploads/`): no se incluyen.

Pendiente para el chat 4: ninguno.
