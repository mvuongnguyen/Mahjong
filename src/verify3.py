# -*- coding: utf-8 -*-
"""Tightened audit: real hands only, and patterns judged by their full definition."""
import re, data
from verify import facts, DRAGONS, WINDS, NAMES

VAL = {"All Sequences":1,"All Triplets":3,"All Quadruplets":13,"Dragon":1,
       "Small Three Dragons":5,"Big Three Dragons":8,"Small Four Winds":6,"Big Four Winds":13,
       "Mixed Flush":3,"Full Flush":7,"Mixed Terminals":4,"All Terminals":13,"All Honours":10,
       "Seven Pairs":4}

def qualifies(nm, f):
    """Full definition, not just tile composition."""
    trip = f["all_triplets"]
    if nm == "Mixed Flush":           return f["mixed_flush"]
    if nm == "Full Flush":            return f["full_flush"]
    if nm == "All Sequences":         return f["all_chows"]
    if nm == "All Triplets":          return trip
    if nm == "All Quadruplets":       return f["all_kongs"]
    if nm == "Small Three Dragons":   return f["small_dragons"]
    if nm == "Big Three Dragons":     return f["big_dragons"]
    if nm == "Small Four Winds":      return f["small_winds"]
    if nm == "Big Four Winds":        return f["big_winds"]
    # these three are all-triplet hands by definition on this sheet
    if nm == "Mixed Terminals":       return f["mixed_terminals"] and trip
    if nm == "All Terminals":         return f["all_terminals"] and trip
    if nm == "All Honours":           return f["all_honour"] and trip
    if nm == "Seven Pairs":           return f["seven_pairs"]
    return None

TERM = re.compile(r"([A-Z][A-Za-z'/\- ]*?)\s+(\d+)(?=\s*[+=])")
print("%-24s %-6s %s" % ("HAND","BADGE","AUDIT"))
print("-"*100)
flags = []
for sec in data.SECTIONS:
    for e in sec["entries"]:
        if e.get("opts") or not e.get("h") or "xx" in e["h"]:   # option rows / text-only / face-down cards
            continue
        f = facts(e.get("h","")); ex = e.get("ex","")
        text = (e["ds"] + " " + e.get("rep","") + " " + ex)
        msgs = []
        claimed = {}
        for m in TERM.finditer(ex.split("=")[0] + " =") if "=" in ex else []:
            claimed[m.group(1).strip()] = int(m.group(2))
        # 1. is every claimed pattern真 true?
        for nm, n in claimed.items():
            q = qualifies(nm, f)
            if nm == "Dragon":
                if len(f["dragon_melds"]) != n:
                    msgs.append("claims Dragon %d, tiles show %d" % (n, len(f["dragon_melds"])))
            elif q is False:
                msgs.append("claims %s, tiles do not qualify" % nm)
        # 2. is anything applicable left out and not accounted for anywhere on the card?
        limit = ("limit" in ex) or (claimed and max(claimed.values()) >= 13)
        if not limit:
            for nm in VAL:
                if nm in claimed or nm == "Dragon": continue
                if qualifies(nm, f) and not re.search(re.escape(nm), text):
                    msgs.append("also qualifies for %s (%d), unaccounted" % (nm, VAL[nm]))
            nd = len(f["dragon_melds"])
            if nd and "Dragon" not in claimed and not re.search(r"Dragon", text):
                msgs.append("has %d dragon pung(s), unaccounted" % nd)
            nw = len(f["wind_melds"])
            if nw and not re.search(r"[Ww]ind", text):
                msgs.append("has %d wind pung(s) - seat/round wind may add" % nw)
        print("%-24s %-6s %s" % (e["en"], e["f"], "; ".join(msgs) if msgs else "ok"))
        if msgs: flags.append(e["en"])
print("-"*100)
print("flagged: %s" % (", ".join(flags) if flags else "nothing"))
