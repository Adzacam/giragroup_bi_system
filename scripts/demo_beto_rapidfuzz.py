import pandas as pd
from pathlib import Path
import torch
from transformers import BertTokenizerFast, BertForTokenClassification
from rapidfuzz import process, fuzz

ROOT = Path('.')
model_path = ROOT / 'pipeline' / 'semantic' / 'beto_local'
tokenizer = BertTokenizerFast.from_pretrained(str(model_path))
model = BertForTokenClassification.from_pretrained(str(model_path))
model.eval()
id2label = model.config.id2label

# Catalogo canonico
programas_canonicos = [
    'DIPLOMADO EN INTELIGENCIA DE NEGOCIOS Y CIENCIA DE DATOS',
    'MAESTRÍA EN DIRECCIÓN ESTRATÉGICA Y GESTIÓN DE NEGOCIOS',
    'DIPLOMADO EN MEDICINA ESTÉTICA Y CUIDADO INTEGRAL',
    'CURSO DE EXPERTO EN CIBERSEGURIDAD Y HACKING ÉTICO',
    'DIPLOMADO EN GESTIÓN TRIBUTARIA',
    'DIPLOMADO EN DERECHO NOTARIAL'
]

modulos_canonicos = [
    'BUSINESS INTELLIGENCE & DATA WAREHOUSING',
    'METODOLOGÍA DE LA INVESTIGACIÓN CIENTÍFICA',
    'ANATOMÍA FACIAL Y TÉCNICAS APLICADAS',
    'SEGURIDAD OFENSIVA Y ANÁLISIS FORENSE',
    'GESTIÓN TRIBUTARIA APLICADA',
    'DERECHO NOTARIAL REGISTRAL'
]

lineas_prueba = [
    ('uploads/data/Base centralizada Académica ARCA (1).xlsx', 'ACTAS DE NOTAS', 5),
    ('uploads/data/BD Cobranzas.xlsx', 0, 10),
    ('uploads/test/Reporte_Aula_Virtual_Moodle_TEST.csv', None, 2)
]

for arch, sheet, fila_idx in lineas_prueba:
    p = ROOT / arch
    if p.suffix == '.csv':
        df = pd.read_csv(p)
    else:
        df = pd.read_excel(p, sheet_name=sheet if sheet is not None else 0)
    
    row = df.iloc[fila_idx]
    items = [f'{c}: {v}' for c, v in row.items() if pd.notna(v) and str(v).strip()]
    texto = ' | '.join(items[:6])
    
    # Inferencia BETO
    inputs = tokenizer(texto, return_tensors='pt', truncation=True, max_length=128)
    with torch.no_grad():
        out = model(**inputs)
        probs = torch.softmax(out.logits, dim=-1)[0]
        preds = torch.argmax(probs, dim=-1)
    
    tokens = tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
    
    # Extraer entidades
    entidades = []
    curr_tokens = []
    curr_label = None
    curr_probs = []
    
    for t, p_id, pr_row in zip(tokens, preds, probs):
        if t in ('[CLS]', '[SEP]', '[PAD]'):
            continue
        lbl = id2label[int(p_id)]
        if lbl != 'O':
            prob_val = float(pr_row[p_id].item())
            if lbl.startswith('B-'):
                if curr_tokens:
                    ent_str = tokenizer.convert_tokens_to_string(curr_tokens)
                    entidades.append((ent_str, curr_label, sum(curr_probs)/len(curr_probs)))
                curr_tokens = [t]
                curr_label = lbl[2:]
                curr_probs = [prob_val]
            elif lbl.startswith('I-') and curr_label == lbl[2:]:
                curr_tokens.append(t)
                curr_probs.append(prob_val)
        else:
            if curr_tokens:
                ent_str = tokenizer.convert_tokens_to_string(curr_tokens)
                entidades.append((ent_str, curr_label, sum(curr_probs)/len(curr_probs)))
                curr_tokens = []
                curr_label = None
                curr_probs = []
    if curr_tokens:
        ent_str = tokenizer.convert_tokens_to_string(curr_tokens)
        entidades.append((ent_str, curr_label, sum(curr_probs)/len(curr_probs)))
        
    print(f'==================================================')
    print(f'ARCHIVO: {arch} | FILA: {fila_idx}')
    print(f'TEXTO RAW: {texto}')
    print(f'ENTIDADES EXTRAIDAS ({len(entidades)}):')
    
    confianzas = []
    for ent_str, lbl, conf in entidades:
        confianzas.append(conf)
        # Normalizacion RapidFuzz
        norm_val = 'N/A'
        sim = 0.0
        if 'PROGRAMA' in lbl:
            match = process.extractOne(ent_str.upper(), programas_canonicos, scorer=fuzz.token_set_ratio)
            if match:
                norm_val, sim = match[0], match[1]
        elif 'MODULO' in lbl:
            match = process.extractOne(ent_str.upper(), modulos_canonicos, scorer=fuzz.token_set_ratio)
            if match:
                norm_val, sim = match[0], match[1]
        elif 'PER_' in lbl:
            norm_val = ent_str.strip().title()
            sim = 100.0
            
        print(f'  - Entidad: "{ent_str}"')
        print(f'    Tipo: {lbl} | Confianza BETO: {conf*100:.2f}%')
        print(f'    Valor Normalizado (RapidFuzz): "{norm_val}" (Similitud: {sim:.1f}%)')
        
    avg_conf = sum(confianzas)/len(confianzas) if confianzas else 0.55
    estado = 'Consolidado directo' if avg_conf >= 0.85 else ('Revision HITL' if avg_conf >= 0.60 else 'Retenido en Staging')
    print(f'INDICE FINAL REGISTRO: {avg_conf:.4f} -> ESTADO: {estado}')
