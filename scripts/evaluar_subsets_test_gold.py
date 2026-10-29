import json
import torch
from transformers import BertTokenizerFast, BertForTokenClassification
from seqeval.metrics import classification_report

device = torch.device('cpu')
model_path = 'pipeline/semantic/beto_local'
tokenizer = BertTokenizerFast.from_pretrained(model_path)
model = BertForTokenClassification.from_pretrained(model_path)
model.to(device)
model.eval()

id2label = model.config.id2label

with open('data/test_gold_real.jsonl', 'r', encoding='utf-8') as f:
    lines = [json.loads(line) for line in f]

lines_a = lines[:100]  # Experiencia Docente 2.0 (no visto)
lines_b = lines[100:] # *_TEST (vistos)

def evaluar_subset(subset, nombre):
    true_labels = []
    pred_labels = []
    for item in subset:
        tokens = item['tokens']
        gold_tags = item['tags']
        enc = tokenizer(tokens, is_split_into_words=True, return_tensors='pt', truncation=True, max_length=128)
        word_ids = enc.word_ids(batch_index=0)
        with torch.no_grad():
            logits = model(input_ids=enc['input_ids'].to(device), attention_mask=enc['attention_mask'].to(device)).logits
            preds = torch.argmax(logits, dim=-1)[0].cpu().numpy()
        
        gold_aligned = []
        pred_aligned = []
        prev_w = None
        for i, w in enumerate(word_ids):
            if w is None or w == prev_w:
                continue
            if w < len(gold_tags):
                gold_aligned.append(gold_tags[w])
                pred_aligned.append(id2label[preds[i]])
            prev_w = w
        true_labels.append(gold_aligned)
        pred_labels.append(pred_aligned)
    
    rep = classification_report(true_labels, pred_labels, output_dict=True, digits=4, zero_division=0)
    print(f"\n=======================================================")
    print(f"=== SUBSET: {nombre} (n={len(subset)}) ===")
    print(f"=======================================================")
    for ent in ['MODULO', 'PER_DOCENTE', 'PER_ESTUDIANTE', 'PROGRAMA', 'micro avg', 'macro avg', 'weighted avg']:
        if ent in rep:
            m = rep[ent]
            print(f"  {ent:15}: Prec={m['precision']:.4f}, Rec={m['recall']:.4f}, F1={m['f1-score']:.4f}, Sup={m['support']}")

evaluar_subset(lines_a, 'Experiencia Docente 2.0 (Libro NO visto, 100 lineas)')
evaluar_subset(lines_b, '*_TEST de libros vistos (80 lineas: 50 ARCA + 30 INSCRITOS)')
