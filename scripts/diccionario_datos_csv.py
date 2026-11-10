"""Diccionario de datos: una fila por columna de las 48 tablas de public y las 2 tablas de bi (tabla, columna, tipo, nulo, PK/FK,
referencia, descripción). Tipo, nulo, PK/FK y referencia salen de la base; la descripción se obtiene priorizando comentarios
del catálogo, descripciones formales de los Apéndices de documentación (docs/apendices/diccionario_datos.md) y definiciones
canónicas del sistema.
Uso: DATABASE_URL=... python scripts/diccionario_datos_csv.py -> docs/evidencias/diccionario_datos.csv y ./diccionario_datos.csv
"""
import csv, os, re
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent

# 1. Extracción de descripciones formales desde docs/apendices/diccionario_datos.md
MD_DESC = {}
md_path = ROOT / "docs" / "apendices" / "diccionario_datos.md"
if md_path.exists():
    with open(md_path, "r", encoding="utf-8") as f:
        text_md = f.read()
    pattern = r"\*\*Tabla [FG]\.\d+ Diccionario de datos - ([a-zA-Z0-9_]+)\*\*"
    sections = re.split(pattern, text_md)
    for i in range(1, len(sections), 2):
        tname = sections[i]
        content = sections[i + 1]
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("|") and "Campo" not in line and "---" not in line:
                parts = [p.strip() for p in line.split("|")[1:-1]]
                if len(parts) >= 5:
                    campo = parts[0]
                    desc = parts[4]
                    if desc and desc not in ("—", "Por documentar"):
                        MD_DESC[(tname, campo)] = desc

