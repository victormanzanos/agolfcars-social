#!/usr/bin/env python3
"""Badge limpio de Art's Golf Cars, fiel al SVG del nav de agolfcars.com.
El PNG antiguo (brand-a-badge.png) tenía "GOLF CARS" demasiado grande y bajo,
pisando el aro interior. Aquí se redibuja con la geometría correcta del vector:
"A" Georgia itálica centrada, dos rayitas a los lados (y=225) y "GOLF CARS"
Arial pequeño con tracking a y=262, holgadamente dentro del aro interior.

Salida: brand-a-badge-clean.png (1200x1200, fondo transparente).
Geometría SVG (viewBox 400): outer r140 w5, inner r118 w2, A@180 96px,
lines y225, "GOLF CARS" Arial 16px ls6 y262.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = (200, 169, 110)
SS = 2                      # supersampling
OUT = 1200 * SS
CX = CY = OUT // 2
# radio 140 (SVG) -> 552px de radio en el frame de 1200 (deja ~8% de margen)
SCALE = (552 * SS) / 140.0

def P(sx, sy):
    return (CX + (sx - 200) * SCALE, CY + (sy - 200) * SCALE)

img = Image.new("RGBA", (OUT, OUT), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

def ring(r_svg, alpha, w_svg):
    r = r_svg * SCALE
    d.ellipse([CX - r, CY - r, CX + r, CY + r], outline=GOLD + (alpha,), width=max(1, round(w_svg * SCALE)))

ring(140, 255, 5)
ring(118, 102, 2)                       # 0.4 alpha

# "A" Georgia italic 96px @ (200,180) dominant-baseline central
georgia_i = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia Italic.ttf", round(96 * SCALE))
ax, ay = P(200, 180)
d.text((ax, ay), "A", font=georgia_i, fill=GOLD + (255,), anchor="mm")

# dos rayitas a los lados @ y=225
for x1, x2 in ((120, 160), (240, 280)):
    d.line([P(x1, 225), P(x2, 225)], fill=GOLD + (89,), width=max(1, round(2 * SCALE)))  # 0.35

# "GOLF CARS" Arial 16px letter-spacing 6, gold@0.5, baseline y=262 centrado
arial = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", round(16 * SCALE))
text, lsp = "GOLF CARS", 6 * SCALE
widths = [d.textlength(ch, font=arial) for ch in text]
total = sum(widths) + lsp * (len(text) - 1)
bx, by = P(200, 262)
x = bx - total / 2
for ch, w in zip(text, widths):
    d.text((x, by), ch, font=arial, fill=GOLD + (128,), anchor="ls")   # 0.5
    x += w + lsp

img = img.resize((1200, 1200), Image.LANCZOS)
out = os.path.join(HERE, "brand-a-badge-clean.png")
img.save(out)
print("brand-a-badge-clean.png", img.size)
