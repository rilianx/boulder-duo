"""Fin por tiempo: en qué tick terminó cada partida. Si las victorias ocurren siempre en el mismo tick, se
gana por sobrevivir hasta ahí."""
from . import Mecanica


class FinTiempo(Mecanica):
    nombre = "fin_tiempo"
    prioridad = 10
    estado = {"end_ticks": (dict, "I>v")}               # tick → [partidas, victorias]
    neutros = {"time_limit": None}

    def time_limit(self):
        """Tick en que se gana por sobrevivir, si las victorias ocurren siempre en el mismo tick; o None."""
        wins = [int(k) for k, v in self.K.end_ticks.items() for _ in range(v[1])]
        if len(wins) >= 2 and max(wins) - min(wins) <= 2:
            return min(wins)
        return None

    def al_fin(self, st, gano, ctx, **_):
        if st is None or gano is None:
            return
        tick = st.tick + 1
        r = self.K.end_ticks.setdefault(tick, [0, 0]); r[0] += 1; r[1] += int(gano == 1)
        T = self.K.time_limit()
        # ganar por tiempo no dice nada de qué quedaba ni de lo último tocado
        ctx["por_tiempo"] = gano == 1 and T is not None and abs(tick - T) <= 2
