"""T-2: Diagnostico del clasificador detectar_tipo_fuente_por_cabeceras sobre BD Techos y los 10 archivos."""
import json
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from services.ingestion_service import _contiene_tokens, _strip_accents, detectar_tipo_fuente_por_cabeceras


def analizar_libro(path: Path):
    xl = pd.ExcelFile(path)
    hojas = {s: pd.read_excel(xl, sheet_name=s) for s in xl.sheet_names}
    tokens_cabecera = []
    for sheet_name, df in hojas.items():
        s_str = _strip_accents(str(sheet_name))
        if s_str and not s_str.startswith("sheet") and not s_str.startswith("hoja"):
            tokens_cabecera.append(s_str)
        if df is None or df.empty:
            continue
        for col in df.columns:
            c_str = _strip_accents(str(col))
            if c_str and not c_str.startswith("unnamed"):
                tokens_cabecera.append(c_str)
        for idx in range(min(15, len(df))):
            for v in df.iloc[idx].values:
                if pd.notna(v):
                    v_raw = str(v).strip()
                    v_str = _strip_accents(v_raw)
                    if v_str and not v_str.replace(".", "", 1).replace("-", "", 1).isdigit() and len(v_str) < 60:
                        tokens_cabecera.append(v_str)

    joined = " | ".join(tokens_cabecera)
    tipo_ganador = detectar_tipo_fuente_por_cabeceras(hojas, filename=path.name)

    tokens_mkt = ("lead", "leads", "campana", "campaña", "medio de contacto", "canal", "fuente lead", "asesor comercial", "reservas", "costo programa")
    tokens_techo = ("techo", "techos", "techo presupuestario", "presupuesto asignado", "presupuestado")
    tokens_adm = ("postulante", "postulantes", "preinscrito", "preinscritos", "preinscripcion", "matricula", "matriculas", "inscrito", "inscritos", "marca temporal", "formulario")
    tokens_rent = ("rentabilidad", "ejecutado vs meta", "ejecutado", "monto_ejecutado", "monto_meta", "ebitda", "margen", "utilidad", "meta por categoria")
    tokens_egreso = ("egreso", "egresos", "gasto", "gastos", "partida", "comprobante de egreso", "proveedor", "proveedores", "desembolso", "beneficiario")

    hits = {
        "MARKETING": [t for t in tokens_mkt if _contiene_tokens(joined, (t,))],
        "TECHOS": [t for t in tokens_techo if _contiene_tokens(joined, (t,))],
        "ADMISION": [t for t in tokens_adm if _contiene_tokens(joined, (t,))],
        "RENTABILIDAD": [t for t in tokens_rent if _contiene_tokens(joined, (t,))],
        "EGRESOS": [t for t in tokens_egreso if _contiene_tokens(joined, (t,))],
    }
    puntajes_relevantes = {
        "MARKETING": 14 if hits["MARKETING"] else 0,
        "TECHOS": 12 if hits["TECHOS"] else 0,
        "ADMISION": 12 if hits["ADMISION"] else 0,
        "RENTABILIDAD": 14 if hits["RENTABILIDAD"] else 0,
        "EGRESOS": 12 if hits["EGRESOS"] else 0,
    }
    return {
        "archivo": str(path.relative_to(ROOT)),
        "tipo_ganador": tipo_ganador,
        "puntajes_relevantes": puntajes_relevantes,
        "tokens_activados": hits,
        "causa_marketing_sobre_techos": (
            "En ingestion_service.py:367-382, has_mkt ('asesor comercial') suma +14 a MARKETING, "
            "mientras has_techo ('techo', 'gestion techo', 'escuela techo') suma +12 a TECHOS (14 > 12)."
        ),
    }


def main():
    full_techos = analizar_libro(ROOT / "uploads/data/BD Techos.xlsx")
    slice_techos = analizar_libro(ROOT / "output/backups/f0_lote/slices/BD Techos.xlsx")

    otros_9 = []
    for p in sorted((ROOT / "uploads/data").glob("*.xlsx")):
        if p.name == "BD Techos.xlsx":
            continue
        info = analizar_libro(p)
        otros_9.append({
            "archivo": p.name,
            "tipo_actual": info["tipo_ganador"],
            "tiene_tokens_techos": info["tokens_activados"]["TECHOS"],
            "cambiaria_si_techos_superara_14": bool(info["tokens_activados"]["TECHOS"]) and info["puntajes_relevantes"]["RENTABILIDAD"] < 15,
        })

    out = {
        "etiqueta": "F3T, solo diagnostico",
        "tarea": "T-2 (Clasificacion de BD Techos.xlsx)",
        "libro_completo": full_techos,
        "recorte_mensual": slice_techos,
        "impacto_en_otros_9_archivos_si_techos_ganara": otros_9,
    }
    (ROOT / "docs/mediciones/f3t_clasificacion_techos.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[OK] T-2 full={full_techos['tipo_ganador']} slice={slice_techos['tipo_ganador']}")


if __name__ == "__main__":
    main()
