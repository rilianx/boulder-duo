"""Evalúa nuestras políticas en el Boulder Dash real de GVGAI (5 niveles oficiales).

    python gvgai_eval.py --seeds 20                 # A* con reglas de peligro para GVGAI
    python gvgai_eval.py --seeds 20 --no-danger     # el mismo A* sin costos de peligro
Tasa de victoria = juntar 9 diamantes y llegar a la salida antes de 2000 ticks, con 1 vida.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor

from boulder.gvgai_env import GvgaiBridge
from boulder.gvgai_policy import GV_DEFAULT, gv_act


def run(job):
    level, seeds, P = job
    b = GvgaiBridge()
    try:
        return level, [b.play(level, s, lambda st, br: gv_act(st, P)) for s in seeds]
    finally:
        b.close()


def evaluate(P, seeds, procs=4, label=""):
    with ProcessPoolExecutor(procs) as ex:
        res = list(ex.map(run, [(lv, list(seeds), P) for lv in range(5)]))
    allr = [r for _, rs in res for r in rs]
    per = " ".join(f"n{lv}:{sum(r[0] for r in rs)}/{len(rs)}" for lv, rs in res)
    win = 100 * sum(r[0] for r in allr) / len(allr)
    print(f"{label:>22}: victorias {win:5.1f}% ({per}) | puntaje medio {sum(r[1] for r in allr) / len(allr):5.1f} | "
          f"ticks medios {sum(r[2] for r in allr) / len(allr):5.0f}", flush=True)
    return win


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=20)
    p.add_argument("--procs", type=int, default=4)
    p.add_argument("--no-danger", action="store_true")
    a = p.parse_args()
    seeds = range(100, 100 + a.seeds)
    evaluate(GV_DEFAULT, seeds, a.procs, "A* con peligro")
    if a.no_danger:
        evaluate({**GV_DEFAULT, "h_under": 0.0, "h_col": 0.0, "h_e1": 0.0, "h_e2": 0.0}, seeds, a.procs, "A* sin peligro")


if __name__ == "__main__":
    main()
