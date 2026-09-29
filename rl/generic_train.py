"""Agente genérico por juego de GVGAI: aprende transitabilidad, peligro y valores, sin reglas del juego.

    python generic_train.py boulderdash all        # collect → train → tune → eval
    python generic_train.py zelda collect|train|tune|eval
Boulder Dash usa niveles generados para aprender y ajustar (los 5 oficiales quedan para la prueba);
los demás juegos solo tienen 5 niveles: se aprende y ajusta en 0–2 y se reporta aparte 3–4 (no vistos).
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from boulder.generic import (DEFAULT_W, WEIGHTS, GDanger, GDangerNet, GenericAgent, GenericBridge, Knowledge,
                             gfeatures, gplanes)
from boulder.gvgai_levels import write_levels

RUNS = Path(__file__).parent / "runs" / "generic"


def paths(game):
    d = RUNS / game
    d.mkdir(parents=True, exist_ok=True)
    return d


def train_levels(game):
    if game == "boulderdash":
        return [str(p) for p in write_levels(300, Path(__file__).parent / "runs" / "gvgai_levels", 0)]
    return [0, 1, 2]


def random_weights(rng):
    """Pesos al azar con mucha curiosidad: para explorar y tocar de todo mientras se juntan datos."""
    P = {k: float(rng.uniform(lo, hi)) for k, (lo, hi, _) in WEIGHTS.items()}
    P["k_new"] = float(rng.uniform(10, 20))
    P["lam"] = float(rng.uniform(0.02, 0.2))        # ir lejos: para llegar a juntar todo y probar la salida
    return P


# ------------------------------------------------------------------ 1. datos + transitabilidad
def _collect(job):
    game, levels, n_target, seed = job
    rng = np.random.default_rng(seed)
    b = GenericBridge(game)
    K = Knowledge()
    X, Y = [], []
    T = None
    g = 0
    try:
        while len(Y) < n_target:
            ag = GenericAgent(random_weights(rng), know=K, rng=rng, eps=0.3)

            def pol(st, br):
                nonlocal T
                if T is None:
                    T = max(st.types) + 1
                a = ag(st, br)
                W, N = st.W, len(st.masks)
                cand = [(d, st.pos + o) for d, o in enumerate((-W, 1, W, -1)) if 0 <= st.pos + o < N]
                cand = [(d, j) for d, j in cand if not any(st.masks[j] >> t & 1 and K.is_blocking(t) for t in range(63))]
                if cand:
                    lab = br.labels(3, 4)
                    X.append(gfeatures(gplanes(st, T), [j for _, j in cand], [d for d, _ in cand], W).astype(np.uint8))
                    Y.extend(lab[d] for d, _ in cand)
                return a

            b.play(levels[g % len(levels)], seed * 1000 + g, pol)
            g += 1
    finally:
        b.close()
    return np.concatenate(X), np.array(Y, np.float32), K.to_json(), T


def collect(game, samples, procs):
    lv = train_levels(game)
    with ProcessPoolExecutor(procs) as ex:
        parts = list(ex.map(_collect, [(game, lv[k::procs] if len(lv) > procs else lv, samples // procs, 11 + k)
                                       for k in range(procs)]))
    X = np.concatenate([p[0] for p in parts]); Y = np.concatenate([p[1] for p in parts])
    K = Knowledge()
    for p in parts:                                  # combinar lo aprendido por cada proceso
        K.merge(Knowledge.from_json(p[2]))
    d = paths(game)
    np.savez_compressed(d / "data.npz", X=X, Y=Y, T=parts[0][3])
    (d / "knowledge.json").write_text(json.dumps(K.to_json()))
    print(f"{game}: {len(Y):,} ejemplos | {100 * (Y > 0.5).mean():.1f}% con p > 0,5 | "
          f"bloquean: {sorted(t for t in set(K.passed) | set(K.blocked) if K.is_blocking(t))}")
    describe(game, K)


def describe(game, K):
    b = GenericBridge(game); b.play(train_levels(game)[0], 0, lambda st, br: 4); types = b.types; b.close()
    for t in sorted(K.eff):
        ds, dr, da, pd, n = K.effect(t)
        wins = {k: v for k, v in K.term.get(t, {}).items() if v[1]}
        print(f"   {types[t][0]:>14}: tocado {n:5d} | Δpuntaje {ds:+.2f} | Δrecursos {dr:+.2f} | cambia avatar {da:.2f} | "
              f"muere {pd:.2f}" + (f" | gana con (avatar|recursos) {sorted(wins)[:4]}" if wins else ""))


# ------------------------------------------------------------------ 2. predictor
def train(game, epochs=10, hidden=128):
    d = paths(game)
    z = np.load(d / "data.npz")
    X, Y, T = torch.from_numpy(z["X"].astype(np.float32)), torch.from_numpy(z["Y"]), int(z["T"])
    n = len(Y); perm = torch.randperm(n, generator=torch.Generator().manual_seed(0))
    va, tr = perm[: n // 5], perm[n // 5:]
    torch.manual_seed(0)
    net = GDangerNet(X.shape[1], hidden)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    pw = float((1 - Y[tr].mean()) / max(float(Y[tr].mean()), 1e-3)) ** 0.5
    lossf = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pw))
    for ep in range(epochs):
        p2 = tr[torch.randperm(len(tr))]
        for k in range(0, len(p2), 512):
            b = p2[k:k + 512]
            loss = lossf(net(X[b]), Y[b]); opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        pv = torch.sigmoid(net(X[va])).numpy()
    yv = Y[va].numpy() > 0.5
    pred = pv > 0.5
    tp = (pred & yv).sum(); prec = tp / max(pred.sum(), 1); rec = tp / max(yv.sum(), 1)
    print(f"{game}: predictor | precisión {100 * prec:.1f}% | exhaustividad {100 * rec:.1f}% (validación aleatoria)")
    torch.save({"model": net.state_dict(), "hidden": hidden, "n_in": X.shape[1], "T": T}, d / "danger.pt")


# ------------------------------------------------------------------ 3–4. jugar, CEM, evaluar
_D = {}


def _play(job):
    game, P, level, seeds, use_danger = job
    torch.set_num_threads(1)
    d = paths(game)
    if use_danger and game not in _D:
        _D[game] = GDanger(d / "danger.pt")
    K = Knowledge.from_json(json.loads((d / "knowledge.json").read_text()))
    b = GenericBridge(game)
    try:
        return level, [b.play(level, s, GenericAgent(P, know=K, danger=_D.get(game) if use_danger else None))
                       for s in seeds]
    finally:
        b.close()


def score_of(rs):
    return np.mean([100 * r[0] + r[1] - r[2] / 100 for r in rs])


def tune(game, procs, gens=10, pop=16, elite=4):
    d = paths(game)
    K = Knowledge.from_json(json.loads((d / "knowledge.json").read_text()))
    names = list(WEIGHTS)
    lo = np.array([WEIGHTS[n][0] for n in names]); hi = np.array([WEIGHTS[n][1] for n in names])
    dec = lambda u: {n: float(v) for n, v in zip(names, lo + np.clip(u, 0, 1) * (hi - lo))}
    mu = (np.array([DEFAULT_W[n] for n in names]) - lo) / (hi - lo)
    sigma = np.full(len(names), 0.3)
    rng = np.random.default_rng(0)
    lv = train_levels(game)
    with ProcessPoolExecutor(procs) as pool:
        for gen in range(gens):
            U = np.clip(mu + sigma * rng.standard_normal((pop, len(names))), 0, 1); U[0] = mu
            if game == "boulderdash":
                levels, seeds = list(rng.choice(lv, 6, replace=False)), [gen]
            else:
                levels, seeds = lv, [2 * gen, 2 * gen + 1]
            jobs = [(game, dec(u), l, seeds, True) for u in U for l in levels]
            res = list(pool.map(_play, jobs))
            per = len(levels)
            scores = np.array([score_of([r for _, rs in res[k * per:(k + 1) * per] for r in rs]) for k in range(pop)])
            wins = [np.mean([r[0] for _, rs in res[k * per:(k + 1) * per] for r in rs]) for k in range(pop)]
            order = np.argsort(-scores)
            el = U[order[:elite]]; mu = el.mean(0); sigma = np.maximum(0.7 * sigma + 0.3 * el.std(0), 0.04)
            print(f"{game} gen {gen + 1:2d}: mejor {scores[order[0]]:7.1f} (victorias {100 * wins[order[0]]:.0f}%) | "
                  f"centro {scores[0]:7.1f} (victorias {100 * wins[0]:.0f}%)", flush=True)
            (d / "values.json").write_text(json.dumps(dec(mu), indent=1))


def evaluate(game, procs, n_seeds=20):
    d = paths(game)
    P = json.loads((d / "values.json").read_text())
    seeds = list(range(100, 100 + n_seeds))
    with ProcessPoolExecutor(procs) as pool:
        for label, use in (("genérico con predictor", True), ("genérico sin predictor", False)):
            res = dict(pool.map(_play, [(game, P, lv, seeds, use) for lv in range(5)]))
            allr = [r for rs in res.values() for r in rs]
            per = " ".join(f"n{lv}:{sum(r[0] for r in rs)}/{len(rs)}" for lv, rs in sorted(res.items()))
            unseen = [r for lv, rs in res.items() if lv in (3, 4) for r in rs]
            print(f"{game} {label}: victorias {100 * np.mean([r[0] for r in allr]):5.1f}% ({per}) | "
                  f"niveles 3–4 {100 * np.mean([r[0] for r in unseen]):5.1f}% | puntaje {np.mean([r[1] for r in allr]):5.1f}",
                  flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("game")
    p.add_argument("cmd", choices=["collect", "train", "tune", "eval", "all"])
    p.add_argument("--samples", type=int, default=60_000)
    p.add_argument("--procs", type=int, default=4)
    p.add_argument("--seeds", type=int, default=20)
    a = p.parse_args()
    steps = ["collect", "train", "tune", "eval"] if a.cmd == "all" else [a.cmd]
    d = paths(a.game)
    if a.cmd == "all":                                # reanudable: salta lo que ya está hecho
        if (d / "data.npz").exists() and (d / "knowledge.json").exists():
            steps.remove("collect")
        if (d / "danger.pt").exists() and "collect" not in steps:
            steps.remove("train")
    for s in steps:
        {"collect": lambda: collect(a.game, a.samples, a.procs), "train": lambda: train(a.game),
         "tune": lambda: tune(a.game, a.procs), "eval": lambda: evaluate(a.game, a.procs, a.seeds)}[s]()


if __name__ == "__main__":
    main()
