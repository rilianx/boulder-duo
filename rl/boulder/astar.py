"""Búsqueda de caminos con costos de peligro, para acciones de alto nivel ("ir a este punto").

Se puede pisar vacío, tierra y gemas (costo 1). Una casilla o un paso peligroso suma `hazard`
(o se prohíbe si hazard = inf):
  - algo va a caer sobre la casilla: roca/gema cayendo justo encima, o hueco con roca/gema encima;
  - la casilla está a 2 pasos o menos de una luciérnaga o mariposa;
  - bajar desde debajo de una roca/gema: al irte, cae y te alcanza en la casilla de abajo.
Las rocas y los enemigos se mueven, así que la ruta se recalcula en cada tick.
"""
from __future__ import annotations

import heapq
import math

from .env import enemy_zone
from .sim import DIRT, DXY, E, EXIT, GEM, OFF, ROCK, W, H, Sim

INF = math.inf


def _faller(t):
    return t == ROCK or t == GEM


def hazard_map(sim: Sim) -> bytearray:
    g, f = sim.grid, sim.fall
    z = enemy_zone(sim)
    for j in range(2 * W, W * H):
        if z[j]:
            continue
        a1 = g[j - W]
        if (_faller(a1) and f[j - W]) or (a1 == E and _faller(g[j - 2 * W])):
            z[j] = 1
    return z


def plan(sim: Sim, goals, hazard: float = 25.0, hz=None):
    """Dijkstra desde el PC hasta el objetivo más barato de `goals` (conjunto de índices de celda).

    Devuelve (costo, destino, primera_dirección) o None si ninguno es alcanzable. El destino puede ser
    una celda no transitable (la salida): se llega a ella entrando desde un vecino.
    """
    a = sim.agent
    g = sim.grid
    if hz is None:
        hz = hazard_map(sim)
    start = a.y * W + a.x
    if start in goals:
        return 0.0, start, None
    best = {start: 0.0}
    first = {start: -1}
    pq = [(0.0, start)]
    while pq:
        c, i = heapq.heappop(pq)
        if c > best.get(i, INF):
            continue
        if i in goals and i != start:
            return c, i, first[i]
        above_faller = _faller(g[i - W])
        for d in range(4):
            j = i + OFF[d]
            t = g[j]
            if not (t == E or t == DIRT or t == GEM or (t == EXIT and j in goals)):
                continue
            step = 1.0
            if hz[j]:
                step += hazard
            if d == 2 and above_faller:
                step += hazard
            if step == INF:
                continue
            nc = c + step
            if nc < best.get(j, INF):
                best[j] = nc
                first[j] = d if i == start else first[i]
                heapq.heappush(pq, (nc, j))
    return None


def gem_cells(sim: Sim):
    g = sim.grid
    return {i for i in range(W * H) if g[i] == GEM}


def exit_cells(sim: Sim):
    g = sim.grid
    return {i for i in range(W * H) if g[i] == EXIT}
