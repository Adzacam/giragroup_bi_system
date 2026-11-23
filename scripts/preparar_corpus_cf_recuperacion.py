"""Aumenta CF-L2 con formatos institucionales y un dev de formatos independiente."""
import argparse
import csv
import json
import random
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from preparar_corpus_robusto import (
    ARCHIVOS_CORPUS, BASE_DIR, ETIQUETAS_CF, MAX_TOKENS_CF, MODELO_CF,
    leer_jsonl, normalizar_cf, registro_cf, reglas_rechazo_cf, sha256_archivo,
    verificar_cf, escribir_jsonl,
)
from backend.services.modulo_validador import validar_nombre_modulo


FAMILIA_MARCADOR = re.compile(
    r"\bPOS\s*[-:]?\s*\d+\b|\bV\s*\.?\s*\d+\b|"
    r"\b\d+\s*(?:RA|DA|TA|RO|DO|TO)\b\.?|[-–—]\s*NAL\b|\bedici[oó]n\b",
    re.IGNORECASE,
)
FORMATOS = ("traspuesto", "membrete", "campos_intercalados", "narrativo", "columnas_sin_nombre", "exportacion")


def titulo_familia(texto):
    return " ".join(FAMILIA_MARCADOR.sub("", texto).split()).strip(" :-–—.,;|")


def consultar(inventario, neg):
    """Solo lee las filas institucionales de CF-L0, sin dependencias del conjunto reservado."""
    with inventario.open(encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))
    catalogo, aliases = {}, {}
    for fila in filas:
        if fila["tipo"] != "cat_programa":
            continue
        can = titulo_familia(fila["texto"])
        clave = normalizar_cf(can)
        if not clave:
            continue
        catalogo[fila["codigo"]] = (clave, can, fila["detalle"].rsplit("version=", 1)[-1])
        for etiqueta in (can, fila["texto"], fila["referencia"]):
            if etiqueta:
                aliases[normalizar_cf(etiqueta)] = clave
    for fila in filas:
        if fila["tipo"] == "dim_modulo" and fila["categoria"].startswith("titulo_oferta"):
            clave = normalizar_cf(titulo_familia(fila["texto"]))
            if fila["codigo"] in catalogo and clave:
                aliases[normalizar_cf(fila["texto"])] = catalogo[fila["codigo"]][0]
    casos = defaultdict(list)
    for fila in filas:
        if fila["tipo"] != "cat_modulo_maestro" or fila["codigo"] not in catalogo:
            continue
        codigo = fila["codigo"]
        familia, programa, version = catalogo[codigo]
        modulo = " ".join(fila["texto"].split())
        numero = fila["detalle"].removeprefix("nro_modulo=")
        if not numero.isdecimal() or not validar_nombre_modulo(modulo, reglas_override=neg)[0]:
            continue
        if normalizar_cf(modulo) != familia:
            casos[familia].append((programa, modulo, numero, codigo, version))
    return casos, aliases


def familias_en(filas, aliases):
    return {
        aliases.get(normalizar_cf(s["val"]), normalizar_cf(titulo_familia(s["val"])))
        for r in filas for s in r["spans"] if s["tipo"] == "PROGRAMA"
    }


def modulos_en(filas):
    return {normalizar_cf(s["val"]) for r in filas for s in r["spans"] if s["tipo"] == "MODULO"}


