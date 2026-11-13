"""El catálogo de personas preparado una sola vez debe dar exactamente lo mismo que la resolución original (que normalizaba
cada persona en cada llamada). Se compara contra una copia literal del algoritmo anterior sobre nombres variados."""
import random

from rapidfuzz import fuzz

from pipeline.normalization import person_resolver as pr


def _candidatos_original(personas, cand, toks_c, umbral):
    apellido = toks_c[-1]
    out = []
    for p in personas:
        canon = pr.quitar_titulos(p["nombre"])
        toks_p = pr._tokens(canon)
        if len(toks_p) < 2:
            continue
        if apellido not in toks_p[1:] and toks_c[0] not in toks_p[1:]:
            continue
        if len(set(toks_c) & set(toks_p)) < 2:
            continue
        ts = fuzz.token_sort_ratio(cand, canon)
        score = max(ts, fuzz.token_set_ratio(cand, canon)) / 100.0
        if score >= umbral:
            out.append((score, ts, p))
    return out


def _resolver_original(nombre, ci, personas, contexto=None, ctx_modulo=None, umbral=pr.UMBRAL_PERSONA):
    if pr.es_correo(nombre):
        return {"resultado": None, "motivo": "correo", "nivel": None}
    ci_n = pr._norm_ci(ci)
    if len(ci_n) >= 5:
        for p in personas:
            if pr._norm_ci(p.get("ci")) == ci_n:
                return {"resultado": {"id": p["id"], "nombre": p["nombre"], "score": 1.0, "fuente": "CI_EXACTA"}, "motivo": None, "nivel": "CI"}
    cand = pr.quitar_titulos(nombre or "")
    toks_c = pr._tokens(cand)
    if len(toks_c) < 2:
        return {"resultado": None, "motivo": "sin_candidatos", "nivel": None}
    ctx_mod = [c for c in (ctx_modulo or []) if c]
    ctx_prog = [c for c in (contexto or []) if c]
    niveles = []
    if ctx_mod:
        niveles.append(("MODULO", [p for p in personas if pr._coincide_contexto(p.get("modulos") or [], ctx_mod)]))
    if ctx_prog:
        niveles.append(("PROGRAMA", [p for p in personas if pr._coincide_contexto(p.get("contextos") or [], ctx_prog)]))
    niveles.append(("DIMENSION", personas))
    empate = False
    for nivel, pool in niveles:
        cands = _candidatos_original(pool, cand, toks_c, umbral)
        if not cands:
            continue
        cands.sort(key=lambda x: (x[0], x[1]), reverse=True)
        if len(cands) > 1 and (cands[0][0], cands[0][1]) == (cands[1][0], cands[1][1]) and cands[0][2]["id"] != cands[1][2]["id"]:
            empate = True
            break
        sc, _, p = cands[0]
        return {"resultado": {"id": p["id"], "nombre": p["nombre"], "score": round(sc, 4), "fuente": "FUZZY"}, "motivo": None, "nivel": nivel}
    return {"resultado": None, "motivo": "empate" if empate else "sin_candidatos", "nivel": None}


NOMBRES = ["María José Pérez Gómez", "Lic. Juan Carlos Rojas Noya", "Ana Lucía de la Cruz", "Pedro Antonio Quispe Mamani",
           "Dra. Carla Fernández Salazar", "Luis Alberto Vargas Ríos", "José Luis Mamani Quispe", "Rosa Elena Pérez Gómez",
           "Ing. Marco Antonio Flores", "Daniela Alejandra Suárez", "Jorge Rojas", "Carmen San Martín López"]
CONTEXTOS = ["Maestría en Gestión de Datos", "Diplomado en Ciberseguridad", "POS-5887", None]


def _catalogo(semilla=7):
    rnd = random.Random(semilla)
    personas = []
    for i in range(300):
        base = rnd.choice(NOMBRES)
        variante = base if rnd.random() < 0.5 else " ".join(reversed(base.split()))
        personas.append({"id": i + 1, "nombre": variante, "ci": f"{1000000 + i}" if rnd.random() < 0.6 else None,
                         "contextos": [c for c in rnd.sample(CONTEXTOS, 2) if c], "modulos": [rnd.choice(["Módulo 1", "Módulo 2", None])]})
    personas[0]["modulos"] = [None]
    return personas


def test_preparado_equivale_al_algoritmo_original():
    personas = _catalogo()
    rnd = random.Random(11)
    consultas = []
    for base in NOMBRES:
        for mod in (base, base.lower(), base.replace("é", "e"), "Mgr. " + base, " ".join(base.split()[1:]) or base, base + " Extra"):
            consultas.append((mod, None, rnd.choice(CONTEXTOS), None))
    consultas += [("cualquiera", "1000005", None, None), ("Pedro Quispe", "1.000.010", None, None), ("juan@correo.com", None, None, None),
                  ("Solo", None, None, None), ("Jorge Rojas", None, "Diplomado en Ciberseguridad", "Módulo 2")]
    for nombre, ci, ctx, ctx_mod in consultas:
        esperado = _resolver_original(nombre, ci, personas, contexto=[ctx] if ctx else None, ctx_modulo=[ctx_mod] if ctx_mod else None)
        obtenido = pr.resolver_persona_detalle(nombre, ci, personas, contexto=[ctx] if ctx else None, ctx_modulo=[ctx_mod] if ctx_mod else None)
        assert obtenido == esperado, (nombre, ci, ctx, ctx_mod)


def test_el_catalogo_se_prepara_una_vez_y_se_rehace_si_cambia():
    personas = _catalogo(3)
    prep1 = pr._preparar(personas)
    assert pr._preparar(personas) is prep1
    personas.append({"id": 999, "nombre": "Nuevo Integrante Pérez", "ci": None})
    prep2 = pr._preparar(personas)
    assert prep2 is not prep1 and len(prep2) == len(personas)
    assert pr.resolver_persona("Nuevo Integrante Pérez", None, personas)["id"] == 999
