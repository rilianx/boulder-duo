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
from boulder.nav import NAV_DEFAULT, NAV_PARAMS, MCTSNavigator, Navigator, shortest

RUNS = Path(__file__).parent / "runs" / "generic"


class OrderGiver:
    """Hace de agente de alto nivel: da órdenes al azar y lleva la cuenta de cómo terminan."""

    T_mult, T_add = 3, 20            # plazo de cada orden: T_mult · distancia + T_add ticks

    def __init__(self, nav, rng, stats, T=None):
        self.nav, self.rng, self.stats = nav, rng, stats
        self.goal = None
        if T is not None:
            self.T_mult, self.T_add = T

    def _new_order(self, st):
        K = self.nav.know
        W, N = st.W, len(st.masks)
        blocked = K.blocked_cells(st)
        interesting = [j for j in range(N) if not blocked[j] and j != st.pos
                       and any(st.masks[j] >> t & 1 for t in range(63) if t not in K.floor and t not in K.avatar_types)]
        free = [j for j in range(N) if not blocked[j] and j != st.pos]
        pool = interesting if (interesting and self.rng.random() < 0.5) else free
        for _ in range(40):
            j = int(self.rng.choice(pool))
            d = shortest(st, K, j)
            if d is not None and 5 <= d <= 25:
                self.goal, self.dist, self.t0 = j, d, st.tick
                self.limit = self.T_mult * d + self.T_add
                self.nav.deadline = st.tick + self.limit      # el navegador puede usar el plazo (P["deadline"])
                self.stats["orders"] += 1
                return
        self.goal = None

    def _finish(self, how, st=None):
        self.stats[how] = self.stats.get(how, 0) + 1
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
            elif self.nav.know.blocked_cells(st)[self.goal]:
                self._finish("invalid")                  # el mundo tapó el destino (p. ej. cayó una roca)
            elif st.tick - self.t0 > getattr(self, "limit", 3 * self.dist + 20):
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
    game, P, levels, seeds, use_danger, n_orders = job[:6]
    T = job[6] if len(job) > 6 else None
    cube = use_danger in ("cube", "hybrid", "objects", "objects+pred")
    torch.set_num_threads(1)
    d = RUNS / game
    if use_danger and use_danger not in ("cube", "objects") and game not in _D:
        _D[game] = GDanger(d / "danger.pt")
    K = Knowledge.from_json(json.loads((d / "knowledge.json").read_text()))
    stats = {"orders": 0, "reached": 0, "died": 0, "timeout": 0, "unreachable": 0, "reached_win": 0, "invalid": 0,
             "stretch": []}
    b = GenericBridge(game)
    rng = np.random.default_rng(seeds[0])
    try:
        k = 0
        while stats["orders"] < n_orders:
            if use_danger == "mcts":
                nav = MCTSNavigator(K, P)
            elif use_danger in ("objects", "objects+pred"):
                nav = ObjectCubeNavigator(K, CellRisk(d / "cell_risk.pt"), P,
                                          danger=_D.get(game) if use_danger == "objects+pred" else None)
            elif cube:
                nav = CubeNavigator(K, CellRisk(d / "cell_risk.pt"), P,
                                    danger=_D.get(game) if use_danger == "hybrid" else None)
            else:
                nav = Navigator(K, _D.get(game) if use_danger else None, P)
            b.play(levels[k % len(levels)], seeds[k % len(seeds)] + 1000 * k, OrderGiver(nav, rng, stats, T))
            jt = stats.setdefault("java_t", [0, 0, 0.0, 0.0])   # decisiones, >40 ms, máx, suma (ms), desde Java
            n, over, mx, tot = getattr(b, "timing", (0, 0, 0.0, 0.0))
            jt[0] += n; jt[1] += over; jt[2] = max(jt[2], mx); jt[3] += tot
            k += 1
    finally:
        b.close()
    stats["know"] = K.to_json()                  # lo aprendido al vuelo (transitabilidad, giros)
    return stats


def merge(parts):
    out = {k: 0 for k in ("orders", "reached", "died", "timeout", "unreachable", "reached_win", "invalid")}
    out["stretch"] = []
    out["by_row"] = {}
    out["ms"] = []
    out["java_t"] = [0, 0, 0.0, 0.0]
    for p in parts:
        for k in out:
            if k == "java_t":
                jt = p.get("java_t", [0, 0, 0.0, 0.0])
                out[k] = [out[k][0] + jt[0], out[k][1] + jt[1], max(out[k][2], jt[2]), out[k][3] + jt[3]]
            elif k == "ms":
                out["ms"] += p.get("ms", [])
            elif k == "by_row":
                for kk, v in p.get("by_row", {}).items():
                    out["by_row"][kk] = out["by_row"].get(kk, 0) + v
            else:
                out[k] = out[k] + p.get(k, 0)
    return out


