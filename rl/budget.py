"""Variante con presupuesto de entrenamiento (al estilo de la pista de aprendizaje de GVGAI): todo lo que el
agente sabe de un juego se aprende en `--budget` segundos de reloj, en un solo proceso, jugando los niveles de
entrenamiento y sin consultar el simulador. Nada se trae del framework principal: ni conocimiento, ni
predictor, ni pesos ajustados (se usan los valores por defecto).

Fases, todas dentro del presupuesto:
  1. explorar (fracción --explore): el agente genérico, barato, con mucha curiosidad. Aprende transitabilidad,
     efectos de tocar, movimiento de cada tipo, teletransportes... y cada paso real queda etiquetado
     "murió en los k ticks siguientes o no" (solo lo vivido, sin contrafactuales).
  2. ajustar el riesgo: predictor de muerte y riesgo por casilla con esas etiquetas.
  3. practicar con el agente completo (alto nivel + navegador) hasta que queda justo el tiempo del reajuste:
     aprende qué toque gana, usar, empujar; y sigue juntando etiquetas.
  4. reajustar el riesgo con todo lo vivido.
Los modelos van a runs/presupuesto/b<segundos>/<juego>, así que el framework principal no se toca. Después se
evalúa igual que siempre (play_hl.py) en los niveles de prueba, que no se vieron.

    python budget.py zelda --budget 300 --eval --seeds 15
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent


def run(a, out):
    # se importa después de fijar GVGAI_RUNS: los módulos leen la carpeta de modelos al importarse
    import numpy as np
    import torch
    from boulder.cube import CellRisk, fit_cell_risk
    from boulder.generic import DEFAULT_W, GDanger, GenericAgent, GenericBridge, Knowledge, gfeatures, gplanes
    from boulder.highlevel import Commander
    from boulder.objcube import ObjectCubeNavigator
    from generic_train import random_weights, train
    from nav_bench import train_levels

    torch.set_num_threads(1)
    t0 = time.time()
    deadline = t0 + a.budget
    d = out / a.game
    d.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    lv = train_levels(a.game)
    K = Knowledge(apagadas=[x for x in a.sin.split(",") if x])   # ablación: mecánicas apagadas
    X, Y = [], []
    T = [None]
    arms = {w: [0.0, 0] for w in a.w_arms}               # w_risk → [suma de puntajes, partidas]
    log = {"juegos_explorar": 0, "juegos_practica": 0, "victorias_practica": 0}

    def recorder(inner, stop_at):
        """Envuelve una política: etiqueta los pasos reales y, pasado stop_at, se queda quieta sin pensar."""
        pending = []

        def pol(st, br):
            if T[0] is None:
                T[0] = max(st.types) + 1
            if time.time() > stop_at:
                return 4
            pending[:] = [(t, i) for t, i in pending if st.tick - t <= a.k]
            act = inner(st, br)
            W, N = st.W, len(st.masks)
            if isinstance(act, int) and act < 4:
                j = st.pos + (-W, 1, W, -1)[act]
                if 0 <= j < N and not K.blocked_cells(st)[j]:
                    X.append(gfeatures(gplanes(st, T[0]), [j], [act], W).astype(np.uint8))
                    Y.append(0.0)
                    pending.append((st.tick, len(Y) - 1))
            return act

        def end(won):
            if won != 1:                               # murió (o se acabó sin ganar): culpar a los últimos pasos
                for _, i in pending:
                    Y[i] = 1.0
            inner.end(won)
        pol.end = end
        return pol

    def fit():
        np.savez_compressed(d / "data.npz", X=np.concatenate(X), Y=np.array(Y, np.float32), T=T[0])
        (d / "knowledge.json").write_text(json.dumps(K.to_json()))
        train(a.game)
        fit_cell_risk(d / "data.npz", d / "cell_risk.pt")

    b = GenericBridge(a.game)
    try:
        # 1. explorar, adaptativo: mientras el explorador barato siga descubriendo algo (tipos tocados, qué
        # bloquea, teletransportes, arrastres, empujes, cómo se mueve cada tipo). Se corta tras --patience
        # partidas seguidas sin novedad, o al llegar al tope --explore del presupuesto.
        seen = {}                                        # (tipo en la casilla pisada, murió) → veces

        def signature():
            # situaciones de riesgo vividas al menos 3 veces: pisar un tipo y sobrevivir o morir
            for i in range(signature.n, len(Y)):
                m = X[i].reshape(-1)
                for t in range(T[0]):
                    if m[t * 49 + 24]:                    # plano "ahora" del tipo t, casilla central
                        k = (t, int(Y[i] > 0.5)); seen[k] = seen.get(k, 0) + 1
            signature.n = len(Y)
            return (frozenset(k for k, v in seen.items() if v >= 3),
                    frozenset(t for t, e in K.eff.items() if e[0] >= 3),frozenset(t for t, e in K.eff.items() if e[0] >= 3),
                    frozenset(t for t in set(K.passed) | set(K.blocked) if K.is_blocking(t)),
                    frozenset(K.teleport), frozenset(K.carriers()), frozenset(t for t in K.push if K.pushable(t)),
                    frozenset(K.move_dirs), frozenset(K.avatar_types))
        signature.n = 0
        t_exp = t0 + a.explore * a.budget
        g, quiet, sig, t_new = 0, 0, signature(), time.time()
        while time.time() < t_exp and (quiet < a.patience or time.time() - t_new < a.patience_t * a.budget):
            ag = GenericAgent(random_weights(rng), know=K, rng=rng, eps=0.3)
            b.play(lv[g % len(lv)], a.seed * 1000 + g, recorder(ag, t_exp))
            g += 1
            new = signature()
            if new != sig:
                quiet, t_new = 0, time.time()
            else:
                quiet += 1
            sig = new
        log["juegos_explorar"] = g
        log["segundos_explorar"] = round(time.time() - t0, 1)
        # 2. ajustar el riesgo
        tf = time.time()
        fit()
        t_fit = time.time() - tf
        # 3. practicar, dejando tiempo para el reajuste final
        stop = deadline - 1.5 * t_fit - 2
        NP = {"w_risk": a.w_arms[0], "alpha": 1.0, "patience": 0}
        nav_models = (CellRisk(d / "cell_risk.pt"), GDanger(d / "danger.pt"))
        last_fit = time.time()
        while time.time() < stop:
            # reajustar cada tanto con lo vivido en la práctica: el riesgo aprendido del explorador (que se
            # tira a todo) es pesimista, y las partidas del agente completo lo corrigen
            if a.refit and time.time() - last_fit > a.refit and time.time() + 1.5 * t_fit < stop:
                tf = time.time()
                fit()
                t_fit = time.time() - tf
                stop = deadline - 1.5 * t_fit - 2
                nav_models = (CellRisk(d / "cell_risk.pt"), GDanger(d / "danger.pt"))
                last_fit = time.time()
                log["reajustes"] = log.get("reajustes", 0) + 1
            nav = ObjectCubeNavigator(K, nav_models[0], NP, danger=nav_models[1])
            cmd = Commander(K, dict(DEFAULT_W), nav, {"practice": True})
            won, _, ticks = b.play(lv[g % len(lv)], a.seed * 1000 + g, recorder(cmd, stop))
            log["juegos_practica"] += 1
            log["victorias_practica"] += int(won == 1)
            g += 1
            # prudencia adaptativa (en vez de ajustar w_risk por juego con una grilla): bandido UCB sobre unos
            # pocos valores, con el puntaje de la partida = (llegar − 0,5·tiempo agotado) por orden − 2·morir.
            # No se supone la dirección: en Frogs quedarse quieto también mata, así que más prudencia no siempre
            # es menos muerte
            died = won != 1 and ticks < a.max_ticks and time.time() < stop
            st_ = cmd.stats
            J = (st_["reached"] - 0.5 * st_["timeout"]) / max(st_["orders"], 1) - 2 * died + 2 * (won == 1)
            arm = arms[NP["w_risk"]]; arm[0] += J; arm[1] += 1
            n = sum(v[1] for v in arms.values())
            NP["w_risk"] = max(arms, key=lambda w: math.inf if arms[w][1] == 0 else
                               arms[w][0] / arms[w][1] + a.ucb * math.sqrt(math.log(n) / arms[w][1]))
            log.setdefault("w_risk", []).append(round(NP["w_risk"], 1))
    finally:
        b.close()
    # 4. reajustar con todo lo vivido
    fit()
    (d / "knowledge_hl.json").write_text(json.dumps(K.to_json()))
    # la prudencia con mejor puntaje medio en la práctica es la que usa la evaluación
    tried = {w: v for w, v in arms.items() if v[1]}
    best = max(tried, key=lambda w: tried[w][0] / tried[w][1]) if tried else 20.0
    (d / "nav_objects.json").write_text(json.dumps({"w_risk": best, "alpha": 1.0}))
    log["w_risk"] = {w: (round(v[0] / v[1], 2), v[1]) for w, v in tried.items()}
    log["w_risk_final"] = best
    log.update({"segundos": round(time.time() - t0, 1), "presupuesto": a.budget, "pasos": len(Y),
                "muertes_etiquetadas": int(sum(Y)), "k": a.k})
    (d / "budget_log.json").write_text(json.dumps(log))
    print(f"{a.game} presupuesto {a.budget} s: {log}", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("game")
    p.add_argument("--budget", type=float, default=300, help="segundos de reloj para aprender el juego")
    p.add_argument("--refit", type=float, default=30, help="segundos entre reajustes del riesgo al practicar (0 = no)")
    p.add_argument("--out", default=None, help="subcarpeta de runs/presupuesto (por defecto b<segundos>)")
    p.add_argument("--explore", type=float, default=0.3, help="tope de la fracción del presupuesto para explorar barato")
    p.add_argument("--patience", type=int, default=20, help="partidas seguidas sin novedad para dejar de explorar")
    p.add_argument("--patience-t", dest="patience_t", type=float, default=0.05,
                   help="y además esta fracción del presupuesto sin novedad")
    p.add_argument("--k", type=int, default=1, help="a cuántos ticks previos a la muerte se culpa")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--w-arms", dest="w_arms", type=lambda v: [float(x) for x in v.split(",")], default=[20.0, 6.0, 12.0, 40.0],
                   help="valores de w_risk entre los que elige el bandido de la práctica")
    p.add_argument("--ucb", type=float, default=1.0)
    p.add_argument("--max-ticks", dest="max_ticks", type=int, default=1990, help="terminar antes de esto sin ganar = murió")
    p.add_argument("--eval", action="store_true", help="evaluar después en los niveles de prueba")
    p.add_argument("--seeds", type=int, default=15)
    p.add_argument("--procs", type=int, default=4, help="procesos para evaluar (entrenar es siempre 1)")
    p.add_argument("--hl", default="{}")
    p.add_argument("--sin", default="", help="mecánicas apagadas (ablación), p. ej. usar,empujar")
    p.add_argument("--retrain", action="store_true", help="entrenar de nuevo aunque ya esté hecho")
    a = p.parse_args()
    out = ROOT / "runs" / "presupuesto" / (a.out or f"b{int(a.budget)}")
    os.environ["GVGAI_RUNS"] = str(out)
    if a.retrain or not (out / a.game / "budget_log.json").exists():
        run(a, out)
    if a.eval:
        subprocess.run([sys.executable, str(ROOT / "play_hl.py"), a.game, "--seeds", str(a.seeds),
                        "--procs", str(a.procs), "--hl", a.hl, "--sin", a.sin], check=True, env=os.environ.copy())


if __name__ == "__main__":
    main()
