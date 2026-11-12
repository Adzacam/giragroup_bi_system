"""Agrega las corridas de medir_flujo_repetido.py: media y desviación estándar (muestral, n-1) por etapa, recursos y
estimación de la parte humana con el modelo KLM (Card, Moran y Newell, 1980) sobre los grupos y casos reales de la bandeja.

Uso: python scripts/agregar_flujo_repetido.py <carpeta_con_flujo_corrida_i.json> <salida.json>
"""
import json
import statistics as st
import sys
from pathlib import Path

# Parámetros KLM explícitos (segundos). Valores clásicos de Card, Moran y Newell; W es la espera real de la pantalla del paso ④.
K, P, H, M, B = 0.28, 1.10, 0.40, 1.35, 0.10
CLIC = 2 * B           # pulsar y soltar
W_DESHACER = 10.0      # la pantalla espera 10 s antes de enviar la acción (se puede deshacer)
TECLAS_FECHA = 6       # "3" + tab + "2026"
TECLAS_ESTADO = 12     # nombre canónico de estado (estimación)
M_POR_GRUPO = 2        # leer título/cantidad + decidir
M_POR_CASO = 2         # leer el caso + decidir (aprobar tal cual)
PAGINA = 5             # grupos por página; cambiar de página = P + clic


def klm(eventos, con_espera):
    w = W_DESHACER if con_espera else 0.0
    t_total, desglose = 0.0, {"bloque": 0.0, "corregir_fecha": 0.0, "mapear_estado": 0.0, "manual": 0.0, "paginacion": 0.0}
    paginas = (len(eventos) + PAGINA - 1) // PAGINA
    desglose["paginacion"] = max(0, paginas - 1) * (P + CLIC)
    for e in eventos:
        a = e["accion"]
        if a == "MANUAL":  # por caso: leer + decidir + puntero + clic en Aprobar (+ espera)
            d = e["casos"] * (M_POR_CASO * M + P + CLIC + w)
            desglose["manual"] += d
        elif a == "APROBAR":
            d = M_POR_GRUPO * M + P + CLIC + w
            desglose["bloque"] += d
        elif a == "CORREGIR_FECHA":  # abrir diálogo, escribir mes/gestión, confirmar
            d = M_POR_GRUPO * M + P + CLIC + M + H + TECLAS_FECHA * K + P + CLIC + w
            desglose["corregir_fecha"] += d
        else:  # MAPEAR_ESTADO
            d = M_POR_GRUPO * M + P + CLIC + M + H + TECLAS_ESTADO * K + P + CLIC + w
            desglose["mapear_estado"] += d
        t_total += d
    t_total += desglose["paginacion"]
    return round(t_total, 1), {k: round(v, 1) for k, v in desglose.items()}


def ms(v):
    return {"media": round(st.mean(v), 2), "de": round(st.stdev(v), 2) if len(v) > 1 else 0.0, "min": round(min(v), 2), "max": round(max(v), 2)}


def main(carpeta, salida, revision_json=None):
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(carpeta).glob("flujo_corrida_*.json"))]
    corr = json.loads((Path(carpeta) / "corridas.json").read_text(encoding="utf-8"))
    etapas = {k: ms([r["etapas_s"][k] for r in runs]) for k in
              ("carga_s", "lectura_beto_s", "lineas_por_s_beto", "consolidacion_s", "revision_maquina_s")}
    maquina = [r["total"]["tiempo_maquina_s"] for r in runs]
    ref = json.loads(Path(revision_json).read_text(encoding="utf-8")) if revision_json else runs[0]
    eventos = ref.get("revision_eventos") or ref["eventos"]
    firmas = [[(e["accion"], e["casos"]) for e in eventos]]
    dw_igual = all(r["dw_despues"] == runs[0]["dw_despues"] for r in runs)
    rev_maq = (ref.get("resumen") or ref["revision"])["tiempo_maquina_real_aprobaciones_s"]
    k_con, d_con = klm(eventos, True)
    k_sin, d_sin = klm(eventos, False)
    m_media = st.mean(maquina) + rev_maq
    rev0 = ref.get("resumen") or ref["revision"]
    out = {"n_corridas": len(runs), "etapas_s": etapas, "tiempo_maquina_s": ms(maquina),
           "registros_leidos_beto": [r["etapas_s"]["lineas_leidas_beto"] for r in runs],
           "bandeja": {"casos": rev0["casos"], "grupos": rev0["grupos"], "grupos_en_bloque": rev0["grupos_aprobables_en_bloque"],
                       "grupos_manuales": rev0["grupos_manuales"], "casos_manuales": sum(e["casos"] for e in eventos if e["accion"] == "MANUAL"),
                       "casos_rechazados_por_regla": rev0["casos_rechazados_por_regla"], "origen": revision_json or "corrida 1", "dw_identico_en_las_3_corridas": dw_igual, "revision_maquina_s": rev_maq},
           "klm": {"parametros_s": {"K": K, "P": P, "H": H, "M": M, "B": B, "clic": CLIC, "W_deshacer": W_DESHACER, "teclas_fecha": TECLAS_FECHA,
                                    "teclas_estado": TECLAS_ESTADO, "M_por_grupo": M_POR_GRUPO, "M_por_caso": M_POR_CASO, "grupos_por_pagina": PAGINA},
                   "con_espera_10s_s": k_con, "sin_espera_s": k_sin, "desglose_con_espera_s": d_con, "desglose_sin_espera_s": d_sin},
           "total_estimado_min": {"con_espera": round((m_media + k_con) / 60, 1), "sin_espera": round((m_media + k_sin) / 60, 1),
                                  "maquina_media_min": round(m_media / 60, 1)},
           "recursos_por_corrida": [c["recursos"] for c in corr],
           "dw_despues_corrida_1": runs[0]["dw_despues"]}
    Path(salida).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
