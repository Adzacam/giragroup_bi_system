# PLAN F0 — 13 de noviembre de 2026

Objetivo: medir las opciones BETO sobre un único lote congelado y una copia aislada, sin cambiar defaults ni invariantes, y producir evidencia para decidir en F1.

Entrada: no hay `CIERRE_*.md` ni `FIGURAS_*.md` previos en `docs/cierres/`. Rama observada: `beto-integracion`, commit `16bba9f6a662233841b8a3b46f0d98354931e218`. El árbol contiene instrucciones locales sin seguimiento; no incorporarlas automáticamente al commit de F0.

Fuentes leídas: `CLAUDE.md`, `.claude/skills/gira-planificar/SKILL.md`, `.claude/skills/gira-desarrollar/SKILL.md`, `docs/cierres/plan_maestro.md` (especialmente §§3–5), `docs/fuente_verdad_tesis.md` y `docs/auditoria/beto_integracion_implementacion.md`. Esta última es la ubicación real del archivo citado en el prompt como `docs/beto_integracion_implementacion.md`.

## Alcance y límites

F0 comprende A-1, A-2, A-3, A-4 y A-6; B-3, B-4, B-5 y B-10 avanzan en paralelo con las restricciones de recursos indicadas abajo. No comprende A-5/7/8/9/10, B-1/2/6/7 ni las tareas opcionales de fases siguientes. No hay entrenamiento, merge, selección de flags finales, purga de la base viva ni congelamiento nuevo de la fuente de verdad. El cierre sí incluye pruebas, commit de F0 y reconstrucción de lo efectivamente tocado según la skill de desarrollo.

Se mantienen **todos** los invariantes de la §3 del plan maestro: cascada CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO; BETO solo en residuales, sin sobrescribir A/B ni crear perfiles; umbrales 0,92 / 90 / 85 / 80 y bandas 0,85 / 0,60; estados A/B/C; catálogo institucional sin personas; modelo `dccuchile/bert-base-spanish-wwm-cased`, IOB2 y 128 tokens; DW de 50 tablas + 9 vistas bi, 9 hechos, 7 dimensiones y 1 puente e idempotencia por `carga_fila_origen`; 22 KPI y endpoint CMI declarado; Holt-Winters amortiguado m=12 y hold-out de 6 meses, OLS mensual N=40 y anual descriptiva; 11 RF, 7 RNF, 12 HU, 6 sprints; RNF-03 <15 min (aceptable <20) y RNF-04 F1≥0,85; 9 servicios sin licencias comerciales; snapshot inmutable y mediciones en tmpfs. F0 no resuelve si la caché cuenta en las 50 tablas.

## Paso previo obligatorio: F0-P, congelar entrada y entorno

Responsable: `dev-alta` (protocolo y validación), con inventario mecánico de `dev-baja`. No iniciar corridas hasta pasar esta puerta.

