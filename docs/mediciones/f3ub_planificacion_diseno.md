# Diseño F3U-B — PLANIFICACION y CMI

Fecha: 2026-11-17 · Propuesta documental para F3V; no cambia código ni esquema.

## Decisiones incorporadas y discrepancias de la fuente

- Opción **B**: proponer `fact_planificacion_programa`, `bi.vw_planificacion_ejecucion_mensual` y KPI-23. Los invariantes quedarían en **51 tablas / 10 hechos / 23 KPI**; vistas `bi`: 9 → 10. KPI-02/03/13/14 mantienen su fuente y fórmula actual.
- En los estados del hecho, `Inicio Confirmado`, `En curso` y `Finalizo` cuentan como iniciado. `Por iniciar` entra al denominador; `Baja` y estado vacío se excluyen. Se conserva el valor original del estado.
- `P/EJECUTADO` / `P/ASIGNADO` se guardan como `pauta_ejecutada` / `pauta_asignada`. No se agregan a ingresos ni al KPI-23.
- B-4 encontró que la meta mensual manual de techos de Bs 89.000 existe en `Informe Gestión` para febrero–noviembre de 2026; `EJECUTADO VS META` tiene valores distintos. Se recomienda mantener `EJECUTADO VS META.xlsx` como autoridad de KPI financieros y usar `Informe Gestión` en el modelo de planificación, con categorías distintas.
- **Discrepancia del OKR:** el plan describe «Abrir 12 programas al mes», pero la celda `Informe Gestión!M4` dice “Abrir 12 programas de Diplomado, 6 Programas Experto y 8 Cursos Cortos al mes”, es decir, 26 aperturas mensuales al sumar los tres tipos. La meta de aperturas no debe codificarse hasta resolver si el objetivo operativo es 12 o 26. KPI-23 porcentual y su banda propuesta son independientes del conteo mensual OKR.
- El inventario U-3 anterior atribuía 71,56 % a KPI-23. Ese cálculo queda **anulado**: no incluía los estados `Inicio Confirmado` de las hojas mensuales y mezclaba una población que requiere deduplicación por POS/mes.

Evidencia: [inventario U-3](f3u_planificacion_inventario.json), [adenda B-4](f3ub_planificacion_adenda.json). La adenda lista todas las 358 celdas constantes de `Informe Gestión`, las 24 metas regulares mensuales, las 48 comparaciones, los estados por hoja y las 48 filas de pauta.

## U-3: hojas fuente y aporte por hoja

Las 18 hojas mensuales suman **622** filas útiles; `Programas Notificados` aporta **1.041**; estimación total: **1.663 filas** antes de la conciliación U-2. Una fila útil es la que contiene programa o POS válido; no incluye filas plantilla ni hojas derivadas. Se esperan hasta 1.663 registros en el hecho nuevo; el número final depende del cuadre U-2.

| Hoja `dato_fuente` | Filas útiles | Mapeo al hecho propuesto |
|---|---:|---|
| `Julio-2025` | 22 | Mapeo mensual común (debajo) |
| `Agosto-2025` | 20 | Mapeo mensual común |
| `Septiembre-2025` | 24 | Mapeo mensual común |
| `Octubre-2025` | 30 | Mapeo mensual común |
| `Noviembre-2025` | 20 | Mapeo mensual común |
| `Diciembre-2025` | 24 | Mapeo mensual común |
| `Enero-2026` | 22 | Mapeo mensual común |
| `Febrero-2026` | 34 | Mapeo mensual común |
| `Marzo-2026` | 55 | Mapeo mensual común |
| `Abril-2026` | 50 | Mapeo mensual común |
| `Mayo-2026` | 63 | Mapeo mensual común |
| `Junio-2026` | 53 | Mapeo mensual común |
| `Julio-2026` | 30 | Mapeo mensual común |
| `Agosto-2026` | 37 | Mapeo mensual común |
| `Septiembre-2026` | 36 | Mapeo mensual común |
| `Octubre-2026` | 42 | Mapeo mensual común |
| `Noviembre-2026` | 37 | Mapeo mensual común |
| `Diciembre-2026` | 23 | Mapeo mensual común |
| `Programas Notificados` | 1.041 | Mapeo de notificaciones (debajo) |

