# Metodología de Forecasting y Trabajo Futuro (Capítulos 4 y 5)
## Sistema de Inteligencia de Negocios — GiraGroup S.R.L.
**Ticket:** GIRA-60 | **Épica:** GIRA-23 (Sprint 4)

---

## 1. Contenido para Capítulo 4: Metodología y Resultados Predictivos

### 1.1. Criterios de Selección y Alcance del Módulo Predictivo
A partir de la auditoría de calidad de datos y análisis exploratorio longitudinal sobre las fuentes operativas (`TBL_INSCRITOS.xlsx`, `EJECUTADO VS META.xlsx`), se establecieron criterios formales para determinar la viabilidad matemática de las series temporales:

1. **Condición de Suficiencia Longitudinal:** Mínimo de $N \ge 24$ observaciones mensuales continuas (equivalente a dos ciclos estacionales completos de 12 meses) para habilitar modelos con componente estacional anual.
2. **Principio de Parsimonia (Navaja de Ockham):** Selección del modelo más simple y robusto que satisfaga el comportamiento empírico observado. Frente a series de tamaño muestral medio ($N \in [24, 43]$), modelos como ARIMA/SARIMA imponen una sobrecarga de hiperparámetros $(p, d, q)(P, D, Q)_s$ difíciles de justificar con muestras acotadas. Se priorizó el suavizamiento exponencial de Holt-Winters frente a formulaciones autorregresivas complejas.
3. **Horizonte Temporal Acotado:** Restricción estricta del horizonte de proyección a $h \in [1, 6]$ meses. Proyecciones más allá de un semestre en programas de educación continua presentan una rápida degradación del intervalo de confianza por volatilidad en la oferta académica.

### 1.2. Casos de Uso Viables Implementados

| Caso de Uso | Fuente Primaria | $N$ Real | Granularidad | Método Implementado |
|---|---|---|---|---|
| **Alumnos Global** | `TBL_INSCRITOS` | 43 meses (Nov 2022 – May 2026) | Mensual | Holt-Winters Aditivo ($s=12$) |
| **Alumnos por Tipo de Programa** | `TBL_INSCRITOS` | 41 a 43 meses por tipo | Mensual | Holt-Winters Aditivo ($s=12$) |
| **Metas Financieras Mensuales** | `EJECUTADO VS META` | 36 meses (2023–2025) | Mensual | Holt-Winters Aditivo ($s=12$) |
| **Metas Financieras Anuales** | `EJECUTADO VS META` | 3 años (2023, 2024, 2025) | Anual | OLS Lineal (Tendencia Indicativa) |

### 1.3. Formulación Matemática de Holt-Winters Aditivo
Para las series mensuales con estacionalidad anual marcada (picos en los inicios de ciclo académico en marzo, julio–agosto y octubre–noviembre), se implementó el método de Holt-Winters aditivo mediante las ecuaciones de actualización:

$$\ell_t = \alpha (y_t - s_{t-m}) + (1 - \alpha)(\ell_{t-1} + b_{t-1})$$

$$b_t = \beta (\ell_t - \ell_{t-1}) + (1 - \beta) b_{t-1}$$

$$s_t = \gamma (y_t - \ell_{t-1} - b_{t-1}) + (1 - \gamma) s_{t-m}$$

La ecuación de pronóstico a $h$ periodos adelante está dada por:

$$\hat{y}_{t+h|t} = \ell_t + h b_t + s_{t+h-m(k+1)}$$

Donde $m = 12$ representa el ciclo estacional, $\ell_t$ es el nivel estimado, $b_t$ es la tendencia lineal, $s_t$ es el componente estacional y $\alpha, \beta, \gamma \in [0, 1]$ son los parámetros de suavizamiento optimizados mediante la minimización del error cuadrático medio.

### 1.4. Rigor Metodológico en Estimaciones Anuales ($N=3$)
Para la proyección de metas anuales de recaudación institucional, se dispone de $N=3$ puntos históricos consolidados (gestiones 2023, 2024 y 2025). 

