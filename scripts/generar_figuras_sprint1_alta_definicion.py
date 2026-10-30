"""
Script para la regeneración integral de las Figuras del Sprint 1 para la Tesis de Grado.
Estilo: Académico formal / monocromático (escala de grises, fondo blanco #FFFFFF, líneas nítidas, tipografía sans-serif limpia).
Regla estricta: CERO títulos incrustados en la imagen (los títulos van exclusivamente en las leyendas de Word).
Resolución: 300 DPI, ancho >= 2200 px.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Configuración global
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['figure.facecolor'] = '#FFFFFF'
plt.rcParams['axes.facecolor'] = '#FFFFFF'

OUTPUT_DIRS = [
    r"docs\images",
    r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0"
]

def save_fig(fig, filename):
    for d in OUTPUT_DIRS:
        if os.path.exists(d):
            path = os.path.join(d, filename)
            fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
            print(f"Guardado exitosamente: {path}")

# ==============================================================================
# FIGURA 3.2: ARQUITECTURA FÍSICA Y ORQUESTACIÓN DE CONTENEDORES
# ==============================================================================
def generar_figura_3_2():
    fig, ax = plt.subplots(figsize=(15, 9.5), dpi=300)
    ax.set_xlim(0, 150)
    ax.set_ylim(0, 95)
    ax.axis('off')

    # Borde de Servidor Host
    host_rect = patches.FancyBboxPatch((4, 3), 142, 75, boxstyle="square,pad=0",
                                       ec="#222222", fc="#FAFAFA", lw=1.8)
    ax.add_patch(host_rect)
    ax.text(6, 76, "Servidor Host / Entorno de Virtualización (Docker Engine 24.x | Red Bridge 'giragroup_network')",
            fontsize=10.5, fontweight='bold', color="#222222")

    # Clientes Externos (Arriba a la derecha)
    client_box = patches.FancyBboxPatch((90, 81), 56, 11, boxstyle="square,pad=0",
                                        ec="#222222", fc="#FFFFFF", lw=1.4)
    ax.add_patch(client_box)
    ax.text(92, 89.5, "Clientes Externos / Estaciones de Trabajo", fontsize=9.5, fontweight='bold', color="#222222")

    spa_box = patches.Rectangle((92, 82.5), 25, 6, ec="#444444", fc="#F5F5F5", lw=1.1)
    ax.add_patch(spa_box)
    ax.text(104.5, 85.5, "Navegador Web / SPA\n(React 18 Dashboard)", fontsize=8, ha='center', va='center')

    pbi_box = patches.Rectangle((119, 82.5), 25, 6, ec="#444444", fc="#F5F5F5", lw=1.1)
    ax.add_patch(pbi_box)
    ax.text(131.5, 85.5, "Power BI Desktop\n(giragroup_cmi.pbix)", fontsize=8, ha='center', va='center')

    # 1. Reverse Proxy / Gateway
    gw_rect = patches.FancyBboxPatch((60, 57), 38, 14, boxstyle="square,pad=0",
                                     ec="#111111", fc="#FFFFFF", lw=1.5)
    ax.add_patch(gw_rect)
    ax.text(79, 68, "1. Reverse Proxy & Gateway\ngiragroup_gateway (Nginx :80)",
            ha='center', va='center', fontsize=9.5, fontweight='bold')
    ax.text(79, 61, "Enrutador perimetral HTTP/WS\nControl de CORS y Proxies",
            ha='center', va='center', fontsize=8, color="#444444")

    # 2. Frontend
    web_rect = patches.FancyBboxPatch((8, 57), 34, 14, boxstyle="square,pad=0",
                                      ec="#222222", fc="#FFFFFF", lw=1.3)
    ax.add_patch(web_rect)
    ax.text(25, 67, "2. Capa de Presentación\ngiragroup_web (:5173)",
            ha='center', va='center', fontsize=9, fontweight='bold')
    ax.text(25, 61, "React 18 + Vite + Tailwind\nRouter: / (Proxy Reverso)",
            ha='center', va='center', fontsize=8, color="#444444")

    # 3. Core API & Pipeline
    core_rect = patches.FancyBboxPatch((8, 30), 40, 21, boxstyle="square,pad=0",
                                       ec="#111111", fc="#FFFFFF", lw=1.5)
    ax.add_patch(core_rect)
    ax.text(28, 48, "3. Backend Núcleo (Core)", fontsize=9.5, fontweight='bold')
    
    api_box = patches.Rectangle((10, 40), 36, 6.5, ec="#444444", fc="#F5F5F5", lw=1.1)
    ax.add_patch(api_box)
    ax.text(28, 43.2, "giragroup_api (FastAPI Core :8000)\n/api/v1/forecast, /kpis, /dataops", fontsize=8, ha='center', va='center')

    pipe_box = patches.Rectangle((10, 31.5), 36, 6.5, ec="#444444", fc="#F5F5F5", lw=1.1)
    ax.add_patch(pipe_box)
    ax.text(28, 34.7, "giragroup_pipeline (PyTorch :8006)\nMotor BETO NER (Inferencia Local)", fontsize=8, ha='center', va='center')

    # 4. Microservicios Auxiliares
    aux_rect = patches.FancyBboxPatch((52, 30), 54, 21, boxstyle="square,pad=0",
                                      ec="#222222", fc="#FFFFFF", lw=1.4)
    ax.add_patch(aux_rect)
    ax.text(79, 48.5, "4. Microservicios Auxiliares Especializados", fontsize=9.5, fontweight='bold', ha='center')

    svc1 = patches.Rectangle((54, 40), 24, 6.5, ec="#444444", fc="#F5F5F5", lw=1)
    ax.add_patch(svc1)
    ax.text(66, 43.2, "auth-service (:8001)\n/api/v1/auth, /users", fontsize=7.5, ha='center', va='center')

    svc2 = patches.Rectangle((80, 40), 24, 6.5, ec="#444444", fc="#F5F5F5", lw=1)
    ax.add_patch(svc2)
    ax.text(92, 43.2, "notifications-service (:8002)\n/api/v1/notifications, /ws", fontsize=7.5, ha='center', va='center')

    svc3 = patches.Rectangle((54, 32), 15, 6.5, ec="#444444", fc="#F5F5F5", lw=1)
    ax.add_patch(svc3)
    ax.text(61.5, 35.2, "analytics-service\n(:8003)", fontsize=7.5, ha='center', va='center')

    svc4 = patches.Rectangle((71, 32), 16, 6.5, ec="#444444", fc="#F5F5F5", lw=1)
    ax.add_patch(svc4)
    ax.text(79, 35.2, "audit-service\n(:8004) /audit", fontsize=7.5, ha='center', va='center')

    svc5 = patches.Rectangle((89, 32), 15, 6.5, ec="#444444", fc="#F5F5F5", lw=1)
    ax.add_patch(svc5)
    ax.text(96.5, 35.2, "storage-service\n(:8005) /storage", fontsize=7.5, ha='center', va='center')

    # 5. Persistencia y Almacenamiento
    db_rect = patches.FancyBboxPatch((8, 6), 98, 19, boxstyle="square,pad=0",
                                     ec="#111111", fc="#FFFFFF", lw=1.5)
    ax.add_patch(db_rect)
    ax.text(57, 22.5, "5. Capa de Persistencia Relacional y Dimensional (PostgreSQL 16)", fontsize=9.5, fontweight='bold', ha='center')

    db1 = patches.Rectangle((12, 8), 44, 12, ec="#333333", fc="#F5F5F5", lw=1.2)
    ax.add_patch(db1)
    ax.text(34, 15.5, "giragroup_db (Puerto :5432)\nData Warehouse Constelación (24 tablas)\nVolumen: postgres_data", fontsize=8.5, ha='center', va='center')

    db2 = patches.Rectangle((60, 8), 42, 12, ec="#333333", fc="#F5F5F5", lw=1.2)
    ax.add_patch(db2)
    ax.text(81, 15.5, "giragroup_catalog_db (Puerto :5433)\nCatálogos Académicos 3NF\nVolumen: catalog_postgres_data", fontsize=8.5, ha='center', va='center')

    # 6. Bind Mounts & Storage
    bm_rect = patches.FancyBboxPatch((110, 18), 32, 28, boxstyle="square,pad=0",
                                     ec="#444444", fc="#F9F9F9", lw=1.2)
    ax.add_patch(bm_rect)
    ax.text(126, 42.5, "Almacenamiento Local", fontsize=9, fontweight='bold', ha='center')
    ax.text(126, 36, "Bind Mount:\n./uploads\n-> /app/uploads", fontsize=8, ha='center', va='center')
    ax.text(126, 26, "Modelos Safetensors:\n./pipeline/semantic/beto_local\n-> /app/beto_local", fontsize=7.5, ha='center', va='center')

    # Conexiones / Flechas
    arrow = dict(arrowstyle="->", lw=1.3, color="#222222")

    # Clientes -> Gateway
    ax.annotate("", xy=(85, 71), xytext=(98, 82.5), arrowprops=arrow)
    ax.text(94, 76, "HTTP :80", fontsize=8, fontweight='bold')

    # Power BI -> PostgreSQL :5432
    ax.annotate("", xy=(56, 17), xytext=(131.5, 82.5),
                arrowprops=dict(arrowstyle="->", lw=1.4, color="#111111", linestyle='--'))
    ax.text(133, 50, "PostgreSQL Wire (:5432)\nConexión Directa DirectQuery", fontsize=8, rotation=270, ha='center')

    # Gateway -> Frontend
    ax.annotate("", xy=(42, 64), xytext=(60, 64), arrowprops=arrow)
    ax.text(51, 65, "/ (Proxy)", fontsize=7.5, ha='center')

    # Gateway -> Core API
    ax.annotate("", xy=(30, 46.5), xytext=(65, 57), arrowprops=arrow)
    ax.text(40, 52, "/api/v1/forecast, /kpis", fontsize=7.5, ha='center')

    # Gateway -> Microservicios Auxiliares
    ax.annotate("", xy=(66, 46.5), xytext=(72, 57), arrowprops=arrow)
    ax.annotate("", xy=(92, 46.5), xytext=(85, 57), arrowprops=arrow)
    ax.annotate("", xy=(80, 38.5), xytext=(80, 57), arrowprops=arrow)

    # Core API -> Pipeline (NER)
    ax.annotate("", xy=(28, 38), xytext=(28, 40), arrowprops=dict(arrowstyle="<->", lw=1.3, color="#111111"))
    ax.text(30, 39, "Inferencia :8006", fontsize=7.5)

    # Core -> DB
    ax.annotate("", xy=(30, 20), xytext=(30, 31.5), arrowprops=arrow)
    ax.text(32, 25, "TCP :5432", fontsize=7.5)

    # Pipeline -> Catalog DB
    ax.annotate("", xy=(75, 20), xytext=(46, 33), arrowprops=arrow)
    ax.text(62, 26, "RapidFuzz :5433", fontsize=7.5)

    save_fig(fig, "figura_3_2_arquitectura_fisica_orquestacion.png")
    plt.close(fig)

# ==============================================================================
# FIGURA 3.3: DIAGRAMA UML DE DESPLIEGUE EN DOCKER COMPOSE
# ==============================================================================
def generar_figura_3_3():
    fig, ax = plt.subplots(figsize=(15.5, 10.5), dpi=300)
    ax.set_xlim(0, 155)
    ax.set_ylim(0, 105)
    ax.axis('off')

    # Device: Estación de Trabajo Cliente
    client_dev = patches.FancyBboxPatch((85, 87), 65, 15, boxstyle="square,pad=0",
                                        ec="#111111", fc="#FAFAFA", lw=1.5)
    ax.add_patch(client_dev)
    ax.text(87, 100, "«device»\nEstación de Trabajo Cliente", fontsize=9, fontweight='bold')

    # Sub-ambientes cliente
    env1 = patches.Rectangle((112, 89), 18, 11, ec="#333333", fc="#FFFFFF", lw=1)
    ax.add_patch(env1)
    ax.text(121, 98.2, "«execution env»\nNavegador Web", fontsize=7.5, ha='center')
    ax.text(121, 92, "«artifact»\nApp.jsx\nReact 18 SPA", fontsize=7, ha='center', color="#333333")

    env2 = patches.Rectangle((132, 89), 16, 11, ec="#333333", fc="#FFFFFF", lw=1)
    ax.add_patch(env2)
    ax.text(140, 98.2, "«execution env»\nPower BI", fontsize=7.5, ha='center')
    ax.text(140, 92, "«artifact»\ngiragroup_cmi.pbix\nMotor CMI", fontsize=7, ha='center', color="#333333")

    # Device: Servidor Host
    host_dev = patches.FancyBboxPatch((5, 4), 145, 79, boxstyle="square,pad=0",
                                      ec="#111111", fc="#FAFAFA", lw=1.8)
    ax.add_patch(host_dev)
    ax.text(7, 81, "«device»\nServidor Host (Docker Engine 24.x | SO: Linux / Windows Server)", fontsize=9.5, fontweight='bold')

    # Nodo Gateway
    gw = patches.Rectangle((62, 63), 32, 13, ec="#222222", fc="#FFFFFF", lw=1.3)
    ax.add_patch(gw)
    ax.text(78, 73.5, "«execution env»\ngiragroup_gateway (nginx:alpine)", fontsize=8, fontweight='bold', ha='center')
    ax.text(78, 66.5, "«artifact» nginx.conf\nPuerto Expuesto: 80", fontsize=7.5, ha='center', color="#333333")

    # Nodo Frontend
    web = patches.Rectangle((8, 63), 32, 13, ec="#222222", fc="#FFFFFF", lw=1.2)
    ax.add_patch(web)
    ax.text(24, 73.5, "«execution env»\ngiragroup_web (node:20-alpine)", fontsize=8, fontweight='bold', ha='center')
    ax.text(24, 66.5, "«artifact» package.json\n«artifact» App.jsx\nPuerto: 5173", fontsize=7.5, ha='center', color="#333333")

    # Nodo API Core
    api = patches.Rectangle((8, 41), 38, 17, ec="#111111", fc="#FFFFFF", lw=1.4)
    ax.add_patch(api)
    ax.text(27, 55.5, "«execution env»\ngiragroup_api (python:3.12-slim)", fontsize=8, fontweight='bold', ha='center')
    ax.text(27, 47, "«artifact» main.py (FastAPI BETO Core)\n«artifact» dw_loader.py\n«artifact» quality_rules.py\nPuerto Interno: 8000", fontsize=7.5, ha='center', color="#333333")

    # Nodo Pipeline BETO
    pipe = patches.Rectangle((8, 22), 38, 16, ec="#111111", fc="#FFFFFF", lw=1.4)
    ax.add_patch(pipe)
    ax.text(27, 35.5, "«execution env»\ngiragroup_pipeline (python:3.11-slim)", fontsize=8, fontweight='bold', ha='center')
    ax.text(27, 27.5, "«artifact» inference_server.py\n«artifact» model.safetensors (beto_local)\n«artifact» ner_engine.py\nPuerto Interno: 8006", fontsize=7.5, ha='center', color="#333333")

    # Microservicios auxiliares
    aux_nodes = [
        (49, 46, "giragroup_auth_svc\n(python:3.11-slim)", "«artifact» auth_service.py\n«artifact» main.py (:8001)"),
        (74, 46, "giragroup_notifications_svc\n(python:3.11-slim)", "«artifact» ws_manager.py\n«artifact» main.py (:8002)"),
        (99, 46, "giragroup_analytics_svc\n(python:3.11-slim)", "«artifact» main.py\nPuerto Interno: 8003"),
        (49, 29, "giragroup_audit_svc\n(python:3.11-slim)", "«artifact» audit.py\n«artifact» main.py (:8004)"),
        (74, 29, "giragroup_storage_svc\n(python:3.11-slim)", "«artifact» uploader.py\n«artifact» main.py (:8005)"),
    ]

    for x, y, name, art in aux_nodes:
        box = patches.Rectangle((x, y), 23, 14, ec="#333333", fc="#FFFFFF", lw=1)
        ax.add_patch(box)
        ax.text(x + 11.5, y + 10.5, f"«execution env»\n{name}", fontsize=7.5, fontweight='bold', ha='center')
        ax.text(x + 11.5, y + 4.5, art, fontsize=7, ha='center', color="#333333")

    # Nodos Bases de Datos
    db1 = patches.Rectangle((8, 6), 46, 13, ec="#111111", fc="#FFFFFF", lw=1.5)
    ax.add_patch(db1)
    ax.text(31, 15.5, "«execution env»\ngiragroup_db (postgres:16-alpine)", fontsize=8.5, fontweight='bold', ha='center')
    ax.text(31, 9.5, "«artifact» schema.sql (Constelación DWH - 24 tablas)\n«artifact» seed_dim_tiempo.sql | Puerto: 5432", fontsize=7.5, ha='center', color="#333333")

    db2 = patches.Rectangle((57, 6), 44, 13, ec="#111111", fc="#FFFFFF", lw=1.3)
    ax.add_patch(db2)
    ax.text(79, 15.5, "«execution env»\ngiragroup_catalog_db (postgres:16-alpine)", fontsize=8.5, fontweight='bold', ha='center')
    ax.text(79, 9.5, "«artifact» schema_catalogos.sql\n«artifact» seed_catalogos.sql | Puerto: 5433", fontsize=7.5, ha='center', color="#333333")

    # Bind mount & Volumes
    vol_box = patches.Rectangle((104, 6), 42, 20, ec="#444444", fc="#FFFFFF", lw=1.1)
    ax.add_patch(vol_box)
    ax.text(125, 23, "Almacenamiento Persistente", fontsize=8.5, fontweight='bold', ha='center')
    ax.text(125, 17, "«volume» postgres_data\n-> /var/lib/postgresql/data\n«volume» catalog_postgres_data", fontsize=7.5, ha='center')
    ax.text(125, 9, "«bind mount» ./uploads\n-> /app/uploads", fontsize=7.5, ha='center', color="#222222")

    # Conexiones
    arrow = dict(arrowstyle="->", lw=1.3, color="#222222")

    # Navegador a Gateway
    ax.annotate("", xy=(85, 76), xytext=(118, 89), arrowprops=arrow)
    ax.text(105, 83, "HTTP/WS :80", fontsize=8)

    # Power BI a giragroup_db
    ax.annotate("", xy=(54, 13), xytext=(140, 89), arrowprops=dict(arrowstyle="->", lw=1.4, color="#111111", linestyle="--"))
    ax.text(142, 55, "TCP Wire :5432", fontsize=8, rotation=270, ha='center')

    # Gateway a Contenedores
    ax.annotate("", xy=(40, 69.5), xytext=(62, 69.5), arrowprops=arrow)
    ax.annotate("", xy=(35, 58), xytext=(65, 63), arrowprops=arrow)
    ax.annotate("", xy=(60, 60), xytext=(72, 63), arrowprops=arrow)
    ax.annotate("", xy=(82, 60), xytext=(80, 63), arrowprops=arrow)

    # API Core a Pipeline
    ax.annotate("", xy=(27, 38), xytext=(27, 41), arrowprops=dict(arrowstyle="<->", lw=1.3, color="#111111"))

    # Conexión DB
    ax.annotate("", xy=(27, 19), xytext=(27, 22), arrowprops=arrow)
    ax.annotate("", xy=(65, 19), xytext=(46, 25), arrowprops=arrow)

    save_fig(fig, "figura_3_3_diagrama_despliegue_docker_compose.png")
    plt.close(fig)

# ==============================================================================
# FIGURA 3.4: MODELO CONCEPTUAL DEL ALMACÉN DE DATOS (METODOLOGÍA HEFESTO)
# ==============================================================================
def generar_figura_3_4():
    fig, ax = plt.subplots(figsize=(15.5, 9), dpi=300)
    ax.set_xlim(0, 155)
    ax.set_ylim(0, 90)
    ax.axis('off')

    # Configuración de Cajas (Hefesto Conceptual: Fact Core en medio de dimensiones)
    # 2 Núcleos de Hechos: Rendimiento Académico y Situación Financiera
    # 6 Dimensiones: Estudiante, Tiempo, Módulo/Programa, Origen Documental (Conformadas), Docente, Categoría Financiera (Específicas)

    # 1. Dimensión Específica: Docente (Izquierda)
    doc_box = patches.Rectangle((5, 48), 30, 24, ec="#222222", fc="#FFFFFF", lw=1.3)
    ax.add_patch(doc_box)
    ax.text(20, 69, "«Dimensión Específica»\nDocente", fontsize=9, fontweight='bold', ha='center')
    ax.axhline(65, 0.035, 0.225, color="#444444", lw=0.8)
    ax.text(7, 55, "Identificador: id_docente\nNombre Completo\nÁrea de Especialidad\nGrado Académico Máximo\nTipo (Titular / Invitado)", fontsize=8, color="#222222", va='center')

    # 2. Núcleo de Hechos: Rendimiento Académico (Centro-Izquierda)
    fact1_box = patches.Rectangle((42, 45), 33, 30, ec="#111111", fc="#FFFFFF", lw=1.6)
    ax.add_patch(fact1_box)
    ax.text(58.5, 71.5, "«Núcleo de Hechos»\nRendimiento Académico", fontsize=9.5, fontweight='bold', ha='center')
    ax.axhline(67, 0.275, 0.48, color="#222222", lw=1)
    ax.text(44, 55, "Nota Final (Escala 0 - 100)\nAsistencia Porcentual (%)\nIncumplimiento de Tareas (%)\nNivel de Confianza IA (0.0 - 1.0)\nAlerta de Retención Estudiantil\nFlag Requiere Revisión (HITL)", fontsize=8, color="#111111", va='center')

    # 3. Núcleo de Hechos: Situación Financiera (Centro-Derecha)
    fact2_box = patches.Rectangle((83, 45), 33, 30, ec="#111111", fc="#FFFFFF", lw=1.6)
    ax.add_patch(fact2_box)
    ax.text(99.5, 71.5, "«Núcleo de Hechos»\nSituación Financiera", fontsize=9.5, fontweight='bold', ha='center')
    ax.axhline(67, 0.54, 0.745, color="#222222", lw=1)
    ax.text(85, 55, "Monto Deuda Devengada (Bs)\nMonto Pagado Amortizado (Bs)\nMonto Saldo Pendiente (Bs)\nCuotas Impagas Vencidas\nEstado de Cartera (Mora)\nAlerta Financiera Crediticia", fontsize=8, color="#111111", va='center')

    # 4. Dimensión Específica: Categoría Financiera (Derecha)
    cat_box = patches.Rectangle((122, 48), 28, 24, ec="#222222", fc="#FFFFFF", lw=1.3)
    ax.add_patch(cat_box)
    ax.text(136, 69, "«Dimensión Específica»\nCategoría Financiera", fontsize=9, fontweight='bold', ha='center')
    ax.axhline(65, 0.79, 0.965, color="#444444", lw=0.8)
    ax.text(124, 55, "Identificador: id_categoria\nCódigo Estándar Contable\nNombre de Partida\nTipo Flujo (Ingreso/Egreso)\nRubro Presupuestario", fontsize=8, color="#222222", va='center')

    # Dimensiones Conformadas Compartidas (Abajo y Arriba)
    # 5. Dimensión Conformada: Estudiante (Arriba Centro)
    est_box = patches.Rectangle((58, 80), 42, 9.5, ec="#222222", fc="#FFFFFF", lw=1.3)
    ax.add_patch(est_box)
    ax.text(79, 86.5, "«Dimensión Conformada» Estudiante", fontsize=8.5, fontweight='bold', ha='center')
    ax.text(79, 82.5, "id_estudiante | Código | CI | Nombre Completo | Género | Ciudad | Edad", fontsize=7.5, ha='center', color="#333333")

    # 6. Dimensión Conformada: Tiempo (Centro Abajo)
    tie_box = patches.Rectangle((62, 22), 34, 18, ec="#222222", fc="#FFFFFF", lw=1.4)
    ax.add_patch(tie_box)
    ax.text(79, 36.5, "«Dimensión Conformada»\nTiempo", fontsize=9, fontweight='bold', ha='center')
    ax.axhline(33.5, 0.405, 0.615, color="#444444", lw=0.8)
    ax.text(64, 27.5, "Identificador: id_tiempo\nGestión (Año Calendario)\nSemestre / Trimestre\nMes (Número y Nombre)\nFecha Calendario (Día)", fontsize=8, color="#222222", va='center')

    # 7. Dimensión Conformada: Módulo / Programa (Abajo Izquierda)
    mod_box = patches.Rectangle((18, 5), 44, 14, ec="#222222", fc="#FFFFFF", lw=1.3)
    ax.add_patch(mod_box)
    ax.text(40, 15.5, "«Dimensión Conformada» Módulo / Programa", fontsize=8.5, fontweight='bold', ha='center')
    ax.text(40, 9.5, "id_modulo | Nombre Módulo Curricular\nCódigo Programa (POS) | Versión | Sede / Escuela", fontsize=7.5, ha='center', color="#333333")

    # 8. Dimensión Conformada: Origen Documental (Abajo Derecha)
    orig_box = patches.Rectangle((96, 5), 44, 14, ec="#222222", fc="#FFFFFF", lw=1.3)
    ax.add_patch(orig_box)
    ax.text(118, 15.5, "«Dimensión Conformada» Origen Documental", fontsize=8.5, fontweight='bold', ha='center')
    ax.text(118, 9.5, "id_origen | Nombre Archivo Fuente | Tipo Formato\nHash Criptográfico SHA-256 | Lote de Ingesta", fontsize=7.5, ha='center', color="#333333")

    # Relaciones y Cardinalidades (Líneas formales con 1 y *)
    line_kw = dict(color="#222222", lw=1.3)

    # Docente - Rendimiento
    ax.plot([35, 42], [60, 60], **line_kw)
    ax.text(36, 61, "1", fontsize=8.5, fontweight='bold')
    ax.text(40.5, 61, "*", fontsize=9, fontweight='bold')

    # Rendimiento - Tiempo
    ax.plot([60, 62], [45, 35], **line_kw)
    ax.text(58, 43, "*", fontsize=9, fontweight='bold')
    ax.text(63, 36, "1", fontsize=8.5, fontweight='bold')

    # Situación - Tiempo
    ax.plot([98, 96], [45, 35], **line_kw)
    ax.text(99, 43, "*", fontsize=9, fontweight='bold')
    ax.text(94, 36, "1", fontsize=8.5, fontweight='bold')

    # Situación - Categoría Financiera
    ax.plot([116, 122], [60, 60], **line_kw)
    ax.text(117, 61, "*", fontsize=9, fontweight='bold')
    ax.text(120.5, 61, "1", fontsize=8.5, fontweight='bold')

    # Estudiante a Rendimiento y Situación
    ax.plot([68, 58], [80, 75], **line_kw)
    ax.text(69, 78, "1", fontsize=8.5, fontweight='bold')
    ax.text(57, 76, "*", fontsize=9, fontweight='bold')

    ax.plot([90, 100], [80, 75], **line_kw)
    ax.text(88, 78, "1", fontsize=8.5, fontweight='bold')
    ax.text(101, 76, "*", fontsize=9, fontweight='bold')

    # Rendimiento a Módulo
    ax.plot([50, 45], [45, 19], **line_kw)
    ax.text(51, 41, "*", fontsize=9, fontweight='bold')
    ax.text(46, 21, "1", fontsize=8.5, fontweight='bold')

    # Situación a Módulo
    ax.plot([85, 58], [45, 19], **line_kw)
    ax.text(84, 41, "*", fontsize=9, fontweight='bold')

    # Rendimiento y Situación a Origen Documental
    ax.plot([65, 105], [45, 19], **line_kw)
    ax.text(67, 41, "*", fontsize=9, fontweight='bold')

    ax.plot([108, 114], [45, 19], **line_kw)
    ax.text(107, 41, "*", fontsize=9, fontweight='bold')
    ax.text(115, 21, "1", fontsize=8.5, fontweight='bold')

    save_fig(fig, "figura_3_4_modelo_conceptual_hefesto.png")
    plt.close(fig)

# ==============================================================================
# FIGURA 3.5: ESQUEMA FÍSICO RELACIONAL EN CONSTELACIÓN (DERIVADO DE db/schema.sql)
# ==============================================================================
def generar_figura_3_5():
    fig, ax = plt.subplots(figsize=(16, 11), dpi=300)
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 110)
    ax.axis('off')

    # Helper para dibujar tabla relacional
    def draw_table(x, y, w, h, title, cols, is_fact=False):
        header_h = 4
        # Caja principal
        box = patches.Rectangle((x, y), w, h, ec="#111111", fc="#FFFFFF", lw=1.5 if is_fact else 1.2)
        ax.add_patch(box)
        # Cabecera
        head = patches.Rectangle((x, y + h - header_h), w, header_h, ec="#111111", fc="#F0F0F0" if is_fact else "#F8F8F8", lw=1.2)
        ax.add_patch(head)
        ax.text(x + w/2, y + h - header_h/2, title, fontsize=8.5 if is_fact else 8, fontweight='bold', ha='center', va='center')
        
        # Columnas
        line_y = y + h - header_h - 2.5
        for col, col_type in cols:
            ax.text(x + 2, line_y, col, fontsize=7.2, color="#111111", fontweight='bold' if 'PK' in col or 'FK' in col else 'normal')
            ax.text(x + w - 2, line_y, col_type, fontsize=7, color="#555555", ha='right')
            line_y -= 2.6

    # Dimensiones Principales (7 Dimensiones)
    draw_table(5, 78, 32, 28, "dim_docente", [
        ("id_docente [PK]", "SERIAL"),
        ("nombre_completo", "VARCHAR(200)"),
        ("area_especialidad", "VARCHAR(150)"),
        ("grado_academico", "VARCHAR(50)"),
        ("tipo_docente", "VARCHAR(50)"),
        ("id_institucion [FK]", "INTEGER"),
        ("fecha_registro", "TIMESTAMP"),
    ])

    draw_table(44, 82, 38, 25, "dim_estudiante", [
        ("id_estudiante [PK]", "SERIAL"),
        ("nombre_completo", "VARCHAR(250)"),
        ("codigo_estudiante", "VARCHAR(50)"),
        ("ci", "VARCHAR(20)"),
        ("id_temporal", "VARCHAR(50)"),
        ("identidad_verificada", "BOOLEAN"),
        ("ciudad", "VARCHAR(100)"),
        ("edad", "INTEGER"),
    ])

    draw_table(90, 82, 36, 25, "dim_tiempo", [
        ("id_tiempo [PK]", "INTEGER"),
        ("fecha", "DATE"),
        ("anio", "INTEGER"),
        ("semestre", "INTEGER"),
        ("trimestre", "INTEGER"),
        ("mes", "INTEGER"),
        ("nombre_mes", "VARCHAR(20)"),
        ("semana_anio", "INTEGER"),
    ])

    draw_table(130, 78, 26, 28, "dim_categoria_financiera", [
        ("id_categoria [PK]", "SERIAL"),
        ("codigo", "VARCHAR(50)"),
        ("nombre", "VARCHAR(100)"),
        ("tipo", "VARCHAR(50)"),
        ("descripcion", "TEXT"),
    ])

    draw_table(5, 6, 34, 25, "dim_modulo", [
        ("id_modulo [PK]", "SERIAL"),
        ("codigo_modulo", "VARCHAR(50)"),
        ("nombre_modulo", "VARCHAR(200)"),
        ("codigo_programa", "VARCHAR(50)"),
        ("programa_nombre", "VARCHAR(200)"),
        ("creditos", "INTEGER"),
        ("orden_modulo", "INTEGER"),
    ])

    draw_table(65, 4, 38, 27, "dim_origen_documental", [
        ("id_origen [PK]", "SERIAL"),
        ("nombre_archivo", "VARCHAR(255)"),
        ("hash_sha256", "VARCHAR(64)"),
        ("tipo_formato", "VARCHAR(50)"),
        ("fecha_carga", "TIMESTAMP"),
        ("lote_id [FK]", "INTEGER"),
        ("total_registros", "INTEGER"),
        ("registros_validos", "INTEGER"),
    ])

    draw_table(122, 6, 32, 25, "dim_meta", [
        ("id_meta [PK]", "SERIAL"),
        ("codigo_kpi", "VARCHAR(50)"),
        ("nombre_kpi", "VARCHAR(150)"),
        ("valor_meta", "NUMERIC(14,2)"),
        ("valor_minimo", "NUMERIC(14,2)"),
        ("gestion", "INTEGER"),
        ("area", "VARCHAR(50)"),
    ])

    # Tablas de Hechos Centrales (2 Fact Cores)
    draw_table(16, 37, 52, 36, "fact_rendimiento_academico", [
        ("id_rendimiento [PK]", "SERIAL"),
        ("fk_estudiante [FK]", "INTEGER"),
        ("fk_docente [FK]", "INTEGER"),
        ("fk_modulo [FK]", "INTEGER"),
        ("fk_tiempo [FK]", "INTEGER"),
        ("fk_origen [FK]", "INTEGER"),
        ("nota_final", "NUMERIC(5,2)"),
        ("asistencia_porcentaje", "NUMERIC(5,2)"),
        ("tareas_incompletas_porcentaje", "NUMERIC(5,2)"),
        ("calificacion_docente", "NUMERIC(5,2)"),
        ("fk_estado", "INTEGER"),
        ("nivel_confianza_ia", "NUMERIC(4,3)"),
        ("requiere_revision", "BOOLEAN"),
        ("tipo_alerta", "VARCHAR(50)"),
    ], is_fact=True)

    draw_table(88, 37, 54, 36, "fact_situacion_financiera", [
        ("id_situacion [PK]", "SERIAL"),
        ("fk_estudiante [FK]", "INTEGER"),
        ("fk_modulo [FK]", "INTEGER"),
        ("fk_categoria [FK]", "INTEGER"),
        ("fk_tiempo [FK]", "INTEGER"),
        ("fk_origen [FK]", "INTEGER"),
        ("monto_total_deuda", "NUMERIC(14,2)"),
        ("monto_total_pagado", "NUMERIC(14,2)"),
        ("monto_pendiente_pago", "NUMERIC(14,2)"),
        ("dias_mora", "INTEGER"),
        ("cuotas_impagas", "INTEGER"),
        ("fk_estado", "INTEGER"),
        ("nivel_confianza_ia", "NUMERIC(4,3)"),
        ("requiere_revision", "BOOLEAN"),
        ("tipo_alerta", "VARCHAR(50)"),
    ], is_fact=True)

    # Hecho Complementario 1: fact_forecast
    draw_table(70, 42, 16, 26, "fact_forecast", [
        ("id_forecast [PK]", "SERIAL"),
        ("serie_objetivo", "VARCHAR(50)"),
        ("periodo", "VARCHAR(20)"),
        ("valor_proy", "NUMERIC"),
        ("lim_inf_95", "NUMERIC"),
        ("lim_sup_95", "NUMERIC"),
    ], is_fact=True)

    # Conexiones FK sutiles
    line_s = dict(color="#444444", lw=1.1, linestyle=":")
    ax.plot([21, 21], [78, 73], **line_s) # Docente -> Fact Rendimiento
    ax.plot([50, 45], [82, 73], **line_s) # Estudiante -> Fact Rendimiento
    ax.plot([60, 95], [82, 73], **line_s) # Estudiante -> Fact Financiera
    ax.plot([95, 60], [82, 73], **line_s) # Tiempo -> Fact Rendimiento
    ax.plot([105, 115], [82, 73], **line_s) # Tiempo -> Fact Financiera
    ax.plot([135, 135], [78, 73], **line_s) # Categoria -> Fact Financiera
    ax.plot([25, 25], [37, 31], **line_s) # Fact Rendimiento -> Modulo
    ax.plot([92, 38], [37, 28], **line_s) # Fact Financiera -> Modulo
    ax.plot([55, 75], [37, 31], **line_s) # Fact Rendimiento -> Origen
    ax.plot([105, 95], [37, 31], **line_s) # Fact Financiera -> Origen

    save_fig(fig, "figura_3_5_esquema_constelacion_fisico.png")
    plt.close(fig)

# ==============================================================================
# FIGURA 3.6: DIAGRAMA DE CLASES DEL SISTEMA (ORM SQLALCHEMY Y PYDANTIC)
# ==============================================================================
def generar_figura_3_6():
    fig, ax = plt.subplots(figsize=(15.5, 10), dpi=300)
    ax.set_xlim(0, 155)
    ax.set_ylim(0, 100)
    ax.axis('off')

    def draw_class(x, y, w, h, class_type, class_name, attrs, methods=None):
        header_h = 6
        box = patches.Rectangle((x, y), w, h, ec="#111111", fc="#FFFFFF", lw=1.3)
        ax.add_patch(box)
        head = patches.Rectangle((x, y + h - header_h), w, header_h, ec="#111111", fc="#F8F8F8", lw=1)
        ax.add_patch(head)
        ax.text(x + w/2, y + h - 2.2, f"«{class_type}»", fontsize=7.5, fontstyle='italic', ha='center')
        ax.text(x + w/2, y + h - 4.5, class_name, fontsize=8.5, fontweight='bold', ha='center')

        cur_y = y + h - header_h - 2.5
        for a in attrs:
            ax.text(x + 2, cur_y, a, fontsize=7.2, color="#111111")
            cur_y -= 2.4

        if methods:
            ax.axhline(cur_y + 1, x/155, (x+w)/155, color="#555555", lw=0.6)
            cur_y -= 1.5
            for m in methods:
                ax.text(x + 2, cur_y, m, fontsize=7.2, color="#222222", fontstyle='italic')
                cur_y -= 2.4

    # Modelos ORM SQLAlchemy (backend/models/)
    draw_class(5, 58, 44, 38, "SQLAlchemy Model", "FactRendimientoAcademico", [
        "+ id_rendimiento: Integer [PK]",
        "+ fk_estudiante: Integer [FK]",
        "+ fk_docente: Integer [FK]",
        "+ fk_modulo: Integer [FK]",
        "+ fk_tiempo: Integer [FK]",
        "+ fk_origen: Integer [FK]",
        "+ nota_final: Numeric(5,2)",
        "+ asistencia_porcentaje: Numeric(5,2)",
        "+ tareas_incompletas: Numeric(5,2)",
        "+ nivel_confianza_ia: Numeric(4,3)",
        "+ requiere_revision: Boolean",
        "+ tipo_alerta: String(50)",
    ], [
        "+ estudiante: relationship('DimEstudiante')",
        "+ modulo: relationship('DimModulo')",
        "+ docente: relationship('DimDocente')",
    ])

    draw_class(55, 58, 45, 38, "SQLAlchemy Model", "FactSituacionFinanciera", [
        "+ id_situacion: Integer [PK]",
        "+ fk_estudiante: Integer [FK]",
        "+ fk_modulo: Integer [FK]",
        "+ fk_categoria: Integer [FK]",
        "+ fk_tiempo: Integer [FK]",
        "+ fk_origen: Integer [FK]",
        "+ monto_total_deuda: Numeric(14,2)",
        "+ monto_total_pagado: Numeric(14,2)",
        "+ monto_pendiente: Numeric(14,2)",
        "+ dias_mora: Integer",
        "+ cuotas_impagas: Integer",
        "+ nivel_confianza_ia: Numeric(4,3)",
        "+ requiere_revision: Boolean",
    ], [
        "+ estudiante: relationship('DimEstudiante')",
        "+ modulo: relationship('DimModulo')",
        "+ categoria: relationship('DimCategoriaFinanciera')",
    ])

    draw_class(106, 58, 44, 38, "SQLAlchemy Model", "DimEstudiante", [
        "+ id_estudiante: Integer [PK]",
        "+ nombre_completo: String(250)",
        "+ codigo_estudiante: String(50)",
        "+ ci: String(20)",
        "+ id_temporal: String(50)",
        "+ identidad_verificada: Boolean",
        "+ ciudad: String(100)",
        "+ edad: Integer",
        "+ genero: String(20)",
    ], [
        "+ rendimientos: relationship('FactRendimientoAcademico')",
        "+ situaciones: relationship('FactSituacionFinanciera')",
    ])

    # Esquemas Pydantic DTO (backend/schemas/)
    draw_class(5, 12, 44, 38, "Pydantic Schema", "RendimientoAcademicoResponse", [
        "+ id_rendimiento: int",
        "+ estudiante_nombre: str",
        "+ modulo_nombre: str",
        "+ docente_nombre: str",
        "+ nota_final: float",
        "+ asistencia_porcentaje: float",
        "+ tareas_incompletas: float",
        "+ estado_evaluacion: str",
        "+ nivel_confianza_ia: float",
        "+ requiere_revision: bool",
        "+ tipo_alerta: Optional[str]",
    ], [
        "+ model_config = ConfigDict(from_attributes=True)"
    ])

    draw_class(55, 12, 45, 38, "Pydantic Schema", "SituacionFinancieraResponse", [
        "+ id_situacion: int",
        "+ estudiante_nombre: str",
        "+ modulo_nombre: str",
        "+ categoria_nombre: str",
        "+ monto_total_deuda: float",
        "+ monto_total_pagado: float",
        "+ monto_pendiente: float",
        "+ dias_mora: int",
        "+ nivel_confianza_ia: float",
        "+ requiere_revision: bool",
    ], [
        "+ model_config = ConfigDict(from_attributes=True)"
    ])

    draw_class(106, 12, 44, 38, "Pydantic Schema", "EstudianteResponse", [
        "+ id_estudiante: int",
        "+ nombre_completo: str",
        "+ codigo_estudiante: Optional[str]",
        "+ ci: Optional[str]",
        "+ id_temporal: Optional[str]",
        "+ identidad_verificada: bool",
        "+ ciudad: Optional[str]",
        "+ edad: Optional[int]",
    ], [
        "+ model_config = ConfigDict(from_attributes=True)"
    ])

    # Relaciones entre ORM y Pydantic (Líneas formales de transformación)
    line_tr = dict(color="#444444", lw=1.2, linestyle="--")
    ax.annotate("", xy=(27, 50), xytext=(27, 58), arrowprops=dict(arrowstyle="->", lw=1.2, color="#333333"))
    ax.text(28, 54, "serializa a DTO", fontsize=7.2, fontstyle='italic')

    ax.annotate("", xy=(77, 50), xytext=(77, 58), arrowprops=dict(arrowstyle="->", lw=1.2, color="#333333"))
    ax.text(78, 54, "serializa a DTO", fontsize=7.2, fontstyle='italic')

    ax.annotate("", xy=(128, 50), xytext=(128, 58), arrowprops=dict(arrowstyle="->", lw=1.2, color="#333333"))
    ax.text(129, 54, "serializa a DTO", fontsize=7.2, fontstyle='italic')

    save_fig(fig, "figura_3_6_diagrama_clases_orm_pydantic.png")
    plt.close(fig)

if __name__ == "__main__":
    print("Generando Figuras Sprint 1 corregidas (300 DPI, Grayscale formal, Sin títulos incrustados)...")
    generar_figura_3_2()
    generar_figura_3_3()
    generar_figura_3_4()
    generar_figura_3_5()
    generar_figura_3_6()
    print("¡Generación completada exitosamente!")
