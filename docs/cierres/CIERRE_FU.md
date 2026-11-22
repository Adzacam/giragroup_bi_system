# CIERRE FU (plan FUENTES_UPLOADS, FU-L0 a FU-L9) — 2026-11-22
Rama / commit: beto-integracion (último commit de este plan: ver `git log`, `fu(L9): cierre del plan FU`)

Hecho (máx. 10 líneas):
- Los 10 loops tienen su cierre: `CIERRE_FU_L0.md` a `CIERRE_FU_L9.md` (L9 completo en `CIERRE_FINAL_FU_ADW_L9.md`). Principio rector cumplido: sin nombres de archivo ni de hoja en el código, mapeo por sinónimos en `config/mapeo_fuentes.yaml` (+ espejo JSON), pruebas con fuentes sintéticas.
- DW viva recargada con los 10 libros y migraciones 022 a 028 aplicadas y registradas en `backend/core/migraciones.py` (esto último lo hizo la sesión de FU-L9, no este chat; contradice la decisión inicial «esperar a FU-L9», que se cumplió al llegar a él).
- Comparación DW viva contra fuente: inscritos por año, pagos por año, estudiantes en mora y hechos de evaluación coinciden exactamente (`fu_cierre_dw_viva.csv`, 24 filas, solo lectura).
- Revisión posterior al cierre de FU-L9, con cuatro correcciones: (1) la vista viva `bi.vw_cmi_valores` quedó con la migración 028 aplicada con mala codificación (mojibake en `translate`): KPI-16 daba 2,68 % y 1,79 % y volvió a 5,38 % y 6,47 % al reaplicarla en UTF-8 (la reaplicó Lean tras la propuesta de este chat; verificado en solo lectura); (2) filtros de Alertas Tempranas acotados a 100 opciones por selector (`6f18500`); (3) riesgo de deserción de Alertas por estado Deserción/Abandono (`3083636`, 0 → 478 casos); (4) `adw_l9_remedicion_final.csv` pasado de UTF-16 a UTF-8 (`118764c`).
- Contaminación de tests corregida: el test de FU-L8 dejaba un usuario simulado puesto y rompía 4 tests de auth (`13f263e`).
- Invariantes verificados en la DW viva: 51 tablas (49 public + 2 bi), 10 vistas bi, 23 KPI en `bi.ref_kpi`; `verificar_sfv.py`: 181 ítems, 0 discrepancias; `snapshot_dw_20261110_1201` intacto.

No hecho y por qué:
- La diferencia de actas (ARCA) no cierra en la DW viva: 25.208 filas contra 27.731 en la copia limpia. La DW viva conserva los estudiantes del snapshot y la cascada de identidad bloquea filas (1.516 pendientes de revisión humana: 747 CI_NOMBRE_DISCORDANTE, 363 HOMONIMIA, 323 BAJA_CONFIANZA_IA). Efecto: KPI-07 2024 = 82,32 (limpia 80,72) y KPI-08 2024 = 84,98 (limpia 80,89). Se dejó así porque la cascada es invariante.
- No hay cifras con la recarga sobre la matrícula completa de la fuente para KPI-16 de 2024 (10,17 %): la DW viva da 5,38 %. Depende de la decisión de Lean (ver riesgos).
- Verificación visual completa del flujo DataOps en navegador (3 pasos, claro/oscuro, móvil): solo se comprobó la pantalla de Alertas Tempranas; el resto lo declaró la sesión de FU-L8 sin clic interactivo.

Invariantes cambiados: no (cascada, umbrales 0,92 / 90 / 85 / 80, bandas 0,85 / 0,60, estados A/B/C, BETO 128 tokens, 51 tablas + 10 vistas bi, 23 KPI)

Pruebas: 1.286 passed / 6 failed / 41 skipped / 7 xfailed (suite completa, 6:06 min) · cobertura del último informe 76 % (sentencias; backend + pipeline). Vitest: 103 de 103; build de producción en verde.
- Las 6 fallas son de entorno: 4 BETO (falta `seqeval`), `test_f2_b8_intervalos` y Holt-Winters (`statsmodels`).

