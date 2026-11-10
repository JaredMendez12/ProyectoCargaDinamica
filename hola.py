from mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
if rank == 0:
    comm.send("hola", dest=1)
    print("Maestro (rank 0) envió: hola")
else:
    mensaje = comm.recv(source=0)
    print(f"Trabajador (rank {rank}) recibió: {mensaje}")
