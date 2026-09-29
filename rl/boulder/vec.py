"""Entornos en paralelo: cada proceso corre varios BoulderEnv y responde en bloque."""
from __future__ import annotations

import multiprocessing as mp
import signal

import numpy as np

from .env import BoulderEnv
from .macro import MacroEnv


def _worker(conn, n, seed, levels, max_tokens, kind):
    signal.signal(signal.SIGINT, signal.SIG_IGN)      # el proceso principal decide cuándo parar
    cls = MacroEnv if kind == "macro" else BoulderEnv
    envs = [cls(levels=levels, seed=seed * 1000 + k, max_tokens=max_tokens) for k in range(n)]
    while True:
        cmd, data = conn.recv()
        if cmd == "reset":
            obs = [e.reset()[0] for e in envs]
            conn.send(obs)
        elif cmd == "step":
            res = [e.step(a) for e, a in zip(envs, data)]
            conn.send([(o, r, t, tr, i) for o, r, t, tr, i in res])
        elif cmd == "close":
            conn.close()
            return


class VecEnv:
    def __init__(self, n_workers=3, envs_per_worker=8, seed=0, levels=range(1, 13), max_tokens=32, kind="micro"):
        ctx = mp.get_context("spawn")
        self.conns, self.procs = [], []
        for w in range(n_workers):
            a, b = ctx.Pipe()
            p = ctx.Process(target=_worker, args=(b, envs_per_worker, seed + w, list(levels), max_tokens, kind), daemon=True)
            p.start()
            self.conns.append(a)
            self.procs.append(p)
        self.per = envs_per_worker
        self.n = n_workers * envs_per_worker

    @staticmethod
    def _stack(obs):
        return tuple(np.stack([o[k] for o in obs]) for k in range(len(obs[0])))

    def reset(self):
        for c in self.conns:
            c.send(("reset", None))
        return self._stack([o for c in self.conns for o in c.recv()])

    def step(self, actions):
        for k, c in enumerate(self.conns):
            c.send(("step", [int(a) for a in actions[k * self.per:(k + 1) * self.per]]))
        res = [x for c in self.conns for x in c.recv()]
        obs = self._stack([x[0] for x in res])
        rew = np.array([x[1] for x in res], np.float32)
        term = np.array([x[2] for x in res])
        trunc = np.array([x[3] for x in res])
        return obs, rew, term, trunc, [x[4] for x in res]

    def close(self):
        for c in self.conns:
            try:
                c.send(("close", None))
            except (BrokenPipeError, OSError):
                pass
        for p in self.procs:
            p.join(timeout=2)
