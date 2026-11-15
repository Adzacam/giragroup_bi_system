# Endurecimiento del entrenamiento BETO

Fecha: 13 de noviembre de 2026. Rama: `beto-entrenamiento`, base `limpieza-repo` (`73ec78f`). Trabajo en worktree aislado `giragroup_beto_wt`.

## Alcance y restricciones

No se ejecutó entrenamiento ni inferencia del modelo. No se modificaron `pipeline/`, los `data/*.jsonl` vigentes, `data/ner/test.conll`, el snapshot ni la DW viva. No se usaron conexiones a base de datos. No se regeneraron gráficos finales. El reentrenamiento se realizará **una sola vez después de integrar las opciones 1–3 de BETO**; los comandos de entrenamiento siguientes son instrucciones para esa tarea futura.

## Cambios

- `scripts/preparar_corpus_robusto.py`: deduplicación ordenada (`sorted(set(...))` y equivalentes), RNG sembrado en 42 y salida explícita. JSONL en UTF-8 con LF. Rechaza salidas protegidas o corpus existente. `--fraccion-dev` parametriza la fracción de identidades reservadas (por defecto 0.2); `--n-total` controla las líneas (80/20); `--semilla` conserva 42 por defecto. Se separan personas ANTES de aumentar y combinar ejemplos, agrupando estudiantes y docentes por una identidad común sin títulos, tildes, casing ni espacios repetidos. Se verifican personas extraídas de spans, no solo los pools iniciales.
- `scripts/entrenar_beto_robusto.py`: `--salida` obligatorio, directorio nuevo/vacío fuera de `pipeline/`, validación también al llamar la función. Tres épocas fijas y selección del checkpoint por mayor F1 estricto de dev; **no hay early stopping**. CPU, un hilo, algoritmos deterministas y semilla 42. `training_info.json` registra SHA-256 de `model.safetensors` y train/dev/test, versiones de torch/transformers/seqeval/numpy/Python, argv, cwd, PYTHONHASHSEED, semilla y selección. Guardado explícito en safetensors. Métricas y predicciones quedan junto al modelo nuevo.
- `scripts/finetune_beto_ner.py`: conservado y marcado **NO USADO para el modelo vigente**. Conserva imports utilizados por pruebas transversales del extractor relacional. Retirarlo rompería esos consumidores; migrarlos es un trabajo separado. No se ha ejecutado su entrenamiento.
- `scripts/matriz_confusion_ner.py`: matriz real a partir de `y_true/y_pred`, validación de alineación, filas reales y columnas predichas, B/I colapsadas al tipo e inclusión explícita de **O**. Es una matriz por token, no una matriz de entidades. Cuenta FN hacia O y FP desde O; no se reconstruye a partir de P/R agregados.
- `scripts/generar_graficos_3_1_3_3.py`: gráfico 3.1 alimentado exclusivamente desde `docs/evidencias/matriz_confusion_ner.json`; omite la generación si falta. Usa clases separadas del gráfico 3.3 y evita división por cero. No se ejecutó el generador ni se alteraron PNG históricos. Las métricas históricas del 3.3 continúan pendientes de renovación tras reentrenar.
- `scripts/beto_metricas.py`: carga de CoNLL sin generar/sobrescribir el test y F1 relajado por solapamiento del mismo tipo con matching máximo uno a uno (evita contar una predicción varias veces).
- `scripts/evaluar_beto_checkpoint.py`: checkpoint explícito, evaluación sin fallback ni cuantización, estricta IOB2 y relajada sobre `gold_510`, `layouts_5` y `test.conll`. Alineación por primera subpieza de cada token gold; rechaza secuencias truncadas. En layouts filtra NOTA/FECHA/CI del gold NER, conserva O. Guarda predicciones, métricas y matriz en la salida temporal. Esta evaluación de tokens gold difiere de la evaluación interna del entrenador sobre subpiezas: identificar siempre protocolo y conjunto al comparar cifras.
- `make beto-reproducir`: corpus → entrenamiento en directorio temporal nuevo → evaluación estricta/relajada de los tres conjuntos. Exporta `PYTHONHASHSEED=0`, UTF-8, un hilo y FP32. También admite `BETO_SALIDA` nuevo/vacío y `PYTHON` explícito. El target **no se ejecutó**; se validó la orquestación sustituyendo Python por un programa que solo registra argumentos.
- `scripts/ablacion_beto.py`: acepta `--modelo` y `--gold` para evaluar artefactos alternativos conservando los defaults. El target utiliza el evaluador aislado anterior para evitar dependencias en efectos colaterales del pipeline.
- `backend/routers/dataops/maestros.py`: descripciones y arquitectura corregidas a checkpoint local basado en `dccuchile/bert-base-spanish-wwm-cased`, con nueve etiquetas BIO institucionales. `mrm8488/bert-spanish-cased-finetuned-ner` se describe como fallback de `pipeline/config.py:31`.

