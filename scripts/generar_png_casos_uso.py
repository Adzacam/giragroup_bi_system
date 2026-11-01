import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Configurar fuentes legibles >= 11 pt
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "figure.autolayout": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.dpi": 300
})

fig, ax = plt.subplots(figsize=(16, 12))
ax.set_xlim(0, 16)
ax.set_ylim(0, 12)
ax.axis("off")

# Límite del Sistema
system_box = patches.FancyBboxPatch((4.5, 0.5), 11.0, 11.0, boxstyle="round,pad=0.2", fc="#f8fafc", ec="#1e293b", lw=2, linestyle="-")
ax.add_patch(system_box)
ax.text(10.0, 11.2, "Sistema de Inteligencia de Negocios GiraGroup BI (Casos de Uso HU-01 a HU-12)", color="#0f172a", weight="bold", fontsize=13, ha="center")

# Actores (Roles Reales) a la izquierda
actores = [
    {"nombre": "ADMIN\n(Administrador General)", "y": 9.8, "roles": ["HU-01", "HU-02", "HU-03", "HU-04", "HU-05", "HU-06", "HU-07", "HU-08", "HU-09", "HU-10", "HU-11", "HU-12"]},
    {"nombre": "AUDITOR_CALIDAD\n(DataOps / HITL)", "y": 7.6, "roles": ["HU-03", "HU-04", "HU-05", "HU-06", "HU-07", "HU-08", "HU-09", "HU-12"]},
    {"nombre": "DIRECTOR_ACADEMICO\n(Gestión Docente)", "y": 5.4, "roles": ["HU-08", "HU-09", "HU-10", "HU-12"]},
    {"nombre": "ANALISTA_FINANCIERO\n(Tesorería y Cartera)", "y": 3.2, "roles": ["HU-08", "HU-09", "HU-11", "HU-12"]},
    {"nombre": "ANALISTA_MARKETING\n(Demanda y Cursos)", "y": 1.2, "roles": ["HU-09", "HU-10", "HU-11", "HU-12"]}
]

for act in actores:
    y = act["y"]
    # Dibujar monigote UML
    head = patches.Circle((1.5, y + 0.4), 0.22, ec="#0f172a", fc="#ffffff", lw=1.8)
    ax.add_patch(head)
    ax.plot([1.5, 1.5], [y + 0.18, y - 0.25], color="#0f172a", lw=1.8) # cuerpo
    ax.plot([1.1, 1.9], [y + 0.05, y + 0.05], color="#0f172a", lw=1.8) # brazos
    ax.plot([1.5, 1.2], [y - 0.25, y - 0.6], color="#0f172a", lw=1.8)  # pierna izq
    ax.plot([1.5, 1.8], [y - 0.25, y - 0.6], color="#0f172a", lw=1.8)  # pierna der
    ax.text(1.5, y - 0.85, act["nombre"], fontsize=10.5, weight="bold", ha="center", va="top", color="#0f172a")

# Caso de Uso Central: Autenticación 2FA/OTP
auth_box = patches.FancyBboxPatch((8.2, 9.8), 3.6, 0.8, boxstyle="round,pad=0.15", fc="#dbeafe", ec="#1d4ed8", lw=2)
ax.add_patch(auth_box)
ax.text(10.0, 10.2, "«include»\nAutenticación 2FA / OTP", fontsize=11, weight="bold", color="#1e3a8a", ha="center", va="center")

# 12 Casos de Uso (HU-01 a HU-12)
casos_uso = [
    {"id": "HU-01", "nombre": "HU-01: Gestión de Sesión y Credenciales", "x": 6.8, "y": 8.7},
    {"id": "HU-02", "nombre": "HU-02: Control de Roles y Usuarios RBAC", "x": 13.2, "y": 8.7},
    {"id": "HU-03", "nombre": "HU-03: Ingesta Documental Multiarchivo", "x": 6.8, "y": 7.3},
    {"id": "HU-04", "nombre": "HU-04: Extracción Semántica BETO NER", "x": 13.2, "y": 7.3},
    {"id": "HU-05", "nombre": "HU-05: Normalización Léxica RapidFuzz", "x": 6.8, "y": 5.9},
    {"id": "HU-06", "nombre": "HU-06: Revisión Humana HITL de Errores", "x": 13.2, "y": 5.9},
    {"id": "HU-07", "nombre": "HU-07: Consolidación Data Warehouse", "x": 6.8, "y": 4.5},
    {"id": "HU-08", "nombre": "HU-08: Detección Alertas Tempranas", "x": 13.2, "y": 4.5},
    {"id": "HU-09", "nombre": "HU-09: Consulta de Tableros CMI", "x": 6.8, "y": 3.1},
    {"id": "HU-10", "nombre": "HU-10: Pronóstico Demanda Holt-Winters", "x": 13.2, "y": 3.1},
    {"id": "HU-11", "nombre": "HU-11: Metas y Viabilidad OLS", "x": 6.8, "y": 1.7},
    {"id": "HU-12", "nombre": "HU-12: Exportación de Reportes (XLSX/PDF)", "x": 13.2, "y": 1.7},
]

pos_map = {}
for cu in casos_uso:
    pos_map[cu["id"]] = (cu["x"], cu["y"])
    box = patches.FancyBboxPatch((cu["x"] - 2.8, cu["y"] - 0.45), 5.6, 0.9, boxstyle="round,pad=0.15", fc="#ffffff", ec="#334155", lw=1.5)
    ax.add_patch(box)
    ax.text(cu["x"], cu["y"], cu["nombre"], fontsize=11, weight="bold", color="#1e293b", ha="center", va="center")

    # Línea include hacia Autenticación
    ax.plot([cu["x"], 10.0], [cu["y"] + 0.45, 9.8], color="#94a3b8", lw=1.0, linestyle=":")

# Conexiones de Actores a Casos de Uso
for act in actores:
    y_act = act["y"]
    for hid in act["roles"]:
        cu_x, cu_y = pos_map[hid]
        ax.plot([2.5, cu_x - 2.8], [y_act, cu_y], color="#475569", lw=1.1, alpha=0.85)

# Pie de figura
ax.text(0.5, 0.1, "Fuente: Elaboración propia según backlog del proyecto (FastAPI, RBAC, PyTorch BETO, PostgreSQL)", fontsize=11, style="italic", color="#64748b")

plt.tight_layout()
plt.savefig("output/figura_casos_de_uso_general_sprint2.png", dpi=300, bbox_inches="tight")
print("PNG generado en output/figura_casos_de_uso_general_sprint2.png")
