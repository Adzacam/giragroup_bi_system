"""R-2: extrae de una base tmpfs ya consolidada los casos pendientes de la bandeja, todos los hechos/staging y el índice BETO
de cada línea del lote, con claves estables entre corridas. Corre DENTRO de giragroup_api (PYTHONPATH = árbol aislado).

Uso: DATABASE_URL=<tmpfs> BETO_MODELO_VERSION=<v> python f1_r2_extraer_casos.py <dir_lectura_no_usado> <salida.json>
La salida contiene datos personales (CI, nombres en el texto): queda en el contenedor/scratchpad, nunca en docs/mediciones.
Las claves de grupo se calculan con las mismas funciones que la bandeja (services/bandeja_grupos, revision_consulta).
"""
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter as Counter_, defaultdict

from sqlalchemy import create_engine, text

from pipeline.semantic.indice_confianza import texto_para_indice
from services.bandeja_grupos import clave_grupo, motivo_estado, grupos_pendientes
from services.revision_consulta import token_grupo
from core.database import SessionLocal

MODELO = os.environ["BETO_MODELO_VERSION"]
ENG = create_engine(os.environ["DATABASE_URL"])


def q(sql, **kw):
    with ENG.connect() as c:
        return [dict(r._mapping) for r in c.execute(text(sql), kw)]


def num(v):
    return None if v is None else float(v)


