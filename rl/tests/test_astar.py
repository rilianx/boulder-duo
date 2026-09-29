import math

from boulder.astar import hazard_map, plan
from boulder.sim import BUTT, E, GEM, ROCK, W

from tests.test_tokens import empty_sim


def test_goes_straight_when_safe():
    s = empty_sim()
    s.grid[10 * W + 24] = GEM
    cost, goal, d = plan(s, {10 * W + 24})
    assert (cost, goal, d) == (4.0, 10 * W + 24, 1)


def test_detours_around_a_hanging_rock():
    s = empty_sim()
    g = s.grid
    g[10 * W + 22] = GEM
    g[9 * W + 21] = E          # hueco…
    g[8 * W + 21] = ROCK       # …con roca encima: la casilla (21, 10) es peligrosa
    assert hazard_map(s)[10 * W + 21]
    cost, _, _ = plan(s, {10 * W + 22}, hazard=25)
    assert 2 < cost < 25, "rodea en vez de pasar bajo la roca"
    assert plan(s, {10 * W + 22}, hazard=0)[0] == 2


def test_never_steps_down_from_under_a_rock():
    s = empty_sim()
    g = s.grid
    a = s.agent
    g[(a.y - 1) * W + a.x] = ROCK              # roca apoyada sobre el PC
    g[(a.y + 3) * W + a.x] = GEM               # gema justo abajo
    _, _, d = plan(s, {(a.y + 3) * W + a.x}, hazard=math.inf)
    assert d in (1, 3), "primero se hace a un lado; bajar dejaría caer la roca encima"


def test_enemy_zone_is_avoided_with_infinite_hazard():
    s = empty_sim()
    g = s.grid
    for y in range(1, 21):
        g[y * W + 22] = BUTT if y == 10 else g[y * W + 22]
    g[10 * W + 24] = GEM
    assert plan(s, {10 * W + 24}, hazard=math.inf) is None or plan(s, {10 * W + 24}, hazard=math.inf)[0] > 4
