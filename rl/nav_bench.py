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
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from boulder.generic import GDanger, GenericBridge, Knowledge
from boulder.gvgai_levels import write_levels
from boulder.cube import CellRisk, CubeNavigator
from boulder.objcube import ObjectCubeNavigator
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
        self.stats.setdefault("by_row", {}).setdefault(f"{self.goal // self.W}:{how}", 0)
        self.stats["by_row"][f"{self.goal // self.W}:{how}"] += 1
        if how == "reached":
            self.stats["stretch"].append((st.tick - self.t0) / max(self.dist, 1))
        self.goal = None

    def __call__(self, st, br):
        return self._decide(st, br)

    def _decide(self, st, br):
        self.W = st.W
        if self.goal is not None:
            if st.pos == self.goal:
                self._finish("reached", st)
            elif st.tick - self.t0 > 3 * self.dist + 20:
                self._finish("timeout")
        if self.goal is None:
            self._new_order(st)
            if self.goal is None:
                return 4
        t0 = time.perf_counter()                          # solo el navegador, no la generación de órdenes
        act, ok = self.nav.step(st, self.goal, br)
        self.stats.setdefault("ms", []).append(1000 * (time.perf_counter() - t0))
        if not ok:
            self.stats["unreachable"] += 1
            self.goal = None
        return act

    def end(self, won):
        if self.goal is not None and hasattr(self, "W"):
            self._finish("died" if won != 1 else "reached_win")
        self.nav.last = None


_D = {}


def run(job):
    game, P, levels, seeds, use_danger, n_orders = job
    cube = use_danger in ("cube", "hybrid", "objects", "objects+pred")
    torch.set_num_threads(1)
    d = RUNS / game
    if use_danger and use_danger not in ("cube", "objects") and game not in _D:
        _D[game] = GDanger(d / "danger.pt")
    K = Knowledge.from_json(json.loads((d / "knowledge.json").read_text()))
    stats = {"orders": 0, "reached": 0, "died": 0, "timeout": 0, "unreachable": 0, "reached_win": 0, "stretch": []}
    b = GenericBridge(game)
    rng = np.random.default_rng(seeds[0])
    try:
        k = 0
        while stats["orders"] < n_orders:
            if use_danger in ("objects", "objects+pred"):
                nav = ObjectCubeNavigator(K, CellRisk(d / "cell_risk.pt"), P,
                                          danger=_D.get(game) if use_danger == "objects+pred" else None)
            elif cube:
                nav = CubeNavigator(K, CellRisk(d / "cell_risk.pt"), P,
                                    danger=_D.get(game) if use_danger == "hybrid" else None)
            else:
                nav = Navigator(K, _D.get(game) if use_danger else None, P)
            b.play(levels[k % len(levels)], seeds[k % len(seeds)] + 1000 * k, OrderGiver(nav, rng, stats))
            k += 1
    finally:
        b.close()
    return stats


def merge(parts):
    out = {k: 0 for k in ("orders", "reached", "died", "timeout", "unreachable", "reached_win")}
    out["stretch"] = []
    out["by_row"] = {}
    out["ms"] = []
    for p in parts:
        for k in out:
            if k == "ms":
                out["ms"] += p.get("ms", [])
            elif k == "by_row":
                for kk, v in p.get("by_row", {}).items():
                    out["by_row"][kk] = out["by_row"].get(kk, 0) + v
            else:
                out[k] = out[k] + p[k]
    return out


def report(label, s):
    n = max(s["orders"], 1)
    reached = s["reached"] + s["reached_win"]
    print(f"{label:>26}: órdenes {s['orders']:4d} | llegó {100 * reached / n:5.1f}% | murió {100 * s['died'] / n:5.1f}% | "
          f"tiempo {100 * s['timeout'] / n:5.1f}% | inalcanzable {100 * s['unreachable'] / n:4.1f}% | "
          f"ruta / más corta {np.median(s['stretch']) if s['stretch'] else float('nan'):.2f}", flush=True)
    if s.get("by_row") and label.endswith("(filas)"):
        rows = sorted({int(k.split(':')[0]) for k in s["by_row"]})
        for r in rows:
            cnt = {k.split(':')[1]: v for k, v in s["by_row"].items() if int(k.split(':')[0]) == r}
            print(f"      fila {r:2d}: {cnt}", flush=True)


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


