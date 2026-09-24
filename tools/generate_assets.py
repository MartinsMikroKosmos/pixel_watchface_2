#!/usr/bin/env python3
"""Generates the bitmap resources for the "Pixel Parchment" watch face.

Most ornaments are cut out of the concept renders in tools/source/ (b1.jpeg:
weather medallions, b2.jpeg: the watch face itself) and turned into
transparent PNGs by removing the paper colour ("colour to alpha").
The parchment background is generated procedurally.

Needs: pillow, numpy, opencv-python-headless
Run from the project root:  python3 tools/generate_assets.py
"""
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source")
OUT = os.path.join(HERE, "..", "watchface", "src", "main", "res", "drawable-nodpi")

N = 450  # watch face canvas

# The watch screen in b2.jpeg: centre and radius of the display (inside the
# black bezel ring), measured by a circle fit.  All layout coordinates below
# are in "screen" pixels of b2 and mapped to the 450px canvas with to_face().
B2_SCREEN_X, B2_SCREEN_Y = 1041, 394          # crop origin of the screen in b2
SCR_CX, SCR_CY, SCR_R = 369.4, 355.7, 359.0   # display circle inside that crop
K = (N / 2) / SCR_R                            # screen px -> face px


def to_face(x, y):
    return (x - SCR_CX) * K + N / 2, (y - SCR_CY) * K + N / 2


def load(name):
    return np.asarray(Image.open(os.path.join(SRC, name)).convert("RGB")).astype(np.float32)


B1 = load("b1.jpeg")
B2 = load("b2.jpeg")
SCREEN = B2[B2_SCREEN_Y:B2_SCREEN_Y + 774, B2_SCREEN_X:B2_SCREEN_X + 775]


def save(arr, name, size=None):
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA" if arr.shape[2] == 4 else "RGB")
    if size:
        img = img.resize(size, Image.LANCZOS)
    img.save(os.path.join(OUT, name + ".png"), optimize=True)
    print(f"  {name}.png {img.size[0]}x{img.size[1]}")


def paper_color(rgb, mask=None):
    """Median colour of the brightest half of the pixels = the paper."""
    px = rgb.reshape(-1, 3) if mask is None else rgb[mask]
    lum = px @ [0.3, 0.59, 0.11]
    return np.median(px[lum >= np.percentile(lum, 55)], axis=0)


def color_to_alpha(rgb, paper, ink=(95, 60, 25), floor=0.07, gain=1.15):
    """Remove the paper: returns RGBA where the paper is transparent and the
    engraving keeps its own (gold/brown) colour."""
    paper = np.asarray(paper, np.float32)
    ink = np.asarray(ink, np.float32)
    a = np.max((paper - rgb) / np.maximum(paper - ink, 1), axis=-1)
    a = np.clip(a * gain, 0, 1)
    col = paper + (rgb - paper) / np.maximum(a, 1e-3)[..., None]
    a = np.clip((a - floor) / (1 - floor), 0, 1)
    return np.dstack([np.clip(col, 0, 255), a * 255])


def circle_mask(h, w, cx, cy, r, soft=1.5):
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.hypot(xx - cx, yy - cy)
    return np.clip((r - d) / soft + 0.5, 0, 1)


def fit_circle(xs, ys):
    for _ in range(3):
        A = np.c_[2 * xs, 2 * ys, np.ones_like(xs)]
        cx, cy, c = np.linalg.lstsq(A, xs ** 2 + ys ** 2, rcond=None)[0]
        r = np.sqrt(c + cx * cx + cy * cy)
        keep = np.abs(np.hypot(xs - cx, ys - cy) - r) < 8
        xs, ys = xs[keep], ys[keep]
    return cx, cy, r


def screen_crop(x0, y0, x1, y1):
    return SCREEN[y0:y1, x0:x1].copy()


def face_size(x0, y0, x1, y1):
    return max(1, round((x1 - x0) * K)), max(1, round((y1 - y0) * K))


