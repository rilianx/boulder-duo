"""Núcleo — hacia dónde se mueve cada tipo: tipo → {(dx, dy): veces}. Lo llena y lo usa el rastreador de
objetos (objcube.ObjectTracker: dirección principal, velocidad, si se mueve al azar)."""
from . import Mecanica


class DireccionObjetos(Mecanica):
    nombre = "movimiento"
    prioridad = 10
    nucleo = True
    estado = {"move_dirs": (dict, "I>T>v")}

    def al_objeto_movio(self, t, d, **_):
        dd = self.K.move_dirs.setdefault(t, {})
        dd[d] = dd.get(d, 0) + 1
