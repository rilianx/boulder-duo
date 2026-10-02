"""Teletransporte: el avatar entró a una casilla y apareció a más de 2 casillas. Tipo de entrada → tipo que
había donde apareció; la salida es la más vista."""
from . import Mecanica


class Teletransporte(Mecanica):
    nombre = "teletransporte"
    estado = {"teleport": (dict, "I>I>v")}             # tipo de entrada → {tipo en la llegada: veces}
    neutros = {"teleport_exit": None}

    def record_jump(self, entry_mask, landed_mask):
        """El avatar entró a una casilla y apareció lejos: lo que había ahí es un teletransporte."""
        K = self.K
        entry = [t for t in range(63) if entry_mask >> t & 1 and t not in K.avatar_types and t not in K.floor]
        landed = [t for t in range(63) if landed_mask >> t & 1 and t not in K.avatar_types and t not in K.floor]
        for t in entry:
            dd = K.teleport.setdefault(t, {})
            for e in landed:
                dd[e] = dd.get(e, 0) + 1

    def teleport_exit(self, t):
        """Tipo que marca adónde lleva un teletransporte de tipo t (el más visto al llegar), o None."""
        d = self.K.teleport.get(t)
        if not d or sum(d.values()) < 2:
            return None
        return max(d.items(), key=lambda kv: kv[1])[0]
