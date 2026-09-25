# -*- coding: utf-8 -*-
"""Stacking data, derived from the sheet's own Fan values so the two can't drift."""
import data

F = {}
for s in data.SECTIONS:
    for e in s["entries"]:
        F[e["en"]] = e["f"]

def fan(n):
    """Badges like "1x" mean the Fan repeats; take the base number."""
    return int(F[n].rstrip("x").split("/")[0])

LIMIT = 13

# Honour-based bonuses need honour tiles in the hand; a Full Flush has none.
HONOUR_BONUS = ["Dragon", "Round Wind / Seat Wind", "Small Three Dragons",
                "Big Three Dragons", "Small Four Winds", "Big Four Winds"]

# Shape hands: how the four sets are arranged.
SHAPE = ["All Sequences", "All Triplets", "All Concealed Triplets", "All Quadruplets"]

# Win-action bonuses, available to any hand.
ACTION = ["Self-Pick", "Concealed Hand", "Win by Kong Replacement",
          "Double Kong Replacement", "Robbing the Kong", "Moon Under The Sea"]

PAIRHAND = ["Seven Pairs", "Luxury Seven Pairs"]

NOTES = {
 "All Concealed Triplets": "replaces All Triplets",
 "All Quadruplets":        "replaces All Triplets",
 "Mixed Terminals":        "All Triplets 3 is inside",
 "Small Three Dragons":    "replaces per-triplet Dragon",
 "Big Three Dragons":      "replaces the Dragon scores",
 "Small Four Winds":       "replaces Round / Seat Wind",
 "Big Four Winds":         "the limit on its own",
 "Win by Kong Replacement":"replaces Self-Pick",
 "Double Kong Replacement":"replaces both Kong wins",
 "Luxury Seven Pairs":     "2 per four-of-a-kind",
 "Dragon":                 "1 per dragon triplet",
 "Round Wind / Seat Wind": "1 each, 2 if both",
 "Robbing the Kong":       "the robbed tile joins a sequence",
}

# additions the base already pays for: shown, but worth 0 more
BUILT_IN = {("Seven Pairs", "Concealed Hand")}

BASE_NOTES = {
 ("Seven Pairs", "Concealed Hand"):  "built in \u2014 you never Pong or Chow",
 ("Mixed Terminals", "Big Four Winds"): "the pair carries the 1 or 9",
}

# what each base already folds into its own Fan, per the scoring sheet
CONTAINS = {
 "All Triplets":    ["All Triplets"],
 "Mixed Terminals": ["All Triplets"],
 "All Honours":     ["All Triplets"],
 "Mixed Flush":     [], "Full Flush": [], "Seven Pairs": [],
}
# what an addition replaces rather than adds to
REPLACES = {
 "All Concealed Triplets":  ["All Triplets"],
 "All Quadruplets":         ["All Triplets"],
 "All Terminals":           ["Mixed Terminals", "All Triplets"],
 "Small Three Dragons":     ["Dragon"],
 "Big Three Dragons":       ["Dragon", "Small Three Dragons"],
 "Small Four Winds":        ["Round Wind / Seat Wind"],
 "Big Four Winds":          ["Round Wind / Seat Wind", "Small Four Winds"],
 "Win by Kong Replacement": ["Self-Pick"],
 "Double Kong Replacement": ["Self-Pick", "Win by Kong Replacement"],
 "Full Flush":              ["Mixed Flush"],
}
# Seven Pairs has no sets at all: every honour bonus needs a triplet, and declaring
# a Kong would collapse two of the pairs into one set.  Robbing the Kong survives -
# that is another player's Kong, not yours.
NEEDS_A_SET = set(HONOUR_BONUS) | {"Win by Kong Replacement", "Double Kong Replacement"}

# Robbing the Kong takes the 4th copy of a tile an opponent already holds three of,
# so that tile can only ever complete a sequence in your hand.
NO_SEQUENCE = {"All Triplets", "Mixed Terminals", "All Honours", "Seven Pairs"}

# pairs that cannot occur together at all
def _clashes(base, n):
    shapes = {"All Sequences", "All Triplets", "All Concealed Triplets", "All Quadruplets"}
    if n == base: return True
    if n in CONTAINS.get(base, []): return True          # already inside the base
    # a hand made of triplets can never also be all sequences
    triplet_bases = {"All Triplets", "Mixed Terminals", "All Honours"}
    if base in triplet_bases and n == "All Sequences": return True
    if base == "Seven Pairs" and (n in shapes or n in NEEDS_A_SET): return True
    if base in NO_SEQUENCE and n == "Robbing the Kong": return True
    return False

def total_for(base, n, extra=None):
    """base + addition, honouring the sheet's replacement rules."""
    b, v = fan(base), (fan(n) if extra is None else extra)
    if base in REPLACES.get(n, []):        # the addition supersedes the base outright
        raw = v
    else:
        ded = sum(fan(c) for c in REPLACES.get(n, []) if c in CONTAINS.get(base, []))
        raw = b - ded + v
    return min(raw, LIMIT), raw > LIMIT

def stacks_for(base):
    """Ordered (name, added fan, total, note, capped) for everything that can join `base`."""
    out = []
    def add(n, extra=None):
        if _clashes(base, n): return
        if (base, n) in BUILT_IN: extra = 0
        tot, cap = total_for(base, n, extra)
        note = BASE_NOTES.get((base, n)) or NOTES.get(n, "")
        if base in REPLACES.get(n, []) or any(c in CONTAINS.get(base, [])
                                              for c in REPLACES.get(n, [])):
            note = note or "replaces, does not add"
        out.append((n, fan(n) if extra is None else extra, tot, note, cap))
    if base != "Seven Pairs":          # a pairs hand has no sets to shape
        for n in SHAPE: add(n)
    if base in ("Mixed Flush", "Full Flush"):
        add("Seven Pairs")
        sp = fan("Seven Pairs")
        tot = min(fan(base) + sp + 2, LIMIT)
        out.append(("Luxury Seven Pairs", 2, tot, NOTES["Luxury Seven Pairs"],
                    fan(base) + sp + 2 > LIMIT))
    if base == "Mixed Flush":
        add("Mixed Terminals"); add("Full Flush")
    if base == "Seven Pairs":
        sp = fan("Seven Pairs")
        out.append(("Luxury Seven Pairs", 2, min(sp + 2, LIMIT),
                    NOTES["Luxury Seven Pairs"], sp + 2 > LIMIT))
        for n in ("Mixed Flush", "Full Flush", "All Honours"): add(n)
    if base == "All Honours":
        add("Seven Pairs")
        sp = fan("Seven Pairs")
        out.append(("Luxury Seven Pairs", 2, min(fan(base) + sp + 2, LIMIT),
                    NOTES["Luxury Seven Pairs"], fan(base) + sp + 2 > LIMIT))
    if base != "Full Flush":
        for n in HONOUR_BONUS: add(n)
    for n in ACTION: add(n)
    return out

BASES = ["Mixed Flush", "Full Flush", "All Triplets", "Mixed Terminals",
         "Seven Pairs", "All Honours"]

# one-line gloss for each base, so the sheet stands on its own
DESC = {
 "Mixed Flush":     "one suit plus honours (winds & dragons)",
 "Full Flush":      "one suit only, no honours",
 "All Triplets":    "four triplets or quadruplets, plus a pair",
 "Mixed Terminals": "no tile outside 1s, 9s and honours",
 "Seven Pairs":     "seven different pairs \u2014 no sets, so no triplet or Kong bonuses",
 "All Honours":     "honour tiles only (winds & dragons)",
}
