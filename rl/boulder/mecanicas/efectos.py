"""Efectos causales: qué hace desaparecer a qué. Cada tick se comparan los conteos de cada tipo con los del tick
anterior. Si siempre que desaparece un X desaparece también algún Y (y Y casi nunca desaparece por su cuenta),
se aprende "X desaparece → Y desaparece" (la caja 0 cae en el hoyo 0 → se abren todas las puertas 0). Lo mismo
con "el avatar tocó X → Y desaparece" (una palanca, una llave).

La estrategia (medios y fines): si lo valioso no se alcanza porque lo tapa un tipo D, y D desaparece cuando
desaparece (o se toca) C, entonces hacer desaparecer C vale lo que vale lo tapado. Ese valor lo usan el plan de
empujes (empujar C hacia donde desaparece) y la elección de metas (tocar C).
"""
from . import Mecanica, conteos, media, seguro


def observar(agente, K, st):
    """Lo llama cada agente que aprende, una vez por tick: emite "conteos" con lo que cambió desde el tick
    anterior y los tipos de la casilla a la que entró el avatar."""
    ahora, prev = conteos(st), getattr(agente, "_prev_cnt", None)
    if prev is not None:
        pm, pp = prev[1], prev[2]
        tocado = [t for t in range(63) if pm[st.pos] >> t & 1 and t not in K.avatar_types] \
            if st.pos != pp and len(pm) == len(st.masks) else []
        K.emitir("conteos", antes=prev[0], ahora=ahora, tocado=tocado)
    agente._prev_cnt = (ahora, list(st.masks), st.pos)


class Efectos(Mecanica):
    nombre = "efectos"
    # co[x][y]: ticks en que desaparecieron x e y a la vez; ven[x]: ticks en que desapareció x;
    # toco[k][y] / tocados[k]: lo mismo con "el avatar entró a una casilla con k"; ticks: ticks observados
    estado = {"co": (dict, "I>I>v"), "ven": (dict, "I>v"), "toco": (dict, "I>I>v"), "tocados": (dict, "I>v"),
              "ticks": (lambda: [0], "v")}
    neutros = {"causas_de": [], "bonos_causales": ({}, {}), "companeros": set()}

    def al_conteos(self, antes, ahora, tocado):
        K = self.K
        K.ticks[0] += 1
        fue = [t for t, n in antes.items() if ahora.get(t, 0) < n and t not in K.avatar_types]
        for x in fue:
            K.ven[x] = K.ven.get(x, 0) + 1
            for y in fue:
                if y != x:
                    d = K.co.setdefault(x, {}); d[y] = d.get(y, 0) + 1
        for k in tocado:
            K.tocados[k] = K.tocados.get(k, 0) + 1
            for y in fue:
                if y != k:
                    d = K.toco.setdefault(k, {}); d[y] = d.get(y, 0) + 1

    def _raro(self, y):
        """¿y casi nunca desaparece por su cuenta? (si no, cualquier co-desaparición es casualidad)"""
        K = self.K
        n = K.ven.get(y, 0)
        return media(n, K.ticks[0] - n) < 0.05

    def companeros(self, c):
        """Tipos que desaparecen junto con c (casi siempre que c desaparece): la caja y su hoyo."""
        K = self.K
        n = K.ven.get(c, 0)
        return {y for y, k in K.co.get(c, {}).items() if seguro(k, n - k)}

    def causas_de(self, d):
        """[(c, "desaparece" | "tocar")]: lo que, al desaparecer o al tocarlo, hace desaparecer al tipo d."""
        K = self.K
        if not self._raro(d):
            return []
        out = []
        for c, ys in K.co.items():
            k = ys.get(d, 0)
            if k and seguro(k, K.ven.get(c, 0) - k):
                out.append((c, "desaparece"))
        for c, ys in K.toco.items():
            k = ys.get(d, 0)
            if k and seguro(k, K.tocados.get(c, 0) - k):
                out.append((c, "tocar"))
        return out

    def bonos_causales(self, cmd, st, info, vals, targets):
        """({tipo: valor de hacerlo desaparecer}, {tipo: valor de tocarlo}). Medios y fines hacia atrás: para
        cada tipo D que bloquea y que se sabe quitar, se mira qué se alcanzaría sin él; si ahí hay algo valioso,
        sus causas valen eso. Y si lo que se alcanza sin D deja ver otro bloqueo quitable D2, se encadena (abrir
        D para después abrir D2...), con un descuento por paso."""
        K, W, H, N = self.K, st.W, st.H, len(st.masks)
        blocked = K.blocked_cells(st)
        want = {j for j in range(N) if j not in info and not blocked[j]
                and any(st.masks[j] >> t & 1 and vals.get(t, 0) >= 1.0 for t in targets)}
        bm = K.blocking_bits(getattr(st, "res", None))
        presentes = {t for m in st.masks for t in range(63) if m >> t & 1}
        quitables = {}
        for d in presentes:
            if bm >> d & 1:
                c = K.causas_de(d)
                if c:
                    quitables[d] = c
        if not quitables:
            return {}, {}

        def alcance(abiertos):
            pared = bm
            for d in abiertos:
                pared &= ~(1 << d)
            seen, fr = {st.pos}, [st.pos]
            while fr:
                i = fr.pop()
                x, y = i % W, i // W
                for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                    xx, yy = x + dx, y + dy
                    j = yy * W + xx
                    if 0 <= xx < W and 0 <= yy < H and j not in seen and not (st.masks[j] & pared):
                        seen.add(j); fr.append(j)
            return seen

        memo = {}

        def valor(abiertos, prof):
            if abiertos in memo:
                return memo[abiertos]
            seen = alcance(abiertos)
            v = max((vals.get(t, 0) for i in seen & want for t in targets if st.masks[i] >> t & 1), default=0.0)
            if any(i not in info and i not in cmd.visits for i in seen):
                v = max(v, cmd.P.get("abrir", 1.0))       # abre terreno nunca pisado: curiosidad
            if prof < 3:
                for d2 in quitables:
                    if d2 not in abiertos:
                        v = max(v, 0.9 * valor(abiertos | {d2}, prof + 1))
            memo[abiertos] = v
            return v

        base = len(alcance(frozenset()))
        quitar, tocar = {}, {}
        for d, causas in quitables.items():
            if len(alcance(frozenset([d]))) <= base:
                continue                                    # quitar D no abre nada (no es el obstáculo)
            mejor = valor(frozenset([d]), 1)
            if mejor <= 0:
                continue
            for c, como in causas:
                dest = quitar if como == "desaparece" else tocar
                dest[c] = max(dest.get(c, 0.0), mejor)
        if quitar or tocar:
            cmd.stats["causal"] = cmd.stats.get("causal", 0) + 1
        return quitar, tocar
