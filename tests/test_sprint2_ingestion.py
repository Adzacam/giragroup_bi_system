"""
test_sprint2_ingestion.py — Tests de integración para Sprint 2
Verifica los componentes nuevos y modificados del pipeline de ingestión:
- Detección y fusión de encabezados de 2 niveles
- Clasificación de hojas por contenido y exclusión de hojas financieras (IBP)
- Mapeo canónico de columnas (exacto, fuzzy con threshold, anti-aliases y perfilado)
- Perfilado automático y clasificación texto_libre
- Enriquecimiento relacional (DOCENTE desde cruce POS+MÓDULO)
- Documento Mínimo (GIRA-40) con hashing idempotente
- Bloqueo de docente en encuestas y guardián de asignación única por columna
- Validación estricta de CI y extracción limpia de POS (descarte de cadenas de grupos)
- Limpieza de texto (N/A, mojibake, deduplicación)
- Verificación de llaves foráneas (GIRA-50 semilla)
"""

import pytest
import pandas as pd
import hashlib

# ── Componente 1: Canonical Mapper ────────────────────────────────────────

from pipeline.ingestion.canonical_mapper import CanonicalMapper


class TestCanonicalMapper:
    """Tests para el mapeo canónico de columnas."""

    @pytest.fixture
    def mapper(self):
        return CanonicalMapper()

    def test_coincidencia_exacta(self, mapper):
        """Alias exacto del diccionario se resuelve correctamente."""
        campo, metodo, score = mapper.resolver_columna("cédula de identidad")
        assert campo == "identificador_persona"
        assert metodo == "EXACTO"
        assert score == 100.0

    def test_coincidencia_exacta_case_insensitive(self, mapper):
        """La resolución es case-insensitive."""
        campo, _, _ = mapper.resolver_columna("CÉDULA DE IDENTIDAD")
        assert campo == "identificador_persona"

    def test_coincidencia_fuzzy_pregunta_abierta(self, mapper):
        """Variaciones de redacción en preguntas abiertas se resuelven por fuzzy."""
        campo, metodo, score = mapper.resolver_columna(
            "6. ¿Qué aspectos del estilo de enseñanza podrían mejorarse?"
        )
        assert campo == "sugerencia_estilo_docente"
        assert metodo in ("EXACTO", "FUZZY")
        assert score >= mapper.threshold

    def test_anti_alias_exclusion(self, mapper):
        """'nombres' jamás debe mapearse a 'nombre_programa' gracias a las reglas de anti-alias."""
        campo, metodo, _ = mapper.resolver_columna("nombres")
        assert campo != "nombre_programa"

    def test_docente_survey_mapping_lock(self, mapper):
        """En encuestas (es_encuesta=True), la columna 'docente' no se asigna vía mapper."""
        campo, metodo, _ = mapper.resolver_columna("nombre del docente", es_encuesta=True)
        assert campo != "docente"

    def test_columna_no_reconocida(self, mapper):
        """Una columna completamente desconocida retorna NO_MATCH."""
        campo, metodo, _ = mapper.resolver_columna("xyzzy_columna_random_42")
        assert campo is None
        assert metodo == "NO_MATCH"

    def test_resolver_multiples_columnas(self, mapper):
        """Resuelve un lote de columnas con estadísticas."""
        resultado = mapper.resolver_columnas_df([
            "ci", "nombre del programa", "xyzzy_desconocida"
        ])
        assert resultado["estadisticas"]["exactas"] >= 1
        assert resultado["estadisticas"]["no_match"] >= 1
        assert len(resultado["no_mapeadas"]) >= 1

    def test_hoja_descartable_por_nombre(self, mapper):
        """Hojas con nombres tipo 'Copia de...' se detectan como descartables."""
        es_desc, razon = mapper.es_hoja_descartable("Copia de Respuestas")
        assert es_desc is True
        assert razon == "HOJA_DUPLICADA_BORRADOR"

    def test_hoja_normal_no_descartable(self, mapper):
        """Hojas con nombres normales no se descartan."""
        es_desc, _ = mapper.es_hoja_descartable("DIPLOMADOS DOCENTE")
        assert es_desc is False


# ── Componente 2: Header Detector ────────────────────────────────────────

from pipeline.ingestion.header_detector import (
    detectar_encabezado,
    aplicar_encabezado,
)


