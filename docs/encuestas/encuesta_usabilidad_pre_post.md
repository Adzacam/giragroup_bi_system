# Cuestionario de diagnóstico y evaluación — Sistema BI GiraGroup

Mismo instrumento del Apéndice C (F-2) de la tesis. Se aplica a las **mismas 10 personas** dos veces: **antes** (situación sin el sistema) y **después** (con el sistema). Respuestas anónimas: cada persona recibe un código (P01 a P10) y no se escribe su nombre.

**Participante:** P__  **Rol en el sistema:** ☐ Administrador ☐ Auditor de calidad (DataOps) ☐ Director académico ☐ Analista financiero ☐ Analista de marketing  **Área:** ☐ Academia ☐ Finanzas ☐ Marketing ☐ Calidad ☐ Admisiones  **Fecha:** ___/___/2026

**Quiénes responden:** 10 de los 33 colaboradores de planta, con selección intencional según el Cap. I, «Muestra». Tienen que ser usuarios directos que hayan usado el sistema, para poder responder la columna «Con el sistema». Se recomiendan 2 por cada rol RBAC (10 en total), y entre ellos los 3 coordinadores que consolidan los reportes.

> **Nota para Lean:** si el «antes» se responde ahora, recordando cómo se trabajaba sin el sistema, es un **pretest retrospectivo**. La tesis debe declararlo así en la metodología y en las limitaciones.

## Sección A — Preguntas de control (datos objetivos)
Escriba el número exacto.

| N° | Pregunta | Antes del sistema | Con el sistema |
|---|---|---|---|
| C1 | ¿Cuántas horas-persona le toma consolidar un ciclo académico completo? | | |
| C2 | ¿Cuántas fuentes distintas (archivos) debe abrir para generar un reporte final? | | |
| C3 | ¿Cuántos KPI puede consultar sin hacer trabajo manual previo? | | |
| C4 | ¿Cuántos errores o correcciones manuales hizo en el último ciclo académico? | | |

## Sección B — Escala Likert (1 a 5)
1 = Totalmente en desacuerdo · 2 = En desacuerdo · 3 = Ni de acuerdo ni en desacuerdo · 4 = De acuerdo · 5 = Totalmente de acuerdo

| N° | Dimensión | Afirmación | Antes (1–5) | Con el sistema (1–5) |
|---|---|---|---|---|
| 1 | Disponibilidad | La información académica de los diferentes programas es de fácil acceso cuando la necesito. | | |
| 2 | Automatización | Los reportes de indicadores se generan sin necesidad de intervención manual extensa. | | |
| 3 | Eficiencia temporal | El tiempo que invierto en consolidar información de un ciclo académico es aceptable. | | |
| 4 | Integración de datos | Me resulta sencillo relacionar datos de un estudiante distribuidos en distintos archivos. | | |
| 5 | Alertas académicas | Los reportes actuales me permiten identificar oportunamente a estudiantes con bajo rendimiento. | | |
| 6 | CMI / Decisiones | Cuento con indicadores centralizados y actualizados para tomar decisiones de gestión. | | |
| 7 | Ticket promedio | Puedo consultar el ticket promedio por programa de forma inmediata y actualizada. | | |
| 8 | Metas | Puedo verificar el cumplimiento de metas mensuales y anuales sin hacer cálculos manuales. | | |
| 9 | Conversión | Tengo visibilidad sobre la tasa de conversión de leads a inscritos en tiempo real. | | |

---
**Cómo se registran las respuestas:** en `docs/encuestas/likert_respuestas_plantilla.csv` (guardarlo como `docs/mediciones/likert_respuestas.csv`), una fila por participante y por momento (`pre` / `post`), con valores enteros de 1 a 5 en I1–I9 y números en C1–C4. No se escriben nombres, CI ni correos. Las celdas sin respuesta se dejan vacías; nunca se ponen ceros.