def norm(t):
    t = "".join(ch for ch in unicodedata.normalize("NFD", t or "") if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", t).strip().upper()


def sha(t):
    return hashlib.sha256((t or "").encode("utf-8")).hexdigest()


def main(salida):
    archivos = {r["id_documento"]: r["nombre_archivo"] for r in q("SELECT id_documento, nombre_archivo FROM dim_origen_documental")}
    cache = {r["hash_texto"].strip(): float(r["indice"]) for r in q("SELECT hash_texto, indice FROM cache_indice_beto WHERE modelo = :m", m=MODELO)}

    # Líneas: misma partición que routers/dataops/consolidacion.py (texto_plano por '\n', sin vacías)
    lineas, por_doc = [], defaultdict(list)
    for s in q("SELECT id, id_documento, hoja, fila_inicio, texto_plano FROM staging_registros_crudos ORDER BY id"):
        raw = (s["texto_plano"] or "").strip()
        ls = [l.strip() for l in raw.split("\n") if l.strip()] or ([raw] if raw else [])
        for k, l in enumerate(ls):
            h = sha(texto_para_indice(l))
            key = f"{s['id_documento']}|{s['hoja']}|{s['fila_inicio']}|{k}"
            item = {"linea": key, "id_documento": s["id_documento"], "archivo": archivos.get(s["id_documento"]),
                    "indice": cache.get(h), "hash_indice": h}
            lineas.append(item)
            por_doc[s["id_documento"]].append((key, l, cache.get(h)))
    texto_a_linea = defaultdict(list)
    for d, ls in por_doc.items():
        for key, l, _ in ls:
            texto_a_linea[(d, l)].append(key)

    est = {r["id_estudiante"]: r for r in q("SELECT id_estudiante, nombre_completo, ci_numero, ci, identidad_verificada, id_temporal, fk_estado FROM dim_estudiante")}
    mod = {r["id_modulo"]: r for r in q("SELECT id_modulo, pos_code, nombre_modulo FROM dim_modulo")}
    pos_catalogo = {m.group(1) for r in mod.values() for m in [re.match(r"POS-(\d+)", r["pos_code"] or "")] if m}
    fuentes = {r["id_documento"]: r["tipo_fuente"] for r in q("SELECT id_documento, tipo_fuente FROM dim_origen_documental")}

    def est_campos(id_est):
        e = est.get(id_est)
        if not e:
            return {"est_clave": "", "est_ci_exacta": False, "est_temporal": None, "est_fk_estado": None, "_ci": None, "_nombre": None}
        ci = (e["ci_numero"] or "").strip() if e["ci_numero"] is not None else ""
        clave = ("CI:" + ci) if ci else ("NOM:" + sha(norm(e["nombre_completo"]))[:16])
        return {"est_clave": clave, "est_ci_exacta": bool(e["identidad_verificada"]) and bool(ci), "est_temporal": bool(e["id_temporal"]),
                "est_fk_estado": e["fk_estado"], "_ci": ci or None, "_nombre": e["nombre_completo"]}

    def mod_clave(id_mod):
        m = mod.get(id_mod)
        return f"{m['pos_code'] or ''}|{norm(m['nombre_modulo'])}" if m else ""

    def linea_de_hecho(doc, indice, ci, extras):
        """Línea de origen del hecho: mismo documento, mismo índice BETO (4 decimales), CI y valores presentes en el texto."""
        cands = [(k, l) for k, l, i in por_doc.get(doc, []) if i is not None and indice is not None and abs(round(i, 4) - indice) < 5e-5]
        if ci:
            c2 = [(k, l) for k, l in cands if ci in l]
            cands = c2 or cands
        for x in extras:
            c3 = [(k, l) for k, l in cands if x and x in l]
            if c3:
                cands = c3
        return (cands[0][0], len(cands)) if cands else (None, 0)

    todos, pendientes = [], []
    rid = 0
    for h in q("""SELECT id_hecho_aca, id_documento, id_estudiante, id_modulo, nota_final, asistencia_pct, id_tiempo, nivel_confianza_ia,
                         requiere_revision, estado_academico, estado_tutoria, estado_arca FROM fact_rendimiento_academico ORDER BY id_hecho_aca"""):
        rid += 1
        e = est_campos(h["id_estudiante"])
        faltan = ",".join(f for f, falta in (("estudiante", not h["id_estudiante"]), ("modulo", not h["id_modulo"]), ("nota", h["nota_final"] is None), ("fecha", not h["id_tiempo"])) if falta) or "ninguno"
        me = motivo_estado(h["estado_academico"], h["estado_tutoria"], h["estado_arca"])
        clave = f"HECHO_EN_REVISION::academico|doc{h['id_documento']}|falta:{faltan}|{h['estado_academico']}|{h['estado_tutoria']}|{h['estado_arca']}|estado:{me}"
        accion = "MAPEAR_ESTADO" if me != "OK" else "APROBAR" if faltan == "ninguno" else "CORREGIR_FECHA" if faltan == "fecha" else "MANUAL"
        if accion == "MAPEAR_ESTADO" and "|falta:ninguno|" not in clave:
            accion = "MANUAL"
        nota = num(h["nota_final"])
        m = mod.get(h["id_modulo"])
        linea, n_cand = linea_de_hecho(h["id_documento"], num(h["nivel_confianza_ia"]), e["_ci"],
                                       [f": {int(nota)}" if nota is not None and nota == int(nota) else None, (m or {}).get("pos_code")])
        c = {"rid": f"aca{rid}", "tipo": "aca", "motivo": "HECHO_EN_REVISION", "id_documento": h["id_documento"], "archivo": archivos.get(h["id_documento"]),
             "modulo_clave": mod_clave(h["id_modulo"]), "id_tiempo": h["id_tiempo"], "nota": nota, "asistencia": num(h["asistencia_pct"]),
             "estado_academico": h["estado_academico"], "estado_tutoria": h["estado_tutoria"], "estado_arca": h["estado_arca"],
             "estado_motivo": me, "faltan": faltan, "indice": num(h["nivel_confianza_ia"]), "pendiente": bool(h["requiere_revision"]),
             "grupo": token_grupo(clave), "accion": accion, "linea": linea, "linea_candidatas": n_cand,
             **{k: v for k, v in e.items() if not k.startswith("_")}}
        todos.append(c)
        if c["pendiente"]:
            pendientes.append(c)
    for h in q("""SELECT id_hecho_fin, id_documento, id_estudiante, id_tiempo, monto_deuda, nivel_confianza_ia, requiere_revision, concepto, id_modulo
                  FROM fact_situacion_financiera ORDER BY id_hecho_fin"""):
        rid += 1
        e = est_campos(h["id_estudiante"])
        faltan = ",".join(f for f, falta in (("estudiante", not h["id_estudiante"]), ("fecha", not h["id_tiempo"]), ("monto", h["monto_deuda"] is None)) if falta) or "ninguno"
        clave = f"HECHO_EN_REVISION::financiero|doc{h['id_documento']}|falta:{faltan}"
        linea, n_cand = linea_de_hecho(h["id_documento"], num(h["nivel_confianza_ia"]), e["_ci"], [])
        c = {"rid": f"fin{rid}", "tipo": "fin", "motivo": "HECHO_EN_REVISION", "id_documento": h["id_documento"], "archivo": archivos.get(h["id_documento"]),
             "id_tiempo": h["id_tiempo"], "monto_deuda": num(h["monto_deuda"]), "concepto": h["concepto"], "modulo_clave": mod_clave(h["id_modulo"]),
             "faltan": faltan, "indice": num(h["nivel_confianza_ia"]), "pendiente": bool(h["requiere_revision"]), "grupo": token_grupo(clave),
             "accion": "APROBAR" if faltan == "ninguno" else "CORREGIR_FECHA" if faltan == "fecha" else "MANUAL",
             "linea": linea, "linea_candidatas": n_cand, **{k: v for k, v in e.items() if not k.startswith("_")}}
        todos.append(c)
        if c["pendiente"]:
            pendientes.append(c)
    for s in q("""SELECT id_staging, id_documento, motivo, texto_original, clave_origen, nivel_confianza, resuelto, payload_json
                  FROM stg_entidad_no_resuelta ORDER BY id_staging"""):
        rid += 1
        p = s["payload_json"] if isinstance(s["payload_json"], dict) else {}
        raw = p.get("raw_line") or s["texto_original"] or ""
        keys = texto_a_linea.get((s["id_documento"], raw.strip())) or []
        if not keys and raw:
            keys = [k for k, l, _ in por_doc.get(s["id_documento"], []) if l.startswith(raw.strip()[:200])]
        ents = [{"tag": x.get("tag"), "fuente": x.get("fuente_resolucion")} for x in (p.get("entities") or []) if isinstance(x, dict)]
        poss = re.findall(r"POS-(\d+)", raw)
        c = {"rid": f"stg{rid}", "tipo": "stg", "motivo": s["motivo"], "id_documento": s["id_documento"], "archivo": archivos.get(s["id_documento"]),
             "tipo_fuente": fuentes.get(s["id_documento"]), "encabezado_programa": bool(re.search(r"(^|\| )(PROGRAMA|NRO POS): ", raw)),
             "pos_en_linea": bool(poss), "pos_en_catalogo": bool(poss) and all(n in pos_catalogo for n in poss),
             "clave_origen": s["clave_origen"], "texto_sha256": sha(s["texto_original"]), "indice": num(s["nivel_confianza"]),
             "pendiente": not s["resuelto"], "grupo": token_grupo(clave_grupo(s["motivo"], s["texto_original"])), "accion": "MANUAL",
             "linea": keys[0] if keys else None, "linea_candidatas": len(keys), "entidades": ents}
        todos.append(c)
        if c["pendiente"]:
            pendientes.append(c)
    # Evaluación docente pendiente de vinculación (un caso por grupo, como en bandeja_grupos._grupos_hechos)
    from services.revision_hechos import _q_eval
    db = SessionLocal()
    try:
        for id_doc, id_mod, *_ in _q_eval(db, list(archivos)).all():
            rid += 1
            clave = f"HECHO_EN_REVISION::evaluacion|doc{id_doc or 0}|mod{id_mod or 0}"
            c = {"rid": f"eva{rid}", "tipo": "eva", "motivo": "HECHO_EN_REVISION", "id_documento": id_doc, "archivo": archivos.get(id_doc),
                 "modulo_clave": mod_clave(id_mod), "indice": None, "pendiente": True, "grupo": token_grupo(clave), "accion": "MANUAL", "linea": None}
            todos.append(c)
            pendientes.append(c)
        api = grupos_pendientes(db, list(archivos), limite=10**9)
    finally:
        db.close()
    out = {"modelo": MODELO, "lineas": lineas, "todos": todos, "pendientes": pendientes,
           "grupos_api": [{"grupo": token_grupo(g["clave"]), "n": g["n"]} for g in api["grupos"]], "total_api": api["total_casos"],
           "kpi18_sql": int(q("SELECT count(*) AS n FROM stg_entidad_no_resuelta WHERE resuelto = FALSE")[0]["n"]),
           "cache_filas": len(cache), "lineas_sin_indice": sum(1 for l in lineas if l["indice"] is None)}
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, default=str)
    print(json.dumps({"pendientes": len(pendientes), "total_api": api["total_casos"], "lineas": len(lineas),
                      "lineas_sin_indice": out["lineas_sin_indice"], "kpi18": out["kpi18_sql"]}))