def tune_objects(game, procs, orders=100):
    """Grilla de w_risk para "objetos + predictor" (escenario sin modelo) en niveles de entrenamiento."""
    lv = train_levels(game)
    rng = np.random.default_rng(0)
    levels = [x.item() if hasattr(x, "item") else x for x in rng.choice(lv, min(len(lv), 12), replace=False)]
    best = (-1e9, None)
    for w in (1.0, 3.0, 6.0, 12.0, 20.0):
        P = {**NAV_DEFAULT, "w_risk": w}
        s = bench(game, P, orders, procs, "objects+pred", levels, seed0=700)
        report(f"w_risk={w:g} (entren.)", s)
        if nav_score(s) > best[0]:
            best = (nav_score(s), P)
    (RUNS / game / "nav_objects.json").write_text(json.dumps(best[1], indent=1))
    print(f"{game}: mejor en entrenamiento {best[1]} (llegar − 3·morir = {best[0]:.3f})", flush=True)


def tune(game, procs, orders=100):
    """Búsqueda en grilla de w_risk y p_max en niveles de entrenamiento (son solo 2 parámetros)."""
    lv = train_levels(game)
    rng = np.random.default_rng(0)
    levels = [x.item() if hasattr(x, "item") else x for x in rng.choice(lv, min(len(lv), 12), replace=False)]
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
    p.add_argument("--only-cube", action="store_true")
    p.add_argument("--only-hybrid", action="store_true")
    p.add_argument("--timing", action="store_true", help="tiempo por decisión de cada navegador")
    p.add_argument("--no-model", action="store_true", help="escenario B: sin modelo del juego en ejecución")
    p.add_argument("--tune-objects", action="store_true", help="grilla de w_risk para objetos + predictor")
    a = p.parse_args()
    if a.tune_objects:
        return tune_objects(a.game, a.procs)
    if a.no_model:
        lv = test_levels(a.game)
        variants = [("sin peligro", {**NAV_DEFAULT, "w_risk": 0.0}, False), ("predictor", NAV_DEFAULT, True),
                    ("objetos", NAV_DEFAULT, "objects"), ("objetos + predictor", NAV_DEFAULT, "objects+pred")]
        f = RUNS / a.game / "nav_objects.json"
        if f.exists():
            variants.append(("objetos + predictor ajust.", json.loads(f.read_text()), "objects+pred"))
        for label, P, kind in variants:
            s = bench(a.game, P, a.orders, a.procs, kind, lv)
            report(f"{a.game} {label}", s)
            ms = np.array(s["ms"])
            print(f"{'':>26}  tiempo media {ms.mean():5.1f} ms | p95 {np.percentile(ms, 95):5.1f} | sobre 40 ms {100 * (ms > 40).mean():4.1f}%",
                  flush=True)
        return
    if a.timing:
        lv = test_levels(a.game)
        for label, P, kind in (("sin peligro", {**NAV_DEFAULT, "w_risk": 0.0}, False), ("predictor", NAV_DEFAULT, True),
                               ("predictor + escudo", {**NAV_DEFAULT, "shield": 0.25}, True),
                               ("cubo + escudo", {**NAV_DEFAULT, "shield": 0.25}, "cube")):
            s = bench(a.game, P, a.orders, a.procs, kind, lv)
            ms = np.array(s["ms"])
            print(f"{a.game:>11} {label:>20}: {len(ms):6d} decisiones | media {ms.mean():6.1f} ms | p50 {np.median(ms):6.1f} | "
                  f"p95 {np.percentile(ms, 95):6.1f} | máx {ms.max():7.1f} | sobre 40 ms {100 * (ms > 40).mean():5.1f}%", flush=True)
        return
    if a.only_hybrid:
        return report(f"{a.game} híbrido + escudo (filas)", bench(a.game, {**NAV_DEFAULT, "shield": 0.25}, a.orders,
                                                                  a.procs, "hybrid", test_levels(a.game)))
    if a.only_cube:
        return report(f"{a.game} cubo + escudo (filas)", bench(a.game, {**NAV_DEFAULT, "shield": 0.25}, a.orders, a.procs,
                                                        "cube", test_levels(a.game)))
    if a.tune:
        return tune(a.game, a.procs)
    lv = test_levels(a.game)
    report(f"{a.game} sin peligro", bench(a.game, {**NAV_DEFAULT, "w_risk": 0.0}, a.orders, a.procs, False, lv))
    report(f"{a.game} solo escudo", bench(a.game, {**NAV_DEFAULT, "w_risk": 0.0, "shield": 0.25}, a.orders, a.procs, False, lv))
    report(f"{a.game} predictor (a mano)", bench(a.game, NAV_DEFAULT, a.orders, a.procs, True, lv))
    report(f"{a.game} predictor + escudo", bench(a.game, {**NAV_DEFAULT, "shield": 0.25}, a.orders, a.procs, True, lv))
    report(f"{a.game} cubo + escudo", bench(a.game, {**NAV_DEFAULT, "shield": 0.25}, a.orders, a.procs, "cube", lv))
    f = RUNS / a.game / "nav.json"
    if f.exists():
        report(f"{a.game} predictor + CEM", bench(a.game, json.loads(f.read_text()), a.orders, a.procs, True, lv))


if __name__ == "__main__":
    main()
