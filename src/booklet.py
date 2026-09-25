# -*- coding: utf-8 -*-
"""Half-letter booklet.

reading  : 5.5 x 8.5 portrait panels, one per PDF page, in reading order (for proofing)
print    : the same panels imposed two-up on Letter landscape, saddle-stitch ordered
"""
import importlib, sys
import sheet, stackdata as sd, stackbases
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.colors import HexColor

PANEL = (5.5*inch, 8.5*inch)
NOTE  = ("HK Mahjong Scoring Sheet v3.0  ·  after the HKMJ Cheat Sheet v1.0 by "
         "/u/danma, expanded by J. Lee")


def cover(c, s, full):
    """Panel 1: title, how to use, the variant note, attribution."""
    import data
    y = s.PH - s.M - 18
    c.setFillColor(s.INK); c.setFont(s.HB, 30)
    c.drawString(s.M, y - 30, "Hong Kong")
    c.drawString(s.M, y - 64, "Mahjong")
    c.setFillColor(HexColor("#7e6c17")); c.drawString(s.M, y - 98, "Scoring Sheet")
    c.setFont("CJKB", 20); c.setFillColor(HexColor("#2f4f3f"))
    c.drawString(s.M, y - 130, "\u9999\u6e2f\u9ebb\u96c0\u6b63\u7d71\u724c\u578b")
    c.setStrokeColor(HexColor("#9a9384")); c.setLineWidth(1.2)
    c.line(s.M, y - 148, s.M + full, y - 148)

    HOW_HS, HOW_S, HOW_LD = 12.0, 9.6, 12.8
    ytxt = y - 176
    c.setFillColor(s.INK); c.setFont(s.HB, HOW_HS)
    c.drawString(s.M, ytxt, "How to Use")
    yy = ytxt - 17
    for i, t in enumerate(data.HOWTO):
        warn = (i == 1) or t.startswith(s.VAR_MARK)
        col  = HexColor("#8a2f20") if warn else HexColor("#3d382f")
        yy = s.para(c, u"\u2022  " + t, s.M, yy, full, s.HB if warn else s.HR,
                    HOW_S, HOW_LD, col) - 3
    h = s.varnote_h(full)
    s.draw_varnote(c, yy - 10, full)
    txt = ("Based on the HKMJ Cheat Sheet v1.0 (3 April 2025) by /u/danma, "
           "updated and expanded by J. Lee.")
    s.para(c, txt, s.M, s.M + 6 + s.para_h(txt, s.HO, 8.2, 10.2, full),
           full, s.HO, 8.2, 10.2, s.MUTED)


def scorepad(c, s, full):
    """Last panel: a 16-hand score grid."""
    c.setFillColor(s.INK); c.setFont(s.HB, s.HEAD_S*1.2)
    c.drawString(s.M, s.PH - s.M - s.HEAD_S*1.2, "Score Pad")
    c.setFont(s.HO, 8.6); c.setFillColor(s.MUTED)
    y = s.para(c, "One row per hand \u2014 a full game runs sixteen. Note the Fan, then each "
                  "player's running total.", s.M, s.PH - s.M - s.HEAD_S*1.9,
               full, s.HO, 8.6, 10.6, s.MUTED) - 8
    rows, cols = 16, ["Hand", "Fan", "", "", "", ""]
    wfan, wh = 34.0, 30.0
    wp = (full - wh - wfan)/4.0
    rh = (y - s.M - 14)/float(rows + 1)
    xs = [s.M, s.M + wh, s.M + wh + wfan]
    for i in range(4): xs.append(s.M + wh + wfan + wp*(i+1))
    c.setStrokeColor(HexColor("#c9c2ae")); c.setLineWidth(0.7)
    for r in range(rows + 2):
        yy = y - r*rh
        c.setLineWidth(1.1 if r in (0, 1) else 0.6)
        c.line(s.M, yy, s.M + full, yy)
    for x in xs + [s.M + full]:
        c.line(x, y, x, y - (rows + 1)*rh)
    c.setFillColor(s.INK); c.setFont(s.HB, 8.6)
    c.drawCentredString(s.M + wh/2, y - rh + 5, "#")
    c.drawCentredString(s.M + wh + wfan/2, y - rh + 5, "Fan")
    c.setFillColor(s.MUTED); c.setFont(s.HO, 8.0)
    for i in range(4):
        c.drawCentredString(xs[2] + wp*i + wp/2, y - rh + 5, "player")
    c.setFillColor(s.MUTED); c.setFont(s.HR, 8.4)
    for r in range(rows):
        c.drawCentredString(s.M + wh/2, y - (r+2)*rh + 5, str(r+1))


