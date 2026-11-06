import re
from pathlib import Path

p = Path("pipeline/semantic/ner_engine.py")
text = p.read_text(encoding="utf-8")

patron = re.compile(r'        # Fallback sobre texto libre.*?        # 3\. Montos monetarios', re.DOTALL)
good_block = '''        # Fallback sobre texto libre con regex de 1-2 dígitos si el texto menciona 'nota' o 'calificacion'
        if not encontro_nota and any(w in texto.lower() for w in ("nota", "calificaci", "puntaje")):
            for m_fb in re.finditer(r'\\b([0-9]{1,2}(?:\\.[0-9])?)\\b', texto):
                start_fb = m_fb.start(1)
                contexto_izq = texto[max(0, start_fb - 15):start_fb].upper()
                if any(w in contexto_izq for w in ["MODULO", "MÓDULO", "MATERIA", "-", "/", "CARNET", "C.I.", "CI"]):
                    continue
                try:
                    num_fb = float(m_fb.group(1))
                    if 0.0 < num_fb <= 10.0:
                        num_fb = round(num_fb * 10.0, 2)
                    if 0.0 <= num_fb <= 100.0:
                        entidades.append(
                            EntidadExtraida(
                                tipo=TipoEntidad.NOTA,
                                valor=str(num_fb),
                                start_char=start_fb,
                                end_char=m_fb.end(1),
                                score=0.85,
                                origen="REGEX_FALLBACK",
                                fuente_resolucion="REGEX",
                                metadata={"valor_numerico": num_fb}
                            )
                        )
                        break
                except ValueError:
                    pass

        # 3. Montos monetarios'''

text_fixed, count = patron.subn(good_block, text, count=1)
print(f"Reemplazo realizado: {count}")
p.write_text(text_fixed, encoding="utf-8")
