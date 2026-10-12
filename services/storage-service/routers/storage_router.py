"""
services/storage-service/routers/storage_router.py
--------------------------------------------------
Router de gestión y carga de archivos heterogéneos.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List, Dict, Any
import hashlib
import os

router = APIRouter(prefix="/api/v1/storage", tags=["File Storage"])
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    tipo_fuente: str = Form(None)
) -> Dict[str, Any]:
    contents = await file.read()
    file_hash = hashlib.sha256(contents).hexdigest()
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as f:
        f.write(contents)
        
    return {
        "filename": file.filename,
        "size_bytes": len(contents),
        "sha256": file_hash,
        "tipo_fuente": tipo_fuente or "AUTO_DETECTED",
        "status": "STORED",
        "path": file_path
    }

@router.get("/files")
def list_files() -> List[Dict[str, Any]]:
    files = []
    if os.path.exists(UPLOAD_DIR):
        for fname in os.listdir(UPLOAD_DIR):
            fpath = os.path.join(UPLOAD_DIR, fname)
            if os.path.isfile(fpath):
                files.append({
                    "filename": fname,
                    "size_bytes": os.path.getsize(fpath)
                })
    return files
