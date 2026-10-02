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
        # el presupuesto incluye seguimiento y cubo; el replanteo sin plazo (_dl_off) tiene su propio tiempo
        t_start = time.perf_counter() if getattr(self, "_dl_off", False) else (getattr(self, "_t0", None) or time.perf_counter())
        budget = self.P.get("budget_ms", 25.0) / 1000
        Rw = int(self.P.get("win", 8))
        cube = self._cube(st)                                # cube[k] = máscaras dentro de k+1 ticks
        W, Hh, N = st.W, st.H, len(st.masks)
        K = self.know
        offs = (-W, 1, W, -1, 0)
        H = len(cube)
        bm = K.blocking_bits(getattr(st, "res", None))
        C = np.array(cube, dtype=np.int64) if H else np.zeros((0, N), np.int64)
        blocked = (C & bm) != 0                              # [H, N]
        R = self._adjust_risk([self.risk.grid(c) for c in cube])
        self._R = R                                          # riesgo por casilla y tick (lo usa el alto nivel)
        now_blocked = (np.array(st.masks, dtype=np.int64) & bm) != 0
        dist = self._dist_to_goal(st, goal, now_blocked)
        if goal != getattr(self, "_ugoal", None):
            self._ugoal, self._unreach = goal, 0
        if dist[st.pos] is None:
            # el camino se puede cerrar por un rato (una roca que cae o rebota): esperar; "inalcanzable"
            # solo tras 10 ticks sin camino (en total, en esta orden)
            self._unreach += 1
            return None if self._unreach >= 10 else (math.inf, self._safest_move(st, R, now_blocked))
        # impaciencia: si el avatar no se acerca al destino, el peso del riesgo baja a la mitad cada
        # P["patience"] ticks (piso 0,1), para no esperar para siempre un peligro que nunca se va
        if goal != getattr(self, "_goal", None):
            self._goal, self._bestd, self._stall = goal, math.inf, 0
        if dist[st.pos] < self._bestd:
            self._bestd, self._stall = dist[st.pos], 0
        else:
            self._stall += 1
        pat = self.P.get("patience", 0)
        wmul = max(0.1, 0.5 ** (self._stall // pat)) if pat else 1.0
        tc = K.turn_cost if self.P.get("turns", 1) else 0
        ax, ay = st.pos % W, st.pos // W
        inwin = lambda c: abs(c % W - ax) <= Rw and abs(c // W - ay) <= Rw
        # plazo: con P["deadline"] el navegador conoce el tick límite de la orden (self.deadline) y minimiza
        # el riesgo sujeto a llegar antes; el tiempo solo desempata (time_w). Si ninguna ruta llega a
        # tiempo, planifica como siempre (la más barata en tiempo + riesgo).
        dl = bool(self.P.get("deadline")) and getattr(self, "deadline", None) is not None \
            and not getattr(self, "_dl_off", False)
        rem = self.deadline - st.tick if dl else math.inf
        tw = self.P.get("time_w", 0.3) if dl else 1.0
        if dl:
            wmul = 1.0
            if dist[st.pos] > rem:
                dl, rem, tw = False, math.inf, 1.0
        w = self.P["w_risk"] * wmul
        # riesgo medio por paso más allá del horizonte (en la ventana, en el último tick simulado): sin esto,
        # con plazo, al A* le conviene dejar lo peligroso para después del horizonte, donde "no cuesta"
        hz_tail = 0.0
        if dl and H:
            cells = [j for j in range(N) if inwin(j) and not now_blocked[j]]
            if cells:
                # percentil 25: el riesgo de ir por lo razonablemente seguro, no el promedio (en Frogs la mitad
                # de la ventana es agua mortal y el promedio haría "carísimo" todo camino que pase el horizonte)
                hz_tail = float(np.percentile(-np.log(np.clip(1 - R[H - 1][cells], 1e-4, 1)), 25))
        pred = {}
        if self.pred is not None:
            pred = self.pred.probs(st, [j for j in range(N) if not now_blocked[j] and inwin(j)])
        start = (st.pos, 0)
        best = {start: 0.0}; first = {start: -1}
        facing = {start: self.last_dir}                     # dirección del avatar (si gira antes de moverse)
        pq = [(tw * dist[st.pos], 0.0, st.pos, 0)]
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
                return (best_partial[0], best_partial[1]) if best_partial[1] is not None else (math.inf, -1)
            if k == H or not inwin(c):                       # fuera del horizonte o de la ventana: completar
                if dist[c] is not None and k + dist[c] <= rem:
                    node = (goal, -1)
                    ng = g + (tw + w * hz_tail) * dist[c]
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
                j = c + offs[d] if d < 4 else self._carried_to(k, c)
                if j is None:
                    continue
                if blocked[k][j] and j != goal:
                    continue
                if dist[j] is None:
                    continue
                # un avatar orientado gasta un tick girando: se queda en c un tick y recién después entra a j
                turn = tc and d < 4 and facing.get((c, k)) is not None and facing[(c, k)] != d and k + 1 < H
                kk = k + 1 if turn else k
                if turn and blocked[kk][j] and j != goal:
                    continue
                p = float(R[kk][j])
                if d < 4 and pred and k < self.P.get("pred_k", 99):
                    # pred_k: hasta qué tick se usa el predictor; mira la grilla de ahora, así que para
                    # peligros que se mueven solo vale cerca del presente (el resto lo cubre el cubo)
                    # alpha: cuánto pesa el predictor ("¿muero si entro y me quedo?") frente al cubo;
                    # alto donde el peligro lo provoca el avatar (Boulder Dash), bajo con peligro que pasa (Frogs)
                    p = max(p, self.P.get("alpha", 1.0) * pred.get((j, d), 0.0))
                if kk + 1 + dist[j] > rem:                   # ya no llega a tiempo por aquí
                    continue
                # restricción de riesgo: con plazo, un paso con p > eps no se toma (mejor agotar el tiempo que
                # tirarse al agua para "cumplir"); si así no hay ruta, se planifica sin plazo
                if dl and p > self.P.get("eps", 0.25):
                    continue
                ng = g + tw + w * -math.log(max(1e-4, 1 - p))
                if turn:
                    ng += tw + w * -math.log(max(1e-4, 1 - float(R[k][c])))
                node = (j, kk + 1)
                if ng < best.get(node, math.inf):
                    best[node] = ng
                    first[node] = d if k == 0 else first[(c, k)]
                    facing[node] = d if d < 4 else facing.get((c, k))
                    heapq.heappush(pq, (ng + tw * dist[j], ng, j, kk + 1))
        if dl:                                               # nada llega a tiempo: planificar sin plazo
            self._dl_off = True
            try:
                return self.plan(st, goal, strict)
            finally:
                self._dl_off = False
        # sin salida dentro del horizonte (p. ej. objetos extrapolados tapan todo): el destino sigue siendo
        # alcanzable en el mapa actual, así que se acerca lo mejor posible o espera; no es "inalcanzable"
        return (math.inf, best_partial[1] if best_partial[1] is not None else -1)

    def _adjust_risk(self, R):
        """Gancho: riesgo por casilla y tick ya calculado; las subclases pueden sumarle otros peligros."""
        return R

    def _carried_to(self, k, c):
        """Dónde queda el avatar si espera en c durante el tick k (lo mueve un objeto que arrastra)."""
        return c

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

    def _safest_move(self, st, R, blocked, k=4):
        """Sin camino a la meta no conviene quedarse quieto sin más (algo puede venir persiguiendo): el
        movimiento (o quedarse, −1) con menos riesgo previsto en esa casilla durante los próximos k ticks."""
        if not len(R):
            return -1
        W, N = st.W, len(st.masks)
        x, y = st.pos % W, st.pos // W
        best, act = None, -1
        for d, (dx, dy) in [(-1, (0, 0)), (0, (0, -1)), (1, (1, 0)), (2, (0, 1)), (3, (-1, 0))]:
            if not (0 <= x + dx < W and 0 <= y + dy < st.H):
                continue
            c = st.pos + dy * W + dx
            if d >= 0 and blocked[c]:
                continue
            h = sum(-math.log(max(1e-4, 1 - float(R[i][c]))) for i in range(min(k, len(R))))
            if best is None or h < best - 1e-6:
                best, act = h, d
        return act

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
