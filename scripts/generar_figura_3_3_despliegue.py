"""
Generador de ultra alta precisión de la Figura 3.3: Diagrama UML de Despliegue de la solución en Docker Compose.
Ajustes milimétricos:
- Fontsize adaptativo para nombres de archivo largos (inference_server.py, model.safetensors, schema_catalogos.sql, seed_dim_tiempo.sql) evitando cualquier desborde.
- Expansión del canal central a 8 unidades entre Core y Microservicios para dw_loader.
- Reubicación de badges RapidFuzz y DWH Pool a y=28 (fuera del header de la capa de persistencia).
- Artefactos 100% verídicos: App.jsx, giragroup_cmi.pbix, model.safetensors, inference_server.py.
- Imágenes base exactas: python:3.12-slim, python:3.11-slim, node:20-alpine, nginx:alpine, postgres:16-alpine.
- 300 DPI, fondo blanco puro, ancho >= 3500 px.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_PATHS = [
    r"docs\images\figura_3_3_diagrama_despliegue_docker_compose.png",
    r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0\figura_3_3_diagrama_despliegue_docker_compose.png"
]

def dibujar_icono_artefacto(ax, x, y, w=2.2, h=2.6):
    fold = 0.6
    poly = patches.Polygon([
        [x, y],
        [x + w - fold, y],
        [x + w, y - fold],
        [x + w, y - h],
        [x, y - h]
    ], closed=True, ec="#333333", fc="#FFFFFF", lw=0.8)
    ax.add_patch(poly)
    fold_poly = patches.Polygon([
        [x + w - fold, y],
        [x + w - fold, y - fold],
        [x + w, y - fold]
    ], closed=True, ec="#333333", fc="#E5E5E5", lw=0.7)
    ax.add_patch(fold_poly)

def dibujar_caja_artefacto(ax, x, y, w, h, nombre, detalle=None, fsize=6.8):
    card = patches.Rectangle((x, y), w, h, ec="#444444", fc="#FFFFFF", lw=0.9)
    ax.add_patch(card)
    dibujar_icono_artefacto(ax, x + w - 2.6, y + h - 0.4)
    
    ax.text(x + 0.8, y + h - 1.8, "«artifact»", fontsize=5.8, fontstyle='italic', color="#444444")
    ax.text(x + 0.8, y + h - 3.7, nombre, fontsize=fsize, fontweight='bold', color="#111111")
    if detalle:
        ax.text(x + 0.8, y + 1.1, detalle, fontsize=5.8, color="#555555")

def generar_diagrama_despliegue():
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
    # 0. ESTACIÓN DE TRABAJO CLIENTE («device»)
    # =========================================================================
    client_dev = patches.FancyBboxPatch((86, 95), 74, 15, boxstyle="square,pad=0",
                                        ec=c_line, fc="#FFFFFF", lw=1.3)
    ax.add_patch(client_dev)
    ax.text(88, 108, "«device» Estación de Trabajo Cliente", fontsize=8.5, fontweight='bold', color=c_text_dark)

    # Entorno 1: Navegador Web
    env_web = patches.Rectangle((88, 96.5), 34, 10, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(env_web)
    ax.text(90, 104.8, "«execution environment» Navegador Web", fontsize=6.8, fontweight='bold', color=c_text_dark)
    dibujar_caja_artefacto(ax, 89.5, 97.5, 31, 6.2, "App.jsx", "React 18 SPA + Vite runtime", fsize=7.2)

    # Entorno 2: Power BI Desktop
    env_pbi = patches.Rectangle((124, 96.5), 34, 10, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(env_pbi)
    ax.text(126, 104.8, "«execution environment» Power BI Desktop", fontsize=6.8, fontweight='bold', color=c_text_dark)
    dibujar_caja_artefacto(ax, 125.5, 97.5, 31, 6.2, "giragroup_cmi.pbix", "Modelos DAX & Visuales CMI", fsize=7.0)

    # =========================================================================
    # SERVIDOR HOST («device»)
    # =========================================================================
    host_dev = patches.FancyBboxPatch((4, 4), 156, 88, boxstyle="square,pad=0",
                                      ec=c_line, fc="#FFFFFF", lw=1.6)
    ax.add_patch(host_dev)

    host_hdr = patches.Rectangle((4, 88.5), 156, 3.5, ec=c_line, fc=c_header_bg, lw=1.1)
    ax.add_patch(host_hdr)
    ax.text(6, 90.2, "«device» Servidor Host Físico / VM (Docker Engine 24.x | Red Bridge Interna: 'giragroup_network')",
            fontsize=9, fontweight='bold', color=c_text_dark, va='center')

    # =========================================================================
    # 1. GATEWAY («execution environment»)
    # =========================================================================
    gw_env = patches.Rectangle((54, 71.5), 52, 14.5, ec=c_line, fc="#FFFFFF", lw=1.3)
    ax.add_patch(gw_env)
    gw_hdr = patches.Rectangle((54, 82.5), 52, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(gw_hdr)
    ax.text(80, 84.2, "«execution environment» giragroup_gateway (nginx:alpine)", fontsize=8, fontweight='bold', ha='center', va='center')

    ax.text(56, 80.5, "Contenedor: giragroup_gateway | Puerto Expuesto: 80", fontsize=7, color=c_text_gray)
    dibujar_caja_artefacto(ax, 56, 73, 48, 6.5, "nginx.conf", "Configuración de upstream perimetral y proxies inversos", fsize=7.2)

    # =========================================================================
    # 2. FRONTEND WEB («execution environment»)
    # =========================================================================
    web_env = patches.Rectangle((6, 71.5), 42, 14.5, ec=c_line, fc="#FFFFFF", lw=1.3)
    ax.add_patch(web_env)
    web_hdr = patches.Rectangle((6, 82.5), 42, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(web_hdr)
    ax.text(27, 84.2, "«execution env» giragroup_web (node:20-alpine)", fontsize=7.8, fontweight='bold', ha='center', va='center')

    ax.text(8, 80.5, "Puerto Interno: 5173", fontsize=7, color=c_text_gray)
    dibujar_caja_artefacto(ax, 8, 73, 18, 6.5, "App.jsx", "Dashboard UI", fsize=7.2)
    dibujar_caja_artefacto(ax, 28, 73, 18, 6.5, "package.json", "Vite & React 18", fsize=7.2)

    # =========================================================================
    # 3. BACKEND CORE & PIPELINE («execution environments»)
    # =========================================================================
    core_grp = patches.Rectangle((6, 29), 45, 38, ec=c_line, fc="#FFFFFF", lw=1.4)
    ax.add_patch(core_grp)
    core_hdr = patches.Rectangle((6, 63.5), 45, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(core_hdr)
    ax.text(28.5, 65.2, "Servicios Backend Core & Inteligencia Artificial", fontsize=7.8, fontweight='bold', ha='center', va='center')

    # giragroup_api
    api_env = patches.Rectangle((7.5, 48), 42, 14, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(api_env)
    ax.text(8.5, 60.5, "«execution env» giragroup_api (python:3.12-slim)", fontsize=7.0, fontweight='bold', color=c_text_dark)
    ax.text(8.5, 58.5, "Puerto Interno: 8000 | FastAPI BETO Core", fontsize=6.2, color=c_text_gray)
    dibujar_caja_artefacto(ax, 8.5, 49.5, 12.5, 7.8, "main.py", "API Router", fsize=6.8)
    dibujar_caja_artefacto(ax, 22.0, 49.5, 13.5, 7.8, "dw_loader.py", "Carga DW Hefesto", fsize=6.6)
    dibujar_caja_artefacto(ax, 36.5, 49.5, 12, 7.8, "quality_rules.py", "Reglas Calidad", fsize=6.2)

    # giragroup_pipeline
    pipe_env = patches.Rectangle((7.5, 31), 42, 14.5, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(pipe_env)
    ax.text(8.5, 43.8, "«execution env» giragroup_pipeline (python:3.11-slim)", fontsize=7.0, fontweight='bold', color=c_text_dark)
    ax.text(8.5, 41.8, "Puerto Interno: 8006 | PyTorch & HuggingFace", fontsize=6.2, color=c_text_gray)
    dibujar_caja_artefacto(ax, 8.5, 32.5, 13, 8.0, "inference_server.py", "FastAPI /predict", fsize=5.7)
    dibujar_caja_artefacto(ax, 22.5, 32.5, 12.5, 8.0, "ner_engine.py", "BETO & Fallback", fsize=6.4)
    dibujar_caja_artefacto(ax, 36.0, 32.5, 12.5, 8.0, "model.safetensors", "beto weights", fsize=5.7)

    # =========================================================================
    # 4. MICROSERVICIOS AUXILIARES («execution environments»)
    # Se expande el canal entre core y aux: aux inicia en x=58
    # =========================================================================
    aux_grp = patches.Rectangle((58, 29), 66, 38, ec=c_line, fc="#FFFFFF", lw=1.4)
    ax.add_patch(aux_grp)
    aux_hdr = patches.Rectangle((58, 63.5), 66, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(aux_hdr)
    ax.text(91, 65.2, "Microservicios Auxiliares (Base: python:3.11-slim)", fontsize=8, fontweight='bold', ha='center', va='center')

    # auth_svc
    auth_env = patches.Rectangle((60, 48), 30, 14, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(auth_env)
    ax.text(61, 60.5, "«execution env» auth_svc (:8001)", fontsize=6.8, fontweight='bold')
    dibujar_caja_artefacto(ax, 61, 49.5, 13, 9.2, "main.py", "Auth Router", fsize=6.8)
    dibujar_caja_artefacto(ax, 75, 49.5, 14, 9.2, "auth_service.py", "JWT & RBAC", fsize=6.2)

    # notifications_svc
    notif_env = patches.Rectangle((92, 48), 30, 14, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(notif_env)
    ax.text(93, 60.5, "«execution env» notif_svc (:8002)", fontsize=6.8, fontweight='bold')
    dibujar_caja_artefacto(ax, 93, 49.5, 13, 9.2, "main.py", "Alerts Router", fsize=6.8)
    dibujar_caja_artefacto(ax, 107, 49.5, 14, 9.2, "ws_manager.py", "WebSocket HITL", fsize=6.2)

    # analytics_svc
    an_env = patches.Rectangle((60, 31), 19, 14.5, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(an_env)
    ax.text(61, 43.8, "analytics_svc (:8003)", fontsize=6.6, fontweight='bold')
    ax.text(61, 41.8, "[Servicio Interno]", fontsize=6.0, color=c_text_gray)
    dibujar_caja_artefacto(ax, 61, 32.5, 17, 8.0, "main.py", "Métricas & Series", fsize=6.8)

    # audit_svc
    au_env = patches.Rectangle((81, 31), 20, 14.5, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(au_env)
    ax.text(82, 43.8, "audit_svc (:8004)", fontsize=6.6, fontweight='bold')
    ax.text(82, 41.8, "Trazabilidad NLP", fontsize=6.0, color=c_text_gray)
    dibujar_caja_artefacto(ax, 82, 32.5, 18, 8.0, "audit.py", "Log de Ingesta", fsize=6.8)

    # storage_svc
    st_env = patches.Rectangle((103, 31), 19, 14.5, ec=c_subline, fc=c_card_bg, lw=1)
    ax.add_patch(st_env)
    ax.text(104, 43.8, "storage_svc (:8005)", fontsize=6.6, fontweight='bold')
    ax.text(104, 41.8, "Gestor Archivos", fontsize=6.0, color=c_text_gray)
    dibujar_caja_artefacto(ax, 104, 32.5, 17, 8.0, "uploader.py", "Control MIME", fsize=6.8)

    # =========================================================================
    # 5. BASES DE DATOS («execution environments»)
    # =========================================================================
    db_grp = patches.Rectangle((6, 6), 118, 20.5, ec=c_line, fc="#FFFFFF", lw=1.4)
    ax.add_patch(db_grp)
    db_hdr = patches.Rectangle((6, 23), 118, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(db_hdr)
    ax.text(65, 24.7, "Capa de Persistencia Relacional y Dimensional (postgres:16-alpine)", fontsize=8, fontweight='bold', ha='center', va='center')

    # catalog_db (Izquierda)
    cat_env = patches.Rectangle((8, 7.5), 52, 14, ec=c_subline, fc=c_card_bg, lw=1.1)
    ax.add_patch(cat_env)
    ax.text(9, 19.8, "«execution env» giragroup_catalog_db (Puerto: 5433)", fontsize=7.2, fontweight='bold')
    dibujar_caja_artefacto(ax, 9, 12.2, 24, 6.5, "schema_catalogos.sql", "Catálogos 3NF", fsize=6.0)
    dibujar_caja_artefacto(ax, 34, 12.2, 24.5, 6.5, "seed_catalogos.sql", "748 inserts canónicos", fsize=6.2)
    ax.text(9, 9, "«volume» catalog_postgres_data -> /var/lib/postgresql/data", fontsize=6.3, fontstyle='italic', color="#222222")

    # giragroup_db (Derecha)
    dw_env = patches.Rectangle((63, 7.5), 59, 14, ec=c_subline, fc=c_card_bg, lw=1.2)
    ax.add_patch(dw_env)
    ax.text(64, 19.8, "«execution env» giragroup_db (Puerto Expuesto: 5432)", fontsize=7.2, fontweight='bold')
    dibujar_caja_artefacto(ax, 64, 12.2, 27, 6.5, "schema.sql", "Constelación DWH (24 tablas)", fsize=6.6)
    dibujar_caja_artefacto(ax, 93, 12.2, 27.5, 6.5, "seed_dim_tiempo.sql", "Dimensión Tiempo", fsize=6.0)
    ax.text(64, 9, "«volume» postgres_data -> /var/lib/postgresql/data", fontsize=6.3, fontstyle='italic', color="#222222")

    # =========================================================================
    # ALMACENAMIENTO PERSISTENTE Y BIND MOUNTS (Extrema Derecha)
    # =========================================================================
    stor_box = patches.Rectangle((128, 6), 28, 61, ec=c_line, fc="#FFFFFF", lw=1.3)
    ax.add_patch(stor_box)
    stor_hdr = patches.Rectangle((128, 63.5), 28, 3.5, ec=c_line, fc=c_header_bg, lw=1)
    ax.add_patch(stor_hdr)
    ax.text(142, 65.2, "Almacenamiento Persistente", fontsize=8, fontweight='bold', ha='center', va='center')

    # Bind mount uploads
    bm1 = patches.Rectangle((130, 48), 24, 13, ec=c_subline, fc=c_card_bg, lw=0.9, linestyle="--")
    ax.add_patch(bm1)
    ax.text(142, 58, "«bind mount»\n./uploads", fontsize=7.2, fontweight='bold', ha='center', color=c_text_dark)
    ax.text(142, 51.5, "Montado en:\n/app/uploads", fontsize=6.5, ha='center', color=c_text_gray)

    # Bind mount beto_local
    bm2 = patches.Rectangle((130, 31), 24, 15, ec=c_subline, fc=c_card_bg, lw=0.9, linestyle="--")
    ax.add_patch(bm2)
    ax.text(142, 42.5, "«bind mount»\nbeto_local", fontsize=6.8, fontweight='bold', ha='center', color=c_text_dark)
    ax.text(142, 35, "«artifact» model.safetensors\n«artifact» config.json\n(Pesos fine-tuned 768d)", fontsize=6.2, ha='center', color=c_text_gray)

    # Volúmenes administrados
    vol_box = patches.Rectangle((130, 8), 24, 21, ec=c_subline, fc=c_card_bg, lw=0.9)
    ax.add_patch(vol_box)
    ax.text(142, 25.5, "«volume» Docker", fontsize=7.2, fontweight='bold', ha='center', color=c_text_dark)
    ax.text(142, 17, "• postgres_data\n  (/var/lib/postgresql/data)\n• catalog_postgres_data\n  (/var/lib/postgresql/data)",
            fontsize=6.5, ha='center', color=c_text_gray)

    # =========================================================================
    # CONECTORES UML ORTOGONALES
    # =========================================================================
    def badge(x, y, text, fontsize=6.5, fontweight='normal'):
        ax.text(x, y, text, fontsize=fontsize, fontweight=fontweight, ha='center', va='center',
                bbox=dict(boxstyle="square,pad=0.2", fc="#FFFFFF", ec="#777777", lw=0.7))

    # 1. Navegador Web -> Gateway
    ax.plot([105, 105, 80, 80], [96.5, 93.5, 93.5, 86], color=c_line, lw=1.3)
    ax.annotate("", xy=(80, 86), xytext=(80, 88), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(92.5, 93.5, "«HTTP/WS :80»", fontsize=6.8, fontweight='bold')

    # 2. Power BI Desktop -> giragroup_db (Línea directa al borde derecho)
    ax.plot([141.5, 141.5, 125, 125, 122], [96.5, 94.5, 94.5, 14.5, 14.5], color=c_line, lw=1.5, linestyle="--")
    ax.annotate("", xy=(122, 14.5), xytext=(123.8, 14.5), arrowprops=dict(arrowstyle="->", lw=1.5, color=c_line))
    badge(125, 80, "«TCP Wire :5432»\nDirectQuery", fontsize=6.8, fontweight='bold')

    # 3. Gateway -> Frontend
    ax.plot([54, 48], [78.5, 78.5], color=c_line, lw=1.2)
    ax.annotate("", xy=(48, 78.5), xytext=(50, 78.5), arrowprops=dict(arrowstyle="->", lw=1.2, color=c_line))
    badge(51, 80.5, "«HTTP :5173»", fontsize=6.5)

    # 4. Gateway -> giragroup_api
    ax.plot([58, 28.5, 28.5], [71.5, 69, 67], color=c_line, lw=1.3)
    ax.annotate("", xy=(28.5, 67), xytext=(28.5, 68.5), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(33.5, 69, "«HTTP :8000» (/forecast, /kpis, /dataops)", fontsize=6.3, fontweight='bold')

    # 5. Gateway -> auth-service y notifications-service
    ax.plot([70, 70], [71.5, 67], color=c_line, lw=1.2)
    ax.annotate("", xy=(70, 67), xytext=(70, 68.5), arrowprops=dict(arrowstyle="->", lw=1.2, color=c_line))
    badge(70, 69, "«HTTP :8001»", fontsize=6.5)

    ax.plot([92, 92], [71.5, 67], color=c_line, lw=1.2)
    ax.annotate("", xy=(92, 67), xytext=(92, 68.5), arrowprops=dict(arrowstyle="->", lw=1.2, color=c_line))
    badge(92, 69, "«HTTP/WS :8002»", fontsize=6.5)

    # 6. Gateway -> audit y storage
    ax.plot([102, 112, 112], [71.5, 69, 67], color=c_line, lw=1.2)
    ax.annotate("", xy=(112, 67), xytext=(112, 68.5), arrowprops=dict(arrowstyle="->", lw=1.2, color=c_line))
    badge(112, 69, "«HTTP :8004, :8005»", fontsize=6.5)

    # 7. Core API <-> Pipeline NER
    ax.plot([28.5, 28.5], [48, 45.5], color=c_line, lw=1.3)
    ax.annotate("", xy=(28.5, 45.5), xytext=(28.5, 47), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(28.5, 46.8, "«HTTP :8006» Inferencia NER", fontsize=6.4)

    # 8. Pipeline -> catalog_db
    ax.plot([23, 23], [31, 21.5], color=c_line, lw=1.3)
    ax.annotate("", xy=(23, 21.5), xytext=(23, 23), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(23, 27.5, "«TCP :5433» RapidFuzz", fontsize=6.4)

    # 9. Core API -> giragroup_db (Canal libre entre core y aux en x=54)
    ax.plot([49.5, 54, 54, 63], [52, 52, 17.5, 17.5], color=c_line, lw=1.3)
    ax.annotate("", xy=(63, 17.5), xytext=(61, 17.5), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(54, 38, "«TCP :5432»\ndw_loader", fontsize=6.4)

    # 10. Microservicios -> giragroup_db
    ax.plot([90.5, 90.5], [31, 21.5], color=c_line, lw=1.1, linestyle=":")
    ax.annotate("", xy=(90.5, 21.5), xytext=(90.5, 23), arrowprops=dict(arrowstyle="->", lw=1.1, color=c_line))
    badge(90.5, 27.5, "«TCP :5432» DWH Pool", fontsize=6.4)

    # Guardado de archivos
    for path in OUTPUT_PATHS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
        print(f"Figura 3.3 generada con éxito en: {path}")

    plt.close(fig)

if __name__ == "__main__":
    generar_diagrama_despliegue()
