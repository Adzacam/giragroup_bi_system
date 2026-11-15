# PLAN F1 — 14 de noviembre de 2026

Objetivo: resolver los pendientes de validez de F0 y preparar la configuración final, la gestión de caché y la integración del entrenamiento BETO, sin cambiar invariantes ni adelantar el congelamiento de F3.

Entrada: `docs/cierres/CIERRE_F0.md`, `PLAN_F0.md`, `plan_maestro.md`, `CLAUDE.md`, `docs/fuente_verdad_tesis.md`, evidencias F0 y skill `gira-planificar`. Rama base observada: `beto-integracion`, commit `2aa5398d917ef503a26bb300cf514ed2ffd1db62`. El código medido en F0 fue `16bba9f6a662233841b8a3b46f0d98354931e218`; no confundirlo con el commit de cierre.

El texto pegado del chat anterior es un registro histórico de recuperación, no una orden para reanudar tareas o demonios. El cierre informa **42 corridas válidas terminadas y tmpfs desmontado**. No quedan tres corridas F0 por lanzar. No ejecutar los task IDs antiguos ni mantener procesos de energía por ese registro.

## Qué sigue y qué aún no está resuelto

La fase nominal siguiente es **F1**, conforme a §5 del plan maestro: decisiones A-5/A-9 y ejecución A-7/A-8/A-10. El cierre de F0 es una entrega de evidencia con pendientes, no una aceptación total de A-3/A-4.

Antes de decisiones dependientes, completar o documentar estos arrastres de F0, sin alterar sus archivos sellados:

- A-3: 90 contextos con sugerencias automáticas; **0 validaciones humanas**. El porcentaje sugerido por el script no acredita tasa real de falsos desacuerdos.
- A-4: 7 casos únicos elegibles, **0 decisiones humanas válidas**, top-1=N/D. Las réplicas y configuraciones no multiplican el número de decisiones independientes.
- Referencia `73ec78f` con el lote F0: no ejecutada. Antes de afirmar equivalencia actual con flags apagados, obtenerla con los mismos bytes o mantener explícitamente esa limitación.
- KPI-10/11 son NULL en la ablación F0. Preservar NULL y no afirmar una mejora cuantificada del KPI a partir de ellos. Su cobertura/cálculo final pertenece a B-2/F2.

## Propuesta concreta de decisiones para Lean (sin aprobación todavía)

### D1 / A-5: flags

**Propuesta conservadora:** mantener por ahora los cuatro flags en `False`: `BETO_CASCADA_FINAL`, `BETO_ACUERDO_QC`, `BETO_SUGERENCIA_HITL`, `BETO_VENTANA`. Esto conserva la configuración actual; no elimina el BETO ya presente en el sistema base. Registrar aprobación o alternativa de Lean antes de declarar defaults finales.

| Configuración | Evidencia F0 | Implicación para decidir |
|---|---|---|
| a0, todo apagado | Máquina caché vacía 803,58±173,04 s (13,39 min); llena 210,08±7,24 s | Referencia conservadora; falta revisión humana/KLM del ciclo completo. |
| a1, cascada final | Vacía 739,61±11,12 s (12,32 min); llena 206,33±1,74 s; 1 resolución BETO reportada en lectura y 1 en consolidación; bandeja y KPI-18 iguales a a0 | Es candidata a habilitar, pero no sumar etapas como dos personas ni interpretar la diferencia de tiempo como aceleración causal. Trazar y validar el rescate y comparar huellas antes de proponerla como default. |
| a2 / a12 / a123 | Caché vacía 18,50 / 17,76 / 17,81 min; sin ventana 34,09 % no evaluables en la comparación reportada | Tiempo automático ya por encima de la meta; QC pendiente de validación humana. No recomendar activación persistente con esta evidencia. |
| a2w | No evaluables 17,89 %; caché vacía 37,43 min; llena 3,60 min | Cumple la puerta de cobertura A-2 reportada, pero supera 20 min incluso antes de sumar revisión. No activar por defecto sobre esta base. |
| a3 | Top-1 aún N/D | No justificar activación por una eficacia humana que no se ha medido. |