def _plan(heights, first, rest):
    """Greedy top-down fill; returns the panel each block lands on."""
    panels, y = [], first
    for h in heights:
        if y - h < 0 and panels:
            panels.append(None)
        if not panels or y - h < 0:
            y = rest
        panels.append(h); y -= h + GUTP[0]
    return None

def _simulate(heights, first, rest, gut):
    """Return (n panels, list of leftover space per panel) for this block order."""
    slack, y, n = [], first, 1
    for h in heights:
        if y - h < 0:
            slack.append(y); n += 1; y = rest
        y -= h + gut
    slack.append(y)
    return n, slack

def _order(blocks, first, rest, gut, pin=0):
    """Pick the block order that uses fewest panels, then fills them most evenly."""
    from itertools import permutations
    head, tail = blocks[:pin], blocks[pin:]
    best = None
    for perm in permutations(range(len(tail))):
        cand = head + [tail[i] for i in perm]
        n, slack = _simulate([b[0] for b in cand], first, rest, gut)
        inv = sum(1 for i in range(len(perm)) for j in range(i+1, len(perm))
                  if perm[i] > perm[j])          # distance from the given order
        score = (n, inv, max(slack) - min(slack))
        if best is None or score < best[0]: best = (score, cand)
    return best[1], best[0][0]

def _flow(c, s, blocks, top, ybot, full, heading, headfn):
    """Drop measured blocks down the panel, starting a new panel when one won't fit."""
    y = headfn(c, top) if heading else top
    for h, draw in blocks:
        if y - h < ybot:
            s.footer(c, NOTE); c.showPage()
            yield 1
            y = s.PH - s.M
        draw(c, s.M, y)
        y -= h + s.GUT
    yield 0

