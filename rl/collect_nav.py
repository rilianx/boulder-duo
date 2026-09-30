"""Segunda pasada de datos: juntar etiquetas contrafactuales jugando con el navegador bueno.

La primera pasada exploraba al azar y en Frogs moría siempre en la carretera: nunca vio el río. Aquí el
navegador (objetos + predictor, que ya sabe cruzar la carretera) recibe órdenes al azar y va a zonas nuevas;
en cada tick se guardan las etiquetas "¿muero si entro aquí?" (el modelo del juego se usa solo para
entrenar). Después se reentrenan el predictor y el riesgo por casilla con los datos viejos + nuevos.

    python collect_nav.py frogs --samples 30000
"""
from __future__ import annotations

import os
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

# carpeta de modelos: GVGAI_RUNS la cambia (p. ej. para la variante con presupuesto, sin tocar la principal)
RUNS = Path(os.environ.get("GVGAI_RUNS", Path(__file__).parent / "runs" / "generic"))


class NoveltyOrderGiver(OrderGiver):
    """Como OrderGiver, pero prefiere destinos con tipos de sprite poco vistos en los datos (sin nombrarlos)."""

    def __init__(self, nav, rng, stats, counts):
        super().__init__(nav, rng, stats)
        self.counts = counts                       # itype → ejemplos etiquetados con ese tipo en la casilla

    linger = 0
    bank = False

    def _decide(self, st, br):
        if self.linger > 0:                          # quedarse en la orilla juntando etiquetas
            self.linger -= 1
            return 4
        return super()._decide(st, br)

    def _finish(self, how, st=None):
        if how == "reached" and self.bank:
            self.linger = 10
        super()._finish(how, st)

    def _new_order(self, st):
        K = self.nav.know
        N, W = len(st.masks), st.W
        blocked = K.blocked_cells(st)
        is_rare = [any(st.masks[j] >> t & 1 and self.counts.get(t, 0) < 2000 for t in range(63)
                       if t not in K.avatar_types) for j in range(N)]
        rare = [j for j in range(N) if j != st.pos and not blocked[j] and is_rare[j]]
        # orilla: casillas pisables, no raras, con una vecina rara (desde ahí se etiqueta entrar a lo raro)
        near = [j for j in range(N) if j != st.pos and not blocked[j] and not is_rare[j]
                and any(0 <= j + o < N and is_rare[j + o] for o in (-W, 1, W, -1))]
        self.bank = False
        u = self.rng.random()
        if near and u < 0.5:
            rare, self.bank = near, True
        if rare and u < 0.85:
            j = int(self.rng.choice(rare))
            from boulder.nav import shortest
            d = shortest(st, K, j)
            if d is not None and d >= 1:
                self.goal, self.dist, self.t0 = j, d, st.tick
                self.stats["orders"] += 1
                return
        super()._new_order(st)


def _collect(job):
    game, levels, n_target, seed = job
    torch.set_num_threads(1)
    d = RUNS / game
    K = Knowledge.from_json(json.loads((d / "knowledge.json").read_text()))
    D = GDanger(d / "danger.pt")
    risk = CellRisk(d / "cell_risk.pt")
    rng = np.random.default_rng(seed)
    X, Y = [], []
    with np.load(d / "data.npz") as z:                # cuántas veces vimos cada tipo en la casilla destino
        T0 = int(z["T"])
        pres = z["X"][:, [t * 49 + 24 for t in range(T0)]].sum(0)
    counts = {t: int(pres[t]) for t in range(T0)}
    b = GenericBridge(game)
    T = None
    stats = {"orders": 0, "reached": 0, "died": 0, "timeout": 0, "unreachable": 0, "reached_win": 0, "stretch": []}
    try:
        g = 0
        while len(Y) < n_target:
            f = d / "nav_objects.json"
            P = {**(json.loads(f.read_text()) if f.exists() else NAV_DEFAULT), "patience": 10}
            og = NoveltyOrderGiver(ObjectCubeNavigator(K, risk, P, danger=D), rng, stats, counts)

            def pol(st, br):
                nonlocal T
                if T is None:
                    T = D.T
                a = og(st, br)
                if rng.random() < 0.15:
                    a = int(rng.integers(5))          # algo de azar para ver también errores
                W, N = st.W, len(st.masks)
                cand = [(dd, st.pos + o) for dd, o in enumerate((-W, 1, W, -1)) if 0 <= st.pos + o < N]
                cand = [(dd, j) for dd, j in cand if not K.blocked_cells(st)[j]]
                if cand:
                    lab = br.labels(3, 4)
                    X.append(gfeatures(gplanes(st, T), [j for _, j in cand], [dd for dd, _ in cand], W).astype(np.uint8))
                    Y.extend(lab[dd] for dd, _ in cand)
                    for _, j in cand:
                        for t in range(T):
                            if st.masks[j] >> t & 1:
                                counts[t] = counts.get(t, 0) + 1
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
    with np.load(d / "data.npz") as z:                # leer todo antes de sobrescribir el archivo
        Xo, Yo, T = z["X"], z["Y"], z["T"]
    np.savez_compressed(d / "data_first_pass.npz", X=Xo, Y=Yo, T=T)
    np.savez_compressed(d / "data.npz", X=np.concatenate([Xo, Xn]), Y=np.concatenate([Yo, Yn]), T=T)
    print(f"{a.game}: {len(Yn):,} ejemplos nuevos ({100 * (Yn > 0.5).mean():.1f}% con p > 0,5); total {len(Yn) + len(Yo):,}")
    train(a.game)
    w, b = fit_cell_risk(d / "data.npz", d / "cell_risk.pt")
    print("riesgo por casilla reajustado; sesgo", round(b, 2))


if __name__ == "__main__":
    main()
