#!/usr/bin/env python
"""
scripts/generar_layouts_adversarios.py
======================================
Genera 5 archivos Excel con estructuras heterogéneas y adversarias (Punto 5):
1. layout1_cabeceras_desconocidas.xlsx
2. layout2_columnas_invertidas_ruido.xlsx
3. layout3_celdas_combinadas_merged.xlsx
4. layout4_filas_totales_subtotales.xlsx
5. layout5_multihoja_anidada.xlsx
"""

import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

OUT_DIR = os.path.join("uploads", "test", "layouts_adversarios")
os.makedirs(OUT_DIR, exist_ok=True)

# 1. Cabeceras desconocidas / coloquiales
def crear_layout1():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "PLANILLA_INEDITA"
    
    headers = ["Catedrático a Cargo", "Inscrito Registrado", "Materia de Avance", "Calificación Obtenida", "Curso Mayor"]
    ws.append(headers)
    
    datos = [
        ["Dr. Alejandro Siles", "Mariana Choquehuanca", "Módulo 1 Finanzas", "88", "Maestría en Finanzas"],
        ["Lic. Roberto Carlos Duran", "Gabriel Alarcón Flores", "Módulo 2 Gestión", "92", "Diplomado en BI"],
        ["Ing. Marcelo Claure", "Valeria Gutiérrez Paz", "Módulo 3 Big Data", "74", "Maestría en Data Science"],
        ["Dra. Carmen Rosa Morales", "Fernando Torrico Roca", "Módulo 4 Auditoría", "81", "Especialidad Tributaria"],
        ["Prof. Gonzalo Sanchez", "Claudia Méndez Vaca", "Módulo 1 Fundamentos", "65", "Diplomado Educación"],
    ]
    for d in datos:
        ws.append(d)
    
    path = os.path.join(OUT_DIR, "layout1_cabeceras_desconocidas.xlsx")
    wb.save(path)
    print(f"Creado: {path}")

# 2. Columnas invertidas y columnas de ruido
def crear_layout2():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "REGISTRO_COLUMNAS_INVERTIDAS"
    
    headers = ["Puntaje", "Teléfono Móvil", "Fecha Registro", "Materia / Asignatura", "Docente", "Observaciones", "Participante"]
    ws.append(headers)
    
    datos = [
        ["95", "70123456", "2025-03-15", "Módulo 1 Big Data", "Lic. Roberto Carlos Duran", "Sin mora", "Patricia Daza Arteaga"],
        ["60", "71234567", "2025-03-16", "Módulo 2 Modelado", "Ing. Marcelo Claure", "Pendiente pago", "Rodrigo Fernández Roca"],
        ["82", "72345678", "2025-03-17", "Módulo 3 ETL", "Dra. Carmen Rosa Morales", "Regular", "Guillermo Justiniano"],
        ["45", "73456789", "2025-03-18", "Módulo 4 Visualización", "Dr. Alejandro Siles", "Riesgo académico", "Ana Claudia Torrico"],
    ]
    for d in datos:
        ws.append(d)
        
    path = os.path.join(OUT_DIR, "layout2_columnas_invertidas_ruido.xlsx")
    wb.save(path)
    print(f"Creado: {path}")

# 3. Celdas combinadas horizontales y verticales
def crear_layout3():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "ACTA_CON_MERGED_CELLS"
    
    # Fila de metadatos combinada
    ws.merge_cells("A1:D1")
    ws["A1"] = "PROGRAMA DE POSGRADO: MAESTRÍA EN DATA SCIENCE - GESTIÓN 2026"
    ws["A1"].font = Font(bold=True)
    
    ws.merge_cells("A2:D2")
    ws["A2"] = "DOCENTE ASIGNADO: ING. MARCELO CLAURE | MÓDULO 2 ARQUITECTURA ETL"
    
    # Encabezados en fila 4
    ws["A4"] = "Nro"
    ws["B4"] = "Estudiante"
    ws["C4"] = "Nota Final"
    ws["D4"] = "Estado"
    
    datos = [
        [1, "Javier Mendoza Salazar", 90, "Aprobado"],
        [2, "Maria Elena Ríos", 85, "Aprobado"],
        [3, "Sergio Alarcón Flores", 78, "Aprobado"],
        [4, "Valeria Gutiérrez Paz", 50, "Reprobado"],
    ]
    for idx, d in enumerate(datos, start=5):
        for col_idx, val in enumerate(d, start=1):
            ws.cell(row=idx, column=col_idx, value=val)
            
    path = os.path.join(OUT_DIR, "layout3_celdas_combinadas_merged.xlsx")
    wb.save(path)
    print(f"Creado: {path}")

