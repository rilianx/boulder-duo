"""Acciones de alto nivel: la política elige un token y A* con costos de peligro lleva al PC hasta él.

Qué significa elegir cada token:
  - propio (0): esperar hasta 3 ticks;
  - gema: ir a tomarla (dentro o fuera de pantalla);
  - salida: ir a ella (solo válida con la cuota cumplida);
  - roca: ponerse al lado y empujarla (hacia el lado libre; si ambos, el más barato);
  - refugio: ir a una casilla segura cercana (4 candidatas, agregadas como tokens extra).
Enemigos y explosiones no se pueden elegir. La acción termina al llegar, si el destino desaparece o
se vuelve inalcanzable, si la casilla del PC se vuelve peligrosa, o a los 40 ticks.

Recompensas por tick iguales a BoulderEnv, sin el premio por acercarse (A* ya navega). La recompensa
de una acción es la suma descontada Σ γ^k r_k y `info["ticks"]` da su duración K para el bootstrap γ^K.
"""
from __future__ import annotations

import heapq
import math
import random

import numpy as np

from .astar import hazard_map, plan
from .sim import DIRT, E, EXIT, GEM, OFF, ROCK, STAY, W, H, Sim
from .tokens import N_FEATURES, Tokenizer

N_MACRO_FEATURES = N_FEATURES + 3      # + refugio, elegible, costo A* hasta el destino / 40
MAX_MACRO_TICKS = 40
WAIT_TICKS = 3
N_REFUGE = 4


def cost_map(sim: Sim, hazard: float, hz):
    """Costo A* (Dijkstra) desde el PC a toda casilla transitable, con las mismas reglas que plan()."""
    g = sim.grid
    a = sim.agent
    start = a.y * W + a.x
    best = {start: 0.0}
    pq = [(0.0, start)]
    while pq:
        c, i = heapq.heappop(pq)
        if c > best[i]:
            continue
        above = g[i - W] in (ROCK, GEM)
        for d in range(4):
            j = i + OFF[d]
            t = g[j]
            if not (t == E or t == DIRT or t == GEM):
                continue
            nc = c + 1.0 + (hazard if hz[j] else 0.0) + (hazard if d == 2 and above else 0.0)
            if nc < best.get(j, math.inf):
                best[j] = nc
                heapq.heappush(pq, (nc, j))
    return best


