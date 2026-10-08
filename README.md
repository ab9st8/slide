# Totem downward-slide layout

A small, reproducible analysis that proposes a letter layout for the 30 core keys of a
[Totem](https://github.com/GEIGEIGEIST/TOTEM) split keyboard (3×5 per half, ignoring the outer pinky
keys and the thumb clusters). The idea: on a board with straight columns (and keycaps that form a
well per column), a digraph typed by sliding one finger *down* a column costs about as much as one
keystroke. So the layout puts common digraphs on downward slides and avoids every other
same-finger motion.

There are two versions.

| | v2 (`totem-layout-v2.png`) | v1 (`totem-layout.png`) |
|---|---|---|
| Layout | `' W B , /   Z . C F P`<br>`S I E O A   H N T R L`<br>`J G X U K   Q D V M Y` | `K C M V .   ' P , U W`<br>`I O A E T   S L N R H`<br>`G F B X Z   Q Y D J /` |
| Downward slides | 5.29% of digraphs | 7.13% |
| Other same-finger digraphs | **0.83%** | 4.24% |
| Hand alternation | 66.1% | 59.2% |

For reference, QWERTY has 5.25% non-slide same-finger digraphs and Colemak-DH has 0.56%.

## Try it: the slide trainer (`trainer/`)

A small typing test (Vite + React) that emulates any of these layouts in the browser, so you can
try them without flashing firmware. It remaps keys by *physical position* (`event.code`), so a
keyboard sending stock QWERTY, like a Totem on its default keymap, types the chosen layout.

```bash
cd trainer
npm install
npm run dev   # http://127.0.0.1:47321
```

- Layouts: Slide v2, Slide v1, QWERTY and Colemak (baselines), or paste your own 3×10 grid (for example the
  output of `totem_layout_v2.py --slide-bottom 0.5`).
- Tests: 25/50 words or 30/60 seconds, from the top 200 or 1,000 English words, or a slide drill of
  words that contain the layout's slides. Optional punctuation.
- After each test it shows the median time of your downward slides against hand switches,
  same-hand rolls, and other same-finger pairs, which is the question this layout is betting on.
  Results are kept per layout in local storage.
- Turn off "emulate from QWERTY positions" once you've flashed the layout for real.

## v1: greedy downward digraphs (`totem_layout.py`)

1. **Home row** = the 10 most frequent English letters (E T A O I N S R H L, 74.2% of letters).
2. **Downward digraphs.** A top-row letter `X` above home key `K` is scored by `XK`; a bottom-row
   letter `Y` below `K` is scored by `KY`. Slots are filled greedily from the most frequent
   downward digraph, so every accepted pair beats every rival for both its letter and its slot.
3. **Hand split and finger order**, chosen for hand alternation, finger effort, and inward rolls.
4. **Ties, by intuition** for Q, Z, J and punctuation.

v1 ignores two things: the reverse (upward) direction of each column, and the fact that the
inner column shares the index finger. That leaves T and E on the same finger (`te`/`et`, 1.6% of
digraphs) and `fo` as an upward stroke.

## v2: whole-board optimisation (`totem_layout_v2.py`)

Same home row. Every layout is scored as:

- **+1** per top → home slide and **+1** per home → bottom slide (same column)
- **−1** per other same-finger digraph: one row up, top ↔ bottom, or index ↔ inner column
- **+0.05** per digraph that alternates hands, **−0.05** × key frequency × key effort

The score is searched with simulated annealing (16 fixed seeds; several of them converge on the
same optimum). Punctuation frequencies and `'s` / `n't` are rough estimates, because the corpus
contains letters only.

The slide rewards are the main knobs:

```bash
python totem_layout_v2.py --slide-bottom 0.5            # home -> bottom slides feel worse
python totem_layout_v2.py --slide-top 2 --slide-bottom 2 # slide-hungry
python totem_layout_v2.py --sfb 2 --out strict.png       # punish other same-finger pairs harder
```

Data: Peter Norvig, [English Letter Frequency Counts: Mayzner Revisited](https://norvig.com/mayzner.html)
(Google Books, ~743 billion words). The letter and digraph totals are vendored in `data/`.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python totem_layout.py     # v1: prints the derivation, writes totem-layout.png
python totem_layout_v2.py  # v2: about 30 s, writes totem-layout-v2.png
```

`layoutkit.py` holds the shared corpus loading, same-finger metrics, and the Totem renderer.
