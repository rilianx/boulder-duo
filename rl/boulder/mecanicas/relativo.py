"""Movimiento relativo: si los movimientos de un tipo lo acercan o alejan del avatar (−1) o de la instancia
más cercana de otro tipo. tipo → {objetivo: [se acercó, se alejó]}. La llena el rastreador de objetos; el cubo
la usa para predecir perseguidores y fugitivos del avatar."""
from . import Mecanica, media, seguro


class MovimientoRelativo(Mecanica):
    nombre = "relativo"
    prioridad = 20
    estado = {"rel": (dict, "I>I>v")}
    neutros = {"attractor": None}

    def attractor(self, t):
        """(objetivo, signo, fracción) si los movimientos del tipo t casi siempre lo acercan (+1) o alejan (−1) de algo:
        objetivo −1 = avatar, u = tipo u. None si no hay una tendencia clara."""
        best = None
        for u, (c, f) in self.K.rel.get(t, {}).items():
            for sign, k, o in ((1, c, f), (-1, f, c)):
                if seguro(k, o, 0.7):                  # casi siempre lo acerca (o lo aleja)
                    q = media(k, o)
                    if best is None or q > best[2]:
                        best = (u, sign, q)
        return best                                          # (objetivo, signo, fracción explicada)

    def al_objeto_movio(self, st, t, px, py, x, y, tracker, **_):
        """¿El movimiento acercó o alejó al objeto del avatar y de la instancia más cercana de cada tipo?"""
        targets = {}
        if tracker._apos is not None:
            targets[-1] = [tracker._apos]
        for u, c in tracker._type_cells(st).items():
            if u != t:
                targets[u] = c
        for u, cells in targets.items():
            d0 = min(abs(px - cx) + abs(py - cy) for cx, cy in cells)
            d1 = min(abs(x - cx) + abs(y - cy) for cx, cy in cells)
            if abs(d1 - d0) < 1e-6 or d0 == 0:
                continue
            r = self.K.rel.setdefault(t, {}).setdefault(u, [0, 0])
            r[0 if d1 < d0 else 1] += 1
