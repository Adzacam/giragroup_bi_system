# ADW L6-0 · Fuente de captación para KPI-06 (conversión de admisiones)

Fecha: 2026-11-20 · Modo: solo lectura (DW viva y snapshot sin tocar; consultas `SELECT` sobre la copia tmpfs `adw_pg_tmpfs`; sin commit).
Scripts: `scripts/auditoria_dw/adw_l6_0_inventario_excel.py`, `scripts/auditoria_dw/adw_l6_0_kpi06.py`.
Salidas: `docs/mediciones/adw_l6_0_inventario_excel.csv` (2.094 columnas), `docs/mediciones/adw_l6_0_kpi06.csv`.

## Conclusión

KPI-06 **no se puede calcular hoy desde `fact_marketing`**, que es de donde lee el CMI. Sí existe, en el propio lote, una fuente con interesados (LEADS) e inscritos en la misma fila: la hoja mensual de `PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx` (doc 1). Ya está cargada en `fact_planificacion_programa` (`leads_fuente`, `inscritos_fuente`). Su cobertura es parcial: solo 2025 (jul–dic) y 2026 (ene–jun). No hay datos para 2023 ni 2024.

Correcciones al plan:
- `fact_marketing.reservas` **no** está lleno: es 0 en las 13.860 filas y en todas las gestiones. Los datos de reservas están en el doc 1 y en `fact_planificacion_programa.reservas_fuente`.
- Los leads que faltan en `fact_marketing` están en el doc 1, pero el cargador no los envía a esa tabla (ver sección 3).

## 1. Identificación de `TBL_INSCRITOS.xlsx` (doc 44)

El hash cargado en `dim_origen_documental` (id 44, `id_lote` 36) es `5b72c61c436fd5d7e7332ae734001aaee52f9fb24645400d253a6c64b3d8b572`.

| Ruta | Bytes | Filas (hoja TBL_INSCRITOS) | sha256 (inicio) | Estado |
|---|---|---|---|---|
| `uploads/data/TBL_INSCRITOS.xlsx` | 3.436.775 | 15.196 datos | 5b72c61c… | **Cargado (idéntico al hash del doc 44)** |
| `output/backups/f0_lote/originales/TBL_INSCRITOS.xlsx` | 3.436.775 | igual | 5b72c61c… | Copia idéntica |
| `output/backups/f0_lote/generador/uploads/data/TBL_INSCRITOS.xlsx` | 3.436.775 | igual | 5b72c61c… | Copia idéntica |
| `output/backups/f0_lote/slices/TBL_INSCRITOS.xlsx` | 118.393 | 391 datos | d2be9a42… | Recorte |
| `output/backups/f0_lote/corridas/f0_a0_llena_r1_interrumpida/landing/1/TBL_INSCRITOS.xlsx` | 118.393 | igual que slices (mismo hash) | d2be9a42… | Recorte |
| `backend/docs/evidencias/ciclo_mensual_slices/TBL_INSCRITOS.xlsx` | 119.038 | 391 datos | 935e1ef2… | Recorte (distinto del anterior) |
| `uploads/test/TBL_INSCRITOS_TEST.xlsx` | 40.864 | 150 datos | 0000b55f… | Prueba |

Hojas de `TBL_INSCRITOS.xlsx`: `TBL_INSCRITOS` (37 columnas) y `BAJAS POR DUPLICADOS` (sin datos). Columnas relevantes: `MARCA TEMPORAL`, `NOMBRE DEL PROGRAMA`, `NUMEROPROYECTO`, `ESTADO DEL INSCRITO`, `TIPO DE INSCRIPCION`. **No tiene ninguna columna de interesados, leads, reservas ni prospectos.** Las únicas coincidencias de palabras clave son texto libre (`INSTITUCION DONDE TRABAJA`, `CORREO`).

