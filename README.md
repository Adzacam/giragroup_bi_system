# Proyectos Académicos — Universidad Privada del Valle

Sistema web académico para la gestión y seguimiento de proyectos estudiantiles, desarrollado con **Laravel**, **React**, **Inertia.js**, **Vite**, **Docker** y **PostgreSQL**.

> **El entorno está completamente dockerizado.** No se necesita PHP, Composer ni Node instalados localmente. Solo se necesita **Git** y **Docker Desktop**.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Laravel 13 (PHP 8.4) |
| Frontend | React + Inertia.js + Vite |
| Base de datos | PostgreSQL 16 |
| Administración BD | pgAdmin 4 |
| Estilos | Tailwind CSS |
| Entorno | Docker + Docker Compose |

---

## Requisitos previos

Cada integrante solo necesita:

- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — con WSL2 habilitado en Windows

Verificar instalaciones:

```bash
git --version
docker --version
docker compose version
```

---

## 1. Clonar el proyecto

```bash
git clone https://github.com/feli2710/giragroup-bi-system.git
cd giragroup-bi-system
git checkout main
git pull origin main
```

---

## 2. Crear el archivo `.env`

**Linux / macOS / Git Bash:**
```bash
cp .env.example .env
```

**Windows CMD:**
```cmd
copy .env.example .env
```

Abrir `.env` y configurar las siguientes variables:

```env
APP_NAME="GiraGroup BI System"
APP_ENV=local
APP_DEBUG=true
APP_URL=http://localhost:8000

APP_LOCALE=es
APP_FALLBACK_LOCALE=es
APP_FAKER_LOCALE=es_ES

DB_CONNECTION=pgsql
DB_HOST=giragroup_db
DB_PORT=5432
DB_DATABASE=giragroup_db
DB_USERNAME=giragroup_user
DB_PASSWORD=giragroup_secret_2026
```

> **Importante:** `DB_HOST` debe ser `giragroup_db` (nombre del contenedor), no `127.0.0.1`. El puerto es `5432` interno de Docker, no `5433`.

---

## 3. Levantar todo el entorno

```bash
docker compose up -d
```

La primera vez tarda varios minutos porque construye las imágenes de PHP y Node. Las siguientes veces es inmediato.

Verificar que los 4 contenedores estén corriendo:

```bash
docker ps
```

Deben aparecer:
- `giragroup_postgres`
- `giragroup_pgadmin`
- `giragroup_laravel`
- `giragroup_vite`

---

## 4. Acceder al sistema

| Servicio | URL |
|---|---|
| Aplicación Laravel | http://localhost:8000 |
| Vite / React HMR | http://localhost:5173 |
| pgAdmin | http://localhost:5051 |

---

## 5. Credenciales de PostgreSQL

| Campo | Valor |
|---|---|
| Motor | PostgreSQL 16 |
| Host (desde Laravel/Docker) | `giragroup_db` |
| Host (desde tu máquina) | `127.0.0.1` |
| Puerto (desde tu máquina) | `5433` |
| Base de datos | `giragroup_db` |
| Usuario | `giragroup_user` |
| Contraseña | `giragroup_secret_2026` |

---

## 6. Acceder a pgAdmin

