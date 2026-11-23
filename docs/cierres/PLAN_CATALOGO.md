# PLAN CATALOGO (CAT) — Módulos e instituciones del catálogo de referencia — 2026-11-22

**Objetivo (1 línea):** que el catálogo de módulos e instituciones solo contenga entidades institucionales válidas, sin números, fechas, profesiones ni valores centinela, y que el pipeline no vuelva a crearlas.

**Entrada:**
- `CIERRE_DATAOPS_FLUJO.md` (`a7be77c`), con DF cerrado salvo DF-L10.
- Rama `beto-integracion` `f2c6bcf`.
- DW viva **vaciada a propósito** por Lean el 2026-11-22: hechos, lotes, tareas y staging en 0; quedan las dimensiones (16.874 estudiantes y 4.565 módulos) y `carga_fila_origen` (984.182 claves).

**Método:**
- `SELECT` sobre `giragroup_db`.
- Lectura de `dw_loader.py`, `catalogo_dataops.py` y `maestros.py`.
- Captura de Lean de `/v2/dataops/datos-maestros`.

---

## PARTE 1 — Hallazgos

### Módulos (`dim_modulo`, 4.565)
| Clase | N | Ejemplos | Válido |
|---|---|---|---|
| Con código POS | 3.930 | «2da. JORNADA DE ODONTOLOGÍA PARA BEBÉ - NAL» (POS-5072) | Sí (1.334 sin `programa`: muestran «Sin dato») |
| `MOD-GEN`: título o profesión | 216 | «ABOGADO», «LIC. ECONOMIA», «ING. SISTEMAS», «INGENIERO CIVIL» | **No** |
| `MOD-GEN`: carrera, cargo u ocupación | ~406 | «ESTUDIANTE», «MARKETING», «MÚSICO», «DIRECTORA EJECUTIVA NACIONAL…» | **No** (salvo 3 que parecen programa) |
| `MOD-GEN`: centinela | 7 | «SI», «N/A», «-» | **No** |
| `MOD-GEN`: número | 2 | «0», «1» | **No** |
| `MOD-GEN`: fecha | 1 | «2025-06-24 17:59:00» | **No** |

**Causa raíz:**
1. **Se crea un módulo con cualquier texto.** `DwLoader.resolver_o_crear_modulo` (`backend/services/dw_loader.py:915-937`) busca un nombre igual o con un parecido ≥ 80. Si no lo encuentra, **inserta un `DimModulo` con `pos_code = "MOD-GEN"`** sin comprobar que el texto tenga forma de módulo. Hacen lo mismo `dw_loader.py:1906` y `:2237` («Módulo General») y `routers/dataops/lectura.py:804`.
2. **Columna equivocada.** Al cargar inscripciones, la columna leída como módulo era carrera, nivel académico u ocupación del inscrito (hallazgo corregido en FU-L3: «inscripción asignada a un módulo leído de otra columna»). Cada valor distinto se convirtió en un módulo.
3. **Nadie limpia.** FU-L3 corrigió el mapeo de los hechos, pero no borró los módulos ya creados. Borrar o recargar un documento tampoco elimina las dimensiones que generó.

### Instituciones (`cat_institucion`, 4)
| id | Nombre | Sigla | Observación |
|---|---|---|---|
| 1 | GiraGroup | GG | **Duplica** a la 361 (misma sigla) |
| 2 | Escuela de Negocios y Postgrado | ENP | Semilla de demo; 0 módulos la usan |
| 3 | Facultad de Ciencias de la Salud | FCS | Semilla de demo; 0 módulos la usan |
| 361 | GiraGroup Posgrado | GG | La que usan los 4.565 módulos y los 16.874 estudiantes |

Las instituciones de convenio (24 en la fuente de techos) no están en este catálogo: `cat_institucion_convenio` tiene 0 filas en la DW.

### Pantalla «Catálogo de referencia»
- 5 filas por página: 4.565 módulos son 913 páginas.
- «Eliminar» aparece activo en todas las filas, sin decir si el módulo está en uso.
- No hay filtro para ver solo los módulos genéricos o los que no tienen programa.

