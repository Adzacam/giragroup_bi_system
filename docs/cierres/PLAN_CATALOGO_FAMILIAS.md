# PLAN CATALOGO_FAMILIAS (CF) — 2026-11-23

Objetivo de la fase: sanear programas y módulos por familia y oferta, reentrenar BETO durante 2–5 épocas, habilitar el rescate residual NER+PLN y medir RNF-03 y RNF-04.

Entrada: `CIERRE_CATALOGO.md` y `CIERRE_BETO_ACTIVO.md`. Rama base `beto-integracion`, HEAD `30b05df` al redactar. Revisar diferencias locales y preparar un commit selectivo.

## Decisiones de diseño

- **DCF-1.** Sanear `dim_modulo.programa` con el nombre canónico de familia. Limpiar también `nombre_modulo` únicamente cuando el inventario confirme que contiene el título de programa con marcadores de oferta. Conservar nombres de asignaturas, códigos y PK. Guardar el original, el resultado y el motivo en la evidencia de la migración. Derivar los casos dudosos a revisión.
- **DCF-2.** Agrupar las ofertas por nombre canónico normalizado de familia y usar aliases explícitos para variantes confirmadas. Mantener un registro por `pos_code`, con su versión, edición y alcance cuando consten en la fuente. Dos códigos con igual familia y versión se conservan como ofertas distintas. Validar colisiones de nombre entre programas realmente distintos y conservar el texto fuente en `nombre_completo_raw` cuando corresponda.
- **DCF-3.** Mantener la FK local y sincronizar `giragroup_db.cat_modulo` desde el catálogo maestro `giragroup_catalog_db`. En el maestro, la clave de módulo es la oferta más su número de módulo, representable como `(pos_code, nro_modulo)`. Usar un mapeo estable hacia los IDs locales respetando el esquema y las referencias existentes. Para completar la FK exigir coincidencia inequívoca dentro de la oferta por número o nombre canónico comprobado. Si la fila representa la oferta completa, carece de código o tiene candidatos ambiguos, conservar la FK nula y registrar el motivo. Sincronizar y vincular en una transacción local reejecutable y sin borrados implícitos.

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación | Salida en `docs/mediciones/` |
|---|---|---|---|---|---|---|
| CF-L0 | Inventariar las cuatro tablas con consultas de solo lectura. Clasificar títulos de oferta, asignaturas, códigos inválidos, colisiones de familia, candidatos de FK y ejemplos residuales. | `dev-baja` | — | — | Conteos observados y conciliación documentada contra los valores de entrada 3.930 / 0 / 1.229 / 1.747. Verificar el subconjunto propuesto de 1.549 filas. | `cf_l0_familias_residuales.csv` |
| CF-L1 | Implementar `backend/services/programa_normalizador.py` y aplicar DCF-1 a DCF-3 en `populate_catalogos.py`, `dw_loader.py`, `extraccion.py`, `consolidacion.py`, `revision_acciones_ejecutor.py` y `catalog_service.py` según sus puntos de entrada. Separar POS, versión, edición (`1RA`, `2da.`) y alcance (`- NAL`, `– NAL`). Conservar el umbral de módulos del 80 %. | `dev-media` | CF-L0 | CF-L2 | ≥15 casos pytest, 0 marcadores POS en nombres saneados de programa, 0 valores inválidos `POS--` o `undefined` persistidos en las filas intervenidas, 0 `MOD-GEN` nuevos, 0 FK huérfanas, 0 cambios de PK y 0 cambios adicionales al reejecutar. Dos respaldos verificados antes de escribir. | `cf_l1_catalogo_saneado.csv` |
| CF-L2 | Preparar corpus v2 en `scripts/preparar_corpus_robusto.py` con programas y módulos empresariales, formatos difíciles y ejemplos negativos de `MODULO_RECHAZO`. Usar la salida de solo lectura de CF-L0 y mantener separados los conjuntos de evaluación reservados. | `dev-media` | CF-L0 | CF-L1 | 9 etiquetas IOB2 existentes, máximo 128 tokens, 0 solapamientos de personas entre particiones, SHA-256 y procedencia. Usar `MODULO_RECHAZO` como criterio para ejemplos negativos, sin añadir una etiqueta al modelo. | `cf_l2_corpus_meta.json` |
| CF-L3 | Parametrizar `--epochs` en `scripts/entrenar_beto_robusto.py`. Comparar 2, 3, 4 y 5 épocas en dev con semilla, corpus y métrica comunes. Evaluar el candidato elegido en FP32 e INT8, y versionar el artefacto aprobado, por ejemplo `beto-v3`, para invalidar cachés previas. | `dev-media` | CF-L2 | — | 4 resultados dev, F1 micro ≥0,85 en `test_gold_real` para el artefacto INT8 y mejora en `layouts_5` frente al modelo vigente, revaluado con idéntico conjunto y métrica. Reportar resultados por etiqueta. | `cf_l3_finetuning.json` |
| CF-L4 | Habilitar rescate residual `PROGRAMA`/`MODULO` en `beto_integracion.py`, `extraccion.py`, `evaluacion.py` y `consolidacion.py`, desacoplado de `BETO_TIPOS_FUENTE_CON_PERSONA`. Validar con el normalizador, `modulo_validador.py` y catálogo. Conservar el ruteo de bandeja vigente. | `dev-media` | CF-L1, CF-L3 | — | 0 sobrescrituras A/B, 0 perfiles creados por BETO, 0 `MOD-GEN` nuevos y pruebas verdes de preservación de valores previos, rescate válido, rechazo y ambigüedad. | `cf_l4_cascada_beto.txt` |
| CF-L5 | Medir DataOps pasos ② y ③ en `beto_pg_tmpfs`, con el lote congelado, candidato INT8 y comparación contra la configuración vigente. Aislar ambas bases, incluida la caché persistente en catálogo. Medir caché fría y llena, con restauración de estado comparable entre corridas. | `dev-media` | CF-L4 | — | 3 corridas por condición, tiempos por paso y media/desviación. Reportar tiempo de máquina y total con intervención humana según la metodología del ciclo congelado. RNF-03 <15 min ideal y <20 min aceptable. RNF-04 F1 micro ≥0,85. 0 regresiones en los controles de catálogo y `dim_modulo`. | `cf_l5_rnf03_rnf04.json`, `cf_l5_rnf03_rnf04.csv` |

