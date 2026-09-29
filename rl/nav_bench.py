"""Banco de navegación: órdenes al azar "ve a X" y cuántas se cumplen sin morir.

    python nav_bench.py boulderdash --orders 300           # compara sin peligro / con predictor
    python nav_bench.py boulderdash --tune                  # grilla de w_risk y p_max en niveles de entrenamiento
Cada orden: destino al azar entre 5 y 25 pasos (la mitad sobre algo que no es fondo: diamantes, llaves...,
la otra mitad cualquier casilla transitable). Termina en: llegó / murió / inalcanzable / tiempo agotado
(3 × distancia más corta + 20 ticks). Al terminar una orden llega la siguiente; la partida sigue hasta morir,
ganar o 2000 ticks. Usa lo aprendido por generic_train.py (transitabilidad y predictor de muerte).
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from boulder.generic import GDanger, GenericBridge, Knowledge
from boulder.gvgai_levels import write_levels
from boulder.nav import NAV_DEFAULT, NAV_PARAMS, Navigator, shortest

RUNS = Path(__file__).parent / "runs" / "generic"


class OrderGiver:
    """Hace de agente de alto nivel: da órdenes al azar y lleva la cuenta de cómo terminan."""

    def __init__(self, nav, rng, stats):
        self.nav, self.rng, self.stats = nav, rng, stats
        self.goal = None

    def _new_order(self, st):
        K = self.nav.know
        W, N = st.W, len(st.masks)
        blocked = [any(m >> t & 1 and K.is_blocking(t) for t in range(63)) for m in st.masks]
        interesting = [j for j in range(N) if not blocked[j] and j != st.pos
                       and any(st.masks[j] >> t & 1 for t in range(63) if t not in K.floor and t not in K.avatar_types)]
        free = [j for j in range(N) if not blocked[j] and j != st.pos]
        pool = interesting if (interesting and self.rng.random() < 0.5) else free
        for _ in range(40):
            j = int(self.rng.choice(pool))
            d = shortest(st, K, j)
            if d is not None and 5 <= d <= 25:
                self.goal, self.dist, self.t0 = j, d, st.tick
                self.stats["orders"] += 1
                return
        self.goal = None

    def _finish(self, how, st=None):
        self.stats[how] += 1
        if how == "reached":
            self.stats["stretch"].append((st.tick - self.t0) / max(self.dist, 1))
        self.goal = None

    def __call__(self, st, br):
        if self.goal is not None:
            if st.pos == self.goal:
                self._finish("reached", st)
            elif st.tick - self.t0 > 3 * self.dist + 20:
                self._finish("timeout")
        if self.goal is None:
            self._new_order(st)
            if self.goal is None:
                return 4
        act, ok = self.nav.step(st, self.goal)
        if not ok:
            self.stats["unreachable"] += 1
            self.goal = None
        return act

    def end(self, won):
        if self.goal is not None:
            self._finish("died" if won != 1 else "reached_win")
        self.nav.last = None


_D = {}


def run(job):
    game, P, levels, seeds, use_danger, n_orders = job
    torch.set_num_threads(1)
    d = RUNS / game
    if use_danger and game not in _D:
        _D[game] = GDanger(d / "danger.pt")
    K = Knowledge.from_json(json.loads((d / "knowledge.json").read_text()))
    stats = {"orders": 0, "reached": 0, "died": 0, "timeout": 0, "unreachable": 0, "reached_win": 0, "stretch": []}
    b = GenericBridge(game)
    rng = np.random.default_rng(seeds[0])
    try:
        k = 0
        while stats["orders"] < n_orders:
            nav = Navigator(K, _D.get(game) if use_danger else None, P)
            b.play(levels[k % len(levels)], seeds[k % len(seeds)] + 1000 * k, OrderGiver(nav, rng, stats))
            k += 1
    finally:
        b.close()
    return stats


def merge(parts):
    out = {k: 0 for k in ("orders", "reached", "died", "timeout", "unreachable", "reached_win")}
    out["stretch"] = []
    for p in parts:
        for k in out:
            out[k] = out[k] + p[k]
    return out


def report(label, s):
    n = max(s["orders"], 1)
    reached = s["reached"] + s["reached_win"]
    print(f"{label:>26}: órdenes {s['orders']:4d} | llegó {100 * reached / n:5.1f}% | murió {100 * s['died'] / n:5.1f}% | "
          f"tiempo {100 * s['timeout'] / n:5.1f}% | inalcanzable {100 * s['unreachable'] / n:4.1f}% | "
          f"ruta / más corta {np.median(s['stretch']) if s['stretch'] else float('nan'):.2f}", flush=True)


def test_levels(game):
    return list(range(5))                    # los niveles oficiales


def train_levels(game):
    if game == "boulderdash":
        return [str(p) for p in write_levels(300, Path(__file__).parent / "runs" / "gvgai_levels", 0)]
    return [0, 1, 2]


def bench(game, P, orders, procs, use_danger, levels, seed0=500):
    per = max(orders // procs, 1)
    with ProcessPoolExecutor(procs) as ex:
        parts = list(ex.map(run, [(game, P, levels[k::procs] or levels, [seed0 + k], use_danger, per)
                                  for k in range(procs)]))
    return merge(parts)


def nav_score(s):
    n = max(s["orders"], 1)
    return (s["reached"] + s["reached_win"]) / n - 3 * s["died"] / n


def tune(game, procs, orders=100):
    """Búsqueda en grilla de w_risk y p_max en niveles de entrenamiento (son solo 2 parámetros)."""
    lv = train_levels(game)
    rng = np.random.default_rng(0)
    levels = list(rng.choice(lv, min(len(lv), 12), replace=False))
    best = (-1e9, None)
    for w in (5.0, 10.0, 20.0, 40.0):
        for pmax in (0.5, 0.8, 1.0):
            P = {"w_risk": w, "p_max": pmax}
            s = bench(game, P, orders, procs, True, levels, seed0=700)
            sc = nav_score(s)
            report(f"w_risk={w:g} p_max={pmax:g} (entren.)", s)
            if sc > best[0]:
                best = (sc, P)
    (RUNS / game / "nav.json").write_text(json.dumps(best[1], indent=1))
    print(f"{game}: mejor en entrenamiento {best[1]} (llegar − 3·morir = {best[0]:.3f})", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("game")
    p.add_argument("--orders", type=int, default=300)
    p.add_argument("--procs", type=int, default=4)
    p.add_argument("--tune", action="store_true")
    a = p.parse_args()
    if a.tune:
        return tune(a.game, a.procs)
    lv = test_levels(a.game)
    report(f"{a.game} sin peligro", bench(a.game, {**NAV_DEFAULT, "w_risk": 0.0}, a.orders, a.procs, False, lv))
    report(f"{a.game} predictor (a mano)", bench(a.game, NAV_DEFAULT, a.orders, a.procs, True, lv))
    f = RUNS / a.game / "nav.json"
    if f.exists():
        report(f"{a.game} predictor + CEM", bench(a.game, json.loads(f.read_text()), a.orders, a.procs, True, lv))


if __name__ == "__main__":
    main()