1. Inventariar los XLSX de `uploads/data`; exigir exactamente **10 archivos** elegibles y registrar orden, nombres y tamaños. Si no son 10, detener solo la medición y pedir a Lean la composición del lote; no escoger silenciosamente.
2. Copiar los originales a un directorio privado de trabajo congelado. Generar **una sola vez** los 10 slices, con mes objetivo explícito `2026-03` y `CICLO_FILAS_SIN_FECHA=0`, usando `construir_slices()` de `scripts/medir_ciclo_mensual.py`, sin ejecutar su `main()` de procesamiento. Registrar mes efectivamente elegido por hoja, incluidos los fallback al mes más frecuente. Exigir 10 slices, sin omitidos.
3. Registrar SHA-256 y bytes de cada original y cada slice; número de hojas y filas; algoritmo de selección; orden real del flujo (ANTIGUO al final); versión del generador; fecha con zona America/La_Paz. Huella global: SHA-256 de un manifiesto canónico UTF-8 de rutas relativas ordenadas, tamaños y SHA-256, con serialización documentada. Guardar `docs/mediciones/f0_lote_manifest.json` y `f0_lote_sha256.txt`.
4. Conservar una copia recuperable de los bytes fuera del volumen efímero tmpfs, en almacenamiento local privado; registrar su ubicación sin versionar datos personales. Los JSON/CSV de evidencia usan IDs, hashes y CI enmascarado. No regenerar XLSX: openpyxl puede cambiar bytes aunque las celdas coincidan.
5. Instalar los slices exactos en `giragroup_api:/tmp/slices_flujo`; fijar también la lista de originales que descubre el generador. Atención: los scripts copiados se ejecutan desde `/tmp/flujo/scripts`, por lo que su `ROOT` es `/tmp/flujo`, no `/tmp/medida`. Preparar `/tmp/flujo/uploads/data` con los originales congelados y sustituir en la copia `/tmp/medida` el enlace a `/app/uploads` por la entrada congelada. No modificar `/app/uploads` ni el directorio vivo. Crear `/tmp/flujo/scripts` antes del wrapper.
6. Verificar el manifiesto **antes y después de cada corrida**, con `CICLO_REUSAR_SLICES=1`. Como el generador puede crear slices faltantes incluso con ese flag, abortar ante cualquier archivo faltante/extra o hash distinto, antes de llamarlo. Guardar verificación por corrida en `f0_<config>_<estado>_r<n>.meta.json`.
7. Registrar commit, diff local relevante, hash del árbol copiado, imagen/contenedor y pesos/tokenizador BETO, CPU/RAM, workers=2, stride=32, dispositivo, variables efectivas y versiones en `f0_entorno.json`. Fijar los cuatro flags por corrida, incluso los apagados; no heredar valores del contenedor.
8. Verificar huella del snapshot antes/después y fidelidad inicial de su copia antes de `vacio`. Guardar `f0_snapshot_antes.json`, `f0_snapshot_despues.json` y `f0_snapshot_copia.json`; exigir 0 diferencias entre antes/después y entre origen/copia inicial. No comparar el resultado del lote con el DW histórico esperando identidad: son cargas distintas.

Las 12.992 líneas/182 casos y 15.926/194 son antecedentes de lotes distintos, **no objetivos ni resultados de F0**. Registrar los conteos que produzcan los bytes congelados.

## Tareas, dependencias y aceptación

Todos los nombres de salida de la tabla son relativos a `docs/mediciones/`.

