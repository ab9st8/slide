"""Derive a 30-key Totem layout from English letter and digraph frequencies.

Rules (from the brief):
  1. The 10 most frequent letters go on the home row.
  2. Every other key sits directly above or below a home key. A key earns its
     slot through a *downward* digraph on the same column:
        top letter X above home K   ->  digraph "XK" (top -> home)
        bottom letter Y below home K ->  digraph "KY" (home -> bottom)
     Slots are filled greedily from the most frequent downward digraph down,
     so every accepted pair beats every rival for both its letter and its slot.
  3. Whatever the data can't decide (near-zero counts, punctuation, column
     order) is settled by explicit judgment calls documented below.

Data: Peter Norvig's "English Letter Frequency Counts: Mayzner Revisited"
(Google Books, ~743 billion words). See data/.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, permutations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.transforms import Affine2D

ROOT = Path(__file__).parent
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Finger order within one hand, outermost first.
FINGERS = ["pinky", "ring", "middle", "index", "inner"]
# Relative cost of a home-row key per finger (lower = easier).
FINGER_EFFORT = [1.6, 1.3, 1.05, 1.0, 1.5]
ROLL_WEIGHT = 1.0
# Downward digraphs rarer than this are treated as noise, i.e. ties.
NOISE_PCT = 0.05
PUNCTUATION = [",", ".", "'", "/"]


def load(path: Path) -> dict[str, int]:
    out = {}
    for line in path.read_text().splitlines():
        k, v = line.split("\t")
        out[k] = int(v)
    return out


LETTERS = load(ROOT / "data" / "letters.tsv")
DIGRAPHS = load(ROOT / "data" / "digraphs.tsv")
L_TOTAL = sum(LETTERS.values())
D_TOTAL = sum(DIGRAPHS.values())


def lpct(c: str) -> float:
    return LETTERS.get(c, 0) / L_TOTAL * 100


def dpct(d: str) -> float:
    return DIGRAPHS.get(d, 0) / D_TOTAL * 100


@dataclass
class Placement:
    letter: str
    home: str
    row: str  # "top" | "bottom"
    pct: float
    rival: str | None = None
    rival_pct: float = 0.0
    how: str = "data"  # "data" | "noise" | "judgment"

    @property
    def digraph(self) -> str:
        return self.letter + self.home if self.row == "top" else self.home + self.letter


# --------------------------------------------------------------------------
# Step 1: home row
# --------------------------------------------------------------------------
by_freq = sorted(ALPHABET, key=lambda c: -LETTERS[c])
HOME = by_freq[:10]
REST = by_freq[10:]

# --------------------------------------------------------------------------
# Step 2: greedy downward-digraph matching
# --------------------------------------------------------------------------
edges = []
for L in REST:
    for K in HOME:
        edges.append((dpct(L + K), "top", L, K))
        edges.append((dpct(K + L), "bottom", L, K))
edges.sort(key=lambda e: -e[0])

placements: list[Placement] = []
placed: set[str] = set()
taken: set[tuple[str, str]] = set()
for i, (w, row, L, K) in enumerate(edges):
    if L in placed or (row, K) in taken:
        continue
    rival = None
    for w2, row2, L2, K2 in edges[i + 1 :]:
        if L2 in placed or (row2, K2) in taken:
            continue
        if L2 == L or (row2, K2) == (row, K):
            rival = (w2, L2 + K2 if row2 == "top" else K2 + L2)
            break
    p = Placement(L, K, row, w, how="data" if w >= NOISE_PCT else "noise")
    if rival:
        p.rival_pct, p.rival = rival
    placements.append(p)
    placed.add(L)
    taken.add((row, K))

column: dict[str, dict[str, Placement]] = {K: {} for K in HOME}
for p in placements:
    column[p.home][p.row] = p


def column_letters(K: str) -> str:
    return K + "".join(p.letter for p in column[K].values())


# --------------------------------------------------------------------------
# Step 3: split columns across hands to maximise hand alternation
# --------------------------------------------------------------------------
def same_hand_pct(left: set[str]) -> float:
    L = set("".join(column_letters(k) for k in left))
    R = set("".join(column_letters(k) for k in HOME if k not in left))
    return sum(
        v for d, v in DIGRAPHS.items() if (d[0] in L and d[1] in L) or (d[0] in R and d[1] in R)
    ) / D_TOTAL * 100


splits = sorted(
    ((same_hand_pct(set(s)), s) for s in combinations(HOME, 5) if HOME[0] in s),
    key=lambda x: x[0],
)
BEST_SPLIT_PCT, left_cols = splits[0]
RUNNER_SPLIT_PCT, runner_split = splits[1]
LEFT_COLS = [k for k in HOME if k in left_cols]
RIGHT_COLS = [k for k in HOME if k not in left_cols]


# --------------------------------------------------------------------------
# Step 4: order columns within a hand (finger effort + inward rolls)
# --------------------------------------------------------------------------
def hand_score(order: tuple[str, ...]) -> float:
    effort = sum(
        sum(lpct(c) for c in column_letters(k)) * FINGER_EFFORT[i] for i, k in enumerate(order)
    )
    pos = {c: i for i, k in enumerate(order) for c in column_letters(k)}
    roll = 0.0
    for d, v in DIGRAPHS.items():
        a, b = pos.get(d[0]), pos.get(d[1])
        if a is None or b is None or a == b or {a, b} == {3, 4}:
            continue
        roll += v if a < b else -v
    return effort / 100 - ROLL_WEIGHT * roll / D_TOTAL


LEFT_ORDER = list(min(permutations(LEFT_COLS), key=hand_score))  # pinky -> inner
RIGHT_ORDER = list(min(permutations(RIGHT_COLS), key=hand_score))  # pinky -> inner

# Board columns, left to right: L pinky .. L inner, R inner .. R pinky.
BOARD_HOME = LEFT_ORDER + RIGHT_ORDER[::-1]

# --------------------------------------------------------------------------
# Step 5: judgment calls for the slots the data leaves empty
# --------------------------------------------------------------------------
# Rank empty slots by how easy they are to reach: top row before bottom on a
# column-staggered board, and strong fingers before weak ones.
SLOT_EASE = {
    ("top", "middle"): 0, ("top", "index"): 1, ("bottom", "middle"): 2, ("bottom", "index"): 3,
    ("top", "ring"): 4, ("top", "inner"): 5, ("bottom", "ring"): 6, ("bottom", "inner"): 7,
    ("top", "pinky"): 8, ("bottom", "pinky"): 9,
}


def finger_of(K: str) -> str:
    order = LEFT_ORDER if K in LEFT_ORDER else RIGHT_ORDER
    return FINGERS[order.index(K)]


judgments: list[Placement] = []
empty = [(row, K) for K in BOARD_HOME for row in ("top", "bottom") if row not in column[K]]
# "'s" is by far the most common apostrophe digraph, so the apostrophe goes
# directly above S: the same downward rule, applied to punctuation.
if ("top", "S") in empty:
    judgments.append(Placement("'", "S", "top", 0.0, how="judgment"))
    empty.remove(("top", "S"))
empty.sort(key=lambda s: SLOT_EASE[(s[0], finger_of(s[1]))])
for sym, (row, K) in zip([s for s in PUNCTUATION if s != "'"], empty):
    judgments.append(Placement(sym, K, row, 0.0, how="judgment"))
for p in judgments:
    column[p.home][p.row] = p


def key_at(row: str, col: int) -> str:
    K = BOARD_HOME[col]
    if row == "home":
        return K
    p = column[K].get(row)
    return p.letter if p else ""


LAYOUT = {r: [key_at(r, c) for c in range(10)] for r in ("top", "home", "bottom")}

HOME_COVERAGE = sum(lpct(c) for c in HOME)
DOWNWARD_COVERAGE = sum(p.pct for p in placements)


# --------------------------------------------------------------------------
# Rendering
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

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK})


def draw_key(ax, cx, cy, angle, *, fill, edge, ls="-", lw=1.6, size=0.92):
    t = Affine2D().rotate_deg_around(cx, cy, angle) + ax.transData
    box = mpatches.FancyBboxPatch(
        (cx - size / 2, cy - size / 2), size, size,
        boxstyle="round,pad=0,rounding_size=0.14",
        facecolor=fill, edgecolor=edge, linewidth=lw, linestyle=ls, transform=t, zorder=2,
    )
    ax.add_patch(box)


def rot(x, y, ox, oy, angle):
    import math

    a = math.radians(angle)
    dx, dy = x - ox, y - oy
    return ox + dx * math.cos(a) - dy * math.sin(a), oy + dx * math.sin(a) + dy * math.cos(a)


# Totem-ish column stagger (pinky -> inner), in key units.
STAGGER = [-0.30, 0.18, 0.42, 0.18, 0.02]
ROW_Y = {"top": 1.0, "home": 0.0, "bottom": -1.0}
PITCH = 1.04
HALF_GAP = 2.6
SPLAY = 4.0


def half_positions(side: str):
    """Return dict[(row, finger_idx)] -> (x, y, angle) plus ghost key positions."""
    sign = -1 if side == "left" else 1
    pivot = (sign * (HALF_GAP / 2 + 2.5 * PITCH), 0.0)
    angle = -SPLAY if side == "left" else SPLAY
    pos = {}
    for fi in range(5):
        col_from_center = 4 - fi
        x = sign * (HALF_GAP / 2 + 0.5 + col_from_center * PITCH)
        for row, ry in ROW_Y.items():
            y = ry * PITCH + STAGGER[fi]
            pos[(row, fi)] = (*rot(x, y, *pivot, angle), angle)
    ghosts = []
    gx = sign * (HALF_GAP / 2 + 0.5 + 5 * PITCH)
    gy = -1.0 * PITCH + STAGGER[0] - 0.15
    ghosts.append((*rot(gx, gy, *pivot, angle), angle, "outer"))
    for j, (dx, dy, da) in enumerate([(2.15, -2.35, -14), (1.05, -2.15, -4), (0.0, -2.1, 6)]):
        tx = sign * (HALF_GAP / 2 + 0.5 + dx * PITCH)
        tx2, ty2 = rot(tx, dy, *pivot, angle)
        ghosts.append((tx2, ty2, (angle + (da if side == "left" else -da)), "thumb"))
    return pos, ghosts


def draw_keyboard(ax):
    ax.set_facecolor(BG)
    ax.set_aspect("equal")
    ax.axis("off")
    for side, order in (("left", LEFT_ORDER), ("right", RIGHT_ORDER)):
        pos, ghosts = half_positions(side)
        for gx, gy, ga, kind in ghosts:
            draw_key(ax, gx, gy, ga, fill="none", edge=GHOST_EDGE, ls=(0, (3, 2.5)), lw=1.2)
            ax.text(gx, gy, "ignored", ha="center", va="center", fontsize=7.5, color="#B0AB9F",
                    rotation=ga, zorder=3)
        for fi, K in enumerate(order):
            for row in ("top", "home", "bottom"):
                x, y, a = pos[(row, fi)]
                if row == "home":
                    draw_key(ax, x, y, a, fill=HOME_FILL, edge=HOME_FILL)
                    ax.text(x, y + 0.08, K, ha="center", va="center", fontsize=30,
                            fontweight="bold", color="white", rotation=a, zorder=3)
                    ax.text(x, y - 0.30, f"{lpct(K):.1f}%", ha="center", va="center",
                            fontsize=9, color="#C9D1F0", rotation=a, zorder=3)
                    continue
                p = column[K].get(row)
                if p is None:
                    draw_key(ax, x, y, a, fill="none", edge=GHOST_EDGE)
                    continue
                if p.how == "data":
                    fill, edge = (TOP_FILL, TOP_EDGE) if row == "top" else (BOT_FILL, BOT_EDGE)
                    sub = f"{p.digraph.lower()} {p.pct:.2f}%"
                    color = edge
                elif p.how == "noise":
                    fill, edge = NOISE_FILL, NOISE_EDGE
                    sub = f"{p.digraph.lower()} <0.01%"
                    color = NOISE_EDGE
                else:
                    fill, edge = NOISE_FILL, NOISE_EDGE
                    sub = "'s ↓" if p.letter == "'" else ""
                    color = NOISE_EDGE
                draw_key(ax, x, y, a, fill=fill, edge=edge,
                         ls="-" if p.how == "data" else (0, (4, 2)))
                ax.text(x, y + 0.10, p.letter, ha="center", va="center", fontsize=26,
                        fontweight="bold", color=INK, rotation=a, zorder=3)
                ax.text(x, y - 0.30, sub, ha="center", va="center", fontsize=8.2,
                        color=color, rotation=a, zorder=3, fontweight="bold")
            # downward arrows on the column
            xt, yt, _ = pos[("top", fi)]
            xh, yh, _ = pos[("home", fi)]
            xb, yb, _ = pos[("bottom", fi)]
            for (x0, y0), (x1, y1), r, c in (
                ((xt, yt), (xh, yh), "top", TOP_EDGE),
                ((xh, yh), (xb, yb), "bottom", BOT_EDGE),
            ):
                p = column[K].get(r)
                if p is None or p.how != "data":
                    continue
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                ax.annotate("", xy=(mx + (x1 - x0) * 0.09, my + (y1 - y0) * 0.09),
                            xytext=(mx - (x1 - x0) * 0.09, my - (y1 - y0) * 0.09),
                            arrowprops=dict(arrowstyle="-|>", color=c, lw=2.0,
                                            mutation_scale=13), zorder=4)
            fx, fy, fa = pos[("bottom", fi)]
            fx, fy = fx + 0.0, fy - 0.72
            ax.text(fx, fy, FINGERS[fi], ha="center", va="center", fontsize=8.5, color=MUTED,
                    rotation=fa)
    ax.set_xlim(-8.0, 8.0)
    ax.set_ylim(-3.15, 1.95)


def draw_frequency(ax):
    ax.set_facecolor(BG)
    vals = [lpct(c) for c in by_freq]
    colors = [HOME_FILL if c in HOME else "#CFCBC2" for c in by_freq]
    ax.bar(range(26), vals, color=colors, width=0.78, zorder=2)
    ax.set_xticks(range(26))
    ax.set_xticklabels(by_freq, fontsize=9.5, fontweight="bold")
    ax.tick_params(axis="x", length=0, colors=INK)
    ax.tick_params(axis="y", labelsize=8, colors=MUTED, length=0)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(axis="y", color="#E3DFD6", zorder=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.axvline(9.5, color=MUTED, lw=1, ls=(0, (3, 3)))
    ax.text(4.5, 13.4, f"home row: {HOME_COVERAGE:.1f}% of all letters", ha="center",
            fontsize=9.5, color=HOME_FILL, fontweight="bold")
    ax.text(18, 13.4, f"other 16: {100 - HOME_COVERAGE:.1f}%", ha="center", fontsize=9.5,
            color=MUTED)
    ax.set_ylim(0, 14.6)
    ax.set_xlim(-0.7, 25.7)


def draw_log(ax):
    ax.set_facecolor(BG)
    ax.axis("off")
    rows = placements
    n = len(rows)
    y0, dy = 0.965, 0.92 / (n + 1)
    hdr = ["#", "digraph", "freq", "placement", "closest rival", ""]
    xs = [0.0, 0.06, 0.21, 0.36, 0.62, 0.82]
    for x, h in zip(xs, hdr):
        ax.text(x, y0, h, fontsize=8.8, color=MUTED, fontweight="bold", transform=ax.transAxes,
                va="center")
    for i, p in enumerate(rows):
        y = y0 - (i + 1) * dy
        noise = p.how == "noise"
        c = NOISE_EDGE if noise else (TOP_EDGE if p.row == "top" else BOT_EDGE)
        ink = NOISE_EDGE if noise else INK
        where = f"{p.letter} {'above' if p.row == 'top' else 'below'} {p.home}"
        if i % 2 == 0:
            ax.add_patch(mpatches.Rectangle((-0.01, y - dy / 2), 1.0, dy, transform=ax.transAxes,
                                            color="#EFECE5", zorder=0, lw=0))
        ax.text(xs[0], y, f"{i + 1}", fontsize=9, color=MUTED, transform=ax.transAxes, va="center")
        ax.text(xs[1], y, p.digraph, fontsize=10.5, color=c, fontweight="bold",
                family="DejaVu Sans Mono", transform=ax.transAxes, va="center")
        ax.text(xs[2], y, f"{p.pct:.3f}%", fontsize=9, color=ink, family="DejaVu Sans Mono",
                transform=ax.transAxes, va="center")
        ax.text(xs[3], y, where, fontsize=9, color=ink, transform=ax.transAxes, va="center")
        if p.rival:
            ax.text(xs[4], y, f"{p.rival}  {p.rival_pct:.3f}%", fontsize=9, color=MUTED,
                    family="DejaVu Sans Mono", transform=ax.transAxes, va="center")
            ratio = p.pct / p.rival_pct if p.rival_pct else float("inf")
            tag = "tie-ish" if ratio < 1.15 else ""
            if noise:
                tag = "noise"
            if tag:
                ax.text(xs[5] + 0.06, y, tag, fontsize=8.2, color="#B4541A" if tag == "tie-ish"
                        else NOISE_EDGE, fontweight="bold", transform=ax.transAxes, va="center")


def draw_notes(ax):
    ax.set_facecolor(BG)
    ax.axis("off")
    t = ax.transAxes

    def para(y, title, lines):
        ax.text(0, y, title, fontsize=12.5, fontweight="bold", color=INK, transform=t, va="top")
        ax.text(0, y - 0.075, "\n".join(lines), fontsize=9.6, color="#3A3F4C", transform=t,
                va="top", linespacing=1.55)

    para(1.0, "3 · Split the columns across hands", [
        "All 126 ways to put 5 of the 10 columns on each hand,",
        "scored by how many digraphs stay on one hand. Winner:",
        f"left  {' '.join(LEFT_COLS)}   |   right  {' '.join(RIGHT_COLS)}",
        f"{100 - BEST_SPLIT_PCT:.1f}% of digraphs alternate hands "
        f"(runner-up {100 - RUNNER_SPLIT_PCT:.1f}%).",
    ])
    para(0.66, "4 · Order the fingers", [
        "All 120 orders per hand, scored by finger effort",
        "(index < middle < ring < inner < pinky) minus inward rolls.",
        f"left pinky→inner  {' '.join(LEFT_ORDER)}     right pinky→inner  {' '.join(RIGHT_ORDER)}",
    ])
    noise = [p for p in placements if p.how == "noise"]
    j = {p.letter: p for p in judgments}

    names = {",": "Comma", ".": "period", "/": "Slash"}

    def where(p):
        return f"{names.get(p.letter, p.letter)} ({p.letter}) {'above' if p.row == 'top' else 'below'} {p.home}"

    lines = [
        f"•  Q, Z, J: their best downward digraphs ({', '.join(p.digraph.lower() for p in noise)})",
        f"    are all under {NOISE_PCT}%, so they are effectively ties. They kept",
        "    their greedy slots on low-traffic columns.",
        "•  Apostrophe above S, so that 's is a downward stroke too.",
    ]
    if "," in j and "." in j:
        lines.append(f"•  {where(j[','])}, {where(j['.'])}: the two easiest free slots")
        lines.append("    go to the two most common punctuation marks.")
    if "/" in j:
        lines.append(f"•  {where(j['/'])}: the last slot.")
    para(0.38, "5 · Ties, broken by intuition", lines)


def draw_card(ax):
    ax.set_facecolor(BG)
    ax.axis("off")
    t = ax.transAxes
    ax.add_patch(mpatches.FancyBboxPatch((0.02, 0.06), 0.96, 0.9, transform=t,
                                         boxstyle="round,pad=0,rounding_size=0.04",
                                         facecolor="white", edgecolor="#E3DFD6", lw=1.2))
    ax.text(0.09, 0.88, "The layout", fontsize=13, fontweight="bold", color=INK, transform=t,
            va="top")
    for i, r in enumerate(("top", "home", "bottom")):
        left = " ".join(c or "·" for c in LAYOUT[r][:5])
        right = " ".join(c or "·" for c in LAYOUT[r][5:])
        color = HOME_FILL if r == "home" else INK
        ax.text(0.5, 0.70 - i * 0.105, f"{left}   {right}", fontsize=19, ha="center", va="center",
                family="DejaVu Sans Mono", fontweight="bold", color=color, transform=t)
    stats = [
        (f"{HOME_COVERAGE:.1f}%", "of letters typed on the home row"),
        (f"{DOWNWARD_COVERAGE:.2f}%", "of digraphs are same-column downward strokes"),
        (f"{100 - BEST_SPLIT_PCT:.1f}%", "of digraphs alternate hands"),
    ]
    for i, (big, small) in enumerate(stats):
        y = 0.33 - i * 0.085
        ax.text(0.09, y, big, fontsize=13, fontweight="bold", color=HOME_FILL, transform=t,
                va="center")
        ax.text(0.33, y, small, fontsize=9.6, color=MUTED, transform=t, va="center")


def render(path: Path):
    fig = plt.figure(figsize=(20, 13.2), dpi=150, facecolor=BG)
    gs = fig.add_gridspec(3, 3, height_ratios=[0.075, 0.5, 0.42], width_ratios=[1.0, 1.08, 0.98],
                          left=0.03, right=0.975, top=0.97, bottom=0.035, hspace=0.14, wspace=0.12)

    ax_t = fig.add_subplot(gs[0, :])
    ax_t.axis("off")
    ax_t.text(0, 0.95, "A Totem layout built from English digraphs that flow downward",
              fontsize=25, fontweight="bold", color=INK, va="top")
    ax_t.text(0, 0.18,
              "30 keys (3×5 per half; outer pinky keys and thumbs ignored). Home row = the 10 most "
              "frequent letters. Every other key sits directly above or below the home key it "
              "most often flows into (or out of) on a downward stroke.",
              fontsize=12.2, color=MUTED, va="top")

    ax_k = fig.add_subplot(gs[1, :2])
    draw_keyboard(ax_k)
    legend = [
        mpatches.Patch(facecolor=HOME_FILL, edgecolor=HOME_FILL, label="home row (letter freq)"),
        mpatches.Patch(facecolor=TOP_FILL, edgecolor=TOP_EDGE, label="top → home digraph"),
        mpatches.Patch(facecolor=BOT_FILL, edgecolor=BOT_EDGE, label="home → bottom digraph"),
        mpatches.Patch(facecolor=NOISE_FILL, edgecolor=NOISE_EDGE, ls="--",
                       label="tie / judgment call"),
        mpatches.Patch(facecolor="none", edgecolor=GHOST_EDGE, ls="--", label="ignored key"),
    ]
    ax_k.legend(handles=legend, loc="lower center", ncol=5, frameon=False, fontsize=10.5,
                bbox_to_anchor=(0.5, -0.07), handlelength=1.6, columnspacing=1.6)

    draw_card(fig.add_subplot(gs[1, 2]))

    ax_f = fig.add_subplot(gs[2, 0])
    draw_frequency(ax_f)
    ax_f.set_title("1 · Home row = the 10 most frequent letters", loc="left", fontsize=12.5,
                   fontweight="bold", color=INK, pad=10)

    ax_l = fig.add_subplot(gs[2, 1])
    draw_log(ax_l)
    ax_l.set_title("2 · Greedy downward-digraph matching", loc="left", fontsize=12.5,
                   fontweight="bold", color=INK, pad=10)

    draw_notes(fig.add_subplot(gs[2, 2]))

    fig.text(0.975, 0.01, "Data: Norvig, \"English Letter Frequency Counts: Mayzner Revisited\" "
             "(Google Books, ~743B words)", ha="right", fontsize=8.5, color=MUTED)
    fig.savefig(path, facecolor=BG)


def report():
    print("Home row:", " ".join(HOME), f"({HOME_COVERAGE:.1f}% of letters)")
    print("\nGreedy downward matching:")
    for i, p in enumerate(placements, 1):
        rival = f"  rival {p.rival} {p.rival_pct:.3f}%" if p.rival else ""
        print(f"  {i:2}. {p.digraph}  {p.pct:.3f}%  {p.letter} {p.row:<6} {p.home}  [{p.how}]{rival}")
    print(f"\nHand split: {LEFT_COLS} | {RIGHT_COLS}  same-hand {BEST_SPLIT_PCT:.2f}%"
          f" (runner-up {runner_split} {RUNNER_SPLIT_PCT:.2f}%)")
    print("Left pinky->inner:", LEFT_ORDER, " Right pinky->inner:", RIGHT_ORDER)
    print("\nLayout:")
    for r in ("top", "home", "bottom"):
        print("  " + " ".join(c or "_" for c in LAYOUT[r][:5]) + "   " + " ".join(c or "_" for c in LAYOUT[r][5:]))


if __name__ == "__main__":
    report()
    out = ROOT / "totem-layout.png"
    render(out)
    print(f"\nWrote {out}")
