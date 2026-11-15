# PLAN F1D3B — 15 de noviembre de 2026
Objetivo de la fase: comparar beto-v1 y beto-v2 lado a lado (calidad, validez del reentrenamiento, efecto operativo) para que Lean decida D3-bis. **No cambia ningún default:** `BETO_MODELO_VERSION=beto-v2` sigue en `docker-compose.yml` y `pipeline/semantic/beto_local` no se toca.
Entrada: CIERRE_F1R2.md; rama base = `beto-integracion` `ce8ff46`.

**Modelos**
| Versión | Ruta (solo lectura) | `model.safetensors` sha256 | Corpus de entrenamiento |
|---|---|---|---|
| beto-v1 | `output/f1/beto_local_respaldo/` | `5966dde3…9543` | `data/train_robusto.jsonl` (`c4311540…278df2`, auditado en `f0_b4_auditoria.json`) |
| beto-v2 | `pipeline/semantic/beto_local/` (= `output/f1/reproduccion_1/modelo`) | según `f1_modelo_manifest.json` | `output/f1/reproduccion_1/corpus/train_robusto.jsonl` (`d02ae168…c5b7`) |

| ID | Tarea | Agente | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| D-A | Calidad del modelo, sin pipeline | dev-media | — | D-B, D-C | (1) Para cada versión, en `gold_510` y `layouts_5`, en modos A/B/C, con criterio estricto y relajado: TP, FP, FN, P, R y F1. Son 2 versiones × 2 conjuntos × 3 modos × 2 criterios = 24 filas. (2) Mismo `scripts/ablacion_beto.py` (sha256 registrado), `--semilla 42`, mismo gold (`7dce0bec…a5a5`) y misma versión de torch y transformers en las dos versiones. (3) Control: v1 reproduce `f0_b3_ablacion.csv` fila a fila (Δ = 0); si no, se reporta la diferencia y su causa. (4) Soporte de `gold_510` declarado (503 o 510, con motivo, según B-3) | `f1_d3b_calidad.csv`, `f1_d3b_calidad.json` |
| D-B | Validez del reentrenamiento de v2 | dev-media | — | D-A, D-C | (1) Tabla v1 frente a v2: corpus (ruta, sha256, filas, personas únicas), épocas, mejor época, lr, weight_decay, batch, max_length, semilla, duración y Dev F1, todo tomado de los `training_info.json`. (2) Orden «aumento / separación»: respuesta sí/no con líneas de `scripts/preparar_corpus_robusto.py` (separación por claves de persona, ~l.105; aumento por pool de cada partición, ~l.338) y prueba empírica: 0 personas compartidas entre train y dev en cada corpus. (3) Fuga contra `gold_510` y `layouts_5`, **en el train de v1 y en el de v2**, con el número de coincidencias por cada uno de 4 niveles: a) hash de la oración exacta; b) hash del texto normalizado (NFKD, casefold, sin tildes ni títulos, como en f0_b4); c) variantes: plantilla con entidades enmascaradas por tipo y Jaccard de tokens normalizados ≥ 0,8; d) personas normalizadas compartidas. Si algún nivel > 0, se listan los pares | `f1_d3b_validez.json` |
| D-C | Efecto operativo, pipeline completo | dev-alta | — | D-A, D-B | (1) Lote congelado `aafde8ad…db60` verificado antes y después. (2) Para cada versión: 3 corridas con caché vacía y 3 con caché llena, en tmpfs, con los 4 flags en 0, intercaladas v1/v2 para controlar la deriva. Cada versión usa su propio contenedor de índice y su propia base tmpfs: v1 con `BETO_MODELO_VERSION=beto-v1` y v2 con `beto-v2`. (3) Por versión: líneas, filas de los 9 hechos, staging, bandeja (casos y grupos), KPI-10/11/18, y tiempo de máquina y de pared (media y DE, n=3, vacía y llena). (4) Las 6 corridas de cada versión son idénticas entre sí (0 diferencias en huella, bandeja y KPI); v1 = `f1_off` y v2 = `f1_validacion` en huella y bandeja. (5) KLM estimado con `klm()` de `scripts/agregar_flujo_repetido.py`, con y sin espera W, sobre los grupos y casos reales de cada bandeja; regla de mapeo grupo → acción (APROBAR / MANUAL / CORREGIR_FECHA / MAPEAR_ESTADO) escrita en el JSON. (6) Tiempo total = máquina (media con caché vacía) + KLM, para las dos variantes de W. (7) Explicación de 182/12 → 680/19 a partir de `f1_r2_bandeja_diff.csv` (sin reejecutar): casos por motivo y por archivo (los 5 primeros), grupos nuevos y su tamaño; las cuentas cuadran con +569 / −71 | `f1_d3b_operativo.json`, `f1_d3b_klm.json`, `f1_d3b_corrida_<v>_<vacia\|llena>_r<i>.json` con su `.huella.json` |
| D-T | Tabla única y entrega | dev-baja | D-A, D-B, D-C | — | Una sola tabla con las métricas de A y C en filas y las columnas v1, v2 y Δ. Cada cifra con el nombre del archivo del que sale; ninguna cifra sin fuente. Resultado de B (cuatro niveles × dos trains). Huellas del DW: sha256 de la huella de cada versión y lista de las tablas que difieren | `f1_d3b_comparacion.md`, `f1_d3b_comparacion.json` |

