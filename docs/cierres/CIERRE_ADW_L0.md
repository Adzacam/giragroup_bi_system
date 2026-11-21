# CIERRE ADW-L0 (PARCIAL) — 2026-11-20
Rama / commit: beto-integracion (hash en el commit `adw(L0)`; sin tocar el árbol de RV2 sin commit)
Hecho (máx. 10 líneas):
- L0-1 completo: 9 scripts `scripts/auditoria_dw/adw_*.sql` + `ejecutar_l0.sh` → 9 CSV `docs/mediciones/adw_l0_*.csv`, ejecutados en la copia tmpfs `adw_pg_tmpfs`.
- Copia tmpfs creada con `pg_dump` de solo lectura de la DW **viva** (el snapshot del 10-nov no contiene los datos auditados). Detalle en `docs/mediciones/adw_l0_entorno.md`.
- Los CSV confirman A1, A2, A3, A5, C1, C2 y C3. Tres diferencias frente al texto de la auditoría, anotadas en `adw_l0_entorno.md`.
- **Hallazgo nuevo A13:** 162 de los 25.191 hechos académicos tienen `id_tiempo` NULL; ninguna vista por gestión los cuenta.
No hecho y por qué:
- **L0-2 (capturas por módulo) y L0-3 (cruce web ↔ DW):** el navegador integrado está en el login y el 2FA lo ingresa Lean. No se introdujeron credenciales ni se generó token. Bloquea el cierre completo de L0.
Invariantes cambiados: no
Pruebas: 6 failed / 920 passed / 12 skipped / 7 xfailed (938 colectadas) · cobertura no capturada (no se tocó código). Los 6 fallos no vienen de este trabajo: 4 por `torch`/`seqeval` ausentes en el host (`tests/sprint3/test_beto_entrenamiento_endurecimiento.py`) y 2 de Holt-Winters (`test_f2_b8_intervalos`, `TestHoltWinters::test_parametros_suavizado_estimados`) en el árbol con RV2 sin commit; no se comprobó si ya fallaban antes de RV2.
Servicios reconstruidos + estado de docker compose ps: ninguno (no se tocó backend, pipeline ni frontend). Los 9 servicios siguen arriba; se añadió el contenedor aparte `adw_pg_tmpfs` (:55433), fuera del compose.
Cambios de esquema o API: ninguno
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Académico por gestión (2024 / 2025 / sin gestión) | 14.285 / 10.744 / 162 | adw_l0_academico.csv
- Tarea 47 LECTURA_BETO en ERROR | 878 s (no 180 s) | adw_l0_tareas.csv
- `reservas` en marketing | 0 en todas las gestiones | adw_l0_marketing.csv
- Razón claves/hechos de `carga_fila_origen` | 2,00 a 3,52 según tabla | adw_l0_carga_fila_origen.csv
Impacto en el documento (sección o tabla): ninguno (L0 no cambia cifras congeladas).
Riesgos abiertos:
- RV2 (L0–L7) sigue sin commit y mezclado en el árbol de trabajo; este commit incluye solo los archivos de L0. Hay que decidir cuándo commitear RV2 (antes de L1).
- `adw_pg_tmpfs` es efímero; si se detiene, hay que recrearlo para repetir L0.
- DA6/L6-0 debe corregir su premisa: `reservas` no está «lleno».
Pendiente para el chat 4: nada. Para Lean: iniciar sesión (2FA) en el navegador integrado para cerrar L0-2 y L0-3.
