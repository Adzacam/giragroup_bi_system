# Reporte Final de Cierre — Sprint 2 (v2 Monolítico)

Este reporte consolida el resultado de la reconstrucción de Sprint 2 sobre los 10 archivos reales del corpus.
Este número representa el **nuevo punto de partida para Sprint 3 (BETO NER)**.

## 1. Resumen Ejecutivo

- **Archivos procesados:** 10
- **Hojas leídas:** 29 (0 vacías justificadas)
- **Bloques tabulares detectados:** 31 (31 válidos, 0 ruido/baja confianza)
- **Documentos de texto plano generados:** 31
- **Invariante de conservación:** ✅ CUMPLIDO (100% registros justificados)

## 2. Invariante de Conservación de Filas

$$\text{Total Filas Raw} = \text{Filas en Bloques} + \text{Filas Vacías (Gaps)}$$
$$1,793 = 1,785 + 8$$

## 3. Desglose de Documentos por Categoría

| Categoría | Bloques / Documentos | % del Total | Descripción / Destino en Sprint 3 |
|:---|:---:|:---:|:---|
| `academico` | 16 | 51.6% | Notas, actas, evaluaciones docentes, módulos |
| `financiero` | 14 | 45.2% | Cobranzas, egresos, techos presupuestarios |
| `comercial` | 1 | 3.2% | Inscritos, metas, prospectos |

## 4. Auditoría por Archivo (Corpus Real)

| Archivo | Hojas | Bloques | Filas Raw | Filas Bloques | Vacías (Gaps) | Invariante |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `Base_Academica_ARCA_TEST.xlsx` | 4 | 4 | 199 | 199 | 0 | ✅ OK |
| `BBDD_Evaluacion_Docente_GiraGroup_TEST.xlsx` | 2 | 2 | 232 | 232 | 0 | ✅ OK |
| `BD_Cobranzas_giraGroup.xlsx` | 4 | 6 | 315 | 307 | 8 | ✅ OK |
| `BD_Egresos_TEST.xlsx` | 3 | 3 | 115 | 115 | 0 | ✅ OK |
| `BD_Techos_TEST.xlsx` | 1 | 1 | 51 | 51 | 0 | ✅ OK |
| `EJECUTADO_VS_META_TEST.xlsx` | 2 | 2 | 98 | 98 | 0 | ✅ OK |
| `Evaluacion_Docente_GiraGroup_TEST.xlsx` | 2 | 2 | 212 | 212 | 0 | ✅ OK |
| `Experiencia_Docente_TEST.xlsx` | 2 | 2 | 172 | 172 | 0 | ✅ OK |
| `Planificacion_Ejecucion_TEST.xlsx` | 8 | 8 | 248 | 248 | 0 | ✅ OK |
| `TBL_INSCRITOS_TEST.xlsx` | 1 | 1 | 151 | 151 | 0 | ✅ OK |

## 5. Salidas Persistidas para Sprint 3

- **JSON Lines:** `output/sprint2_documentos.jsonl` (73 bloques con texto plano serializado y metadatos).
- **CSV Resumen:** `output/sprint2_documentos.csv`.
- **Trazabilidad:** Cada bloque conserva `{archivo, hoja, bloque_id, categoria, texto_plano, metadata}`.