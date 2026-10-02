"""Plantillas de mecánicas: cada una es una hipótesis genérica sobre cómo funcionan los juegos de cuadrícula
("¿este tipo bloquea?", "¿esto se empuja?", "¿se gana por sobrevivir?") que se llena contando lo vivido.

Una mecánica declara:
  - nombre, y si es parte del núcleo (no se puede apagar);
  - estado: {campo: (valor inicial, forma)}; la forma dice cómo se guarda y se fusiona (ver `codec`);
  - métodos públicos: registros (record_*, lo que observa) y consultas (lo que el agente le pregunta);
  - neutros: {consulta: valor} que devuelve si se la apaga (ablación).

`Knowledge` (generic.py) reúne todas las de `REGISTRO`: su estado y sus métodos quedan como atributos del
conocimiento, así que el resto del agente sigue usando K.is_blocking(t), K.teleport_exit(t), etc.
Guardar, cargar y fusionar lo aprendido (entre procesos o tras la práctica) es automático a partir del estado
declarado. Agregar una plantilla = escribir un archivo con su clase y sumarla a REGISTRO.
"""
from __future__ import annotations

import copy


class Mecanica:
    nombre = ""
    nucleo = False          # las del núcleo no se apagan (sin ellas el agente no puede ni caminar)
    estado: dict = {}       # campo → (fábrica del valor inicial, forma)
    neutros: dict = {}      # consulta → valor cuando la mecánica está apagada
    prioridad = 50          # orden en que reacciona a cada evento (menor primero)

    def __init__(self, K):
        self.K = K
        self.activa = True

    # Eventos: el agente emite K.emitir("paso", ...), y cada mecánica activa que tenga al_paso(...) reacciona,
    # en orden de prioridad. Eventos de hoy: paso (el avatar intentó moverse), quieto (esperó sobre algo),
    # toque (entró o chocó con una casilla), objeto_movio / objeto_avance (lo ve el rastreador de objetos),
    # empuje, sonda_usar, mitad (muestra a mitad de partida) y fin (terminó la partida).

    # Opción del alto nivel (opcional): una mecánica con orden_opcion define opcion(cmd, st, info, vals,
    # targets) → (casilla, tiempo) o None. Cuando no hay nada valioso que tocar, el alto nivel les pregunta en
    # orden (apuntar para usar, portal, abrir camino, sobrevivir) y toma la primera que propone algo.
    orden_opcion = None

    def metodos(self):
        """Métodos públicos que esta mecánica aporta al conocimiento."""
        return {n: getattr(self, n) for n, v in type(self).__dict__.items()
                if callable(v) and not n.startswith("__") and not n.startswith("al_") and n != "opcion"}

    def despues_de_cargar(self):
        """Ajustes tras cargar el estado (p. ej. claves que deben existir)."""


def conteos(st):
    """{tipo: cuántas casillas lo tienen} en el estado st (con 0 para los tipos ausentes)."""
    c = {}
    for m in st.masks:
        while m:
            b = m & -m; t = b.bit_length() - 1; m ^= b
            c[t] = c.get(t, 0) + 1
    for t in st.types:
        c.setdefault(t, 0)
    return c


# ------------------------------------------------------------------ formas del estado: guardar y cargar
# "v": hoja (número, lista de números: se copia); "set": conjunto ↔ lista ordenada; "lists": lista de listas;
# "I>…": diccionario con claves enteras; "S>…": claves texto; "T>…": claves tupla de enteros ("dx,dy").
def codificar(v, forma):
    if forma == "set":
        return sorted(v)
    if forma in ("v", "lists"):
        return v
    pre, resto = forma[:2], forma[2:]
    if pre == "T>":
        return {f"{k[0]},{k[1]}": codificar(x, resto) for k, x in v.items()}
    return {k: codificar(x, resto) for k, x in v.items()}


def decodificar(v, forma):
    if forma == "set":
        return set(v)
    if forma == "v":
        return list(v) if isinstance(v, list) else v
    if forma == "lists":
        return [list(x) for x in v]
    pre, resto = forma[:2], forma[2:]
    if pre == "I>":
        return {int(k): decodificar(x, resto) for k, x in v.items()}
    if pre == "T>":
        return {tuple(int(q) for q in k.split(",")): decodificar(x, resto) for k, x in v.items()}
    return {k: decodificar(x, resto) for k, x in v.items()}


# ------------------------------------------------------------------ fusionar lo aprendido
def sumar(a, b):
    """a + b (conteos): diccionarios por clave, listas elemento a elemento, conjuntos por unión."""
    if isinstance(a, set):
        return a | b
    if isinstance(a, dict):
        out = dict(a)
        for k, x in b.items():
            out[k] = sumar(out[k], x) if k in out else copy.deepcopy(x)
        return out
    if isinstance(a, list):
        return [sumar(x, y) for x, y in zip(a, b)] + copy.deepcopy(b[len(a):])
    if isinstance(a, bool):
        return a or b
    return a + b


def restar(b, o):
    """b − o (lo nuevo de un proceso respecto de lo que tenía al empezar); o puede faltar (= nada)."""
    if o is None:
        return copy.deepcopy(b)
    if isinstance(b, set):
        return b - o
    if isinstance(b, dict):
        return {k: restar(x, o.get(k)) for k, x in b.items()}
    if isinstance(b, list):
        return [restar(x, o[i] if i < len(o) else None) for i, x in enumerate(b)]
    if isinstance(b, bool):
        return b
    return b - o


from .tipos import Tipos                    # noqa: E402
from .bloqueo import Bloqueo                # noqa: E402
from .direcciones import Direcciones        # noqa: E402
from .giro import Giro                      # noqa: E402
from .arrastre import Arrastre              # noqa: E402
from .teletransporte import Teletransporte  # noqa: E402
from .toque import EfectoToque              # noqa: E402
from .letalidad import Letalidad            # noqa: E402
from .consumo import Consumo                # noqa: E402
from .movimiento import DireccionObjetos    # noqa: E402
from .caida import Caida                    # noqa: E402
from .relativo import MovimientoRelativo    # noqa: E402
from .usar import Usar                      # noqa: E402
from .empujar import Empujar                # noqa: E402
from .fin_conteo import FinConteo           # noqa: E402
from .fin_tiempo import FinTiempo           # noqa: E402

REGISTRO = [Tipos, Bloqueo, Direcciones, Giro, Arrastre, Teletransporte, EfectoToque, Letalidad, Consumo,
            DireccionObjetos, Caida, MovimientoRelativo, Usar, Empujar, FinConteo, FinTiempo]
