import numpy as np

from boulder.env import BoulderEnv, target_distance
from boulder.sim import BUTT, DIRT, E, GEM, P2, ROCK, STEEL, W, H, Sim
from boulder.tokens import N_FEATURES, Tokenizer


def empty_sim():
    """Una mina toda de tierra con el PC en (20, 10), para armar escenas a mano."""
    s = Sim()
    s.init_level(1)
    g = s.grid
    for y in range(H):
        for x in range(W):
            g[y * W + x] = STEEL if x in (0, W - 1) or y in (0, H - 1) else DIRT
    for arr in (s.fall, s.dir, s.aux):
        arr[:] = bytes(len(arr))
    a = s.agent
    a.x, a.y = 20, 10
    g[a.y * W + a.x] = P2
    return s


def rows_of_type(tokens, mask, type_col):
    return [r for r, m in zip(tokens, mask) if m and r[type_col] == 1]


def test_shape_and_self_token_first():
    env = BoulderEnv(seed=1)
    (tok, mask), _ = env.reset()
    assert tok.shape == (64, N_FEATURES) and mask.shape == (64,)
    assert mask[0] and tok[0, 0] == 1 and tok[0, 8] == 0 and tok[0, 9] == 0
    assert mask.sum() > 5
    assert not tok[~mask].any(), "los tokens de relleno deben ser ceros"


def test_rock_over_a_hole_is_visible_in_its_local_data():
    s = empty_sim()
    g = s.grid
    g[8 * W + 22] = ROCK          # roca 2 a la derecha y 2 arriba del PC
    g[9 * W + 22] = E             # hueco bajo la roca: va a caer
    tok, mask = Tokenizer().encode(s)
    (rock,) = rows_of_type(tok, mask, 1)
    assert rock[8] == 2 / 8 and rock[9] == -2 / 6
    below = 21 + 6 * 7            # vecino (0, +1) es el índice 6 en _NEIGH
    assert rock[below + 0] == 1, "debajo de la roca hay vacío"
    assert rock[77 + 1] == 1, "dos más abajo hay tierra"


def test_enemy_direction_and_far_gems():
    s = empty_sim()
    g = s.grid
    g[10 * W + 25] = BUTT
    s.dir[10 * W + 25] = 3
    g[10 * W + 38] = GEM          # fuera de la pantalla del PC
    tok, mask = Tokenizer().encode(s)
    (bf,) = rows_of_type(tok, mask, 4)
    assert bf[14 + 3] == 1 and bf[18] == 1
    (gem,) = rows_of_type(tok, mask, 2)
    assert gem[18] == 0, "la gema lejana va marcada como fuera de vista"


def test_safe_route_avoids_a_hanging_rock():
    s = empty_sim()
    g = s.grid
    # gema dos a la derecha; la casilla del medio tiene una roca en el aire encima → peligrosa
    g[10 * W + 22] = GEM
    g[10 * W + 21] = E
    g[8 * W + 21] = ROCK
    g[9 * W + 21] = E
    d, _ = target_distance(s)
    assert d > 2, "la ruta segura debe rodear la casilla bajo la roca"


def test_env_runs_and_reports_outcomes():
    env = BoulderEnv(seed=3)
    env.reset()
    rnd = np.random.default_rng(3)
    outcomes = set()
    for _ in range(4000):
        _, r, term, trunc, info = env.step(int(rnd.integers(5)))
        assert np.isfinite(r)
        if term or trunc:
            outcomes.add(info["outcome"])
    assert "death" in outcomes