**Mapeo mensual común** (según encabezado real por hoja): `POS` → `pos_code_fuente` y `id_modulo` cuando resuelva; `PROGRAMA` → `nombre_programa`; `TIPO DE PROGRAMA` → `tipo_programa`; `ESCUELA` → `escuela`; `ORIGEN DEL PROGRAMA` → `origen_programa`; `DISEÑO CURRICULAR` → `diseno_curricular`; `FECHA`/`AÑO`/`MES`/`NOMBRE MES` → `id_tiempo_plan` (si falta una parte, completar del nombre de la hoja; si persiste vacío, `NULL`); `NOTIFICADO` → `notificado`; `ESTADO` → `estado_fuente` sin normalizar; `FECHA INICIO`/`FECHA FIN` → fechas plan; `COSTO PROGRAMA`, `CP CON DESCUENTO 20%`, `TP AL CONTADO 100%`, `TP AL CONTADO 80%`, `PE` → columnas independientes de costo/tarifa/punto de equilibrio; `LEADS`, `RESERVAS`, `N° INSCRITOS` → columnas fuente separadas (no llamar “real” hasta validar su semántica); `P/EJECUTADO`/`P/ASIGNADO` → pauta; `REPROGRAMACIONES`, `COMENTARIOS`, `Comentario DAF`, `Comentario Admisiones`, `Comentario Digital / Video solicitado`, fechas de campaña y días → campos de pauta/comentario o `payload_fuente` preservado. Las variaciones de escritura de los encabezados quedan en U-3.

`Programas Notificados`: `POS`, `Programa`, `Tipo de programa`, `Escuela`, `Categoria de origen del programa`, `Diseño Curricular`, `Fecha de nofiticación`, `Fecha Inicio`, `Fecha de Finalización`, `Duración del programa (meses)`, `Costo programa`, `Punto de equilibrio` y `Estado del programa` → los campos equivalentes del hecho. Las seis filas sin mes conservan `id_tiempo_plan = NULL`; no se inventa un periodo. U-3 observa ocho colisiones de POS+mes; el hecho guarda cada fila fuente, pero la vista no debe sumar costos o tarifas repetidas de fuentes distintas hasta que haya una regla de precedencia validada.

`Informe Gestión` aporta metas mensuales a `dim_meta`, no una fila por programa: las celdas G de los 12 renglones mensuales (filas 8–13 y 15–20 para 2025; 27–38 para 2026) llevan el rótulo **“META (PROGRAMAS REGULARES Y TECHOS ACADÉMICOS)”**. Se mapean como meta total a `dim_meta.monto_meta`, categoría `PLAN_INGRESO_TOTAL`, con `id_tiempo` mensual. No se inventa una meta separada de programas regulares, porque G no separa los componentes. Las celdas E28:E37 son el ingreso proyectado de techos, Bs 89.000 de febrero a noviembre 2026; se mapean como categoría de planificación separada `PLAN_INGRESO_TECHOS_PROYECTADO`. Los objetivos mensuales de apertura van a `dim_meta` como categoría `OKR_APERTURAS`, pero el monto objetivo (12 o 26) queda bloqueado por la discrepancia anterior. La clave lógica es categoría + periodo + tipo; la procedencia fila/celda se registra en `carga_fila_origen`. Las 358 celdas constantes de esa hoja están enumeradas en B-4; no se cargan fórmulas como valores fuente.

`Centralizado_Mensual` (28.320 fórmulas), dashboards, hojas auxiliares de mes y borradores no se cargan como hechos fuente. `Dashboard Programas` no tiene objetos PivotTable ni archivos pivot cache/table en el XLSX; es derivada, no fuente.

## Conciliación de metas y pauta (B-4)

La adenda presenta una tabla de conciliación de **24 filas, una por mes**, con la meta total de columna G frente a la suma de categorías `PROGRAMAS` y `TECHOS/CERRADOS` en `EJECUTADO VS META`, además de las 48 filas de detalle por categoría. La meta total de Informe Gestión difiere de esa suma en los 24 meses. En 2026, el ingreso proyectado de techos de Bs 89.000 difiere de `META POR CATEGORIA 2026` en los diez meses: el archivo de metas contiene valores de Bs 99.024 para febrero–junio y Bs 116.657 para julio–noviembre. En consecuencia:

- `fact_rentabilidad.monto_meta` y KPI-02/03/13/14 siguen alimentándose de `EJECUTADO VS META.xlsx`; no se suman ni reemplazan con metas de Informe Gestión.
- La vista de planificación muestra separadamente la meta total de Informe Gestión, el ingreso proyectado de techos, y los importes de meta/ejecución de `EJECUTADO VS META`; la diferencia de fuente se hace visible sin sumar ambos archivos.
- `dim_meta` tiene `(categoria, id_tiempo, monto_meta, tipo_programa)` y no define unicidad/procedencia. F3V debe agregar idempotencia consultable por fila fuente/celda con `carga_fila_origen`, además de una regla de sustitución controlada por `clave_origen` para no duplicar una misma meta al recargar.

