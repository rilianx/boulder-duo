"""Empujar: ¿el objeto se corrió al entrar el avatar a su casilla? Y al empujarlo hacia cada contenido:
[avanzó, se trabó, desapareció, Σ Δpuntaje] (la caja en el hoyo). Lo registra y lo usa el alto nivel
(planificador de empujes)."""
import math
from . import CONF, Mecanica, media, p_mayor, seguro


class Empujar(Mecanica):
    nombre = "empujar"
    estado = {"push": (dict, "I>v"), "push_into": (dict, "I>I>v")}
    neutros = {"pushable": False, "push_candidate": False, "push_ok": False, "push_value": (0.0, 0),
               "plan_empujes": None, "push_vanishes": False}

    def pushable(self, t):
        """¿El avatar corre al tipo t al entrar en su casilla? (una caja de Sokoban)"""
        c = self.K.push.get(t, [0, 0])
        return seguro(c[0], c[1])

    def push_candidate(self, t):
        """¿Vale la pena planear empujes con t? Si ya se sabe empujable, o si alguna vez se pudo pisar su casilla
        y todavía se probó poco empujarlo (curiosidad)."""
        K = self.K
        c = K.push.get(t, [0, 0])
        incierto = 1 - CONF < p_mayor(c[0], c[1]) < CONF    # todavía no se sabe si se empuja
        return K.pushable(t) or (incierto and K.passed.get(t, 0) > 0)

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
        return (r[3] / r[0] if media(r[2], r[0] - r[2]) > 0.5 else 0.0), r[0]

    def push_vanishes(self, t, mask):
        """¿Empujar un t hacia esa máscara lo hace desaparecer? (visto al menos una vez, y casi siempre)"""
        r = self.K.push_into.get(t, {}).get(mask)
        return bool(r and r[2] and media(r[2], r[0] - r[2]) > 0.5)

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
                adelante = masks0[dest] & ~abits
                if K.pushable(t) or any(adelante >> u & 1 and u != t and K.is_blocking(u) for u in range(63)):
                    r[1] += 1             # se trabó: si adelante había algo que bloquea, no dice si t se empuja
                else:
                    p[1] += 1

    # ------------------------------------------------------------------ opción del alto nivel
    def plan_empujes(self, cmd, st):
        """Planificador de empujes con lo aprendido: para cada objeto empujable cercano, búsqueda en anchura
        sobre (casilla del objeto, zona del avatar) hasta empujarlo a una casilla donde empujarlo rinde (o que
        aún no se probó: curiosidad). Devuelve (valor, [(acción, casilla esperada del avatar)]) o None."""
        K, W, H, N = cmd.know, st.W, st.H, len(st.masks)
        p = cmd.nav.risk.grid(st.masks)
        boxes = {}
        quitar = getattr(cmd, "_quitar", {})
        for oid, (t, x, y) in st.objects.items():
            # solo objetos quietos (lo que se mueve solo no es una caja) y en casillas sin riesgo
            # (o, si quitarlo abre algo, con que se haya corrido alguna vez)
            cand = K.push_candidate(t) or (quitar.get(t, 0) > 0 and K.push.get(t, [0])[0] > 0)
            if st.types.get(t, ("", -1))[1] != 6 or not cand or cmd.nav.track.random_type(t):
                continue
            vx, vy = cmd.nav.track.velocity(oid)
            b = int(round(y)) * W + int(round(x))
            if len(cmd.nav.track.hist.get(oid, [])) >= 3 and abs(vx) + abs(vy) < 0.01 and abs(x - round(x)) < 0.05 and abs(y - round(y)) < 0.05 and float(p[b]) < 0.2:
                boxes[b] = t
        if not boxes:
            return None
        blocked = K.blocked_cells(st)
        wall = [blocked[j] or float(p[j]) > 0.3 for j in range(N)]
        for b in boxes:
            wall[b] = True

        def nbrs(i):
            x, y = i % W, i // W
            for d, (dx, dy) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
                if 0 <= x + dx < W and 0 <= y + dy < H:
                    yield d, i + dy * W + dx

        def flood(walls, s):
            lab, k = {}, 0
            for s0 in ([s] if s is not None else range(N)):
                if walls[s0] or s0 in lab:
                    continue
                lab[s0] = k; fr = [s0]
                while fr:
                    i = fr.pop()
                    for _, j in nbrs(i):
                        if not walls[j] and j not in lab:
                            lab[j] = k; fr.append(j)
                k += 1
            return lab

        def path(walls, a, g):
            prev, fr = {a: None}, [a]
            while fr and g not in prev:
                nx = []
                for i in fr:
                    for d, j in nbrs(i):
                        if not walls[j] and j not in prev:
                            prev[j] = (i, d); nx.append(j)
                fr = nx
            if g not in prev:
                return None
            acts = []
            while prev[g] is not None:
                i, d = prev[g]; acts.append((d, g)); g = i
            return acts[::-1]

        reach = flood(wall, st.pos)
        comp_t = {t: K.companeros(t) if quitar.get(t) else set() for t in set(boxes.values())}
        ab = ~cmd._abits()
        lam, best = cmd.P["lam"], None
        for b0, t in boxes.items():
            if not any(j in reach for _, j in nbrs(b0)):
                continue
            walls2 = list(wall); walls2[b0] = False
            comps = {}

            def comp(b):
                if b not in comps:
                    w = list(walls2); w[b] = True
                    comps[b] = flood(w, None)
                return comps[b]
            s0 = (b0, comp(b0).get(st.pos))
            par, fr, n = {s0: None}, [s0], 0
            while fr and n < cmd.P["push_states"]:
                nx = []
                for (b, lab) in fr:
                    n += 1
                    cb = comp(b)
                    for d, dest in nbrs(b):
                        bx, by = b % W - (d == 1) + (d == 3), b // W - (d == 2) + (d == 0)
                        if not (0 <= bx < W and 0 <= by < H):
                            continue
                        behind = by * W + bx
                        m = st.masks[dest] & ab
                        if walls2[behind] or cb.get(behind) != lab:
                            continue
                        # medios y fines: si hacer desaparecer t abre algo valioso, empujarlo adonde desaparece
                        # (visto al empujar, o donde está lo que desaparece junto con él: su hoyo) vale eso
                        bono = quitar.get(t, 0.0)
                        junto = bono > 0 and (self.push_vanishes(t, m) or any(m >> u & 1 for u in comp_t[t]))
                        if not junto and not K.push_ok(t, m):
                            continue
                        v, tries = K.push_value(t, m)
                        if junto and bono > v:
                            v = bono
                        cur = cmd.P["push_new"] / (1 + tries) if v <= 0 and tries < 2 else 0.0
                        steps = 0
                        s, chain = (b, lab), [(behind, d)]
                        while par[s] is not None:
                            s, bh, dd = par[s]; chain.append((bh, dd)); steps += 1
                        # se elige por valor con un costo leve por empuje (un plan largo al hoyo sirve); el
                        # valor devuelto usa el costo de siempre (lam por paso) para compararlo con otras metas
                        key = max(v, cur) - cmd.P["push_lam"] * (steps + 1)
                        if (v > 0 or cur > 0) and (best is None or key > best[3]):
                            best = (max(v, cur) - lam * 3 * (steps + 1), b0, chain[::-1], key)
                        if v > 0:                           # desaparece ahí: no se sigue empujando
                            continue
                        if walls2[dest]:
                            continue
                        ns = (dest, comp(dest).get(b))
                        if ns not in par:
                            par[ns] = ((b, lab), behind, d); nx.append(ns)
                fr = nx
        if best is None or best[3] <= 0:
            return None
        val, b0, chain, _ = best
        walls2 = list(wall); walls2[b0] = False
        a, b, acts = st.pos, b0, []
        for behind, d in chain:
            w = list(walls2); w[b] = True
            seg = path(w, a, behind) if a != behind else []
            if seg is None:
                return None
            acts += seg
            off = (-W, 1, W, -1)[d]
            acts.append((d, b)); a, b = b, b + off
        return val, acts
