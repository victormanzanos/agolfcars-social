#!/usr/bin/env python3
"""Tarjeta de marca con el LOGO de Art's Golf Cars centrado sobre fondo verde
tinta (#0D2818) con el doble marco dorado — primer post del feed y story de
presentación. Reusa las primitivas de make_agolfcars.py."""
import os
from PIL import Image
from make_agolfcars import (GOLD, INK, POST_W, POST_H, STORY_W, STORY_H,
                            LOGO_GOLD, OUT_POSTS, OUT_STORIES,
                            draw_double_frame, draw_corner_accents)

def make_logo_card(story=False):
    w, h = (STORY_W, STORY_H) if story else (POST_W, POST_H)
    img = Image.new("RGB", (w, h), INK)
    if story:
        img = draw_double_frame(img, 54, 20, 4, 1)
        img = draw_corner_accents(img, 54, 90, 4)
    else:
        img = draw_double_frame(img, 44, 16, 3, 1)
        img = draw_corner_accents(img, 44, 70, 3)
    canvas = img.convert("RGBA")
    logo = Image.open(LOGO_GOLD).convert("RGBA")
    # WHY: 78% del ancho — el logo es la única pieza de la tarjeta, protagonista
    # pero sin tocar el marco interior (queda ~7% de aire por lado)
    target_w = int(w * 0.78)
    target_h = int(target_w * logo.height / logo.width)
    logo = logo.resize((target_w, target_h), Image.LANCZOS)
    canvas.alpha_composite(logo, ((w - target_w) // 2, (h - target_h) // 2))
    out_dir = OUT_STORIES if story else OUT_POSTS
    name = "00-logo-story.jpg" if story else "00-logo.jpg"
    out = os.path.join(out_dir, name)
    canvas.convert("RGB").save(out, "JPEG", quality=92, optimize=True)
    print("  ✓", name)

if __name__ == "__main__":
    make_logo_card(story=False)
    make_logo_card(story=True)
