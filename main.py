#!/usr/bin/env python3
"""One Strawberry, Dripping.

Draws a single perfect ripe strawberry with dew drops on a dark
background, procedurally with PIL only. Fully deterministic: no
randomness, no network, no timestamps. Writes /output/entry.png
(1024x1024, <= 1 MiB) and ./entry.png for reference.

Run:  python3 main.py
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

W = H = 1024          # final size
SS = 2                # supersampling factor
CW, CH = W * SS, H * SS
OUT = "/output/entry.png"

# Deterministic jitter only (fixed seed).
rng = random.Random(20261122)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def vgrad(size, top, bottom):
    """Vertical linear gradient RGB image."""
    w, h = size
    img = Image.new("RGB", (1, h))
    px = img.load()
    for y in range(h):
        px[0, y] = lerp(top, bottom, y / max(1, h - 1))
    return img.resize((w, h))


def radial_glow(size, center, radius, color, peak=110):
    """Soft radial glow on a transparent layer."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    steps = 48
    for i in range(steps, 0, -1):
        t = i / steps
        r = radius * t
        a = int(peak * (1 - t) ** 2)
        d.ellipse([center[0] - r, center[1] - r,
                   center[0] + r, center[1] + r],
                  fill=color + (a,))
    return layer


def catmull_rom(pts, samples=24):
    """Closed Catmull-Rom spline through control points."""
    out = []
    n = len(pts)
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        for j in range(samples):
            t = j / samples
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    return out


def berry_outline(cx, top, width, height):
    """Strawberry silhouette: wide rounded shoulders, shallow top dip,
    tapering sides, softly rounded tip. Control points in unit space."""
    ctrl = [(-0.07, 0.055), (-0.46, 0.02), (-0.76, 0.09), (-0.94, 0.27),
            (-0.86, 0.50), (-0.62, 0.72), (-0.34, 0.90), (0.0, 0.985),
            (0.34, 0.90), (0.62, 0.72), (0.86, 0.50), (0.94, 0.27),
            (0.76, 0.09), (0.46, 0.02), (0.07, 0.055)]
    pts = catmull_rom(ctrl)
    return [(cx + x * width, top + y * height) for (x, y) in pts]


