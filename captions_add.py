#!/usr/bin/env python3
"""Añade entradas a CAPTIONS.md sin romper el markdown que parsea daily_engine.

Uso:  python3 captions_add.py entradas.json
donde entradas.json = [{"card":"NN-slug.jpg","kind":"post","caption":"..."} , ...]
Las de kind=story van a la seccion STORIES (una linea descriptiva).
Idempotente: si la tarjeta ya figura en el fichero, la salta.
"""
import os, sys, json, re, shutil, datetime
P = os.path.expanduser("~/agolfcars-social/CAPTIONS.md")

def main(path):
    entries = json.load(open(path))
    txt = open(P, encoding="utf-8").read()
    shutil.copyfile(P, P + ".bak-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    posts   = [e for e in entries if e["kind"] == "post"   and f"`{e['card']}`" not in txt]
    stories = [e for e in entries if e["kind"] == "story"  and f"`{e['card']}`" not in txt]

    # la seccion POSTS termina donde empieza "## ... STORIES"
    m = re.search(r"^## .*STOR.*$", txt, flags=re.M)
    if not m:
        print("No encuentro la seccion de STORIES"); return 1
    head, tail = txt[:m.start()], txt[m.start():]
    block_p = "".join(f"### `{e['card']}`\n{e['caption'].strip()}\n\n" for e in posts)
    block_s = "".join(f"### `{e['card']}`\n{e['caption'].strip()}\n\n" for e in stories)
    head = head.rstrip("\n") + "\n\n" + block_p
    tail = tail.rstrip("\n") + "\n\n" + block_s
    out = head + tail
    # actualizar el contador del encabezado "## N POSTS"
    n_posts = len(re.findall(r"^### `", head, flags=re.M))
    out = re.sub(r"^## \d+ POSTS", f"## {n_posts} POSTS", out, count=1, flags=re.M)
    open(P, "w", encoding="utf-8").write(out)
    print(f"añadidos {len(posts)} posts y {len(stories)} stories · total posts ahora {n_posts}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