class MacroEnv:
    def __init__(self, levels=range(1, 13), seed=None, max_tokens=32, hazard=25.0, gamma=0.99):
        self.levels = list(levels)
        self.rand = random.Random(seed)
        self.sim = Sim()
        self.max_tokens = max_tokens
        self.tok = Tokenizer(max_tokens - N_REFUGE)
        self.hazard = hazard
        self.gamma = gamma

    @property
    def obs_shape(self):
        return self.max_tokens, N_MACRO_FEATURES

    # ------------------------------------------------------------ observación y opciones
    def _obs(self):
        s = self.sim
        base, bmask = self.tok.encode(s)
        T, F = self.max_tokens, N_MACRO_FEATURES
        out = np.zeros((T, F), np.float32)
        out[:base.shape[0], :N_FEATURES] = base
        mask = np.zeros(T, bool)
        mask[:base.shape[0]] = bmask
        hz = hazard_map(s)
        cost = cost_map(s, self.hazard, hz)
        a = s.agent
        opts = []                                # por token: (tipo, destino, extra)
        for n, (t, j) in enumerate(self.tok.last_meta):
            opt = None
            if n == 0:
                opt = ("wait", j, 0.0)
            elif t == GEM and j in cost:
                opt = ("goto", j, cost[j])
            elif t == EXIT and s.exit_open():
                c = min((cost.get(j + o, math.inf) for o in OFF), default=math.inf)
                if c < math.inf:
                    opt = ("goto", j, c + 1)
            elif t == ROCK and not s.fall[j]:
                best = None
                for push, stand in ((3, j + 1), (1, j - 1)):   # empujar ← desde la derecha, → desde la izquierda
                    if s.grid[j + OFF[push]] == E and stand in cost and (best is None or cost[stand] < best[2]):
                        best = (push, stand, cost[stand])
                if best:
                    opt = ("push", best[1], best[2], best[0], j)
            opts.append(opt)
        # refugios: la casilla segura más cercana en cada dirección dominante (←, →, ↑, ↓)
        n0 = len(self.tok.last_meta)
        sectors = {}
        for j, c in cost.items():
            if hz[j] or s.grid[j - W] in (ROCK, GEM) or s.grid[j] not in (E, DIRT):
                continue
            dx, dy = j % W - a.x, j // W - a.y
            if abs(dx) + abs(dy) < 2:
                continue
            sec = (1 if dx > 0 else 3) if abs(dx) >= abs(dy) else (2 if dy > 0 else 0)
            if sec not in sectors or c < sectors[sec][1]:
                sectors[sec] = (j, c)
        for k, (sec, (j, c)) in enumerate(sorted(sectors.items())[:N_REFUGE]):
            row = out[n0 + k]
            x, y = j % W, j // W
            row[8] = (x - a.x) / 8
            row[9] = (y - a.y) / 6
            row[10] = (abs(x - a.x) + abs(y - a.y)) / 20
            row[18] = 1
            self.tok._local(s, row, x, y)
            row[N_FEATURES] = 1
            mask[n0 + k] = True
            opts.append(("goto", j, c))
        valid = np.zeros(T, bool)
        for n, o in enumerate(opts):
            if o is not None:
                valid[n] = True
                out[n, N_FEATURES + 1] = 1
                out[n, N_FEATURES + 2] = min(o[2] / 40, 2)
        self.opts = opts
        return out, mask, valid

    # ------------------------------------------------------------ ciclo
    def _new_level(self):
        self.sim.init_level(self.rand.choice(self.levels))

    def reset(self, seed=None):
        if seed is not None:
            self.rand.seed(seed)
        self._new_level()
        self.ep_gems = 0
        return self._obs(), {}

    def _wait_respawn(self):
        s = self.sim
        while not s.agent.alive:
            s.tick(STAY)
            if s.time_left <= 0:
                self._new_level()
                return

    def _one_tick(self, action):
        """Un tick: devuelve (recompensa, fin) con fin en {None, 'exit', 'death', 'timeout'}."""
        s = self.sim
        ev = s.tick(action)
        r = s.agent.reward
        self.ep_gems += ev.count("gem")
        if "exit" in ev:
            return r + 60, "exit"
        if "death" in ev or not s.agent.alive:
            return r - 40, "death"
        if s.time_left <= 0:
            return r - .05, "timeout"
        return r - .05, None

    def step(self, choice: int):
        s = self.sim
        opt = self.opts[choice] if 0 <= choice < len(self.opts) else None
        if opt is None:
            opt = ("wait", None, 0.0)                # elección inválida: se trata como esperar
        kind = opt[0]
        R, disc, k, end = 0.0, 1.0, 0, None
        pushes = 0
        while k < MAX_MACRO_TICKS:
            a = s.agent
            here = a.y * W + a.x
            if k > 0 and hazard_map(s)[here]:
                break                                # peligro nuevo: que la red decida
            if kind == "wait":
                if k >= WAIT_TICKS:
                    break
                act = STAY
            elif kind == "goto":
                goal = opt[1]
                t = s.grid[goal]
                if t not in (GEM, EXIT) and here == goal:
                    break                            # llegó al refugio
                if t not in (GEM, EXIT, E, DIRT):
                    break                            # el destino desapareció (roca cayó, gema tomada…)
                r = plan(s, {goal}, self.hazard)
                if r is None or r[2] is None:
                    break
                act = r[2]
            else:                                    # push
                stand, push, rock = opt[1], opt[3], opt[4]
                if s.grid[rock] != ROCK or pushes >= 3:
                    break
                if here == stand:
                    act = push
                    pushes += 1
                else:
                    r = plan(s, {stand}, self.hazard)
                    if r is None or r[2] is None:
                        break
                    act = r[2]
            rt, end = self._one_tick(act)
            R += disc * rt
            disc *= self.gamma
            k += 1
            if end:
                break
            if kind == "goto" and s.grid[opt[1]] not in (GEM, EXIT) and s.agent.y * W + s.agent.x == opt[1]:
                break                                # tomó la gema o llegó
        info = {"ticks": max(k, 1)}
        terminated = end in ("exit", "death")
        truncated = end == "timeout"
        if k == 0:                                   # la opción no pudo ni empezar: un tick quieto
            rt, end = self._one_tick(STAY)
            R, info["ticks"] = rt, 1
            terminated = end in ("exit", "death")
            truncated = end == "timeout"
        if terminated or truncated:
            info["outcome"] = end
            info["gems"] = self.ep_gems
            self.ep_gems = 0
            if end == "death":
                self._wait_respawn()
            else:
                self._new_level()
        return self._obs(), R, terminated, truncated, info
