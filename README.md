# Sistema de Inteligencia de Negocios y PLN — GiraGroup S.R.L.

Sistema de Inteligencia de Negocios basado en Procesamiento de Lenguaje Natural (PLN) y Cuadro de Mando Integral (CMI) para la mitigación de la fragmentación informacional. 

Desarrollado bajo una **Arquitectura Monolítica Modular Orientada a Datos** con **Python**, **FastAPI**, **React**, modelo **BETO**, **Docker** y **PostgreSQL**.

> **El entorno está completamente dockerizado.** No se necesita Python, Node ni PostgreSQL instalados localmente. Solo se necesita **Git** y **Docker Desktop**.

---

## 🏗️ Stack Tecnológico y Arquitectura (5 Capas)

| Capa | Componente | Tecnología |
|---|---|---|
| 1 y 2. Pipeline de Datos | Ingestión y PLN | Python, Pandas, Rapidfuzz, BETO (HuggingFace) |
| 3. Persistencia | Data Warehouse | PostgreSQL 16 (Esquema Estrella) |
| 4. Backend (API) | Exposición de Datos | FastAPI, SQLAlchemy, Pydantic |
| 5A. Frontend Web | Auditoría y DataOps | React + Vite + Tailwind |
| 5B. Visualización | Cuadro de Mando | Power BI Desktop |
| Infraestructura | Orquestación | Docker + Docker Compose |

---

## ⚙️ Requisitos previos

- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — con WSL2 habilitado en Windows.

Verificar instalaciones:

```bash
git --version
docker --version
docker-compose version
```

---

## 1. Clonar el repositorio

```bash
git clone [https://github.com/Adzacam/giragroup_bi_system.git](https://github.com/Adzacam/giragroup_bi_system.git)
cd giragroup_bi_system
git checkout main
  ```

## 2. Crear `.env` a partir del `.env.example`


**Windows PowerShell:**

```powershell
Copy-Item .env.example.env
```

**Linux / Git Bash:**
```bash
cp .env.example .env
```

Configurar variables en `.env`:

```bash
APP_ENV=local
APP_DEBUG=true

DB_HOST=pg_database
DB_PORT=5432
DB_DATABASE=giragroup_db
DB_USERNAME=giragroup_user
DB_PASSWORD=giragroup_secret_2026

# Configuración de BERT local (sin HuggingFace)
USE_LOCAL_BETO=true
LOCAL_BETO_PATH=./local_beto_model
```

**Importante**: Asegúrate de que la cadena de conexión a la base de datos en `.env` apunte al contenedor Docker interno, **NO** a tu host local. Debe verse así:

```bash
DATABASE_URL=postgresql://giragroup_user:giragroup_secret_2026@giragroup_db:5432/giragroup_db
```

---

## 3. Estructura del Proyecto

```text
giragroup_bi_system/
│
├── pipeline/                        # CAPAS 1 y 2: Ingestión y Procesamiento NLP
│   ├── ingestion/                   # sheets/, moodle/, excel/, forms/
│   ├── normalization/               # entities/, fuzzy_matching/, validation/
│   ├── semantic/                    # models/, inference/, embeddings/, confidence/
│   ├── analytics/                   # indicators/, scoring/, projections/, alerts/
│   ├── load/                        # Carga batch al Data Warehouse
│   ├── jobs/                        # scheduler.py, sync_moodle.py, process_semantic.py
│   ├── logs/                        # Logs de ejecución del pipeline
│   └── requirements.txt             # Dependencias de IA (Transformers, Torch, Pandas)
│
├── db/                              # CAPA 3: Persistencia Analítica
│   ├── warehouse/                   # facts/, dimensions/, materialized_views/
│   ├── migrations/                  # Control de versiones de BD (Alembic o SQL)
│   ├── seeds/                       # Datos iniciales estáticos (ej. dim_tiempo)
│   └── snapshots/                   # Respaldos de datasets versionados
│
├── backend/                         # CAPA 4: Exposición (API REST)
│   ├── core/                        # security/, config/, middleware/
│   ├── models/                      # Mapeo ORM (SQLAlchemy)
│   ├── schemas/                     # DTOs y validación (Pydantic)
│   ├── routers/                     # Endpoints expuestos (FastAPI)
│   ├── services/                    # Lógica de lectura y reglas de negocio
│   │   ├── academic_service.py
│   │   ├── finance_service.py
│   │   └── risk_service.py
│   ├── shared/                      # utils/, constants/, exceptions/
│   ├── tests/                       # Pruebas unitarias de la API
│   ├── main.py                      # Entrypoint Uvicorn
│   └── requirements.txt             # Dependencias ligeras (FastAPI, Pydantic, SQLAlchemy)
│
├── frontend/                        # CAPA 5A: Interfaz Web (DataOps y Auditoría)
│   ├── src/
│   │   ├── components/              # UI reutilizable
│   │   ├── modules/                 # dashboard/, risks/, indicators/, validation/, audit/
│   │   ├── pages/                   # Vistas principales por rol
│   │   ├── services/                # Cliente API (Axios/Fetch)
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── store/                   # Manejo de estado global (Zustand/Redux)
│   │   └── layouts/                 # Estructuras de página (Sidebar, Navbar)
│   ├── package.json
│   └── vite.config.js
│
├── powerbi/                         # CAPA 5B: Visualización Estratégica (CMI)
│   ├── dashboards/                  # giragroup_cmi.pbix
│   ├── templates/                   # Plantillas base corporativas
│   └── exports/                     # Reportes exportados (PDF/PPTX)
│
├── infrastructure/                  # DevOps y Despliegue
│   ├── docker/                      # api.Dockerfile, pipeline.Dockerfile, web.Dockerfile
│   ├── nginx/                       # Configuración de proxy inverso
│   ├── scripts/                     # Scripts de inicialización (init_db.sh)
│   └── monitoring/                  # Configuraciones de monitoreo de contenedores
│
├── docs/                            # Documentación del Proyecto
│   ├── architecture/                # Diagramas C4 o Mermaid
│   ├── api/                         # Colecciones de Postman o Swagger estático
│   ├── database/                    # Diccionario de datos
│   └── thesis/                      # Borradores o respaldos del documento Word
│
├── .github/                         # CI/CD Workflows
│   └── workflows/                   # Acciones de GitHub para testing automático
│
├── .env.example                     # Plantilla de variables de entorno
├── .gitignore                       # Reglas de exclusión unificadas
├── docker-compose.yml               # Orquestador local principal
└── README.md                        # Documentación técnica de entrada

```
---

