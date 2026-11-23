# TRASPASO al chat 1 — RNF-03 tras F5C/F5V (2026-11-19)

Rama / commits: `beto-integracion` `84cd352`, `804970e`, `38e317f` (cierres: `CIERRE_F5C.md`, `CIERRE_F5V.md`).

## Qué decidir
La nueva medición B-7 (n = 3, KLM con W = 2,5 s, 474,0 s) incumple RNF-03 (< 15 min, aceptable < 20):

| Condición | Tiempo | Estado |
|---|---|---|
| Caché llena + KLM | 1.231,46 s (20,52 min) | supera 20 min |
| Caché vacía + KLM | 1.904,98 s (31,75 min) | supera 20 min |

Fuente: `docs/mediciones/f5c_b7_corridas.json`, `f5c_klm.json`. El cierre F5C lo declara como incumplimiento; no se cambió umbral ni método.

## Contexto
- F5C cambió el mapeo por encabezado y el cálculo de confianza por origen; el índice se recalculó (DECISIÓN 1 de Lean). Informe A/B en `f5c_indice_ab.json`; lote 1.387: 97,76 % directo, 31 HITL.
- Hay que determinar cuánto del aumento viene de F5C (más casos de revisión → más KLM) y cuánto del método de medición.
- Las cifras anteriores congeladas (SFV) fueron reemplazadas por las de `f5c_*`; `verificar_sfv.py` da 0/0/0.

## Pedir al chat 1
1. Plan para decidir: declarar el incumplimiento en el documento, o una fase de optimización (con nueva medición), o revisar el método de B-7.
2. Anexo de cambios F5C para el chat 3 (cifras `f5c_*`).
3. Decisión escrita de Lean si se toca el umbral o el criterio de RNF-03 (invariante).

## Sin commitear (previos a F5C/F5V)
`backend/routers/powerbi.py`, `.claude/*`, gráficos `docs/evidencias/graficos_v2/*`. Un test de `test_powerbi_retencion` falla por el cambio en `powerbi.py`.
