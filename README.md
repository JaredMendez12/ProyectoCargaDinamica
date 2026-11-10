# Carga dinámica: balanceo estático vs. dinámico (Maestro–Trabajador)

Comparación de estrategias de **balanceo de carga** en un esquema Maestro–Trabajador con
**Python + MPI (mpi4py)**. Cada proceso MPI es un "nodo"; los nodos lentos se simulan
(`tiempo = costo / velocidad`), así que todo corre en **una sola laptop**. También incluye
instrucciones para correrlo en un **clúster real de laptops** en red local.

Estrategias implementadas: `estatico` (bloques), `estatico_ciclico`, `estatico_ponderado`,
`dinamico` (por paquetes de tamaño fijo) y `guiado` (paquetes decrecientes).

### Resultado principal (4 trabajadores con velocidades 1, 1, 0.5, 0.25)

| Estrategia | Tiempo | Speedup | Utilización |
|---|---|---|---|
| Estático (bloques) | ~2.4 s | 0.92× | ~49 % |
| Dinámico (paquete 4) | ~0.9 s | ~2.4× | ~91 % |

El dinámico es **~2.6× más rápido** que el estático cuando los nodos son heterogéneos
(tiempo ideal: 0.80 s). Los números exactos varían un poco en cada máquina.

---

## 1. Requisitos

| Qué | Para qué | ¿Obligatorio? |
|---|---|---|
| **Python 3.9 o superior** | Todo el proyecto | Sí |
| **Una implementación de MPI** (MS-MPI, Open MPI o MPICH) | Ejecutar `mpiexec` | Sí |
| `mpi4py`, `numpy`, `matplotlib` (`requirements.txt`) | Código y gráficas | Sí |
| **LaTeX** con XeLaTeX y pdflatex (MiKTeX, TeX Live u Overleaf) | Compilar la presentación y los PDF | Solo si quieres regenerar los PDF |
| Navegador web | Demo en vivo y visualizador | Opcional |

Los PDF ya compilados (`presentacion/main.pdf`, `presentacion/guion.pdf`, `codigo_fuente.pdf`),
los resultados (`resultados/*.json`) y las figuras (`resultados/figuras*/`) vienen incluidos
en el repositorio, así que no necesitas LaTeX solo para verlos.

### Instalar MPI según tu sistema

**Windows** — Microsoft MPI (MS-MPI):
1. Descarga **MS-MPI** desde la página oficial de Microsoft
   (busca "Microsoft MPI download") e instala **`msmpisetup.exe`**.
2. Cierra y vuelve a abrir la terminal, y comprueba: `mpiexec -help`
   (si no lo encuentra, agrega `C:\Program Files\Microsoft MPI\Bin` al `PATH`).

**Linux (Ubuntu/Debian)**:

    sudo apt update
    sudo apt install openmpi-bin libopenmpi-dev python3-venv python3-dev

**macOS** (con Homebrew):

    brew install open-mpi

---

## 2. Instalación paso a paso

```bash
# 1) Clonar el repositorio
git clone https://github.com/<tu-usuario>/carga-dinamica.git
cd carga-dinamica

# 2) (Recomendado) crear un entorno virtual
python -m venv .venv
#    Windows (PowerShell):  .venv\Scripts\Activate.ps1
#    Linux / macOS:         source .venv/bin/activate

# 3) Instalar dependencias de Python
pip install -r requirements.txt
```

> En Linux/macOS usa `python3` en lugar de `python` si tu sistema lo requiere.

---

## 3. Ejecución

### Paso 1 — Comprobar que MPI funciona

    mpiexec -n 2 python hola.py

Debe imprimir algo como `Maestro (rank 0) envió: hola` y `Trabajador (rank 1) recibió: hola`.

Diagnóstico más completo (IP, latencia, velocidad relativa de cada proceso):

    mpiexec -n 3 python cluster_diagnostico.py

> **Open MPI** (Linux/macOS): si dice que no hay suficientes núcleos ("not enough slots"),
> agrega `--oversubscribe`, por ejemplo `mpiexec --oversubscribe -n 5 python balanceo.py ...`.
> En Windows (MS-MPI) no hace falta.

### Paso 2 — Prueba rápida: estático vs. dinámico

    mpiexec -n 5 python balanceo.py --estrategia estatico --velocidades 1,1,0.5,0.25
    mpiexec -n 5 python balanceo.py --estrategia dinamico --chunk 8 --velocidades 1,1,0.5,0.25

`-n 5` = 1 maestro + 4 trabajadores, y `--velocidades` da la velocidad relativa de cada trabajador.
Cada ejecución imprime el tiempo total, el speedup, la eficiencia, la utilización y una tabla por nodo
(ver `presentacion/ejemplo_salida.txt`).

Opciones de `balanceo.py`:

| Opción | Valor por defecto | Descripción |
|---|---|---|
| `--estrategia` | `dinamico` | `estatico`, `estatico_ciclico`, `estatico_ponderado`, `dinamico`, `guiado` |
| `--tareas` | 240 | Número total de tareas |
| `--costo-medio-ms` | 10 | Costo medio de una tarea |
| `--variabilidad` | 0.8 | Variación del costo entre tareas |
| `--velocidades` | `1,1,0.5,0.25` | Velocidad de cada trabajador (debe haber `n-1` valores) |
| `--chunk` | 4 | Tamaño de paquete (dinámico) |
| `--factor-guiado` | 2.0 | Factor del reparto guiado |
| `--latencia-ms` | 0 | Latencia de red simulada por mensaje |
| `--degradar` | — | Degradar un nodo a mitad de la ejecución, p. ej. `"4:0.3:0.25"` |
| `--modo` | `simulado` | `real` usa carga de CPU real en vez de `sleep` |
| `--semilla` | 42 | Semilla aleatoria |
| `--salida` | — | Guardar los resultados en un `.json` |

