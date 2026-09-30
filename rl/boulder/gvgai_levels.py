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


def generate_v2(seed: int) -> str:
    """Versión 2, más cerca de los oficiales: 21–28 diamantes, ≈11 % de rocas en filas horizontales que a
    menudo descansan justo sobre diamantes o tierra (el patrón peligroso: sacar lo de abajo suelta la roca),
    muros en segmentos y en "L" (≈6 %), y exactamente 2 cangrejos y 2 mariposas en bolsones de vacío."""
    R = random.Random(seed)
    g = [["w" if x in (0, W - 1) or y in (0, H - 1) else "." for x in range(W)] for y in range(H)]
    inner = lambda x, y: 0 < x < W - 1 and 0 < y < H - 1
    free = lambda x, y: inner(x, y) and g[y][x] == "."
    n_in = (W - 2) * (H - 2)

    def count(sym):
        return sum(r.count(sym) for r in g)

    # muros: segmentos rectos y algunas "L", hasta ≈ 3–9 % del interior
    target_w = R.uniform(0.03, 0.09) * n_in
    while count("w") - (2 * W + 2 * H - 4) < target_w:
        x, y = R.randint(1, W - 2), R.randint(1, H - 2)
        L1 = R.randint(2, 7)
        horiz = R.random() < 0.5
        cells = [(x + k, y) if horiz else (x, y + k) for k in range(L1)]
        if R.random() < 0.35:                               # "L"
            ex, ey = cells[-1]
            cells += [(ex, ey + k) if horiz else (ex + k, ey) for k in range(1, R.randint(2, 5))]
        for xx, yy in cells:
            if inner(xx, yy):
                g[yy][xx] = "w"
    # rocas en filas; la mitad de las veces con diamantes justo debajo
    target_o = R.uniform(0.08, 0.13) * n_in
    while count("o") < target_o:
        x, y = R.randint(1, W - 2), R.randint(1, H - 3)
        L = R.randint(1, 6)
        under_gems = R.random() < 0.5
        for k in range(L):
            xx = x + k
            if free(xx, y):
                g[y][xx] = "o"
                if under_gems and free(xx, y + 1):
                    g[y + 1][xx] = "x"
    # diamantes sueltos y en grupos hasta 21–28
    target_x = R.randint(21, 28)
    while count("x") < target_x:
        x, y = R.randint(1, W - 2), R.randint(1, H - 2)
        horiz = R.random() < 0.6
        for k in range(R.randint(1, 3)):
            xx, yy = (x + k, y) if horiz else (x, y + k)
            if free(xx, yy) and count("x") < target_x:
                g[yy][xx] = "x"
    # 2 cangrejos y 2 mariposas en bolsones de vacío
    for sym in "ccbb":
        for _ in range(200):
            x, y = R.randint(2, W - 3), R.randint(1, H - 2)
            if g[y][x] == ".":
                for dx in range(-R.randint(1, 3), R.randint(1, 3) + 1):
                    if inner(x + dx, y) and g[y][x + dx] == ".":
                        g[y][x + dx] = "-"
                for dy in (-1, 1):
                    if R.random() < 0.4 and inner(x, y + dy) and g[y + dy][x] == ".":
                        g[y + dy][x] = "-"
                g[y][x] = sym
                break
    for _ in range(R.randint(2, 8)):
        x, y = R.randint(1, W - 2), R.randint(1, H - 2)
        if free(x, y):
            g[y][x] = "-"
    for sym in "eA":
        while True:
            x, y = R.randint(1, W - 2), R.randint(1, H - 2)
            if free(x, y) and (sym != "A" or g[y - 1][x] != "o"):
                g[y][x] = sym
                break
    return "\n".join("".join(r) for r in g)


def _reachable(g, start):
    Hh, Ww = len(g), len(g[0])
    seen = {start}; fr = [start]
    while fr:
        x, y = fr.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            xx, yy = x + dx, y + dy
            if 0 <= xx < Ww and 0 <= yy < Hh and (xx, yy) not in seen and g[yy][xx] != "w":
                seen.add((xx, yy)); fr.append((xx, yy))
    return seen


