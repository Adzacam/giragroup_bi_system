import re
from pathlib import Path

def patch_ner_engine():
    path = Path("pipeline/semantic/ner_engine.py")
    text = path.read_text(encoding="utf-8")

    # 1. Parche de aislamiento de nota respecto a modulo
    patron_nota_orig = re.compile(
        r'(# 2\. Notas / Calificaciones.*?for m in PATRON_NOTA\.finditer\(texto\):.*?'
        r'start_val = m\.start\(1\)\s*\n\s*end_val = m\.end\(1\)\s*\n)'
        r'(\s*try:)',
        re.DOTALL
    )
    
    aislamiento_codigo = r'''\1            # Aislamiento estricto: no capturar números de módulo, materias ni CI
            contexto_izq = texto[max(0, start_val - 15):start_val].upper()
            if any(w in contexto_izq for w in ["MODULO", "MÓDULO", "MATERIA", "-", "/", "C.I.", "CI"]):
                continue
\2'''

    text_patched, count1 = patron_nota_orig.subn(aislamiento_codigo, text, count=1)
    print(f"Aislamiento PATRON_NOTA aplicado: {count1}")

    # 2. Parche en fallback de nota
    patron_fb_orig = re.compile(
        r'(# Fallback sobre texto libre.*?if not encontro_nota and any\(w in texto\.lower\(\) for w in \("nota", "calificaci", "puntaje"\)\):\s*\n)'
        r'(\s*m_fb = re\.search\(r\'\\b\(\[0-9\]\{1,2\}\(\?:\\\.\[0-9\]\)\?\)\\b\', texto\)\s*\n\s*if m_fb:\s*\n)'
        r'(\s*try:\s*\n\s*num_fb = float\(m_fb\.group\(1\)\)\s*\n)',
        re.DOTALL
    )
    fb_codigo = r'''\1        for m_fb in re.finditer(r'\b([0-9]{1,2}(?:\.[0-9])?)\b', texto):
            start_fb = m_fb.start(1)
            contexto_izq = texto[max(0, start_fb - 15):start_fb].upper()
            if any(w in contexto_izq for w in ["MODULO", "MÓDULO", "MATERIA", "-", "/", "CARNET", "C.I.", "CI"]):
                continue
            try:
                num_fb = float(m_fb.group(1))
'''
    text_patched, count2 = patron_fb_orig.subn(fb_codigo, text_patched, count=1)
    print(f"Aislamiento Fallback NOTA aplicado: {count2}")

    # 3. Parche de orden de consolidación para Cascada B
    patron_sort_orig = 'todas.sort(key=lambda e: (e.start_char, -(e.end_char - e.start_char), -e.score))'
    patron_sort_nuevo = '''# Cascada Arquitectura B: Prioridad de fuentes estricta (CI_EXACTA -> ENCABEZADO -> FUZZY -> REGEX -> BETO)
        # BETO solo actúa sobre entidades no resueltas por las fuentes previas y nunca las sobrescribe.
        prioridad_fuente = {"CI_EXACTA": 1, "ENCABEZADO": 2, "FUZZY": 3, "REGEX": 4, "BETO": 5}
        todas.sort(key=lambda e: (prioridad_fuente.get(e.fuente_resolucion or "BETO", 5), e.start_char, -(e.end_char - e.start_char), -e.score))'''

    if patron_sort_orig in text_patched:
        text_patched = text_patched.replace(patron_sort_orig, patron_sort_nuevo, 1)
        print("Orden de consolidación Cascada B aplicado: 1")
    else:
        print("Aviso: patron_sort_orig no encontrado")

    path.write_text(text_patched, encoding="utf-8")
    print("pipeline/semantic/ner_engine.py guardado.")

if __name__ == "__main__":
    patch_ner_engine()
