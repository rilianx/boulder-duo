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

    FWD = {0: ((0, -1), (1, 0)), 1: ((1, 0), (0, 1)), 2: ((0, 1), (-1, 0)), 3: ((-1, 0), (0, -1))}

    def claves_usar(self, dx, dy, facing, atype=None):
        ks = [f"a|{dx}|{dy}"]
        if facing is not None:
            (fx, fy), (rx, ry) = self.FWD[facing]
            ks.append(f"f|{dx * rx + dy * ry}|{dx * fx + dy * fy}")
        if atype is not None:                             # además, según el tipo de avatar (una nave blanca
            ks += [f"t{atype}|{k}" for k in ks]           # no mata aliens negros)
        return ks

    def efecto_usar(self, t, dx, dy, facing, atype):
        """Efecto de usar sobre t: el específico del tipo de avatar si hay datos, si no el general."""
        K, best = self.K, 0.0
        for k in K.claves_usar(dx, dy, facing):
            sk = f"t{atype}|{k}"
            u = K.use_kill.get(t, {}).get(sk)
            best = max(best, K.use_lift(t, sk) if u and u[1] >= 3 else K.use_lift(t, k))
        return best

    def al_sonda_usar(self, st, used, ax, ay, facing, snap, atype, vanish_ds):
        """Una sonda resuelta: qué de lo que había cerca desapareció (usando o no) y cuánto puntaje dio."""
        K = self.K
        table = K.use_kill if used else K.use_base
        killed = []
        for oid, (t, x, y) in snap.items():
            gone = oid not in st.objects
            for key in K.claves_usar(int(round(x - ax)), int(round(y - ay)), facing, atype):
                r = table.setdefault(t, {}).setdefault(key, [0, 0])
                r[0] += gone; r[1] += 1
            if gone:
                killed.append((oid, t, K.efecto_usar(t, int(round(x - ax)), int(round(y - ay)), facing, atype)))
        if used and killed:
            # puntaje del tick exacto en que desapareció cada uno (no de toda la ventana: ahí caen también
            # los −1 de lo que llegó a una ciudad), y solo de los que estaban donde usar sí afecta
            for oid, t, key_lift in killed:
                if key_lift < 0.5 or oid not in vanish_ds:
                    continue
                v = K.use_score.setdefault(t, [0.0, 0]); v[0] += vanish_ds[oid]; v[1] += 1
