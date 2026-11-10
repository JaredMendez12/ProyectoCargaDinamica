#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
balanceo.py - Balanceo de carga ESTÁTICO vs DINÁMICO con arquitectura
Maestro-Trabajador, usando mpi4py.

Idea: un "nodo" es un proceso MPI. Como en una laptop todos los procesos
tienen la misma velocidad, se SIMULAN nodos lentos y rápidos: cada trabajador
tiene un factor de velocidad (1.0 = rápido, 0.5 = mitad de velocidad, ...) y
tarda  costo / velocidad  en ejecutar una tarea.

    rank 0      -> MAESTRO   (reparte paquetes de trabajo, no calcula)
    rank 1..n-1 -> TRABAJADORES (los "nodos" heterogéneos)

Estrategias (--estrategia):
    estatico            bloques contiguos del mismo tamaño (decidido de antemano)
    estatico_ciclico    tarea i -> trabajador i % W (round-robin, de antemano)
    estatico_ponderado  bloques proporcionales a la velocidad CONOCIDA de cada nodo
    dinamico            el trabajador pide un paquete de --chunk tareas cuando se desocupa
    guiado              dinámico con paquetes que se encogen: restantes / (factor * W)

Ejemplo:
    mpiexec -n 5 python balanceo.py --estrategia dinamico --chunk 4 \
            --velocidades 1,1,0.5,0.25
