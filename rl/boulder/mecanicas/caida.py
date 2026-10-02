"""Regla de caída: si un tipo avanza o no según lo que tiene adelante (una roca cae si abajo queda vacío).
tipo → {máscara de la casilla de adelante: [avanzó, no]}. La llena el rastreador de objetos."""
import heapq
import math
from . import Mecanica


class Caida(Mecanica):
    nombre = "caida"
    orden_opcion = 30          # abrir camino: liberar un objeto que cae para que se corra
    estado = {"fall": (dict, "I>I>v")}
    neutros = {"p_move_into": 0.0}

    def p_move_into(self, t, mask):
        """P(un objeto de tipo t avanza hacia una casilla con esta máscara), aprendido; sin datos: 0."""
        r = self.K.fall.get(t, {}).get(mask)
        return r[0] / (r[0] + r[1]) if r and r[0] + r[1] >= 3 else 0.0

    def al_objeto_avance(self, t, key, moved):
        r = self.K.fall.setdefault(t, {}).setdefault(key, [0, 0])
        r[0 if moved else 1] += 1

    # ------------------------------------------------------------------ opción del alto nivel
    def opcion(self, cmd, st, info, vals, targets):
        """Encerrado: hay destinos con valor fuera de alcance. Se busca un camino a ellos permitiendo cruzar,
        caro, casillas tapadas por objetos que se mueven (categoría VGDL móvil); el primero de esos objetos en
        el camino es el obstáculo. Se aprende hacia dónde se mueve su tipo (una roca: hacia abajo) y la orden
        es ir a la casilla a la que se movería, cavándola: queda libre y el obstáculo se mueve solo."""
        if not cmd.P.get("unlock", True):
            return None
        K, W, N = cmd.know, st.W, len(st.masks)
        blocked = K.blocked_cells(st)
        # destinos que valen la pena (no un resto de curiosidad) y que se pueden pisar (no un muro)
        want = {j for j in range(N) if j not in info and not blocked[j] and cmd.tabu.get(j, -1) <= st.tick
                and any(st.masks[j] >> t & 1 and vals.get(t, 0) >= 1.0 for t in targets)}
        if not want:
            return None
        movable = [t for t, (name, cat) in st.types.items() if cat == 6 and K.is_blocking(t, st.res)]
        mov = [any(m >> t & 1 for t in movable) for m in st.masks]
        offs = (-W, 1, W, -1)
        # distancia de cada casilla a lo deseado, cruzando lo libre (1) y lo tapado por móviles (10)
        dist = {j: 0 for j in want}
        pq = [(0, j) for j in want]
        while pq:
            c, i = heapq.heappop(pq)
            if c > dist[i]:
                continue
            x, y = i % W, i // W
            for d in range(4):
                xx, yy = x + (d == 1) - (d == 3), y + (d == 2) - (d == 0)
                if not (0 <= xx < W and 0 <= yy < st.H):
                    continue
                j = i + offs[d]
                if blocked[j] and not mov[j]:
                    continue
                nc = c + (10 if mov[j] else 1)
                if nc < dist.get(j, math.inf):
                    dist[j] = nc
                    heapq.heappush(pq, (nc, j))
        # candidatos: móviles que dejarían más cerca de lo deseado, con su casilla de liberación alcanzable
        best, choice = math.inf, None
        for o in range(N):
            if not mov[o] or o not in dist:
                continue
            t = next(t for t in movable if st.masks[o] >> t & 1)
            d = cmd.nav.track.main_dir(t)
            if d is None:
                continue
            r = o + d[1] * W + d[0]
            if not (0 <= r < N) or r not in info or blocked[r] or r == st.pos or cmd.tabu.get(r, -1) > st.tick:
                continue
            sc = dist[o] + info[r][0]
            if sc < best:
                best, choice = sc, (r, info[r][0])
        if choice is not None:
            cmd.stats["unlock"] = cmd.stats.get("unlock", 0) + 1
        return choice
