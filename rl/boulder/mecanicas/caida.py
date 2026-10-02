"""Regla de caída: si un tipo avanza o no según lo que tiene adelante (una roca cae si abajo queda vacío).
tipo → {máscara de la casilla de adelante: [avanzó, no]}. La llena el rastreador de objetos."""
from . import Mecanica


class Caida(Mecanica):
    nombre = "caida"
    estado = {"fall": (dict, "I>I>v")}
    neutros = {"p_move_into": 0.0}

    def p_move_into(self, t, mask):
        """P(un objeto de tipo t avanza hacia una casilla con esta máscara), aprendido; sin datos: 0."""
        r = self.K.fall.get(t, {}).get(mask)
        return r[0] / (r[0] + r[1]) if r and r[0] + r[1] >= 3 else 0.0
