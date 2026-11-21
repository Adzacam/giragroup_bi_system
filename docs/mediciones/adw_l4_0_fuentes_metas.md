# ADW L4-0 · Metas y ejecución en los archivos fuente (solo lectura)

Fecha: 2026-11-20. Tarea: L4-0 de `docs/cierres/PLAN_AUDITORIA_DW.md`.
Script: `scripts/auditoria_dw/adw_l4_0_fuentes_metas.py` (salida completa usada aquí: `C:\Users\DAZA\AppData\Local\Temp\claude\dab57b18347621f2\6e5d2bc7-5759-43f3-9912-fbc2964d8fcf\scratchpad\l40.txt`).
Consultas SQL (solo SELECT) sobre la copia tmpfs `adw_pg_tmpfs` / `giragroup_db`.
Nota: `PLAN_AUDITORIA_DW.md` ya marca DA4 como RESUELTA (KPI-02 excluye 2024 y 2023). Este informe documenta la base de esa decisión.

## 1. Archivo realmente cargado (doc 38 y 39)

Consulta: `SELECT id_documento, nombre_archivo, hash_sha256 FROM dim_origen_documental WHERE id_documento IN (38,39);` (la clave es `id_documento`, no `id`).

| Doc | Archivo | sha256 en DW |
|---|---|---|
| 38 | EJECUTADO VS META.xlsx (tipo RENTABILIDAD) | `daee07f1…2852682` |
| 39 | BD Egresos.xlsx (tipo EGRESOS) | `4b4afbdd…6c30c5d` |

| Ruta (sha256 abreviado, bytes) | Coincide con doc |
|---|---|
| `uploads/data/EJECUTADO VS META.xlsx` (daee07f1, 30.879) | **38 (sí)** |
| `uploads/data/BD Egresos.xlsx` (4b4afbdd, 174.709) | **39 (sí)** |
| `output/backups/f0_lote/originales/*` y `output/backups/f0_lote/generador/uploads/data/*` | 38 y 39 (sí, mismos hashes) |
| `backend/docs/evidencias/ciclo_mensual_slices/EJECUTADO VS META.xlsx` (a384af08, 8.932) | no |
| `backend/docs/evidencias/ciclo_mensual_slices/BD Egresos.xlsx` (c5c1e2cd, 37.864) | no |
| `output/backups/f0_lote/slices/*` y `corridas/.../landing/1/*` (1e45cb17 / 8a5c1507) | no |
| `output/lote1387_archivos/EJECUTADO_VS_META_lote1387_24_filas.xlsx` (40336c60) | no |

Conclusión: el archivo cargado es `uploads/data/` (idéntico a `originales/`). Los de `ciclo_mensual_slices/` y `slices/` no son el cargado. Comparados por valor, sus hojas `EJECUTADO`/`GESTIONES` (EVM) y `Gestiones`/`acumulados` (Egresos) coinciden con el original con diferencia ≤ 0,01 Bs; el hash cambia por reescritura. En `ciclo_mensual_slices/BD Egresos.xlsx` la hoja `egresos` tiene 301 filas no vacías frente a 1.374 del original, por lo que es un recorte. El archivo `lote1387` no se comparó por valor.

## 2. Hojas, cabeceras y metas

**EJECUTADO VS META.xlsx** (hojas: `EJECUTADO`, `GESTIONES`; 16 y 12 fórmulas)

| Hoja | Filas con datos | Cabecera relevante |
|---|---|---|
| EJECUTADO | filas 2–25 (categoria PROGRAMAS filas 2–13; TECHOS/CERRADOS filas 14–25) | `EJECUTADO 2023` (D), `META POR CATEGORIA 2024` (E), `EJECUTADO 2024` (F), `EJECUTADO 2025` (G), `META POR CATEGORIA 2025` (H), `EJECUTADO 2026` (I), `META POR CATEGORIA 2026` (J), `EJEC. 2025` (K = G+G fila+12), `META 2025` (L), `META 2026` (Q), `META 2025 2DO SEMESTRE` (S) |
| GESTIONES | filas 2–13 | `EJECUTADO 2023/2024/2025`, `META 2025` (texto «Bs1.198.653», con punto de miles) |

**BD Egresos.xlsx** (hojas: `egresos`, `Gestiones`, `acumulados`; 8.237 fórmulas en `egresos`)

