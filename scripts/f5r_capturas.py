"""Capturas reales de CMI y DataOps en el navegador (Edge headless + CDP) para R-3.
Lee credenciales de F5R_EMAIL / F5R_PASS (sin hardcodear secretos).
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests
import websocket

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = os.getenv("F5R_BASE_URL", "http://127.0.0.1:80").rstrip("/")
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUT_DIR = ROOT / "output" / "f5r"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def login_data() -> dict:
    s = requests.Session()
    r1 = s.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": os.environ["F5R_EMAIL"], "password": os.environ["F5R_PASS"]},
        timeout=20,
    )
    r1.raise_for_status()
    d1 = r1.json()
    if not d1.get("mfa_required") and d1.get("access_token"):
        return d1
    logs = subprocess.check_output(
        ["docker", "logs", "--tail", "30", "giragroup_auth_svc"],
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    otps = re.findall(r"CÓDIGO OTP PARA [^:]+:\s*(\d{6})", logs)
    r2 = s.post(
        f"{BASE_URL}/api/v1/auth/verify-otp",
        json={"temp_token": d1["temp_token"], "code": otps[-1], "remember_device": False},
        timeout=20,
    )
    r2.raise_for_status()
    return r2.json()


class CdpClient:
    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=30)
        self.seq = 0

    def call(self, method: str, params: dict | None = None) -> dict:
        self.seq += 1
        cid = self.seq
        self.ws.send(json.dumps({"id": cid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == cid:
                if "error" in msg:
                    raise RuntimeError(f"CDP error en {method}: {msg['error']}")
                return msg.get("result", {})

    def close(self):
        self.ws.close()


def main() -> int:
    auth = login_data()
    token = auth["access_token"]
    user_obj = auth.get("user") or {"email": os.environ["F5R_EMAIL"], "role": "ADMIN", "username": "admin_general"}

    with tempfile.TemporaryDirectory() as tmp_profile:
        proc = subprocess.Popen(
            [
                EDGE_PATH,
                "--headless=new",
                "--disable-gpu",
                "--remote-debugging-port=9229",
                f"--user-data-dir={tmp_profile}",
                "--window-size=1440,900",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            ws_url = None
            for _ in range(30):
                try:
                    targets = requests.get("http://127.0.0.1:9229/json", timeout=2).json()
                    page = next((t for t in targets if t.get("type") == "page"), None)
                    if page:
                        ws_url = page["webSocketDebuggerUrl"]
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            if not ws_url:
                raise RuntimeError("No se pudo conectar a Edge CDP")

            cdp = CdpClient(ws_url)
            cdp.call("Page.enable")
            cdp.call("Runtime.enable")
            cdp.call("Emulation.setDeviceMetricsOverride", {
                "width": 1440, "height": 900, "deviceScaleFactor": 1, "mobile": False
            })

            # Cargar origen e inyectar sesión
            cdp.call("Page.navigate", {"url": f"{BASE_URL}/login"})
            time.sleep(2.0)
            js_auth = (
                f"localStorage.setItem('gira_token', {json.dumps(token)});"
                f"localStorage.setItem('gira_user', {json.dumps(json.dumps(user_obj))});"
                "localStorage.setItem('gira_theme', 'light');"
            )
            cdp.call("Runtime.evaluate", {"expression": js_auth})

            vistas = [
                ("/v2/cmi", OUT_DIR / "captura_cmi.png", 5.0),
                ("/v2/dataops/ingesta", OUT_DIR / "captura_dataops_ingesta.png", 4.0),
                ("/v2/dataops/lote/35/revision", OUT_DIR / "captura_dataops_revision.png", 5.0),
            ]
            for ruta, destino, espera in vistas:
                cdp.call("Page.navigate", {"url": f"{BASE_URL}{ruta}"})
                time.sleep(espera)
                shot = cdp.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                destino.write_bytes(base64.b64decode(shot["data"]))
                print(f"Captura guardada: {destino} ({destino.stat().st_size} bytes)", flush=True)

            cdp.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
    return 0


if __name__ == "__main__":
    sys.exit(main())