# 2. Descripciones específicas por tabla y columna (BI, bridges, tareas, extensiones y campos especializados)
DESC_TABLA = {
    # bi.ref_kpi
    ("ref_kpi", "codigo"): "Código único identificador del KPI (ej. FIN-01, ACA-02)",
    ("ref_kpi", "perspectiva"): "Perspectiva del CMI a la que pertenece el KPI (FK a bi.ref_perspectiva)",
    ("ref_kpi", "nombre"): "Nombre formal del indicador de desempeño institucional",
    ("ref_kpi", "descripcion"): "Descripción conceptual, propósito institucional y método de cálculo del KPI",
    ("ref_kpi", "unidad"): "Unidad de medida del indicador (%, Bs, al, score)",
    ("ref_kpi", "sentido"): "Sentido de optimización del indicador (MAX para maximizar, MIN para minimizar)",
    ("ref_kpi", "meta"): "Valor meta institucional definido para el KPI",
    ("ref_kpi", "umbral_verde"): "Umbral límite para estado óptimo / satisfactorio (semáforo verde)",
    ("ref_kpi", "umbral_ambar"): "Umbral límite para estado preventivo / advertencia (semáforo ámbar)",
    ("ref_kpi", "peso"): "Ponderación porcentual del KPI dentro de su perspectiva (suma 100%)",
    ("ref_kpi", "orden"): "Orden secuencial de presentación del indicador en el tablero del CMI",
    ("ref_kpi", "activo"): "Indica si el KPI se encuentra vigente para evaluación estratégica",
    ("ref_kpi", "actualizado_en"): "Fecha y hora del último ajuste de umbrales, metas o parámetros",
    ("ref_kpi", "actualizado_por"): "Usuario o rol responsable de la última actualización del indicador",
    # bi.ref_perspectiva
    ("ref_perspectiva", "codigo"): "Código identificador de la perspectiva del CMI (FINANCIERA, CLIENTES, PROCESOS, APRENDIZAJE)",
    ("ref_perspectiva", "nombre"): "Nombre formal de la perspectiva estratégica institucional",
    ("ref_perspectiva", "objetivo"): "Objetivo estratégico global formulado para la perspectiva",
    ("ref_perspectiva", "pregunta"): "Pregunta guía estratégica del Cuadro de Mando Integral",
    ("ref_perspectiva", "peso"): "Ponderación porcentual de la perspectiva en el índice institucional global",
    ("ref_perspectiva", "orden"): "Orden canónico de presentación en el Cuadro de Mando Integral",
    ("ref_perspectiva", "activa"): "Indica si la perspectiva estratégica está activa en el sistema",
    ("ref_perspectiva", "actualizado_en"): "Fecha y hora de última modificación de la perspectiva",
    ("ref_perspectiva", "actualizado_por"): "Usuario responsable del cambio de configuración de la perspectiva",
    # bridge_modulo_docente
    ("bridge_modulo_docente", "id_asignacion"): "Identificador único de la asignación docente al módulo",
    ("bridge_modulo_docente", "id_modulo"): "Módulo cursado o programado (FK a dim_modulo)",
    ("bridge_modulo_docente", "id_docente"): "Docente asignado para el dictado del módulo (FK a dim_docente)",
    ("bridge_modulo_docente", "id_documento"): "Documento fuente que certifica la asignación académica (FK a dim_origen_documental)",
    ("bridge_modulo_docente", "tipo_docente"): "Modalidad de contratación o rol docente (TITULAR, INVITADO, AUXILIAR)",
    ("bridge_modulo_docente", "grado_academico"): "Máximo grado académico del docente (MAESTRÍA, DOCTORADO, ESPECIALIDAD)",
    ("bridge_modulo_docente", "horas_modulo"): "Carga horaria académica asignada al módulo en horas reloj",
    ("bridge_modulo_docente", "pago_docente"): "Honorario o monto liquidado al docente por el módulo en Bs",
    ("bridge_modulo_docente", "fecha_inicio"): "Fecha de inicio del dictado del módulo",
    ("bridge_modulo_docente", "fecha_fin"): "Fecha de conclusión del dictado del módulo",
    # cache_indice_beto
    ("cache_indice_beto", "hash_texto"): "Hash SHA-256 del texto preprocesado para consulta idempotente",
    ("cache_indice_beto", "modelo"): "Identificador del modelo NLP utilizado (BETO-uncased-v1)",
    ("cache_indice_beto", "indice"): "Puntuación de confianza semántica inferida (rango 0.0000 a 1.0000)",
    ("cache_indice_beto", "creado_en"): "Marca temporal de indexación del resultado en caché",
    # carga_fila_origen
    ("carga_fila_origen", "clave"): "Clave de idempotencia única generada por hash SHA-256 de la fila fuente",
    ("carga_fila_origen", "id_documento"): "Documento de origen al que pertenece la fila procesada",
    ("carga_fila_origen", "tabla"): "Tabla de destino en el Data Warehouse donde se persistió el hecho",
    ("carga_fila_origen", "creado_en"): "Marca temporal de inserción de la fila en el almacén",
    # cat_combinacion_estado
    ("cat_combinacion_estado", "id_combinacion"): "Identificador único de la regla de combinación de estados académicos",
    ("cat_combinacion_estado", "id_estado_academico"): "Estado académico base (FK a cat_estado_academico)",
    ("cat_combinacion_estado", "id_estado_reprobado"): "Causa o subestado de reprobación (FK a cat_estado_reprobado)",
    ("cat_combinacion_estado", "id_estado_arca"): "Estado de trámite ARCA asociado (FK a cat_estado_arca)",
    # cat_concepto_financiero
    ("cat_concepto_financiero", "codigo_concepto"): "Código mnemotécnico del concepto de cobro (ej. MAT, CUO-01)",
    ("cat_concepto_financiero", "tipo_categoria"): "Tipo de concepto financiero (MATRÍCULA, COLEGIATURA, TRÁMITE)",
    # cat_guia_texto_plano
    ("cat_guia_texto_plano", "campos_requeridos"): "Lista de campos obligatorios en formato JSON para la serialización a texto plano",
    # cat_institucion
    ("cat_institucion", "tipo_escala_default"): "Escala de calificación predeterminada (CENTESIMAL_100, DECIMAL_10, VIGESIMAL_20)",
    # cat_institucion_convenio
    ("cat_institucion_convenio", "id_convenio"): "Identificador único del convenio interinstitucional",
    ("cat_institucion_convenio", "nombre_institucion"): "Nombre de la empresa o institución contraparte del convenio",
    ("cat_institucion_convenio", "tipo_convenio"): "Modalidad del acuerdo (CORPORATIVO, DESCUENTO_PLANILLA, BECA)",
    ("cat_institucion_convenio", "descuento_pct"): "Porcentaje de descuento corporativo pactado en aranceles",
    ("cat_institucion_convenio", "variantes_origen"): "Variantes textuales y alias del nombre del convenio encontradas en planillas",
    ("cat_institucion_convenio", "fuente_referencia"): "Documento o resolución formal de aprobación del convenio",
    ("cat_institucion_convenio", "activo"): "Indica si el convenio se encuentra legalmente vigente",
    # cat_mapeo_columna
    ("cat_mapeo_columna", "campo_canonico"): "Nombre canónico del campo al que se estandariza el encabezado del archivo",
    # cat_modulo
    ("cat_modulo", "codigo_modulo"): "Código alfanumérico estandarizado del módulo académico",
    # cat_programa
    ("cat_programa", "tipo_escala"): "Escala de notas aplicable al programa (CENTESIMAL_100 por defecto)",
    # dataops_tarea
    ("dataops_tarea", "id"): "Identificador único secuencial de la tarea DataOps",
    ("dataops_tarea", "id_tarea"): "Identificador alfanumérico de la tarea o lote de procesamiento DataOps",
    ("dataops_tarea", "tipo"): "Tipo de proceso ejecutado (INGESTA, NER_BETO, RESOLUCION_HITL, CARGA_DW)",
    ("dataops_tarea", "tipo_operacion"): "Tipo de proceso ejecutado (INGESTA, LIMPIEZA, RESOLUCION_HITL, CARGA_DW)",
    ("dataops_tarea", "id_lote"): "Lote documental asociado a la ejecución de la tarea",
    ("dataops_tarea", "total"): "Total de registros o filas a procesar en la tarea",
    ("dataops_tarea", "procesados"): "Cantidad de registros procesados con éxito",
    ("dataops_tarea", "resultado"): "Resumen cuantitativo del resultado del procesamiento",
    ("dataops_tarea", "error"): "Detalle o traza técnica del error en caso de fallo",
    ("dataops_tarea", "estado"): "Estado de ejecución del trabajo (PENDIENTE, EN_PROCESO, EXITOSO, FALLIDO)",
    ("dataops_tarea", "iniciado_por"): "Usuario o servicio que disparó la ejecución de la tarea",
    ("dataops_tarea", "iniciado_en"): "Fecha y hora de inicio de ejecución de la tarea",
    ("dataops_tarea", "actualizado_en"): "Marca temporal del último cambio de estado de la tarea",
    ("dataops_tarea", "terminado_en"): "Fecha y hora de finalización del proceso",
    ("dataops_tarea", "finalizado_en"): "Fecha y hora de conclusión de la tarea",
    ("dataops_tarea", "detalles_json"): "Metadatos detallados de ejecución, métricas de calidad y errores en formato JSON",
    # dim_estudiante
    ("dim_estudiante", "genero"): "Género del estudiante (M, F u OTRO)",
    ("dim_estudiante", "edad"): "Edad calculada del estudiante en años",
    ("dim_estudiante", "ocupacion"): "Ocupación o profesión declarada por el estudiante",
    ("dim_estudiante", "estado_civil"): "Estado civil declarado por el estudiante",
    # fact_cobranzas_proyectadas
    ("fact_cobranzas_proyectadas", "monto_esperado"): "Monto proyectado a cobrar en la fecha programada en Bs",
    ("fact_cobranzas_proyectadas", "estado_pago"): "Estado de la cobranza proyectada (PENDIENTE, COBRADO, VENCIDO)",
    # fact_costo_programa
    ("fact_costo_programa", "id_hecho_costo"): "Identificador único del registro de costo operativo del programa",
    ("fact_costo_programa", "id_modulo"): "Programa o módulo académico al que se imputa el costo",
    ("fact_costo_programa", "id_tiempo"): "Fecha de corte mensual de devengamiento del costo",
    ("fact_costo_programa", "costo_docencia_bs"): "Total honorarios pagados a docentes del programa en Bs",
    ("fact_costo_programa", "costo_operativo_bs"): "Gastos operativos directos, insumos y materiales de apoyo en Bs",
    ("fact_costo_programa", "costo_total_bs"): "Suma consolidada del costo docente y operativo imputado en Bs",
    ("fact_costo_programa", "egreso_anterior"): "Monto de egreso acumulado en el periodo previo en Bs",
    ("fact_costo_programa", "egreso_real"): "Egreso real devengado en el periodo en Bs",
    ("fact_costo_programa", "ingreso"): "Total ingreso devengado por el programa en Bs",
    ("fact_costo_programa", "rentabilidad"): "Margen de rentabilidad operativo del programa (ingreso - egreso) en Bs",
    ("fact_costo_programa", "actualizado_en"): "Fecha y hora de la última actualización del balance de costos",
    # fact_rendimiento_academico
    ("fact_rendimiento_academico", "estado_tutoria"): "Estado del seguimiento de tutoría académica (ACTIVO, FINALIZADO, ABANDONO)",
    ("fact_rendimiento_academico", "estado_arca"): "Estado del registro del acta ante el sistema ARCA (PENDIENTE, REGISTRADO)",
    # fact_techo_convenio
    ("fact_techo_convenio", "id_hecho_techo"): "Identificador único del registro de ejecución de techo presupuestario",
    ("fact_techo_convenio", "id_tiempo"): "Fecha de evaluación del cumplimiento del convenio",
    ("fact_techo_convenio", "id_convenio"): "Convenio institucional evaluado",
    ("fact_techo_convenio", "clave_convenio"): "Clave única del convenio corporativo evaluado",
    ("fact_techo_convenio", "institucion"): "Nombre de la institución o empresa titular del convenio",
    ("fact_techo_convenio", "id_convenio_catalogo"): "Enlace al catálogo institucional de convenios (cat_institucion_convenio)",
    ("fact_techo_convenio", "monto_convenio"): "Monto total acordado en el convenio en Bs",
    ("fact_techo_convenio", "monto_techo_bs"): "Tope presupuestario o monto máximo pactado para el convenio en Bs",
    ("fact_techo_convenio", "monto_ejecutado_bs"): "Total recaudado o facturado acumulado bajo el convenio en Bs",
    ("fact_techo_convenio", "saldo_disponible_bs"): "Saldo remanente disponible en el techo presupuestario en Bs",
    ("fact_techo_convenio", "n_inscritos"): "Número de estudiantes matriculados bajo el convenio",
    ("fact_techo_convenio", "fecha_inicio"): "Fecha de inicio de vigencia del convenio",
    ("fact_techo_convenio", "fecha_fin"): "Fecha de finalización de vigencia del convenio",
    ("fact_techo_convenio", "actualizado_en"): "Fecha y hora de la última actualización del techo de convenio",
    # log_inconsistencias
    ("log_inconsistencias", "campo_afectado"): "Nombre de la columna o campo que originó la inconsistencia de datos",
    # powerbi_informe_version
    ("powerbi_informe_version", "id"): "Identificador secuencial de la versión del reporte Power BI",
    ("powerbi_informe_version", "id_version"): "Identificador único de la versión del informe Power BI publicado",
    ("powerbi_informe_version", "nombre_informe"): "Nombre del archivo de informe (.pbix) institucional",
    ("powerbi_informe_version", "ruta"): "Ruta relativa del archivo .pbix en el repositorio o contenedor",
    ("powerbi_informe_version", "tamano_bytes"): "Tamaño en bytes del archivo del informe Power BI",
    ("powerbi_informe_version", "sha256"): "Hash SHA-256 de verificación de integridad del archivo .pbix",
    ("powerbi_informe_version", "hash_sha256"): "Hash SHA-256 de integridad del reporte publicado",
    ("powerbi_informe_version", "nota"): "Comentario o bitácora de control de cambios de la versión del informe",
    ("powerbi_informe_version", "vigente"): "True si esta versión es la actualmente desplegada en producción",
    ("powerbi_informe_version", "subido_por"): "Usuario responsable de subir y versionar el informe",
    ("powerbi_informe_version", "subido_en"): "Fecha y hora en que se subió la versión del reporte",
    ("powerbi_informe_version", "publicado_en"): "Fecha y hora de publicación o sincronización con el servicio Power BI",
    ("powerbi_informe_version", "publicado_por"): "Usuario o rol responsable del despliegue del reporte"
}

