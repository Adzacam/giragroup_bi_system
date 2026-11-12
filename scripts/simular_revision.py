"""Simula la revisión humana de la bandeja con la API actual (grupos paginados de 5, claves públicas, espera de 10 s con Deshacer).

El tiempo humano es SIMULADO con un reloj virtual (no se espera): lectura LECTURA_S por grupo, acción ACCION_S, CASO_MANUAL_S por caso en los
grupos manuales y ESPERA_DESHACER_S por cada acción, porque la pantalla del paso ④ espera 10 s antes de enviar y solo admite una operación pendiente.
Las duraciones de máquina de cada llamada son reales.

Uso (en giragroup_api, DATABASE_URL = base aislada tras el ciclo): ID_LOTE=<n> python scripts/simular_revision.py <salida.json>
Sin ID_LOTE revisa todos los documentos con casos pendientes.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

LECTURA_S, ACCION_S, CASO_MANUAL_S, ESPERA_DESHACER_S = 6.0, 2.0, 20.0, 10.0
BASE = "/api/v1/dataops"


def cliente():
    from fastapi.testclient import TestClient
    from main import app
    from core.security import get_current_user
    from models.user import User
    app.dependency_overrides[get_current_user] = lambda: User(id=2, username="auditor", email="a@giragroup.bo", role="AUDITOR_CALIDAD", is_active=True)
    return TestClient(app)


def _todos_los_grupos(cli, params):
    primera = cli.get(f"{BASE}/review-tray/grupos", params=params).json()
    grupos, paginas = list(primera["grupos"]), primera["pagination"]["total_pages"]
    for p in range(2, paginas + 1):
        grupos += cli.get(f"{BASE}/review-tray/grupos", params={**params, "page": p}).json()["grupos"]
    return primera, grupos


def simular(cli, id_lote=None):
    params = {"id_lote": id_lote} if id_lote else {}
    primera, grupos = _todos_los_grupos(cli, params)
    doc_ids = primera.get("doc_ids")
    virtual = datetime.now(timezone.utc)
    inicio_humano = virtual
    eventos, bloque, manuales, bloqueados = [], 0, 0, 0
    for g in grupos:
        accion = g.get("accion_grupo") or "MANUAL"
        v0 = virtual + timedelta(seconds=LECTURA_S)
        t0 = time.perf_counter()
        if accion == "MANUAL":
            manuales += 1
            resueltos = rechazados = 0
            while True:  # caso por caso: aprobar el hecho tal cual (el humano corregiría; aquí solo se mide el flujo)
                casos = cli.get(f"{BASE}/review-tray", params={**params, "grupo": g["clave"], "page": 1, "page_size": 5}).json().get("items") or []
                avance = 0
                for c in casos:
                    rr = cli.post(f"{BASE}/review-tray/{c['id']}/resolve", json={"accion": "APROBAR"})
                    ok = rr.status_code == 200 and (rr.json() or {}).get("status") == "success"
                    resueltos += ok
                    rechazados += not ok
                    avance += ok
                if not casos or not avance:
                    break
            dur_h = (CASO_MANUAL_S + ESPERA_DESHACER_S) * g["n"]
            bloqueados += rechazados
            res = {"resueltos": resueltos, "rechazados_por_regla": rechazados}
        else:
            bloque += 1
            body = {"clave": g["clave"], "doc_ids": doc_ids, "accion": "MAPEAR_ESTADO" if accion == "MAPEAR_ESTADO" else None}
            if accion == "CORREGIR_FECHA":
                body.update({"mes": 3, "gestion": 2026})
            rr = cli.post(f"{BASE}/review-tray/approve-group", json=body)
            res = {"resueltos": (rr.json() or {}).get("resolved_count"), "http": rr.status_code}
            dur_h = ACCION_S + ESPERA_DESHACER_S
        dt = time.perf_counter() - t0
        eventos.append({"grupo": g["clave"][:24], "titulo": g.get("titulo"), "accion": accion, "casos": g["n"],
                        "inicio_humano_simulado": v0.isoformat(), "fin_humano_simulado": (v0 + timedelta(seconds=dur_h)).isoformat(),
                        "segundos_humano_simulado": dur_h, "segundos_maquina_real": round(dt, 3), **res})
        virtual = v0 + timedelta(seconds=dur_h)
    total_h = (virtual - inicio_humano).total_seconds()
    resumen = {"casos": primera["total_casos"], "grupos": primera["total_grupos"], "grupos_aprobables_en_bloque": bloque,
               "grupos_manuales": manuales, "casos_rechazados_por_regla": bloqueados,
               "pct_grupos_aprobables_en_bloque": round(bloque / max(1, len(grupos)) * 100, 1),
               "tiempo_humano_simulado_s": total_h,
               "supuestos": {"lectura_por_grupo_s": LECTURA_S, "accion_por_grupo_s": ACCION_S, "por_caso_manual_s": CASO_MANUAL_S,
                             "espera_deshacer_por_accion_s": ESPERA_DESHACER_S},
               "tiempo_maquina_real_aprobaciones_s": round(sum(e["segundos_maquina_real"] for e in eventos), 2)}
    return {"resumen": resumen, "eventos": eventos}


if __name__ == "__main__":
    salida = simular(cliente(), os.environ.get("ID_LOTE"))
    Path(sys.argv[1]).write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(salida["resumen"], ensure_ascii=False))
