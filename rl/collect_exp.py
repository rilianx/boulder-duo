"""Ablación sin simulador: el predictor de muerte y el riesgo por casilla aprendidos SOLO de lo vivido.

En vez de preguntarle al modelo del juego "¿y si entro aquí?" (labels(), contrafactual), cada paso que el
agente da de verdad se etiqueta con lo que le pasó: 1 si murió en los 3 ticks siguientes, 0 si sobrevivió.
Solo se ve el resultado de lo que eligió hacer, así que hay muchos menos datos y más sesgados. Se aprende en
rondas: se juega con los modelos actuales (al principio sin riesgo aprendido), se reentrena y se repite.
Los modelos van a runs/generic/<juego>_exp; el conocimiento de transitabilidad, giro y arrastre (aprendido
jugando) se copia tal cual.

    python collect_exp.py frogs --rounds 3 --samples 20000
    python nav_bench.py frogs --curve --model-dir frogs_exp       # evaluar igual que el original
"""
from __future__ import annotations

import os
import argparse
import json
import shutil
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from boulder.cube import CellRisk, fit_cell_risk
from boulder.generic import GDanger, GenericBridge, Knowledge, gfeatures, gplanes
from boulder.nav import NAV_DEFAULT
from boulder.objcube import ObjectCubeNavigator
from collect_nav import NoveltyOrderGiver
from generic_train import train
from nav_bench import train_levels

# carpeta de modelos: GVGAI_RUNS la cambia (p. ej. para la variante con presupuesto, sin tocar la principal)
RUNS = Path(os.environ.get("GVGAI_RUNS", Path(__file__).parent / "runs" / "generic"))
K_DEATH = 3


def _collect(job):
    game, mdir, levels, n_target, seed, eps, k_death = job
    torch.set_num_threads(1)
    d = RUNS / mdir
    K = Knowledge.from_json(json.loads((d / "knowledge.json").read_text()))
    D = GDanger(d / "danger.pt") if (d / "danger.pt").exists() else None
    risk = CellRisk(d / "cell_risk.pt")
    T = json.loads((d / "T.json").read_text())["T"]
    rng = np.random.default_rng(seed)
    X, Y = [], []
    counts = {}
    b = GenericBridge(game)
    stats = {"orders": 0, "reached": 0, "died": 0, "timeout": 0, "unreachable": 0, "reached_win": 0, "stretch": []}
    try:
        g = 0
        while len(Y) < n_target:
            P = {**NAV_DEFAULT, "w_risk": 20.0, "alpha": 1.0}
            og = NoveltyOrderGiver(ObjectCubeNavigator(K, risk, P, danger=D), rng, stats, counts)
            pending = []                                   # (tick del paso, índice en X/Y)

            def pol(st, br):
                # los pasos con más de K_DEATH ticks sin morir: sobrevivió → 0 (ya está puesto)
                pending[:] = [(t, i) for t, i in pending if st.tick - t <= k_death]
                a = og(st, br)
                if rng.random() < eps:
                    a = int(rng.integers(5))              # algo de azar: sin esto casi no se ven muertes
                W, N = st.W, len(st.masks)
                if a is not None and a != "use" and a < 4:
                    j = st.pos + (-W, 1, W, -1)[a]
                    if 0 <= j < N and not K.blocked_cells(st)[j]:
                        X.append(gfeatures(gplanes(st, T), [j], [a], W).astype(np.uint8))
                        Y.append(0.0)
                        pending.append((st.tick, len(Y) - 1))
                        for t in range(T):
                            if st.masks[j] >> t & 1:
                                counts[t] = counts.get(t, 0) + 1
                return a

            def end(won):
                if won != 1:                               # murió: los pasos recientes se etiquetan 1
                    for _, i in pending:
                        Y[i] = 1.0
                og.end(won)
            pol.end = end
            b.play(levels[g % len(levels)], seed * 1000 + g, pol)
            g += 1
    finally:
        b.close()
    return np.concatenate(X), np.array(Y, np.float32)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("game")
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--samples", type=int, default=20_000, help="pasos etiquetados por ronda")
    p.add_argument("--procs", type=int, default=4)
    p.add_argument("--k", type=int, default=K_DEATH,
                   help="a cuántos pasos previos a la muerte se culpa (3 = todos los de los 3 ticks anteriores)")
    a = p.parse_args()
    src, mdir = RUNS / a.game, f"{a.game}_exp" + ("" if a.k == K_DEATH else f"_k{a.k}")
    d = RUNS / mdir
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / "knowledge.json", d / "knowledge.json")
    with np.load(src / "data.npz") as z:
        T = int(z["T"])
    (d / "T.json").write_text(json.dumps({"T": T}))
    # ronda 0: sin riesgo aprendido (pesos 0, sesgo muy negativo) y sin predictor
    torch.save({"w": np.zeros(2 * T, np.float32), "b": -6.0, "T": T}, d / "cell_risk.pt")
    lv = train_levels(a.game)
    Xs, Ys = [], []
    for r in range(a.rounds):
        eps = 0.15
        with ProcessPoolExecutor(a.procs) as ex:
            parts = list(ex.map(_collect, [(a.game, mdir, lv[k::a.procs], a.samples // a.procs, 91 + 10 * r + k, eps, a.k)
                                           for k in range(a.procs)]))
        Xs += [q[0] for q in parts]; Ys += [q[1] for q in parts]
        X, Y = np.concatenate(Xs), np.concatenate(Ys)
        np.savez_compressed(d / "data.npz", X=X, Y=Y, T=T)
        print(f"{a.game} ronda {r}: {len(Y):,} pasos vividos, {int(Y.sum())} con muerte ({100 * Y.mean():.2f}%)", flush=True)
        train(mdir)
        fit_cell_risk(d / "data.npz", d / "cell_risk.pt")
    print(f"listo: modelos en {d}", flush=True)


if __name__ == "__main__":
    main()
