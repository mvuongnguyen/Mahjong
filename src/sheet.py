# -*- coding: utf-8 -*-
import os, re, math, itertools
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape, portrait
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import tileart, data, mkfont

# ================= fonts =================
CJK_CHARS = set(chr(i) for i in range(0x20, 0x7F))
def harvest(s):
    for ch in s:
        if ord(ch) > 0x2E80: CJK_CHARS.add(ch)
for sec in data.SECTIONS:
    harvest(sec["title"])
    for e in sec["entries"]:
        for k in ("cn","ds","rep","ex"): harvest(e.get(k,""))
        for _s, _c in e.get("opts", []): harvest(_c)
for a,b in data.TERMS: harvest(a); harvest(b)
for a,b,c in data.SUITROWS: harvest(a); harvest(b)
for s in data.PAYNOTES + data.TERMINOLOGY + data.HOWTO: harvest(s)
harvest("牌章全銃制正花食糊雞和香港麻雀正統牌型東南西北中發白春夏秋冬梅蘭菊竹一二三四五六七八九萬筒索風花季番組合")
mkfont.build(mkfont.find("serif"), 3, CJK_CHARS, "cjkb.ttf", "MJCJKB")
mkfont.build(mkfont.find("sans"),  4, CJK_CHARS, "cjkr.ttf", "MJCJKR")
pdfmetrics.registerFont(TTFont("CJKB", "cjkb.ttf"))
pdfmetrics.registerFont(TTFont("CJKR", "cjkr.ttf"))
HB, HR, HO = "Helvetica-Bold", "Helvetica", "Helvetica-Oblique"
INK, MUTED, LINE, REPC = HexColor("#1b1a17"), HexColor("#5d564a"), HexColor("#c9c1ad"), HexColor("#8a2f20")

# ================= sizing (text +40%, tiles +25% over v2.0) =================
M, GUT      = 22.0, 16.0
PADX, PADY  = 7.0, 4.5
BADGE       = 13.0
KIDIND      = 34.0                      # deeper child indent
NAME_S, DESC_S, REP_S, EX_S = 11.0, 8.5, 8.2, 7.9
NAME_L, DESC_L, REP_L, EX_L = 12.6, 10.2, 9.8, 9.5
HEAD_S, HEAD_H = 15.5, 21.5
OPT_S, OPT_L = 9.6, 12.0
OPT_GAP     = 0.60
OPT_CAPGAP  = 0.30          # caption -> its own tiles below, x OPT_S
OPT_ROWGAP  = 0.70          # tiles -> the NEXT caption, x OPT_S
SEC_GAP     = 13.0        # extra space where one section meets the next
MIN_SECOND_COL = 0.35     # never strand the right column below this fill
TW_BASE     = 24.0                      # tile width
ADV, SEP    = 0.86, 0.24
TRI         = 1.35                      # winning-tile triangle scale
FOOT        = 30.0

PAGE = PW = PH = None
NCOL = COLW = None

def configure(pagesize, ncol):
    global PAGE, PW, PH, NCOL, COLW
    PAGE = pagesize; PW, PH = pagesize; NCOL = ncol
    COLW = (PW - 2*M - (ncol-1)*GUT) / float(ncol)

# ================= mixed Latin / CJK text =================
CJK_FOR = {"Helvetica":"CJKR","Helvetica-Bold":"CJKB","Helvetica-Oblique":"CJKR",
           "Helvetica-BoldOblique":"CJKB",
           "CJKR":"CJKR","CJKB":"CJKB"}
BOLD_FOR = {"Helvetica":"Helvetica-Bold", "Helvetica-Oblique":"Helvetica-BoldOblique",
            "Helvetica-Bold":"Helvetica-Bold", "Helvetica-BoldOblique":"Helvetica-BoldOblique"}

def _bold_split(txt):
    """Split on <b>..</b>: returns (segment, is_bold) in order.
    Tags rather than asterisks, because asterisks are used as footnote marks."""
    out = []
    for i, part in enumerate(re.split(r"</?b>", txt)):
        if part: out.append((part, i % 2 == 1))
    return out

def _tokens(txt, font):
    if "<b>" in txt:
        atoms = []
        for seg, bold in _bold_split(txt):
            atoms.extend(_tokens_plain(seg, BOLD_FOR.get(font, font) if bold else font))
        return atoms
    return _tokens_plain(txt, font)

def _tokens_plain(txt, font):
    cf = CJK_FOR.get(font, "CJKR"); out, buf = [], ""
    for ch in txt:
        if ord(ch) > 0x2E80:
            if buf: out.append((buf, font)); buf = ""
            out.append((ch, cf))
        else: buf += ch
    if buf: out.append((buf, font))
    atoms = []
    for s, f in out:
        if f == font:
            parts = s.split(" ")
            for k, p in enumerate(parts):
                if p: atoms.append((p, f, False))
                if k < len(parts)-1: atoms.append((" ", f, True))
        else: atoms.append((s, f, False))
    return atoms

def wrap_mixed(txt, font, size, width):
    lines, cur, w = [], [], 0.0
    for atom, f, sp in _tokens(txt, font):
        aw = pdfmetrics.stringWidth(atom, f, size)
        if sp and not cur: continue
        if w + aw > width and cur:
            while cur and cur[-1][2]: cur.pop()
            lines.append(cur); cur, w = [], 0.0
            if sp: continue
        cur.append((atom, f, sp)); w += aw
    if cur: lines.append(cur)
    return lines

def para(c, txt, x, y, width, font, size, lead, color):
    c.setFillColor(color)
    for ln in wrap_mixed(txt, font, size, width):
        cx = x
        for atom, f, _ in ln:
            c.setFont(f, size); c.drawString(cx, y - size, atom)
            cx += pdfmetrics.stringWidth(atom, f, size)
        y -= lead
    return y

def para_h(txt, font, size, lead, width):
    return len(wrap_mixed(txt, font, size, width)) * lead

# ================= tiles =================
VBW, VBH = tileart.VBW, tileart.VBH
_readers = {}
def reader(code):
    if code not in _readers:
        _readers[code] = ImageReader(tileart.tile_png(code))
    return _readers[code]

def art_text(c, txt, ax, ay, size_art, color, tx, ty, sc, font="CJKB", align="c"):
    sx = tileart.PX + ax*(tileart.PW/100.0)
    sy = tileart.PY + ay*(tileart.PH/130.0)
    px, py = tx + sx*sc, ty + (VBH - sy)*sc
    fs = size_art*(tileart.PW/100.0)*sc
    c.setFont(font, fs); c.setFillColor(HexColor(color))
    w = pdfmetrics.stringWidth(txt, font, fs)
    if align == "c": px -= w/2.0
    elif align == "r": px -= w
    c.drawString(px, py - fs*0.36, txt)

