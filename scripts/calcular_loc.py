import os
import csv
from pathlib import Path

# Extensions considered as code
EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".css": "CSS",
    ".html": "HTML",
    ".sql": "SQL",
    ".json": "JSON"
}

EXCLUDE_DIRS = {
    "node_modules", ".venv", "__pycache__", ".git", ".pytest_cache", 
    "dist", "build", ".vscode", ".idea", "coverage", "beto_local"
}

def count_file(filepath):
    total = 0
    blank = 0
    comment = 0
    code = 0
    ext = filepath.suffix.lower()
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception:
        return 0, 0, 0, 0

    total = len(lines)
    in_block_comment = False

    for line in lines:
        s = line.strip()
        if not s:
            blank += 1
            continue
        
        # Python comments
        if ext == '.py':
            if in_block_comment:
                comment += 1
                if '"""' in s or "'''" in s:
                    in_block_comment = False
                continue
            if s.startswith('"""') or s.startswith("'''"):
                comment += 1
                if s.count('"""') == 1 or s.count("'''") == 1:
                    in_block_comment = True
                continue
            if s.startswith('#'):
                comment += 1
                continue
            code += 1
        # JS / TS / CSS / SQL comments
        elif ext in ('.js', '.jsx', '.ts', '.tsx', '.css'):
            if in_block_comment:
                comment += 1
                if '*/' in s:
                    in_block_comment = False
                continue
            if s.startswith('/*'):
                comment += 1
                if '*/' not in s:
                    in_block_comment = True
                continue
            if s.startswith('//'):
                comment += 1
                continue
            code += 1
        elif ext == '.sql':
            if s.startswith('--'):
                comment += 1
                continue
            code += 1
        else:
            code += 1

    return total, blank, comment, code

def analyze_directory(base_dir, group_name):
    records = []
    base_path = Path(base_dir)
    
    # Analyze by sub-packages/folders
    # First top-level files
    top_files = [f for f in base_path.glob("*") if f.is_file() and f.suffix.lower() in EXTENSIONS]
    if top_files:
        t_tot, t_blk, t_com, t_cod = 0, 0, 0, 0
        for f in top_files:
            tot, blk, com, cod = count_file(f)
            t_tot += tot
            t_blk += blk
            t_com += com
            t_cod += cod
        records.append({
            "Grupo": group_name,
            "Módulo / Subcarpeta": f"{base_path.name} (raíz)",
            "Archivos": len(top_files),
            "Líneas Totales": t_tot,
            "Líneas en Blanco": t_blk,
            "Comentarios": t_com,
            "Código (SLOC)": t_cod
        })

    for item in sorted(base_path.iterdir()):
        if item.is_dir() and item.name not in EXCLUDE_DIRS:
            sub_files = []
            for root, dirs, files in os.walk(item):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for file in files:
                    fp = Path(root) / file
                    if fp.suffix.lower() in EXTENSIONS:
                        sub_files.append(fp)
            
            if sub_files:
                t_tot, t_blk, t_com, t_cod = 0, 0, 0, 0
                for f in sub_files:
                    tot, blk, com, cod = count_file(f)
                    t_tot += tot
                    t_blk += blk
                    t_com += com
                    t_cod += cod
                records.append({
                    "Grupo": group_name,
                    "Módulo / Subcarpeta": f"{base_path.name}/{item.name}",
                    "Archivos": len(sub_files),
                    "Líneas Totales": t_tot,
                    "Líneas en Blanco": t_blk,
                    "Comentarios": t_com,
                    "Código (SLOC)": t_cod
                })
    return records

def main():
    results = []
    results.extend(analyze_directory("backend", "Backend"))
    results.extend(analyze_directory("pipeline", "Pipeline / NLP"))
    results.extend(analyze_directory("services", "Microservicios"))
    results.extend(analyze_directory("frontend/src", "Frontend (React)"))
    results.extend(analyze_directory("db", "Base de Datos"))

    # Write CSV
    out_csv = Path("output/inventario_loc_proyecto.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Grupo", "Módulo / Subcarpeta", "Archivos", "Líneas Totales", "Líneas en Blanco", "Comentarios", "Código (SLOC)"])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Inventario guardado en {out_csv}")
    for r in results:
        print(f"{r['Grupo']} | {r['Módulo / Subcarpeta']} | Files: {r['Archivos']} | LOC: {r['Código (SLOC)']}")

if __name__ == "__main__":
    main()
