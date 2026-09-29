"""Cubo del futuro: A* sobre (casilla, tick) con el mundo simulado hacia adelante.

1. El modelo del juego simula H ticks con el avatar quieto (R veces si hay azar) → máscaras de tipos por
   casilla y tick (la unión de las R simulaciones: conservador con lo aleatorio).
2. Riesgo de estar en una casilla en un tick = regresión logística sobre los tipos presentes, aprendida de
   las mismas etiquetas contrafactuales que el predictor (p. ej. "agua mata, salvo que haya un tronco").
3. A* sobre (casilla, tick): 4 movimientos o esperar, costo 1 + w_risk·(−log(1 − riesgo)); pasado el
   horizonte, el resto del camino se estima con la distancia sin peligro. Se replanifica cada tick.
"""
from __future__ import annotations

import heapq
import math
import time

import numpy as np
import torch

from .nav import Navigator, shortest

H_DEFAULT = 30


def fit_cell_risk(data_path, out_path, epochs=300):
    """Regresión logística: presencia de cada tipo en la casilla destino (ahora y en movimiento) → muerte."""
    z = np.load(data_path)
    X, Y, T = z["X"], z["Y"], int(z["T"])
    patch = 49
    center = 24
    now = X[:, [t * patch + center for t in range(T)]].astype(np.float32)
    mov = X[:, [(2 * T + t) * patch + center for t in range(T)]].astype(np.float32)
    F = torch.from_numpy(np.concatenate([now, mov], 1)); Yt = torch.from_numpy(Y)
    w = torch.zeros(F.shape[1], requires_grad=True); b = torch.zeros(1, requires_grad=True)
    opt = torch.optim.Adam([w, b], lr=0.05)
    for _ in range(epochs):
        loss = torch.nn.functional.binary_cross_entropy_with_logits(F @ w + b, Yt)
        opt.zero_grad(); loss.backward(); opt.step()
    torch.save({"w": w.detach().numpy(), "b": float(b.item()), "T": T}, out_path)
    return w.detach().numpy(), float(b.item())


class CellRisk:
    def __init__(self, path):
        d = torch.load(path, weights_only=False)
        self.w, self.b, self.T = d["w"], d["b"], d["T"]

    def grid(self, masks):
        """Riesgo por casilla para una lista de máscaras (sin información de movimiento en el futuro)."""
        m = np.array(masks, dtype=np.int64)
        pres = ((m[:, None] >> np.arange(self.T)[None, :]) & 1).astype(np.float32)
        return 1 / (1 + np.exp(-(pres @ self.w[: self.T] + self.b)))