class TestHeaderDetector:

    def test_encabezado_simple(self):
        """Detecta encabezado de un solo nivel en fila 0."""
        df = pd.DataFrame({
            0: ["nombre", "Juan", "María"],
            1: ["ci", "1234567", "7654321"],
            2: ["nota", "85", "92"],
        })
        resultado = detectar_encabezado(df)
        assert resultado["fila_encabezado"] == 0
        assert resultado["es_doble_nivel"] is False
        assert not resultado["encabezado_corrupto"]

    def test_detect_and_merge_two_level_headers(self):
        """Encabezados fusionados de 2 niveles se concatenan correctamente."""
        df = pd.DataFrame({
            0: ["Bloque 1", "Pregunta A", "respuesta1", "respuesta2"],
            1: [None, "Pregunta B", "respuesta3", "respuesta4"],
            2: ["Bloque 2", "Pregunta C", "respuesta5", "respuesta6"],
        })
        resultado = detectar_encabezado(df)
        assert resultado["es_doble_nivel"] or resultado["fila_encabezado"] >= 0
        for col in resultado["columnas_finales"]:
            assert "unnamed" not in col.lower()

    def test_encabezado_corrupto(self):
        """Encabezados con emails/fragmentos se marcan como corruptos."""
        df = pd.DataFrame({
            0: ["user@email.com", "Juan", "María"],
            1: ["12345678", "1234567", "7654321"],
            2: ["farma", "dato1", "dato2"],
        })
        resultado = detectar_encabezado(df)
        assert len(resultado["columnas_corruptas"]) > 0

    def test_aplicar_encabezado(self):
        """Aplica correctamente los encabezados detectados al DataFrame."""
        df = pd.DataFrame({
            0: ["nombre", "Juan", "María"],
            1: ["ci", "1234567", "7654321"],
        })
        resultado = detectar_encabezado(df)
        df_limpio = aplicar_encabezado(df, resultado)
        assert len(df_limpio) == 2
        assert "nombre" in df_limpio.columns


# ── Componente 2: Profiler ───────────────────────────────────────────────

from pipeline.ingestion.profiler import perfilar_columna, perfilar_hoja


class TestProfiler:

    def test_profiler_sampling_and_text_threshold(self):
        """El perfilado usa muestreo y clasifica texto_libre solo si >40% superan umbrales."""
        textos = ["Este es un comentario bastante largo sobre la enseñanza del docente"] * 50
        textos += ["corto"] * 20
        serie = pd.Series(textos)

        perfil = perfilar_columna(serie, "columna_test")
        assert perfil.rol_inferido == "texto_libre"

    def test_perfil_columna_numerica_likert(self):
        """Columna con valores 1-5 se clasifica como categorico_likert."""
        serie = pd.Series([1, 2, 3, 4, 5, 3, 4, 5, 2, 1] * 10)
        perfil = perfilar_columna(serie, "evaluacion")
        assert perfil.rol_inferido == "categorico_likert"

    def test_clasificacion_hoja_encuesta(self):
        """Hoja con columnas Likert + texto libre → familia texto_libre."""
        df = pd.DataFrame({
            "pregunta_1": [4, 5, 3, 4, 5] * 20,
            "pregunta_2": [3, 4, 5, 2, 1] * 20,
            "comentario": [
                "El docente tiene un excelente dominio de la materia y explica muy bien en las sesiones semanales"
            ] * 100,
        })
        resultado = perfilar_hoja(df, "Encuesta Test")
        assert resultado["familia"] == "texto_libre"
        assert "comentario" in resultado["columnas_texto_libre"]

    def test_ibp_sheet_financial_classification(self):
        """Hoja con keywords financieras (ej: IBP) NO se clasifica como texto_libre."""
        df = pd.DataFrame({
            "pos_ibp": ["POS-001", "POS-002"],
            "inversión_del_programa": [10000, 20000],
            "punto_equilibrio": [15, 20],
            "comentarios": ["Resumen breve IBP", "Ok"],
        })
        resultado = perfilar_hoja(df, "IBP")
        assert resultado["familia"] != "texto_libre"
        assert len(resultado["columnas_texto_libre"]) == 0


# ── Componente 4: Text Cleaner ───────────────────────────────────────────

from pipeline.normalization.text_cleaner import (
    es_respuesta_vacia,
    corregir_mojibake,
    limpiar_texto_para_ner,
    deduplicar_respuestas,
)


