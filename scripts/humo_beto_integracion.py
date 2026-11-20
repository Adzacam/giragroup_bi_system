"""Humo de la integración de BETO contra el servicio real (:8006) y una base aislada: pasa N líneas por refinar_lineas con los flags
encendidos y muestra los contadores. NO es una medición: sirve para comprobar el cableado de extremo a extremo.

Uso (en giragroup_api; DATABASE_URL = base aislada que ya tenga un lote cargado; BETO_* = flags a probar):
    BETO_ACUERDO_QC=1 BETO_CASCADA_FINAL=1 python scripts/humo_beto_integracion.py [N=120]
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]
from sqlalchemy import text  # noqa: E402

from core.database import SessionLocal  # noqa: E402
from models.dim_estudiante import DimEstudiante  # noqa: E402
from routers.dataops.extraccion import EXCLUIR_CELDA_BETO, _docentes_con_contexto, extract_entities_from_line, fila_sin_entidad  # noqa: E402
from models.dim_modulo import DimModulo  # noqa: E402
from services import beto_integracion as bi  # noqa: E402


def main(n):
    db = SessionLocal()
    estudiantes = db.query(DimEstudiante).filter(DimEstudiante.deprecado == False).all()  # noqa: E712
    docentes, modulos = _docentes_con_contexto(db), db.query(DimModulo).all()
    filas = db.execute(text("SELECT s.texto_plano, d.tipo_fuente, d.nombre_archivo FROM staging_registros_crudos s JOIN dim_origen_documental d "
                            "ON d.id_documento = s.id_documento WHERE s.es_ruido = false AND d.tipo_fuente IN ('ACTA', 'COBRANZA', 'ADMISION') "
                            "ORDER BY s.id")).fetchall()
    lineas = []
    for texto, tf, archivo in filas:
        for l in (texto or "").splitlines():
            if l.strip() and not fila_sin_entidad(l.strip(), tf):
                lineas.append((l.strip(), tf, archivo))
        if len(lineas) >= n * 4:
            break
    paso = max(1, len(lineas) // n)
    muestra = lineas[::paso][:n]
    cont = bi.Contadores()
    cliente = bi.ClienteBeto(contadores=cont)
    for tf in sorted({m[1] for m in muestra}):
        sub = [m for m in muestra if m[1] == tf]
        res = bi.refinar_lineas([m[0] for m in sub],
                                lambda l, **kw: extract_entities_from_line(l, estudiantes, docentes, modulos, tipo_escala="CENTESIMAL_100", tipo_fuente=tf, **kw),
                                tipo_fuente=tf, cliente=cliente, contadores=cont, archivo=sub[0][2], excluir_celda=EXCLUIR_CELDA_BETO)
        print(tf, len(sub), "líneas; promovidas:", sum(1 for r in res if r and r.promovida_por_beto),
              "desacuerdos:", sum(1 for r in res if r and r.acuerdo == bi.DESACUERDO), "acuerdos:", sum(1 for r in res if r and r.acuerdo == bi.ACUERDO))
    print(json.dumps(cont.como_dict(), ensure_ascii=False))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 120)
