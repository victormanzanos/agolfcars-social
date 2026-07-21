#!/usr/bin/env python3
"""Compone el logo dorado de Art's Golf Cars para las tarjetas de Instagram:
badge circular "A" (brand-a-badge.png de agolfcars.com) + wordmark
"ART'S GOLF CARS" en Georgia (fallback serif del propio sitio: la web usa
'Playfair Display', Georgia, serif) con letter-spacing, todo en oro #C8A96E
sobre PNG transparente. Salida: logo-agc-gold.png
"""
from PIL import Image, ImageDraw, ImageFont
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = (200, 169, 110, 255)  # #C8A96E — oro del sitio agolfcars.com

badge = Image.open(os.path.join(HERE, "brand-a-badge.png")).convert("RGBA")

# WHY: Georgia es el fallback serif declarado en el CSS del sitio; Playfair
# Display no está instalada en el Mac, Georgia mantiene la identidad
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", 300)
TEXT = "ART'S GOLF CARS"
LSP = 24  # letter-spacing proporcional a los 2px/18px del nav de la web

# medir texto con letter-spacing
widths = []
for ch in TEXT:
    bbox = font.getbbox(ch)
    widths.append(bbox[2])
text_w = sum(widths) + LSP * (len(TEXT) - 1)
asc, desc = font.getmetrics()
text_h = asc + desc

GAP = 90  # separación badge-texto
H = badge.height  # 600
W = badge.width + GAP + text_w
canvas = Image.new("RGBA", (int(W), H), (0, 0, 0, 0))
canvas.alpha_composite(badge, (0, 0))

d = ImageDraw.Draw(canvas)
x = badge.width + GAP
y = (H - text_h) // 2
for ch, w in zip(TEXT, widths):
    d.text((x, y), ch, font=font, fill=GOLD)
    x += w + LSP

canvas.save(os.path.join(HERE, "logo-agc-gold.png"))
print("logo-agc-gold.png", canvas.size)
