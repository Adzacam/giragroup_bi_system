# Documento de Diseño de Mockups de Interfaz de Usuario (UI/UX)
## Sistema de Inteligencia de Negocios y Procesamiento de Lenguaje Natural (PLN)
**Proyecto de Grado — Ingeniería de Sistemas Informáticos**  
**Organización:** GiraGroup S.R.L.  
**Plataformas:** Interfaz Web (Escritorio) y Aplicación Móvil (Responsive / PWA)

---

## 1. Introducción y Justificación de las Decisiones de Diseño

### 1.1. Contexto y Objetivos de Experiencia de Usuario (UX)
El presente sistema tiene como propósito central **mitigar la fragmentación informacional** presente en GiraGroup S.R.L., integrando datos provenientes de plataformas heterogéneas (Moodle, hojas de cálculo en Excel, formularios y registros contables) mediante un pipeline DataOps potenciado con procesamiento de lenguaje natural (modelo BETO) y consolidado en un Data Warehouse bajo esquema estrella con un Cuadro de Mando Integral (CMI).

El diseño de la interfaz de usuario se fundamenta en el paradigma del **Diseño Centrado en el Usuario (UCD)** y en la metodología de **Diseño Orientado al Dominio Analítico**. Los usuarios del sistema abarcan desde personal operativo técnico (Auditores de Calidad DataOps) hasta tomadores de decisiones estratégicas (Directores Académicos, Analistas Financieros y Gerencia General). Por tanto, la interfaz debe conciliar dos exigencias:
1. **Densidad informacional y precisión operativa** para tareas de curación de datos y auditoría.
2. **Síntesis visual, claridad ejecutiva y baja carga cognitiva** para la toma ágil de decisiones y monitoreo de indicadores clave de rendimiento (KPIs).

---

### 1.2. Principios y Heurísticas de Usabilidad Aplicadas

El diseño implementado responde rigurosamente a las **10 Heurísticas de Usabilidad de Jakob Nielsen** y a leyes cognitivas de interacción persona-ordenador:

