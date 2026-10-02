"""Giro: al cambiar de dirección, ¿se movió o solo giró? Si casi siempre solo gira, girar cuesta un tick."""
from . import Mecanica, seguro


class Giro(Mecanica):
    nombre = "giro"
    prioridad = 40
    estado = {"turns": (lambda: [0, 0], "v")}          # [se movió, solo giró]
    neutros = {"turn_cost_value": 0}

    def record_turn(self, moved):
        """Intento de moverse cambiando de dirección hacia una casilla pisable: ¿se movió o solo giró?"""
        self.K.turns[0 if moved else 1] += 1

    def turn_cost_value(self):
        """1 si el avatar gasta un tick en girar antes de moverse en otra dirección (aprendido)."""
        return int(seguro(self.K.turns[1], self.K.turns[0]))

    def al_paso(self, same, free, moved, fuente, **_):
        if fuente == "nav" and not same and free:
            self.K.record_turn(moved)
