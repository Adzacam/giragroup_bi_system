# CMI GiraGroup en Power BI

El Cuadro de Mando Integral tiene **una sola definición** para la web y para Power BI:

```
giragroup_db ─► esquema bi (backend/scripts/migrations/006_capa_semantica_cmi.sql)
                 ├─ ref_perspectiva, ref_kpi      ← configuración (se edita en la web: CMI > Configuración)
                 ├─ vw_cmi_scorecard              ← valor, meta, semáforo, tendencia por gestión e indicador
                 ├─ vw_cmi_perspectiva / global   ← índice 0–100 por perspectiva y global
                 └─ vw_metas_mensual, vw_cartera_estado, vw_riesgo_estudiante, vw_dataops_documento
                      │
          ┌───────────┴────────────┐
   GET /api/v1/cmi/scorecard   Power BI (este paquete)
   (SPA React)                 lee las mismas vistas, no recalcula
```

Power BI no recalcula indicadores ni guarda metas: si un umbral cambia en la web, el informe lo refleja en la
siguiente actualización. El informe no se conecta a la base de catálogo.

| Archivo | Uso |
| --- | --- |
| `01_power_query.pq` | Parámetros y consultas M (una por tabla) |
| `02_medidas_cmi.dax` | Medidas para pegar en la vista de consultas DAX |
| `03_tema_giragroup_cmi.json` | Tema con la paleta y el semáforo de la web |

## 1. Base de datos

La migración se aplica sola al arrancar la API. Para el usuario de Power BI, una vez:

```sql
ALTER ROLE powerbi_reader PASSWORD '<secreto fuera del repositorio>';
```

`powerbi_reader` solo lee el esquema `bi`; las vistas no exponen nombre ni CI de estudiantes.

## 2. Modelo

1. **Inicio > Transformar datos**: crear los parámetros `pHost` y `pBase` y las consultas de `01_power_query.pq`.
2. **Vista de modelo**, relaciones (uno a varios, filtro simple):

| Desde (1) | Hacia (*) |
| --- | --- |
| `Gestiones[gestion]` | `Scorecard[gestion]`, `IndicePerspectiva[gestion]`, `MetasMensual[gestion]`, `CarteraEstado[gestion]`, `RiesgoEstudiante[gestion]` |
| `Perspectivas[codigo]` | `Scorecard[perspectiva]`, `IndicePerspectiva[perspectiva]` |

3. Ordenar `Perspectivas[nombre]` por `Perspectivas[orden]` y `Scorecard[nombre]` por `Scorecard[orden]`.
4. **Herramientas externas > Tabular Editor**: ejecutar `04_tabular_editor.cs` (relaciones, orden, medidas y
   `Gestion Vista`) y guardar. Alternativa sin Tabular Editor: vista de consultas DAX con `02_medidas_cmi.dax`.
   Ninguna medida puede llamarse igual que una columna de su tabla (sin distinguir mayúsculas): por eso son
   `[Indice CMI]`, `[Total indicadores]`, `[Objetivo estratégico]`, `[Valor actual]` y `[Total registros]`.
   Si existieran `Indice 1`, `Valor 1`… (renombradas por Power BI), el script las elimina.
   El `EVALUATE` final debe devolver los mismos índices que la web para cada gestión.
5. **Vista > Temas > Examinar temas**: `03_tema_giragroup_cmi.json`.

## 3. Páginas (mismo orden y contenido que la web)

Lienzo 16:9, 1280 × 720. En todas: segmentador de `Gestiones[Gestion Vista]` en modo botones, selección única,
sincronizado entre páginas, con **Actual** seleccionado. `Gestion Vista` es una columna calculada (la crea
`04_tabular_editor.cs`) que rotula «Actual» a la última gestión del DW, así el filtro guardado no queda apuntando
a un año que no existe tras recargar datos reales.

### 1 · Resumen

| Visual | Campos |
| --- | --- |
| Tarjeta | `[Indice Texto]`, título `[Titulo Gestion]`, color de fuente por valor de campo `[Indice Color]` |
| Tarjeta de varias filas | `[En meta]`, `[En alerta]`, `[Críticos]`, `[Sin evaluar]` |
| Barra apilada 100 % | Valores: los cuatro conteos anteriores (colores del semáforo) |
| Mapa estratégico (tabla) | Filas `Perspectivas[nombre]` ordenadas de Financiera (arriba) a Aprendizaje (abajo); columnas `[Objetivo estratégico]`, `[Indice Texto]`, `[Evaluados Texto]`; color de fondo de `[Indice Texto]` por `[Indice Color]` |

Texto fijo bajo el índice: «Cada indicador puntúa 100 en meta, 60 en alerta y 20 si es crítico; los indicadores sin
dato o sin umbral no puntúan.»

### 2 · Financiera · 3 · Estudiantes y mercado · 4 · Procesos internos · 5 · Aprendizaje y crecimiento

Cada página filtra `Perspectivas[codigo]` a su perspectiva (filtro de página) y repite la misma estructura:

| Visual | Campos |
| --- | --- |
| Encabezado | Tarjeta `[Indice Texto]` + cuadro de texto con `[Objetivo estratégico]` |
| Tabla de indicadores | `Scorecard[codigo]`, `Scorecard[nombre]`, `[Valor Texto]`, `[Meta Texto]`, `[Estado Icono]`, `[Tendencia Texto]`, `[Valor Anterior Texto]` |
| Formato condicional | Color de fuente de `[Estado Icono]` por `[Estado Color]`; de `[Tendencia Texto]` por `[Tendencia Color]`; barra de datos con `[Avance Meta]` (0 a 1) |

Detalle adicional por página:

| Página | Visual de detalle |
| --- | --- |
| Financiera | Columnas agrupadas + línea: eje `MetasMensual[fecha_mes]`, columnas `[Ejecutado Bs]` y `[Meta Bs]`, línea `[Ejecutado Año Anterior Bs]`. Anillo de `CarteraEstado[estado_cartera]` por `deuda_bs` |
| Estudiantes y mercado | Solo la tabla de indicadores (las fuentes de detalle viven en el módulo académico) |
| Procesos internos | Tabla de `DataOpsDocumento`: archivo, fecha, `[Total registros]`, `[Consolidado directo]`, `[Revisión humana]`, `[Pendientes]` |
| Aprendizaje y crecimiento | Columnas de `[Estudiantes]` por `RiesgoEstudiante[nivel_prioridad]`; tabla por `RiesgoEstudiante[programa]` con `[Prioridad crítica]` |

## 4. Publicación y actualización

- Guardar como `powerbi/dashboards/giragroup_cmi.pbix` (reemplaza la versión anterior).
- En el servicio de Power BI, la actualización programada necesita una puerta de enlace local hacia `127.0.0.1:5434`.
- Tras editar metas o umbrales en la web, **Inicio > Actualizar** en Desktop (o esperar la actualización programada).

## 5. Comprobación de coherencia

Con la misma gestión seleccionada, la web (CMI > Perspectivas estratégicas) y la página Resumen deben mostrar el
mismo índice global, los mismos conteos por semáforo y el mismo índice por perspectiva. La web calcula el índice global
solo con las perspectivas visibles para el rol del usuario; en Power BI se ven todas, como el rol ADMIN.