---

## PARTE 2 — Loops

| Loop | Tarea | Agente (modelo) | Depende de | Paralelo con | Criterio de aceptación medible | Salida en docs/mediciones/ |
|---|---|---|---|---|---|---|
| CAT-L0 | Inventario reproducible del catálogo por clase (POS, profesión, carrera, centinela, número, fecha) | `dev-baja` (haiku) | — | — | `scripts/auditoria_dw/cat_inventario.sql`, sin PII; los conteos coinciden con la Parte 1 | `cat_l0_inventario.csv` |
| CAT-L1 | **Prevenir:** validar antes de crear un módulo | `dev-media` (sonnet) | L0 | L3 | (a) `es_nombre_modulo_valido()` en `services/` rechaza números, fechas, centinelas («SI», «NO», «N/A», «-»), textos de 3 caracteres o menos y títulos o profesiones; la lista de profesiones y títulos vive en un **catálogo editable** (`cat_etiqueta_clasificacion` u otra tabla `cat_*`), no en el código ([[fuentes-agnosticas]]); (b) `resolver_o_crear_modulo` **ya no crea `MOD-GEN`**: si el nombre no es válido o no hay coincidencia, devuelve `None` y registra `VALOR_FUERA_DE_CATALOGO` (campo módulo), que va a la bandeja con las acciones de DF («Vincular a módulo existente», «Crear módulo» por ADMIN o AUDITOR); (c) se crea un módulo nuevo solo con un código POS válido o por acción humana; (d) test con fixture sintética de inscritos con columnas de carrera y ocupación → **0 módulos nuevos** y n avisos en la bandeja | `cat_l1_pruebas.txt` |
| CAT-L2 | **Limpiar:** borrar los módulos inválidos (según DC1) | `dev-media` (sonnet) | L1 | — | (a) `pg_dump` previo en `backups/`; (b) se borran los `MOD-GEN` de clase inválida que **ningún FK** referencia (las 9 tablas de hechos y puente, más `stg_entidad_no_resuelta.id_dimension_resuelta` y `app.*`); (c) los 3 que parecen programa quedan para Lean (DC3); (d) conteo antes/después y lista de ids borrados | `cat_l2_borrados.csv` |
| CAT-L3 | **Instituciones:** fusionar GiraGroup y GiraGroup Posgrado | `dev-media` (sonnet) | L0 (DC2 resuelta) | L1 | (a) una sola institución canónica (DC2) con el alias de la otra registrado como sinónimo; (b) los FK de `dim_modulo` y `dim_estudiante` apuntan a la canónica; (c) ENP y FCS según DC2; (d) test: cargar una fuente con «GiraGroup» la resuelve a la canónica | `cat_l3_instituciones.csv` |
| CAT-L4 | `programa` vacío en 1.334 módulos con POS | `dev-media` (sonnet) | L0 | L1, L3 | Se completa desde `cat_programa` (`catalog_db`) por `pos_code`. Si no hay coincidencia, queda «Sin dato» con motivo. Conteo antes/después | `cat_l4_programa.csv` |
| CAT-L5 | Pantalla «Catálogo de referencia» | `dev-media` (sonnet) + `/frontend-design` | L1, L2 | — | (a) 20 filas por página; (b) filtros «Solo genéricos», «Sin programa» y «En uso / sin uso»; (c) columna «En uso» (n hechos que lo referencian); «Eliminar» solo se habilita sin referencias y pide confirmación; (d) acción ADMIN «Limpiar módulos sin uso (n)» con vista previa; (e) tokens y animaciones del sistema, responsivo; (f) verificación con Playwright | `cat_l5_capturas/` |
| CAT-L6 | Verificación después de la recarga | `dev-baja` (haiku) | L1–L5 + recarga de Lean | — | Tras la recarga: (a) 0 `MOD-GEN` nuevos; (b) los avisos `VALOR_FUERA_DE_CATALOGO` del campo módulo aparecen en la bandeja; (c) 0 módulos sin uso de clase inválida; (d) invariantes 51 / 10 / 23; (e) la pestaña «Instituciones» muestra «Propia» (1) y «Convenio» (n de CAT-L7) | `cat_l6_post_recarga.csv`, `CIERRE_CAT.md` |

