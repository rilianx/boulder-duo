"""Núcleo — efectos de tocar: por tipo, Δpuntaje, Δrecursos, cambio de avatar y muertes; y qué toques
terminaron la partida (con qué tipo de avatar y recursos), de donde sale P(ganar al tocar)."""
from . import Mecanica


class EfectoToque(Mecanica):
    nombre = "toque"
    prioridad = 45
    nucleo = True
    # eff: tipo → [n, Σ Δpuntaje, Σ Δrecursos, cambios de avatar, muertes];
    # term: tipo → {"tipo de avatar|recursos": [toques, victorias]}
    estado = {"eff": (dict, "I>v"), "term": (dict, "I>S>v")}

    def _e(self, t):
        return self.K.eff.setdefault(t, [0, 0.0, 0.0, 0, 0])

    def record_touch(self, types, dscore, dres, datype):
        for t in types:
            e = self._e(t)
            e[0] += 1; e[1] += dscore; e[2] += dres; e[3] += int(datype)

    def record_terminal_touch(self, types, atype, res, won):
        for t in types:
            k = f"{atype}|{res}"
            d = self.K.term.setdefault(t, {}).setdefault(k, [0, 0])
            d[0] += 1; d[1] += int(won)
            if not won:
                self._e(t)[4] += 1

    def record_nonterminal(self, types, atype, res):
        for t in types:
            d = self.K.term.setdefault(t, {}).setdefault(f"{atype}|{res}", [0, 0])
            d[0] += 1

    def p_win(self, t, atype, res):
        """P(ganar al tocar t | tipo de avatar, recursos): umbral de recursos aprendido de las victorias."""
        d = self.K.term.get(t)
        if not d:
            return 0.0
        rows = [(int(k.split("|")[1]), v) for k, v in d.items() if int(k.split("|")[0]) == atype]
        wins = [r for r, v in rows if v[1] > 0]
        if not wins or res < min(wins):
            return 0.0
        lo = min(wins)
        tot = sum(v[0] for r, v in rows if lo <= r <= res)
        w = sum(v[1] for r, v in rows if lo <= r <= res)
        return w / max(tot, 1)

    def novelty(self, t, atype, res):
        """Veces que se tocó t con este tipo de avatar y estos recursos (para la curiosidad)."""
        return self.K.term.get(t, {}).get(f"{atype}|{res}", [0, 0])[0]

    def effect(self, t):
        e = self.K.eff.get(t)
        if not e or e[0] == 0:
            return 0.0, 0.0, 0.0, 0.0, 0
        n = e[0]
        # la muerte al tocar depende sobre todo del entorno (eso lo ve el predictor): previo fuerte hacia 0
        return e[1] / n, e[2] / n, e[3] / n, e[4] / (n + 10), n

    def al_paso(self, st, mask, same, moved, fuente, **_):
        K = self.K
        if fuente == "explorador" and not moved and same:   # chocar también es probar: agota la curiosidad
            bumped = [t for t in range(63) if mask >> t & 1 and t not in K.avatar_types and t not in K.floor]
            K.record_nonterminal(bumped, st.atype, st.total_res())

    def al_toque(self, types, entro, dscore, dres, datype, at0, res0, fuente, **_):
        K = self.K
        if entro:                                      # solo si de verdad entró (no si solo giró)
            if types:
                K.record_touch(types, dscore, dres, datype)
                K.record_nonterminal(types, at0, res0)
        elif fuente == "cmd" and types:
            K.record_nonterminal(types, at0, res0)     # chocó: tocarlo tampoco terminó nada

    def al_fin(self, gano, tocado, ctx, **_):
        if tocado is not None and gano is not None and not ctx.get("por_tiempo"):
            types, atype, res = tocado
            if types:
                self.K.record_terminal_touch(types, atype, res, gano == 1)   # ganó o perdió al tocarlo