El recuento con valores almacenados de las celdas de estado reporta en `Programas Notificados`: Finalizo 559, En curso 50, Por iniciar 242, Baja 1 y 189 vacíos; 852/1.041 tienen estado conocido (incluye Baja). En las 18 hojas mensuales se conservan los conteos de `Inicio Confirmado`, `Baja` y `Reprogramado` por separado en B-4. No se suman esas poblaciones entre hojas y `Programas Notificados`: pueden representar el mismo POS/mes. Para KPI-23 se agrupa por periodo y POS; para filas sin POS, por clave de origen.

Pauta B-4: 48 filas positivas de julio, agosto y octubre de 2025; rango Bs 60,84–391,77; mediana `P/EJECUTADO / P/ASIGNADO` = 0,805. Correlaciones recalculadas: leads 0,357; Días Activos 0,337; Días Totales 0,347; inscritos 0,150. Ninguno de los dos campos de días reproduce el 0,41 del análisis previo; se deben revisar selección de filas/campo en F3V, sin cambiar la interpretación decidida de que es pauta.

## DDL propuesto: migración backend 017 / versión `V016`

```sql
CREATE TABLE public.fact_planificacion_programa (
  id_planificacion BIGSERIAL PRIMARY KEY,
  id_modulo INTEGER NULL REFERENCES public.dim_modulo(id_modulo) ON DELETE SET NULL,
  id_tiempo_plan INTEGER NULL REFERENCES public.dim_tiempo(id_tiempo) ON DELETE SET NULL,
  id_documento INTEGER NOT NULL REFERENCES public.dim_origen_documental(id_documento) ON DELETE CASCADE,
  clave_fila_origen VARCHAR(64) NOT NULL UNIQUE
    REFERENCES public.carga_fila_origen(clave) ON DELETE CASCADE,
  clave_contenido CHAR(64) NOT NULL,
  hoja VARCHAR(200) NOT NULL,
  fila_excel INTEGER NOT NULL,
  pos_code_fuente VARCHAR(80) NULL,
  nombre_programa TEXT NULL,
  tipo_programa VARCHAR(100) NULL,
  escuela VARCHAR(120) NULL,
  origen_programa VARCHAR(120) NULL,
  diseno_curricular VARCHAR(160) NULL,
  fecha_notificacion DATE NULL,
  fecha_inicio_plan DATE NULL,
  fecha_fin_plan DATE NULL,
  duracion_meses NUMERIC(8,2) NULL,
  estado_fuente VARCHAR(120) NULL,
  notificado BOOLEAN NULL,
  costo_programa NUMERIC(14,2) NULL,
  costo_descuento_20 NUMERIC(14,2) NULL,
  tarifa_contado_100 NUMERIC(14,2) NULL,
  tarifa_contado_80 NUMERIC(14,2) NULL,
  punto_equilibrio NUMERIC(14,2) NULL,
  leads_fuente NUMERIC(14,2) NULL,
  reservas_fuente NUMERIC(14,2) NULL,
  inscritos_fuente NUMERIC(14,2) NULL,
  pauta_ejecutada NUMERIC(14,2) NULL,
  pauta_asignada NUMERIC(14,2) NULL,
  payload_fuente JSONB NULL,
  requiere_revision BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX ix_fact_plan_pos_mes ON public.fact_planificacion_programa(pos_code_fuente,id_tiempo_plan);
```

El loader crea la misma `clave_fila_origen` que registra en `carga_fila_origen.clave`, liga `id_documento` y tabla de destino, y hace upsert/deduplicación por esa clave. Se usa la huella del archivo + hoja + fila Excel + texto de fila, como `clave_origen` en el loader actual. `clave_contenido` conserva además la deduplicación de contenido y ocurrencia. POS+mes es clave de relación, **no** clave única: U-3 observa ocho repeticiones y 323 filas útiles sin POS. Los dos borradores (46 filas útiles) quedan fuera de la carga estimada.

## KPI-23 y vista nueva

Fórmula propuesta mensual: `100 × programas iniciados / programas planificados con estado conocido`. Un programa cuenta como iniciado si cualquier registro del grupo POS+mes tiene estado `Inicio Confirmado`, `En curso` o `Finalizo`; como planificado si al menos uno tiene `Por iniciar`, `Inicio Confirmado`, `En curso` o `Finalizo`. `Baja` y estado vacío no agregan ni al numerador ni al denominador. Para filas sin POS se usa la identidad de fila origen para no perderlas ni unir programas diferentes. El `bool_or` del grupo hace que un estado iniciado no se cuente como dos programas cuando aparece en ambas fuentes.

