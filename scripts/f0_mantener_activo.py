"""Inhibición temporal de suspensión automática durante una serie F0.

No modifica powercfg ni mantiene la pantalla encendida. La tapa, suspensión
manual y batería crítica siguen bajo control de Windows y del usuario.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "output/backups/f0_lote/energia"
STATE = ROOT / "docs/mediciones/f0_energia.json"
STOP = DIRECTORY / "STOP"
LEASE = DIRECTORY / "driver.json"
SYSTEM_REQUIRED = 0x00000001
CONTINUOUS = 0x80000000
SOURCE = "https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate"


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def alive(pid):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes, kernel.CloseHandle.restype = [wintypes.HANDLE], wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
    finally:
        kernel.CloseHandle(handle)


class ExecutionState:
    def __init__(self, setter=None):
        if setter is None:
            setter = ctypes.WinDLL("kernel32", use_last_error=True).SetThreadExecutionState
            setter.argtypes, setter.restype = [wintypes.DWORD], wintypes.DWORD
        self.setter = setter
        self.thread = threading.get_ident()
        self.previous = None

    def refresh(self):
        if threading.get_ident() != self.thread:
            raise RuntimeError("La protección debe usar la misma hebra")
        previous = self.setter(CONTINUOUS | SYSTEM_REQUIRED)
        if not previous:
            raise OSError("SetThreadExecutionState devolvió NULL")
        self.previous = previous
        return previous

    def __enter__(self):
        self.refresh()
        return self

    def __exit__(self, *_):
        if threading.get_ident() != self.thread or not self.setter(CONTINUOUS):
            raise OSError("No se confirmó limpieza de SetThreadExecutionState en la hebra original")


def check():
    if os.name != "nt":
        return {"estado": "no_aplica_windows", "sistema": os.name}
    value = json.loads(STATE.read_text(encoding="utf-8"))
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(value["latido"])).total_seconds()
    if value.get("estado") != "activo" or not value.get("retorno_api") or age > 20 or not alive(value["pid"]):
        raise RuntimeError("Auxiliar de energía no está vivo/verificado; no iniciar reloj")
    return {"pid": value["pid"], "latido": value["latido"], "retorno_api": value["retorno_api"],
            "flags": "ES_CONTINUOUS|ES_SYSTEM_REQUIRED", "pantalla_requerida": False}


def bind_driver():
    check()
    write(LEASE, {"pid": os.getpid(), "fecha": now()})


def request_stop():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    STOP.write_text(now() + "\n", encoding="utf-8")


def hold():
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    STOP.unlink(missing_ok=True)
    LEASE.unlink(missing_ok=True)
    status = {"pid": os.getpid(), "hebra": threading.get_ident(), "inicio": now(), "fuente": SOURCE,
              "flags": "ES_CONTINUOUS|ES_SYSTEM_REQUIRED", "pantalla_requerida": False,
              "configuracion_permanente_modificada": False,
              "limite": "No impide suspensión manual, tapa o batería crítica"}
    try:
        with ExecutionState() as protection:
            while not STOP.exists():
                if LEASE.exists() and not alive(json.loads(LEASE.read_text(encoding="utf-8"))["pid"]):
                    break
                status.update({"estado": "activo", "latido": now(), "retorno_api": protection.refresh()})
                write(STATE, status)
                time.sleep(5)
        status.update({"estado": "limpiado", "fin": now(), "limpieza": "ES_CONTINUOUS en la misma hebra"})
    except Exception as error:
        status.update({"estado": "fallo", "fin": now(), "error": type(error).__name__})
        raise
    finally:
        write(STATE, status)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comprobar", action="store_true")
    parser.add_argument("--detener", action="store_true")
    args = parser.parse_args()
    if args.comprobar:
        print(json.dumps(check()))
    elif args.detener:
        request_stop()
    else:
        hold()
