# Matriz Motivo × Categoría → Campos del Formulario de Revisión (W-1)

| Categoría | Motivo | Casos en `f3w_completo` | Qué lo provoca | Campos obligatorios del formulario |
|---|---|---:|---|---|
| `academico` | `CI_NOMBRE_DISCORDANTE` | 738 | La CI coincide con una persona del catálogo pero el nombre difiere (< umbral). | `nombre_completo`, `ci_opcional`, `confirmar_identidad`, `justificacion` (sin nota/mes/gestión si ya existen) |
| `academico` | `BAJA_CONFIANZA_IA` | 323 | Índice probabilístico BETO en `[0,60; 0,85)`. | `nombre_completo`, `modulo_resuelto`, `nota_final`, `mes`, `gestion`, `justificacion` |
| `academico` | `HOMONIMIA` | 34 | Dos personas con nombre similar (>90 %) sin CI discriminante. | `nombre_completo`, `ci_opcional`, `programa`, `justificacion` |
| `academico` | `CI_DUDOSA` | 2 | CI con `?`, longitud < 5 o formato inválido. | `ci_corregido`, `nombre_completo`, `justificacion` |
| `evaluacion_docente` | `BAJA_CONFIANZA_IA` | 250 | Índice probabilístico BETO en `[0,60; 0,85)` en respuestas Likert. | `programa`, `numero_modulo`, `docente_resuelto`, `escala_respuesta`, `justificacion` (**sin** nota/100) |
| `evaluacion_docente` | `HOMONIMIA` | 19 | Nombre de encuestado/docente ambiguo sin CI. | `nombre_completo`, `ci_opcional`, `programa`, `numero_modulo`, `justificacion` (**sin** nota/100) |
| `admision` | `POS_NO_EN_DIM_MODULO` | 5 | Código `POS` no encontrado en `dim_modulo`. | `codigo_pos`, `programa_resuelto`, `modulo_resuelto`, `justificacion` |
| `admision` | `CI_DUDOSA` | 5 | CI con `?` o formato inválido en `TBL_INSCRITOS`. | `ci_corregido`, `nombre_completo`, `justificacion` |
| `admision` | `FECHA_INSCRIPCION_INVALIDA` | 1 | Fecha nula o fuera de rango en admisión. | `fecha_inscripcion`, `justificacion` |
| `financiero` | `CI_DUDOSA` | 2 | CI con `?` o formato inválido en `BD Cobranzas`. | `ci_corregido`, `nombre_completo`, `monto_deuda`, `cuotas_impagas`, `justificacion` |
| `rentabilidad` | `CI_NOMBRE_DISCORDANTE` | 2 | Discordancia de nombre/CI en `BD Egresos`. | `nombre_completo`, `ci_opcional`, `categoria_financiera`, `justificacion` |
| `rentabilidad` | `HOMONIMIA` | 1 | Homonimia en registro de `BD Egresos`. | `nombre_completo`, `ci_opcional`, `justificacion` |
| `marketing` | `*` (techo/convenio) | 0 abiertos | Convenio/institución o monto por validar (`fact_techo_convenio`). | `institucion`, `clave_convenio`, `monto_convenio`, `justificacion` |

## Verificación D-W7
- **Archivo y líneas:** `pipeline/semantic/formatter.py:238-252`
- **Veredicto:** `defecto` (D-W7). Las columnas Likert 1–10 clasificadas como `NOTA` se multiplicaban por `10.0` (l.242), y las preguntas que contienen `"docente"` entraban a `RESPUESTAS` / contexto cercano.