def draw_tile(c, code, x, y, tw):
    win = code.endswith("*")
    if win: code = code[:-1]
    th, sc = tw*VBH/VBW, tw/VBW
    c.drawImage(reader(code), x, y, width=tw, height=th, mask="auto")
    m = re.match(r"^([1-9])([psm])$", code)
    if m and m.group(2) == "m":
        n = int(m.group(1))
        art_text(c, tileart.NUMS[n-1], 50, 31, 72, "#17324f", x, y, sc)
        art_text(c, "萬", 50, 94, 70, "#bf3226", x, y, sc)
    elif code in tileart.WINDS:
        art_text(c, tileart.WINDS[code], 50, 65, 86, "#17324f", x, y, sc)
    elif code == "dr": art_text(c, "中", 50, 65, 86, "#bf3226", x, y, sc)
    elif code == "dg": art_text(c, "發", 50, 65, 86, "#12693c", x, y, sc)
    elif code in tileart.FLOWERS:
        num, name, col = tileart.FLOWERS[code]
        art_text(c, num,  15, 17, 27, col, x, y, sc)
        art_text(c, name, 85, 17, 27, col, x, y, sc)
    if win:
        cx, b = x + tw*0.5, y - tw*0.10*TRI
        c.setFillColor(HexColor("#bf3226"))
        p = c.beginPath()
        p.moveTo(cx - tw*0.15*TRI, b); p.lineTo(cx + tw*0.15*TRI, b)
        p.lineTo(cx, b + tw*0.20*TRI); p.close()
        c.drawPath(p, fill=1, stroke=0)
    return th

def layout_hand(spec, maxw, tw):
    rows, cur, xo = [], [], 0.0
    for tok in spec.split():
        if tok == "|":
            xo += tw*SEP; continue
        if xo + tw > maxw and cur:
            rows.append(cur); cur, xo = [], 0.0
        cur.append((tok, xo)); xo += tw*ADV
    if cur: rows.append(cur)
    return rows


def layout_opts(opts, maxw, tw):
    """Alternative sets shown side by side, each with its own caption."""
    rows, cur, x = [], [], 0.0
    gap = tw*OPT_GAP
    for i, (spec, cap) in enumerate(opts):
        toks = spec.split()
        n    = len([tk for tk in toks if tk != "|"])
        nsep = len([tk for tk in toks if tk == "|"])
        w    = (n-1)*ADV*tw + tw + nsep*SEP*tw
        cw = max(w, pdfmetrics.stringWidth(cap, HB, OPT_S))
        if cur and x + cw > maxw:
            rows.append(cur); cur, x = [], 0.0
        cur.append((i, x, w, cw)); x += cw + gap
    if cur: rows.append(cur)
    return rows

def _opt_row_h(tw):
    """One example row: the tiles, a small gap, its caption, then a larger
    gap before the next example - so each caption sits with its own tiles."""
    return tw*VBH/VBW + OPT_S*(OPT_CAPGAP + 1.0 + OPT_ROWGAP)

def opts_h(rows, tw):
    return len(rows) * _opt_row_h(tw) if rows else 0.0

def draw_opts(c, opts, rows, x0, ytop, tw, capcol):
    """Each example is labelled above its tiles, so the name is read first."""
    th, y = tw*VBH/VBW, ytop
    for row in rows:
        y -= OPT_S                                   # caption baseline
        c.setFont(HB, OPT_S); c.setFillColor(HexColor(capcol))
        for (i, xo, w, cw) in row:
            c.drawCentredString(x0 + xo + cw/2.0, y, opts[i][1])
        y -= OPT_S*OPT_CAPGAP + th                   # tile baseline
        for (i, xo, w, cw) in row:
            tx = x0 + xo + (cw - w)/2.0
            for tk in opts[i][0].split():
                if tk == "|":
                    tx += tw*SEP; continue
                draw_tile(c, tk, tx, y, tw); tx += tw*ADV
        y -= OPT_S*OPT_ROWGAP                        # space before the next example
    return y

def hand_h(rows, tw):
    return len(rows) * (tw*VBH/VBW + tw*0.26) if rows else 0.0

def draw_hand(c, rows, x, ytop, tw):
    th, y = tw*VBH/VBW, ytop
    for row in rows:
        y -= th
        for code, xo in row: draw_tile(c, code, x + xo, y, tw)
        y -= tw*0.26
    return y

# ================= entry cards =================

VAR_MARK = "\u2020"        # hands whose rules vary by table; see the page footnote

def en_name(e):
    return e["en"] + ("  " + VAR_MARK if e.get("var") else "")

def name_layout(e, inner):
    """Fit "English 中文" into the card: shrink a little, then wrap if needed."""
    size = NAME_S
    def widths(s):
        return (pdfmetrics.stringWidth(en_name(e), HB, s),
                pdfmetrics.stringWidth(e["cn"], "CJKB", s),
                pdfmetrics.stringWidth("  ", HB, s))
    we, wc, ws = widths(size)
    while we + ws + wc > inner and size > NAME_S * 0.78:
        size -= 0.25
        we, wc, ws = widths(size)
    two = (we + ws + wc) > inner          # still too wide -> Chinese on its own line
    return size, two

def entry_geom(e, colw):
    ind   = KIDIND if e.get("kid") else 0.0
    w     = colw - ind
    tx    = PADX + 2*BADGE + 6
    inner = w - tx - PADX
    hw    = w - 2*PADX
    tw = TW_BASE
    if e.get("opts"):
        rows = layout_opts(e["opts"], hw, tw); is_opts = True
    else:
        is_opts = False
        rows = layout_hand(e.get("h",""), hw, tw)
        # an unusually long hand shrinks its own tiles rather than wrapping
        while len(rows) > 1 and tw > TW_BASE * 0.70:
            tw -= 0.5
            rows = layout_hand(e.get("h",""), hw, tw)
    nsize, ntwo = name_layout(e, inner)
    nlead = NAME_L * (nsize / NAME_S)
    h  = PADY + nlead * (2 if ntwo else 1)
    h += para_h(e["ds"], HR, DESC_S, DESC_L, inner)
    if e.get("rep"): h += 2 + para_h(e["rep"], HB, REP_S, REP_L, inner - 7)
    h += 4 + (opts_h(rows, tw) if is_opts else hand_h(rows, tw))
    if e.get("ex"):  h += para_h(e["ex"], HO, EX_S, EX_L, w - 2*PADX)
    h += PADY
    return {"ind":ind,"w":w,"tx":tx,"inner":inner,"hw":hw,"tw":tw,"rows":rows,
            "opts":is_opts,"nsize":nsize,"ntwo":ntwo,"nlead":nlead,
            "h":max(h, 2*BADGE+2*PADY)}

