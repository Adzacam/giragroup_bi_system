"""
conftest.py
-----------
Configuración global de Pytest para asegurar que el directorio raíz
esté en sys.path durante la recolección y ejecución de pruebas.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
