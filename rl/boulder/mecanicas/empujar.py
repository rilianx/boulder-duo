"""Empujar: ¿el objeto se corrió al entrar el avatar a su casilla? Y al empujarlo hacia cada contenido:
[avanzó, se trabó, desapareció, Σ Δpuntaje] (la caja en el hoyo). Lo registra y lo usa el alto nivel
(planificador de empujes)."""
from . import Mecanica


class Empujar(Mecanica):
    nombre = "empujar"
    estado = {"push": (dict, "I>v"), "push_into": (dict, "I>I>v")}
    neutros = {"pushable": False, "push_candidate": False, "push_ok": False, "push_value": (0.0, 0)}

    def pushable(self, t):
        """¿El avatar corre al tipo t al entrar en su casilla? (una caja de Sokoban)"""
        c = self.K.push.get(t)
        return bool(c) and c[0] >= 2 and c[0] > 0.5 * (c[0] + c[1])

    def push_candidate(self, t):
        """¿Vale la pena planear empujes con t? Si ya se sabe empujable, o si alguna vez se pudo pisar su casilla
        y todavía se probó poco empujarlo (curiosidad)."""
        K = self.K
        c = K.push.get(t, [0, 0])
        return K.pushable(t) or (c[0] + c[1] < 4 and K.passed.get(t, 0) > 0)

    def push_ok(self, t, mask):
        """¿Se puede empujar un t hacia una casilla con esta máscara? Sin datos: si no hay nada que bloquee ni
        otro empujable ahí."""
        K = self.K
        r = K.push_into.get(t, {}).get(mask)
        if r and r[0] + r[1] >= 1:
            return r[0] > r[1]
        return not any(mask >> u & 1 and (K.is_blocking(u) or K.pushable(u)) for u in range(63))

    def push_value(self, t, mask):
        """(valor, veces probado) de empujar un t hacia esa máscara: el puntaje medio si ahí desaparece."""
        r = self.K.push_into.get(t, {}).get(mask)
        if not r or r[0] == 0:
            return 0.0, 0
        return (r[3] / r[0] if r[2] > 0.5 * r[0] else 0.0), r[0]
