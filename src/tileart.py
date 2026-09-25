# -*- coding: utf-8 -*-
"""Mahjong tile artwork -> isometric 3D SVG (non-text parts only).
Art space is 100 x 130 (the tile's face panel), matching the web version."""
import math, os, subprocess, hashlib

# ---------- data (ported from the web renderer) ----------
DOTPOS = {
 1:[(50,50)], 2:[(50,28),(50,72)], 3:[(26,23),(50,50),(74,77)],
 4:[(30,28),(70,28),(30,72),(70,72)],
 5:[(28,26),(72,26),(50,50),(28,74),(72,74)],
 6:[(30,22),(70,22),(30,50),(70,50),(30,78),(70,78)],
 7:[(25,17),(50,29),(75,41),(30,63),(70,63),(30,86),(70,86)],
 8:[(32,15),(68,15),(32,38),(68,38),(32,62),(68,62),(32,85),(68,85)],
 9:[(25,22),(50,22),(75,22),(25,50),(50,50),(75,50),(25,78),(50,78),(75,78)]}
DOTSZ = {1:46,2:36,3:31,4:33,5:29,6:29,7:25,8:23,9:27}
DOTCOL = {1:"b",2:"gb",3:"bgr",4:"bggb",5:"bgrgb",6:"ggrrrr",7:"gggrrrr",
          8:"bbbbbbbb",9:"rrrgggbbb"}
BAMPOS = {
 2:[(50,27),(50,73)], 3:[(50,24),(32,73),(68,73)],
 4:[(32,27),(68,27),(32,73),(68,73)],
 5:[(29,25),(71,25),(50,50),(29,75),(71,75)],
 6:[(28,25),(50,25),(72,25),(28,75),(50,75),(72,75)],
 7:[(50,17),(28,52),(50,52),(72,52),(28,84),(50,84),(72,84)],
 8:[(27,25),(42,25),(58,25),(73,25),(27,75),(42,75),(58,75),(73,75)],
 9:[(26,21),(50,21),(74,21),(26,50),(50,50),(74,50),(26,79),(50,79),(74,79)]}
BAMSZ = {2:(17,32),3:(16,28),4:(16,28),5:(15,27),6:(14,27),7:(13,24),8:(11,27),9:(12,23)}
BAMCOL = {2:"gg",3:"ggg",4:"gggg",5:"ggrgg",6:"gggggg",7:"rgggggg",
          8:"gggggggg",9:"gggrrrggg"}
COL = {"b":"#1f5fa8","g":"#1a7a44","r":"#bf3226"}

BIRD = ('<ellipse cx="52" cy="76" rx="27" ry="34" fill="#1a7a44"/>'
 '<ellipse cx="52" cy="76" rx="16" ry="24" fill="#2ea25e"/>'
 '<path d="M52 108 L34 128 L52 120 L70 128 Z" fill="#bf3226"/>'
 '<circle cx="48" cy="33" r="17" fill="#1a7a44"/>'
 '<circle cx="53" cy="30" r="4" fill="#fdfbf4"/>'
 '<path d="M31 33 L8 40 L31 44 Z" fill="#bf3226"/>'
 '<path d="M62 20 q14 -14 20 -2 q-9 -2 -16 8 Z" fill="#bf3226"/>'
 '<path d="M74 60 q16 12 10 30 q-8 -14 -18 -20 Z" fill="#2ea25e"/>')

def blossom(cx, cy, s, petal, core):
    o = ""
    for i in range(5):
        a = math.radians(i*72 - 90)
        o += '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (
              cx+math.cos(a)*s*0.95, cy+math.sin(a)*s*0.95, s*0.74, petal)
    return o + '<circle cx="%s" cy="%s" r="%.1f" fill="%s"/>' % (cx, cy, s*0.5, core)

def chrysanth():
    o = ""
    for i in range(16):
        o += '<ellipse cx="52" cy="26" rx="5.5" ry="18" fill="#d99a24" transform="rotate(%.1f 52 48)"/>' % (i*22.5)
    for i in range(12):
        o += '<ellipse cx="52" cy="34" rx="4.6" ry="13" fill="#f0bb45" transform="rotate(%.1f 52 48)"/>' % (i*30+15)
    return o + '<circle cx="52" cy="48" r="8" fill="#b9701a"/>'

