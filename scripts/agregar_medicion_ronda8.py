"""Ronda 8, tarea 4: media y DE (muestral, n-1) de las 3 corridas finales del ciclo (total, por etapa, por archivo), casos y grupos HITL por corrida
y tiempo_klm.json (detalle por grupo: n_casos y acción, para el cálculo KLM). Lee docs/evidencias/ciclo_r8_<n>.json y revision_r8_<n>.json."""
import json
import statistics as st
from pathlib import Path

E = Path(__file__).resolve().parent.parent / "docs" / "evidencias"
N = (1, 2, 3)
ciclos = [json.loads((E / f"ciclo_r8_{n}.json").read_text(encoding="utf-8")) for n in N]
revs = [json.loads((E / f"revision_r8_{n}.json").read_text(encoding="utf-8")) for n in N]


def ms(xs):
    return {"media": round(st.mean(xs), 2), "de": round(st.stdev(xs), 2), "corridas": [round(x, 2) for x in xs]}


etapas = {k: ms([c["suma_etapas_s"][k] for c in ciclos]) for k in ciclos[0]["suma_etapas_s"]}
archivos = {}
for a in ciclos[0]["archivos"]:
    nombre = a["archivo"]
    filas = [next(x for x in c["archivos"] if x["archivo"] == nombre) for c in ciclos]
    archivos[nombre] = {"filas_total": a["filas_total"], "segundos": ms([f["segundos"] for f in filas]),
                        "etapas_ms": {k: ms([f["tiempos_etapa_ms"].get(k, 0) for f in filas]) for k in a["tiempos_etapa_ms"]},
                        "hechos_cargados_dw": [f["hechos_cargados_dw"] for f in filas]}
resumen = {"corridas": len(N), "tiempo_total_s": ms([c["tiempo_total_s"] for c in ciclos]), "por_etapa_s": etapas, "por_archivo": archivos,
           "hitl_por_corrida": [{"corrida": n, "casos": r["resumen"]["casos"], "grupos": r["resumen"]["grupos"],
                                 "grupos_aprobables_en_bloque": r["resumen"]["grupos_aprobables_en_bloque"], "grupos_manuales": r["resumen"]["grupos_manuales"],
                                 "tiempo_maquina_aprobaciones_s": r["resumen"]["tiempo_maquina_real_aprobaciones_s"],
                                 "tiempo_humano_simulado_s": r["resumen"]["tiempo_humano_simulado_s"]} for n, r in zip(N, revs)]}
(E / "ciclo_r8_resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
# detalle por grupo (corrida 1; las otras dos tienen los mismos grupos si el ciclo es determinista, se verifica abajo)
claves = [sorted((e["clave"], e["casos"], e["accion"]) for e in r["eventos"]) for r in revs]
klm = {"nota": "tiempos humanos NO medidos: el KLM los calcula con n_casos y accion; casos y grupos salen de la ejecucion real",
       "corridas_con_mismos_grupos": claves[0] == claves[1] == claves[2],
       "casos": revs[0]["resumen"]["casos"], "grupos": revs[0]["resumen"]["grupos"],
       "grupos_detalle": [{"orden": i + 1, "clave": e["clave"], "n_casos": e["casos"], "accion": e["accion"], "resueltos": e.get("resueltos"),
                           "segundos_maquina_real": e["segundos_maquina_real"]} for i, e in enumerate(revs[0]["eventos"])]}
(E / "tiempo_klm.json").write_text(json.dumps(klm, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in resumen.items() if k != "por_archivo"}, ensure_ascii=False, indent=1))
print("mismos grupos en las 3 corridas:", klm["corridas_con_mismos_grupos"])
