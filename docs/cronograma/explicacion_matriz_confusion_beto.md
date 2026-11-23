# Explicación Técnica de la Matriz de Confusión de BETO (`beto-v2`) y su Vista Correcta

> **Nota:** Documento técnico de respaldo documental (no se integra en la interfaz web). Todas las cifras provienen directamente de los archivos JSON de medición verificados en `docs/mediciones/` y `docs/evidencias/`.

---

## 1. Dos Niveles Complementarios de Evaluación (Entidad vs. Token)

Para interpretar correctamente el desempeño del modelo NER regenerado (**`beto-v2`**, checkpoint `pipeline/semantic/beto_local/model.safetensors`, SHA-256 `9ff7fb9d914aca9eaa0618d9603d869a30808d9218369aef7b12dd92362b5f92`), es indispensable distinguir **dos niveles de medición**:

1. **Nivel Entidad (`seqeval`, esquema IOB2):** Evalúa si el *span* completo de la entidad (inicio, fin y tipo) coincide con la referencia gold. Es la métrica estándar para NER en producción porque un solo token mal delimitado invalida el span completo bajo criterio estricto.
2. **Nivel Token (`scripts/matriz_confusion_ner.py`):** Evalúa cada token individualmente colapsando `B-X` e `I-X` a su tipo `X` (incluyendo la clase `O`), permitiendo construir la matriz cuadrada $5 \times 5$ real–predicho que respalda el gráfico `docs/evidencias/graficos_v2/grafico_3_1_matriz_confusion_beto.png`.

---

## 2. Evaluación a Nivel Entidad (`gold_510`, Modo C — Solo BETO)

**Fuentes verificadas:**
- `docs/mediciones/f3r_matriz_confusion.json`
- `docs/mediciones/f1_d3b_calidad_v2_gold.json` (`por_modo.C.gold_510`)

Sobre **510 entidades gold** (180 secuencias de `test_gold_real.jsonl`), el modelo predice **517 entidades**:

- **Criterio estricto (`seqeval`, coincidencia exacta de span y tipo):**
  - **TP = 503**, **FN = 7**, **FP = 14**
  - **Precisión = 0,9729** (`97,29%`) | **Recall = 0,9863** (`98,63%`) | **Micro F1 = 0,979552** (`97,96%`)
- **Criterio relajado (solapamiento parcial de tokens con mismo tipo):**
  - **TP = 510**, **FN = 0**, **FP = 6**
  - **Precisión = 0,9884** (`98,84%`) | **Recall = 1,0000** (`100,00%`) | **Micro F1 = 0,9942** (`99,42%`)

### Desglose por Tipo de Entidad (`gold_510`, Modo C)

| Tipo de Entidad | Soporte | TP (Estricto) | FN (Estricto) | FP (Estricto) | Precisión | Recall | F1 Estricto | F1 Relajado |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `MODULO` | 150 | 150 | 0 | 0 | 1,0000 | 1,0000 | **1,0000** | 1,0000 |
| `PER_DOCENTE` | 50 | 50 | 0 | 0 | 1,0000 | 1,0000 | **1,0000** | 1,0000 |
| `PER_ESTUDIANTE` | 130 | 129 | 1 | 1 | 0,9923 | 0,9923 | **0,9923** | 1,0000 |
| `PROGRAMA` | 180 | 174 | 6 | 13 | 0,9305 | 0,9667 | **0,9482** | 0,9836 |
| **Total / Micro Avg** | **510** | **503** | **7** | **14** | **0,9729** | **0,9863** | **0,9796** | **0,9942** |

---

## 3. Matriz de Confusión a Nivel Token (`scripts/matriz_confusion_ner.py`)

El script `scripts/matriz_confusion_ner.py` genera la matriz real (filas = etiqueta real, columnas = etiqueta predicha) colapsando los prefijos `B-` e `I-` al tipo de entidad e incluyendo la clase `O`.

