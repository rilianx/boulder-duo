"""Encuentros: qué le pasa a un objeto cuando otra cosa llega a su casilla, o él llega a la de otra. Por par
(a, b): cuántas veces quedaron juntos sin que pasara nada y cuántas veces a desapareció justo cuando b llegó
(una roca que cae sobre una mariposa), con el Δpuntaje de ese tick.

Y la imaginación: un par que casi no se probó es una hipótesis ("¿la roca le hace algo a la mariposa?"). Vale
la pena probarla en proporción a lo que importa b: si b mata, si b bloquea o si b vale. El plan de empujes usa
ese valor como curiosidad dirigida (empujar una caja hacia el enemigo antes que hacia el pasto).
"""
from . import Mecanica, seguro

MATA = 0.2


class Encuentros(Mecanica):
    nombre = "encuentros"
    # enc[a][b] = por lado de b respecto de a (encima, arriba, derecha, abajo, izquierda), 3 números cada uno:
    # [juntos sin pasar nada, a desapareció estando b ahí, Σ Δpuntaje cuando desapareció]
    estado = {"enc": (dict, "I>I>v")}
    neutros = {"mata": False, "valor_encuentro": 0.0, "hipotesis": 1.0, "pruebas_encuentro": 0,
               "lados_que_matan": [], "metas_encuentro": {}}

    def al_transicion(self, antes, ahora):
        K, W, N = self.K, ahora.W, len(ahora.masks)
        if len(antes.masks) != N:
            return
        av = 0
        for t in K.avatar_types:
            av |= 1 << t
        ds = ahora.score - antes.score

        def casilla(x, y):
            c = int(round(y)) * W + int(round(x))
            return c if 0 <= c < N else None

        def tocan(p, q):
            # vecinos o superpuestos (en casillas, con decimales): dentro de un tick uno puede chocar contra el otro
            return abs(p[1] - q[1]) + abs(p[2] - q[2]) < 1.3

        objs = [(i, o) for i, o in antes.objects.items() if o[0] not in K.avatar_types]
        for oid, o in objs:
            t, c = o[0], casilla(o[1], o[2])
            if c is None:
                continue
            o2 = ahora.objects.get(oid)
            # quién está con él: otros objetos superpuestos (antes o ahora) y lo que llegó a su casilla
            cerca = {(p[0], lado(o, p)) for j, p in antes.objects.items() if j != oid and tocan(o, p)}
            if o2 is not None:
                c2 = casilla(o2[1], o2[2])
                if c2 is None:
                    continue
                # contactos que empiezan este tick (cuentan una vez) y no pasó nada
                ya = cerca | {(u, 0) for u in _bits(antes.masks[c])}
                hoy = {(p[0], lado(o2, p)) for j, p in ahora.objects.items() if j != oid and tocan(o2, p)} | \
                    {(u, 0) for u in _bits(ahora.masks[c2])}
                for b, l in hoy - ya:
                    if b != t and b not in K.avatar_types:
                        _fila(K, t, b)[3 * l] += 1
                continue
            # desapareció. Si el avatar estaba ahí, eso es tocar (otra plantilla)
            if ahora.masks[c] & av or antes.masks[c] & av:
                continue
            llego = ahora.masks[c] & ~antes.masks[c]
            sospechosos = cerca | {(u, 0) for u in _bits(llego)}
            for b, l in sospechosos:
                if b == t or b in K.avatar_types:
                    continue
                if (b, l) not in cerca and _cuenta(ahora, b) > _cuenta(antes, b):
                    continue                                 # apareció de la nada ahí: es el producto, no la causa
                r = _fila(K, t, b)
                r[3 * l + 1] += 1; r[3 * l + 2] += ds

    def pruebas_encuentro(self, a, b):
        r = self.K.enc.get(a, {}).get(b)
        return 0 if r is None else sum(r[3 * l] + r[3 * l + 1] for l in range(5))

    def lados_que_matan(self, b, a):
        """Lados (0–4) desde los que b, al llegar o estar ahí, hace desaparecer a a."""
        r = self.K.enc.get(a, {}).get(b)
        if not r:
            return []
        return [l for l in range(5) if r[3 * l + 1] and seguro(r[3 * l + 1], r[3 * l], MATA)]

    def mata(self, b, a):
        """¿b hace desaparecer a a (desde algún lado)?"""
        return bool(self.lados_que_matan(b, a))

    def valor_encuentro(self, b, a):
        """Δpuntaje medio cuando b hizo desaparecer a a (si se sabe que lo hace)."""
        r = self.K.enc.get(a, {}).get(b)
        ls = self.lados_que_matan(b, a)
        k = sum(r[3 * l + 1] for l in ls) if ls else 0
        return sum(r[3 * l + 2] for l in ls) / k if k else 0.0

    def hipotesis(self, b, mask):
        """Peso de la curiosidad por llevar b a una casilla con esta máscara: 1 si no hay nada que imaginar; más si
        ahí hay algo relevante (que mata, que bloquea, que vale) con el que b casi no se encontró."""
        K, w = self.K, 1.0
        for a in _bits(mask):
            if a == b or a in K.avatar_types or a in K.floor:
                continue
            n = self.pruebas_encuentro(a, b) + self.pruebas_encuentro(b, a)
            if n >= 3:
                continue                                     # ya se probó: lo dice lo aprendido, no la imaginación
            ds, dr, _, pd, nt = K.effect(a)
            rel = 1.0 + (1.0 if pd > 0.05 else 0.0) + (1.0 if K.is_blocking(a) else 0.0) + \
                (1.0 if ds > 0 or dr > 0 else 0.0)
            w = max(w, rel / (1 + n))
        return w

    # ------------------------------------------------------------------ medio: dejar caer
    def metas_encuentro(self, cmd, st, info):
        """{casilla: valor}: dejar caer algo sobre otra cosa. Un objeto quieto que siempre se mueve en una dirección
        (una roca que cae) y que tiene, en esa línea y tras una sola casilla que lo sostiene, a un objeto b con
        camino libre entre ambos: ir a esa casilla (cavarla) lo suelta y cae sobre b. Vale lo que rinde el
        encuentro si se sabe que mata desde ese lado; si casi no se probó y b importa, vale como curiosidad
        (imaginar: "¿la roca le hace algo a la mariposa?")."""
        K, W, H, N = self.K, st.W, st.H, len(st.masks)
        if not st.objects:
            return {}
        track = cmd.nav.track
        blocked = K.blocked_cells(st)
        donde = {}
        for oid, (t, x, y) in st.objects.items():
            donde.setdefault(int(round(y)) * W + int(round(x)), []).append(t)
        out = {}
        for oid, (t, x, y) in st.objects.items():
            d = track.main_dir(t)
            if d is None or abs(x - round(x)) > 0.05 or abs(y - round(y)) > 0.05:
                continue
            vx, vy = track.velocity(oid)
            if abs(vx) + abs(vy) > 0.01:
                continue                                     # ya se está moviendo
            lad = {(0, 1): 1, (0, -1): 3, (1, 0): 4, (-1, 0): 2}.get(tuple(d))
            if lad is None:
                continue
            xx, yy = int(round(x)) + d[0], int(round(y)) + d[1]
            if not (0 <= xx < W and 0 <= yy < H):
                continue
            r = yy * W + xx                                  # lo que lo sostiene: ahí hay que ir
            if r not in info or r == st.pos or donde.get(r):
                continue
            for k in range(1, 5):                            # la línea de caída, hasta 4 casillas
                cx, cy = xx + k * d[0], yy + k * d[1]
                if not (0 <= cx < W and 0 <= cy < H):
                    break
                c = cy * W + cx
                hay = [b for b in donde.get(c, []) if b != t and b not in K.avatar_types]
                if hay:
                    for b in hay:
                        v = self._valor_caer(t, b, lad, st)
                        if v > out.get(r, 0.0):
                            out[r] = v
                    break
                if blocked[c] or st.masks[c] & ~(1 << t) & K.blocking_bits(getattr(st, "res", None)):
                    break
        if out:
            cmd.stats["caer"] = cmd.stats.get("caer", 0) + 1
        return out

    def _valor_caer(self, t, b, lad, st):
        K = self.K
        r = K.enc.get(b, {}).get(t)
        if lad in self.lados_que_matan(t, b):
            return r[3 * lad + 2] / r[3 * lad + 1] if r[3 * lad + 1] else 0.0
        n = r[3 * lad] + r[3 * lad + 1] if r else 0
        if n >= 3:
            return 0.0                                       # ya se probó desde ese lado y no mata
        ds, dr, _, pd, _ = K.effect(b)
        rel = (1.0 if pd > 0.05 else 0.0) + (1.0 if K.is_blocking(b) else 0.0) + (1.0 if ds > 0 or dr > 0 else 0.0)
        return rel / (1 + n)                                 # imaginar: probarlo vale según cuánto importa b


def lado(a, b):
    """0 = superpuestos, 1 = b arriba de a, 2 = a la derecha, 3 = abajo, 4 = a la izquierda."""
    dx, dy = b[1] - a[1], b[2] - a[2]
    if abs(dx) < 0.5 and abs(dy) < 0.5:
        return 0
    if abs(dy) >= abs(dx):
        return 1 if dy < 0 else 3
    return 2 if dx > 0 else 4


def _fila(K, a, b):
    return K.enc.setdefault(a, {}).setdefault(b, [0, 0, 0.0] * 5)


def _bits(m):
    while m:
        b = m & -m
        yield b.bit_length() - 1
        m ^= b


def _cuenta(st, t):
    return sum(1 for m in st.masks if m >> t & 1)
