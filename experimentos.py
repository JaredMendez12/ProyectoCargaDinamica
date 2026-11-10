#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
experimentos.py - Corre balanceo.py con distintos escenarios y guarda
los resultados (mediana de varias repeticiones) en resultados/*.json.

    python experimentos.py                 # todos los experimentos
    python experimentos.py --exp chunk     # solo uno
    python experimentos.py --reps 5        # más repeticiones (menos ruido)

Escenarios:
    homogeneo      4 nodos iguales, tareas de costo variable
    heterogeneo    nodos con velocidades 1, 1, 0.5, 0.25
    chunk          tamaño del paquete vs. latencia de red (compromiso)
    escalabilidad  1, 2, 4 y 8 trabajadores
    degradado      un nodo se vuelve lento a mitad de la ejecución
    gantt          una corrida guardando intervalos (línea de tiempo)
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "resultados")
HETERO = "1,1,0.5,0.25"


def lanzador():
    exe = shutil.which("mpiexec") or shutil.which("mpirun")
    if not exe:
        sys.exit("No encuentro mpiexec/mpirun. Instala MPICH u OpenMPI (o MS-MPI en Windows).")
    return exe


def correr(estrategia, trabajadores, velocidades, reps, extra=(), chunk=1):
    """Ejecuta una configuración `reps` veces y devuelve la corrida mediana."""
    corridas = []
    for r in range(reps):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            ruta = tmp.name
        cmd = [lanzador(), "-n", str(trabajadores + 1), sys.executable,
               os.path.join(AQUI, "balanceo.py"),
               "--estrategia", estrategia, "--chunk", str(chunk),
               "--velocidades", velocidades, "--salida", ruta, *extra]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        with open(ruta, encoding="utf-8") as f:
            corridas.append(json.load(f))
        os.remove(ruta)
    corridas.sort(key=lambda c: c["makespan"])
    mediana = corridas[len(corridas) // 2]
    mediana["makespans"] = [c["makespan"] for c in corridas]
    mediana["makespan_mediana"] = statistics.median(mediana["makespans"])
    return mediana


def guardar(nombre, datos):
    os.makedirs(SALIDA, exist_ok=True)
    with open(os.path.join(SALIDA, nombre + ".json"), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    print(f"  -> resultados/{nombre}.json")


def etiqueta(est, chunk):
    return f"{est} (chunk={chunk})" if est in ("dinamico", "guiado") else est


def exp_comparacion(nombre, velocidades, reps, extra=(), incluir_ponderado=False):
    print(f"[{nombre}] velocidades={velocidades}")
    configs = [("estatico", 1), ("estatico_ciclico", 1)]
    if incluir_ponderado:
        configs.append(("estatico_ponderado", 1))
    configs += [("dinamico", 1), ("dinamico", 4), ("guiado", 1)]
    n_trab = len(velocidades.split(","))
    datos = []
    for est, chunk in configs:
        d = correr(est, n_trab, velocidades, reps, extra, chunk)
        print(f"  {etiqueta(est, chunk):28s} {d['makespan_mediana']:.3f} s")
        datos.append(d)
    guardar(nombre, datos)


def exp_chunk(reps):
    print("[chunk] latencia de red simulada = 3 ms por petición")
    extra = ("--latencia-ms", "3")
    datos = []
    for chunk in (1, 2, 4, 8, 16, 32, 60):
        d = correr("dinamico", 4, HETERO, reps, extra, chunk)
        print(f"  dinamico chunk={chunk:<3d} {d['makespan_mediana']:.3f} s  "
              f"paquetes={d['paquetes']}")
        datos.append(d)
    d = correr("guiado", 4, HETERO, reps, extra, 1)
    print(f"  guiado               {d['makespan_mediana']:.3f} s  paquetes={d['paquetes']}")
    datos.append(d)
    d = correr("estatico_ponderado", 4, HETERO, reps, extra, 1)
    print(f"  estatico_ponderado   {d['makespan_mediana']:.3f} s")
    datos.append(d)
    guardar("chunk", datos)


def exp_escalabilidad(reps):
    print("[escalabilidad] 480 tareas, velocidades en ciclo 1,1,0.5,0.25")
    datos = []
    for w in (1, 2, 4, 8):
        for est, chunk in (("estatico", 1), ("dinamico", 4), ("guiado", 1)):
            d = correr(est, w, HETERO, reps, ("--tareas", "480"), chunk)
            print(f"  W={w} {etiqueta(est, chunk):22s} {d['makespan_mediana']:.3f} s  "
                  f"speedup={d['t_1_nodo'] / d['makespan_mediana']:.2f}")
            datos.append(d)
    guardar("escalabilidad", datos)


def exp_degradado(reps):
    print("[degradado] 4 nodos iguales; el rank 4 baja a velocidad 0.25 a los 0.3 s")
    extra = ("--degradar", "4:0.3:0.25")
    datos = []
    for est, chunk in (("estatico", 1), ("estatico_ciclico", 1),
                       ("dinamico", 4), ("guiado", 1)):
        d = correr(est, 4, "1,1,1,1", reps, extra, chunk)
        print(f"  {etiqueta(est, chunk):28s} {d['makespan_mediana']:.3f} s")
        datos.append(d)
    guardar("degradado", datos)


def exp_gantt():
    print("[gantt] corridas con intervalos guardados (heterogéneo)")
    for est, chunk in (("estatico", 1), ("dinamico", 4), ("guiado", 1)):
        d = correr(est, 4, HETERO, 1, ("--guardar-intervalos",), chunk)
        guardar(f"gantt_{est}", d)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exp", default="todos",
                   choices=["todos", "homogeneo", "heterogeneo", "chunk",
                            "escalabilidad", "degradado", "gantt"])
    p.add_argument("--reps", type=int, default=3)
    a = p.parse_args()
    t = a.exp
    if t in ("todos", "homogeneo"):
        exp_comparacion("homogeneo", "1,1,1,1", a.reps)
    if t in ("todos", "heterogeneo"):
        exp_comparacion("heterogeneo", HETERO, a.reps, incluir_ponderado=True)
    if t in ("todos", "chunk"):
        exp_chunk(a.reps)
    if t in ("todos", "escalabilidad"):
        exp_escalabilidad(a.reps)
    if t in ("todos", "degradado"):
        exp_degradado(a.reps)
    if t in ("todos", "gantt"):
        exp_gantt()


if __name__ == "__main__":
    main()