| ID | Tarea ordenada | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida |
|---|---|---|---|---|---|---|
| F0-P | Congelar lote, entorno, copias y protocolo de caché | dev-alta | Ninguna | B-4; inventario B-10 | 10 originales + 10 slices; 100 % hashes verificados; 0 diferencias origen/copia inicial | `f0_lote_manifest.json`, `f0_lote_sha256.txt`, `f0_entorno.json`, huellas anteriores |
| A-1 | Ablación a0,a1,a2,a3,a12,a123 | dev-alta | F0-P y soporte de medición validado | B-4/B-5/B-10 sin consumo o cambios del entorno medido | 6 configuraciones × 2 estados de caché × 3 corridas válidas = **36**; hechos, staging, bandeja casos/grupos, KPI-10/11/18, contadores y tiempo por etapa/total; media y DE muestral n−1 por celda | 36 `f0_<config>_<estado>_r<n>.json` + `.json.huella.json` + `.meta.json`; `f0_ablacion.json`, `.csv` |
| A-2 | Opción 2 con ventana: a2w frente a a2 | dev-alta | A-1 | B-4; análisis A-3 de celdas ya cerradas | **6** corridas adicionales (2 estados × 3); mismo lote; `no_evaluables / comparadas_acuerdo < 0,20` con denominador >0 en lectura y consolidación por separado; informar también tasa de acuerdo evaluable | `f0_a2w_<estado>_r<n>.*`, `f0_ventana.json` |
| A-3 | Revisar desacuerdos por archivo/tipo/persona | dev-media | A-1 y A-2 para análisis final | A-4, B-3/B-4/B-5/B-10 | Censo si N≤100; si N>100, muestra ≥100, estratificada por archivo/tipo/rol y con ≥1 caso por estrato no vacío; semilla 42, IDs y tamaños; 100 % muestra etiquetada por revisión; falsos/n revisados y cobertura por estrato | `f0_desacuerdos_muestra.csv`, `f0_desacuerdos_resumen.json` |
| A-4 | Validar ranking top-1 con decisiones del revisor | dev-media | A-1 (a3/a123); referencia humana independiente | A-3/A-6 y B | Censo de casos con sugerencias si N≤100 o muestra ≥100 si N>100 (semilla 42); decisiones humanas reales, IDs enlazables y ranking previo inmutable; top-1=coincidencias/N decisiones válidas; N=0 => N/D, nunca 0 % | `f0_top1_candidatos.csv`, `f0_top1_decisiones.csv`, `f0_top1_resumen.json` |
| A-6 | Efecto de QC en KPI y derivación | dev-media | A-1/A-2/A-3; esperar cierre A-4 en el orden principal | B y análisis independientes | 4 contrastes: a0→a2, a1→a12, a2→a2w y a3→a123, separados por caché; 100 % KPI-10/11/18, bandeja/staging y bandas con numerador, denominador, unidad y delta; nulos justificados | `f0_impacto_qc.csv`, `f0_impacto_qc.json` |
| B-3 | Conciliar 503/510 y obtener TP/FP/FN estrictos y relajados por modo A/B/C | dev-media | Inventario de gold/modelo; ventana exclusiva de CPU | B-4/B-5/B-10; nunca inferencia A-1/A-2 simultánea | 3 modos × 2 criterios = **6** filas con TP/FP/FN, P/R/F1 recalculables; soporte por tipo; explicar 503/510 por IDs y definición, sin forzar 510; hash de gold, predicciones y política de matching 1:1 | `f0_b3_ablacion.json`, `.csv`, `f0_b3_conteos.json`, `f0_b3_conciliacion.md` |
| B-4 | Auditar aumento/separación, fuga y anotación gold | dev-media | Código/datasets disponibles | Todas, sin entrenamiento ni inferencia pesada | 3 cruces train–dev/train–gold/dev–gold con conteo exacto y normalizado; familias de aumento y origen; orden real y semilla documentados; procedencia de anotación y evidencia de revisión; faltantes explícitos | `f0_b4_auditoria.json`, `f0_b4_auditoria.md` |
| B-5 | Conciliar OLS anual 2025 y ejecutado de KPI-03 | dev-baja | Copia histórica aislada intacta | A/B si consultas livianas no perturban tiempos | 1 comparación 2025 reproducible con serie anual, filtros/categorías, ejecutado, meta, KPI %, valor ajustado OLS y diferencias; no confundir monto observado con ajustado | `f0_b5_consultas.sql`, `f0_b5_2025.json` |
| B-10 | Retirar contraseña PostgreSQL expuesta de archivos actuales | dev-baja | Inventario sin imprimir secretos | Auditorías; cambios antes de congelar entorno o después de cronometrar | 0 apariciones del secreto identificado en archivos versionables actuales; configuración por entorno sin fallback secreto; diff/reporte redactados; 0 credenciales en evidencia nueva | `f0_b10_saneamiento.json` |

Una tarea alta corresponde a **un solo agente**, sin repartir sus corridas. El mismo `dev-alta` lleva A-1 y después A-2. A-3/A-4/A-6 pueden compartir un `dev-media` o separarse si sus archivos de salida son distintos. La secuencia principal de cierre es F0-P → A-1 → A-2 → A-3 → A-4 → A-6; se permite adelantar análisis de artefactos completos e inmutables. No se ejecutan dos cargas cronometradas juntas.

La tasa de A-2 usa `comparadas_acuerdo` como total y debe conciliarlo con acuerdos + desacuerdos + tipo_distinto + no_evaluables según el código vigente. Publicar además `acuerdos/(acuerdos+desacuerdos)` y su cobertura, sin confundirla con `tasa_acuerdo` implementada. No sumar lectura y consolidación: pueden medir las mismas personas dos veces. Si no se logra <20 %, A-2 queda no cumplida con evidencia; no se cambia el umbral para aprobarla.

A-3 clasifica: desacuerdo real, falso por fragmentación (incluido «ED»+«GAR»), truncamiento/no evaluable, tipo distinto e indeterminado. Con muestreo estratificado publicar porcentajes por estrato y estimación ponderada por población; no presentar la fracción cruda como tasa poblacional. Si falta validación humana, informar revisión técnica y dejar la validación pendiente.

A-4 requiere que el revisor elija sin ver el orden BETO antes de fijar su decisión (o usar decisiones históricas independientes verificables). Guardar rechazo/sin candidato y cobertura sobre todos los casos elegibles; excluirlos de top-1 solo con motivo explícito. Revisar en una copia desechable posterior a las huellas, sin aprobar en la base viva ni usar `simular_revision.py` como verdad humana. Sin decisiones suficientes, entregar candidatos y protocolo, y marcar A-4 pendiente.

