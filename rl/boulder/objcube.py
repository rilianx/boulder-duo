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
import time

import numpy as np

from .cube import CubeNavigator

HIST = 8


class ObjectTracker:
    def __init__(self):
        self.hist = {}           # id → [(tick, x, y)]
        self.moves = {}          # itype → [movimientos, cambios de dirección]
        self.wraps = set()       # itypes que reaparecen por el borde
        self.lastdir = {}
        self.dirs = {}           # itype → {(dx, dy): veces}: hacia dónde se mueve cada tipo
        self.fall = None         # itype → {máscara adelante: [avanzó, no]} (lo comparte el conocimiento)
        # modelo de movimiento por tipo (objetos al azar): [movimientos de casilla, oportunidades]; cada tick
        # observado suma como oportunidad la fracción de vecinas libres (si hay muro, el intento no se ve)
        self.moverate = {}
        self.rel = {}            # movimiento relativo (lo comparte el conocimiento: know.rel)
        self._apos = None        # posición del avatar en el tick anterior

    def update(self, st, free=None):
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
                    dd = self.dirs.setdefault(t, {})
                    dd[d] = dd.get(d, 0) + 1
                    self._record_rel(st, t, px, py, x, y)
            # cuándo avanza en su dirección: según qué había adelante en el tick anterior
            if h and self.fall is not None and getattr(st, "prev", None) is not None and st.tick - h[-1][0] == 1:
                d = self.main_dir(t)
                if d is not None:
                    cx, cy = int(round(h[-1][1])), int(round(h[-1][2]))
                    ax_, ay_ = cx + d[0], cy + d[1]
                    if 0 <= ax_ < st.W and 0 <= ay_ < st.H:
                        key = st.prev[ay_ * st.W + ax_]
                        moved = abs(x - h[-1][1]) + abs(y - h[-1][2]) > 0.01
                        r = self.fall.setdefault(t, {}).setdefault(key, [0, 0])
                        r[0 if moved else 1] += 1
            if h and free is not None and st.tick - h[-1][0] == 1:
                cx, cy = int(round(h[-1][1])), int(round(h[-1][2]))
                nfree = sum(1 for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))
                            if 0 <= cx + dx < st.W and 0 <= cy + dy < st.H and free[(cy + dy) * st.W + cx + dx])
                mv = int(round(x)) != cx or int(round(y)) != cy
                m = self.moverate.setdefault(t, [0, 0.0])
                m[0] += mv; m[1] += nfree / 4
            h.append((st.tick, x, y))
            del h[:-HIST]
        for oid in list(self.hist):
            if oid not in st.objects:
                del self.hist[oid]
        self._apos = (st.fx, st.fy)
        self._cells = None

    def _type_cells(self, st):
        """Casillas de cada tipo poco numeroso (≤ 30) en el tick anterior: candidatos a objetivo."""
        if self._cells is None:
            masks = st.prev or st.masks
            cells = {}
            for i, m in enumerate(masks):
                while m:
                    b = m & -m; u = b.bit_length() - 1; m ^= b
                    cells.setdefault(u, []).append((i % st.W, i // st.W))
            self._cells = {u: c for u, c in cells.items() if len(c) <= 30}
        return self._cells

    def _record_rel(self, st, t, px, py, x, y):
        """¿El movimiento acercó o alejó al objeto del avatar y de la instancia más cercana de cada tipo?"""
        targets = {}
        if self._apos is not None:
            targets[-1] = [self._apos]
        for u, c in self._type_cells(st).items():
            if u != t:
                targets[u] = c
        for u, cells in targets.items():
            d0 = min(abs(px - cx) + abs(py - cy) for cx, cy in cells)
            d1 = min(abs(x - cx) + abs(y - cy) for cx, cy in cells)
            if abs(d1 - d0) < 1e-6 or d0 == 0:
                continue
            r = self.rel.setdefault(t, {}).setdefault(u, [0, 0])
            r[0 if d1 < d0 else 1] += 1

    def speed(self, oid):
        """Casillas recorridas por tick (camino, no desplazamiento neto: lo que zigzaguea no es lento)."""
        h = self.hist.get(oid, [])
        if len(h) < 2:
            return 0.0
        path = sum(abs(b[1] - a[1]) + abs(b[2] - a[2]) for a, b in zip(h, h[1:]))
        return path / max(h[-1][0] - h[0][0], 1)

    def type_speed(self, st, t):
        """Rapidez típica de un tipo (promedio de sus objetos con historia); sin datos, 1 (prudente): un
        objeto recién aparecido (una cabra que se acaba de enojar) no tiene historia propia."""
        vs = [self.speed(o) for o, (tt, _, _) in st.objects.items() if tt == t and len(self.hist.get(o, [])) >= 3]
        if vs:
            return sum(vs) / len(vs)
        m = self.moves.get(t)
        return 1.0 if not m else max(0.2, min(1.0, m[0] / max(1, sum(len(h) for h in self.hist.values()))))

    def predict(self, st, oid, H, attr, blocked):
        """Posiciones (x, y) en los ticks 1..H de un objeto que se acerca (signo +1) o aleja (−1) de su
        objetivo, a su rapidez observada, por casillas libres. El objetivo se toma quieto (el avatar donde está)."""
        t, x, y = st.objects[oid]
        u, sign = attr
        if u == -1:
            goals = [(st.fx, st.fy)]
        else:
            goals = [(i % st.W, i // st.W) for i, m in enumerate(st.masks) if m >> u & 1]
        if not goals:
            return None
        v = self.speed(oid) if len(self.hist.get(oid, [])) >= 3 else self.type_speed(st, t)
        v = max(v, 0.05)
        out = []
        for _ in range(H):
            best = None
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                nx, ny = x + dx * v, y + dy * v
                cx, cy = int(round(nx)), int(round(ny))
                if not (0 <= cx < st.W and 0 <= cy < st.H) or blocked[cy * st.W + cx] and (cx, cy) != (int(round(x)), int(round(y))):
                    continue
                dist = min(abs(nx - gx) + abs(ny - gy) for gx, gy in goals)
                key = sign * dist                     # perseguidor: menor distancia; fugitivo: mayor
                if best is None or key < best[0]:
                    best = (key, nx, ny)
            if best is not None:
                x, y = best[1], best[2]
            out.append((x, y))
        return out

    def random_type(self, t):
        m = self.moves.get(t)
        return bool(m) and m[0] >= 5 and m[1] / m[0] > 0.25

    def main_dir(self, t):
        """Dirección en que se mueve un tipo casi siempre (p. ej. una roca que cae: (0, 1)), o None."""
        dd = self.dirs.get(t)
        if not dd:
            return None
        d, n = max(dd.items(), key=lambda kv: kv[1])
        return d if n >= 3 and n > 0.8 * sum(dd.values()) else None

    def p_attempt(self, t):
        """Probabilidad por tick de que un objeto de tipo t intente moverse (dirección al azar)."""
        m = self.moverate.get(t)
        return min(1.0, m[0] / m[1]) if m and m[1] >= 20 else 0.5

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
        self.track.dirs = know.move_dirs            # hacia dónde se mueve cada tipo: persiste entre partidas
        self.track.fall = know.fall
        self.track.rel = know.rel

    def step(self, st, goal, br=None):
        self._t0 = time.perf_counter()               # el presupuesto por decisión cuenta desde aquí
        self.track.update(st, [not b for b in self.know.blocked_cells(st)])
        self._st = st
        return super().step(st, goal, None)      # sin puente: nada de consultar el modelo del juego

    def _carried_to(self, k, c):
        return self._carry[k].get(c, c) if k < len(self._carry) else c

    def _adjust_risk(self, R):
        """Modelo de objetos (P["objmodel"]): cada objeto que se mueve al azar es una distribución sobre
        casillas que se propaga tick a tick (intenta moverse con p_attempt a una de 4 direcciones al azar; si
        hay muro se queda). Riesgo = 1 − (1 − estático)·Π(1 − P_obj(c, k)·letalidad del tipo)."""
        if not self.P.get("objmodel"):
            return R
        st = self._st
        W, H, N = st.W, st.H, len(st.masks)
        free = np.array([not b for b in self.know.blocked_cells(st)], dtype=bool).reshape(H, W)
        floor = 0
        for t in self.know.floor:
            floor |= 1 << t
        lethal = {}
        surv = [np.ones((H, W)) for _ in R]
        for oid, (t, x, y) in st.objects.items():
            if not self.track.random_type(t) or oid in getattr(self, "_paths", {}):
                continue
            if t not in lethal:
                base = float(self.risk.grid([floor])[0])
                lethal[t] = max(float(self.P.get("obj_lethal", 0.0)), float(self.risk.grid([floor | 1 << t])[0]) - base)
            p = self.track.p_attempt(t)
            P = np.zeros((H, W))
            cx, cy = int(round(x)), int(round(y))
            if not (0 <= cx < W and 0 <= cy < H):
                continue
            P[cy, cx] = 1.0
            for k in range(len(R)):
                nxt = P * (1 - p)
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    moved = np.zeros((H, W))
                    ys, yd = (slice(1, H), slice(0, H - 1)) if dy == -1 else (slice(0, H - 1), slice(1, H)) if dy == 1 else (slice(0, H), slice(0, H))
                    xs, xd = (slice(1, W), slice(0, W - 1)) if dx == -1 else (slice(0, W - 1), slice(1, W)) if dx == 1 else (slice(0, W), slice(0, W))
                    moved[yd, xd] = P[ys, xs] * (p / 4)
                    ok = moved * free                      # entra si la casilla destino está libre
                    nxt += ok
                    # lo que choca con muro o borde se queda donde estaba
                    back = np.zeros((H, W)); back[ys, xs] = (moved - ok)[yd, xd]
                    nxt += back
                    edge = P * (p / 4)                     # intentos hacia fuera del mapa
                    if dy == -1: nxt[0, :] += edge[0, :]
                    if dy == 1: nxt[H - 1, :] += edge[H - 1, :]
                    if dx == -1: nxt[:, 0] += edge[:, 0]
                    if dx == 1: nxt[:, W - 1] += edge[:, W - 1]
                P = nxt
                surv[k] *= 1 - P * lethal[t]
        return [1 - (1 - np.asarray(r)) * s.reshape(N) for r, s in zip(R, surv)]

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
        paths = {}
        if self.P.get("relmodel", True):
            blocked = self.know.blocked_cells(st)
            for oid, (t, x, y) in st.objects.items():
                attr = self.know.attractor(t)
                # solo si la tendencia explica sus movimientos mejor que ir siempre en la misma dirección (un
                # camión que va a la derecha "se acerca" por casualidad a lo que está a la derecha)
                dd = self.track.dirs.get(t, {})
                straight = max(dd.values()) / sum(dd.values()) if dd else 0.0
                if attr is not None and attr[2] > straight and t not in self.know.avatar_types:
                    pth = self.track.predict(st, oid, self.Hz, attr[:2], blocked)
                    if pth:
                        paths[oid] = pth
        self._paths = paths
        chasers = {}                                     # perseguidores del avatar → su rapidez
        for oid in paths:
            t = st.objects[oid][0]
            a = self.know.attractor(t)
            if a[1] > 0 and (a[0] == -1 or a[0] in self.know.avatar_types):
                h = self.track.hist.get(oid, [])
                chasers[oid] = self.track.speed(oid) if len(h) >= 3 else self.track.type_speed(st, t)
        cube = []
        for k in range(1, self.Hz + 1):
            masks = list(static)
            for oid, (t, x, y) in st.objects.items():
                bit = 1 << t
                if oid in paths:                         # perseguidor / fugitivo: según su tendencia aprendida
                    if oid in chasers:
                        # persigue al avatar, que también se mueve: peligrosa toda la zona que alcanza en k ticks
                        r = min(3, int(math.ceil(chasers[oid] * k)))
                        cx, cy = int(round(x)), int(round(y))
                        for yy in range(max(0, cy - r), min(H, cy + r + 1)):
                            for xx in range(max(0, cx - r), min(W, cx + r + 1)):
                                if abs(xx - cx) + abs(yy - cy) <= r:
                                    masks[yy * W + xx] |= bit
                    px, py = paths[oid][k - 1]
                    for xx in {int(math.floor(px)), int(math.ceil(px))}:
                        for yy in {int(math.floor(py)), int(math.ceil(py))}:
                            if 0 <= xx < W and 0 <= yy < H:
                                masks[yy * W + xx] |= bit
                    continue
                if self.track.random_type(t) and self.P.get("objmodel"):
                    continue                              # va como distribución de probabilidad (_adjust_risk)
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