## Evidencia de determinismo e independencia

`docs/evidencias/beto_corpus_determinismo.json` conserva dos ejecuciones completas en procesos y directorios temporales independientes, con PYTHONHASHSEED=0 y semilla 42. En ambas: 1.400 train, 350 dev y 180 test. SHA-256 idénticos entre corridas:

| Archivo temporal | SHA-256 en ambas corridas |
|---|---|
| train_robusto.jsonl | d02ae16807831aab92b4d7cef34962c0d2a42f5221c646162e46efd5f155c5b7 |
| dev_robusto.jsonl | 9f3e7371ae654404591d6892c8d4d01b806f37f5344640d8ea8c52a774c7de9e |
| test_gold_real.jsonl | ebbbe6f262a28ac9a17dd9abbb195fd8a7db1f8429720d6f791d8adad3dd8f60 |

Solapamiento nuevo de personas normalizadas: **train/dev=0; train/test=0; dev/test=0**. Personas distintas observadas: train 1.967, dev 485, test 83. Textos compartidos: 0 en los tres cruces. Los programas sí pueden repetirse (338 entre train/dev); la garantía solicitada es por persona.

**El dev anterior no era independiente**: en los JSONL vigentes se midieron 273 personas compartidas entre train/dev y 312 de 350 líneas dev con alguna persona de train. No hay textos idénticos compartidos; esa condición no basta para independencia. Sus métricas dev no deben presentarse como evaluación independiente por identidad. El nuevo test temporal es semánticamente idéntico al vigente; cambia el hash de bytes al escribir LF en lugar del formato de línea anterior. El archivo vigente permanece intacto.

## Manifiesto y dependencias

`docs/evidencias/beto_manifiesto.json` registra todos los `data/*.jsonl` vigentes, modelo/tokenizer/config/training_info disponibles, las fuentes Excel, seed SQL, layouts y test.conll, más el hash de `requirements-lock.txt`. El script falla si no se suministra un checkpoint con `model.safetensors`, evitando un manifiesto engañosamente vacío. El checkpoint no se incluye en Git: `.gitignore:75`.

SHA-256 vigente de model.safetensors:
`5966dde3fa4adccacb8ed74c62c991a6bf140c2b4d67598a05a1c35e67ec9543` (437.092.180 bytes).

En este worktree el checkpoint no está presente completo; se leyó desde el directorio original, sin copiarlo ni modificarlo. Para obtenerlo, solicitar el respaldo completo de `beto_local/` de la máquina de entrenamiento (pesos, config y tokenizer) y verificar el hash antes de usarlo. No existe aquí un enlace público versionado al checkpoint institucional. Regenerarlo produce un modelo nuevo, no garantiza recuperar el hash histórico.

`requirements-lock.txt` coincide línea a línea con `pip freeze` del `.venv` utilizado: Python 3.14 en Windows; torch 2.13.0, transformers 5.14.1 y seqeval 1.2.2. Es una captura exacta del entorno instalado, no un lock universal entre sistemas ni un lock con hashes de ruedas.

```bash
python -m pip install -r requirements-lock.txt
PYTHONHASHSEED=0 python scripts/generar_manifiesto_beto.py --modelo <respaldo/beto_local>
```

## Pruebas y comandos

Nuevas pruebas en `tests/sprint3/test_beto_entrenamiento_endurecimiento.py` (Sprint 3, PLN/BETO). Resultado final: **15 passed, 0 failed**, 23,12 s. Cubren dos procesos reales del corpus, identidad normalizada y roles, parámetros inválidos, formato y hashes de training_info con pesos ficticios, salidas protegidas, matriz y errores de alineación, evaluación relajada uno a uno, alineación/truncamiento con dobles y orquestación con intérprete espía. La prueba del manifiesto verifica datos y fuentes; compara también los pesos si están disponibles localmente. En esta tarea los pesos vigentes se comprobaron explícitamente por lectura desde el directorio original.

