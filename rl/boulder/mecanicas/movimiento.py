"""Núcleo — hacia dónde se mueve cada tipo: tipo → {(dx, dy): veces}. Lo llena y lo usa el rastreador de
objetos (objcube.ObjectTracker: dirección principal, velocidad, si se mueve al azar)."""
from . import Mecanica


class DireccionObjetos(Mecanica):
    nombre = "movimiento"
    nucleo = True
    estado = {"move_dirs": (dict, "I>T>v")}