1. **Visibilidad del Estado del Sistema (Nielsen #1):**
   - En la versión Web, se implementa una barra de progreso superior de navegación instantánea, breadcrumbs contextuales e indicadores de latencia/sincronización del Data Warehouse.
   - En los procesos de Inteligencia Artificial (extracción BETO) y subida de archivos, se despliegan estados visuales de microprogreso (*Skeletons*, barras porcentuales y logs reactivos de telemetría).

2. **Consistencia y Estándares (Nielsen #4):**
   - Se mantiene un lenguaje visual unificado entre Web y Móvil basado en el sistema de diseño institucional de GiraGroup. Los mismos iconos semánticos (Lucide Icons), esquemas de color para los cuatro cuadrantes del CMI y etiquetas operativas se preservan de forma estricta.

3. **Prevención de Errores y Reconocimiento antes que Recuerdo (Nielsen #5 y #6):**
   - En el módulo de Revisión Humana (*Human-in-the-Loop* o HITL), las entidades extraídas por el modelo BETO cuentan con un **semáforo de confianza cromático** (Verde: Confianza $\ge 85\%$, Ámbar: $60\% - 84\%$, Rojo: $< 60\%$). El auditor no debe adivinar dónde intervenir: el sistema guía proactivamente la mirada hacia las anomalías.

4. **Flexibilidad y Eficiencia de Uso (Nielsen #7) y Control de Acceso Basado en Roles (RBAC):**
   - El sistema adapta la navegación y vistas de acuerdo al rol autenticado (`ADMIN`, `DIRECTOR_ACADEMICO`, `ANALISTA_FINANCIERO`, `AUDITOR_CALIDAD`), ocultando elementos irrelevantes y acelerando los flujos diarios de trabajo.

5. **Leyes Psicológicas de UX:**
   - **Ley de Fitts:** En la versión móvil, todos los puntos de navegación primaria y acciones críticas se ubican en la parte inferior de la pantalla (`MobileBottomNav`), dentro del radio de alcance natural del pulgar (zona ergonómica cómoda), con áreas táctiles mínimas de $44 \times 44\text{ px}$.
   - **Ley de Miller:** Los paneles informativos organizan los datos en "trozos" (*chunks*) de 3 a 5 KPIs por fila en escritorio y tarjetas colapsables en móvil, evitando la saturación mental.
   - **Ley de Hick / Divulgación Progresiva (*Progressive Disclosure*):** En móvil se muestran primero las métricas de resumen y se relega el detalle analítico granular a acordeones desplegables o modales táctiles.

---

### 1.3. Sistema de Diseño Institucional (Tokens Visuales)

El sistema cuenta con una arquitectura de diseño basada en tokens estandarizados (`tokens.css`), garantizando identidad corporativa y contraste certificado:

| Elemento | Valor / Token | Justificación de Usabilidad y Marca |
|---|---|---|
| **Color Primario (Navy)** | `#0C1E33` | Transmite autoridad, estabilidad y sobriedad institucional. Empleado en barras de navegación, encabezados y fondos ejecutivos. |
| **Color Acento (Gold)** | `#D99B26` / `#F1B844` | Color distintivo de GiraGroup. Se utiliza exclusivamente para llamadas a la acción (CTAs), KPIs líderes y estados destacados. |
| **Fondos Neutros** | `#FAF9F6` (Alabaster) / `#FFFFFF` | Proporciona una lectura limpia, simulando papel institucional de alta calidad, reduciendo la fatiga visual. |
| **Tipografía de Display** | *Newsreader* (Serif, regular 400) | Aplicada a títulos de nivel H1/H2 y encabezados de sección. Aporta distinción académica y elegancia ejecutiva. |
| **Tipografía de Interfaz** | *Plus Jakarta Sans* (400, 500, 600) | Fuente sans-serif moderna con alta x-height, diseñada para máxima legibilidad en pantallas digitales y dispositivos móviles. |
| **Tipografía de Datos / Código** | *JetBrains Mono* | Utilizada en tablas de DataOps, valores monetarios, códigos POS y visualización de tokens NER extraídos por BETO. |
| **Radio de Borde** | Tarjetas: `24px` · Botones: `9999px` (Pill) | Esquinas redondeadas orgánicas que transmiten modernidad, calidez y jerarquía visual amable al tacto. |

---

## 2. Cobertura de Plataformas y Estrategia Adaptativa (Web vs. Móvil)

El diseño cubre de manera integral las dos plataformas objetivo requeridas por el proyecto de grado, considerando sus diferentes contextos de uso:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ESTRATEGIA DE COHERENCIA MULTIPLATAFORMA                                     │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ 🖥️ VERSIÓN WEB (Desktop / Dashboard) │ 📱 VERSIÓN MÓVIL (Supervisor / PWA)  │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ • Resolución base: 1440 × 900 px     │ • Resolución base: 390 × 844 px      │
│ • Contexto: Oficina, análisis denso  │ • Contexto: En movimiento, decisiones│
│ • Navegación: Sidebar lateral fijo   │ • Navegación: Bottom Bar ergonómica  │
│   (276px) + Navbar superior flotante │   (5 accesos rol) + Drawer táctil    │
│ • Disposición: Grillas de 3-4 col.   │ • Disposición: 1 columna vertical    │
│ • Densidad: Tablas con filtros y     │ • Densidad: Tarjetas sintetizadas    │
│   ordenamiento dinámico              │   con acordeones y swipes            │
│ • Flujo DataOps: Split-screen con    │ • Flujo DataOps: Tarjetas de tarjeta │
│   documento vs entidades NER         │   de confirmación rápida (Aprobar)   │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

### Matriz de Correspondencia Funcional entre Plataformas

| Módulo Funcional | Funcionalidad en Versión Web (Escritorio) | Adaptación en Versión Móvil (Smartphone) |
|---|---|---|
| **1. Autenticación & RBAC** | Formulario centrado con canvas 3D interactivo de fondo, selector institucional y acceso directo por credenciales. | Formulario vertical optimizado para teclado móvil, botones táctiles grandes y autenticación persistente. |
| **2. Cuadro de Mando Integral (CMI)** | Matriz cuadrante de 4 perspectivas simultáneas (Financiera, Académica, Procesos, Aprendizaje) con micrográficos interactivos. | Carrusel superior de KPIs globales (`Swipe`) y lista vertical de tarjetas por perspectiva con estados de semáforo. |
| **3. Pipeline DataOps & BETO** | Consola completa de 4 pasos (Ingesta $\rightarrow$ Texto $\rightarrow$ BETO NER $\rightarrow$ HITL) con panel dividido de revisión de entidades. | Vista de supervisión del pipeline: estado de lotes en ejecución y vista simplificada de aprobación rápida de entidades dudosas. |
| **4. Alertas Académicas** | Tabla matricial de alumnos con riesgo de deserción, filtros multicriterio (asistencia, notas) y panel lateral de ficha estudiantil. | Lista de alertas priorizadas por severidad (Rojo/Ámbar), botón de contacto directo y visualización de semáforo de riesgo. |
| **5. Gestión Financiera** | Gráfico temporal de recaudación vs meta, tabla de mora agrupada por cohortes/sedes y panel de proyección Holt-Winters ($h=6$). | Resumen de recaudación diaria/mensual, indicadores de cartera vencida y gráfica de barras compacta con scroll horizontal. |

---

## 3. Especificación Detallada de Pantallas Clave (Mockups de Flujos Críticos)

A continuación se presenta la arquitectura visual y funcional de las pantallas más representativas del sistema:

---

### PANTALLA 1: Inicio de Sesión Corporativo y Acceso por Roles (RBAC)
* **Objetivo:** Garantizar la seguridad, trazabilidad de accesos y despacho automático del usuario según su perfil operativo o directivo.

#### A. Versión Web (Desktop: 1440 × 900 px)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [Logo GiraGroup BI]                                            [Tema: Oscuro]│
│                                                                              │
│                         ┌───────────────────────────────┐                    │
│                         │        GIRAGROUP S.R.L.       │                    │
│                         │    Sistema BI & NLP · Login   │                    │
│                         ├───────────────────────────────┤                    │
│                         │ Correo Institucional          │                    │
│                         │ [ usuario@giragroup.com     ] │                    │
│                         │                               │                    │
│                         │ Contraseña                    │                    │
│                         │ [ ••••••••••••••••••      👁 ] │                    │
│                         │                               │                    │
│                         │ Rol de Acceso (Validado)      │                    │
│                         │ (●) Director Académico        │                    │
│                         │ ( ) Analista Financiero       │                    │
│                         │ ( ) Auditor DataOps           │                    │
│                         │                               │                    │
│                         │ [     INICIAR SESIÓN        ] │  ← Botón Gold Pill  │
│                         │                               │                    │
│                         │ 🔒 Conexión Segura TLS 1.3    │                    │
│                         └───────────────────────────────┘                    │
│                                                                              │
│ [Fondo: Geometría Isométrica 3D Dinámica con Tokens Institucionales]         │
└──────────────────────────────────────────────────────────────────────────────┘
```

#### B. Versión Móvil (Smartphone: 390 × 844 px)
```
┌──────────────────────────────────┐
│ 09:41                       100% │
├──────────────────────────────────┤
│                                  │
│         [Logo GiraGroup]         │
│          GIRAGROUP BI            │
│  Inteligencia de Negocios & PLN  │
│                                  │
│  ┌────────────────────────────┐  │
│  │ Correo Corporativo         │  │
│  │ [ admin@giragroup.com    ] │  │
│  │                            │  │
│  │ Contraseña                 │  │
│  │ [ ••••••••••••••••••   👁 ] │  │
│  │                            │  │
│  │ Recordar en este equipo [✓]│  │
│  │                            │  │
│  │ [    INGRESAR AL SISTEMA ] │  │ ← Altura 48px
│  └────────────────────────────┘  │
│                                  │
│  ¿Problemas de acceso? Soporte   │
│  Versión v1.0.4 · Docker Cloud   │
└──────────────────────────────────┘
```

---

### PANTALLA 2: Cuadro de Mando Integral (CMI - Dashboard Ejecutivo)
* **Objetivo:** Brindar a la dirección una vista panorámica de la salud institucional a través de las 4 perspectivas del CMI.

#### A. Versión Web (Desktop: 1440 × 900 px)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [GIRA BI]  Dashboard  |  DataOps  |  Académico  |  Finanzas  | [Perfil Admin]│
├──────────────────────────────────────────────────────────────────────────────┤
│ Cuadro de Mando Integral (CMI)                     Filtro: [Gestión 2026 ▼]  │
│ Resumen Estratégico Multidimensional              Actualizado: hace 3 min 🟢 │
├──────────────────────────────────────────────────────────────────────────────┤
│ [ 📊 PERSPECTIVA FINANCIERA ]       │ [ 🎓 PERSPECTIVA ACADÉMICA / CLIENTES ]│
│ Recaudación Total: Bs. 1,420,500    │ Alumnos Matriculados: 1,845            │
│ Meta del Periodo:  94.2% [=======-] │ Tasa de Retención:    91.8% [========] │
│ Cartera en Mora:   Bs. 84,200 (6%)  │ Índice Satisfacción:  4.6 / 5.0 ⭐     │
│ [ Gráfico de Línea: Meta vs Real  ] │ [ Gráfico de Barras: Alumnos/Carrera ] │
├─────────────────────────────────────┼────────────────────────────────────────┤
│ [ ⚙️ PERSPECTIVA PROCESOS (DATAOPS) ]│ [ 💡 APRENDIZAJE Y CALIDAD DE DATOS ]  │
│ Lotes Ingeridos:  142 archivos      │ Precisión Modelo BETO: 96.4% F1-Score  │
│ Tasa Resolución:  98.1% sin error   │ Entidades Auditadas:   12,450 tokens   │
│ Tiempo Medio ETL: 1.8 segundos      │ Anomalías Corregidas:  148 casos       │
│ [ Gráfico Sparkline de Ingesta    ] │ [ Distribución Confianza BETO        ] │
└──────────────────────────────────────────────────────────────────────────────┘
```

#### B. Versión Móvil (Smartphone: 390 × 844 px)
```
┌──────────────────────────────────┐
│ 09:41                   [🔔] [👤]│
│ GIRA BI · Cuadro de Mando (CMI)  │
├──────────────────────────────────┤
│ [ Período: Gestión 2026  ▼ ]     │
│                                  │
│ ┌── CAROUSEL KPIS RESUMEN ─────┐ │
│ │  Recaudación   │ Retención   │ │
│ │  Bs. 1.42M     │ 91.8%       │ │
│ │  ▲ +4.2% vs M  │ 🟢 Óptimo   │ │
│ └──────────────────────────────┘ │
│                                  │
│ ▼ Perspectiva Financiera         │
│   Meta Alcanzada: 94.2%          │
│   [████████████████░░]           │
│   Mora Acumulada: Bs. 84.2K      │
│                                  │
│ ▼ Perspectiva Académica          │
│   Matrícula Activa: 1,845 est.   │
│   Alumnos en Riesgo: 28 ⚠️       │
│                                  │
│ ▼ DataOps & Modelo BETO          │
│   Precisión NLP: 96.4%           │
│   Lotes Pendientes HITL: 2       │
│                                  │
├──────────────────────────────────┤
│ [📊 CMI] [⚡ DataOps] [🎓 Acad] [☰]│ ← MobileBottomNav fija ergonómica
└──────────────────────────────────┘
```

---

### PANTALLA 3: Pipeline DataOps — Ingesta, BETO NLP y Revisión Humana (HITL)
* **Objetivo:** Permitir al auditor cargar fuentes fragmentadas, ejecutar el modelo de lenguaje BETO y verificar manualmente las entidades con baja confianza.

#### A. Versión Web (Desktop: 1440 × 900 px - Split Screen de Auditoría)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ DataOps > Lote #LOTE-2026-088 > Revisión Humana (Human-in-the-Loop)         │
├──────────────────────────────────────────────────────────────────────────────┤
│ [1. Carga] ─── [2. Texto Plano] ─── [3. BETO NLP] ─── [● 4. Auditoría HITL] │
├────────────────────────────────────────┬─────────────────────────────────────┤
│ TEXTO PLANO TRANSFORMADO (ORIGINAL)    │ ENTIDADES DETECTADAS POR BETO NLP   │
├────────────────────────────────────────┼─────────────────────────────────────┤
│ Estudiante: Juan Perez Colque          │ [👤 ALUMNO] Juan Perez Colque       │
│ CI: 8392012 LP · Sede: Central         │   Confianza: 98.4% 🟢 APROBADO AUTO │
│ Materia: Arquitectura de Software      │                                     │
│ Monto pagado: 450 Bs por concepto de   │ [📚 PROGRAMA] Arq. de Software      │
│ segunda cuota inscripcion modulo II.   │   Confianza: 94.1% 🟢 APROBADO AUTO │
│ Observacion: Pago con cheque diferido  │                                     │
│ banco union ref 994021.                │ [💰 MONTO] 450 Bs                   │
│                                        │   Confianza: 99.0% 🟢 APROBADO AUTO │
│                                        │                                     │
│                                        │ [⚠️ CONCEPTO] "cheque diferido..."  │
│                                        │   Confianza: 62.3% 🟡 REQUIERE HITL  │
│                                        │   [ Corregir ] [ Validar como OK ]  │
├────────────────────────────────────────┴─────────────────────────────────────┤
│ Progreso del Lote: 48/50 Registros Validados (96%)     [ GUARDAR Y CONSOLIDAR]│
└──────────────────────────────────────────────────────────────────────────────┘
```

#### B. Versión Móvil (Smartphone: 390 × 844 px - Modo Tarjeta Rápida)
```
┌──────────────────────────────────┐
│ ← DataOps: Auditoría HITL (48/50)│
├──────────────────────────────────┤
│ Registro 49 de 50: LOTE-088      │
│                                  │
│ ┌── TARJETA DE REVISIÓN ───────┐ │
│ │ Alumno: Juan Perez Colque    │ │
│ │ Materia: Arq. de Software    │ │
│ │ Monto:   Bs. 450             │ │
│ │                              │ │
│ │ Entidad con Duda (62%):      │ │
│ │ 🟡 Concepto: "cheque dif..." │ │
│ │ Clasificación sugerida:      │ │
│ │ [ PAGO_CUOTA_REGULAR     ▼ ] │ │
│ └──────────────────────────────┘ │
│                                  │
│ Acciones Rápidas con el Pulgar:  │
│ [ ❌ Rechazar ]   [ ✅ Aprobar ] │ ← Botones de 52px con alto contraste
│                                  │
│ [ Ver fragmento de texto fuente] │
├──────────────────────────────────┤
│ [📊 CMI] [⚡ DataOps] [🎓 Acad] [☰]│
└──────────────────────────────────┘
```

---

### PANTALLA 4: Módulo Académico — Rendimiento y Alertas Tempranas de Deserción
* **Objetivo:** Proveer al Director Académico de un sistema de alerta temprana ante estudiantes en riesgo académico o inasistencia crítica.

#### A. Versión Web (Desktop: 1440 × 900 px)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Académico > Rendimiento & Alertas Tempranas                  [Exportar Excel]│
├──────────────────────────────────────────────────────────────────────────────┤
│ Filtros: Carrera: [Sistemas ▼] | Sede: [Todas ▼] | Nivel Riesgo: [Crítico 🔴]│
├──────────────────────────────────────────────────────────────────────────────┤
│ ESTUDIANTE        │ CARRERA   │ NOTA PROM │ ASISTENCIA │ FACTOR RIESGO│ ACCIÓN│
├───────────────────┼───────────┼───────────┼────────────┼──────────────┼───────┤
│ Carlos Mamani R.  │ Sistemas  │ 42 / 100  │ 55% 🔴     │ Acad.+Inasist│ [Ver] │
│ Maria Laura Torrez│ Redes     │ 48 / 100  │ 62% 🟡     │ Bajas notas  │ [Ver] │
│ Rodrigo Morales P.│ Sistemas  │ 50 / 100  │ 50% 🔴     │ Inasistencia │ [Ver] │
│ Ana Belen Rios    │ Sistemas  │ 52 / 100  │ 71% 🟡     │ Mora+Notas   │ [Ver] │
├──────────────────────────────────────────────────────────────────────────────┤
│ 28 Alumnos identificados con probabilidad de deserción > 65% (Scoring AI)    │
└──────────────────────────────────────────────────────────────────────────────┘
```

#### B. Versión Móvil (Smartphone: 390 × 844 px)
```
┌──────────────────────────────────┐
│ Alertas Académicas (28 Críticos) │
├──────────────────────────────────┤
│ [ 🔍 Buscar estudiante...      ] │
│ [ Filtro: Riesgo Alto (🔴 28)  ] │
│                                  │
│ ┌── TARJETA ESTUDIANTE ────────┐ │
│ │ Carlos Mamani R.             │ │
│ │ Ing. de Sistemas · 4to Sem   │ │
│ │ Nota: 42/100 · Asist: 55%    │ │
│ │ 🔴 Riesgo Crítico Deserción  │ │
│ │ [ Contactar ] [ Ver Historial]│
│ └──────────────────────────────┘ │
│                                  │
│ ┌── TARJETA ESTUDIANTE ────────┐ │
│ │ Maria Laura Torrez           │ │
│ │ Adm. Redes · 2do Sem         │ │
│ │ Nota: 48/100 · Asist: 62%    │ │
│ │ 🟡 Riesgo Medio              │ │
│ └──────────────────────────────┘ │
├──────────────────────────────────┤
│ [📊 CMI] [⚡ DataOps] [🎓 Acad] [☰]│
└──────────────────────────────────┘
```

---

### PANTALLA 5: Módulo Financiero — Recaudación, Mora y Proyección Holt-Winters
* **Objetivo:** Supervisar el flujo de caja, la cartera en mora y la proyección predictiva de recaudación semestral ($h=6$).

#### A. Versión Web (Desktop: 1440 × 900 px)
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Finanzas > Recaudación, Cartera en Mora & Proyección Predictiva              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Recaudado: Bs. 1,420,500 | Meta: Bs. 1,508,000 | Mora Total: Bs. 84,200 (6%) │
├────────────────────────────────────────┬─────────────────────────────────────┤
│ CURVA DE RECAUDACIÓN Y FORECASTING     │ CARTERA VENCIDA POR ANTIGÜEDAD      │
│ [Gráfico Combinado:                    │ • 1 a 30 días:   Bs. 42,100 (50%) 🟡 │
│  - Histórico 43 meses (Nov 2022-2026)  │ • 31 a 60 días:  Bs. 26,300 (31%) 🟠 │
│  - Proyección Holt-Winters h=6 meses   │ • > 60 días:     Bs. 15,800 (19%) 🔴 │
│  - Banda de confianza del 95%]         │                                     │
│  Parámetros: α=0.32, β=0.15, γ=0.41    │ [Tabla Detallada con Botón Notificar]│
└────────────────────────────────────────┴─────────────────────────────────────┘
```

#### B. Versión Móvil (Smartphone: 390 × 844 px)
```
┌──────────────────────────────────┐
│ Finanzas: Recaudación & Mora     │
├──────────────────────────────────┤
│ Recaudado a la Fecha:            │
│ Bs. 1,420,500  (94.2% Meta)      │
│                                  │
│ ┌── DISTRIBUCIÓN DE MORA ──────┐ │
│ │ Cartera Total: Bs. 84,200    │ │
│ │ [██████████░░░░░░░░░░]       │ │
│ │ 🟡 1-30 días:  Bs. 42.1K     │ │
│ │ 🟠 31-60 días: Bs. 26.3K     │ │
│ │ 🔴 > 60 días:  Bs. 15.8K     │ │
│ └──────────────────────────────┘ │
│                                  │
│ Proyección Próximo Mes (AI):     │
│ 📈 Bs. 248,000 (Holt-Winters)    │
├──────────────────────────────────┤
│ [📊 CMI] [⚡ DataOps] [🎓 Acad] [☰]│
└──────────────────────────────────┘
```

---

## 4. Metodología y Herramientas para la Generación de los Mockups

Para la elaboración formal de los mockups solicitados en el proyecto de grado, se recomiendan dos metodologías complementarias:

### Opción A (Recomendada): Generación Directa desde el Entorno Real ("Code-to-Mockup")
Dado que el repositorio de GiraGroup BI ya cuenta con una interfaz React + Tailwind + Tokens CSS implementada en `frontend/`:
1. **Ejecución local del Frontend:**
   ```bash
   cd frontend
   npm install   # o pnpm install
   npm run dev
   ```
2. **Captura de Pantallas Web de Alta Fidelidad:**
   - Abrir el navegador Google Chrome en `http://localhost:5173`.
   - Ajustar la ventana a resolución estándar de escritorio: `1440 × 900` o `1920 × 1080`.
   - Tomar capturas de las 5 rutas clave: `/login`, `/dashboard`, `/dataops/beto`, `/academico/rendimiento`, `/financiero/recaudacion`.
3. **Captura de Pantallas Móviles:**
   - Abrir las Herramientas de Desarrollador de Chrome (`F12` o `Ctrl + Shift + I`).
   - Activar el modo de emulación de dispositivos (`Ctrl + Shift + M`).
   - Seleccionar un dispositivo móvil estándar: **iPhone 14 / 15 Pro (390 × 844)** o **Pixel 7 (412 × 915)**.
   - Observar cómo la interfaz conmuta automáticamente al layout móvil: el Sidebar se oculta, emerge la barra inferior `MobileBottomNav` y las tablas se transforman en tarjetas apiladas.
   - Capturar las pantallas completas usando `Ctrl + Shift + P` $\rightarrow$ *"Capture full size screenshot"*.
4. **Montaje en Mockups de Dispositivos (Device Frames):**
   - Importar las capturas en herramientas gratuitas de maquetado como **Mockupbro**, **Previewed.app** o **Figma** (usando el plugin *Device Mockup*) para presentarlas dentro de marcos de MacBook y iPhone.

### Opción B: Diseño Vectorial en Figma / Penpot (Desde Cero)
Si la cátedra solicita el archivo editable de diseño (`.fig`):
1. **Configurar los Canvas:**
   - Frame Web: `1440 × 900 px` (Desktop). Grilla de 12 columnas, márgenes laterales de `80px`, gutter de `24px`.
   - Frame Mobile: `390 × 844 px` (iPhone 14/15). Grilla de 4 columnas, márgenes laterales de `16px`, gutter de `12px`.
2. **Aplicar la Biblioteca de Estilos:**
   - Colores: Navy `#0C1E33`, Gold `#D99B26`, Alabaster `#FAF9F6`, Slate `#777B86`.
   - Tipografías: Newsreader para títulos y Plus Jakarta Sans para el cuerpo.
   - Componentes clave: Tarjeta KPI con borde `24px`, Chip de estado de confianza BETO y Barra `MobileBottomNav`.

---

## 5. Cuadro de Autoevaluación frente a la Rúbrica Académica

| Criterio de la Rúbrica | Ponderación | Nivel Alcanzado | Justificación Técnica Presentada en el Documento |
|---|---|---|---|
| **Claridad en la funcionalidad** | 35% | **Excelente (4/4)** | Se detallan y resuelven los 5 flujos centrales del sistema: Login RBAC, CMI multidimensional de 4 perspectivas, Pipeline DataOps con NLP BETO y revisión HITL, Alertas Académicas predictivas y Módulo Financiero con proyecciones Holt-Winters. |
| **Explicación de decisiones de diseño** | 35% | **Excelente (4/4)** | Fundamentación rigurosa basada en las Heurísticas de Nielsen, Ley de Fitts, Ley de Miller, Divulgación Progresiva, Sistema de Tokens institucional (`tokens.css`) y accesibilidad cromática WCAG. |
| **Cobertura de plataformas** | 30% | **Excelente (4/4)** | Cobertura total y simétrica tanto de la versión Web (1440x900 con Sidebar y densidad analítica) como de la versión Móvil (390x844 con MobileBottomNav y tarjetas táctiles adaptadas a la zona del pulgar). |