# ---------------------------------------------------------------- background
def background():
    rng = np.random.default_rng(7)
    base = np.array([243, 234, 213], np.float32)  # sampled from the render

    def noise(scale, amp):
        small = rng.standard_normal((N // scale + 2, N // scale + 2)).astype(np.float32)
        big = cv2.resize(small, (N, N), interpolation=cv2.INTER_CUBIC)
        return big / (big.std() + 1e-6) * amp

    lum = noise(90, 2.6) + noise(35, 1.6) + noise(12, 0.9) + rng.standard_normal((N, N)).astype(np.float32) * 1.1
    # a few darker stains, like aged paper
    stains = np.zeros((N, N), np.float32)
    for _ in range(9):
        x, y = rng.uniform(0, N, 2)
        r = rng.uniform(25, 70)
        cv2.circle(stains, (int(x), int(y)), int(r), float(rng.uniform(2, 4)), -1)
    stains = cv2.GaussianBlur(stains, (0, 0), 22)
    # faint creases
    crease = np.zeros((N, N), np.float32)
    for _ in range(7):
        p0 = rng.uniform(-50, N + 50, 2)
        ang = rng.uniform(0, np.pi)
        d = np.array([np.cos(ang), np.sin(ang)]) * 600
        cv2.line(crease, tuple(int(v) for v in p0 - d), tuple(int(v) for v in p0 + d), 1.0, 1, cv2.LINE_AA)
    crease = cv2.GaussianBlur(crease, (0, 0), 0.8) * 3 + cv2.GaussianBlur(crease, (0, 0), 3) * 3
    # vignette: slightly darker and warmer towards the rim
    yy, xx = np.mgrid[0:N, 0:N]
    rr = np.hypot(xx - N / 2, yy - N / 2) / (N / 2)
    vig = np.clip(rr - 0.5, 0, 1) ** 1.6 * 26

    shade = lum - stains - crease - vig
    warm = np.array([1.0, 1.08, 1.55], np.float32)  # darkening pulls towards brown
    img = base[None, None, :] + shade[..., None] * warm[None, None, :]
    save(img, "bg_parchment")


# ------------------------------------------------------------- weather icons
# Medallion centres in b1 as shown at 2000px width (scaled to the original).
B1_SCALE = B1.shape[1] / 2000
WEATHER = {
    "wx_sunny": (198, 197), "wx_partly": (482, 197), "wx_cloudy": (1530, 197), "wx_rain": (1812, 197),
    "wx_heavy_rain": (198, 532), "wx_thunder": (482, 532), "wx_snow": (1530, 532), "wx_hail": (1812, 532),
    "wx_wind": (198, 866), "wx_fog": (482, 866), "wx_frost": (1530, 866), "wx_night": (1812, 866),
}


def weather_icons(size=96):
    for name, (x, y) in WEATHER.items():
        cx, cy, half = x * B1_SCALE, y * B1_SCALE, 135 * B1_SCALE
        x0, y0 = int(cx - half), int(cy - half)
        crop = B1[y0:int(cy + half), x0:int(cx + half)]
        h, w = crop.shape[:2]
        # find the gold rim to centre the icon precisely
        lum = crop @ [0.3, 0.59, 0.11]
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.hypot(xx - w / 2, yy - h / 2)
        sel = (lum < 175) & (d > 0.72 * w / 2) & (d < 0.98 * w / 2)
        ys, xs = np.where(sel)
        mcx, mcy, mr = fit_circle(xs.astype(float), ys.astype(float))
        inner = mr * 0.80  # inside the rim bevel
        mask = circle_mask(h, w, mcx, mcy, inner, soft=inner * 0.06)
        # the medallion is domed, so the paper colour depends on the radius
        dist = np.hypot(xx - mcx, yy - mcy)
        paper = np.zeros_like(crop)
        edges = np.linspace(0, inner * 1.02, 13)
        prof = []
        for r0, r1 in zip(edges, edges[1:]):
            ring = (dist >= r0) & (dist < r1)
            prof.append(paper_color(crop, ring))
        mids = (edges[:-1] + edges[1:]) / 2
        for c in range(3):
            paper[..., c] = np.interp(dist, mids, [p[c] for p in prof])
        rgba = color_to_alpha(crop, paper, floor=0.1)
        rgba[..., 3] *= mask
        s = int(inner * 0.97)
        c = rgba[int(mcy - s):int(mcy + s), int(mcx - s):int(mcx + s)]
        save(c, name, (size, size))


# ------------------------------------------------------------ small ornaments
def cutout(name, box, scale=1.0, **kw):
    crop = screen_crop(*box)
    border = np.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]])
    paper = np.median(border, axis=0)
    rgba = color_to_alpha(crop, paper, **kw)
    # never pick up the black bezel ring
    x0, y0, x1, y1 = box
    rgba[..., 3] *= circle_mask(y1 - y0, x1 - x0, SCR_CX - x0, SCR_CY - y0, SCR_R - 6, soft=2)
    w, h = face_size(*box)
    save(rgba, name, (round(w * scale), round(h * scale)))


