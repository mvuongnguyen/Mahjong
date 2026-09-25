# -*- coding: utf-8 -*-
"""Two Letter-size portrait variations of the rule sheet."""
import importlib, sheet
from reportlab.lib.pagesizes import letter, portrait

SCALABLE = ["M","GUT","PADX","PADY","BADGE","KIDIND",
            "NAME_S","DESC_S","REP_S","EX_S","NAME_L","DESC_L","REP_L","EX_L",
            "HEAD_S","HEAD_H","OPT_S","OPT_L","SEC_GAP","TW_BASE","FOOT"]

def build(out, tile=None, factor=None):
    importlib.reload(sheet)
    if factor:
        for k in SCALABLE:
            setattr(sheet, k, getattr(sheet, k) * factor)
    if tile:
        sheet.TW_BASE = tile
    import stackbases
    stackbases.sheet = sheet                     # the stacking page shares this config
    n = sheet.render(portrait(letter), 2, 2, out,
                     extra=lambda c: stackbases.draw_page(c, standalone=False))
    return n, sheet.DESC_S, sheet.TW_BASE

# A: built natively for Letter - text stays at its true size
a = build("HKMJ-Letter-A-readable.pdf", tile=17.0)
# B: the A3 layout reproduced at Letter scale - everything 72.7% smaller
b = build("HKMJ-Letter-B-compact.pdf", factor=612.0/842.0)

print("A  readable : %d pages | detail text %.1fpt | tile %.1fpt" % a)
print("B  compact  : %d pages | detail text %.1fpt | tile %.1fpt" % b)
