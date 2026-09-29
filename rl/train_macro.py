"""PPO semi-Markov para acciones de alto nivel: la red elige un token y A* lleva al PC hasta él.

    python train_macro.py --name destinos --steps 300000          # pasos = decisiones
    python train_macro.py --name destinos --steps 600000 --resume

Cada decisión dura K ticks; su recompensa ya viene descontada dentro de la opción y el bootstrap usa
γ^K (GAE con γ^K·λ). Guarda runs/<nombre>/ckpt.pt y metrics.csv igual que train_ppo.py.
"""
from __future__ import annotations

import argparse
import collections
import csv
import os
import signal
import time
from pathlib import Path

import numpy as np
import torch
from torch.distributions import Categorical

from boulder.macro import N_MACRO_FEATURES
from boulder.model import PointerTransformer
from boulder.vec import VecEnv


def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--name", default="destinos")
    p.add_argument("--steps", type=int, default=300_000, help="decisiones en total")
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    p.add_argument("--envs-per-worker", type=int, default=8)
    p.add_argument("--rollout", type=int, default=32)
    p.add_argument("--epochs", type=int, default=4)
    p.add_argument("--minibatch", type=int, default=256)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--gamma", type=float, default=0.99, help="por tick")
    p.add_argument("--gae", type=float, default=0.95)
    p.add_argument("--clip", type=float, default=0.2)
    p.add_argument("--ent", type=float, default=0.01)
    p.add_argument("--vf", type=float, default=0.5)
    p.add_argument("--d", type=int, default=64)
    p.add_argument("--layers", type=int, default=3)
    p.add_argument("--heads", type=int, default=4)
    p.add_argument("--max-tokens", type=int, default=32)
    p.add_argument("--save-every", type=int, default=10)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    return p.parse_args()


