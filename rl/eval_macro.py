"""Evalúa una política de destinos entrenada contra el baseline A* en las mismas condiciones.

    python eval_macro.py --name destinos --lives 300
Muestra gemas por vida y % de salida/muerte/tiempo para: la red (muestreando y en modo codicioso)
y la política "destino más barato" dentro del mismo entorno de destinos.
"""
import argparse
import collections
import multiprocessing as mp
from pathlib import Path

import torch

from boulder.macro import MacroEnv
from boulder.model import PointerTransformer
from boulder.sim import EXIT, GEM


def cheapest(env, *_):
    best, bc = 0, 1e9
    for n, o in enumerate(env.opts):
        if o and o[0] == "goto" and env.sim.grid[o[1]] in (GEM, EXIT) and o[2] < bc:
            best, bc = n, o[2]
    return best


def run(job):
    name, mode, lives, seed = job
    torch.set_num_threads(1)
    env = MacroEnv(seed=seed)
    obs, _ = env.reset()
    model = None
    if mode != "cheapest":
        ck = torch.load(Path(__file__).parent / "runs" / name / "ckpt.pt", weights_only=False)
        model = PointerTransformer(**ck["config"]); model.load_state_dict(ck["model"]); model.eval()
    out = collections.Counter(); gems = done = 0; kinds = collections.Counter()
    while done < lives:
        if model is None:
            a = cheapest(env)
        else:
            with torch.no_grad():
                lg, _ = model(*(torch.from_numpy(x)[None] for x in obs))
            a = int(lg.argmax()) if mode == "greedy" else int(torch.distributions.Categorical(logits=lg).sample())
        o = env.opts[a] if a < len(env.opts) else None
        kinds[("refugio" if o and o[0] == "goto" and env.sim.grid[o[1]] not in (GEM, EXIT)
               else "salida" if o and env.sim.grid[o[1]] == EXIT else "gema" if o and o[0] == "goto"
               else o[0] if o else "inválida")] += 1
        obs, _, te, tr, info = env.step(a)
        if te or tr:
            done += 1; out[info["outcome"]] += 1; gems += info["gems"]
    return mode, gems / lives, {k: 100 * out[k] / lives for k in ("exit", "death", "timeout")}, kinds


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--name", default="destinos")
    p.add_argument("--lives", type=int, default=300)
    a = p.parse_args()
    jobs = [(a.name, m, a.lives, 123) for m in ("cheapest", "sample", "greedy")]
    with mp.get_context("spawn").Pool(3) as pool:
        for mode, gpl, pct, kinds in pool.imap(run, jobs):
            tot = sum(kinds.values())
            mix = ", ".join(f"{k} {100 * v / tot:.0f}%" for k, v in kinds.most_common())
            label = {"cheapest": "destino más barato", "sample": "red (muestreo)", "greedy": "red (codiciosa)"}[mode]
            print(f"{label:>20}: gemas/vida {gpl:5.2f} | salida {pct['exit']:5.1f}% | muerte {pct['death']:5.1f}% | "
                  f"tiempo {pct['timeout']:5.1f}% | elige: {mix}", flush=True)


if __name__ == "__main__":
    main()
