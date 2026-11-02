# GiraGroup BI System

Sistema de Inteligencia de Negocios con Procesamiento de Lenguaje Natural (BETO) y Cuadro de Mando Integral para GiraGroup Posgrado. Integra fuentes académicas, financieras y comerciales heterogéneas (Excel, CSV, Google Forms, Moodle) en un Data Warehouse en constelación, con revisión humana (HITL) de los casos dudosos y pronóstico de demanda con Holt-Winters.

> Todo corre en Docker. En la máquina solo hacen falta **Git** y **Docker Desktop** (con WSL2 en Windows).

---

## Arquitectura

| Servicio (contenedor) | Función | Puerto en el host |
|---|---|---|
| `gateway` | Nginx: punto de entrada único y cabeceras de seguridad | **80** |
| `web` | Frontend React 18 + Vite (PWA) | **5173** |
| `api` | Monolito modular FastAPI: DataOps, pipeline, KPIs, forecast, catálogos, riesgos, reportes | 8000 |
| `auth-service` | Autenticación, 2FA por OTP y usuarios | interno (8001) |
| `notifications-service` | Notificaciones y WebSocket | interno (8002) |
| `audit-service` | Auditoría y observabilidad | interno (8004) |
| `pipeline` | Servidor de inferencia BETO (PyTorch) | interno (8006) |
| `db` | PostgreSQL 16: Data Warehouse (7 tablas de hechos) | `127.0.0.1:5434` |
| `catalog_db` | PostgreSQL 16: catálogos institucionales 3NF | `127.0.0.1:5433` |

El frontend llama a rutas relativas `/api/...`; Vite las reenvía al gateway, y el gateway, a cada servicio.

---

## Puesta en marcha

```bash
git clone https://github.com/Adzacam/giragroup_bi_system.git
```

```bash
cd giragroup_bi_system
```

Crear el `.env` a partir de la plantilla (Git Bash / Linux):

```bash
cp .env.example .env
```

