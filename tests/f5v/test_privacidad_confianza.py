"""F5V V-7: registro_beto_publico conserva confianza/origen_confianza/detalleConfianza y enmascara datos personales."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from services.dataops_privacy import registro_beto_publico  # noqa: E402


def test_registro_beto_publico_expone_origen_y_enmascara_pii():
    reg = {
        "id": 1,
        "estudiante": "Maria Lopez Quispe",
        "ci": "4567890",
        "correo": "maria.lopez@ejemplo.com",
        "modulo": "Gestion de Datos",
        "indice_registro": 88.0,
        "estado": "AUTOMATICO",
        "lectura": {
            "texto": "ESTUDIANTE: Maria Lopez Quispe | CI: 4567890 | DOCENTE: Ing. Pedro Rojas",
            "entidades": [
                {
                    "label": "ESTUDIANTE",
                    "token": "Maria Lopez Quispe",
                    "confianza": 0.73,
                    "origen_confianza": "BETO",
                    "lecturaModelo": 0.73,
                    "betoConfidence": 0.73,
                    "detalleConfianza": {"probabilidad": 0.73},
                },
                {
                    "label": "PROGRAMA",
                    "token": "DIPLOMADO EN DATOS",
                    "confianza": 0.96,
                    "origen_confianza": "REGLA_ENCABEZADO",
                    "detalleConfianza": {"similitudEncabezado": 0.96, "validez": 1.0},
                },
            ],
        },
    }
    pub = registro_beto_publico(reg)
    ents = pub["lectura"]["entidades"]
    est, prog = ents[0], ents[1]
    assert est["origen_confianza"] == "BETO"
    assert est["confianza"] == 0.73
    assert "Maria" not in str(est["token"])
    assert "4567890" not in str(pub)
    assert "maria.lopez@ejemplo.com" not in str(pub)
    assert prog["origen_confianza"] == "REGLA_ENCABEZADO"
    assert prog["confianza"] == 0.96
    assert prog["detalleConfianza"]["similitudEncabezado"] == 0.96
