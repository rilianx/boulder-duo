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
        cp = f"{ROOT / 'vendor' / 'classes'}{os.pathsep}{ROOT / 'vendor' / 'GVGAI' / 'gson-2.6.2.jar'}"
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
    """Transitabilidad por tipo, tipos "de fondo" y tipos del avatar, aprendidos jugando."""

    def __init__(self):
        self.passed = {}
        self.blocked = {}
        self.floor = set()
        self.avatar_types = set()
        # efectos de tocar cada tipo: n, suma de Δpuntaje, Δrecursos, cambios de avatar, muertes
        self.eff = {}
        # partidas terminadas al tocar el tipo: (tipo de avatar, recursos) → [toques, victorias]
        self.term = {}
        # transitabilidad según cuántos recursos de ese mismo tipo lleva el avatar: tipo → cantidad → [pasó, no]
        self.by_res = {}
        self.turns = [0, 0]                 # cambios de dirección: [se movió, solo giró]
        self.carry = {}                     # tipo de objeto bajo el avatar quieto → [lo movió, no lo movió]
        self.move_dirs = {}                 # tipo de objeto → {(dx, dy): veces que se movió así}
        # cuándo se mueve: tipo → {máscara de la casilla de adelante: [se movió, no]} (una roca cae si abajo
        # queda vacío); y qué desaparece al pisarlo: tipo → [desapareció, quedó] (la tierra, los diamantes)
        self.fall = {}
        self.consumed = {}
        # efecto de USAR: tipo → {"a|dx|dy" (absoluto) o "f|dx|dy" (según hacia dónde mira): [desapareció, visto]}
        # con y sin usar (use_kill / use_base), y cuánto puntaje sube por cada uno que desaparece al usar
        self.use_kill = {}
        self.use_base = {}
        self.use_score = {}
        self.teleport = {}                  # tipo de entrada → {tipo en la casilla de llegada: veces}
        # empujar: tipo → [se corrió al entrar el avatar, no]; y qué pasa al empujarlo hacia una casilla con cierta
        # máscara: tipo → {máscara: [avanzó, se trabó, desapareció, suma de Δpuntaje]}
        self.push = {}
        self.push_into = {}
        self.avoid_push = False

    def _e(self, t):
        return self.eff.setdefault(t, [0, 0.0, 0.0, 0, 0])

    def record_touch(self, types, dscore, dres, datype):
        for t in types:
            e = self._e(t)
            e[0] += 1; e[1] += dscore; e[2] += dres; e[3] += int(datype)

    def record_terminal_touch(self, types, atype, res, won):
        for t in types:
            k = f"{atype}|{res}"
            d = self.term.setdefault(t, {}).setdefault(k, [0, 0])
            d[0] += 1; d[1] += int(won)
            if not won:
                self._e(t)[4] += 1

    def record_nonterminal(self, types, atype, res):
        for t in types:
            d = self.term.setdefault(t, {}).setdefault(f"{atype}|{res}", [0, 0])
            d[0] += 1

    def p_win(self, t, atype, res):
        """P(ganar al tocar t | tipo de avatar, recursos): umbral de recursos aprendido de las victorias."""
        d = self.term.get(t)
        if not d:
            return 0.0
        rows = [(int(k.split("|")[1]), v) for k, v in d.items() if int(k.split("|")[0]) == atype]
        wins = [r for r, v in rows if v[1] > 0]
        if not wins or res < min(wins):
            return 0.0
        lo = min(wins)
        tot = sum(v[0] for r, v in rows if lo <= r <= res)
        w = sum(v[1] for r, v in rows if lo <= r <= res)
        return w / max(tot, 1)

    def novelty(self, t, atype, res):
        """Veces que se tocó t con este tipo de avatar y estos recursos (para la curiosidad)."""
        return self.term.get(t, {}).get(f"{atype}|{res}", [0, 0])[0]

    def effect(self, t):
        e = self.eff.get(t)
        if not e or e[0] == 0:
            return 0.0, 0.0, 0.0, 0.0, 0
        n = e[0]
        # la muerte al tocar depende sobre todo del entorno (eso lo ve el predictor): previo fuerte hacia 0
        return e[1] / n, e[2] / n, e[3] / n, e[4] / (n + 10), n

    def observe_types(self, st):
        for t, (name, cat) in st.types.items():
            if cat in (CAT_AVATAR, CAT_FROMAVATAR):
                self.avatar_types.add(t)
        if not self.floor:
            n = len(st.masks)
            for t in st.types:
                if sum(1 for m in st.masks if m >> t & 1) > 0.5 * n:
                    self.floor.add(t)

    def is_blocking(self, t, res=None):
        """¿Bloquea el tipo t? Si el avatar lleva recursos de ese mismo tipo, se mira lo aprendido con esa
        cantidad exacta (p. ej. un recurso que no se puede recoger más allá de su tope deja de ser pisable).
        Lo que teletransporta se trata como bloqueo al caminar (pisarlo sin querer lleva lejos): solo se entra
        cuando es la meta de la orden."""
        if sum(self.teleport.get(t, {}).values()) >= 2:
            return True
        if self.avoid_push and self.pushable(t):        # al caminar no se empuja nada sin querer
            return True
        if res is not None:
            n = res.get(t)
            if n is not None:
                pb = self.by_res.get(t, {}).get(n)
                if pb is not None and pb[0] + pb[1] >= 3:
                    return pb[1] > 2 * pb[0] + 1
        return self.blocked.get(t, 0) > 2 * self.passed.get(t, 0) + 1

    def blocking_bits(self, res=None):
        bm = 0
        for t in set(self.passed) | set(self.blocked):
            if self.is_blocking(t, res):
                bm |= 1 << t
        return bm

    def blocked_cells(self, st):
        bm = self.blocking_bits(getattr(st, "res", None))
        return [(m & bm) != 0 for m in st.masks]

    def record_move(self, mask, moved, res=None):
        types = [t for t in range(63) if mask >> t & 1 and t not in self.avatar_types]
        if res:
            for t in types:
                if t in res:
                    pb = self.by_res.setdefault(t, {}).setdefault(res[t], [0, 0])
                    pb[0 if moved else 1] += 1
        if moved:
            for t in types:
                self.passed[t] = self.passed.get(t, 0) + 1
        else:
            suspects = [t for t in types if self.passed.get(t, 0) == 0] or types
            for t in suspects:
                self.blocked[t] = self.blocked.get(t, 0) + 1

    def record_jump(self, entry_mask, landed_mask):
        """El avatar entró a una casilla y apareció lejos: lo que había ahí es un teletransporte."""
        entry = [t for t in range(63) if entry_mask >> t & 1 and t not in self.avatar_types and t not in self.floor]
        landed = [t for t in range(63) if landed_mask >> t & 1 and t not in self.avatar_types and t not in self.floor]
        for t in entry:
            dd = self.teleport.setdefault(t, {})
            for e in landed:
                dd[e] = dd.get(e, 0) + 1

    def record_turn(self, moved):
        """Intento de moverse cambiando de dirección hacia una casilla pisable: ¿se movió o solo giró?"""
        self.turns[0 if moved else 1] += 1

    def record_carry(self, types, moved):
        for t in types:
            c = self.carry.setdefault(t, [0, 0])
            c[0 if moved else 1] += 1

    def p_move_into(self, t, mask):
        """P(un objeto de tipo t avanza hacia una casilla con esta máscara), aprendido; sin datos: 0."""
        r = self.fall.get(t, {}).get(mask)
        return r[0] / (r[0] + r[1]) if r and r[0] + r[1] >= 3 else 0.0

    def is_consumed(self, t):
        """¿El tipo desaparece cuando el avatar lo pisa? (tierra, diamantes...)"""
        c = self.consumed.get(t)
        return bool(c) and c[0] + c[1] >= 3 and c[0] > 0.5 * (c[0] + c[1])

    def use_lift(self, t, key):
        """Cuánto más probable es que un objeto de tipo t en esa posición relativa desaparezca si se usa (vs. no)."""
        u = self.use_kill.get(t, {}).get(key); b = self.use_base.get(t, {}).get(key)
        if not u or u[1] < 3:
            return 0.0
        pu = u[0] / u[1]
        pb = b[0] / b[1] if b and b[1] >= 3 else 0.0
        return max(0.0, pu - pb)

    def use_value(self, t):
        """Puntaje medio que da cada objeto de tipo t eliminado al usar (0,5 de curiosidad si hay pocos datos)."""
        v = self.use_score.get(t)
        return v[0] / v[1] if v and v[1] >= 3 else 0.5

    def teleport_exit(self, t):
        """Tipo que marca adónde lleva un teletransporte de tipo t (el más visto al llegar), o None."""
        d = self.teleport.get(t)
        if not d or sum(d.values()) < 2:
            return None
        return max(d.items(), key=lambda kv: kv[1])[0]

    def pushable(self, t):
        """¿El avatar corre al tipo t al entrar en su casilla? (una caja de Sokoban)"""
        c = self.push.get(t)
        return bool(c) and c[0] >= 2 and c[0] > 0.5 * (c[0] + c[1])

    def push_candidate(self, t):
        """¿Vale la pena planear empujes con t? Si ya se sabe empujable, o si alguna vez se pudo pisar su casilla
        y todavía se probó poco empujarlo (curiosidad)."""
        c = self.push.get(t, [0, 0])
        return self.pushable(t) or (c[0] + c[1] < 4 and self.passed.get(t, 0) > 0)

    def push_ok(self, t, mask):
        """¿Se puede empujar un t hacia una casilla con esta máscara? Sin datos: si no hay nada que bloquee ni
        otro empujable ahí."""
        r = self.push_into.get(t, {}).get(mask)
        if r and r[0] + r[1] >= 1:
            return r[0] > r[1]
        return not any(mask >> u & 1 and (self.is_blocking(u) or self.pushable(u)) for u in range(63))

    def push_value(self, t, mask):
        """(valor, veces probado) de empujar un t hacia esa máscara: el puntaje medio si ahí desaparece."""
        r = self.push_into.get(t, {}).get(mask)
        if not r or r[0] == 0:
            return 0.0, 0
        return (r[3] / r[0] if r[2] > 0.5 * r[0] else 0.0), r[0]

    def carriers(self):
        """Tipos de objeto que arrastran al avatar que está quieto encima (p. ej. un tronco en un río)."""
        return {t for t, (a, b) in self.carry.items() if a + b >= 5 and a > 0.5 * (a + b)}

    @property
    def turn_cost(self):
        """1 si el avatar gasta un tick en girar antes de moverse en otra dirección (aprendido)."""
        n = sum(self.turns)
        return int(n >= 20 and self.turns[1] > 0.5 * n)

    def to_json(self):
        return {"passed": self.passed, "blocked": self.blocked, "floor": sorted(self.floor),
                "avatar_types": sorted(self.avatar_types), "eff": self.eff, "term": self.term,
                "by_res": self.by_res, "turns": self.turns, "carry": self.carry,
                "move_dirs": {t: {f"{d[0]},{d[1]}": n for d, n in dd.items()} for t, dd in self.move_dirs.items()},
                "fall": {t: {str(m): v for m, v in dd.items()} for t, dd in self.fall.items()},
                "consumed": self.consumed, "use_kill": self.use_kill, "use_base": self.use_base,
                "use_score": self.use_score, "teleport": self.teleport, "push": self.push,
                "push_into": {t: {str(m): v for m, v in dd.items()} for t, dd in self.push_into.items()}}

    @classmethod
    def from_json(cls, d):
        k = cls()
        k.passed = {int(a): b for a, b in d["passed"].items()}
        k.blocked = {int(a): b for a, b in d["blocked"].items()}
        k.floor = set(d["floor"]); k.avatar_types = set(d["avatar_types"])
        k.eff = {int(a): list(b) for a, b in d.get("eff", {}).items()}
        k.term = {int(a): {kk: list(vv) for kk, vv in b.items()} for a, b in d.get("term", {}).items()}
        k.by_res = {int(a): {int(n): list(v) for n, v in b.items()} for a, b in d.get("by_res", {}).items()}
        k.turns = list(d.get("turns", [0, 0]))
        k.carry = {int(a): list(b) for a, b in d.get("carry", {}).items()}
        k.move_dirs = {int(a): {tuple(int(v) for v in key.split(",")): n for key, n in b.items()}
                       for a, b in d.get("move_dirs", {}).items()}
        k.fall = {int(a): {int(m): list(v) for m, v in b.items()} for a, b in d.get("fall", {}).items()}
        k.consumed = {int(a): list(b) for a, b in d.get("consumed", {}).items()}
        for name in ("use_kill", "use_base"):
            setattr(k, name, {int(a): {kk: list(v) for kk, v in b.items()} for a, b in d.get(name, {}).items()})
        k.use_score = {int(a): list(b) for a, b in d.get("use_score", {}).items()}
        k.teleport = {int(a): {int(e): n for e, n in b.items()} for a, b in d.get("teleport", {}).items()}
        k.push = {int(a): list(b) for a, b in d.get("push", {}).items()}
        k.push_into = {int(a): {int(m): list(v) for m, v in b.items()} for a, b in d.get("push_into", {}).items()}
        return k

    def merge(self, o):
        for t, v in o.passed.items(): self.passed[t] = self.passed.get(t, 0) + v
        for t, v in o.blocked.items(): self.blocked[t] = self.blocked.get(t, 0) + v
        self.floor |= o.floor; self.avatar_types |= o.avatar_types
        for t, e in o.eff.items():
            m = self._e(t)
            for i in range(5): m[i] += e[i]
        for t, d in o.term.items():
            for k, v in d.items():
                m = self.term.setdefault(t, {}).setdefault(k, [0, 0]); m[0] += v[0]; m[1] += v[1]
        for t, d in o.by_res.items():
            for n, v in d.items():
                m = self.by_res.setdefault(t, {}).setdefault(n, [0, 0]); m[0] += v[0]; m[1] += v[1]
        self.turns = [self.turns[0] + o.turns[0], self.turns[1] + o.turns[1]]
        for t, v in o.carry.items():
            m = self.carry.setdefault(t, [0, 0]); m[0] += v[0]; m[1] += v[1]
        for t, d in o.teleport.items():
            for e, n in d.items():
                self.teleport.setdefault(t, {})[e] = self.teleport.get(t, {}).get(e, 0) + n


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
            if moved or same_dir:
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