| CAT-L7 | **Instituciones de convenio** (DC4) | `dev-media` (sonnet) | L3 | L4 | (a) Comprobar dónde vive `cat_institucion_convenio` (DW y `catalog_db`) y usar una sola tabla de verdad. (b) El cargador llena el catálogo desde el campo canónico `institucion` de **cualquier** fuente de tipo TECHOS ([[fuentes-agnosticas]]), sin el nombre del libro. (c) Variantes de escritura («ECOGUZ» en dos formas) se fusionan con similitud ≥ 90 % (regla de homónimos) + sinónimos del catálogo; con duda, `VALOR_FUERA_DE_CATALOGO` a la bandeja. (d) `fact_techo_convenio` apunta a la institución por FK; el 40,6 % sin `id_institucion` se resuelve o va a revisión con su motivo. (e) La pestaña muestra dos grupos: **«Propia»** (GiraGroup Posgrado) y **«Convenio»** (nombre, sigla si existe, n programas, n inscritos y años con techo), con búsqueda y la misma paginación de 20. (f) Criterio tras la recarga: instituciones de convenio en el catálogo = instituciones distintas de la fuente después de fusionar variantes (la fuente trae 24 nombres; la cifra final queda en la evidencia), y 0 techos sin institución, salvo los que estén en la bandeja | `cat_l7_instituciones_convenio.csv`, `cat_l7_capturas/` |

Orden (DC1): **L0 → L1 → L2 (ahora, con la DW vacía) → (L3 ‖ L4) → L7 → L5 → recarga (Lean) → L6.**

**Por qué CAT-L1 va antes de la recarga:** si se recarga con la regla actual, los mismos textos vuelven a crear módulos `MOD-GEN`.

## Comandos
```powershell
docker compose exec -T db pg_dump -U giragroup_user -Fc giragroup_db -f /tmp/cat_pre_l2.dump
```
```powershell
.venv\Scripts\python -m pytest tests -q -k "modulo or catalogo"
```
```powershell
cd frontend; npx vitest run; npm run build
```

## Riesgos y control
- **Borrar con la DW vacía:** con los hechos en 0, *todos* los módulos aparecen sin uso, incluidos los 3.930 buenos. CAT-L2 **nunca** borra por «sin uso» solamente: exige **clase inválida + sin referencias**. El borrado general de módulos sin uso solo se ofrece en CAT-L5 y después de la recarga.
- **Invariantes:** el catálogo sigue con solo entidades institucionales; la cascada y los umbrales no cambian; borrar filas no cambia el conteo de 51 tablas.
- **Credenciales:** el `pg_dump` usa las variables de entorno del contenedor, sin contraseñas en archivos.

## DECISIONES PENDIENTES PARA LEAN
- **DC1 — RESUELTA (Lean, 2026-11-22): borrar ahora, antes de la recarga.**
  - **Orden:** CAT-L0 → CAT-L1 → **CAT-L2 de inmediato** (con la DW vacía) → recarga. CAT-L1 sigue yendo antes, para que la recarga no los vuelva a crear.
  - **Alcance:** los `MOD-GEN` de clase inválida (≈ 632: profesión o título, carrera u ocupación, centinela, número, fecha) **y** con 0 referencias en las 9 tablas de FK, en `stg_entidad_no_resuelta.id_dimension_resuelta` y en `app.*`. Los 3 que parecen programa no se tocan hasta DC3.
  - **Doble filtro obligatorio:** clase inválida **y** sin referencias. Nunca se borra solo por estar sin uso: con la DW vacía, los 3.930 módulos con POS también están sin uso y se conservan.
  - **Respaldo:** `pg_dump` previo y `cat_l2_borrados.csv` con id, clase y nombre (los nombres de módulo no son PII).
  - **Criterio:** `MOD-GEN` restantes = **0** (DC3 resuelve los 5 que parecían programa); módulos con POS = 3.930, sin cambios, o + 0 si el 1224 se fusiona en uno existente.
