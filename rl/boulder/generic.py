"""Agente genérico para juegos de grilla de GVGAI: nada de Boulder Dash escrito a mano.

Lo que usa del juego es solo lo que da el motor: la grilla como conjuntos de tipos de sprite (con su
categoría VGDL), la posición y el tipo del avatar, sus recursos, y el modelo del juego para preguntar
"¿muero si hago X?". Todo lo demás se aprende:
  - transitabilidad: por experiencia, ¿al intentar entrar a una casilla con estos tipos me moví?
  - peligro: el predictor de muerte, sobre planos por tipo (tick actual y anterior, para ver movimiento);
  - qué perseguir: efectos de tocar cada tipo, aprendidos por experiencia (cambio de puntaje, de recursos,
    de tipo de avatar, y si la partida se gana o se pierde, según cuántos recursos y qué avatar se tenía).
    El valor de un tipo combina esos efectos con 7 pesos globales ajustados con CEM.
Elige el objetivo con mayor V_t − costo de ruta (A* con costo de riesgo) y da el primer paso; si no hay
nada que valga la pena, explora hacia casillas poco visitadas.
"""
from __future__ import annotations

import gc
import heapq
import json
import math
import os
import subprocess
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .gvgai_env import ROOT

EX = ROOT / "vendor" / "GVGAI" / "examples" / "gridphysics"
TO_BRIDGE = {0: 1, 1: 4, 2: 2, 3: 3, 4: 0}          # nuestras direcciones → acciones del puente
CAT_AVATAR, CAT_FROMAVATAR = 0, 5
R = 3
PATCH = 2 * R + 1


def game_file(name):
    return EX / f"{name}.txt"


def level_file(name, k):
    return EX / f"{name}_lvl{k}.txt"


# ------------------------------------------------------------------ estado y puente
class GState:
    def __init__(self, line, types):
        f = line.split(" ")
        self.tick, self.score = int(f[0]), float(f[1])
        self.ax, self.ay, self.atype = int(f[2]), int(f[3]), int(f[4])
        self.W, self.H = int(f[5]), int(f[6])
        self.masks = [int(v, 16) for v in f[7].split(",")]
        self.moving = [int(v, 16) for v in f[8].split(",")]      # sprites entre dos casillas
        self.res = {}
        if f[9] != "-":
            for kv in f[9].strip(";").split(";"):
                k, v = kv.split(":")
                self.res[int(k)] = int(v)
        # objetos móviles observados: id → (itype, x, y) en casillas (con decimales)
        self.objects = {}
        if len(f) > 10 and f[10] != "-":
            for tok in f[10].strip(";").split(";"):
                t, oid, x, y = tok.split(":")
                self.objects[int(oid)] = (int(t), float(x), float(y))
        self.fx, self.fy = float(self.ax), float(self.ay)       # posición exacta del avatar
        if len(f) > 11:
            self.fx, self.fy = (float(v) for v in f[11].split(":"))
        self.types = types                 # itype → (nombre, categoría)
        self.prev = None                   # máscaras del tick anterior

    @property
    def pos(self):
        return self.ay * self.W + self.ax

    def total_res(self):
        return sum(self.res.values())


