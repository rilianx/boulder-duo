"""Segunda pasada de datos: juntar etiquetas contrafactuales jugando con el navegador bueno.

La primera pasada exploraba al azar y en Frogs moría siempre en la carretera: nunca vio el río. Aquí el
navegador (objetos + predictor, que ya sabe cruzar la carretera) recibe órdenes al azar y va a zonas nuevas;
en cada tick se guardan las etiquetas "¿muero si entro aquí?" (el modelo del juego se usa solo para
entrenar). Después se reentrenan el predictor y el riesgo por casilla con los datos viejos + nuevos.

    python collect_nav.py frogs --samples 30000
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from boulder.cube import CellRisk, fit_cell_risk
from boulder.generic import GDanger, GenericBridge, Knowledge, gfeatures, gplanes
from boulder.nav import NAV_DEFAULT
from boulder.objcube import ObjectCubeNavigator
from generic_train import train, train_levels
from nav_bench import OrderGiver

RUNS = Path(__file__).parent / "runs" / "generic"


def _collect(job):
    game, levels, n_target, seed = job
    torch.set_num_threads(1)
    d = RUNS / game
    K = Knowledge.from_json(json.loads((d / "knowledge.json").read_text()))
    D = GDanger(d / "danger.pt")
    risk = CellRisk(d / "cell_risk.pt")
    rng = np.random.default_rng(seed)
    X, Y = [], []
    b = GenericBridge(game)
    T = None
    stats = {"orders": 0, "reached": 0, "died": 0, "timeout": 0, "unreachable": 0, "reached_win": 0, "stretch": []}
    try:
        g = 0
        while len(Y) < n_target:
            og = OrderGiver(ObjectCubeNavigator(K, risk, NAV_DEFAULT, danger=D), rng, stats)

            def pol(st, br):
                nonlocal T
                if T is None:
                    T = D.T
                a = og(st, br)
                if rng.random() < 0.15:
                    a = int(rng.integers(5))          # algo de azar para ver también errores
                W, N = st.W, len(st.masks)
                cand = [(dd, st.pos + o) for dd, o in enumerate((-W, 1, W, -1)) if 0 <= st.pos + o < N]
                cand = [(dd, j) for dd, j in cand if not any(st.masks[j] >> t & 1 and K.is_blocking(t) for t in range(63))]
                if cand:
                    lab = br.labels(3, 4)
                    X.append(gfeatures(gplanes(st, T), [j for _, j in cand], [dd for dd, _ in cand], W).astype(np.uint8))
                    Y.extend(lab[dd] for dd, _ in cand)
                return a
            pol.end = og.end
            b.play(levels[g % len(levels)], seed * 1000 + g, pol)
            g += 1
    finally:
        b.close()
    return np.concatenate(X), np.array(Y, np.float32)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("game")
    p.add_argument("--samples", type=int, default=30_000)
    p.add_argument("--procs", type=int, default=4)
    a = p.parse_args()
    lv = train_levels(a.game)
    with ProcessPoolExecutor(a.procs) as ex:
        parts = list(ex.map(_collect, [(a.game, lv[k::a.procs] if len(lv) > a.procs else lv, a.samples // a.procs, 51 + k)
                                       for k in range(a.procs)]))
    Xn = np.concatenate([q[0] for q in parts]); Yn = np.concatenate([q[1] for q in parts])
    d = RUNS / a.game
    old = np.load(d / "data.npz")
    np.savez_compressed(d / "data_first_pass.npz", X=old["X"], Y=old["Y"], T=old["T"])
    np.savez_compressed(d / "data.npz", X=np.concatenate([old["X"], Xn]), Y=np.concatenate([old["Y"], Yn]), T=old["T"])
    print(f"{a.game}: {len(Yn):,} ejemplos nuevos ({100 * (Yn > 0.5).mean():.1f}% con p > 0,5); total {len(Yn) + len(old['Y']):,}")
    train(a.game)
    w, b = fit_cell_risk(d / "data.npz", d / "cell_risk.pt")
    print("riesgo por casilla reajustado; sesgo", round(b, 2))


if __name__ == "__main__":
    main()
