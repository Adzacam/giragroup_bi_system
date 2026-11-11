"""
backend/routers/powerbi.py
--------------------------
Acceso al informe de Power BI Desktop del CMI (migración 007).

Sin Power BI Service (sin licencia Pro) el informe se distribuye como archivo .pbix:
- ADMIN: descarga, sube nuevas versiones y puede restaurar una anterior.
- LECTORES: sólo descargan la versión vigente para consultarla en Desktop.
Desktop no tiene modo de sólo lectura; la protección real está en los datos: el informe se
conecta con el rol powerbi_reader, de sólo lectura sobre el esquema bi y sin PII.
"""

import hashlib
import os
import re
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import require_roles
from models.user import User

router = APIRouter(prefix="/api/v1/powerbi", tags=["Power BI"])

EDITORES = ["ADMIN"]
LECTORES = ["ADMIN", "ANALISTA_MARKETING"]
MAX_BYTES = 150 * 1024 * 1024  # igual que client_max_body_size del gateway
DIR_INFORMES = Path(os.environ.get("POWERBI_DIR", Path(__file__).resolve().parents[1] / "uploads" / "powerbi"))
NOMBRE_BASE = "giragroup_cmi"
# Versiones que se conservan en disco (la vigente siempre se conserva); las más antiguas se eliminan al publicar
MAX_VERSIONES = max(1, int(os.environ.get("POWERBI_MAX_VERSIONES", "3")))

CONEXION = {
    "servidor": f"{os.environ.get('POWERBI_DB_HOST', '127.0.0.1')}:{os.environ.get('POWERBI_DB_PORT', '5434')}",
    "base_datos": os.environ.get("POWERBI_DB_NAME", "giragroup_db"),
    "usuario": "powerbi_reader",
    "esquema": "bi",
}

_COLS = "version, nombre_archivo, tamano_bytes, sha256, nota, vigente, subido_por, subido_en"


def _fila(r) -> dict:
    d = dict(r._mapping)
    d["subido_en"] = d["subido_en"].isoformat()
    return d


def _version(db: Session, version: Optional[int]):
    if version is None:
        q, p = "WHERE vigente", {}
    else:
        q, p = "WHERE version = :v", {"v": version}
    return db.execute(text(f"SELECT {_COLS}, ruta FROM public.powerbi_informe_version {q}"), p).first()


def _aplicar_retencion(db: Session, max_versiones: int = MAX_VERSIONES) -> int:
    """Elimina archivo y registro de las versiones que exceden la retención. Nunca toca la vigente."""
    filas = db.execute(text("SELECT version, ruta, vigente FROM public.powerbi_informe_version ORDER BY version DESC")).all()
    conservar = {f.version for f in filas[:max_versiones]} | {f.version for f in filas if f.vigente}
    eliminadas = 0
    for f in filas:
        if f.version in conservar:
            continue
        Path(f.ruta).unlink(missing_ok=True)
        db.execute(text("DELETE FROM public.powerbi_informe_version WHERE version = :v"), {"v": f.version})
        eliminadas += 1
    return eliminadas


@router.get("/informe")
def get_informe(db: Session = Depends(get_db), user: User = Depends(require_roles(LECTORES))):
    r = _version(db, None)
    vigente = None
    if r:
        vigente = _fila(r)
        vigente.pop("ruta")
    return {"vigente": vigente, "conexion": CONEXION, "puede_editar": user.role in EDITORES,
            "max_versiones": MAX_VERSIONES}


@router.get("/informe/descargar")
def descargar(version: Optional[int] = Query(None, ge=1), db: Session = Depends(get_db),
              user: User = Depends(require_roles(LECTORES))):
    if version is not None and user.role not in EDITORES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sólo el administrador descarga versiones anteriores.")
    r = _version(db, version)
    if not r or not Path(r.ruta).is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay un informe de Power BI disponible.")
    return FileResponse(r.ruta, media_type="application/octet-stream",
                        filename=f"{NOMBRE_BASE}_v{r.version}.pbix")


