# Reporte Final de Cierre — Sprint 2 (v2 Monolítico)

Este reporte consolida el resultado de la reconstrucción de Sprint 2 sobre los 10 archivos reales del corpus.
Este número representa el **nuevo punto de partida para Sprint 3 (BETO NER)**.

## 1. Resumen Ejecutivo

- **Archivos procesados:** 10
- **Hojas leídas:** 62 (2 vacías justificadas)
- **Bloques tabulares detectados:** 73 (68 válidos, 5 ruido/baja confianza)
- **Documentos de texto plano generados:** 73
- **Invariante de conservación:** ✅ CUMPLIDO (100% registros justificados)

## 2. Invariante de Conservación de Filas

$$\text{Total Filas Raw} = \text{Filas en Bloques} + \text{Filas Vacías (Gaps)}$$
$$93,006 = 92,921 + 85$$

## 3. Desglose de Documentos por Categoría

| Categoría | Bloques / Documentos | % del Total | Descripción / Destino en Sprint 3 |
|:---|:---:|:---:|:---|
| `academico` | 55 | 75.3% | Notas, actas, evaluaciones docentes, módulos |
| `financiero` | 12 | 16.4% | Cobranzas, egresos, techos presupuestarios |
| `ruido` | 5 | 6.8% | Bloques < 2 filas (etiquetados de baja confianza) |
| `comercial` | 1 | 1.4% | Inscritos, metas, prospectos |

## 4. Auditoría por Archivo (Corpus Real)

| Archivo | Hojas | Bloques | Filas Raw | Filas Bloques | Vacías (Gaps) | Invariante |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `[BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx` | 3 | 3 | 19,127 | 19,126 | 1 | ✅ OK |
| `Base centralizada Académica ARCA (1).xlsx` | 7 | 5 | 11,459 | 11,459 | 0 | ✅ OK |
| `BD Cobranzas.xlsx` | 5 | 7 | 16,048 | 16,041 | 7 | ✅ OK |
| `BD Egresos.xlsx` | 3 | 3 | 1,412 | 1,412 | 0 | ✅ OK |
| `BD Techos.xlsx` | 1 | 1 | 208 | 208 | 0 | ✅ OK |
| `EJECUTADO VS META.xlsx` | 2 | 2 | 38 | 38 | 0 | ✅ OK |
| `Evaluación Docente y Unifranz.xlsx` | 3 | 3 | 4,892 | 4,892 | 0 | ✅ OK |
| `Experiencia Docente 2.0.xlsx` | 4 | 4 | 17,699 | 17,699 | 0 | ✅ OK |
| `PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx` | 32 | 43 | 6,925 | 6,848 | 77 | ✅ OK |
| `TBL_INSCRITOS.xlsx` | 2 | 2 | 15,198 | 15,198 | 0 | ✅ OK |

## 5. Salidas Persistidas para Sprint 3

- **JSON Lines:** `output/sprint2_documentos.jsonl` (73 bloques con texto plano serializado y metadatos).
- **CSV Resumen:** `output/sprint2_documentos.csv`.
- **Trazabilidad:** Cada bloque conserva `{archivo, hoja, bloque_id, categoria, texto_plano, metadata}`.