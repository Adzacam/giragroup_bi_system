"""
backend/services/revision_acciones_descriptor.py
----------------------------------------------
Genera el descriptor `acciones[]` por motivo y rol para la bandeja de revisión humana (DF-L2 / DD2).
Cada acción declara:
  {codigo, etiqueta, widget, campos, precarga, efecto, confirmacion}
El frontend renderiza genéricamente sin hardcodear reglas por motivo ni límites de campos.
"""
from typing import Any, Dict, List, Optional


def _campo_desc(
    name: str,
    label: str,
    tipo: str = "text",
    required: bool = True,
    options: Optional[List[str]] = None,
    max_length: Optional[int] = None,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    default: Any = "",
) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "name": name,
        "label": label,
        "type": tipo,
        "required": required,
        "default": default,
    }
    if options is not None:
        d["options"] = list(options)
    if max_length is not None:
        d["max_length"] = max_length
    if min_val is not None:
        d["min"] = min_val
    if max_val is not None:
        d["max"] = max_val
    return d


def _accion(
    codigo: str,
    etiqueta: str,
    widget: str,
    campos: List[Dict[str, Any]],
    precarga: Optional[Dict[str, Any]] = None,
    efecto: str = "resuelve_caso",
    confirmacion: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "codigo": codigo,
        "etiqueta": etiqueta,
        "widget": widget,
        "campos": campos,
        "precarga": precarga or {},
        "efecto": efecto,
        "confirmacion": confirmacion,
    }


def _motivo_efectivo(motivo: Optional[str], nivel_confianza: Optional[float]) -> str:
    mot = (motivo or "REVISION_GENERAL").strip().upper()
    if mot in ("BAJA_CONFIANZA", "BAJA_CONFIANZA_IA") and (nivel_confianza is None or float(nivel_confianza) <= 0.0):
        return "SIN_LECTURA"
    if mot == "BAJA_CONFIANZA":
        return "BAJA_CONFIANZA_IA"
    return mot


