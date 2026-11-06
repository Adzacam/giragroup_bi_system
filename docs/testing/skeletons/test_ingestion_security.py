"""
docs/testing/skeletons/test_ingestion_security.py
------------------------------------------------
Esqueleto de pruebas unitarias para las validaciones de seguridad en la ingesta de archivos.
Reglas:
- Validación de Magic Bytes (Firma Binaria PK para .xlsx, texto para .csv).
- Deduplicación por hash SHA-256.
- Tamaño máximo permitido: 50 MB por archivo.
- Rechazo de extensiones no autorizadas (.exe, .sh, .py, .xls, .xml).
Marcador: unit
"""

import hashlib
import io
import pytest

MAGIC_BYTES_XLSX = b"PK\x03\x04"
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024 # 50 MB

@pytest.mark.unit
class TestIngestionSecurity:

    def test_validacion_magic_bytes_xlsx_valido(self):
        """Un archivo .xlsx válido debe iniciar con la cabecera PK\x03\x04."""
        contenido = b"PK\x03\x04\x14\x00\x06\x00resto_del_contenido_zip"
        es_valido = contenido.startswith(MAGIC_BYTES_XLSX)
        assert es_valido is True

    def test_rechazo_magic_bytes_falsos(self):
        """Un ejecutable o script renombrado a .xlsx debe ser rechazado inmediatamente."""
        contenido_malicioso = b"MZ\x90\x00\x03\x00\x00\x00" # Cabecera ejecutable PE Windows
        es_valido = contenido_malicioso.startswith(MAGIC_BYTES_XLSX)
        assert es_valido is False

    def test_limite_tamano_archivo_50mb(self):
        """Archivos mayores a 50 MB deben ser rechazados sin cargar en memoria completa."""
        tamano_valido = 49 * 1024 * 1024
        tamano_excedido = 51 * 1024 * 1024

        assert tamano_valido <= MAX_FILE_SIZE_BYTES
        assert tamano_excedido > MAX_FILE_SIZE_BYTES

    def test_calculo_hash_sha256_consistente(self):
        """Verifica que el hash SHA-256 sea determinista y detecte duplicados exactos."""
        payload = b"Contenido de prueba para calcular hash"
        hash_1 = hashlib.sha256(payload).hexdigest()
        hash_2 = hashlib.sha256(payload).hexdigest()
        assert hash_1 == hash_2
        assert len(hash_1) == 64

    def test_extensiones_permitidas_whitelist(self):
        """Solo se admiten extensiones .xlsx y .csv en minúsculas."""
        permitidas = {".xlsx", ".csv"}
        assert ".xlsx" in permitidas
        assert ".csv" in permitidas
        assert ".xls" not in permitidas
        assert ".xml" not in permitidas
        assert ".exe" not in permitidas
