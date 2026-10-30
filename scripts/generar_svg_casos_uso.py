import os

svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 950" width="100%" height="100%" style="background:#ffffff; font-family:'Segoe UI', Arial, sans-serif;">
  <defs>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="2" dy="2" stdDeviation="3" flood-opacity="0.12" />
    </filter>
  </defs>

  <!-- Límite del Sistema -->
  <rect x="360" y="30" width="810" height="880" rx="12" fill="#f8fafc" stroke="#334155" stroke-width="2" stroke-dasharray="6,4" />
  <text x="765" y="65" fill="#0f172a" font-size="16" font-weight="bold" text-anchor="middle">Sistema de Inteligencia de Negocios GiraGroup BI (FastAPI Backend + React SPA)</text>

  <!-- Caso de Uso Central: Autenticación 2FA/OTP -->
  <rect x="640" y="95" width="250" height="55" rx="27" fill="#dbeafe" stroke="#1d4ed8" stroke-width="2" filter="url(#shadow)" />
  <text x="765" y="120" fill="#1e3a8a" font-size="12" font-weight="bold" text-anchor="middle">«include»</text>
  <text x="765" y="138" fill="#1e3a8a" font-size="12" font-weight="bold" text-anchor="middle">Autenticación 2FA / OTP (JWT)</text>

  <!-- Casos de Uso Columna 1 -->
  <!-- HU-01 -->
  <rect x="400" y="180" width="320" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="560" y="210" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-01: Gestión de Sesión y Perfil</text>

  <!-- HU-03 -->
  <rect x="400" y="260" width="320" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="560" y="290" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-03: Ingesta Documental Multiarchivo</text>

  <!-- HU-05 -->
  <rect x="400" y="340" width="320" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="560" y="370" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-05: Normalización Léxica RapidFuzz</text>

  <!-- HU-07 -->
  <rect x="400" y="420" width="320" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="560" y="450" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-07: Consolidación Data Warehouse</text>

  <!-- HU-09 -->
  <rect x="400" y="500" width="320" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="560" y="530" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-09: Consulta de Tableros CMI</text>

  <!-- HU-11 -->
  <rect x="400" y="580" width="320" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="560" y="610" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-11: Proyección de Metas y Viabilidad (OLS)</text>

  <!-- Casos de Uso Columna 2 -->
  <!-- HU-02 -->
  <rect x="800" y="180" width="330" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="965" y="210" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-02: Control de Roles y Usuarios RBAC</text>

  <!-- HU-04 -->
  <rect x="800" y="260" width="330" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="965" y="290" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-04: Extracción Semántica BETO NER</text>

  <!-- HU-06 -->
  <rect x="800" y="340" width="330" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="965" y="370" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-06: Revisión Humana HITL de Errores</text>

  <!-- HU-08 -->
  <rect x="800" y="420" width="330" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="965" y="450" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-08: Detección Alertas Tempranas</text>

  <!-- HU-10 -->
  <rect x="800" y="500" width="330" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="965" y="530" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-10: Pronóstico Demanda (Holt-Winters)</text>

  <!-- HU-12 -->
  <rect x="800" y="580" width="330" height="48" rx="24" fill="#ffffff" stroke="#475569" stroke-width="1.5" filter="url(#shadow)" />
  <text x="965" y="610" fill="#0f172a" font-size="12" font-weight="bold" text-anchor="middle">HU-12: Exportación Reportes (XLSX/PDF)</text>

  <!-- Flechas include hacia Autenticación (Punteadas) -->
  <g stroke="#94a3b8" stroke-width="1.2" stroke-dasharray="4,3">
    <line x1="560" y1="180" x2="690" y2="150" />
    <line x1="965" y1="180" x2="840" y2="150" />
    <line x1="560" y1="260" x2="710" y2="150" />
    <line x1="965" y1="260" x2="820" y2="150" />
    <line x1="560" y1="340" x2="730" y2="150" />
    <line x1="965" y1="340" x2="800" y2="150" />
    <line x1="560" y1="420" x2="745" y2="150" />
    <line x1="965" y1="420" x2="785" y2="150" />
    <line x1="560" y1="500" x2="755" y2="150" />
    <line x1="965" y1="500" x2="775" y2="150" />
    <line x1="560" y1="580" x2="760" y2="150" />
    <line x1="965" y1="580" x2="770" y2="150" />
  </g>

  <!-- Actores (5 Roles Reales) -->
  <!-- 1. ADMIN -->
  <g transform="translate(80, 160)">
    <circle cx="50" cy="20" r="16" fill="#ffffff" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="36" x2="50" y2="80" stroke="#0f172a" stroke-width="2" />
    <line x1="25" y1="52" x2="75" y2="52" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="80" x2="28" y2="120" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="80" x2="72" y2="120" stroke="#0f172a" stroke-width="2" />
    <text x="50" y="145" font-size="12" font-weight="bold" fill="#0f172a" text-anchor="middle">ADMIN</text>
    <text x="50" y="160" font-size="10.5" fill="#475569" text-anchor="middle">(Administrador General)</text>
  </g>

  <!-- 2. AUDITOR_CALIDAD -->
  <g transform="translate(80, 315)">
    <circle cx="50" cy="20" r="16" fill="#ffffff" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="36" x2="50" y2="80" stroke="#0f172a" stroke-width="2" />
    <line x1="25" y1="52" x2="75" y2="52" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="80" x2="28" y2="120" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="80" x2="72" y2="120" stroke="#0f172a" stroke-width="2" />
    <text x="50" y="145" font-size="12" font-weight="bold" fill="#0f172a" text-anchor="middle">AUDITOR_CALIDAD</text>
    <text x="50" y="160" font-size="10.5" fill="#475569" text-anchor="middle">(DataOps / HITL)</text>
  </g>

  <!-- 3. DIRECTOR_ACADEMICO -->
  <g transform="translate(80, 470)">
    <circle cx="50" cy="20" r="16" fill="#ffffff" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="36" x2="50" y2="80" stroke="#0f172a" stroke-width="2" />
    <line x1="25" y1="52" x2="75" y2="52" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="80" x2="28" y2="120" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="80" x2="72" y2="120" stroke="#0f172a" stroke-width="2" />
    <text x="50" y="145" font-size="12" font-weight="bold" fill="#0f172a" text-anchor="middle">DIRECTOR_ACADEMICO</text>
    <text x="50" y="160" font-size="10.5" fill="#475569" text-anchor="middle">(Gestión Docente)</text>
  </g>

  <!-- 4. ANALISTA_FINANCIERO -->
  <g transform="translate(80, 625)">
    <circle cx="50" cy="20" r="16" fill="#ffffff" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="36" x2="50" y2="80" stroke="#0f172a" stroke-width="2" />
    <line x1="25" y1="52" x2="75" y2="52" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="80" x2="28" y2="120" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="80" x2="72" y2="120" stroke="#0f172a" stroke-width="2" />
    <text x="50" y="145" font-size="12" font-weight="bold" fill="#0f172a" text-anchor="middle">ANALISTA_FINANCIERO</text>
    <text x="50" y="160" font-size="10.5" fill="#475569" text-anchor="middle">(Cartera y Cobranzas)</text>
  </g>

  <!-- 5. ANALISTA_MARKETING -->
  <g transform="translate(80, 775)">
    <circle cx="50" cy="20" r="16" fill="#ffffff" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="36" x2="50" y2="80" stroke="#0f172a" stroke-width="2" />
    <line x1="25" y1="52" x2="75" y2="52" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="80" x2="28" y2="120" stroke="#0f172a" stroke-width="2" />
    <line x1="50" y1="80" x2="72" y2="120" stroke="#0f172a" stroke-width="2" />
    <text x="50" y="130" font-size="12" font-weight="bold" fill="#0f172a" text-anchor="middle">ANALISTA_MARKETING</text>
    <text x="50" y="145" font-size="10.5" fill="#475569" text-anchor="middle">(Embudo Comercial)</text>
  </g>

  <!-- Conexiones Actor-CU (Líneas sólidas) -->
  <g stroke="#334155" stroke-width="1.2">
    <!-- ADMIN a casos de gestión y todos los módulos -->
    <line x1="160" y1="210" x2="400" y2="204" />
    <line x1="160" y1="210" x2="800" y2="204" />
    <line x1="160" y1="210" x2="400" y2="284" />
    <!-- AUDITOR a Ingesta, NER, HITL, DW -->
    <line x1="160" y1="365" x2="400" y2="284" />
    <line x1="160" y1="365" x2="800" y2="284" />
    <line x1="160" y1="365" x2="400" y2="364" />
    <line x1="160" y1="365" x2="800" y2="364" />
    <line x1="160" y1="365" x2="400" y2="444" />
    <!-- DIRECTOR ACAD a Alertas, CMI, HW, Export -->
    <line x1="160" y1="520" x2="800" y2="444" />
    <line x1="160" y1="520" x2="400" y2="524" />
    <line x1="160" y1="520" x2="800" y2="524" />
    <line x1="160" y1="520" x2="800" y2="604" />
    <!-- ANALISTA FINANCIERO a Alertas, CMI, OLS, Export -->
    <line x1="160" y1="675" x2="800" y2="444" />
    <line x1="160" y1="675" x2="400" y2="524" />
    <line x1="160" y1="675" x2="400" y2="604" />
    <line x1="160" y1="675" x2="800" y2="604" />
    <!-- ANALISTA MARKETING a CMI, HW, OLS, Export -->
    <line x1="160" y1="810" x2="400" y2="524" />
    <line x1="160" y1="810" x2="800" y2="524" />
    <line x1="160" y1="810" x2="400" y2="604" />
    <line x1="160" y1="810" x2="800" y2="604" />
  </g>

  <!-- Pie de figura -->
  <text x="360" y="930" font-size="11" fill="#64748b" font-style="italic">Fuente: Elaboración propia según backlog del sistema (FastAPI, RBAC, PyTorch BETO, PostgreSQL)</text>
</svg>
"""

with open("output/figura_casos_de_uso_general_sprint2.svg", "w", encoding="utf-8") as f:
    f.write(svg_content)

print("SVG generado en output/figura_casos_de_uso_general_sprint2.svg")