Fuentes: `docs/mediciones/f0_ablacion.csv`, `f0_ventana.json`, `f0_top1_resumen.json`. Distinguir etapas y denominadores de `f0_ventana.json`; no convertir una tasa de la etapa reportada en afirmación sobre todas las etapas.

Los tiempos F0 son de máquina sin revisión. **No certifican RNF-03 del ciclo final**. La adopción de un modelo nuevo invalida su traslado como resultado del nuevo modelo: volver a comprobar la configuración elegida y medir el ciclo final en F3.

### D2 / A-9: caché y las 50 tablas

Preparar primero un inventario físico por esquema, distinguiendo snapshot histórico, copia actual y objetivo. La fuente de verdad histórica ya incluye `cache_indice_beto` dentro de sus 50 tablas; no excluir todas las cachés por analogía ni reescribir ese inventario.

Propuesta para revisión de Lean: describir `cache_beto_entidades` como caché operativa adicional separada del inventario DW declarado, **solo si Lean confirma expresamente ese alcance** y el inventario permite describir ambos conteos sin afirmar un total físico falso. Hasta esa decisión, no cambiar definiciones ni afirmar que agregarla mantiene 50 tablas físicas. Si cumplir 50 exige mover/alterar esquema, no ejecutar esa solución: elevarla como cambio de invariante.

### D3: adopción del checkpoint y destino de integración

El estado observado es `beto-entrenamiento` en `9888539`, con worktree separado `giragroup_beto_wt`. Su documentación indica endurecimiento del proceso, **sin entrenamiento ejecutado**. Tiene cambios en 18 archivos respecto de su base común, incluidos scripts, Makefile, dependencias, pruebas y `backend/routers/dataops/maestros.py`; no es una rama de pesos ya validados.

Preparar A-8 y la integración en `beto-integracion`. No modificar el worktree ajeno, no hacer push y no integrar en `main` implícitamente. La adopción del checkpoint en servicio solo procede tras evaluación y decisión escrita de Lean, con hash y ruta concretos. No sustituir el modelo vigente para averiguar si el nuevo funciona.

## Tareas, agentes, dependencias y aceptación

