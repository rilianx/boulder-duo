"""Calibración: agentes de GVGAI (OLETS, sampleMCTS, ...) en los 5 niveles oficiales de Boulder Dash.

    python gvgai_baselines.py --agents olets,sampleMCTS --seeds 5
Cada agente usa el límite de la competencia: 40 ms de CPU por acción, 2000 ticks por partida.
"""
import argparse
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

from boulder.gvgai_env import GAME, LEVELS, ROOT

AGENTS = {"olets": "tracks.singlePlayer.advanced.olets.Agent",
          "sampleMCTS": "tracks.singlePlayer.advanced.sampleMCTS.Agent",
          "sampleRHEA": "tracks.singlePlayer.advanced.sampleRHEA.Agent",
          "random": "tracks.singlePlayer.simple.sampleRandom.Agent"}


def run(agent, level, seeds):
    cp = f"{ROOT / 'vendor' / 'classes'}{os.pathsep}{ROOT / 'vendor' / 'GVGAI' / 'gson-2.6.2.jar'}"
    out = subprocess.run(["java", "-cp", cp, "boulderduo.RunAgent", str(GAME), AGENTS[agent], str(LEVELS[level])]
                         + [str(s) for s in seeds], capture_output=True, text=True, cwd=str(ROOT / "vendor" / "GVGAI")).stdout
    return [tuple(float(v) for v in l.split()[1:]) for l in out.splitlines() if l.startswith("@E")]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--agents", default="olets,sampleMCTS")
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--procs", type=int, default=4)
    a = p.parse_args()
    for ag in a.agents.split(","):
        with ThreadPoolExecutor(a.procs) as ex:
            res = list(ex.map(lambda lv: (lv, run(ag, lv, range(1, a.seeds + 1))), range(5)))
        allr = [r for _, rs in res for r in rs]
        per = " ".join(f"n{lv}:{sum(r[0] for r in rs):.0f}/{len(rs)}" for lv, rs in res)
        print(f"{ag:>11}: victorias {100 * sum(r[0] for r in allr) / len(allr):5.1f}% ({per}) | "
              f"puntaje medio {sum(r[1] for r in allr) / len(allr):5.1f} | ticks medios {sum(r[2] for r in allr) / len(allr):5.0f}",
              flush=True)


if __name__ == "__main__":
    main()