SQL de referencia (el filtro del periodo se aplica al parámetro `:id_tiempo`):

```sql
WITH por_programa_mes AS (
  SELECT id_tiempo_plan,
         COALESCE(NULLIF(upper(btrim(pos_code_fuente)), ''),
                  'ORIGEN:' || min(clave_fila_origen)) AS programa_mes,
         bool_or(estado_fuente IN ('Inicio Confirmado','En curso','Finalizo')) AS iniciado,
         bool_or(estado_fuente IN ('Por iniciar','Inicio Confirmado','En curso','Finalizo')) AS planificado
  FROM public.fact_planificacion_programa
  WHERE id_tiempo_plan = :id_tiempo
  GROUP BY id_tiempo_plan,
           COALESCE(NULLIF(upper(btrim(pos_code_fuente)), ''),
                    'ORIGEN:' || clave_fila_origen)
)
SELECT 100.0 * count(*) FILTER (WHERE iniciado)
       / NULLIF(count(*) FILTER (WHERE planificado), 0) AS kpi_23
FROM por_programa_mes;
```

`bi.ref_kpi` agrega KPI-23 bajo Procesos, unidad `%`, sentido `MAX`, meta propuesta `0.85`, umbral verde `0.85`, ámbar `0.60`; la meta exige aprobación final de Lean. El OKR de aperturas se muestra como objetivo operacional mensual separado, no es numerador ni ingreso del KPI-23. La vista `bi.vw_planificacion_ejecucion_mensual` entrega `gestion`, `mes`, `id_tiempo`, `programas_planificados`, `programas_iniciados`, `programas_finalizados`, `programas_baja`, `programas_reprogramados`, `kpi_23`, `cobertura_estado`, `programas_con_pos`, `meta_ingreso_total`, `ingreso_proyectado_techos`, `meta_aperturas_okr`, `costo_programa`, y `pauta_asignada`/`pauta_ejecutada` por separado. Cuando falte POS, fecha o estado, la cobertura deja visible la falta; no se imputa.

## Archivos, requisitos y pruebas para F3V

Áreas previstas de cambio: `backend/models/` (hecho), `backend/services/ingestion_service.py` y `backend/services/extraccion_por_encabezado.py` (mapeo y preservación), `backend/services/dw_loader.py` (idempotencia del hecho y metas), `backend/routers/dataops/` (consolidación), `backend/scripts/migrations/017_*.sql`, `db/migrations/V016__*.sql`, `backend/scripts/migrations/006_capa_semantica_cmi.sql` o migración posterior (vista y catálogo), `backend/routers/cmi.py` / `backend/services/kpi_service.py` y el cliente del scorecard CMI. La pauta no se enruta a ingreso ni altera `fact_marketing` sin decisión adicional.

Pruebas nuevas: extracción y carga de las 32 hojas (19 fuente/11 derivada/2 borrador); idempotencia por archivo-fila y por recarga; ocho colisiones POS+mes; 323 registros sin POS; seis de `Programas Notificados` sin periodo; estados (incluye `Inicio Confirmado`, `Baja` y vacío); reglas de `bool_or` con estado duplicado; conversión de fechas/montos; metas con dos archivos y una celda 2026 discrepante; 48 filas de pauta separadas de ingresos; generación del scorecard KPI-23; repetición completa del lote y comparación de huellas.

Documentación a actualizar en F3V, solo después de resultados finales: el inventario DW y su invariante 50/9/22; la definición y visualización CMI (SFV F.2 y detalle del scorecard); la matriz de trazabilidad de `HU-09` (cálculo dinámico) y `HU-10` (vistas CMI); el modelo físico y catálogo KPI de la tesis. No tocar la fuente de verdad en F3U-B.

## Decisiones finales para Lean

1. Aprobar o corregir la meta de aperturas: la celda `M4` suma 26 por mes; el plan F3U-B la resume como 12. Confirmar también si los tres objetivos por tipo son sumables.
2. Confirmar que las metas de Informe Gestión quedan en `dim_meta` con categorías de planificación y que KPI-02/03/13/14 conservan `EJECUTADO VS META.xlsx` como autoridad ante diferencias.
3. Confirmar meta KPI-23 `85 %` y bandas `85 % / 60 %`, y si la unidad de scorecard es porcentaje mensual.
4. Decidir si las diferencias de días/correlación de pauta y los defectos de U-2 requieren corrección en F3V o se declaran limitaciones.
5. Pendientes de la remedición final F3V: encabezado/huella de SFV, B-7 n=3 en alto rendimiento y citar corridas limpias.
