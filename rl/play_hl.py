"""Juego completo con el alto nivel (Commander) + navegador, en los niveles oficiales.

    python play_hl.py zelda --seeds 10          # victorias por nivel, puntaje, ticks
"""
from __future__ import annotations

import os
import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import torch

from boulder.cube import CellRisk
from boulder.generic import GDanger, GenericBridge, Knowledge
from boulder.highlevel import Commander
from boulder.objcube import ObjectCubeNavigator

# carpeta de modelos: GVGAI_RUNS la cambia (p. ej. para la variante con presupuesto, sin tocar la principal)
RUNS = Path(os.environ.get("GVGAI_RUNS", Path(__file__).parent / "runs" / "generic"))


def _play(job):
    game, level, seeds, NP, HP = job
    torch.set_num_threads(1)
    d = RUNS / NP.get("model_dir", game)
    kf = RUNS / game / "knowledge_hl.json"            # conocimiento tras la práctica del alto nivel, si existe
    K = Knowledge.from_json(json.loads((kf if kf.exists() and not HP.get("practice") else d / "knowledge.json").read_text()))
    vf = RUNS / game / "values.json"
    from boulder.generic import DEFAULT_W
    V = json.loads(vf.read_text()) if vf.exists() else dict(DEFAULT_W)   # sin CEM: pesos por defecto
    D = GDanger(d / "danger.pt")
    b = GenericBridge(game)
    out = []
    try:
        pairs = zip(level, seeds) if isinstance(level, list) else ((level, s) for s in seeds)
        for lv, s in pairs:
            nav = ObjectCubeNavigator(K, CellRisk(d / "cell_risk.pt"), NP, danger=D)
            cmd = Commander(K, V, nav, HP)
            won, score, ticks = b.play(lv, s, cmd)
            out.append((won, score, ticks, cmd.stats))
    finally:
        b.close()
    if HP.get("practice"):
        return level, out, K.to_json()
    return level, out


