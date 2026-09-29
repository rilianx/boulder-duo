"""Generador de niveles de Boulder Dash en el formato de GVGAI (26×13, mismos símbolos que los oficiales).

Imita las estadísticas de los 5 niveles oficiales: rocas en grupos (≈10 %), diamantes en grupos de 1–3
(≥ 14), algunos muros internos, cangrejos y mariposas en bolsones de vacío, avatar sobre tierra y la salida
en cualquier parte. Sirve para entrenar y ajustar sin tocar los niveles oficiales, que quedan para probar.
"""
from __future__ import annotations

import random
from pathlib import Path

W, H = 26, 13


def generate(seed: int) -> str:
    R = random.Random(seed)
    g = [["w" if x in (0, W - 1) or y in (0, H - 1) else "." for x in range(W)] for y in range(H)]
    inner = lambda x, y: 0 < x < W - 1 and 0 < y < H - 1

    def free(x, y):
        return inner(x, y) and g[y][x] == "."

    # muros internos: 1–3 segmentos rectos
    for _ in range(R.randint(1, 3)):
        horiz = R.random() < 0.5
        L = R.randint(3, 9)
        x, y = R.randint(1, W - 2), R.randint(2, H - 3)
        for k in range(L):
            xx, yy = (x + k, y) if horiz else (x, y + k)
            if inner(xx, yy) and yy < H - 1:
                g[yy][xx] = "w"
    # grupos de rocas y de diamantes
    for sym, groups, size in (("o", R.randint(8, 13), (1, 4)), ("x", R.randint(7, 11), (1, 3))):
        for _ in range(groups):
            x, y = R.randint(1, W - 2), R.randint(1, H - 2)
            horiz = R.random() < 0.7
            for k in range(R.randint(*size)):
                xx, yy = (x + k, y) if horiz else (x, y + k)
                if free(xx, yy):
                    g[yy][xx] = sym
    # enemigos en bolsones de vacío
    for sym in "c" * R.randint(1, 3) + "b" * R.randint(1, 3):
        for _ in range(100):
            x, y = R.randint(2, W - 3), R.randint(1, H - 2)
            if g[y][x] in ".":
                for dx in range(-R.randint(1, 2), R.randint(1, 2) + 1):
                    if inner(x + dx, y) and g[y][x + dx] == ".":
                        g[y][x + dx] = "-"
                if R.random() < 0.4 and inner(x, y + 1) and g[y + 1][x] == ".":
                    g[y + 1][x] = "-"
                g[y][x] = sym
                break
    # vacío suelto
    for _ in range(R.randint(4, 12)):
        x, y = R.randint(1, W - 2), R.randint(1, H - 2)
        if free(x, y):
            g[y][x] = "-"
    # al menos 14 diamantes (los oficiales tienen 14–20)
    n = sum(r.count("x") for r in g)
    while n < 14:
        x, y = R.randint(1, W - 2), R.randint(1, H - 2)
        if free(x, y):
            g[y][x] = "x"; n += 1
    for sym in "eA":
        while True:
            x, y = R.randint(1, W - 2), R.randint(1, H - 2)
            if free(x, y) and (sym != "A" or g[y - 1][x] not in "o"):
                g[y][x] = sym
                break
    return "\n".join("".join(r) for r in g)


def write_levels(n: int, out: Path, first_seed: int = 0):
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for k in range(n):
        p = out / f"gen_{first_seed + k:04d}.txt"
        p.write_text(generate(first_seed + k))
        paths.append(p)
    return paths


if __name__ == "__main__":
    print(generate(0)); print(); print(generate(1))