| Hoja | Contenido | Metas |
|---|---|---|
| egresos | 1.374 filas por programa (POS): egreso, ingreso, rentabilidad | No hay columna de meta |
| Gestiones | filas por «POR PROGRAMAS» y «POR TECHOS/CERRADOS» × 12 meses | `META 2025` (G) únicamente |
| acumulados | 12 meses | `META 2025` (F) únicamente |

**Respuestas**
- **¿2024 trae metas mensuales?** No. Solo hay **una cifra anual**: `EJECUTADO VS META.xlsx`, hoja `EJECUTADO`, celda **E25** (fila TECHOS/CERRADOS, DICIEMBRE, columna `META POR CATEGORIA 2024`) = **10.719.694,00**. Las demás celdas de la columna E están vacías (E2–E24 y todas las de PROGRAMAS). No hay meta 2024 en `BD Egresos.xlsx`.
- **¿Hay metas 2023?** No. No existe ninguna columna `META` de 2023 en ningún archivo; solo `EJECUTADO 2023`.
- **Cifra anual 2024 vs ejecución:** la ejecución 2024 (PROG+TECH) suma 10.961.730,41 Bs. Frente a 10.719.694 da 102,26 %. Esto sugiere que la cifra anual es total de empresa, no solo TECHOS, pero **no se puede confirmar desde el archivo** (no determinado).
- **2026, ejecución:** enero–mayo (`EJECUTADO 2026`, col I). Mayo es parcial: PROGRAMAS 252.233,32 y TECHOS vacío. Junio–diciembre vacíos.
- **2026, meta:** enero–diciembre en `META POR CATEGORIA 2026` (col J) para PROGRAMAS; TECHOS tiene enero–noviembre, diciembre vacío. Total mensual meta (DW) de diciembre = 1.165.112,00.
- **Otras columnas de meta no usadas por la DW:**
  - `META 2025 2DO SEMESTRE` (S8:S13): 1.129.560,17 por mes para PROGRAMAS julio–diciembre (total U15 = 6.777.361; U14 = SUM S8:S13). Suma de meta PROG julio–diciembre según DW = 5.911.519,96. Diferencia 865.841,04 Bs. No determinado cuál aplica.
  - `META 2026` (Q): 1.627.619,50 constante en todas las filas de PROGRAMAS. La DW usa `META POR CATEGORIA 2026` (J).

## 3. Conflictos CONFLICTO_FUENTES (10, MEDIA, PENDIENTE)

Consulta: `SELECT ... FROM log_inconsistencias WHERE tipo_regla='CONFLICTO_FUENTES';`. El registro está ligado a `id_documento = 39` (BD Egresos). `fila_origen` y `regla_origen` están vacíos. `stg_entidad_no_resuelta` no contiene estos conflictos (son registros de estudiantes con motivo CI_DUDOSA), así que no se usó.

| id | Campo | Mes 2025 | DW conserva (EVM) | Egresos trae | Diferencia |
|---|---|---|---|---|---|
| 2662 | PROGRAMAS, monto_ejecutado | Mar | 997.224,70 | 660.209,00 | 337.015,70 |
| 2663 | PROGRAMAS, monto_meta | Abr | 1.008.766,54 | 1.108.766,54 | 100.000,00 |
| 2664 | PROGRAMAS, monto_meta | May | 1.007.494,54 | 1.107.494,54 | 100.000,00 |
| 2665 | PROGRAMAS, monto_meta | Jun | 1.001.583,82 | 1.101.583,82 | 100.000,00 |
| 2666 | PROGRAMAS, monto_meta | Jul | 1.068.196,00 | 1.168.196,00 | 100.000,00 |
| 2667 | PROGRAMAS, monto_meta | Ago | 1.115.596,83 | 1.215.596,83 | 100.000,00 |
| 2668 | PROGRAMAS, monto_meta | Sep | 1.061.647,20 | 1.161.647,20 | 100.000,00 |
| 2669 | PROGRAMAS, monto_meta | Oct | 1.061.647,20 | 1.161.647,20 | 100.000,00 |
| 2670 | PROGRAMAS, monto_meta | Dic | 608.960,50 | 648.684,50 | 39.724,00 |
| 2671 | TECHOS/CERRADOS, monto_ejecutado | Mar | 34.778,94 | 4.153,94 | 30.625,00 |

