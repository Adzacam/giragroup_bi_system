# Umbrales reales de RapidFuzz (leídos del código vigente)

## Resolución de personas (`pipeline/normalization/person_resolver.py`)
Cascada para estudiantes y docentes, sin catálogo de docentes:

1. **CI exacta** (≥ 5 caracteres alfanuméricos tras normalizar): fuente `CI_EXACTA`, score 1,0. No usa RapidFuzz.
2. **Sin CI: RapidFuzz con bloqueo escalonado** `MODULO → PROGRAMA → DIMENSION`. El mismo umbral (`UMBRAL_PERSONA = 0,92`) rige en los tres niveles; lo que cambia es el conjunto de personas contra el que se compara:
   - **Módulo**: personas de la dimensión cuyos módulos coinciden (uno contiene al otro) con los módulos del registro. Solo si el registro trae módulo.
   - **Programa**: personas cuyos programas coinciden con los del registro. Solo si el registro trae programa.
   - **Dimensión completa**: todo `dim_estudiante` / `dim_docente`.
   Un nivel resuelve si tiene exactamente un candidato o uno con score estrictamente mayor. Con 0 candidatos pasa al nivel siguiente. Con ≥ 2 empatados en (score, token_sort) y ids distintos, devuelve `empate` y va a HITL. Si ningún nivel tiene candidatos, `sin_candidatos` (miembro nuevo B si hay ≥ 2 tokens y parece nombre; si no, HITL).
3. **Score** = `max(token_sort_ratio, token_set_ratio) / 100`, sobre el nombre sin títulos (Lic., Ing., Dr., MSc…), sin acentos y en minúsculas.
4. **Regla de apellido y tokens** (se aplica antes del score): con tokens de 3+ letras sin conectores (de, del, la, los, y, san), el candidato necesita **≥ 2 tokens en común** con la persona de la dimensión, y su **último token (apellido) o su primer token** debe estar entre los tokens de la persona **sin contar el primero** (los apellidos). Un nombre de un solo token no se resuelve.

## Otros umbrales de RapidFuzz en la carga (`backend/services/dw_loader.py`)
| Uso | Medida | Umbral |
|---|---|---|
| Variante de nombre con la misma CI (`CI_NOMBRE_VARIANTE`) | `token_set_ratio` tras quitar títulos, con ≥ 1 token de 3+ letras en común | ≥ 85 |
| Candidatos de estudiante sin CI (homonimia, `_candidatos_estudiante_fuzzy`) | `token_sort_ratio` | ≥ 90 |
| Docente sin CI en la carga (`resolver_o_crear_docente`) | `token_sort_ratio` (mejor candidato) | ≥ 85 |
| Módulo por nombre (`resolver_o_crear_modulo`) | `token_sort_ratio` (mejor candidato) | ≥ 80 |

Nota: la evaluación del lote 1.387 usa la resolución de `person_resolver` (0,92). La carga al DW usa además los umbrales de la tabla.
