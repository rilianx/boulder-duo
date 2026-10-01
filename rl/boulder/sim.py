"""Port fiel de la simulación de index.html (modo "Entrenar PC": un solo agente, el J2).

Cada función replica a su par en JS, en el mismo orden, para que un nivel y una secuencia de
acciones produzcan exactamente la misma grilla tick a tick (ver tests/test_parity.py).
"""
from __future__ import annotations

import math

W, H, TICK = 40, 22, 120
VW, VH = 17, 12
E, DIRT, WALL, STEEL, ROCK, GEM, EXIT, FIRE, BUTT, P1, P2, BOOM = range(12)
OFF = (-W, 1, W, -1)                       # arriba, derecha, abajo, izquierda
DXY = ((0, -1), (1, 0), (0, 1), (-1, 0))
STAY = 4
M32 = 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    return (a * b) & M32


def rng(seed: int):
    """mulberry32, idéntico a `rng()` en JS."""
    s = seed & M32

    def nxt() -> float:
        nonlocal s
        s = (s + 0x6D2B79F5) & M32
        t = _imul(s ^ (s >> 15), 1 | s)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & M32) ^ t
        return ((t ^ (t >> 14)) & M32) / 4294967296
    return nxt


class Agent:
    __slots__ = ("x", "y", "sx", "sy", "alive", "exited", "gems", "respawn", "immune", "push", "reward")

    def __init__(self):
        self.x = self.y = self.sx = self.sy = 0
        self.alive = self.exited = False
        self.gems = 0
        self.respawn = -1
        self.immune = 0
        self.push = 0
        self.reward = 0.0          # recompensa acumulada en el tick (gemas, choques)