"""
import argparse
import json
import math
import sys
import time

import numpy as np
from mpi4py import MPI

# Etiquetas (tags) de los mensajes MPI
TAG_PEDIR = 1     # trabajador -> maestro : "estoy libre, dame trabajo"
TAG_TRABAJO = 2   # maestro -> trabajador : paquete de tareas
TAG_FIN = 3       # maestro -> trabajador : ya no hay más trabajo

ESTRATEGIAS = ["estatico", "estatico_ciclico", "estatico_ponderado",
               "dinamico", "guiado"]


# --------------------------------------------------------------------------
# Generación de la carga de trabajo
# --------------------------------------------------------------------------
def generar_costos(n, costo_medio_ms, variabilidad, semilla):
    """Costo (en segundos, a velocidad 1.0) de cada tarea.

    variabilidad = 0   -> todas las tareas cuestan lo mismo.
    variabilidad > 0   -> distribución log-normal (algunas tareas son mucho
                          más pesadas), con media = costo_medio_ms.
    """
    rng = np.random.default_rng(semilla)
    if variabilidad <= 0:
        costos = np.full(n, costo_medio_ms / 1000.0)
    else:
        mu = math.log(costo_medio_ms) - variabilidad ** 2 / 2.0
        costos = rng.lognormal(mu, variabilidad, n) / 1000.0
    return np.clip(costos, 0.0005, None)


# --------------------------------------------------------------------------
# Ejecución de una tarea en un nodo con cierta velocidad
# --------------------------------------------------------------------------
def contar_primos(cantidad):
    """Carga CPU real: cuenta primos entre 10^6 y 10^6 + cantidad."""
    total = 0
    for x in range(1_000_001, 1_000_001 + cantidad, 2):
        es_primo = True
        i = 3
        while i * i <= x:
            if x % i == 0:
                es_primo = False
                break
            i += 2
        total += es_primo
    return total


def calibrar_real():
    """Cuántos números por milisegundo procesa contar_primos en esta máquina."""
    t = time.perf_counter()
    contar_primos(4000)
    return 4000 / max((time.perf_counter() - t) * 1000.0, 1e-6)


def ejecutar_tarea(costo, velocidad, modo, num_por_ms):
    if modo == "simulado":
        # el nodo "tarda" costo/velocidad (dormir = no estorba a los demás)
        time.sleep(costo / velocidad)
    else:
        # modo real: trabajo CPU de verdad; un nodo con velocidad 1/k
        # repite el trabajo k veces (0.5 -> 2 veces, 0.25 -> 4 veces)
        repeticiones = max(1, round(1.0 / velocidad))
        for _ in range(repeticiones):
            contar_primos(int(costo * 1000.0 * num_por_ms))


# --------------------------------------------------------------------------
# Reparto ESTÁTICO (se decide antes de empezar, sin mirar cómo avanza todo)
# --------------------------------------------------------------------------
def reparto_estatico(costos, n_trab, estrategia, velocidades):
    n = len(costos)
    paquetes = [[] for _ in range(n_trab)]
    if estrategia == "estatico":
        base, extra = divmod(n, n_trab)
        ini = 0
        for w in range(n_trab):
            tam = base + (1 if w < extra else 0)
            paquetes[w] = costos[ini:ini + tam].tolist()
            ini += tam
    elif estrategia == "estatico_ciclico":
        for i, c in enumerate(costos):
            paquetes[i % n_trab].append(float(c))
    elif estrategia == "estatico_ponderado":
        v = np.array([velocidades[w % len(velocidades)] for w in range(n_trab)])
        cuota = n * v / v.sum()
        cuentas = np.floor(cuota).astype(int)
        resto = n - cuentas.sum()
        for w in np.argsort(-(cuota - cuentas))[:resto]:
            cuentas[w] += 1
        ini = 0
        for w in range(n_trab):
            paquetes[w] = costos[ini:ini + cuentas[w]].tolist()
            ini += cuentas[w]
    return paquetes


# --------------------------------------------------------------------------
# Tamaño del paquete en el reparto DINÁMICO
# --------------------------------------------------------------------------
def tam_paquete(estrategia, restantes, n_trab, chunk, factor):
    if estrategia == "dinamico":
        return min(chunk, restantes)
    # guiado: paquetes grandes al inicio, pequeños al final (menos esperas)
    return min(restantes, max(chunk, math.ceil(restantes / (factor * n_trab))))


# --------------------------------------------------------------------------
# MAESTRO
# --------------------------------------------------------------------------
def maestro(comm, args, costos):
    n_trab = comm.Get_size() - 1
    info = {"paquetes": 0, "mensajes": 0}

    if args.estrategia.startswith("estatico"):
        # Un solo envío por trabajador, decidido de antemano (Scatter)
        velocidades = [float(v) for v in args.velocidades.split(",")]
        paquetes = reparto_estatico(costos, n_trab, args.estrategia, velocidades)
        comm.scatter([[]] + paquetes, root=0)
        info["paquetes"] = n_trab
        info["mensajes"] = n_trab
    else:
        # Cola de trabajo: el que se desocupa pide más (pull / self-scheduling)
        st = MPI.Status()
        siguiente, n, activos = 0, len(costos), n_trab
        while activos > 0:
            comm.recv(source=MPI.ANY_SOURCE, tag=TAG_PEDIR, status=st)
            w = st.Get_source()
            info["mensajes"] += 1
            if siguiente < n:
                tam = tam_paquete(args.estrategia, n - siguiente, n_trab,
                                  args.chunk, args.factor_guiado)
                comm.send(costos[siguiente:siguiente + tam].tolist(),
                          dest=w, tag=TAG_TRABAJO)
                siguiente += tam
                info["paquetes"] += 1
            else:
                comm.send(None, dest=w, tag=TAG_FIN)
                activos -= 1
            info["mensajes"] += 1
    return info


# --------------------------------------------------------------------------
# TRABAJADOR
# --------------------------------------------------------------------------
def trabajador(comm, args, t0, num_por_ms):
    rank = comm.Get_rank()
    lista_v = [float(v) for v in args.velocidades.split(",")]
    vel_base = lista_v[(rank - 1) % len(lista_v)]

    # --degradar "rank:segundos:nueva_velocidad"  (un nodo se vuelve lento
    # a mitad de la ejecución, p. ej. otro proceso le roba CPU)
    deg = None
    if args.degradar:
        r, t, v = args.degradar.split(":")
        if int(r) == rank:
            deg = (float(t), float(v))

    def velocidad_ahora():
        if deg and (time.perf_counter() - t0) >= deg[0]:
            return deg[1]
        return vel_base

    intervalos = []          # (inicio, fin, num. tareas) relativo a t0
    espera, tareas = 0.0, 0

    def procesar(lista_costos):
        nonlocal tareas
        ini = time.perf_counter()
        for c in lista_costos:
            ejecutar_tarea(c, velocidad_ahora(), args.modo, num_por_ms)
        fin = time.perf_counter()
        tareas += len(lista_costos)
        intervalos.append((ini - t0, fin - t0, len(lista_costos)))

    if args.estrategia.startswith("estatico"):
        mi_paquete = comm.scatter(None, root=0)
        procesar(mi_paquete)
    else:
        st = MPI.Status()
        while True:
            t_a = time.perf_counter()
            comm.send(None, dest=0, tag=TAG_PEDIR)
            if args.latencia_ms > 0:                     # latencia de red simulada
                time.sleep(args.latencia_ms / 1000.0)
            paquete = comm.recv(source=0, tag=MPI.ANY_TAG, status=st)
            espera += time.perf_counter() - t_a
            if st.Get_tag() == TAG_FIN:
                break
            procesar(paquete)

    ocupado = sum(f - i for i, f, _ in intervalos)
    return {"rank": rank, "velocidad": vel_base, "tareas": tareas,
            "ocupado": ocupado, "espera_maestro": espera,
            "intervalos": intervalos}


# --------------------------------------------------------------------------
# Programa principal
# --------------------------------------------------------------------------
def leer_argumentos():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--estrategia", choices=ESTRATEGIAS, default="dinamico")
    p.add_argument("--tareas", type=int, default=240, help="número total de tareas")
    p.add_argument("--costo-medio-ms", type=float, default=10.0)
    p.add_argument("--variabilidad", type=float, default=0.8,
                   help="sigma log-normal del costo (0 = tareas idénticas)")
    p.add_argument("--semilla", type=int, default=42)
    p.add_argument("--velocidades", default="1,1,0.5,0.25",
                   help="velocidad de cada trabajador (se repite en ciclo)")
    p.add_argument("--chunk", type=int, default=4,
                   help="tareas por paquete (dinámico) o paquete mínimo (guiado)")
    p.add_argument("--factor-guiado", type=float, default=2.0)
    p.add_argument("--latencia-ms", type=float, default=0.0,
                   help="latencia de red simulada por petición al maestro")
    p.add_argument("--modo", choices=["simulado", "real"], default="simulado")
    p.add_argument("--degradar", default="",
                   help='"rank:segundos:nueva_velocidad"')
    p.add_argument("--salida", default="", help="archivo .json para guardar resultados")
    p.add_argument("--guardar-intervalos", action="store_true")
    return p.parse_args()


def main():
    args = leer_argumentos()
    comm = MPI.COMM_WORLD
    rank, size = comm.Get_rank(), comm.Get_size()
    if size < 2:
        if rank == 0:
            sys.exit("Se necesitan al menos 2 procesos (1 maestro + 1 trabajador): "
                     "mpiexec -n 5 python balanceo.py ...")
        return
    n_trab = size - 1

    costos = None
    num_por_ms = 1.0
    if rank == 0:
        costos = generar_costos(args.tareas, args.costo_medio_ms,
                                args.variabilidad, args.semilla)
        if args.modo == "real":
            num_por_ms = calibrar_real()
    num_por_ms = comm.bcast(num_por_ms, root=0)

    comm.Barrier()
    t0 = time.perf_counter()
    if rank == 0:
        info = maestro(comm, args, costos)
        mi = None
    else:
        mi = trabajador(comm, args, t0, num_por_ms)
    comm.Barrier()
    makespan = time.perf_counter() - t0
    todos = comm.gather(mi, root=0)

    if rank != 0:
        return

    # ---------------------------- métricas -------------------------------
    trab = [t for t in todos if t is not None]
    total_trabajo = float(costos.sum())
    vel = [t["velocidad"] for t in trab]
    t_ideal = total_trabajo / sum(vel)               # balance perfecto, sin costos extra
    t_1_nodo = total_trabajo / max(vel)              # el nodo más rápido trabajando solo
    for t in trab:
        t["ocioso"] = makespan - t["ocupado"]
        t["utilizacion"] = t["ocupado"] / makespan
    ocupados = [t["ocupado"] for t in trab]
    res = {
        "estrategia": args.estrategia, "chunk": args.chunk,
        "trabajadores": n_trab, "tareas": args.tareas,
        "velocidades": vel, "latencia_ms": args.latencia_ms,
        "modo": args.modo, "degradar": args.degradar,
        "makespan": makespan, "t_ideal": t_ideal, "t_1_nodo": t_1_nodo,
        "speedup": t_1_nodo / makespan,
        "eficiencia_balanceo": t_ideal / makespan,
        "utilizacion_media": float(np.mean([t["utilizacion"] for t in trab])),
        "ocioso_total": float(sum(t["ocioso"] for t in trab)),
        "desbalance": max(ocupados) / (sum(ocupados) / len(ocupados)),
        "paquetes": info["paquetes"], "mensajes": info["mensajes"],
        "trabajadores_detalle": trab if args.guardar_intervalos else
            [{k: v for k, v in t.items() if k != "intervalos"} for t in trab],
    }

    etiqueta = args.estrategia + (f" (chunk={args.chunk})"
                                  if args.estrategia in ("dinamico", "guiado") else "")
    print(f"\n=== {etiqueta} | {n_trab} trabajadores | {args.tareas} tareas "
          f"| modo {args.modo} ===")
    print(f"Tiempo total (makespan): {makespan:.3f} s   "
          f"ideal: {t_ideal:.3f} s   1 nodo rápido: {t_1_nodo:.3f} s")
    print(f"Speedup: {res['speedup']:.2f}x   eficiencia de balanceo: "
          f"{100 * res['eficiencia_balanceo']:.1f} %   "
          f"utilización media: {100 * res['utilizacion_media']:.1f} %")
    print(f"Paquetes: {info['paquetes']}   mensajes: {info['mensajes']}")
    print(f"{'rank':>4} {'vel':>5} {'tareas':>7} {'ocupado':>9} {'ocioso':>8} {'util':>6}")
    for t in trab:
        print(f"{t['rank']:>4} {t['velocidad']:>5.2f} {t['tareas']:>7} "
              f"{t['ocupado']:>8.3f}s {t['ocioso']:>7.3f}s "
              f"{100 * t['utilizacion']:>5.1f}%")

    if args.salida:
        with open(args.salida, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
