"""Utilidades de las pruebas de la integración de BETO: catálogo de juguete, cliente con servicio simulado y extracción real por reglas."""
from types import SimpleNamespace

from routers.dataops.extraccion import _es_encabezado_no_estudiante, extract_entities_from_line
from services.beto_integracion import CacheMemoria, ClienteBeto, Contadores, EntidadBeto


def catalogo():
    estudiantes = [SimpleNamespace(id_estudiante=1, nombre_completo="Maria Lopez Quispe", ci_numero="4567890", ci=None,
                                   codigo_estudiante="4567890", programa_origen=None),
                   SimpleNamespace(id_estudiante=2, nombre_completo="Juan Carlos Mamani Flores", ci_numero="1234500", ci=None,
                                   codigo_estudiante="1234500", programa_origen=None)]
    docentes = [SimpleNamespace(id_docente=1, nombre_completo="Ing. Pedro Rojas Vargas", _contextos=[])]
    modulos = [SimpleNamespace(id_modulo=100, nombre_modulo="Gestion de Datos", pos_code="POS-1001", programa=None)]
    return estudiantes, docentes, modulos


def extraer_con(estudiantes, docentes, modulos, tipo_fuente="ACTA"):
    def extraer(linea, **kw):
        return extract_entities_from_line(linea, estudiantes, docentes, modulos, tipo_escala="CENTESIMAL_100", tipo_fuente=tipo_fuente, **kw)
    return extraer


class ServicioFalso:
    """Simula POST /infer-batch: por texto devuelve las entidades que se le indiquen (o ninguna)."""

    def __init__(self, por_texto=None, falla=False):
        self.por_texto, self.falla, self.llamadas = por_texto or {}, falla, []

    def __call__(self, lote):
        self.llamadas.append(list(lote))
        if self.falla:
            raise RuntimeError("servicio caído")
        return [self.por_texto.get(t, []) for t in lote]


def cliente(servicio, contadores=None):
    return ClienteBeto(cache=CacheMemoria(), post=servicio, configuracion="prueba", contadores=contadores or Contadores())


def ent(tipo, texto, linea, score=0.97):
    ini = linea.index(texto)
    return EntidadBeto(tipo, texto, ini, ini + len(texto), score)


EXCLUIR = _es_encabezado_no_estudiante
