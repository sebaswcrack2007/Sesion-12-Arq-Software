# backoff_jitter_sim.py
# Simulación de Thundering Herd: Sin Jitter vs Jitter Fijo (0.5s) vs Full Jitter
import random
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt

T_BASE, T_MAX, JITTER, N, C = 1.0, 30.0, 0.5, 10_000, 2_000

def simular_llegadas(modo, intento=1):
    techo = min(T_MAX, T_BASE * (2 ** intento))
    tiempos = []
    for _ in range(N):
        if modo == "sin_jitter":
            t = techo
        elif modo == "jitter_fijo":
            t = techo + random.uniform(0, JITTER)
        elif modo == "full_jitter":
            t = random.uniform(0, techo)
        tiempos.append(t)
    return tiempos

random.seed(42)
for modo, nombre in [("sin_jitter", "Sin Jitter"), ("jitter_fijo", "Jitter Fijo 0.5s"), ("full_jitter", "Full Jitter (0..2s)")]:
    llegadas = simular_llegadas(modo, intento=1)
    por_ms = Counter(int(t * 1000) for t in llegadas)
    por_seg = Counter(int(t) for t in llegadas)
    segs_saturados = sum(1 for v in por_seg.values() if v > C)
    print(f"{nombre:20s} | Pico/ms: {max(por_ms.values()):5d} | Ventana: {len(por_ms):4d} ms | Pico TPS: {max(por_seg.values()):5d} | Segs > 2000 TPS: {segs_saturados} s")