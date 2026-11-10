#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ejecutar_todo.py - Corre experimentos, genera figuras y compila la presentación."""
import os
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PRES = os.path.join(AQUI, "presentacion")


def paso(cmd, cwd=AQUI):
    print("\n$", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


paso([sys.executable, "experimentos.py"])
paso([sys.executable, "graficas.py"])                      # figuras oscuras (main_oscuro.tex)
os.environ["TEMA"] = "claro"
paso([sys.executable, "graficas.py"])                      # figuras crema (main_claro.tex)
os.environ["TEMA"] = "formal"
paso([sys.executable, "graficas.py"])                      # figuras blancas (main.tex)
paso([sys.executable, "tabla_latex.py"])
if shutil.which("xelatex"):
    paso(["xelatex", "-interaction=nonstopmode", "main.tex"], PRES)
    paso(["xelatex", "-interaction=nonstopmode", "main.tex"], PRES)
if shutil.which("pdflatex"):
    paso([sys.executable, "guion.py"], PRES)
    paso(["pdflatex", "-interaction=nonstopmode", "guion.tex"], PRES)
    paso(["pdflatex", "-interaction=nonstopmode", "codigo_fuente.tex"], AQUI)
    paso(["pdflatex", "-interaction=nonstopmode", "codigo_fuente.tex"], AQUI)
else:
    print("pdflatex no encontrado: compila presentacion/main.tex (XeLaTeX) en Overleaf o con tu distribución de LaTeX.")
