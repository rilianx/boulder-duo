"""Genera datos contrafactuales del simulador y entrena el predictor de muerte (boulder/danger.py).

    python train_danger.py --samples 150000          # → runs/danger.pt y un informe de precisión

Política de comportamiento: el A* con peligro reducido (arriesga más) y 20 % de pasos al azar, para
visitar muchas situaciones riesgosas. Por cada tick y cada dirección transitable se etiqueta "¿muere si
entra ahí y se queda quieto 3 ticks?". Se compara contra la regla escrita a mano en los mismos ejemplos.
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import random
import time
from pathlib import Path

import numpy as np
import torch

from boulder.astar import hazard_map
from boulder.danger import N_IN, DangerNet, features, label, planes
from boulder.env import BoulderEnv
from boulder.policy import DEFAULT, act
from boulder.sim import DIRT, E, GEM, OFF, ROCK, W

RISKY = {**DEFAULT, "h_fall": 5.0, "h_down": 5.0, "h_e1": 5.0, "h_e2": 3.0}


def collect(job):
    n_target, seed = job
    rnd = random.Random(seed)
    env = BoulderEnv(seed=seed)
    env.tok.encode = lambda sim: (None, None)
    env.reset()
    X, Y, RULE, LV = [], [], [], []
    n = 0
    while n < n_target:
        s = env.sim
        a = s.agent
        if a.alive:
            i = a.y * W + a.x
            cand = [d for d in range(4) if s.grid[i + OFF[d]] in (E, DIRT, GEM)]
            if cand:
                pl = planes(s)
                hz = hazard_map(s)
                above = s.grid[i - W] in (ROCK, GEM)
                cells = [i + OFF[d] for d in cand]
                X.append(features(pl, cells, cand).astype(np.uint8))
                for d, j in zip(cand, cells):
                    Y.append(label(s, d))
                    RULE.append(int(hz[j] or (d == 2 and above)))
                    LV.append(s.level)
                n += len(cand)
        action = rnd.randrange(5) if rnd.random() < 0.2 else act(s, RISKY)
        env.step(action)
    return np.concatenate(X), np.array(Y, np.float32), np.array(RULE, np.float32), np.array(LV)


def auc(y, p):
    order = np.argsort(p)
    r = np.empty(len(p)); r[order] = np.arange(1, len(p) + 1)
    pos = y == 1
    return (r[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * (~pos).sum())


def report(name, y, p, thr=0.5):
    pred = p >= thr
    tp = (pred & (y == 1)).sum(); fp = (pred & (y == 0)).sum(); fn = (~pred & (y == 1)).sum()
    prec = tp / max(tp + fp, 1); rec = tp / max(tp + fn, 1)
    a = auc(y, p) if len(set(p.tolist())) > 2 else float("nan")
    print(f"{name:>18}: precisión {100 * prec:5.1f}% | exhaustividad {100 * rec:5.1f}% | "
          f"F1 {2 * prec * rec / max(prec + rec, 1e-9):.3f}" + (f" | AUC {a:.3f}" if a == a else ""))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=int, default=150_000)
    p.add_argument("--procs", type=int, default=4)
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--hidden", type=int, default=128)
    a = p.parse_args()
    t0 = time.time()
    per = a.samples // a.procs
    with mp.get_context("spawn").Pool(a.procs) as pool:
        parts = pool.map(collect, [(per, 500 + k) for k in range(a.procs)])
    X = np.concatenate([q[0] for q in parts]); Y = np.concatenate([q[1] for q in parts])
    RULE = np.concatenate([q[2] for q in parts]); LV = np.concatenate([q[3] for q in parts])
    print(f"{len(Y):,} ejemplos en {time.time() - t0:.0f} s | {100 * Y.mean():.1f}% mueren")
    # validación por nivel: niveles 3, 7 y 11 nunca se ven al entrenar
    val = np.isin(LV, [3, 7, 11])
    Xt, Yt = torch.from_numpy(X[~val].astype(np.float32)), torch.from_numpy(Y[~val])
    Xv, Yv = torch.from_numpy(X[val].astype(np.float32)), Y[val]
    torch.manual_seed(0)
    net = DangerNet(a.hidden)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    pw = torch.tensor((1 - Yt.mean()) / Yt.mean().clamp_min(1e-3))
    lossf = torch.nn.BCEWithLogitsLoss(pos_weight=pw ** 0.5)
    for ep in range(a.epochs):
        perm = torch.randperm(len(Yt))
        for k in range(0, len(perm), 1024):
            b = perm[k:k + 1024]
            loss = lossf(net(Xt[b]), Yt[b])
            opt.zero_grad(); loss.backward(); opt.step()
        with torch.no_grad():
            pv = torch.sigmoid(net(Xv)).numpy()
        print(f"época {ep + 1}: pérdida {loss.item():.4f} | AUC validación {auc(Yv, pv):.3f}")
    print("\nEn niveles no vistos (3, 7, 11):")
    report("regla a mano", Yv, RULE[val])
    report("red aprendida", Yv, pv)
    out = Path(__file__).parent / "runs" / "danger.pt"
    out.parent.mkdir(exist_ok=True)
    torch.save({"model": net.state_dict(), "hidden": a.hidden, "n_in": N_IN}, out)
    print("guardado en", out)


if __name__ == "__main__":
    main()
