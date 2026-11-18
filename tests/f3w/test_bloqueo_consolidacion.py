"""F3W (bloqueo en la línea 104.250): la consolidación del lote de 10 libros acumulaba en memoria todas las respuestas de
evaluación diferidas (715 mil) y sus trazas (1,6 millones) hasta finalizar_cargas(); el proceso de la API se quedaba sin
memoria a mitad de 'Experiencia Docente 2.0' y la tarea quedaba sin latido. Evidencia: docs/mediciones/f3w_bloqueo_consolidacion.json.

Las pruebas usan un doble de la base PostgreSQL que aplica las mismas reglas ON CONFLICT que los INSERT en bloque."""
from types import SimpleNamespace

import psycopg2.extras

from services import tareas_dataops
from services.dw_loader import DWLoaderService


class _Dialecto:
    name = "postgresql"


class _Resultado:
    def fetchall(self):
        return []  # carga_fila_origen vacía al empezar


class _BaseFalsa:
    """Doble de la sesión: solo lo que usan _reclamar_fila_origen y las escrituras en bloque."""

    def __init__(self):
        self.eval = {}       # clave_respuesta -> fila (ON CONFLICT DO UPDATE: gana la última)
        self.cfo = {}        # clave -> (doc, tabla)  (ON CONFLICT DO NOTHING: gana la primera)
        self.max_pendientes = 0

    def get_bind(self):
        return SimpleNamespace(dialect=_Dialecto())

    def execute(self, *_a, **_k):
        return _Resultado()

    def flush(self):
        pass

    def connection(self):
        cursor = SimpleNamespace(close=lambda: None, execute=lambda *_a: None, fetchone=lambda: (0,))  # MAX(id_hecho_eval)
        return SimpleNamespace(connection=SimpleNamespace(cursor=lambda: cursor))


def _execute_values_falso(base):
    def ejecutar(_cur, sql, filas, page_size=None, fetch=False):
        if "carga_fila_origen" in sql:
            for c, d, t in filas:
                base.cfo.setdefault(c, (d, t))
        elif "fact_evaluacion_docente" in sql:
            claves = [f[0] for f in filas]
            assert len(claves) == len(set(claves)), "una página no puede tocar dos veces la misma fila"
            for f in filas:
                base.eval[f[0]] = f
            if fetch:  # RETURNING clave_respuesta, id_hecho_eval (todas nuevas: id > MAX previo = 0)
                return [(f[0], 1 + list(base.eval).index(f[0])) for f in filas]
        else:
            raise AssertionError(f"INSERT inesperado: {sql[:60]}")
    return ejecutar


def _registro(i):
    """Una respuesta de encuesta (Experiencia Docente 2.0 como EVALUACION_DOCENTE); cada 7 filas repite contenido."""
    fila = i if i % 7 else i - 1
    return {
        "doc_id": None,
        "tipo_fuente": "EVALUACION_DOCENTE",
        "clave_origen": f"origen-{i}",
        "clave_contenido": f"contenido-{fila}",
        "resoluciones": {
            "estudiante": {}, "anonima": True,
            "docente": {"valor_extraido": "DOCENTE X"}, "modulo": {"valor_extraido": "POS-1-M01"},
            "puntuacion": (i % 5) + 1, "escala_max": 5, "pregunta_bloque": f"P{i % 13}", "tipo_pregunta": "DOCENTE",
            "clave_respuesta": f"resp-{i % 4000}", "fecha": "2025-03-01",
        },
        "calidad": {"requiere_revision": False},
    }


def _cargar(monkeypatch, n, limite=None):
    base = _BaseFalsa()
    monkeypatch.setattr(psycopg2.extras, "execute_values", _execute_values_falso(base))
    dw = DWLoaderService(base)
    dw.diferir_eval = True
    if limite is not None:
        dw.limite_eval_diferidas = limite
    latidos = []
    dw.al_latir = lambda: latidos.append(1)
    dw.resolver_o_crear_estudiante = lambda **k: (None, "C")
    dw.resolver_o_crear_tiempo = lambda f=None: 5
    dw.resolver_o_crear_modulo = lambda *a, **k: 7
    dw.resolver_o_crear_docente = lambda *a, **k: 3
    for i in range(n):
        res = dw.cargar_registro(_registro(i))
        assert res["status"] in ("loaded", "skipped")
        base.max_pendientes = max(base.max_pendientes, len(dw._eval_pendientes), len(dw._cfo_pendientes) // 2)
    dw.finalizar_cargas()
    return base, latidos


def test_memoria_acotada_durante_la_consolidacion(monkeypatch):
    """Antes: las 9.000 respuestas quedaban en memoria hasta el final. Después: nunca más de `limite_eval_diferidas`."""
    base, latidos = _cargar(monkeypatch, 9000, limite=1000)
    assert base.max_pendientes <= 1000
    assert latidos, "las escrituras en bloque deben dar señal de vida a la tarea"


def test_misma_huella_que_escribir_todo_al_final(monkeypatch):
    """Volcar por tramos no cambia qué se carga: mismas respuestas (gana la última por clave) y mismas trazas."""
    una_vez, _ = _cargar(monkeypatch, 9000, limite=10 ** 9)
    por_tramos, _ = _cargar(monkeypatch, 9000, limite=1000)
    assert una_vez.max_pendientes > 1000  # control: sin tope, todo queda en memoria hasta finalizar_cargas()
    assert por_tramos.eval == una_vez.eval
    assert por_tramos.cfo == una_vez.cfo
    assert len(una_vez.eval) == 4000


def test_latir_no_cambia_el_avance(monkeypatch):
    """El latido solo renueva actualizado_en (la regla de 180 s sin latido no corta una escritura en bloque larga)."""
    sentencias = []
    monkeypatch.setattr(tareas_dataops, "_ejecutar", lambda sql, p: sentencias.append((sql, p)))
    tareas_dataops._ultima_escritura.pop(99, None)
    tareas_dataops.latir(99)
    tareas_dataops.latir(99)  # dentro del mismo segundo: no escribe otra vez
    assert len(sentencias) == 1
    sql, params = sentencias[0]
    assert "actualizado_en" in sql and "procesados" not in sql and params == {"id": 99}
