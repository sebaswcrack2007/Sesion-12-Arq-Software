# bulkhead_pools.py
# Aislamiento de hilos por compartimento mediante ThreadPoolExecutor y BoundedSemaphore (Paso 2.4)
from concurrent.futures import ThreadPoolExecutor
import threading

# Tres pools independientes: una saturación en IA no afecta los hilos de alertas ni telemetría
pool_alertas = ThreadPoolExecutor(max_workers=16, thread_name_prefix="uci-alerta")
pool_telemetria = ThreadPoolExecutor(max_workers=8, thread_name_prefix="telemetria")
pool_ia = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ia-nube")

# Cupo máximo del compartimento IA: 4 hilos en ejecución + 20 peticiones en cola
cupo_ia = threading.BoundedSemaphore(4 + 20)

def enviar_a_ia(muestra_ecg, llamar_ia_fn, fallback_local_fn):
    # Si el compartimento de IA está lleno (24 peticiones), rechaza al instante sin bloquear
    if not cupo_ia.acquire(blocking=False):
        return fallback_local_fn(muestra_ecg)

    fut = pool_ia.submit(llamar_ia_fn, muestra_ecg)
    # Libera un cupo del semáforo tan pronto termina la tarea
    fut.add_done_callback(lambda _: cupo_ia.release())
    return fut