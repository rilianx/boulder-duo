"""Ajusta los parámetros del A* (boulder/policy.py) con CEM, sin redes: prueba, mide y se queda con lo mejor.

    python tune_astar.py --gens 20 --pop 16 --lives 60        # guarda runs/astar_tuned.json
    python tune_astar.py --eval --lives 400                   # compara ajustado vs. a mano en vidas nuevas

Puntaje por vida = 5·gemas + 60·salida − 40·muerte − 0,05·ticks (las recompensas del RL, sin el premio
por acercarse). Cada generación evalúa a todos los candidatos en los mismos niveles (números aleatorios
comunes) para que las diferencias vengan de los parámetros y no de la suerte.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np

from boulder.env import BoulderEnv
from boulder.policy import DEFAULT, LEARNED_DEFAULT, LEARNED_PARAMS, PARAMS, act, act_learned

RUNS = Path(__file__).parent / "runs"
SPACE, NAMES, LO, HI, OUT = PARAMS, None, None, None, None
_MODEL = None


def set_space(learned: bool):
    global SPACE, NAMES, LO, HI, OUT
    SPACE = LEARNED_PARAMS if learned else PARAMS
    NAMES = list(SPACE)
    LO = np.array([SPACE[k][0] for k in NAMES])
    HI = np.array([SPACE[k][1] for k in NAMES])
    OUT = RUNS / ("astar_learned_tuned.json" if learned else "astar_tuned.json")


set_space(False)


def policy_for(P):
    """Reglas a mano si P trae h_fall; predictor de muerte si trae w_risk."""
    global _MODEL
    if "w_risk" not in P:
        return lambda sim: act(sim, P)
    if _MODEL is None:
        import torch
        from boulder.danger import DangerModel
        torch.set_num_threads(1)
        _MODEL = DangerModel(RUNS / "danger.pt")
    return lambda sim: act_learned(sim, P, _MODEL)


def decode(u):
    return {k: float(v) for k, v in zip(NAMES, LO + np.clip(u, 0, 1) * (HI - LO))}


def encode(P):
    return (np.array([P[k] for k in NAMES]) - LO) / (HI - LO)


def play(job):
    P, lives, seed = job
    pol = policy_for(P)
    env = BoulderEnv(seed=seed)
    env.tok.encode = lambda sim: (None, None)
    env.reset()
    stats = {"exit": 0, "death": 0, "timeout": 0}
    gems = ticks = done = 0
    while done < lives:
        _, _, te, tr, info = env.step(pol(env.sim))
        ticks += 1
        if te or tr:
            stats[info["outcome"]] += 1
            gems += info["gems"]
            done += 1
    score = (5 * gems + 60 * stats["exit"] - 40 * stats["death"] - 0.05 * ticks) / lives
    return score, gems / lives, {k: 100 * v / lives for k, v in stats.items()}


def fmt(P):
    return " ".join(f"{k}={P[k]:.1f}" for k in NAMES)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gens", type=int, default=20)
    p.add_argument("--pop", type=int, default=16)
    p.add_argument("--elite", type=int, default=4)
    p.add_argument("--lives", type=int, default=60)
    p.add_argument("--procs", type=int, default=4)
    p.add_argument("--eval", action="store_true")
    p.add_argument("--learned", action="store_true", help="usar el predictor de muerte en vez de las reglas")
    p.add_argument("--seed-base", type=int, default=10_000, help="semillas de la evaluación")
    a = p.parse_args()
    set_space(a.learned)
    pool = mp.get_context("spawn").Pool(a.procs)

    if a.eval:
        cands = [("reglas a mano", DEFAULT)]
        if (RUNS / "astar_tuned.json").exists():
            cands.append(("reglas + CEM", json.loads((RUNS / "astar_tuned.json").read_text())["params"]))
        if (RUNS / "danger.pt").exists():
            cands.append(("aprendido, sin CEM", LEARNED_DEFAULT))
            if (RUNS / "astar_learned_tuned.json").exists():
                cands.append(("aprendido + CEM", json.loads((RUNS / "astar_learned_tuned.json").read_text())["params"]))
        for label, P in cands:
            # bloques de vidas con semillas nuevas (distintas de las del ajuste)
            res = pool.map(play, [(P, a.lives // a.procs, a.seed_base + k) for k in range(a.procs)])
            s = np.mean([r[0] for r in res]); g = np.mean([r[1] for r in res])
            pc = {k: np.mean([r[2][k] for r in res]) for k in ("exit", "death", "timeout")}
            print(f"{label:>18}: puntaje {s:6.1f} | gemas/vida {g:5.2f} | salida {pc['exit']:5.1f}% | "
                  f"muerte {pc['death']:5.1f}% | tiempo {pc['timeout']:5.1f}%")
        return

    rng = np.random.default_rng(0)
    mu = encode(LEARNED_DEFAULT if a.learned else DEFAULT)
    sigma = np.full(len(NAMES), 0.25)
    best = (-1e9, None, None)
    for gen in range(a.gens):
        t0 = time.time()
        U = np.clip(mu + sigma * rng.standard_normal((a.pop, len(NAMES))), 0, 1)
        U[0] = mu                                   # el centro actual siempre compite
        seed = 1_000 + gen
        res = pool.map(play, [(decode(u), a.lives, seed) for u in U])
        scores = np.array([r[0] for r in res])
        order = np.argsort(-scores)
        el = U[order[:a.elite]]
        mu = el.mean(0)
        sigma = np.maximum(0.7 * sigma + 0.3 * el.std(0), 0.03)
        top = res[order[0]]
        if top[0] > best[0]:
            best = (top[0], decode(U[order[0]]), top)
        print(f"gen {gen + 1:2d} | mejor {top[0]:6.1f} (gemas {top[1]:5.2f}, salida {top[2]['exit']:5.1f}%, "
              f"muerte {top[2]['death']:5.1f}%) | centro {scores[0]:6.1f} | {time.time() - t0:4.0f} s", flush=True)
        OUT.parent.mkdir(exist_ok=True)
        OUT.write_text(json.dumps({"params": decode(mu), "best_single": best[1], "gen": gen + 1}, indent=1))
    print("parámetros ajustados:", fmt(decode(mu)))


if __name__ == "__main__":
    main()
