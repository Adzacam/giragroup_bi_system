"""Contrato de estado del lote: CONSOLIDADO solo con hechos en el DW y 0 pendientes; 409 si se intenta mutar."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from routers import dataops as d


class _Q:
    def __init__(self, rows, n):
        self._rows, self._n = rows, n

    def filter(self, *_a, **_k):
        return self

    def all(self):
        return self._rows

    def count(self):
        return self._n


class _Db:
    def __init__(self, docs, pendientes):
        self._docs, self._pend = docs, pendientes

    def query(self, modelo):
        return _Q(self._docs, 0) if modelo is d.DimOrigenDocumental else _Q([], self._pend)


def _preparar(monkeypatch, hechos_dw, hechos_en_revision):
    monkeypatch.setattr(d, "_lote_tiene_hechos_dw", lambda db, ids: hechos_dw)
    monkeypatch.setattr(d, "contar_hechos_en_revision", lambda db, ids: hechos_en_revision)


DOCS = [SimpleNamespace(id_documento=1), SimpleNamespace(id_documento=2)]


def test_consolidado_sin_pendientes_devuelve_409(monkeypatch):
    _preparar(monkeypatch, hechos_dw=True, hechos_en_revision=0)
    with pytest.raises(HTTPException) as exc:
        d._asegurar_lote_editable(_Db(DOCS, 0), 1)
    assert exc.value.status_code == 409
    assert exc.value.detail["estado_flujo"] == "CONSOLIDADO"


@pytest.mark.parametrize("hechos_dw,hechos_rev,pend", [(True, 1, 0), (True, 0, 2), (False, 0, 0)])
def test_en_curso_permite_mutar(monkeypatch, hechos_dw, hechos_rev, pend):
    _preparar(monkeypatch, hechos_dw, hechos_rev)
    d._asegurar_lote_editable(_Db(DOCS, pend), 1)  # no lanza
    assert d._estado_flujo_lote(_Db(DOCS, pend), [1, 2], pend) == "EN_CURSO"


def test_sin_id_lote_no_valida(monkeypatch):
    _preparar(monkeypatch, True, 0)
    d._asegurar_lote_editable(_Db(DOCS, 0), None)


def test_endpoint_confirm_dw_insert_responde_409_sobre_lote_consolidado(monkeypatch):
    """Ruta real POST /api/v1/dataops/confirm-dw-insert (HTTP completo, auth y DB sustituidos): 409 serializado."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    _preparar(monkeypatch, hechos_dw=True, hechos_en_revision=0)
    app = FastAPI()
    app.include_router(d.router)
    app.dependency_overrides[d.get_current_user] = lambda: SimpleNamespace(role="ADMIN", username="qa", id=1)
    app.dependency_overrides[d.get_db] = lambda: _Db(DOCS, 0)

    for en_segundo_plano in (True, False):
        r = TestClient(app).post("/api/v1/dataops/confirm-dw-insert", json={"id_lote": 1, "en_segundo_plano": en_segundo_plano})
        assert r.status_code == 409
        assert r.json()["detail"]["estado_flujo"] == "CONSOLIDADO"
