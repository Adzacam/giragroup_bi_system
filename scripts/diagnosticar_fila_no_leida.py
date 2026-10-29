import openpyxl
from pipeline.ingesta import leer_archivo

path = "uploads/test/layouts_adversarios/layout3_celdas_combinadas_merged.xlsx"
wb = openpyxl.load_workbook(path, data_only=True)
ws = wb.active

print(f"Hoja: {ws.title}, max_row: {ws.max_row}, max_column: {ws.max_column}")
for r in range(1, ws.max_row + 1):
    vals = [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)]
    is_empty = all(v is None or str(v).strip() == "" for v in vals)
    print(f"Fila {r}: empty={is_empty} -> {vals}")

df = leer_archivo(path)
print(f"\nDataFrame leido por pipeline.ingesta: shape={df.shape}")
print(df)
