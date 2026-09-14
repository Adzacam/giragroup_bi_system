# Guía de Integración Power BI — Módulo de Forecasting (GIRA-59)

**Dashboard:** `powerbi/dashboards/giragroup_cmi.pbix`  
**Tabla DW a incorporar:** `public.fact_forecast`  
**Relaciones del Modelo:**
- `fact_forecast[id_tiempo]` $\rightarrow$ `dim_tiempo[id_tiempo]` (Relación Muchos a Uno, filtro cruzado Simple).

---

## 1. Consulta SQL de Importación (Power Query / PostgreSQL)

Al importar la tabla desde el origen PostgreSQL (`localhost:5432` / `giragroup_db`), utilizar la siguiente vista analítica o consulta nativa:

```sql
SELECT 
    ff.id_forecast,
    ff.caso_uso,
    dt.periodo_mes,
    dt.gestion,
    dt.semestre,
    dt.nombre_mes,
    dt.fecha,
    ff.valor_forecast,
    ff.ic_lower,
    ff.ic_upper,
    ff.metodo,
    ff.horizonte_meses,
    ff.generado_en
FROM public.fact_forecast ff
JOIN public.dim_tiempo dt ON ff.id_tiempo = dt.id_tiempo
ORDER BY ff.caso_uso, dt.fecha;
```

---

## 2. Medidas DAX Recomendadas

### A. Proyección de Alumnos Inscritos
```dax
Pronostico_Alumnos = 
CALCULATE(
    SUM(fact_forecast[valor_forecast]),
    fact_forecast[caso_uso] IN {"ALUMNOS_GLOBAL", "ALUMNOS_DIPLOMADO", "ALUMNOS_CURSO", "ALUMNOS_EXPERTO"}
)
```

### B. Banda Superior de Confianza (95%)
```dax
Banda_Superior_Alumnos = 
CALCULATE(
    SUM(fact_forecast[ic_upper]),
    fact_forecast[caso_uso] = "ALUMNOS_GLOBAL"
)
```

### C. Banda Inferior de Confianza (95%)
```dax
Banda_Inferior_Alumnos = 
CALCULATE(
    SUM(fact_forecast[ic_lower]),
    fact_forecast[caso_uso] = "ALUMNOS_GLOBAL"
)
```

### D. Proyección de Recaudación Mensual (Bs.)
```dax
Pronostico_Recaudacion_Bs = 
CALCULATE(
    SUM(fact_forecast[valor_forecast]),
    fact_forecast[caso_uso] = "META_MENSUAL_PROGRAMAS"
)
```

---

## 3. Especificación de Objetos Visuales

1. **Gráfico de Líneas con Sombreado de Intervalo (Demanda Estudiantil):**
   - Eje X: `dim_tiempo[periodo_mes]`.
   - Eje Y:
     - Línea 1 (Histórica): `SUM(fact_marketing[inscritos])`.
     - Línea 2 (Pronóstico): `[Pronostico_Alumnos]`.
     - Líneas 3 y 4 (Banda de error): `[Banda_Superior_Alumnos]` y `[Banda_Inferior_Alumnos]`.
   - Segmentador (Slicer): `fact_forecast[caso_uso]` para alternar entre Demanda Global, Diplomados, Cursos y Programas Expertos.

2. **Gráfico de Barras Agrupadas vs. Línea (Metas Financieras):**
   - Eje X: `dim_tiempo[periodo_mes]`.
   - Columnas: Recaudación ejecutada real (`fact_rentabilidad[monto_ejecutado]`) y Meta presupuestada (`dim_meta[monto_meta]`).
   - Línea superpuesta: `[Pronostico_Recaudacion_Bs]` con horizonte a 6 meses.
