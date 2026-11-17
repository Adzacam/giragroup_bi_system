# Diseño U-4 — Aporte de PLANIFICACION al DW y al CMI

Fecha: 2026-11-17 · Solo diseño, sin cambios de código ni esquema.

## Evidencia U-3 y estimación de carga

El libro `PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx` tiene 32 hojas y SHA-256 `c65129c62c9cfaa13ac483d2f5d7afed5c65d4a503547adb08829a075cf8dba0`. El inventario registra **19 hojas `dato_fuente`**, **11 `derivada`** (incluidas dashboards y tablas con fórmulas), **2 `borrador_duplicado`** y ninguna vacía. Se estiman **1,663 filas fuente útiles**: 18 hojas mensuales y `Programas Notificados`. Las filas útiles se cuentan cuando hay programa o POS; las filas plantilla con solo `FALSE`/`TRUE`/`0` se excluyen. Hay 49,540 fórmulas en el libro, por lo que sus resultados calculados no se tratan como valores fuente.

| Hoja fuente | Filas útiles | Filas con POS + mes | Destino A / B |
|---|---:|---:|---|
| `Julio-2025` | 22 | 22 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Agosto-2025` | 20 | 20 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Septiembre-2025` | 24 | 24 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Octubre-2025` | 30 | 23 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Noviembre-2025` | 20 | 20 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Diciembre-2025` | 24 | 24 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Programas Notificados` | 1,041 | 1,021 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Enero-2026` | 22 | 22 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Febrero-2026` | 34 | 29 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Marzo-2026` | 55 | 34 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Abril-2026` | 50 | 33 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Mayo-2026` | 63 | 30 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Junio-2026` | 53 | 32 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Julio-2026` | 30 | 0 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Agosto-2026` | 37 | 0 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Septiembre-2026` | 36 | 0 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Octubre-2026` | 42 | 0 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Noviembre-2026` | 37 | 0 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |
| `Diciembre-2026` | 23 | 0 | `dim_modulo` + `fact_planificacion_programa` (A: parcial; B: completa) |

En esas filas, **1.340** tienen POS válido y **1.334** forman una clave POS + mes; faltan POS en **323** filas y a 6 filas de `Programas Notificados` les falta además el mes. La clave POS + mes presenta **8 repeticiones** (7 dentro de una hoja y 1 entre `Diciembre-2025` y `Programas Notificados`). Por tanto sirve para relacionar planificación con programa/periodo, pero no es clave única de fila.

Los dos borradores reúnen 46 filas útiles y se excluyen del estimado fuente. `Julio-2025 borrador` comparte 18 POS con los 22 de `Julio-2025` y solo una fila idéntica; `Septiembre-2025boor` comparte sus 24 POS con `Septiembre-2025`, sin coincidencias de fila completa. El nombre sugiere borrador/copia, pero el contenido no es copia exacta. El inventario detallado, encabezados, columnas por tipo, fórmulas, estados y muestras queda en `f3u_planificacion_inventario.json`.

## Qué existe hoy y qué puede almacenar

| Tabla | Grano/capacidad útil | Límite para esta fuente |
|---|---|---|
| `dim_modulo` | Un programa/POS; `pos_code`, `nombre_modulo`, `programa`, institución | No tiene atributos de escuela, origen, fechas de notificación/inicio, estado de planificación ni precio/costo por periodo. Un POS vacío no puede vincularse con seguridad. |
| `fact_costo_programa` | Un registro por módulo (`id_modulo` es UNIQUE); costo/egreso/ingreso/rentabilidad | No tiene mes ni estados; una fila mensual sobrescribiría/colisionaría con el grano existente. `COSTO PROGRAMA` es candidato a `egreso_real`, pero no conserva versiones ni periodo. |
| `fact_rentabilidad` | Monto ejecutado y meta por categoría y tiempo | Hay `UNIQUE(id_categoria,id_tiempo)`: no acepta varias filas POS × mes en una categoría. Agregar renglones de planificación a la métrica actual podría duplicar o reemplazar las metas de `EJECUTADO VS META.xlsx`. |
| `dim_meta` | Meta por categoría/mes y tipo de programa | No tiene POS, estado ni fecha de inicio; el CMI no la usa para calcular valores actuales. |
| `fact_forecast` | Pronóstico por caso de uso y mes; único por caso/tiempo | Guarda predicciones generadas, no registros fuente de programas; no admite una fila por POS. |
| `fact_cobranzas_proyectadas` | Proyección por estudiante y tiempo | No tiene módulo/POS ni estado de inicio; no representa la planificación académica. |
| `fact_marketing` (otra tabla existente) | `id_modulo` + mes, leads, reservas, inscritos y costo; alimenta conversión | Puede recibir esos conteos si se confirma que son reales y comparables con KPI-06; no conserva estado, fechas de notificación/inicio ni id_documento en el hecho. `carga_fila_origen` puede conservar la procedencia de cada carga. |

El financiero ya expone la ejecución mensual mediante `bi.vw_metas_mensual`; la pantalla `RecaudacionCobranzas` muestra meta frente a ejecutado y las proyecciones. `bi.vw_cmi_valores` calcula **KPI-02** (ejecutado/meta del último mes con ejecución), **KPI-03** (ejecutado/meta de meses ejecutados), **KPI-13** (ejecutado/meta anual) y **KPI-14** (brecha a meta). `KPI-06` es inscritos/leads desde `fact_marketing`. El scorecard CMI lee `bi.vw_cmi_scorecard`. Estos indicadores no miden el plan de aperturas ni guardan el estado de cada programa.

## Mapeo de columnas observado

| Origen en hojas mensuales (18 hojas) | Destino A (existente, parcial) | Destino B propuesto |
|---|---|---|
| `POS` | `dim_modulo.pos_code`; relación con `dim_tiempo` por año/mes cuando ambos existan | `fact_planificacion_programa.pos_code_fuente` y `id_modulo` nullable; POS + mes como clave de relación |
| `PROGRAMA`, `TIPO DE PROGRAMA` | `dim_modulo.nombre_modulo`, `dim_modulo.programa` | `nombre_programa`, `tipo_programa` |
| `ESCUELA`, `ORIGEN DEL PROGRAMA`, `DISEÑO CURRICULAR` | Sin columna compatible en `dim_modulo` | Atributos de planificación preservados en el hecho nuevo (o dimensiones posteriores si se decide normalizarlos) |
| `FECHA` / `AÑO` / `MES` / `NOMBRE MES` | `dim_tiempo` como calendario, sin hecho de estado | `id_tiempo_plan` y `mes_plan` |
| `NOTIFICADO`, `ESTADO`, `FECHA INICIO`, `FECHA FIN` | Sin destino; no entran en `fact_costo_programa` ni en `fact_rentabilidad` | `notificado`, `estado_fuente`, `fecha_notificacion`, `fecha_inicio_plan`, `fecha_fin_plan` |
| `COSTO PROGRAMA`, `CP CON DESCUENTO 20%`, `TP AL CONTADO 100%`, `TP AL CONTADO 80%` | `COSTO PROGRAMA` → `fact_costo_programa.egreso_real` solo como resumen por POS y sin mes; precios/tarifas requieren confirmar semántica antes de mapear a `ingreso` | Campos numéricos separados, con etiqueta de origen y unidad; no sumarlos como ingresos hasta validarlos |
| `LEADS`, `RESERVAS`, `N° INSCRITOS` | `fact_marketing.leads`, `.reservas`, `.inscritos`, si se comprueba que son datos observados | Conteos planificados y observados separados para no mezclar pronóstico con ejecución |
| `P/EJECUTADO`, `P/ASIGNADO`, `N°`, reprogramación y comentarios | Sin destino inequívoco; `P/EJECUTADO` tiene valores numéricos heterogéneos | Guardar campos originales con su nombre/unidad; mapear solo tras validar significado. `P/EJECUTADO` queda `requiere_revision`. |

`Programas Notificados` (1.041 filas útiles) aporta `POS`, programa/tipo, costo, punto de equilibrio, fecha de notificación, fecha de inicio/finalización, duración y estado. Los estados observados son `Finalizo` (559), `En curso` (50), `Por iniciar` (242), `Baja` (1) y 189 vacíos. El destino A puede poblar `dim_modulo` y resumir costo en `fact_costo_programa`, pero pierde estado y fechas. En B esos campos van a `fact_planificacion_programa`.

Los estados mensuales incluyen `Inicio Confirmado`, `Baja` y `Reprogramado`; `NOTIFICADO` es booleano. `Inicio Confirmado` no se equipara automáticamente con `En curso`: se conserva como estado propio hasta definir la regla de negocio.

## Opción A — solo tablas y KPI existentes

- Upsert de POS y nombre/tipo en `dim_modulo`.
- Cargar `LEADS`, `RESERVAS`, `N° INSCRITOS` y costos a `fact_marketing` solo tras verificar que son observaciones reales y que el grano POS/mes no duplica otras fuentes. De ese modo podría aportar al KPI-06 y a su serie mensual.
- Cargar `COSTO PROGRAMA` a `fact_costo_programa` únicamente como un resumen por POS sin mes; conservar montos por periodo en `fact_rentabilidad`/`dim_meta` exige agregarlos por categoría y mes y conciliar primero contra las metas ya existentes.
- KPI-02/03/13/14 y `bi.vw_metas_mensual` permanecen como están; siguen midiendo ejecución contra metas agregadas. KPI-06 usa leads e inscritos solamente si se valida su semántica.
- **No puede** mostrar `programas planificados frente a iniciados` ni conservar `notificado`, `Inicio Confirmado`, `Por iniciar`, `En curso`, `Finalizo`, fecha de inicio o reprogramaciones. Tampoco admite metas por POS/mes en `fact_rentabilidad` sin cambiar su unicidad. A es apta solo para los atributos/cifras que encajan tras agregación, no para el aporte integral prometido.

## Opción B — un hecho de planificación y un KPI

Crear en F3V **`fact_planificacion_programa`**, con grano de una fila fuente útil (programa/mes/hoja/fila); `id_modulo` nullable para filas todavía sin POS; `id_tiempo_plan`; POS y nombre fuente; tipo/escuela/origen; fechas de notificación/inicio/fin; estado original; costo/tarifas separados; punto de equilibrio y conteos con sus indicadores de plan/real. La vista mensual calcula conteos por estado y deja los importes agregados disponibles cuando su unidad se confirme. `bi.vw_metas_mensual` y KPI-02/03/13/14 siguen dando el comparativo financiero agregado actual, sin sumar dos fuentes de meta no conciliadas.

- **Clave de relación:** POS + mes cuando exista POS; los 323 renglones sin POS quedan guardados con `id_modulo = NULL` y mes/nombre. No asignar un POS inventado.
- **Idempotencia:** derivar la clave de fila origen con el mecanismo de `carga_fila_origen` (hash de archivo + hoja + fila Excel + contenido; registrar además la clave de contenido). Guardar en la nueva fila la clave por archivo/fila como UNIQUE/FK. POS + mes no es único (hay repeticiones observadas) y no sustituye la clave de origen.
- **KPI-23 propuesto — programas iniciados frente a programas planificados:** `100 × COUNT(plan_id con estado en (En curso, Finalizo)) / COUNT(plan_id con estado en (Por iniciar, En curso, Finalizo))`, usando por ahora únicamente los estados conocidos de `Programas Notificados`; `Baja` y estado vacío se excluyen del numerador y denominador. Con los conteos actuales: `100 × (50 + 559) / (242 + 50 + 559) = 71,56 %`. El KPI debe mostrar cobertura de estado: `851/1.041` filas (81,75 %) tienen estado conocido; no extrapolar los 189 vacíos.
- **Vista nueva** `bi.vw_planificacion_ejecucion_mensual`: conteos planificados/iniciados/finalizados/baja/reprogramados por mes, cobertura POS, y montos por campo separado cuando Lean confirme unidad. El scorecard CMI incorpora KPI-23; la vista se ofrece a CMI Power BI y al detalle mensual. La tendencia financiera agregada de `bi.vw_metas_mensual` continúa en `RecaudacionCobranzas`.
- **Presupuesto frente a ejecutado:** los KPI actuales entregan comparación agregada mes/año. El libro no tiene un campo `ingreso ejecutado` con semántica confirmada por POS/mes; `P/EJECUTADO` requiere revisión. No se propone un KPI de monto planificado/ejecutado por POS hasta conciliar ese campo y su correspondencia con `fact_rentabilidad`.

### Invariantes de B

| Invariante actual | B propuesto | Cambio |
|---|---:|---|
| Tablas DW | 50 | **51** (+1 tabla) |
| Hechos | 9 | **10** (+1 hecho) |
| KPI activos | 22 | **23** (+1: KPI-23) |
| KPI de ingreso agregado | KPI-02/03/13/14 | Mantienen definición y origen | 0 cambios de fórmula durante F3U |

La vista adicional es una vista, no una tabla. Si después se aprueba otro KPI monetario por programa, el contador subiría a 24 y su fórmula/origen habría que definirlos tras resolver `P/EJECUTADO`; no está incluido en la alternativa B propuesta.

## Recomendación para decisión de Lean

**B**, porque el requisito de PLANIFICACION incluye fechas/estados por programa y cruces POS/mes; los hechos existentes no tienen ese grano y sus restricciones harían perder filas o mezclar metas. Mantener la ejecución financiera agregada existente hasta validar importes del libro. Antes de F3V, resolver el significado de `P/EJECUTADO` y si `Inicio Confirmado` representa inicio efectivo; no inferir esas reglas de los nombres.
