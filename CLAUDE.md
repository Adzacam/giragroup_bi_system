# GiraGroup BI — reglas comunes a todos los chats

Este repositorio es el sistema de la tesis. **El sistema respeta lo que el documento declara.** Las cifras nuevas entran al documento una sola vez, desde `docs/fuente_verdad_tesis.md` con la etiqueta CONGELADO.

## Roles (cada chat carga su skill al empezar)
| Chat | Skill | Modo |
|---|---|---|
| 1. Planificación | `/gira-planificar` | Solo lectura (modo plan) |
| 2. Desarrollo | `/gira-desarrollar` | Escritura local; solo ejecuta un `PLAN_<fase>.md` |
| 3. Documento ↔ sistema | claude.ai (Proyecto) | Solo con cifras congeladas |
| 4. Figuras y comandos | `/gira-figuras` | Solo salidas a partir de `docs/mediciones/` |

Traspasos: `docs/cierres/PLAN_<fase>.md`, `CIERRE_<fase>.md`, `FIGURAS_<fase>.md`.

## Invariantes (no se cambian sin decisión escrita de Lean)
- **Cascada:** CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO. BETO va al final, solo para residuales; nunca sobrescribe A/B ni crea perfiles.
- **Umbrales:** 0,92 personas · 90 % homónimos · 85 % CI variante y docentes · 80 % módulos · bandas 0,85 / 0,60.
- **Estados de identidad:** A (CI exacta), B (rescate difuso o TEMP), C (homonimia o docente provisional).
- **Catálogo:** solo entidades institucionales, sin docentes ni estudiantes.
- **BETO:** `dccuchile/bert-base-spanish-wwm-cased`, IOB2, 128 tokens (ventana deslizante permitida; no 512).
- **DW:** 50 tablas + 9 vistas `bi`; 9 hechos, 7 dimensiones, 1 puente; constelación; idempotencia por `carga_fila_origen`.
- **CMI:** 22 KPI en `bi.ref_kpi`; endpoint `/api/v1/cmi/scorecard`.
- **Pronóstico:** Holt-Winters amortiguado (m = 12, hold-out de 6 meses); OLS mensual N = 40; OLS anual solo descriptiva.
- **Requisitos:** 11 RF, 7 RNF, 12 HU, 6 sprints; RNF-03 < 15 min (aceptable < 20); RNF-04 F1 ≥ 0,85.
- **Infraestructura:** 9 servicios en docker-compose, sin licencias comerciales.
- **Datos:** el snapshot `snapshot_dw_20261110_1201` es de solo lectura; las mediciones van en la copia tmpfs; un único lote congelado para la medición final.

## Reglas de evidencia
1. Ningún chat inventa datos. Una cifra sin archivo en `docs/mediciones/` no existe.
2. No se toca el docx de la tesis desde este repositorio.
3. No se escriben credenciales en archivos versionados.
