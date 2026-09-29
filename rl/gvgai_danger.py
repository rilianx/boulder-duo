"""Predictor de muerte + A* + CEM en el Boulder Dash real de GVGAI, sin reglas de peligro escritas a mano.

    python gvgai_danger.py collect --samples 40000     # etiquetas del modelo del juego (vía el puente)
    python gvgai_danger.py train                       # → runs/gvgai_danger.pt (entrena con niveles 0–2)
    python gvgai_danger.py tune                        # CEM de c_dirt, w_risk, detour en niveles 0–2
    python gvgai_danger.py eval --seeds 20             # 5 niveles con semillas nuevas; 3 y 4 nunca vistos

Etiqueta: fracción de 4 copias del modelo del juego en que el avatar muere al entrar a la casilla vecina y
luego quedarse quieto 3 ticks (los enemigos son aleatorios, por eso es una probabilidad).
"""
from __future__ import annotations

import argparse
import json
import random
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from boulder.danger import N_IN, DangerModel, DangerNet, features, planes
from boulder.gvgai_env import GvgaiBridge
from boulder.gvgai_policy import (GV_DEFAULT, GV_LEARNED_DEFAULT, GV_LEARNED_PARAMS, gv_act, gv_act_learned,
                                  gv_costs)
from boulder.sim import DIRT, E, GEM

RUNS = Path(__file__).parent / "runs"
DATA = RUNS / "gvgai_danger_data.npz"
MODEL = RUNS / "gvgai_danger.pt"
TUNED = RUNS / "gvgai_learned_tuned.json"
TRAIN_LEVELS, TEST_LEVELS = [0, 1, 2], [3, 4]
RISKY = {**GV_DEFAULT, "h_under": 0.0, "h_col": 0.0, "h_e1": 0.0, "h_e2": 0.0}   # imprudente: visita peligros
RULE = {"c_dirt": 1.0, "h_under": 1.0, "h_col": 1.0, "h_e1": 1.0, "h_e2": 0.0, "detour": 0.0}


# ------------------------------------------------------------------ datos
def _collect(job):
    level, n_target, seed = job
    rnd = random.Random(seed)
    b = GvgaiBridge()
    X, Y, RU = [], [], []
    game = 0
    try:
        while len(Y) < n_target:
            def pol(st, br):
                W = st.W
                i = st.agent.y * W + st.agent.x
                cand = [(d, i + o) for d, o in enumerate((-W, 1, W, -1)) if st.grid[i + o] in (E, DIRT, GEM)]
                if cand:
                    lab = br.labels(3, 4)
                    pl = planes(st)
                    base = gv_costs(st, {**RULE, "h_under": 0, "h_col": 0, "h_e1": 0})
                    rule = gv_costs(st, RULE)
                    X.append(features(pl, [j for _, j in cand], [d for d, _ in cand], W).astype(np.uint8))
                    for d, j in cand:
                        Y.append(lab[d]); RU.append(float(rule[j] > base[j]))
                if rnd.random() < 0.3:
                    return rnd.randrange(5)
                return gv_act(st, RISKY)
            b.play(level, seed * 1000 + game, pol)
            game += 1
    finally:
        b.close()
    return level, np.concatenate(X), np.array(Y, np.float32), np.array(RU, np.float32)


def collect(samples, procs):
    per = samples // 5
    with ProcessPoolExecutor(procs) as ex:
        parts = list(ex.map(_collect, [(lv, per, 7 + lv) for lv in range(5)]))
    X = np.concatenate([p[1] for p in parts]); Y = np.concatenate([p[2] for p in parts])
    RU = np.concatenate([p[3] for p in parts]); LV = np.concatenate([np.full(len(p[2]), p[0]) for p in parts])
    RUNS.mkdir(exist_ok=True)
    np.savez_compressed(DATA, X=X, Y=Y, RU=RU, LV=LV)
    print(f"{len(Y):,} ejemplos | probabilidad media de muerte {Y.mean():.3f} | "
          f"{100 * (Y > 0.5).mean():.1f}% con p > 0,5")


# ------------------------------------------------------------------ predictor
def auc(y, p):
    order = np.argsort(p); r = np.empty(len(p)); r[order] = np.arange(1, len(p) + 1)
    pos = y == 1
    return (r[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / max(pos.sum() * (~pos).sum(), 1)


def prf(y, pred):
    tp = (pred & y).sum(); fp = (pred & ~y).sum(); fn = (~pred & y).sum()
    pr, rc = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    return pr, rc, 2 * pr * rc / max(pr + rc, 1e-9)


def train(epochs=12, hidden=128):
    d = np.load(DATA)
    X, Y, RU, LV = d["X"], d["Y"], d["RU"], d["LV"]
    tr = np.isin(LV, TRAIN_LEVELS)
    Xt, Yt = torch.from_numpy(X[tr].astype(np.float32)), torch.from_numpy(Y[tr])
    Xv, Yv = torch.from_numpy(X[~tr].astype(np.float32)), Y[~tr]
    torch.manual_seed(0)
    net = DangerNet(hidden)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    pw = float((1 - Yt.mean()) / max(float(Yt.mean()), 1e-3)) ** 0.5
    lossf = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pw))
    for ep in range(epochs):
        perm = torch.randperm(len(Yt))
        for k in range(0, len(perm), 512):
            b = perm[k:k + 512]
            loss = lossf(net(Xt[b]), Yt[b])
            opt.zero_grad(); loss.backward(); opt.step()
        with torch.no_grad():
            pv = torch.sigmoid(net(Xv)).numpy()
        print(f"época {ep + 1:2d}: AUC en niveles 3–4 {auc(Yv > 0.5, pv):.3f}")
    yb = Yv > 0.5
    print(f"\nEn niveles no vistos (3, 4), muerte = p > 0,5 ({yb.sum()} de {len(yb)} casos):")
    for name, pred in (("reglas a mano", RU[~tr] > 0.5), ("red aprendida", pv > 0.5)):
        pr, rc, f1 = prf(yb, pred)
        print(f"{name:>15}: precisión {100 * pr:5.1f}% | exhaustividad {100 * rc:5.1f}% | F1 {f1:.3f}")
    torch.save({"model": net.state_dict(), "hidden": hidden, "n_in": N_IN, "levels": TRAIN_LEVELS}, MODEL)
    print("guardado en", MODEL)


