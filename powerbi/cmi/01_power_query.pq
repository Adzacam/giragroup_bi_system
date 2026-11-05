// =============================================================================
// Power Query (M) del CMI GiraGroup — solo esquema bi (migración 006_capa_semantica_cmi.sql)
//
// Inicio > Transformar datos > Administrar parámetros > Nuevo (tipo Texto):
//     pHost = "127.0.0.1:5434"     (giragroup_db, docker-compose.yml)
//     pBase = "giragroup_db"
// Credenciales: Base de datos, usuario powerbi_reader (contraseña asignada con
//     ALTER ROLE powerbi_reader PASSWORD '...'). Solo lectura sobre bi; sin PII.
//
// Cada bloque es UNA consulta en blanco (Inicio > Nuevo origen > Consulta en blanco >
// Editor avanzado). Nombre de la consulta = nombre del comentario.
// No se conecta a la base de catálogo: el CMI solo muestra perspectivas e indicadores.
// =============================================================================

// --- Consulta: Fuente (clic derecho > desmarcar "Habilitar carga") ---
let
    Fuente = PostgreSQL.Database(pHost, pBase, [CreateNavigationProperties = false])
in
    Fuente

// --- Consulta: Gestiones ---
let
    Src   = Fuente{[Schema = "bi", Item = "vw_cmi_gestiones"]}[Data],
    Tipos = Table.TransformColumnTypes(Src, {{"gestion", Int64.Type}, {"indicadores_con_dato", Int64.Type}})
in
    Table.Sort(Tipos, {{"gestion", Order.Ascending}})

// --- Consulta: Perspectivas (configuración: nombre, objetivo, peso, orden) ---
let
    Src   = Fuente{[Schema = "bi", Item = "ref_perspectiva"]}[Data],
    Sel   = Table.SelectColumns(Src, {"codigo", "nombre", "objetivo", "pregunta", "peso", "orden", "activa"}),
    Tipos = Table.TransformColumnTypes(Sel, {{"peso", type number}, {"orden", Int64.Type}, {"activa", type logical}})
in
    Table.SelectRows(Tipos, each [activa])

// --- Consulta: Scorecard (una fila por gestión e indicador; valores, metas y semáforo) ---
let
    Src   = Fuente{[Schema = "bi", Item = "vw_cmi_scorecard"]}[Data],
    Tipos = Table.TransformColumnTypes(Src, {
        {"gestion", Int64.Type}, {"valor", type number}, {"valor_anterior", type number},
        {"delta", type number}, {"meta", type number}, {"umbral_verde", type number},
        {"umbral_ambar", type number}, {"peso", type number}, {"orden", Int64.Type},
        {"puntaje", type number}})
in
    Tipos

// --- Consulta: IndicePerspectiva ---
let
    Src   = Fuente{[Schema = "bi", Item = "vw_cmi_perspectiva"]}[Data],
    Tipos = Table.TransformColumnTypes(Src, {
        {"gestion", Int64.Type}, {"peso", type number}, {"orden", Int64.Type}, {"indicadores", Int64.Type},
        {"verdes", Int64.Type}, {"ambar", Int64.Type}, {"rojos", Int64.Type}, {"sin_evaluar", Int64.Type},
        {"indice", type number}})
in
    Tipos

// --- Consulta: MetasMensual (detalle de la perspectiva Financiera) ---
let
    Src   = Fuente{[Schema = "bi", Item = "vw_metas_mensual"]}[Data],
    Tipos = Table.TransformColumnTypes(Src, {
        {"gestion", Int64.Type}, {"mes", Int64.Type}, {"fecha_mes", type date}, {"ejecutado", type number},
        {"meta", type number}, {"avance_pct", type number}, {"ejecutado_anio_ant", type number}})
in
    Tipos

// --- Consulta: CarteraEstado (detalle Financiera) ---
let
    Src = Fuente{[Schema = "bi", Item = "vw_cartera_estado"]}[Data]
in
    Table.TransformColumnTypes(Src, {{"gestion", Int64.Type}, {"deuda_bs", type number}, {"pagado_bs", type number}})

// --- Consulta: RiesgoEstudiante (detalle Aprendizaje; sin nombre ni CI) ---
let
    Src = Fuente{[Schema = "bi", Item = "vw_riesgo_estudiante"]}[Data]
in
    Table.TransformColumnTypes(Src, {{"gestion", Int64.Type}, {"prom_notas", type number}, {"k_reglas", Int64.Type}})

// --- Consulta: DataOpsDocumento (detalle Procesos internos) ---
let
    Src = Fuente{[Schema = "bi", Item = "vw_dataops_documento"]}[Data]
in
    Table.TransformColumnTypes(Src, {{"fecha", type date}, {"confianza_media_pct", type number}})
