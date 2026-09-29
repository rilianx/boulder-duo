"""Calibración: agentes de GVGAI (OLETS, sampleMCTS, ...) en los 5 niveles oficiales de Boulder Dash.

    python gvgai_baselines.py --agents olets,sampleMCTS --seeds 5
Cada agente usa el límite de la competencia: 40 ms por acción (descalificado si pasa de 50 ms), 2000 ticks.
Correrlo con la máquina libre: con la CPU saturada los agentes se pasan del tiempo y quedan descalificados.
"""
import argparse
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from boulder.gvgai_env import GAME, LEVELS, ROOT
from boulder.generic import game_file, level_file

AGENTS = {"olets": "tracks.singlePlayer.advanced.olets.Agent",
          "sampleMCTS": "tracks.singlePlayer.advanced.sampleMCTS.Agent",
          "sampleRHEA": "tracks.singlePlayer.advanced.sampleRHEA.Agent",
          "random": "tracks.singlePlayer.simple.sampleRandom.Agent"}


def run(agent, level, seeds, game="boulderdash"):
    cp = f"{ROOT / 'vendor' / 'classes'}{os.pathsep}{ROOT / 'vendor' / 'GVGAI' / 'gson-2.6.2.jar'}"
    out = subprocess.run(["java", "-cp", cp, "boulderduo.RunAgent", str(game_file(game)), AGENTS[agent], str(level_file(game, level))]
                         + [str(s) for s in seeds], capture_output=True, text=True, cwd=str(ROOT / "vendor" / "GVGAI")).stdout
    return [tuple(float(v) for v in l.split()[1:]) for l in out.splitlines() if l.startswith("@E")]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--agents", default="olets,sampleMCTS")
    p.add_argument("--seeds", type=int, default=5)
    p.add_argument("--procs", type=int, default=4)
    p.add_argument("--game", default="boulderdash")
    a = p.parse_args()
    for ag in a.agents.split(","):
        with ThreadPoolExecutor(a.procs) as ex:
            res = list(ex.map(lambda lv: (lv, run(ag, lv, range(1, a.seeds + 1), a.game)), range(5)))
        allr = [r for _, rs in res for r in rs]
        # GVGAI: 1 gana, 0 pierde, -100 descalificado (se pasó del tiempo por acción)
        per = " ".join(f"n{lv}:{sum(r[0] == 1 for r in rs)}/{len(rs)}" for lv, rs in res)
        disq = sum(r[0] == -100 for r in allr)
        print(f"{a.game} {ag:>11}: victorias {100 * sum(r[0] == 1 for r in allr) / len(allr):5.1f}% ({per}) | "
              f"descalificadas {disq}/{len(allr)} | puntaje medio (sin descalificadas) "
              f"{np.mean([r[1] for r in allr if r[0] != -100] or [0]):5.1f} | ticks medios {np.mean([r[2] for r in allr]):5.0f}",
              flush=True)

if __name__ == "__main__":
    main()
