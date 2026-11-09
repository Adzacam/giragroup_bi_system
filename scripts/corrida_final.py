"""Corrida final reproducible (lote 1.387, semilla 42): ejecuta lote + cifra BETO y arma una tabla única.
Uso: DATABASE_URL=... python scripts/corrida_final.py <n>   -> docs/evidencias/corrida_final_<n>.json"""
import json, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
E = R / "docs" / "evidencias"
n = sys.argv[1]
for s in ("reejecutar_lote_1387_uploads_data.py", "beto_cifra_unica.py"):
    subprocess.run([sys.executable, "-W", "ignore", str(R / "scripts" / s)], check=True, cwd=R, capture_output=True)
l = json.loads((E / "lote_1387_uploads_data_arquitectura_b.json").read_text(encoding="utf-8"))
b = json.loads((E / "beto_cifra_unica.json").read_text(encoding="utf-8"))
m = json.loads((E / "muestra_50_entidades_beto_semilla42.json").read_text(encoding="utf-8"))
out = {
    "extraccion_A_vs_B": {k: b[k] for k in ("total", "directo_A", "pct_directo_A", "directo_B", "pct_directo_B", "diferencia_B_menos_A")},
    "carga_final": l["distribucion_bandas_con_regla_personas"],
    "personas": l["personas"], "personas_por_fk_estado": l["personas_por_fk_estado"],
    "hitl_personas_por_motivo": l["personas_hitl_desglose_bloqueo_escalonado_umbral_092"],
    "descartadas_PER_SIN_FORMA_NOMBRE": l["descartadas_PER_SIN_FORMA_NOMBRE"], "log_inconsistencias_registradas": l["log_inconsistencias_PER_SIN_FORMA_NOMBRE_registradas"],
    "registros_directo_movidos_a_hitl_por_persona_sin_resolver": l["registros_directo_movidos_a_hitl_por_persona_sin_resolver"],
    "correos_filtrados": l["correos_filtrados_como_no_nombre"], "texto_libre": l.get("texto_libre"),
    "KPI_10a_todas": l["kpis"]["KPI_10a_media_todas_las_entidades"], "KPI_10b_solo_BETO": l["kpis"]["KPI_10b_media_solo_entidades_BETO"],
    "KPI_11_directo_final_pct": l["kpis"]["KPI_11_directo_con_regla_personas_pct"],
    "conteos_fuente_resolucion": l["conteos_fuente_resolucion"],
    "muestra_50_BETO_semilla42": [(e["tipo"], e["valor"], e["archivo"], e["fila_origen"]) for e in (m["entidades"] if isinstance(m, dict) and "entidades" in m else m.get("muestra", m) if isinstance(m, dict) else m)],
    "dimensiones_dw": l["dimensiones_dw_usadas"],
}
(E / f"corrida_final_{n}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("ok", n)
