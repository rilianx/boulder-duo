"""Fin por conteo: cuántos objetos de cada tipo quedaban al ganar, al perder y a mitad de partida. Un tipo
casi siempre extinto al ganar (o al perder) y no a mitad de partida es la condición de victoria (o derrota)."""
from . import Mecanica, conteos, seguro


class FinConteo(Mecanica):
    nombre = "fin_conteo"
    prioridad = 20
    # ends: {"win"|"loss"|"mid": {tipo: [veces con ≤ 1, total]}}
    estado = {"ends": (lambda: {"win": {}, "loss": {}, "mid": {}}, "S>I>v")}
    neutros = {"extinct_win": False, "extinct_loss": False}

    def despues_de_cargar(self):
        for kind in ("win", "loss", "mid"):
            self.K.ends.setdefault(kind, {})

    def record_counts(self, kind, counts):
        """counts = {tipo: cuántas casillas lo tienen}; kind = "win", "loss" o "mid"."""
        d = self.K.ends.setdefault(kind, {})
        for t, n in counts.items():
            r = d.setdefault(t, [0, 0]); r[0] += int(n <= 1); r[1] += 1

    def _km(self, kind, t):
        r = self.K.ends.get(kind, {}).get(t, [0, 0])
        return r[0], r[1] - r[0]                        # (veces extinto, veces no)

    def extinct_win(self, t):
        """¿Se gana cuando no queda ningún t? (al ganar casi seguro extinto; a mitad de partida casi seguro no)"""
        kw, mw = self._km("win", t); km, mm = self._km("mid", t)
        return seguro(kw, mw) and seguro(mm, km)

    def extinct_loss(self, t):
        """¿Se pierde cuando no queda ningún t? (las ciudades de Missilecommand)"""
        if t in self.K.avatar_types:
            return False
        kl, ml = self._km("loss", t); km, mm = self._km("mid", t); kw, mw = self._km("win", t)
        # al perder casi seguro extinto, a mitad de partida casi seguro no, y al ganar no
        return seguro(kl, ml) and seguro(mm, km) and not seguro(kw, mw)

    def al_mitad(self, st):
        self.K.record_counts("mid", conteos(st))

    def al_fin(self, st, gano, ctx, **_):
        if st is not None and gano is not None and not ctx.get("por_tiempo"):
            self.K.record_counts("win" if gano == 1 else "loss", conteos(st))