Las salidas de la tabla son relativas a `docs/mediciones/`. No se ejecuta desarrollo desde este chat de planificación.

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio medible | Salida |
|---|---|---|---|---|---|---|
| F1-P | Verificar cierre, recuperar lote y preparar aislamiento | dev-alta | CIERRE_F0 | Inventario A-9 y revisión humana offline | 10 originales+10 slices con huella global `aafde8adc246af13c4eeb9ffbf766eda4348cfb6e855860d0bf00bcd24cbdb60`; 0 cambios snapshot; commit/modelo/puerto/rutas registrados | `f1_preflight.json`, `f1_snapshot_antes.json`, `f1_snapshot_despues.json` |
| F0-R3 | Incorporar revisión humana de desacuerdos | dev-media + revisor humano | Paquete F0 privado intacto | F0-R4, inventarios | 90/90 contextos con etiqueta independiente o cobertura incompleta explícita; tasa por etapa/estrato y casos indeterminados; conservar limitación de logs agregados | `f1_a3_decisiones.csv`, `f1_a3_validacion.json` |
| F0-R4 | Incorporar decisiones ciegas top-1 | dev-media + revisor humano | Paquete F0 sellado | F0-R3 y auditorías | 7 casos únicos revisados o pendientes explícitos; coincidencias/N válidas por configuración; exclusiones y cobertura; 0 etiquetas simuladas | `f1_a4_decisiones.csv`, `f1_a4_validacion.json` |
| F0-R0 | Referencia de código base con lote F0 | dev-alta | F1-P | Revisión humana offline | 1 referencia `73ec78f` y 1 a0 F0, mismo lote/estado de caché; 0 diferencias de huella esperadas; si difieren, análisis y bloqueo de afirmación de equivalencia | `f1_base.json`, `f1_base.json.huella.json`, `f1_off.json`, `f1_off.json.huella.json`, `f1_comparacion_base.txt` |
| A-5 | Formalizar flags | Lean + planificación; dev-media aplica lo aprobado | D1; revisión de rescate si se elige a1; A-8 si cambia modelo | A-9 | 4 valores explícitos, justificación, hash modelo, aprobación atribuible a Lean; 0 overrides inadvertidos del entorno | `f1_decision_flags.json` |
| A-9 | Inventario y decisión de alcance caché | dev-baja inventaría; Lean decide | D2 | F0-R3/R4, auditoría A-8 | Conteo físico reproducible public/bi/tablas/vistas; 1 decisión escrita; 0 ocultación de objetos extra | `f1_inventario_objetos.csv`, `f1_decision_cache.json` |
| A-7 | Herramienta de purga de entidades | dev-baja | A-9 para tratamiento de esquema; DB objetivo aislada | Evaluación offline A-8, sin tocar archivos comunes | Purga explícita aislada: filas antes>0 y después=0; segunda ejecución idempotente; 0 cambios fuera de caché; pruebas de tabla ausente y destino prohibido | `f1_purga_cache.json` |
| A-8a | Auditar e integrar endurecimiento | dev-alta | F1-P; revisión diff de 9888539 | Revisión humana e inventario | Revisar 18 archivos/diff real; 0 cambios de invariantes; 0 regresiones de pruebas de integración F0; preservar parametrización B-10 | `f1_a8_integracion.md` |
| A-8b | Corpus independiente y un entrenamiento | dev-alta | A-8a | Revisión humana; sin cronómetros/inferencia compartida | 2 generaciones a rutas nuevas con hashes idénticos; 0 personas normalizadas compartidas en 3 cruces train/dev/test; 1 entrenamiento CPU/FP32, 128 tokens, 3 épocas y selección solo por dev; hashes completos | `f1_corpus_auditoria.json`, `f1_training_info.json`, `f1_modelo_manifest.json` |
| A-8c | Comparar checkpoints con mismo evaluador | dev-alta | A-8b y baseline capturada antes | Análisis offline | 2 modelos × 3 conjuntos (gold_510, layouts_5, test.conll) × estricto/relajado; TP/FP/FN/P/R/F1 por tipo y micro; sin truncamiento silencioso ni fallback | `f1_evaluacion_antes/`, `f1_evaluacion_despues/`, `f1_modelo_comparacion.json` |
| F1-V | Verificar configuración candidata final | dev-alta | A-5, A-9, A-8c y decisión de adopción | Ninguna carga pesada concurrente | 3 corridas por caché vacía/llena = 6 válidas con flags/modelo decididos; hashes lote pre/post; media/DE y huellas; criterio humano de aporte si flag activo | `f1_validacion_<estado>_r<n>.json` y acompañantes; `f1_validacion_resumen.json` |
| A-10 | Integración final, pruebas, commit y rebuild | dev-baja | Puertas anteriores y aprobaciones necesarias | Ninguna mutación concurrente | 0 fallos nuevos; pruebas/cobertura reales; 9 servicios Up y salud comprobada según soporte; commit trazable; sin merge/push a main | `f1_pruebas.txt`, `f1_servicios.txt`, `f1_cierre_manifest.json` |

Asignación: una única persona/agente `dev-alta` conserva completa cada tarea alta; no dividir el entrenamiento ni sus evaluaciones entre agentes. F0-R3 y F0-R4 pueden hacerse en paralelo si usan salidas distintas y revisores que mantienen el cegamiento. A-7 y A-9 pueden compartir `dev-baja`. Serializar cualquier modificación del índice Git, configuración, modelo, entorno o servicios.

F0-R3/R4 siguen siendo pendientes de **F0**, registrados como arrastre, no resultados inventados de F1. Si falta intervención humana, preparar todo lo independiente y cerrar con pendientes; no declarar que esa validación terminó. Si D1 mantiene QC/sugerencias apagados, esos pendientes no obligan a bloquear auditorías o la preparación del entrenamiento; sí bloquean afirmar su eficacia validada.

