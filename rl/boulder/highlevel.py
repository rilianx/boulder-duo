"""Agente de alto nivel: elige destinos y le da órdenes al navegador (ObjectCubeNavigator).

Oráculo barato: un solo Dijkstra desde el avatar sobre el riesgo actual da, para cada casilla, el tiempo
estimado (pasos) y el riesgo acumulado del camino H = Σ −log(1 − p). La probabilidad de llegar vivo es e^(−H).
Puntaje de un destino = valor del tipo · e^(−H) − lam · tiempo, con el valor por tipo del agente genérico
(efectos aprendidos al tocar cada tipo, pesos ajustados con CEM). Sin nada que valga la pena: explorar la
casilla alcanzable menos visitada. El navegador cumple la orden con plazo T = 3·tiempo + 20; si no llega
(tiempo agotado o sin camino) el destino queda vetado un rato.
"""
from __future__ import annotations

import heapq
import math

from .generic import GenericAgent, value_params


class Commander:
    def __init__(self, know, values, nav, P=None):
        self.know, self.nav = know, nav
        # replan: cada cuántos ticks se reevalúa el destino (0 = solo al terminar la orden); margin: cuánto
        # mejor tiene que ser otro destino para cambiar (sin margen el agente titubea entre dos parecidos)
        self.P = {"lam": values.get("lam", 0.1), "w_oracle": 1.0, "tabu": 60, "min_score": 0.0,
                  "replan": 0, "margin": 0.2, **(P or {})}
        self.va = GenericAgent(values, know=know, learn=False)      # solo para _value()
        self.goal = None
        self.visits, self.tabu = {}, {}
        self.touch = None            # (tipos, puntaje, recursos, tipo de avatar, casilla) del último intento
        self.learn = self.P.get("learn", True)
        self.stats = {"orders": 0, "reached": 0, "timeout": 0, "unreachable": 0, "explore": 0, "switch": 0,
                      "vanished": 0, "invalid": 0}

    # ------------------------------------------------------------------ oráculo
    def oracle(self, st):
        """{casilla: (tiempo, H)} por el camino de menor tiempo + w·H desde el avatar."""
        K, W, N = self.know, st.W, len(st.masks)
        blocked = K.blocked_cells(st)
        p = self.nav.risk.grid(st.masks)
        haz = [-math.log(max(1e-4, 1 - float(p[j]))) for j in range(N)]
        pred = {}
        if self.nav.pred is not None:
            pred = self.nav.pred.probs(st, [j for j in range(N) if not blocked[j]])
        alpha, w = self.nav.P.get("alpha", 1.0), self.P["w_oracle"]
        offs = (-W, 1, W, -1)
        best = {st.pos: 0.0}
        info = {st.pos: (0, 0.0)}
        pq = [(0.0, st.pos)]
        while pq:
            c, i = heapq.heappop(pq)
            if c > best[i]:
                continue
            t, H = info[i]
            x, y = i % W, i // W
            for d in range(4):
                xx, yy = x + (d == 1) - (d == 3), y + (d == 2) - (d == 0)
                if not (0 <= xx < W and 0 <= yy < st.H):
                    continue
                j = i + offs[d]
                h = haz[j]
                if pred:
                    h = max(h, -math.log(max(1e-4, 1 - alpha * pred.get((j, d), 0.0))))
                nt, nH = t + 1, H + h
                if blocked[j]:                     # se puede terminar en una casilla bloqueada (tocarla)
                    if j not in best and (j not in info or nt < info[j][0]):
                        info[j] = (nt, nH)
                    continue
                nc = nt + w * nH
                if nc < best.get(j, math.inf):
                    best[j] = nc; info[j] = (nt, nH)
                    heapq.heappush(pq, (nc, j))
        return info

    # ------------------------------------------------------------------ elegir destino
    def choose(self, st):
        K = self.know
        info = self.oracle(st)
        targets, avatars, _ = value_params(st.types, K)
        # no perseguir lo que se mueve (categorías VGDL NPC = 3 y móvil = 6): la meta se escapa, y tocar un
        # enemigo suele matar; las metas son cosas quietas (recursos, puertas, salidas...)
        targets = [t for t in targets if st.types.get(t, ("", -1))[1] not in (3, 6)]
        vals = {t: self.va._value(t, st, avatars) for t in targets}
        best, choice = self.P["min_score"], None
        self._scores = {}
        for j, (t, H) in info.items():
            if j == st.pos or self.tabu.get(j, -1) > st.tick:
                continue
            m = st.masks[j]
            v = max((vals[ty] for ty in targets if m >> ty & 1), default=0.0)
            if v <= 0:
                continue
            s = v * math.exp(-H) - self.P["lam"] * t
            self._scores[j] = s
            if s > best:
                best, choice = s, (j, t)
        self._best_score = best if choice is not None else None
        if choice is None:                         # explorar
            blocked = K.blocked_cells(st)
            cand = [(self.visits.get(j, 0) * 5 + t, j, t) for j, (t, H) in info.items()
                    if j != st.pos and not blocked[j] and t >= 3 and self.tabu.get(j, -1) <= st.tick]
            if cand:
                _, j, t = min(cand)
                choice = (j, t)
                self.stats["explore"] += 1
        return choice

    # ------------------------------------------------------------------ política del puente
    def _learn_touch(self, st):
        """Efectos de tocar cada tipo (como el agente genérico): puntaje, recursos, avatar y, si se chocó, que
        tocarlo no terminó la partida (así la curiosidad por lo que bloquea se agota)."""
        if self.touch is None or not self.learn:
            return
        types, sc0, res0, at0, cell = self.touch
        K = self.know
        if st.pos == cell:
            K.record_touch(types, st.score - sc0, st.total_res() - res0, st.atype != at0)
            K.record_nonterminal(types, at0, res0)
        else:
            K.record_nonterminal(types, at0, res0)          # chocó: tocarlo tampoco terminó nada
        self.touch = None

    def __call__(self, st, br):
        self.know.observe_types(st)
        self._learn_touch(st)
        self.visits[st.pos] = self.visits.get(st.pos, 0) + 1
        if self.goal is not None:
            j, t0, limit = self.goal
            if st.pos == j:
                self.stats["reached"] += 1; self.goal = None
            elif self._goal_valuable and not self._goal_blocked0 and self.know.blocked_cells(st)[j]:
                # el mundo tapó la meta (p. ej. un diamante que cayó y quedó una roca): cancelar y vetar
                self.stats["invalid"] = self.stats.get("invalid", 0) + 1
                self.tabu[j] = st.tick + self.P["tabu"]; self.goal = None
            elif st.tick - t0 > limit:
                self.stats["timeout"] += 1; self.tabu[j] = st.tick + self.P["tabu"]; self.goal = None
            elif self.P["replan"] and self._goal_valuable and not self._valuable(st, j):
                self.stats["vanished"] += 1; self.goal = None      # el objeto de la meta ya no está
            elif self.P["replan"] and (st.tick - t0) % self.P["replan"] == 0 and st.tick > t0:
                old = self.goal
                c = self.choose(st)
                cur = self._scores.get(j)
                if c is not None and c[0] != j and self._best_score is not None and \
                        (cur is None or self._best_score > cur + self.P["margin"] * abs(cur)):
                    self.stats["switch"] += 1
                    self._set_goal(st, c)
                else:
                    self.goal = old
        if self.goal is None:
            c = self.choose(st)
            if c is None:
                return 4
            self._set_goal(st, c)
        act, ok = self.nav.step(st, self.goal[0], br)
        if not ok:
            self.stats["unreachable"] += 1
            self.tabu[self.goal[0]] = st.tick + self.P["tabu"]
            self.goal = None
            return 4
        if act < 4:
            K, W = self.know, st.W
            j = st.pos + (-W, 1, W, -1)[act]
            if 0 <= j < len(st.masks):
                m = st.masks[j]
                touched = [t for t in range(63) if m >> t & 1 and t not in K.avatar_types and t not in K.floor]
                if touched:
                    self.touch = (touched, st.score, st.total_res(), st.atype, j)
        return act

    def _set_goal(self, st, c):
        j, t = c
        limit = 3 * t + 20
        self.goal = (j, st.tick, limit)
        self._goal_valuable = self._valuable(st, j)
        self._goal_blocked0 = self.know.blocked_cells(st)[j]      # ya bloqueada al elegirla (p. ej. una puerta)
        self.nav.deadline = st.tick + limit
        self.stats["orders"] += 1

    def _valuable(self, st, j):
        """¿La casilla j tiene algún tipo con valor positivo? (False para una meta de exploración)."""
        targets, avatars, _ = value_params(st.types, self.know)
        m = st.masks[j]
        return any(m >> t & 1 and self.va._value(t, st, avatars) > 0 for t in targets)

    def end(self, won):
        if self.touch is not None and self.learn and won is not None:
            types, _, res, atype, _ = self.touch
            self.know.record_terminal_touch(types, atype, res, won == 1)   # ganó o perdió al tocarlo
        self.touch = None
        self.goal = None
        self.nav.last = None
