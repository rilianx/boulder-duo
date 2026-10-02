"""Prueba de referencia para refactorizar sin cambiar el comportamiento.

Juega partidas deterministas (semillas fijas, A* sin límite de tiempo) con el explorador barato y con el
agente completo aprendiendo, y guarda la secuencia de acciones y el conocimiento final. `--check` compara
contra lo guardado y dice qué juego y qué campo difiere.

    python golden.py --save runs/golden.json
    python golden.py --check runs/golden.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

from boulder.cube import CellRisk
from boulder.generic import DEFAULT_W, GDanger, GenericAgent, GenericBridge, Knowledge
from boulder.highlevel import Commander
from boulder.objcube import ObjectCubeNavigator
from generic_train import random_weights

GAMES = ["sokoban", "portals", "frogs", "aliens", "chase", "missilecommand", "survivezombies", "zelda",
         "boulderdash", "butterflies"]
# sin límite de tiempo por acción: si no, una decisión lenta se vuelve "nada" según la carga de la máquina
os.environ.setdefault("GVGAI_CLASSES", str(Path(__file__).parent / "gvgai" / "vendor" / "classes_notime"))
RUNS = Path(os.environ.get("GVGAI_RUNS", Path(__file__).parent / "runs" / "mecanicas"))
TICKS = 250


class Stop(Exception):
    pass


def play(game, level, seed, policy, ticks):
    acts = []

    def pol(st, br):
        if st.tick >= ticks:
            raise Stop
        a = policy(st, br)
        acts.append(a)
        return a
    if hasattr(policy, "end"):
        pol.end = policy.end
    b = GenericBridge(game)
    try:
        b.play(level, seed, pol)
    except Stop:
        pass
    finally:
        b.p.kill()
        b.p.wait()
    return acts


def canon(kj):
    return json.loads(json.dumps(kj, sort_keys=True))


def run_game(game):
    torch.manual_seed(0)
    d = RUNS / game
    out = {}
    # 1) explorador barato desde cero
    K = Knowledge()
    rng = np.random.default_rng(7)
    ag = GenericAgent(random_weights(rng), know=K, rng=rng, eps=0.3)
    acts = play(game, 0, 11, ag, TICKS)
    out["explorer"] = {"acts": hashlib.sha1(json.dumps(acts).encode()).hexdigest(), "n": len(acts),
                       "know": canon(K.to_json())}
    # 2) agente completo aprendiendo, desde el conocimiento de la práctica
    K = Knowledge.from_json(json.loads((d / "knowledge_hl.json").read_text()))
    risk, D = CellRisk(d / "cell_risk.pt"), GDanger(d / "danger.pt")
    hl = {"chase_movers": True} if game == "chase" else {}
    for g, (lv, seed) in enumerate([(1, 21), (2, 22)]):
        nav = ObjectCubeNavigator(K, risk, {"w_risk": 20.0, "alpha": 1.0, "patience": 0, "budget_ms": 1e7}, danger=D)
        cmd = Commander(K, dict(DEFAULT_W), nav, {"practice": True, **hl})
        acts = play(game, lv, seed, cmd, TICKS)
        if os.environ.get("GOLDEN_DUMP"):
            Path(os.environ["GOLDEN_DUMP"] + f"_{game}_{g}.json").write_text(json.dumps([str(x) for x in acts]))
        out[f"agent{g}"] = {"acts": hashlib.sha1(json.dumps(acts).encode()).hexdigest(), "n": len(acts),
                            "stats": cmd.stats}
    out["agent_know"] = canon(K.to_json())
    return out


def diff(a, b, path=""):
    if type(a) != type(b):
        return [f"{path}: tipo {type(a).__name__} ≠ {type(b).__name__}"]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}/{k}: solo en {'nuevo' if k in b else 'referencia'}")
            else:
                out += diff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: largo {len(a)} ≠ {len(b)}"]
        return [x for i in range(len(a)) for x in diff(a[i], b[i], f"{path}[{i}]")]
    if isinstance(a, float) and isinstance(b, float):
        return [] if abs(a - b) <= 1e-9 * max(1.0, abs(a)) else [f"{path}: {a} ≠ {b}"]
    return [] if a == b else [f"{path}: {a!r} ≠ {b!r}"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--save")
    p.add_argument("--check")
    p.add_argument("--games", default=",".join(GAMES))
    a = p.parse_args()
    torch.set_num_threads(1)
    res = {g: run_game(g) for g in a.games.split(",")}
    if a.save:
        Path(a.save).write_text(json.dumps(res, sort_keys=True))
        print("guardado", a.save)
    if a.check:
        ref = json.loads(Path(a.check).read_text())
        bad = 0
        for g, r in res.items():
            dd = diff(ref[g], canon(r), g)
            bad += len(dd)
            print(f"{g}: {'idéntico' if not dd else f'{len(dd)} diferencias'}")
            for x in dd[:8]:
                print("   ", x)
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
