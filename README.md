# Totem downward-digraph layout

A small, reproducible analysis that proposes a letter layout for the 30 core keys of a
[Totem](https://github.com/GEIGEIGEIST/TOTEM) split keyboard (3×5 per half, ignoring the outer pinky
keys and the thumb clusters). The result is rendered to [`totem-layout.png`](totem-layout.png).

```
K C M V .   ' P , U W
I O A E T   S L N R H
G F B X Z   Q Y D J /
```

## Method

1. **Home row** = the 10 most frequent English letters (E T A O I N S R H L, 74.2% of letters).
2. **Downward digraphs.** Every other key sits directly above or below a home key, on the same
   finger, so that a common digraph is typed as one downward stroke:
   - a top-row letter `X` above home key `K` is scored by the digraph `XK`
   - a bottom-row letter `Y` below home key `K` is scored by the digraph `KY`

   Slots are filled greedily, starting with the most frequent downward digraph. That makes every
   accepted pair the strongest remaining option for both its letter and its slot. For example,
   `ND` (1.35%) puts D under N because no other digraph wants D, or the slot under N, more.
3. **Hand split.** All 126 ways to put 5 of the 10 columns (with their stacked keys) on each hand
   are scored by same-hand digraphs. Vowels + T on the left gives the most alternation (59.2%).
4. **Finger order** within each hand: all 120 permutations, scored by finger effort minus inward
   rolls.
5. **Ties, by intuition.** Digraphs under 0.05% (Q, Z, J) are treated as noise. The apostrophe goes
   above S (so `'s` is downward), comma and period take the two easiest free slots, and slash takes
   the last one.

Data: Peter Norvig, [English Letter Frequency Counts: Mayzner Revisited](https://norvig.com/mayzner.html)
(Google Books, ~743 billion words). The letter and digraph totals are vendored in `data/`.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python totem_layout.py   # prints the derivation and writes totem-layout.png
```

Tunables (`NOISE_PCT`, `FINGER_EFFORT`, `ROLL_WEIGHT`, `PUNCTUATION`) are constants at the top of
`totem_layout.py`.
