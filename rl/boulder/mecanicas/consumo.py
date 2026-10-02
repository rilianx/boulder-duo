"""Se consume al pisar: ¿el tipo seguía en la casilla después de pisarla? (la tierra, los diamantes)."""
from . import Mecanica


class Consumo(Mecanica):
    nombre = "consumo"
    estado = {"consumed": (dict, "I>v")}               # tipo → [desapareció, quedó]
    neutros = {"is_consumed": False}

    def is_consumed(self, t):
        """¿El tipo desaparece cuando el avatar lo pisa? (tierra, diamantes...)"""
        c = self.K.consumed.get(t)
        return bool(c) and c[0] + c[1] >= 3 and c[0] > 0.5 * (c[0] + c[1])
