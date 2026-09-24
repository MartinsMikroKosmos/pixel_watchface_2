#!/usr/bin/env python3
"""Builds the font resources from the OFL variable fonts in tools/source/fonts.

- parchment_time.ttf  Playfair Display Regular, digits + colon only, with lining
                      figures (the default ones are old-style) made tabular so
                      the clock does not jump around every minute.
- parchment_text.ttf  Libre Baskerville Regular for all other text.

Both fonts are modified, so their names are changed (OFL Reserved Font Names).

Needs: fonttools
Run from the project root:  python3 tools/generate_fonts.py
"""
import os

from fontTools import subset
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source", "fonts")
OUT = os.path.join(HERE, "..", "watchface", "src", "main", "res", "font")

DIGITS = "0123456789"
NAMES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]


def instance(file, weight):
    font = TTFont(os.path.join(SRC, file))
    font = instantiateVariableFont(font, {"wght": weight})
    for tag in ("DSIG", "STAT"):
        if tag in font:
            del font[tag]
    return font


def rename(font, family):
    for rec in font["name"].names:
        if rec.nameID in (1, 16):
            rec.string = family
        elif rec.nameID == 3:
            rec.string = family.replace(" ", "") + "-Regular"
        elif rec.nameID == 4:
            rec.string = family
        elif rec.nameID == 6:
            rec.string = family.replace(" ", "") + "-Regular"


def do_subset(font, text):
    opts = subset.Options()
    opts.layout_features = ["kern"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)


def time_font():
    font = instance("PlayfairDisplay.ttf", 400)
    glyf, hmtx = font["glyf"], font["hmtx"]
    gs = font.getGlyphSet()
    lining = [n + ".lf" for n in NAMES]
    adv = max(hmtx[g][0] for g in lining)
    for g in lining:
        dx = (adv - hmtx[g][0]) / 2
        pen = TTGlyphPen(gs)
        gs[g].draw(TransformPen(pen, (1, 0, 0, 1, dx, 0)))
        glyph = pen.glyph()
        glyph.recalcBounds(glyf)
        glyf[g] = glyph
        hmtx[g] = (adv, getattr(glyph, "xMin", 0))
    for table in font["cmap"].tables:
        if table.isUnicode():
            for d, g in zip(DIGITS, lining):
                table.cmap[ord(d)] = g
    do_subset(font, DIGITS + ": ")
    rename(font, "Parchment Time")
    font.save(os.path.join(OUT, "parchment_time.ttf"))


def text_font():
    font = instance("LibreBaskerville.ttf", 400)
    rename(font, "Parchment Text")
    font.save(os.path.join(OUT, "parchment_text.ttf"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    time_font()
    text_font()
    print("fonts written to", os.path.abspath(OUT))
