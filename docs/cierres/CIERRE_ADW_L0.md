# CIERRE ADW-L0 — 2026-11-20
Rama / commit: beto-integracion · primer commit `f0a120b` (L0-1) y segundo commit `adw(L0): capturas y cruce web↔DW` (L0-2 y L0-3); sin tocar el árbol de RV2 sin commit
Hecho (máx. 10 líneas):
- L0-1: 9 scripts `scripts/auditoria_dw/adw_*.sql` + `ejecutar_l0.sh` → 9 CSV `adw_l0_*.csv` en la copia tmpfs `adw_pg_tmpfs`, creada con `pg_dump` de solo lectura de la DW **viva** (el snapshot del 10-nov no contiene los datos auditados). Ver `adw_l0_entorno.md`.
- L0-2: 18 capturas en `adw_l0_capturas/` y 129 cifras visibles en `adw_l0_cifras_web.csv` (CMI en 2 modos, Académico ×4, Financiero ×4, DataOps ×6, Auditoría, Reportes).
- L0-3: CMI web ↔ `bi.vw_cmi_scorecard` = **92/92 iguales**. Resto de módulos: de 28 cifras, **15 difieren** de la DW (`adw_l0_cruce_web_dw.csv`).
- Los CSV confirman A1, A2, A3, A5, C1, C2 y C3, y añaden hallazgos A13–A24 (tabla en `adw_l0_entorno.md`). Los más graves: A17 (la «cartera vencida exigible» es la deuda total), A18 (recaudación consolidada = Bs 0), A21 (las pantallas financieras y el CMI usan alcances distintos), A14 (comentarios entran como docentes).
No hecho y por qué:
- Las capturas no son de 1440 px reales: el panel del navegador las devuelve reducidas (700–800 px). Sirven como evidencia de contenido, no como figuras del documento.
- No se cruzaron «Meta mes actual / cierre proyectado» de Proyección financiera, «Seguridad & 2FA» ni la bitácora de Reportes (sin fuente equivalente en la DW de datos).
- No se reprodujo con SQL simple el saldo en mora Bs 903.179,09 de Cartera (el SQL da 529.816,81): lo resuelve L4.
Invariantes cambiados: no
Pruebas: 6 failed / 920 passed / 12 skipped / 7 xfailed (938 colectadas) · cobertura no capturada (no se tocó código). Los 6 fallos no vienen de este trabajo: 4 por `torch`/`seqeval` ausentes en el host (`tests/sprint3/test_beto_entrenamiento_endurecimiento.py`) y 2 de Holt-Winters (`test_f2_b8_intervalos`, `TestHoltWinters::test_parametros_suavizado_estimados`) en el árbol con RV2 sin commit; no se comprobó si ya fallaban antes de RV2.
Servicios reconstruidos + estado de docker compose ps: ninguno (no se tocó backend, pipeline ni frontend). Los 9 servicios siguen arriba; se añadió el contenedor `adw_pg_tmpfs` (:55433), fuera del compose.
Cambios de esquema o API: ninguno
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- KPI del CMI web iguales a la vista | 92 de 92 | adw_l0_cruce_kpi_web_dw.csv
- Cifras de otros módulos que difieren de la DW | 15 de 28 | adw_l0_cruce_web_dw.csv
- Hechos académicos sin `id_tiempo` | 162 de 25.191 | adw_l0_academico.csv + adw_l0_entorno.md
- Docentes con nombre > 60 caracteres | 43 de 689 | adw_l0_cruce_dw_valores.csv
- Cartera «vencida exigible» en pantalla = deuda total | Bs 4.832.610,08 | adw_l0_cruce_dw_valores.csv
- Meta 2026: PROGRAMAS frente a todas las categorías | 16.894.995 frente a 17.973.400 | adw_l0_rentabilidad.csv
- Tarea 47 LECTURA_BETO en ERROR | 878 s (no 180 s) | adw_l0_tareas.csv
- `reservas` en marketing | 0 en todas las gestiones | adw_l0_marketing.csv
Impacto en el documento (sección o tabla): ninguno por L0 (no cambia cifras congeladas). Posible: serie predictiva N = 33 en pantalla frente a N = 40 del invariante (A22); verificar antes del recongelado.
Riesgos abiertos:
- RV2 (L0–L7) sigue sin commit; los commits de L0 incluyen solo archivos de L0. Decidir cuándo commitear RV2 (antes de L1).
- `adw_pg_tmpfs` es efímero: si se detiene, hay que recrearlo para repetir L0.
- El front en ejecución no llama a `/cmi/perspectivas/*/detalle`, así que el 500 de CLIENTES (B1) está latente; L1 debe comprobar contra el build correcto.
- Premisas del plan por corregir: `reservas` no está «lleno» (DA6/L6-0); `bitacora_dataops` no existe (L7); tarea 47 duró 878 s.
- Los hallazgos A14–A24 no están asignados a un loop de forma definitiva: los decide Lean (propuesta en la tabla de `adw_l0_entorno.md`).
Pendiente para el chat 4: si se quieren figuras de pantalla, repetir las capturas a 1440 px reales.
