# Contexto de Datos — Analítica Predictiva Macro (`/api/v1/forecast/analitica-macro`)

Documento de referencia para analistas y desarrolladores del Cuadro de Mando Integral V2 (Loop L5-0).

## Invariantes del motor predictivo
- **Holt-Winters amortiguado (`damped_trend=True`, `seasonal_periods=12`)**: se utiliza para proyección mensual de demanda (Caso 1) y cierre mensual (Caso 3), con evaluación **hold-out de 6 meses** e **Intervalo de Confianza al 95 %** acotado a $\hat{y} \ge 0$.
- **OLS mensual (`N = 40` meses)**: recta de tendencia indicativa superpuesta sobre la serie mensual histórica.
- **OLS anual**: **solo descriptiva** (N reducido de gestiones anuales cerradas); nunca se interpreta como pronóstico inferencial.

## Campos por caso

### `caso1_demanda_global` (Demanda Global de Alumnos)
| Campo | Significado | Uso analítico |
|---|---|---|
| `n_observaciones` | Cantidad de meses históricos ($N$) | Valida cobertura longitudinal |
| `periodos_historicos`, `valores_historicos` | Serie mensual real de inscritos | Línea base histórica |
| `periodos_proyectados`, `forecast_hw` | Proyección Holt-Winters para el horizonte (1–6 m) | Planificación de cupos |
| `ic_lower_95`, `ic_upper_95` | Bandas de confianza al 95 % ($\hat{y} \ge 0$) | Rango de incertidumbre |
| `mape_pct`, `rmse` | Error porcentual medio y error cuadrático medio en hold-out 6 m | Calidad del modelo (< 20 % MAPE = buena precisión) |
| `pendiente_ols_mes`, `cagr_historico_pct` | Ritmo mensual OLS y crecimiento anual compuesto | Dirección de largo plazo |

### `caso2_demanda_programa` (Matriz de Viabilidad por Programa)
| Campo | Significado | Uso analítico |
|---|---|---|
| `matriz_viabilidad[]` | Lista de programas con `programa`, `tipo`, `total_historico`, `anio_anterior`, `inscritos_anio_anterior`, `anio_actual`, `inscritos_anio_actual`, `cagr_pct`, `proyeccion_6m`, `tendencia_ols`, `decision_sugerida`, `justificacion`, `badge_color` | Priorización comercial (abrir nueva versión, continuar o reestructurar) |

### `caso3_metas_mensuales` (Presupuesto y Recaudación Mensual)
| Campo | Significado | Uso analítico |
|---|---|---|
| `meses_etiquetas`, `meta_catalogo_bs`, `ejecutado_real_bs` | Serie mensual comparativa Meta vs. Recaudado (Bs) | Control presupuestario mensual |
| `mes_actual` | Objeto con `periodo`, `meta_mes_bs`, `cierre_proyectado_hw_bs`, `cumplimiento_proyectado_pct` | Alerta temprana de cierre del mes en curso |

### `caso4_metas_anuales` (Planificación Plurianual — OLS solo descriptiva)
| Campo | Significado | Uso analítico |
|---|---|---|
| `gestion_actual`, `meta_anual_institucional_bs`, `recaudado_acumulado_bs`, `porcentaje_avance_meta` | Avance de recaudación frente a la meta anual | Medidor ejecutivo anual |
| `anios_historicos`, `valores_historicos_bs`, `proyecciones_ols` | Serie anual real y recta OLS descriptiva | Referencia visual de trayectoria anual |
| `pendiente_anual_bs`, `cagr_historico_pct`, `nota_metodologica` | Pendiente anual OLS, CAGR y nota de alcance | Contexto descriptivo |