def draw_entry(c, e, g, x, ytop, pal):
    bg, bg2, bd, badge = [HexColor(v) for v in pal]
    x0, h = x + g["ind"], g["h"]
    c.setFillColor(bg2 if e.get("kid") else bg)
    c.setStrokeColor(bd); c.setLineWidth(1.4)
    c.roundRect(x0, ytop - h, g["w"], h, 5, fill=1, stroke=1)
    if e.get("kid"):                                   # bold elbow connector
        ARR = HexColor("#2f2b24")
        c.setStrokeColor(ARR); c.setLineWidth(3.0); c.setLineCap(1)
        ex, ey = x + 11, ytop - 26
        c.line(ex, ytop + 5, ex, ey)
        c.line(ex, ey, x0 - 9, ey)
        p = c.beginPath()
        p.moveTo(x0 - 0.5, ey); p.lineTo(x0 - 11, ey + 6.5); p.lineTo(x0 - 11, ey - 6.5); p.close()
        c.setFillColor(ARR); c.drawPath(p, fill=1, stroke=0)
        c.setLineCap(0)
    bcx, bcy = x0 + PADX + BADGE, ytop - PADY - BADGE
    c.setFillColor(badge); c.circle(bcx, bcy, BADGE, fill=1, stroke=0)
    fs = 13.2 if len(e["f"]) < 3 else 10.6
    c.setFont(HB, fs); c.setFillColor(HexColor("#ffffff"))
    c.drawCentredString(bcx, bcy - fs*0.35, e["f"])
    tx, y = x0 + g["tx"], ytop - PADY
    ns, ntwo, nlead = g["nsize"], g["ntwo"], g["nlead"]
    c.setFont(HB, ns); c.setFillColor(INK)
    c.drawString(tx, y - ns, e["en"])
    if e.get("var"):                       # the dagger picks up the warning colour
        c.setFillColor(REPC)
        c.drawString(tx + pdfmetrics.stringWidth(e["en"] + "  ", HB, ns), y - ns, VAR_MARK)
    if ntwo:
        y -= nlead
        c.setFont("CJKB", ns); c.setFillColor(HexColor("#3a352c"))
        c.drawString(tx, y - ns, e["cn"])
    else:
        nw = pdfmetrics.stringWidth(en_name(e) + "  ", HB, ns)
        c.setFont("CJKB", ns); c.setFillColor(HexColor("#3a352c"))
        c.drawString(tx + nw, y - ns, e["cn"])
    y -= nlead
    y = para(c, e["ds"], tx, y, g["inner"], HR, DESC_S, DESC_L, HexColor("#3d382f"))
    if e.get("rep"):
        y -= 2; ytr = y
        y = para(c, e["rep"], tx + 7, y, g["inner"] - 7, HB, REP_S, REP_L, REPC)
        c.setStrokeColor(HexColor("#c28a7c")); c.setLineWidth(2.4)
        c.line(tx + 2.2, ytr - 1, tx + 2.2, y + 1)
    y -= 4
    if g.get("opts"):
        y = draw_opts(c, e["opts"], g["rows"], x0 + PADX, y, g["tw"], pal[3])
    else:
        y = draw_hand(c, g["rows"], x0 + PADX, y, g["tw"])
    if e.get("ex"):
        para(c, e["ex"], x0 + PADX, y + 2, g["w"] - 2*PADX, HO, EX_S, EX_L, HexColor("#6b6252"))

# ================= masthead =================
TITLE_EN = "Hong Kong Mahjong Scoring Sheet"
TITLE_ZH = "香港麻雀正統牌型"
DASH     = "  —  "

def head_parts(ts):
    """Title, dash and Chinese name all sit on one line; return their widths."""
    return (pdfmetrics.stringWidth(TITLE_EN, HB, ts),
            pdfmetrics.stringWidth(DASH, HB, ts*0.72),
            pdfmetrics.stringWidth(TITLE_ZH, "CJKB", ts*0.82))

def masthead(c, y):
    TS = 27                            # title size; shrinks if the line runs long
    while sum(head_parts(TS)) > (PW - 2*M) * 0.78 and TS > 15.0:
        TS -= 0.5
    wt, wd, wz = head_parts(TS)
    base = y - TS + 2
    c.setFillColor(INK); c.setFont(HB, TS)
    c.drawString(M, base, TITLE_EN)
    c.setFont(HB, TS*0.72); c.setFillColor(HexColor("#9a9384"))
    c.drawString(M + wt, base, DASH)
    c.setFont("CJKB", TS*0.82); c.setFillColor(HexColor("#2f4f3f"))
    c.drawString(M + wt + wd, base, TITLE_ZH)
    tw_title = wt + wd + wz
    bx = M + tw_title + 34
    bw = PW - M - bx
    HOW_F  = 0.80                      # How to Use box, relative to the old size
    HOW_HS = 13.0*HOW_F                # heading
    HOW_S  = 11.5*HOW_F                # bullets
    HOW_LD = 14.6*HOW_F                # line step
    HOW_T  = 19.0*HOW_F                # top pad to the heading baseline
    HOW_G  = 16.0*HOW_F                # heading baseline to the first bullet
    HOW_B  = 13.0*HOW_F                # bottom pad
    bh = HOW_T + HOW_G + HOW_LD*(len(data.HOWTO) - 1) + HOW_B
    if bw < 400:                           # portrait: put the box under the title
        bx, bw = M, PW - 2*M
        c.setFillColor(HexColor("#f0ede3")); c.setStrokeColor(HexColor("#9a9384")); c.setLineWidth(1.4)
        c.roundRect(bx, y - TS*1.45 - bh, bw, bh, 4, fill=1, stroke=1)
        ytxt = y - TS*1.45
    else:
        c.setFillColor(HexColor("#f0ede3")); c.setStrokeColor(HexColor("#9a9384")); c.setLineWidth(1.4)
        c.roundRect(bx, y - bh, bw, bh, 4, fill=1, stroke=1)
        ytxt = y
    c.setFillColor(INK); c.setFont(HB, HOW_HS)
    c.drawString(bx + 13, ytxt - HOW_T, "How to Use")
    yy = ytxt - HOW_T - HOW_G
    for i, t in enumerate(data.HOWTO):
        warn = (i == 1) or t.startswith(VAR_MARK)
        c.setFillColor(HexColor("#8a2f20") if warn else HexColor("#3d382f"))
        c.setFont(HB if warn else HR, HOW_S)
        c.drawString(bx + 13, yy, u"•  " + t)
        yy -= HOW_LD
    return min(ytxt - bh - 14, y - TS*1.45 - 14)

VARNOTE = ("\u2020  Only played in certain variants \u2014 agree these before the first deal. "
           "Kong, Knitted Tiles, Lesser Honours and Greater Honours follow MCR (Chinese "
           "Official) scoring; Seven Pairs and Luxury Seven Pairs come from Taiwanese play.")

def varnote_h(w):
    return para_h(VARNOTE, HB, REP_S, REP_L, w - 14) + 8

def draw_varnote(c, ytop, w):
    """One shared note for every hand marked with a dagger."""
    h = varnote_h(w)
    c.setFillColor(HexColor("#fbf4f2")); c.setStrokeColor(HexColor("#c28a7c"))
    c.setLineWidth(1.0)
    c.roundRect(M, ytop - h, w, h, 3, fill=1, stroke=1)
    para(c, VARNOTE, M + 7, ytop - 4, w - 14, HB, REP_S, REP_L, REPC)
    return h

def footer(c, note):
    """The note shrinks if it would run into the page number."""
    pg = "Page %d" % c.getPageNumber()
    c.setFont(HB, 9.0)
    room = (PW - 2*M) - pdfmetrics.stringWidth(pg, HB, 9.0) - 22
    fs = 9.0
    while fs > 6.0 and pdfmetrics.stringWidth(note, HO, fs) > room:
        fs -= 0.25
    c.setFillColor(MUTED)
    c.setFont(HO, fs); c.drawString(M, M - 8, note)
    c.setFont(HO, 9.0); c.drawRightString(PW - M, M - 8, pg)