A-6 trata 97,55/2,45 % como referencia histórica del lote 1.387. El lote congelado de 10 archivos tiene otra población. No publicar una resta causal entre ambos. Medir las bandas y revisión antes/después **en F0**, con la misma unidad y denominador; separar hechos cargados con `requiere_revision`, staging y descartes. a0→a2 y a1→a12 aíslan QC; a2→a2w aísla la ventana. a3→a123 añade opciones 1 y 2 juntas: es un contraste combinado, no una estimación causal exclusiva de QC. Si se pide actualizar exactamente el lote histórico, falta una entrada distinta y queda para Lean.

## Comandos de medición y soporte autorizado

Ejecutar en **Git Bash/POSIX**, desde la raíz del repo; las asignaciones `VAR=valor comando` no son sintaxis PowerShell. Esta planificación no ejecuta los comandos. Conservar stdout/stderr completos redactados en `docs/mediciones/`, además de las salidas del wrapper.

### Preparación de §7 (una vez)

```bash
sh scripts/aislada_tmpfs.sh up
# Aquí verificar huellas origen/copia, ANTES de vaciar la plantilla.
sh scripts/aislada_tmpfs.sh vacio
sh scripts/copiar_arbol.sh medida
docker exec giragroup_api mkdir -p /tmp/flujo/scripts
# Aquí instalar originales y slices congelados, verificar hashes y rutas (F0-P).
docker compose restart pipeline
```

El reinicio es solo para cargar el código `/infer-batch` con BETO_WORKERS=2: coordinar exclusividad temporal del :8006, esperar disponibilidad y hacer calentamiento fijo no cronometrado. Si ya sirve exactamente código/modelo verificados, registrar y evitar un reinicio innecesario. Nunca reiniciar durante las series.

**Diferencias verificadas entre §7 y los scripts actuales; resolver antes de medir:**

- `flujo_aislada.sh` clona `dw_vacio` en cada llamada. Sin `CACHE_VACIA=1` no hereda automáticamente la caché que produjo la corrida anterior. Deben controlarse **ambas** tablas: `cache_indice_beto` y `cache_beto_entidades`.
- Para caché llena, hacer un calentamiento descartado por configuración, guardar únicamente sus cachés en una base semilla aislada y restaurarlas en cada clon nuevo **después** del clonado y **antes** del cronómetro. No copiar hechos, bandeja ni logs. Fijar semilla por configuración a0/a1/a2/a3/a12/a123/a2w; no usar una caché generada por otra ventana/modelo. Verificar claves, conteos, misses y hits antes/después. Para caché vacía, exigir 0 entradas de ambas antes de comenzar; la caché se puede llenar dentro del flujo medido.
- Autorizar a Chat 2 un cambio acotado del wrapper de medición: variable opcional `CACHE_SEED_DB`, validada como nombre de base tmpfs, para restaurar las dos cachés tras `clon`. Nunca exportar cachés con nombres personales a archivos versionados. Sin esa variable, mantener el comportamiento existente. `CACHE_VACIA=1` y `CACHE_SEED_DB` juntos deben fallar.
- Fijar `CATALOG_DATABASE_URL` a `catalogo_copia` en cada invocación; comprobar que ningún cliente usa la base viva. El wrapper no lo fija por sí mismo. Rechazar respuestas HTTP fallidas, lecturas FALLIDA/timeout y archivos incompletos aunque el pipeline de shell aparente éxito.
- `agregar_flujo_repetido.py` busca `flujo_corrida_*.json` y `corridas.json` y calcula KLM/revisión; no acepta directamente los JSON sin revisión de este wrapper (`FLUJO_SIN_REVISION=1`). No inventar esos datos ni ejecutar revisión simulada para satisfacerlo. Autorizar un agregador exclusivo de F0 que reutilice media/DE muestral y omita KLM; B-6/B-7 siguen en sus fases.

**Soporte nuevo a implementar por Chat 2, no disponible todavía:** `scripts/medir_f0.py`, herramienta de medición sin cambios a lógica productiva, con estas invocaciones/contratos:

