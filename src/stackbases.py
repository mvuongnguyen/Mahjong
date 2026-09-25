# -*- coding: utf-8 -*-
"""Stacking reference: each base hand with everything that can be added to it."""
import importlib, sheet, stackdata as sd
from reportlab.lib.pagesizes import letter, portrait
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.colors import HexColor

LH, TOTW = 11.0, 30.0

def card_h(base):
    return 39 + len(sd.stacks_for(base))*LH + 9

def draw_card(c, base, x, y, w):
    s = sheet
    rows = sd.stacks_for(base)
    h = card_h(base)
    c.setFillColor(HexColor("#ffffff")); c.setStrokeColor(s.LINE); c.setLineWidth(1.0)
    c.roundRect(x, y - h, w, h, 5, fill=1, stroke=1)
    c.setFillColor(s.INK); c.setFont(s.HB, 12.6)
    c.drawString(x + 11, y - 18, base)
    c.setFont(s.HB, 12.6); c.setFillColor(HexColor("#7e6c17"))
    c.drawRightString(x + w - 11, y - 18, "%d Fan" % sd.fan(base))
    c.setFont(s.HO, 7.9); c.setFillColor(s.MUTED)
    c.drawString(x + 11, y - 29, sd.DESC.get(base, ""))
    c.setStrokeColor(HexColor("#d8d0bb")); c.setLineWidth(0.6)
    c.line(x + 11, y - 35, x + w - 11, y - 35)
    yy = y - 43
    for n, v, tot, note, cap in rows:
        c.setFont(s.HR, 8.8); c.setFillColor(s.INK)
        c.drawString(x + 14, yy - 9, "+ " + n)
        c.setFont(s.HB, 9.0); c.setFillColor(HexColor("#b1482c") if cap else s.INK)
        c.drawRightString(x + w - 11, yy - 9, ("= %d ↑" % tot) if cap else ("= %d" % tot))
        if note:                        # only if it genuinely fits beside the total
            nx = x + 14 + pdfmetrics.stringWidth("+ " + n, s.HR, 8.8) + 7
            room = (x + w - 11 - TOTW) - nx
            for fs in (7.4, 6.9, 6.4):
                if pdfmetrics.stringWidth(note, s.HO, fs) <= room:
                    c.setFont(s.HO, fs); c.setFillColor(s.MUTED)
                    c.drawString(nx, yy - 9, note); break
        yy -= LH
    return h

def draw_page(c, standalone=True):
    """Paint the stacking page onto an existing canvas."""
    s = sheet
    c.setFillColor(s.INK); c.setFont(s.HB, 17.5)
    c.drawString(s.M, s.PH - s.M - 17.5, "Stacking Reference")
    c.setFont("CJKB", 13.5); c.setFillColor(HexColor("#2f4f3f"))
    c.drawString(s.M + pdfmetrics.stringWidth("Stacking Reference", s.HB, 17.5) + 12,
                 s.PH - s.M - 17.5, "番組合")
    sub = ("Every base here clears a 3 Fan minimum on its own \u2014 Mixed Flush is the "
           "cheapest and most forgiving, which is why a stalled 1 Fan hand so often becomes "
           "one. Each figure is the resulting TOTAL Fan for the whole hand, not the amount "
           "added; an arrow marks a "
           "total held at the 13 Fan Limit.")
    ytxt = s.para(c, sub, s.M, s.PH - s.M - 22, s.PW - 2*s.M, s.HO, 9.0, 11.0, s.MUTED)
    top  = ytxt - 6
    ybot = s.M + 16
    cw   = (s.PW - 2*s.M - s.GUT)/2.0

    # exhaustive best split across two columns: both must fit, then balance
    avail = top - ybot
    best = None
    for mask in range(1 << len(sd.BASES)):
        a = [b for i, b in enumerate(sd.BASES) if mask >> i & 1]
        z = [b for i, b in enumerate(sd.BASES) if not mask >> i & 1]
        if not a or not z: continue
        ha = sum(card_h(b) for b in a) + 12*(len(a)-1)
        hz = sum(card_h(b) for b in z) + 12*(len(z)-1)
        if ha > avail or hz > avail: continue
        score = (abs(ha - hz), max(ha, hz))
        if best is None or score < best[0]: best = (score, a, z, ha, hz)
    if best is None:
        raise SystemExit("no two-column split fits; the sheet needs a second page")
    _, ca, cz, ha, hz = best
    cols, heights = [ca, cz], [ha, hz]
    for j, col in enumerate(cols):
        x, y = s.M + j*(cw + s.GUT), top
        for b in col:
            y -= draw_card(c, b, x, y, cw) + 12
    if standalone:                    # inside the scoring sheet the usual footer applies
        c.setFont(s.HO, 8.0); c.setFillColor(s.MUTED)
        c.drawString(s.M, s.M - 8,
            "Companion to the Hong Kong Mahjong Scoring Sheet v3.0  ·  Fan values follow "
            "that sheet  ·  based on the HKMJ Cheat Sheet v1.0 by /u/danma, expanded by J. Lee")
    return heights, top - ybot

def build(out):
    """Standalone one-page PDF."""
    importlib.reload(sheet); sheet.TW_BASE = 17.0
    sheet.configure(portrait(letter), 2)
    globals()["sheet"] = sheet
    c = canvas.Canvas(out, pagesize=sheet.PAGE)
    c.setTitle("Hong Kong Mahjong Stacking Reference")
    c.setAuthor("J. Lee, companion to the HK Mahjong Scoring Sheet v3.0")
    r = draw_page(c, standalone=True)
    c.save()
    return r

if __name__ == "__main__":
    h, cap = build("HK-Mahjong-Stacking-Reference.pdf")
    print("column loads %.0f / %.0f pt against %.0f available" % (h[0], h[1], cap))