# ================= page flow =================
def build_groups():
    blocks = []
    for sec in data.SECTIONS:
        blocks.append({"t":"head","title":sec["title"],"h":HEAD_H,"pal":sec["pal"],"sec":sec["title"]})
        for e in sec["entries"]:
            g = entry_geom(e, COLW)
            blocks.append({"t":"ent","e":e,"g":g,"h":g["h"]+6.0,"pal":sec["pal"],"sec":sec["title"]})
    groups, i = [], 0
    while i < len(blocks):
        b = blocks[i]; run = [b]; j = i + 1
        if b["t"] == "head":
            while j < len(blocks) and blocks[j]["t"] == "ent":
                run.append(blocks[j]); j += 1
                if j < len(blocks) and blocks[j]["t"] == "ent" and blocks[j]["e"].get("kid"): continue
                break
        else:
            while j < len(blocks) and blocks[j]["t"] == "ent" and blocks[j]["e"].get("kid"):
                run.append(blocks[j]); j += 1
        groups.append({"run":run, "h":sum(x["h"] for x in run), "first":b,
                       "pal":b["pal"], "sec":b["sec"]})
        i = j
    return groups


def tops_for(ytop, ncol, cont, head_h):
    """Column tops for a page; column 0 loses room to a 'continued' header."""
    return [ytop - (head_h if cont else 0.0)] + [ytop]*(ncol-1)

def pack_cols(grps, tops, ybot, ncol, target=None):
    """Pack groups into columns. Returns (cols, ok).

    With two columns every split point can be tried, so we choose properly:
    break between sections where possible, then fill the first column the way
    a newspaper reads, without stranding the second column near-empty."""
    cols = None
    if ncol == 2 and len(grps) > 1:
        cands = []
        for k in range(1, len(grps)):
            a, b = grps[:k], grps[k:]
            ua, ub = sum(g["h"] for g in a), sum(g["h"] for g in b)
            if ua > tops[0] - ybot + 0.5 or ub > tops[1] - ybot + 0.5:
                continue
            clean = 0 if a[-1]["sec"] != b[0]["sec"] else 1
            cands.append((clean, ua, ub, [a, b]))
        if cands:
            # 1. a break between sections beats one inside a section
            best_clean = min(c[0] for c in cands)
            pool = [c for c in cands if c[0] == best_clean]
            # 2. then fill the first column as a newspaper would, but never
            #    leave the second column looking abandoned
            floor = MIN_SECOND_COL * (tops[1] - ybot)
            filled = [c for c in pool if c[2] >= floor]
            if filled:
                cols = max(filled, key=lambda c: c[1])[3]
            else:
                cols = min(pool, key=lambda c: abs(c[1] - c[2]))[3]
    if cols is None:
        cols = [[] for _ in range(ncol)]
        col, used = 0, 0.0
        for g in grps:
            avail = tops[col] - ybot
            need_new = used + g["h"] > avail
            want_new = target is not None and used + g["h"] > target*1.04
            if cols[col] and (need_new or want_new) and col < ncol - 1:
                col += 1; used = 0.0
            cols[col].append(g); used += g["h"]
    # A section header stranded at the foot of a column, with the rest of its
    # section in the next column, reads as a broken section. Push it across
    # when the next column can take it.
    for ci in range(ncol - 1):
        if not cols[ci] or not cols[ci + 1]:
            continue
        last = cols[ci][-1]
        if last["run"][0]["t"] != "head":
            continue
        if cols[ci + 1][0]["sec"] != last["sec"]:
            continue
        room = (tops[ci + 1] - ybot) - sum(g["h"] for g in cols[ci + 1])
        if last["h"] <= room + 0.5:
            cols[ci].pop()
            cols[ci + 1].insert(0, last)

    ok = True
    for ci in range(ncol):
        if sum(g["h"] for g in cols[ci]) > (tops[ci] - ybot) + 0.5: ok = False
    return cols, ok

def page_fits(grps, ytop, ybot, ncol, cont, head_h):
    return pack_cols(grps, tops_for(ytop, ncol, cont, head_h), ybot, ncol)[1]

def _fill(groups, caps, limit):
    """Greedy fill honouring both a soft per-page limit and the hard capacity."""
    pages, cur, used, pi = [], [], 0.0, 0
    for g in groups:
        cap = caps[pi] if pi < len(caps) else caps[-1]
        if cur and (used + g["h"] > min(cap, limit)):
            pages.append(cur); cur, used, pi = [], 0.0, pi + 1
            cap = caps[pi] if pi < len(caps) else caps[-1]
        cur.append(g); used += g["h"]
    if cur: pages.append(cur)
    return pages

def _needs_header(page):
    return bool(page) and page[0]["first"]["t"] != "head"

def has_var(grps):
    """Does this set of groups contain a hand marked with the dagger?"""
    return any(b["t"] == "ent" and b["e"].get("var") for g in grps for b in g["run"])

def _yb(ybot, grps):
    """ybot may be a pair (plain, with-note) - a page only reserves the note if it needs one."""
    if isinstance(ybot, tuple):
        return ybot[1] if has_var(grps) else ybot[0]
    return ybot

def _greedy(groups, ytop1, ytopn, ybot, ncol, head_h, limit=None):
    pages, cur, ytop = [], [], ytop1
    for g in groups:
        trial = cur + [g]
        cont = bool(pages) and _needs_header(trial)
        load = sum(x["h"] for x in trial) + (head_h if cont else 0.0)
        too_big = (limit is not None and cur and load > limit)
        if cur and (too_big or not page_fits(trial, ytop, _yb(ybot, trial), ncol, cont, head_h)):
            pages.append(cur); cur, ytop = [g], ytopn
        else:
            cur = trial
    if cur: pages.append(cur)
    return pages


def _by_section(groups, ytop1, ytopn, ybot, ncol, head_h):
    """Candidate pagination that only ever breaks between sections."""
    secs, cur = [], []
    for g in groups:
        if cur and g["sec"] != cur[-1]["sec"]:
            secs.append(cur); cur = []
        cur.append(g)
    if cur: secs.append(cur)
    pages, page, ytop = [], [], ytop1
    for blockk in secs:
        trial = page + blockk
        if page and not page_fits(trial, ytop, _yb(ybot, trial), ncol, False, head_h):
            pages.append(page); page, ytop = list(blockk), ytopn
        else:
            page = trial
        if not page_fits(page, ytop, _yb(ybot, page), ncol, False, head_h):
            return None                      # a single section will not fit a page
    if page: pages.append(page)
    return pages