## Comandos y procedimiento para Chat 2

Bloques POSIX: ejecutar en Git Bash desde raíz. Comandos de inspección no implican aprobar decisiones. Los programas de purga y agregación F1 aún no existen: Chat 2 puede implementar auxiliares limitados a estas tareas, documentar su CLI y probar los controles; no fingir una ejecución disponible.

### 1. Preflight, datos y puertos

```bash
git status --short
git rev-parse HEAD
git worktree list
git log -1 --oneline beto-entrenamiento
git diff --stat beto-integracion...beto-entrenamiento
python scripts/medir_f0.py verificar --manifest docs/mediciones/f0_lote_manifest.json
docker compose ps
```

No regenerar ni volver a congelar el lote para corregir un hash. Si la copia privada falta, recuperar los bytes originales con el manifiesto; detener únicamente las mediciones dependientes si no se pueden recuperar. No correr `medir_f0.py series` para iniciar F1: administra la serie F0 y sus salidas.

La recuperación F0 usó puerto host **55632** por exclusión Windows de **55432**. `scripts/aislada_tmpfs.sh` aún contiene 55432 fijo; no afirmar que soporta una variable de puerto que no existe. Autorizar parametrización acotada del puerto de host para el laboratorio y registro del valor real, conservando la conexión entre contenedores `beto_pg_tmpfs:5432`. Elegir un puerto libre verificado sin cambiar puertos de DB viva. Solo después preparar laboratorio mediante `up`/`vacio` y comprobar fidelidad con SELECT/huellas antes de vaciar la plantilla. No ejecutar `up` sobre un laboratorio existente con evidencia aún sin exportar: elimina el contenedor anterior.

Crear copias separadas para referencia, validación y pruebas; `giragroup_db` dentro de `beto_pg_tmpfs` es copia, no el contenedor vivo homónimo. Registrar host/contenedor/base en cada reporte, sin credenciales productivas. Mantener catálogo en `catalogo_copia`.

### 2. Revisión humana sin inferencias nuevas

Conservar `docs/mediciones/f0_top1_resumen.json` y los paquetes sellados. El paquete privado observado está en `output/backups/f0_lote/revision_ciega/final/`: `casos.json` y `rankings_privados_no_mostrar.json`. No mostrar rankings/score al revisor antes de recoger decisiones. El agente planificador ya inspeccionó parte de los rankings públicos; no puede sustituir al revisor independiente.

Comando existente, cuando el revisor entregue el CSV en el formato `DECISION_FIELDS` de `scripts/f0_revision_humana.py`:

```bash
python scripts/f0_revision_humana.py --package output/backups/f0_lote/revision_ciega/final/casos.json --rankings output/backups/f0_lote/revision_ciega/final/rankings_privados_no_mostrar.json --manifest docs/mediciones/f0_top1_resumen.json --decisions docs/mediciones/f1_a4_decisiones.csv --output docs/mediciones/f1_a4_validacion.json
```

Validar el contrato real de los JSON con el script antes de ejecutarlo; no cambiar hashes/atestaciones para aceptar un CSV inválido. No sobrescribir `f0_top1_decisiones.csv`. A-3 usa `output/backups/f0_lote/revision_desacuerdos/final.json`: exportar vista sin sugerencia automática, recoger etiqueta humana y conciliar por ID. No publicar nombres, texto o CI en evidencias versionadas.

### 3. Rama de entrenamiento y baseline

Primero revisar de solo lectura el diff completo y el informe:

```bash
git diff beto-integracion...beto-entrenamiento
git show beto-entrenamiento:docs/auditoria/beto_entrenamiento_endurecimiento.md
```

Integrar el código de `9888539` en **beto-integracion** como parte de A-8a/A-10, preservando cambios F0 y B-10. No arrastrar automáticamente trabajo local ajeno. Las reglas de resolución de conflictos son mantener invariantes y pruebas, no escoger todo un lado. Si un conflicto exige cambiar un invariante, detener esa parte y elevarlo. No cambiar defaults antes de D1.

