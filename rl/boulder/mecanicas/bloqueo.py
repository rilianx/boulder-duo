"""Núcleo — bloqueo: al intentar entrar a una casilla, ¿se movió? Por tipo [pasó, chocó], y también según
cuántos recursos de ese tipo lleva el avatar. Bloquea si chocó más del doble de lo que pasó."""
from . import Mecanica


class Bloqueo(Mecanica):
    nombre = "bloqueo"
    prioridad = 30
    nucleo = True
    # transitabilidad según cuántos recursos de ese mismo tipo lleva el avatar: tipo → cantidad → [pasó, no]
    estado = {"passed": (dict, "I>v"), "blocked": (dict, "I>v"), "by_res": (dict, "I>I>v")}

    def record_move(self, mask, moved, res=None):
        K = self.K
        types = [t for t in range(63) if mask >> t & 1 and t not in K.avatar_types]
        if res:
            for t in types:
                if t in res:
                    pb = K.by_res.setdefault(t, {}).setdefault(res[t], [0, 0])
                    pb[0 if moved else 1] += 1
        if moved:
            for t in types:
                K.passed[t] = K.passed.get(t, 0) + 1
        else:
            suspects = [t for t in types if K.passed.get(t, 0) == 0] or types
            for t in suspects:
                K.blocked[t] = K.blocked.get(t, 0) + 1

    def is_blocking(self, t, res=None):
        """¿Bloquea el tipo t? Si el avatar lleva recursos de ese mismo tipo, se mira lo aprendido con esa
        cantidad exacta (p. ej. un recurso que no se puede recoger más allá de su tope deja de ser pisable).
        Lo que teletransporta se trata como bloqueo al caminar (pisarlo sin querer lleva lejos): solo se entra
        cuando es la meta de la orden."""
        K = self.K
        if sum(K.teleport.get(t, {}).values()) >= 2:
            return True
        if K.avoid_push and K.pushable(t):              # al caminar no se empuja nada sin querer
            return True
        if res is not None:
            n = res.get(t)
            if n is not None:
                pb = K.by_res.get(t, {}).get(n)
                if pb is not None and pb[0] + pb[1] >= 3:
                    return pb[1] > 2 * pb[0] + 1
        return K.blocked.get(t, 0) > 2 * K.passed.get(t, 0) + 1

    def blocking_bits(self, res=None):
        K = self.K
        bm = 0
        for t in set(K.passed) | set(K.blocked):
            if K.is_blocking(t, res):
                bm |= 1 << t
        return bm

    def blocked_cells(self, st):
        bm = self.K.blocking_bits(getattr(st, "res", None))
        return [(m & bm) != 0 for m in st.masks]

    def al_paso(self, d, mask, same, res, moved, fuente, **_):
        K = self.K
        if (moved or same) and K.dir_ok(d):           # si esa dirección no mueve, no es culpa de la casilla
            K.record_move(mask, moved, res if fuente == "nav" else None)