def construir_acciones(
    motivo: Optional[str],
    cat_ruteo: str,
    datos: Optional[Dict[str, Any]] = None,
    rol_usuario: Optional[str] = None,
    candidatos: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    datos = datos or {}
    rol = (rol_usuario or "").strip().upper()
    es_admin_o_auditor = rol in ("ADMIN", "AUDITOR_CALIDAD")
    es_admin = rol == "ADMIN"
    mot = _motivo_efectivo(motivo, datos.get("ner_confidence"))

    precarga_base = {
        "programa": datos.get("programa") or "",
        "modulo_resuelto": datos.get("modulo_detectado") or "",
        "numero_modulo": datos.get("numero_modulo") if datos.get("numero_modulo") is not None else "",
        "docente_resuelto": datos.get("docente") or "",
        "nota_final": datos.get("nota_final") if datos.get("nota_final") is not None else "",
        "mes": datos.get("mes") if datos.get("mes") is not None else "",
        "gestion": datos.get("gestion") if datos.get("gestion") is not None else "",
        "monto_deuda": datos.get("monto_deuda") if datos.get("monto_deuda") is not None else "",
        "cuotas_impagas": datos.get("cuotas_impagas") if datos.get("cuotas_impagas") is not None else "",
        "codigo_pos": datos.get("codigo_pos") or "",
        "justificacion": "",
    }
    campo_just = _campo_desc("justificacion", "Justificación", "text", required=False, max_length=300)
    campo_motivo_descarte = _campo_desc(
        "motivo_descarte",
        "Motivo de descarte",
        "select",
        required=True,
        options=["Fila vacía o sin datos", "Registro duplicado", "Dato de prueba o cabecera", "Otro motivo"],
        default="Fila vacía o sin datos",
    )

    if mot == "CI_NOMBRE_DISCORDANTE":
        acciones = [
            _accion(
                "REGISTRAR_VARIANTE",
                "Misma persona: registrar variante",
                "IdentityCompare",
                [campo_just],
                precarga={"ci_enmascarado": datos.get("ci_enmascarado"), "similitud": datos.get("similitud_nombre_completo"), "justificacion": ""},
                efecto="registra_variante_sin_cambiar_padron",
            ),
            _accion(
                "ACTUALIZAR_NOMBRE_PADRON",
                "Misma persona: actualizar el nombre del padrón",
                "IdentityCompare",
                [_campo_desc("nombre_completo", "Nuevo nombre en padrón", "text", required=True, max_length=150), campo_just],
                precarga={"ci_enmascarado": datos.get("ci_enmascarado"), "justificacion": ""},
                efecto="actualiza_padron",
                confirmacion="¿Confirmas actualizar el nombre canónico en el padrón?",
            ),
            _accion(
                "CORREGIR_CI",
                "Otra persona: corregir la CI",
                "IdentityCompare",
                [_campo_desc("ci_corregido", "Cédula corregida", "text", required=True, max_length=32), campo_just],
                precarga={"justificacion": ""},
                efecto="corrige_ci",
            ),
        ]
    elif mot == "HOMONIMIA":
        acciones = [
            _accion(
                "VINCULAR_CANDIDATO",
                "Vincular al candidato seleccionado",
                "CandidateSelector",
                [_campo_desc("id_estudiante_candidato", "Candidato seleccionado", "candidate", required=True), campo_just],
                precarga={"candidatos": candidatos or [], "justificacion": ""},
                efecto="vincula_estudiante_existente",
            ),
        ]
        if es_admin_o_auditor:
            acciones.append(
                _accion(
                    "CREAR_PERFIL_C",
                    "Es otra persona: crear perfil en estado C",
                    "CandidateSelector",
                    [_campo_desc("nombre_completo", "Nombre completo", "text", required=True, max_length=150), _campo_desc("ci_opcional", "Cédula (opcional)", "text", required=False, max_length=32), campo_just],
                    precarga={"justificacion": ""},
                    efecto="crea_perfil_estado_c",
                    confirmacion="Se creará un perfil nuevo en estado C (acción humana auditada).",
                )
            )
    elif mot == "BAJA_CONFIANZA_IA":
        acciones = [
            _accion(
                "CONFIRMAR_ENTIDADES",
                "Confirmar las entidades",
                "EntityTagEditor",
                [campo_just],
                precarga={"entidades": datos.get("entidades") or [], "beto_ents": datos.get("beto_ents") or [], "justificacion": ""},
                efecto="confirma_entidades_beto",
            ),
            _accion(
                "CORREGIR_ENTIDAD",
                "Corregir una entidad",
                "EntityTagEditor",
                [
                    _campo_desc("entidad_tipo", "Tipo de entidad", "select", required=True, options=["PER_ESTUDIANTE", "PER_DOCENTE", "MODULO", "PROGRAMA"], default="MODULO"),
                    _campo_desc("entidad_texto", "Texto o valor corregido", "text", required=True, max_length=200),
                    campo_just,
                ],
                precarga={"entidades": datos.get("entidades") or [], "beto_ents": datos.get("beto_ents") or [], **precarga_base},
                efecto="corrige_entidad",
            ),
        ]
    elif mot == "SIN_LECTURA":
        acciones = [
            _accion(
                "COMPLETAR_DATOS",
                "Completar los datos faltantes",
                "ValueCorrector",
                [
                    _campo_desc("nombre_completo", "Nombre completo", "text", required=False, max_length=150),
                    _campo_desc("modulo_resuelto", "Módulo", "text", required=False, max_length=150),
                    _campo_desc("nota_final", "Nota sobre 100", "number", required=False, min_val=0, max_val=100),
                    campo_just,
                ],
                precarga=precarga_base,
                efecto="completa_datos_faltantes",
            ),
            _accion(
                "DESCARTAR_VACIA",
                "Descartar por vacía",
                "ValueCorrector",
                [campo_just],
                precarga={"justificacion": "Fila sin datos legibles"},
                efecto="descarta_fila",
            ),
        ]
        return acciones
    elif mot == "CI_DUDOSA":
        acciones = [
            _accion(
                "CORREGIR_CI",
                "Corregir la CI",
                "CiEditor",
                [
                    _campo_desc("ci_numero", "Número de CI", "text", required=True, max_length=20),
                    _campo_desc("ci_complemento", "Complemento / Exp.", "text", required=False, max_length=10),
                    campo_just,
                ],
                precarga={"ci_enmascarado": datos.get("ci_enmascarado"), "justificacion": ""},
                efecto="corrige_ci",
            ),
            _accion(
                "PERFIL_TEMP_B",
                "Sin CI: perfil TEMP (estado B)",
                "CiEditor",
                [campo_just],
                precarga={"justificacion": ""},
                efecto="crea_perfil_temp_b",
            ),
        ]
    elif mot in ("FILA_SIN_IDENTIDAD", "LINEA_SIN_IDENTIDAD"):
        acciones = [
            _accion(
                "VINCULAR_PERSONA",
                "Vincular a una persona",
                "PersonSearch",
                [_campo_desc("id_estudiante_candidato", "Persona en el padrón", "person_search", required=True), campo_just],
                precarga={"justificacion": ""},
                efecto="vincula_estudiante_existente",
            ),
        ]
    elif mot == "VALOR_FUERA_DE_CATALOGO":
        if (datos.get("campo_afectado") or "").lower() == "modulo":
            acciones = [
                _accion(
                    "VINCULAR_MODULO",
                    "Vincular a un módulo existente",
                    "ModuleSearch",
                    [_campo_desc("id_modulo_destino", "Módulo existente", "module_search", required=True), campo_just],
                    precarga={
                        "valor_recibido": datos.get("valor_recibido") or "",
                        "codigo_pos": datos.get("codigo_pos") or "",
                        "programa": datos.get("programa") or "",
                        "justificacion": "",
                    },
                    efecto="vincula_modulo",
                ),
            ]
            if es_admin_o_auditor:
                acciones.append(
                    _accion(
                        "CREAR_MODULO",
                        "Crear módulo",
                        "ModuleSearch",
                        [
                            _campo_desc("codigo_pos", "Código POS", "text", required=True, max_length=60),
                            _campo_desc("modulo_resuelto", "Nombre del módulo", "text", required=True, max_length=150),
                            _campo_desc("programa_resuelto", "Programa", "text", required=False, max_length=150),
                            campo_just,
                        ],
                        precarga={
                            "codigo_pos": datos.get("codigo_pos") or "",
                            "modulo_resuelto": datos.get("valor_recibido") or "",
                            "programa_resuelto": datos.get("programa") or "",
                            "justificacion": "",
                        },
                        efecto="crea_modulo_en_dim",
                        confirmacion="Se creará un nuevo módulo en el catálogo institucional.",
                    )
                )
            acciones.append(
                _accion(
                    "MARCAR_SIN_DATO",
                    "Marcar sin dato",
                    "CatalogPicker",
                    [campo_just],
                    precarga={"justificacion": ""},
                    efecto="marca_sin_dato",
                )
            )
        else:
            campos_cat = [_campo_desc("valor_canonico", "Valor canónico", "text", required=True, max_length=150)]
            if es_admin_o_auditor:
                campos_cat.append(_campo_desc("recordar_sinonimo", "Recordar como sinónimo", "checkbox", required=False, default=True))
            campos_cat.append(campo_just)
            acciones = [
                _accion(
                    "ASIGNAR_CANONICO",
                    "Asignar un valor canónico",
                    "CatalogPicker",
                    campos_cat,
                    precarga={"valor_recibido": datos.get("valor_recibido") or "", "opciones_catalogo": datos.get("opciones_catalogo") or [], "justificacion": ""},
                    efecto="asigna_valor_canonico",
                ),
                _accion(
                    "MARCAR_SIN_DATO",
                    "Marcar sin dato",
                    "CatalogPicker",
                    [campo_just],
                    precarga={"justificacion": ""},
                    efecto="marca_sin_dato",
                ),
            ]
    elif mot == "RESPUESTA_EN_COLUMNA_EQUIVOCADA":
        acciones = [
            _accion(
                "MOVER_A_PREGUNTA",
                "Mover a la pregunta correcta",
                "ColumnReassign",
                [_campo_desc("pregunta_destino", "Pregunta correcta", "text", required=True, max_length=200), campo_just],
                precarga={"pregunta_origen": datos.get("campo_afectado") or "", "justificacion": ""},
                efecto="reasigna_columna",
            ),
            _accion(
                "MARCAR_SIN_RESPUESTA",
                "Marcar sin respuesta",
                "ColumnReassign",
                [campo_just],
                precarga={"justificacion": ""},
                efecto="marca_sin_respuesta",
            ),
        ]
    elif mot in ("PUNTUACION_FUERA_DE_ESCALA", "NOTA_FUERA_DE_RANGO", "NOTA_FUERA_ESCALA"):
        acciones = [
            _accion(
                "CORREGIR_VALOR",
                "Corregir el valor",
                "ValueCorrector",
                [_campo_desc("valor_corregido", "Valor corregido", "number", required=True, min_val=0, max_val=100), campo_just],
                precarga={"valor_recibido": datos.get("valor_recibido") or datos.get("nota_final") or "", "justificacion": ""},
                efecto="corrige_valor_numerico",
            ),
            _accion(
                "ANULAR_VALOR",
                "Anular (NULL)",
                "ValueCorrector",
                [campo_just],
                precarga={"justificacion": ""},
                efecto="anula_valor",
            ),
        ]
        if cat_ruteo == "academico":
            acciones.append(
                _accion(
                    "MARCAR_INASISTENCIA",
                    "Es inasistencia",
                    "ValueCorrector",
                    [campo_just],
                    precarga={"justificacion": ""},
                    efecto="marca_inasistencia",
                )
            )
    elif mot == "POS_NO_EN_DIM_MODULO":
        acciones = [
            _accion(
                "VINCULAR_MODULO",
                "Vincular a un módulo existente",
                "ModuleSearch",
                [_campo_desc("id_modulo_destino", "Módulo existente", "module_search", required=True), campo_just],
                precarga={"codigo_pos": datos.get("codigo_pos") or "", "programa": datos.get("programa") or "", "justificacion": ""},
                efecto="vincula_modulo",
            ),
        ]
        if es_admin_o_auditor:
            acciones.append(
                _accion(
                    "CREAR_MODULO",
                    "Crear módulo",
                    "ModuleSearch",
                    [
                        _campo_desc("codigo_pos", "Código POS", "text", required=True, max_length=60),
                        _campo_desc("modulo_resuelto", "Nombre del módulo", "text", required=True, max_length=150),
                        _campo_desc("programa_resuelto", "Programa", "text", required=True, max_length=150),
                        campo_just,
                    ],
                    precarga={"codigo_pos": datos.get("codigo_pos") or "", "programa_resuelto": datos.get("programa") or "", "justificacion": ""},
                    efecto="crea_modulo_en_dim",
                    confirmacion="Se creará un nuevo módulo en el catálogo institucional.",
                )
            )
    elif mot == "CONFLICTO_FUENTES":
        acciones = []
        if es_admin:
            acciones.append(
                _accion(
                    "CAMBIAR_FUENTE_PRIORITARIA",
                    "Cambiar la fuente prioritaria",
                    "SourceConflict",
                    [_campo_desc("fuente_prioritaria", "Fuente prioritaria", "text", required=True, max_length=80), campo_just],
                    precarga={"justificacion": ""},
                    efecto="cambia_regla_global_fuente",
                    confirmacion="Esto modifica la regla global de prioridad de fuentes para futuras consolidaciones.",
                )
            )
        return acciones
    elif mot == "RELACION_INCOHERENTE":
        acciones = [
            _accion(
                "VINCULAR_RELACION",
                "Vincular a…",
                "ModuleSearch",
                [_campo_desc("id_modulo_destino", "Programa o módulo destino", "module_search", required=True), campo_just],
                precarga={
                    "regla": datos.get("regla_relacion") or "",
                    "valor": datos.get("valor_incoherente") or "",
                    "codigo_pos": datos.get("codigo_pos") or "",
                    "justificacion": "",
                },
                efecto="vincula_modulo",
            ),
            _accion(
                "CORREGIR_FECHA",
                "Corregir fecha",
                "DatePicker",
                [
                    _campo_desc("mes", "Mes", "number", required=True, min_val=1, max_val=12),
                    _campo_desc("gestion", "Gestión (año)", "number", required=True, min_val=2015, max_val=2030),
                    campo_just,
                ],
                precarga={"mes": precarga_base["mes"], "gestion": precarga_base["gestion"], "justificacion": ""},
                efecto="corrige_fecha_y_consolida",
            ),
            _accion(
                "MARCAR_SIN_DATO",
                "Marcar sin dato",
                "ValueCorrector",
                [campo_just],
                precarga={"regla": datos.get("regla_relacion") or "", "justificacion": ""},
                efecto="anula_valor",
            ),
        ]
    elif mot == "DESACUERDO_REGLA_BETO":
        acciones = [
            _accion(
                "APROBAR",
                "Confirmar persona leída por regla",
                "StudentSearch",
                [campo_just],
                precarga={"justificacion": "", "candidatos": candidatos or []},
                efecto="resuelve_caso",
            ),
            _accion(
                "VINCULAR_ESTUDIANTE",
                "Vincular a otra persona del padrón",
                "StudentSearch",
                [_campo_desc("id_estudiante_destino", "Persona del padrón", "student_search", required=True), campo_just],
                precarga={"candidatos": candidatos or [], "justificacion": ""},
                efecto="vincula_estudiante",
            ),
        ]
    else:
        acciones = [
            _accion(
                "APROBAR",
                "Aprobar con corrección",
                "ValueCorrector",
                [_campo_desc("modulo_resuelto", "Módulo", "text", required=False, max_length=150), campo_just],
                precarga=precarga_base,
                efecto="resuelve_caso",
            )
        ]

    acciones.append(
        _accion(
            "DESCARTAR",
            "Descartar",
            acciones[0]["widget"] if acciones else "ValueCorrector",
            [campo_motivo_descarte, campo_just],
            precarga={"motivo_descarte": "Fila vacía o sin datos", "justificacion": ""},
            efecto="descarta_fila",
            confirmacion="¿Confirmas descartar este registro de la consolidación?",
        )
    )
    return acciones
