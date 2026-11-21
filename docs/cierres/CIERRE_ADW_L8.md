# CIERRE ADW-L8 — 2026-11-20
Rama / commit: beto-integracion · commit `adw(L8): …` (ver `git log`); solo mis archivos: el árbol tiene cambios simultáneos de FU-L1 (`ingestion_service.py`, `planificacion_extractor.py`, `tests/fu_l1/`, `tests/fixtures/`) que no se incluyeron
Hecho (máx. 10 líneas):
- **D2 (aprobación en bloque):** una aprobación en bloque sin cambios se guarda con el marcador `APROBACION_BLOQUE` y ya no como texto de corrección. Módulo nuevo `services/auditoria_hitl.py` con `es_correccion_humana()` y `accion_de_auditoria()`: ni la aprobación en bloque ni la revelación de datos cuentan como corrección. La pantalla de Auditoría rotula «Aprobación en bloque (sin cambios)» y «Revelación autorizada de dato personal» (también para las filas históricas). Comprobado con la API contra la copia tmpfs: 192 y 8 etiquetas, 0 como «Resolución HITL».
- **Historial:** `adw_l8_reclasificar_bloque.sql` pasó en tmpfs las 12.326 filas históricas a `APROBACION_BLOQUE`; las que cuentan como corrección humana pasan de 12.336 a 0 (todas eran en bloque o revelaciones).
- **DA7 en el código:** `motivo_fila_sin_entidad` distingue `CATALOGO_PROGRAMA_NO_ALUMNO`, `CATALOGO_PROGRAMA_NO_PAGO` y `DOCENTE_NO_ESTUDIANTE` (se descartan con motivo) y `FILA_SIN_IDENTIDAD` (pagos o facturas sin estudiante, estados sueltos y filas sin patrón: **no se descartan**, quedan PENDIENTES en la bandeja). Sobre las 1.308 filas reales: 472 + 749 catálogo, 69 docentes y 18 a la bandeja (16 académicas y 2 facturas) — `adw_l8_clasificacion_nueva.csv`.
- **Agrupación por patrón:** las 756 discordancias de nombre tenían ~720 CI distintas, así que agrupar por CI no agrupaba nada. `grupos_pendientes` devuelve ahora `patrones`: muy distinto (< 30): 360 casos / 341 grupos; parcialmente distinto: 387 / 376; casi igual: 9 / 9. La aprobación sigue siendo por CI (nunca se aprueba de una vez a personas distintas).
- Filas vacías: ya se descartan solas (`FILA_SIN_CABECERAS`); no hizo falta código nuevo.
- Tests: 24 nuevos en `tests/adw/test_l8_revision.py` y 1 en `test_bandeja_hechos_en_revision.py`; actualicé 2 expectativas de `test_bandeja_hitl_ruido_y_un_clic.py` a los motivos nuevos (cambio intencional).
No hecho y por qué:
- **Las 5 filas `BAJA_CONFIANZA` del doc 44 NO se descartaron:** la auditoría decía que eran «filas vacías de TBL_INSCRITOS», pero son líneas completas (833–942 caracteres, con fecha, proyecto y módulo) con índice de confianza 0,0000. Descartarlas habría perdido inscripciones. Causa del índice 0 sin investigar: puede ser que el índice no se calculó; queda para FU-L3/L7.
- **El front no muestra `patrones`** ni los motivos nuevos con diseño propio (usan el formulario genérico de la categoría). Falta FU-L8.
- **La DW viva no se tocó:** las filas históricas siguen con el texto antiguo y las filas sin estudiante ya cargadas siguen con el motivo viejo. Las clasificaciones nuevas aplican a la próxima carga o recarga (FU-L9). SQL para el historial: `scripts/auditoria_dw/adw_l8_reclasificar_bloque.sql`; decide Lean.
- No se verificó la pantalla de Auditoría en el navegador: la sesión caducó y el 2FA lo ingresa Lean.
- Tarea hecha en línea por el chat de desarrollo, no delegada a `dev-media`.
Invariantes cambiados: no (cascada, umbrales, estados A/B/C y 51/10/23 intactos; ningún perfil TEMP nuevo).
Pruebas: 9 failed / 991 passed / 12 skipped / 7 xfailed (1.019 colectadas) · cobertura 73 %. De los 9: 6 son los de L0; 2 eran de L8 y se corrigieron (expectativas de motivos) y 1 es de `tests/fu_l1/` (trabajo en curso de otro chat; pasa al ejecutarlo solo). Tras la corrección: `tests/adw` + `test_bandeja_hitl_ruido_y_un_clic` = 57 passed. No se volvió a correr la suite completa. `dataops_tarea` de la DW viva sigue en 10 filas.
Servicios reconstruidos + estado de docker compose ps: `api` reconstruida; los 9 servicios `Up`.
Cambios de esquema o API: `GET /review-tray/grupos` (vía `grupos_pendientes`): campo nuevo `patrones`; grupos de CI_NOMBRE_DISCORDANTE con `patron`. Motivos nuevos en `stg_entidad_no_resuelta.motivo` (sin cambio de esquema). `consolidacion` devuelve `enviados_a_bandeja_sin_identidad`. Sin migraciones.
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Filas históricas reclasificadas a APROBACION_BLOQUE (tmpfs) | 12.326 | adw_l8_antes.json / adw_l8_despues.json
- Cuentan como corrección humana | 12.336 → 0 | adw_l8_despues.json
- Filas sin estudiante: catálogo / docente / a la bandeja | 1.221 / 69 / 18 | adw_l8_clasificacion_nueva.csv
- Discordancias por patrón (muy distinto / parcial / casi igual) | 360 / 387 / 9 | adw_l8_despues.json
Impacto en el documento (sección o tabla): ninguno. Cuando se recargue (FU-L9), KPI-18 recibirá 18 casos más; los «descartados por regla» cambiarán de nombre.
Riesgos abiertos:
- Dos de las tres «excepciones por patrón» en producción dependen de que el reader detecte bien los encabezados (`POS - IBP`, `POS - MODULO`): otra hoja con otros nombres caería en `FILA_SIN_IDENTIDAD` y llegaría a la bandeja (seguro, pero más trabajo humano).
- Las 2 facturas tenían «Código Estudiante o NIT» vacío; la hipótesis del agente de L8-0 («CI existente») era incorrecta.
- Concurrencia: FU-L1 edita archivos cercanos (`ingestion_service.py`, `planificacion_extractor.py`); posible conflicto al integrar.
Pendiente para el chat 4: nada.
