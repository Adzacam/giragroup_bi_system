# scripts/patch_ner_engine_fuente.py
with open("pipeline/semantic/ner_engine.py", "r", encoding="utf-8") as f:
    text = f.read()

# BETO
text = text.replace(
    'origen="BETO_NER",\n                        metadata={"etiqueta_original": etiqueta}',
    'origen="BETO_NER",\n                        fuente_resolucion="BETO",\n                        metadata={"etiqueta_original": etiqueta}'
)

# POS
text = text.replace(
    'origen="REGEX_SEMANTICO",\n                    metadata={"codigo_pos": m.group(1)}',
    'origen="REGEX_SEMANTICO",\n                    fuente_resolucion="REGEX",\n                    metadata={"codigo_pos": m.group(1)}'
)

# NOTA
text = text.replace(
    'origen="REGEX_SEMANTICO",\n                            metadata={"valor_numerico": num}',
    'origen="REGEX_SEMANTICO",\n                            fuente_resolucion="REGEX",\n                            metadata={"valor_numerico": num}'
)

# CI
text = text.replace(
    'tipo=TipoEntidad.CI,\n                    valor=valor_ci,\n                    start_char=start_val,\n                    end_char=end_val,\n                    score=0.96,\n                    origen="REGEX_SEMANTICO"',
    'tipo=TipoEntidad.CI,\n                    valor=valor_ci,\n                    start_char=start_val,\n                    end_char=end_val,\n                    score=0.96,\n                    origen="REGEX_SEMANTICO",\n                    fuente_resolucion="CI_EXACTA"'
)

# MONTO
text = text.replace(
    'origen="REGEX_SEMANTICO",\n                    metadata={"moneda": "BOB"}',
    'origen="REGEX_SEMANTICO",\n                    fuente_resolucion="REGEX",\n                    metadata={"moneda": "BOB"}'
)

with open("pipeline/semantic/ner_engine.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Patch applied to ner_engine.py!")