def construir(caso, formato, perfil):
    programa, modulo, numero, codigo, version = caso
    if perfil == 1:
        return registro_cf((f"{codigo} / oferta registrada \n", None), (programa, "PROGRAMA"),
                           (" \nAsignatura: POR DEFINIR", None))
    if perfil == 2:
        return registro_cf(("Carga: ACTA | campo 06\n", None), (modulo, "MODULO"),
                           (f"\nORDEN: {numero} | OFERTA SIN DATO", None))
    if perfil == 3:
        return registro_cf((f"Registro {codigo} | Programa: POR DEFINIR | Módulo: SIN DATO | Estado: Revisión", None))
    p, m = (programa, "PROGRAMA"), (modulo, "MODULO")
    if formato == "traspuesto":
        return registro_cf(("Oferta     | Asignatura     | Orden\n", None), p, ("\t|\t", None), m, (f"\t|\t{numero}", None))
    if formato == "membrete":
        return registro_cf((f"ACTA DE REGISTRO\nFicha {codigo} — versión {version}\n", None), p,
                           (f"\n••• {numero} •••\n", None), m, ("\nActa validada", None))
    if formato == "campos_intercalados":
        return registro_cf(("Campo E→ ", None), m, (f" | Estado: COMPLETO\\{codigo} | campo B→ ", None), p)
    if formato == "narrativo":
        return registro_cf(("Se verificó la asignatura ", None), m, (" dentro de la oferta ", None), p,
                           (f"; consta en ficha {codigo}.", None))
    if formato == "columnas_sin_nombre":
        return registro_cf(("Unnamed: 2: Aprobado | 0 = ", None), p, (" /// 4 = ", None), m,
                           (f" | N° {numero}", None))
    return registro_cf((f"Ref.{numero} || ", None), (modulo.upper(), "MODULO"),
                       (f" || [{codigo}] || ", None), (programa.lower(), "PROGRAMA"))


def muestra(pool, familias, cantidad, rng, previos, tokenizer):
    fichas = [(f, caso) for f in sorted(familias) for caso in pool[f]]
    rng.shuffle(fichas)
    candidatos = []
    for paso in range(4):
        for i, (familia, caso) in enumerate(fichas):
            formato = FORMATOS[(i + paso) % len(FORMATOS)]
            perfil = {0: 1, 1: 2, 2: 3}.get((i + paso) % 13, 0)
            candidatos.append((familia, formato, perfil, construir(caso, formato, perfil)))
    aceptados = []
    for inicio in range(0, len(candidatos), 128):
        lote = candidatos[inicio:inicio + 128]
        longitudes = verificar_cf([r for _, _, _, r in lote], tokenizer, "recuperacion")
        for (familia, formato, perfil, fila), longitud in zip(lote, longitudes, strict=True):
            clave = normalizar_cf(fila["texto"])
            if clave in previos or longitud > MAX_TOKENS_CF:
                continue
            previos.add(clave)
            aceptados.append((familia, formato, perfil, fila, longitud))
            if len(aceptados) == cantidad:
                return aceptados
    raise ValueError(f"Solo {len(aceptados)} ejemplos elegibles de {cantidad} requeridos")