## Comandos

CF-L0 y CF-L5 deben dejar los comandos reproducibles en sus evidencias, con nombres de bases, huella del lote y configuración efectiva. Reutilizar el procedimiento de `CIERRE_BETO_ACTIVO.md` para preparar tmpfs. Registrar precalentamiento y ajustes de `BETO_WORKERS` o `TORCH_NUM_THREADS` cuando se prueben. Cargar la misma versión del catálogo en cada condición y confirmar el destino de escritura antes de iniciar.

CF-L1, respaldo de las bases de desarrollo antes de aplicar el saneamiento. En el ensayo usar los servicios o destinos equivalentes de la copia aislada.

```powershell
docker compose exec -T db pg_dump -U giragroup_user -Fc giragroup_db -f /tmp/cf_pre_saneamiento.dump
docker compose exec -T catalog_db pg_dump -U giragroup_user -Fc giragroup_catalog_db -f /tmp/cf_pre_catalog.dump
docker compose exec -T db pg_restore --list /tmp/cf_pre_saneamiento.dump
docker compose exec -T catalog_db pg_restore --list /tmp/cf_pre_catalog.dump
```

CF-L3, después de implementar `--epochs` y seleccionar por dev antes de consultar los conjuntos reservados. Cada ejecución usa un directorio de salida nuevo y una ruta de corpus v2 verificada.

```powershell
foreach ($epocaCF in 2..5) {
    .venv\Scripts\python scripts\entrenar_beto_robusto.py --datos output\cf\corpus_v2 --epochs $epocaCF --salida "output\cf\beto_e$epocaCF"
    if ($LASTEXITCODE -ne 0) { throw "Falló el entrenamiento CF con $epocaCF épocas" }
}
```

CF-L1/CF-L4 y cierre. Incluir en la cobertura los módulos intervenidos y contrastar los fallos históricos documentados en `CIERRE_BETO_ACTIVO.md`.

```powershell
.venv\Scripts\python -m pytest tests/cat/ tests/beto_activo/ -q --cov=backend --cov=pipeline --cov-report=term-missing
docker compose up -d --build --no-deps api pipeline
docker compose ps
```

## Controles y prueba manual de Lean

- Mantener 51 tablas y 10 vistas BI en el DW, los umbrales vigentes y el orden CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO. Ensayar con las bases aisladas y preservar el snapshot de solo lectura.
- Seleccionar el checkpoint por dev. Si el candidato INT8 falla RNF-04 o la cascada presenta regresiones, conservar el modelo vigente. Reportar incumplimientos de RNF-03 con sus tiempos observados, sin convertir extrapolaciones en resultados.
- Entregar ejemplos reproducibles con IDs, datos de entrada y resultado esperado. En **Datos Maestros → Módulos**, comprobar un título saneado y una asignatura cuyo nombre se conserva. Revisar dos ofertas de una familia con distintos códigos y confirmar que su alcance y versión siguen reconocibles.
- En una carga de prueba, ejecutar Evaluar y Consolidar. Comprobar un residual con módulo inequívoco vinculado, otro ambiguo enviado a bandeja y una entidad A/B preservada. Acompañar con una consulta de solo lectura para verificar la FK, el código y la ausencia de duplicados al reintentar. Registrar además la verificación pendiente de CAT-L6 en la recarga de prueba aplicable.

Decisiones pendientes para Lean: ninguna para iniciar CF-L0. Elevar cualquier cambio de invariantes o conflicto de identidad de catálogo que no pueda resolverse con evidencia.

Al cerrar: pruebas y cobertura, rebuild de servicios intervenidos, verificación de salud, commit selectivo, y `CIERRE_CATALOGO_FAMILIAS.md` con evidencias, resultados observados y guía de prueba manual. Las cifras de tesis siguen el flujo de congelamiento establecido.

## PROMPT PARA CHAT 2

`/gira-desarrollar`

Ejecuta `docs/cierres/PLAN_CATALOGO_FAMILIAS.md` con agentes `dev-media` y `dev-baja`. Ejecuta primero CF-L0. Coordina CF-L1 y CF-L2 en paralelo sobre salidas separadas. Conserva los cambios locales ajenos y entrega el cierre y los ejemplos de prueba manual.
