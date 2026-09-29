"""Política trivial con A*: ir a la gema más barata (según costo con peligro) y, con la cuota, a la salida.

    python baseline.py --lives 300              # evalúa varias penalizaciones de peligro
Mide lo mismo que el juego y PPO: gemas por vida, % que sale, % que muere, % que se le acaba el tiempo.
"""
from __future__ import annotations

import argparse
import math
import multiprocessing as mp
import time

from boulder.astar import exit_cells, gem_cells, hazard_map, plan
from boulder.env import BoulderEnv
from boulder.sim import DIRT, E, H, STAY, W


def act(sim, hazard):
    goals = exit_cells(sim) if sim.exit_open() else gem_cells(sim)
    hz = hazard_map(sim)
    r = plan(sim, goals, hazard, hz)
    if r is None or r[2] is None:
        # nada alcanzable: si donde estoy es peligroso, voy a la casilla segura más cercana
        a = sim.agent
        here = a.y * W + a.x
        if hz[here]:
            safe = {j for j in range(2 * W, W * H) if not hz[j] and sim.grid[j] in (E, DIRT)}
            r = plan(sim, safe, math.inf, hz)
            if r and r[2] is not None:
                return r[2]
        return STAY
    return r[2]


def evaluate(args):
    hazard, lives, seed = args
    env = BoulderEnv(seed=seed)
    env.tok.encode = lambda sim: (None, None)          # la política no usa tokens: más rápido
    env.reset()
    stats = {"exit": 0, "death": 0, "timeout": 0}
    gems = ticks = 0
    t0 = time.time()
    done = 0
    while done < lives:
        _, _, term, trunc, info = env.step(act(env.sim, hazard))
        ticks += 1
        if term or trunc:
            stats[info["outcome"]] += 1
            gems += info["gems"]
            done += 1
    return hazard, lives, gems / lives, {k: 100 * v / lives for k, v in stats.items()}, ticks / lives, time.time() - t0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lives", type=int, default=300)
    p.add_argument("--hazards", default="0,5,25,inf")
    p.add_argument("--procs", type=int, default=4)
    a = p.parse_args()
    hz = [float(h) for h in a.hazards.split(",")]
    with mp.get_context("spawn").Pool(a.procs) as pool:
        for hazard, lives, gpl, pct, tpl, dt in pool.imap(evaluate, [(h, a.lives, 11) for h in hz]):
            print(f"peligro {hazard:>4}: gemas/vida {gpl:5.2f} | salida {pct['exit']:5.1f}% | muerte {pct['death']:5.1f}% | "
                  f"tiempo {pct['timeout']:5.1f}% | {tpl:5.0f} ticks/vida | {lives} vidas en {dt:.0f} s", flush=True)


if __name__ == "__main__":
    main()
