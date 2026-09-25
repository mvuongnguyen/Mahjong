# -*- coding: utf-8 -*-
"""Independent audit of every Fan breakdown on the sheet."""
import re, data
from collections import Counter

SUIT = {"p":"dots","s":"sticks","m":"chars"}
WINDS = {"we","ws","ww","wn"}
DRAGONS = {"dr","dg","dw"}
HONOURS = WINDS | DRAGONS
NAMES = {"dr":"中","dg":"發","dw":"白",
         "we":"東","ws":"南","ww":"西","wn":"北"}

def parse(spec):
    """-> list of sets, each a list of tile codes."""
    sets, cur = [], []
    for tok in spec.split():
        if tok == "|":
            if cur: sets.append(cur); cur = []
        else:
            cur.append(tok.rstrip("*"))
    if cur: sets.append(cur)
    return sets

def suit_of(t):
    return SUIT.get(t[-1]) if t[-1] in SUIT and t[0].isdigit() else ("honour" if t in HONOURS else "?")

def kind(st):
    c = Counter(st)
    if len(st) == 4 and len(c) == 1: return "kong"
    if len(st) == 3 and len(c) == 1: return "pung"
    if len(st) == 2 and len(c) == 1: return "pair"
    if len(st) == 3 and len(c) == 3 and all(t[0].isdigit() for t in st):
        su = {t[-1] for t in st}; ns = sorted(int(t[0]) for t in st)
        if len(su) == 1 and ns[1] == ns[0]+1 and ns[2] == ns[1]+1: return "chow"
    if len(st) == 1: return "single"
    return "other"

def facts(spec):
    sets = parse(spec)
    tiles = [t for st in sets for t in st]
    kinds = [kind(st) for st in sets]
    suits = {suit_of(t) for t in tiles}
    numeric = [t for t in tiles if t[0].isdigit()]
    suited = {suit_of(t) for t in numeric}
    f = {}
    f["n"] = len(tiles)
    f["dup_ok"] = all(v <= 4 for v in Counter(tiles).values())
    f["sets"] = list(zip(kinds, sets))
    f["kinds"] = Counter(kinds)
    f["has_honour"] = any(t in HONOURS for t in tiles)
    f["one_suit"] = len(suited) == 1
    f["all_honour"] = len(numeric) == 0 and len(tiles) > 0
    f["full_flush"] = f["one_suit"] and not f["has_honour"]
    f["mixed_flush"] = f["one_suit"] and f["has_honour"] and not f["all_honour"]
    f["all_terminals"] = bool(numeric) and all(t[0] in "19" for t in numeric) and not f["has_honour"]
    f["mixed_terminals"] = bool(numeric) and all(t[0] in "19" for t in numeric) and f["has_honour"]
    melds = [(k, st) for k, st in f["sets"] if k in ("pung","kong")]
    f["all_triplets"] = len(melds) == 4 and f["kinds"].get("pair",0) == 1
    f["all_chows"] = f["kinds"].get("chow",0) == 4 and f["kinds"].get("pair",0) == 1
    f["all_kongs"] = f["kinds"].get("kong",0) == 4
    f["dragon_melds"] = [st[0] for k, st in melds if st[0] in DRAGONS]
    f["wind_melds"]   = [st[0] for k, st in melds if st[0] in WINDS]
    pairs = [st[0] for k, st in f["sets"] if k == "pair"]
    f["dragon_pair"] = [t for t in pairs if t in DRAGONS]
    f["wind_pair"]   = [t for t in pairs if t in WINDS]
    f["small_dragons"] = len(f["dragon_melds"]) == 2 and len(f["dragon_pair"]) == 1
    f["big_dragons"]   = len(f["dragon_melds"]) == 3
    f["small_winds"]   = len(f["wind_melds"]) == 3 and len(f["wind_pair"]) == 1
    f["big_winds"]     = len(f["wind_melds"]) == 4
    # seven pairs: every tile count even and fourteen tiles in seven pairs.
    # a four-of-a-kind supplies two pairs (Luxury Seven Pairs); tables that bar
    # that still satisfy this test, so it accepts both readings.
    _cnt = Counter(tiles)
    f["seven_pairs"]   = (all(v % 2 == 0 for v in _cnt.values())
                          and sum(v // 2 for v in _cnt.values()) == 7)
    f["luxury_pairs"]  = f["seven_pairs"] and any(v == 4 for v in _cnt.values())
    f["all_singles"]   = f["kinds"].get("single",0) + sum(1 for k,st in f["sets"] if k=="other" and len(set(st))==len(st)) > 0 \
                         and f["kinds"].get("pair",0)==0 and f["kinds"].get("pung",0)==0 and f["kinds"].get("kong",0)==0
    return f

TERM = re.compile(r"([A-Z][A-Za-z'/\- ]*?)\s+(\d+)(?=\s*[+=])")
def arith(ex):
    """Check the stated sum adds up. -> (terms, stated_total, ok)"""
    if "=" not in ex: return None
    left, right = ex.split("=", 1)
    terms = [(m.group(1).strip(), int(m.group(2))) for m in TERM.finditer(left + " =")]
    m = re.search(r"(\d+)", right)
    if not m or not terms: return None
    total = int(m.group(1))
    return terms, total, sum(v for _, v in terms) == total

print("%-24s %-5s %s" % ("HAND", "BADGE", "AUDIT"))
print("-"*100)
issues = []
for sec in data.SECTIONS:
    for e in sec["entries"]:
        specs = [s for s, _ in e.get("opts", [])] or ([e["h"]] if e.get("h") else [])
        notes = []
        for spec in specs:
            f = facts(spec)
            if e.get("opts"): continue          # option rows are fragments, not hands
            if f["n"] not in (14, 15, 16, 17, 18):
                notes.append("hand has %d tiles" % f["n"])
            if not f["dup_ok"]:
                notes.append("more than 4 of a tile")
        ex = e.get("ex")
        if ex:
            a = arith(ex)
            if a is None:
                notes.append("breakdown not parseable")
            else:
                terms, total, ok = a
                if not ok:
                    notes.append("ARITHMETIC: %s = %d but sums to %d"
                                 % (" + ".join("%s %d" % t for t in terms), total,
                                    sum(v for _,v in terms)))
        print("%-24s %-5s %s" % (e["en"], e["f"], "; ".join(notes) if notes else "ok"))
        if notes: issues.append((e["en"], notes))
print("-"*100)
print("cards with something to look at: %d" % len(issues))