def ornaments():
    cutout("ic_watch", (443, 150, 477, 200))
    cutout("ic_phone", (574, 238, 605, 290))
    cutout("ic_heart_small", (428, 551, 469, 591))


# --------------------------------------------------------------- medallions
def medallion(name, cx, cy, r, erase):
    """Cuts a medallion out of the screen and removes the text in `erase`
    (list of boxes relative to the medallion centre)."""
    pad = 10
    x0, y0 = cx - r - pad, cy - r - pad
    crop = screen_crop(x0, y0, cx + r + pad, cy + r + pad)
    h, w = crop.shape[:2]
    lum = crop @ [0.3, 0.59, 0.11]
    blur = cv2.GaussianBlur(lum, (0, 0), 9)
    mask = np.zeros((h, w), np.uint8)
    for bx0, by0, bx1, by1 in erase:
        sl = np.s_[by0 + r + pad:by1 + r + pad, bx0 + r + pad:bx1 + r + pad]
        m = (lum[sl] < blur[sl] - 6).astype(np.uint8)
        mask[sl] = m
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8))
    clean = cv2.inpaint(crop.astype(np.uint8), mask, 7, cv2.INPAINT_TELEA).astype(np.float32)
    # smooth the inpainted area so no smudges remain
    soft = cv2.GaussianBlur(clean, (0, 0), 4)
    m3 = cv2.GaussianBlur(cv2.dilate(mask, np.ones((9, 9), np.uint8)).astype(np.float32), (0, 0), 3)[..., None]
    clean = clean * (1 - m3) + soft * m3
    # alpha: the disc itself plus a soft drop shadow outside
    disc = circle_mask(h, w, w / 2, h / 2, r + 1, soft=1.2)
    rgba = np.dstack([clean, disc * 255])
    shadow = Image.fromarray((circle_mask(h, w, w / 2 + 2, h / 2 + 4, r, 1) * 90).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(4))
    sh = np.asarray(shadow, np.float32) / 255
    a = disc + sh * (1 - disc)
    col = (clean * disc[..., None] + np.array([90, 60, 30], np.float32) * (sh * (1 - disc))[..., None]) / np.maximum(a, 1e-3)[..., None]
    rgba = np.dstack([col, a * 255])
    size = round(w * K)
    save(rgba, name, (size, size))


def medallions():
    # steps: remove "10,421" and "/ 10K Schritte", keep boots + scroll
    medallion("med_steps", 228, 540, 115, [(-100, -40, 100, 52)])
    # heart rate: remove "♥ 78 BPM", keep heart + pulse line + scroll
    medallion("med_heart", 512, 540, 115, [(-100, 8, 100, 54)])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    background()
    weather_icons()
    ornaments()
    medallions()
    print("assets written to", os.path.abspath(OUT))