Filas de `TBL_INSCRITOS` por año de `MARCA TEMPORAL`: 2022: 53 · 2023: 3.551 · 2024: 4.563 · 2025: 4.737 · 2026: 2.292.

## 2. Inventario de hojas y columnas de captación (lote completo)

Lista completa: `docs/mediciones/adw_l6_0_inventario_excel.csv`. Solo se muestran columnas con embudo previo a la inscripción.

| Archivo (doc) | Hoja | Columna | Qué contiene | N filas no vacías |
|---|---|---|---|---|
| PLANIFICACION… (doc 1) | Centralizado_Mensual | `LEADS` | Interesados por programa y mes | 83 |
| PLANIFICACION… (doc 1) | Centralizado_Mensual | `RESERVAS` | Reservas por programa y mes | 114 |
| PLANIFICACION… (doc 1) | Centralizado_Mensual | `N° INSCRITOS` | Inscritos por programa y mes | 84 |
| PLANIFICACION… (doc 1) | Julio-2025 … Junio-2026 (12 hojas mensuales) | `LEADS`, `RESERVAS`, `N° INSCRITOS` | Mismo dato por fila-programa; fuente primaria | LEADS 2025: 128 · 2026: 174 · INSCRITOS 2025: 129 · 2026: 151 · RESERVAS 2025: 108 · 2026: 138 |
| PLANIFICACION… (doc 1) | `Julio-2025 borrador`, `Septiembre-2025boor` | `LEADS`, `RESERVAS` | Duplicados de borrador; **excluidos** (Julio-2025 borrador suma lo mismo que Julio-2025) | — |
| Base centralizada ARCA (doc 43) | IBP | `LEADS` | Leads por programa, 2026 (suma 41.416) | 147 (145 pares con `N° DE INSCRITOS`) |
| Base centralizada ARCA (doc 43) | IBP | `N° DE INSCRITOS` | Inscritos por programa, 2026 (suma 1.198) | 146 |
| TBL_INSCRITOS (doc 44) | TBL_INSCRITOS | — | Sin columna de embudo | 0 |
| BD Cobranzas (doc 36), BD Egresos (doc 39), Evaluaciones (docs 40–42) | varias | solo texto | `OBSERVACIÓN`, `COMENTARIOS` y preguntas abiertas que mencionan «reserva», «interés» o «inscrito» | no es embudo |
| BD Techos (37), EJECUTADO VS META (38) | — | — | Sin leads ni reservas | 0 |

Notas:
- La hoja IBP tiene 146 filas en 2026 y 1 en 2025 (sin valores). **No determinado** si IBP es real o proyectado: el nombre sugiere un plan de negocio (META 2025/2027, PUNTO EQUILIBRIO).
- La definición de `LEADS` no está documentada en ningún archivo del lote. **No determinado** si incluye reservas o si coincide con «interesados».
- `N° INSCRITOS` (doc 1) no concilia con `TBL_INSCRITOS`: 2025 Jul–Dic suma 1.430 en el doc 1, frente a 4.737 filas de TBL_INSCRITOS en todo 2025. Las dos fuentes no son intercambiables.

Verificación cruzada: los totales del doc 1 coinciden exactamente con `fact_planificacion_programa` en la copia tmpfs (2025: leads 35.460, inscritos 1.430, reservas 119; 2026: leads 47.402, inscritos 1.314, reservas 179). Esto confirma que el doc 1 ya está cargado en esa tabla.

## 3. Por qué `fact_marketing.leads` = 0

Consulta (tmpfs): `fact_marketing` por gestión, `leads` = 0 y `reservas` = 0 en 2022–2026; `inscritos` = 106 / 7.102 / 9.124 / 9.472 / 4.576; `leads_captacion` y `inscritos_captacion` = NULL en todas las filas.

Quién escribe `fact_marketing` (código de `pipeline/` y `backend/services/`):

