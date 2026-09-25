# -*- coding: utf-8 -*-
"""Do the claimed patterns actually hold for the tiles shown, and is anything missed?"""
import re, data
from verify import facts, parse, DRAGONS, WINDS, NAMES

# what the sheet says each pattern is worth
VAL = {"All Sequences":1,"All Triplets":3,"All Concealed Triplets":8,"All Quadruplets":13,
       "Dragon":1,"Small Three Dragons":5,"Big Three Dragons":8,
       "Small Four Winds":6,"Big Four Winds":13,
       "Mixed Flush":3,"Full Flush":7,"Mixed Terminals":4,"All Terminals":13,"All Honours":10,
       "Seven Pairs":4,"Knitted Tiles":5,"Lesser Honours":8,"Greater Honours":10}

def holds(name, f, n):
    if name == "Mixed Flush":          return f["mixed_flush"]
    if name == "Full Flush":           return f["full_flush"]
    if name == "Dragon":               return len(f["dragon_melds"]) == n
    if name == "All Sequences":        return f["all_chows"]
    if name == "All Triplets":         return f["all_triplets"]
    if name == "All Concealed Triplets":return f["all_triplets"]
    if name == "All Quadruplets":      return f["all_kongs"]
    if name == "Small Three Dragons":  return f["small_dragons"]
    if name == "Big Three Dragons":    return f["big_dragons"]
    if name == "Small Four Winds":     return f["small_winds"]
    if name == "Big Four Winds":       return f["big_winds"]
    if name == "Mixed Terminals":      return f["mixed_terminals"]
    if name == "All Terminals":        return f["all_terminals"]
    if name == "All Honours":          return f["all_honour"]
    if name == "Seven Pairs":          return f["seven_pairs"]
    return None                         # win actions / MCR shapes: not derivable from tiles

TERM = re.compile(r"([A-Z][A-Za-z'/\- ]*?)\s+(\d+)(?=\s*[+=])")
print("%-24s %s" % ("HAND", "CLAIM CHECK"))
print("-"*104)
bad = 0
for sec in data.SECTIONS:
    for e in sec["entries"]:
        ex = e.get("ex")
        if not ex or "=" not in ex or not e.get("h") or "xx" in e["h"]: continue
        f = facts(e.get("h",""))
        left = ex.split("=")[0]
        msgs = []
        claimed = set()
        for m in TERM.finditer(left + " ="):
            nm, n = m.group(1).strip(), int(m.group(2))
            claimed.add(nm)
            h = holds(nm, f, n)
            if h is False:
                msgs.append("claims %s but tiles do not support it" % nm)
            elif h is None:
                pass
        # anything applicable but not claimed, and not explicitly excluded in the note?
        for nm in ("Mixed Flush","Full Flush","All Triplets","All Sequences",
                   "Small Three Dragons","Big Three Dragons","Small Four Winds","Big Four Winds",
                   "Mixed Terminals","All Terminals","All Honours","Seven Pairs"):
            if nm in claimed: continue
            if holds(nm, f, 0) is True:
                if re.search(re.escape(nm), ex):        # mentioned as replaced/not added
                    continue
                msgs.append("ALSO qualifies for %s (%d) - not in the breakdown" % (nm, VAL[nm]))
        nd = len(f["dragon_melds"])
        if nd and "Dragon" not in claimed and "Dragons" not in ex and not f["all_honour"]:
            msgs.append("has %d dragon pung(s) (%s) - Dragon %d not in the breakdown"
                        % (nd, ",".join(NAMES[d] for d in f["dragon_melds"]), nd))
        print("%-24s %s" % (e["en"], "; ".join(msgs) if msgs else "ok"))
        if msgs: bad += 1
print("-"*104)
print("cards flagged: %d" % bad)
