"""Cubo del futuro SIN modelo del juego: solo lo observado, con los objetos extrapolados por su velocidad.

El puente manda los objetos móviles con su posición exacta (información observada, como la vería un
jugador). Se sigue a cada objeto entre ticks por su id y se estima su velocidad (promedio de los últimos
8 ticks). Por tipo se detecta:
  - movimiento aleatorio (cambia seguido de dirección): su zona de peligro crece con el tiempo (tope 2);
  - reaparición por el borde (salta más de medio mapa): la extrapolación da la vuelta.
Con eso se arma el mismo "cubo" (máscaras por casilla y tick) que en cube.py y se usa el mismo A*
espacio-tiempo. El primer paso lo cubre el predictor (aprendido antes, sin consultar el modelo en juego).
"""
from __future__ import annotations

import math

from .cube import CubeNavigator

HIST = 8


class ObjectTracker:
    def __init__(self):
        self.hist = {}           # id → [(tick, x, y)]
        self.moves = {}          # itype → [movimientos, cambios de dirección]
        self.wraps = set()       # itypes que reaparecen por el borde
        self.lastdir = {}

    def update(self, st):
        for oid, (t, x, y) in st.objects.items():
            h = self.hist.setdefault(oid, [])
            if h:
                _, px, py = h[-1]
                dx, dy = x - px, y - py
                if abs(dx) > st.W / 2 or abs(dy) > st.H / 2:
                    self.wraps.add(t)
                    h.clear()
                elif abs(dx) + abs(dy) > 0:
                    d = (round(math.copysign(1, dx)) if dx else 0, round(math.copysign(1, dy)) if dy else 0)
                    m = self.moves.setdefault(t, [0, 0])
                    m[0] += 1
                    if oid in self.lastdir and self.lastdir[oid] != d:
                        m[1] += 1
                    self.lastdir[oid] = d
            h.append((st.tick, x, y))
            del h[:-HIST]
        for oid in list(self.hist):
            if oid not in st.objects:
                del self.hist[oid]

    def random_type(self, t):
        m = self.moves.get(t)
        return bool(m) and m[0] >= 5 and m[1] / m[0] > 0.25

    def velocity(self, oid):
        h = self.hist.get(oid, [])
        if len(h) < 2:
            return 0.0, 0.0
        (t0, x0, y0), (t1, x1, y1) = h[0], h[-1]
        return (x1 - x0) / max(t1 - t0, 1), (y1 - y0) / max(t1 - t0, 1)


class ObjectCubeNavigator(CubeNavigator):
    def __init__(self, know, risk, P, horizon=20, danger=None, **kw):
        super().__init__(know, risk, P, horizon=horizon, reps=1, danger=danger, **kw)
        self.track = ObjectTracker()

    def step(self, st, goal, br=None):
        self.track.update(st)
        self._st = st
        return super().step(st, goal, None)      # sin puente: nada de consultar el modelo del juego

    def _carried_to(self, k, c):
        return self._carry[k].get(c, c) if k < len(self._carry) else c

    def _cube(self, st):
        W, H, N = st.W, st.H, len(st.masks)
        # arrastre: casilla de un objeto que arrastra en el tick k → su casilla en k+1 (None si sale del mapa)
        carriers = self.know.carriers()
        self._carry = [dict() for _ in range(self.Hz + 1)]
        for oid, (t, x, y) in st.objects.items():
            if t not in carriers:
                continue
            vx, vy = self.track.velocity(oid)
            for k in range(self.Hz + 1):
                a = (x + vx * k, y + vy * k); b = (x + vx * (k + 1), y + vy * (k + 1))
                ca = int(round(a[1])) * W + int(round(a[0]))
                if not (0 <= round(a[0]) < W and 0 <= round(a[1]) < H):
                    break
                inb = 0 <= round(b[0]) < W and 0 <= round(b[1]) < H
                self._carry[k][ca] = int(round(b[1])) * W + int(round(b[0])) if inb else None
        obj_types = {t for t, _, _ in st.objects.values()}
        clear = ~sum(1 << t for t in obj_types) if obj_types else ~0
        static = [m & clear for m in st.masks]
        cube = []
        for k in range(1, self.Hz + 1):
            masks = list(static)
            for oid, (t, x, y) in st.objects.items():
                bit = 1 << t
                if self.track.random_type(t):
                    r = min(2, int(math.ceil(k * 0.5)))   # zona que crece con el tiempo
                    cx, cy = int(round(x)), int(round(y))
                    for yy in range(max(0, cy - r), min(H, cy + r + 1)):
                        for xx in range(max(0, cx - r), min(W, cx + r + 1)):
                            if abs(xx - cx) + abs(yy - cy) <= r:
                                masks[yy * W + xx] |= bit
                    continue
                vx, vy = self.track.velocity(oid)
                px, py = x + vx * k, y + vy * k
                if t in self.track.wraps:
                    px %= W; py %= H
                elif not (0 <= px < W and 0 <= py < H):
                    continue
                x0, y0 = int(math.floor(px)), int(math.floor(py))
                for xx in {x0, int(math.ceil(px))}:
                    for yy in {y0, int(math.ceil(py))}:
                        if 0 <= xx < W and 0 <= yy < H:
                            masks[yy * W + xx] |= bit
            cube.append(masks)
        return cube