class GenericBridge:
    def __init__(self, game):
        # GVGAI_CLASSES: otra compilación de GVGAI (p. ej. sin límite de tiempo por acción, para golden.py)
        classes = os.environ.get("GVGAI_CLASSES", str(ROOT / "vendor" / "classes"))
        cp = f"{classes}{os.pathsep}{ROOT / 'vendor' / 'GVGAI' / 'gson-2.6.2.jar'}"
        self.game = game
        self.p = subprocess.Popen(["java", "-cp", cp, "boulderduo.Bridge", str(game_file(game)), "generic"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=open(os.environ["BRIDGE_ERR"], "a") if os.environ.get("BRIDGE_ERR") else subprocess.DEVNULL,
                                  text=True,
                                  bufsize=1, cwd=str(ROOT / "vendor" / "GVGAI"))
        self.types = {}

    def _read(self):
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("el proceso de GVGAI terminó")
            if line.startswith("@T"):
                for tok in line.split()[1:]:
                    i, name, cat = tok.split(":")
                    self.types[int(i)] = (name, int(cat))
                continue
            if line.startswith("@"):
                return line.rstrip("\n")

    def future(self, h=30, reps=3):
        """Cubo del futuro: máscaras por casilla para cada uno de los próximos h ticks (avatar quieto)."""
        self.p.stdin.write(f"F {h} {reps}\n"); self.p.stdin.flush()
        n = int(self._read().split()[1])
        return [[int(v, 16) for v in self.p.stdout.readline().strip().split(",")] for _ in range(n)]

    def mcts(self, goal, dist, ms=35.0, depth=10):
        """Baseline: la acción la elige un MCTS en Java, con el modelo del juego, navegando a goal."""
        self.p.stdin.write(f"N {ms} {depth} {goal} {','.join(str(-1 if d is None else d) for d in dist)}\n")
        self.p.stdin.flush()

    def labels(self, k=3, reps=4):
        self.p.stdin.write(f"L {k} {reps}\n"); self.p.stdin.flush()
        return [float(v) for v in self._read()[3:].split()]

    def play(self, level, seed, policy):
        path = level_file(self.game, level) if isinstance(level, int) else Path(level).resolve()
        self.p.stdin.write(f"G {path} {seed}\n"); self.p.stdin.flush()
        prev = None
        gc.disable()                         # sin pausas de recolección de basura en medio de una decisión
        try:
            return self._loop(policy, prev)
        finally:
            gc.enable()
            gc.collect()

    def _loop(self, policy, prev):
        while True:
            line = self._read()
            if line.startswith("@M"):
                n, over, mx, tot = line.split()[1:]
                self.timing = (int(n), int(over), float(mx), float(tot))
                continue
            if line.startswith("@E"):
                _, won, score, ticks = line.split(" ")
                if hasattr(policy, "end"):
                    policy.end(int(won))
                return int(won), float(score), int(ticks)
            st = GState(line[3:], self.types)
            st.prev = prev
            prev = st.masks
            a = policy(st, self)
            if a is None:                  # la acción ya la eligió Java (p. ej. el MCTS de referencia)
                continue
            self.p.stdin.write(f"A {5 if a == 'use' else TO_BRIDGE[a]}\n"); self.p.stdin.flush()

    def close(self):
        try:
            self.p.stdin.write("Q\n"); self.p.stdin.flush()
        except OSError:
            pass
        try:
            self.p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()


# ------------------------------------------------------------------ conocimiento aprendido por experiencia
class Knowledge:
    """Conocimiento aprendido jugando: reúne las plantillas de mecánicas (boulder/mecanicas). El estado y los
    métodos de cada una quedan como atributos (K.passed, K.is_blocking(t), K.teleport_exit(t)...).
    Guardar, cargar y fusionar es automático a partir del estado que declara cada mecánica; `apagadas`
    (nombres) las desactiva para ablaciones: sus consultas devuelven el valor neutro y no registran nada."""

    def __init__(self, apagadas=()):
        from .mecanicas import REGISTRO
        self.mecs = {}
        self.apagadas = set()
        self.avoid_push = False
        for cls in REGISTRO:
            m = cls(self)
            self.mecs[m.nombre] = m
            for campo, (fab, _) in m.estado.items():
                setattr(self, campo, fab())
            for n, f in m.metodos().items():
                setattr(self, n, f)
        for n in apagadas:
            self.desactivar(n)

    @property
    def turn_cost(self):
        return self.turn_cost_value()

    def desactivar(self, nombre):
        m = self.mecs[nombre]
        if m.nucleo:
            raise ValueError(f"la mecánica '{nombre}' es del núcleo y no se puede apagar")
        m.activa = False
        self.apagadas.add(nombre)
        for campo, (fab, _) in m.estado.items():
            setattr(self, campo, fab())
        for n in m.metodos():
            if n in m.neutros:
                setattr(self, n, lambda *a, _v=m.neutros[n], **k: _v)
            elif n.startswith("record_"):
                setattr(self, n, lambda *a, **k: None)

    def _campos(self):
        for m in self.mecs.values():
            for campo, (fab, forma) in m.estado.items():
                yield m, campo, fab, forma

    def to_json(self):
        from .mecanicas import codificar
        return {campo: codificar(getattr(self, campo), forma) for _, campo, _, forma in self._campos()}

    @classmethod
    def from_json(cls, d, apagadas=()):
        from .mecanicas import decodificar
        k = cls()
        for m, campo, fab, forma in k._campos():
            if campo in d:
                setattr(k, campo, decodificar(d[campo], forma))
        for m in k.mecs.values():
            m.despues_de_cargar()
        for n in apagadas:
            k.desactivar(n)
        return k

    def merge(self, o):
        """Suma lo aprendido por otro conocimiento (otro proceso)."""
        from .mecanicas import sumar
        for _, campo, _, _ in self._campos():
            setattr(self, campo, sumar(getattr(self, campo), getattr(o, campo)))

    def merge_delta(self, new, old):
        """Suma lo que `new` aprendió desde que era `old` (p. ej. un proceso de práctica que partió de old)."""
        from .mecanicas import restar, sumar
        for _, campo, _, _ in self._campos():
            setattr(self, campo, sumar(getattr(self, campo), restar(getattr(new, campo), getattr(old, campo))))


# ------------------------------------------------------------------ predictor de muerte genérico
def gplanes(st, T):
    """[3T, H+2R, W+2R]: un plano por tipo en este tick, en el anterior y "en movimiento" (entre casillas)."""
    Wd, Hd = st.W, st.H
    out = np.zeros((3 * T, Hd + 2 * R, Wd + 2 * R), np.float32)
    for half, masks in ((0, st.masks), (1, st.prev or st.masks), (2, st.moving)):
        m = np.array(masks, dtype=np.int64).reshape(Hd, Wd)
        for t in range(T):
            out[half * T + t, R:R + Hd, R:R + Wd] = (m >> t) & 1
    return out


def gfeatures(pl, cells, dirs, W):
    cells = np.asarray(cells); dirs = np.asarray(dirs)
    ys, xs = cells // W, cells % W
    win = np.lib.stride_tricks.sliding_window_view(pl, (PATCH, PATCH), axis=(1, 2))
    X = np.zeros((len(cells), pl.shape[0] * PATCH * PATCH + 4), np.float32)
    X[:, :-4] = win[:, ys, xs].transpose(1, 0, 2, 3).reshape(len(cells), -1)
    X[np.arange(len(cells)), X.shape[1] - 4 + dirs] = 1
    return X


class GDangerNet(nn.Module):
    def __init__(self, n_in, hidden=128):
        super().__init__()
        self.f = nn.Sequential(nn.Linear(n_in, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, 1))

    def forward(self, x):
        return self.f(x).squeeze(-1)


class GDanger:
    def __init__(self, path):
        ck = torch.load(path, weights_only=False)
        self.T = ck["T"]
        self.net = GDangerNet(ck["n_in"], ck["hidden"]); self.net.load_state_dict(ck["model"]); self.net.eval()

    def probs(self, st, cells):
        if not cells:
            return {}
        cs = [c for c in cells for _ in range(4)]
        ds = [d for _ in cells for d in range(4)]
        with torch.no_grad():
            p = torch.sigmoid(self.net(torch.from_numpy(gfeatures(gplanes(st, self.T), cs, ds, st.W)))).numpy()
        return {(c, d): float(q) for c, d, q in zip(cs, ds, p)}


# ------------------------------------------------------------------ política
WEIGHTS = {                 # nombre: (mínimo, máximo, inicial)
    "k_score": (0.0, 20.0, 5.0),     # × Δpuntaje medio al tocar el tipo
    "k_res": (0.0, 40.0, 10.0),      # × Δrecursos medio
    "k_avatar": (0.0, 40.0, 10.0),   # × probabilidad de cambiar el tipo de avatar
    "k_win": (0.0, 200.0, 100.0),    # × P(ganar al tocarlo con los recursos y avatar actuales)
    "k_death": (0.0, 200.0, 50.0),   # × P(morir al tocarlo)
    "k_new": (0.0, 20.0, 5.0),       # curiosidad: / (1 + veces tocado con estos recursos y avatar)
    "w_risk": (0.0, 60.0, 20.0),     # × −log(1 − p_muerte) en cada paso de la ruta
    "lam": (0.01, 1.0, 0.1),         # cuánto resta cada paso del camino al valor del objetivo
}
DEFAULT_W = {k: v[2] for k, v in WEIGHTS.items()}


def value_params(types, know):
    """Tipos que pueden ser objetivo (ni avatar, ni fondo) y los pesos globales que ajusta el CEM."""
    targets = [t for t in sorted(types) if t not in know.avatar_types and t not in know.floor and types[t][1] != -1]
    return targets, [], list(WEIGHTS)


class GenericAgent:
    """Llamable como política del puente. Aprende transitabilidad al vuelo (self.know)."""

    def __init__(self, P, know=None, danger=None, rng=None, eps=0.0, learn=True):
        self.P, self.know, self.danger = P, know or Knowledge(), danger
        self.rng = rng or np.random.default_rng(0)
        self.eps, self.learn = eps, learn
        self.reset()

    def reset(self):
        self.last = None
        self.last_dir = None
        self.touch = None          # (tipos tocados, puntaje, recursos, tipo de avatar) del último paso
        self.tabu = {}
        self.visits = {}
        self.target = None
        self.target_since = 0

    def end(self, won=None):
        if self.touch is not None and self.learn and won is not None:
            types, _, res, atype, _ = self.touch
            self.know.record_terminal_touch(types, atype, res, won == 1)
        self.reset()

    def _value(self, t, st, avatars):
        P, K = self.P, self.know
        ds, dr, da, pd, n = K.effect(t)
        return (P["k_score"] * ds + P["k_res"] * dr + P["k_avatar"] * da
                + P["k_win"] * K.p_win(t, st.atype, st.total_res()) - P["k_death"] * pd
                + P["k_new"] / (1 + K.novelty(t, st.atype, st.total_res())))

    def __call__(self, st, br):
        K = self.know
        K.observe_types(st)
        W, N = st.W, len(st.masks)
        offs = (-W, 1, W, -1)
        # 1) aprender transitabilidad del intento anterior
        if self.last is not None and self.learn:
            pos0, d, mask, same_dir = self.last
            moved = st.pos == pos0 + offs[d]
            if abs(st.pos % W - pos0 % W) + abs(st.pos // W - pos0 // W) > 2:
                K.record_jump(mask, st.masks[st.pos])      # teletransporte: se movió, y lejos
                moved = True
            # los avatares orientados giran sin moverse al cambiar de dirección: eso no es un bloqueo
            if same_dir and not any(mask >> t & 1 and K.is_blocking(t) for t in range(63)):
                K.record_dir(d, moved)
            if (moved or same_dir) and K.dir_ok(d):        # si esa dirección no mueve, no es culpa de la casilla
                K.record_move(mask, moved)
            if not moved and same_dir:                # chocar también es probar: agota la curiosidad
                bumped = [t for t in range(63) if mask >> t & 1 and t not in K.avatar_types and t not in K.floor]
                K.record_nonterminal(bumped, st.atype, st.total_res())
        # efectos del toque anterior (la partida siguió: no fue terminal)
        if self.touch is not None and self.learn:
            types, sc0, res0, at0, cell = self.touch
            if st.pos == cell:                        # solo si de verdad entró (no si solo giró)
                K.record_touch(types, st.score - sc0, st.total_res() - res0, st.atype != at0)
                K.record_nonterminal(types, at0, res0)
        self.touch = None
        pos = st.pos
        self.visits[pos] = self.visits.get(pos, 0) + 1
        # 2) costos: bloqueado si algún tipo bloquea; riesgo del predictor
        blocked = [any(m >> t & 1 and K.is_blocking(t) for t in range(63)) for m in st.masks]
        risk = {}
        if self.danger is not None:
            cells = [j for j in range(N) if not blocked[j]]
            w = self.P.get("w_risk", 20.0)
            risk = {k: -w * math.log(max(1e-4, 1 - p)) for k, p in self.danger.probs(st, cells).items()}
        # 3) Dijkstra desde el avatar a todo
        best = {pos: 0.0}; first = {pos: -1}; pq = [(0.0, pos)]
        while pq:
            c, i = heapq.heappop(pq)
            if c > best[i]:
                continue
            x, y = i % W, i // W
            for d in range(4):
                j = i + offs[d]
                xx, yy = x + (d == 1) - (d == 3), y + (d == 2) - (d == 0)
                if not (0 <= xx < W and 0 <= yy < st.H) or blocked[j]:
                    continue
                nc = c + 1.0 + risk.get((j, d), 0.0)
                if nc < best.get(j, math.inf):
                    best[j] = nc; first[j] = d if i == pos else first[i]
                    heapq.heappush(pq, (nc, j))
        # 4) objetivos: tipo con valor positivo, llegando a la casilla o a un vecino si está bloqueada
        targets, avatars, _ = value_params(st.types, K)
        vals = {t: self._value(t, st, avatars) for t in targets}
        choice, bestscore = None, -math.inf
        for j in range(N):
            if j == pos or self.tabu.get(j, -1) > st.tick:
                continue
            m = st.masks[j]
            v = max((vals[t] for t in targets if m >> t & 1), default=-math.inf)
            if v <= 0:
                continue
            if j in best:
                c, via = best[j], first[j]
            else:
                c, via = math.inf, None
                x, y = j % W, j // W
                for d in range(4):                  # entrar desde un vecino alcanzable
                    i = j - offs[d]
                    if i in best and best[i] + 1 < c:
                        c = best[i] + 1
                        via = first[i] if i != pos else d
            if via is None or via == -1:
                continue
            s = v - self.P.get("lam", 1.0) * c
            if s > bestscore:
                bestscore, choice = s, (j, via)
        if choice is None:                          # explorar: casillas alcanzables poco visitadas
            cand = [(self.visits.get(j, 0) * 5 + c, j) for j, c in best.items() if j != pos]
            if cand:
                _, j = min(cand)
                choice = (j, first[j])
        if choice is None:
            act = 4
        else:
            j, act = choice
            if self.target != j:
                self.target, self.target_since = j, st.tick
            elif st.tick - self.target_since > 3 * (best.get(j, 10) + 5):
                self.tabu[j] = st.tick + 60           # no logra nada con este objetivo: descartarlo un rato
        if self.eps and self.rng.random() < self.eps:
            act = int(self.rng.integers(5))
        if act < 4 and 0 <= pos + offs[act] < N:
            self.last = (pos, act, st.masks[pos + offs[act]], self.last_dir == act)
            m = st.masks[pos + offs[act]]
            touched = [t for t in range(63) if m >> t & 1 and t not in K.avatar_types and t not in K.floor
                       and not K.is_blocking(t)]
            if touched:
                self.touch = (touched, st.score, st.total_res(), st.atype, pos + offs[act])
        else:
            self.last = None
        self.last_dir = act if act < 4 else self.last_dir
        return act
