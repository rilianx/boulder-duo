"""Usar (disparar, espada): qué desaparece cerca del avatar al usar y al no usar, por posición relativa
("a|dx|dy"), según hacia dónde mira ("f|dx|dy") y por tipo de avatar ("t<tipo>|..."); y cuánto puntaje da cada
tipo eliminado (medido en el tick exacto). Lo registra el alto nivel (sondas de usar / no usar)."""
from . import Mecanica


class Usar(Mecanica):
    nombre = "usar"
    estado = {"use_kill": (dict, "I>S>v"), "use_base": (dict, "I>S>v"), "use_score": (dict, "I>v")}
    neutros = {"use_lift": 0.0, "use_value": 0.0}

    def use_lift(self, t, key):
        """Cuánto más probable es que un objeto de tipo t en esa posición relativa desaparezca si se usa (vs. no)."""
        K = self.K
        u = K.use_kill.get(t, {}).get(key); b = K.use_base.get(t, {}).get(key)
        if not u or u[1] < 3:
            return 0.0
        pu = u[0] / u[1]
        pb = b[0] / b[1] if b and b[1] >= 3 else 0.0
        return max(0.0, pu - pb)

    def use_value(self, t):
        """Puntaje medio que da cada objeto de tipo t eliminado al usar (0,5 de curiosidad si hay pocos datos)."""
        v = self.K.use_score.get(t)
        return v[0] / v[1] if v and v[1] >= 3 else 0.5
