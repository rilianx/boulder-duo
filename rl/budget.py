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
    K = Knowledge()
    X, Y = [], []
    T = [None]
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
        # 1. explorar
        t_exp = t0 + a.explore * a.budget
        g = 0
        while time.time() < t_exp:
            ag = GenericAgent(random_weights(rng), know=K, rng=rng, eps=0.3)
            b.play(lv[g % len(lv)], a.seed * 1000 + g, recorder(ag, t_exp))
            g += 1
        log["juegos_explorar"] = g
        # 2. ajustar el riesgo
        tf = time.time()
        fit()
        t_fit = time.time() - tf
        # 3. practicar, dejando tiempo para el reajuste final
        stop = deadline - 1.5 * t_fit - 2
        NP = {"w_risk": 20.0, "alpha": 1.0, "patience": 0}
        nav_models = (CellRisk(d / "cell_risk.pt"), GDanger(d / "danger.pt"))
        while time.time() < stop:
            nav = ObjectCubeNavigator(K, nav_models[0], NP, danger=nav_models[1])
            cmd = Commander(K, dict(DEFAULT_W), nav, {"practice": True})
            won, _, _ = b.play(lv[g % len(lv)], a.seed * 1000 + g, recorder(cmd, stop))
            log["juegos_practica"] += 1
            log["victorias_practica"] += int(won == 1)
            g += 1
    finally:
        b.close()
    # 4. reajustar con todo lo vivido
    fit()
    (d / "knowledge_hl.json").write_text(json.dumps(K.to_json()))
    log.update({"segundos": round(time.time() - t0, 1), "presupuesto": a.budget, "pasos": len(Y),
                "muertes_etiquetadas": int(sum(Y)), "k": a.k})
    (d / "budget_log.json").write_text(json.dumps(log))
    print(f"{a.game} presupuesto {a.budget} s: {log}", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("game")
    p.add_argument("--budget", type=float, default=300, help="segundos de reloj para aprender el juego")
    p.add_argument("--explore", type=float, default=0.3, help="fracción del presupuesto para explorar barato")
    p.add_argument("--k", type=int, default=1, help="a cuántos ticks previos a la muerte se culpa")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--eval", action="store_true", help="evaluar después en los niveles de prueba")
    p.add_argument("--seeds", type=int, default=15)
    p.add_argument("--procs", type=int, default=4, help="procesos para evaluar (entrenar es siempre 1)")
    p.add_argument("--hl", default="{}")
    a = p.parse_args()
    out = ROOT / "runs" / "presupuesto" / f"b{int(a.budget)}"
    os.environ["GVGAI_RUNS"] = str(out)
    run(a, out)
    if a.eval:
        subprocess.run([sys.executable, str(ROOT / "play_hl.py"), a.game, "--seeds", str(a.seeds),
                        "--procs", str(a.procs), "--hl", a.hl], check=True, env=os.environ.copy())


if __name__ == "__main__":
    main()
