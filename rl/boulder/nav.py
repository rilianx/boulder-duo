"""El A* como subordinado: recibe órdenes "ve a la casilla X" de un agente de alto nivel y las cumple sin morir.

Navigator.step(estado, destino) devuelve la acción del tick; el resultado de la orden lo decide quien la
emite: llegó (el avatar está en el destino), murió (la partida terminó perdiendo), inalcanzable (no hay ruta)
o tiempo agotado. No sabe nada de qué conviene en el juego: solo qué se puede pisar (aprendido) y dónde hay
peligro (predictor de muerte aprendido), con estos parámetros:
  w_risk  costo extra de un paso = w_risk · (−log(1 − p_muerte))
  p_max   un paso con p_muerte ≥ p_max se prohíbe salvo que no haya otra ruta
"""
from __future__ import annotations

import heapq
import math

NAV_PARAMS = {"w_risk": (0.0, 60.0, 20.0), "p_max": (0.3, 1.0, 1.0)}
NAV_DEFAULT = {k: v[2] for k, v in NAV_PARAMS.items()}


class Navigator:
    def __init__(self, know, danger=None, P=NAV_DEFAULT, learn=True):
        self.know, self.danger, self.P, self.learn = know, danger, P, learn
        self.last = None
        self.last_dir = None

    def _blocked(self, st):
        K = self.know
        return [any(m >> t & 1 and K.is_blocking(t) for t in range(63)) for m in st.masks]

    def plan(self, st, goal, strict=True):
        """(costo, primera dirección) hacia goal; se puede terminar en goal aunque esté "bloqueado"."""
        W, N = st.W, len(st.masks)
        offs = (-W, 1, W, -1)
        blocked = self._blocked(st)
        risk, bad = {}, set()
        if self.danger is not None:
            cells = [j for j in range(N) if not blocked[j]]
            w, pmax = self.P["w_risk"], self.P["p_max"]
            for k, p in self.danger.probs(st, cells).items():
                risk[k] = -w * math.log(max(1e-4, 1 - p))
                if strict and p >= pmax:
                    bad.add(k)
        pos = st.pos
        best = {pos: 0.0}; first = {pos: -1}; pq = [(0.0, pos)]
        while pq:
            c, i = heapq.heappop(pq)
            if i == goal:
                return c, first[i]
            if c > best[i]:
                continue
            x, y = i % W, i // W
            for d in range(4):
                xx, yy = x + (d == 1) - (d == 3), y + (d == 2) - (d == 0)
                if not (0 <= xx < W and 0 <= yy < st.H):
                    continue
                j = i + offs[d]
                if (blocked[j] and j != goal) or (j, d) in bad:
                    continue
                nc = c + 1.0 + risk.get((j, d), 0.0)
                if nc < best.get(j, math.inf):
                    best[j] = nc; first[j] = d if i == pos else first[i]
                    heapq.heappush(pq, (nc, j))
        if strict and bad:
            return self.plan(st, goal, strict=False)     # sin ruta "segura": la menos mala
        return None

    def step(self, st, goal):
        """Acción para acercarse a goal (4 = quieto si no hay ruta). Aprende transitabilidad al vuelo."""
        W = st.W
        offs = (-W, 1, W, -1)
        if self.last is not None and self.learn:
            pos0, d, mask, same = self.last
            moved = st.pos == pos0 + offs[d]
            if moved or same:
                self.know.record_move(mask, moved)
        r = self.plan(st, goal)
        act = r[1] if r is not None and r[1] >= 0 else 4
        if act < 4 and 0 <= st.pos + offs[act] < len(st.masks):
            self.last = (st.pos, act, st.masks[st.pos + offs[act]], self.last_dir == act)
            self.last_dir = act
        else:
            self.last = None
        return act, r is not None


def shortest(st, know, goal):
    """Distancia sin considerar peligro (para medir cuánto alarga la ruta la prudencia)."""
    W, N = st.W, len(st.masks)
    offs = (-W, 1, W, -1)
    blocked = [any(m >> t & 1 and know.is_blocking(t) for t in range(63)) for m in st.masks]
    seen = {st.pos: 0}; fr = [st.pos]
    while fr:
        nx = []
        for i in fr:
            x, y = i % W, i // W
            for d in range(4):
                xx, yy = x + (d == 1) - (d == 3), y + (d == 2) - (d == 0)
                j = i + offs[d]
                if 0 <= xx < W and 0 <= yy < st.H and j not in seen and (not blocked[j] or j == goal):
                    seen[j] = seen[i] + 1
                    if j == goal:
                        return seen[j]
                    nx.append(j)
        fr = nx
    return None
