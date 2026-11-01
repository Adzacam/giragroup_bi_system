"""
populate_dim_tiempo.py — Generador e Inserctor de Dimensión Tiempo (Grano Diario)

Genera el calendario analítico para el Data Warehouse (giragroup_db):
- Rango: 2022-01-01 a 2027-12-31 (2,191 días exactos).
- Clave primaria natural numérica YYYYMMDD.
- Atributos analíticos: semestre, trimestre, semana ISO, nombre de día/mes, flags fin de semana.
- Soporta inserción directa en PostgreSQL e idempotencia total (ON CONFLICT).
- Genera también el archivo SQL de siembra 'db/seeds/seed_dim_tiempo.sql'.
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Nombres en español
NOMBRES_MESES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
NOMBRES_DIAS = [
    "", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"
]


def generar_registros_tiempo(fecha_inicio: date, fecha_fin: date) -> list[dict]:
    """Genera una lista de diccionarios con los atributos de cada día calendario."""
    registros = []
    actual = fecha_inicio
    delta = timedelta(days=1)

    while actual <= fecha_fin:
        id_tiempo = actual.year * 10000 + actual.month * 100 + actual.day
        semestre = 1 if actual.month <= 6 else 2
        trimestre = (actual.month - 1) // 3 + 1
        semana_iso = actual.isocalendar()[1]
        dia_semana = actual.isoweekday()  # 1=Lunes .. 7=Domingo
        es_fin_semana = dia_semana in (6, 7)
        periodo_mes = f"{actual.year:04d}-{actual.month:02d}"

        registros.append({
            "id_tiempo": id_tiempo,
            "fecha": str(actual),
            "gestion": actual.year,
            "semestre": semestre,
            "trimestre": trimestre,
            "mes": actual.month,
            "nombre_mes": NOMBRES_MESES[actual.month],
            "semana_iso": semana_iso,
            "dia_mes": actual.day,
            "dia_semana": dia_semana,
            "nombre_dia": NOMBRES_DIAS[dia_semana],
            "es_fin_semana": es_fin_semana,
            "periodo_mes": periodo_mes,
        })
        actual += delta

    return registros


def exportar_sql(registros: list[dict], ruta_archivo: str):
    """Exporta los registros a un script SQL con ON CONFLICT para inserción directa."""
    lineas = [
        "-- =============================================================================",
        "-- SEMILLA DIMENSIÓN TIEMPO (2022 a 2027 - Grano Diario)",
        "-- Total registros: " + str(len(registros)),
        "-- =============================================================================",
        "INSERT INTO public.dim_tiempo (id_tiempo, fecha, gestion, semestre, trimestre, mes, nombre_mes, semana_iso, dia_mes, dia_semana, nombre_dia, es_fin_semana, periodo_mes)",
        "VALUES",
    ]
    valores = []
    for r in registros:
        val = (
            f"  ({r['id_tiempo']}, '{r['fecha']}', {r['gestion']}, {r['semestre']}, {r['trimestre']}, "
            f"{r['mes']}, '{r['nombre_mes']}', {r['semana_iso']}, {r['dia_mes']}, {r['dia_semana']}, "
            f"'{r['nombre_dia']}', {'TRUE' if r['es_fin_semana'] else 'FALSE'}, '{r['periodo_mes']}')"
        )
        valores.append(val)

    lineas.append(",\n".join(valores))
    lineas.append("ON CONFLICT (id_tiempo) DO NOTHING;\n")

    os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    print(f"-> Archivo SQL generado exitosamente: {ruta_archivo} ({len(registros)} registros)")


def sembrar_en_postgres(registros: list[dict], db_url: str = None) -> bool:
    """Inserta en PostgreSQL si la base de datos está disponible."""
    try:
        from sqlalchemy import create_engine, text
        from dotenv import load_dotenv
        load_dotenv()

        url = db_url or os.getenv("DATABASE_URL")
        if not url:
            return False

        # Si corre en host local y apunta a giragroup_db, ajustar a localhost
        if "giragroup_db" in url and not os.getenv("DOCKER_ENV"):
            url = url.replace("giragroup_db", "localhost")

        engine = create_engine(url, connect_args={"connect_timeout": 3})
        with engine.begin() as conn:
            stmt = text("""
                INSERT INTO public.dim_tiempo (
                    id_tiempo, fecha, gestion, semestre, trimestre, mes,
                    nombre_mes, semana_iso, dia_mes, dia_semana, nombre_dia,
                    es_fin_semana, periodo_mes
                ) VALUES (
                    :id_tiempo, :fecha, :gestion, :semestre, :trimestre, :mes,
                    :nombre_mes, :semana_iso, :dia_mes, :dia_semana, :nombre_dia,
                    :es_fin_semana, :periodo_mes
                ) ON CONFLICT (id_tiempo) DO NOTHING
            """)
            conn.execute(stmt, registros)
        print(f"-> Inserción exitosa en PostgreSQL ({len(registros)} registros)")
        return True
    except Exception as e:
        print(f"-> Nota: No se insertó directamente en Postgres ({e}). El archivo SQL quedó listo.")
        return False


def main():
    inicio = date(2022, 1, 1)
    fin = date(2027, 12, 31)
    registros = generar_registros_tiempo(inicio, fin)
    print(f"Generados {len(registros)} días entre {inicio} y {fin}.")

    ruta_sql = os.path.join(os.path.dirname(__file__), "seed_dim_tiempo.sql")
    exportar_sql(registros, ruta_sql)
    sembrar_en_postgres(registros)


if __name__ == "__main__":
    main()