def generate_zelda(seed: int) -> str:
    """Zelda de GVGAI (13×9 como los oficiales): muros internos, llave '+', puerta 'g', avatar y 2–4 monstruos,
    todo alcanzable desde el avatar."""
    R = random.Random(seed)
    Wz, Hz = 13, 9
    while True:
        g = [["w" if x in (0, Wz - 1) or y in (0, Hz - 1) else "." for x in range(Wz)] for y in range(Hz)]
        for _ in range(R.randint(3, 7)):
            horiz = R.random() < 0.5
            x, y = R.randint(1, Wz - 2), R.randint(1, Hz - 2)
            for k in range(R.randint(1, 5)):
                xx, yy = (x + k, y) if horiz else (x, y + k)
                if 0 < xx < Wz - 1 and 0 < yy < Hz - 1:
                    g[yy][xx] = "w"
        free = [(x, y) for y in range(1, Hz - 1) for x in range(1, Wz - 1) if g[y][x] == "."]
        R.shuffle(free)
        ax, ay = free.pop()
        g[ay][ax] = "A"
        reach = _reachable(g, (ax, ay))
        cand = [c for c in free if c in reach and abs(c[0] - ax) + abs(c[1] - ay) >= 3]
        n_mon = R.randint(2, 4)
        if len(cand) < 2 + n_mon or len(reach) < 0.7 * len(free):
            continue
        for sym in "+g" + "".join(R.choice("123") for _ in range(n_mon)):
            x, y = cand.pop()
            g[y][x] = sym
        return "\n".join("".join(r) for r in g)


def generate_frogs(seed: int) -> str:
    """Frogs de GVGAI (28 de ancho): meta entre muros arriba, 2–4 filas de río (agua '0' y troncos '=', con el
    generador de troncos en la última columna), orilla con huecos, 2–4 carriles de camiones (una dirección por
    carril, rápidos y lentos), a veces una franja de pasto intermedia, y el avatar abajo."""
    R = random.Random(seed)
    Wf = 28
    rows = ["w" * Wf]
    gx = R.randint(1, Wf - 3)
    rows.append("".join("w" if x in (gx - 1, gx + 1) else "g" if x == gx else "+" for x in range(Wf)))

    def river_row():
        dens = R.uniform(0.3, 0.6)
        r, x = [], 0
        while x < Wf - 1:
            if R.random() < dens:
                L = R.randint(2, 6); r += ["="] * L; x += L
            else:
                L = R.randint(1, 4); r += ["0"] * L; x += L
        r = r[: Wf - 1]
        spawn = R.choice("1234")                    # 1/3 agua con generador denso/ralo, 2/4 con tronco
        return "".join(r) + spawn

    def road_row():
        slow, fast = R.choice([("-", "x"), ("_", "l")])
        dens = R.uniform(0.2, 0.45)
        r, x = [], 0
        while x < Wf:
            if R.random() < dens:
                L = R.randint(1, 4); sym = fast if R.random() < 0.4 else slow; r += [sym] * L; x += L
            else:
                L = R.randint(1, 4); r += ["."] * L; x += L
        return "".join(r[:Wf])

    n_river = R.randint(2, 4)
    split = R.random() < 0.3 and n_river >= 3
    for k in range(n_river):
        rows.append(river_row())
        if split and k == n_river // 2 - 1:
            rows.append("+" * (Wf - 1) + "w")
    bank = ["w"] * Wf
    for _ in range(R.randint(3, 6)):
        x = R.randint(1, Wf - 4)
        for k in range(R.randint(2, 4)):
            bank[x + k] = "+"
    rows.append("".join(bank))
    for _ in range(R.randint(2, 4)):
        rows.append(road_row())
    ax = R.randint(1, Wf - 2)
    rows.append("".join("w" if x in (0, Wf - 1) else "A" if x == ax else "+" for x in range(Wf)))
    rows.append("w" * Wf)
    return "\n".join(rows)


GENERATORS = {"boulderdash": generate, "boulderdash_v2": generate_v2, "zelda": generate_zelda, "frogs": generate_frogs}


def write_levels(n: int, out: Path, first_seed: int = 0, game: str = "boulderdash"):
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for k in range(n):
        p = out / f"gen_{first_seed + k:04d}.txt"
        p.write_text(GENERATORS[game](first_seed + k))
        paths.append(p)
    return paths


if __name__ == "__main__":
    print(generate(0)); print(); print(generate(1))
