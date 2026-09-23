#!/usr/bin/env python3
"""Art's Golf Cars — backfill de Instagram -> Facebook (una sola vez, re-ejecutable).

Lee el FEED REAL publicado en Instagram (@agolfcars) por la Graph API de Instagram y
republica cada post de imagen en la Pagina de Facebook, con el MISMO caption, en orden
cronologico (los mas antiguos primero) para que el muro de Facebook quede igual que el
de Instagram.

- Idempotente: guarda en .fb_mirror_state.json los id de media de IG ya espejados, asi
  que re-ejecutarlo NO duplica; solo publica lo que falte.
- No toca Instagram. Solo publica en Facebook.
- Requiere en Keychain: AGOLFCARS_IG_ACCESS_TOKEN / _ACCOUNT_ID (ya existen) y
  AGOLFCARS_FB_PAGE_ID / _TOKEN (los crea fb_setup_token.py).

Uso:
    python3 ~/agolfcars-social/fb_backfill.py            # publica de verdad
    DRY=1 python3 ~/agolfcars-social/fb_backfill.py      # simulacro, no publica
"""
import json, os, subprocess, sys, time, urllib.parse, urllib.request, urllib.error

BASE_DIR = os.path.expanduser("~/agolfcars-social")
STATE    = os.path.join(BASE_DIR, ".fb_mirror_state.json")
SECRETS  = "/Users/victor/Code/CyberSecurity/scripts/secrets.sh"
IG_GRAPH = "https://graph.instagram.com/v21.0"
FB_GRAPH = "https://graph.facebook.com/v21.0"
DRY      = os.environ.get("DRY") == "1"
UA       = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
# Pausa entre publicaciones: reparte la carga y respeta los limites de la Pagina.
# 4 s es holgado (el limite real es ~decenas/min); evita rafagas que Meta penaliza.
GAP_SECONDS = 4


def secret(name):
    return subprocess.check_output([SECRETS, "get", name]).decode().strip()


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def http_post(url, params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "body": e.read().decode()[:300]}


def load_state():
    try:
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {"mirrored": []}


def save_state(s):
    with open(STATE, "w") as f:
        json.dump(s, f, indent=2)


def fetch_ig_feed(ig_id, ig_tok):
    """Devuelve TODA la media de IG, mas antigua primero."""
    items, url = [], (f"{IG_GRAPH}/{ig_id}/media?fields=id,caption,media_type,media_url,"
                      f"thumbnail_url,timestamp,permalink&limit=50&access_token={urllib.parse.quote(ig_tok)}")
    while url:
        j = http_get(url)
        if "error" in j:
            sys.exit(f"Error leyendo el feed de IG: {json.dumps(j['error'])[:300]}")
        items.extend(j.get("data", []))
        url = (j.get("paging") or {}).get("next")
    items.reverse()  # cronologico: los mas antiguos primero
    return items


def image_url_for(item, ig_tok):
    """URL de imagen publicable en FB. IMAGE -> media_url. CAROUSEL -> 1ª imagen hija."""
    mt = item.get("media_type")
    if mt == "IMAGE":
        return item.get("media_url")
    if mt == "CAROUSEL_ALBUM":
        j = http_get(f"{IG_GRAPH}/{item['id']}/children?fields=media_url,media_type"
                     f"&access_token={urllib.parse.quote(ig_tok)}")
        for ch in j.get("data", []):
            if ch.get("media_type") == "IMAGE" and ch.get("media_url"):
                return ch["media_url"]
    return None  # VIDEO/REELS: se omiten (FB los trata distinto)


def main():
    ig_id  = secret("AGOLFCARS_IG_ACCOUNT_ID")
    ig_tok = secret("AGOLFCARS_IG_ACCESS_TOKEN")
    try:
        fb_id  = secret("AGOLFCARS_FB_PAGE_ID")
        fb_tok = secret("AGOLFCARS_FB_PAGE_TOKEN")
    except Exception:
        sys.exit("Falta el token de Pagina de Facebook. Ejecuta primero fb_setup_token.py.")

    state = load_state()
    done  = set(state.get("mirrored", []))

    feed = fetch_ig_feed(ig_id, ig_tok)
    print(f"Instagram tiene {len(feed)} publicaciones. Ya espejadas: {len(done)}.")

    posted = skipped = failed = 0
    for it in feed:
        mid = it["id"]
        if mid in done:
            continue
        img = image_url_for(it, ig_tok)
        caption = it.get("caption") or ""
        when = it.get("timestamp", "")[:10]
        if not img:
            print(f"  · omito {mid} ({it.get('media_type')}, sin imagen) {when}")
            skipped += 1
            continue
        if DRY:
            print(f"  [DRY] publicaria {mid} {when}: {caption[:60].replace(chr(10),' ')}...")
            posted += 1
            continue
        res = http_post(f"{FB_GRAPH}/{fb_id}/photos",
                        {"url": img, "caption": caption, "published": "true", "access_token": fb_tok})
        if res.get("id") or res.get("post_id"):
            done.add(mid)
            state["mirrored"] = sorted(done)
            save_state(state)  # persistir tras CADA publicacion (re-ejecutable sin duplicar)
            posted += 1
            print(f"  [OK] {when} -> FB id {res.get('post_id') or res.get('id')}")
            time.sleep(GAP_SECONDS)
        else:
            failed += 1
            print(f"  [FALLO] {mid} {when}: {json.dumps(res)[:200]}")
            if res.get("_http_error") in (400, 190):
                # 190 = token invalido/caducado; 400 puede ser limite: parar en seco.
                print("  Detengo el backfill (token o limite). Re-ejecuta mas tarde para continuar.")
                break

    print(f"\nResumen: publicadas {posted}, omitidas {skipped}, fallidas {failed}.")
    if not DRY and posted:
        print("Facebook ahora refleja el feed de Instagram. Re-ejecutar es seguro (no duplica).")


if __name__ == "__main__":
    main()
