"""Observación como conjunto de tokens de entidades con datos locales (sin tokens de terreno).

Token 0 = el propio PC. Luego, ordenadas por cercanía (Manhattan), las entidades de su pantalla
(17×12): rocas, gemas, luciérnagas, mariposas, explosiones y la salida; y hasta 4 gemas fuera de
pantalla más la salida si no se ve, marcadas como "fuera de vista". El terreno entra como vecindario
local de cada token: las 8 casillas que lo rodean y la casilla 2 más abajo (por donde caería).

Columnas (N_FEATURES = 91):
  0-7    tipo: propio, roca, gema, luciérnaga, mariposa, salida, explosión, otro jugador
  8-9    Δx/8, Δy/6 con signo (relativo al PC)
  10     |Δx|+|Δy| / 20
  11     distancia BFS desde el PC por casillas transitables / 30 (1 si no alcanzable)
  12     alcanzable dentro de la pantalla
  13     cayendo
  14-17  dirección de movimiento (enemigos)
  18     en pantalla
  19-20  roca empujable hacia ←, hacia →
  21-76  vecindario 3×3 (8 vecinos × 7 clases: vacío, tierra, sólido, roca, gema, enemigo, jugador)
  77-83  casilla 2 más abajo (7 clases)
  84-90  solo token propio: gemas/cuota, salida abierta, tiempo restante, inmune,
         roca cayendo sobre su columna (≤3), contador de empuje, gemas a la vista/10
"""
from __future__ import annotations

import numpy as np

from .sim import BOOM, BUTT, DIRT, DXY, E, EXIT, FIRE, GEM, H, P1, P2, ROCK, STEEL, W, WALL, Sim

N_FEATURES = 91
_TYPE = {ROCK: 1, GEM: 2, FIRE: 3, BUTT: 4, EXIT: 5, BOOM: 6}
_NEIGH = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
_ENT = (ROCK, GEM, FIRE, BUTT, EXIT, BOOM)


def cell_class(t: int) -> int:
    if t == E:
        return 0
    if t == DIRT:
        return 1
    if t in (WALL, STEEL, EXIT):
        return 2
    if t == ROCK:
        return 3
    if t == GEM:
        return 4
    if t in (FIRE, BUTT):
        return 5
    return 6          # P1, P2, BOOM


def bfs_distances(sim: Sim, win):
    """Distancias desde el PC por E/tierra/gema dentro de la pantalla; entidades alcanzables al tocarlas."""
    x0, y0, x1, y1 = win
    a = sim.agent
    g = sim.grid
    dist = {}
    if not a.alive:
        return dist
    start = a.y * W + a.x
    dist[start] = 0
    frontier = [start]
    d = 0
    while frontier:
        d += 1
        nxt = []
        for i in frontier:
            x, y = i % W, i // W
            for dx, dy in DXY:
                xx, yy = x + dx, y + dy
                if xx < x0 or xx > x1 or yy < y0 or yy > y1:
                    continue
                j = yy * W + xx
                if j in dist:
                    continue
                dist[j] = d                       # se registra aunque no sea transitable (roca, enemigo…)
                if g[j] in (E, DIRT, GEM):
                    nxt.append(j)
        frontier = nxt
    return dist


class Tokenizer:
    def __init__(self, max_tokens: int = 64):
        self.max_tokens = max_tokens
        self.n_features = N_FEATURES

    def _local(self, sim: Sim, row, x, y):
        g = sim.grid
        for k, (dx, dy) in enumerate(_NEIGH):
            xx, yy = x + dx, y + dy
            c = cell_class(g[yy * W + xx]) if 0 <= xx < W and 0 <= yy < H else 2
            row[21 + k * 7 + c] = 1
        yy = y + 2
        c = cell_class(g[yy * W + x]) if yy < H else 2
        row[77 + c] = 1

    def encode(self, sim: Sim):
        T, F = self.max_tokens, N_FEATURES
        out = np.zeros((T, F), np.float32)
        mask = np.zeros(T, bool)
        a = sim.agent
        g, fall, dr = sim.grid, sim.fall, sim.dir
        win = sim.window()
        x0, y0, x1, y1 = win
        dist = bfs_distances(sim, win)

        # token propio
        me = out[0]
        me[0] = 1
        self._local(sim, me, a.x, a.y)
        me[12] = 1
        me[18] = 1
        me[84] = min(a.gems / max(1, sim.need_each), 1.5)
        me[85] = float(sim.exit_open())
        me[86] = max(sim.time_left, 0) / max(1, sim.time_start)
        me[87] = float(a.immune > 0)
        for k in range(1, 4):
            j = (a.y - k) * W + a.x
            if j < 0:
                break
            t = g[j]
            if (t == ROCK or t == GEM) and fall[j]:
                me[88] = 1
                break
            if t != E:
                break
        me[89] = a.push / 2
        mask[0] = True
        self.last_meta = [(sim.CELL, a.y * W + a.x)]      # (tipo de celda, índice) de cada token válido

        ents = []
        exit_seen = False
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                t = g[y * W + x]
                if t in _ENT or (t in (P1, P2) and t != sim.CELL):
                    ents.append((abs(x - a.x) + abs(y - a.y), x, y, t, True))
                    exit_seen |= t == EXIT
        n_view_gems = sum(1 for e in ents if e[3] == GEM)
        me[90] = n_view_gems / 10
        # fuera de pantalla: las 4 gemas más cercanas y la salida
        far = []
        for i in range(W * H):
            t = g[i]
            if t != GEM and not (t == EXIT and not exit_seen):
                continue
            x, y = i % W, i // W
            if x0 <= x <= x1 and y0 <= y <= y1:
                continue
            far.append((abs(x - a.x) + abs(y - a.y), x, y, t, False))
        far.sort()
        far_gems = [e for e in far if e[3] == GEM][:4]
        far_exit = [e for e in far if e[3] == EXIT][:1]
        ents.sort()
        room = T - 1 - len(far_gems) - len(far_exit)
        chosen = ents[:room] + far_gems + far_exit

        for n, (m, x, y, t, in_view) in enumerate(chosen, start=1):
            row = out[n]
            row[_TYPE.get(t, 7)] = 1
            dx, dy = x - a.x, y - a.y
            row[8] = dx / 8
            row[9] = dy / 6
            row[10] = m / 20
            j = y * W + x
            if j in dist:
                row[11] = min(dist[j] / 30, 1)
                row[12] = 1
            else:
                row[11] = 1
            row[13] = fall[j]
            if t in (FIRE, BUTT):
                row[14 + dr[j]] = 1
            row[18] = float(in_view)
            if t == ROCK and not fall[j]:
                row[19] = float(x - 1 >= 0 and g[j - 1] == E)
                row[20] = float(x + 1 < W and g[j + 1] == E)
            self._local(sim, row, x, y)
            mask[n] = True
            self.last_meta.append((t, j))
        return out, mask