def main():
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=BASE_DIR / "output/cf/corpus_v2")
    parser.add_argument("--inventario", type=Path, default=BASE_DIR / "docs/mediciones/cf_l0_familias_residuales.csv")
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    meta_base = json.loads((args.base / "corpus_meta.json").read_text(encoding="utf-8"))
    for nombre in ARCHIVOS_CORPUS:
        if sha256_archivo(args.base / nombre) != meta_base["sha256"][nombre]:
            raise ValueError("El corpus CF-L2 base difiere de su manifiesto")
    train, dev = (leer_jsonl(args.base / f) for f in ARCHIVOS_CORPUS[:2])
    pool, aliases = consultar(args.inventario, reglas_rechazo_cf())
    familias_base = familias_en(train, aliases)
    opciones = sorted(set(pool) - familias_base - familias_en(dev, aliases))
    rng = random.Random(42)
    rng.shuffle(opciones)
    corte = round(len(opciones) * 0.50)
    tokenizer = AutoTokenizer.from_pretrained(MODELO_CF, local_files_only=True)
    previos = {normalizar_cf(r["texto"]) for r in train + dev}
    modulos_base = modulos_en(train)
    pool_dev = {f: [caso for caso in pool[f] if normalizar_cf(caso[1]) not in modulos_base] for f in opciones[:corte]}
    formatos_dev = muestra(pool_dev, opciones[:corte], 144, rng, previos, tokenizer)
    modulos_dev = modulos_en([r for _, _, _, r, _ in formatos_dev])
    pool_train = {f: [caso for caso in pool[f] if normalizar_cf(caso[1]) not in modulos_dev]
                  for f in set(pool) - set(opciones[:corte])}
    formatos_train = muestra(pool_train, pool_train, 300, rng, previos, tokenizer)
    familias_train = familias_base | {f for f, *_ in formatos_train}
    familias_dev = {f for f, *_ in formatos_dev}
    if familias_train & familias_dev:
        raise ValueError("Familias sintéticas de dev presentes en train")
    aumento = [r for _, _, _, r, _ in formatos_train]
    dev_formatos = [r for _, _, _, r, _ in formatos_dev]
    if any(s["tipo"].startswith("PER_") for r in aumento + dev_formatos for s in r["spans"]):
        raise ValueError("Los aumentos institucionales deben quedar sin personas anotadas")
    train.extend(aumento)
    if modulos_dev & modulos_en(train):
        raise ValueError("Asignaturas sintéticas de dev presentes en train")
    rng.shuffle(train)
    args.salida.mkdir(parents=True, exist_ok=False)
    escribir_jsonl(args.salida / ARCHIVOS_CORPUS[0], train)
    for nombre in ARCHIVOS_CORPUS[1:]:
        shutil.copyfile(args.base / nombre, args.salida / nombre)
    archivo_dev = "dev_layout_cf.jsonl"
    escribir_jsonl(args.salida / archivo_dev, dev_formatos)
    meta = {
        "cohorte": "CF-L2b recuperación independiente", "semilla": 42,
        "procedencia_sha256": {
            "cf_l0_familias_residuales.csv": sha256_archivo(args.inventario),
            "preparar_corpus_cf_recuperacion.py": sha256_archivo(Path(__file__)),
            "cf_l2_corpus_meta.json": sha256_archivo(BASE_DIR / "docs/mediciones/cf_l2_corpus_meta.json"),
        },
        "tamanos": {"train": len(train), "aumento_train": len(aumento), "dev_general": len(dev),
                    "dev_formatos": len(dev_formatos), "test_gold_real": meta_base["tamanos"]["test"]},
        "sha256": {f: sha256_archivo(args.salida / f) for f in (*ARCHIVOS_CORPUS, archivo_dev)},
        "familias_nuevas_dev": len(familias_dev), "familias_dev_presentes_en_train": 0,
        "nombres_de_asignatura_dev_presentes_en_train": 0,
        "filas_exactas_o_normalizadas_repetidas_dev_formatos_vs_train": 0,
        "aumentos_con_personas_anotadas": 0, "etiquetas_iob2": ETIQUETAS_CF,
        "tokenizador": {"modelo": MODELO_CF, "limite": MAX_TOKENS_CF,
                         "maximos_con_especiales": {"aumento_train": max(x[-1] for x in formatos_train),
                                                    "dev_formatos": max(x[-1] for x in formatos_dev)}},
        "formatos_de_muestras": {
            grupo: dict(Counter(formato for _, formato, perfil, _, _ in filas if perfil == 0))
            for grupo, filas in (("aumento_train", formatos_train), ("dev_formatos", formatos_dev))
        },
        "perfiles_de_muestras": {
            grupo: dict(Counter(("ambos", "solo_programa", "solo_modulo", "ninguno")[perfil] for _, _, perfil, _, _ in filas))
            for grupo, filas in (("aumento_train", formatos_train), ("dev_formatos", formatos_dev))
        },
        "reservados": "Los diseños se derivan de CF-L0. Gold se copia en bytes. No se consultan ejemplos de layouts_5, gold o CoNLL para generar muestras.",
        "protocolo": "cf_l2_recuperacion_protocolo.json",
    }
    texto = json.dumps(meta, ensure_ascii=False, indent=2) + "\n"
    (args.salida / "corpus_meta.json").write_text(texto, encoding="utf-8")
    print(texto, end="")


if __name__ == "__main__":
    main()
