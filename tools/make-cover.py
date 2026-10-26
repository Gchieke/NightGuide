#!/usr/bin/env python3
"""Regenerate the NightGuide brand graphic (og share card + FB Page cover)
with current counts. Matches the neon-noir og-image design."""
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = int(sys.argv[1]), int(sys.argv[2])
OUT = sys.argv[3]
CLUBS, CITIES = sys.argv[4], sys.argv[5]

BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

# --- background: deep navy base + colored glows ---
img = Image.new("RGB", (W, H), (5, 5, 16))
glow = Image.new("RGB", (W, H), (0, 0, 0))
gd = ImageDraw.Draw(glow)
gd.ellipse([-W * 0.25, -H * 0.55, W * 0.45, H * 0.45], fill=(58, 26, 110))    # purple TL
gd.ellipse([W * 0.55, -H * 0.6, W * 1.2, H * 0.35], fill=(10, 52, 78))          # teal TR
gd.ellipse([W * 0.55, H * 0.55, W * 1.25, H * 1.3], fill=(96, 12, 58))          # magenta BR
glow = glow.filter(ImageFilter.GaussianBlur(W // 7))
from PIL import ImageChops
img = ImageChops.add(img, glow)

S = W / 1640.0  # scale factor vs cover master

# --- crescent moon (left) ---
cx, cy, R = int(W * 0.155), int(H * 0.50), int(H * 0.25)
moon = Image.new("RGBA", (W, H), (0, 0, 0, 0))
md = ImageDraw.Draw(moon)
md.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(122, 92, 116, 255))         # mauve halo disc
r2 = int(R * 0.88)
md.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(240, 110, 192, 255))     # pink disc
moon = moon.filter(ImageFilter.GaussianBlur(1.2))
img = Image.alpha_composite(img.convert("RGBA"), moon)
d = ImageDraw.Draw(img)
r3 = int(R * 0.82)
off = int(R * 0.30)
d.ellipse([cx - r3 + off, cy - r3, cx + r3 + off, cy + r3], fill=(6, 6, 18, 255))  # dark cut

def tracked(draw, xy, text, font, tracking, fill):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        w = draw.textlength(ch, font=font)
        x += w + tracking
    return x

def tracked_width(draw, text, font, tracking):
    return sum(draw.textlength(c, font=font) + tracking for c in text) - tracking

# --- wordmark ---
tx = int(W * 0.30)
fsize = int(118 * S * (1640 / W) * (W / 1640))  # keep proportional
fsize = int(H * 0.155)
font = ImageFont.truetype(BOLD, fsize)
tr = fsize * 0.14
y = int(H * 0.30)
x = tracked(d, (tx, y), "NIGHT", font, tr, (245, 245, 250, 255))
tracked(d, (x + fsize * 0.12, y), "GUIDE", font, tr, (255, 47, 178, 255))

# --- subline ---
sub = f"{CLUBS} clubs · {CITIES} cities · What's on tonight"
sfont = ImageFont.truetype(REG, int(H * 0.062))
d.text((tx, int(H * 0.545)), sub, font=sfont, fill=(168, 172, 205, 255))

# --- link pill ---
pfont = ImageFont.truetype(BOLD, int(H * 0.058))
label = "nightguide.club"
tw = d.textlength(label, font=pfont)
pad_x, pad_y = int(H * 0.055), int(H * 0.028)
px, py = tx, int(H * 0.66)
pw, ph = tw + pad_x * 2, int(H * 0.058) + pad_y * 2
d.rounded_rectangle([px, py, px + pw, py + ph], radius=ph // 2, fill=(34, 200, 229, 255))
d.text((px + pad_x, py + pad_y - int(H * 0.006)), label, font=pfont, fill=(4, 10, 14, 255))

img.convert("RGB").save(OUT, "PNG")
print("wrote", OUT, W, H)