## Comandos exactos por tarea
- **D-A**
  ```
  python scripts/ablacion_beto.py --modo ALL --dataset gold_510 --semilla 42 --modelo output/f1/beto_local_respaldo --output_json docs/mediciones/f1_d3b_calidad_v1_gold.json --output_csv docs/mediciones/f1_d3b_calidad_v1_gold.csv
  ```
  Lo mismo con `--dataset layouts_5`, y las dos veces con `--modelo pipeline/semantic/beto_local` (sufijo `v2`). Al final se unen en `f1_d3b_calidad.csv` y `.json`. `BETO_INT8=0` y `max_tokens=128` en las dos versiones.
- **D-B:** solo lectura de los corpus y de los `training_info.json`. Un script nuevo `scripts/f1_d3b_validez.py` (sin escribir en `data/`) que reutiliza la normalización de `scripts/auditar_f0_corpus.py` y la de `scripts/f1_fuga_evaluacion.py`.
- **D-C**
  - `TMPFS_PORT` verificado (55632) y `scripts/aislada_tmpfs.sh up`.
  - Contenedor de índice para v1 como en R-2 (`beto_pipeline_r2v1`, que monta `output/f1/beto_local_respaldo` como `/app/pipeline/semantic/beto_local`) y el equivalente para v2 sobre el modelo vigente. Ninguno usa el servicio compartido `:8006`.
  - Corridas con `scripts/f1_validar.py`, o el ejecutor de R-2 si `f1_validar.py` no acepta el modelo como parámetro. Cada corrida va con `scripts/huella_dw.py`.
  - Orden: v1-vacía-r1, v2-vacía-r1, v1-llena-r1, v2-llena-r1 y así hasta r3. La caché se vacía antes de cada corrida «vacía»: base nueva desde `dw_vacio`.
  - KLM: importar `klm` desde `scripts/agregar_flujo_repetido.py` sin modificarlo.
  - Al terminar: `scripts/aislada_tmpfs.sh down`.
- **D-T:** solo lee los JSON de D-A, D-B y D-C.

## Riesgos y control
- **DW viva y defaults:** ninguna tarea escribe en `giragroup_db` (:5434), en el snapshot, en `docker-compose.yml`, en `pipeline/semantic/beto_local` ni en `confianza_service.py`. Se verifica con `git status`, que no debe mostrar cambios en esos archivos, y con el sha256 del modelo vigente antes y después.
- **Caché cruzada:** cada versión con su propio `BETO_MODELO_VERSION` y su propia base tmpfs. Que una corrida «llena» de v1 encuentre filas `beto-v2` es motivo para invalidarla.
- **Tiempos:** son tiempos de máquina en este equipo; no certifican RNF-03 (eso es B-7 en F3). Se intercalan las versiones y se registran la CPU y la carga de la máquina en cada `.meta.json`.
- **KLM:** es una estimación con parámetros clásicos y una regla de mapeo explícita; no sustituye a B-6 (F2). Se etiqueta `klm_estimado_d3b`.
- **Comparabilidad de A:** si D-A con v1 no reproduce f0_b3, la comparación se reporta como «no comparable» hasta explicar la diferencia.
- **Sin etiquetas humanas:** ningún veredicto de esta fase se presenta como humano.

## DECISIONES PENDIENTES PARA LEAN (no se ejecutan hasta que responda)
1. **D3-bis:** con `f1_d3b_comparacion.md` en la mano, mantener beto-v2 o volver a beto-v1 (respaldo + `BETO_MODELO_VERSION=beto-v1` + rebuild de pipeline y api). Esta fase no lo ejecuta.
2. **B-10 residual** (sin cambios).

## Al cerrar
pytest + cobertura · sin rebuild (no se toca código de producción ni modelo vigente) · commit `chore(f1d3b): comparación beto-v1 vs beto-v2 para D3-bis` · `CIERRE_F1D3B.md`, que incluye la tabla de D-T.

## PROMPT PARA CHAT 2
```
/gira-desarrollar
Ejecuta docs/cierres/PLAN_F1D3B.md.
- D-A (dev-media), D-B (dev-media) y D-C (dev-alta) en paralelo; D-T (dev-baja) al final.
- No cambies defaults: BETO_MODELO_VERSION=beto-v2, pipeline/semantic/beto_local, docker-compose.yml
  y la DW viva quedan intactos. Comprueba el sha256 del modelo vigente antes y después.
- v1 se lee de output/f1/beto_local_respaldo; v2, de pipeline/semantic/beto_local. Ambos en solo lectura.
- D-C en tmpfs, lote aafde8ad…db60, 3 corridas con caché vacía y 3 con caché llena por versión,
  intercaladas, cada una con su contenedor de índice y su BETO_MODELO_VERSION.
- KLM con klm() de scripts/agregar_flujo_repetido.py, sin modificarlo, etiquetado klm_estimado_d3b.
- No ejecutes D3-bis ni B-10.
Al terminar: pytest con cobertura, commit y docs/cierres/CIERRE_F1D3B.md con la tabla v1/v2/Δ
de D-T, el resultado de D-B y las huellas del DW de ambas versiones.
```
