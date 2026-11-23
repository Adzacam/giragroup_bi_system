"""Selecciona por dev y evalúa los checkpoints de CF-L3 en los conjuntos reservados."""

import argparse
from collections import Counter
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.entrenar_beto_robusto import ID2LABEL, LABEL_LIST, SEED, sha256_archivo
from scripts.evaluar_beto_checkpoint import MAX_LENGTH, predecir

EPOCAS_CF = (2, 3, 4, 5)
ETIQUETAS = tuple(tag[2:] for tag in LABEL_LIST if tag.startswith("B-"))
GOLD_REL = Path("data/test_gold_real.jsonl")
LAYOUTS_REL = Path("uploads/test/layouts_adversarios/gold_layouts_adversarios.json")
MIN_F1_DEV_GENERAL_RECUPERACION = 0.85


def leer_jsonl(ruta):
    return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.strip()]


def seleccionar_checkpoint(corridas):
    historial = []
    for epoca in EPOCAS_CF:
        ruta = corridas / f"beto_e{epoca}"
        info = json.loads((ruta / "training_info.json").read_text(encoding="utf-8"))
        if info["saved_epoch"] != epoca or info["epochs"] != epoca or info["seed"] != SEED:
            raise ValueError(f"Configuración de entrenamiento incompatible en {ruta}")
        if info["test_gold_size"] is not None:
            raise ValueError(f"La corrida {ruta} consultó un conjunto reservado")
        if info["sha256"]["model.safetensors"] != sha256_archivo(ruta / "model.safetensors"):
            raise ValueError(f"Huella del modelo incompatible en {ruta}")
        puntos = [punto for punto in info["epoch_history"] if punto["epoch"] == epoca]
        if len(puntos) != 1:
            raise ValueError(f"Historial dev incompatible en {ruta}")
        historial.append({"ruta": str(ruta), "train_info": info, "resultado_dev": puntos[0]})

    campos = ("model_base", "learning_rate", "weight_decay", "batch_size", "max_length", "seed", "device",
              "determinism", "training_dtype", "versions", "train_size", "dev_size", "classes")
    base = historial[0]["train_info"]
    for corrida in historial[1:]:
        info = corrida["train_info"]
        if any(info[campo] != base[campo] for campo in campos):
            raise ValueError(f"Configuración distinta entre las corridas de {corrida['ruta']}")
        for archivo in ("train_robusto.jsonl", "dev_robusto.jsonl"):
            if info["sha256"][archivo] != base["sha256"][archivo]:
                raise ValueError(f"Corpus distinto entre las corridas de {corrida['ruta']}")

    mejor = max(historial, key=lambda corrida: corrida["resultado_dev"]["dev_f1"])
    return historial, mejor


def evaluar(tokenizer, model, filas):
    from seqeval.metrics import classification_report
    from seqeval.scheme import IOB2

    esperadas = []
    predichas = []
    for fila in filas:
        tokens = fila["tokens"]
        tags = fila["tags"]
        if len(tokens) != len(tags):
            raise ValueError("Etiquetas de referencia desalineadas con el conjunto reservado")
        esperadas.append([tag if tag in LABEL_LIST else "O" for tag in tags])
        predichas.append(predecir(tokens, tokenizer, model))

    reporte = classification_report(esperadas, predichas, mode="strict", scheme=IOB2,
                                    output_dict=True, zero_division=0)
    etiquetas = (*ETIQUETAS, "micro avg", "macro avg", "weighted avg")
    return {etiqueta: reporte.get(etiqueta, {"precision": 0.0, "recall": 0.0, "f1-score": 0.0, "support": 0})
            for etiqueta in etiquetas}


def evaluar_spans_servicio(tokenizer, model, filas):
    """Sensibilidad exacta por offsets del NER, previa a reglas y catálogo."""
    from seqeval.metrics.sequence_labeling import get_entities
    from transformers import pipeline

    from pipeline.semantic.ner_engine import BetoNEREngine

    tokenizer.model_max_length = MAX_LENGTH
    motor = BetoNEREngine(device="cpu", auto_load=False)
    ner = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple", device=-1)
    textos = [fila["texto"].strip() for fila in filas]
    gold, pred, verdaderos = Counter(), Counter(), Counter()
    for fila, texto, salida in zip(filas, textos, ner(textos, batch_size=64), strict=True):
        offsets = list(re.finditer(r"\w+|[^\w\s]", texto))
        if [token.group() for token in offsets] != fila["tokens"]:
            raise ValueError("La tokenización de referencia no coincide con los offsets del texto")
        tags = [tag if tag in LABEL_LIST else "O" for tag in fila["tags"]]
        gold_fila = {(tipo, offsets[inicio].start(), offsets[fin].end()) for tipo, inicio, fin in get_entities(tags)}
        pred_fila = {(e.metadata["etiqueta_original"], e.start_char, e.end_char)
                     for e in motor._procesar_predicciones_beto(texto, salida)}
        gold.update(tipo for tipo, _, _ in gold_fila)
        pred.update(tipo for tipo, _, _ in pred_fila)
        verdaderos.update(tipo for tipo, _, _ in gold_fila & pred_fila)

    def metricas(tp, total_gold, total_pred):
        return {
            "precision": tp / total_pred if total_pred else 0.0,
            "recall": tp / total_gold if total_gold else 0.0,
            "f1-score": 2 * tp / (total_gold + total_pred) if total_gold + total_pred else 0.0,
            "support": total_gold,
        }

    return {
        **{tipo: metricas(verdaderos[tipo], gold[tipo], pred[tipo]) for tipo in ETIQUETAS},
        "micro avg": metricas(verdaderos.total(), gold.total(), pred.total()),
    }


