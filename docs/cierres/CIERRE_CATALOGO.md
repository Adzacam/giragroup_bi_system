# CIERRE CATALOGO — 2026-11-22
Rama / commit: `beto-integracion` (pendiente commit selectivo al cierre)

Hecho (máx. 10 líneas):
- **CAT-L0:** Inventario reproducible en `scripts/auditoria_dw/cat_inventario.sql` y `docs/mediciones/cat_l0_inventario.csv` (4.565 módulos: 3.928 POS, 2 otros códigos, 635 `MOD-GEN` incluidos los 5 candidatos DC3).
- **CAT-L1:** `backend/services/modulo_validador.py` (`es_nombre_modulo_valido`, `validar_nombre_modulo`) con 88 reglas editables en `cat_etiqueta_clasificacion` (`categoria='MODULO_RECHAZO'`) en `giragroup_catalog_db` y `db/seeds/seed_catalogos_config.sql`; `DWLoaderService.resolver_o_crear_modulo` ya no crea `MOD-GEN` y registra `VALOR_FUERA_DE_CATALOGO` (`campo_afectado='modulo'`) con acciones `VINCULAR_MODULO` / `CREAR_MODULO` en bandeja.
- **CAT-L2 (DC1 + DC3):** Respaldo `backups/cat_pre_l2.dump`; eliminados 635 `MOD-GEN` con 0 referencias FK/staging (incluidos los 5 candidatos DC3, ya que 1224 no tuvo coincidencia en `cat_programa`), quedando 3.930 módulos (3.928 POS + `MKT-GEN`, `ADM-GEN`) y 0 `MOD-GEN`.
- **CAT-L3 (DC2):** Unificada `cat_institucion` a `361` («GiraGroup Posgrado»), eliminadas `1`, `2` (ENP) y `3` (FCS) tras verificar 0 referencias, y registrado sinónimo `GiraGroup` → `GiraGroup Posgrado` en `cat_mapeo_columna` y `_resolver_id_institucion`.
- **CAT-L4:** Completados `1.256` de `1.334` módulos sin `programa` desde `cat_programa` (`giragroup_catalog_db`); quedan `78` con motivo explícito en `docs/mediciones/cat_l4_programa.csv`.
- **CAT-L7 (DC4):** Tabla única de verdad `giragroup_catalog_db.cat_institucion_convenio` (22 filas); `canonizar_o_registrar_institucion` fusiona variantes ≥ 90 %, deriva dudosas (75–89 %) como `VALOR_FUERA_DE_CATALOGO` y registra nuevas instituciones desde TECHOS; pestaña «Instituciones» con grupos «Propia» (1) y «Convenio» (22).
- **CAT-L5:** `MasterDataView.jsx` + `MasterDataView.css` + `catalogo_dataops.py` actualizados a 20 filas/página, filtros («Solo genéricos», «Sin programa», «En uso / sin uso»), columna «En uso», «Eliminar» deshabilitado con referencias, acción ADMIN «Limpiar módulos sin uso (n)» con vista previa en `<dialog>` nativo y layout responsivo.

No hecho y por qué:
- **CAT-L6 (Verificación después de la recarga):** Pendiente hasta que Lean ejecute la recarga completa del lote sobre la DW limpia.

Invariantes cambiados: no

Pruebas:
- `pytest tests/cat/ -v`: 26 passed (0 failed).
- `vitest run`: 23 archivos, 117 passed (0 failed).
- `npm run build` (`vite build`): OK (2.82 s).

Servicios reconstruidos + estado de docker compose ps:
- Reconstruidos `web`, `api` y `pipeline` (`docker compose up -d --build --no-deps ...`); verificación directa de endpoints `/api/v1/dataops/catalogs` (`200 OK`) y capturas Playwright en desktop (1440×900) y móvil (390×844).

Cambios de esquema o API:
- `GET /api/v1/dataops/catalogs`: `page_size=20`, nuevos query params `solo_genericos`, `sin_programa`, `uso`, `grupo`, campo `en_uso` por módulo, `resumen.total_sin_uso` y `grupos` (`propia`, `convenio`).
- `GET /api/v1/dataops/catalogs/modulos-sin-uso/preview` y `DELETE /api/v1/dataops/catalogs/modulos-sin-uso` (solo `ADMIN`).

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Módulos iniciales por clase | 4.565 total (3.928 POS, 2 otros, 635 `MOD-GEN`) | `docs/mediciones/cat_l0_inventario.csv`
- Módulos `MOD-GEN` eliminados en CAT-L2 | 635 (restantes `MOD-GEN` = 0) | `docs/mediciones/cat_l2_borrados.csv`
- Instituciones propias tras fusión | 1 (`id=361`, 3.930 módulos, 16.874 estudiantes) | `docs/mediciones/cat_l3_instituciones.csv`
- Programas completados en CAT-L4 | 1.256 completados, 78 sin coincidencia | `docs/mediciones/cat_l4_programa.csv`
- Instituciones de convenio en catálogo | 22 | `docs/mediciones/cat_l7_instituciones_convenio.csv`

Impacto en el documento (sección o tabla):
- Gobernanza de catálogo de referencia (Sección de DataOps / Datos Maestros) y calidad de dimensiones (`dim_modulo`, `cat_institucion`, `cat_institucion_convenio`).

Riesgos abiertos:
- Tras la recarga de Lean, verificar CAT-L6 (0 `MOD-GEN` nuevos, avisos en bandeja y resolución de instituciones de convenio en `fact_techo_convenio`).
- En `02_modulos_mobile.png` (390 px), los nombres de módulo muy largos muestran recorte lateral derecho en tarjetas apiladas (`white-space`/`word-break` menor).

Pendiente para el chat 4:
- Ejecutar CAT-L6 tras la recarga de Lean y exportar cifras finales post-recarga.
