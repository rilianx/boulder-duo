"""Fin por tiempo: en qué tick terminó cada partida. Si las victorias ocurren siempre en el mismo tick, se
gana por sobrevivir hasta ahí."""
import math
from . import Mecanica


class FinTiempo(Mecanica):
    nombre = "fin_tiempo"
    orden_opcion = 40          # sin metas: ir a la casilla más segura
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

    # ------------------------------------------------------------------ opción del alto nivel
    def opcion(self, cmd, st, info, vals, targets):
        """Se gana por llegar vivo a cierto tick: sin nada mejor que hacer, ir a la casilla alcanzable donde el
        riesgo previsto (cubo del navegador, próximos ticks) más el de llegar es menor."""
        if not cmd.P.get("survive", True) or cmd.know.time_limit() is None:
            return None
        R = getattr(cmd.nav, "_R", None)
        if not R:
            return None
        K = cmd.know
        blocked = K.blocked_cells(st)
        best, choice = math.inf, None
        Hk = min(len(R), 10)
        for j, (t, H) in info.items():
            if blocked[j] or t > Hk:
                continue
            haz = H + sum(-math.log(max(1e-4, 1 - float(R[k][j]))) for k in range(min(t, Hk - 1), Hk))
            sc = haz + 0.01 * t
            if sc < best:
                best, choice = sc, (j, max(t, 1))
        if choice is not None:
            cmd.stats["survive"] = cmd.stats.get("survive", 0) + 1
            if choice[0] == st.pos:
                return None
        return choice
