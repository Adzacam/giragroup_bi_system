with open('pipeline/semantic/ner_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """            # Desambiguación semántica de entidades PER
            tipo_final = TipoEntidad.OTRO
            if etiqueta == "PER":"""

replacement = """            # Soporte nativo para etiquetas de BETO GiraGroup fine-tuned y fallback CoNLL
            tipo_final = TipoEntidad.OTRO
            if etiqueta == "PER_ESTUDIANTE":
                tipo_final = TipoEntidad.ESTUDIANTE
            elif etiqueta == "PER_DOCENTE":
                tipo_final = TipoEntidad.DOCENTE
            elif etiqueta == "MODULO":
                tipo_final = TipoEntidad.MODULO
            elif etiqueta == "PROGRAMA":
                tipo_final = TipoEntidad.PROGRAMA
            elif etiqueta == "PER":"""

if target in content:
    new_content = content.replace(target, replacement, 1)
    with open('pipeline/semantic/ner_engine.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replaced successfully!")
else:
    # Try normalizing newlines
    c_norm = content.replace("\r\n", "\n")
    t_norm = target.replace("\r\n", "\n")
    r_norm = replacement.replace("\r\n", "\n")
    if t_norm in c_norm:
        new_content = c_norm.replace(t_norm, r_norm, 1)
        with open('pipeline/semantic/ner_engine.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Replaced successfully after newline normalization!")
    else:
        print("Target still not found!")
