"""Movimiento relativo: si los movimientos de un tipo lo acercan o alejan del avatar (−1) o de la instancia
más cercana de otro tipo. tipo → {objetivo: [se acercó, se alejó]}. La llena el rastreador de objetos; el cubo
la usa para predecir perseguidores y fugitivos del avatar."""
from . import Mecanica


class MovimientoRelativo(Mecanica):
    nombre = "relativo"
    estado = {"rel": (dict, "I>I>v")}
    neutros = {"attractor": None}

    def attractor(self, t):
        """(objetivo, signo, fracción) si los movimientos del tipo t casi siempre lo acercan (+1) o alejan (−1) de algo:
        objetivo −1 = avatar, u = tipo u. None si no hay una tendencia clara."""
        best = None
        for u, (c, f) in self.K.rel.get(t, {}).items():
            n = c + f
            if n < 10:
                continue
            for sign, k in ((1, c), (-1, f)):
                q = k / n
                if q >= 0.75 and (best is None or q > best[2]):
                    best = (u, sign, q)
        return best                                          # (objetivo, signo, fracción explicada)
