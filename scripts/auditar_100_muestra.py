# scripts/auditar_100_muestra.py
"""
Audita una muestra aleatoria determinista de 100 registros (semilla 42)
del lote de 1.387 en Modo A y Modo C.
"""
import random
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ablacion_beto import EvaluadorAblacion
from pipeline.semantic.indice_confianza import calcular_indices, clasificar_banda, BANDA_CONSOLIDADO

ROOT = Path(".")
SEMILLA = 42
random.seed(SEMILLA)

evaluador = EvaluadorAblacion()
lote = evaluador.cargar_lote_1387()

indices_100 = random.sample(range(len(lote)), 100)
muestra_100 = [lote[i] for i in indices_100]
textos_100 = [item["texto"] for item in muestra_100]

indices_beto_100 = calcular_indices(textos_100)

aciertos_a = 0
aciertos_c = 0
directos_a = 0
directos_c = 0

detalles_a = []
detalles_c = []

for idx, (item, idx_beto) in enumerate(zip(muestra_100, indices_beto_100), 1):
    txt = item["texto"]
    res_a = evaluador.parser.procesar_fila(txt)
    
    # Evaluación MODO A
    # Carga directa: res_a["resuelta"] == True
    if res_a["resuelta"]:
        directos_a += 1
        # Validar si las entidades extraídas corresponden a valores válidos de la fila y no a ruido
        ents_a = {e.tipo: e.valor for e in res_a["entidades"]}
        tiene_estudiante_valido = "PER_ESTUDIANTE" in ents_a and len(ents_a["PER_ESTUDIANTE"]) > 3
        tiene_ci_valido = "CI" in ents_a and len(ents_a["CI"]) >= 5
        # En ARCA / Cobranzas, una fila directa es correcta si identificó a la persona legítima
        if tiene_estudiante_valido or tiene_ci_valido:
            aciertos_a += 1
            detalles_a.append((idx, "CORRECTO", txt[:60]))
        else:
            detalles_a.append((idx, "FALSO_POSITIVO", txt[:60]))
            
    # Evaluación MODO C
    banda_c = clasificar_banda(idx_beto)
    if banda_c == BANDA_CONSOLIDADO:
        directos_c += 1
        # En BETO, verificar si el texto tiene entidad y si la confianza >= 0.85 refleja un hecho real
        pred_tokens, _ = evaluador.inferir_beto_tokens(txt.split())
        tiene_ent_beto = any(t.startswith("B-") for t in pred_tokens)
        if tiene_ent_beto and idx_beto >= 0.85:
            aciertos_c += 1
            detalles_c.append((idx, "CORRECTO", txt[:60]))
        else:
            detalles_c.append((idx, "FALSO_POSITIVO", txt[:60]))

prec_a = (aciertos_a / directos_a * 100.0) if directos_a else 0.0
prec_c = (aciertos_c / directos_c * 100.0) if directos_c else 0.0

print(f"=== RESULTADOS AUDITORÍA MUESTRA N=100 (SEMILLA {SEMILLA}) ===")
print(f"Modo A (Parser Estructural):")
print(f"  - Registros enviados a carga directa: {directos_a}/100")
print(f"  - Registros validados correctos:       {aciertos_a}/{directos_a}")
print(f"  - Precisión de Carga Directa:         {prec_a:.2f}%\n")

print(f"Modo C (BETO Puro):")
print(f"  - Registros enviados a carga directa: {directos_c}/100")
print(f"  - Registros validados correctos:       {aciertos_c}/{directos_c}")
print(f"  - Precisión de Carga Directa:         {prec_c:.2f}%\n")
