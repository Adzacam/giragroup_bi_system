from pathlib import Path

p = Path("backend/routers/dataops.py")
text = p.read_text(encoding="utf-8")

patches = [
    # 1. ESTUDIANTE catalog match
    ('"algorithm": best_est_algo,\n            "es_nuevo_perfil": False,',
     '"algorithm": best_est_algo,\n            "fuente_resolucion": "FUZZY" if "Fuzzy" in best_est_algo else "ENCABEZADO",\n            "es_nuevo_perfil": False,'),

    # 2. ESTUDIANTE no catalog
    ('"algorithm": "Sin coincidencia en catálogo (Perfil Nuevo)",\n            "es_nuevo_perfil": True,',
     '"algorithm": "Sin coincidencia en catálogo (Perfil Nuevo)",\n            "fuente_resolucion": "BETO",\n            "es_nuevo_perfil": True,'),

    # 3. CI dudoso
    ('"algorithm": "Regex Validation Failed (Sufijo ?)",\n            }',
     '"algorithm": "Regex Validation Failed (Sufijo ?)",\n                "fuente_resolucion": "REGEX",\n            }'),

    # 4. CI exacto
    ('"algorithm": "Regex CI Exact Format",\n            }',
     '"algorithm": "Regex CI Exact Format",\n                "fuente_resolucion": "CI_EXACTA",\n            }'),

    # 5. CI no provisto
    ('"algorithm": "Identificación por Nombre / TEMP-ID",\n        }',
     '"algorithm": "Identificación por Nombre / TEMP-ID",\n            "fuente_resolucion": "REGEX",\n        }'),

    # 6. DOCENTE catalog match
    ('"algorithm": best_doc_algo,\n            "es_nuevo_perfil": False,',
     '"algorithm": best_doc_algo,\n            "fuente_resolucion": "FUZZY" if "Fuzzy" in best_doc_algo else "ENCABEZADO",\n            "es_nuevo_perfil": False,'),

    # 7. DOCENTE no catalog
    ('"algorithm": "Sin coincidencia en catálogo (Perfil Nuevo en Catálogo de Docentes)",\n            "es_nuevo_perfil": True,',
     '"algorithm": "Sin coincidencia en catálogo (Perfil Nuevo en Catálogo de Docentes)",\n            "fuente_resolucion": "BETO",\n            "es_nuevo_perfil": True,'),

    # 8. MODULO catalog match
    ('"algorithm": best_mod_algo,\n            "es_nuevo_perfil": False,',
     '"algorithm": best_mod_algo,\n            "fuente_resolucion": "FUZZY" if "Fuzzy" in best_mod_algo else "ENCABEZADO",\n            "es_nuevo_perfil": False,'),

    # 9. MODULO no catalog
    ('"algorithm": "Sin coincidencia en catálogo (Perfil Nuevo en Catálogo de Módulos)",\n            "es_nuevo_perfil": True,',
     '"algorithm": "Sin coincidencia en catálogo (Perfil Nuevo en Catálogo de Módulos)",\n            "fuente_resolucion": "BETO",\n            "es_nuevo_perfil": True,'),

    # 10. CONCEPTO FINANCIERO
    ('"algorithm": "Token Sort Similarity",\n        }',
     '"algorithm": "Token Sort Similarity",\n            "fuente_resolucion": "FUZZY",\n        }'),

    # 11. MONTO
    ('"algorithm": "Regex Currency Format",\n            }',
     '"algorithm": "Regex Currency Format",\n                "fuente_resolucion": "REGEX",\n            }'),

    # 12. PROGRAMA
    ('"catalogTable": "Catálogo de Programas",\n            "matchedCanonical": str(prog_token),',
     '"catalogTable": "Catálogo de Programas",\n            "matchedCanonical": str(prog_token),\n            "fuente_resolucion": "ENCABEZADO" if (labeled_data and any(k in labeled_data for k in ["PROGRAMA", "CARRERA", "POS", "DIPLOMADO"])) else "REGEX",'),

    # 13. NOTA
    ('"algorithm": "Explicit Scale Declared" if not grade_invalida else "Unspecified Scale Error",\n            }',
     '"algorithm": "Explicit Scale Declared" if not grade_invalida else "Unspecified Scale Error",\n                "fuente_resolucion": "ENCABEZADO" if (labeled_data and any(k in labeled_data for k in ["NOTA", "CALIFICACION", "PUNTAJE"])) else "REGEX",\n            }'),

    # 14. ASISTENCIA
    ('"algorithm": "Regex Attendance Pattern",\n            }',
     '"algorithm": "Regex Attendance Pattern",\n                "fuente_resolucion": "ENCABEZADO" if (labeled_data and any(k in labeled_data for k in ["ASISTENCIA", "ASIST", "INASISTENCIA"])) else "REGEX",\n            }'),

    # 15. REGISTRO fallback
    ('"algorithm": "Raw Token Parser",\n        }',
     '"algorithm": "Raw Token Parser",\n            "fuente_resolucion": "REGEX",\n        }')
]

crlf = "\r\n" in text
for old, new in patches:
    if crlf:
        old = old.replace("\n", "\r\n")
        new = new.replace("\n", "\r\n")
    if old in text:
        text = text.replace(old, new, 1)
        print("Patch aplicado con éxito.")
    else:
        print("AVISO: No se encontró patrón para parchear:", old[:40])

p.write_text(text, encoding="utf-8")
print("backend/routers/dataops.py actualizado con fuente_resolucion en todas las entidades.")
