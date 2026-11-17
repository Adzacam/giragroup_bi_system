"""T-4: Reconciliacion de la formula exacta de KPI-15 (73,44 % vs 69,93 %)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    f3_2 = json.loads((ROOT / "docs/mediciones/f3_2_kpi15.json").read_text(encoding="utf-8"))
    f3r_cuadre = json.loads((ROOT / "docs/mediciones/f3r_kpi15_cuadre.json").read_text(encoding="utf-8"))

    mora_deuda = f3r_cuadre["por_estado_cartera"]["Mora"]["monto_deuda"]
    prev_deuda = f3r_cuadre["por_estado_cartera"]["Previsionable"]["monto_deuda"]
    vig_deuda = f3r_cuadre["por_estado_cartera"]["Vigente"]["monto_deuda"]
    tot_deuda = round(mora_deuda + prev_deuda + vig_deuda, 2)

    mora_filas = f3r_cuadre["por_estado_cartera"]["Mora"]["filas"]
    prev_filas = f3r_cuadre["por_estado_cartera"]["Previsionable"]["filas"]
    vig_filas = f3r_cuadre["por_estado_cartera"]["Vigente"]["filas"]
    tot_filas = mora_filas + prev_filas + vig_filas

    out = {
        "etiqueta": "F3T",
        "tarea": "T-4 (Formula exacta de KPI-15: 73,44 % vs 69,93 %)",
        "definicion_oficial_sql": {
            "archivo_y_lineas": "backend/scripts/migrations/006_capa_semantica_cmi.sql:73,268-269 y 014_conversion_captacion_comprobable.sql:106",
            "nombre": "Cartera vencida",
            "descripcion": "Deuda en mora o previsionable sobre la deuda total (por gestion en bi.vw_cmi_valores)",
            "formula": "100.0 * SUM(monto_deuda) FILTER (WHERE estado_cartera IN ('Mora','En Mora','Previsionable')) / NULLIF(SUM(monto_deuda), 0)",
        },
        "origen_73_44": {
            "valor": 73.44,
            "valor_sql_exacto": f3_2["kpi_15_api_vs_sql"]["2025"]["sql"],
            "gestion": 2025,
            "base": "f3_base (bi.vw_cmi_valores / GET /api/v1/cmi/scorecard?gestion=2025)",
            "criterio": "Proporcion de monto_deuda en Mora+Previsionable sobre monto_deuda total de la gestion 2025",
            "es_el_kpi15_oficial": True,
        },
        "origen_69_93": {
            "valor": 69.93,
            "numerador_filas": mora_filas + prev_filas,
            "denominador_filas": tot_filas,
            "calculo": f"({mora_filas} + {prev_filas}) / {tot_filas} * 100 = {round((mora_filas + prev_filas) / tot_filas * 100, 2)}%",
            "gestion": "Todas las gestiones acumuladas (sin filtro de gestion)",
            "criterio": "Conteo de filas (no monto_deuda); corresponde a una razon operativa de filas del cuadre (cercana a KPI-05 sin deduplicar estudiante), NO a KPI-15 oficial",
            "es_el_kpi15_oficial": False,
        },
        "nota_monto_acumulado_todas_gestiones": {
            "numerador_bs": round(mora_deuda + prev_deuda, 2),
            "denominador_bs": tot_deuda,
            "pct_todas_gestiones": round((mora_deuda + prev_deuda) / tot_deuda * 100.0, 2),
        },
        "nota_kpi_service_py": "backend/services/kpi_service.py:434 calcula mora_total_pct por conteo (KPI-05), mientras KPI-15 en el CMI proviene de bi.vw_cmi_valores (monto_deuda por gestion).",
        "decision_sfv": "La SFV debe publicar 73,44 % (gestion 2025, f3s_base / f3_2_kpi15.json) como KPI-15 oficial, y el cuadre 500/7/218 (69,93 % en filas) solo como desglose de conteo de filas acumuladas.",
    }
    (ROOT / "docs/mediciones/f3t_kpi15_formula.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("[OK] T-4 KPI-15: 73.44% (monto_deuda 2025) vs 69.93% (filas acumuladas)")


if __name__ == "__main__":
    main()
