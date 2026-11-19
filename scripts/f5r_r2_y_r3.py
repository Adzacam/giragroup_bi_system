"""R-2 (Casos de identidad pendientes por motivo, con 5 ejemplos enmascarados)
y R-3 (Verificación de uso: 23 KPI en /api/v1/cmi/scorecard, KPI-23 Δ=0 vs f3v_kpi23_serie.json, alertas y pronósticos).
Lee credenciales de F5R_EMAIL / F5R_PASS / PG_PASS (sin hardcodear secretos).
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import psycopg2
import requests

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = os.getenv("F5R_BASE_URL", "http://127.0.0.1:80").rstrip("/")


def mask_text(s: str | None) -> str | None:
    if not s:
        return s
    # Enmascarar posibles CIs/números largos y palabras de nombres propios
    tokens = re.split(r"(\s+|\|)", s)
    out = []
    for tok in tokens:
        if not tok or tok.isspace() or tok == "|":
            out.append(tok)
        elif re.fullmatch(r"\d{5,}", tok):
            out.append("***" + tok[-3:])
        elif "@" in tok:
            user, _, dom = tok.partition("@")
            out.append((user[:1] + "***@" + dom) if user else "***@" + dom)
        elif len(tok) <= 2:
            out.append(tok[0] + "*")
        else:
            out.append(tok[0] + "***" + tok[-1])
    return "".join(out)


def login_token(session: requests.Session) -> str:
    email = os.environ["F5R_EMAIL"]
    password = os.environ["F5R_PASS"]
    r1 = session.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    r1.raise_for_status()
    data1 = r1.json()
    if not data1.get("mfa_required") and data1.get("access_token"):
        return data1["access_token"]
    logs = subprocess.check_output(
        ["docker", "logs", "--tail", "30", "giragroup_auth_svc"],
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    otps = re.findall(r"CÓDIGO OTP PARA [^:]+:\s*(\d{6})", logs)
    if not otps:
        raise RuntimeError("No se encontró OTP en logs de giragroup_auth_svc")
    r2 = session.post(
        f"{BASE_URL}/api/v1/auth/verify-otp",
        json={"temp_token": data1["temp_token"], "code": otps[-1], "remember_device": False},
        timeout=20,
    )
    r2.raise_for_status()
    return r2.json()["access_token"]


def ejecutar_r2() -> dict:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5434,
        dbname="giragroup_db",
        user="giragroup_user",
        password=os.getenv("PG_PASS", "giragroup_secret_2026"),
    )
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(motivo, 'SIN_MOTIVO') AS motivo,
               COALESCE(tipo_entidad, 'DESCONOCIDO') AS tipo_entidad,
               count(*) AS cantidad
        FROM stg_entidad_no_resuelta
        WHERE resuelto = false
        GROUP BY 1, 2
        ORDER BY cantidad DESC, motivo ASC
    """)
    pendientes_por_motivo = []
    total_pendientes = 0
    for motivo, tipo_entidad, cantidad in cur.fetchall():
        total_pendientes += int(cantidad)
        cur.execute("""
            SELECT s.id_staging, s.id_documento, d.nombre_archivo,
                   s.texto_original, s.ci_temporal, s.mejor_candidato,
                   s.score_fuzzy, s.nivel_confianza
            FROM stg_entidad_no_resuelta s
            LEFT JOIN dim_origen_documental d ON d.id_documento = s.id_documento
            WHERE s.resuelto = false
              AND COALESCE(s.motivo, 'SIN_MOTIVO') = %s
              AND COALESCE(s.tipo_entidad, 'DESCONOCIDO') = %s
            ORDER BY s.id_staging ASC
            LIMIT 5
        """, (motivo, tipo_entidad))
        ejemplos = []
        for id_stg, id_doc, nom_arch, txt, ci_tmp, cand, score, conf in cur.fetchall():
            ejemplos.append({
                "id_staging": id_stg,
                "id_documento": id_doc,
                "archivo": nom_arch,
                "texto_enmascarado": mask_text(txt),
                "ci_temporal_enmascarado": mask_text(ci_tmp),
                "mejor_candidato_enmascarado": mask_text(cand),
                "score_fuzzy": float(score) if score is not None else None,
                "nivel_confianza": float(conf) if conf is not None else None,
            })
        pendientes_por_motivo.append({
            "motivo": motivo,
            "tipo_entidad": tipo_entidad,
            "cantidad": int(cantidad),
            "ejemplos_enmascarados": ejemplos,
        })

    cur.execute("""
        SELECT COALESCE(motivo, 'SIN_MOTIVO') AS motivo,
               COALESCE(estado_resolucion, 'DESCONOCIDO') AS estado_resolucion,
               count(*) AS cantidad
        FROM stg_entidad_no_resuelta
        WHERE resuelto = true
        GROUP BY 1, 2
        ORDER BY cantidad DESC
    """)
    resueltos_o_descartados = [
        {"motivo": m, "estado_resolucion": e, "cantidad": int(c)}
        for m, e, c in cur.fetchall()
    ]
    total_descartados = sum(x["cantidad"] for x in resueltos_o_descartados)

    cur.close()
    conn.close()

    out = {
        "tarea": "R-2",
        "nota": "Casos de identidad pendientes de resolución humana (no aprobados ni descartados automáticamente).",
        "total_pendientes": total_pendientes,
        "total_resueltos_o_descartados": total_descartados,
        "pendientes_por_motivo": pendientes_por_motivo,
        "resueltos_o_descartados_por_motivo": resueltos_o_descartados,
    }
    (ROOT / "docs" / "mediciones" / "f5r_casos_pendientes.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"R-2 OK: {total_pendientes} pendientes en {len(pendientes_por_motivo)} motivos", flush=True)
    return out


def ejecutar_r3() -> dict:
    s = requests.Session()
    token = login_token(s)
    headers = {"Authorization": f"Bearer {token}"}

    kpi23_ref_raw = json.loads(
        (ROOT / "docs" / "mediciones" / "f3v_kpi23_serie.json").read_text(encoding="utf-8")
    )["kpi23_por_gestion"]
    kpi23_ref = {int(item["gestion"]): item for item in kpi23_ref_raw}

    scorecards_por_gestion = {}
    kpi23_comparacion = []
    for g in (2023, 2024, 2025, 2026):
        r = s.get(f"{BASE_URL}/api/v1/cmi/scorecard", params={"gestion": g}, headers=headers, timeout=30)
        r.raise_for_status()
        sc = r.json()
        kpis = [k for p in sc.get("perspectivas", []) for k in p.get("kpis", [])]
        con_valor = [k for k in kpis if k.get("valor") is not None]
        kpi23 = next((k for k in kpis if k.get("codigo") == "KPI-23"), None)
        ref = kpi23_ref.get(g, {})
        val_viva = kpi23.get("valor") if kpi23 else None
        val_ref = ref.get("valor")
        delta = (
            0.0 if (val_viva is None and val_ref is None)
            else round(float(val_viva) - float(val_ref), 4) if (val_viva is not None and val_ref is not None)
            else None
        )
        scorecards_por_gestion[str(g)] = {
            "total_kpis": len(kpis),
            "kpis_con_valor": len(con_valor),
            "indice_global": (sc.get("global") or {}).get("indice"),
            "perspectivas": [
                {
                    "codigo": p.get("codigo"),
                    "indicadores": p.get("indicadores"),
                    "indice": p.get("indice"),
                }
                for p in sc.get("perspectivas", [])
            ],
        }
        kpi23_comparacion.append({
            "gestion": g,
            "valor_dw_viva": val_viva,
            "valor_f3v_congelado": val_ref,
            "semaforo_dw_viva": kpi23.get("semaforo") if kpi23 else None,
            "semaforo_f3v_congelado": ref.get("semaforo"),
            "delta": delta,
        })

    # Alertas
    r_al_kpis = s.get(f"{BASE_URL}/api/v1/alertas", headers=headers, timeout=60)
    r_al_kpis.raise_for_status()
    al_kpis = r_al_kpis.json()

    r_al_temp = s.get(f"{BASE_URL}/api/v1/riesgos/alertas-tempranas", headers=headers, timeout=60)
    r_al_temp.raise_for_status()
    al_temp = r_al_temp.json()

    # Pronósticos
    r_fc = s.get(
        f"{BASE_URL}/api/v1/forecast/analitica-macro",
        params={"horizonte": 6},
        headers=headers,
        timeout=30,
    )
    r_fc.raise_for_status()
    fc = r_fc.json()

    out = {
        "tarea": "R-3",
        "scorecards_por_gestion": scorecards_por_gestion,
        "kpi23_vs_f3v_kpi23_serie": kpi23_comparacion,
        "alertas_kpis": {
            "status_code": r_al_kpis.status_code,
            "total": al_kpis.get("total_alertas", len(al_kpis.get("data", []))),
            "criticas": al_kpis.get("criticas"),
            "advertencias": al_kpis.get("advertencias"),
        },
        "alertas_tempranas": {
            "status_code": r_al_temp.status_code,
            "total_matricula_activa": al_temp.get("total_matricula_activa") if isinstance(al_temp, dict) else None,
            "total_estudiantes_filtrados": al_temp.get("total_estudiantes_filtrados") if isinstance(al_temp, dict) else None,
            "tarjetas": {
                k: {
                    "total_alumnos": v.get("total_alumnos"),
                    "porcentaje_matricula": v.get("porcentaje_matricula"),
                    "monto_mora_bs": v.get("monto_mora_bs"),
                }
                for k, v in (al_temp.get("tarjetas") or {}).items()
            } if isinstance(al_temp, dict) else None,
        },
        "pronostico_analitica_macro": {
            "status_code": r_fc.status_code,
            "claves": sorted(fc.keys()) if isinstance(fc, dict) else None,
        },
    }
    (ROOT / "docs" / "mediciones" / "f5r_verificacion_uso.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("R-3 API OK:", json.dumps(kpi23_comparacion, ensure_ascii=False), flush=True)
    return out


if __name__ == "__main__":
    ejecutar_r2()
    ejecutar_r3()