```bash
# Copia privada, generación única, manifiesto y despliegue en las rutas F0-P.
python scripts/medir_f0.py congelar --mes 2026-03 --esperados 10 --salida docs/mediciones/f0_lote_manifest.json
# Calentamientos descartados por configuración, claves y metadatos, sin escribir en producción.
python scripts/medir_f0.py preparar-cache --configuraciones a0,a1,a2,a3,a12,a123,a2w --salida docs/mediciones/f0_cache_semillas.json
# Solo agregar 42 corridas válidas + huellas/metadatos, nunca calentamientos.
python scripts/medir_f0.py agregar --directorio docs/mediciones --prefijo f0 --salida docs/mediciones/f0_ablacion.json --csv docs/mediciones/f0_ablacion.csv
```

El soporte debe verificar hashes, registrar estado real de caché y rutas/flags, fallar ante entrada distinta y conservar las comprobaciones por corrida. Validarlo con pruebas de: slice faltante/hash alterado; clon vacío; clon con semillas; flags heredados; salida parcial; agregación con n≠3. Las ayudas se implementan **antes** de congelar el árbol de medición. Si no se puede garantizar aislamiento o caché, no iniciar cronómetros.

### A-1/A-2: matriz exacta derivada de §7

Convención: `vacia`/`llena`, repetición 1–3, bases `run_f0_<config>_<estado>_r<n>` y archivos `f0_<config>_<estado>_r<n>.json`. La configuración `a123` es la `v1` del ejemplo de §7; `a2w` es su `w1`. La ventana permanece apagada en las 6 configuraciones de ablación.

Tras implementar el soporte anterior, este bloque ejecuta las **42** corridas. Las semillas `f0_cache_<config>` solo contienen el calentamiento descartado correspondiente y deben constar en `f0_cache_semillas.json`. El calentamiento del modelo/servicio se mantiene uniforme también para caché DB vacía.

```bash
set -eu
for config in a0 a1 a2 a3 a12 a123 a2w; do
  case "$config" in
    a0)   c=0; q=0; h=0; w=0 ;;
    a1)   c=1; q=0; h=0; w=0 ;;
    a2)   c=0; q=1; h=0; w=0 ;;
    a3)   c=0; q=0; h=1; w=0 ;;
    a12)  c=1; q=1; h=0; w=0 ;;
    a123) c=1; q=1; h=1; w=0 ;;
    a2w)  c=0; q=1; h=0; w=1 ;;
  esac
  for estado in vacia llena; do
    for n in 1 2 3; do
      if [ "$estado" = vacia ]; then
        export CACHE_VACIA=1
        unset CACHE_SEED_DB
      else
        unset CACHE_VACIA
        export CACHE_SEED_DB="f0_cache_${config}"
      fi
      sh scripts/flujo_aislada.sh /tmp/medida \
        "run_f0_${config}_${estado}_r${n}" "f0_${config}_${estado}_r${n}.json" \
        BETO_CASCADA_FINAL="$c" BETO_ACUERDO_QC="$q" \
        BETO_SUGERENCIA_HITL="$h" BETO_VENTANA="$w" BETO_VENTANA_STRIDE=32 \
        CATALOG_DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/catalogo_copia
    done
  done
done
unset CACHE_VACIA CACHE_SEED_DB
```

El wrapper instrumentado debe verificar manifiesto y metadatos por llamada; registrar orden efectivo y rechazar corridas perturbadas, conservarlas como inválidas y repetir con sufijo nuevo, sin sobrescribir evidencia. Media/DE solo de las 3 válidas por celda. `tmpfs_local` es la clave desechable del contenedor aislado definida en el script, no una credencial productiva.

Comparaciones concretas (repetir por estado y repetición; cotejar también réplicas de la misma celda):

```bash
python scripts/comparar_huellas.py docs/mediciones/f0_a0_vacia_r1.json.huella.json docs/mediciones/f0_a1_vacia_r1.json.huella.json
python scripts/comparar_huellas.py docs/mediciones/f0_a0_vacia_r1.json.huella.json docs/mediciones/f0_a2_vacia_r1.json.huella.json
python scripts/comparar_huellas.py docs/mediciones/f0_a1_vacia_r1.json.huella.json docs/mediciones/f0_a12_vacia_r1.json.huella.json
python scripts/comparar_huellas.py docs/mediciones/f0_a3_vacia_r1.json.huella.json docs/mediciones/f0_a123_vacia_r1.json.huella.json
python scripts/comparar_huellas.py docs/mediciones/f0_a2_vacia_r1.json.huella.json docs/mediciones/f0_a2w_vacia_r1.json.huella.json
```

