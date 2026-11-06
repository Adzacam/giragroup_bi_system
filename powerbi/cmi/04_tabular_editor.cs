// Tabular Editor 2 (gratuito). Power BI Desktop > Herramientas externas > Tabular Editor > pegar en "C# Script" > F5 > Ctrl+S
foreach(var rr in Model.Relationships.Where(x => !x.FromTable.Name.StartsWith("LocalDateTable") && !x.ToTable.Name.StartsWith("LocalDateTable") && !x.FromTable.Name.StartsWith("DateTableTemplate") && !x.ToTable.Name.StartsWith("DateTableTemplate")).ToList()) rr.Delete();  // quita relaciones automaticas, respeta las tablas de fecha ocultas
var nombres = new Dictionary<string,string>{
  {"vw_cmi_gestiones","Gestiones"},{"ref_perspectiva","Perspectivas"},{"vw_cmi_scorecard","Scorecard"},
  {"vw_cmi_perspectiva","IndicePerspectiva"},{"vw_metas_mensual","MetasMensual"},{"vw_cartera_estado","CarteraEstado"},
  {"vw_riesgo_estudiante","RiesgoEstudiante"},{"vw_dataops_documento","DataOpsDocumento"}};
foreach(var kv in nombres){
  var t = Model.Tables.FirstOrDefault(x => x.Name == kv.Value || x.Name.EndsWith(kv.Key));
  if(t != null) t.Name = kv.Value;
}
Action<string,string,string,string> rel = (desde, cd, hacia, ch) => {
  if(Model.Relationships.Any(r => r.FromTable.Name==hacia && r.FromColumn.Name==ch && r.ToTable.Name==desde)) return;
  var r2 = Model.AddRelationship();
  r2.FromColumn = Model.Tables[hacia].Columns[ch];
  r2.ToColumn = Model.Tables[desde].Columns[cd];
  r2.FromCardinality = RelationshipEndCardinality.Many;
  r2.ToCardinality = RelationshipEndCardinality.One;
};
foreach(var h in new[]{"Scorecard","IndicePerspectiva","MetasMensual","CarteraEstado","RiesgoEstudiante"}) rel("Gestiones","gestion",h,"gestion");
foreach(var h in new[]{"Scorecard","IndicePerspectiva"}) rel("Perspectivas","codigo",h,"perspectiva");
Model.Tables["Perspectivas"].Columns["nombre"].SortByColumn = Model.Tables["Perspectivas"].Columns["orden"];
Model.Tables["Scorecard"].Columns["nombre"].SortByColumn = Model.Tables["Scorecard"].Columns["orden"];
var medidas = new[]{
    new[]{@"IndicePerspectiva",@"Indice",@"// Promedio ponderado por peso de las perspectivas con índice; en el contexto de una
    // perspectiva devuelve su propio índice. Igual que el índice global de la API.
    VAR _t = FILTER ( IndicePerspectiva, NOT ISBLANK ( IndicePerspectiva[indice] ) )
    RETURN ROUND ( DIVIDE ( SUMX ( _t, IndicePerspectiva[indice] * IndicePerspectiva[peso] ),
                            SUMX ( _t, IndicePerspectiva[peso] ) ), 1 )"},
    new[]{@"IndicePerspectiva",@"Indice Banda",@"VAR _i = [Indice]
    RETURN SWITCH ( TRUE (), ISBLANK ( _i ), ""Sin evaluar"", _i >= 80, ""En meta"", _i >= 50, ""En alerta"", ""Crítico"" )"},
    new[]{@"IndicePerspectiva",@"Indice Color",@"SWITCH ( [Indice Banda], ""En meta"", ""#1B8754"", ""En alerta"", ""#C27C0E"", ""Crítico"", ""#D9383A"", ""#9A9CA3"" )"},
    new[]{@"IndicePerspectiva",@"Indice Texto",@"IF ( ISBLANK ( [Indice] ), ""—"", FORMAT ( [Indice], ""0.0"" ) )"},
    new[]{@"IndicePerspectiva",@"En meta",@"SUM ( IndicePerspectiva[verdes] )"},
    new[]{@"IndicePerspectiva",@"En alerta",@"SUM ( IndicePerspectiva[ambar] )"},
    new[]{@"IndicePerspectiva",@"Críticos",@"SUM ( IndicePerspectiva[rojos] )"},
    new[]{@"IndicePerspectiva",@"Sin evaluar",@"SUM ( IndicePerspectiva[sin_evaluar] )"},
    new[]{@"IndicePerspectiva",@"Indicadores",@"SUM ( IndicePerspectiva[indicadores] )"},
    new[]{@"IndicePerspectiva",@"Evaluados Texto",@"FORMAT ( [En meta] + [En alerta] + [Críticos], ""0"" ) & "" de "" & FORMAT ( [Indicadores], ""0"" ) & "" evaluados"""},
    new[]{@"IndicePerspectiva",@"Objetivo",@"SELECTEDVALUE ( Perspectivas[objetivo] )"},
    new[]{@"IndicePerspectiva",@"Titulo Gestion",@"""Índice de desempeño · "" & FORMAT ( SELECTEDVALUE ( Gestiones[gestion] ), ""0"" )"},
    new[]{@"Scorecard",@"Valor",@"SELECTEDVALUE ( Scorecard[valor] )"},
    new[]{@"Scorecard",@"Valor Texto",@"VAR _v = [Valor]
    VAR _u = SELECTEDVALUE ( Scorecard[unidad] )
    RETURN IF ( ISBLANK ( _v ), ""—"",
        SWITCH ( _u,
            ""PCT"", FORMAT ( _v, ""#,0.0"" ) & "" %"",
            ""PTS"", FORMAT ( _v, ""#,0.0"" ),
            ""BS"",  IF ( ABS ( _v ) >= 1000000, ""Bs "" & FORMAT ( _v / 1000000, ""#,0.00"" ) & "" M"", ""Bs "" & FORMAT ( _v, ""#,0"" ) ),
            FORMAT ( _v, ""#,0"" ) ) )"},
    new[]{@"Scorecard",@"Meta Texto",@"VAR _m = SELECTEDVALUE ( Scorecard[meta] )
    VAR _u = SELECTEDVALUE ( Scorecard[unidad] )
    VAR _s = IF ( SELECTEDVALUE ( Scorecard[sentido] ) = ""MIN"", ""≤ "", ""≥ "" )
    RETURN IF ( ISBLANK ( _m ), ""No definida"",
        _s & SWITCH ( _u,
            ""PCT"", FORMAT ( _m, ""#,0.0"" ) & "" %"",
            ""BS"",  IF ( ABS ( _m ) >= 1000000, ""Bs "" & FORMAT ( _m / 1000000, ""#,0.00"" ) & "" M"", ""Bs "" & FORMAT ( _m, ""#,0"" ) ),
            FORMAT ( _m, ""#,0.0"" ) ) )"},
    new[]{@"Scorecard",@"Estado",@"IF ( ISBLANK ( [Valor] ), ""Sin dato"",
        SWITCH ( SELECTEDVALUE ( Scorecard[semaforo] ),
            ""VERDE"", ""En meta"", ""AMBAR"", ""En alerta"", ""ROJO"", ""Crítico"", ""Sin evaluar"" ) )"},
    new[]{@"Scorecard",@"Estado Color",@"SWITCH ( SELECTEDVALUE ( Scorecard[semaforo] ),
        ""VERDE"", ""#1B8754"", ""AMBAR"", ""#C27C0E"", ""ROJO"", ""#D9383A"", ""#9A9CA3"" )"},
    new[]{@"Scorecard",@"Estado Icono",@"// Círculo + texto: el estado no depende solo del color (accesibilidad)
    ""● "" & [Estado]"},
    new[]{@"Scorecard",@"Tendencia Texto",@"VAR _d = SELECTEDVALUE ( Scorecard[delta] )
    VAR _u = SELECTEDVALUE ( Scorecard[unidad] )
    RETURN IF ( ISBLANK ( _d ) || _d = 0, """",
        IF ( _d > 0, ""▲ +"", ""▼ −"" ) &
        SWITCH ( _u,
            ""PCT"", FORMAT ( ABS ( _d ), ""#,0.0"" ) & "" pp"",
            ""BS"",  IF ( ABS ( _d ) >= 1000000, ""Bs "" & FORMAT ( ABS ( _d ) / 1000000, ""#,0.00"" ) & "" M"", ""Bs "" & FORMAT ( ABS ( _d ), ""#,0"" ) ),
            FORMAT ( ABS ( _d ), ""#,0.0"" ) ) )"},
    new[]{@"Scorecard",@"Tendencia Color",@"SWITCH ( SELECTEDVALUE ( Scorecard[tendencia] ), ""MEJORA"", ""#1B8754"", ""EMPEORA"", ""#D9383A"", ""#9A9CA3"" )"},
    new[]{@"Scorecard",@"Avance Meta",@"// 0–1: MAX → valor/meta; MIN → 1 si valor ≤ meta, si no meta/valor. Igual que la barra de la web.
    VAR _v = [Valor]
    VAR _m = SELECTEDVALUE ( Scorecard[meta] )
    RETURN SWITCH ( TRUE (),
        ISBLANK ( _v ) || ISBLANK ( _m ), BLANK (),
        SELECTEDVALUE ( Scorecard[sentido] ) = ""MAX"", IF ( _m > 0, MIN ( MAX ( _v / _m, 0 ), 1 ) ),
        _v <= _m, 1,
        IF ( _v > 0 && _m > 0, MIN ( _m / _v, 1 ), 0 ) )"},
    new[]{@"Scorecard",@"Valor Anterior Texto",@"VAR _p = SELECTEDVALUE ( Scorecard[valor_anterior] )
    RETURN IF ( ISBLANK ( _p ), """", ""Anterior "" &
        SWITCH ( SELECTEDVALUE ( Scorecard[unidad] ),
            ""PCT"", FORMAT ( _p, ""#,0.0"" ) & "" %"",
            ""BS"",  ""Bs "" & FORMAT ( _p, ""#,0"" ),
            FORMAT ( _p, ""#,0.0"" ) ) )"},
    new[]{@"MetasMensual",@"Ejecutado Bs",@"SUM ( MetasMensual[ejecutado] )"},
    new[]{@"MetasMensual",@"Meta Bs",@"SUM ( MetasMensual[meta] )"},
    new[]{@"MetasMensual",@"Ejecutado Año Anterior Bs",@"SUM ( MetasMensual[ejecutado_anio_ant] )"},
    new[]{@"MetasMensual",@"Cumplimiento %",@"DIVIDE ( [Ejecutado Bs], [Meta Bs] )"},
    new[]{@"RiesgoEstudiante",@"Estudiantes",@"COUNTROWS ( RiesgoEstudiante )"},
    new[]{@"RiesgoEstudiante",@"Prioridad crítica",@"CALCULATE ( COUNTROWS ( RiesgoEstudiante ), RiesgoEstudiante[k_reglas] >= 2 )"},
    new[]{@"DataOpsDocumento",@"Registros",@"SUM ( DataOpsDocumento[registros] )"},
    new[]{@"DataOpsDocumento",@"Consolidado directo",@"SUM ( DataOpsDocumento[consolidado_directo] )"},
    new[]{@"DataOpsDocumento",@"Revisión humana",@"SUM ( DataOpsDocumento[revision_hitl] )"},
    new[]{@"DataOpsDocumento",@"Pendientes",@"SUM ( DataOpsDocumento[pendientes_revision] )"}
};
foreach(var m in medidas){
  var t = Model.Tables[m[0]];
  var ex = t.Measures.FirstOrDefault(x => x.Name == m[1]);
  if(ex != null) ex.Expression = m[2]; else t.AddMeasure(m[1], m[2]);
}