### 3.1. Conjunto `gold_510` (3.511 tokens en 180 secuencias)
**Fuente:** `docs/mediciones/f1_evaluacion_despues/matriz_confusion_ner.json`

| Real \ Predicho | `O` | `MODULO` | `PER_DOCENTE` | `PER_ESTUDIANTE` | `PROGRAMA` | Soporte |
|---|---:|---:|---:|---:|---:|---:|
| **`O`** | **1.470** | 0 | 0 | 0 | 0 | 1.470 |
| **`MODULO`** | 0 | **300** | 0 | 0 | 0 | 300 |
| **`PER_DOCENTE`** | 0 | 0 | **120** | 0 | 0 | 120 |
| **`PER_ESTUDIANTE`** | 0 | 0 | 0 | **467** | **1** | 468 |
| **`PROGRAMA`** | 0 | 0 | 0 | 0 | **1.153** | 1.153 |

- **Lectura exacta:** De 3.511 tokens, **3.510** son clasificados correctamente. El único error a nivel token es **1 token de `PER_ESTUDIANTE` predicho como `PROGRAMA`** (`FN=1` en `PER_ESTUDIANTE`, `FP=1` en `PROGRAMA`).

### 3.2. Conjunto `test_gold_real.jsonl` completo (7.791 tokens en 180 secuencias)
**Fuente:** `docs/evidencias/matriz_confusion_ner.json` (origen: `pipeline/semantic/beto_local/predicciones_test_gold.json`)

| Real \ Predicho | `O` | `MODULO` | `PER_DOCENTE` | `PER_ESTUDIANTE` | `PROGRAMA` | Soporte |
|---|---:|---:|---:|---:|---:|---:|
| **`O`** | **2.796** | 0 | 0 | 0 | 0 | 2.796 |
| **`MODULO`** | 0 | **450** | 0 | 0 | 0 | 450 |
| **`PER_DOCENTE`** | 0 | 0 | **191** | 0 | 0 | 191 |
| **`PER_ESTUDIANTE`** | 0 | 0 | 0 | **867** | **2** | 869 |
| **`PROGRAMA`** | 0 | 0 | 0 | 0 | **3.485** | 3.485 |

- **Lectura exacta:** De 7.791 tokens, **7.789** son aciertos exactos (`99,97%` de exactitud por token), con únicamente **2 tokens de `PER_ESTUDIANTE` confundidos con `PROGRAMA`**.

---

## 4. Por Qué Esta Es la Vista Correcta de la Matriz

1. **Separación entre error de frontera (`span`) y confusión semántica de clase:**
   - A primera vista, ver `503/510` (`FN=7, FP=14`) en `seqeval` estricto podría sugerir que BETO confunde entidades entre sí. Sin embargo, al cruzarlo con la evaluación relajada (`TP=510/510`, `FN=0`) y con la matriz por token (`3.510/3.511` y `7.789/7.791` aciertos), se demuestra que **no existe confusión masiva entre clases**.
   - Los `6` errores estrictos en `PROGRAMA` y `1` en `PER_ESTUDIANTE` corresponden a **límites de span** (por ejemplo, dividir o extender un nombre de programa largo con conectores o paréntesis), no a confundir un módulo con un docente ni con texto fuera de entidad (`O`).
2. **Corrección de sesgos previos en `beto-v2`:**
   - El cálculo automatizado mediante `scripts/matriz_confusion_ner.py` directamente desde `y_true`/`y_pred` reemplaza estimaciones manuales previas, incluye explícitamente la clase `O` (evitando sobreestimar o subestimar falsos positivos de fondo) y confirma que `MODULO` y `PER_DOCENTE` alcanzan **F1 = 1,0000** sin ningún error de frontera ni de clase en `gold_510`.
3. **Respaldo visual:** La representación gráfica oficial de esta matriz se encuentra en `docs/evidencias/graficos_v2/grafico_3_1_matriz_confusion_beto.png`.
