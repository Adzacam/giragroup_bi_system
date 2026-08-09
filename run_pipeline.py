import sys
import json
import logging
from pprint import pprint
from pathlib import Path

# Configurar logging básico para ver el proceso en consola
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from pipeline.ingestion.dispatcher import procesar_documento
from pipeline.normalization.pipeline_orchestrator import ejecutar_pipeline_completo

def run_test(file_path: str):
    if not Path(file_path).exists():
        print(f"Error: No se encontró el archivo '{file_path}'")
        return
    
    print(f"\n{'='*60}")
    print(f" Iniciando procesamiento de: {file_path}")
    print(f"{'='*60}")
    
    try:
        # FASE SPRINT 2: Ingesta (Lectura)
        print("\n[1] Ejecutando Ingesta (Sprint 2)...")
        resultado_ingesta = procesar_documento(file_path)
        print(f"  -> Fuente detectada: {resultado_ingesta['fuente_tipo']}")
        print(f"  -> Registros en crudo leídos: {len(resultado_ingesta['filas_raw'])}")
        
        # Inyectar el DataFrame porque el orquestador espera 'data' como un DataFrame (que internamente se iterará)
        # El sheet_reader u otros lectores normalmente deberían incluir 'data', 
        # pero para asegurar compatibilidad si devuelven 'filas_raw':
        import pandas as pd
        if 'data' not in resultado_ingesta and 'filas_raw' in resultado_ingesta:
             resultado_ingesta['data'] = pd.DataFrame(resultado_ingesta['filas_raw'])

        # FASE SPRINT 3: Orquestación (NLP, Fuzzy, Validación, Confianza)
        print("\n[2] Ejecutando Motor NLP y Confianza (Sprint 3)...")
        contrato_salida = ejecutar_pipeline_completo(resultado_ingesta)
        
        print("\n[3] Resultados Finales:")
        print(f"  -> Archivo Procesado: {contrato_salida['nombre_archivo']}")
        print(f"  -> Total Registros Procesados: {contrato_salida['registros_procesados']}")
        print(f"  -> Índice de Confianza Global: {contrato_salida['indice_confianza_global']}")
        print(f"  -> Estado Dashboard: {contrato_salida['estado_dashboard']}")
        
        print("\n[4] Muestra de 2 registros listos para la Base de Datos:")
        # Mostrar solo los 2 primeros registros para no saturar la consola
        registros_muestra = contrato_salida['payload_listo_para_orm'][:2]
        for idx, registro in enumerate(registros_muestra):
            print(f"\n--- Registro {idx + 1} ---")
            pprint(registro, indent=2)
            
    except Exception as e:
        print(f"\n[ERROR] El procesamiento falló: {e}")

if __name__ == "__main__":
    archivo = sys.argv[1] if len(sys.argv) > 1 else "uploads/Evaluacion_Docente_GiraGroup_TEST.xlsx"
    run_test(archivo)
