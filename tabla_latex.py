#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tabla_latex.py - Convierte resultados/*.json en macros y tablas de LaTeX
para que los números de la presentación siempre coincidan con tus corridas.

    python tabla_latex.py      ->  presentacion/numeros.tex y tabla_resumen.tex
"""
import json
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(AQUI, "resultados")
OUT = os.path.join(AQUI, "presentacion")
os.makedirs(OUT, exist_ok=True)


def cargar(n):
    with open(os.path.join(RES, n + ".json"), encoding="utf-8") as f:
        return json.load(f)


def buscar(lista, est, chunk=None):
    for d in lista:
        if d["estrategia"] == est and (chunk is None or d["chunk"] == chunk):
            return d
    raise KeyError((est, chunk))


het, hom = cargar("heterogeneo"), cargar("homogeneo")
deg, chk, esc = cargar("degradado"), cargar("chunk"), cargar("escalabilidad")
t = lambda d: f"{d['makespan_mediana']:.2f}"

est, cic = buscar(het, "estatico"), buscar(het, "estatico_ciclico")
pon, d1 = buscar(het, "estatico_ponderado"), buscar(het, "dinamico", 1)
d4, gui = buscar(het, "dinamico", 4), buscar(het, "guiado")
din_chk = [d for d in chk if d["estrategia"] == "dinamico"]
mejor = min(din_chk, key=lambda d: d["makespan_mediana"])
peor = max(din_chk, key=lambda d: d["makespan_mediana"])
e8 = [d for d in esc if d["trabajadores"] == 8]

macros = {
    "tEstHet": t(est), "tCicHet": t(cic), "tPondHet": t(pon), "tDinUnoHet": t(d1),
    "tDinHet": t(d4), "tGuiHet": t(gui),
    "tEstHom": t(buscar(hom, "estatico")), "tDinHom": t(buscar(hom, "dinamico", 4)),
    "tIdealHet": f"{est['t_ideal']:.2f}", "tUnNodoHet": f"{est['t_1_nodo']:.2f}",
    "tEstDeg": t(buscar(deg, "estatico")), "tCicDeg": t(buscar(deg, "estatico_ciclico")),
    "tDinDeg": t(buscar(deg, "dinamico", 4)), "tGuiDeg": t(buscar(deg, "guiado")),
    "spEstHet": f"{est['t_1_nodo'] / est['makespan_mediana']:.2f}",
    "spDinHet": f"{d4['t_1_nodo'] / d4['makespan_mediana']:.2f}",
    "efDinHet": f"{100 * d4['t_ideal'] / d4['makespan_mediana']:.0f}",
    "efEstHet": f"{100 * est['t_ideal'] / est['makespan_mediana']:.0f}",
    "utEstHet": f"{100 * est['utilizacion_media']:.0f}",
    "utDinHet": f"{100 * d4['utilizacion_media']:.0f}",
    "mejoraHet": f"{est['makespan_mediana'] / d4['makespan_mediana']:.1f}",
    "mejoraDeg": f"{buscar(deg, 'estatico')['makespan_mediana'] / buscar(deg, 'dinamico', 4)['makespan_mediana']:.1f}",
    "chunkMejor": str(mejor["chunk"]), "tChunkMejor": t(mejor),
    "chunkPeor": str(peor["chunk"]), "tChunkPeor": t(peor),
    "spDinOcho": f"{buscar(e8, 'dinamico', 4)['t_1_nodo'] / buscar(e8, 'dinamico', 4)['makespan_mediana']:.1f}",
    "spEstOcho": f"{buscar(e8, 'estatico')['t_1_nodo'] / buscar(e8, 'estatico')['makespan_mediana']:.1f}",
}
with open(os.path.join(OUT, "numeros.tex"), "w", encoding="utf-8") as f:
    f.write("% Generado por tabla_latex.py - no editar a mano\n")
    for k, v in macros.items():
        f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")

nombres = {"estatico": "Estático (bloques)", "estatico_ciclico": "Estático cíclico",
           "estatico_ponderado": "Estático ponderado", "dinamico": "Dinámico",
           "guiado": "Guiado"}
filas = []
for d in het:
    n = nombres[d["estrategia"]]
    if d["estrategia"] == "dinamico":
        n += f" (paq.\\,{d['chunk']})"
    filas.append(f"{n} & {d['makespan_mediana']:.2f} & "
                 f"{d['t_1_nodo'] / d['makespan_mediana']:.2f}$\\times$ & "
                 f"{100 * d['t_ideal'] / d['makespan_mediana']:.0f}\\,\\% & "
                 f"{100 * d['utilizacion_media']:.0f}\\,\\% & "
                 f"{d['ocioso_total']:.2f} & {d['mensajes']} \\\\")
tabla = ("\\begin{tabular}{@{}lrrrrrr@{}}\n\\toprule\n"
         "Estrategia & Tiempo (s) & Speedup & Efic. & Util. & Ocio (s) & Msj. \\\\\n"
         "\\midrule\n" + "\n".join(filas) + "\n\\bottomrule\n\\end{tabular}\n")
with open(os.path.join(OUT, "tabla_resumen.tex"), "w", encoding="utf-8") as f:
    f.write(tabla)
print("listo: presentacion/numeros.tex y presentacion/tabla_resumen.tex")