```powershell
$env:PYTHONHASHSEED='0'
$env:PYTHONUTF8='1'
& '../giragroup_bi_system/.venv/Scripts/python.exe' -m pytest tests/sprint3/test_beto_entrenamiento_endurecimiento.py -q
```

`.gitattributes` fija LF para `scripts/beto_reproducir.sh`, evitando que autocrlf rompa el script al hacer checkout en Windows.

También se validó `bash -n scripts/beto_reproducir.sh` con Git Bash y `git diff --check`. No se ejecutaron suites que conecten DW, hagan reset o entrenen. El host no dispone de `make`; el script llamado por el target se comprobó con un intérprete espía, sin ejecutar sus tres programas.

Comandos preparados para la tarea futura, después de integrar opciones 1–3:

```bash
# Bash + make, con el Python del entorno bloqueado disponible:
PYTHON=/ruta/.venv/bin/python make beto-reproducir
# Windows Git Bash: PYTHON='C:/ruta/.venv/Scripts/python.exe' bash scripts/beto_reproducir.sh

# Etapas explícitas; elegir directorios nuevos:
PYTHONHASHSEED=0 python scripts/preparar_corpus_robusto.py --salida <temporal/corpus> --fraccion-dev 0.2 --semilla 42
PYTHONHASHSEED=0 python scripts/entrenar_beto_robusto.py --datos <temporal/corpus> --salida <temporal/modelo>
PYTHONHASHSEED=0 python scripts/evaluar_beto_checkpoint.py --modelo <temporal/modelo> --gold <temporal/corpus/test_gold_real.jsonl> --salida <temporal/eval>

# Solo después de validar las predicciones reales, generar el JSON para el gráfico:
python scripts/matriz_confusion_ner.py --predicciones <temporal/eval/gold_510_predicciones.json> --salida docs/evidencias/matriz_confusion_ner.json
```

No existe todavía el JSON de matriz final: generarlo exige ejecutar el modelo. La prueba usa la primera línea real del test y modifica deliberadamente una entidad a O y un token O a PROGRAMA; valida ambos errores y el total de tokens. Es un ejemplo controlado, no una medición del modelo. No sustituir la matriz final por estos datos.

## Tolerancia y pendientes

- Corpus: tolerancia **cero bytes**, hashes idénticos con fuentes/seed/entorno iguales. Las fuentes necesarias se identifican por hash en el manifiesto; el snapshot y DW no son entradas.
- Entrenamiento: se espera igualdad de parámetros y métricas en la misma CPU, versiones y configuración determinista; tiempo, timestamp y rutas pueden variar. No se promete identidad del contenedor safetensors ni de pesos entre hardware/versiones distintos. Para comparar métricas entre entornos, umbral de revisión propuesto de **0,001 absoluto de F1 micro** (0,1 puntos porcentuales), no una tolerancia medida ni permiso automático para diferencias. Toda diferencia debe registrar entorno y hashes. Falta medirlo tras la integración; no se ejecutarán múltiples entrenamientos en esta tarea para estimarlo.
- Ejecutar una única corrida de entrenamiento después de integrar opciones 1–3, medir F1 estricto/relajado en los tres conjuntos, generar matriz real y actualizar informe y gráficos tras revisión. La selección de checkpoint usa exclusivamente dev.
- **Límite conocido: test.conll micro F1 estricto = 0,7147**, evidencia histórica `_archivo/output/metricas_ner_robusto.json`, micro avg con soporte 750. Es una limitación del modelo vigente, no un resultado nuevo ni un umbral modificado. No se alteró test.conll.
- Fijar una revisión inmutable del modelo base Hugging Face y archivar pesos base/ruedas si se requiere reconstrucción completamente sin red. El identificador base actual no fija una revisión; el lock de paquetes y los hashes de corpus no sustituyen ese archivo.
- `pipeline/semantic/inference_server.py:9–13` mantiene su descripción histórica incorrecta. **Pendiente por la prohibición explícita de tocar pipeline/**. Corrección concreta para integrar en la rama propietaria: “El checkpoint local BETO basado en dccuchile/bert-base-spanish-wwm-cased emite nueve etiquetas IOB2 institucionales (O y B/I de PER_ESTUDIANTE, PER_DOCENTE, MODULO y PROGRAMA). mrm8488/bert-spanish-cased-finetuned-ner, con etiquetas CoNLL, se utiliza solo si falla la carga local, según MODELO_BETO_FALLBACK de config.py”. Conservar el detalle de mapeo CoNLL solo bajo el apartado de fallback. Esta corrección no se ha aplicado a ese archivo.
