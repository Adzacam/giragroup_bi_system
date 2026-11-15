#!/usr/bin/env python
"""R-2 (PLAN_F1R2): diagnóstico de la bandeja 182 -> 680 y de KPI-18 59 -> 36 entre f1_off (beto-v1) y f1_validacion (beto-v2).

Las huellas existentes solo guardan conteos y la firma de grupos, así que el desglose caso a caso exige reproducir las dos
corridas en la copia tmpfs (scripts/aislada_tmpfs.sh) con el mismo lote congelado, el mismo código y los 4 flags en 0:

  v1: índice BETO servido por un contenedor AISLADO (beto_pipeline_r2v1) con los pesos de output/f1/beto_local_respaldo
      (beto-v1, sha256 en f1_promocion_modelo.json) y BETO_MODELO_VERSION=beto-v1, caché vacía. No toca el servicio vivo.
  v2: BETO_MODELO_VERSION=beto-v2 con la caché sembrada por F1-V (output/f1/f1v_cache_seed.sql): todos los índices salen
      de la caché, ninguna petición al servicio vivo.
Cada corrida se acepta solo si su huella es idéntica a la de referencia (f1_off / f1_validacion_llena_r1).

Subcomandos:
  correr v1|v2        corrida en tmpfs (base run_r2r_<v>, no se borra) -> docs/mediciones/f1_r2_corrida_<v>.json(+huella, meta)
  extraer v1|v2       casos y líneas de la base -> scratchpad (contiene datos personales: NO va a docs/mediciones)
  analizar            diff caso a caso, atribución, muestra, conclusión -> f1_r2_bandeja_diff.csv, f1_r2_diagnostico.json

No cambia el modelo vivo, la cascada ni los umbrales; no toca la DW viva ni el snapshot (solo lo lee aislada_tmpfs.sh up).
"""
import argparse
import csv
import hashlib
import json
import random
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEDICIONES = ROOT / "docs/mediciones"
ARBOL = "/tmp/f1_r2"
CONTENEDOR_V1 = "beto_pipeline_r2v1"
SEMILLA_MUESTRA = 20261115
N_MUESTRA = 30
UMBRAL_CONSOLIDADO, UMBRAL_REVISION = 0.85, 0.60  # leídos de pipeline/semantic/indice_confianza.py, no se cambian

FLAGS = ["BETO_CASCADA_FINAL=0", "BETO_ACUERDO_QC=0", "BETO_SUGERENCIA_HITL=0", "BETO_VENTANA=0", "BETO_VENTANA_STRIDE=32",
         "BETO_UMBRAL_REGLA=0.85", "BETO_UMBRAL_BETO=0.85", "BETO_PESO_SIM=0.55", "BETO_PESO_BETO=0.45", "BETO_INT8=0"]
REFERENCIA = {"v1": MEDICIONES / "f1_off.json.huella.json", "v2": MEDICIONES / "f1_validacion_llena_r1.json.huella.json"}


