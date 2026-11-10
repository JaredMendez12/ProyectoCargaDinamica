#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guion.py - Extrae las \\note de main.tex y arma guion.tex (guion del expositor).

    python guion.py && pdflatex guion.tex
"""
import re
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(AQUI, "main.tex"), encoding="utf-8").read()
src = src.split(r"\begin{document}", 1)[1]
partes = re.split(r"\\begin\{frame\}", src)[1:]
cuerpo = []
for n, p in enumerate(partes, 1):
    p = p.split(r"\end{frame}")[0]
    m = re.match(r"(?:\[[^\]]*\])?(?:\{([^\n]*)\})?", p)
    titulo = (m.group(1) or "").strip() or "Portada / cierre"
    notas = re.findall(r"\\note\[item\]\{((?:[^{}]|\{[^{}]*\})*)\}", p)
    if not notas:
        continue
    items = "\n".join(f"  \\item {x}" for x in notas)
    cuerpo.append(f"\\subsection*{{Diapositiva {n}: {titulo}}}\n\\begin{{itemize}}\n{items}\n\\end{{itemize}}")


REPARTO = r"""\subsection*{Reparto entre los integrantes (equitativo: 5--5--5--5 diapositivas)}
\begin{itemize}
  \item \textbf{Jared Méndez Valencia}: diapositivas 1--5 (portada, objetivos, problema, conceptos y arquitectura Maestro--Trabajador).
  \item \textbf{Daniel del Valle Andrade}: diapositivas 6--10 (protocolo, estático vs.\ dinámico, algoritmos, diagrama de flujo y cuadro comparativo).
  \item \textbf{Johan Lezama Núñez}: diapositivas 11--15 (paquetes según la velocidad, estrategias, simulación, Gantt y tiempo total).
  \item \textbf{Camila Serrano Trinidad}: diapositivas 16--20 (tamaño del paquete y escalabilidad, clúster de laptops, latencia y CPU/GPU, conclusiones, preguntas y referencias). Johan contesta primero las preguntas de la diapositiva 16.
\end{itemize}
\textbf{Reglas del equipo.} (1) No se leen las diapositivas: se explican con palabras propias usando las notas como guía. (2) Cada pregunta la contesta primero quien tiene ese tema (tabla de abajo) y los demás pueden complementar. (3) Todos deben poder contestar cualquier pregunta del tema; el código completo está en \texttt{codigo\_fuente.pdf}.

\subsection*{Mapa de la rúbrica}
\begin{center}\small
\begin{tabular}{@{}p{5.2cm}p{10.3cm}@{}}
\hline
\textbf{Criterio} & \textbf{Dónde se cubre}\\ \hline
Dominio del tema (25) & Diapositivas 3--12: conceptos, protocolo, algoritmos, diagrama de flujo, cuadro comparativo, estrategias, $M=2(\lceil N/k\rceil+W)$, $T_{\text{ideal}}$.\\
Calidad LaTeX/Beamer (20) & \texttt{main.tex}: \texttt{frame}, \texttt{block}, \texttt{alertblock}, \texttt{exampleblock}, fórmulas \texttt{\$...\$}, tablas con \texttt{booktabs}, TikZ.\\
Entregable gráfico o código (20) & Arquitectura (5), pseudocódigo con \texttt{listings} (8), diagrama de flujo (9), gráficas de resultados y escalabilidad (11, 14--16), \texttt{codigo\_fuente.pdf}.\\
Aplicación al clúster (20) & Diapositivas 17--18: IP, \texttt{hosts.txt}, \texttt{mpiexec}, latencia, balanceo CPU/GPU; \texttt{cluster\_diagnostico.py}.\\
Preguntas y respuestas (15) & Banco de preguntas de abajo, con responsable por tema.\\ \hline
\end{tabular}
\end{center}
"""

PREGUNTAS = r"""\newpage
\section*{Banco de preguntas frecuentes}
Responde primero quien aparece entre paréntesis; los demás complementan.

\subsection*{Conceptos y arquitectura (Jared)}
\begin{itemize}
  \item \textbf{¿Qué es la heterogeneidad y por qué importa?} Que los nodos tengan velocidades $v_i$ distintas. Con un reparto igual el tiempo total es $T=\max_i T_i$, así que el nodo más lento marca el ritmo y los demás quedan ociosos.
  \item \textbf{¿Speedup y eficiencia son lo mismo?} No. Speedup $S=T_{1\,\text{nodo}}/T$ compara contra un solo nodo. La eficiencia de balanceo del proyecto es $E=T_{\text{ideal}}/T$, con $T_{\text{ideal}}=\sum c_j/\sum v_i$; vale 100\,\% si todos terminan a la vez y no hay costo de comunicación.
  \item \textbf{¿Por qué el maestro no calcula?} Para atender las peticiones con baja latencia; si calculara, los trabajadores esperarían su turno para pedir trabajo.
  \item \textbf{¿Qué pasa si el maestro falla?} Es un punto único de falla y un posible cuello de botella. Alternativas: robo de trabajo sin maestro (Fernandes et al., 2024) o maestros jerárquicos; está planteado como trabajo futuro.