def build_reading(out, tile=13.0):
    importlib.reload(sheet)
    s = sheet
    s.TW_BASE = tile
    stackbases.sheet = s
    s.configure(PANEL, 1)
    c = canvas.Canvas(out, pagesize=s.PAGE)
    c.setTitle("Hong Kong Mahjong Scoring Sheet — booklet")
    c.setAuthor("J. Lee, based on the HKMJ Cheat Sheet v1.0 by /u/danma")
    full, ybot = s.PW - 2*s.M, s.M + 6
    n = 0

    # ---- cover -------------------------------------------------------------
    cover(c, s, full)
    s.footer(c, NOTE); c.showPage(); n += 1

    # ---- hands -------------------------------------------------------------
    pages = s.paginate(s.build_groups(), s.PH - s.M, s.PH - s.M, ybot, s.NCOL, s.HEAD_H + 2)
    for pi, grps in enumerate(pages):
        if pi: s.footer(c, NOTE); c.showPage()
        cont = None
        if pi and grps[0]["first"]["t"] != "head":
            cont = (grps[0]["sec"] + "  (continued)", grps[0]["pal"])
        s.place_page(c, grps, s.PH - s.M, s._yb(ybot, grps), cont)
    n += len(pages)
    s.footer(c, NOTE); c.showPage()

    # ---- reference ---------------------------------------------------------
    def head(cc, y, en, zh):
        cc.setFillColor(s.INK); cc.setFont(s.HB, s.HEAD_S*1.2)
        cc.drawString(s.M, y - s.HEAD_S*1.2, en)
        cc.setFont("CJKB", s.HEAD_S*0.85); cc.setFillColor(HexColor("#2f4f3f"))
        cc.drawString(s.M + pdfmetrics.stringWidth(en, s.HB, s.HEAD_S*1.2) + 12,
                      y - s.HEAD_S*1.2, zh)
        return y - s.HEAD_S*1.62

    # Side by side the two halves of the tile chart cap each other at ~5pt tiles
    # on a panel this narrow.  Stacked, each gets the full width; size them both
    # to whatever the nine-across suits row allows, so they stay consistent.
    tw = s._num_geom(full, 99.0)["tw"]
    blocks = [(s.m_nums(full, tw),    lambda cc, x, y: s.d_nums(cc, x, y, full, tw)),
              (s.m_honours(full, tw), lambda cc, x, y: s.d_honours(cc, x, y, full, tw)),
              (s.m_payment(full),   lambda cc, x, y: s.d_payment(cc, x, y, full)),
              (s.m_seat(full),      lambda cc, x, y: s.d_seat(cc, x, y, full)),
              (s.m_canto(full),     lambda cc, x, y: s.d_canto(cc, x, y, full)),
              (s.m_terms(full),     lambda cc, x, y: s.d_terms(cc, x, y, full))]
    n += 1
    for step in _flow(c, s, blocks, s.PH - s.M, ybot, full,
                      True, lambda cc, y: head(cc, y, "Reference", "牌章")):
        n += step
    s.footer(c, NOTE); c.showPage()

    # ---- stacking ----------------------------------------------------------
    sub = ("Each figure is the resulting TOTAL Fan for the whole hand, not the amount "
           "added; an arrow marks a total held at the 13 Fan Limit.")
    def shead(cc, y):
        y2 = head(cc, y, "Stacking Reference", "番組合")
        return s.para(cc, sub, s.M, y2, full, s.HO, 8.2, 10.0, s.MUTED) - 5
    cards = [(stackbases.card_h(b),
              (lambda b: lambda cc, x, y: stackbases.draw_card(cc, b, x, y, full))(b))
             for b in sd.BASES]
    n += 1
    for step in _flow(c, s, cards, s.PH - s.M, ybot, full, True, shead):
        n += step
    s.footer(c, NOTE); c.showPage(); n += 1
    scorepad(c, s, full)
    s.footer(c, NOTE)
    c.save()
    return n

if __name__ == "__main__":
    tile = float(sys.argv[1]) if len(sys.argv) > 1 else 13.0
    print("panels:", build_reading("HKMJ-Booklet-reading.pdf", tile))

def impose(src, out, ticks=True, flip_backs=False):
    """Two-up saddle-stitch imposition onto Letter landscape.

    flip_backs rotates every reverse side 180 degrees, for a duplex setting
    that flips the sheet the other way."""
    from pypdf import PdfReader, PdfWriter, PageObject, Transformation
    import io as _io
    r = PdfReader(src)
    idx = list(range(len(r.pages)))
    idx += [None] * ((-len(idx)) % 4)
    N = len(idx)
    order = []
    for i in range(N // 4):
        order.append((idx[N-1-2*i], idx[2*i]))        # outer side of sheet i
        order.append((idx[2*i+1],   idx[N-2-2*i]))    # inner side
    SW, SH = 792.0, 612.0
    mark = None
    if ticks:
        buf = _io.BytesIO()
        cc = canvas.Canvas(buf, pagesize=(SW, SH))
        cc.setStrokeColor(HexColor("#b9b2a0")); cc.setLineWidth(0.5)
        cc.line(SW/2, SH, SW/2, SH - 9); cc.line(SW/2, 0, SW/2, 9)
        cc.save(); buf.seek(0)
        mark = PdfReader(buf).pages[0]
    w = PdfWriter()
    for left, right in order:
        pg = PageObject.create_blank_page(width=SW, height=SH)
        back = flip_backs and (len(w.pages) % 2 == 1)
        for dx, i in ((0.0, left), (SW/2, right)):
            if i is None: continue
            t = Transformation().translate(dx, 0)
            if back: t = t.rotate(180).translate(SW, SH)
            pg.merge_transformed_page(r.pages[i], t)
        if mark is not None: pg.merge_page(mark)
        w.add_page(pg)
    with open(out, "wb") as f: w.write(f)
    return len(order), N, order