def learn_knowledge(game, procs, orders=200):
    """Actualiza knowledge.json jugando órdenes en niveles de entrenamiento: transitabilidad según recursos y
    si el avatar gira antes de moverse. No usa nada del resultado de la evaluación."""
    lv = train_levels(game)
    P = {**json.loads((RUNS / game / "nav_objects.json").read_text()), "patience": 10}
    per = max(orders // procs, 1)
    with ProcessPoolExecutor(procs) as ex:
        parts = list(ex.map(run, [(game, P, lv[k::procs][:30] or lv, [300 + k], "objects+pred", per) for k in range(procs)]))
    f = RUNS / game / "knowledge.json"
    base = Knowledge.from_json(json.loads(f.read_text()))
    K0 = Knowledge.from_json(json.loads(f.read_text()))
    for p in parts:                                  # cada parte = base + lo nuevo: sumar solo lo nuevo
        k = Knowledge.from_json(p["know"])
        k.by_res = {t: {n: v for n, v in d.items()} for t, d in k.by_res.items()}
        for t, d in k.by_res.items():
            for n, v in d.items():
                old = K0.by_res.get(t, {}).get(n, [0, 0])
                m = base.by_res.setdefault(t, {}).setdefault(n, [0, 0])
                m[0] += v[0] - old[0]; m[1] += v[1] - old[1]
        base.turns = [base.turns[0] + k.turns[0] - K0.turns[0], base.turns[1] + k.turns[1] - K0.turns[1]]
        for t, v in k.carry.items():
            old = K0.carry.get(t, [0, 0])
            m = base.carry.setdefault(t, [0, 0])
            m[0] += v[0] - old[0]; m[1] += v[1] - old[1]
    f.write_text(json.dumps(base.to_json()))
    print(f"{game}: giro cuesta un tick = {base.turn_cost} "
          f"(giros {base.turns}); transitabilidad por recursos:", flush=True)
    print(f"   arrastran: {sorted(base.carriers())} ({base.carry})", flush=True)
    for t, d in base.by_res.items():
        print(f"   tipo {t}: " + ", ".join(f"{n}:{v}" for n, v in sorted(d.items())), flush=True)


def seeds_report(game, variants, orders, procs, lv, n):
    """Cada variante con n semillas distintas: media e IC 95 % (t de Student) de llegar / morir / tiempo agotado."""
    T975 = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 8: 2.365, 10: 2.262}   # t_{0,975} con n − 1 g.l.
    out = {}
    for label, P, kind in variants:
        rows = []
        for k in range(n):
            s = bench(game, P, orders, procs, kind, lv, seed0=500 + 100 * k)
            m = max(s["orders"], 1)
            rows.append([(s["reached"] + s["reached_win"]) / m, s["died"] / m, s["timeout"] / m, s.get("invalid", 0) / m])
            report(f"{game} {label} semilla {k}", s)
        r = np.array(rows) * 100
        h = T975.get(n, 2.0) * r.std(0, ddof=1) / np.sqrt(n) if n > 1 else np.zeros(4)
        out[label] = {"media": r.mean(0).round(1).tolist(), "ic95": h.round(1).tolist(), "n": n}
        print(f"{game} {label}: llega {r[:, 0].mean():.1f} ± {h[0]:.1f} | muere {r[:, 1].mean():.1f} ± {h[1]:.1f} | "
              f"tiempo {r[:, 2].mean():.1f} ± {h[2]:.1f} | invalidada {r[:, 3].mean():.1f} ± {h[3]:.1f}  (n = {n})", flush=True)
    (RUNS / game / "nav_seeds.json").write_text(json.dumps(out, indent=1))


def curve(game, procs, orders=150):
    """Curva llegar vs. morir en los niveles oficiales: el navegador de siempre barriendo w_risk, y el navegador
    con plazo (minimiza el riesgo sujeto a llegar antes de T), para plazos T = m·d + a distintos."""
    f = RUNS / game / "nav_objects.json"
    alpha = json.loads(f.read_text()).get("alpha", 1.0) if f.exists() else 1.0
    lv = test_levels(game)
    out = RUNS / game / "nav_curve.json"
    res = json.loads(out.read_text()) if out.exists() else []
    done = {(r["kind"], r["w"], tuple(r["T"])) for r in res}
    jobs = [("w", w, (3, 20)) for w in (0, 3, 6, 12, 20, 30, 50)]
    jobs += [("w", w, T) for T in ((1.5, 10), (5, 30)) for w in (6, 20)]
    jobs += [("plazo", 50, T) for T in ((1.5, 10), (3, 20), (5, 30))]
    for kind, w, T in jobs:
        if (kind, w, tuple(T)) in done:
            continue
        P = {**NAV_DEFAULT, "w_risk": float(w), "alpha": alpha, "patience": 0, "deadline": kind == "plazo"}
        s = bench(game, P, orders, procs, "objects+pred", lv, T=T)
        m = max(s["orders"], 1)
        r = {"kind": kind, "w": w, "T": list(T), "orders": s["orders"],
             "reached": 100 * (s["reached"] + s["reached_win"]) / m, "died": 100 * s["died"] / m,
             "timeout": 100 * s["timeout"] / m, "invalid": 100 * s.get("invalid", 0) / m,
             "unreachable": 100 * s["unreachable"] / m}
        res.append(r)
        out.write_text(json.dumps(res, indent=1))
        print(f"{game} {kind:5} w={w:>2} T={T[0]}·d+{T[1]}: llega {r['reached']:5.1f} | muere {r['died']:5.1f} | "
              f"tiempo {r['timeout']:5.1f} | invalidada {r['invalid']:4.1f} | inalcanzable {r['unreachable']:4.1f}", flush=True)