def main():
    # ---------- background: dark plum gradient + warm glow ----------
    bg = vgrad((CW, CH), (26, 18, 34), (10, 8, 16)).convert("RGBA")
    glow = radial_glow((CW, CH), (CW // 2, int(CH * 0.52)),
                       int(CW * 0.52), (150, 40, 55), peak=72)
    bg.alpha_composite(glow)

    # soft vignette
    vig = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    dv = ImageDraw.Draw(vig)
    dv.ellipse([-CW * 0.25, -CH * 0.25, CW * 1.25, CH * 1.25],
               outline=(0, 0, 0, 170), width=int(CW * 0.28))
    vig = vig.filter(ImageFilter.GaussianBlur(CW // 8))
    bg.alpha_composite(vig)

    # ---------- soft shadow under the berry ----------
    shadow = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    ds = ImageDraw.Draw(shadow)
    ds.ellipse([CW * 0.26, CH * 0.90, CW * 0.76, CH * 0.985],
               fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(CW // 22))
    bg.alpha_composite(shadow)

    # ---------- strawberry body ----------
    cx = CW * 0.50
    scale = CW * 0.42
    body_pts = berry_outline(cx, CH * 0.21, scale, CH * 0.74)

    # body mask (for clipping seeds / shading)
    mask = Image.new("L", (CW, CH), 0)
    dm = ImageDraw.Draw(mask)
    dm.polygon(body_pts, fill=255)

    body = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    db = ImageDraw.Draw(body)
    db.polygon(body_pts, fill=(196, 18, 38, 255))

    # radial shading: bright upper-left, deep crimson edges/bottom
    shade = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    dsh = ImageDraw.Draw(shade)
    hx, hy = CW * 0.40, CH * 0.36
    for i in range(60, 0, -1):
        t = i / 60.0
        r = scale * 1.15 * t
        # dark rim -> transparent centre
        a = int(120 * t * t)
        dsh.ellipse([hx - r, hy - r, hx + r, hy + r],
                    outline=(120, 4, 22, a), width=max(2, int(scale * 0.02)))
    shade = shade.filter(ImageFilter.GaussianBlur(int(scale * 0.06)))

    # warm highlight wash upper-left (strong: the juicy side catches light)
    hi = radial_glow((CW, CH), (int(CW * 0.38), int(CH * 0.33)),
                     int(scale * 0.66), (255, 110, 95), peak=150)
    # bright scarlet core just off-centre
    core = radial_glow((CW, CH), (int(CW * 0.46), int(CH * 0.45)),
                       int(scale * 0.55), (255, 70, 60), peak=90)
    # deep shadow bottom-right and along the rim
    lo = radial_glow((CW, CH), (int(CW * 0.62), int(CH * 0.78)),
                     int(scale * 0.62), (80, 2, 16), peak=130)

    body.alpha_composite(shade)
    body.alpha_composite(hi)
    body.alpha_composite(core)
    body.alpha_composite(lo)

    # clip everything to the berry silhouette
    body.putalpha(Image.composite(body.split()[3], Image.new("L", (CW, CH), 0), mask))
    bg.alpha_composite(body)

    # ---------- glossy specular highlight ----------
    gloss = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    dg = ImageDraw.Draw(gloss)
    dg.ellipse([CW * 0.30, CH * 0.22, CW * 0.50, CH * 0.44],
               fill=(255, 235, 225, 120))
    dg.ellipse([CW * 0.36, CH * 0.27, CW * 0.46, CH * 0.38],
               fill=(255, 255, 255, 170))
    gloss = gloss.filter(ImageFilter.GaussianBlur(int(scale * 0.13)))
    gloss.putalpha(Image.composite(gloss.split()[3],
                                   Image.new("L", (CW, CH), 0), mask))
    bg.alpha_composite(gloss)

    # ---------- achenes (seeds): rows inside the berry ----------
    seeds = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    dsd = ImageDraw.Draw(seeds)
    # rows across the body; keep points inside the mask
    mpx = mask.load()
    rows = 9
    for row in range(rows):
        y = int(CH * 0.33 + row * (CH * 0.55) / rows)
        # seed count follows the berry's width: widest near the top
        width_frac = 1.0 - 0.55 * (row / (rows - 1)) ** 1.6
        n_seed = max(3, int(7 * width_frac))
        stagger = (CW * 0.038) if row % 2 else 0
        for k in range(n_seed):
            x = int(CW * 0.50 + stagger
                    + (k - (n_seed - 1) / 2.0) * CW * 0.105
                    + rng.uniform(-5, 5) * SS)
            yy = int(y + rng.uniform(-5, 5) * SS)
            if not (0 <= x < CW and 0 <= yy < CH):
                continue
            if mpx[x, yy] == 0:
                continue
            # pit shadow, then pale gold seed, then tiny glint
            sw, sh = int(CW * 0.009), int(CW * 0.015)
            dsd.ellipse([x - sw, yy - sh + 3, x + sw, yy + sh + 3],
                        fill=(120, 10, 20, 160))
            dsd.ellipse([x - sw, yy - sh, x + sw, yy + sh],
                        fill=(238, 200, 120, 255))
            dsd.ellipse([x - sw * 0.45, yy - sh * 0.55,
                         x + sw * 0.15, yy - sh * 0.05],
                        fill=(255, 246, 210, 255))
    bg.alpha_composite(seeds)

    # ---------- dew drops ----------
    dew = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dew)
    drops = [
        (0.415, 0.475, 0.030), (0.565, 0.420, 0.024),
        (0.520, 0.610, 0.034), (0.430, 0.660, 0.022),
        (0.610, 0.560, 0.019), (0.480, 0.330, 0.018),
    ]
    for fx, fy, fr in drops:
        x, y, r = int(CW * fx), int(CH * fy), int(CW * fr)
        dd.ellipse([x - r, y - r, x + r, y + r],
                   fill=(255, 255, 255, 46))
        dd.ellipse([x - r, y - r, x + r, y + r],
                   outline=(255, 255, 255, 150), width=max(2, r // 6))
        dd.ellipse([x - r * 0.45, y - r * 0.55, x + r * 0.05, y - r * 0.05],
                   fill=(255, 255, 255, 235))
        dd.ellipse([x - r * 0.15, y + r * 0.35, x + r * 0.35, y + r * 0.70],
                   fill=(255, 255, 255, 90))
    dew.putalpha(Image.composite(dew.split()[3],
                                 Image.new("L", (CW, CH), 0), mask))
    bg.alpha_composite(dew)

    # ---------- calyx leaves + stem ----------
    leaves = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    dl = ImageDraw.Draw(leaves)
    # calyx sits ON the berry's top dip, leaves fanning out over the fruit
    top_x, top_y = CW * 0.50, CH * 0.235
    leaf_defs = [(-68, 0.135, 0.62), (-46, 0.155, 0.66), (-24, 0.165, 0.68),
                 (0, 0.170, 0.68), (24, 0.165, 0.68), (46, 0.155, 0.66),
                 (68, 0.135, 0.62)]
    for ang, length, width in leaf_defs:
        a = math.radians(ang - 90)
        length *= CH
        tip = (top_x + length * math.cos(a),
               top_y + length * math.sin(a))
        perp = a + math.pi / 2
        wdt = width * length * 0.42
        base_l = (top_x + wdt * math.cos(perp), top_y + wdt * math.sin(perp))
        base_r = (top_x - wdt * math.cos(perp), top_y - wdt * math.sin(perp))
        mid = ((top_x + tip[0]) / 2 + wdt * 0.30 * math.cos(perp),
               (top_y + tip[1]) / 2 + wdt * 0.30 * math.sin(perp))
        dl.polygon([base_l, mid, tip,
                    ((top_x + tip[0]) / 2 - wdt * 0.30 * math.cos(perp),
                     (top_y + tip[1]) / 2 - wdt * 0.30 * math.sin(perp)),
                    base_r], fill=(52, 138, 58, 255))
        dl.line([top_x, top_y, tip[0], tip[1]],
                fill=(165, 220, 140, 220), width=max(2, int(4 * SS)))
    # green cap covering the leaf bases
    dl.ellipse([top_x - CW * 0.045, top_y - CH * 0.018,
                top_x + CW * 0.045, top_y + CH * 0.018],
               fill=(38, 112, 46, 255))
    # stem
    dl.line([top_x, top_y - 6 * SS, top_x + 12 * SS, top_y - 52 * SS],
            fill=(96, 122, 60, 255), width=max(3, int(10 * SS)))
    dl.line([top_x, top_y - 6 * SS, top_x + 12 * SS, top_y - 52 * SS],
            fill=(155, 185, 115, 255), width=max(2, int(3 * SS)))
    leaves = leaves.filter(ImageFilter.GaussianBlur(SS))
    bg.alpha_composite(leaves)

    # ---------- final: downscale, save ----------
    img = bg.convert("RGB").resize((W, H), Image.LANCZOS)
    os.makedirs("/output", exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    img.save("entry.png", format="PNG", optimize=True)
    print(f"wrote {OUT} {img.size} ")


if __name__ == "__main__":
    main()
