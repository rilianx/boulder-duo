"""Arrastre: quieto encima de un tipo, ¿el avatar se movió igual? (el tronco que lleva en Frogs)."""
from . import Mecanica


class Arrastre(Mecanica):
    nombre = "arrastre"
    estado = {"carry": (dict, "I>v")}                  # tipo bajo el avatar quieto → [lo movió, no]
    neutros = {"carriers": set()}

    def record_carry(self, types, moved):
        for t in types:
            c = self.K.carry.setdefault(t, [0, 0])
            c[0 if moved else 1] += 1

    def carriers(self):
        """Tipos de objeto que arrastran al avatar que está quieto encima (p. ej. un tronco en un río)."""
        return {t for t, (a, b) in self.K.carry.items() if a + b >= 5 and a > 0.5 * (a + b)}
