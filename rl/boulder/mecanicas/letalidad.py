"""Letalidad contada: fracción de toques de un tipo que terminaron en derrota. Si es ≥ 50 % (con ≥ 3
muertes), es un piso para el riesgo de su casilla (lo aplica cube.KnownRisk). Usa lo que cuenta `toque`."""
from . import Mecanica


class Letalidad(Mecanica):
    nombre = "letalidad"
    neutros = {"lethality": 0.0}

    def lethality(self, t):
        """Fracción de veces que tocar t terminó en derrota (contado, no estimado): 0 con pocos datos."""
        e = self.K.eff.get(t)
        if not e or e[4] < 3:
            return 0.0
        return e[4] / (e[4] + e[0])
