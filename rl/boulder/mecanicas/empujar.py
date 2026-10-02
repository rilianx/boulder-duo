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

    def al_empuje(self, st, pos0, act, objs, masks0, sc0, turned, abits):
        """Tras un paso: ¿el objeto que había en la casilla a la que entró el avatar se corrió en esa dirección,
        desapareció (p. ej. cayó en un hoyo) o se trabó? Se anota según qué había adelante."""
        K, W = self.K, st.W
        off = (-W, 1, W, -1)[act]
        c, dest = pos0 + off, pos0 + 2 * off
        dx, dy = (0, 1, 0, -1)[act], (-1, 0, 1, 0)[act]
        x2, y2 = pos0 % W + 2 * dx, pos0 // W + 2 * dy
        if not (0 <= x2 < W and 0 <= y2 < st.H):
            return
        for oid, (t, cell) in objs.items():
            if cell != c:
                continue
            p = K.push.setdefault(t, [0, 0])
            r = K.push_into.setdefault(t, {}).setdefault(masks0[dest] & ~abits, [0, 0, 0, 0.0])
            if st.pos == c:
                o = st.objects.get(oid)
                if o is None:
                    # desapareció: si ya se lo vio correrse es "lo empujé y cayó" (la caja en el hoyo); si no,
                    # es que se consume al tocarlo (la miel), y eso no es empujar
                    if K.pushable(t):
                        p[0] += 1; r[0] += 1; r[2] += 1; r[3] += st.score - sc0
                elif int(round(o[2])) * W + int(round(o[1])) == dest:
                    p[0] += 1; r[0] += 1; r[3] += st.score - sc0
                else:
                    p[1] += 1
            elif not turned:
                if K.pushable(t):
                    r[1] += 1                                     # empujable, pero ahí se traba
                else:
                    p[1] += 1