def main():
    args = parse()
    torch.manual_seed(args.seed)
    n_cpu = os.cpu_count() or 2
    run = Path(__file__).parent / "runs" / args.name
    run.mkdir(parents=True, exist_ok=True)
    cfg = {"n_features": N_MACRO_FEATURES, "d": args.d, "heads": args.heads, "layers": args.layers}
    model = PointerTransformer(**cfg)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, eps=1e-5)
    steps = updates = episodes = ticks_total = 0
    if args.resume and (run / "ckpt.pt").exists():
        ck = torch.load(run / "ckpt.pt", weights_only=False)
        model.load_state_dict(ck["model"]); opt.load_state_dict(ck["opt"])
        steps, updates, episodes, ticks_total = ck["steps"], ck["updates"], ck["episodes"], ck.get("ticks", 0)
        print(f"retomando {run / 'ckpt.pt'}: {steps:,} decisiones, {episodes:,} vidas")

    def save():
        tmp = run / "ckpt.pt.tmp"
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "steps": steps, "updates": updates,
                    "episodes": episodes, "ticks": ticks_total, "max_tokens": args.max_tokens, "kind": "macro",
                    "config": cfg}, tmp)
        os.replace(tmp, run / "ckpt.pt")

    venv = VecEnv(args.workers, args.envs_per_worker, seed=args.seed + updates * 7919,
                  max_tokens=args.max_tokens, kind="macro")
    N, R = venv.n, args.rollout
    tok, mask, valid = venv.reset()
    recent = collections.deque(maxlen=300)
    new_csv = not (run / "metrics.csv").exists() or not args.resume
    fcsv = open(run / "metrics.csv", "w" if new_csv else "a", newline="")
    wcsv = csv.writer(fcsv)
    if new_csv:
        wcsv.writerow(["updates", "decisions", "ticks", "episodes", "gems_per_life", "exit_pct", "death_pct",
                       "timeout_pct", "ticks_per_decision", "decisions_per_s", "entropy", "value_loss", "approx_kl"])
    stop = {"flag": False}
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__("flag", True))
    T, F = tok.shape[1:]
    t0, s0 = time.time(), steps
    try:
        while steps < args.steps and not stop["flag"]:
            B = {k: np.zeros((R, N) + sh, dt) for k, sh, dt in [
                ("tok", (T, F), np.float32), ("mask", (T,), bool), ("valid", (T,), bool)]}
            act = np.zeros((R, N), np.int64); logp = np.zeros((R, N), np.float32)
            val = np.zeros((R, N), np.float32); rew = np.zeros((R, N), np.float32)
            done = np.zeros((R, N), np.float32); disc = np.zeros((R, N), np.float32)
            torch.set_num_threads(max(1, n_cpu - args.workers))
            kt = 0
            for t in range(R):
                with torch.no_grad():
                    lg, v = model(torch.from_numpy(tok), torch.from_numpy(mask), torch.from_numpy(valid))
                dist = Categorical(logits=lg)
                a = dist.sample()
                B["tok"][t], B["mask"][t], B["valid"][t] = tok, mask, valid
                act[t], logp[t], val[t] = a.numpy(), dist.log_prob(a).numpy(), v.numpy()
                (tok, mask, valid), r, term, trunc, infos = venv.step(a.numpy())
                rew[t] = r
                done[t] = np.logical_or(term, trunc)
                K = np.array([i["ticks"] for i in infos], np.float32)
                disc[t] = args.gamma ** K
                kt += K.sum()
                for inf in infos:
                    if "outcome" in inf:
                        recent.append((inf["gems"], inf["outcome"]))
                        episodes += 1
            steps += R * N
            ticks_total += int(kt)
            with torch.no_grad():
                _, nxt = model(torch.from_numpy(tok), torch.from_numpy(mask), torch.from_numpy(valid))
            nxt = nxt.numpy()
            adv = np.zeros((R, N), np.float32); gae = np.zeros(N, np.float32)
            for t in reversed(range(R)):
                nonterm = 1.0 - done[t]
                delta = rew[t] + disc[t] * nxt * nonterm - val[t]
                gae = delta + disc[t] * args.gae * nonterm * gae
                adv[t] = gae
                nxt = val[t]
            ret = adv + val

            f = {k: torch.from_numpy(v.reshape((R * N,) + v.shape[2:])) for k, v in B.items()}
            f_act = torch.from_numpy(act.reshape(-1)); f_logp = torch.from_numpy(logp.reshape(-1))
            f_ret = torch.from_numpy(ret.reshape(-1))
            f_adv = torch.from_numpy(adv.reshape(-1)); f_adv = (f_adv - f_adv.mean()) / (f_adv.std() + 1e-8)
            torch.set_num_threads(n_cpu)
            idx = np.arange(R * N)
            ents, vls, kls = [], [], []
            for _ in range(args.epochs):
                np.random.shuffle(idx)
                for a0 in range(0, len(idx), args.minibatch):
                    mb = torch.from_numpy(idx[a0:a0 + args.minibatch])
                    lg, v = model(f["tok"][mb], f["mask"][mb], f["valid"][mb])
                    dist = Categorical(logits=lg)
                    lp = dist.log_prob(f_act[mb])
                    ratio = (lp - f_logp[mb]).exp()
                    pg = -torch.min(ratio * f_adv[mb], ratio.clamp(1 - args.clip, 1 + args.clip) * f_adv[mb]).mean()
                    vl = 0.5 * (v - f_ret[mb]).pow(2).mean()
                    ent = dist.entropy().mean()
                    loss = pg + args.vf * vl - args.ent * ent
                    opt.zero_grad(); loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)
                    opt.step()
                    ents.append(ent.item()); vls.append(vl.item())
                    kls.append(((ratio - 1) - (lp - f_logp[mb])).mean().item())
            updates += 1
            n = len(recent) or 1
            gpl = sum(g for g, _ in recent) / n
            pct = lambda o: 100 * sum(1 for _, x in recent if x == o) / n
            dps = (steps - s0) / (time.time() - t0)
            tpd = kt / (R * N)
            wcsv.writerow([updates, steps, ticks_total, episodes, round(gpl, 3), round(pct("exit"), 2), round(pct("death"), 2),
                           round(pct("timeout"), 2), round(tpd, 2), round(dps), round(np.mean(ents), 4),
                           round(np.mean(vls), 4), round(np.mean(kls), 5)])
            fcsv.flush()
            print(f"act {updates:4d} | decisiones {steps:>8,} | vidas {episodes:>6,} | gemas/vida {gpl:5.2f} | "
                  f"salida {pct('exit'):5.1f}% | muerte {pct('death'):5.1f}% | tiempo {pct('timeout'):5.1f}% | "
                  f"{tpd:4.1f} ticks/dec | {dps:,.0f} dec/s", flush=True)
            if updates % args.save_every == 0:
                save()
    finally:
        save(); fcsv.close(); venv.close()
        print(f"guardado en {run / 'ckpt.pt'}")


if __name__ == "__main__":
    main()
