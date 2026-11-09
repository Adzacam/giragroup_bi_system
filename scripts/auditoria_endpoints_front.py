"""Ronda 9, tarea 1: endpoints que llama el frontend (src/api/*.js) frente al OpenAPI vigente del backend (docs/evidencias/openapi_actual.json)."""
import json, re, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
spec = json.loads((R / "docs/evidencias/openapi_actual.json").read_text(encoding="utf-8"))
def norm(p): return re.sub(r"\{[^}]+\}", "{}", p.split("?")[0])
api = {(m.upper(), norm(p)): (p, op) for p, ms in spec["paths"].items() for m, op in ms.items() if m in ("get", "post", "put", "patch", "delete")}
usados = {}
for f in sorted((R / "frontend/src/api").glob("*.js")):
    s = f.read_text(encoding="utf-8")
    base = dict(re.findall(r"const (?:BASE_URL|BASE)\s*=\s*['\"]([^'\"]+)['\"]", s) and [("BASE", re.findall(r"const (?:BASE_URL|BASE)\s*=\s*['\"]([^'\"]+)['\"]", s)[0])])
    for m in re.finditer(r"client\.(get|post|put|patch|delete)\(\s*([`'\"])(.*?)\2", s, re.S):
        url = m.group(3).replace("${BASE_URL}", base.get("BASE", "")).replace("${BASE}", base.get("BASE", ""))
        url = re.sub(r"\$\{[^}]+\}", "{}", url)
        usados.setdefault((m.group(1).upper(), norm(url)), set()).add(f.stem)
filas = []
for (m, p), fs in sorted(usados.items(), key=lambda x: x[0][1]):
    filas.append((m, p, ", ".join(sorted(fs)), "SI" if (m, p) in api else "NO"))
no = [f for f in filas if f[3] == "NO"]
sin_uso = sorted(k for k in api if k not in usados)
out = {"endpoints_backend": len(api), "llamadas_distintas_del_front": len(filas), "coinciden": len(filas) - len(no), "sin_coincidencia": no,
       "backend_sin_uso_en_front": len(sin_uso)}
Path(R / "docs/evidencias/auditoria_endpoints_front.json").write_text(json.dumps({**out, "llamadas": filas, "sin_uso": sin_uso}, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
for k in sin_uso:
    if "dataops" in k[1] and ("review-tray" in k[1]): print("backend sin uso:", k)

# Tabla en Markdown: endpoint, ¿lo usa el front?, ¿coincide el contrato (método + ruta)?, pantalla afectada
PANTALLA = {"dataopsApi": "DataOps (ingesta, lectura BETO, bandeja HITL)", "kpiApi": "Dashboards / CMI", "cmiApi": "CMI web", "authApi": "Login", "usersApi": "Gestión de usuarios",
            "notificationsApi": "Notificaciones", "catalogApi": "Catálogos maestros / Cobranzas", "academicApi": "Rendimiento y alertas", "forecastApi": "Proyecciones",
            "powerbiApi": "CMI · Power BI", "reportesApi": "Centro de reportes", "auditApi": "Auditoría"}
SERVICIOS = {"authApi", "usersApi", "notificationsApi"}  # los atienden auth/notifications-service detrás del gateway, no el OpenAPI de la API
L = ["| Endpoint | ¿Lo usa el front? | ¿Coincide el contrato? | Pantalla afectada |", "|---|---|---|---|"]
for m, p, fs, ok in filas:
    pant = "; ".join(sorted({PANTALLA.get(f, f) for f in fs.split(", ")}))
    coincide = "sí" if ok == "SI" else ("sí (microservicio tras el gateway)" if set(fs.split(", ")) <= SERVICIOS else "NO")
    L.append(f"| {m} {p} | sí | {coincide} | {pant} |")
for m, p in sin_uso:
    L.append(f"| {m} {p} | no | — | — |")
Path(R / "docs/evidencias/auditoria_endpoints_front.md").write_text("\n".join(L) + "\n", encoding="utf-8")