Guardar stdout en `f0_comparacion_<origen>_<destino>_<estado>_r<n>.txt`. Con flags activos las diferencias deben explicarse por tabla/filas, bandeja y KPI; no son automáticamente un fallo. Para a0 comparar además el código base `73ec78f` en árbol separado con **el mismo lote F0**, no contra huellas históricas de otro lote; 0 diferencias esperadas. Si no se puede ejecutar esa referencia, declararla pendiente, sin reutilizar la antigua prueba como nueva evidencia.

### B-3/B-4/B-5/B-10: ejecución paralela controlada

B-3 tiene este comando existente para las salidas A/B/C del gold; ejecutarlo en entorno aislado con modelo/hash fijados, fuera de los cronómetros:

```bash
python scripts/ablacion_beto.py --modo ALL --dataset gold_510 --semilla 42 --output_json docs/mediciones/f0_b3_ablacion.json --output_csv docs/mediciones/f0_b3_ablacion.csv
```

Auditar primero si el evaluador expone TP/FP/FN y qué significa relajado. Si falta el conteo, añadir exportación auxiliar de spans/predicciones y matching biyectivo con su definición explícita, sin retocar gold, modelo ni umbrales para mejorar resultados. Los modos A/B/C de extracción **no equivalen** a los flags a0/a1/a2/a3. En F0 se entregan datos para Gráfico 3.1; el gráfico final corresponde a F4.

Para B-4 seguir generadores reales de train/dev y `scripts/entrenar_beto_robusto.py`, además del gold y registros de anotación: detectar duplicados por texto/tokens, normalización documentada y parentesco de aumento. No ejecutar entrenamiento ni redistribuir conjuntos. Un cruce no demostrable por falta de IDs/procedencia se etiqueta «no verificable», nunca «sin fuga».

B-5 usa `giragroup_db` **dentro de `beto_pg_tmpfs`**, la copia histórica conservada antes de `vacio`; no usar el clon del lote mensual para un total anual. Guardar SQL con SELECT y respuestas CMI/OLS mediante TestClient conectado a esa copia, con catálogo aislado. Crear `f0_b5_consultas.sql` con filtros exactos obtenidos de `forecast_service` y del cálculo KPI-03; ejecutar:

```bash
docker exec -i beto_pg_tmpfs psql -U giragroup_user -d giragroup_db -v ON_ERROR_STOP=1 < docs/mediciones/f0_b5_consultas.sql > docs/mediciones/f0_b5_consultas.txt
```

La consulta debe ejecutarse en transacción READ ONLY. `f0_b5_2025.json` distingue PROGRAMAS/global, fuente, meses, n, ejecutado/meta y observado/ajustado; registra delta absoluto/relativo y razón de la discrepancia. No cambiar OLS mensual N=40 ni convertir la anual en modelo inferencial.

B-10 escanea archivos actuales y detecta ubicaciones **sin mostrar valores secretos**; sustituye por variables de entorno y ejemplos ficticios. Preservar el `.env` privado, no versionarlo. No cambiar contraseñas activas ni reiniciar servicios mientras se mide. Eliminar una cadena del árbol actual no la borra de commits antiguos: informar esa limitación; rotación y reescritura de historial quedan pendientes para Lean. No guardar el secreto ni siquiera en un reporte de búsqueda.

## Riesgos de §8 y controles de validez

