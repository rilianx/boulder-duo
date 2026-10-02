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
import random

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
        # usar (disparar, espada...): se aprende qué hace comparando qué desaparece al usar y al no usar
        self.P = {"use": True, "use_eps": 0.05, "use_R": 6, "use_lag": 10, "use_thr": 0.3, **self.P}
        self._probes = []
        self._vanish_ds = {}
        # empujar (cajas de Sokoban): se aprende qué se corre al entrar y qué pasa al empujarlo contra cada cosa
        self.P = {"push": True, "push_new": 0.5, "push_states": 4000, "push_lam": 0.01, **self.P}
        # una mecánica apagada (ablación) apaga también su acción: no se usa ni se empuja al azar
        if "usar" in know.apagadas:
            self.P["use"] = False
        if "empujar" in know.apagadas:
            self.P["push"] = False
        know.avoid_push = self.P["push"]
        self.plan, self._plan_expect, self._mv = None, None, None
        self.rng = random.Random(self.P.get("seed", 0))
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
            ax, ay = st.pos % W, st.pos // W             # solo cerca del avatar: el predictor es caro
            pred = self.nav.pred.probs(st, [j for j in range(N) if not blocked[j]
                                            and abs(j % W - ax) + abs(j // W - ay) <= 6])
        alpha, w = self.nav.P.get("alpha", 1.0), self.P["w_oracle"]
        offs = (-W, 1, W, -1)
        best = {st.pos: 0.0}
        info = {st.pos: (0, 0.0)}
        self._prev = prev = {st.pos: None}
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
                        info[j] = (nt, nH); prev[j] = i
                    continue
                nc = nt + w * nH
                if nc < best.get(j, math.inf):
                    best[j] = nc; info[j] = (nt, nH); prev[j] = i
                    heapq.heappush(pq, (nc, j))
        return info

    # ------------------------------------------------------------------ elegir destino
    def choose(self, st):
        K = self.know
        info = self.oracle(st)
        targets, avatars, _ = value_params(st.types, K)
        # no perseguir lo que se mueve (categorías VGDL NPC = 3 y móvil = 6): la meta se escapa, y tocar un
        # enemigo suele matar; las metas son cosas quietas (recursos, puertas, salidas...)
        # excepción (P["chase_movers"]): perseguir un tipo que se mueve si tocarlo dio puntos o recursos y casi
        # nunca mató (p. ej. las cabras de Chase), según lo aprendido
        def safe_mover(t):
            ds, dr, da, pd, n = K.effect(t)
            return self.P.get("chase_movers", False) and n >= 3 and (ds > 0 or dr > 0) and pd < 0.1
        # lo que se mueve = lo que se vio moverse (no la categoría VGDL: la miel es "móvil" y nunca se mueve)
        def moves(t):
            return st.types.get(t, ("", -1))[1] == 3 or sum(K.move_dirs.get(t, {}).values()) >= 3
        targets = [t for t in targets if not moves(t) or safe_mover(t)]
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
        if choice is not None:
            # entre metas de igual puntaje, la de índice mayor (más abajo y a la derecha): en Boulder Dash junta
            # primero lo de abajo y las rocas caen en huecos inofensivos (era todo el aporte de la "previsión")
            best, j = max((sc, j) for j, sc in self._scores.items() if sc > self.P["min_score"])
            choice = (j, info[j][0])
        self._best_score = best if choice is not None else None
        # opciones que proponen las mecánicas activas (apuntar, portal, abrir camino), en orden
        for m in self._opciones():
            if choice is not None:
                break
            choice = m.opcion(self, st, info, vals, targets)
        if choice is None:                         # explorar
            blocked = K.blocked_cells(st)
            cand = [(self.visits.get(j, 0) * 5 + t, j, t) for j, (t, H) in info.items()
                    if j != st.pos and not blocked[j] and t >= 3 and self.tabu.get(j, -1) <= st.tick]
            if cand:
                _, j, t = min(cand)
                choice = (j, t)
                self.stats["explore"] += 1
        return choice

    def _opciones(self):
        return sorted((m for m in self.know.mecs.values() if m.activa and getattr(m, "orden_opcion", None) is not None),
                      key=lambda m: m.orden_opcion)

    # ------------------------------------------------------------------ empujar
    def _learn_push(self, st):
        """Tras un paso: ¿el objeto que había en la casilla a la que entró el avatar se corrió en esa dirección,
        desapareció (p. ej. cayó en un hoyo) o se trabó? Se anota según qué había adelante."""
        if self._mv is None or not self.learn:
            return
        pos0, act, objs, masks0, sc0, turned = self._mv
        self._mv = None
        self.know.emitir("empuje", st=st, pos0=pos0, act=act, objs=objs, masks0=masks0, sc0=sc0,
                         turned=turned, abits=self._abits())

    def _plan_step(self, st):
        if st.pos != self._plan_expect:
            self.stats["push_fail"] = self.stats.get("push_fail", 0) + 1; self.plan = None
            return None
        if not self.plan:
            self.stats["push_done"] = self.stats.get("push_done", 0) + 1; self.plan = None
            return None
        act, exp = self.plan.pop(0)
        if self.know.turn_cost and self.nav.last_dir != act:
            self.plan.insert(0, (act, exp)); exp = st.pos       # primero gira sin moverse
        self._plan_expect = exp
        self._note_move(st, act)
        self.nav.last_dir = act
        return act

    def _abits(self):
        return sum(1 << t for t in self.know.avatar_types)

    def _note_move(self, st, act):
        W = st.W
        objs = {oid: (t, int(round(y)) * W + int(round(x))) for oid, (t, x, y) in st.objects.items()
                if abs(x - st.fx) + abs(y - st.fy) <= 1.5}
        turned = self.know.turn_cost and self.nav.last_dir is not None and self.nav.last_dir != act
        self._mv = (st.pos, act, objs, st.masks, st.score, turned)

    # ------------------------------------------------------------------ política del puente
    def _learn_touch(self, st):
        """Efectos de tocar cada tipo (como el agente genérico): puntaje, recursos, avatar y, si se chocó, que
        tocarlo no terminó la partida (así la curiosidad por lo que bloquea se agota)."""
        if self.touch is None or not self.learn:
            return
        types, sc0, res0, at0, cell, alltypes = self.touch
        self.know.emitir("toque", st=st, types=types, alltypes=alltypes, entro=st.pos == cell, cell=cell,
                         dscore=st.score - sc0, dres=st.total_res() - res0, datype=st.atype != at0,
                         at0=at0, res0=res0, fuente="cmd")
        self.touch = None

    # ------------------------------------------------------------------ usar
    def _keys(self, dx, dy, facing, atype=None):
        return self.know.claves_usar(dx, dy, facing, atype)

    def _lift(self, t, dx, dy, facing, atype):
        return self.know.efecto_usar(t, dx, dy, facing, atype)

    def _probe(self, st, used):
        snap = {oid: (t, x, y) for oid, (t, x, y) in st.objects.items() if t not in self.know.avatar_types
                and abs(x - st.fx) <= self.P["use_R"] and abs(y - st.fy) <= self.P["use_R"]}
        if snap:
            self._probes.append((st.tick, used, st.fx, st.fy, self.nav.last_dir, snap, st.score, st.atype))

    def _resolve_probes(self, st):
        K, keep = self.know, []
        for pr in self._probes:
            tick, used, ax, ay, facing, snap, sc0, at = pr
            if st.tick - tick < self.P["use_lag"]:
                keep.append(pr); continue
            K.emitir("sonda_usar", st=st, used=used, ax=ax, ay=ay, facing=facing, snap=snap, atype=at,
                     vanish_ds=self._vanish_ds)
        self._probes = keep

    def _danger_near(self, st, R, thr=0.3):
        W = st.W
        x, y = st.pos % W, st.pos // W
        for k in range(min(3, len(R))):
            for dx, dy in ((0, 0), (0, -1), (1, 0), (0, 1), (-1, 0)):
                if 0 <= x + dx < W and 0 <= y + dy < st.H and float(R[k][st.pos + dy * W + dx]) > thr:
                    return True
        return False

    def _use_eps(self):
        """Probabilidad de usar al azar para aprender: baja a un décimo cuando ya se probó bastante y usar no
        hizo desaparecer nada más que sin usar (en Boulder Dash, por ejemplo, solo gasta ticks)."""
        if getattr(self, "_eps_cache", None) is None:
            K = self.know
            n = sum(v[1] for d in K.use_kill.values() for v in d.values())
            lift = max((K.use_lift(t, k) for t, d in K.use_kill.items() for k in d), default=0.0)
            self._eps_cache = self.P["use_eps"] * (0.1 if n >= 300 and lift < 0.05 else 1.0)
        return self._eps_cache

    def _use_ev(self, st, ax, ay, facing, dt=0):
        """Valor esperado de usar desde (ax, ay) mirando hacia `facing`, dentro de dt ticks (los objetos se
        extrapolan con la velocidad que estima el rastreador: se apunta adonde estarán, no adonde están)."""
        K, ev = self.know, 0.0
        for oid, (t, x, y) in st.objects.items():
            if t in K.avatar_types:
                continue
            if dt:
                pth = getattr(self.nav, "_paths", {}).get(oid) if self.P.get("aim_paths", True) else None
                if pth:                                    # perseguidor / fugitivo: adonde lo lleva su tendencia
                    x, y = pth[max(1, min(int(dt), len(pth))) - 1]
                else:
                    vx, vy = self.nav.track.velocity(oid)
                    x, y = x + vx * dt, y + vy * dt
            lift = self._lift(t, int(round(x - ax)), int(round(y - ay)), facing, st.atype)
            if lift > 0:
                v = K.use_value(t)
                a = K.attractor(t)
                if a is not None and a[0] >= 0 and a[1] > 0 and K.extinct_loss(a[0]):
                    v += self.P.get("protect", 1.0)      # va hacia algo que hay que proteger: eliminarlo vale más
                ev += lift * v
        return ev

    def __call__(self, st, br):
        self.know.observe_types(st)
        self._last_st = st
        if self.learn and st.tick % 50 == 25:              # muestras de mitad de partida (para el fin por conteo)
            self.know.emitir("mitad", st=st)
        self._learn_touch(st)
        if self.P["push"]:
            self._learn_push(st)
        if self.P["use"]:
            # qué desapareció este tick y cuánto cambió el puntaje justo ahora (para el valor de usar)
            prev = getattr(self, "_prev_objs", None)
            if prev is not None:
                gone = [o for o in prev if o not in st.objects]
                if gone:
                    ds = (st.score - self._prev_score) / len(gone)
                    for o in gone:
                        self._vanish_ds[o] = ds
            self._prev_objs, self._prev_score = set(st.objects), st.score
            self._resolve_probes(st)
            eps = self._use_eps()
            R = getattr(self.nav, "_R", None)              # no experimentar con peligro cerca: es gastar un tick
            if R is not None and len(R) and self._danger_near(st, R):
                eps = 0.0
            if self.learn and self.rng.random() < eps:                     # explorar: usar al azar...
                self._probe(st, True)
                return "use"
            if self.learn and self.rng.random() < eps:                     # ...y la comparación sin usar
                self._probe(st, False)
            danger_here = R is not None and len(R) and any(float(R[k][st.pos]) > 0.3 for k in range(min(6, len(R))))
            if not danger_here and self._use_ev(st, st.fx, st.fy, self.nav.last_dir) > self.P["use_thr"]:
                self.stats["use"] = self.stats.get("use", 0) + 1
                self._probe(st, True)
                return "use"
        self.visits[st.pos] = self.visits.get(st.pos, 0) + 1
        self._pos0, self._pos_last = getattr(self, "_pos_last", None), st.pos
        if self.plan is not None:                          # siguiendo un plan de empujes
            act = self._plan_step(st)
            if act is not None:
                return act
        if self.goal is not None:
            j, t0, limit = self.goal
            jumped = self._pos0 is not None and abs(st.pos % st.W - self._pos0 % st.W) + \
                abs(st.pos // st.W - self._pos0 // st.W) > 2
            if st.pos == j or jumped:                      # llegó (o entró al teletransporte de la meta)
                self.stats["reached"] += 1; self.goal = None
            elif self._goal_valuable and not self._goal_blocked0 and self.know.blocked_cells(st)[j]:
                # el mundo tapó la meta (p. ej. un diamante que cayó y quedó una roca): cancelar y vetar
                self.stats["invalid"] = self.stats.get("invalid", 0) + 1
                self.tabu[j] = st.tick + self.P["tabu"]; self.goal = None
            elif st.tick - t0 > limit:
                self.stats["timeout"] += 1; self.tabu[j] = st.tick + self.P["tabu"]; self.goal = None
            elif self.P["replan"] and self._goal_valuable and not self._valuable(st, j):
                self.stats["vanished"] += 1; self.goal = None      # el objeto de la meta ya no está
            elif self.P["replan"] and (st.tick - t0) % self.P["replan"] == 0 and st.tick > t0 \
                    and self._goal_t >= self.P.get("replan_min_t", 0):   # solo órdenes largas
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
            if self.P["push"]:
                pp = self.know.plan_empujes(self, st)
                if pp is not None and (c is None or self._best_score is None or pp[0] > self._best_score):
                    self.stats["push"] = self.stats.get("push", 0) + 1
                    self.plan, self._plan_expect = pp[1], st.pos
                    act = self._plan_step(st)
                    if act is not None:
                        return act
            if c is None:
                return 4
            self._set_goal(st, c)
        act, ok = self.nav.step(st, self.goal[0], br)
        if not ok:
            self.stats["unreachable"] += 1
            self.tabu[self.goal[0]] = st.tick + self.P["tabu"]
            self.goal = None
            return 4
        if act < 4 and self.P["push"]:
            self._note_move(st, act)
        if act < 4:
            K, W = self.know, st.W
            j = st.pos + (-W, 1, W, -1)[act]
            if 0 <= j < len(st.masks):
                m = st.masks[j]
                touched = [t for t in range(63) if m >> t & 1 and t not in K.avatar_types and t not in K.floor]
                alltypes = [t for t in range(63) if m >> t & 1 and t not in K.avatar_types]
                if alltypes:
                    self.touch = (touched, st.score, st.total_res(), st.atype, j, alltypes)
        return act

    def _set_goal(self, st, c):
        j, t = c
        limit = 3 * t + 20
        self.goal = (j, st.tick, limit)
        self._goal_valuable = self._valuable(st, j)
        self._goal_t = t
        self._goal_blocked0 = self.know.blocked_cells(st)[j]      # ya bloqueada al elegirla (p. ej. una puerta)
        self.nav.deadline = st.tick + limit
        self.stats["orders"] += 1

    def _valuable(self, st, j):
        """¿La casilla j tiene algún tipo con valor positivo? (False para una meta de exploración)."""
        targets, avatars, _ = value_params(st.types, self.know)
        m = st.masks[j]
        return any(m >> t & 1 and self.va._value(t, st, avatars) > 0 for t in targets)

    def end(self, won):
        if self.learn and won is not None:                 # cómo terminó: tiempo, conteos, último toque
            tocado = None if self.touch is None else (self.touch[0], self.touch[3], self.touch[2])
            self.know.emitir("fin", st=getattr(self, "_last_st", None), gano=won, tocado=tocado, ctx={})
        self.touch = None
        self.goal = None
        self.plan, self._mv, self._pos_last = None, None, None
        self._eps_cache = None
        self._last_st = None
        self._prev_objs = None
        self._vanish_ds = {}
        self.nav.last = None
