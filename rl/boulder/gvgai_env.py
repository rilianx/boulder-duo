"""Boulder Dash de GVGAI real (motor Java) visto con la interfaz de nuestro Sim.

El motor corre en Java (rl/gvgai/java/boulderduo). Cada tick recibimos la grilla y la traducimos a nuestros
códigos de celda, para que el A*, el tokenizador y el predictor de muerte funcionen igual:
    crab → FIRE, butterfly → BUTT, boulder → ROCK, diamond → GEM, exitdoor → EXIT, wall → WALL,
    dirt → DIRT, vacío → E, avatar → P2.
Reglas de GVGAI que cambian respecto a nuestro juego: 1 vida, 9 diamantes y salir, 2000 ticks,
rocas que caen 0,2 casillas por tick y no ruedan, diamantes fijos, no se empujan rocas, enemigos al azar.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .sim import BUTT, DIRT, E, EXIT, FIRE, GEM, P2, ROCK, STAY, WALL, Agent

ROOT = Path(__file__).resolve().parent.parent / "gvgai"
GAME = ROOT / "vendor" / "GVGAI" / "examples" / "gridphysics" / "boulderdash.txt"
LEVELS = [ROOT / "vendor" / "GVGAI" / "examples" / "gridphysics" / f"boulderdash_lvl{k}.txt" for k in range(5)]
CODE = {"A": P2, "c": FIRE, "b": BUTT, "o": ROCK, "x": GEM, "e": EXIT, "w": WALL, ".": DIRT, "-": E}
# nuestras direcciones (0 ↑, 1 →, 2 ↓, 3 ←, 4 quieto) → acciones del puente (0 NIL, 1 UP, 2 DOWN, 3 LEFT, 4 RIGHT, 5 USE)
TO_BRIDGE = {0: 1, 1: 4, 2: 2, 3: 3, 4: 0}
MAX_TICKS = 2000
NEED = 9


class GvgaiState:
    """Estado de un tick con los atributos que usan nuestras políticas (grid, fall, dir, agent, W, H…)."""

    CELL = P2

    def __init__(self, line: str):
        f = line.split(" ")
        self.tick, self.score = int(f[0]), float(f[1])
        ax, ay, self.gems = int(f[2]), int(f[3]), int(f[4])
        self.W, self.H = int(f[5]), int(f[6])
        self.grid = bytearray(CODE[c] for c in f[7])
        self.fall = bytearray(self.W * self.H)
        self.dir = bytearray(self.W * self.H)
        if f[8] != "-":
            for r in f[8].strip(";").split(";"):
                x, y, fy = r.split(",")
                x, y, fy = int(x), int(y), float(fy)
                j = y * self.W + x
                below = j + self.W
                # en GVGAI la roca "cae" siempre que puede: si está entre casillas o bajo ella hay vacío
                if fy > 0 or (below < len(self.grid) and self.grid[below] in (E, P2)):
                    self.fall[j] = 1
        a = self.agent = Agent()
        a.x, a.y, a.gems, a.alive = ax, ay, self.gems, True
        self.need_each = NEED
        self.time_left = MAX_TICKS - self.tick
        self.time_start = MAX_TICKS
        self.level = 0

    def exit_open(self) -> bool:
        return self.gems >= NEED

    def window(self):
        return 0, 0, self.W - 1, self.H - 1             # el nivel entero cabe en pantalla (26×13)


class GvgaiBridge:
    """Proceso Java con el motor. play(level, seed, policy) juega una partida completa."""

    def __init__(self):
        cp = f"{ROOT / 'vendor' / 'classes'}{os.pathsep}{ROOT / 'vendor' / 'GVGAI' / 'gson-2.6.2.jar'}"
        self.p = subprocess.Popen(["java", "-cp", cp, "boulderduo.Bridge", str(GAME)], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1,
                                  cwd=str(ROOT / "vendor" / "GVGAI"))

    def _read(self):
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("el proceso de GVGAI terminó")
            if line.startswith("@"):
                return line.rstrip("\n")

    def labels(self, k=3, reps=4):
        """Probabilidad de morir al tomar ↑ → ↓ ← / quieto y luego no hacer nada k ticks (modelo del juego)."""
        self.p.stdin.write(f"L {k} {reps}\n"); self.p.stdin.flush()
        return [float(v) for v in self._read()[3:].split()]

    def play(self, level: int, seed: int, policy, on_state=None):
        """policy(state, bridge) → nuestra dirección 0..4 (o 'use' para el pico). Devuelve (ganó, puntaje, ticks).

        `level` es un nivel oficial (0–4) o la ruta a un archivo de nivel."""
        path = LEVELS[level] if isinstance(level, int) else Path(level).resolve()   # nivel oficial 0–4 o un archivo
        self.p.stdin.write(f"G {path} {seed}\n"); self.p.stdin.flush()
        while True:
            line = self._read()
            if line.startswith("@E"):
                _, won, score, ticks = line.split(" ")
                return int(won), float(score), int(ticks)
            st = GvgaiState(line[3:])
            st.level = level
            if on_state:
                on_state(st, self)
            a = policy(st, self)
            b = 5 if a == "use" else TO_BRIDGE[a]
            self.p.stdin.write(f"A {b}\n"); self.p.stdin.flush()

    def close(self):
        try:
            self.p.stdin.write("Q\n"); self.p.stdin.flush()
        except OSError:
            pass
        self.p.wait(timeout=10)
