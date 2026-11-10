#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""servidor_demo.py - Demo en vivo: una página web que ejecuta balanceo.py con MPI de verdad.

    python servidor_demo.py            (abre http://127.0.0.1:8765 en el navegador)

La página manda los parámetros de cada paso; este servidor lanza
    mpiexec -n N python balanceo.py ...        (sin shell, parámetros validados)
y devuelve la salida de la terminal y los intervalos reales de cada nodo para animarlos.
Solo escucha en 127.0.0.1 (tu propia laptop). Ctrl+C para detenerlo.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.abspath(__file__))
PUERTO = int(os.environ.get("PUERTO_DEMO", "8765"))
ESTRATEGIAS = {"estatico", "estatico_ciclico", "estatico_ponderado", "dinamico", "guiado"}
MPIEXEC = shutil.which("mpiexec") or shutil.which("mpiexec.exe") or shutil.which("mpirun")
CANDADO = threading.Lock()          # una ejecución a la vez (para medir bien los tiempos)
RE_DEGRADAR = re.compile(r"^\d{1,2}:\d{1,3}(\.\d+)?:\d{1,2}(\.\d+)?$")


def numero(valor, minimo, maximo, nombre):
    x = float(valor)
    if not (minimo <= x <= maximo):
        raise ValueError(f"{nombre} fuera de rango ({minimo} a {maximo})")
    return x


def correr(cmd, timeout):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run(cmd, cwd=RAIZ, capture_output=True, timeout=timeout, env=env)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def con_mpi(args_python, n, timeout):
    """Ejecuta mpiexec -n N python <args>. Reintenta con --oversubscribe (Open MPI)."""
    if not MPIEXEC:
        raise RuntimeError("No encuentro mpiexec en el PATH. Instala MS-MPI (Windows) o MPICH/Open MPI.")
    base = [MPIEXEC, "-n", str(n), sys.executable] + args_python
    codigo, salida, error = correr(base, timeout)
    if codigo != 0 and "slots" in (error + salida).lower():
        base = [MPIEXEC, "--oversubscribe", "-n", str(n), sys.executable] + args_python
        codigo, salida, error = correr(base, timeout)
    return codigo, salida, error, base


def ejecutar_balanceo(p):
    estrategia = str(p.get("estrategia", "dinamico"))
    if estrategia not in ESTRATEGIAS:
        raise ValueError("estrategia no válida")
    vel = [numero(v, 0.05, 4, "velocidad") for v in str(p.get("velocidades", "1,1,0.5,0.25")).split(",")]
    if not (1 <= len(vel) <= 8):
        raise ValueError("de 1 a 8 trabajadores")
    chunk = int(numero(p.get("chunk", 4), 1, 1000, "chunk"))
    lat = numero(p.get("latencia_ms", 0), 0, 200, "latencia")
    tareas = int(numero(p.get("tareas", 240), 20, 2000, "tareas"))
    degradar = str(p.get("degradar", "") or "")
    if degradar and not RE_DEGRADAR.match(degradar):
        raise ValueError("degradar debe ser rank:segundos:velocidad")
    vel_txt = ",".join(f"{v:g}" for v in vel)

    with tempfile.TemporaryDirectory() as tmp:
        salida_json = os.path.join(tmp, "resultado.json")
        args = ["balanceo.py", "--estrategia", estrategia, "--chunk", str(chunk),
                "--velocidades", vel_txt, "--latencia-ms", f"{lat:g}", "--tareas", str(tareas),
                "--guardar-intervalos", "--salida", salida_json]
        if degradar:
            args += ["--degradar", degradar]
        codigo, salida, error, cmd = con_mpi(args, len(vel) + 1, 120)
        if codigo != 0 or not os.path.exists(salida_json):
            raise RuntimeError((error or salida or "mpiexec terminó con error").strip()[-1500:])
        with open(salida_json, encoding="utf-8") as f:
            resultado = json.load(f)
    return {"ok": True, "salida": salida, "resultado": resultado}


def ejecutar_diagnostico(_p):
    codigo, salida, error, cmd = con_mpi(["cluster_diagnostico.py", "--pings", "100"], 3, 120)
    if codigo != 0:
        raise RuntimeError((error or salida).strip()[-1500:])
    return {"ok": True, "salida": salida}


class Manejador(BaseHTTPRequestHandler):
    def _enviar(self, codigo, cuerpo, tipo="application/json; charset=utf-8"):
        datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(datos)

    def _local(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self._local():
            return self._enviar(403, {"ok": False, "error": "solo localhost"})
        if self.path in ("/", "/index.html"):
            with open(os.path.join(RAIZ, "demo", "index.html"), "rb") as f:
                return self._enviar(200, f.read(), "text/html; charset=utf-8")
        if self.path == "/favicon.ico":
            return self._enviar(204, b"", "image/x-icon")
        if self.path == "/api/estado":
            return self._enviar(200, {"ok": True, "mpiexec": MPIEXEC, "python": sys.executable,
                                      "version": sys.version.split()[0]})
        self._enviar(404, {"ok": False, "error": "no existe"})

    def do_POST(self):
        if not self._local() or self.path not in ("/api/ejecutar", "/api/diagnostico"):
            return self._enviar(403, {"ok": False, "error": "no permitido"})
        try:
            largo = min(int(self.headers.get("Content-Length") or 0), 10000)
            datos = json.loads(self.rfile.read(largo) or b"{}")
            with CANDADO:
                if self.path == "/api/diagnostico":
                    r = ejecutar_diagnostico(datos)
                else:
                    r = ejecutar_balanceo(datos)
            self._enviar(200, r)
        except subprocess.TimeoutExpired:
            self._enviar(200, {"ok": False, "error": "Tiempo agotado: mpiexec tardó más de 2 minutos."})
        except Exception as e:                               # noqa: BLE001
            self._enviar(200, {"ok": False, "error": str(e)})

    def log_message(self, fmt, *a):
        sys.stderr.write("  " + (fmt % a) + "\n")


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    url = f"http://127.0.0.1:{PUERTO}"
    print(f"Demo en vivo en {url}   (Ctrl+C para salir)")
    print("mpiexec:", MPIEXEC or "NO ENCONTRADO")
    try:
        webbrowser.open(url)
    except Exception:                                         # noqa: BLE001
        pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")


if __name__ == "__main__":
    main()