# 3. Diccionario general por nombre de columna común
DESC = {
    "id_documento": "Documento de origen (dim_origen_documental) del que viene el dato",
    "id_tiempo": "Día del calendario (dim_tiempo)",
    "id_modulo": "Módulo o programa (dim_modulo)",
    "id_estudiante": "Estudiante (dim_estudiante)",
    "id_docente": "Docente (dim_docente)",
    "id_categoria": "Categoría financiera (dim_categoria_financiera)",
    "id_categoria_fin": "Identificador de la categoría financiera estándar",
    "id_institucion": "Institución institucional de posgrado (cat_institucion)",
    "fk_estado": "Estado de la llave: A CI exacta, B coincidencia aproximada, C miembro nuevo sin candidatos",
    "requiere_revision": "True si el hecho espera revisión humana",
    "motivo_revision": "Motivo de la marca de revisión o nota informativa (LIMITACION_FUENTE, TIEMPO_IMPUTADO, RESUELTO_HUMANO)",
    "nivel_confianza_ia": "Índice de confianza BETO del registro (nulo si las reglas resolvieron la línea sin consultar el modelo)",
    "nivel_confianza": "Índice de confianza BETO asociado al caso",
    "nombre_completo": "Nombre completo de la persona",
    "ci": "Cédula de identidad con complemento",
    "ci_numero": "Número de la cédula normalizado",
    "clave_respuesta": "Hash estable de la fila y la pregunta (idempotencia)",
    "clave_origen": "Clave de idempotencia (hash del archivo, tipo, motivo y valor)",
    "clave": "Clave de idempotencia por fila de origen",
    "created_at": "Fecha y hora de creación",
    "fecha_registro": "Fecha y hora de inserción del registro",
    "monto_ejecutado": "Monto ejecutado (recaudación) en Bs",
    "monto_meta": "Meta del mes en Bs",
    "puntuacion": "Puntaje de la respuesta",
    "escala_max": "Máximo de la escala de la pregunta (5 o 10)",
    "comentario": "Comentario libre de la respuesta",
    "tipo_pregunta": "DOCENTE, INSTITUCIONAL o NPS",
    "nota_final": "Nota final normalizada a base 100",
    "asistencia_pct": "Porcentaje de asistencia",
    "monto_deuda": "Deuda del estudiante en Bs",
    "monto_pagado": "Monto pagado en Bs",
    "cuotas_impagas": "Cuotas impagas",
    "estado_cartera": "Estado de la cartera (Vigente, Mora...)",
    "inscritos": "Inscritos del mes en el módulo",
    "leads": "Interesados del mes",
    "reservas": "Reservas del mes",
    "periodo_mes": "Período AAAA-MM",
    "gestion": "Año (gestión)",
    "mes": "Mes (1-12)",
    "fecha": "Fecha",
    "pos_code": "Código POS del programa o módulo (POS-xxxx[-Mnn])",
    "nombre_modulo": "Nombre del módulo o programa",
    "programa": "Programa al que pertenece",
    "motivo": "Motivo por el que el caso llegó a la cola",
    "texto_original": "Texto original del caso",
    "tipo_regla": "Regla que generó el registro del log",
    "estado_resolucion": "Estado de resolución del caso",
    "resuelto": "True si el caso ya fue resuelto",
    "hash_sha256": "Hash SHA-256 del archivo",
    "nombre_archivo": "Nombre del archivo subido",
    "tipo_fuente": "Tipo de fuente detectado (ACTA, COBRANZA, RENTABILIDAD...)",
    "email": "Correo electrónico",
    "role": "Rol del usuario",
    "username": "Nombre de usuario",
    "version": "Versión del registro (control optimista)",
    "codigo": "Código del indicador o perspectiva",
    "meta": "Meta del indicador",
    "umbral_verde": "Umbral del semáforo verde",
    "umbral_ambar": "Umbral del semáforo ámbar",
    "nombre": "Nombre",
    "descripcion": "Descripción",
    "orden": "Orden de presentación",
    "activo": "True si el registro está vigente",
    "applied_at": "Fecha de aplicación de la migración",
    "version_migracion": "Versión de la migración",
}

