# CIERRE ADW-L5 — 2026-11-20
Rama / commit: beto-integracion · commit `adw(L5): …` (ver `git log`); solo mis archivos (el árbol tiene trabajo simultáneo de FU en `dw_loader.py` y otros)
Hecho (máx. 10 líneas):
- **Lector único del CMI:** `services/cmi_valores.py` lee `bi.vw_cmi_valores` por gestión (`gestion_vigente`, `valores`). Sin las vistas `bi` devuelve vacío y `KPIService` conserva su cálculo local, declarándolo en `fuente`.
- **`obtener_perspectivas_cmi_completo`:** sin filtro de programa, la gestión es la del CMI (la pedida o la última; antes agregaba **todas**) y 12 cifras salen del CMI: KPI-01, 02, 13, 04, 05, 06, 21, 07, 08, 09, 10, 11 y 18. La respuesta trae `fuente` y `filtros.gestion` (el esquema los descartaba). Con filtro de programa se calcula aparte y dice `calculo_local (filtro de programa)`.
- **`/kpis/academico` y `/kpis/financiero`:** aceptan `?gestion=`; por defecto, la última del CMI. KPI-07, 08 y 09 (académico) y KPI-05, 15 y 04 (financiero) vienen del CMI.
- **A18 resuelto:** «Recaudación consolidada» de Cartera mostraba Bs 0 porque la pantalla leía `total_recaudado_bs`, que `KPIService` no entregaba. Ahora lo entrega (2026: 5.843.360,51; 2025: 13.050.264,34).
- **A17 mitigado:** la tarjeta «Cartera Vencida Exigible» pasó a «Deuda Total Registrada» (era la deuda total, no la vencida). Se toma de la misma gestión que el resto.
- **B4:** `tasa_calidad_nlp_pct` cuenta las entidades pendientes en staging: de ≈ 99,6 % a **92,87 %** (485 hechos en revisión + 1.413 pendientes sobre 25.191 + 1.413).
- Contrato en `tests/adw/test_l5_motor_unico.py` (7 pruebas, PostgreSQL de solo lectura): por cada gestión del CMI, la cifra del módulo es igual a la del CMI.
No hecho y por qué:
- **Pantalla de Alertas Tempranas** (`routers/riesgos.py`, SQL propio): sigue calculando por su cuenta (crítica 107 frente a 78 del CMI; riesgo financiero 1.440 frente a 249). Además `bi.vw_riesgo_estudiante` parte de los estudiantes con registro académico, por eso 2026 queda vacía. Unificarla exige decidir la base de la vista.
- **Pronóstico financiero** (`routers/forecast.py`: recaudación, metas, 31,4 %): usa solo la categoría PROGRAMAS; el CMI suma también TECHOS_CERRADOS (31,7 %). **Decisión pendiente de Lean (DA8):** ¿la meta y la recaudación son solo PROGRAMAS o todas las categorías?
- **El mismo concepto con otra definición** que L3 y L4 cambiarán (DA2/DA3, ahora FU-L2/L4): como el motor ya lee del CMI, las pantallas seguirán al CMI cuando cambien las vistas.
- No se verificó en el navegador (sesión caducada, 2FA de Lean). Se comprobó por HTTP en proceso contra la copia tmpfs (7 endpoints 200).
- Tarea hecha en línea por el chat de desarrollo, no delegada a `dev-media`.
Invariantes cambiados: no (23 KPI en `bi.ref_kpi`, `/api/v1/cmi/scorecard` intactos; ningún cambio de vistas).
Pruebas: 10 failed / 1.003 passed / 12 skipped / 7 xfailed · cobertura 73 %. De los 10: 6 son los de L0; 1 era mío (`test_kpis_financieros_calculo_totales`, fila simulada sin `total_pagado`) y se corrigió; 3 son de trabajo simultáneo de FU (`dw_loader.py` modificado por otro chat: 2 de `test_dataops_integridad` y `test_fu_l0_perfil`). Tras la corrección: `tests/sprint4` + `tests/adw` = 145 passed. Vitest: 17 archivos, 93 passed.
Servicios reconstruidos + estado de docker compose ps: `api` y `web` reconstruidos; los 9 servicios `Up`.
Cambios de esquema o API: `GET /kpis/academico` y `/kpis/financiero`: parámetro `gestion`; campos nuevos `gestion`, `fuente`, `total_recaudado_bs`, `mora_estudiantes_pct`, `cartera_vencida_pct`, `estudiantes_con_riesgo_financiero`. `GET /kpis/cmi-completo`: campos `fuente` y `filtros`; **cambio de comportamiento:** sin `gestion` ya no agrega todas las gestiones sino la última del CMI. Sin migraciones.
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Tasa de calidad NLP con pendientes de staging | 92,87 % (antes ≈ 99,6 %) | consulta en tmpfs; reproducible con `tests/adw/test_l5_motor_unico.py::test_calidad_nlp_cuenta_las_entidades_pendientes`
- Cifras de módulo iguales al CMI | 12 KPI × 4 gestiones | `tests/adw/test_l5_motor_unico.py`
Impacto en el documento (sección o tabla): `tasa_calidad_nlp_pct` (si el documento cita la calidad NLP del módulo de pipeline) y cualquier tabla que use `/kpis/cmi-completo` agregado por todas las gestiones.
Riesgos abiertos:
- Las pantallas que mostraban el agregado de todas las gestiones ahora muestran 2026 por defecto, y 2026 no tiene datos académicos: Metas de gestión (usa `cmi-completo`) puede verse vacía en lo académico; es coherente con el CMI.
- Alertas y pronóstico siguen fuera del motor único (ver arriba).
- Cambios simultáneos de FU en archivos cercanos pueden chocar al integrar.
Pendiente para el chat 4: nada.