Ayuda completa: `python balanceo.py --help`.

### Paso 3 — Reproducir todos los experimentos, gráficas y la presentación

    python ejecutar_todo.py

Tarda unos minutos. Hace lo mismo que correr esto a mano:

    python experimentos.py          # escenarios -> resultados/*.json
    python graficas.py              # figuras -> resultados/figuras/
    python tabla_latex.py           # -> presentacion/numeros.tex y tabla_resumen.tex
    cd presentacion
    xelatex main.tex && xelatex main.tex        # presentación
    python guion.py && pdflatex guion.tex       # guion del expositor

Si no tienes LaTeX, el script lo detecta, se salta la compilación y regenera todo lo demás.
Los números de las diapositivas salen de `resultados/*.json`, así que la presentación se
actualiza sola con los resultados de tu máquina. También puedes subir la carpeta `presentacion/`
a **Overleaf** (Menú → Compilador → **XeLaTeX**).

`experimentos.py --exp <nombre> --reps <n>` corre un solo escenario (`homogeneo`, `heterogeneo`,
`chunk`, `escalabilidad`, `degradado`, `gantt`) con *n* repeticiones (3 por defecto).

### Paso 4 (opcional) — Demo en vivo en el navegador

    python servidor_demo.py

Abre `http://127.0.0.1:8765`. La página ejecuta cada comando con MPI de verdad y anima lo que hace
cada nodo. El servidor solo escucha en tu propia laptop; se detiene con `Ctrl+C`.
Puedes cambiar el puerto con la variable de entorno `PUERTO_DEMO`.

`visualizador/index.html` es un visualizador independiente: ábrelo directo en el navegador,
sin necesitar MPI ni el servidor.

### Paso 5 (opcional) — Clúster real de laptops

Ver [`cluster/README_cluster.md`](cluster/README_cluster.md): requisitos de cada laptop,
archivo de hosts (`cluster/hosts.txt.ejemplo`), diagnóstico de red y comandos para Windows y Linux.

---

## 4. Estructura del proyecto

```
carga-dinamica/
├── balanceo.py              # Maestro, trabajador, las 5 estrategias y las métricas
├── experimentos.py          # Escenarios: homogéneo, heterogéneo, paquete, escalabilidad, degradado
├── graficas.py              # Figuras (Gantt, barras, curva de paquete, speedup...)
├── tabla_latex.py           # Resultados -> macros y tabla de LaTeX
├── ejecutar_todo.py         # Corre todo el flujo
├── cluster_diagnostico.py   # Diagnóstico de nodos (IP, latencia, velocidad, GPU)
├── hola.py                  # Prueba mínima de MPI
├── servidor_demo.py         # Servidor local de la demo en vivo
├── demo/index.html          # Página de la demo en vivo
├── visualizador/index.html  # Visualizador independiente (sin MPI)
├── codigo_fuente.tex/.pdf   # Listado del código para entregar
├── requirements.txt
├── cluster/                 # Guía y ejemplo de hosts para el clúster real
├── fuentes/                 # Tipografía Kalam (SIL OFL, ver fuentes/OFL.txt)
├── presentacion/
│   ├── main.tex / main.pdf  # Presentación Beamer (formal, XeLaTeX)
│   ├── main_claro.tex       # Versión crema con fuente Kalam
│   ├── main_oscuro.tex      # Versión oscura (pdflatex)
│   ├── guion.py / guion.tex / guion.pdf   # Guion del expositor
│   ├── numeros.tex, tabla_resumen.tex     # Generados por tabla_latex.py
│   └── ejemplo_salida.txt
└── resultados/
    ├── *.json               # Resultados de los experimentos
    └── figuras/, figuras_claro/, figuras_formal/   # Gráficas (tema oscuro, crema y formal)
```

---

## 5. Problemas comunes

| Síntoma | Solución |
|---|---|
| `mpiexec` no se reconoce | Instala MPI (sección 1) y reabre la terminal; revisa el `PATH`. |
| `pip install mpi4py` falla compilando (Linux) | Instala primero `libopenmpi-dev` (o `libmpich-dev`) y `python3-dev`. |
| Open MPI: "not enough slots" | Agrega `--oversubscribe` antes de `-n`. |
| Open MPI se niega a correr como root | Agrega `--allow-run-as-root` (solo en contenedores). |
| Aviso `findfont: Font family 'Liberation Serif' not found` | Es inofensivo: matplotlib usa otra fuente serif de la lista. |
| `xelatex` / `pdflatex` no encontrado | Instala MiKTeX o TeX Live, o compila en Overleaf. Los PDF incluidos ya están compilados. |
| La demo no abre en el puerto 8765 | Usa otro puerto: `PUERTO_DEMO=9000 python servidor_demo.py` (en PowerShell: `$env:PUERTO_DEMO=9000`). |
| Windows pide permiso de firewall al correr MPI | Acepta para redes privadas (necesario en el clúster real). |

---

## Licencias

- Tipografía **Kalam** (`fuentes/`): SIL Open Font License 1.1, ver [`fuentes/OFL.txt`](fuentes/OFL.txt).
