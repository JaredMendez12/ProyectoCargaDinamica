#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cluster_diagnostico.py - Diagnostico de un cluster de laptops en red local (mpi4py).

Para cada nodo (proceso MPI) mide lo que necesita el balanceo de carga:
  * nombre de host y direccion IP         -> comprobar que MPI llego a cada laptop
  * latencia de ida y vuelta (RTT) al maestro -> decide el tamano del paquete
  * velocidad relativa v (1.0 = el mas rapido) -> alimenta --velocidades
  * si hay GPU NVIDIA (nvidia-smi)         -> informativo (CPU/GPU)

Uso (una laptop):
    mpiexec -n 3 python cluster_diagnostico.py
Uso (cluster; hosts.txt con una IP por linea, ver cluster/hosts.txt.ejemplo):
    mpiexec -f cluster/hosts.txt -n 4 python cluster_diagnostico.py
Windows (MS-MPI):
    mpiexec -hosts 4 192.168.1.10 1 192.168.1.11 1 192.168.1.12 1 192.168.1.13 1 python cluster_diagnostico.py
"""
import argparse
import math
import shutil
import socket
import statistics
import time

from mpi4py import MPI


def ip_local():
    """IP de la interfaz que usaria para salir a la red (no envia paquetes)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return socket.gethostbyname(socket.gethostname())
    finally:
        s.close()


def trabajo_cpu(n):
    """Carga fija: cuenta primos hasta n (mismo trabajo en todos los nodos)."""
    cuenta = 0
    for k in range(2, n):
        for d in range(2, int(math.isqrt(k)) + 1):
            if k % d == 0:
                break
        else:
            cuenta += 1
    return cuenta


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pings", type=int, default=200, help="ida y vuelta por nodo")
    ap.add_argument("--n-primos", type=int, default=60000, help="tamano del benchmark")
    ap.add_argument("--costo-medio-ms", type=float, default=10.0,
                    help="costo medio de una tarea (para sugerir el paquete)")
    args = ap.parse_args()

    comm = MPI.COMM_WORLD
    rank, size = comm.Get_rank(), comm.Get_size()

    # 1) latencia: rank 0 hace ping-pong con cada trabajador
    rtt = {}
    for w in range(1, size):
        comm.Barrier()
        if rank == 0:
            muestras = []
            for _ in range(args.pings):
                t0 = time.perf_counter()
                comm.send(b"x", dest=w, tag=1)
                comm.recv(source=w, tag=2)
                muestras.append((time.perf_counter() - t0) * 1000)
            rtt[w] = statistics.median(muestras)
        elif rank == w:
            for _ in range(args.pings):
                comm.recv(source=0, tag=1)
                comm.send(b"x", dest=0, tag=2)

    # 2) velocidad: todos hacen el mismo trabajo y se compara el tiempo
    trabajo_cpu(2000)                      # calentamiento
    comm.Barrier()
    t0 = time.perf_counter()
    trabajo_cpu(args.n_primos)
    t_cpu = time.perf_counter() - t0

    info = (rank, socket.gethostname(), ip_local(), t_cpu,
            shutil.which("nvidia-smi") is not None)
    todos = comm.gather(info, root=0)

    if rank == 0:
        t_min = min(t[3] for t in todos if t[0] != 0) if size > 1 else todos[0][3]
        print(f"{'rank':>4}  {'host':<16} {'IP':<15} {'RTT ms':>7} {'t cpu s':>8} {'v':>5}  GPU")
        vs = []
        for r, host, ip, t, gpu in todos:
            v = t_min / t
            etiqueta = "maestro" if r == 0 else ""
            lat = "-" if r == 0 else f"{rtt[r]:.3f}"
            print(f"{r:>4}  {host:<16} {ip:<15} {lat:>7} {t:>8.3f} {min(v, 1.0):>5.2f}  "
                  f"{'si' if gpu else 'no'} {etiqueta}")
            if r != 0:
                vs.append(min(v, 1.0))
        if vs:
            L = max(rtt.values()) / 2                  # latencia de un sentido (ms)
            k = max(1, math.ceil(18 * L * max(vs) / args.costo_medio_ms))
            print("\nVelocidades para --velocidades :", ",".join(f"{v:.2f}" for v in vs))
            print(f"Latencia de un sentido L = {L:.3f} ms")
            print(f"Paquete sugerido (sobrecosto <= 10 %): k >= 18*L*v/c = {k} tareas "
                  f"(c = {args.costo_medio_ms:g} ms)")


if __name__ == "__main__":
    main()