- **DC2 — RESUELTA (Lean, 2026-11-22): canónica = «GiraGroup Posgrado» (id 361); «GiraGroup» queda como sinónimo; se borran ENP y FCS.**
  - **CAT-L3:**
    - re-apuntar todo FK hacia `cat_institucion.id_institucion` = 1 → 361 (hoy 0 filas lo usan, pero se comprueba en `dim_modulo`, `dim_estudiante` y cualquier otra tabla que lo referencie);
    - registrar «GiraGroup» como sinónimo de la 361 en el catálogo de mapeo, para que una fuente que diga «GiraGroup» resuelva a la 361;
    - borrar las filas 1 (GiraGroup), 2 (ENP) y 3 (FCS), solo si tienen 0 referencias; si alguna tiene, se detiene y lo informa.
  - **Semillas:** quitar ENP, FCS y la fila GiraGroup de las semillas (`db/seeds/` y migraciones de seed) para que no vuelvan en una instalación limpia, conservando una sola fila canónica.
  - **Criterios:**
    - `cat_institucion` = 1 fila (361);
    - 0 FK huérfanos;
    - test: una fuente con «GiraGroup» → 361.
- **DC3 — RESUELTA (Lean, 2026-11-22): vincular si existe el POS; si no, borrar.** Son **5**, no 3:

  | id | Nombre | Acción |
  |---|---|---|
  | 1224 | PROGRAMA EXPERTO EN MEDICINA ESTÉTICA v. XVIII - NAL | Buscar el programa en `cat_programa` (`catalog_db`) por nombre normalizado y versión (≥ 90 por la regla de homónimos; con varios candidatos, se detiene y lo informa). Con coincidencia única: **fusionar** en el módulo con POS de ese programa (re-apuntar FK si hubiera y borrar el `MOD-GEN`). Sin coincidencia: **borrar** |
  | 4318 | DIPLOMADO(ESTOESUNAPRUEBA) | Borrar (registro de prueba) |
  | 1380 | INGENIERÍA DE MEDIO AMBIENTE Y RECURSOS NATURALES | Borrar (carrera del inscrito) |
  | 1439 | LIC EN ADMINISTRACIÓN DE EMPRESAS TURÍSTICAS… (EN CURSO) | Borrar (carrera) |
  | 1502 | GERENCIA DE RECURSOS HUMANOS | Borrar (carrera o cargo) |

  - Se hace dentro de **CAT-L2**, con el mismo doble filtro (0 referencias) y el mismo respaldo.
  - **Criterio:** `MOD-GEN` restantes = **0**.
  - La regla de CAT-L1 hace que «DIPLOMADO…», «PROGRAMA…» y «CURSO…» sin POS vayan a la bandeja como `VALOR_FUERA_DE_CATALOGO`, con la acción «Vincular a módulo existente».
- **DC4 — RESUELTA (Lean, 2026-11-22): la pestaña «Instituciones» también muestra las instituciones de convenio.** Se hace en el loop nuevo **CAT-L7**. Son entidades institucionales, así que se respeta el invariante del catálogo.

Al cerrar cada loop: pytest + vitest · rebuild de lo tocado · commit `cat(L<n>): …` · `CIERRE_CAT_L<n>.md`.

## PROMPT PARA CHAT 2
```
/gira-desarrollar
Ejecuta SOLO el loop CAT-L<n> de docs/cierres/PLAN_CATALOGO.md.
- Agentes con model "sonnet" (o "haiku"), nunca Opus.
- La DW está vacía a propósito: no borres módulos por «sin uso» solamente; exige clase inválida + 0 referencias.
- Listas de profesiones o centinelas en un catálogo editable, no en el código.
- Si el loop depende de una DECISIÓN (DC*) sin respuesta de Lean, detente.
- Cierra con CIERRE_CAT_L<n>.md y commit cat(L<n>).
```
