#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graficas.py - Genera las figuras (PNG) a partir de resultados/*.json.

    python graficas.py

Salida: resultados/figuras/*.png  (fondo oscuro, listas para Beamer)
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

AQUI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(AQUI, "resultados")
FIG = os.path.join(RES, "figuras")

# Tema: "oscuro" (por defecto) o "claro" (variable de entorno TEMA=claro)
TEMA = os.environ.get("TEMA", "oscuro")
if TEMA == "formal":
    FIG = os.path.join(RES, "figuras_formal")
    SUPERFICIE, TINTA, TINTA2, REJILLA = "#ffffff", "#111111", "#555555", "#dddddd"
    COLOR = {"dinamico": "#1f3a68", "estatico": "#9b2335", "guiado": "#2e7d7a",
             "estatico_ciclico": "#b8860b", "estatico_ponderado": "#7a6a9c"}
elif TEMA == "claro":
    FIG = os.path.join(RES, "figuras_claro")
    SUPERFICIE, TINTA, TINTA2, REJILLA = "#f6f3ec", "#23201c", "#6f685c", "#ddd7cb"
    COLOR = {"dinamico": "#2f6b5a", "estatico": "#9c3d54", "guiado": "#4c63a8",
             "estatico_ciclico": "#c9962b", "estatico_ponderado": "#d9743a"}
else:
    SUPERFICIE, TINTA, TINTA2, REJILLA = "#1a1a19", "#f0efec", "#c3c2b7", "#3a3a38"
    COLOR = {"dinamico": "#3987e5", "estatico": "#d95926", "guiado": "#199e70",
             "estatico_ciclico": "#c98500", "estatico_ponderado": "#d55181"}
os.makedirs(FIG, exist_ok=True)
NOMBRE = {"estatico": "Estático (bloques)", "estatico_ciclico": "Estático cíclico",
          "estatico_ponderado": "Estático ponderado", "guiado": "Guiado"}

# Tipografía opcional (Kalam) si está en la carpeta fuentes/ del proyecto
FUENTE = {}
_kal = os.path.join(AQUI, "fuentes", "Kalam-Regular.ttf")
if TEMA == "formal":
    FUENTE = {"font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "TeX Gyre Termes", "DejaVu Serif"]}
if TEMA == "claro" and os.path.exists(_kal):
    from matplotlib import font_manager
    font_manager.fontManager.addfont(_kal)
    font_manager.fontManager.addfont(os.path.join(AQUI, "fuentes", "Kalam-Bold.ttf"))
    FUENTE = {"font.family": "Kalam"}

# En el tema claro las figuras se hacen más chicas (texto relativamente más grande)
ESCALA_CLARO = 0.78 if TEMA in ("claro", "formal") else 1.0
_subplots = plt.subplots


def _subplots_escalado(*a, **kw):
    if "figsize" in kw:
        kw["figsize"] = tuple(x * ESCALA_CLARO for x in kw["figsize"])
    return _subplots(*a, **kw)


plt.subplots = _subplots_escalado

plt.rcParams.update({
    "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE,
    "savefig.facecolor": SUPERFICIE, "text.color": TINTA,
    "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "axes.edgecolor": REJILLA, "grid.color": REJILLA,
    "font.size": {"claro": 9.5, "formal": 10.5}.get(TEMA, 11),
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlecolor": TINTA,
    **FUENTE,
})


def cargar(nombre):
    with open(os.path.join(RES, nombre + ".json"), encoding="utf-8") as f:
        return json.load(f)


def nombre(d):
    if d["estrategia"] == "dinamico":
        return f"Dinámico (paquete={d['chunk']})"
    return NOMBRE[d["estrategia"]]


def guardar(fig, archivo):
    fig.savefig(os.path.join(FIG, archivo), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  figura:", archivo)


# ---------------------------------------------------------------- 1. Gantt
def gantt():
    corridas = [cargar("gantt_estatico"), cargar("gantt_dinamico")]
    fig, ejes = plt.subplots(2, 1, figsize=(8.2, 4.3), sharex=True)
    xmax = max(c["makespan"] for c in corridas) * 1.06
    for ax, c in zip(ejes, corridas):
        col = COLOR[c["estrategia"]]
        trab = c["trabajadores_detalle"]
        for fila, t in enumerate(trab):
            y = len(trab) - 1 - fila
            fin_ultimo = 0
            for ini, fin, n in t["intervalos"]:
                ax.barh(y, fin - ini, left=ini, height=0.62, color=col,
                        edgecolor=SUPERFICIE, linewidth=1.6)
                fin_ultimo = max(fin_ultimo, fin)
            # tiempo ocioso: desde que termina hasta el final de la corrida
            if c["makespan"] - fin_ultimo > 0.02:
                ax.barh(y, c["makespan"] - fin_ultimo, left=fin_ultimo, height=0.62,
                        facecolor="none", edgecolor=TINTA2, hatch="////",
                        linewidth=0, alpha=0.55)
        ax.axvline(c["t_ideal"], color=TINTA2, linestyle=(0, (4, 3)), linewidth=1.2)
        ax.set_yticks(range(len(trab)))
        ax.set_yticklabels([f"Nodo {t['rank']}  (v={t['velocidad']:g})"
                            for t in reversed(trab)])
        ax.set_title(f"{nombre(c)}  —  {c['makespan']:.2f} s", loc="left")
        ax.set_xlim(0, xmax)
        ax.grid(axis="x", linewidth=0.6)
        ax.set_axisbelow(True)
    ejes[-1].set_xlabel("Tiempo (s)")
    ejes[1].legend(handles=[Patch(facecolor=COLOR["dinamico"], label="trabajando"),
                            Patch(facecolor="none", edgecolor=TINTA2, hatch="////",
                                  label="ocioso (esperando)"),
                            Line2D([0], [0], color=TINTA2, linestyle=(0, (4, 3)),
                                   label="tiempo ideal")],
                   loc="center right", frameon=False, labelcolor=TINTA2, fontsize=9.5)
    fig.tight_layout()
    guardar(fig, "gantt.png")


# ------------------------------------------------- 2. makespan por estrategia
def barras_makespan():
    escenarios = [("homogeneo", "Nodos iguales  (1, 1, 1, 1)"),
                  ("heterogeneo", "Nodos distintos  (1, 1, 0.5, 0.25)")]
    fig, ejes = plt.subplots(1, 2, figsize=(9, 3.4), sharex=True, sharey=False)
    xmax = 0
    for ax, (arch, titulo) in zip(ejes, escenarios):
        datos = cargar(arch)
        ys = list(range(len(datos)))[::-1]
        for y, d in zip(ys, datos):
            ax.barh(y, d["makespan_mediana"], height=0.62, color=COLOR[d["estrategia"]])
            ax.text(d["makespan_mediana"] + 0.04, y, f"{d['makespan_mediana']:.2f} s",
                    va="center", color=TINTA, fontsize=9.5)
            xmax = max(xmax, d["makespan_mediana"])
        ax.set_yticks(ys)
        ax.set_yticklabels([nombre(d) for d in datos], fontsize=9.5)
        ax.set_title(titulo, loc="left", fontsize=14)
        ax.grid(axis="x", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_xlabel("Tiempo total (s)  —  menos es mejor")
    for ax in ejes:
        ax.set_xlim(0, xmax * 1.18)
    fig.tight_layout()
    guardar(fig, "makespan.png")


# ------------------------------------------- 3. ocupado vs ocioso por nodo
def ocio_por_nodo():
    corridas = [cargar("gantt_estatico"), cargar("gantt_dinamico")]
    fig, ejes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, c in zip(ejes, corridas):
        col = COLOR[c["estrategia"]]
        trab = c["trabajadores_detalle"]
        xs = range(len(trab))
        ocupado = [t["ocupado"] for t in trab]
        ocioso = [t["ocioso"] for t in trab]
        ax.bar(xs, ocupado, width=0.62, color=col, edgecolor=SUPERFICIE, linewidth=2)
        ax.bar(xs, ocioso, width=0.62, bottom=ocupado, facecolor="none",
               edgecolor=TINTA2, hatch="////", linewidth=0, alpha=0.6)
        for x, t in zip(xs, trab):
            ax.text(x, c["makespan"] + 0.05, f"{100 * t['utilizacion']:.0f} %",
                    ha="center", color=TINTA, fontsize=9.5)
        ax.set_xticks(list(xs))
        ax.set_xticklabels([f"Nodo {t['rank']}\nv={t['velocidad']:g}" for t in trab])
        ax.set_title(f"{nombre(c)}", loc="left")
        ax.set_ylim(0, max(x["makespan"] for x in corridas) * 1.18)
        ax.grid(axis="y", linewidth=0.6)
        ax.set_axisbelow(True)
    ejes[0].set_ylabel("Tiempo (s)")
    ejes[1].legend(handles=[Patch(facecolor=COLOR["dinamico"], label="ocupado"),
                            Patch(facecolor="none", edgecolor=TINTA2, hatch="////",
                                  label="ocioso")],
                   loc="upper right", frameon=False, labelcolor=TINTA2, fontsize=9.5)
    fig.tight_layout()
    guardar(fig, "ocio_nodos.png")


# ------------------------------------------------ 4. tamaño de paquete
def chunk():
    datos = cargar("chunk")
    din = [d for d in datos if d["estrategia"] == "dinamico"]
    guiado = next(d for d in datos if d["estrategia"] == "guiado")
    pond = next(d for d in datos if d["estrategia"] == "estatico_ponderado")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.2, 4.4), sharex=True,
                                 gridspec_kw={"height_ratios": [3, 1.6]})
    xs = list(range(len(din)))
    ys = [d["makespan_mediana"] for d in din]
    a1.plot(xs, ys, color=COLOR["dinamico"], linewidth=2.4, marker="o",
            markersize=9, markeredgecolor=SUPERFICIE, markeredgewidth=2)
    a1.axhline(guiado["makespan_mediana"], color=COLOR["guiado"], linewidth=1.8,
               linestyle=(0, (5, 3)))
    a1.axhline(pond["makespan_mediana"], color=COLOR["estatico_ponderado"],
               linewidth=1.8, linestyle=(0, (5, 3)))
    a1.text(len(xs) - 1.05, guiado["makespan_mediana"] + 0.04, "Guiado",
            color=COLOR["guiado"], ha="right", fontsize=9.5)
    a1.text(len(xs) - 1.05, pond["makespan_mediana"] - 0.13, "Estático ponderado",
            color=COLOR["estatico_ponderado"], ha="right", fontsize=9.5)
    a1.set_ylabel("Tiempo total (s)")
    a1.set_title("Paquete chico = muchos mensajes · paquete grande = nodos lentos frenan",
                 loc="left", fontsize=10.5)
    a1.grid(axis="y", linewidth=0.6)
    a1.set_ylim(0.7, max(ys) * 1.1)
    a2.bar(xs, [d["paquetes"] for d in din], width=0.6, color=COLOR["dinamico"],
           alpha=0.75)
    for x, d in zip(xs, din):
        a2.text(x, d["paquetes"] * 1.15, str(d["paquetes"]), ha="center",
                color=TINTA2, fontsize=9.5)
    a2.set_yscale("log")
    a2.set_ylim(1, 900)
    a2.set_ylabel("Paquetes\n(log)")
    a2.set_xticks(xs)
    a2.set_xticklabels([str(d["chunk"]) for d in din])
    a2.set_xlabel("Tareas por paquete (chunk)")
    a2.grid(axis="y", linewidth=0.6)
    fig.tight_layout()
    guardar(fig, "chunk.png")


# ------------------------------------------------ 5. escalabilidad
def escalabilidad():
    datos = cargar("escalabilidad")
    base = [1, 1, 0.5, 0.25]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ws = [1, 2, 4, 8]
    ideal = []
    for w in ws:
        v = [base[i % 4] for i in range(w)]
        ideal.append(sum(v) / max(v))
    ax.plot(ws, ideal, color=TINTA2, linewidth=1.6, linestyle=(0, (5, 3)), marker="o",
            markersize=6)
    ax.text(8.12, ideal[-1], "ideal", color=TINTA2, va="center", fontsize=9.5)
    for est, chunk_ in (("dinamico", 4), ("guiado", 1), ("estatico", 1)):
        serie = [d for d in datos if d["estrategia"] == est and d["chunk"] == chunk_]
        serie.sort(key=lambda d: d["trabajadores"])
        sp = [d["t_1_nodo"] / d["makespan_mediana"] for d in serie]
        ax.plot(ws, sp, color=COLOR[est], linewidth=2.6, marker="o", markersize=9,
                markeredgecolor=SUPERFICIE, markeredgewidth=2)
        etiqueta = {"dinamico": "Dinámico", "guiado": "Guiado", "estatico": "Estático"}[est]
        dy = {"dinamico": 0.28, "guiado": -0.42, "estatico": 0}[est]
        ax.text(8.12, sp[-1] + dy, etiqueta, color=COLOR[est], va="center", fontsize=10.5)
    ax.set_xticks(ws)
    ax.set_xlim(0.7, 9.6)
    ax.set_xlabel("Número de trabajadores (nodos)")
    ax.set_ylabel("Speedup vs. el nodo más rápido solo")
    ax.grid(axis="y", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    guardar(fig, "escalabilidad.png")


# ------------------------------------------------ 6. nodo degradado
def degradado():
    datos = cargar("degradado")
    fig, ax = plt.subplots(figsize=(7.4, 2.9))
    ys = list(range(len(datos)))[::-1]
    for y, d in zip(ys, datos):
        ax.barh(y, d["makespan_mediana"], height=0.6, color=COLOR[d["estrategia"]])
        ax.text(d["makespan_mediana"] + 0.03, y, f"{d['makespan_mediana']:.2f} s",
                va="center", fontsize=10.5)
    ax.set_yticks(ys)
    ax.set_yticklabels([nombre(d) for d in datos])
    ax.set_xlim(0, max(d["makespan_mediana"] for d in datos) * 1.18)
    ax.set_xlabel("Tiempo total (s)  —  menos es mejor")
    ax.grid(axis="x", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    guardar(fig, "degradado.png")


# ------------------------------------------------ 7. tareas por nodo
def tareas_por_nodo():
    est = cargar("gantt_estatico")["trabajadores_detalle"]
    din = cargar("gantt_dinamico")["trabajadores_detalle"]
    total = sum(t["tareas"] for t in din)
    suma_v = sum(t["velocidad"] for t in din)
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    ancho = 0.34
    for i, (e, d) in enumerate(zip(est, din)):
        ax.bar(i - ancho / 2 - 0.02, e["tareas"], ancho, color=COLOR["estatico"])
        ax.bar(i + ancho / 2 + 0.02, d["tareas"], ancho, color=COLOR["dinamico"])
        ideal = total * d["velocidad"] / suma_v
        ax.plot([i - 0.45, i + 0.45], [ideal, ideal], color=TINTA2, linewidth=1.8,
                linestyle=(0, (4, 3)))
        ax.text(i + ancho / 2 + 0.02, d["tareas"] + 2, str(d["tareas"]), ha="center",
                color=TINTA, fontsize=9.5)
        ax.text(i - ancho / 2 - 0.02, e["tareas"] + 2, str(e["tareas"]), ha="center",
                color=TINTA, fontsize=9.5)
    ax.set_xticks(range(len(din)))
    ax.set_xticklabels([f"Nodo {t['rank']}\nv={t['velocidad']:g}" for t in din])
    ax.set_ylabel("Tareas que ejecutó")
    ax.set_ylim(0, max(t["tareas"] for t in din) * 1.2)
    ax.grid(axis="y", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(handles=[Patch(facecolor=COLOR["estatico"], label="Estático (60 c/u)"),
                       Patch(facecolor=COLOR["dinamico"], label="Dinámico"),
                       Line2D([0], [0], color=TINTA2, linestyle=(0, (4, 3)),
                              label="proporcional a v")],
              loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False,
              labelcolor=TINTA2, fontsize=9.5)
    fig.tight_layout()
    guardar(fig, "tareas_nodo.png")


# ------------------------------------------------ 8. tamaño de paquetes guiado
def paquetes_guiado(n=240, w=4, factor=2.0, minimo=1):
    import math
    tam, restantes = [], n
    while restantes > 0:        # misma fórmula que tam_paquete() de balanceo.py
        t = min(restantes, max(minimo, math.ceil(restantes / (factor * w))))
        tam.append(t)
        restantes -= t
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.bar(range(1, len(tam) + 1), tam, color=COLOR["guiado"], width=0.7)
    ax.axhline(4, color=COLOR["dinamico"], linewidth=2, linestyle=(0, (5, 3)))
    ax.text(len(tam), 5.2, "Dinámico fijo: siempre 4", color=COLOR["dinamico"],
            ha="right", fontsize=9.5)
    ax.text(1.4, tam[0] - 1.5, f"{tam[0]} tareas", color=TINTA, fontsize=9.5)
    ax.set_xlabel("Número de paquete entregado")
    ax.set_ylabel("Tareas en el paquete")
    ax.grid(axis="y", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    guardar(fig, "paquetes_guiado.png")


# ------------------------------------------------ 9. tiempos en dos escenarios
def tiempos_dos_escenarios():
    escenarios = [("heterogeneo", "Nodos distintos  (1, 1, 0.5, 0.25)"),
                  ("degradado", "Un nodo se degrada a mitad")]
    fig, ejes = plt.subplots(1, 2, figsize=(9, 3.1), sharex=True)
    xmax = 0
    for ax, (arch, titulo) in zip(ejes, escenarios):
        datos = cargar(arch)
        ys = list(range(len(datos)))[::-1]
        for y, d in zip(ys, datos):
            ax.barh(y, d["makespan_mediana"], height=0.62, color=COLOR[d["estrategia"]])
            ax.text(d["makespan_mediana"] + 0.04, y, f"{d['makespan_mediana']:.2f} s",
                    va="center", color=TINTA, fontsize=10)
            xmax = max(xmax, d["makespan_mediana"])
        ax.set_yticks(ys)
        ax.set_yticklabels([nombre(d) for d in datos], fontsize=9.5)
        ax.set_title(titulo, loc="left", fontsize=11.5)
        ax.grid(axis="x", linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_xlabel("Tiempo total (s)  -  menos es mejor")
    for ax in ejes:
        ax.set_xlim(0, xmax * 1.2)
    fig.tight_layout()
    guardar(fig, "tiempos.png")


if __name__ == "__main__":
    gantt()
    barras_makespan()
    ocio_por_nodo()
    chunk()
    escalabilidad()
    degradado()
    tareas_por_nodo()
    paquetes_guiado()
    tiempos_dos_escenarios()