class Sim:
    """Estado del nivel + física. El agente ocupa la celda P2, como el PC en el juego."""

    CELL = P2

    def __init__(self):
        self.agent = Agent()
        self.level = 1
        self.events: list[str] = []

    # ------------------------------------------------------------------ nivel
    def gen_level(self, n: int):
        R = rng(n * 7919 + 13)
        N = W * H
        g = self.grid = bytearray(N)
        self.fall = bytearray(N)
        self.dir = bytearray(N)
        self.aux = bytearray(N)
        self.moved = bytearray(N)
        pr = min(.10 + n * .012, .22)
        pg = .045 + min(n * .004, .03)
        pe = .035
        for y in range(H):
            for x in range(W):
                i = y * W + x
                if x == 0 or y == 0 or x == W - 1 or y == H - 1:
                    g[i] = STEEL
                    continue
                r = R()
                g[i] = ROCK if r < pr else GEM if r < pr + pg else E if r < pr + pg + pe else DIRT
        n_walls = 1 + math.floor(R() * 2) + (1 if n > 2 else 0)
        for _ in range(n_walls):
            y = 5 + math.floor(R() * (H - 9))
            x0 = 1 + math.floor(R() * 10)
            ln = 14 + math.floor(R() * 22)
            for x in range(x0, min(W - 1, x0 + ln)):
                g[y * W + x] = WALL
            gaps = 1 + math.floor(R() * 2)
            for _ in range(gaps):
                gx = x0 + 2 + math.floor(R() * (ln - 4))
                if 0 < gx < W - 1:
                    g[y * W + gx] = DIRT
        if n > 1 and R() < .6:
            x = 8 + math.floor(R() * (W - 16))
            y0 = 3 + math.floor(R() * 5)
            ln = 5 + math.floor(R() * 7)
            for y in range(y0, min(H - 2, y0 + ln)):
                g[y * W + x] = WALL
        spawns = [(2, 2), (W - 3, 2)]
        for sx, sy in spawns:
            for dy in range(-1, 3):
                for dx in range(-1, 2):
                    x, y = sx + dx, sy + dy
                    if 0 < x < W - 1 and 0 < y < H - 1:
                        g[y * W + x] = DIRT
        ex = 3 + math.floor(R() * (W - 6))
        ey = H - 2
        g[ey * W + ex] = EXIT
        g[(ey - 1) * W + ex] = DIRT

        n_f = min(1 + n // 2, 6)
        n_b = min(1 + n // 3, 4) if n >= 2 else 0

        def place(tp):
            for _ in range(300):
                x = 2 + math.floor(R() * (W - 9))
                y = 3 + math.floor(R() * (H - 6))
                if any(abs(sx - (x + 2)) + abs(sy - y) < 9 for sx, sy in spawns):
                    continue
                if any(g[y * W + x + k] in (STEEL, EXIT, WALL, FIRE, BUTT) for k in range(5)):
                    continue
                for k in range(5):
                    g[y * W + x + k] = E
                    up = (y - 1) * W + x + k
                    if g[up] in (ROCK, GEM):
                        g[up] = DIRT
                g[y * W + x + 2] = tp
                self.dir[y * W + x + 2] = math.floor(R() * 4)
                return

        for _ in range(n_f):
            place(FIRE)
        for _ in range(n_b):
            place(BUTT)

        D = sum(1 for v in g if v == GEM)
        want = 12 + n * 2
        while D < want + 6:
            i = (1 + math.floor(R() * (H - 3))) * W + 1 + math.floor(R() * (W - 2))
            if g[i] == DIRT and i // W > 4:
                g[i] = GEM
                D += 1
        self.need = want
        self.need_each = math.ceil(want * .6)
        self.time_left = max(90, 160 - n * 6)
        self.time_start = self.time_left
        return spawns

    def init_level(self, n: int):
        self.level = n
        spawns = self.gen_level(n)
        a = self.agent
        a.sx, a.sy = spawns[1]
        a.x, a.y = a.sx, a.sy
        a.gems = 0
        a.exited = False
        a.push = 0
        a.alive = True
        a.respawn = -1
        a.immune = 16
        a.reward = 0.0
        self.grid[a.y * W + a.x] = self.CELL
        self.time_acc = 0

    # ------------------------------------------------------------------ reglas
    def exit_open(self) -> bool:
        return self.agent.gems >= self.need_each

    def _move(self, i, j):
        g, f, d = self.grid, self.fall, self.dir
        g[j] = g[i]; d[j] = d[i]; f[j] = f[i]
        g[i] = E; f[i] = 0; self.aux[i] = self.aux[j] = 0; self.moved[j] = 1

    def _kill(self):
        a = self.agent
        if not a.alive:
            return
        a.alive = False
        a.respawn = 10
        self.events.append("death")

    def _explode(self, cx, cy, to_gem):
        g = self.grid
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                j = (cy + dy) * W + cx + dx
                t = g[j]
                if t == STEEL or t == EXIT:
                    continue
                if t == P1 or t == P2:
                    if t == self.CELL:
                        if self.agent.immune > 0:
                            continue
                        self._kill()
                g[j] = BOOM; self.aux[j] = 0; self.dir[j] = 1 if to_gem else 0
                self.fall[j] = 0; self.moved[j] = 1

    def _step_agent(self, d):
        a = self.agent
        if not a.alive:
            return
        if d == STAY:
            a.push = 0
            return
        dx, dy = DXY[d]
        g = self.grid
        i = a.y * W + a.x
        j = i + OFF[d]
        t = g[j]

        def go():
            g[i] = E; g[j] = self.CELL; self.moved[j] = 1
            a.x += dx; a.y += dy

        if t == E or t == DIRT:
            go(); a.push = 0
        elif t == GEM:
            a.gems += 1; go(); a.push = 0
            a.reward += 5
            self.events.append("gem")
        elif t == EXIT and self.exit_open():
            g[i] = E; a.alive = False; a.exited = True; a.x += dx; a.y += dy
            self.events.append("exit")
        elif t == ROCK and dy == 0 and g[j + OFF[d]] == E and not self.fall[j]:
            a.push += 1
            if a.push >= 2:
                self._move(j, j + OFF[d]); self.fall[j + OFF[d]] = 0; go(); a.push = 0
        else:
            a.push = 0
            a.reward -= .3

    def _fall_obj(self, i, x, y):
        g, f = self.grid, self.fall
        b = i + W
        bt = g[b]
        if bt == E:
            # quieta, espera un tick antes de empezar a caer (aux la marca)
            if f[i] or self.aux[i]:
                self._move(i, b); f[b] = 1
            else:
                self.aux[i] = 1
            return
        self.aux[i] = 0
        if f[i]:
            if bt == P1 or bt == P2:
                if bt != self.CELL or self.agent.immune <= 0:
                    self._explode(x, y + 1, False)
                    return
            elif bt == FIRE or bt == BUTT:
                self._explode(x, y + 1, bt == BUTT)
                return
        if bt == ROCK or bt == GEM or bt == WALL:
            if g[i - 1] == E and g[b - 1] == E:
                self._move(i, i - 1); f[i - 1] = 1
                return
            if g[i + 1] == E and g[b + 1] == E:
                self._move(i, i + 1); f[i + 1] = 1
                return
        f[i] = 0

    def _enemy(self, i, x, y, t):
        g = self.grid
        for k in range(4):
            n = g[i + OFF[k]]
            if (n == P1 or n == P2) and (n != self.CELL or self.agent.immune <= 0):
                self._explode(x, y, t == BUTT)
                return
        d = self.dir[i]
        turn = (d + 3) % 4 if t == FIRE else (d + 1) % 4
        if g[i + OFF[turn]] == E:
            j = i + OFF[turn]; self._move(i, j); self.dir[j] = turn
        elif g[i + OFF[d]] == E:
            self._move(i, i + OFF[d])
        else:
            self.dir[i] = (d + 1) % 4 if t == FIRE else (d + 3) % 4

    def tick(self, action: int):
        """Un tick del juego. Devuelve la lista de eventos ("gem", "death", "exit")."""
        self.events = []
        self.agent.reward = 0.0
        moved = self.moved
        for k in range(W * H):
            moved[k] = 0
        self._step_agent(action)
        g, aux = self.grid, self.aux
        for y in range(1, H - 1):
            row = y * W
            for x in range(1, W - 1):
                i = row + x
                if moved[i]:
                    continue
                t = g[i]
                if t == ROCK or t == GEM:
                    self._fall_obj(i, x, y)
                elif t == FIRE or t == BUTT:
                    self._enemy(i, x, y, t)
                elif t == BOOM:
                    aux[i] += 1
                    if aux[i] >= 4:
                        g[i] = GEM if self.dir[i] else E
                        self.dir[i] = 0; self.fall[i] = 0
        a = self.agent
        if a.immune > 0:
            a.immune -= 1
        if not a.alive and not a.exited and a.respawn > 0:
            a.respawn -= 1
            if a.respawn == 0:
                j = a.sy * W + a.sx
                t = g[j]
                if t in (P1, P2, BOOM):
                    a.respawn = 1
                else:
                    g[j] = self.CELL; self.fall[j] = 0
                    a.x, a.y = a.sx, a.sy
                    a.alive = True; a.immune = 24; a.push = 0
        self.time_acc += TICK
        if self.time_acc >= 1000:
            self.time_acc -= 1000
            self.time_left -= 1
        return self.events

    # ------------------------------------------------------------------ utilidades
    def copy(self) -> "Sim":
        """Copia independiente del estado, para simular hipótesis (\"¿y si entro ahí?\")."""
        c = Sim.__new__(Sim)
        c.__dict__.update({k: (bytearray(v) if isinstance(v, bytearray) else v) for k, v in self.__dict__.items()
                           if k not in ("agent", "events")})
        c.events = []
        c.agent = Agent()
        for k in Agent.__slots__:
            setattr(c.agent, k, getattr(self.agent, k))
        return c

    def window(self):
        """Lo que muestra la cámara del PC: VW x VH casillas alrededor del agente (aiWindow en JS)."""
        a = self.agent
        x0 = min(max(a.x - (VW >> 1), 0), W - VW)
        y0 = min(max(a.y - (VH >> 1), 0), H - VH)
        return x0, y0, x0 + VW - 1, y0 + VH - 1

    def snapshot_hash(self) -> int:
        """FNV-1a de grilla + estado del agente; debe coincidir con __sim.hash() en JS."""
        h = 0x811C9DC5
        for arr in (self.grid, self.fall, self.dir, self.aux):
            for v in arr:
                h = ((h ^ v) * 0x01000193) & M32
        a = self.agent
        for v in (a.x, a.y, int(a.alive), int(a.exited), a.gems, a.immune, a.respawn & 0xFF, a.push, self.time_left):
            h = ((h ^ (v & 0xFF)) * 0x01000193) & M32
        return h