## 4. Levantar el entorno Docker

```bash
# Levantar todo (Python 3.11 + PostgreSQL)
docker-compose up -d --build
```

**La primera vez:** tardará varios minutos mientras descarga las imágenes de Python, Node y PostgreSQL. y ejecuta `init.sql` para crear la base de datos.

**Verificar:**

```bash
docker ps
```

Deben aparecer:
- `giragroup_db`
- `giragroup_api`
- `giragroup_web`
- `giragroup_pipeline`

---

## 5. Acceder al sistema

| Servicio | URL |
|---|---|
| Documentación API (Swagger) | http://localhost:8000/docs |
| Interfaz Web (Capa 5A - React + Vite) | http://localhost:5173 |
| Health Check BD | http://localhost:8000/health |

---
###  **Redenciales de PostgreSQL (Para DBeaver o Power BI)**

Para conectar herramientas externas desde tu máquina local a la base de datos de Docker:

| Campo | Valor |
|---|---|
| Motor | PostgreSQL 16 |
| Host | localhost o 127.0.0.1 |
| Puerto | 5432 |
| Base de datos | giragroup_db |
| Usuario | giragroup_user |
| Contraseña | giragroup_secret_2026 |

### Base de datos inicial

El archivo db/schema.sql se ejecuta automáticamente al crear el contenedor de PostgreSQL por primera vez, levantando el esquema estrella, dimensiones financieras y transaccionales.

**Para reiniciar la base de datos desde cero (Reset Total)**:

```bash
docker-compose down -v
docker-compose up -d
```

## 6. Descargar el modelo BETO Local

Ejecutar **una sola vez** dentro del contenedor Python (no en host):

```bash
# Entrar al contenedor
docker-compose exec python_env bash

# Ejecutar el script de descarga
python data_pipelines/scripts/descargar_beto.py
```

Dentro de Python:

```python
from transformers import AutoTokenizer, AutoModel
import os

# Crear directorio local
os.makedirs("beto_local", exist_ok=True)

# Descargar BETO
tokenizer = AutoTokenizer.from_pretrained("dccuchile/bert-base-spanish-wwm-cased")
model = AutoModel.from_pretrained("dccuchile/bert-base-spanish-wwm-cased")

tokenizer.save_pretrained("beto_local")
model.save_pretrained("beto_local")

exit()
```

Ahora el modelo está en `data_pipelines/models/beto_local/`.

---

## 7. Ejecutar Pipeline de Datos

```bash
# Entrar al contenedor
docker-compose exec python_env bash

# Ejecutar ETL
python data_pipelines/scripts/etl_pipeline.py
```

Genera:
- `data_pipelines/data/dataset_final_limpio.csv`
- `data_pipelines/data/clustering_summary.csv`
- `data_pipelines/data/similarity_matrix.csv`

---

## 8. Cargar Datos al Data Warehouse (PostgreSQL)

```bash
docker-compose exec python_env bash

# Ejecutar script de carga
python data_pipelines/scripts/cargar_a_bd.py
```

Crea las tablas:
- `dim_proyecto`
- `dim_fecha`
- `dim_area`
- `fact_proyectos`

---

## 9. Probar la API REST (FastAPI)