**Patrón**
- Los 10 están en 2025. Hay 8 de metas (7 meses con +100.000 exacto y diciembre con +39.724) y 2 de ejecución de marzo.
- Las metas de noviembre y las de enero–marzo no difieren (por encima de 1 Bs).
- **Lo que dicen los archivos (no hay un archivo correcto demostrable):**
  - Metas: el detalle `EJECUTADO` de EVM (que usa la DW) difiere de **ambos resúmenes** (`GESTIONES` de EVM y `acumulados` de Egresos), que coinciden entre sí en las 12 metas 2025. Dos fuentes contra una, pero el detalle es el que tiene las celdas por categoría. **No determinado.**
  - Ejecución marzo 2025: detalle EVM total 1.032.003,64; detalle Egresos total 664.362,94; ambos resúmenes dicen 711.450,00. Ninguno de los detalles coincide con su propio resumen. **No determinado.**
- Las metas del detalle EVM coinciden con la DW en las 48 filas (ver §4). La DW conserva el valor de EVM por regla de precedencia.

## 4. Cruce con la DW (`docs/mediciones/adw_l0_rentabilidad.csv`)

Resultado: **48 de 48 meses** coinciden en ejecutado y en meta con la suma PROGRAMAS + TECHOS/CERRADOS del detalle `EJECUTADO` de EVM (diferencia < 1 Bs).

Qué hoja alimenta cada categoría:

| Categoría DW | Hoja / columna EVM (detalle) | Hoja Egresos |
|---|---|---|
| PROGRAMAS (web financiera) | EJECUTADO, filas PROGRAMAS; meta 2024 vacía | Gestiones, «POR PROGRAMAS» |
| TECHOS_CERRADOS (suma en CMI) | EJECUTADO, filas TECHOS/CERRADOS; **meta 2024 en E25** | Gestiones, «POR TECHOS/CERRADOS» |
| Total (csv) | Suma de ambas | Suma de ambas |

Diferencias explicadas:
- Ejecución dic-2024: web (solo PROGRAMAS) = 631.036,18; DW (PROG+TECH) = 670.367,88. La diferencia 39.331,70 es exactamente TECHOS dic-2024.
- Meta 2024: la cifra anual de 10.719.694 está solo en TECHOS/CERRADOS. Si la web usara solo PROGRAMAS, no tendría meta 2024.
- Meta 2025 en el csv (= detalle EVM): distinta de los resúmenes en abr–oct y dic (ver §3).
- Gestión 2026 en csv: sin ejecución de junio en adelante; dic-2026 solo PROGRAMAS.

## 5. KPI-02 de 2024 con las tres opciones

Base: KPI-02 = ejecución del último mes cerrado / meta del mismo mes. En la DW es dic-2024. Ejecución dic-2024 (PROG+TECH) = **670.367,88 Bs**.

| Opción | Meta usada | KPI-02 2024 | Observación |
|---|---|---|---|
| A. Cargar meta mensual real | No existe en los archivos | **no determinado** | Haría falta una fuente nueva |
| B. Excluir 2024 (sin dato) | — | **sin dato** | Coincide con la decisión ya registrada en el plan |
| C. Prorratear (suposición: partes iguales) | 10.719.694 / 12 = 893.307,83 | 670.367,88 / 893.307,83 = **75,04 %** | Suposición; no es dato de la fuente |

Referencia: la DW actual (meta anual completa en dic) da 670.367,88 / 10.719.694 = **6,25 %**.

## 6. Cifras clave

1. Meta 2024: una sola cifra anual, 10.719.694 Bs, en `EJECUTADO VS META.xlsx` hoja `EJECUTADO` celda E25. No hay meta mensual 2024 ni meta 2023.
2. Conflictos: 10, de los cuales 8 son de meta (7 meses con +100.000 Bs, dic +39.724 Bs) y 2 de ejecución de marzo 2025. Ninguno se puede resolver con los archivos.
3. KPI-02 2024: 6,25 % (actual, meta anual en dic), 75,04 % si se prorratea (suposición), sin dato si se excluye 2024.

## 7. Lo que queda para Lean

- La meta mensual real 2024 no existe en la fuente; la opción A no es viable sin un archivo nuevo.
- Decidir la fuente de meta 2025 entre el detalle EVM y los resúmenes (abr–oct, dic) y si la meta 2do semestre (S8:S13) aplica.
- Confirmar si 10.719.694 es total de empresa (sugerido por el 102 % anual) o solo TECHOS.