# ------------------------------------------------------------------ juego
_M = None


def _play(job):
    global _M
    kind, P, level, seeds = job
    if kind == "learned" and _M is None:
        torch.set_num_threads(1)
        _M = DangerModel(MODEL)
    pol = (lambda st, br: gv_act_learned(st, P, _M)) if kind == "learned" else (lambda st, br: gv_act(st, P))
    b = GvgaiBridge()
    try:
        return level, [b.play(level, s, pol) for s in seeds]
    finally:
        b.close()


def play_many(pool, kind, P, levels, seeds):
    res = list(pool.map(_play, [(kind, P, lv, list(seeds)) for lv in levels]))
    return {lv: rs for lv, rs in res}


def summary(label, res):
    allr = [r for rs in res.values() for r in rs]
    per = " ".join(f"n{lv}:{sum(r[0] for r in rs)}/{len(rs)}" for lv, rs in sorted(res.items()))
    unseen = [r for lv, rs in res.items() if lv in TEST_LEVELS for r in rs]
    print(f"{label:>24}: victorias {100 * sum(r[0] for r in allr) / len(allr):5.1f}% ({per}) | "
          f"no vistos (3–4) {100 * sum(r[0] for r in unseen) / max(len(unseen), 1):5.1f}% | "
          f"ticks medios {sum(r[2] for r in allr) / len(allr):4.0f}", flush=True)


def tune(procs, gens=8, pop=10, seeds_per=4):
    names = list(GV_LEARNED_PARAMS)
    lo = np.array([GV_LEARNED_PARAMS[k][0] for k in names]); hi = np.array([GV_LEARNED_PARAMS[k][1] for k in names])
    dec = lambda u: {k: float(v) for k, v in zip(names, lo + np.clip(u, 0, 1) * (hi - lo))}
    mu = (np.array([GV_LEARNED_DEFAULT[k] for k in names]) - lo) / (hi - lo)
    sigma = np.full(len(names), 0.25)
    rng = np.random.default_rng(0)
    with ProcessPoolExecutor(procs) as pool:
        for gen in range(gens):
            U = np.clip(mu + sigma * rng.standard_normal((pop, len(names))), 0, 1); U[0] = mu
            seeds = range(500 + gen * 10, 500 + gen * 10 + seeds_per)
            scores = []
            for u in U:
                res = play_many(pool, "learned", dec(u), TRAIN_LEVELS, seeds)
                rs = [r for v in res.values() for r in v]
                scores.append(100 * np.mean([r[0] for r in rs]) - np.mean([r[2] for r in rs]) / 100)
            scores = np.array(scores); order = np.argsort(-scores)
            el = U[order[:3]]; mu = el.mean(0); sigma = np.maximum(0.7 * sigma + 0.3 * el.std(0), 0.03)
            print(f"gen {gen + 1}: mejor {scores[order[0]]:6.1f} | centro {scores[0]:6.1f} | "
                  + " ".join(f"{k}={v:.2f}" for k, v in dec(mu).items()), flush=True)
            TUNED.write_text(json.dumps(dec(mu), indent=1))


def evaluate(procs, n):
    seeds = range(100, 100 + n)
    with ProcessPoolExecutor(procs) as pool:
        summary("A* reglas a mano", play_many(pool, "hand", GV_DEFAULT, range(5), seeds))
        summary("A* predictor, sin CEM", play_many(pool, "learned", GV_LEARNED_DEFAULT, range(5), seeds))
        if TUNED.exists():
            summary("A* predictor + CEM", play_many(pool, "learned", json.loads(TUNED.read_text()), range(5), seeds))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["collect", "train", "tune", "eval"])
    p.add_argument("--samples", type=int, default=40_000)
    p.add_argument("--procs", type=int, default=4)
    p.add_argument("--seeds", type=int, default=20)
    a = p.parse_args()
    {"collect": lambda: collect(a.samples, a.procs), "train": train,
     "tune": lambda: tune(a.procs), "eval": lambda: evaluate(a.procs, a.seeds)}[a.cmd]()


if __name__ == "__main__":
    main()
