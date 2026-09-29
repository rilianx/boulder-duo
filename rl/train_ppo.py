"""Entrena el transformer de entidades con PPO y guarda el avance en rl/runs/<nombre>/.

    python train_ppo.py --name base --steps 2000000          # entrenar
    python train_ppo.py --name base --steps 4000000 --resume # seguir desde el último checkpoint

Guarda `ckpt.pt` (modelo + optimizador + contadores) cada --save-every actualizaciones y al
interrumpir con Ctrl-C, y agrega una fila por actualización a `metrics.csv`.
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

from boulder.model import EntityTransformer
from boulder.vec import VecEnv


def parse():
    p = argparse.ArgumentParser()
    p.add_argument("--name", default="base")
    p.add_argument("--steps", type=int, default=2_000_000, help="pasos de entorno en total")
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    p.add_argument("--envs-per-worker", type=int, default=8)
    p.add_argument("--rollout", type=int, default=64)
    p.add_argument("--epochs", type=int, default=4)
    p.add_argument("--minibatch", type=int, default=512)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--gamma", type=float, default=0.99)
    p.add_argument("--gae", type=float, default=0.95)
    p.add_argument("--clip", type=float, default=0.2)
    p.add_argument("--ent", type=float, default=0.01)
    p.add_argument("--vf", type=float, default=0.5)
    p.add_argument("--d", type=int, default=64)
    p.add_argument("--layers", type=int, default=3)
    p.add_argument("--heads", type=int, default=4)
    p.add_argument("--save-every", type=int, default=10)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-tokens", type=int, default=32)
    return p.parse_args()


def main():
    args = parse()
    torch.manual_seed(args.seed)
    n_cpu = os.cpu_count() or 2
    run = Path(__file__).parent / "runs" / args.name
    run.mkdir(parents=True, exist_ok=True)

    model = EntityTransformer(d=args.d, heads=args.heads, layers=args.layers)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, eps=1e-5)
    steps = updates = 0
    episodes = 0
    if args.resume and (run / "ckpt.pt").exists():
        ck = torch.load(run / "ckpt.pt", weights_only=False)
        model.load_state_dict(ck["model"]); opt.load_state_dict(ck["opt"])
        steps, updates, episodes = ck["steps"], ck["updates"], ck["episodes"]
        print(f"retomando {run / 'ckpt.pt'}: {steps:,} pasos, {episodes:,} episodios")

    def save():
        tmp = run / "ckpt.pt.tmp"
        torch.save({"model": model.state_dict(), "opt": opt.state_dict(), "steps": steps, "updates": updates,
                    "episodes": episodes, "max_tokens": args.max_tokens,
                    "config": {"d": args.d, "heads": args.heads, "layers": args.layers}}, tmp)
        os.replace(tmp, run / "ckpt.pt")

    venv = VecEnv(args.workers, args.envs_per_worker, seed=args.seed + updates * 7919, max_tokens=args.max_tokens)
    N, R = venv.n, args.rollout
    tok, mask = venv.reset()
    recent = collections.deque(maxlen=300)
    new_csv = not (run / "metrics.csv").exists() or not args.resume
    fcsv = open(run / "metrics.csv", "w" if new_csv else "a", newline="")
    wcsv = csv.writer(fcsv)
    if new_csv:
        wcsv.writerow(["updates", "steps", "episodes", "gems_per_life", "exit_pct", "death_pct", "timeout_pct",
                       "steps_per_s", "entropy", "value_loss", "approx_kl"])

    stop = {"flag": False}
    signal.signal(signal.SIGINT, lambda *_: stop.__setitem__("flag", True))
    T, F = tok.shape[1:]
    t_start, s_start = time.time(), steps
    try:
        while steps < args.steps and not stop["flag"]:
            b_tok = np.zeros((R, N, T, F), np.float32); b_mask = np.zeros((R, N, T), bool)
            b_act = np.zeros((R, N), np.int64); b_logp = np.zeros((R, N), np.float32)
            b_val = np.zeros((R, N), np.float32); b_rew = np.zeros((R, N), np.float32)
            b_done = np.zeros((R, N), np.float32)
            torch.set_num_threads(max(1, n_cpu - args.workers))   # los entornos usan el resto
            for t in range(R):
                with torch.no_grad():
                    logits, v = model(torch.from_numpy(tok), torch.from_numpy(mask))
                dist = Categorical(logits=logits)
                a = dist.sample()
                b_tok[t], b_mask[t] = tok, mask
                b_act[t], b_logp[t], b_val[t] = a.numpy(), dist.log_prob(a).numpy(), v.numpy()
                (tok, mask), r, term, trunc, infos = venv.step(a.numpy())
                b_rew[t] = r
                # un timeout también corta el episodio (sin bootstrap: sesgo pequeño y conocido)
                b_done[t] = np.logical_or(term, trunc)
                for inf in infos:
                    if "outcome" in inf:
                        recent.append((inf["gems"], inf["outcome"]))
                        episodes += 1
            steps += R * N
            with torch.no_grad():
                _, last_v = model(torch.from_numpy(tok), torch.from_numpy(mask))
            adv = np.zeros((R, N), np.float32)
            gae = np.zeros(N, np.float32)
            nxt = last_v.numpy()
            for t in reversed(range(R)):
                nonterm = 1.0 - b_done[t]
                delta = b_rew[t] + args.gamma * nxt * nonterm - b_val[t]
                gae = delta + args.gamma * args.gae * nonterm * gae
                adv[t] = gae
                nxt = b_val[t]
            ret = adv + b_val

            f_tok = torch.from_numpy(b_tok.reshape(R * N, T, F)); f_mask = torch.from_numpy(b_mask.reshape(R * N, T))
            f_act = torch.from_numpy(b_act.reshape(-1)); f_logp = torch.from_numpy(b_logp.reshape(-1))
            f_adv = torch.from_numpy(adv.reshape(-1)); f_ret = torch.from_numpy(ret.reshape(-1))
            f_adv = (f_adv - f_adv.mean()) / (f_adv.std() + 1e-8)
            torch.set_num_threads(n_cpu)                          # los entornos esperan: todos los núcleos a la red
            idx = np.arange(R * N)
            ents, vls, kls = [], [], []
            for _ in range(args.epochs):
                np.random.shuffle(idx)
                for s0 in range(0, len(idx), args.minibatch):
                    mb = torch.from_numpy(idx[s0:s0 + args.minibatch])
                    logits, v = model(f_tok[mb], f_mask[mb])
                    dist = Categorical(logits=logits)
                    logp = dist.log_prob(f_act[mb])
                    ratio = (logp - f_logp[mb]).exp()
                    pg = -torch.min(ratio * f_adv[mb], ratio.clamp(1 - args.clip, 1 + args.clip) * f_adv[mb]).mean()
                    vl = 0.5 * (v - f_ret[mb]).pow(2).mean()
                    ent = dist.entropy().mean()
                    loss = pg + args.vf * vl - args.ent * ent
                    opt.zero_grad(); loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)
                    opt.step()
                    ents.append(ent.item()); vls.append(vl.item())
                    kls.append(((ratio - 1) - (logp - f_logp[mb])).mean().item())
            updates += 1

            n = len(recent) or 1
            gpl = sum(g for g, _ in recent) / n
            pct = lambda o: 100 * sum(1 for _, x in recent if x == o) / n
            sps = (steps - s_start) / (time.time() - t_start)
            row = [updates, steps, episodes, round(gpl, 3), round(pct("exit"), 2), round(pct("death"), 2),
                   round(pct("timeout"), 2), round(sps), round(np.mean(ents), 4), round(np.mean(vls), 4), round(np.mean(kls), 5)]
            wcsv.writerow(row); fcsv.flush()
            print(f"act {updates:5d} | pasos {steps:>10,} | vidas {episodes:>7,} | gemas/vida {gpl:5.2f} | "
                  f"salida {pct('exit'):5.1f}% | muerte {pct('death'):5.1f}% | {sps:,.0f} pasos/s", flush=True)
            if updates % args.save_every == 0:
                save()
    finally:
        save()
        fcsv.close()
        venv.close()
        print(f"guardado en {run / 'ckpt.pt'}")


if __name__ == "__main__":
    main()