def paginate(groups, ytop1, ytopn, ybot, ncol, head_h):
    """Greedy pages validated against the real column packing, then balanced."""
    base = _greedy(groups, ytop1, ytopn, ybot, ncol, head_h)
    n = len(base)
    total = sum(g["h"] for g in groups)

    def break_flags(pg):
        """1 per page break that lands mid-section, in page order."""
        return tuple(1 if (pg[i] and pg[i+1] and pg[i][-1]["sec"] == pg[i+1][0]["sec"]) else 0
                     for i in range(len(pg) - 1))

    best, best_score = base, None
    # a pagination that never splits a section is ideal when it needs no more pages
    sec_cand = _by_section(groups, ytop1, ytopn, ybot, ncol, head_h)
    if sec_cand and len(sec_cand) <= n:
        loads = [sum(g["h"] for g in p) for p in sec_cand]
        best, best_score = sec_cand, (0, tuple(0 for _ in range(len(sec_cand)-1)),
                                      max(loads) - min(loads))
    mult = 1.00
    while mult <= 1.80:
        pg = _greedy(groups, ytop1, ytopn, ybot, ncol, head_h, (total/float(n))*mult)
        if len(pg) <= n:
            loads = [sum(g["h"] for g in p) for p in pg]
            # fewest sections broken, then break as late as possible so the
            # early pages hold whole sections, then even page loads
            flags = break_flags(pg)
            score = (sum(flags), flags, max(loads) - min(loads))
            if best_score is None or score < best_score:
                best, best_score = pg, score
        mult += 0.05
    return best

def place_page(c, grps, ytop, ybot, cont):
    head_h = HEAD_H + 2
    tops   = tops_for(ytop, NCOL, bool(cont), head_h)
    total  = sum(g["h"] for g in grps)
    cols, ok = pack_cols(grps, tops, ybot, NCOL, total/float(NCOL))
    if not ok:                                   # balance overflowed -> pack tight
        cols, ok = pack_cols(grps, tops, ybot, NCOL, None)
    if cont:
        title, pal = cont
        c.setFillColor(HexColor(pal[3])); c.setFont(HB, HEAD_S)
        c.drawString(M, ytop - HEAD_S + 1, title)
        c.setStrokeColor(HexColor(pal[2])); c.setLineWidth(2.6)
        c.line(M, ytop - HEAD_S - 4, M + COLW, ytop - HEAD_S - 4)
    for ci in range(NCOL):
        x, y = M + ci*(COLW + GUT), tops[ci]
        n     = len(cols[ci])
        slack = (tops[ci] - ybot) - sum(g["h"] for g in cols[ci])
        # a new section gets a wider gap than the cards inside one section
        nsec  = sum(1 for gi in range(1, n) if cols[ci][gi]["sec"] != cols[ci][gi-1]["sec"])
        secx  = min(SEC_GAP, slack/float(nsec)) if nsec else 0.0
        secx  = max(0.0, secx)
        rem   = slack - secx*nsec
        extra = max(0.0, min(rem/max(1, n-1), 9.0)) if n > 1 else 0.0
        for gi, g in enumerate(cols[ci]):
            if gi:
                y -= extra
                if cols[ci][gi]["sec"] != cols[ci][gi-1]["sec"]: y -= secx
            for b in g["run"]:
                if b["t"] == "head":
                    c.setFillColor(HexColor(b["pal"][3])); c.setFont(HB, HEAD_S)
                    c.drawString(x, y - HEAD_S + 1, b["title"])
                    c.setStrokeColor(HexColor(b["pal"][2])); c.setLineWidth(2.6)
                    c.line(x, y - HEAD_S - 4, x + COLW, y - HEAD_S - 4)
                    y -= b["h"] + 2
                else:
                    draw_entry(c, b["e"], b["g"], x, y, b["pal"])
                    y -= b["h"]

# ================= reference =================
def card(c, x, ytop, w, h, title, center=False):
    c.setFillColor(HexColor("#ffffff")); c.setStrokeColor(LINE); c.setLineWidth(1.0)
    c.roundRect(x, ytop - h, w, h, 5, fill=1, stroke=1)
    ts = HEAD_S*0.80                             # shrink rather than run past the border
    while ts > HEAD_S*0.52 and pdfmetrics.stringWidth(title, HB, ts) > w - 24:
        ts -= 0.25
    c.setFillColor(INK); c.setFont(HB, ts)
    y = ytop - HEAD_S*0.80 - 6
    if center:                                   # sits over a centred diagram
        c.drawCentredString(x + w/2.0, y, title)
    else:
        c.drawString(x + 12, y, title)
    return HEAD_S*0.80 + 14            # y used by the title

# ---- every reference card measures itself, then draws into that height ----
def ROW(): return DESC_S * 1.85        # table row height
def PADC(): return 11.0                # inner padding

CAP_GAP = 5.5
SUIT_PITCH = 1.30           # column pitch of the 1-9 suit tiles, x tile width
NUM_F   = 1.18              # size of the 1-9 column numbers, x DESC_S
CAPN_F  = 1.02              # size of the per-tile name captions
ROWL_F  = 1.12              # size of the row labels (Dots, Winds, ...)

def _suit_geom(w, tw):
    """Numbered suits left, named honours and bonus tiles right.

    The right column is sized from what the tile-name captions need; the
    suits take the rest and their tiles shrink to fit whichever half is
    tighter, so the two halves can never collide."""
    inner = w - 24
    capl  = DESC_S*max(NUM_F, CAPN_F)*1.28
    labl  = max(pdfmetrics.stringWidth(r[0], HB, DESC_S*ROWL_F) for r in data.NUM_ROWS) + 7
    labr  = max(pdfmetrics.stringWidth(h[0], HB, DESC_S*ROWL_F) for h in data.HONOUR_ROWS) + 7
    ncell = max(len(its) for _l, _z, its in data.HONOUR_ROWS)
    capw  = max([pdfmetrics.stringWidth(n, HB, DESC_S*CAPN_F)
                 for _l, _z, its in data.HONOUR_ROWS if len(its) == ncell
                 for _c, n in its]
                + [pdfmetrics.stringWidth(n, HB, DESC_S*CAPN_F)*len(its)/float(ncell)
                   for _l, _z, its in data.HONOUR_ROWS if len(its) < ncell
                   for _c, n in its]) + CAP_GAP

    wr    = labr + 6 + ncell*capw               # what the named half wants
    wl    = inner - GUT - wr                    # the suits take the remainder
    tw    = min(tw, (wl - labl - 6)/(9*SUIT_PITCH),  # nine tiles fit left
                    ((wr - labr - 6)/ncell)/1.14)
    cellw = max(tw*1.14, capw)
    step  = tw*VBH/VBW + DESC_S*0.55
    left  = capl + len(data.NUM_ROWS)*step
    right = len(data.HONOUR_ROWS)*(capl + step)
    # the named half has four rows to the numbered half's three, so the suits
    # would otherwise sit bunched at the top with dead space beneath them.
    # spread them over the same height instead - it costs nothing.
    lstep = step
    if right > left:
        lstep = (right - capl)/float(len(data.NUM_ROWS))
    return dict(wl=wl, wr=wr, tw=tw, cellw=cellw, ncell=ncell, step=step, lstep=lstep,
                capl=capl, labl=labl, labr=labr, h=max(left, right))

def m_suits(w, tw):
    g = _suit_geom(w, tw)
    return (HEAD_S*0.80 + 14) + g["h"] + PADC()

