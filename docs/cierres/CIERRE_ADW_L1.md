# CIERRE ADW-L1 — 2026-11-20
Rama / commit: beto-integracion · commit `rv2+adw(L1)` (decisión de Lean: commitear RV2 junto con L1 porque `routers/cmi.py` depende de archivos de RV2). Se añadieron solo los archivos de RV2 y L1; quedaron fuera `backups/`, `backend/uploads/`, `output/`, `.claude/`, `.agent*/`, scripts de figuras y los cambios de estilos (`tokens.css`, `v2-*.css`), `conftest.py`, `database.py`, `NotificationPopover.jsx`, `LoginHeroPane.jsx` y tres pruebas (`test_kpi23`, `test_forecasting`, `test_seguridad_y_resiliencia_api`), que no pude atribuir a RV2.
Hecho (máx. 10 líneas):
- B1: `GET /api/v1/cmi/perspectivas/CLIENTES/detalle` ya no da 500. `inscritos_programa` se reescribió con tablas reales: `fact_marketing` + `dim_modulo` (nombre del programa) + `dim_tiempo.gestion`. Las tablas anteriores (`fact_inscripcion`, `dim_programa`, `fact_captacion_marketing`, `dim_fuente_captacion`, `t.anio`) no existen.
- `conversion_fuente` se retiró hasta que exista la fuente (A5/KPI-06). La respuesta lo explica en `avisos`; la pantalla ya mostraba «No hay cifras de captación comprobables…» con una serie vacía.
- B2: cada serie del desglose pasa por un ayudante que, ante `SQLAlchemyError`, hace `logger.exception` («cmi_router»), `rollback`, deja la serie vacía y añade un texto a `avisos`. Los KPP y gráficas personalizados hacen lo mismo; `get_config` también registra el error.
- La respuesta del detalle ahora incluye `avisos: list[str]`.
- Tests nuevos `tests/adw/test_l1_cmi_detalle.py` (7): serie que falla → 200 + aviso + log; el código ya no cita las tablas viejas; toda tabla o vista citada en `routers/` y en `cmi_personalizacion_service` existe (PostgreSQL); las 4 perspectivas responden 200 en las 4 gestiones.
- Comprobado en el navegador (`/v2/cmi?p=CLIENTES`, gestión 2026): 200 OK con 12 programas y el aviso. Log de la API sin 500 ni trazas tras la reconstrucción.
No hecho y por qué:
- El front no muestra `avisos` (el JSX de RV2 no los lee); queda para el chat de front si se quiere.
- No se corrió vitest: no se tocó frontend.
- Tarea hecha en línea por el chat de desarrollo y no delegada a `dev-media` (era un cambio de un solo archivo con el contexto ya cargado).
Invariantes cambiados: no
Pruebas: 959 colectadas / 934 passed / 6 failed / 12 skipped / 7 xfailed · cobertura 73 % (sentencias, `--cov=backend --cov=pipeline`). Los 6 fallos son los mismos de L0 (4 por `torch`/`seqeval` ausentes en el host y 2 de Holt-Winters), ajenos a L1. La colección creció 21 pruebas desde L0: 7 son de L1 y el resto vienen de cambios de otras sesiones en el árbol.
Servicios reconstruidos + estado de docker compose ps: `api` reconstruido; los 9 servicios `Up`. `giragroup_catalog_db` se reinició al levantar la API (aparece «Up 14 seconds (healthy)»).
Cambios de esquema o API: `GET /cmi/perspectivas/{codigo}/detalle`: campo nuevo `avisos`; `series.conversion_fuente` ya no se envía; `inscritos_programa.programa` ahora es el nombre del módulo. Sin cambios de esquema.
Cifras nuevas (cifra | valor | archivo en docs/mediciones/): ninguna nueva; evidencia en `tests/adw/test_l1_cmi_detalle.py`.
Impacto en el documento (sección o tabla): ninguno.
Riesgos abiertos:
- **Commit de RV2:** al commitear RV2 con L1, el resto del árbol (156 rutas sin relación) sigue sin commit. Los archivos excluidos listados arriba pueden contener cambios de RV2 que no pude confirmar; revisar con `git status` antes de dar RV2 por cerrado.
- «Inscritos por programa» suma `fact_marketing.inscritos`, que parece duplicado (≈ 2×; hipótesis de L6-0, la corrige FU-L3). Las cifras del gráfico no son definitivas.
- `dim_modulo` contiene módulos basura (`MOD-GEN*`, «0», «1», una fecha): pueden aparecer como «programa» en otras gestiones (hallazgo A15).
- Los toasts «Lectura de BETO · Lote #1» seguían apareciendo en la UI durante la prueba (relacionado con C1/D3, L7).
Pendiente para el chat 4: nada.
