"""La simulación en Python debe reproducir tick a tick la de index.html.

Las trazas de referencia salen del juego real: `node rl/tests/gen_js_traces.cjs`.
"""
import json
from pathlib import Path

import pytest

from boulder.sim import Sim, W

TRACES = json.loads((Path(__file__).parent / "fixtures" / "js_traces.json").read_text())


@pytest.mark.parametrize("tr", TRACES, ids=[f"nivel{t['level']}" for t in TRACES])
def test_same_ticks_as_js(tr):
    sim = Sim()
    sim.init_level(tr["level"])
    assert sim.snapshot_hash() == tr["hashes"][0], "el nivel generado difiere del de JS"
    for k, a in enumerate(tr["actions"]):
        sim.tick(a)
        assert sim.snapshot_hash() == tr["hashes"][k + 1], f"diverge en el tick {k + 1} (acción {a})"
    fin = tr["final"]
    assert list(sim.grid) == [int(v) for v in fin["grid"].split(",")]
    ag = sim.agent
    assert (ag.x, ag.y, ag.gems, ag.alive) == (fin["agent"]["x"], fin["agent"]["y"], fin["agent"]["gems"], fin["agent"]["alive"])
    assert sim.time_left == fin["timeLeft"]


def test_traces_exercise_the_physics():
    """Las trazas deben cubrir caídas, gemas y (al menos una) muerte, o la paridad no prueba mucho."""
    deaths = gems = 0
    for tr in TRACES:
        sim = Sim()
        sim.init_level(tr["level"])
        for a in tr["actions"]:
            ev = sim.tick(a)
            deaths += ev.count("death")
            gems += ev.count("gem")
    assert gems > 10
    assert deaths >= 1
