"""Direcciones que mueven: por dirección (arriba, derecha, abajo, izquierda), [se movió, intentos hacia una
casilla libre]. Una dirección que casi nunca mueve (una nave que solo va de lado) deja de usarse."""
from . import Mecanica


class Direcciones(Mecanica):
    nombre = "direcciones"
    estado = {"dir_moves": (lambda: [[0, 0], [0, 0], [0, 0], [0, 0]], "lists")}
    neutros = {"dir_ok": True}

    def record_dir(self, d, moved):
        r = self.K.dir_moves[d]; r[0] += int(moved); r[1] += 1

    def dir_ok(self, d):
        """¿Moverse en la dirección d mueve al avatar? False si se intentó bastante y casi nunca funcionó."""
        m, n = self.K.dir_moves[d]
        return not (n >= 15 and m <= 0.05 * n)