| Escritor | Fuente que espera | Qué escribe |
|---|---|---|
| `dw_loader.py` ~1483–1503 (ruta ADMISION) | Inscripciones (TBL_INSCRITOS) | `inscritos += 1`; crea filas con `leads=0`, `reservas=0` (hardcoded) |
| `dw_loader.py` ~1858–1910 (ruta MARKETING) | Registros clasificados como marketing con `leads` e `inscritos` explícitos en el mismo registro | `leads`, `reservas`, `leads_captacion`, `inscritos_captacion` |
| `pipeline/analytics/seed_historical_facts.py` `seed_fact_marketing` | TBL_INSCRITOS | `inscritos` = conteo por mes y programa; `leads=0`, `reservas=0` |
| `seed_historical_facts.py` `seed_fact_marketing_leads` | Doc 1, hoja Centralizado_Mensual: `LEADS`, `RESERVAS`, `AÑO`, `MES`, `POS` | `leads` y `reservas` |

Por qué quedan en cero:
1. **TBL_INSCRITOS no tiene leads.** `pipeline/ingesta.py` línea 716 clasifica la fuente como `MARKETING` solo si detecta una columna de lead. Como TBL_INSCRITOS no la tiene, queda como `ADMISION`, y esa ruta fija `leads=0`.
2. **Ninguna fuente del lote llega a la ruta MARKETING.** El doc 1 se clasifica como `PLANIFICACION`, y sus leads van a `fact_planificacion_programa.leads_fuente`, no a `fact_marketing`.
3. **El único escritor de leads sobre `fact_marketing` no dejó datos.** `seed_fact_marketing_leads` lee `Centralizado_Mensual` y exige `AÑO` y `MES`. En esa hoja `AÑO` está poblado solo en 2026 (83 filas con leads). Aun si se hubiera ejecutado, solo cargaría 2026. Como 2026 también está en 0, el seed no se ejecutó sobre esta DW, o se ejecutó antes de otro proceso. **No determinado**, porque no hay log de ejecución del seed.
4. `seed_fact_marketing` usa `ON CONFLICT DO UPDATE SET inscritos` y no toca `leads`, así que no puede poner los leads a cero.

Hallazgo adicional (hipótesis): `fact_marketing.inscritos` es aproximadamente el doble de las filas de TBL_INSCRITOS por año (2023: 7.102 = 2 × 3.551 exacto; 2024: 9.124 frente a 2 × 4.563 = 9.126; 2025: 9.472 frente a 2 × 4.737 = 9.474; 2026: 4.576 frente a 2 × 2.292 = 4.584). Una explicación posible es que el seed fije el conteo y el loader ADMISION sume 1 por fila sobre el mismo registro. **No verificado**: haría falta reproducir la carga en tmpfs. Sea cual sea la causa, `inscritos` de `fact_marketing` no es confiable como numerador de KPI-06.

## 4. Historial de la migración 014

- Archivo: `backend/scripts/migrations/014_conversion_captacion_comprobable.sql`. Historial (`git log --follow`): un solo commit, `ff0b1db` (2026-11-12, «fix(dataops): conciliar conteos y acreditar conversiones»). Aplicada en la DW el 2026-11-12 13:31 (`schema_migrations`).
- Agrega `leads_captacion` e `inscritos_captacion` (INTEGER, NULL) y reescribe `bi.vw_cmi_valores`. KPI-06 solo lee esas dos columnas. Su comentario dice: «No reconstruir captación a partir de inscripciones ni alterar contadores históricos.»
- La regla de carga está en `dw_loader.py` ~1893: solo se llena captación cuando el **mismo registro** trae `leads` e `inscritos` explícitos, con `0 ≤ inscritos ≤ leads` y `leads > 0`.
- La migración **no nombra ningún archivo**. La fuente esperada era un registro de marketing con ambas columnas. Ningún archivo del lote cae en esa ruta, así que la columna nunca se llenó. Por eso KPI-06 sale «sin dato» por diseño.