def practice(a):
    """Práctica en niveles generados: el alto nivel aprende los efectos de tocar cada tipo (incluido ganar)."""
    from nav_bench import train_levels
    f = RUNS / a.game / "nav_objects.json"
    NP = {**({"w_risk": 20.0, "alpha": 1.0} if not f.exists() else json.loads(f.read_text())), "patience": 0,
          **json.loads(a.nav)}
    HP = {**json.loads(a.hl), "practice": True}
    lv = train_levels(a.game)
    per = max(a.practice // a.procs, 1)
    if len(lv) < a.practice:                          # pocos niveles de entrenamiento: se repiten con otras semillas
        lv = [lv[i % len(lv)] for i in range(a.practice)]
    jobs = [(a.game, lv[k * per:(k + 1) * per], list(range(900 + 50 * k, 900 + 50 * k + per)), NP, HP)
            for k in range(a.procs)]
    base = Knowledge.from_json(json.loads((RUNS / a.game / "knowledge.json").read_text()))
    K0 = Knowledge.from_json(json.loads((RUNS / a.game / "knowledge.json").read_text()))
    wins = n = 0
    with ProcessPoolExecutor(a.procs) as ex:
        for _, out, kj in ex.map(_play, jobs):
            wins += sum(r[0] == 1 for r in out); n += len(out)
            k = Knowledge.from_json(kj)
            for t, e in k.eff.items():                     # sumar solo lo nuevo de cada proceso
                o = K0.eff.get(t, [0, 0.0, 0.0, 0, 0]); m = base._e(t)
                for i in range(5):
                    m[i] += e[i] - o[i]
            for t, dd in k.move_dirs.items():
                for dd_k, cnt in dd.items():
                    o = K0.move_dirs.get(t, {}).get(dd_k, 0)
                    m = base.move_dirs.setdefault(t, {})
                    m[dd_k] = m.get(dd_k, 0) + cnt - o
            for t, dd in k.fall.items():
                for mk, v in dd.items():
                    o = K0.fall.get(t, {}).get(mk, [0, 0])
                    m = base.fall.setdefault(t, {}).setdefault(mk, [0, 0])
                    m[0] += v[0] - o[0]; m[1] += v[1] - o[1]
            for name in ("use_kill", "use_base"):
                for t, dd in getattr(k, name).items():
                    for key, v in dd.items():
                        o = getattr(K0, name).get(t, {}).get(key, [0, 0])
                        m = getattr(base, name).setdefault(t, {}).setdefault(key, [0, 0])
                        m[0] += v[0] - o[0]; m[1] += v[1] - o[1]
            for t, v in k.use_score.items():
                o = K0.use_score.get(t, [0.0, 0])
                m = base.use_score.setdefault(t, [0.0, 0])
                m[0] += v[0] - o[0]; m[1] += v[1] - o[1]
            for t, dd in k.teleport.items():
                for e, cnt in dd.items():
                    o = K0.teleport.get(t, {}).get(e, 0)
                    m = base.teleport.setdefault(t, {})
                    m[e] = m.get(e, 0) + cnt - o
            for t, v in k.push.items():
                o = K0.push.get(t, [0, 0])
                m = base.push.setdefault(t, [0, 0])
                m[0] += v[0] - o[0]; m[1] += v[1] - o[1]
            for t, dd in k.push_into.items():
                for mk, v in dd.items():
                    o = K0.push_into.get(t, {}).get(mk, [0, 0, 0, 0.0])
                    m = base.push_into.setdefault(t, {}).setdefault(mk, [0, 0, 0, 0.0])
                    for i in range(4):
                        m[i] += v[i] - o[i]
            for t, v in k.consumed.items():
                o = K0.consumed.get(t, [0, 0])
                m = base.consumed.setdefault(t, [0, 0])
                m[0] += v[0] - o[0]; m[1] += v[1] - o[1]
            for t, dd in k.term.items():
                for key, v in dd.items():
                    o = K0.term.get(t, {}).get(key, [0, 0])
                    m = base.term.setdefault(t, {}).setdefault(key, [0, 0])
                    m[0] += v[0] - o[0]; m[1] += v[1] - o[1]
    (RUNS / a.game / "knowledge_hl.json").write_text(json.dumps(base.to_json()))
    won = {t: {k: v for k, v in dd.items() if v[1]} for t, dd in base.term.items()}
    print(f"{a.game} práctica: {n} partidas, {wins} ganadas; toques que ganaron: {dict((t, w) for t, w in won.items() if w)}",
          flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("game")
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--procs", type=int, default=4)
    p.add_argument("--nav", default="{}", help="parámetros extra del navegador (JSON)")
    p.add_argument("--hl", default="{}", help="parámetros del alto nivel (JSON)")
    p.add_argument("--practice", type=int, default=0,
                   help="jugar N partidas en niveles generados aprendiendo qué hace ganar; guarda knowledge_hl.json")
    a = p.parse_args()
    if a.practice:
        return practice(a)
    f = RUNS / a.game / "nav_objects.json"
    NP = {**({"w_risk": 20.0, "alpha": 1.0} if not f.exists() else json.loads(f.read_text())), "patience": 0,
          **json.loads(a.nav)}
    HP = json.loads(a.hl)
    seeds = list(range(100, 100 + a.seeds))
    with ProcessPoolExecutor(a.procs) as ex:
        from nav_bench import test_levels
        res = dict(ex.map(_play, [(a.game, lv, seeds, NP, HP) for lv in test_levels(a.game)]))
    allr = [r for rs in res.values() for r in rs]
    per = " ".join(f"n{lv}:{sum(r[0] == 1 for r in rs)}/{len(rs)}" for lv, rs in sorted(res.items()))
    dq = sum(r[0] not in (0, 1) for r in allr)       # descalificadas por tiempo (GVGAI devuelve −100)
    keys = {k for r in allr for k in r[3]}
    st = {k: sum(r[3].get(k, 0) for r in allr) for k in sorted(keys)}
    print(f"{a.game} alto nivel + navegador {a.nav} {a.hl}: victorias {100 * np.mean([r[0] == 1 for r in allr]):5.1f}% ({per}) | descalificadas {dq} | "
          f"puntaje {np.mean([r[1] for r in allr]):5.1f} | ticks {np.mean([r[2] for r in allr]):6.0f} | órdenes {st}", flush=True)


if __name__ == "__main__":
    main()