```bash
# Listar endpoints
docker-compose exec python_env curl -X GET "http://localhost:8000/docs" -s | grep "http://localhost:8000"

# Listar proyectos
docker-compose exec python_env curl -X GET "http://localhost:8000/proyectos?page=1&limit=10" -s | python -m json.tool

# Buscar proyectos similares
docker-compose exec python_env curl -X GET "http://localhost:8000/proyectos/similares?titulo=Finanzas&top_k=5" -s | python -m json.tool

# Carga de proyectos del año 2024
docker-compose exec python_env curl -X GET "http://localhost:8000/proyectos?anio=2024" -s | python -m json.tool

# Carga de proyectos del año 2025
docker-compose exec python_env curl -X GET "http://localhost:8000/proyectos?anio=2025" -s | python -m json.tool

# Carga de proyectos con fecha límite en 2026
docker-compose exec python_env curl -X GET "http://localhost:8000/proyectos?fecha_limite_inicio=2026-01-01&fecha_limite_fin=2026-12-31" -s | python -m json.tool
```

---

## 10. Conectar Power BI al Data Warehouse

1. Abrir **Power BI Desktop**
2. Click **Obtener datos** → **Base de datos** → **PostgreSQL**
3. Ingresar:
   - Servidor: `localhost`
   - Puerto: `5432`
   - Base de datos: `giragroup_db`
   - Autenticación: Usuario `giragroup_user`, Contraseña `giragroup_secret_2026`
4. Seleccionar tablas:
   - `fact_proyectos`
   - `dim_proyecto`
   - `dim_fecha`
   - `dim_area`

---

## 11. Guía de Referencia y Flujos de Trabajo Diarios

A continuación, se detallan los comandos más utilizados para el desarrollo diario y control de versiones.

### 1. Gestión del Entorno Virtual Local (Windows)
Comandos utilizados para configurar el analizador del IDE y ejecutar scripts fuera de los contenedores.

* **Crear entorno:** `py -m venv .venv`
* **Activar entorno:** `.\.venv\Scripts\activate`
* **Instalar dependencias API:** `pip install -r backend/requirements.txt`
* **Instalar dependencias Pipeline:** `pip install -r pipeline/requirements.txt`
* **Ejecutar script local:** `python pipeline/ingestion/sheet_reader.py`
* **Desactivar entorno:** `deactivate`

### 2. Orquestación de Infraestructura (Docker)
Comandos para controlar el ciclo de vida de las 5 capas de la arquitectura.

* **Encender servicios:** `docker-compose up -d`
* **Reconstruir y encender (aplicar cambios en Dockerfile/schema):** `docker-compose up -d --build`
* **Apagar servicios (mantiene los datos):** `docker-compose down`
* **Reset total (borra la base de datos de PostgreSQL):** `docker-compose down -v`
* **Verificar contenedores activos:** `docker ps`
* **Ver logs en tiempo real (ej. de la API):** `docker-compose logs -f api`

### 3. Ejecución Interna (Docker Exec)
Comando para lanzar procesos directamente sobre el entorno Linux del contenedor, aprovechando las librerías nativas preinstaladas.

* **Ejecutar extracción de Excel:** `docker exec -it giragroup_pipeline python pipeline/ingestion/sheet_reader.py`

### 4. Control de Versiones (Git - Cierre de Sprint)
Flujo estándar utilizado para consolidar la rama de desarrollo con la rama principal.

* **Preparar archivos:** `git add .`
* **Crear punto de restauración:** `git commit -m "mensaje descriptivo"`
* **Subir a la rama activa:** `git push origin nombre-rama`
* **Cambiar de rama:** `git checkout main`
* **Fusionar cambios:** `git merge nombre-rama`

---

## 11.5. Mantenimiento del Proyecto

### Mover el proyecto de sitio
Si necesitas cambiar la carpeta del proyecto de ubicación o de computadora:
1. Apaga los contenedores: `docker-compose down`
2. **Elimina la carpeta `.venv`** (si la creaste).
3. Mueve la carpeta física.

### Quitar el proyecto de un dispositivo (Limpieza Total)
Si quieres eliminar por completo el proyecto de una computadora:
```bash
# 1. Detener y borrar volúmenes (datos)
docker-compose down -v

# 2. Eliminar imágenes de Docker asociadas
docker rmi giragroup_bi_system-api
docker rmi postgres:16-alpine

# 3. Eliminar la carpeta física del proyecto manualmente
```

---

## 12. Solución de Errores Comunes

**Error de conexión a BD:**
Verificar `.env`:
```env
DB_HOST=pg_database
DB_PORT=5432
```
No usar `127.0.0.1` ni `5433` — esos son para conexiones desde fuera de Docker.

**Modelo BETO no encontrado:**
Re-ejecutar paso 6.

**FastAPI no responde:**
```bash
docker-compose logs python_env
```

**Power BI no conecta:**
Verificar puertos en `docker-compose.yml`:
```yaml
ports:
  - "5433:5432"   # PostgreSQL
  - "5051:80"     # pgAdmin
```