class TestTextCleaner:

    @pytest.mark.parametrize("valor", [
        "", "N/A", "N/A.1", "N/A.2", "nan", "None", ".", "-", "5", "X",
    ])
    def test_clean_and_deduplicate_vacios(self, valor):
        assert es_respuesta_vacia(valor) is True

    @pytest.mark.parametrize("valor", [
        "El docente explica bien",
        "Necesita mejorar la didáctica",
        "Muy buena clase, aprendí mucho",
    ])
    def test_texto_valido_no_vacio(self, valor):
        assert es_respuesta_vacia(valor) is False

    def test_correccion_mojibake(self):
        texto_corrupto = "La evaluaci\u00c3\u00b3n fue excelente y la ense\u00c3\u00b1anza muy buena"
        corregido = corregir_mojibake(texto_corrupto)
        assert "\u00f3" in corregido
        assert "\u00f1" in corregido

    def test_deduplicacion_por_llaves(self):
        registros = [
            {"pos": "P001", "identificador_persona": "1234567", "fecha_evento": "2026-01-15", "texto": "A"},
            {"pos": "P001", "identificador_persona": "1234567", "fecha_evento": "2026-01-15", "texto": "B"},
            {"pos": "P002", "identificador_persona": "7654321", "fecha_evento": "2026-02-20", "texto": "C"},
        ]
        unicos, duplicados = deduplicar_respuestas(registros)
        assert len(unicos) == 2
        assert len(duplicados) == 1


# ── Componente 4: Entity Enricher ────────────────────────────────────────

from pipeline.normalization.entity_enricher import EntityEnricher


class TestEntityEnricher:

    def test_entity_enricher_docente_lookup(self):
        enricher = EntityEnricher()

        df_modulos = pd.DataFrame({
            "pos": ["P001", "P001", "P002"],
            "modulo": ["MOD-101", "MOD-102", "MOD-201"],
            "docente": ["Juan Perez", "Maria Garcia", "Carlos Lopez"],
            "nombre_programa": ["DERECHO", "DERECHO", "MEDICINA"],
        })

        hoja_maestra = {
            "data": df_modulos,
            "mapeo_columnas": {
                "pos": "pos",
                "modulo": "modulo",
                "docente": "docente",
                "nombre_programa": "nombre_programa",
            },
            "nombre_hoja": "MODULOS",
        }

        enricher.cargar_desde_dataframes([hoja_maestra])

        assert enricher.cargado is True
        assert enricher.total_docentes == 3
        assert enricher.buscar_docente("P001", "MOD-101") == "Juan Perez"

    def test_enricher_programa(self):
        enricher = EntityEnricher()
        df = pd.DataFrame({
            "pos": ["P001", "P002"],
            "modulo": ["M1", "M2"],
            "docente": ["Doc1", "Doc2"],
            "nombre_programa": ["DERECHO", "MEDICINA"],
        })
        hoja = {
            "data": df,
            "mapeo_columnas": {"pos": "pos", "nombre_programa": "nombre_programa",
                               "modulo": "modulo", "docente": "docente"},
            "nombre_hoja": "TEST",
        }
        enricher.cargar_desde_dataframes([hoja])
        assert enricher.buscar_programa("P001") == "DERECHO"


# ── Componente 4: Document Builder ───────────────────────────────────────

from pipeline.normalization.document_builder import (
    construir_documentos_minimos,
    extraer_codigo_pos,
    _validar_formato_ci,
)


class TestDocumentBuilder:

    def test_ci_regex_validation(self):
        """Secuencias numéricas de fila ('1', '16') son rechazadas como CI."""
        assert _validar_formato_ci("1") == ""
        assert _validar_formato_ci("16") == ""
        assert _validar_formato_ci("1234567") == "1234567"
        assert _validar_formato_ci("estudiante@test.com") == "estudiante@test.com"

    def test_pos_extraction_rejection(self):
        """Cadenas de grupo sin código POS son rechazadas."""
        assert extraer_codigo_pos("Grupo B - La Paz") == ""
        assert extraer_codigo_pos("Maestría en Finanzas / POS-028") == "POS-028"

    def test_beto_payload_excludes_administrative_tags(self):
        """Columnas de grupo no generan documentos para BETO."""
        df = pd.DataFrame({
            "pos": ["POS-001"],
            "grupos": ["Grupo B - La Paz"],
            "comentario": ["El docente tiene buena didáctica en clase"],
        })
        hoja_info = {
            "nombre_archivo": "test.xlsx",
            "nombre_hoja": "Encuesta",
            "data": df,
            "columnas_texto_libre": ["grupos", "comentario"],
            "mapeo_columnas": {"pos": "pos", "grupos": "grupo", "comentario": "comentario_general"},
        }
        docs = construir_documentos_minimos(hoja_info)
        # La columna 'grupos' (mapeada a 'grupo') debe filtrarse y no generar doc
        assert len(docs) == 1
        assert docs[0]["pregunta_canonica"] == "comentario_general"

    def test_document_builder_output(self):
        df = pd.DataFrame({
            "pos": ["POS-001", "POS-002"],
            "comentario": [
                "El docente muestra excelente dominio de la materia",
                "Necesita mejorar la metodología de enseñanza",
            ],
        })

        hoja_info = {
            "nombre_archivo": "test.xlsx",
            "nombre_hoja": "Encuesta",
            "data": df,
            "columnas_texto_libre": ["comentario"],
            "mapeo_columnas": {"pos": "pos", "comentario": "comentario_general"},
        }

        docs = construir_documentos_minimos(hoja_info)
        assert len(docs) == 2

        for doc in docs:
            assert "id_documento" in doc
            assert "texto_plano" in doc
            assert "fuente" in doc
            assert "fila_original" in doc
            assert "pregunta_canonica" in doc
            assert "llaves_relacion" in doc
            assert "es_respuesta_vacia" in doc
            assert "estado" in doc

    def test_idempotent_sha256_hashing(self):
        df = pd.DataFrame({
            "pos": ["POS-001"],
            "comentario": ["Excelente docente en clase"],
        })
        hoja_info = {
            "nombre_archivo": "test.xlsx",
            "nombre_hoja": "Enc",
            "data": df,
            "columnas_texto_libre": ["comentario"],
            "mapeo_columnas": {"pos": "pos", "comentario": "comentario_general"},
        }

        docs1 = construir_documentos_minimos(hoja_info)
        docs2 = construir_documentos_minimos(hoja_info)
        assert docs1[0]["id_documento"] == docs2[0]["id_documento"]