* **Advertencia Metodológica:** Un ajuste de regresión con $N=3$ dispone únicamente de $\text{dof} = N - 2 = 1$ grado de libertad. En consecuencia, el coeficiente de determinación $R^2$ tiende trivialmente a la unidad por construcción matemática y no representa evidencia estadística de ajuste.
* **Decisión Técnica:** No se reportan intervalos de confianza formales al 95%. La proyección para 2026 y 2027 se define formalmente como una **"proyección indicativa de tendencia lineal"**, reportando la tasa absoluta de variación interanual ($\Delta \text{Bs./año}$) y la tasa de crecimiento anual compuesta (CAGR) como referencia orientativa de planificación estratégica.

---

## 2. Contenido para Capítulo 5: Recomendaciones y Trabajo Futuro

Para evitar observaciones del tribunal sobre casos de uso no abordados en el sistema activo, se establece formalmente su justificación y encuadre como líneas de trabajo futuro:

### 2.1. Proyección de Demanda por Programa Individual (`NUMEROPROYECTO`)
* **Diagnóstico Técnico:** El análisis longitudinal reveló que los 973 códigos POS registrados poseen una mediana de duración histórica de $N=2$ periodos mensuales (con un máximo absoluto de 5 periodos). Cada `NUMEROPROYECTO` corresponde a una cohorte académica cerrada y no a un producto recurrente longitudinal.
* **Trabajo Futuro Recomendado:** Reemplazar el modelado de series de tiempo por un enfoque de **regresión transversal (cross-sectional)** o modelos de árboles de decisión (LightGBM/XGBoost). En este esquema, se predice el número final de matriculados antes del lanzamiento de una cohorte en función de variables exógenas: escuela, precio del programa, punto de equilibrio y presupuesto publicitario (`P/ASIGNADO`).

### 2.2. Proyección de Demanda por Escuela Temática
* **Diagnóstico Técnico:** La clasificación por facultad o escuela académica no reside en el padrón de inscritos, sino en catálogos auxiliares (`IBP` de ARCA).
* **Trabajo Futuro Recomendado:** Consolidar e institucionalizar el cruce referencial automatizado en el Data Warehouse (`dim_modulo.pos_code` $\rightarrow$ `cat_escuela`) para derivar las series históricas por facultad una vez estabilizado el catálogo canónico.

### 2.3. Metas Semestrales de Recaudación ($N=6$)
* **Diagnóstico Técnico:** Con 6 observaciones semestrales (2 semestres $\times$ 3 gestiones), no es estadísticamente viable separar la tendencia general de las fluctuaciones semestrales.
* **Trabajo Futuro Recomendado:** Diferir el pronóstico semestral hasta la consolidación del segundo semestre de 2026, alcanzando el umbral mínimo de $N \ge 8$ periodos.

### 2.4. Techos Académicos y Convenios Institucionales a Nivel Mensual
* **Diagnóstico Técnico:** Aunque se cuenta con 207 contratos registrados en `BD Techos.xlsx`, las fechas de inicio presentan heterogeneidad de formatos de texto libre que requieren un proceso previo de estandarización.
* **Trabajo Futuro Recomendado:** Integrar un parser determinista de fechas de contratación en el pipeline ETL para habilitar proyecciones mensuales del canal corporativo (B2B).

### 2.5. Recomendación de Oferta Académica vs. Series de Tiempo
* **Distinción Conceptual Crítica:** El requerimiento de "recomendación de cursos" no constituye un problema de series temporales. Intentar pronosticar recomendaciones de cursos mediante modelos autorregresivos representa un error conceptual de formulación.
* **Trabajo Futuro Recomendado:** Implementar un motor de filtrado colaborativo basado en la matriz estudiante-programa y similitud de perfiles demográficos/profesionales (`CARRERA L`, `NIVEL ACADEMICO L`, `CIUDAD L`) disponible en `dim_estudiante`.
