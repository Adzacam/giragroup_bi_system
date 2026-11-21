"""L8-0 (solo lectura): clasifica las filas sin estudiante de stg_entidad_no_resuelta.

Consulta solo la copia efimera adw_pg_tmpfs. Imprime unicamente agregados (sin CI,
nombres, correos ni payloads). Uso: python adw_l8_0_filas_sin_estudiante.py
"""
import csv
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CARTERA = RAIZ / "docs" / "mediciones" / "adw_l0_cartera.csv"
MOTIVOS = ("FILA_FINANCIERA_SIN_ESTUDIANTE", "FILA_ACADEMICA_SIN_ESTUDIANTE")
NOMBRE_LABEL = re.compile(r"^(nombres?|nombre completo|estudiante|alumno|apellidos?|razon social|docente)$")
CI_LABEL = re.compile(r"\b(ci|cedula|documento|nit|codigo estudiante)\b")
CI_VALOR = re.compile(r"^\d{5,10}(\s*[A-Z]{2})?$")
TOTAL = re.compile(r"\b(sub)?total(es)?\b|encabezado|cabecera", re.I)


def norm(texto):
    t = unicodedata.normalize("NFD", str(texto).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", t).split())


def psql_json(sql):
    salida = subprocess.run(
        ["docker", "exec", "adw_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", "giragroup_db", "-At", "-c", sql],
        capture_output=True, check=True,
    ).stdout.decode("utf-8")
    return [json.loads(l) for l in salida.splitlines() if l.strip()]


def en_lista(motivos):
    return ",".join("'" + m + "'" for m in motivos)


def parsear(raw):
    campos = []
    for parte in (raw or "").split("|"):
        parte = parte.strip()
        if not parte:
            continue
        if ":" in parte:
            etiqueta, valor = parte.split(":", 1)
            campos.append((etiqueta.strip(), valor.strip()))
        else:
            campos.append((None, parte))
    return campos


def digitos(valor):
    return re.sub(r"\D", "", valor or "")


def monto(valor):
    s = re.sub(r"[^\d,.\-]", "", valor or "")
    if s.count(",") and s.count("."):
        s = s.replace(".", "").replace(",", ".")
    elif s.count(","):
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def main():
    filas = psql_json(
        "select json_build_object('id', id_staging, 'motivo', motivo, 'doc', id_documento, "
        "'raw', payload_json->>'raw_line', 'tipo', payload_json->>'tipo_fuente', "
        "'descarte', payload_json->>'descarte') from public.stg_entidad_no_resuelta "
        "where motivo in (" + en_lista(MOTIVOS) + ") order by id_staging"
    )
    alumnos = psql_json(
        "select json_build_object('nombre', nombre_completo, 'ci', ci, 'ci_numero', ci_numero) "
        "from public.dim_estudiante where deprecado = false"
    )
    ci_dim = set()
    nombres_dim = set()
    for a in alumnos:
        for c in (a["ci"], a["ci_numero"]):
            if c and digitos(c):
                ci_dim.add(digitos(c))
        if a["nombre"]:
            nombres_dim.add(norm(a["nombre"]))

    print("Filas en staging: %d | estudiantes en dim_estudiante: %d" % (len(filas), len(alumnos)))
    print("Conteo por motivo:", dict(Counter(f["motivo"] for f in filas)))
    print("Descarte / tipo_fuente:", dict(Counter((f["motivo"], f["descarte"], f["tipo"]) for f in filas)))

    clases = defaultdict(list)
    for f in filas:
        campos = parsear(f["raw"])
        etiquetas = [e for e, _ in campos if e]
        ci_hallado = []
        nombres = []
        for etiqueta, valor in campos:
            if etiqueta and CI_LABEL.search(norm(etiqueta)) and digitos(valor):
                ci_hallado.append(digitos(valor))
            elif not etiqueta and CI_VALOR.match(valor):
                ci_hallado.append(digitos(valor))
            if etiqueta and NOMBRE_LABEL.match(norm(etiqueta)) and valor:
                nombres.append(norm(valor))
        ci_hallado = [c for c in ci_hallado if len(c) >= 5]
        if not etiquetas or TOTAL.search(f["raw"] or "") or len(campos) <= 1:
            clase = "D"
        elif ci_hallado and not any(c in ci_dim for c in ci_hallado):
            clase = "C"
        elif ci_hallado:
            clase = "E"
        elif nombres:
            clase = "B"
        else:
            clase = "A"
        clases[(f["motivo"], clase)].append({"f": f, "campos": campos, "ci": ci_hallado, "nombres": nombres})

    print("\nClasificacion por motivo y clase:")
    for motivo in MOTIVOS:
        total = sum(len(v) for (m, _), v in clases.items() if m == motivo)
        for clase in "ABCDE":
            n = len(clases.get((motivo, clase), []))
            print("  %s %s: %d (%.1f %%)" % (motivo, clase, n, n / total * 100 if total else 0))
        print("  %s total: %d" % (motivo, total))

    c_rows = [r for m in MOTIVOS for r in clases.get((m, "C"), [])]
    b_rows = [r for m in MOTIVOS for r in clases.get((m, "B"), [])]
    print("\nClase C: filas %d | rescatables por nombre exacto normalizado: %d" % (
        len(c_rows), sum(1 for r in c_rows if any(n in nombres_dim for n in r["nombres"]))))
    print("Clase B: filas %d | con nombre exacto en dim_estudiante: %d" % (
        len(b_rows), sum(1 for r in b_rows if any(n in nombres_dim for n in r["nombres"]))))

    print("\nFinancieras (doc 36):")
    fin = [f for f in filas if f["motivo"] == "FILA_FINANCIERA_SIN_ESTUDIANTE"]
    etiquetas_fin = Counter()
    for f in fin:
        for e, _ in parsear(f["raw"]):
            if e:
                etiquetas_fin[norm(e)] += 1
    for pat in ("monto", "deuda", "pag", "cuota", "saldo", "mora", "impag", "cartera", "gestion", "factura", "concepto"):
        print("  etiquetas con '%s': %s" % (pat, sorted(k for k in etiquetas_fin if pat in k) or "ninguna"))
    montos = []
    for f in fin:
        for e, v in parsear(f["raw"]):
            if e and "monto" in norm(e):
                m = monto(v)
                if m is not None:
                    montos.append(m)
    suma = sum(montos)
    print("  filas con monto Bs: %d | suma Bs: %.2f" % (len(montos), suma))
    if CARTERA.exists():
        with CARTERA.open(encoding="utf-8") as fh:
            deuda_total = sum(float(r["deuda_bs"]) for r in csv.DictReader(fh))
        print("  deuda_bs total cartera (adw_l0_cartera.csv): %.2f" % deuda_total)
        print("  monto financieras / deuda cartera: %.4f %%" % (suma / deuda_total * 100))

    print("\nAcademicas (doc 43):")
    aca = [f for f in filas if f["motivo"] == "FILA_ACADEMICA_SIN_ESTUDIANTE"]
    anios = Counter()
    programas = set()
    estados = Counter()
    notas = 0
    for f in aca:
        for e, v in parsear(f["raw"]):
            if not e:
                continue
            k = norm(e)
            if k == "ano ibp":
                anios[v] += 1
            if k == "nombre del programa" and v:
                programas.add(norm(v))
            if k.startswith("estado"):
                estados[(k, norm(v))] += 1
            if re.search(r"nota|calific|promedio|puntaj", k):
                notas += 1
    print("  distribucion AÑO IBP: %s" % (dict(anios) or "no determinado"))
    print("  programas distintos (nombres no mostrados): %d" % len(programas))
    print("  campos de nota o calificacion: %d -> %s" % (notas, "no determinado" if notas == 0 else "ver conteo"))
    print("  estados academicos (etiqueta, valor): %s" % (dict(estados) or "ninguno"))

    print("\nSubtipos de clase A (sin CI ni nombre):")
    a_rows = [r for m in MOTIVOS for r in clases.get((m, "A"), [])]
    es_estado = lambda r: any(e and re.match(r"estado (academico|reprobado|arca)", norm(e)) for e, _ in r["campos"])
    es_programa = lambda r: any(e and re.search(r"programa|curso|pos|inscrit|diplom|modulo|ibp", norm(e)) for e, _ in r["campos"])
    print("  A con estado academico individual: %d" % sum(1 for r in a_rows if es_estado(r)))
    print("  A de catalogo de programas/cursos (sin estado individual): %d" % sum(1 for r in a_rows if not es_estado(r) and es_programa(r)))
    print("  A restantes: %d" % sum(1 for r in a_rows if not es_estado(r) and not es_programa(r)))

    print("\nFilas con CI existente en dim_estudiante (clase E), por motivo:")
    for m in MOTIVOS:
        e_rows = clases.get((m, "E"), [])
        print("  %s: %d" % (m, len(e_rows)))

    print("\nFinancieras con monto Bs: clase y campos de pago presentes (sin valores):")
    for r in [r for r in fin if any(e and "monto" in norm(e) for e, _ in parsear(r["raw"]))]:
        clase = next(c for (m, c), v in clases.items() if any(x["f"]["id"] == r["id"] for x in v))
        etq = sorted({norm(e) for e, _ in parsear(r["raw"]) if e})
        print("  clase %s | etiquetas: %d | ci_en_fila: %d | canal_pago: %s" % (
            clase, len(etq), len(next(x for x in clases[(r["motivo"], clase)] if x["f"]["id"] == r["id"])["ci"]),
            any("canal de pago" in k for k in etq)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