def report(label, s):
    n = max(s["orders"], 1)
    reached = s["reached"] + s["reached_win"]
    print(f"{label:>26}: órdenes {s['orders']:4d} | llegó {100 * reached / n:5.1f}% | murió {100 * s['died'] / n:5.1f}% | "
          f"tiempo {100 * s['timeout'] / n:5.1f}% | inalcanzable {100 * s['unreachable'] / n:4.1f}% | "
          f"invalidada {100 * s.get('invalid', 0) / n:4.1f}% | "
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
        # versión 2 del generador: más cerca de los oficiales (rocas sobre diamantes, 24 diamantes, 2+2 enemigos)
        return [str(p) for p in write_levels(300, Path(__file__).parent / "runs" / "gvgai_levels_v2", 0, "boulderdash_v2")]
    # Zelda y Frogs: niveles generados (antes solo los oficiales 0–2, y el ajuste sobreajustaba)
    return [str(p) for p in write_levels(200, Path(__file__).parent / "runs" / f"gvgai_levels_{game}", 0, game)]


def bench(game, P, orders, procs, use_danger, levels, seed0=500, T=None):
    per = max(orders // procs, 1)
    with ProcessPoolExecutor(procs) as ex:
        parts = list(ex.map(run, [(game, P, levels[k::procs] or levels, [seed0 + k], use_danger, per, T)
                                  for k in range(procs)]))
    return merge(parts)


def nav_score(s):
    n = max(s["orders"], 1)
    # una muerte cuesta 2 órdenes cumplidas y un tiempo agotado media
    return (s["reached"] + s["reached_win"]) / n - 2 * s["died"] / n - 0.5 * s["timeout"] / n


def tune_objects(game, procs, orders=160):
    """Grilla de w_risk para "objetos + predictor" (escenario sin modelo) en niveles de entrenamiento."""
    lv = train_levels(game)
    rng = np.random.default_rng(0)
    levels = [x.item() if hasattr(x, "item") else x for x in rng.choice(lv, min(len(lv), 12), replace=False)]
    best = (-1e9, None)
    for w in (12.0, 20.0, 30.0):
        for alpha in (0.0, 1.0):
            for pat in (0, 10):
                P = {**NAV_DEFAULT, "w_risk": w, "alpha": alpha, "patience": pat}
                s = bench(game, P, orders, procs, "objects+pred", levels, seed0=700)
                report(f"w_risk={w:g} alpha={alpha:g} paciencia={pat} (entren.)", s)
                if nav_score(s) > best[0]:
                    best = (nav_score(s), P)
    (RUNS / game / "nav_objects.json").write_text(json.dumps(best[1], indent=1))
    print(f"{game}: mejor en entrenamiento {best[1]} (llegar − 2·morir − 0,5·tiempo = {best[0]:.3f})", flush=True)


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
    print(f"{game}: mejor en entrenamiento {best[1]} (llegar − 2·morir − 0,5·tiempo = {best[0]:.3f})", flush=True)


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
    p.add_argument("--tune-objects", action="store_true", help="grilla de w_risk y alpha para objetos + predictor")
    p.add_argument("--only-tuned", action="store_true", help="con --no-model: solo la variante ajustada")
    p.add_argument("--curve", action="store_true", help="curva llegar vs. morir (w_risk y navegador con plazo)")
    p.add_argument("--learn-know", action="store_true", help="actualizar knowledge.json (recursos, giros)")
    p.add_argument("--seeds", type=int, default=0, help="con --no-model --only-tuned: repetir con N semillas y dar IC 95 %")
    a = p.parse_args()
    if a.curve:
        return curve(a.game, a.procs)
    if a.learn_know:
        return learn_knowledge(a.game, a.procs)
    if a.tune_objects:
        return tune_objects(a.game, a.procs)
    if a.no_model:
        lv = test_levels(a.game)
        variants = [("sin peligro", {**NAV_DEFAULT, "w_risk": 0.0}, False), ("predictor", NAV_DEFAULT, True),
                    ("objetos", NAV_DEFAULT, "objects"), ("objetos + predictor", NAV_DEFAULT, "objects+pred")]
        f = RUNS / a.game / "nav_objects.json"
        if f.exists():
            variants.append(("objetos + predictor ajust.", json.loads(f.read_text()), "objects+pred"))
        if a.only_tuned:
            variants = variants[-1:]
        if a.seeds:
            return seeds_report(a.game, variants, a.orders, a.procs, lv, a.seeds)
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