Dato útil: la regla de pareja de la migración 014 **sí** se cumple en el doc 1, porque `LEADS` e `N° INSCRITOS` están en la misma fila-programa-mes.

## 5. Opciones para KPI-06

Regla aplicada en todas las opciones: pareja de la misma fila, `leads > 0`, `0 ≤ inscritos ≤ leads` (la misma regla de la migración 014). Consulta: `scripts/auditoria_dw/adw_l6_0_kpi06.py` sobre `fact_planificacion_programa`.

| Gestión | Filas con leads | Pares válidos | Meses con datos | Leads (pares) | Inscritos (pares) | Reservas (pares) |
|---|---|---|---|---|---|---|
| 2023 | 0 | 0 | 0 | — | — | — |
| 2024 | 0 | 0 | 0 | — | — | — |
| 2025 | 128 | 125 | 6 (jul–dic) | 35.085 | 1.351 | 119 |
| 2026 | 174 | 149 | 6 (ene–jun) | 44.003 | 1.314 | 178 |
| 2026 sin junio | 146 | 144 | 5 (ene–may) | 43.313 | 1.297 | — |

**(a) Fuente existente: doc 1, `LEADS` e `N° INSCRITOS` en la misma fila (`fact_planificacion_programa`).**
- KPI-06 = inscritos / leads × 100.
- 2025 (jul–dic, parcial): 1.351 / 35.085 = **3,85 %**.
- 2026 (ene–jun, parcial): 1.314 / 44.003 = **2,99 %**. Sin junio: 1.297 / 43.313 = **2,99 %**. Junio tiene 28 filas con leads, pero solo 5 con inscritos, así que su captura está incompleta.
- 2023 y 2024: **no calculable**. No hay leads en ninguna fuente.
- Riesgo: la cifra cubre solo 6 meses por gestión. Tiene que mostrarse como «parcial (n meses)», no como cifra anual.

**(b) Redefinir con otra columna disponible: `RESERVAS`.**
- Lo único disponible es reservas / leads = 119 / 35.085 = **0,34 %** (2025) y 178 / 44.003 = **0,40 %** (2026).
- No sirve como etapa intermedia del embudo: inscritos / reservas = 1.351 / 119 = 11,35, es decir 1.135 %. Hay más inscritos que reservas, así que `RESERVAS` no es un paso previo a la inscripción. **No determinado** qué mide.
- En `fact_marketing.reservas`, la columna que usaría el CMI, el valor es 0 en todas las gestiones: **no calculable** desde esa tabla.

**(c) No medible.**
- Sin leads en 2023 ni 2024; sin datos para 2025 ene–jun ni jul–dic 2026 (vacíos).
- Definición de `LEADS` no documentada.
- `N° INSCRITOS` (doc 1) no concilia con TBL_INSCRITOS, y `fact_marketing.inscritos` parece duplicado (hipótesis, sección 3). Ningún inscrito del CMI es comparable con los leads del doc 1.

Recomendación (decide Lean, DA6): opción (a) con cobertura explícita. KPI-06 = «parcial» para 2025 y 2026, y «sin dato» para 2023 y 2024. Hay que leer `fact_planificacion_programa` en vez de `fact_marketing`, porque es la tabla que tiene la fuente con interesados. La opción (b) no es una alternativa válida. La opción (c) queda como respaldo si Lean no acepta cobertura parcial.

## Pendientes y límites

- No determinado: si el seed `seed_fact_marketing_leads` se ejecutó alguna vez sobre esta DW (no hay logs).
- No determinado: definición de `LEADS` y de `N° INSCRITOS` en el doc 1, y si IBP es real o proyectado.
- No verificado: la causa del doble conteo de `fact_marketing.inscritos` (requiere reproducir la carga en tmpfs).
- Sin PII: no se citan nombres, CI ni correos. Solo columnas y agregados.