FIGURE = {
 "h1": ('<path d="M4 110 q11 -6 22 0 t22 0 t22 0 t22 0" stroke="#3fa0cc" stroke-width="4" fill="none" stroke-linecap="round"/>'
        '<path d="M4 121 q11 -6 22 0 t22 0 t22 0 t22 0" stroke="#7fc8e4" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
        '<line x1="30" y1="84" x2="93" y2="22" stroke="#8a5a2b" stroke-width="4.5" stroke-linecap="round"/>'
        '<line x1="93" y1="22" x2="90" y2="58" stroke="#6b6355" stroke-width="1.8"/>'
        '<path d="M90 58 l7 5 l-7 5 l-5 -5 z" fill="#bf3226"/>'
        '<path d="M33 60 q17 -7 32 0 l9 46 q-26 8 -50 0 z" fill="#2a5fa0"/>'
        '<circle cx="48" cy="48" r="13" fill="#f0d6b0"/>'
        '<path d="M21 44 q27 -30 54 0 z" fill="#d2a94e"/>'
        '<ellipse cx="48" cy="44" rx="28" ry="4" fill="#b08c38"/>'),
 "h2": ('<rect x="5" y="50" width="28" height="9" rx="4.5" fill="#8a5a2b"/>'
        '<rect x="5" y="62" width="28" height="9" rx="4.5" fill="#a87038"/>'
        '<rect x="5" y="74" width="28" height="9" rx="4.5" fill="#8a5a2b"/>'
        '<line x1="72" y1="106" x2="82" y2="32" stroke="#8a5a2b" stroke-width="5" stroke-linecap="round"/>'
        '<path d="M82 30 q18 3 15 19 q-16 1 -20 -8 z" fill="#9aa0a4"/>'
        '<path d="M38 60 q17 -7 32 0 l8 46 q-25 8 -48 0 z" fill="#1a7a44"/>'
        '<circle cx="53" cy="48" r="13" fill="#f0d6b0"/>'
        '<path d="M39 40 q14 -14 28 0 q-14 6 -28 0 z" fill="#5a4632"/>'
        '<path d="M6 96 q10 -10 20 -4 q-9 10 -20 4z" fill="#2ea25e"/>'),
 "h3": ('<g stroke="#c9a24a" stroke-width="3.2" stroke-linecap="round" fill="none">'
        '<path d="M12 122 q3 -30 8 -48"/><path d="M26 124 q-1 -28 -3 -42"/></g>'
        '<ellipse cx="20" cy="62" rx="6" ry="12" fill="#dcb44e"/>'
        '<ellipse cx="25" cy="72" rx="5" ry="10" fill="#c99b36"/>'
        '<line x1="70" y1="108" x2="82" y2="34" stroke="#8a5a2b" stroke-width="4.5" stroke-linecap="round"/>'
        '<path d="M82 32 l17 7 l-5 13 l-15 -9 z" fill="#9aa0a4"/>'
        '<path d="M38 62 q17 -7 32 0 l8 45 q-25 8 -48 0 z" fill="#bf3226"/>'
        '<circle cx="53" cy="50" r="13" fill="#f0d6b0"/>'
        '<path d="M27 46 q26 -26 52 0 z" fill="#d2a94e"/>'),
 "h4": ('<g fill="#c4dcea"><circle cx="12" cy="20" r="4.2"/><circle cx="88" cy="30" r="3.6"/>'
        '<circle cx="20" cy="46" r="3"/><circle cx="86" cy="66" r="3.2"/><circle cx="9" cy="76" r="2.8"/></g>'
        '<path d="M31 62 q19 -7 36 0 l9 46 q-27 8 -54 0 z" fill="#22447a"/>'
        '<circle cx="49" cy="48" r="13" fill="#f0d6b0"/>'
        '<path d="M35 42 q14 -18 28 0 z" fill="#1b3050"/>'
        '<rect x="30" y="36" width="38" height="6" rx="3" fill="#1b3050"/>'
        '<path d="M26 90 l23 -7 l0 23 l-23 7 z" fill="#fdfbf4" stroke="#8a7c5c" stroke-width="1.6"/>'
        '<path d="M72 90 l-23 -7 l0 23 l23 7 z" fill="#efe8d6" stroke="#8a7c5c" stroke-width="1.6"/>'),
 "h5": ('<path d="M10 126 q18 -32 32 -52 q12 -18 26 -34" stroke="#6b4423" stroke-width="7.5" fill="none" stroke-linecap="round"/>'
        '<path d="M38 88 q18 -8 30 -24" stroke="#6b4423" stroke-width="5" fill="none" stroke-linecap="round"/>'
        '<path d="M50 64 q-16 -8 -30 -6" stroke="#6b4423" stroke-width="4.5" fill="none" stroke-linecap="round"/>'
        + blossom(74,30,12,"#ea7d9b","#f5d24a") + blossom(70,62,10,"#e06a8c","#f5d24a")
        + blossom(20,54,9.5,"#ea7d9b","#f5d24a") + blossom(42,100,9,"#e06a8c","#f5d24a")),
 "h6": ('<g stroke="#1e7a45" fill="none" stroke-linecap="round">'
        '<path d="M44 126 q-32 -28 -38 -70" stroke-width="5"/>'
        '<path d="M47 126 q-13 -44 -3 -80" stroke-width="5"/>'
        '<path d="M50 126 q20 -38 44 -54" stroke-width="5"/>'
        '<path d="M50 126 q28 -20 46 -12" stroke-width="4"/></g>'
        '<g fill="#9b59b6"><ellipse cx="58" cy="54" rx="5" ry="13" transform="rotate(-32 58 54)"/>'
        '<ellipse cx="74" cy="58" rx="5" ry="13" transform="rotate(30 74 58)"/>'
        '<ellipse cx="66" cy="44" rx="4.6" ry="12"/></g>'
        '<circle cx="66" cy="58" r="5.5" fill="#f5d24a"/>'),
 "h7": ('<line x1="52" y1="80" x2="52" y2="128" stroke="#1e7a45" stroke-width="5" stroke-linecap="round"/>'
        '<path d="M52 104 q-22 -14 -34 -2 q16 14 34 2z" fill="#2ea25e"/>'
        '<path d="M52 114 q22 -12 32 2 q-18 12 -32 -2z" fill="#1e7a45"/>' + chrysanth()),
 "h8": ('<rect x="31" y="4" width="17" height="124" rx="5" fill="#1e7a45"/>'
        '<rect x="57" y="32" width="13" height="96" rx="4" fill="#2ea25e"/>'
        '<g stroke="#0d5730" stroke-width="3">'
        '<line x1="31" y1="40" x2="48" y2="40"/><line x1="31" y1="78" x2="48" y2="78"/>'
        '<line x1="31" y1="112" x2="48" y2="112"/>'
        '<line x1="57" y1="62" x2="70" y2="62"/><line x1="57" y1="98" x2="70" y2="98"/></g>'
        '<g fill="#3fbb72"><path d="M31 32 q-24 -14 -30 4 q22 12 30 -4z"/>'
        '<path d="M48 22 q22 -18 31 -3 q-20 14 -31 3z"/>'
        '<path d="M70 56 q22 -7 26 9 q-22 5 -26 -9z"/></g>')}

