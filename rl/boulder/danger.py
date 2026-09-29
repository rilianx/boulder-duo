"""Predictor de muerte aprendido: reemplaza las reglas de peligro escritas a mano del A*.

Etiqueta (contrafactual, sale gratis del simulador): desde un estado, el PC entra a la casilla vecina en
la dirección d y luego se queda quieto HORIZON ticks. ¿Muere? Entrada: parche 7×7 centrado en la casilla
destino (clases de celda + "cayendo" + dirección de los enemigos) y la dirección d del paso. Así la red
debe descubrir sola que una roca sobre un hueco cae, que bajar de debajo de una roca la trae encima o
que una luciérnaga cerca explota.
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn

from .sim import BOOM, BUTT, DIRT, E, EXIT, FIRE, GEM, OFF, P1, P2, ROCK, STAY, STEEL, W, WALL, H, Sim

HORIZON = 3
R = 3                                     # radio del parche → 7×7
PATCH = 2 * R + 1
N_CLASS = 8                               # vacío, tierra, sólido, roca, gema, enemigo, explosión, PC
N_CH = N_CLASS + 1 + 4                    # + cayendo + dirección del enemigo
N_IN = N_CH * PATCH * PATCH + 4
_CLASS = np.full(256, 2, np.int64)
for t, c in ((E, 0), (DIRT, 1), (WALL, 2), (STEEL, 2), (EXIT, 2), (ROCK, 3), (GEM, 4), (FIRE, 5), (BUTT, 5),
             (BOOM, 6), (P1, 7), (P2, 7)):
    _CLASS[t] = c


def planes(sim: Sim) -> np.ndarray:
    """Tensor [N_CH, H+2R, W+2R] con la grilla codificada y un borde sólido de R casillas."""
    g = np.frombuffer(bytes(sim.grid), np.uint8).reshape(H, W)
    f = np.frombuffer(bytes(sim.fall), np.uint8).reshape(H, W)
    d = np.frombuffer(bytes(sim.dir), np.uint8).reshape(H, W)
    out = np.zeros((N_CH, H + 2 * R, W + 2 * R), np.float32)
    out[2] = 1                                                    # fuera del mapa = sólido
    inner = out[:, R:R + H, R:R + W]
    inner[2] = 0
    cls = _CLASS[g]
    for c in range(N_CLASS):
        inner[c] = cls == c
    inner[N_CLASS] = f
    enemy = (g == FIRE) | (g == BUTT)
    for k in range(4):
        inner[N_CLASS + 1 + k] = enemy & (d == k)
    return out


def features(pl: np.ndarray, cells, dirs) -> np.ndarray:
    """Entrada de la red para (casilla destino, dirección del paso)."""
    cells = np.asarray(cells); dirs = np.asarray(dirs)
    ys, xs = cells // W, cells % W
    win = np.lib.stride_tricks.sliding_window_view(pl, (PATCH, PATCH), axis=(1, 2))   # [C, H, W, 7, 7]
    patches = win[:, ys, xs].transpose(1, 0, 2, 3).reshape(len(cells), -1)
    X = np.zeros((len(cells), N_IN), np.float32)
    X[:, :-4] = patches
    X[np.arange(len(cells)), N_IN - 4 + dirs] = 1
    return X


def label(sim: Sim, d: int) -> int:
    """1 si al entrar en dirección d y quedarse quieto HORIZON ticks el PC muere."""
    s = sim.copy()
    s.agent.immune = 0                     # se mide el peligro de la casilla, no la suerte de ser inmune
    ev = s.tick(d)
    for _ in range(HORIZON):
        if not s.agent.alive:
            break
        ev += s.tick(STAY)
    return int("death" in ev or (not s.agent.alive and not s.agent.exited))


class DangerNet(nn.Module):
    def __init__(self, hidden=128):
        super().__init__()
        self.f = nn.Sequential(nn.Linear(N_IN, hidden), nn.ReLU(), nn.Linear(hidden, hidden), nn.ReLU(),
                               nn.Linear(hidden, 1))

    def forward(self, x):
        return self.f(x).squeeze(-1)


class DangerModel:
    """Envoltura para usar la red dentro del A*: probabilidades por (casilla, dirección) en la pantalla."""

    def __init__(self, path):
        ck = torch.load(path, weights_only=False)
        self.net = DangerNet(ck["hidden"])
        self.net.load_state_dict(ck["model"])
        self.net.eval()
        torch.set_num_threads(1)

    def window_probs(self, sim: Sim):
        """dict {(j, d): p} para toda casilla transitable de la pantalla entrada desde su vecino en d."""
        g = sim.grid
        x0, y0, x1, y1 = sim.window()
        cells, dirs = [], []
        for y in range(max(1, y0), min(H - 1, y1 + 1)):
            for x in range(max(1, x0), min(W - 1, x1 + 1)):
                j = y * W + x
                if g[j] in (E, DIRT, GEM):
                    for d in range(4):
                        cells.append(j); dirs.append(d)
        if not cells:
            return {}
        pl = planes(sim)
        with torch.no_grad():
            p = torch.sigmoid(self.net(torch.from_numpy(features(pl, cells, dirs)))).numpy()
        return {(j, d): float(q) for j, d, q in zip(cells, dirs, p)}
