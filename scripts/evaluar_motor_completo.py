import sys
sys.path.insert(0, ".")
import json
from seqeval.metrics import classification_report
from pipeline.semantic.ner_engine import BetoNEREngine

engine = BetoNEREngine()

def alinear_entidades_a_tokens(tokens, texto, entidades):
    # Encontrar spans de cada token en el texto
    token_spans = []
    idx = 0
    for t in tokens:
        pos = texto.find(t, idx)
        if pos == -1:
            # fallback si hay normalización
            token_spans.append((idx, idx + len(t)))
            idx += len(t)
        else:
            token_spans.append((pos, pos + len(t)))
            idx = pos + len(t)
    
    pred_tags = ["O"] * len(tokens)
    for ent in entidades:
        ent_start = ent.start_char
        ent_end = ent.end_char
        tipo_str = ent.tipo.value if hasattr(ent.tipo, "value") else str(ent.tipo)
        
        # Mapear tipos a etiquetas del esquema
        if tipo_str == "DOCENTE":
            tipo_tag = "PER_DOCENTE"
        elif tipo_str == "ESTUDIANTE":
            tipo_tag = "PER_ESTUDIANTE"
        elif tipo_str in ["MODULO", "PROGRAMA"]:
            tipo_tag = tipo_str
        else:
            tipo_tag = tipo_str
        
        is_first = True
        for t_idx, (s, e) in enumerate(token_spans):
            # Si hay overlap significativo
            if max(s, ent_start) < min(e, ent_end):
                if is_first:
                    pred_tags[t_idx] = f"B-{tipo_tag}"
                    is_first = False
                else:
                    pred_tags[t_idx] = f"I-{tipo_tag}"
    return pred_tags

print("\n--- 1. EVALUANDO MOTOR COMPLETO EN TEST GOLD REAL (180 LINEAS) ---")
true_gold = []
pred_gold = []
with open("data/test_gold_real.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        d = json.loads(line)
        texto = d["texto"]
        tokens = d["tokens"]
        gold_tags = d["tags"]
        
        res = engine.extraer_entidades(texto)
        p_tags = alinear_entidades_a_tokens(tokens, texto, res.entidades)
        
        true_gold.append(gold_tags)
        pred_gold.append(p_tags)

rep_gold = classification_report(true_gold, pred_gold, output_dict=True, digits=4, zero_division=0)
for ent in ['MODULO', 'PER_DOCENTE', 'PER_ESTUDIANTE', 'PROGRAMA', 'micro avg', 'macro avg', 'weighted avg']:
    if ent in rep_gold:
        m = rep_gold[ent]
        print(f"  {ent:15}: Prec={m['precision']:.4f}, Rec={m['recall']:.4f}, F1={m['f1-score']:.4f}, Sup={m['support']}")

print("\n--- 2. EVALUANDO MOTOR COMPLETO EN TEST.CONLL (230 ORACIONES) ---")
sentences = []
curr_tokens = []
curr_tags = []
with open("test.conll", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            if curr_tokens:
                sentences.append((curr_tokens, curr_tags))
                curr_tokens = []
                curr_tags = []
        else:
            parts = line.split()
            if len(parts) >= 2:
                curr_tokens.append(parts[0])
                curr_tags.append(parts[-1])
if curr_tokens:
    sentences.append((curr_tokens, curr_tags))

true_conll = []
pred_conll = []
for tokens, gold_tags in sentences:
    texto = " ".join(tokens)
    res = engine.extraer_entidades(texto)
    p_tags = alinear_entidades_a_tokens(tokens, texto, res.entidades)
    
    true_conll.append(gold_tags)
    pred_conll.append(p_tags)

rep_conll = classification_report(true_conll, pred_conll, output_dict=True, digits=4, zero_division=0)
for ent in ['MODULO', 'PER_DOCENTE', 'PER_ESTUDIANTE', 'PROGRAMA', 'micro avg', 'macro avg', 'weighted avg']:
    if ent in rep_conll:
        m = rep_conll[ent]
        print(f"  {ent:15}: Prec={m['precision']:.4f}, Rec={m['recall']:.4f}, F1={m['f1-score']:.4f}, Sup={m['support']}")
