#!/usr/bin/env python3
"""Foto de perfil de @agolfcars en MÁXIMA resolución.

Redibuja el badge SVG vectorial de agolfcars.com (círculo doble + "A" Georgia
itálica + "GOLF CARS") a 2400x2400 px, en dos variantes: fondo verde tinta
#0D2818 (recomendada para IG) y transparente. Se dibuja a 4800px y se reduce
con LANCZOS para antialiasing limpio.

Geometría fiel al SVG del sitio (viewBox 400x400, ver index.html nav-logo):
  circle r=140 stroke #C8A96E w5 · circle r=118 stroke gold@0.4 w2
  "A" Georgia italic 96px @(200,180) central · líneas y=225 gold@0.35
  "GOLF CARS" Arial 16px ls=6 gold@0.5 baseline y=262
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = (200, 169, 110)
INK  = (13, 40, 24)
# WHY: escala 24x sobre el viewBox de 400 → lienzo 9600 que se reduce a 2400
# (supersampling 4x para bordes suaves en los trazos finos)
S = 24
CANVAS = 400 * S          # 9600
OUT_SIZE = 2400

def build(background):
    img = Image.new("RGBA", (CANVAS, CANVAS), background)
    d = ImageDraw.Draw(img)
    cx = cy = 200 * S

    def ring(r, color, width):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=width)

    ring(140 * S, GOLD + (255,), 5 * S)
    ring(118 * S, GOLD + (102,), 2 * S)          # 0.4 alpha

    georgia_i = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia Italic.ttf", 96 * S)
    d.text((cx, 180 * S), "A", font=georgia_i, fill=GOLD + (255,), anchor="mm")

    for x1, x2 in ((120, 160), (240, 280)):
        d.line([(x1 * S, 225 * S), (x2 * S, 225 * S)], fill=GOLD + (89,), width=2 * S)  # 0.35

    arial = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16 * S)
    text, lsp = "GOLF CARS", 6 * S
    widths = [d.textlength(ch, font=arial) for ch in text]
    total = sum(widths) + lsp * (len(text) - 1)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        d.text((x, 262 * S), ch, font=arial, fill=GOLD + (128,), anchor="ls")  # 0.5
        x += w + lsp

    return img.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)

if __name__ == "__main__":
    dark = build(INK + (255,)).convert("RGB")
    dark.save(os.path.join(HERE, "agolfcars-profile-2400-dark.png"))
    build((0, 0, 0, 0)).save(os.path.join(HERE, "agolfcars-profile-2400-transparent.png"))
    print("✓ agolfcars-profile-2400-dark.png + agolfcars-profile-2400-transparent.png (2400x2400)")
