"""Teletransporte: el avatar entró a una casilla y apareció a más de 2 casillas. Tipo de entrada → tipo que
había donde apareció; la salida es la más vista."""
import math
from . import Mecanica


class Teletransporte(Mecanica):
    nombre = "teletransporte"
    orden_opcion = 20          # entrar al portal que deja alcanzable lo valioso
    prioridad = 10
    estado = {"teleport": (dict, "I>I>v")}             # tipo de entrada → {tipo en la llegada: veces}
    neutros = {"teleport_exit": None}

    def record_jump(self, entry_mask, landed_mask):
        """El avatar entró a una casilla y apareció lejos: lo que había ahí es un teletransporte."""
        K = self.K
        entry = [t for t in range(63) if entry_mask >> t & 1 and t not in K.avatar_types and t not in K.floor]
        landed = [t for t in range(63) if landed_mask >> t & 1 and t not in K.avatar_types and t not in K.floor]
        for t in entry:
            dd = K.teleport.setdefault(t, {})
            for e in landed:
                dd[e] = dd.get(e, 0) + 1

    def teleport_exit(self, t):
        """Tipo que marca adónde lleva un teletransporte de tipo t (el más visto al llegar), o None."""
        d = self.K.teleport.get(t)
        if not d or sum(d.values()) < 2:
            return None
        return max(d.items(), key=lambda kv: kv[1])[0]

    def al_paso(self, st, mask, salto, **_):
        if salto:                                      # entró y apareció lejos
            self.K.record_jump(mask, st.masks[st.pos])

    # ------------------------------------------------------------------ opción del alto nivel
    def opcion(self, cmd, st, info, vals, targets):
        """Lo valioso no se alcanza caminando, pero sí desde la salida de un teletransporte aprendido: la orden
        es entrar al teletransporte (al aparecer del otro lado viene la orden siguiente)."""
        K, W, N = cmd.know, st.W, len(st.masks)
        blocked = K.blocked_cells(st)
        want = {j for j in range(N) if j not in info and not blocked[j]
                and any(st.masks[j] >> t & 1 and vals.get(t, 0) >= 1.0 for t in targets)}
        if not want:
            return None
        best, choice = math.inf, None
        for p, (t_p, H) in info.items():
            for t in range(63):
                if not st.masks[p] >> t & 1:
                    continue
                e = K.teleport_exit(t)
                if e is None:
                    continue
                for q in range(N):                         # salidas de ese tipo: ¿desde ahí se llega a lo valioso?
                    if not st.masks[q] >> e & 1:
                        continue
                    seen, fr, dq = {q}, [q], None
                    steps = 0
                    while fr and dq is None and steps < N:
                        nx = []
                        for i in fr:
                            if i in want:
                                dq = steps; break
                            x, y = i % W, i // W
                            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                                xx, yy = x + dx, y + dy
                                k = yy * W + xx
                                if 0 <= xx < W and 0 <= yy < st.H and k not in seen and (not blocked[k] or k in want):
                                    seen.add(k); nx.append(k)
                        fr = nx; steps += 1
                    if dq is not None and t_p + dq < best and cmd.tabu.get(p, -1) <= st.tick:
                        best, choice = t_p + dq, (p, t_p)
        if choice is not None:
            cmd.stats["portal"] = cmd.stats.get("portal", 0) + 1
        return choice