TABLAS_BI = ("ref_kpi", "ref_perspectiva")

eng = create_engine(os.environ["DATABASE_URL"])
filas = []
with eng.connect() as c:
    cols = c.execute(text("""
        SELECT c.table_schema, c.table_name, c.column_name, c.data_type, c.character_maximum_length, c.numeric_precision, c.numeric_scale, c.is_nullable, c.ordinal_position
        FROM information_schema.columns c JOIN information_schema.tables t ON t.table_schema=c.table_schema AND t.table_name=c.table_name
        WHERE t.table_type='BASE TABLE' AND ((c.table_schema='public') OR (c.table_schema='bi' AND c.table_name = ANY(:bi)))
        ORDER BY c.table_schema, c.table_name, c.ordinal_position"""), {"bi": list(TABLAS_BI)}).all()
    pk = {(r[0], r[1], r[2]) for r in c.execute(text(
        "SELECT kcu.table_schema, kcu.table_name, kcu.column_name FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu "
        "ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema WHERE tc.constraint_type='PRIMARY KEY'"))}
    fk = {(r[0], r[1], r[2]): f"{r[3]}.{r[4]}" for r in c.execute(text(
        "SELECT kcu.table_schema, kcu.table_name, kcu.column_name, ccu.table_schema||'.'||ccu.table_name, ccu.column_name "
        "FROM information_schema.table_constraints tc JOIN information_schema.key_column_usage kcu ON tc.constraint_name=kcu.constraint_name AND tc.table_schema=kcu.table_schema "
        "JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name=tc.constraint_name WHERE tc.constraint_type='FOREIGN KEY'"))}
    coment = {(r[0], r[1], r[2]): r[3] for r in c.execute(text(
        "SELECT n.nspname, cl.relname, a.attname, d.description FROM pg_description d JOIN pg_class cl ON cl.oid=d.objoid JOIN pg_namespace n ON n.oid=cl.relnamespace "
        "JOIN pg_attribute a ON a.attrelid=cl.oid AND a.attnum=d.objsubid WHERE d.objsubid>0"))}