def d_suits(c, x, ytop, w, tw):
    g  = _suit_geom(w, tw)
    tw, step, capl = g["tw"], g["step"], g["capl"]
    h  = m_suits(w, tw)
    used = card(c, x, ytop, w, h, "Suits, Honours and Bonus Tiles")
    lift = DESC_S*0.55*0.5

    def rowlabel(xr, ybase, label, zh, st=None):
        st = step if st is None else st
        c.setFont(HB, DESC_S*ROWL_F); c.setFillColor(INK)
        c.drawRightString(xr, ybase - st*0.44, label)
        c.setFont("CJKR", DESC_S*0.82); c.setFillColor(MUTED)
        c.drawRightString(xr, ybase - st*0.44 - DESC_S*1.0, zh)

    # ---- left: the three suits, numbered 1 to 9 ----
    x0, tx0 = x + 12, x + 12 + g["labl"] + 6
    yy, lstep = ytop - used - capl, g["lstep"]
    # sit the numbers just above the first row of tiles, not up in the
    # header slot - the rows are spread out, so that would leave them adrift
    nrow = (yy - lstep + DESC_S*0.55*0.5) + tw*VBH/VBW + 3
    c.setFont(HB, DESC_S*NUM_F); c.setFillColor(MUTED)
    for i in range(9):
        c.drawCentredString(tx0 + i*tw*SUIT_PITCH + tw*0.5, nrow, str(i+1))
    for label, zh, suit in data.NUM_ROWS:
        rowlabel(x0 + g["labl"], yy, label, zh, lstep)
        for i in range(9):
            draw_tile(c, "%d%s" % (i+1, suit), tx0 + i*tw*SUIT_PITCH, yy - lstep + lift, tw)
        yy -= lstep

    # ---- right: winds, dragons, flowers and seasons, each tile named ----
    span = g["ncell"]*g["cellw"]
    x1  = x + 12 + g["wl"] + GUT
    tx1 = x1 + g["labr"] + 6
    yy  = ytop - used
    for label, zh, items in data.HONOUR_ROWS:
        cellw = span/float(len(items))
        c.setFont(HB, DESC_S*CAPN_F); c.setFillColor(MUTED)
        for i, (_code, nm) in enumerate(items):
            c.drawCentredString(tx1 + i*cellw + cellw*0.5, yy - capl + DESC_S*CAPN_F*0.30, nm)
        rowlabel(x1 + g["labr"], yy - capl, label, zh)
        for i, (code, _nm) in enumerate(items):
            draw_tile(c, code, tx1 + i*cellw + (cellw - tw)/2.0, yy - capl - step + lift, tw)
        yy -= capl + step
    return h

# ---- narrow-page variant: the chart split into two full-width cards -------
# Side by side, each half gets only half the width, and on a 5.5" booklet panel
# that caps the tiles at about 13pt.  Stacked, each card gets the full width and
# the tiles roughly double.

def _num_geom(w, tw):
    inner = w - 24
    capl  = DESC_S*NUM_F*1.28
    labl  = max(pdfmetrics.stringWidth(r[0], HB, DESC_S*ROWL_F) for r in data.NUM_ROWS) + 7
    tw    = min(tw, (inner - labl - 6)/(9*SUIT_PITCH))
    step  = tw*VBH/VBW + DESC_S*0.55
    return dict(tw=tw, labl=labl, capl=capl, step=step,
                h=capl + len(data.NUM_ROWS)*step)

def m_nums(w, tw):
    return (HEAD_S*0.80 + 14) + _num_geom(w, tw)["h"] + PADC()

def d_nums(c, x, ytop, w, tw):
    g = _num_geom(w, tw)
    tw, step, capl = g["tw"], g["step"], g["capl"]
    h = m_nums(w, tw)
    used = card(c, x, ytop, w, h, "Suits")
    lift = DESC_S*0.55*0.5
    x0, tx0 = x + 12, x + 12 + g["labl"] + 6
    yy = ytop - used - capl
    nrow = (yy - step + lift) + tw*VBH/VBW + 3
    c.setFont(HB, DESC_S*NUM_F); c.setFillColor(MUTED)
    for i in range(9):
        c.drawCentredString(tx0 + i*tw*SUIT_PITCH + tw*0.5, nrow, str(i+1))
    for label, zh, suit in data.NUM_ROWS:
        c.setFont(HB, DESC_S*ROWL_F); c.setFillColor(INK)
        c.drawRightString(x0 + g["labl"], yy - step*0.44, label)
        c.setFont("CJKR", DESC_S*0.82); c.setFillColor(MUTED)
        c.drawRightString(x0 + g["labl"], yy - step*0.44 - DESC_S*1.0, zh)
        for i in range(9):
            draw_tile(c, "%d%s" % (i+1, suit), tx0 + i*tw*SUIT_PITCH, yy - step + lift, tw)
        yy -= step
    return h

def _hon_geom(w, tw):
    inner = w - 24
    capl  = DESC_S*CAPN_F*1.28
    labr  = max(pdfmetrics.stringWidth(h[0], HB, DESC_S*ROWL_F) for h in data.HONOUR_ROWS) + 7
    ncell = max(len(its) for _l, _z, its in data.HONOUR_ROWS)
    capw  = max([pdfmetrics.stringWidth(n, HB, DESC_S*CAPN_F)
                 for _l, _z, its in data.HONOUR_ROWS if len(its) == ncell
                 for _c, n in its]) + CAP_GAP
    tw    = min(tw, ((inner - labr - 6)/ncell)/1.14)
    cellw = max(tw*1.14, capw)
    step  = tw*VBH/VBW + DESC_S*0.55
    return dict(tw=tw, labr=labr, capl=capl, step=step, ncell=ncell, cellw=cellw,
                h=len(data.HONOUR_ROWS)*(capl + step))

def m_honours(w, tw):
    return (HEAD_S*0.80 + 14) + _hon_geom(w, tw)["h"] + PADC()

def d_honours(c, x, ytop, w, tw):
    g = _hon_geom(w, tw)
    tw, step, capl = g["tw"], g["step"], g["capl"]
    h = m_honours(w, tw)
    used = card(c, x, ytop, w, h, "Honours and Bonus Tiles")
    lift = DESC_S*0.55*0.5
    span = g["ncell"]*g["cellw"]
    x1, tx1 = x + 12, x + 12 + g["labr"] + 6
    yy = ytop - used
    for label, zh, items in data.HONOUR_ROWS:
        cellw = span/float(len(items))
        c.setFont(HB, DESC_S*CAPN_F); c.setFillColor(MUTED)
        for i, (_code, nm) in enumerate(items):
            c.drawCentredString(tx1 + i*cellw + cellw*0.5, yy - capl + DESC_S*CAPN_F*0.30, nm)
        c.setFont(HB, DESC_S*ROWL_F); c.setFillColor(INK)
        c.drawRightString(x1 + g["labr"], yy - capl - step*0.44, label)
        c.setFont("CJKR", DESC_S*0.82); c.setFillColor(MUTED)
        c.drawRightString(x1 + g["labr"], yy - capl - step*0.44 - DESC_S*1.0, zh)
        for i, (code, _nm) in enumerate(items):
            draw_tile(c, code, tx1 + i*cellw + (cellw - tw)/2.0, yy - capl - step + lift, tw)
        yy -= capl + step
    return h

