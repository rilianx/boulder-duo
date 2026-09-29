"""Política A* con parámetros ajustables: el costo de cada tipo de riesgo y cuándo ir a la salida.

Cada tick: costo por casilla = base (vacío 1, tierra `c_dirt`, gema 1) + peligros, y Dijkstra desde el PC.
  h_fall   casilla sobre la que algo va a caer (roca/gema cayendo encima, o hueco con roca/gema encima)
  h_under  casilla justo bajo una roca/gema quieta (cavar debajo de ella)
  h_down   bajar desde debajo de una roca/gema (te sigue y te aplasta)
  h_e1..3  casilla a distancia Manhattan 1, 2, 3 de una luciérnaga o mariposa
  detour   con la cuota cumplida, se desvía a una gema si cuesta a lo más `detour`; si no, va a la salida
Si no alcanza nada y su casilla es peligrosa, huye a la casilla segura más barata; si no, espera.
"""
from __future__ import annotations

import heapq
import math

from .sim import BUTT, DIRT, E, EXIT, FIRE, GEM, OFF, ROCK, STAY, W, H, Sim

PARAMS = {             # nombre: (mínimo, máximo, valor a mano ≈ baseline con peligro 25)
    "c_dirt": (0.5, 3.0, 1.0),
    "h_fall": (0.0, 80.0, 25.0),
    "h_under": (0.0, 20.0, 0.0),
    "h_down": (0.0, 80.0, 25.0),
    "h_e1": (0.0, 120.0, 25.0),
    "h_e2": (0.0, 80.0, 25.0),
    "h_e3": (0.0, 40.0, 0.0),
    "detour": (0.0, 12.0, 0.0),
}
DEFAULT = {k: v[2] for k, v in PARAMS.items()}


def _faller(t):
    return t == ROCK or t == GEM


def cell_costs(sim: Sim, P):
    """Costo de entrar a cada casilla (inf = no transitable) y máscara de casillas peligrosas."""
    g, f = sim.grid, sim.fall
    N = W * H
    edist = [9] * N
    for i in range(N):
        if g[i] == FIRE or g[i] == BUTT:
            x, y = i % W, i // W
            for dy in range(-3, 4):
                yy = y + dy
                if not 0 <= yy < H:
                    continue
                r = 3 - abs(dy)
                for xx in range(max(0, x - r), min(W - 1, x + r) + 1):
                    j = yy * W + xx
                    d = abs(dy) + abs(xx - x)
                    if d < edist[j]:
                        edist[j] = d
    he = (P["h_e1"], P["h_e1"], P["h_e2"], P["h_e3"])
    cost = [math.inf] * N
    danger = bytearray(N)
    c_dirt, h_fall, h_under = P["c_dirt"], P["h_fall"], P["h_under"]
    for j in range(2 * W, N):
        t = g[j]
        if not (t == E or t == DIRT or t == GEM):
            continue
        c = c_dirt if t == DIRT else 1.0
        a1 = g[j - W]
        if (_faller(a1) and f[j - W]) or (a1 == E and _faller(g[j - 2 * W])):
            c += h_fall
            danger[j] = 1
        elif _faller(a1):
            c += h_under
        if edist[j] <= 3:
            c += he[edist[j]]
            if edist[j] <= 2:
                danger[j] = 1
        cost[j] = c
    return cost, danger


def dijkstra(sim: Sim, goals, cost, P, edge=None):
    """(costo, primera dirección) hasta el objetivo más barato de `goals`, o None."""
    g = sim.grid
    a = sim.agent
    start = a.y * W + a.x
    best = {start: 0.0}
    first = {start: -1}
    pq = [(0.0, start)]
    h_down = P["h_down"]
    while pq:
        c, i = heapq.heappop(pq)
        if c > best[i]:
            continue
        if i in goals and i != start:
            return c, first[i]
        above = _faller(g[i - W])
        for d in range(4):
            j = i + OFF[d]
            if j in goals and g[j] == EXIT:
                step = 1.0
            else:
                step = cost[j]
                if step == math.inf:
                    continue
            if d == 2 and above:
                step += h_down
            if edge is not None:
                step += edge.get((j, d), 0.0)
            nc = c + step
            if nc < best.get(j, math.inf):
                best[j] = nc
                first[j] = d if i == start else first[i]
                heapq.heappush(pq, (nc, j))
    return None


def act(sim: Sim, P=DEFAULT) -> int:
    g = sim.grid
    cost, danger = cell_costs(sim, P)
    gems = {i for i in range(W * H) if g[i] == GEM}
    r = None
    if sim.exit_open():
        rex = dijkstra(sim, {i for i in range(W * H) if g[i] == EXIT}, cost, P)
        rg = dijkstra(sim, gems, cost, P) if P["detour"] > 0 else None
        r = rg if rg and (rex is None or rg[0] <= P["detour"]) else rex
    else:
        r = dijkstra(sim, gems, cost, P)
    if r is not None:
        return r[1]
    a = sim.agent
    if danger[a.y * W + a.x]:
        safe = {j for j in range(2 * W, W * H) if cost[j] < math.inf and not danger[j] and g[j] != GEM}
        r = dijkstra(sim, safe, cost, P)
        if r is not None:
            return r[1]
    return STAY


# ---------------------------------------------------------------- peligro aprendido
LEARNED_PARAMS = {     # nombre: (mínimo, máximo, inicial)
    "c_dirt": (0.5, 3.0, 1.0),
    "w_risk": (0.0, 60.0, 10.0),      # costo extra = w_risk · (−log(1 − p_muerte))
    "detour": (0.0, 12.0, 0.0),
}
LEARNED_DEFAULT = {k: v[2] for k, v in LEARNED_PARAMS.items()}


def act_learned(sim: Sim, P, model) -> int:
    """Igual que act(), pero sin reglas de peligro: el costo de cada paso sale del predictor de muerte."""
    g = sim.grid
    Q = {**P, "h_fall": 0.0, "h_under": 0.0, "h_down": 0.0, "h_e1": 0.0, "h_e2": 0.0, "h_e3": 0.0}
    cost = [math.inf] * (W * H)
    for j in range(W * H):
        t = g[j]
        if t == E or t == GEM:
            cost[j] = 1.0
        elif t == DIRT:
            cost[j] = Q["c_dirt"]
    probs = model.window_probs(sim)
    w = P["w_risk"]
    edge = {k: -w * math.log(max(1e-4, 1.0 - p)) for k, p in probs.items()}
    gems = {i for i in range(W * H) if g[i] == GEM}
    if sim.exit_open():
        rex = dijkstra(sim, {i for i in range(W * H) if g[i] == EXIT}, cost, Q, edge)
        rg = dijkstra(sim, gems, cost, Q, edge) if P["detour"] > 0 else None
        r = rg if rg and (rex is None or rg[0] <= P["detour"]) else rex
    else:
        r = dijkstra(sim, gems, cost, Q, edge)
    return r[1] if r is not None else STAY
