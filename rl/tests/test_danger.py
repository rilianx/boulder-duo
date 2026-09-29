import numpy as np

from boulder.danger import N_IN, features, label, planes
from boulder.policy import DEFAULT, act, cell_costs
from boulder.sim import E, FIRE, ROCK, W

from tests.test_tokens import empty_sim


def test_copy_does_not_touch_the_original():
    s = empty_sim()
    before = bytes(s.grid)
    c = s.copy()
    c.tick(1)
    assert bytes(s.grid) == before and (c.agent.x, s.agent.x) == (21, 20)


def test_counterfactual_labels_match_the_physics():
    s = empty_sim(); a = s.agent
    s.grid[(a.y - 2) * W + a.x + 1] = ROCK
    s.grid[(a.y - 1) * W + a.x + 1] = E
    assert label(s, 1) == 1 and label(s, 3) == 0          # bajo roca en el aire vs. al otro lado
    s = empty_sim(); a = s.agent
    s.grid[(a.y - 1) * W + a.x] = ROCK
    assert label(s, 2) == 1 and label(s, 1) == 0          # bajar desde debajo de una roca vs. de lado


def test_label_ignores_respawn_immunity():
    s = empty_sim(); a = s.agent
    a.immune = 20
    s.grid[(a.y - 1) * W + a.x] = ROCK
    assert label(s, 2) == 1


def test_features_are_local_and_directional():
    s = empty_sim(); a = s.agent
    pl = planes(s)
    j = a.y * W + a.x + 1
    X = features(pl, [j, j], [1, 2])
    assert X.shape == (2, N_IN)
    assert (X[0, :-4] == X[1, :-4]).all() and X[0, -4 + 1] == 1 and X[1, -4 + 2] == 1


def test_hand_policy_avoids_a_firefly():
    s = empty_sim(); a = s.agent
    for x in range(a.x + 1, a.x + 6):
        s.grid[a.y * W + x] = E
    s.grid[a.y * W + a.x + 3] = FIRE
    cost, danger = cell_costs(s, DEFAULT)
    assert danger[a.y * W + a.x + 1] and cost[a.y * W + a.x + 1] > 20
