import collections

import numpy as np
import torch

from boulder.macro import N_MACRO_FEATURES, MacroEnv
from boulder.model import PointerTransformer
from boulder.sim import E, EXIT, GEM, ROCK, W

from tests.test_tokens import empty_sim


def env_with(sim):
    env = MacroEnv(seed=0)
    env.reset()
    env.sim = sim
    return env


def test_obs_and_valid_mask():
    env = MacroEnv(seed=2)
    (tok, mask, valid), _ = env.reset()
    assert tok.shape == (32, N_MACRO_FEATURES)
    assert valid[0], "esperar siempre es válido"
    assert not (valid & ~mask).any(), "solo tokens reales son elegibles"
    assert (tok[valid, N_MACRO_FEATURES - 2] == 1).all()


def test_goto_gem_collects_it_in_one_decision():
    s = empty_sim()
    s.grid[10 * W + 24] = GEM
    env = env_with(s)
    tok, mask, valid = env._obs()
    k = next(n for n, o in enumerate(env.opts) if o and o[0] == "goto" and o[1] == 10 * W + 24)
    _, r, term, trunc, info = env.step(k)
    assert s.agent.gems == 1 and info["ticks"] == 4
    assert r > 4, "gema (+5) menos 4 pasos"


def test_push_rock_option_moves_the_rock():
    s = empty_sim()
    g = s.grid
    g[10 * W + 23] = ROCK
    g[10 * W + 22] = E
    g[10 * W + 21] = E
    for x in range(19, 26):
        g[11 * W + x] = 2        # piso de muro para que la roca no caiga
    env = env_with(s)
    env._obs()
    k = next(n for n, o in enumerate(env.opts) if o and o[0] == "push")
    env.step(k)
    assert g[10 * W + 23] != ROCK, "la roca se movió"


def test_exit_only_valid_with_quota():
    s = empty_sim()
    s.grid[10 * W + 23] = EXIT
    env = env_with(s)
    env._obs()
    assert not any(o and o[1] == 10 * W + 23 for o in env.opts)
    s.agent.gems = s.need_each
    env._obs()
    assert any(o and o[1] == 10 * W + 23 for o in env.opts)


def test_pointer_never_picks_invalid_tokens():
    env = MacroEnv(seed=4)
    (tok, mask, valid), _ = env.reset()
    m = PointerTransformer(N_MACRO_FEATURES)
    lg, v = m(torch.from_numpy(tok)[None], torch.from_numpy(mask)[None], torch.from_numpy(valid)[None])
    p = torch.softmax(lg, -1)[0].detach().numpy()
    assert p[~valid].sum() < 1e-6 and abs(p.sum() - 1) < 1e-5


def test_cheapest_target_policy_matches_the_astar_baseline():
    """Elegir siempre la gema/salida más barata dentro de MacroEnv debe jugar tan bien como baseline.py."""
    env = MacroEnv(seed=7)
    env.reset()
    out = collections.Counter()
    gems = lives = 0
    while lives < 40:
        best, bc = 0, 1e9
        for n, o in enumerate(env.opts):
            if o and o[0] == "goto" and env.sim.grid[o[1]] in (GEM, EXIT) and o[2] < bc:
                best, bc = n, o[2]
        _, _, te, tr, info = env.step(best)
        if te or tr:
            lives += 1
            out[info["outcome"]] += 1
            gems += info["gems"]
    assert gems / lives > 10
    assert out["exit"] / lives > 0.5