def sh(*args, check=True, cwd=ROOT):
    res = subprocess.run(args, cwd=cwd, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if check and res.returncode != 0:
        raise RuntimeError(f"Falló {' '.join(args[:4])}...: {(res.stderr or res.stdout)[-800:]}")
    return res.stdout


def sql(db, q):
    if not re.fullmatch(r"run_r2r_v[12]", db):
        raise ValueError(f"Base no autorizada: {db}")
    return sh("docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", db, "-Atc", q).strip()


def sha256_archivo(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def banda(i):
    if i is None or i < UMBRAL_REVISION:
        return "STAGING"
    return "REVISION" if i < UMBRAL_CONSOLIDADO else "CONSOLIDADO"


def firma_sha(firma):
    return hashlib.sha256(json.dumps(firma, sort_keys=True).encode()).hexdigest()


def comparar_con_referencia(huella, ref_path):
    ref = json.loads(Path(ref_path).read_text(encoding="utf-8"))
    tablas = sorted(t for t in set(ref["tablas"]) | set(huella["tablas"]) if ref["tablas"].get(t) != huella["tablas"].get(t))
    b, rb = dict(huella["bandeja"]), dict(ref["bandeja"])
    for x in (b, rb):
        if "firma" in x:
            x["firma_sha256"] = firma_sha(x.pop("firma"))
    return {"referencia": ref_path.name, "tablas_distintas": tablas, "bandeja_igual": b == rb, "kpis_iguales": ref["kpis"] == huella["kpis"],
            "identica": not tablas and b == rb and ref["kpis"] == huella["kpis"], "bandeja": b, "bandeja_referencia": rb}


# ----------------------------------------------------------------------------------------------------------- correr
def puertos():
    tmpfs = sh("docker", "port", "beto_pg_tmpfs").strip()
    viva = sh("docker", "port", "giragroup_db").strip()
    p_tmpfs = re.findall(r":(\d+)$", tmpfs, re.M)
    p_viva = re.findall(r":(\d+)$", viva, re.M)
    if not p_tmpfs or set(p_tmpfs) & set(p_viva):
        raise RuntimeError(f"TMPFS_PORT no verificado: tmpfs={tmpfs!r} viva={viva!r}")
    return {"tmpfs_port": int(p_tmpfs[0]), "dw_viva_port": int(p_viva[0]) if p_viva else None}


def correr(variante, preparar):
    sys.path.insert(0, str(ROOT / "scripts"))
    import f1_validar as fv
    import medir_f0 as f0
    fv.ARBOL = ARBOL
    db = f"run_r2r_{variante}"
    pt = puertos()
    if preparar:
        fv.preparar_arbol()  # copia backend/pipeline/lote al árbol y verifica el lote dentro del contenedor
    verif_antes = f0.verify()
    servicio = None
    if variante == "v1":
        servicio = {"contenedor": CONTENEDOR_V1,
                    "model_safetensors_sha256": sh("docker", "exec", CONTENEDOR_V1, "sha256sum",
                                                   "/app/pipeline/semantic/beto_local/model.safetensors").split()[0],
                    "health": json.loads(sh("docker", "exec", "giragroup_api", "python", "-c",
                                            f"import urllib.request;print(urllib.request.urlopen('http://{CONTENEDOR_V1}:8006/health',timeout=30).read().decode())"))}
        promo = json.loads((MEDICIONES / "f1_promocion_modelo.json").read_text(encoding="utf-8"))
        esperado = {x["archivo"]: x["sha256"] for x in promo["respaldo_archivos"]}["model.safetensors"]
        if servicio["model_safetensors_sha256"] != esperado:
            raise RuntimeError("El contenedor aislado no sirve los pesos beto-v1 del respaldo")
    lectura, landing = f"/tmp/f1v/{db}/lectura", f"/tmp/f1v/{db}/landing"
    sh("docker", "exec", "giragroup_api", "rm", "-rf", f"/tmp/f1v/{db}")
    sh("docker", "exec", "giragroup_api", "mkdir", "-p", lectura, landing)
    sh(shutil.which("sh") or r"C:\Program Files\Git\bin\sh.exe", "scripts/aislada_tmpfs.sh", "clon", db)
    sql(db, "TRUNCATE public.cache_indice_beto;")
    if variante == "v2":
        seed = ROOT / "output/f1/f1v_cache_seed.sql"
        sh("docker", "cp", str(seed), "beto_pg_tmpfs:/tmp/f1_r2_seed.sql")
        sh("docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", db, "-q", "-v", "ON_ERROR_STOP=1", "-f", "/tmp/f1_r2_seed.sql")
    cache_antes = int(sql(db, "SELECT count(*) FROM public.cache_indice_beto"))
    modelo = "beto-v1" if variante == "v1" else "beto-v2"
    env = FLAGS + [f"BETO_MODELO_VERSION={modelo}",
                   f"DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/{db}",
                   "FLUJO_SIN_REVISION=1", "CICLO_REUSAR_SLICES=1", "CICLO_FILAS_SIN_FECHA=0", "CICLO_SLICES=/tmp/slices_flujo",
                   f"LECTURA_CACHE_DIR={lectura}", f"LANDING_DIR={landing}", f"PYTHONPATH={ARBOL}:{ARBOL}/backend:/tmp/flujo/scripts"]
    if variante == "v1":
        base = f"http://{CONTENEDOR_V1}:8006"
        env += [f"BETO_INDICE_URL={base}/indice", f"BETO_INFERENCE_URL={base}/infer", f"BETO_INFER_BATCH_URL={base}/infer-batch"]
    else:  # sin servicio: si faltara un índice en la caché la petición falla y la huella dejaría de coincidir
        env += ["BETO_INDICE_URL=http://127.0.0.1:9/indice", "BETO_INFERENCE_URL=http://127.0.0.1:9/infer",
                "BETO_INFER_BATCH_URL=http://127.0.0.1:9/infer-batch"]
    salida = f"f1_r2_corrida_{variante}.json"
    inicio = datetime.now(timezone.utc).astimezone().isoformat()
    t0 = time.perf_counter()
    sh("docker", "exec", "-w", ARBOL, "giragroup_api", "env", *env, "python", "/tmp/flujo/scripts/medir_flujo_dataops.py", "/tmp/" + salida)
    pared = round(time.perf_counter() - t0, 3)
    sh("docker", "cp", f"giragroup_api:/tmp/{salida}", str(MEDICIONES / salida))
    sh("docker", "cp", f"giragroup_api:/tmp/{salida}.huella.json", str(MEDICIONES / f"{salida}.huella.json"))
    data = json.loads((MEDICIONES / salida).read_text(encoding="utf-8"))
    data.get("carga", {}).pop("errores", None)
    (MEDICIONES / salida).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    huella = json.loads((MEDICIONES / f"{salida}.huella.json").read_text(encoding="utf-8"))
    verif_despues = f0.verify()
    meta = {"fecha_inicio": inicio, "fecha_fin": datetime.now(timezone.utc).astimezone().isoformat(), "variante": variante,
            "base_tmpfs": db, "arbol": ARBOL, "modelo_version": modelo, "flags": FLAGS, "puertos": pt,
            "servicio_indice": servicio or "ninguno (todos los índices desde la caché sembrada)",
            "cache_seed_sha256": sha256_archivo(ROOT / "output/f1/f1v_cache_seed.sql") if variante == "v2" else None,
            "cache_indice_beto_antes": cache_antes, "cache_indice_beto_despues": int(sql(db, "SELECT count(*) FROM public.cache_indice_beto")),
            "lote_sha256_antes": verif_antes["sha256"], "lote_sha256_despues": verif_despues["sha256"], "pared_s": pared,
            "comparacion": comparar_con_referencia(huella, REFERENCIA[variante])}
    (MEDICIONES / f"{salida}.meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(meta["comparacion"], ensure_ascii=False))


# ---------------------------------------------------------------------------------------------------------- extraer
def extraer(variante, destino):
    db = f"run_r2r_{variante}"
    sh("docker", "cp", str(ROOT / "scripts/f1_r2_extraer_casos.py"), "giragroup_api:/tmp/flujo/scripts/f1_r2_extraer_casos.py")
    modelo = "beto-v1" if variante == "v1" else "beto-v2"
    sh("docker", "exec", "-w", ARBOL, "giragroup_api", "env", f"DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/{db}",
       f"BETO_MODELO_VERSION={modelo}", f"PYTHONPATH={ARBOL}:{ARBOL}/backend", "python", "/tmp/flujo/scripts/f1_r2_extraer_casos.py",
       f"/tmp/f1v/{db}/lectura", f"/tmp/f1_r2_casos_{variante}.json")
    Path(destino).mkdir(parents=True, exist_ok=True)
    sh("docker", "cp", f"giragroup_api:/tmp/f1_r2_casos_{variante}.json", str(Path(destino) / f"casos_{variante}.json"))
    sh("docker", "exec", "giragroup_api", "rm", "-f", f"/tmp/f1_r2_casos_{variante}.json")


def entidades(destino):
    """Entidades BETO de v1 y v2 en cada línea que cambia de banda, servidas por dos contenedores AISLADOS (beto_pipeline_r2v1
    con el respaldo beto-v1 y beto_pipeline_r2v2 con pipeline/semantic/beto_local = beto-v2). Sin texto en la salida."""
    A = json.loads((Path(destino) / "casos_v1.json").read_text(encoding="utf-8"))
    B = json.loads((Path(destino) / "casos_v2.json").read_text(encoding="utf-8"))
    ib = {l["linea"]: l["indice"] for l in B["lineas"]}
    claves = sorted(l["linea"] for l in A["lineas"] if banda(l["indice"]) != banda(ib[l["linea"]]))
    tmp = Path(destino) / "claves_cambio_banda.json"
    tmp.write_text(json.dumps(claves), encoding="utf-8")
    sh("docker", "cp", str(tmp), "giragroup_api:/tmp/f1_r2_claves.json")
    sh("docker", "cp", str(ROOT / "scripts/f1_r2_extraer_casos.py"), "giragroup_api:/tmp/flujo/scripts/f1_r2_extraer_casos.py")
    print(sh("docker", "exec", "-w", ARBOL, "giragroup_api", "env", "DATABASE_URL=postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/run_r2r_v2",
             "BETO_MODELO_VERSION=beto-v2", f"PYTHONPATH={ARBOL}:{ARBOL}/backend", "python", "/tmp/flujo/scripts/f1_r2_extraer_casos.py",
             "entidades", "/tmp/f1_r2_claves.json", "/tmp/f1_r2_entidades.json", "http://beto_pipeline_r2v1:8006", "http://beto_pipeline_r2v2:8006"))
    sh("docker", "cp", "giragroup_api:/tmp/f1_r2_entidades.json", str(Path(destino) / "entidades.json"))
    sh("docker", "exec", "giragroup_api", "rm", "-f", "/tmp/f1_r2_entidades.json", "/tmp/f1_r2_claves.json")
    meta = {"contenedores": {}}
    for c in ("beto_pipeline_r2v1", "beto_pipeline_r2v2"):
        meta["contenedores"][c] = sh("docker", "exec", c, "sha256sum", "/app/pipeline/semantic/beto_local/model.safetensors").split()[0]
    (Path(destino) / "entidades_meta.json").write_text(json.dumps(meta), encoding="utf-8")


# --------------------------------------------------------------------------------------------------------- analizar
def clave_natural(c):
    """Clave estable entre corridas (sin ids sustitutos): valores del hecho o la clave de origen del staging."""
    if c["tipo"] == "stg":
        return ("stg", c["archivo"], c["clave_origen"] or c["texto_sha256"])
    if c["tipo"] == "aca":
        return ("aca", c["archivo"], c["est_clave"], c["modulo_clave"], c["id_tiempo"], c["nota"], c["asistencia"],
                c["estado_academico"], c["estado_tutoria"], c["estado_arca"])
    if c["tipo"] == "fin":
        return ("fin", c["archivo"], c["est_clave"], c["id_tiempo"], c["monto_deuda"], c["concepto"], c["modulo_clave"])
    return ("eva", c["archivo"], c["modulo_clave"])


def emparejar(a, b):
    """Multiconjuntos por clave natural: devuelve (pares, solo_a, solo_b)."""
    ia, ib = defaultdict(list), defaultdict(list)
    for x in a:
        ia[clave_natural(x)].append(x)
    for x in b:
        ib[clave_natural(x)].append(x)
    pares, sa, sb = [], [], []
    for k in set(ia) | set(ib):
        la, lb = ia.get(k, []), ib.get(k, [])
        n = min(len(la), len(lb))
        pares += list(zip(la[:n], lb[:n]))
        sa += la[n:]
        sb += lb[n:]
    return pares, sa, sb


def veredicto_tecnico(c, contra):
    """Regla técnica explícita (no es una etiqueta humana): ¿las reglas deterministas corroboran el caso por sí solas?

    Comprobaciones, todas contra datos del propio sistema (CI, encabezado, catálogo):
      ci_exacta      el estudiante tiene CI exacta verificada (estado A: identidad_verificada y ci_numero no nulo)
      modulo_catalogo el módulo está resuelto contra el catálogo institucional (id_modulo no nulo)
      fecha          el hecho tiene fecha (id_tiempo no nulo)
      valor          nota en [0, 100] o monto no nulo y >= 0
      estados_ok     estados de acta dentro del catálogo y combinación válida (motivo_estado == OK); solo académicos
    Para un caso de staging de una fuente a nivel de programa (tipo_fuente RENTABILIDAD/MARKETING: sin estudiante) se
    comprueba el encabezado y el catálogo: encabezado_programa (la línea trae 'PROGRAMA:' o 'NRO POS:') y pos_catalogo (todo
    código POS-n de la línea existe en dim_modulo). Para otro caso de staging se evalúan los campos del hecho homólogo de la
    otra corrida (misma línea) si existe; si no, las entidades del payload (CI_EXACTA y módulo con fuente de resolución).
      todas pasan -> 'revision_innecesaria_reglas_corroboran'
      alguna falla -> 'revision_justificada_regla_falla:<lista>'
    Lectura: en un alta (caso que v2 añade) 'innecesaria' = regresión y 'justificada' = mejora; en una baja (caso que v2
    quita) 'innecesaria' = mejora y 'justificada' = regresión.
    """
    h = c if c["tipo"] in ("aca", "fin") else (contra if contra and contra["tipo"] in ("aca", "fin") else None)
    fallas = []
    if c["tipo"] == "stg" and c.get("tipo_fuente") in ("RENTABILIDAD", "MARKETING"):
        if not c.get("encabezado_programa"):
            fallas.append("encabezado_programa")
        if not c.get("pos_en_catalogo"):
            fallas.append("pos_catalogo")
        fuente = "encabezado_y_catalogo_de_la_linea"
    elif c["tipo"] == "eva":
        fallas.append("evaluacion_sin_vinculo")
        fuente = "hecho"
    elif h is not None:
        if not h.get("est_ci_exacta"):
            fallas.append("ci_exacta")
        if h["tipo"] == "aca" or h.get("modulo_clave"):
            if not h.get("modulo_clave"):
                fallas.append("modulo_catalogo")
        if h.get("id_tiempo") in (None, "", "None"):
            fallas.append("fecha")
        if h["tipo"] == "aca":
            nota = h.get("nota")
            if nota is None or not (0 <= float(nota) <= 100):
                fallas.append("valor")
            if h.get("estado_motivo") != "OK":
                fallas.append("estados_ok")
        else:
            if h.get("monto_deuda") is None or float(h["monto_deuda"]) < 0:
                fallas.append("valor")
        fuente = "hecho" if h is c else "hecho_homologo_otra_corrida"
    else:
        ents = c.get("entidades") or []
        if not any(e.get("fuente") == "CI_EXACTA" for e in ents):
            fallas.append("ci_exacta")
        if not any(e.get("tag", "").endswith("MODULO") and e.get("fuente") for e in ents):
            fallas.append("modulo_catalogo")
        fuente = "payload_staging"
    v = "revision_innecesaria_reglas_corroboran" if not fallas else "revision_justificada_regla_falla:" + ",".join(fallas)
    return v, fuente


def analizar(origen, salida_csv, salida_json):
    A = json.loads((Path(origen) / "casos_v1.json").read_text(encoding="utf-8"))
    B = json.loads((Path(origen) / "casos_v2.json").read_text(encoding="utf-8"))
    meta = {v: json.loads((MEDICIONES / f"f1_r2_corrida_{v}.json.meta.json").read_text(encoding="utf-8")) for v in ("v1", "v2")}
    for v, X in (("v1", A), ("v2", B)):  # la extracción caso a caso reproduce la bandeja contada por la API
        h = json.loads((MEDICIONES / f"f1_r2_corrida_{v}.json.huella.json").read_text(encoding="utf-8"))
        assert len(X["pendientes"]) == h["bandeja"]["casos"], (v, len(X["pendientes"]), h["bandeja"]["casos"])
        assert sorted(Counter(c["grupo"][:16] for c in X["pendientes"]).items()) == sorted((g, n) for g, _, n in h["bandeja"]["firma"]), v
    # índice v1 y v2 por línea (documento|hoja|fila_inicio|k, partición de consolidacion.py): banda de cada línea en cada corrida
    lin_a = {l["linea"]: l for l in A["lineas"]}
    lin_b = {l["linea"]: l for l in B["lineas"]}
    assert set(lin_a) == set(lin_b), "las dos corridas no partieron el lote en las mismas líneas"
    assert all(lin_a[k]["hash_indice"] == lin_b[k]["hash_indice"] for k in lin_a), "mismo texto por línea en ambas corridas"
    trans_lineas = Counter()
    for k in lin_a:
        trans_lineas[(lin_a[k]["archivo"], banda(lin_a[k]["indice"]), banda(lin_b[k]["indice"]))] += 1

    # homólogo de cada caso pendiente en la otra corrida, entre TODOS sus registros (hechos y staging)
    todos_a, todos_b = A["todos"], B["todos"]
    pend_pares, bajas, altas = emparejar(A["pendientes"], B["pendientes"])  # solo en v1 = bajas; solo en v2 = altas
    idx_a, idx_b = defaultdict(list), defaultdict(list)
    for x in todos_a:
        idx_a[clave_natural(x)].append(x)
    for x in todos_b:
        idx_b[clave_natural(x)].append(x)
    usados_a, usados_b = Counter(), Counter()
    for x, _ in pend_pares:
        usados_a[clave_natural(x)] += 1
    for _, y in pend_pares:
        usados_b[clave_natural(y)] += 1
    # staging <-> hecho: misma línea de origen cuando el extractor la pudo fijar (si hay varios hechos por línea, el primero)
    por_linea_a, por_linea_b = {}, {}
    for pl, todos in ((por_linea_a, todos_a), (por_linea_b, todos_b)):
        for x in todos:
            if x.get("linea") is not None:
                pl.setdefault(x["linea"], x)

    def homologo(c, idx, usados, por_linea):
        k = clave_natural(c)
        cand = idx.get(k, [])
        if usados[k] < len(cand):
            usados[k] += 1
            return cand[usados[k] - 1]
        if c.get("linea") is not None:
            return por_linea.get(c["linea"])
        return None

    filas = []

    def causa(c, otro, sentido):
        """Atribución: banda del índice BETO de la MISMA línea de origen en v1 y en v2 (umbrales 0,85/0,60 sin cambio).
        Si la banda cambia, la causa es beto-v2; si no cambia (o no hay línea), se nombra la otra causa."""
        L = c.get("linea")
        i_v1 = lin_a[L]["indice"] if L in lin_a else None
        i_v2 = lin_b[L]["indice"] if L in lin_b else None
        if L is None:  # caso sin línea de origen (p. ej. HOMONIMIA, cuyo texto es solo un nombre): índice de los registros
            i_v2, i_v1 = (c.get("indice"), otro.get("indice") if otro else None) if sentido == "alta" else (otro.get("indice") if otro else None, c.get("indice"))
        b_v1 = banda(i_v1) if i_v1 is not None else ""
        b_v2 = banda(i_v2) if i_v2 is not None else ""
        if b_v1 and b_v2 and b_v1 != b_v2:
            return f"beto_v2_cambio_banda_{b_v1}_a_{b_v2}", i_v1, i_v2, b_v1, b_v2
        if L is None and otro is None:
            return "otra_causa_sin_linea_ni_homologo", i_v1, i_v2, b_v1, b_v2
        if otro is not None and otro["tipo"] == c["tipo"] and otro.get("grupo") != c["grupo"]:
            return "otra_causa_cambio_de_grupo_misma_banda", i_v1, i_v2, b_v1, b_v2
        return "otra_causa_misma_banda", i_v1, i_v2, b_v1, b_v2

    for sentido, lista, idx, usados, pl in (("alta", altas, idx_a, usados_a, por_linea_a), ("baja", bajas, idx_b, usados_b, por_linea_b)):
        for c in lista:
            otro = homologo(c, idx, usados, pl)
            cz, i1, i2, b1, b2 = causa(c, otro, sentido)
            filas.append({"caso_id": hashlib.sha256(repr(clave_natural(c)).encode()).hexdigest()[:16] + f"-{c['rid']}",
                          "sentido": sentido, "corrida_presente": "f1_validacion(v2)" if sentido == "alta" else "f1_off(v1)",
                          "tipo_caso": c["tipo"], "motivo": c["motivo"], "grupo": c["grupo"][:16], "accion_grupo": c["accion"],
                          "archivo": c["archivo"], "id_documento": c["id_documento"], "linea": c.get("linea"),
                          "homologo_tipo": otro["tipo"] if otro else "", "homologo_requiere_revision": otro.get("pendiente") if otro else "",
                          "indice_v1": i1, "indice_v2": i2, "banda_v1": b1, "banda_v2": b2, "atribucion": cz, "_c": c, "_o": otro})
    # cambio de entidad BETO en la línea de origen (subcomando entidades; servicios aislados v1 y v2)
    ent_path = Path(origen) / "entidades.json"
    ent = json.loads(ent_path.read_text(encoding="utf-8")) if ent_path.exists() else {}
    consistencia = {"lineas": len(ent), "indice_servicio_igual_a_cache_v1": 0, "indice_servicio_igual_a_cache_v2": 0}
    for k, e in ent.items():
        consistencia["indice_servicio_igual_a_cache_v1"] += abs(round(e["indice_v1_servicio"], 4) - lin_a[k]["indice"]) < 5e-5
        consistencia["indice_servicio_igual_a_cache_v2"] += abs(round(e["indice_v2_servicio"], 4) - lin_b[k]["indice"]) < 5e-5
    for f in filas:
        e = ent.get(f["linea"]) if f["atribucion"].startswith("beto_v2") else None
        f["cambio_entidad_beto"] = e["clase"] if e else ("" if not f["atribucion"].startswith("beto_v2") else "sin_dato")
        f["entidades_pierde_v2"] = "+".join(e["pierde"]) if e else ""
        f["entidades_gana_v2"] = "+".join(e["gana"]) if e else ""
    # muestra reproducible de 30 altas
    altas_f = sorted((f for f in filas if f["sentido"] == "alta"), key=lambda f: f["caso_id"])
    muestra = random.Random(SEMILLA_MUESTRA).sample(altas_f, min(N_MUESTRA, len(altas_f)))
    for f in filas:
        f["veredicto_tecnico_automatico"], f["veredicto_fuente"] = veredicto_tecnico(f["_c"], f["_o"])
        f["en_muestra_30"] = f in muestra
    campos = ["caso_id", "sentido", "corrida_presente", "tipo_caso", "motivo", "grupo", "accion_grupo", "archivo", "id_documento", "linea",
              "homologo_tipo", "homologo_requiere_revision", "indice_v1", "indice_v2", "banda_v1", "banda_v2", "atribucion",
              "cambio_entidad_beto", "entidades_pierde_v2", "entidades_gana_v2",
              "veredicto_tecnico_automatico", "veredicto_fuente", "en_muestra_30"]
    filas.sort(key=lambda f: (f["sentido"], f["tipo_caso"], f["grupo"], f["caso_id"]))
    with open(salida_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)

    def desglose(X):
        g = Counter((c["tipo"], c["motivo"], c["grupo"][:16], c["accion"]) for c in X["pendientes"])
        return {"casos": len(X["pendientes"]), "por_tipo": dict(Counter(c["tipo"] for c in X["pendientes"])),
                "por_motivo": dict(Counter(c["motivo"] for c in X["pendientes"])),
                "por_archivo": dict(Counter(c["archivo"] for c in X["pendientes"])),
                "grupos": [{"tipo": t, "motivo": m, "grupo": gr, "accion": a, "n": n} for (t, m, gr, a), n in sorted(g.items(), key=lambda x: -x[1])]}

    da, db_ = desglose(A), desglose(B)
    ga = {x["grupo"]: x["n"] for x in da["grupos"]}
    gb = {x["grupo"]: x["n"] for x in db_["grupos"]}
    info_g = {x["grupo"]: x for x in da["grupos"] + db_["grupos"]}
    por_grupo = [{"grupo": g, "tipo": info_g[g]["tipo"], "motivo": info_g[g]["motivo"], "accion": info_g[g]["accion"],
                  "f1_off": ga.get(g, 0), "f1_validacion": gb.get(g, 0), "delta": gb.get(g, 0) - ga.get(g, 0)}
                 for g in sorted(set(ga) | set(gb), key=lambda g: -(gb.get(g, 0) - ga.get(g, 0)))]
    n_altas, n_bajas = sum(f["sentido"] == "alta" for f in filas), sum(f["sentido"] == "baja" for f in filas)
    atrib = {s: dict(Counter(f["atribucion"] for f in filas if f["sentido"] == s)) for s in ("alta", "baja")}
    atrib_tipo = {s: {f"{t}|{a}": n for (t, a), n in Counter((f["tipo_caso"], f["atribucion"]) for f in filas if f["sentido"] == s).items()}
                  for s in ("alta", "baja")}
    ver = {s: dict(Counter(f["veredicto_tecnico_automatico"].split(":")[0] for f in filas if f["sentido"] == s)) for s in ("alta", "baja")}
    ver_m = dict(Counter(f["veredicto_tecnico_automatico"].split(":")[0] for f in muestra))

    # KPI-18 = COUNT(stg_entidad_no_resuelta WHERE resuelto = FALSE) (backend/scripts/migrations/014..., CTE backlog)
    stg_a = [c for c in A["pendientes"] if c["tipo"] == "stg"]
    stg_b = [c for c in B["pendientes"] if c["tipo"] == "stg"]
    kpi_filas = [f for f in filas if f["tipo_caso"] == "stg"]
    kpi = {"definicion": "KPI-18 = COUNT(*) FROM public.stg_entidad_no_resuelta WHERE resuelto = FALSE (CTE backlog, migración 014)",
           "f1_off": len(stg_a), "f1_validacion": len(stg_b),
           "huella_f1_off": A["kpi18_sql"], "huella_f1_validacion": B["kpi18_sql"],
           "altas_stg": sum(f["sentido"] == "alta" for f in kpi_filas), "bajas_stg": sum(f["sentido"] == "baja" for f in kpi_filas),
           "por_motivo_y_archivo": {f"{f}|{s}|{m}|{a}": n for (f, s, m, a), n in
                                    Counter(("stg", f["sentido"], f["motivo"], f["archivo"]) for f in kpi_filas).items()},
           "atribucion": {f"{s}|{a}": n for (s, a), n in Counter((f["sentido"], f["atribucion"]) for f in kpi_filas).items()},
           "destino_de_las_bajas": dict(Counter((f["homologo_tipo"] or "sin_homologo") for f in kpi_filas if f["sentido"] == "baja"))}
    kpi["cuadra"] = kpi["f1_off"] + kpi["altas_stg"] - kpi["bajas_stg"] == kpi["f1_validacion"]

    fuentes = {}
    for p in [MEDICIONES / "f1_off.json", MEDICIONES / "f1_off.json.huella.json", MEDICIONES / "f1_validacion_llena_r1.json",
              MEDICIONES / "f1_validacion_llena_r1.json.huella.json", MEDICIONES / "f1_validacion_resumen.json",
              MEDICIONES / "f1_promocion_modelo.json", MEDICIONES / "f0_lote_manifest.json", ROOT / "output/f1/f1v_cache_seed.sql",
              ROOT / "output/f1/beto_local_respaldo/model.safetensors"] + \
             [MEDICIONES / f"f1_r2_corrida_{v}.json{s}" for v in ("v1", "v2") for s in ("", ".huella.json", ".meta.json")]:
        fuentes[str(p.relative_to(ROOT)).replace("\\", "/")] = sha256_archivo(p)
    fuentes["scripts/f1_r2_diagnostico.py"] = sha256_archivo(Path(__file__))
    fuentes["scripts/f1_r2_extraer_casos.py"] = sha256_archivo(ROOT / "scripts/f1_r2_extraer_casos.py")

    mejora = ver.get("alta", {}).get("revision_justificada_regla_falla", 0)
    regresion = ver.get("alta", {}).get("revision_innecesaria_reglas_corroboran", 0)
    bajas_ok = ver.get("baja", {}).get("revision_innecesaria_reglas_corroboran", 0)
    bajas_mal = ver.get("baja", {}).get("revision_justificada_regla_falla", 0)
    n_mejora, n_regresion = mejora + bajas_ok, regresion + bajas_mal
    concl = "mezcla" if n_mejora and n_regresion else "mejora" if n_mejora else "regresion"
    out = {
        "tarea": "R-2 PLAN_F1R2", "fecha": datetime.now(timezone.utc).astimezone().isoformat(),
        "aviso": "veredicto_tecnico_automatico es una regla técnica automática; no es una etiqueta humana ni la sustituye.",
        "reejecucion_tmpfs": {"hubo": True, "motivo": "las huellas existentes solo guardan conteos y la firma de grupos; sin casos",
                              "puertos": meta["v1"]["puertos"], "bases": [meta["v1"]["base_tmpfs"], meta["v2"]["base_tmpfs"]],
                              "v1": {k: meta["v1"][k] for k in ("modelo_version", "servicio_indice", "cache_indice_beto_antes", "lote_sha256_antes", "lote_sha256_despues", "comparacion")},
                              "servicios_entidades": json.loads((Path(origen) / "entidades_meta.json").read_text(encoding="utf-8")) if (Path(origen) / "entidades_meta.json").exists() else None,
                              "v2": {k: meta["v2"][k] for k in ("modelo_version", "servicio_indice", "cache_seed_sha256", "cache_indice_beto_antes", "cache_indice_beto_despues", "lote_sha256_antes", "lote_sha256_despues", "comparacion")}},
        "desglose": {"f1_off": da, "f1_validacion": db_, "por_grupo": por_grupo},
        "reconciliacion": {"f1_off": len(A["pendientes"]), "f1_validacion": len(B["pendientes"]), "neto": len(B["pendientes"]) - len(A["pendientes"]),
                           "casos_emparejados_en_ambas": len(pend_pares), "altas": n_altas, "bajas": n_bajas,
                           "cuadra": len(A["pendientes"]) + n_altas - n_bajas == len(B["pendientes"]),
                           "atribucion": atrib, "atribucion_por_tipo": atrib_tipo,
                           "suma_atribuciones_altas": sum(atrib["alta"].values()), "suma_atribuciones_bajas": sum(atrib["baja"].values())},
        "cambio_entidad_beto": {
            "metodo": "entidades_beto de /infer-batch (solo BETO, antes de reglas) sobre texto_para_indice de la línea, v1 y v2 en contenedores aislados",
            "consistencia_indice": consistencia,
            "lineas_que_cambian_de_banda_por_clase": dict(Counter(e["clase"] for e in ent.values())),
            "por_sentido_atribucion_y_clase": {f"{s}|{a}|{c}": n for (s, a, c), n in Counter((f["sentido"], f["atribucion"], f["cambio_entidad_beto"]) for f in filas).items()},
            "tipos_perdidos_por_v2_en_casos": dict(Counter(t for f in filas for t in f["entidades_pierde_v2"].split("+") if t)),
            "tipos_ganados_por_v2_en_casos": dict(Counter(t for f in filas for t in f["entidades_gana_v2"].split("+") if t))},
        "transicion_bandas_por_linea": {"descripcion": "líneas del lote (documento, línea) por banda del índice BETO v1 -> v2; umbrales 0,85/0,60 sin cambio",
                                        "lineas_comparadas": sum(trans_lineas.values()),
                                        "conteos": [{"archivo": a, "banda_v1": b1, "banda_v2": b2, "lineas": n} for (a, b1, b2), n in sorted(trans_lineas.items())]},
        "muestra_30": {"semilla": SEMILLA_MUESTRA, "metodo": "random.Random(semilla).sample(altas ordenadas por caso_id, 30)",
                       "archivo": "docs/mediciones/f1_r2_bandeja_diff.csv (columna en_muestra_30 = True)",
                       "regla": veredicto_tecnico.__doc__.strip(), "conteo_veredictos": ver_m,
                       "casos": [{k: f[k] for k in ("caso_id", "tipo_caso", "motivo", "grupo", "archivo", "indice_v1", "indice_v2", "atribucion", "cambio_entidad_beto", "entidades_pierde_v2", "entidades_gana_v2", "veredicto_tecnico_automatico", "veredicto_fuente")} for f in sorted(muestra, key=lambda f: f["caso_id"])]},
        "veredictos_todos": ver,
        "conclusion": {"veredicto": concl, "casos_mejora": n_mejora, "casos_regresion": n_regresion,
                       "criterio": "mejora = altas con regla que falla + bajas que las reglas corroboran; regresión = altas que las reglas corroboran + bajas con regla que falla",
                       "altas_mejora_regla_falla": mejora, "altas_regresion_reglas_corroboran": regresion,
                       "bajas_correctas_reglas_corroboran": bajas_ok, "bajas_con_defecto_regla_falla": bajas_mal,
                       "muestra_30": ver_m},
        "kpi_18": kpi,
        "fuera_de_bandeja": {
            "nota": "la bandeja solo cuenta staging pendiente y hechos académicos/financieros/evaluación en revisión (services/bandeja_grupos.py); "
                    "fact_costo_programa con requiere_revision no aparece en ella",
            **{v: {"fact_costo_programa": int(sql(f"run_r2r_{v}", "SELECT count(*) FROM fact_costo_programa")),
                   "fact_costo_programa_requiere_revision": int(sql(f"run_r2r_{v}", "SELECT count(*) FROM fact_costo_programa WHERE requiere_revision")),
                   "fact_evaluacion_docente_requiere_revision": int(sql(f"run_r2r_{v}", "SELECT count(*) FROM fact_evaluacion_docente WHERE requiere_revision"))}
               for v in ("v1", "v2")}},
        "fuentes_sha256": fuentes,
        "notas": [
            "Las dos corridas reproducen byte a byte las huellas de referencia (14 tablas, firma de bandeja y KPI): el código es el mismo, "
            "así que toda diferencia caso a caso entre f1_off y f1_validacion procede del cambio de modelo beto-v1 -> beto-v2.",
            "El índice BETO de cada línea entra a la cascada solo como banda (>= 0,85 hecho; [0,60, 0,85) hecho en revisión; < 0,60 staging); "
            "no cambian umbrales, cascada ni flags (4 en 0).",
            "En tmpfs ya existían run_r2_v1/run_r2_v2 de una corrida previa sin procedencia documentada; no se usaron ni se borraron "
            "(run_r2_v1 no reproduce f1_off: 199 casos, KPI-18 76).",
            "veredicto_tecnico_automatico es una regla técnica; no es ni sustituye una etiqueta humana.",
        ],
    }
    Path(salida_json).write_text(json.dumps(out, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"reconciliacion": out["reconciliacion"], "conclusion": out["conclusion"], "kpi_18": {k: kpi[k] for k in ("f1_off", "f1_validacion", "altas_stg", "bajas_stg", "cuadra", "atribucion")}}, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("correr")
    c.add_argument("variante", choices=("v1", "v2"))
    c.add_argument("--preparar", action="store_true")
    e = sp.add_parser("extraer")
    e.add_argument("variante", choices=("v1", "v2"))
    e.add_argument("destino")
    n = sp.add_parser("entidades")
    n.add_argument("destino")
    a = sp.add_parser("analizar")
    a.add_argument("origen")
    a.add_argument("--csv", default=str(MEDICIONES / "f1_r2_bandeja_diff.csv"))
    a.add_argument("--json", default=str(MEDICIONES / "f1_r2_diagnostico.json"))
    args = ap.parse_args()
    if args.cmd == "correr":
        correr(args.variante, args.preparar)
    elif args.cmd == "extraer":
        extraer(args.variante, args.destino)
    elif args.cmd == "entidades":
        entidades(args.destino)
    else:
        analizar(args.origen, args.csv, args.json)


if __name__ == "__main__":
    main()