def cargar_checkpoint(ruta):
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(ruta, local_files_only=True)
    modelo = AutoModelForTokenClassification.from_pretrained(ruta, local_files_only=True).cpu().eval()
    if modelo.config.id2label != ID2LABEL:
        raise ValueError(f"Inventario IOB2 incompatible en {ruta}")
    return tokenizer, modelo


def cuantizar(modelo):
    import torch

    cuantizado = torch.ao.quantization.quantize_dynamic(modelo, {torch.nn.Linear}, dtype=torch.qint8)
    lineales_int8 = sum(isinstance(capa, torch.ao.nn.quantized.dynamic.Linear) for capa in cuantizado.modules())
    if not lineales_int8:
        raise ValueError("La cuantización INT8 no se aplicó")
    return cuantizado, lineales_int8


def evaluar_checkpoint(ruta, datasets, metrica=evaluar):
    tokenizer, modelo = cargar_checkpoint(ruta)
    resultados = {"fp32": {nombre: metrica(tokenizer, modelo, filas) for nombre, filas in datasets.items()}}
    cuantizado, lineales_int8 = cuantizar(modelo)
    resultados["int8"] = {nombre: metrica(tokenizer, cuantizado, filas) for nombre, filas in datasets.items()}
    return {
        "ruta": str(ruta),
        "sha256": {archivo.name: sha256_archivo(archivo) for archivo in sorted(ruta.iterdir())
                   if archivo.is_file() and archivo.suffix in (".json", ".safetensors")},
        "capas_lineales_int8": lineales_int8,
        "resultados": resultados,
    }


def seleccionar_candidato_recuperacion(historial, dev_formatos):
    dev_general = dev_formatos.with_name("dev_robusto.jsonl")
    rutas_dev = {"formatos": dev_formatos, "general": dev_general}
    conjuntos = {nombre: leer_jsonl(ruta) for nombre, ruta in rutas_dev.items()}
    if not all(conjuntos.values()):
        raise ValueError("Las dos particiones de desarrollo de recuperación deben tener registros")
    huellas = {nombre: sha256_archivo(ruta) for nombre, ruta in rutas_dev.items()}
    if huellas["general"] != historial[0]["train_info"]["sha256"]["dev_robusto.jsonl"]:
        raise ValueError("La huella de dev general difiere del dev registrado por las corridas")

    elegibles = []
    for corrida in historial:
        tokenizer, fp32 = cargar_checkpoint(Path(corrida["ruta"]))
        int8, _ = cuantizar(fp32)
        resultados = {nombre: evaluar(tokenizer, int8, filas) for nombre, filas in conjuntos.items()}
        corrida["dev_recuperacion_int8"] = resultados
        if resultados["general"]["micro avg"]["f1-score"] >= MIN_F1_DEV_GENERAL_RECUPERACION:
            elegibles.append(corrida)
        print(f"Dev recuperación época {corrida['resultado_dev']['epoch']}: "
              f"formatos={resultados['formatos']['micro avg']['f1-score']:.6f} "
              f"general={resultados['general']['micro avg']['f1-score']:.6f}", flush=True)

    mejor = max(elegibles, key=lambda corrida: corrida["dev_recuperacion_int8"]["formatos"]["micro avg"]["f1-score"],
                default=None)
    protocolo = {
        "criterio": "Mayor F1 micro IOB2 estricto INT8 en dev de formatos; en empate gana la menor época.",
        "minimo_f1_micro_int8_dev_general": MIN_F1_DEV_GENERAL_RECUPERACION,
        "particiones": {nombre: {"ruta": str(ruta), "sha256": huellas[nombre], "filas": len(conjuntos[nombre])}
                        for nombre, ruta in rutas_dev.items()},
        "nota": "Los reservados históricos se consultan una vez tras fijar el candidato; ya se usaron en CF-L3 inicial.",
    }
    return mejor, protocolo


