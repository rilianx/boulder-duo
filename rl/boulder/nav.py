"""El A* como subordinado: recibe órdenes "ve a la casilla X" de un agente de alto nivel y las cumple sin morir.

Navigator.step(estado, destino) devuelve la acción del tick; el resultado de la orden lo decide quien la
emite: llegó (el avatar está en el destino), murió (la partida terminó perdiendo), inalcanzable (no hay ruta)
o tiempo agotado. No sabe nada de qué conviene en el juego: solo qué se puede pisar (aprendido) y dónde hay
peligro (predictor de muerte aprendido), con estos parámetros:
  w_risk  costo extra de un paso = w_risk · (−log(1 − p_muerte))
  p_max   un paso con p_muerte ≥ p_max se prohíbe salvo que no haya otra ruta
  shield  si > 0, escudo de un paso: antes de moverse pregunta al modelo del juego (4 copias, 3 ticks) cuán
          mortal es cada movimiento y quedarse quieto; si el paso elegido tiene riesgo ≥ shield y hay una
          opción más segura (esperar primero, o hacerse a un lado), la toma. Así puede dejar pasar un
          enemigo o una roca en vez de meterse.
"""
from __future__ import annotations

import heapq
import math

NAV_PARAMS = {"w_risk": (0.0, 60.0, 20.0), "p_max": (0.3, 1.0, 1.0), "shield": (0.0, 1.0, 0.0)}
NAV_DEFAULT = {k: v[2] for k, v in NAV_PARAMS.items()}


class SurpriseLog:
    """Contradicciones entre lo que el conocimiento esperaba y lo que pasó, agrupadas por tipos de objeto.

    move:  intentó entrar a una casilla; ¿esperaba moverse (pisable y sin giro pendiente) y se movió?
    drift: estaba quieto; ¿esperaba que lo arrastraran (objeto que arrastra debajo) y se desplazó?
    death: murió; ¿la casilla a la que había entrado tenía riesgo aprendido bajo (< 0,2)?
    """

    def __init__(self):
        self.d = {}                 # tipo de evento → (tipos...) → [n, sorpresas]

    def add(self, kind, types, surprise):
        c = self.d.setdefault(kind, {}).setdefault(tuple(sorted(types)), [0, 0])
        c[0] += 1; c[1] += int(surprise)

    def merge(self, o):
        for k, dd in o.items():
            for t, (n, s) in dd.items():
                c = self.d.setdefault(k, {}).setdefault(tuple(t), [0, 0]); c[0] += n; c[1] += s

    def explained(self):
        n = sum(v[0] for dd in self.d.values() for v in dd.values())
        s = sum(v[1] for dd in self.d.values() for v in dd.values())
        return 1 - s / max(n, 1), n


class Navigator:
    def __init__(self, know, danger=None, P=NAV_DEFAULT, learn=True):
        self.know, self.danger, self.P, self.learn = know, danger, P, learn
        self.last = None
        self.last_dir = None

    def _blocked(self, st):
        return self.know.blocked_cells(st)

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

    def step(self, st, goal, br=None):
        """Acción para acercarse a goal (4 = quieto si no hay ruta). Aprende transitabilidad al vuelo."""
        W = st.W
        offs = (-W, 1, W, -1)
        log = getattr(self, "surprise", None)
        if self.last is not None and (self.learn or log is not None):
            pos0, d, mask, same, res, free = self.last
            moved = st.pos == pos0 + offs[d]
            W_ = st.W
            jump = abs(st.pos % W_ - pos0 % W_) + abs(st.pos // W_ - pos0 // W_) > 2
            if jump:                                     # teletransporte: lo que había en la casilla lleva lejos
                if self.learn:
                    self.know.record_jump(mask, st.masks[st.pos])
                moved = True
            if log is not None:
                expect = free and (same or not self.know.turn_cost)
                types = [t for t in range(63) if mask >> t & 1 and t not in self.know.avatar_types]
                log.add("move", types, expect != moved)
            if self.learn:
                if moved or same:
                    self.know.record_move(mask, moved, res)
                if not same and free:
                    self.know.record_turn(moved)
        if getattr(self, "_waited", None) is not None and (self.learn or log is not None):
            p0, otypes = self._waited
            moved = abs(st.fx - p0[0]) + abs(st.fy - p0[1]) > 0.01
            if otypes and self.learn:
                self.know.record_carry(otypes, moved)
            if log is not None:
                log.add("drift", otypes, bool(otypes & self.know.carriers()) != moved)
        r = self.plan(st, goal)
        act = r[1] if r is not None and r[1] >= 0 else 4
        thr = self.P.get("shield", 0.0)
        if thr > 0 and br is not None and act < 4:
            lab = br.labels(3, 4)                      # riesgo real de ↑ → ↓ ← y quieto según el modelo
            if lab[act] >= thr:
                blocked = self._blocked(st)
                opts = [4] + [d for d in range(4) if 0 <= st.pos + offs[d] < len(st.masks) and not blocked[st.pos + offs[d]]]
                safest = min(opts, key=lambda d: (lab[d], d != 4))   # a igual riesgo, esperar
                if lab[safest] < lab[act]:
                    act = safest
                    self.stats_wait = getattr(self, "stats_wait", 0) + (safest == 4)
        if act < 4 and 0 <= st.pos + offs[act] < len(st.masks):
            j = st.pos + offs[act]
            free = not self.know.blocked_cells(st)[j]
            self.last = (st.pos, act, st.masks[j], self.last_dir == act, dict(st.res), free)
            self._entered = st.masks[j]
            self.last_dir = act
        else:
            self.last = None
        # quieto: ¿qué objetos comparten la casilla del avatar? (para aprender si lo arrastran)
        if act == 4:
            ax, ay = st.pos % st.W, st.pos // st.W
            self._waited = ((st.fx, st.fy), {t for t, x, y in getattr(st, "objects", {}).values()
                                     if round(x) == ax and round(y) == ay})
        else:
            self._waited = None
        return act, r is not None


class MCTSNavigator:
    """Referencia con el mismo presupuesto: UCT en Java con el modelo del juego (Bridge.mcts), yendo a goal.

    Recibe el mismo campo de distancias sin peligro que nuestro A* (transitabilidad aprendida) para valorar
    las simulaciones que no llegan. Parámetros: ms (tiempo por decisión) y depth (profundidad de simulación)."""

    def __init__(self, know, P):
        self.know, self.P = know, P
        self.last = None

    def step(self, st, goal, br):
        from .cube import CubeNavigator
        blocked = self.know.blocked_cells(st)
        dist = CubeNavigator._dist_to_goal(self, st, goal, blocked)
        if dist[st.pos] is None:
            return 4, False
        br.mcts(goal, dist, self.P.get("ms", 35.0), int(self.P.get("depth", 10)))
        return None, True


def shortest(st, know, goal):
    """Distancia sin considerar peligro (para medir cuánto alarga la ruta la prudencia)."""
    W, N = st.W, len(st.masks)
    offs = (-W, 1, W, -1)
    blocked = know.blocked_cells(st)
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