def m_payment(w):
    rh = ROW()
    h = (HEAD_S*0.80 + 14) + (len(data.PAYROWS) + 1)*rh + 8
    for n in data.PAYNOTES: h += para_h(n, HR, DESC_S, DESC_L, w - 24) + 4
    return h + PADC()

def d_payment(c, x, ytop, w):
    h = m_payment(w); rh = ROW()
    used = card(c, x, ytop, w, h, "Payment Table (New Style)")
    cw4 = (w - 24)/4.0
    gtop = ytop - used
    c.setFillColor(HexColor("#e7f0e6")); c.rect(x+12, gtop-rh, cw4*4, rh, fill=1, stroke=0)
    c.setFont(HB, DESC_S); c.setFillColor(INK)
    for j, htxt in enumerate(["Fan","Points","Fan","Points"]):
        c.drawCentredString(x + 12 + cw4*(j+0.5), gtop - rh + rh*0.30, htxt)
    yy = gtop - rh
    for k, row in enumerate(data.PAYROWS):
        if k % 2 == 0:
            c.setFillColor(HexColor("#fafaf4")); c.rect(x+12, yy-rh, cw4*4, rh, fill=1, stroke=0)
        for j, v in enumerate(row):
            c.setFillColor(HexColor("#2f7d3a") if j % 2 == 0 else INK)
            c.setFont(HB if j % 2 == 0 else HR, DESC_S)
            c.drawCentredString(x + 12 + cw4*(j+0.5), yy - rh + rh*0.30, str(v))
        yy -= rh
    c.setStrokeColor(LINE); c.setLineWidth(0.6)
    for r in range(len(data.PAYROWS) + 2):
        c.line(x+12, gtop - r*rh, x+12+cw4*4, gtop - r*rh)
    for j in range(5):
        c.line(x+12+cw4*j, gtop, x+12+cw4*j, gtop - (len(data.PAYROWS)+1)*rh)
    yy -= 8
    for n in data.PAYNOTES:
        yy = para(c, n, x+12, yy, w-24, HR, DESC_S, DESC_L, HexColor("#3d382f")) - 4
    return h

def m_terms(w):
    h = HEAD_S*0.80 + 14
    for tx in data.TERMINOLOGY: h += para_h(tx, HR, DESC_S, DESC_L, w - 24) + 5
    return h + PADC()

def d_terms(c, x, ytop, w):
    h = m_terms(w)
    used = card(c, x, ytop, w, h, "Terminology")
    yy = ytop - used
    for tx in data.TERMINOLOGY:
        yy = para(c, tx, x+12, yy, w-24, HR, DESC_S, DESC_L, HexColor("#3d382f")) - 5
    return h

CANTO_NOTE = ('Fan values and structure follow the HKMJ Cheat Sheet v1.0 (3 April 2025) by /u/danma. The six hands marked † are added here, with values from MCR (Chinese Official) or Taiwanese play. Tile examples, Fan breakdowns and notes by J. Lee.')

def m_canto(w):
    return (HEAD_S*0.80 + 14) + len(data.TERMS)*ROW() + 8 \
           + para_h(CANTO_NOTE, HO, DESC_S*0.95, DESC_L*0.95, w - 24) + PADC()

def d_canto(c, x, ytop, w):
    h = m_canto(w); rh = ROW()
    used = card(c, x, ytop, w, h, "Cantonese Terms")
    yy = ytop - used
    for k, (en, zh) in enumerate(data.TERMS):
        if k % 2 == 0:
            c.setFillColor(HexColor("#fafaf4")); c.rect(x+12, yy-rh, w-24, rh, fill=1, stroke=0)
        c.setFont(HR, DESC_S); c.setFillColor(INK)
        c.drawString(x+18, yy-rh+rh*0.30, en)
        c.setFont("CJKR", DESC_S*1.05)
        c.drawRightString(x+w-18, yy-rh+rh*0.30, zh)
        yy -= rh
    c.setStrokeColor(LINE); c.setLineWidth(0.6)
    for r in range(len(data.TERMS)+1):
        c.line(x+12, yy + r*rh, x+w-12, yy + r*rh)
    para(c, CANTO_NOTE, x+12, yy-8, w-24, HO, DESC_S*0.95, DESC_L*0.95, MUTED)
    return h

SEAT_NOTE = ("Your seat number tells you which flower and season are yours for "
             "\u6b63\u82b1 (Seat Flower). East is 1, South 2, West 3, North 4.")

def seat_square(w):
    """The diagram is useless below about 150pt, so that is the floor.
    The cap is what the reference page can spare in height."""
    return max(140.0, min(w - 22, 196.0))

def m_seat(w):
    return (HEAD_S*0.80 + 14) + seat_square(w) + 12 \
           + para_h(SEAT_NOTE, HR, DESC_S, DESC_L, w - 24) + PADC()

def d_seat(c, x, ytop, w):
    h = m_seat(w)
    used = card(c, x, ytop, w, h, "Seating and Flower Numbers", center=True)
    s  = seat_square(w)
    ox = x + (w - s)/2.0
    oy = ytop - used - s
    c.setFillColor(HexColor("#f6efdc")); c.setStrokeColor(HexColor("#c9a24a")); c.setLineWidth(1.8)
    c.rect(ox, oy, s, s, fill=1, stroke=1)
    c.setStrokeColor(HexColor("#b7ae95")); c.setLineWidth(0.8)
    q = s*0.30
    c.line(ox, oy, ox+q, oy+q); c.line(ox+s, oy, ox+s-q, oy+q)
    c.line(ox, oy+s, ox+q, oy+s-q); c.line(ox+s, oy+s, ox+s-q, oy+s-q)
    c.setFillColor(HexColor("#efe6cb")); c.setStrokeColor(HexColor("#b7ae95"))
    c.rect(ox+q, oy+q, s-2*q, s-2*q, fill=1, stroke=1)
    f = s/210.0                                    # scale the labels with the square
    # counter-clockwise turn arrow, drawn rather than set as a glyph
    acx, acy, r = ox + s/2, oy + s/2 + 0.052*s, 0.082*s
    arc = c.beginPath()
    arc.arc(acx - r, acy - r, acx + r, acy + r, -205, 292)
    c.setStrokeColor(INK); c.setLineWidth(max(0.9, 1.7*f)); c.setLineCap(1)
    c.drawPath(arc, stroke=1, fill=0)
    c.setLineCap(0)
    hl, hw = 0.055*s, 0.034*s                      # head at the top, pointing left
    head = c.beginPath()
    head.moveTo(acx - hl*1.15, acy + r)
    head.lineTo(acx + hl*0.30, acy + r + hw)
    head.lineTo(acx + hl*0.30, acy + r - hw)
    head.close()
    c.setFillColor(INK); c.drawPath(head, fill=1, stroke=0)
    c.setFillColor(INK); c.setFont(HB, 9.0*f)
    c.drawCentredString(ox+s/2, oy + s/2 - 0.105*s, "DEALER")
    seats = [("\u6771","East","5\u00b79\u00b713\u00b717","1", ox+s/2, oy+q*0.52,"c"),
             ("\u897f","West","3\u00b77\u00b711\u00b715","3", ox+s/2, oy+s-q*0.48,"c"),
             ("\u5317","North","4\u00b78\u00b712\u00b716","4", ox+q*0.50, oy+s/2,"v"),
             ("\u5357","South","6\u00b710\u00b714\u00b718","2", ox+s-q*0.50, oy+s/2,"v")]
    for zh, en, nums, fl, cx, cy, al in seats:
        if al == "c":
            c.setFillColor(INK); c.setFont("CJKB", 15*f)
            c.drawCentredString(cx, cy+5*f, zh + " " + en)
            c.setFont(HB, 10.4*f); c.setFillColor(MUTED); c.drawCentredString(cx, cy-7*f, nums)
            c.setFont(HB, 9.8*f); c.setFillColor(HexColor("#a3306d"))
            c.drawCentredString(cx, cy-18*f, "flower " + fl)
        else:
            # same face and size as East and West; stacked because the side
            # quadrants are narrow, so the two words will not sit on one line
            c.setFillColor(INK); c.setFont("CJKB", 15*f)
            c.drawCentredString(cx, cy+18*f, zh)
            c.drawCentredString(cx, cy+1.5*f, en)
            c.setFont(HB, 9.6*f); c.setFillColor(MUTED)
            c.drawCentredString(cx, cy-11.5*f, nums)
            c.setFont(HB, 9.4*f); c.setFillColor(HexColor("#a3306d"))
            c.drawCentredString(cx, cy-23*f, "flower " + fl)
    para(c, SEAT_NOTE, x+12, oy-8, w-24, HR, DESC_S, DESC_L, HexColor("#3d382f"))
    return h