Tras integrar las ayudas, ejecutar en entorno del proyecto con dependencias verificadas contra `requirements-lock.txt` (no instalar a ciegas en el entorno compartido). Capturar primero el checkpoint vigente con el mismo evaluador que se usará después:

```bash
PYTHONHASHSEED=0 PYTHONUTF8=1 BETO_INT8=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python scripts/evaluar_beto_checkpoint.py --modelo pipeline/semantic/beto_local --gold data/test_gold_real.jsonl --salida docs/mediciones/f1_evaluacion_antes
```

Antes de ejecutar, comprobar que esa ruta contiene el checkpoint usado realmente por :8006; si difiere, usar su ruta verificada y registrarla, no caer a modelo remoto. Los conjuntos deben conservar identidad semántica y hashes documentados, incluidos cambios de LF. Mantener el test fijo; no usarlo para escoger época o retocar entrenamiento.

Generar el corpus dos veces en directorios nuevos bajo `output/f1/`, auditar independencia y determinismo; este comando es una de las dos generaciones:

```bash
PYTHONHASHSEED=0 PYTHONUTF8=1 python scripts/preparar_corpus_robusto.py --salida output/f1/corpus_verificacion_1 --fraccion-dev 0.2 --semilla 42
PYTHONHASHSEED=0 PYTHONUTF8=1 python scripts/preparar_corpus_robusto.py --salida output/f1/corpus_verificacion_2 --fraccion-dev 0.2 --semilla 42
```

Si las puertas pasan, realizar **un solo entrenamiento** con la orquestación existente y ruta nueva/vacía:

```bash
BETO_SALIDA=output/f1/reproduccion_1 PYTHON=.venv/Scripts/python.exe bash scripts/beto_reproducir.sh
```

El target vuelve a generar su corpus dentro de esa salida: verificar identidad con las dos generaciones anteriores antes de aceptar el entrenamiento. Conserva los pesos vigentes; el script no despliega en `pipeline/`. Copiar metadatos/métricas/predicciones sanitizadas a las salidas F1 y mantener pesos/datos privados fuera de Git. No ejecutar múltiples entrenamientos buscando el mejor test.

```bash
PYTHONHASHSEED=0 PYTHONUTF8=1 BETO_INT8=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python scripts/evaluar_beto_checkpoint.py --modelo output/f1/reproduccion_1/modelo --gold data/test_gold_real.jsonl --salida docs/mediciones/f1_evaluacion_despues
```

Comparar baseline/candidato con idéntico protocolo, además del informe del target. F0 Modo C y el evaluador de tokens gold no necesariamente implementan el mismo protocolo: no restar sus F1 como si fueran equivalentes. Publicar matriz real por token con O y confusiones, separada de TP/FP/FN por entidad.

Puerta propuesta de adopción: gold_510 F1 micro estricto≥0,85 y sin degradación frente a baseline en gold_510/layouts_5 bajo el mismo protocolo; registrar también test.conll. El informe de entrenamiento advierte F1 histórico test.conll=0,7147: no ocultarlo ni afirmar cumplimiento RNF-04 para todo conjunto a partir de gold_510. Si hay regresión, cobertura/truncamiento o discrepancia de protocolo, no desplegar; presentar comparación a Lean. La cifra 0,001 de ese informe es una tolerancia propuesta, no autorización para ignorar diferencias. No reparar la falta de revisión humana del gold reetiquetando automáticamente.

### 4. Purga y decisión de caché

A-7 implementa purga explícita y verificable de `cache_beto_entidades`, sin cambiar banda, inferencia ni entidades de negocio. Probar en copia aislada: tabla presente con filas, vacía y ausente; segundo intento; hash/conteos de tablas ajenas antes/después. Guardar solo conteos/fechas/hash de destino. No ampliar a borrado de todas las cachés ni a scheduler/TTL sin requisito escrito. La retención automática es una decisión separada si se considera necesaria.

