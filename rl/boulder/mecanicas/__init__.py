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
import math
import os

# ------------------------------------------------------------------ decisiones con probabilidades
# Cada "sí/no" que cuenta una plantilla (pasó/chocó, se corrió/no, extinto/no...) es una tasa con previo
# Beta(1, 1) ("no sé"). Una plantilla concluye algo cuando la probabilidad de que la tasa supere un nivel es
# al menos CONF. Reemplaza los umbrales fijados a mano (mínimos de observaciones y porcentajes).
PRIOR = (1.0, 1.0)
CONF = float(os.environ.get("MECANICAS_CONF", 0.8))


def p_mayor(k, m, u=0.5):
    """P(tasa > u) con k éxitos y m fracasos, previo Beta(PRIOR)."""
    a, b = k + PRIOR[0], m + PRIOR[1]
    if a + b > 200 or a != int(a) or b != int(b):      # muchos datos: aproximación normal
        mu = a / (a + b); sd = math.sqrt(a * b / ((a + b) ** 2 * (a + b + 1)))
        return 0.5 * math.erfc((u - mu) / (sd * math.sqrt(2)))
    a, b = int(a), int(b)
    n = a + b - 1                                      # P(Beta(a,b) > u) = P(Binomial(n, u) ≤ a − 1)
    if u <= 0:
        return 1.0
    if u >= 1:
        return 0.0
    lu, l1 = math.log(u), math.log(1 - u)
    return min(1.0, sum(math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lu + (n - i) * l1)
                        for i in range(a)))


def seguro(k, m, u=0.5):
    """¿Se puede concluir, con confianza CONF, que la tasa de éxito supera u?"""
    return p_mayor(k, m, u) >= CONF


def media(k, m):
    """Tasa estimada (media a posteriori) con k éxitos y m fracasos."""
    return (k + PRIOR[0]) / (k + m + PRIOR[0] + PRIOR[1])


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
    # en orden de prioridad. Eventos de hoy: paso (el avatar intentó moverse), toque (entró o chocó con una
    # casilla), objeto_movio (lo ve el rastreador de objetos),
    # empuje, sonda_usar, mitad (muestra a mitad de partida) y fin (terminó la partida).

    # Opción del alto nivel (opcional): una mecánica con orden_opcion define opcion(cmd, st, info, vals,
    # targets) → (casilla, tiempo) o None. Cuando no hay nada valioso que tocar, el alto nivel les pregunta en
    # orden (apuntar para usar, portal, abrir camino) y toma la primera que propone algo.
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
from .giro import Giro                      # noqa: E402
from .teletransporte import Teletransporte  # noqa: E402
from .toque import EfectoToque              # noqa: E402
from .movimiento import DireccionObjetos    # noqa: E402
from .relativo import MovimientoRelativo    # noqa: E402
from .usar import Usar                      # noqa: E402
from .empujar import Empujar                # noqa: E402
from .fin_conteo import FinConteo           # noqa: E402
from .efectos import Efectos                # noqa: E402

REGISTRO = [Tipos, Bloqueo, Giro, Teletransporte, EfectoToque, DireccionObjetos, MovimientoRelativo, Usar,
            Empujar, FinConteo, Efectos]