\end{itemize}

\subsection*{Protocolo y algoritmos (Daniel)}
\begin{itemize}
  \item \textbf{¿Qué hace \texttt{ANY\_SOURCE}?} Permite que el maestro reciba de cualquier trabajador, así atiende al primero que pide en lugar de seguir un orden fijo.
  \item \textbf{¿Cuántos mensajes se envían?} $M=2(\lceil N/k\rceil+W)$: cada paquete cuesta un PEDIR y un TRABAJO, y cada trabajador hace un PEDIR final que se contesta con FIN. Con $N=240$, $k=8$, $W=4$ son 68 (con $k=4$ serían 128).
  \item \textbf{¿Cómo se evita repetir o perder tareas?} La cola vive solo en el maestro y cada tarea sale una vez; el ciclo termina cuando \texttt{activos}\,$=0$.
  \item \textbf{¿Cuándo conviene estático?} Si las velocidades se conocen y son estables y las tareas son parejas: menos mensajes y más simple. Si no, dinámico.
\end{itemize}

\subsection*{Simulación y resultados (Johan)}
\begin{itemize}
  \item \textbf{¿Por qué \texttt{sleep}?} Hace los resultados reproducibles y no dependientes de cuántos núcleos tiene la laptop. También existe el modo \texttt{--modo real} con carga de CPU.
  \item \textbf{¿Por qué el guiado salió peor que el dinámico?} En el escenario con nodos distintos (\tGuiHet\,s contra \tDinHet\,s del dinámico) su primer paquete es grande y puede caer en el nodo lento, que luego retrasa el final. No siempre pierde: con un nodo que se degrada salió mejor (\tGuiDeg\,s contra \tDinDeg\,s), porque los paquetes grandes del inicio ahorran mensajes y los chicos del final reparten bien.
  \item \textbf{¿Cómo se eligió el tamaño del paquete?} Barrido de 1 a 60 tareas con una latencia simulada de 3\,ms por petición: paquetes chicos aumentan los mensajes y paquetes grandes desbalancean el final. El mejor en nuestra corrida fue \chunkMejor, aunque entre paquetes chicos (2 a 8) el tiempo casi empata, así que la diferencia es ruido de medición. En la simulación casi no hay latencia; en una red real el paquete óptimo sube.
  \item \textbf{¿Los resultados son confiables?} Mismas tareas (semilla fija) para todas las estrategias y mediana de varias corridas. Las cifras del equipo pueden variar con la laptop; lo que se debe sostener es la tendencia, no el decimal.
\end{itemize}

\subsection*{Clúster de laptops (Camila)}
\begin{itemize}
  \item \textbf{¿Cómo se llevaría esto a laptops reales?} Misma versión de Python, mpi4py y MPI en todas, el proyecto en la misma ruta, SSH sin contraseña, un \texttt{hosts.txt} con las IP y \texttt{mpiexec -f hosts.txt -n 4 python balanceo.py ...}. El código es el mismo que en la simulación.
  \item \textbf{¿Qué cambia con Wi-Fi?} Aumenta y varía la latencia $L$, así que el paquete mínimo $k\ge 18\,L\,v/\bar c$ crece. Con Ethernet o un switch se pueden usar paquetes más chicos.
  \item \textbf{¿Cómo se maneja CPU y GPU?} Cada nodo tiene una velocidad relativa $v_i$ (rendimiento entre el del más rápido), sin importar qué hardware hace el trabajo. El dinámico no necesita conocerla: la laptop con GPU pide más seguido.
  \item \textbf{¿Cómo se mide la velocidad de cada nodo?} Con \texttt{cluster\_diagnostico.py}: todos ejecutan la misma carga fija, se compara el tiempo, y también reporta IP, RTT al maestro y si hay GPU.
  \item \textbf{¿Escala a muchos nodos?} Hasta que el maestro se satura: llegan más peticiones por segundo de las que puede atender. Se mitiga con paquetes más grandes, prefetch o robo de trabajo.
  \item \textbf{¿Qué pasa si una laptop se cae?} La versión actual no tolera fallos: MPI normalmente aborta el trabajo. Habría que añadir tiempos límite y reasignar el paquete perdido (trabajo futuro).
\end{itemize}
"""

doc = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\IfFileExists{spanish.ldf}{\usepackage[spanish,es-noshorthands]{babel}}{\usepackage[english]{babel}}
\usepackage[margin=2cm]{geometry}
\usepackage{amsmath,xcolor,enumitem,array}
\setlist{itemsep=2pt}
\newcommand{\mono}[1]{\texttt{#1}}
\input{numeros.tex}
\begin{document}
\section*{Guion del expositor: Carga dinámica}
""" + REPARTO + "\n\n".join(cuerpo) + "\n\n" + PREGUNTAS + "\n\\end{document}\n"
open(os.path.join(AQUI, "guion.tex"), "w", encoding="utf-8").write(doc)
print("guion.tex listo con", len(cuerpo), "diapositivas")
