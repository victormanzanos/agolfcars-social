#!/usr/bin/env python3
"""Alta de imágenes nuevas en la rotación de @agolfcars, con dedup OBLIGATORIO.

Regla de Victor (2026-09-17): una misma foto NO puede publicarse dos veces, ni en
post ni en story, en 360 días. Antes de esto el dedup era "mira el manifiesto por
nombre de fichero", que no ve una foto repetida con otro nombre ni la misma foto a
otra resolución. Aquí el dedup es por CONTENIDO: md5 + hash perceptual (aHash 16x16,
Hamming <= 6 = misma foto), contra raw/ y contra el índice de tarjetas.

Uso:
  python3 add_images.py add post  <fuente.jpg> <NN-slug>   # tarjeta de post
  python3 add_images.py add story <fuente.jpg> <sNN-slug>  # tarjeta de story
  python3 add_images.py check                              # auditoría completa
  python3 add_images.py plan [N]                           # simula las N próximas publicaciones

`add` falla (exit 2) si la foto ya existe en la rotación. Eso es deliberado: es la
red que impide que una foto repetida entre en la baraja.
"""
import os, sys, json, shutil, hashlib, datetime, importlib.util
from PIL import Image

LOCAL = os.path.expanduser("~/agolfcars-social")
RAWD  = os.path.join(LOCAL, "raw")
INDEX = os.path.join(LOCAL, ".image_index.json")
LEDGER = os.path.join(LOCAL, ".published_images.json")
# Hamming <= 6 sobre aHash 16x16: la MISMA foto reescalada o recomprimida.
# Umbral aprendido en [[agolfcars-ig-engine]] (10-sep-2026): el md5 no basta,
# dos copias de la misma foto a 1200px y 1600px tienen md5 distinto.
PHASH_NEAR = 6


def ahash(im, n=16):
    im = im.convert("L").resize((n, n))
    px = list(im.getdata()); avg = sum(px) / len(px)
    return sum(1 << i for i, p in enumerate(px) if p > avg)

def ham(a, b):
    return bin(int(a) ^ int(b)).count("1")

def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default

