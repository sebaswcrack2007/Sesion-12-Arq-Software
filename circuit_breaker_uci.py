# circuit_breaker_uci.py
# Máquina de estados Circuit Breaker para conexión HospitValle UCI -> IA en Nube (Paso 2.1)
from collections import deque
import time

# Estados del Circuit Breaker
CLOSED = "CLOSED"
OPEN = "OPEN"
HALF_OPEN = "HALF_OPEN"

estado = CLOSED
ventana = deque(maxlen=20)  # Ventana deslizante basada en las últimas 20 llamadas
t_apertura = 0.0
pruebas = 0

def abrir():
    global estado, t_apertura
    estado = OPEN
    t_apertura = time.monotonic()

def tasa_fallos(win: deque) -> float:
    fallos = sum(1 for ok, _ in win if not ok)
    return fallos / len(win)

def tasa_lentas(win: deque) -> float:
    lentas = sum(1 for _, lenta in win if lenta)
    return lentas / len(win)

def llamar_ia(muestra_ecg, ia_nube, fallback_local):
    global estado, pruebas

    # 1. Estado OPEN: verificar si ya pasaron los 15 s de espera
    if estado == OPEN:
        if time.monotonic() - t_apertura >= 15.0:
            estado = HALF_OPEN
            pruebas = 0
        else:
            # Fail-fast en microsegundos hacia el modelo ligero local
            return fallback_local(muestra_ecg)

    # 2. Estado HALF-OPEN: limitar a máximo 3 llamadas de prueba simultáneas
    if estado == HALF_OPEN and pruebas >= 3:
        return fallback_local(muestra_ecg)

    # 3. Ejecución controlada con timeout de 800 ms (0.8 s)
    t0 = time.monotonic()
    try:
        r = ia_nube.analizar(muestra_ecg, timeout=0.8)
        ok = True
    except (TimeoutError, ConnectionError):
        r = None
        ok = False

    duracion = time.monotonic() - t0
    lenta = duracion > 0.5  # Umbral de degradación: 500 ms
    ventana.append((ok, lenta))

    # 4. Transiciones de estado según resultados
    if estado == HALF_OPEN:
        pruebas += 1
        if not ok or lenta:
            abrir()  # Si alguna prueba falla o es lenta, vuelve a OPEN
        elif pruebas == 3:
            estado = CLOSED  # 3 pruebas exitosas -> recupera operación normal
            ventana.clear()
    elif len(ventana) >= 10 and (tasa_fallos(ventana) >= 0.20 or tasa_lentas(ventana) >= 0.30):
        abrir()  # Supera umbral clínico -> abre circuito

    return r if ok else fallback_local(muestra_ecg)