| Riesgo | Control y evidencia |
|---|---|
| 1. No evaluables por primeras 8 celdas | a2w con línea completa y ventanas de 128/stride32; fracción no evaluable y cobertura por etapa/archivo; <20 % como puerta, sin asumir éxito. |
| 2. Coste de QC y ventana | 3 corridas por estado/configuración, media y DE; tiempos reales por etapa; sin cargas simultáneas. Los ≈13 min y ≈3,7× son antecedentes, no resultados. Registrar si <15, 15–<20 o ≥20 min; F0 no certifica ciclo completo RNF-03 porque omite revisión. |
| 3. Nombres fragmentados | A-3 verifica spans/texto original en entorno privado y etiqueta falsos desacuerdos; no ajustar reglas/modelo en F0. |
| 4. KPI/bandeja cambian por 0,84 | A-6 separa confianza, automatización, hechos en revisión, staging y logs; traza `DESACUERDO_REGLA_BETO`; NULL se conserva con explicación. |
| 5. Opción 1 tiene alcance acotado | Desglosar por tipo de fuente y residual; no atribuir rescate de ruido académico descartado a BETO; exigir trazabilidad sin sobrescritura A/B. |
| 6. Pesos 0,5/0,5 sin validación | A-4 contra decisiones humanas independientes; no usar aprobación simulada como etiqueta ni modificar pesos. |
| 7. Caché guarda personas | Semillas exclusivamente aisladas y privadas; no publicar contenido; declarar retención temporal y eliminación del contenedor al cierre. La purga productiva A-7 sigue en F1. |
| 8. :8006 compartido | Reservar ventana de uso exclusivo; B-3 no infiere durante A-1/A-2; B-10 no cambia entorno/reinicia entonces; registrar reinicios y tráfico/carga concurrente; invalidar corridas afectadas. No levantar un décimo servicio permanente. |
| 9. Humo no es medición | Humo/calibración/calentamientos se etiquetan y excluyen de n=3; no trasladar valores de la implementación como resultados F0. |
| Lote cambiante o caché supuestamente llena | Hash de originales y slices pre/post; rechazar faltantes; clonar estado de negocio idéntico y poblar solo cachés verificadas; registrar hits/misses, modelo y ventana. |
| Evidencia incompleta o variabilidad del entorno | Validar HTTP, estado terminal, 10 éxitos/0 fallidos, mismos conteos de entrada, tiempos y huellas presentes; justificar variación entre réplicas; no rellenar ausencias con ceros. |

## DECISIONES PENDIENTES PARA LEAN

No bloquean las tareas independientes. Registrar la pregunta concreta y su evidencia en el cierre.

1. Cualquier solución que exija alterar un invariante: **no ejecutarla**. Incluye cambiar umbrales, etiquetas/esquema declarado, 128→512, personas en catálogo, crear perfiles BETO o sobrescribir A/B. No se propone ninguna de estas modificaciones en F0.
2. Si el inventario no da 10 archivos o no hay una entrada recuperable: Lean debe fijar composición/bytes antes de medir. Si el lote y mes aquí definidos se pueden congelar sin contradicción, proceder sin pedir otra aprobación.
3. Si no hay decisiones humanas independientes para A-4, solicitar revisión de la muestra preparada; entregar el resto y dejar top-1 pendiente. No inventar una tasa ni declarar F0 íntegramente cumplida.
4. Reproducir específicamente 97,55/2,45 % requeriría el lote histórico 1.387 y su protocolo. F0 informa comparabilidad y tasas del lote nuevo; no amplía por sí sola la entrada.
5. Elegir defaults A-5 y resolver conteo de caché A-9 pertenecen a `PLAN_F1.md`, después de revisar la evidencia. No activar flags persistentes en F0.
6. B-10: rotar secreto de producción o reescribir/purgar historial remoto requiere una decisión explícita y coordinación; F0 sanea archivos actuales y reporta exposición residual. Fuga o anotación no verificable en B-4 se informa; no reentrenar ni cambiar gold en esta fase.

## Cierre y archivos de entrega

Antes de desmontar tmpfs: completar/exportar toda evidencia, recoger decisiones humanas disponibles, verificar snapshot y hashes finales y guardar estado de servicios. La ablación incluye IDs de cada corrida, hashes de entrada/código/modelo, estado comprobado de caché, muestras inválidas y razones; **42 válidas** y sus acompañantes para cumplir A-1/A-2. Resultados negativos no autorizan cambios de producto.

Ejecutar la suite con las URLs aisladas de §7 (desde host, intérprete del proyecto):

```bash
DATABASE_URL=postgresql://giragroup_user:tmpfs_local@127.0.0.1:55432/giragroup_db CATALOG_DATABASE_URL=postgresql://giragroup_user:tmpfs_local@127.0.0.1:55432/catalogo_copia python -m pytest tests --cov=backend --cov=pipeline > docs/mediciones/f0_pytest_cobertura.txt 2>&1
```

