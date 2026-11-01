"""
Generador de alta precisión de la Figura 3.2: Diagrama de arquitectura física y orquestación de contenedores del sistema.
Refinamiento visual:
- Separación limpia entre badges de Nginx (/auth y /notifications).
- Etiqueta de dw_loader en canal despejado.
- Flechas y conectores ortogonales matemáticamente alineados.
- 300 DPI, fondo blanco puro, ancho >= 3500 px.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_PATHS = [
    r"docs\images\figura_3_2_arquitectura_fisica_orquestacion.png",
    r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0\figura_3_2_arquitectura_fisica_orquestacion.png"
]

def dibujar_figura_3_2_optimizada():
    fig, ax = plt.subplots(figsize=(16.5, 11.2), dpi=300)
    ax.set_xlim(0, 165)
    ax.set_ylim(0, 112)
    ax.axis('off')

    c_line = "#111111"
    c_subline = "#333333"
    c_header_bg = "#EAEAEA"
    c_card_bg = "#FAFAFA"
    c_text_dark = "#111111"
    c_text_gray = "#444444"

    # =========================================================================
    # 0. CLIENTES EXTERNOS (Fuera del Servidor Host, Arriba)
    # =========================================================================
    ext_group = patches.FancyBboxPatch((88, 96), 72, 13.5, boxstyle="square,pad=0",
                                       ec=c_line, fc="#FFFFFF", lw=1.3)
    ax.add_patch(ext_group)
    ax.text(90, 107, "Clientes Externos / Estaciones de Trabajo", fontsize=8.5, fontweight='bold', color=c_text_dark)

    # Cliente 1: Navegador Web
    spa_card = patches.Rectangle((90, 97.5), 33, 8, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(spa_card)
    ax.text(106.5, 102.5, "Navegador Web (SPA)", fontsize=8, fontweight='bold', ha='center', color=c_text_dark)
    ax.text(106.5, 99.5, "Usuario Final / Operador HITL (React 18)", fontsize=7, ha='center', color=c_text_gray)

    # Cliente 2: Power BI Desktop
    pbi_card = patches.Rectangle((125, 97.5), 33, 8, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(pbi_card)
    ax.text(141.5, 102.5, "Power BI Desktop", fontsize=8, fontweight='bold', ha='center', color=c_text_dark)
    ax.text(141.5, 99.5, "Analista BI / Directivos (giragroup_cmi.pbix)", fontsize=7, ha='center', color=c_text_gray)

    # =========================================================================
    # SERVIDOR HOST (DOCKER ENGINE 24.x)
    # =========================================================================
    host_border = patches.FancyBboxPatch((4, 4), 156, 89, boxstyle="square,pad=0",
                                         ec=c_line, fc="#FFFFFF", lw=1.6)
    ax.add_patch(host_border)

    # Franja superior del Host
    host_header = patches.Rectangle((4, 89.5), 156, 3.5, ec=c_line, fc=c_header_bg, lw=1.1)
    ax.add_patch(host_header)
    ax.text(6, 91.2, "Servidor Host / Entorno Virtualizado (Docker Engine 24.x | Red Bridge: 'giragroup_network')",
            fontsize=9, fontweight='bold', color=c_text_dark, va='center')

    # =========================================================================
    # 1. RED DE ENTRADA / REVERSE PROXY (Nginx :80)
    # =========================================================================
    gw_rect = patches.Rectangle((54, 72.5), 52, 14.5, ec=c_line, fc="#FFFFFF", lw=1.3)
    ax.add_patch(gw_rect)
    gw_hdr = patches.Rectangle((54, 83.5), 52, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(gw_hdr)
    ax.text(80, 85.2, "1. Red de Entrada / Reverse Proxy", fontsize=8.5, fontweight='bold', ha='center', va='center')

    ax.text(80, 79.5, "giragroup_gateway (Nginx :80)", fontsize=8.5, fontweight='bold', ha='center')
    ax.text(80, 75.5, "Proxy Reverso Perimetral, Control CORS, SSL y Balanceo\nEnrutamiento Centralizado hacia Servicios Internos",
            fontsize=7.2, ha='center', color=c_text_gray)

    # =========================================================================
    # 2. CAPA DE PRESENTACIÓN (FRONTEND)
    # =========================================================================
    web_rect = patches.Rectangle((6, 72.5), 42, 14.5, ec=c_line, fc="#FFFFFF", lw=1.3)
    ax.add_patch(web_rect)
    web_hdr = patches.Rectangle((6, 83.5), 42, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(web_hdr)
    ax.text(27, 85.2, "2. Capa de Presentación", fontsize=8.5, fontweight='bold', ha='center', va='center')

    ax.text(27, 79.5, "giragroup_web (:5173)", fontsize=8.5, fontweight='bold', ha='center')
    ax.text(27, 75.5, "React 18 + Vite + Tailwind CSS\nDashboards CMI, Consola HITL & Ingesta DataOps",
            fontsize=7.2, ha='center', color=c_text_gray)

    # =========================================================================
    # 3. CAPA DE SERVICIOS BACKEND (CORE & INFERENCIA) (Izquierda)
    # =========================================================================
    core_rect = patches.Rectangle((6, 29), 46, 38, ec=c_line, fc="#FFFFFF", lw=1.4)
    ax.add_patch(core_rect)
    core_hdr = patches.Rectangle((6, 63.5), 46, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(core_hdr)
    ax.text(29, 65.2, "3. Capa de Servicios Backend (Core)", fontsize=8.5, fontweight='bold', ha='center', va='center')

    # Contenedor 3: giragroup_api
    api_card = patches.Rectangle((8, 48), 42, 14, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(api_card)
    ax.text(29, 58.5, "giragroup_api (FastAPI BETO Core :8000)", fontsize=8, fontweight='bold', ha='center')
    ax.text(29, 53, "Endpoints: /api/v1/forecast, /kpis, /dataops, /reports\nMotor Orquestador ETL, dw_loader.py,\nquality_rules.py y Handoff Semántico",
            fontsize=6.8, ha='center', color=c_text_gray)

    # Contenedor 4: giragroup_pipeline
    pipe_card = patches.Rectangle((8, 31), 42, 13.5, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(pipe_card)
    ax.text(29, 41, "giragroup_pipeline (PyTorch :8006)", fontsize=8, fontweight='bold', ha='center')
    ax.text(29, 35.8, "Inferencia Semántica BETO NER (Local)\nTokenizador WordPiece, BIO Tagging (9 clases)\nNormalización y Desambiguación Léxica",
            fontsize=6.8, ha='center', color=c_text_gray)

    # =========================================================================
    # 4. MICROSERVICIOS AUXILIARES ESPECIALIZADOS (Centro-Derecha)
    # =========================================================================
    aux_rect = patches.Rectangle((56, 29), 68, 38, ec=c_line, fc="#FFFFFF", lw=1.4)
    ax.add_patch(aux_rect)
    aux_hdr = patches.Rectangle((56, 63.5), 68, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(aux_hdr)
    ax.text(90, 65.2, "4. Microservicios Auxiliares Especializados", fontsize=8.5, fontweight='bold', ha='center', va='center')

    # Fila Superior: auth-service y notifications-service
    auth_card = patches.Rectangle((58, 48), 31, 14, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(auth_card)
    ax.text(73.5, 58.5, "auth-service (:8001)", fontsize=8, fontweight='bold', ha='center')
    ax.text(73.5, 53.5, "Rutas: /api/v1/auth, /users\nAutenticación JWT, RBAC,\nCriptografía Passlib/bcrypt", fontsize=6.8, ha='center', color=c_text_gray)

    notif_card = patches.Rectangle((91, 48), 31, 14, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(notif_card)
    ax.text(106.5, 58.5, "notifications-service (:8002)", fontsize=8, fontweight='bold', ha='center')
    ax.text(106.5, 53.5, "Rutas: /api/v1/notifications, /ws\nWebSocket en tiempo real,\nAlertas HITL y telemetría", fontsize=6.8, ha='center', color=c_text_gray)

    # Fila Inferior: analytics-service, audit-service, storage-service
    analytics_card = patches.Rectangle((58, 31), 20, 14.5, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(analytics_card)
    ax.text(68, 41.5, "analytics-service\n(:8003)", fontsize=7.5, fontweight='bold', ha='center')
    ax.text(68, 35, "[Servicio Interno]\nCálculo métricas\ny series auxiliares\n(No perimetral)", fontsize=6.5, ha='center', color=c_text_gray)

    audit_card = patches.Rectangle((80, 31), 21, 14.5, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(audit_card)
    ax.text(90.5, 41.5, "audit-service\n(:8004)", fontsize=7.5, fontweight='bold', ha='center')
    ax.text(90.5, 35, "Ruta: /api/v1/audit\nLog de auditoría\ny trazabilidad NLP", fontsize=6.5, ha='center', color=c_text_gray)

    storage_card = patches.Rectangle((103, 31), 19, 14.5, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(storage_card)
    ax.text(112.5, 41.5, "storage-service\n(:8005)", fontsize=7.5, fontweight='bold', ha='center')
    ax.text(112.5, 35, "Ruta: /api/v1/storage\nCargas masivas y\ncontrol MIME", fontsize=6.5, ha='center', color=c_text_gray)

    # =========================================================================
    # 5. CAPA DE PERSISTENCIA RELACIONAL Y DIMENSIONAL (Abajo)
    # catalog_db (Izquierda) | giragroup_db (Derecha)
    # =========================================================================
    db_rect = patches.Rectangle((6, 6), 118, 20, ec=c_line, fc="#FFFFFF", lw=1.4)
    ax.add_patch(db_rect)
    db_hdr = patches.Rectangle((6, 22.5), 118, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(db_hdr)
    ax.text(65, 24.2, "5. Capa de Persistencia Relacional y Dimensional (PostgreSQL 16)", fontsize=8.5, fontweight='bold', ha='center', va='center')

    # Contenedor 11: catalog_db (Izquierda)
    cat_card = patches.Rectangle((8, 7.5), 50, 13.5, ec=c_subline, fc=c_card_bg, lw=1.1)
    ax.add_patch(cat_card)
    ax.text(33, 17.5, "giragroup_catalog_db (PostgreSQL 16 :5433)", fontsize=8, fontweight='bold', ha='center')
    ax.text(33, 12, "Catálogos Maestros Académicos en Tercera Forma Normal (3NF)\n• Tablas canónicas: cat_programa, cat_modulo, cat_institucion\n• Soporte de validación difusa con RapidFuzz\n• Volumen persistente: catalog_postgres_data",
            fontsize=6.7, ha='center', color=c_text_gray)

    # Contenedor 10: giragroup_db (Derecha)
    dw_card = patches.Rectangle((62, 7.5), 60, 13.5, ec=c_subline, fc=c_card_bg, lw=1.2)
    ax.add_patch(dw_card)
    ax.text(92, 17.5, "giragroup_db (PostgreSQL 16 :5432)", fontsize=8.2, fontweight='bold', ha='center')
    ax.text(92, 12, "Data Warehouse Institucional (Esquema Constelación - 24 tablas)\n• Hechos: fact_rendimiento_academico, fact_situacion_financiera, fact_forecast\n• Dimensiones: dim_estudiante, dim_docente, dim_modulo, dim_tiempo, dim_meta\n• Volumen persistente: postgres_data (/var/lib/postgresql/data)",
            fontsize=6.7, ha='center', color=c_text_gray)

    # =========================================================================
    # ALMACENAMIENTO LOCAL Y VOLÚMENES (Extrema Derecha)
    # =========================================================================
    stor_rect = patches.Rectangle((128, 6), 28, 61, ec=c_line, fc="#FFFFFF", lw=1.3)
    ax.add_patch(stor_rect)
    stor_hdr = patches.Rectangle((128, 63.5), 28, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(stor_hdr)
    ax.text(142, 65.2, "Almacenamiento y Volúmenes", fontsize=8, fontweight='bold', ha='center', va='center')

    ax.text(142, 55, "Bind Mount de Archivos:\n./uploads\n-> /app/uploads\n(Compartido entre API\ny Storage Service)",
            fontsize=7, ha='center', va='center', color=c_text_dark)

    ax.plot([130, 154], [46, 46], color="#CCCCCC", lw=0.8)

    ax.text(142, 37, "Artefactos BETO NER:\n./pipeline/semantic/beto_local\n-> model.safetensors\n-> config.json\n(Pesos fine-tuned locales)",
            fontsize=7, ha='center', va='center', color=c_text_dark)

    ax.plot([130, 154], [28, 28], color="#CCCCCC", lw=0.8)

    ax.text(142, 16, "Volúmenes Docker:\n• postgres_data\n  -> giragroup_db\n• catalog_postgres_data\n  -> catalog_db",
            fontsize=7, ha='center', va='center', color=c_text_dark)

    # =========================================================================
    # ENLACES Y ETIQUETAS ORTOGONALES DE ENRUTAMIENTO
    # =========================================================================
    def badge(x, y, text, fontsize=6.8, fontweight='normal'):
        ax.text(x, y, text, fontsize=fontsize, fontweight=fontweight, ha='center', va='center',
                bbox=dict(boxstyle="square,pad=0.25", fc="#FFFFFF", ec="#777777", lw=0.7))

    # 1. Navegador Web -> Gateway
    ax.plot([106.5, 106.5, 80, 80], [97.5, 94.5, 94.5, 87], color=c_line, lw=1.3)
    ax.annotate("", xy=(80, 87), xytext=(80, 89), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(93, 94.5, "HTTP / HTTPS :80", fontsize=7.2, fontweight='bold')

    # 2. Power BI Desktop -> giragroup_db (Línea directa al borde derecho de giragroup_db)
    ax.plot([141.5, 141.5, 125, 125, 122], [97.5, 95.5, 95.5, 14, 14], color=c_line, lw=1.5, linestyle="--")
    ax.annotate("", xy=(122, 14), xytext=(123.8, 14), arrowprops=dict(arrowstyle="->", lw=1.5, color=c_line))
    badge(125, 80, "PostgreSQL Wire (:5432)\nConexión DirectQuery", fontsize=7, fontweight='bold')

    # 3. Gateway -> giragroup_web
    ax.plot([54, 48], [79.5, 79.5], color=c_line, lw=1.2)
    ax.annotate("", xy=(48, 79.5), xytext=(50, 79.5), arrowprops=dict(arrowstyle="->", lw=1.2, color=c_line))
    badge(51, 81.5, "/ (Proxy :5173)", fontsize=6.8)

    # 4. Canal de Enrutamiento Gateway -> Backend y Microservicios
    # A giragroup_api
    ax.plot([58, 29, 29], [72.5, 70, 67], color=c_line, lw=1.3)
    ax.annotate("", xy=(29, 67), xytext=(29, 68.5), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(33, 70, "/api/v1/forecast, /kpis, /dataops, /reports (:8000)", fontsize=6.6, fontweight='bold')

    # A auth-service (:8001)
    ax.plot([70, 70], [72.5, 67], color=c_line, lw=1.2)
    ax.annotate("", xy=(70, 67), xytext=(70, 68.5), arrowprops=dict(arrowstyle="->", lw=1.2, color=c_line))
    badge(70, 69.8, "/api/v1/auth (:8001)", fontsize=6.6)

    # A notifications-service (:8002)
    ax.plot([92, 92], [72.5, 67], color=c_line, lw=1.2)
    ax.annotate("", xy=(92, 67), xytext=(92, 68.5), arrowprops=dict(arrowstyle="->", lw=1.2, color=c_line))
    badge(92, 69.8, "/api/v1/notifications, /ws (:8002)", fontsize=6.6)

    # A audit y storage (:8004, :8005)
    ax.plot([102, 112, 112], [72.5, 70, 67], color=c_line, lw=1.2)
    ax.annotate("", xy=(112, 67), xytext=(112, 68.5), arrowprops=dict(arrowstyle="->", lw=1.2, color=c_line))
    badge(114, 70, "/api/v1/audit, /storage (:8004, :8005)", fontsize=6.6)

    # 5. Core API <-> Pipeline NER
    ax.plot([29, 29], [48, 44.5], color=c_line, lw=1.3)
    ax.annotate("", xy=(29, 44.5), xytext=(29, 46), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(29, 46.2, "Inferencia BETO :8006 (/predict)", fontsize=6.6)

    # 6. Pipeline -> catalog_db (Izquierda directa)
    ax.plot([23, 23], [31, 21], color=c_line, lw=1.3)
    ax.annotate("", xy=(23, 21), xytext=(23, 23), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(23, 25.5, "TCP :5433 (Catálogos 3NF)", fontsize=6.6)

    # 7. Core API -> giragroup_db (DW)
    ax.plot([48, 54, 54, 62], [48, 48, 17, 17], color=c_line, lw=1.3)
    ax.annotate("", xy=(62, 17), xytext=(60, 17), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(54, 38, "TCP :5432\n(dw_loader)", fontsize=6.6)

    # 8. Microservicios Auxiliares -> giragroup_db (DW)
    ax.plot([90.5, 90.5], [31, 21], color=c_line, lw=1.1, linestyle=":")
    ax.annotate("", xy=(90.5, 21), xytext=(90.5, 23), arrowprops=dict(arrowstyle="->", lw=1.1, color=c_line))
    badge(90.5, 25.5, "Pool Conexiones DWH (:5432)", fontsize=6.6)

    # Guardado de archivos
    for path in OUTPUT_PATHS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
        print(f"Figura 3.2 guardada con éxito en: {path}")

    plt.close(fig)

if __name__ == "__main__":
    dibujar_figura_3_2_optimizada()
