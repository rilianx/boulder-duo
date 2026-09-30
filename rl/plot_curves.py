"""Gráfico de las curvas llegar vs. morir (runs/generic/<juego>/nav_curve.json) → docs/curvas.png"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUNS = Path(__file__).parent / "runs" / "generic"
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#1a1a19", "#6b6a63", "#e6e5df"
TNAME = {(1.5, 10): "T corto", (3, 20): "T medio", (5, 30): "T largo"}

fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), sharey=True)
for ax, (game, title) in zip(axes, (("boulderdash", "Boulder Dash"), ("zelda", "Zelda"), ("frogs", "Frogs"))):
    r = json.loads((RUNS / game / "nav_curve.json").read_text())
    base = sorted((x for x in r if x["kind"] == "w" and tuple(x["T"]) == (3, 20)), key=lambda x: x["w"])
    other = [x for x in r if x["kind"] == "w" and tuple(x["T"]) != (3, 20)]
    dl = [x for x in r if x["kind"] == "plazo"]
    ax.plot([x["died"] for x in base], [x["reached"] for x in base], color=BLUE, lw=2, zorder=2)
    ax.scatter([x["died"] for x in base], [x["reached"] for x in base], s=46, color=BLUE, edgecolor="white",
               linewidth=2, zorder=3, label="normal, T medio (barriendo w_risk)")
    xmax = 50
    for x in base:
        if x["w"] in (0, 50):
            if x["died"] > xmax:                     # fuera del eje: flecha al borde
                ax.annotate(f"w=0: muere {x['died']:.0f}% →", (xmax, x["reached"]), xytext=(-4, 4),
                            textcoords="offset points", ha="right", fontsize=8, color=MUTED)
            else:
                ax.annotate(f"w={x['w']}", (x["died"], x["reached"]), textcoords="offset points", xytext=(6, -12),
                            fontsize=8, color=MUTED)
    ax.scatter([x["died"] for x in other], [x["reached"] for x in other], s=46, facecolor="white", edgecolor=BLUE,
               linewidth=1.5, zorder=3, label="normal, T corto / largo (w = 6, 20)")
    ax.scatter([x["died"] for x in dl], [x["reached"] for x in dl], s=70, marker="D", color=ORANGE, edgecolor="white",
               linewidth=2, zorder=4, label="con plazo (conoce T)")
    groups = []                                     # etiquetas de puntos casi iguales, juntas
    for x in sorted(dl, key=lambda x: x["T"][0]):
        for gr in groups:
            if abs(gr[0]["died"] - x["died"]) < 3.5 and abs(gr[0]["reached"] - x["reached"]) < 4:
                gr.append(x); break
        else:
            groups.append([x])
    for gr in groups:
        ax.annotate(" / ".join(TNAME[tuple(x["T"])] for x in gr), (gr[0]["died"], gr[0]["reached"]),
                    textcoords="offset points", xytext=(-8, 8), ha="right", fontsize=8, color=INK,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))
    ax.set_title(title, fontsize=12, color=INK, loc="left")
    ax.set_xlabel("% de órdenes en que muere", color=MUTED, fontsize=9)
    ax.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.set_xlim(0, min(xmax, max(x["died"] for x in r) + 5))
axes[0].set_ylabel("% de órdenes en que llega", color=MUTED, fontsize=9)
axes[0].legend(frameon=False, fontsize=8, loc="lower right")
fig.suptitle("Cumplir sin morir: mejor = arriba a la izquierda", x=0.01, ha="left", fontsize=13, color=INK)
fig.tight_layout()
out = Path(__file__).parent / "docs" / "curvas.png"
fig.savefig(out, dpi=150, facecolor="white")
print(out)