Servicios reconstruidos + estado de docker compose ps: `api` y `web` reconstruidos con los commits `6f18500` y `3083636`; gateway reiniciado; 9 servicios Up; `/health` 200 y `/api/v1/health` 200.

Cambios de esquema o API: migraciones 022 a 028 en la DW viva; `/api/v1/riesgos/alertas-tempranas` devuelve `filtros_totales` y filtros acotados; `/api/v1/riesgos/resumen-vista` (FU-L9).

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Pagos 2024 / 2025 / 2026 (Bs), fuente = DW viva | 8.071.737,03 / 12.422.501,39 / 4.841.944,46 | fu_cierre_dw_viva.csv
- Inscritos 2022 a 2026, fuente = DW viva | 53 / 3.551 / 4.563 / 4.737 / 2.292 | fu_cierre_dw_viva.csv
- Estudiantes con ≥ 2 cuotas 2024 / 2025 / 2026 | 362 / 808 / 641 | fu_cierre_dw_viva.csv
- Hechos de evaluación docente; fuera de escala; sin fecha | 409.859; 0; 12.937 | fu_cierre_dw_viva.csv
- KPI-16 (DW viva) 2024 / 2025 | 5,38 % / 6,47 % | adw_l9_remedicion_final.csv
- Riesgo de deserción en Alertas / alerta crítica | 478 / 320 estudiantes (antes 0 / 198) | medición de solo lectura del 2026-11-22; sin archivo propio

Impacto en el documento (sección o tabla): ya recibió el recongelado de FU-L9 (`fuente_verdad_tesis.md`, Tabla F.1, CONGELADO). Lo de esta revisión no cambia ninguna cifra de esa tabla (KPI-16 volvió a su valor congelado). Si se cita la tarjeta «Riesgo de deserción» de Alertas (478), explicar que cuenta estudiantes con ese estado en cualquier gestión; KPI-16 es por gestión sobre la matrícula.

Riesgos abiertos:
- **Decisión de Lean sobre KPI-16 2024:** «Deserción + Abandono sobre la matrícula de la fuente» da 10,17 %; la DW viva da 5,38 %. Aceptar la cifra viva, o depurar las filas bloqueadas por la cascada y recargar.
- **KPI-03 y KPI-12 excluyen el mes parcial** (extensión no pedida por Lean, FU-L6; KPI-03 2026 = 109,07 y KPI-12 2026 = 20,61). Lean debe confirmarla o quitarla.
- **Datos sucios en dimensiones:** aparecen profesiones y números sueltos como programas y módulos (por ejemplo «ABOGADA», un teléfono como módulo) en las listas de filtros. Viene de columnas mal leídas en la carga; no se corrigió.
- **Detección Egresos frente a Rentabilidad** en `ingestion_service`: si se sube el libro de Egresos con otro tipo, el conflicto de metas queda pendiente y la regla de prioridad no se aplica.
- **Procedimiento:** otra sesión aplicó migraciones, reconstruyó servicios y recargó la DW viva sin avisar a este chat, y commiteó trabajo de L6 a L8 en paralelo. Conviene una sola sesión por loop y no aplicar migraciones a mano con otra codificación (la causa del mojibake).
- **Árbol con cambios sin commitear que no son de este plan:** `backend/config/`, `backend/output/`, `backend/scripts/auditoria_fuentes/`, `backend/uploads/`, `output/fu_l6_recarga_*.json`, `scripts/auditoria_dw/_parche_da8.py`, figuras y `.claude/*`.
- **Consola del navegador:** dos mensajes «An unknown error occurred when fetching the script» en Alertas Tempranas; ninguna petición de la app falló y no se investigaron.

Pendiente para el chat 4: ninguno (las cifras del documento son las del recongelado de FU-L9).
