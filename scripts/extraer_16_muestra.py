import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ablacion_beto import EvaluadorAblacion
from pipeline.semantic.indice_confianza import calcular_indices, clasificar_banda, BANDA_CONSOLIDADO, BANDA_REVISION

def main():
    evaluador = EvaluadorAblacion()
    lote = evaluador.cargar_lote_1387()

    random.seed(42)
    indices_muestra = sorted(random.sample(range(len(lote)), 100))
    muestra = [lote[i] for i in indices_muestra]

    textos = [m["texto"] for m in muestra]
    indices_c = calcular_indices(textos)

    difs_16 = []
    for idx_rel, (item, idx_c) in enumerate(zip(muestra, indices_c)):
        texto = item["texto"]
        res_a = evaluador.parser.procesar_fila(texto)
        banda_a = res_a["banda"]
        banda_c = clasificar_banda(idx_c)
        if banda_a == BANDA_CONSOLIDADO and banda_c == BANDA_REVISION:
            tokens = [tok for tok in [t.strip() for t in texto.split()] if tok]
            tags_c, confs_c = evaluador.inferir_beto_tokens(tokens)
            difs_16.append({
                "numero": len(difs_16) + 1,
                "indice_en_muestra": idx_rel,
                "indice_global_lote": indices_muestra[idx_rel],
                "archivo": Path(item["archivo"]).name,
                "hoja": item.get("hoja", ""),
                "texto": texto,
                "confianza_a": round(res_a["confianza"], 4),
                "confianza_c": round(idx_c, 4),
                "entidades_a": [
                    {
                        "tipo": e.tipo,
                        "valor": e.valor,
                        "score": round(e.score, 4),
                        "fuente": e.fuente_resolucion
                    } for e in res_a["entidades"]
                ],
                "tokens_beto_c": [
                    {"token": tok, "tag": tag, "conf": round(conf, 4)}
                    for tok, tag, conf in zip(tokens, tags_c, confs_c) if tag != "O"
                ]
            })

    print(f"Total de discrepancias en la muestra de 100: {len(difs_16)}")
    out_path = Path("docs/evidencias/16_registros_muestra_c_hitl_a_directo.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(difs_16, f, indent=2, ensure_ascii=False)
    print(f"Guardado en {out_path}")

    sys_out = open(1, "w", encoding="utf-8", closefd=False)
    sys_out.write("\n" + "="*80 + "\n")
    sys_out.write("LOS 16 REGISTROS DE LA MUESTRA ALEATORIA (SEMILLA 42) DONDE C FUE A HITL Y A FUE DIRECTO\n")
    sys_out.write("="*80 + "\n\n")

    for d in difs_16:
        sys_out.write(f"[{d['numero']}] Muestra #{d['indice_en_muestra']} | Lote #{d['indice_global_lote']} | Archivo: {d['archivo']} ({d['hoja']})\n")
        sys_out.write(f"    Confianza A: {d['confianza_a']} (Directo) | Confianza C: {d['confianza_c']} (HITL)\n")
        sys_out.write(f"    Texto: {d['texto']}\n")
        sys_out.write(f"    Entidades resueltas por Modo A:\n")
        for ea in d["entidades_a"]:
            sys_out.write(f"      - {ea['tipo']}: '{ea['valor']}' (Score: {ea['score']}, Fuente: {ea['fuente']})\n")
        sys_out.write(f"    Predicciones de Modo C (BETO puro):\n")
        if d["tokens_beto_c"]:
            for tc in d["tokens_beto_c"]:
                sys_out.write(f"      - {tc['tag']}: '{tc['token']}' (Conf: {tc['conf']})\n")
        else:
            sys_out.write(f"      - Ninguna entidad detectada por BETO (confianza de contexto 0.72)\n")
        sys_out.write("-" * 80 + "\n")

if __name__ == "__main__":
    main()