Abrir: [http://localhost:5051](http://localhost:5051)

| Campo | Valor |
|---|---|
| Correo | `admin@giragroup.dev` |
| Contraseña | `giragroup_secret_2026` |

**Registrar el servidor:**

1. Click derecho en **Servers** → **Register** → **Server**
2. Pestaña **General** → Name: `GiraGroup PostgreSQL`
3. Pestaña **Connection:**
   - Host: `giragroup_db`
   - Port: `5432`
   - Database: `giragroup_db`
   - Username: `giragroup_user`
   - Password: `giragroup_secret_2026`
   - Activar **Save password**
4. Click **Save**

---

## 7. Base de datos inicial

El archivo `init.sql` se ejecuta automáticamente la primera vez que Docker crea el contenedor de PostgreSQL. No se necesita correr migraciones manualmente.

Para reiniciar la base de datos desde cero:

```bash
docker compose down -v
docker compose up -d
```

> ⚠️ Este comando borra todos los datos locales de PostgreSQL.

---

## 8. Comandos del día a día

Cada integrante ejecuta al iniciar el día:

```bash
git checkout main
git pull origin main
docker compose up -d
```

Para apagar todo:

```bash
docker compose down
```

---

## 9. Ejecutar comandos de Laravel (Artisan)

Como Laravel corre dentro de Docker, todos los comandos de Artisan se ejecutan así:

```bash
docker exec -it giragroup_laravel php artisan <comando>
```

Ejemplos:

```bash
# Limpiar caché
docker exec -it giragroup_laravel php artisan optimize:clear

# Ver rutas
docker exec -it giragroup_laravel php artisan route:list

# Estado de migraciones
docker exec -it giragroup_laravel php artisan migrate:status

# Limpiar configuración
docker exec -it giragroup_laravel php artisan config:clear
```

---

## 10. Usar Tinker

```bash
docker exec -it giragroup_laravel php artisan tinker
```

Dentro de Tinker, crear un usuario coordinador:

```php
use App\Models\User;

User::create([
    'name' => 'Nombre Apellido',
    'email' => 'correo@gmail.com',
    'password' => bcrypt('Contrasena123!'),
    'rol' => 'coordinador',
    'activo' => true,
]);
```

Asignar rol coordinador a un usuario existente:

```php
use App\Models\User;

User::where('email', 'correo@gmail.com')->update([
    'rol' => 'coordinador',
    'activo' => true,
]);
```

Salir de Tinker:

```php
exit
```

---

## 11. Ejecutar npm (frontend)

El contenedor `giragroup_vite` ya corre `npm run dev` automáticamente al levantar Docker. No es necesario ejecutarlo manualmente.

Si necesitas correr un comando npm puntual:

```bash
docker exec -it giragroup_vite npm <comando>
```

Ejemplo:

```bash
docker exec -it giragroup_vite npm install
```

---

## 12. Ejecutar Composer

El contenedor `giragroup_laravel` ya corre `composer install` automáticamente al arrancar. Si necesitas un comando específico:

```bash
docker exec -it giragroup_laravel composer <comando>
```

Ejemplo:

```bash
docker exec -it giragroup_laravel composer dump-autoload
```

---

## 13. Usuarios y roles
(cambios hay aca con mas areas administrativas y financieross, estrategica,gerencial)
Los roles se almacenan en `users.rol`:

| Rol | Descripción |
|---|---|
| `estudiante` | Usuario por defecto al registrarse |
| `tutor` | Supervisa proyectos asignados |
| `revisor` | Evalúa proyectos en fase final |
| `coordinador` | Administra el sistema completo |

El estado del usuario se almacena en `users.activo`. Un usuario con `activo = false` no puede iniciar sesión.

---

## 14. Módulo de gestión de usuarios

Solo accesible con rol `coordinador`.

| Ruta | Descripción |
|---|---|
| `/usuarios` | Directorio de usuarios |
| `/usuarios/crear` | Crear usuario |
| `/usuarios/{id}/editar` | Editar usuario |
| `/usuarios/papelera` | Usuarios inactivos |

**Restricciones:**
- No se puede desactivar al último coordinador activo.
- No se puede quitar el rol al último coordinador activo.
- Un coordinador no puede modificar su propio rol.

---

## 15. Autenticación y seguridad

- Inicio de sesión y registro
- Recuperación de contraseña
- Bloqueo temporal tras 5 intentos fallidos consecutivos
- Validación de cuenta activa/inactiva
- Control de acceso basado en roles (RBAC) mediante middleware

---

## 16. Flujo de trabajo con Git

No trabajar directamente en `main`.

**Crear una rama nueva:**
```bash
git checkout main
git pull origin main
git checkout -b nombre-de-la-rama
```

**Guardar y subir cambios:**
```bash
git status
git add .
git commit -m "Descripción del cambio"
git push origin nombre-de-la-rama
```

Luego crear un **Pull Request** hacia `main`.

**Fusionar con main:**
```bash
git checkout main
git pull origin main
git merge nombre-de-la-rama
git push origin main
```

**Actualizar una rama con cambios de main:**
```bash
git checkout nombre-de-la-rama
git merge main
```

---

## 17. Comandos útiles de Docker

```bash
# Levantar todos los contenedores
docker compose up -d

# Ver contenedores activos
docker ps

# Detener contenedores (sin borrar datos)
docker compose down

# Detener y borrar volúmenes (reset total de BD)
docker compose down -v

# Reconstruir imágenes después de cambiar un Dockerfile
docker compose up -d --build

# Ver logs en tiempo real de todos los servicios
docker compose logs -f

# Ver logs de un servicio específico
docker logs giragroup_laravel
docker logs giragroup_vite
docker logs giragroup_postgres

# Entrar al contenedor de Laravel
docker exec -it giragroup_laravel sh

# Entrar al contenedor de Vite
docker exec -it giragroup_vite sh
```

---

## 18. Solución de errores comunes

**Error de conexión a PostgreSQL desde Laravel**

Verificar que el `.env` tenga:
```env
DB_HOST=sudosquad_db
DB_PORT=5432
```
No usar `127.0.0.1` ni `5433` — esos son para conexiones desde fuera de Docker.

---

**pgAdmin no abre en localhost:5051**

```bash
docker ps | grep giragroup_pgadmin
docker logs giragroup_pgadmin
```

Si el volumen está corrupto:
```bash
docker compose down
docker volume rm giragroup_pgadmin_data
docker compose up -d
```

---

**Laravel no responde en localhost:8000**

```bash
docker logs giragroup_laravel
```

Si el servidor no arrancó:
```bash
docker compose down
docker compose up -d
```

---

**Vite no compila / wayfinder falla**

```bash
docker logs giragroup_vite
```

Si hay error de PHP no encontrado, reconstruir la imagen de Vite:
```bash
docker compose up -d --build giragroup_vite
```

---

**Caché de Laravel desactualizada**

```bash
docker exec -it sudosquad_laravel php artisan optimize:clear
```

---

**Puerto 5433 o 5051 ya ocupado**

Cambiar el puerto externo en `docker-compose.yml`:
```yaml
ports:
  - "5434:5432"   # para postgres
  - "5052:80"     # para pgadmin
```

Y actualizar `.env` si cambiaste el puerto de postgres (solo aplica para conexiones externas, no desde Laravel).

---

## 19. Archivos importantes

| Archivo / Carpeta | Descripción |
|---|---|
| `docker-compose.yml` | Configuración de los 4 contenedores |
| `docker/laravel/Dockerfile` | Imagen PHP 8.4 + Composer para Laravel |
| `docker/vite/Dockerfile` | Imagen Node 20 + PHP84 para Vite/wayfinder |
| `init.sql` | Script inicial de base de datos |
| `.env` | Variables locales del entorno |
| `routes/web.php` | Rutas principales |
| `app/Models/User.php` | Modelo de usuario |
| `app/Http/Controllers/` | Controladores Laravel |
| `app/Providers/FortifyServiceProvider.php` | Autenticación y seguridad |
| `resources/js/pages/` | Vistas React + Inertia |
| `resources/js/components/` | Componentes React reutilizables |

---

## 20. Reglas del equipo

- No subir `.env` ni `node_modules`.
- No modificar `main` directamente — siempre trabajar en una rama.
- Crear una rama por módulo o funcionalidad.
- Hacer `git pull origin main` antes de empezar cualquier sesión.
- Avisar al equipo si se modifica `init.sql`, `docker-compose.yml`, `Dockerfile`, rutas o autenticación.
- Usar mensajes de commit claros y descriptivos en inglés.

---

## Equipo — GiraGroup

| Nombre | Rol |
|---|---|
| Adriano Leandro Daza Campero | Coach / Líder técnico |
| Adriano Leandro Daza Campero | Frontend |
| Adriano Leandro Daza Campero | Backend |
| Adriano Leandro Daza Campero | QA / Calidad |

**Universidad Privada del Valle — Sede La Paz · 2026**