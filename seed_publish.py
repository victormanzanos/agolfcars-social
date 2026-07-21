#!/usr/bin/env python3
"""SIEMBRA INICIAL del feed de @agolfcars (una sola vez, 2026-07-21).

Publica en orden: tarjeta de logo + los 6 posts de bienvenida (captions de
CAPTIONS.md) y después la story de logo + las 6 stories, con espaciado
aleatorio entre publicaciones para no disparar los límites de Meta
(14 publicaciones, muy por debajo del límite de 25/24h del content publishing).

Al terminar deja `.daily_state.json` sincronizado (post=6, story=6,
last_date=hoy) para que el motor diario NO republique hoy y siga la rotación
normal dentro de 2 días.
"""
import datetime, json, os, random, time
from daily_engine import publish_image, POSTS, STORIES, RAW, STATE, rotate_caption

LOGO_POST_CAPTION = (
    "The Art of the Drive. ⛳\n"
    "Art's Golf Cars is Central Florida's premier golf car dealership: new and "
    "pre-owned golf cars, expert service, parts and accessories, and flexible "
    "financing in Dundee, FL.\n"
    "3× Club Car Black & Gold Elite Dealer.\n"
    "Follow along for new arrivals, custom builds and dealership life. "
    "Link in bio or call (863) 439-5431.\n\n"
    "#ArtsGolfCars #GolfCart #GolfCar #CentralFlorida #DundeeFL #ClubCar #GolfCartLife"
)

# WHY: 45-100 s entre publicaciones — humano-plausible y deja la siembra
# completa en ~15-20 min sin acercarse al rate limit
def pause():
    time.sleep(random.randint(45, 100))

def main():
    results = []
    # 1) Post de logo
    r = publish_image(f"{RAW}/posts/00-logo.jpg", caption=LOGO_POST_CAPTION)
    results.append(("POST 00-logo", r))
    print("POST 00-logo:", r.get("permalink") or r, flush=True)

    # 2) Los 6 posts de bienvenida
    for fn, cap in POSTS:
        pause()
        r = publish_image(f"{RAW}/posts/{fn}", caption=rotate_caption(cap))
        results.append((f"POST {fn}", r))
        print(f"POST {fn}:", r.get("permalink") or r, flush=True)

    # 3) Story de logo + las 6 stories
    pause()
    r = publish_image(f"{RAW}/stories/00-logo-story.jpg", story=True)
    results.append(("STORY 00-logo", r))
    print("STORY 00-logo-story:", r.get("id") or r, flush=True)
    for fn, _ in STORIES:
        pause()
        r = publish_image(f"{RAW}/stories/{fn}", story=True)
        results.append((f"STORY {fn}", r))
        print(f"STORY {fn}:", r.get("id") or r, flush=True)

    ok = sum(1 for _, r in results if r.get("id") or r.get("permalink"))
    print(f"\nSIEMBRA: {ok}/{len(results)} publicadas", flush=True)

    # 4) Estado del motor: hoy ya está publicado; rotación sigue en 2 días
    json.dump({"post": len(POSTS), "story": len(STORIES), "since_real": 0,
               "last_date": str(datetime.date.today())}, open(STATE, "w"))
    print("Estado sincronizado:", open(STATE).read(), flush=True)

if __name__ == "__main__":
    main()