def guardar_evidencia(salida, evidencia):
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("x", encoding="utf-8") as archivo:
        json.dump(evidencia, archivo, ensure_ascii=False, indent=2, default=lambda valor: valor.item())
        archivo.write("\n")


def main():
    import torch

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corridas", type=Path, required=True, help="Directorio con beto_e2, beto_e3, beto_e4 y beto_e5")
    ap.add_argument("--vigente", type=Path, required=True, help="Checkpoint vigente de comparación")
    ap.add_argument("--salida", type=Path, required=True, help="Archivo JSON de evidencia")
    ap.add_argument("--spans-servicio", action="store_true", help="Sensibilidad diagnóstica de offsets del NER servido")
    ap.add_argument("--dev-formatos", type=Path, help="Dev independiente de formatos para la cohorte de recuperación")
    args = ap.parse_args()
    if args.salida.exists():
        ap.error("La ruta de evidencia ya existe")
    if args.spans_servicio and args.dev_formatos:
        ap.error("La sensibilidad del servicio se documenta en la primera cohorte")
    historial, mejor = seleccionar_checkpoint(args.corridas)
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    recuperacion = None
    if args.dev_formatos:
        mejor, recuperacion = seleccionar_candidato_recuperacion(historial, args.dev_formatos)
        if mejor is None:
            guardar_evidencia(args.salida, {"protocolo_recuperacion": recuperacion, "resultados_dev": historial,
                                           "epoca_elegida": None, "aprobado_calidad_cf_l3": False})
            print("Ningún checkpoint supera el guardarraíl del dev general")
            return
    candidato_ruta = Path(mejor["ruta"])
    print(f"Checkpoint seleccionado por dev: {candidato_ruta}", flush=True)

    gold = ROOT / GOLD_REL
    layouts = ROOT / LAYOUTS_REL
    datasets = {
        "test_gold_real": leer_jsonl(gold),
        "layouts_5": json.loads(layouts.read_text(encoding="utf-8"))["ejemplos"],
    }
    metrica = evaluar_spans_servicio if args.spans_servicio else evaluar
    vigente = evaluar_checkpoint(args.vigente, datasets, metrica)
    candidato = evaluar_checkpoint(candidato_ruta, datasets, metrica)
    f1_candidato_gold = candidato["resultados"]["int8"]["test_gold_real"]["micro avg"]["f1-score"]
    f1_candidato_layouts = candidato["resultados"]["int8"]["layouts_5"]["micro avg"]["f1-score"]
    f1_vigente_layouts = vigente["resultados"]["int8"]["layouts_5"]["micro avg"]["f1-score"]
    puertas = {"rnf_04_int8_gold_f1_micro_min_0_85": f1_candidato_gold >= 0.85,
               "mejora_int8_layouts_f1_micro": f1_candidato_layouts > f1_vigente_layouts}
    evidencia = {
        "protocolo": {
            "seleccion": (recuperacion["criterio"] if recuperacion
                          else "Mayor F1 micro IOB2 estricto en dev. En empate gana la menor época."),
            "metrica_reservados": (
                "Coincidencia exacta de tipo, inicio y fin en caracteres. Pipeline HF con aggregation_strategy=simple y "
                "_procesar_predicciones_beto, previo a reglas y catálogo." if args.spans_servicio
                else "Seqeval estricto IOB2 en tokens de referencia. Una predicción por token, desde el primer subtoken."
            ),
            "diagnostico": args.spans_servicio,
            "max_tokens": MAX_LENGTH,
            "rnf_04_minimo_f1_micro": 0.85,
            "precision_vigente": "int8",
            "cuantizacion": "Dinámica en CPU de torch.nn.Linear con qint8, como BETO_INT8=1 en producción.",
            "motor_int8": torch.backends.quantized.engine,
            "torch": torch.__version__,
            "comando_evaluacion": [sys.executable, *sys.argv],
        },
        "datasets_reservados": {
            nombre: {"ruta": str(ruta.relative_to(ROOT)), "sha256": sha256_archivo(ruta), "filas": len(datasets[nombre])}
            for nombre, ruta in (("test_gold_real", gold), ("layouts_5", layouts))
        },
        "resultados_dev": historial,
        "epoca_elegida": mejor["resultado_dev"]["epoch"],
        "vigente": vigente,
        "candidato": candidato,
        "delta_f1_micro_layouts_int8": f1_candidato_layouts - f1_vigente_layouts,
        "puertas": puertas,
        "aprobado_calidad_cf_l3": None if args.spans_servicio else all(puertas.values()),
    }
    if recuperacion:
        evidencia["protocolo_recuperacion"] = recuperacion
    guardar_evidencia(args.salida, evidencia)
    print(f"Puertas CF-L3: {puertas}")


if __name__ == "__main__":
    main()