FLOWERS = {"h1":("1","春","#1f5fa8"), "h2":("2","夏","#1f5fa8"),
           "h3":("3","秋","#1f5fa8"), "h4":("4","冬","#1f5fa8"),
           "h5":("1","梅","#1a7a44"), "h6":("2","蘭","#1a7a44"),
           "h7":("3","菊","#1a7a44"), "h8":("4","竹","#1a7a44")}
WINDS = {"we":"東","ws":"南","ww":"西","wn":"北"}
NUMS = "一二三四五六七八九"

# ---------- art (non-text) for a face ----------
def face_art(code):
    if len(code) == 2 and code[0].isdigit() and code[1] in "psm":
        n, suit = int(code[0]), code[1]
        if suit == "p":
            o = ""
            for (px, py), ch in zip(DOTPOS[n], DOTCOL[n]):
                r = DOTSZ[n] / 2.0
                cx, cy, c = px, py*1.3, COL[ch]
                o += ('<circle cx="%.1f" cy="%.1f" r="%.2f" fill="%s"/>'
                      '<circle cx="%.1f" cy="%.1f" r="%.2f" fill="#fdfbf4"/>'
                      '<circle cx="%.1f" cy="%.1f" r="%.2f" fill="%s"/>'
                      % (cx,cy,r,c, cx,cy,r*0.60, cx,cy,r*0.26,c))
            return o
        if suit == "s":
            if n == 1:
                return '<g transform="translate(14,10.4) scale(0.72,0.84)">%s</g>' % BIRD
            bw, bh = BAMSZ[n]; h = bh*1.3
            o = ""
            for (px, py), ch in zip(BAMPOS[n], BAMCOL[n]):
                x, y, c = px-bw/2.0, py*1.3-h/2.0, COL[ch]
                o += ('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" ry="%.1f" fill="%s"/>'
                      '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#ffffff" opacity="0.30"/>'
                      '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#ffffff" opacity="0.30"/>'
                      % (x,y,bw,h,bw*0.42,h*0.14,c,
                         x,y+h*0.33,bw,h*0.055,
                         x,y+h*0.62,bw,h*0.055))
            return o
        return ""          # man: text drawn by reportlab
    if code == "dw":
        return ('<rect x="15" y="17" width="70" height="96" rx="5" fill="none" '
                'stroke="#2a5fa0" stroke-width="7"/>'
                '<rect x="24" y="26" width="52" height="78" rx="3" fill="none" '
                'stroke="#2a5fa0" stroke-width="1.6" opacity="0.45"/>')
    if code in FIGURE:
        return '<g transform="translate(5,20.8) scale(0.90,0.81)">%s</g>' % FIGURE[code]
    return ""              # winds / 中 / 發: text drawn by reportlab