La comprobación aislada y su comando documentado satisfacen la implementación técnica. Una purga sobre DB viva requiere identificar explícitamente esa base y una ventana autorizada: la petición actual de planificación no autoriza ejecutar borrados. Nunca purgar snapshot. Tras cambiar pesos/configuración, evitar reutilizar entidades del modelo anterior: verificar que la clave de caché incorpora la identidad correcta o invalidar únicamente la caché aislada de la evaluación. No usar los seeds de F0 como caché válida del nuevo checkpoint.

### 5. Validación, cierre y entrega

F1-V repite solamente la configuración **decidida** con modelo final, seis corridas, mismo lote, caché pre/post comprobada y huellas. Copiar el árbol final a una ruta distinta de `/tmp/medida` de F0. Añadir un ejecutor F1 si es necesario: `medir_f0.py` puede rechazar nombres/prefijos nuevos, no editar metadatos para eludir esa validación ni escribir sobre artefactos F0. Son pruebas de aceptación del cambio; B-7 sigue siendo la medición del ciclo final en F3, con revisión/KLM conforme a su plan.

Suite final con Python del proyecto, en Git Bash; sustituir el puerto por el **observado y verificado**, sin tocar URLs productivas:

```bash
DATABASE_URL=postgresql://giragroup_user:tmpfs_local@127.0.0.1:55632/giragroup_db CATALOG_DATABASE_URL=postgresql://giragroup_user:tmpfs_local@127.0.0.1:55632/catalogo_copia python -m pytest tests --cov=backend --cov=pipeline > docs/mediciones/f1_pruebas.txt 2>&1
```

La credencial `tmpfs_local` es desechable del laboratorio. 802/784/11/7 y 70 % son antecedentes F0, no expectativas impuestas: registrar resultados y cobertura exactos nuevos. Evitar la fragilidad vista en F0 del test que exige el nombre `giragroup_db`: comprobar aislamiento por servidor/puerto real, no inferirlo solo por nombre.

Solo tras decidir adopción/configuración y terminar cronómetros, reconstruir lo tocado:

```bash
docker compose up -d --build api pipeline
# Si hubo cambios frontend, el servicio real se llama web:
docker compose up -d --build web
docker compose ps
```

No reconstruir `web` si no fue tocado. :8006 es compartido: coordinar reinicio, registrar código/modelo efectivo y verificar salud antes de inferir. Un 401 del CMI acredita autenticación, no funcionamiento del cálculo: verificar también el endpoint con usuario autorizado en copia aislada, sin registrar tokens.

Preparar commit selectivo F1, comprobar ausencia de datos personales/secretos y preservar instrucciones locales preexistentes no versionadas. No usar `git add -A` para incorporar archivos ajenos al plan. Documentar integración de `9888539` y hashes medidos. Exportar pruebas, decisiones y huellas antes de desmontar tmpfs. Cerrar con `docs/cierres/CIERRE_F1.md` conforme a la plantilla: realizado/no realizado, flags efectivos, checkpoint vigente/candidato/adoptado, conteo de caché decidido, pruebas, servicios y riesgos.

No declarar F1 totalmente cumplida si faltan D1/D2/adopción necesaria, merge autorizado o verificaciones. Preparar un cierre parcial honesto y enumerar los bloqueos. No tocar docx ni `fuente_verdad_tesis.md`, no producir cifras finales ni figuras F4. Después de un cierre F1 aceptado, volver a planificación para F2 (B-1/B-2/B-6); F3 será congelamiento y medición final.

## DECISIONES PENDIENTES PARA LEAN

