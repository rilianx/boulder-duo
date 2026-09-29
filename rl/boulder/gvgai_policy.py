"""A* con costos de peligro para el Boulder Dash de GVGAI (misma idea que policy.py, otras reglas).

Física de GVGAI que importa para el peligro:
  - una roca cae mientras debajo no haya tierra, muro, diamante u otra roca, y mata si te alcanza desde arriba:
    cavar la casilla justo bajo una roca es mortal (en nuestro juego no), y también lo es una columna vacía
    bajo una roca;
  - los enemigos se mueven al azar por el vacío (la tierra y los diamantes los bloquean) y matan al tocarte.
Parámetros (ajustables con CEM, ver tune_gvgai.py):
  c_dirt   costo de cavar tierra (vacío = 1)
  h_under  casilla justo bajo una roca
  h_col    casilla con una roca 2 o 3 más arriba y solo vacío entre medio
  h_e1/h_e2 casilla a distancia Manhattan 1 / 2 de un enemigo
  detour   con 9 diamantes, cuánto acepta desviarse por otro antes de ir a la salida
"""
from __future__ import annotations

import heapq
import math

from .sim import BUTT, DIRT, E, EXIT, FIRE, GEM, ROCK, STAY

GV_PARAMS = {
    "c_dirt": (0.5, 3.0, 1.0),
    "h_under": (0.0, 200.0, 100.0),
    "h_col": (0.0, 100.0, 25.0),
    "h_e1": (0.0, 200.0, 50.0),
    "h_e2": (0.0, 100.0, 10.0),
    "detour": (0.0, 20.0, 0.0),
}
GV_DEFAULT = {k: v[2] for k, v in GV_PARAMS.items()}


def gv_costs(st, P):
    W, H, g = st.W, st.H, st.grid
    N = W * H
    edist = [9] * N
    for i in range(N):
        if g[i] == FIRE or g[i] == BUTT:
            x, y = i % W, i // W
            for dy in range(-2, 3):
                yy = y + dy
                if 0 <= yy < H:
                    r = 2 - abs(dy)
                    for xx in range(max(0, x - r), min(W - 1, x + r) + 1):
                        edist[yy * W + xx] = min(edist[yy * W + xx], abs(dy) + abs(xx - x))
    cost = [math.inf] * N
    for j in range(W, N):
        t = g[j]
        if not (t == E or t == DIRT or t == GEM):
            continue
        c = P["c_dirt"] if t == DIRT else 1.0
        if g[j - W] == ROCK:
            c += P["h_under"]
        else:
            k = j - W
            while k >= W and g[k] == E and (j - k) // W < 3:
                k -= W
            if (j - k) // W <= 3 and g[k] == ROCK and k != j - W:
                c += P["h_col"]
        if edist[j] <= 2:
            c += P["h_e1"] if edist[j] <= 1 else P["h_e2"]
        cost[j] = c
    return cost


def gv_dijkstra(st, goals, cost, edge=None):
    W, g = st.W, st.grid
    a = st.agent
    start = a.y * W + a.x
    best = {start: 0.0}
    first = {start: -1}
    pq = [(0.0, start)]
    offs = (-W, 1, W, -1)
    while pq:
        c, i = heapq.heappop(pq)
        if c > best[i]:
            continue
        if i in goals and i != start:
            return c, first[i]
        for d in range(4):
            j = i + offs[d]
            if not 0 <= j < len(g):
                continue
            step = 1.0 if (j in goals and g[j] == EXIT) else cost[j]
            if step == math.inf:
                continue
            if edge is not None:
                step += edge.get((j, d), 0.0)
            nc = c + step
            if nc < best.get(j, math.inf):
                best[j] = nc
                first[j] = d if i == start else first[i]
                heapq.heappush(pq, (nc, j))
    return None


def gv_act(st, P=GV_DEFAULT):
    g = st.grid
    cost = gv_costs(st, P)
    gems = {i for i in range(len(g)) if g[i] == GEM}
    exits = {i for i in range(len(g)) if g[i] == EXIT}
    if st.exit_open():
        rex = gv_dijkstra(st, exits, cost)
        rg = gv_dijkstra(st, gems, cost) if P["detour"] > 0 and gems else None
        r = rg if rg and (rex is None or rg[0] <= P["detour"]) else rex
    else:
        r = gv_dijkstra(st, gems, cost)
    return r[1] if r is not None else STAY


# ---------------------------------------------------------------- peligro aprendido (sin reglas)
GV_LEARNED_PARAMS = {
    "c_dirt": (0.5, 3.0, 1.0),
    "w_risk": (0.0, 80.0, 20.0),      # costo extra = w_risk · (−log(1 − p_muerte))
    "detour": (0.0, 20.0, 0.0),
}
GV_LEARNED_DEFAULT = {k: v[2] for k, v in GV_LEARNED_PARAMS.items()}


def gv_act_learned(st, P, model):
    """A* sin reglas de peligro: el costo de cada paso sale del predictor de muerte."""
    g = st.grid
    cost = [math.inf] * len(g)
    for j, t in enumerate(g):
        if t == E or t == GEM:
            cost[j] = 1.0
        elif t == DIRT:
            cost[j] = P["c_dirt"]
    w = P["w_risk"]
    edge = {k: -w * math.log(max(1e-4, 1.0 - p)) for k, p in model.window_probs(st).items()}
    gems = {i for i in range(len(g)) if g[i] == GEM}
    exits = {i for i in range(len(g)) if g[i] == EXIT}
    if st.exit_open():
        rex = gv_dijkstra(st, exits, cost, edge)
        rg = gv_dijkstra(st, gems, cost, edge) if P["detour"] > 0 and gems else None
        r = rg if rg and (rex is None or rg[0] <= P["detour"]) else rex
    else:
        r = gv_dijkstra(st, gems, cost, edge)
    return r[1] if r is not None else STAY
