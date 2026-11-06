import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ablacion_beto import EvaluadorAblacion
from pipeline.semantic.indice_confianza import (
    BANDA_CONSOLIDADO,
    BANDA_REVISION,
    BANDA_STAGING,
    calcular_indices,
    clasificar_banda
)

def main():
    evaluador = EvaluadorAblacion()
    lote = evaluador.cargar_lote_1387()
    print(f"Total registros cargados en lote: {len(lote)}")

    textos = [item["texto"] for item in lote]
    print("Calculando indices BETO oficiales para el lote...")
    indices_c = calcular_indices(textos)

    difs = []
    for idx, (item, idx_c) in enumerate(zip(lote, indices_c)):
        texto = item["texto"]
        res_a = evaluador.parser.procesar_fila(texto)
        banda_a = res_a["banda"]
        conf_a = res_a["confianza"]

        banda_c = clasificar_banda(idx_c)

        if banda_a == BANDA_CONSOLIDADO and banda_c == BANDA_REVISION:
            tokens = [tok for tok in [t.strip() for t in texto.split()] if tok]
            tags_c, confs_c = evaluador.inferir_beto_tokens(tokens)
            difs.append({
                "indice": idx,
                "archivo": item.get("archivo", ""),
                "categoria": item.get("categoria", ""),
                "hoja": item.get("hoja", ""),
                "texto": texto,
                "confianza_a": round(conf_a, 4),
                "confianza_c": round(idx_c, 4),
                "entidades_modo_a": [
                    {
                        "tipo": e.tipo,
                        "valor": e.valor,
                        "score": round(e.score, 4),
                        "fuente_resolucion": e.fuente_resolucion
                    } for e in res_a["entidades"]
                ],
                "tokens_beto_c": [
                    {"token": tok, "tag": tag, "conf": round(conf, 4)}
                    for tok, tag, conf in zip(tokens, tags_c, confs_c) if tag != "O"
                ]
            })

    print(f"Total registros identificados (C=HITL, A=Directo): {len(difs)}")
    
    out_path = Path("docs/evidencias/16_registros_hitl_c_directo_a.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(difs, f, indent=2, ensure_ascii=False)
    print(f"Guardado en {out_path}")

    # Imprimir en consola con codificación segura
    sys_out = open(1, "w", encoding="utf-8", closefd=False)
    sys_out.write("\n" + "="*80 + "\n")
    sys_out.write(f"LOS {len(difs)} REGISTROS DONDE MODO C DERIVÓ A HITL Y MODO A CARGÓ DIRECTO\n")
    sys_out.write("="*80 + "\n\n")

    for i, d in enumerate(difs):
        sys_out.write(f"[{i+1}] Registro #{d['indice']} | Archivo: {Path(d['archivo']).name} ({d['hoja']})\n")
        sys_out.write(f"    Confianza A: {d['confianza_a']} (Directo) | Confianza BETO C: {d['confianza_c']} (HITL)\n")
        sys_out.write(f"    Texto crudo: {d['texto']}\n")
        sys_out.write(f"    Entidades resueltas por Modo A:\n")
        for ea in d["entidades_modo_a"]:
            sys_out.write(f"      - {ea['tipo']}: '{ea['valor']}' (Score: {ea['score']}, Fuente: {ea['fuente_resolucion']})\n")
        sys_out.write(f"    Tokens etiquetados por Modo C (BETO puro):\n")
        if d["tokens_beto_c"]:
            for ec in d["tokens_beto_c"]:
                sys_out.write(f"      - {ec['tag']}: '{ec['token']}' (Conf: {ec['conf']})\n")
        else:
            sys_out.write(f"      - Ninguna entidad clasificada en texto plano (candidato a revisión)\n")
        sys_out.write("-" * 80 + "\n")

if __name__ == "__main__":
    main()
