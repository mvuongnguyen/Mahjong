import os, sys
from fontTools.ttLib import TTFont as FTFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen

# Noto Serif/Sans CJK, wherever the platform keeps them.  Override with
# HKMJ_CJK_SERIF / HKMJ_CJK_SANS if yours live somewhere else.
CANDIDATES = {
 "serif": ["/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
           "/usr/share/fonts/truetype/noto/NotoSerifCJK-Bold.ttc",
           "/usr/local/share/fonts/NotoSerifCJK-Bold.ttc",
           "/Library/Fonts/NotoSerifCJK-Bold.ttc",
           os.path.expanduser("~/Library/Fonts/NotoSerifCJK-Bold.ttc"),
           "C:/Windows/Fonts/NotoSerifCJK-Bold.ttc"],
 "sans":  ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
           "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
           "/usr/local/share/fonts/NotoSansCJK-Regular.ttc",
           "/Library/Fonts/NotoSansCJK-Regular.ttc",
           os.path.expanduser("~/Library/Fonts/NotoSansCJK-Regular.ttc"),
           "C:/Windows/Fonts/NotoSansCJK-Regular.ttc"],
}

def find(which):
    env = os.environ.get("HKMJ_CJK_" + which.upper())
    if env:
        if not os.path.exists(env):
            raise SystemExit("HKMJ_CJK_%s points at a missing file: %s" % (which.upper(), env))
        return env
    for path in CANDIDATES[which]:
        if os.path.exists(path):
            return path
    raise SystemExit(
        "Noto CJK %s not found.  Install the Noto CJK fonts (Debian/Ubuntu:\n"
        "  sudo apt install fonts-noto-cjk\n"
        "macOS:  brew install --cask font-noto-serif-cjk font-noto-sans-cjk\n"
        "or download from https://github.com/notofonts/noto-cjk/releases )\n"
        "then set HKMJ_CJK_%s to the .ttc file if it is not on the usual path."
        % (which, which.upper()))

def build(src_ttc, subfont, chars, out, family):
    f = FTFont(src_ttc, fontNumber=subfont)
    cmap = f.getBestCmap()
    gs = f.getGlyphSet()
    upem = f["head"].unitsPerEm
    hmtx = f["hmtx"]

    order = [".notdef"]
    newcmap = {}
    missing = []
    for ch in sorted(set(chars)):
        gn = cmap.get(ord(ch))
        if gn is None:
            missing.append(ch); continue
        if gn not in order:
            order.append(gn)
        newcmap[ord(ch)] = gn

    glyphs, metrics = {}, {}
    for gn in order:
        pen = TTGlyphPen(None)
        try:
            gs[gn].draw(Cu2QuPen(pen, 1.0, reverse_direction=True))
        except Exception:
            pass
        glyphs[gn] = pen.glyph()
        adv, lsb = hmtx[gn] if gn in hmtx.metrics else (upem, 0)
        metrics[gn] = (adv, lsb)

    fb = FontBuilder(upem, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(newcmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=int(upem*0.88), descent=-int(upem*0.12))
    fb.setupNameTable({"familyName": family, "styleName": "Regular",
                       "psName": family.replace(" ", ""), "fullName": family})
    fb.setupOS2(sTypoAscender=int(upem*0.88), sTypoDescender=-int(upem*0.12),
                usWinAscent=int(upem*0.88), usWinDescent=int(upem*0.12))
    fb.setupPost()
    fb.save(out)
    return len(order), missing

if __name__ == "__main__":
    test = "一二三四五六七八九萬東南西北中發白春夏秋冬梅蘭菊竹香港麻雀正統牌型"
    n, miss = build(find("serif"), 3, test, "test.ttf", "MJTest")
    print("glyphs:", n, "missing:", miss)
