"""Fin por tiempo: en qué tick terminó cada partida. Si las victorias ocurren siempre en el mismo tick, se
gana por sobrevivir hasta ahí."""
from . import Mecanica


class FinTiempo(Mecanica):
    nombre = "fin_tiempo"
    estado = {"end_ticks": (dict, "I>v")}               # tick → [partidas, victorias]
    neutros = {"time_limit": None}

    def time_limit(self):
        """Tick en que se gana por sobrevivir, si las victorias ocurren siempre en el mismo tick; o None."""
        wins = [int(k) for k, v in self.K.end_ticks.items() for _ in range(v[1])]
        if len(wins) >= 2 and max(wins) - min(wins) <= 2:
            return min(wins)
        return None