Usar una copia aislada desechable adicional si las pruebas mutan datos; B-5 debe terminar primero. Registrar colectadas/passed/failed/skipped/xfailed y cobertura real; no presuponer las 699 pruebas históricas. Criterio: 0 fallos nuevos y verificación de los controles añadidos.

Si se tocó backend/pipeline, después de medir: `docker compose up -d --build api pipeline`; si se tocó frontend: `docker compose up -d --build frontend`. Si solo cambian scripts/documentación no reconstruir imágenes innecesariamente; registrar motivo. Ejecutar `docker compose ps` y humo del endpoint afectado sin escritura en DW viva. Guardar salida redactada en `f0_servicios.txt`.

Preparar commit selectivo de los cambios F0 revisados, sin datos personales, secretos ni cambios preexistentes ajenos; mensaje `F0: medición aislada y evidencia BETO`. No merge. Escribir `docs/cierres/CIERRE_F0.md` con plantilla de la skill, commit medido y commit final, tareas cumplidas/pendientes, invariantes sin cambios, resultados enlazados, limitaciones y decisiones para F1. Si faltan etiquetas humanas o una puerta falla, declararlo: archivo de cierre no equivale a aceptación de todas las tareas.

Después de exportar y verificar todo:

```bash
sh scripts/aislada_tmpfs.sh down
```

No editar el docx ni `docs/fuente_verdad_tesis.md`; estas cifras no entran a la tesis hasta F3. Entrega: `CIERRE_F0.md`, `f0_ablacion.json/.csv`, resultados A/B y evidencias enlazadas en `docs/mediciones/`.

## PROMPT PARA CHAT 2

```text
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F0.md sobre beto-integracion. Lee primero CLAUDE.md y la skill de desarrollo. El md de implementación real es docs/auditoria/beto_integracion_implementacion.md.

Delega conforme a la tabla: dev-alta conserva completa la medición A-1 y luego A-2; dev-media analiza A-3, A-4, A-6, B-3 y B-4; dev-baja hace B-5 y B-10. Paraleliza solo tareas sin colisión de archivos/recursos; ninguna inferencia o reconstrucción concurrente con las corridas cronometradas ni dos agentes sobre una tarea alta.

Primero congela exactamente 10 originales y 10 slices, bytes fijos y SHA-256, y verifica copia/snapshot. Implementa únicamente el soporte de medición especificado (medir_f0.py y restauración opcional de cachés en el wrapper), valida rutas reales, flags explícitos, catálogo aislado y caché comprobada. Esas ayudas aún no existen: no simules que sus comandos ya funcionan. No regeneres slices ni uses una caché llena por suposición.

Mide 36 corridas a0/a1/a2/a3/a12/a123 y 6 de a2w, 3 por estado vacía/llena, de forma secuencial, con clones tmpfs y el mismo lote. Excluye calentamientos. Guarda JSON, huellas y metadatos por corrida, media y DE muestral; no uses el agregador KLM directamente sobre el flujo sin revisión. Evalúa no_evaluables <20 % sin alterar criterios si falla. Revisa desacuerdos y mide top-1 solo con decisiones humanas independientes; si faltan, deja pendiente con candidatos preparados. No mezcles porcentajes del lote histórico 1.387 con los de F0.

En paralelo produce evidencia B-3 (conteos estrictos/relajados A/B/C y 503/510), B-4 (aumento/split/fuga/anotación), B-5 (OLS anual 2025 frente al ejecutado KPI-03 sobre copia histórica) y B-10 (secreto fuera de archivos actuales, sin exponerlo ni reescribir historial o rotar producción).

No cambies defaults ni invariantes, no entrenes, no hagas merge, no toques docx/fuente de verdad ni DW viva/snapshot. Si algo exige un invariante distinto o una decisión pendiente de Lean, detén esa tarea, registra evidencia y continúa las independientes. Coordina el único recurso compartido :8006.

Al cerrar: exporta evidencia, verifica snapshot y lote, pytest con cobertura sobre copia aislada, reconstruye solo lo tocado después de medir, verifica servicios, commit selectivo F0 y docs/cierres/CIERRE_F0.md con enlaces y pendientes honestos. Desmonta tmpfs al terminar. Responde: «CIERRE_F0.md listo; pásalo al chat 1».
```
