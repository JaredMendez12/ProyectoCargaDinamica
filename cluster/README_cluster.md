# Aplicacion al cluster de laptops en red local

Pasos para pasar de la simulacion (una laptop) a un cluster real. Las IP son de ejemplo.

## 1. Requisitos en CADA laptop
- Misma version de Python y de `mpi4py` (`pip install -r requirements.txt`) y la misma MPI
  (MPICH u Open MPI en Linux/Mac, MS-MPI en Windows).
- El proyecto en la MISMA ruta (por ejemplo `~/carga_dinamica`), o una carpeta compartida.
- Todas en la misma red (mismo Wi-Fi o switch). Firewall: permitir MPI / abrir puertos entre ellas.
- Linux/Mac: acceso `ssh` sin contrasena del maestro hacia las demas (`ssh-copy-id usuario@192.168.1.11`).

## 2. Direcciones IP
Averigua la IP de cada laptop (`ip a`, `ifconfig` o `ipconfig`) y ponlas en `cluster/hosts.txt`
(copia de `hosts.txt.ejemplo`). Probar conectividad y latencia a mano: `ping 192.168.1.11`.

## 3. Diagnostico (IP, latencia, velocidad v, GPU)
    mpiexec -f cluster/hosts.txt -n 4 python cluster_diagnostico.py
Windows (MS-MPI):
    mpiexec -hosts 4 192.168.1.10 1 192.168.1.11 1 192.168.1.12 1 192.168.1.13 1 python cluster_diagnostico.py

Imprime una tabla por nodo y sugiere `--velocidades` y el tamano de paquete `k`.

## 4. Ejecutar el balanceo en el cluster
Aqui la heterogeneidad es la del hardware real, asi que NO se simulan velocidades:
    mpiexec -f cluster/hosts.txt -n 4 python balanceo.py --estrategia dinamico --chunk 8 --modo real --velocidades 1,1,1
    mpiexec -f cluster/hosts.txt -n 4 python balanceo.py --estrategia estatico --modo real --velocidades 1,1,1
Para el estatico ponderado usa las velocidades medidas en el paso 3 en lugar de `1,1,1`.

## 5. CPU y GPU
`v` se mide como rendimiento relativo (tareas/s) del nodo; no importa si el trabajo lo hace una CPU
o una GPU. El esquema dinamico no necesita conocer `v`: la laptop con GPU pedira paquetes mas seguido.
`cluster_diagnostico.py` solo indica si hay `nvidia-smi`; para medir la GPU hay que cambiar
`trabajo_cpu` por un kernel de GPU (por ejemplo con CuPy o Numba) en esa laptop.