@router.get("/informe/versiones")
def versiones(db: Session = Depends(get_db), _: User = Depends(require_roles(EDITORES))):
    rows = db.execute(text(f"SELECT {_COLS} FROM public.powerbi_informe_version ORDER BY version DESC")).all()
    return [_fila(r) for r in rows]


def _validar_pbix(ruta: Path) -> None:
    """Un .pbix es un ZIP con DataModel y la definición del informe; rechaza cualquier otro archivo."""
    try:
        with zipfile.ZipFile(ruta) as z:
            nombres = set(z.namelist())
    except zipfile.BadZipFile:
        nombres = set()
    tiene_informe = "Report/Layout" in nombres or any(n.startswith("Report/definition/") for n in nombres)
    if "DataModel" not in nombres or not tiene_informe:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "El archivo no es un informe de Power BI Desktop (.pbix) válido.")


@router.post("/informe", status_code=status.HTTP_201_CREATED)
async def subir(archivo: UploadFile = File(...), nota: Optional[str] = Form(None, max_length=300),
                db: Session = Depends(get_db), user: User = Depends(require_roles(EDITORES))):
    if not (archivo.filename or "").lower().endswith(".pbix"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Sube un archivo .pbix.")
    DIR_INFORMES.mkdir(parents=True, exist_ok=True)
    tmp = DIR_INFORMES / f".subida_{user.id}.tmp"
    sha, total = hashlib.sha256(), 0
    try:
        with tmp.open("wb") as f:
            while chunk := await archivo.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "El archivo supera 150 MB.")
                sha.update(chunk)
                f.write(chunk)
        if total == 0:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El archivo está vacío.")
        _validar_pbix(tmp)
        digest = sha.hexdigest()
        actual = _version(db, None)
        if actual and actual.sha256 == digest:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Es idéntico a la versión vigente (v{actual.version}).")

        # Bloqueo para que dos subidas simultáneas no tomen el mismo número de versión
        db.execute(text("LOCK TABLE public.powerbi_informe_version IN SHARE ROW EXCLUSIVE MODE"))
        nueva = db.execute(text("SELECT COALESCE(MAX(version), 0) + 1 FROM public.powerbi_informe_version")).scalar()
        destino = DIR_INFORMES / f"{NOMBRE_BASE}_v{nueva}.pbix"
        tmp.replace(destino)
        db.execute(text("UPDATE public.powerbi_informe_version SET vigente = FALSE WHERE vigente"))
        db.execute(text("""
            INSERT INTO public.powerbi_informe_version
                (version, nombre_archivo, ruta, tamano_bytes, sha256, nota, vigente, subido_por)
            VALUES (:v, :n, :r, :t, :s, :nota, TRUE, :u)"""),
            {"v": nueva, "n": re.sub(r"[^\w.\- ]", "_", archivo.filename)[:255], "r": str(destino),
             "t": total, "s": digest, "nota": (nota or "").strip() or None, "u": user.username})
        _aplicar_retencion(db)
        db.commit()
    except Exception:
        db.rollback()
        tmp.unlink(missing_ok=True)
        raise
    out = _fila(_version(db, None))
    out.pop("ruta")
    return out


@router.put("/informe/versiones/{version}/vigente")
def restaurar(version: int, db: Session = Depends(get_db), _: User = Depends(require_roles(EDITORES))):
    r = _version(db, version)
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No existe la versión {version}.")
    if not Path(r.ruta).is_file():
        raise HTTPException(status.HTTP_409_CONFLICT, f"El archivo de la versión {version} ya no está en el servidor.")
    db.execute(text("UPDATE public.powerbi_informe_version SET vigente = FALSE WHERE vigente"))
    db.execute(text("UPDATE public.powerbi_informe_version SET vigente = TRUE WHERE version = :v"), {"v": version})
    db.commit()
    out = _fila(_version(db, None))
    out.pop("ruta")
    return out
