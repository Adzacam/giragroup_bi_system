# PLAN F1V — 15 de noviembre de 2026
Objetivo: cerrar F1 aplicando D1/D2/D3 de Lean, validar la configuración final (F1-V) e integrar (A-10).
Entrada: CIERRE_F1.md (parcial) + PLAN_F1.md; rama base = beto-integracion b559292.

## Decisiones de Lean (registradas en el chat 1, 2026-11-15)
- D1/A-5: los 4 flags quedan en False (BETO_CASCADA_FINAL, BETO_ACUERDO_QC, BETO_SUGERENCIA_HITL, BETO_VENTANA).
- D2/A-9: `cache_beto_entidades` es una caché operativa fuera de las 50 tablas DW. La migración 015 deja de aplicarse
  en la inicialización; la tabla solo se crea al vuelo (DDL_CACHE, beto_integracion.py:155) si se enciende la opción 1 o 2.
- D3: promover output/f1/reproduccion_1/modelo **solo si** pasa la puerta de fuga (F1-L). Si no pasa, se conserva el vigente.
- Revisión humana A-3/A-4: diferida. Queda como limitación; **prohibido** generar o simular etiquetas humanas.

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| F1-E | Fe de erratas de los nombres de flags y registro de las decisiones | dev-baja | — | F1-L, F1-D2 | 3 JSON con valor, fecha, «decidido por Lean en chat 1» y fuentes; CIERRE_F1 con una sección de erratas que corrige los nombres de §3 (sin reescribir el resto) | f1_decision_flags.json, f1_decision_cache.json, f1_decision_modelo.json |
| F1-L | Puerta de fuga para D3: gold_510 y layouts_5 frente al corpus de train y dev de reproduccion_1 | dev-media | — | F1-E, F1-D2 | Solapamiento de oraciones normalizadas = 0 (puerta); personas normalizadas compartidas reportadas por cruce; veredicto pasa / no pasa | f1_fuga_evaluacion.json |
| F1-D2 | Sacar 015 de la inicialización | dev-media | — | F1-L | DW nuevo creado con run_migrations = 48 public + 2 bi BASE TABLE + 9 bi VIEW; 015 movida a backend/scripts/migrations_opcionales/ con README; con la opción 1 encendida en tmpfs la tabla se crea al vuelo (prueba); en la DW viva solo inventario de lectura (existe sí/no, filas) | f1_d2_inventario_dw_nuevo.csv, f1_d2_dw_viva.json |
| F1-C | Invalidación de caché por identidad del modelo | dev-alta | F1-L pasa | — | Demostrar que la clave de cache_indice_beto y de cache_beto_entidades incluye la versión del modelo (BETO_MODELO_VERSION o hash); si no la incluye, DETENER y elevarlo a Lean (no tocar la DW viva) | f1_cache_identidad_modelo.json |
| F1-P2 | Promoción del checkpoint | dev-alta | F1-L pasa, F1-C | — | Respaldo del vigente en output/f1/beto_local_respaldo/ con sha256 por archivo; candidato copiado y hashes iguales al manifiesto; pesos fuera de Git (verificar .gitignore); rebuild de pipeline; /health ok; reevaluación en el contenedor = metricas.json de f1_evaluacion_despues (Δ F1 = 0) | f1_promocion_modelo.json |
| F1-V | 6 corridas: flags apagados + modelo final, 3 con caché vacía y 3 con caché llena **llenada con el modelo final** (no seeds F0), mismo lote aafde8ad… | dev-alta | F1-P2 (o F1-L falla → modelo vigente), F1-D2 | Ninguna carga pesada | Hash del lote antes y después idéntico; snapshot 0 diferencias; media ± DE; huella comparada con f1_off (diferencias reportadas por tabla, sin ocultarlas); bandeja, KPI-10/11/18 (NULL se queda NULL) | f1_validacion_{vacia,llena}_r{1..3}.json + acompañantes, f1_validacion_resumen.json |
| A-10 | pytest + cobertura, rebuild, commit | dev-baja | todo lo anterior | — | 0 fallos nuevos (cifras exactas, sin imponer 801); 9 servicios Up; /health; commit selectivo sin pesos, nombres ni CI | f1_pruebas.txt, f1_servicios.txt, f1_cierre_manifest.json |

## Comandos exactos
- Lote: `python scripts/medir_f0.py verificar --manifest docs/mediciones/f0_lote_manifest.json`
- tmpfs: `TMPFS_PORT=55632 bash scripts/aislada_tmpfs.sh up` (verificar que el puerto está libre; registrar el real) … `down` al final.
- F1-L: script nuevo `scripts/f1_fuga_evaluacion.py` que lee output/f1/reproduccion_1/corpus/*.jsonl y los conjuntos de evaluación; la normalización es la misma de f1_corpus_auditoria; solo publica conteos y hashes.
- F1-P2 reevaluación: `PYTHONHASHSEED=0 PYTHONUTF8=1 BETO_INT8=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python scripts/evaluar_beto_checkpoint.py --modelo pipeline/semantic/beto_local --gold data/test_gold_real.jsonl --salida output/f1/eval_post_promocion`
- Rebuild: `docker compose up -d --build pipeline api` → `docker compose ps`
- F1-V: ejecutor F1 con prefijo f1_validacion_ y árbol copiado a una ruta distinta de /tmp/medida; no reutilizar medir_f0.py series.
- pytest: el comando de PLAN_F1 §5 con el puerto verificado → docs/mediciones/f1_pruebas.txt

## Riesgos y control
- Caché obsoleta tras la promoción: cache_indice_beto (90.212 filas en la fuente de verdad) podría servir inferencias del modelo anterior → F1-C es puerta dura.
- Pruebas que asumen que 015 se aplica sola: ajustarlas solo si afirman ese comportamiento; reportar cada cambio.
- test.conll F1 estricto 0,767 < 0,85: no afirmar RNF-04 fuera de gold_510.
- Los tiempos de F1-V son de máquina y no certifican RNF-03 (eso es B-7 en F3).
- :8006 compartido: no medir mientras se reconstruye pipeline.

## DECISIONES PENDIENTES PARA LEAN (no se ejecutan hasta que responda)
1. Si la DW viva ya tiene cache_beto_entidades: ¿purga (A-7) + DROP? El chat 2 solo informa el inventario.
2. Si F1-C muestra que la clave de caché no incluye el modelo: cómo invalidar cache_indice_beto en la DW viva.
3. B-10 residual: rotación de la contraseña y reescritura del historial Git.
4. Revisión humana A-3 (90) y A-4 (7): pendiente; F2 la incorpora cuando Lean entregue los CSV.
