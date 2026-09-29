"""Entorno de RL sobre la simulación: un episodio es una vida del PC, como en index.html.

Recompensas idénticas al agente Q(λ) del juego: +5 gema, +60 salida, −40 muerte, −0,05 por paso,
−0,3 por chocar, y +0,4 por casilla que se acerca al objetivo (distancia de la ruta segura en pantalla).
"""
from __future__ import annotations

import random

from .sim import BUTT, DIRT, DXY, E, EXIT, FIRE, GEM, H, OFF, ROCK, STEEL, W, Sim
from .tokens import Tokenizer


def _faller(t):
    return t == ROCK or t == GEM


def enemy_zone(sim: Sim) -> bytearray:
    """Casillas a 2 pasos (Manhattan) o menos de una luciérnaga o mariposa."""
    g = sim.grid
    z = bytearray(W * H)
    for i in range(W * H):
        if g[i] == FIRE or g[i] == BUTT:
            x, y = i % W, i // W
            for dy in range(-2, 3):
                r = 2 - abs(dy)
                yy = y + dy
                if 0 <= yy < H:
                    for xx in range(max(0, x - r), min(W - 1, x + r) + 1):
                        z[yy * W + xx] = 1
    return z


def danger_at(sim: Sim, j: int, zone: bytearray | None = None) -> int:
    """0 seguro, 1 algo puede caerle encima, 2 enemigo a 2 pasos o menos (dangerAt en JS)."""
    g, f = sim.grid, sim.fall
    a1 = g[j - W]
    a2 = g[j - 2 * W] if j - 2 * W >= 0 else STEEL
    if _faller(a1) and f[j - W]:
        return 1
    if a1 == E and _faller(a2):
        return 1
    if zone is None:
        zone = enemy_zone(sim)
    return 2 if zone[j] else 0


def target_distance(sim: Sim):
    """Largo de la ruta segura (o, si no hay, cualquiera) al objetivo dentro de la pantalla; None si no hay."""
    want_exit = sim.exit_open()
    x0, y0, x1, y1 = sim.window()
    a = sim.agent
    g, f = sim.grid, sim.fall
    zone = enemy_zone(sim)
    for safe in (True, False):
        start = a.y * W + a.x
        seen = {start}
        frontier = [start]
        dist = 0
        while frontier:
            dist += 1
            nxt = []
            for i in frontier:
                x, y = i % W, i // W
                for d in range(4):
                    xx, yy = x + DXY[d][0], y + DXY[d][1]
                    if xx < x0 or xx > x1 or yy < y0 or yy > y1:
                        continue
                    j = yy * W + xx
                    if j in seen:
                        continue
                    seen.add(j)
                    t = g[j]
                    if (not want_exit and t == GEM) or (want_exit and t == EXIT):
                        return dist, want_exit
                    if t == E or t == DIRT or (want_exit and t == GEM):
                        if safe:
                            a1 = g[j - W]
                            if (_faller(a1) and f[j - W]) or (a1 == E and j >= 2 * W and _faller(g[j - 2 * W])) or zone[j]:
                                continue
                        nxt.append(j)
            frontier = nxt
    return None, want_exit


class BoulderEnv:
    """API estilo Gymnasium: reset() -> (obs, info); step(a) -> (obs, r, terminated, truncated, info).

    obs = (tokens float32 [T, F], mask bool [T]). Acciones: 0 ↑, 1 →, 2 ↓, 3 ←, 4 quieto.
    """

    n_actions = 5

    def __init__(self, levels=range(1, 13), seed=None, max_tokens=64):
        self.levels = list(levels)
        self.rand = random.Random(seed)
        self.sim = Sim()
        self.tok = Tokenizer(max_tokens)
        self._dist = (None, False)

    @property
    def obs_shape(self):
        return self.tok.max_tokens, self.tok.n_features

    def _new_level(self):
        self.sim.init_level(self.rand.choice(self.levels))

    def _obs(self):
        return self.tok.encode(self.sim)

    def reset(self, seed=None):
        if seed is not None:
            self.rand.seed(seed)
        self._new_level()
        self._dist = target_distance(self.sim)
        self.ep_gems = 0
        return self._obs(), {}

    def _wait_respawn(self):
        """Tras morir, el mundo sigue hasta que el PC reaparece (o se acaba el tiempo)."""
        s = self.sim
        while not s.agent.alive:
            s.tick(4)
            if s.time_left <= 0:
                self._new_level()
                return

    def step(self, action: int):
        s = self.sim
        ev = s.tick(int(action))
        a = s.agent
        r = a.reward
        self.ep_gems += ev.count("gem")
        info = {}
        terminated = truncated = False
        if "exit" in ev:
            r += 60
            terminated = True
            info["outcome"] = "exit"
        elif "death" in ev or not a.alive:
            r -= 40
            terminated = True
            info["outcome"] = "death"
        elif s.time_left <= 0:
            truncated = True
            info["outcome"] = "timeout"
        else:
            r -= .05
            d_new = target_distance(s)
            if self._dist[0] is not None and d_new[0] is not None and self._dist[1] == d_new[1]:
                r += .4 * (self._dist[0] - d_new[0])
            self._dist = d_new
        if terminated or truncated:
            info["gems"] = self.ep_gems
            self.ep_gems = 0
            if info["outcome"] == "death":
                self._wait_respawn()
            else:
                self._new_level()
            self._dist = target_distance(s)
        return self._obs(), r, terminated, truncated, info
