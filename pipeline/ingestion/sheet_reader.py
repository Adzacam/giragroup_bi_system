import pandas as pd
import os

def leer_excel_academico(file_path: str) -> list[dict]:
    """
    Lee una plantilla de Excel de notas, limpia la estructura base 
    y la convierte en un listado de diccionarios procesables.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"El archivo {file_path} no existe.")

    try:
        # Leer el archivo Excel
        df = pd.read_excel(file_path)
        
        # 1. Limpieza estructural: eliminar filas y columnas completamente vacías
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        
        # 2. Normalización de cabeceras: minúsculas, sin espacios extra, reemplazar espacios por guiones bajos
        df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
        
        # 3. Manejo de nulos: reemplazar valores NaN con strings vacíos para evitar errores en Python/FastAPI
        df = df.fillna("")
        
        # Convertir el DataFrame a una lista de diccionarios
        datos_limpios = df.to_dict(orient="records")
        
        return datos_limpios
        
    except Exception as e:
        print(f"Error crítico procesando el Excel {file_path}: {str(e)}")
        return []

# --- Prueba rápida local ---
if __name__ == "__main__":
    # Cambiar 'plantilla_prueba.xlsx' por el nombre real de tu archivo
    ruta_prueba = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../uploads/Hoja prueba.xlsx"))
    
    print(f"Buscando archivo en: {ruta_prueba}")
    if os.path.exists(ruta_prueba):
        resultados = leer_excel_academico(ruta_prueba)
        print(f"\nÉxito: Se extrajeron {len(resultados)} filas.")
        if resultados:
            print("\nMuestra de la primera fila leída:")
            print(resultados[0])
    else:
        print("No se encontró el archivo en la ruta especificada.")