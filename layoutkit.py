"""Shared corpus data, metrics, and Totem drawing helpers for the layout scripts."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.transforms import Affine2D

ROOT = Path(__file__).parent
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ROWS = ("top", "home", "bottom")

# Finger order within one hand, outermost first.
FINGERS = ["pinky", "ring", "middle", "index", "inner"]
# Board columns left to right -> physical finger (the inner columns share the index finger).
COL_FINGER = [0, 1, 2, 3, 3, 6, 6, 7, 8, 9]
COL_HAND = [0] * 5 + [1] * 5


def col_finger_name(col: int) -> str:
    return FINGERS[col if col < 5 else 9 - col]


def _load(path: Path) -> dict[str, int]:
    out = {}
    for line in path.read_text().splitlines():
        k, v = line.split("\t")
        out[k] = int(v)
    return out


LETTERS = _load(ROOT / "data" / "letters.tsv")
DIGRAPHS = _load(ROOT / "data" / "digraphs.tsv")
L_TOTAL = sum(LETTERS.values())
D_TOTAL = sum(DIGRAPHS.values())


def lpct(c: str) -> float:
    return LETTERS.get(c, 0) / L_TOTAL * 100


def dpct(d: str) -> float:
    return DIGRAPHS.get(d, 0) / D_TOTAL * 100


def sfb_breakdown(rows: list[str]) -> dict[str, float]:
    """Same-finger digraph share (% of all digraphs) for a 3x10 layout, by motion type.

    slide_top: top -> home, same column.  slide_bottom: home -> bottom, same column.
    up: one row upward, same column.  skip: top <-> bottom, same column.
    lateral: different columns on the same finger (index <-> inner).
    """
    pos = {ch: (r, c) for r, row in enumerate(rows) for c, ch in enumerate(row)}
    out = dict(slide_top=0.0, slide_bottom=0.0, up=0.0, skip=0.0, lateral=0.0)
    for d, v in DIGRAPHS.items():
        a, b = d
        if a == b or a not in pos or b not in pos:
            continue
        (r1, c1), (r2, c2) = pos[a], pos[b]
        if COL_FINGER[c1] != COL_FINGER[c2]:
            continue
        if c1 != c2:
            k = "lateral"
        elif r2 - r1 == 1:
            k = "slide_top" if r1 == 0 else "slide_bottom"
        elif r2 - r1 == -1:
            k = "up"
        else:
            k = "skip"
        out[k] += v / D_TOTAL * 100
    out["slides"] = out["slide_top"] + out["slide_bottom"]
    out["bad"] = out["up"] + out["skip"] + out["lateral"]
    out["total"] = out["slides"] + out["bad"]
    return out


def alternation(rows: list[str]) -> float:
    hand = {ch: COL_HAND[c] for row in rows for c, ch in enumerate(row)}
    alt = sum(v for d, v in DIGRAPHS.items()
              if d[0] in hand and d[1] in hand and hand[d[0]] != hand[d[1]])
    return alt / D_TOTAL * 100


REFERENCE_LAYOUTS = {
    "QWERTY": ["QWERTYUIOP", "ASDFGHJKL;", "ZXCVBNM,./"],
    "Colemak-DH": ["QWFPBJLUY;", "ARSTGMNEIO", "ZXCDVKH,./"],
}

# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------
BG = "#F7F5F0"
INK = "#1F2430"
MUTED = "#6B7080"
HOME_FILL = "#2B3A67"
TOP_FILL = "#D9ECEA"
TOP_EDGE = "#2F8F83"
BOT_FILL = "#FBE3C8"
BOT_EDGE = "#C77418"
NOISE_FILL = "#ECEAE4"
NOISE_EDGE = "#9A968C"
GHOST_EDGE = "#C9C5BB"
BAD = "#C2410C"

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK})

KEY_STYLES = {
    "top": (TOP_FILL, TOP_EDGE, "-"),
    "bottom": (BOT_FILL, BOT_EDGE, "-"),
    "noise": (NOISE_FILL, NOISE_EDGE, (0, (4, 2))),
}

# Totem-ish column stagger (pinky -> inner), in key units.
STAGGER = [-0.30, 0.18, 0.42, 0.18, 0.02]
ROW_Y = {"top": 1.0, "home": 0.0, "bottom": -1.0}
PITCH = 1.04
HALF_GAP = 2.6
SPLAY = 4.0


def draw_key(ax, cx, cy, angle, *, fill, edge, ls="-", lw=1.6, size=0.92):
    t = Affine2D().rotate_deg_around(cx, cy, angle) + ax.transData
    ax.add_patch(mpatches.FancyBboxPatch(
        (cx - size / 2, cy - size / 2), size, size,
        boxstyle="round,pad=0,rounding_size=0.14",
        facecolor=fill, edgecolor=edge, linewidth=lw, linestyle=ls, transform=t, zorder=2,
    ))


def _rot(x, y, ox, oy, angle):
    a = math.radians(angle)
    dx, dy = x - ox, y - oy
    return ox + dx * math.cos(a) - dy * math.sin(a), oy + dx * math.sin(a) + dy * math.cos(a)


def _half_positions(side: str):
    """dict[(row, finger_idx)] -> (x, y, angle), plus ignored-key positions."""
    sign = -1 if side == "left" else 1
    pivot = (sign * (HALF_GAP / 2 + 2.5 * PITCH), 0.0)
    angle = -SPLAY if side == "left" else SPLAY
    pos = {}
    for fi in range(5):
        x = sign * (HALF_GAP / 2 + 0.5 + (4 - fi) * PITCH)
        for row, ry in ROW_Y.items():
            pos[(row, fi)] = (*_rot(x, ry * PITCH + STAGGER[fi], *pivot, angle), angle)
    ghosts = []
    gx = sign * (HALF_GAP / 2 + 0.5 + 5 * PITCH)
    ghosts.append((*_rot(gx, -PITCH + STAGGER[0] - 0.15, *pivot, angle), angle))
    for dx, dy, da in [(2.15, -2.35, -14), (1.05, -2.15, -4), (0.0, -2.1, 6)]:
        tx, ty = _rot(sign * (HALF_GAP / 2 + 0.5 + dx * PITCH), dy, *pivot, angle)
        ghosts.append((tx, ty, angle + (da if side == "left" else -da)))
    return pos, ghosts


def board_position(row: str, col: int):
    side, fi = ("left", col) if col < 5 else ("right", 9 - col)
    return _half_positions(side)[0][(row, fi)]


def draw_board(ax, cells: dict, arrows: list[tuple[int, str, str]] = ()):
    """Draw the 30-key board.

    cells[(row, col)] = (label, sublabel, kind); kind is "home", "top", "bottom", or "noise".
    Missing cells are drawn as empty outlines. arrows = [(col, "top"|"bottom", color)] draws a
    downward arrow between that key and the home key.
    """
    ax.set_facecolor(BG)
    ax.set_aspect("equal")
    ax.axis("off")
    for side in ("left", "right"):
        for gx, gy, ga in _half_positions(side)[1]:
            draw_key(ax, gx, gy, ga, fill="none", edge=GHOST_EDGE, ls=(0, (3, 2.5)), lw=1.2)
            ax.text(gx, gy, "ignored", ha="center", va="center", fontsize=7.5, color="#B0AB9F",
                    rotation=ga, zorder=3)
    for col in range(10):
        for row in ROWS:
            x, y, a = board_position(row, col)
            cell = cells.get((row, col))
            if cell is None:
                draw_key(ax, x, y, a, fill="none", edge=GHOST_EDGE)
                continue
            label, sub, kind = cell
            if kind == "home":
                draw_key(ax, x, y, a, fill=HOME_FILL, edge=HOME_FILL)
                ax.text(x, y + 0.08, label, ha="center", va="center", fontsize=30,
                        fontweight="bold", color="white", rotation=a, zorder=3)
                ax.text(x, y - 0.30, sub, ha="center", va="center", fontsize=9,
                        color="#C9D1F0", rotation=a, zorder=3)
                continue
            fill, edge, ls = KEY_STYLES[kind]
            draw_key(ax, x, y, a, fill=fill, edge=edge, ls=ls)
            ax.text(x, y + 0.10, label, ha="center", va="center", fontsize=26,
                    fontweight="bold", color=INK, rotation=a, zorder=3)
            ax.text(x, y - 0.30, sub, ha="center", va="center", fontsize=8.2,
                    color=edge, rotation=a, zorder=3, fontweight="bold")
        fx, fy, fa = board_position("bottom", col)
        ax.text(fx, fy - 0.72, col_finger_name(col), ha="center", va="center", fontsize=8.5,
                color=MUTED, rotation=fa)
    for col, row, color in arrows:
        (x0, y0, _), (x1, y1, _) = (
            (board_position("top", col), board_position("home", col)) if row == "top"
            else (board_position("home", col), board_position("bottom", col))
        )
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = (x1 - x0) * 0.09, (y1 - y0) * 0.09
        ax.annotate("", xy=(mx + dx, my + dy), xytext=(mx - dx, my - dy),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=2.0, mutation_scale=13),
                    zorder=4)
    ax.set_xlim(-8.0, 8.0)
    ax.set_ylim(-3.15, 1.95)


def board_legend(ax, bbox=(0.5, -0.07)):
    handles = [
        mpatches.Patch(facecolor=HOME_FILL, edgecolor=HOME_FILL, label="home row (letter freq)"),
        mpatches.Patch(facecolor=TOP_FILL, edgecolor=TOP_EDGE, label="top → home slide"),
        mpatches.Patch(facecolor=BOT_FILL, edgecolor=BOT_EDGE, label="home → bottom slide"),
        mpatches.Patch(facecolor=NOISE_FILL, edgecolor=NOISE_EDGE, ls="--",
                       label="tie / judgment call"),
        mpatches.Patch(facecolor="none", edgecolor=GHOST_EDGE, ls="--", label="ignored key"),
    ]
    ax.legend(handles=handles, loc="lower center", ncol=5, frameon=False, fontsize=10.5,
              bbox_to_anchor=bbox, handlelength=1.6, columnspacing=1.6)