# 4. Filas de totales, subtotales y firmas
def crear_layout4():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "PLANILLA_CON_TOTALES"
    
    headers = ["Estudiante", "Docente", "Programa", "Módulo", "Nota"]
    ws.append(headers)
    
    datos = [
        ["Carlos Mamani Quispe", "Lic. Roberto Carlos Duran", "Diplomado en BI", "Módulo 1", 85],
        ["Ana Claudia Torrico", "Lic. Roberto Carlos Duran", "Diplomado en BI", "Módulo 1", 90],
        ["--- SUBTOTAL PARCIAL GRUPO A ---", "", "", "", 87.5],
        ["Guillermo Justiniano", "Lic. Roberto Carlos Duran", "Diplomado en BI", "Módulo 1", 72],
        ["Patricia Daza Arteaga", "Lic. Roberto Carlos Duran", "Diplomado en BI", "Módulo 1", 98],
        ["PROMEDIO GENERAL DEL CURSO: 86.25", "", "", "", ""],
        ["TOTAL REGISTROS ACTIVOS: 4", "", "", "", ""],
        ["Firma y Sello del Director Académico: Lic. René Salinas", "", "", "", ""],
    ]
    for d in datos:
        ws.append(d)
        
    path = os.path.join(OUT_DIR, "layout4_filas_totales_subtotales.xlsx")
    wb.save(path)
    print(f"Creado: {path}")

# 5. Múltiples hojas con datos en hojas no primarias
def crear_layout5():
    wb = openpyxl.Workbook()
    # Hoja 1: Instrucciones y notas (Ruido)
    ws1 = wb.active
    ws1.title = "INSTRUCCIONES_SECRETARIA"
    ws1["A1"] = "INSTRUCCIONES DE LLENADO DE PLANILLAS"
    ws1["A2"] = "1. Favor ingresar notas sobre 100 puntos."
    ws1["A3"] = "2. No modificar los nombres de los módulos."
    
    # Hoja 2: Datos Académicos
    ws2 = wb.create_sheet("ACTA_NOTAS_REAL")
    ws2.append(["Alumno", "Docente", "Materia", "Oferta Académica", "Calificación"])
    ws2.append(["Rodrigo Fernández Roca", "Dra. Carmen Rosa Morales", "Módulo 3 Gestión", "Especialidad Tributaria", 89])
    ws2.append(["Valeria Gutiérrez Paz", "Dra. Carmen Rosa Morales", "Módulo 3 Gestión", "Especialidad Tributaria", 94])
    ws2.append(["Sergio Alarcón Flores", "Dra. Carmen Rosa Morales", "Módulo 3 Gestión", "Especialidad Tributaria", 70])
    
    # Hoja 3: Datos de Inscripción
    ws3 = wb.create_sheet("INSCRIPCIONES_NUEVAS")
    ws3.append(["Postulante", "Programa de Interés", "Documento CI"])
    ws3.append(["Javier Mendoza Salazar", "Maestría en Data Science", "CI-6192831"])
    ws3.append(["Maria Elena Ríos", "Diplomado en BI", "CI-4920192"])

    path = os.path.join(OUT_DIR, "layout5_multihoja_anidada.xlsx")
    wb.save(path)
    print(f"Creado: {path}")

def main():
    print(f"Generando 5 layouts adversarios en {OUT_DIR}...")
    crear_layout1()
    crear_layout2()
    crear_layout3()
    crear_layout4()
    crear_layout5()
    print("5 layouts creados exitosamente.")

if __name__ == "__main__":
    main()