En PowerShell: `Copy-Item .env.example .env`. Antes de usarlo fuera de tu máquina, cambia `SECRET_KEY` y las contraseñas de base de datos. Las variables SMTP son opcionales (ver [Inicio de sesión](#inicio-de-sesión)).

Levantar todo:

```bash
docker compose up -d --build
```

En Windows también puedes usar `iniciar_sistema.bat`, `apagar_sistema.bat` y `reconstruir_sistema.bat`.

La primera vez tarda varios minutos: descarga imágenes, crea el esquema con `db/schema.sql`, aplica las migraciones pendientes al arrancar la API y siembra los usuarios iniciales. Para comprobar que los 9 contenedores están arriba:

```bash
docker compose ps
```

### Accesos

| Qué | URL |
|---|---|
| Aplicación web | http://localhost:5173 |
| API (Swagger) | http://localhost:8000/docs |
| Estado de la API | http://localhost/api/v1/health |

---

## Inicio de sesión

El acceso usa contraseña + código OTP de 6 dígitos (2FA). Si `SMTP_HOST` está vacío en `.env`, el código no se envía por correo: se imprime en el log del servicio de autenticación.

```bash
docker logs --tail 20 giragroup_auth_svc
```

Usuarios iniciales (solo desarrollo), creados por `backend/seed_users.py`, donde están sus correos y la contraseña inicial:

| Usuario | Rol |
|---|---|
| `admin_general` | `ADMIN` |
| `auditor_dataops` | `AUDITOR_CALIDAD` |
| `dir_academica` | `DIRECTOR_ACADEMICO` |
| `analista_fin` | `ANALISTA_FINANCIERO` |
| `analista_mkt` | `ANALISTA_MARKETING` |

El sembrado no sobrescribe contraseñas ya cambiadas. En producción, cambia todas las contraseñas iniciales y desactiva las cuentas técnicas de pruebas (`qa_admin`, `loadtest_user`).

---

## Motor BETO (NER)

El servidor `pipeline` carga el modelo afinado de `pipeline/semantic/beto_local/`. Esa carpeta no se versiona (~420 MB):

- Si no existe, el sistema usa como respaldo `mrm8488/bert-spanish-cased-finetuned-ner` (Hugging Face).
- Para regenerar el modelo afinado con el corpus de `data/`, en el host, con un entorno que tenga `pipeline/requirements.txt` instalado. El contenedor `pipeline` no monta `scripts/` ni `data/`. Luego reinicia `pipeline` para que lo cargue.

```bash
python scripts/entrenar_beto_robusto.py
```

### ¿CPU o GPU?

BETO **no necesita GPU**. CPU y GPU dan resultados idénticos (F1 0,973 y los mismos índices de confianza sobre las 180 frases de `data/test_gold_real.jsonl`); solo cambia la velocidad:

| Medido (2026-11-01) | CPU, 8 hilos | GPU (RTX 5060 Laptop) |
|---|---|---|
| Lote de ingesta (`/infer-batch`) | 31,6 ms/oración | 8,0 ms/oración |
| Una oración suelta (`/infer`) | 101 ms | 57 ms |
| Lote de ~1 000 filas | ~30 s | ~8 s |
| Memoria | ~540 MB de RAM | ~1 GB de VRAM (estimado) |

**Recomendación**

- **Servidor de producción:** CPU (configuración por defecto). La ingesta trabaja por lotes, así que unos 30 s por cada 1 000 filas es aceptable, y no depende de tener una tarjeta NVIDIA.
- **Equipo de desarrollo o demo con GPU NVIDIA:** usar el override de GPU, unas 4 veces más rápido.

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d pipeline
```

Para volver a CPU:

```bash
docker compose up -d pipeline
```

No exijas la GPU en `docker-compose.yml`: en una máquina sin NVIDIA el contenedor `pipeline` no arrancaría.

Variables de ajuste en el servicio `pipeline`:

| Variable | Por defecto | Efecto |
|---|---|---|
| `TORCH_NUM_THREADS` | 8 (compose) | Hilos de PyTorch. Sin límite, PyTorch usa todos los núcleos del host y cada pasada tarda ~1 s. |
| `BETO_INT8` | 0 | Cuantización int8 en CPU (~20 % más rápida). **Desaconsejada:** baja el F1 de 0,973 a 0,920. |

---

## Base de datos

Conexión desde herramientas externas (DBeaver, Power BI). Usuario y contraseña: los del `.env` (`DATABASE_URL`).

| Base | Host | Puerto |
|---|---|---|
| Data Warehouse `giragroup_db` | `localhost` | **5434** |
| Catálogos `giragroup_catalog_db` | `localhost` | **5433** |

Dentro de Docker los servicios se conectan por el nombre del contenedor y el puerto 5432, como indica `.env.example`.

**Power BI:** el tablero está en `powerbi/dashboards/giragroup_cmi.pbix` y la guía de conexión, en `powerbi/dashboards/guia_integracion_powerbi_forecasting.md`.

**Vaciar los datos cargados** (hechos, staging, lotes y logs; conserva `users`, `dim_tiempo` y `cat_institucion`):

```bash
python scripts/reset_dw.py --confirm
```

**Borrar todo**, incluidos usuarios y esquema (se recrean al volver a levantar):

```bash
docker compose down -v
```

---

## Pruebas

```bash
python -m pytest tests backend/tests_root -q
```

Puertas de salida a producción. Las de `-m readiness_live` necesitan la pila en marcha y variables `READINESS_*`; ver la cabecera del archivo:

```bash
python -m pytest tests/readiness -q
```

Pruebas de carga (Locust; instrucciones en el propio archivo):

```bash
locust -f tests/load/locust_readiness.py --host http://localhost
```

---

## Comandos frecuentes

| Acción | Comando |
|---|---|
| Ver estado | `docker compose ps` |
| Logs de un servicio | `docker compose logs -f api` |
| Reiniciar todo | `docker compose restart` |
| Aplicar cambios de Dockerfile o dependencias | `docker compose up -d --build` |
| Apagar (conserva datos) | `docker compose down` |

---

## Problemas comunes

**El login o cualquier llamada da 404 en `localhost:5173` (pero funciona en `localhost`).** Vite perdió el proxy hacia el gateway, típicamente tras cambiar de rama con los contenedores encendidos. Solución:

```bash
docker restart giragroup_web
```

**No llega el código OTP.** Sin SMTP configurado, el código aparece en `docker logs giragroup_auth_svc`.

**`pipeline` no arranca con el override de GPU.** Falta el soporte de GPU de Docker o los drivers NVIDIA; vuelve a CPU con `docker compose up -d pipeline`.

**Inferencia BETO muy lenta (~1 s por oración).** Revisa que `TORCH_NUM_THREADS` esté definido en el servicio `pipeline`.

---

## Documentación

- `docs/auditoria/production_readiness_2026-11-01.md`: auditoría de preparación para producción (hallazgos y remediación).
- `docs/auditoria/plan_maestro_ejecucion.md`: plan por fases, mediciones y estado de las correcciones.
- `docs/apendices/diccionario_datos.md`: diccionario de datos del DW y de los catálogos.
- `docs/architecture/`: metodología de pronóstico y auditorías de sprints.
- `docs/postman_collection.json`: colección de la API.

## Estructura

```text
backend/          API FastAPI (routers, services, models, schemas, tests_root)
services/         Microservicios auth, notifications y audit
pipeline/         Ingesta, normalización, BETO (semantic/) y analítica (analytics/)
frontend/         SPA React + Vite (PWA)
db/               Esquemas SQL, migraciones y semillas
gateway/          Configuración de Nginx
infrastructure/   Dockerfiles
powerbi/          Tablero y guía de Power BI
scripts/          Entrenamiento y evaluación de BETO, reset del DW, figuras de la tesis
tests/            Pruebas por sprint, readiness y carga
docs/             Documentación técnica y apéndices
```
