# -*- coding: utf-8 -*-
"""Exhaustive structural audit of the stacking page.

Enumerates every legal 14/16/18-tile hand shape over ONE suit + the seven honours
(enough to witness every predicate the page uses), evaluates each hand against the
sheet's own definitions, and reports which printed rows have no possible hand.
"""
import sys
from itertools import combinations
import stackdata as sd

NAME = [str(i+1)+"m" for i in range(9)] + ["E","S","W","N","R","G","Wh"]
SUIT, WIND, DRAG = range(0,9), range(9,13), range(13,16)
TERMINAL = {0, 8}

SETS = []                                   # (kind, tuple16, label)
def vec(**kw):
    v = [0]*16
    for k, n in kw.items(): v[int(k[1:])] = n
    return tuple(v)
for i in range(7):
    v=[0]*16; v[i]=v[i+1]=v[i+2]=1
    SETS.append(("chow", tuple(v), "%s%s%s" % (NAME[i],NAME[i+1],NAME[i+2])))
for i in range(16):
    v=[0]*16; v[i]=3; SETS.append(("pung", tuple(v), NAME[i]*3))
    v=[0]*16; v[i]=4; SETS.append(("kong", tuple(v), NAME[i]+"*4"))
PAIRS = [((lambda i: (lambda v: (v.__setitem__(i,2), tuple(v))[1])([0]*16))(i), i) for i in range(16)]

def predicates(kinds, counts, pair_i, seven=None):
    """seven = list of (tile, npairs) for pair-hands, else None."""
    p = set()
    suits   = [i for i in SUIT if counts[i]]
    honours = [i for i in range(9,16) if counts[i]]
    if suits and not honours: p.add("Full Flush")
    if suits and honours:     p.add("Mixed Flush")
    if suits == [] :          p.add("All Honours")
    if all(i in TERMINAL or i >= 9 for i in range(16) if counts[i]): p.add("Mixed Terminals")
    if seven is not None:
        p.add("Seven Pairs")
        if any(n == 2 for _, n in seven): p.add("Luxury Seven Pairs")
        p.discard("Mixed Terminals")       # sheet folds All Triplets into Mixed Terminals
        p.discard("All Honours") if False else None
        return p
    if all(k == "chow" for k in kinds): p.add("All Sequences")
    if all(k != "chow" for k in kinds):
        p.add("All Triplets"); p.add("All Concealed Triplets")
    else:
        p.discard("Mixed Terminals")       # our sheet's Mixed Terminals bakes in All Triplets
    if all(k == "kong" for k in kinds): p.add("All Quadruplets")
    trip = [i for k, v, i in zip(kinds, range(4), range(4))]
    return p

def hand_predicates(sets, pair_i):
    kinds  = [s[0] for s in sets]
    counts = [0]*16
    for s in sets:
        for i, n in enumerate(s[1]): counts[i] += n
    counts[pair_i] += 2
    p = predicates(kinds, counts, pair_i)
    # honour bonuses need an actual triplet/kong of that honour
    trips = set()
    for k, v, _ in sets:
        if k != "chow":
            trips.add(v.index(max(v)))
    d = trips & set(DRAG); w = trips & set(WIND)
    if d: p.add("Dragon")
    if w: p.add("Round Wind / Seat Wind")
    if len(d) == 2 and pair_i in DRAG and pair_i not in d: p.add("Small Three Dragons")
    if len(d) == 3: p.add("Big Three Dragons")
    if len(w) == 3 and pair_i in WIND and pair_i not in w: p.add("Small Four Winds")
    if len(w) == 4: p.add("Big Four Winds")
    nk = sum(1 for k in kinds if k == "kong")
    ch = sum(1 for k in kinds if k == "chow")
    p |= {"Self-Pick", "Concealed Hand", "Moon Under The Sea"}
    if nk >= 1: p.add("Win by Kong Replacement")
    if nk >= 2: p.add("Double Kong Replacement")
    if ch >= 1: p.add("Robbing the Kong")   # the robbed 4th copy can only join a sequence
    return p, counts

def seven_pair_predicates(types, quads):
    counts = [0]*16
    for t in types: counts[t] = 4 if t in quads else 2
    p = {"Seven Pairs"}
    if quads: p.add("Luxury Seven Pairs")
    suits   = [i for i in SUIT if counts[i]]
    honours = [i for i in range(9,16) if counts[i]]
    if suits and not honours: p.add("Full Flush")
    if suits and honours:     p.add("Mixed Flush")
    if not suits:             p.add("All Honours")
    p |= {"Self-Pick", "Concealed Hand", "Moon Under The Sea"}
    # no sequences and no declarable Kong, so no Robbing / Kong-replacement wins
    return p, counts

REACH = {}      # predicate pair -> witness
def note(p, counts, sets_label):
    for a in p:
        for b in p:
            if a != b: REACH.setdefault((a, b), sets_label)

def walk(start, chosen, counts):
    if len(chosen) == 4:
        for pi in range(16):
            if counts[pi] + 2 > 4: continue
            pr, cc = hand_predicates(chosen, pi)
            note(pr, cc, " ".join(s[2] for s in chosen) + " " + NAME[pi]*2)
        return
    for j in range(start, len(SETS)):
        s = SETS[j]; ok = True
        for i, n in enumerate(s[1]):
            if n and counts[i] + n > 4: ok = False; break
        if not ok: continue
        nc = list(counts)
        for i, n in enumerate(s[1]): nc[i] += n
        walk(j, chosen + [s], nc)

walk(0, [], [0]*16)
for combo in combinations(range(16), 7):
    pr, cc = seven_pair_predicates(combo, ())
    note(pr, cc, " ".join(NAME[t]*2 for t in combo))
for q in range(16):
    for rest in combinations([t for t in range(16) if t != q], 5):
        pr, cc = seven_pair_predicates((q,) + rest, (q,))
        note(pr, cc, NAME[q]*4 + " " + " ".join(NAME[t]*2 for t in rest))

print("distinct reachable predicate pairs: %d\n" % len(REACH))
bad = 0
for base in sd.BASES:
    for n, v, tot, nt, cap in sd.stacks_for(base):
        if (base, n) not in REACH:
            bad += 1; print("  IMPOSSIBLE  %-16s + %s" % (base, n))
print("\nprinted rows checked: %d | impossible: %d"
      % (sum(len(sd.stacks_for(b)) for b in sd.BASES), bad))

print("\n--- reverse check: structurally legal but NOT printed ---")
VOCAB = set(sd.SHAPE) | set(sd.PAIRHAND) | set(sd.HONOUR_BONUS) | set(sd.ACTION) | set(sd.BASES)
for base in sd.BASES:
    printed = {r[0] for r in sd.stacks_for(base)}
    for n in sorted(VOCAB):
        if n == base or n in printed: continue
        if n in sd.CONTAINS.get(base, []): continue
        if (base, n) in REACH:
            print("  legal, absent:  %-16s + %-24s  e.g. %s" % (base, n, REACH[(base, n)]))