def known_hashes():
    """(md5s, phashes) de todo lo que ya está en la rotación."""
    md5s, ph = set(), []
    for f in sorted(os.listdir(RAWD)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        p = os.path.join(RAWD, f)
        md5s.add(hashlib.md5(open(p, "rb").read()).hexdigest())
        try:
            ph.append((f, ahash(Image.open(p))))
        except Exception:
            pass
    for card, e in load(INDEX, {}).items():
        if e.get("phash"):
            ph.append((card, int(e["phash"])))
    return md5s, ph


def cmd_add(kind, src, name):
    assert kind in ("post", "story"), "kind debe ser post o story"
    sys.path.insert(0, LOCAL)
    import make_agolfcars as M

    im = Image.open(src).convert("RGB")
    if min(im.size) < 700:
        print(f"RECHAZADA: {src} demasiado pequeña {im.size} (mínimo lado corto 700px)")
        return 2
    md5 = hashlib.md5(open(src, "rb").read()).hexdigest()
    h = ahash(im)
    md5s, ph = known_hashes()
    if md5 in md5s:
        print(f"RECHAZADA (md5 duplicado): {src}")
        return 2
    for other, oh in ph:
        if ham(h, oh) <= PHASH_NEAR:
            print(f"RECHAZADA (misma foto que {other}, distancia {ham(h, oh)}): {src}")
            return 2

    raw_name = f"{name}.jpg"
    shutil.copyfile(src, os.path.join(RAWD, raw_name))
    card = f"{name}.jpg" if kind == "post" else f"{name}-story.jpg"
    M.make_post(raw_name, card, story=(kind == "story"))
    idx = load(INDEX, {})
    idx[card] = {"src": raw_name, "phash": str(h), "kind": kind}
    json.dump(idx, open(INDEX, "w"), indent=1)
    print(f"OK {card}  (fuente {raw_name}, phash {h})")
    return 0


def cmd_check():
    """Auditoría: duplicados en la baraja, tarjetas sin identidad, repeticiones ya publicadas."""
    idx = load(INDEX, {}); led = load(LEDGER, [])
    problems = 0

    # 1) dos tarjetas distintas con la misma foto
    by_src = {}
    for card, e in idx.items():
        by_src.setdefault(e["src"], []).append(card)
    # Un post y SU story con la misma foto es la baraja histórica (hasta
    # 17-sep-2026 se generaban en pareja). No es un fallo nuevo, pero consume el
    # doble de fotos, así que solo se cuenta. Lo grave es una foto en DOS posts
    # distintos o en DOS stories distintas: eso sí es una repetición encubierta.
    legacy_pairs = 0
    for src, cards in by_src.items():
        posts = [c for c in cards if not c.endswith("-story.jpg")]
        stories = [c for c in cards if c.endswith("-story.jpg")]
        if len(posts) > 1 or len(stories) > 1:
            print(f"⚠️ MISMA FOTO en tarjetas distintas: {src} → {cards}")
            problems += 1
        elif posts and stories:
            legacy_pairs += 1
    if legacy_pairs:
        print(f"ℹ️ {legacy_pairs} fotos compartidas por un post y su story (baraja histórica). "
              "El guard impide publicarlas el mismo día, pero cada pareja solo aporta 1 foto útil.")

    # 2) tarjetas de la rotación sin entrada en el índice (invisibles al guard)
    os.environ["DRY"] = "1"
    spec = importlib.util.spec_from_file_location("de", os.path.join(LOCAL, "daily_engine.py"))
    de = importlib.util.module_from_spec(spec); spec.loader.exec_module(de)
    cards = [f for f, _ in de.POSTS] + list(de.STORY_FILES)
    missing = [c for c in cards if c not in idx]
    if missing:
        print(f"⚠️ {len(missing)} tarjetas SIN identidad de imagen (el guard no las ve): {missing[:8]}")
        problems += 1

    # 3) fotos ya publicadas más de una vez dentro de la ventana
    cut = str(datetime.date.today() - datetime.timedelta(days=de.NO_REPEAT_DAYS))
    seen = {}
    for e in led:
        if e["date"] >= cut:
            seen.setdefault(e["src"], []).append((e["date"], e["kind"], e["card"]))
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    if dups:
        print(f"⚠️ {len(dups)} fotos publicadas MÁS DE UNA VEZ en los últimos {de.NO_REPEAT_DAYS} días:")
        for k, v in list(dups.items())[:10]:
            print(f"    {k}: {v}")
        problems += 1

    # 4) capacidad: fotos frescas que quedan
    fresh = set(e["src"] for e in idx.values()) - set(seen)
    slots = len(fresh) // 2          # cada publicación gasta 2 fotos (post + story)
    print(f"\nfotos en la baraja: {len(by_src)} · publicadas en ventana: {len(seen)} · "
          f"frescas: {len(fresh)} → ~{slots} publicaciones ({slots * 2} días) sin repetir")
    need = 183 * 2 - len(by_src)     # 360 días / cadencia 2 = 183 slots, 2 fotos cada uno
    if need > 0:
        print(f"⚠️ FALTAN ~{need} fotos para cubrir 360 días sin repetir ninguna.")
        problems += 1
    print("RESULTADO:", "OK" if problems == 0 else f"{problems} avisos")
    return 0 if problems == 0 else 1


def cmd_plan(n=20):
    os.environ["DRY"] = "1"
    spec = importlib.util.spec_from_file_location("de", os.path.join(LOCAL, "daily_engine.py"))
    de = importlib.util.module_from_spec(spec); spec.loader.exec_module(de)
    idx = de.image_index(); led = list(de.ledger_load())
    st = load(os.path.join(LOCAL, ".daily_state.json"), {"post": 0, "story": 0})
    p, s = st["post"], st["story"]
    d = datetime.date.today()
    while d.toordinal() % de.CYCLE_DIV != de.CYCLE_DAY or str(d) == st.get("last_date"):
        d += datetime.timedelta(days=1)
    used = {}
    for e in led:
        used.setdefault(e["src"], []).append(e["date"])
    bad = 0
    for _ in range(n):
        cut = str(d - datetime.timedelta(days=de.NO_REPEAT_DAYS))
        srcs = {e["src"] for e in led if e["date"] >= cut}
        ph = [e["phash"] for e in led if e["date"] >= cut]
        (pf, _), p2, pst = de.pick_fresh(de.POSTS, p, srcs, ph)
        pph = [idx[pf]["phash"]] if pf in idx else []
        sf, s2, sst = de.pick_fresh(de.STORY_FILES, s, srcs, ph, pph)
        flags = []
        for card, kind in ((pf, "post"), (sf, "story")):
            src = idx.get(card, {}).get("src", "?")
            if any(x >= cut for x in used.get(src, [])):
                flags.append(f"REPITE {kind} ({src})"); bad += 1
            used.setdefault(src, []).append(str(d))
            led.append({"date": str(d), "kind": kind, "card": card, "src": src,
                        "phash": idx.get(card, {}).get("phash", "0")})
        mark = "  ← " + " · ".join(flags) if flags else ""
        print(f"{d}  post {pf:<32} story {sf:<38}{mark}")
        p, s = p2, s2; d += datetime.timedelta(days=2)
    print(f"\n{n} publicaciones simuladas · repeticiones: {bad}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(1)
    if a[0] == "add":
        sys.exit(cmd_add(a[1], a[2], a[3]))
    if a[0] == "check":
        sys.exit(cmd_check())
    if a[0] == "plan":
        sys.exit(cmd_plan(int(a[1]) if len(a) > 1 else 20))
    print(__doc__); sys.exit(1)
