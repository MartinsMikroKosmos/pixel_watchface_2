#!/usr/bin/env python3
"""Generates the Google Play store graphics for the "Pixel Pergament" watch face.

Needs: pillow
Run from the project root:  python3 tools/generate_store_assets.py
Output: playstore/  (icon 512x512, feature graphic 1024x500, screenshot)
"""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "watchface", "src", "main", "res")
OUT = os.path.join(HERE, "..", "playstore")

PREVIEW = os.path.join(RES, "drawable", "preview.png")
BG = os.path.join(RES, "drawable-nodpi", "bg_parchment.png")
FONT = os.path.join(RES, "font", "parchment_text.ttf")

INK = (74, 52, 32)
GOLD = (168, 124, 70)
GOLD_LIGHT = (200, 164, 110)


def backdrop(w, h):
    """The parchment texture, slightly darkened towards the edges."""
    side = max(w, h)
    img = Image.open(BG).convert("RGBA").resize((side, side), Image.LANCZOS)
    img = img.crop(((side - w) // 2, (side - h) // 2, (side - w) // 2 + w, (side - h) // 2 + h))
    vignette = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vignette).rectangle([0, 0, w, h], outline=110, width=min(w, h) // 8)
    shade = Image.new("RGBA", (w, h), (90, 60, 30, 255))
    shade.putalpha(vignette.filter(ImageFilter.GaussianBlur(min(w, h) // 8)))
    img.alpha_composite(shade)
    return img


def round_face(size):
    """The preview cut to a circle, with transparent corners."""
    face = Image.open(PREVIEW).convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * 4 - 1, size * 4 - 1], fill=255)
    face.putalpha(mask.resize((size, size), Image.LANCZOS))
    return face


def paste_with_rim(canvas, face, x, y, rim=6):
    """Face with a thin gold rim and a soft shadow."""
    size = face.width
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([x - rim, y - rim + 8, x + size + rim, y + size + rim + 8],
                                   fill=(60, 40, 20, 110))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(canvas).ellipse([x - rim, y - rim, x + size + rim, y + size + rim], fill=GOLD)
    canvas.alpha_composite(face, (x, y))


def icon():
    img = backdrop(512, 512)
    paste_with_rim(img, round_face(420), 46, 40)
    img.convert("RGB").save(os.path.join(OUT, "icon_512.png"))


def feature_graphic():
    w, h = 1024, 500
    img = backdrop(w, h)
    paste_with_rim(img, round_face(410), w - 410 - 75, (h - 410) // 2)

    d = ImageDraw.Draw(img)
    d.text((70, 140), "Pixel", font=ImageFont.truetype(FONT, 76), fill=INK)
    d.text((70, 225), "Pergament", font=ImageFont.truetype(FONT, 76), fill=INK)
    d.line([(74, 330), (330, 330)], fill=GOLD_LIGHT, width=3)
    d.text((72, 350), "Wear OS Watch Face", font=ImageFont.truetype(FONT, 28), fill=GOLD)
    img.convert("RGB").save(os.path.join(OUT, "feature_graphic_1024x500.png"))


def screenshot():
    # Play wants square Wear OS screenshots without a round mask
    Image.open(PREVIEW).convert("RGB").save(os.path.join(OUT, "screenshot_1.png"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    icon()
    feature_graphic()
    screenshot()