for sch, tab, col, tipo, ln, prec, esc, nulo, _ in cols:
    t = tipo + (f"({ln})" if ln else f"({prec},{esc})" if tipo == "numeric" and prec else "")
    k = (sch, tab, col)
    desc = (
        coment.get(k)
        or DESC_TABLA.get((tab, col))
        or MD_DESC.get((tab, col))
        or DESC.get(col)
    )
    if not desc:
        desc = "Columna " + col.replace("_", " ") + " (derivada del nombre)"
    rol = "PK" if k in pk else ""
    if k in fk:
        rol = (rol + "+FK") if rol else "FK"
    filas.append([f"{sch}.{tab}", col, t, "SI" if nulo == "YES" else "NO", rol, fk.get(k, ""), desc])

tablas = {f[0] for f in filas}
assert sum(1 for t in tablas if t.startswith("public.")) == 48 and sum(1 for t in tablas if t.startswith("bi.")) == 2, tablas

# Guardar en docs/evidencias/diccionario_datos.csv y en la raíz ./diccionario_datos.csv
destinos = [
    ROOT / "docs" / "evidencias" / "diccionario_datos.csv",
    ROOT / "diccionario_datos.csv"
]
for dest in destinos:
    with open(dest, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tabla", "columna", "tipo", "nulo", "pk_fk", "referencia", "descripcion"])
        w.writerows(filas)

print(len(tablas), "tablas,", len(filas), "columnas;", sum(1 for f in filas if "derivada del nombre" in f[6]), "con descripción derivada del nombre")
