"""
scripts/anonimizar.py
---------------------
Script CLI de anonimización y sanitización de datos confidenciales institucionales.
Cumple con las cláusulas de privacidad y protección de datos:
- Sustituye nombres reales por seudónimos deterministas consistentes.
- Anonimiza números de CI mediante hash determinista de 7 dígitos.
- Anonimiza correos electrónicos y teléfonos.
- Conserva métricas académicas (notas, asistencias) y financieras (montos, cuotas)
  para preservar la validez del análisis de Inteligencia de Negocios.

Uso:
    python scripts/anonimizar.py --input uploads/data/ --output uploads/anonimizados/
    python scripts/anonimizar.py -i archivo.xlsx -o archivo_anon.xlsx
"""

import os
import sys
import argparse
import hashlib
import re
from pathlib import Path
from typing import Dict, Any
import pandas as pd

NOMBRES_FICTICIOS = [
    "Carlos Mendoza", "María Condori", "Juan Pablo Mamani", "Lucía Fernández",
    "Alejandro Quispe", "Sofía Vargas", "Diego Morales", "Valeria Choque",
    "Andrés Flores", "Camila Gutiérrez", "Rodrigo Rojas", "Elena Salguero",
    "Mateo Romero", "Paola Castillo", "Fernando Aliaga", "Gabriela Torrico",
    "Javier Miranda", "Daniela Mercado", "Hugo Claure", "Natalia Benítez"
]


class AnonimizadorInstitucional:
    def __init__(self, salt: str = "giragroup_privacidad_2026"):
        self.salt = salt
        self.ci_cache: Dict[str, str] = {}
        self.nombre_cache: Dict[str, str] = {}

    def anonimizar_ci(self, ci_raw: Any) -> str:
        if pd.isna(ci_raw) or str(ci_raw).strip() == "":
            return ""
        ci_str = str(ci_raw).strip().split(".")[0]
        if ci_str in self.ci_cache:
            return self.ci_cache[ci_str]

        # Hash determinista de 7 dígitos
        hash_val = hashlib.sha256(f"{ci_str}_{self.salt}".encode("utf-8")).hexdigest()
        ci_anon = str(int(hash_val[:8], 16) % 9000000 + 1000000)
        self.ci_cache[ci_str] = ci_anon
        return ci_anon

    def anonimizar_nombre(self, nombre_raw: Any) -> str:
        if pd.isna(nombre_raw) or str(nombre_raw).strip() == "":
            return ""
        nom_str = str(nombre_raw).strip()
        if nom_str in self.nombre_cache:
            return self.nombre_cache[nom_str]

        hash_idx = int(hashlib.md5(f"{nom_str}_{self.salt}".encode("utf-8")).hexdigest(), 16)
        nombre_anon = NOMBRES_FICTICIOS[hash_idx % len(NOMBRES_FICTICIOS)]
        # Añadir inicial para distinguir homónimos seudónimos
        sufijo_id = (hash_idx % 90) + 10
        nombre_final = f"{nombre_anon} ({sufijo_id})"
        self.nombre_cache[nom_str] = nombre_final
        return nombre_final

    def procesar_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()

        for col in df_out.columns:
            col_lower = str(col).lower().strip()
            # Identificar columnas de CI / Carnet (evitando falsos positivos como 'asistencia')
            es_col_ci = bool(re.search(r'\b(ci|carnet|cedula|identidad)\b', col_lower)) or col_lower in ("ci", "ci_estudiante", "ci_docente", "nro_documento", "documento_identidad")
            if es_col_ci and "asistencia" not in col_lower:
                df_out[col] = df_out[col].apply(self.anonimizar_ci)
            # Identificar columnas de Nombre / Estudiante / Docente
            elif any(k in col_lower for k in ("nombre", "estudiante", "alumno", "docente", "profesor", "apellidos")):
                df_out[col] = df_out[col].apply(self.anonimizar_nombre)
            # Identificar columnas de Email
            elif any(k in col_lower for k in ("email", "correo")):
                df_out[col] = df_out[col].apply(
                    lambda v: f"usuario_{hashlib.md5(str(v).encode()).hexdigest()[:6]}@anonimizado.bo" if pd.notna(v) else ""
                )
            # Identificar columnas de Teléfono
            elif any(k in col_lower for k in ("telefono", "celular", "fono")):
                df_out[col] = df_out[col].apply(
                    lambda v: f"7{str(int(hashlib.md5(str(v).encode()).hexdigest()[:6], 16) % 9000000 + 1000000)[:7]}" if pd.notna(v) else ""
                )

        return df_out

    def procesar_archivo(self, ruta_entrada: Path, ruta_salida: Path):
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        ext = ruta_entrada.suffix.lower()

        print(f"[ANON] Procesando: {ruta_entrada.name} -> {ruta_salida.name}")

        if ext in (".xlsx", ".xls"):
            xls = pd.ExcelFile(ruta_entrada)
            with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    df_anon = self.procesar_dataframe(df)
                    df_anon.to_excel(writer, sheet_name=sheet_name, index=False)
        elif ext == ".csv":
            df = pd.read_csv(ruta_entrada)
            df_anon = self.procesar_dataframe(df)
            df_anon.to_csv(ruta_salida, index=False)
        else:
            print(f"[OMITIDO] Tipo de archivo no procesable: {ruta_entrada}")


def main():
    parser = argparse.ArgumentParser(description="Anonimizador de datos confidenciales GiraGroup.")
    parser.add_argument("--input", "-i", required=True, help="Archivo o directorio de entrada")
    parser.add_argument("--output", "-o", required=True, help="Archivo o directorio de salida")
    parser.add_argument("--salt", default="giragroup_privacidad_2026", help="Salt criptográfico determinista")
    args = parser.parse_args()

    anon = AnonimizadorInstitucional(salt=args.salt)
    in_path = Path(args.input)
    out_path = Path(args.output)

    if in_path.is_file():
        anon.procesar_archivo(in_path, out_path)
    elif in_path.is_dir():
        out_path.mkdir(parents=True, exist_ok=True)
        for f in in_path.glob("**/*"):
            if f.is_file() and f.suffix.lower() in (".xlsx", ".xls", ".csv"):
                rel_path = f.relative_to(in_path)
                target = out_path / rel_path
                anon.procesar_archivo(f, target)
        print(f"[OK] Todos los archivos en {in_path} han sido anonimizados en {out_path}.")
    else:
        print(f"[ERROR] Ruta de entrada no encontrada: {in_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