class CubeNavigator(Navigator):
    def __init__(self, know, risk: CellRisk, P, horizon=H_DEFAULT, reps=3, danger=None, **kw):
        """danger (opcional): predictor de muerte sobre la grilla actual; el riesgo de un paso pasa a ser
        max(cubo, predictor), para ver también el peligro que provoca el propio avatar (cavar bajo una roca)."""
        super().__init__(know, None, P, **kw)
        self.risk, self.Hz, self.reps, self.pred = risk, horizon, reps, danger

    def plan(self, st, goal, strict=True):
        """A* sobre (casilla, tick) dentro de una ventana centrada en el avatar, con tope de tiempo.

        Heurística y cola del camino: distancia al destino por BFS inverso (sin peligro). Fuera de la ventana
        o del horizonte se completa con esa distancia. Si se acaba el tiempo (P["budget_ms"]), devuelve la
        primera acción del mejor nodo encontrado hasta ahí."""
        t_start = time.perf_counter()
        budget = self.P.get("budget_ms", 25.0) / 1000
        Rw = int(self.P.get("win", 8))
        cube = self._cube(st)                                # cube[k] = máscaras dentro de k+1 ticks
        W, Hh, N = st.W, st.H, len(st.masks)
        K = self.know
        offs = (-W, 1, W, -1, 0)
        H = len(cube)
        bm = 0
        for t in set(K.passed) | set(K.blocked):
            if K.is_blocking(t):
                bm |= 1 << t
        C = np.array(cube, dtype=np.int64) if H else np.zeros((0, N), np.int64)
        blocked = (C & bm) != 0                              # [H, N]
        R = [self.risk.grid(c) for c in cube]
        now_blocked = (np.array(st.masks, dtype=np.int64) & bm) != 0
        dist = self._dist_to_goal(st, goal, now_blocked)
        if dist[st.pos] is None:
            return None
        ax, ay = st.pos % W, st.pos // W
        inwin = lambda c: abs(c % W - ax) <= Rw and abs(c // W - ay) <= Rw
        w = self.P["w_risk"]
        pred = {}
        if self.pred is not None:
            pred = self.pred.probs(st, [j for j in range(N) if not now_blocked[j] and inwin(j)])
        start = (st.pos, 0)
        best = {start: 0.0}; first = {start: -1}
        pq = [(dist[st.pos], 0.0, st.pos, 0)]
        best_partial = (math.inf, None)
        n_pop = 0
        while pq:
            f, g, c, k = heapq.heappop(pq)
            if c == goal or k == -1:
                return g, first[(c, k)]
            if g > best.get((c, k), math.inf):
                continue
            n_pop += 1
            if dist[c] is not None and dist[c] < best_partial[0] and first[(c, k)] != -1:
                best_partial = (dist[c], first[(c, k)])
            if n_pop % 64 == 0 and time.perf_counter() - t_start > budget:
                return (best_partial[0], best_partial[1]) if best_partial[1] is not None else None
            if k == H or not inwin(c):                       # fuera del horizonte o de la ventana: completar
                if dist[c] is not None:
                    node = (goal, -1)
                    ng = g + dist[c]
                    if ng < best.get(node, math.inf):
                        best[node] = ng; first[node] = first[(c, k)]
                        heapq.heappush(pq, (ng, ng, goal, -1))
                continue
            x, y = c % W, c // W
            for d in range(5):
                if d < 4:
                    xx, yy = x + (d == 1) - (d == 3), y + (d == 2) - (d == 0)
                    if not (0 <= xx < W and 0 <= yy < Hh):
                        continue
                j = c + offs[d]
                if blocked[k][j] and j != goal:
                    continue
                if dist[j] is None:
                    continue
                p = float(R[k][j])
                if d < 4 and pred:
                    p = max(p, pred.get((j, d), 0.0))
                ng = g + 1.0 + w * -math.log(max(1e-4, 1 - p))
                node = (j, k + 1)
                if ng < best.get(node, math.inf):
                    best[node] = ng
                    first[node] = d if k == 0 else first[(c, k)]
                    heapq.heappush(pq, (ng + dist[j], ng, j, k + 1))
        return None

    def _dist_to_goal(self, st, goal, blocked):
        """BFS desde el destino sobre lo transitable ahora: distancia (sin peligro) de cada casilla."""
        W, N = st.W, len(st.masks)
        dist = [None] * N
        dist[goal] = 0
        fr = [goal]
        while fr:
            nx = []
            for i in fr:
                x, y = i % W, i // W
                for d, o in enumerate((-W, 1, W, -1)):
                    xx, yy = x + (d == 1) - (d == 3), y + (d == 2) - (d == 0)
                    j = i + o
                    if 0 <= xx < W and 0 <= yy < st.H and dist[j] is None and not blocked[j]:
                        dist[j] = dist[i] + 1
                        nx.append(j)
            fr = nx
        if dist[st.pos] is None and not blocked[st.pos]:
            pass
        return dist

    def _cube(self, st):
        return self._br.future(self.Hz, self.reps)

    def _tail(self, st, c, goal):
        class _S:  # estado mínimo para shortest() desde otra casilla
            pass
        s = _S(); s.W, s.H, s.masks = st.W, st.H, st.masks; s.pos = c
        return shortest(s, self.know, goal) if c != goal else 0

    def step(self, st, goal, br=None):
        self._br = br
        return super().step(st, goal, br)