# ---------- isometric 3D tile SVG ----------
W, H, DX, DY = 100.0, 136.0, 16.0, 14.0
VBW, VBH = W + DX, H + DY
FX, FY = 0.0, DY                  # front face origin
PX, PY, PW, PH = 6.0, DY + 6.0, 88.0, 124.0   # panel rect

def tile_svg(code, face_down=False):
    top  = '<polygon points="%g,%g %g,%g %g,%g %g,%g" fill="#f7f0dc" stroke="#9c8f6d" stroke-width="1"/>' % (
            FX, FY, FX+DX, FY-DY, FX+W+DX, FY-DY, FX+W, FY)
    side = '<polygon points="%g,%g %g,%g %g,%g %g,%g" fill="#d8cbab" stroke="#9c8f6d" stroke-width="1"/>' % (
            FX+W, FY, FX+W+DX, FY-DY, FX+W+DX, FY+H-DY, FX+W, FY+H)
    if face_down:
        front = ('<rect x="%g" y="%g" width="%g" height="%g" rx="11" ry="9" '
                 'fill="url(#jade)" stroke="#f2ecd8" stroke-width="4"/>'
                 '<rect x="%g" y="%g" width="%g" height="%g" rx="11" ry="9" fill="none" '
                 'stroke="#0a3d29" stroke-width="1.4"/>'
                 '<rect x="12" y="%g" width="76" height="112" rx="7" ry="6" fill="none" '
                 'stroke="#ffffff" stroke-width="2.5" opacity="0.30"/>') % (
                 FX, FY, W, H, FX, FY, W, H, FY+12)
        art = ""
    else:
        front = ('<rect x="%g" y="%g" width="%g" height="%g" rx="11" ry="9" '
                 'fill="url(#ivory)" stroke="#9c8f6d" stroke-width="1.2"/>') % (FX, FY, W, H)
        art = ('<rect x="%g" y="%g" width="%g" height="%g" rx="7" ry="6" fill="#fffdf6" '
               'stroke="#c3b591" stroke-width="1"/>'
               '<g transform="translate(%g,%g) scale(%.5f,%.5f)">%s</g>'
               ) % (PX, PY, PW, PH, PX, PY, PW/100.0, PH/130.0, face_art(code))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %g %g" width="%g" height="%g">'
            '<defs>'
            '<linearGradient id="ivory" x1="0" y1="0" x2="0.6" y2="1">'
            '<stop offset="0" stop-color="#fffdf6"/><stop offset="0.5" stop-color="#f7f1df"/>'
            '<stop offset="1" stop-color="#e9e0c7"/></linearGradient>'
            '<linearGradient id="jade" x1="0" y1="0" x2="0.6" y2="1">'
            '<stop offset="0" stop-color="#2f8f68"/><stop offset="0.55" stop-color="#166344"/>'
            '<stop offset="1" stop-color="#0d4b33"/></linearGradient>'
            '</defs>%s%s%s%s</svg>') % (VBW, VBH, VBW*6, VBH*6, top, side, front, art)

CACHE = "tilecache"
def tile_png(code):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.md5(code.encode()).hexdigest()[:10]
    png = os.path.join(CACHE, "%s_%s.png" % (code.replace("*",""), key))
    if os.path.exists(png):
        return png
    svg = os.path.join(CACHE, "t.svg")
    with open(svg, "w") as fh:
        fh.write(tile_svg(code, face_down=(code == "xx")))
    subprocess.run(["convert", "-background", "none", svg, png], check=True)
    return png