def _post(url, cuerpo):
    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode("utf-8"))


def entidades(claves_path, salida, url_v1, url_v2):
    """Entidades BETO (solo BETO, antes de reglas) de cada línea en v1 y v2, sobre el texto que evalúa el índice.
    Salida sin texto: tipos de entidad, número, índice y clase de cambio por línea."""
    claves = set(json.load(open(claves_path, encoding="utf-8")))
    textos = {}
    for s in q("SELECT id, id_documento, hoja, fila_inicio, texto_plano FROM staging_registros_crudos ORDER BY id"):
        raw = (s["texto_plano"] or "").strip()
        ls = [l.strip() for l in raw.split("\n") if l.strip()] or ([raw] if raw else [])
        for k, l in enumerate(ls):
            key = f"{s['id_documento']}|{s['hoja']}|{s['fila_inicio']}|{k}"
            if key in claves:
                textos[key] = texto_para_indice(l)
    keys = sorted(textos)
    res = {}
    for i in range(0, len(keys), 64):
        parte = keys[i:i + 64]
        ts = [textos[k] for k in parte]
        r = {}
        for v, url in (("v1", url_v1), ("v2", url_v2)):
            r[v] = (_post(url + "/indice", {"textos": ts})["indices"], _post(url + "/infer-batch", {"textos": ts})["resultados"])
        for j, k in enumerate(parte):
            e1 = [(e["type"], e["start"], e["end"]) for e in r["v1"][1][j]["entidades_beto"]]
            e2 = [(e["type"], e["start"], e["end"]) for e in r["v2"][1][j]["entidades_beto"]]
            t1, t2 = Counter_(t for t, _, _ in e1), Counter_(t for t, _, _ in e2)
            perd = sorted((t1 - t2).elements())
            gan = sorted((t2 - t1).elements())
            if not perd and not gan:
                clase = "mismos_tipos_mismos_tramos" if sorted(e1) == sorted(e2) else "mismos_tipos_distinto_tramo"
            elif perd and not gan:
                clase = "v2_pierde_entidad"
            elif gan and not perd:
                clase = "v2_gana_entidad"
            else:
                clase = "v2_cambia_tipo_de_entidad"
            res[k] = {"indice_v1_servicio": r["v1"][0][j], "indice_v2_servicio": r["v2"][0][j],
                      "tipos_v1": dict(t1), "tipos_v2": dict(t2), "pierde": perd, "gana": gan, "clase": clase,
                      "score_medio_v1": round(sum(e["score"] for e in r["v1"][1][j]["entidades_beto"]) / max(1, len(e1)), 4),
                      "score_medio_v2": round(sum(e["score"] for e in r["v2"][1][j]["entidades_beto"]) / max(1, len(e2)), 4)}
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False)
    print(json.dumps({"lineas": len(res), "clases": dict(Counter_(x["clase"] for x in res.values()))}))


if __name__ == "__main__":
    if sys.argv[1] == "entidades":
        entidades(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        main(sys.argv[2])