1. **D1 / A-5:** aprobar mantener los cuatro flags apagados como configuración propuesta, o pedir a1 tras validar el rescate. No activar QC/ventana/sugerencias sobre evidencia humana inexistente.
2. **D2 / A-9:** confirmar el alcance de las 50 tablas tras inventariar `cache_beto_entidades`. Separar caché operativa en la descripción es propuesta pendiente, no una modificación ya autorizada de las cifras físicas.
3. **D3:** adoptar o conservar checkpoint tras evaluar A-8; decisión con hashes y evidencia concreta. La autorización metodológica del plan maestro para integrar A-8 no convierte un entrenamiento exitoso en permiso para desplegar cualquier resultado.
4. **Revisión humana:** asignar revisor independiente para los 90 contextos A-3 y 7 casos A-4. Mostrar primero paquetes ciegos; no pedir a un agente que invente respuestas humanas.
5. **B-10 residual:** rotación de contraseña activa y reescritura de historial siguen pendientes. No incluirlas implícitamente en A-10 ni reproducir secretos en comandos/reporte.
6. **Cualquier invariante:** si una solución exige cambiar cascada, umbrales, modelo base, 128 tokens, estados, catálogo, inventario declarado, KPI, pronóstico, requisitos o infraestructura, detener esa solución y presentar la decisión a Lean. Todo lo independiente continúa.

Estas puertas proceden del plan maestro (A-5/A-9: decisión de Lean) y de la skill local de planificación: «Si una tarea exige cambiar un invariante, no la planifiques: ponla en DECISIONES PENDIENTES». El plan queda preparado para revisión; no atribuir aprobaciones a Lean por silencio o por el mero envío del prompt al chat 2.

## PROMPT PARA CHAT 2

```text
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F1.md. Lee CLAUDE.md, tu skill y CIERRE_F0.md. Base observada: beto-integracion 2aa5398; beto-entrenamiento 9888539 es endurecimiento sin modelo nuevo entrenado.

F0 terminó sus 42 corridas y desmontó tmpfs. El registro pegado es histórico: no reanudes las tres corridas antiguas ni task IDs. Preserva lote SHA-256 aafde8adc246af13c4eeb9ffbf766eda4348cfb6e855860d0bf00bcd24cbdb60 y todas las evidencias selladas.

Trabaja por dependencias. Prepara primero tareas independientes: aislamiento/puerto real, auditoría de integración y esquema, baseline y paquetes de revisión humana. D1/D2/D3 no están aprobadas por el mero envío de este prompt: no fijes defaults, alteres alcance de 50 tablas ni despliegues un checkpoint sin la correspondiente decisión escrita de Lean. Conserva cuatro flags apagados mientras no exista otra decisión.

dev-alta lleva referencia 73ec78f sobre el lote F0, integración de ayudas de entrenamiento, dos generaciones de corpus para auditar determinismo e independencia, un único entrenamiento y evaluación comparable de ambos checkpoints. No fragmentes tareas altas ni corras entrenamiento/inferencia pesada junto a cronómetros. Mantén el worktree beto-entrenamiento ajeno intacto y preserva saneamiento B-10.

dev-media incorpora revisiones humanas reales de A-3 y A-4: 90 contextos y 7 casos únicos. No uses sugerencias automáticas o simulación como decisiones humanas; si faltan, entrega paquetes y deja esas tasas pendientes. dev-baja inventaría tablas/caché, implementa y prueba purga explícita sobre copia aislada y prepara cierre/integración de lo autorizado.

No regeneres lote, no alteres gold vigente, no entrenes buscando mejorar test, no publiques nombres/CI/pesos, no escribas en snapshot o DW viva. Verifica el puerto: F0 usó 55632 tras fallar 55432; el script original tiene 55432 fijo. Parametriza solo laboratorio si hace falta, registrando destino real.

Tras decisiones y evaluación, verifica la configuración/modelo elegidos con seis corridas nuevas F1, sin reutilizar seeds del modelo previo ni sobrescribir F0. No afirmes RNF-03 final con tiempos de máquina. Prueba/cobertura sobre copia aislada, rebuild de servicios realmente tocados al terminar las mediciones, salud y commit selectivo. No push ni merge implícito a main. Entrega CIERRE_F1.md con decisiones, hashes, pendientes y evidencia; no declares fase completa si una puerta sigue abierta. No tocar docx/fuente de verdad ni adelantar F2/F3/F4.
```
