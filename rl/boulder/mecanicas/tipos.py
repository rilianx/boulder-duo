"""Núcleo: qué tipos son el avatar y cuáles el fondo (lo que cubre más de la mitad del mapa)."""
from . import Mecanica

CAT_AVATAR, CAT_FROMAVATAR = 0, 5


class Tipos(Mecanica):
    nombre = "tipos"
    nucleo = True
    estado = {"floor": (set, "set"), "avatar_types": (set, "set")}

    def observe_types(self, st):
        K = self.K
        for t, (name, cat) in st.types.items():
            if cat in (CAT_AVATAR, CAT_FROMAVATAR):
                K.avatar_types.add(t)
        if not K.floor:
            n = len(st.masks)
            for t in st.types:
                if sum(1 for m in st.masks if m >> t & 1) > 0.5 * n:
                    K.floor.add(t)