def _ref_partition(cards, k):
    """Best split of the cards into k columns, original order preserved."""
    best = None
    for assign in itertools.product(range(k), repeat=len(cards)):
        cols = [[cards[i] for i in range(len(cards)) if assign[i] == j]
                for j in range(k)]
        if any(not col for col in cols): continue
        hs = [sum(x[1] for x in col) + GUT*(len(col)-1) for col in cols]
        # read row by row, left to right; prefer the order the cards were given in
        seq, r = [], 0
        while any(len(col) > r for col in cols):
            for col in cols:
                if len(col) > r: seq.append(cards.index(col[r]))
            r += 1
        inv = sum(1 for i in range(len(seq)) for j in range(i+1, len(seq))
                  if seq[i] > seq[j])
        score = (max(hs), inv, max(hs) - min(hs))
        if best is None or score < best[0]: best = (score, cols, hs)
    return best

def reference(c, ncol_ref, ncard=None):
    """Reference page: the tile chart across the top, then the four cards.

    The number of card columns is chosen by measurement - whichever count
    leaves the most height for the tile chart wins, so a tall portrait page
    and a short wide one each get the arrangement that suits them."""
    c.setFillColor(INK); c.setFont(HB, HEAD_S*1.35)
    c.drawString(M, PH - M - HEAD_S*1.35, "Reference")
    c.setFont("CJKB", HEAD_S*0.95); c.setFillColor(HexColor("#2f4f3f"))
    c.drawString(M + pdfmetrics.stringWidth("Reference", HB, HEAD_S*1.35) + 16,
                 PH - M - HEAD_S*1.35, "\u724c\u7ae0")
    top   = PH - M - HEAD_S*1.75
    ybot  = M + 6
    full  = PW - 2*M
    avail = top - ybot

    def plan(k):
        cw = (full - GUT*(k - 1))/float(k)
        # declared in reading order: Terminology closes the section
        cards = [("pay", m_payment(cw), d_payment), ("seat", m_seat(cw), d_seat),
                 ("canto", m_canto(cw), d_canto),   ("term", m_terms(cw), d_terms)]
        _, cols, hs = _ref_partition(cards, k)
        hmax = max(hs)
        tw = 34.0
        while tw > 9.0 and m_suits(full, tw) + GUT + hmax > avail:
            tw -= 0.5
        return tw, cw, cols, hmax

    if not ncard:
        # A tall portrait page reads best with two wide cards - the seating
        # diagram and the payment table both need the width. A short wide page
        # has no such room, so there we take whichever split the page allows.
        if PH > PW:
            ncard = 2
        else:
            best = None
            for k in (2, 3, 4):
                p = plan(k)
                if best is None or p[0] > best[0][0] + 0.01: best = (p, k)
            ncard = best[1]
    tw, cw, cols, hmax = plan(ncard)

    h1 = d_suits(c, M, top, full, tw)
    row2 = top - h1 - GUT
    for j, col in enumerate(cols):
        x0 = M + j*(cw + GUT)
        yy = row2
        for _, hh, fn in col:
            fn(c, x0, yy, cw)
            yy -= hh + GUT
    need = h1 + GUT + hmax
    if need > avail + 1:
        print("   ! reference page overflows by %.0f pt (%d card cols)" % (need - avail, ncard))
    return need, avail

# ================= build =================
def render(pagesize, ncol_hands, ncol_ref, outfile, extra=None):
    configure(pagesize, ncol_hands)
    c = canvas.Canvas(outfile, pagesize=PAGE)
    c.setTitle("Hong Kong Mahjong Scoring Sheet with Tile Examples")
    c.setAuthor("J. Lee, based on the HKMJ Cheat Sheet v1.0 by /u/danma")
    note = ("Hong Kong Mahjong Scoring Sheet v3.0  ·  Based on the HKMJ Cheat Sheet "
            "v1.0 (3 April 2025) by /u/danma, updated and expanded by J. Lee")
    groups = build_groups()
    full   = PW - 2*M
    ybot   = M + 6                        # the dagger is explained in How to Use
    y1     = masthead(c, PH - M)
    pages  = paginate(groups, y1, PH - M, ybot, NCOL, HEAD_H + 2)
    for pi, grps in enumerate(pages):
        if pi:
            footer(c, note); c.showPage()
        ytop = y1 if pi == 0 else PH - M
        cont = None
        if pi and grps[0]["first"]["t"] != "head":
            cont = (grps[0]["sec"] + "  (continued)", grps[0]["pal"])
        place_page(c, grps, ytop, _yb(ybot, grps), cont)
    footer(c, note); c.showPage()
    npages = len(pages)
    configure(pagesize, ncol_ref)
    reference(c, ncol_ref)
    if extra is not None:                  # e.g. the stacking page, placed last
        footer(c, note); c.showPage()
        configure(pagesize, ncol_hands)
        extra(c); npages += 1
    footer(c, note)
    c.save()
    return npages + 1

if __name__ == "__main__":
    n1 = render(landscape(A3), 2, 3, "HKMJ-Cheat-Sheet-3.0-landscape.pdf")
    n2 = render(portrait(A3),  2, 2, "HKMJ-Cheat-Sheet-3.0-portrait.pdf")
    print("landscape pages:", n1, " portrait pages:", n2)
