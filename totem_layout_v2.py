"""v2: optimise the whole 30-key board for downward slides *and* against every other
same-finger digraph.

v1 filled the columns greedily from the most common downward digraph, and never looked
at the reverse direction or at the index finger's second (inner) column. That left
E and T sharing the left index finger and "fo" (as in "for") as an upward stroke.

v2 keeps the same home row (the 10 most frequent letters) and scores a full layout:

    + W_SLIDE_TOP     x  top -> home digraphs on the same column      (a slide)
    + W_SLIDE_BOTTOM  x  home -> bottom digraphs on the same column   (a slide)
    - W_SFB           x  every other same-finger digraph: one row up, top <-> bottom,
                         or index <-> inner column
    + W_ALT           x  digraphs that alternate hands
    - W_EFFORT        x  sum of key frequency x key effort

and searches it with simulated annealing (fixed seeds, so it's reproducible).
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from layoutkit import (
    ALPHABET, BAD, BG, BOT_EDGE, COL_FINGER, COL_HAND, DIGRAPHS, D_TOTAL, HOME_FILL, INK, MUTED,
    REFERENCE_LAYOUTS, ROOT, TOP_EDGE, alternation, board_legend, col_finger_name, draw_board,
    lpct, sfb_breakdown,
)

_cli = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
_cli.add_argument("--slide-top", type=float, default=1.0, help="reward per top->home slide")
_cli.add_argument("--slide-bottom", type=float, default=1.0,
                  help="reward per home->bottom slide")
_cli.add_argument("--sfb", type=float, default=1.0, help="penalty per non-slide same-finger pair")
_cli.add_argument("--out", default="totem-layout-v2.png")
ARGS = _cli.parse_args()

W_SLIDE_TOP = ARGS.slide_top
W_SLIDE_BOTTOM = ARGS.slide_bottom
W_SFB = ARGS.sfb
W_ALT = 0.05
W_EFFORT = 0.05

# Key effort by row and finger (pinky, ring, middle, index, inner).
EFFORT = {
    "top": [2.4, 1.8, 1.4, 1.5, 2.1],
    "home": [1.6, 1.3, 1.05, 1.0, 1.5],
    "bottom": [2.6, 2.0, 1.6, 1.6, 2.3],
}

# The corpus has no punctuation. These are rough estimates, as % of letters typed
# (about 65 periods, 62 commas, and 24 apostrophes per 1,000 words of English prose).
PUNCT_FREQ = {".": 1.4, ",": 1.3, "'": 0.5, "/": 0.05}
# Estimated digraphs involving punctuation, as % of digraphs ("'s" is about half of all
# apostrophes; "n't" accounts for most of the rest).
PUNCT_DIGRAPHS = {"'S": 0.3, "N'": 0.12, "'T": 0.12}

SEEDS = range(16)
STEPS = 150_000

ROWS = ("top", "home", "bottom")
SYMBOLS = list(ALPHABET) + list(PUNCT_FREQ)
IDX = {s: i for i, s in enumerate(SYMBOLS)}
N = len(SYMBOLS)

HOME = sorted(ALPHABET, key=lambda c: -lpct(c))[:10]

# ---------------------------------------------------------------- score model
F = np.zeros((N, N))
for d, v in DIGRAPHS.items():
    if d[0] != d[1]:
        F[IDX[d[0]], IDX[d[1]]] = v / D_TOTAL * 100
for d, v in PUNCT_DIGRAPHS.items():
    F[IDX[d[0]], IDX[d[1]]] = v
FREQ = np.array([lpct(s) if s in ALPHABET else PUNCT_FREQ[s] for s in SYMBOLS])


def slot(row: int, col: int) -> int:
    return row * 10 + col


def finger_slot_index(col: int) -> int:
    return col if col < 5 else 9 - col


W = np.zeros((30, 30))
KIND = np.full((30, 30), "", dtype=object)
for s in range(30):
    r1, c1 = divmod(s, 10)
    for t in range(30):
        r2, c2 = divmod(t, 10)
        if s == t:
            continue
        if COL_HAND[c1] != COL_HAND[c2]:
            W[s, t] = W_ALT
        elif COL_FINGER[c1] == COL_FINGER[c2]:
            if c1 == c2 and r2 == r1 + 1:
                W[s, t] = W_SLIDE_TOP if r1 == 0 else W_SLIDE_BOTTOM
                KIND[s, t] = "slide"
            else:
                W[s, t] = -W_SFB
                KIND[s, t] = "sfb"
SLOT_EFFORT = np.array([EFFORT[ROWS[s // 10]][finger_slot_index(s % 10)] for s in range(30)])


def score(pos: np.ndarray) -> float:
    """pos[symbol] = slot."""
    return float((F * W[np.ix_(pos, pos)]).sum() - W_EFFORT * (FREQ * SLOT_EFFORT[pos]).sum())


# ---------------------------------------------------------------- search
HOME_SLOTS = [slot(1, c) for c in range(10)]
OTHER_SLOTS = [slot(r, c) for r in (0, 2) for c in range(10)]
HOME_IDX = [IDX[c] for c in HOME]
OTHER_IDX = [i for i in range(N) if SYMBOLS[i] not in HOME]


def anneal(seed: int) -> tuple[float, np.ndarray]:
    rng = random.Random(seed)
    pos = np.zeros(N, dtype=int)
    hs, os_ = HOME_SLOTS[:], OTHER_SLOTS[:]
    rng.shuffle(hs)
    rng.shuffle(os_)
    pos[HOME_IDX] = hs
    pos[OTHER_IDX] = os_
    at = {int(p): i for i, p in enumerate(pos)}
    cur = score(pos)
    best, best_pos = cur, pos.copy()
    t0, t1 = 0.3, 0.001
    for step in range(STEPS):
        temp = t0 * (t1 / t0) ** (step / STEPS)
        move = rng.random()
        if move < 0.25:
            # swap two whole columns (keeps every stacked key with its home key)
            c1, c2 = rng.sample(range(10), 2)
            pairs = [(slot(r, c1), slot(r, c2)) for r in range(3)]
        elif move < 0.4:
            a, b = rng.sample(HOME_SLOTS, 2)
            pairs = [(a, b)]
        else:
            a, b = rng.sample(OTHER_SLOTS, 2)
            pairs = [(a, b)]
        for a, b in pairs:
            ia, ib = at[a], at[b]
            pos[ia], pos[ib] = b, a
            at[a], at[b] = ib, ia
        new = score(pos)
        if new >= cur or rng.random() < math.exp((new - cur) / temp):
            cur = new
            if cur > best:
                best, best_pos = cur, pos.copy()
        else:
            for a, b in reversed(pairs):
                ia, ib = at[a], at[b]
                pos[ia], pos[ib] = b, a
                at[a], at[b] = ib, ia
    return best, best_pos


def to_rows(pos: np.ndarray) -> list[str]:
    grid = [[" "] * 10 for _ in range(3)]
    for i, s in enumerate(pos):
        r, c = divmod(int(s), 10)
        grid[r][c] = SYMBOLS[i]
    return ["".join(r) for r in grid]


def from_rows(rows: list[str]) -> np.ndarray:
    pos = np.zeros(N, dtype=int)
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            pos[IDX[ch]] = slot(r, c)
    return pos


def mirror(rows: list[str]) -> list[str]:
    return [r[::-1] for r in rows]


V1 = ["KCMV.'P,UW", "IOAETSLNRH", "GFBXZQYDJ/"]

runs = sorted((anneal(s) for s in SEEDS), key=lambda x: -x[0])
BEST_SCORE, BEST_POS = runs[0]
LAYOUT = to_rows(BEST_POS)
# Present with the vowels on the left, like v1 (the score is mirror-symmetric).
if "E" in LAYOUT[1][5:]:
    LAYOUT = mirror(LAYOUT)
SEEDS_AT_BEST = sum(1 for s, _ in runs if s >= BEST_SCORE - 1e-9)

CANDIDATES = {"v2": LAYOUT, "v1": V1, **REFERENCE_LAYOUTS}
STATS = {name: {**sfb_breakdown(rows), "alt": alternation(rows)} for name, rows in CANDIDATES.items()}


def column_ledger(rows: list[str]):
    """Per column: slide digraphs, plus the same-column reverses that count against it."""
    out = []
    for c in range(10):
        top, home, bot = rows[0][c], rows[1][c], rows[2][c]
        pairs = []
        for a, b in ((top, home), (home, bot)):
            pairs.append((a + b, F[IDX[a], IDX[b]], "slide"))
        for a, b in ((home, top), (bot, home), (top, bot), (bot, top)):
            pairs.append((a + b, F[IDX[a], IDX[b]], "sfb"))
        out.append((c, top, home, bot, pairs))
    return out


def lateral_pairs(rows: list[str], top_n: int = 4):
    pos = {ch: (r, c) for r, row in enumerate(rows) for c, ch in enumerate(row)}
    found = []
    for i, a in enumerate(SYMBOLS):
        for j, b in enumerate(SYMBOLS):
            if a == b:
                continue
            (_, c1), (_, c2) = pos[a], pos[b]
            if c1 != c2 and COL_FINGER[c1] == COL_FINGER[c2] and F[i, j] > 0:
                found.append((F[i, j], a + b))
    return sorted(found, reverse=True)[:top_n]


# ---------------------------------------------------------------- rendering
def draw_keyboard(ax, rows: list[str]):
    cells, arrows = {}, []
    for c in range(10):
        home = rows[1][c]
        cells[("home", c)] = (home, f"{lpct(home):.1f}%", "home")
        for r, row in ((0, "top"), (2, "bottom")):
            ch = rows[r][c]
            d = ch + home if row == "top" else home + ch
            down = F[IDX[d[0]], IDX[d[1]]]
            if down >= 0.05:
                sub = ("'s ↓" if d == "'S" else f"{d.lower()} {down:.2f}%")
                cells[(row, c)] = (ch, sub, row)
                arrows.append((c, row, TOP_EDGE if row == "top" else BOT_EDGE))
            else:
                cells[(row, c)] = (ch, "", "noise")
    draw_board(ax, cells, arrows)


def draw_comparison(ax):
    ax.set_facecolor(BG)
    names = list(CANDIDATES)
    y = np.arange(len(names))[::-1]
    segs = [("slides", "downward slides", "#3E9E8F"), ("up", "upward", BAD),
            ("skip", "top↔bottom", "#E07B39"), ("lateral", "index↔inner", "#F2B279")]
    left = np.zeros(len(names))
    for key, label, color in segs:
        vals = np.array([STATS[n][key] for n in names])
        ax.barh(y, vals, left=left, color=color, height=0.62, label=label, zorder=2,
                edgecolor=BG, linewidth=1)
        left += vals
    for yi, n in zip(y, names):
        s = STATS[n]
        ax.text(s["total"] + 0.2, yi, f"{s['bad']:.2f}% non-slide", va="center", fontsize=9.5,
                color=BAD if n in ("v1", "QWERTY") else INK, fontweight="bold")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=11, fontweight="bold")
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", labelsize=8.5, colors=MUTED, length=0)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(axis="x", color="#E3DFD6", zorder=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlim(0, max(STATS[n]["total"] for n in names) + 3.6)
    ax.legend(loc="lower right", ncol=2, frameon=False, fontsize=9, handlelength=1.2,
              columnspacing=1.2)
    ax.set_title("Same-finger digraphs, % of all digraphs", loc="left", fontsize=12.5,
                 fontweight="bold", color=INK, pad=10)


def draw_ledger(ax, rows: list[str]):
    ax.set_facecolor(BG)
    ax.axis("off")
    t = ax.transAxes
    ledger = column_ledger(rows)
    hdr = [("column", 0.0), ("slides", 0.2), ("same-column reverses", 0.55), ("net", 0.9)]
    for h, x in hdr:
        ax.text(x, 0.97, h, fontsize=8.8, color=MUTED, fontweight="bold", transform=t, va="center")
    dy = 0.088
    for i, (c, top, home, bot, pairs) in enumerate(ledger):
        y = 0.97 - (i + 1) * dy
        if i % 2 == 0:
            ax.add_patch(mpatches.Rectangle((-0.01, y - dy / 2), 1.0, dy, transform=t,
                                            color="#EFECE5", zorder=0, lw=0))
        ax.text(0.0, y, f"{top}{home}{bot}", fontsize=11, family="DejaVu Sans Mono",
                fontweight="bold", color=INK, transform=t, va="center")
        ax.text(0.085, y, col_finger_name(c)[:3], fontsize=8, color=MUTED, transform=t,
                va="center")
        slides = [(d, v) for d, v, k in pairs if k == "slide" and v >= 0.05]
        rev = sorted([(d, v) for d, v, k in pairs if k == "sfb" and v >= 0.05], key=lambda x: -x[1])
        ax.text(0.2, y, "  ".join(f"{d.lower()} {v:.2f}" for d, v in slides) or "—",
                fontsize=9, family="DejaVu Sans Mono", color="#2F7F75", transform=t, va="center")
        ax.text(0.55, y, "  ".join(f"{d.lower()} {v:.2f}" for d, v in rev[:2]) or "—",
                fontsize=9, family="DejaVu Sans Mono", color=BAD if rev else MUTED,
                transform=t, va="center")
        net = sum(v for _, v, k in pairs if k == "slide") - sum(v for _, v, k in pairs if k == "sfb")
        ax.text(0.9, y, f"{net:+.2f}", fontsize=9.5, family="DejaVu Sans Mono", fontweight="bold",
                color=INK, transform=t, va="center")
    ax.set_title("Column ledger (% of digraphs)", loc="left", fontsize=12.5,
                 fontweight="bold", color=INK, pad=10)


def draw_notes(ax, rows: list[str]):
    ax.set_facecolor(BG)
    ax.axis("off")
    t = ax.transAxes
    v1, v2 = STATS["v1"], STATS["v2"]
    lat = lateral_pairs(rows, 3)

    def para(y, title, lines):
        ax.text(0, y, title, fontsize=12.5, fontweight="bold", color=INK, transform=t, va="top")
        ax.text(0, y - 0.075, "\n".join(lines), fontsize=9.6, color="#3A3F4C", transform=t,
                va="top", linespacing=1.55)

    para(1.0, "What changed from v1", [
        f"•  Non-slide same-finger pairs: {v1['bad']:.2f}% → {v2['bad']:.2f}%"
        f" (QWERTY {STATS['QWERTY']['bad']:.2f}%).",
        f"•  Downward slides: {v1['slides']:.2f}% → {v2['slides']:.2f}%.",
        f"•  Hand alternation: {v1['alt']:.1f}% → {v2['alt']:.1f}%.",
        "•  Index↔inner pairs: " + (", ".join(f"{d.lower()} {v:.2f}%" for v, d in lat) or "none") + ".",
    ])
    para(0.6, "How it was scored", [
        f"+{W_SLIDE_TOP:g} per top→home slide, +{W_SLIDE_BOTTOM:g} per home→bottom slide,",
        f"−{W_SFB:g} per other same-finger digraph, +{W_ALT:g} per hand switch,",
        f"−{W_EFFORT:g} × key frequency × key effort. Home row fixed to the top 10.",
        f"Simulated annealing, {len(SEEDS)} seeds; {SEEDS_AT_BEST} of them hit this exact optimum.",
        "Punctuation frequencies are estimates; the corpus has none.",
    ])
    para(0.16, "Tune it", [
        "python totem_layout_v2.py --slide-bottom 0.5   (if home→bottom slides feel worse)",
        "python totem_layout_v2.py --slide-top 2 --slide-bottom 2   (slide-hungry)",
    ])


def render(path: Path):
    fig = plt.figure(figsize=(20, 13.2), dpi=150, facecolor=BG)
    gs = fig.add_gridspec(3, 3, height_ratios=[0.075, 0.5, 0.42], width_ratios=[1.0, 1.08, 0.98],
                          left=0.06, right=0.975, top=0.97, bottom=0.035, hspace=0.14,
                          wspace=0.14)
    ax_t = fig.add_subplot(gs[0, :])
    ax_t.axis("off")
    ax_t.text(0, 0.95, "Totem downward-slide layout, v2", fontsize=25, fontweight="bold",
              color=INK, va="top")
    ax_t.text(0, 0.18,
              "Same home row as v1. This time the whole board is optimised: reward digraphs that "
              "slide down a column, penalise every other same-finger digraph (upward, two-row, "
              "and the index finger's inner column).",
              fontsize=12.2, color=MUTED, va="top")

    ax_k = fig.add_subplot(gs[1, :2])
    draw_keyboard(ax_k, LAYOUT)
    board_legend(ax_k)

    ax_c = fig.add_subplot(gs[1, 2])
    ax_c.axis("off")
    ax_c.add_patch(mpatches.FancyBboxPatch((0.02, 0.06), 0.96, 0.9, transform=ax_c.transAxes,
                                           boxstyle="round,pad=0,rounding_size=0.04",
                                           facecolor="white", edgecolor="#E3DFD6", lw=1.2))
    ax_c.text(0.09, 0.88, "The layout", fontsize=13, fontweight="bold", color=INK,
              transform=ax_c.transAxes, va="top")
    for i, row in enumerate(LAYOUT):
        ax_c.text(0.5, 0.70 - i * 0.105, " ".join(row[:5]) + "   " + " ".join(row[5:]),
                  fontsize=19, ha="center", va="center", family="DejaVu Sans Mono",
                  fontweight="bold", color=HOME_FILL if i == 1 else INK,
                  transform=ax_c.transAxes)
    ax_c.text(0.5, 0.37, "v1:  " + "  /  ".join(r[:5] + " " + r[5:] for r in V1), fontsize=8.8,
              ha="center", family="DejaVu Sans Mono", color=MUTED, transform=ax_c.transAxes)
    s = STATS["v2"]
    stats = [
        (f"{s['slides']:.2f}%", "of digraphs are downward slides"),
        (f"{s['bad']:.2f}%", "are other same-finger digraphs"),
        (f"{s['alt']:.1f}%", "alternate hands"),
    ]
    for i, (big, small) in enumerate(stats):
        y = 0.28 - i * 0.075
        ax_c.text(0.09, y, big, fontsize=13, fontweight="bold", color=HOME_FILL,
                  transform=ax_c.transAxes, va="center")
        ax_c.text(0.33, y, small, fontsize=9.6, color=MUTED, transform=ax_c.transAxes,
                  va="center")

    draw_comparison(fig.add_subplot(gs[2, 0]))
    draw_ledger(fig.add_subplot(gs[2, 1]), LAYOUT)
    draw_notes(fig.add_subplot(gs[2, 2]), LAYOUT)
    fig.text(0.975, 0.01, "Data: Norvig, \"English Letter Frequency Counts: Mayzner Revisited\" "
             "(Google Books, ~743B words)", ha="right", fontsize=8.5, color=MUTED)
    fig.savefig(path, facecolor=BG)


def report():
    print(f"Best score {BEST_SCORE:.3f} ({SEEDS_AT_BEST}/{len(SEEDS)} seeds); v1 scores "
          f"{score(from_rows(V1)):.3f}")
    print("Top runs:", ", ".join(f"{s:.3f}" for s, _ in runs[:6]))
    print("\nLayout:")
    for r in LAYOUT:
        print("  " + " ".join(r[:5]) + "   " + " ".join(r[5:]))
    print()
    for name, s in STATS.items():
        print(f"  {name:11} slides {s['slides']:5.2f}%  up {s['up']:.2f}  skip {s['skip']:.2f}  "
              f"lateral {s['lateral']:.2f}  non-slide {s['bad']:.2f}%  alt {s['alt']:.1f}%")
    print("\nIndex/inner pairs:", ", ".join(f"{d} {v:.3f}%" for v, d in lateral_pairs(LAYOUT, 6)))


if __name__ == "__main__":
    report()
    out = ROOT / ARGS.out
    render(out)
    print(f"\nWrote {out}")