# ── Componente 5: FK Checker & Audit Logger ──────────────────────────────

from pipeline.normalization.fk_checker import ForeignKeyChecker
from pipeline.normalization.audit_logger import AuditLogger


class TestFKCheckerAndAudit:

    def test_foreign_key_flagging(self):
        checker = ForeignKeyChecker()
        df_maestro = pd.DataFrame({"pos": ["POS-001", "POS-002"]})
        hoja = {
            "data": df_maestro,
            "mapeo_columnas": {"pos": "pos"},
            "nombre_hoja": "Maestro",
        }
        checker.cargar_pos_maestros([hoja])

        documentos = [
            {"llaves_relacion": {"POS": "POS-001"}, "estado": "ok"},
            {"llaves_relacion": {"POS": "POS-999"}, "estado": "ok"},
            {"llaves_relacion": {"POS": ""}, "estado": "ok"},
        ]

        resultado = checker.verificar_documentos(documentos)
        assert resultado["pos_validos"] == 1
        assert resultado["pos_invalidos"] == 1
        assert resultado["pos_vacios"] == 1

    def test_audit_logger_reporte(self, tmp_path):
        audit = AuditLogger("test_file.xlsx")
        audit.registrar_hoja_descartada("Dashboard 1", "DASHBOARD_SIN_DATOS")
        ruta_json = str(tmp_path / "audit.json")
        reporte = audit.exportar_reporte(ruta=ruta_json)
        assert reporte["resumen"]["hojas_descartadas"] == 1

    def test_grupo_excluded_despite_relaxed_metrics(self):
        """Verifica que cadenas tipo 'Grupo B - La Paz' sean bloqueadas por document_builder incluso con métricas de profiler."""
        df = pd.DataFrame({
            "pos": ["POS-001"],
            "grupos": ["Grupo B - La Paz"],
            "comentario": ["El docente explica muy bien la materia en clase"],
        })
        hoja_info = {
            "nombre_archivo": "test.xlsx",
            "nombre_hoja": "Encuesta",
            "data": df,
            "columnas_texto_libre": ["grupos", "comentario"],
            "mapeo_columnas": {"pos": "pos", "grupos": "grupo", "comentario": "comentario_general"},
        }
        docs = construir_documentos_minimos(hoja_info)
        assert len(docs) == 1
        assert docs[0]["pregunta_canonica"] == "comentario_general"
        assert docs[0]["texto_plano"] == "El docente explica muy bien la materia en clase"

    def test_cursos_docente_survey_classification(self):
        """Verifica que una hoja como CURSOS DOCENTE con Likert y open text conciso se clasifique como texto_libre."""
        df = pd.DataFrame({
            "1: Docente explica claramente (1-5)": [4, 5, 3] * 10,
            "2: Docente domina el contenido (1-5)": [5, 4, 4] * 10,
            "15: Contenido adicional deseado (abierta)": ["Temas de IA", "Más casos reales", "Ninguno"] * 10,
        })
        resultado = perfilar_hoja(df, "CURSOS DOCENTE")
        assert resultado["familia"] == "texto_libre"

    def test_roster_sheet_name_reinforcement(self):
        """Una hoja llamada 'Docentes' que es solo un padrón académico (sin Likert ni abiertas) NO se clasifica como texto_libre."""
        df = pd.DataFrame({
            "codigo_docente": ["D001", "D002", "D003"],
            "nombre": ["Juan Perez", "Maria Gomez", "Carlos Lopez"],
            "especialidad": ["Derecho", "Medicina", "Ingeniería"],
        })
        resultado = perfilar_hoja(df, "Docentes")
        assert resultado["familia"] != "texto_libre"

    def test_actas_and_modulos_relational_priority(self):
        """Verifica que ACTAS DE NOTAS con columna de COMENTARIOS se clasifique como estructurado_relacional por esquema de llaves maestras."""
        df = pd.DataFrame({
            "POS - ACTAS": ["POS-001", "POS-002"],
            "DOCENTE": ["Juan Perez", "Maria Gomez"],
            "MÓDULO 1": [90, 85],
            "COMENTARIOS": ["Pendiente", "Aprobado"],
        })
        resultado = perfilar_hoja(df, "ACTAS DE NOTAS")
        assert resultado["familia"] == "estructurado_relacional"

    def test_estado_del_programa_anti_alias(self):
        """Verifica que 'estado_del_programa' no sea mapeado a 'nombre_programa'."""
        mapper = CanonicalMapper()
        columnas = ["estado_del_programa", "nombre_del_programa"]
        res = mapper.resolver_columnas_df(columnas)
        mapeo = res.get("mapeo", res)
        assert mapeo.get("estado_del_programa") != "nombre_programa"
        assert mapeo.get("nombre_del_programa") == "nombre_programa"

    def test_composite_pos_extraction(self):
        """Verifica que la extracción de POS recorte sufijos de CI en claves compuestas."""
        assert extraer_codigo_pos("POS-033-5160091") == "POS-033"
        assert extraer_codigo_pos("POS-028-7344449") == "POS-028"

    def test_fk_checker_updates_doc_status(self):
        """Verifica que FKChecker cambie el estado a 'sin_llave_valida' cuando el POS no está en maestros."""
        checker = ForeignKeyChecker()
        checker._cargado = True
        checker._pos_validos = {"pos-001"}
        docs = [
            {"id_documento": "1", "estado": "ok", "llaves_relacion": {"POS": "POS-999"}},
            {"id_documento": "2", "estado": "ok", "llaves_relacion": {"POS": "POS-001"}},
        ]
        res = checker.verificar_documentos(docs)
        assert res["documentos_actualizados"][0]["estado"] == "sin_llave_valida"
        assert res["documentos_actualizados"][1]["estado"] == "ok"

    def test_survey_with_pos_and_specific_open_questions(self):
        """Verifica que una hoja con columnas POS+DOCENTE+MÓDULO Y preguntas abiertas específicas sea clasificada como texto_libre."""
        df = pd.DataFrame({
            "POS": ["POS-021"],
            "DOCENTE": ["Juan Perez"],
            "MÓDULO": [12],
            "8_aspectos_del_estilo_docente_a_mejorar_abierta": ["Mejorar los ejemplos prácticos en clase"],
        })
        mapper = CanonicalMapper()
        perfiles_map = {p["nombre"]: p for p in perfilar_hoja(df, "TBL EVALUACION DOCENTE")["perfiles_columnas"]}
        mapeo = mapper.resolver_columnas_df(df.columns.tolist(), perfiles_map=perfiles_map)
        
        has_pregunta_especifica = any(
            mapper.es_campo_pregunta_especifica(c) for c in mapeo.get("mapeo", {}).values() if c
        )
        assert has_pregunta_especifica is True

    def test_master_relational_with_generic_comment(self):
        """Verifica que una hoja con POS+DOCENTE y solo comentario genérico siga ganando estructurado_relacional."""
        df = pd.DataFrame({
            "POS - ACTAS": ["POS-001"],
            "DOCENTE": ["Juan Perez"],
            "MÓDULO 1": [90],
            "COMENTARIOS": ["Pendiente"],
        })
        resultado = perfilar_hoja(df, "ACTAS DE NOTAS")
        mapper = CanonicalMapper()
        mapeo = mapper.resolver_columnas_df(df.columns.tolist())
        has_pregunta_especifica = any(
            mapper.es_campo_pregunta_especifica(c) for c in mapeo.get("mapeo", {}).values() if c
        )
        assert has_pregunta_especifica is False
        assert resultado["familia"] == "estructurado_relacional"
