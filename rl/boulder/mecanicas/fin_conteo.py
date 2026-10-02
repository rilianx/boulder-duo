"""Fin por conteo: cuántos objetos de cada tipo quedaban al ganar, al perder y a mitad de partida. Un tipo
casi siempre extinto al ganar (o al perder) y no a mitad de partida es la condición de victoria (o derrota)."""
from . import Mecanica


class FinConteo(Mecanica):
    nombre = "fin_conteo"
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

    def _frac(self, kind, t):
        r = self.K.ends.get(kind, {}).get(t)
        return (r[0] / r[1], r[1]) if r and r[1] else (None, 0)

    def extinct_win(self, t):
        """¿Se gana cuando no queda ningún t? (al ganar casi siempre quedaban 0–1, a mitad de partida no)"""
        fw, nw = self._frac("win", t); fm, nm = self._frac("mid", t)
        return nw >= 3 and nm >= 5 and fw >= 0.8 and fw - fm >= 0.5

    def extinct_loss(self, t):
        """¿Se pierde cuando no queda ningún t? (las ciudades de Missilecommand)"""
        if t in self.K.avatar_types:
            return False
        fl, nl = self._frac("loss", t); fm, nm = self._frac("mid", t); fw, nw = self._frac("win", t)
        # contraste: mucho más seguido extinto al perder que a mitad de partida (y no al ganar)
        return nl >= 3 and nm >= 5 and fl >= 0.6 and fl - fm >= 0.25 and (fw is None or fw <= 0.3)
