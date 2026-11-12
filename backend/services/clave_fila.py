"""Clave de una fila de origen por su contenido, para no sumar dos veces la misma fila cuando el archivo se vuelve a exportar.

La clave por archivo (huella del archivo, hoja y posición) solo protege frente a un archivo byte a byte idéntico. Esta clave usa
el tipo de fuente, la hoja y el texto de la fila, más el número de ocurrencia dentro de la hoja para que dos filas realmente
iguales de un mismo archivo sigan contando como dos.
"""
import hashlib
from collections import Counter


class ContadorOcurrencias:
    def __init__(self):
        self._vistas = Counter()

    def siguiente(self, hoja, linea) -> int:
        clave = (hoja, linea)
        n = self._vistas[clave]
        self._vistas[clave] += 1
        return n


def clave_contenido(tipo_fuente, hoja, linea, ocurrencia=0) -> str:
    return hashlib.sha256(f"contenido|{tipo_fuente}|{hoja}|{linea}|{ocurrencia}".encode("utf-8")).hexdigest()
