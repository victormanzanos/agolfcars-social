#!/usr/bin/env python3
"""Art's Golf Cars — DAILY ENGINE para @agolfcars.

Clonado del motor probado de @manzanoshabitat/@manzanosmobility (mismas
defensas: idempotencia local + server-side, estado persistido justo tras
publicar, api() nunca propaga errores de red) con:
- Credenciales propias (AGOLFCARS_IG_ACCESS_TOKEN / _ACCOUNT_ID)
- Repo público propio: github.com/victormanzanos/agolfcars-social
- Captions parseadas de CAPTIONS.md (single source of truth)
- Cadencia cada 2 días: ordinal%2==0. Coincide en días con Habitat (pares)
  pero son cuentas distintas con horas de disparo distintas — sin problema.
- Idempotencia (1 publicación/día), jitter, defer aleatorio, foto real opcional
  (drop folder ~/agolfcars-social/reales — fotos del concesionario).

Variables de entorno:
  DRY=1     → preview sin publicar ni email (no necesita credenciales)
  FORCE=1   → salta la guardia de "día de descanso"
"""
import datetime, json, os, random, re, ssl, smtplib, subprocess, time
import urllib.request, urllib.parse, urllib.error
import base64, hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# ── CONFIG ────────────────────────────────────────────────────────────────
LOCAL    = os.path.expanduser("~/agolfcars-social")
SECRETS  = os.path.expanduser("~/Code/CyberSecurity/scripts/secrets.sh")
STATE    = os.path.join(LOCAL, ".daily_state.json")
CAPTIONS_FILE = os.path.join(LOCAL, "CAPTIONS.md")
RAW      = "https://raw.githubusercontent.com/victormanzanos/agolfcars-social/main"
BASE     = "https://graph.instagram.com/v23.0"
REPO     = "victormanzanos/agolfcars-social"
H        = "#ArtsGolfCars"   # brand hashtag — siempre se mantiene

# Cadencia: cada 2 días (julian ordinal % 2 == 0)
CYCLE_DIV = 2
CYCLE_DAY = 0

# Foto real intercalada — 1 real cada N posts de marca (drop folder ~/agolfcars-social/reales)
REAL_EVERY = 3
TDIR     = os.path.join(LOCAL, "reales")
DONE_DIR = os.path.join(TDIR, "published")
IMG_EXT  = (".jpg", ".jpeg", ".png")
DEFAULT_REAL_CAPTION = (
    "Straight from the lot at Art's Golf Cars 🌴\n"
    "Central Florida's premier golf car dealership. New & pre-owned golf cars, "
    "service, parts and accessories in Dundee, FL. Link in bio.\n\n"
    "#ArtsGolfCars #GolfCart #CentralFlorida #DundeeFL #GolfCartLife"
)

DRY = os.environ.get("DRY") == "1"

# Credenciales — lazy load para que DRY=1 funcione sin credenciales
TOK = None
IGID = None
def _secret(n):
    return subprocess.check_output([SECRETS, "get", n]).decode().strip()
def ensure_creds():
    global TOK, IGID
    if TOK is None:
        TOK  = _secret("AGOLFCARS_IG_ACCESS_TOKEN")
        IGID = _secret("AGOLFCARS_IG_ACCOUNT_ID")


# ── PARSE CAPTIONS.md → POSTS, STORIES ────────────────────────────────────
def parse_captions(path):
    text = open(path, encoding="utf-8").read()
    sections = re.split(r"^## ", text, flags=re.M)
    posts, stories = [], []
    for sec in sections:
        head = sec.splitlines()[0].strip().upper() if sec.strip() else ""
        if "POSTS" in head and "STOR" not in head:
            target = posts
        elif "STOR" in head:
            target = stories
        else:
            continue
        for entry in re.split(r"^### ", sec, flags=re.M)[1:]:
            lines = entry.splitlines()
            if not lines:
                continue
            m = re.search(r"`([^`]+\.jpg)`", lines[0])
            if not m:
                continue
            filename = m.group(1)
            body = []
            for ln in lines[1:]:
                if ln.startswith("##") or ln.startswith("---"):
                    break
                body.append(ln)
            target.append((filename, "\n".join(body).strip()))
    return posts, stories

POSTS, STORIES = parse_captions(CAPTIONS_FILE)
STORY_FILES = [fn for fn, _ in STORIES]
assert POSTS,   "No se parsearon posts de CAPTIONS.md"
assert STORIES, "No se parsearon stories de CAPTIONS.md"


# ── STATE ─────────────────────────────────────────────────────────────────
def state():
    s = json.load(open(STATE)) if os.path.exists(STATE) else {}
    s.setdefault("post", 0)
    s.setdefault("story", 0)
    s.setdefault("since_real", 0)
    return s
def save_state(s):
    json.dump(s, open(STATE, "w"))


# ── FOTO REAL intercalada (drop folder) ───────────────────────────────────
def real_collect():
    if not os.path.isdir(TDIR):
        return []
    out = []
    for name in sorted(os.listdir(TDIR)):
        path = os.path.join(TDIR, name)
        if not os.path.isfile(path):
            continue
        base, ext = os.path.splitext(name)
        if ext.lower() not in IMG_EXT:
            continue
        cap_file = os.path.join(TDIR, base + ".txt")
        cap = open(cap_file, encoding="utf-8").read().strip() if os.path.exists(cap_file) else DEFAULT_REAL_CAPTION
        out.append((path, cap))
    return out

def gh_upload(local_path, remote_name, folder="reales"):
    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    remote_path = f"{folder}/{remote_name}"
    sha = None
    probe = subprocess.run(["gh", "api", f"/repos/{REPO}/contents/{remote_path}"],
                           capture_output=True, text=True)
    if probe.returncode == 0:
        try:    sha = json.loads(probe.stdout).get("sha")
        except: sha = None
    args = ["gh", "api", "--method", "PUT", f"/repos/{REPO}/contents/{remote_path}",
            "-f", f"message=Add real photo {remote_name}", "-f", f"content={content_b64}"]
    if sha: args += ["-f", f"sha={sha}"]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh upload failed: {r.stderr.strip()[:300]}")
    return f"{RAW}/{remote_path}"

def archive_real(path):
    os.makedirs(DONE_DIR, exist_ok=True)
    name = os.path.basename(path)
    os.rename(path, os.path.join(DONE_DIR, name))
    cap_file = os.path.join(TDIR, os.path.splitext(name)[0] + ".txt")
    if os.path.exists(cap_file):
        os.rename(cap_file, os.path.join(DONE_DIR, os.path.basename(cap_file)))


# ── DÍAS ESPECIALES US / FLORIDA ──────────────────────────────────────────
# Petición de Victor (2026-07-21): cualquier día especial de EE.UU. o Florida
# tiene su propio post + story ese mismo día. Se publica AUNQUE sea día de
# descanso y NO consume el turno de la rotación (los índices no avanzan).
# Tarjeta = make_text_card (texto dorado sobre verde tinta). Determinista,
# sin depender de servicios externos.

def _nth_weekday(year, month, weekday, n):
    """n-ésimo weekday (0=lunes) del mes."""
    d = datetime.date(year, month, 1)
    return d + datetime.timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))

def _last_weekday(year, month, weekday):
    d = (datetime.date(year, 12, 31) if month == 12
         else datetime.date(year, month + 1, 1) - datetime.timedelta(days=1))
    return d - datetime.timedelta(days=(d.weekday() - weekday) % 7)

def _easter(year):
    """Computus gregoriano (algoritmo anónimo)."""
    a = year % 19
    b, c = divmod(year, 100)
    dd, e = divmod(b, 4)
    g = (8 * b + 13) // 25
    h = (19 * a + b - dd - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return datetime.date(year, month, day + 1)

def special_day(d):
    """(slug, texto_tarjeta, caption) del día especial US/FL en la fecha d, o None."""
    y = d.year
    fixed = {
        (1, 1):   ("new-year", f"Happy New Year {y}",
                   f"Happy New Year from Art's Golf Cars! 🎆 Here's to new rides and new adventures in {y}.\n\n#ArtsGolfCars #HappyNewYear #NewYear #CentralFlorida #GolfCartLife"),
        (2, 14):  ("valentines", "Happy Valentine's Day",
                   "Happy Valentine's Day! ❤️ Love is a two-seater.\n\n#ArtsGolfCars #ValentinesDay #GolfCartLife #CentralFlorida"),
        (3, 3):   ("florida-statehood", "Happy Birthday, Florida",
                   "Happy Birthday, Florida! On March 3, 1845 the Sunshine State became the 27th state of the Union. Proud to call it home. 🌴\n\n#ArtsGolfCars #Florida #SunshineState #FloridaStatehood #CentralFlorida"),
        (3, 17):  ("st-patricks", "Happy St. Patrick's Day",
                   "Happy St. Patrick's Day! 🍀 May your day be lucky and your ride be smooth.\n\n#ArtsGolfCars #StPatricksDay #GolfCartLife #CentralFlorida"),
        (4, 2):   ("pascua-florida", "Happy Pascua Florida Day",
                   "Happy Pascua Florida Day! On April 2, 1513 Juan Ponce de León sighted the land he named La Florida. Celebrating the state we call home. 🌴\n\n#ArtsGolfCars #PascuaFlorida #Florida #SunshineState #FloridaHistory"),
        (6, 19):  ("juneteenth", "Juneteenth",
                   "Honoring Juneteenth, Freedom Day. 🕊️\n\n#Juneteenth #FreedomDay #ArtsGolfCars"),
        (7, 4):   ("july-4", "Happy 4th of July",
                   "Happy Independence Day! 🇺🇸 Wishing you a safe and happy 4th of July from all of us at Art's Golf Cars.\n\n#ArtsGolfCars #4thOfJuly #IndependenceDay #USA #CentralFlorida"),
        (10, 4):  ("golf-lovers-day", "Happy Golf Lover's Day",
                   "Happy National Golf Lover's Day! ⛳ Our favorite day of the year, for obvious reasons.\n\n#ArtsGolfCars #GolfLoversDay #Golf #GolfCart #CentralFlorida"),
        (11, 11): ("veterans-day", "Thank You, Veterans",
                   "Thank you, Veterans. Today and every day, we honor your service and sacrifice. 🇺🇸\n\n#VeteransDay #ThankYouVeterans #ArtsGolfCars"),
        (12, 25): ("christmas", "Merry Christmas",
                   "Merry Christmas from the Art's Golf Cars family to yours! 🎄\n\n#ArtsGolfCars #MerryChristmas #Christmas #CentralFlorida"),
        (12, 31): ("new-years-eve", "See You Next Year",
                   f"Cheers to the last ride of {y}. See you in {y + 1}! 🥂\n\n#ArtsGolfCars #NewYearsEve #GolfCartLife #CentralFlorida"),
    }
    if (d.month, d.day) in fixed:
        return fixed[(d.month, d.day)]
    floating = {
        _nth_weekday(y, 1, 0, 3):  ("mlk-day", "Honoring Dr. King",
                                    "Honoring the life and legacy of Dr. Martin Luther King Jr. 🕊️\n\n#MLKDay #MartinLutherKingJr #ArtsGolfCars"),
        _nth_weekday(y, 2, 0, 3):  ("presidents-day", "Happy Presidents' Day",
                                    "Happy Presidents' Day! 🇺🇸\n\n#ArtsGolfCars #PresidentsDay #USA #CentralFlorida"),
        _easter(y):                ("easter", "Happy Easter",
                                    "Happy Easter from all of us at Art's Golf Cars! 🐣\n\n#ArtsGolfCars #HappyEaster #Easter #CentralFlorida"),
        _nth_weekday(y, 5, 6, 2):  ("mothers-day", "Happy Mother's Day",
                                    "Happy Mother's Day to all the amazing moms out there! 💐\n\n#ArtsGolfCars #MothersDay #CentralFlorida #FloridaLiving"),
        _last_weekday(y, 5, 0):    ("memorial-day", "In Remembrance",
                                    "Memorial Day. Honoring those who gave everything. 🇺🇸\n\n#MemorialDay #Remember #ArtsGolfCars"),
        _nth_weekday(y, 6, 6, 3):  ("fathers-day", "Happy Father's Day",
                                    "Happy Father's Day to all the dads! Enjoy the ride. 🏌️‍♂️\n\n#ArtsGolfCars #FathersDay #GolfCartLife #CentralFlorida"),
        _nth_weekday(y, 9, 0, 1):  ("labor-day", "Happy Labor Day",
                                    "Happy Labor Day! Here's to hard work and a well-earned day off. 🇺🇸\n\n#ArtsGolfCars #LaborDay #USA #CentralFlorida"),
        _nth_weekday(y, 11, 3, 4): ("thanksgiving", "Happy Thanksgiving",
                                    "Happy Thanksgiving from our family to yours. Grateful for this community, today and every day. 🦃\n\n#ArtsGolfCars #Thanksgiving #Grateful #CentralFlorida"),
    }
    return floating.get(d)


def publish_special_day(s, hol):
    """Publica el post + story del día especial. Devuelve True si publicó (o ya estaba)."""
    slug, card_text, caption = hol
    today = str(datetime.date.today())
    year = datetime.date.today().year
    print(f"DÍA ESPECIAL: {slug} → \"{card_text}\"")
    if DRY:
        print(f"--- CAPTION ---\n{caption}\n--- DRY RUN, nada publicado.")
        return True
    if s.get("last_date") == today:
        print(f"Ya se publicó hoy ({today}).")
        return True
    # Idempotencia server-side (el estado pudo perderse): mismo caption ya arriba → sync.
    body = caption_body(caption)
    if body and latest_post_body() == body:
        print("El post del día especial YA es el último del feed — re-sincronizo estado.")
        s["last_date"] = today
        save_state(s)
        return True
    from make_agolfcars import make_text_card
    # WHY: eyebrow "DUNDEE, FLORIDA" — el logo de abajo ya dice el nombre de la
    # marca; repetirlo en el rótulo superior era redundante
    pf_local = make_text_card(card_text, f"holiday-{slug}-{year}.jpg", story=False, eyebrow="DUNDEE, FLORIDA")
    sf_local = make_text_card(card_text, f"holiday-{slug}-{year}-story.jpg", story=True, eyebrow="DUNDEE, FLORIDA")
    url_p = gh_upload(pf_local, os.path.basename(pf_local), folder="holidays")
    url_s = gh_upload(sf_local, os.path.basename(sf_local), folder="holidays")
    time.sleep(5)  # que el raw URL propague
    time.sleep(random.randint(30, 240))  # jitter corto: el día especial debe salir sí o sí
    pr = publish_image(url_p, caption=caption)
    post_ok = bool(pr.get("permalink") or pr.get("id"))
    if post_ok:
        # WHY: NO avanzamos s["post"]/s["story"] — el día especial no consume
        # el turno de la rotación; solo marca que hoy ya se publicó.
        s["last_date"] = today
        save_state(s)
    time.sleep(random.randint(20, 120))
    sr = publish_image(url_s, story=True)
    story_ok = bool(sr.get("permalink") or sr.get("id"))
    plink = (pr.get("permalink")
             or (f"publicado (id {pr.get('id')})" if pr.get("id")
                 else "ERROR: " + json.dumps(pr)[:220]))
    sok = "publicada ✅" if story_ok else ("ERROR: " + json.dumps(sr)[:220])
    print("post especial:", plink)
    print("story especial:", sok)
    subj = (f"🎉 Instagram — Art's Golf Cars · día especial: {card_text}"
            if post_ok else
            f"⚠️ FALLO al publicar día especial ({slug}) — Instagram Art's Golf Cars")
    email_summary(
        f"<p>Día especial <b>{card_text}</b> publicado en <b>@agolfcars</b>:</p>"
        f"<p>📸 <b>Post:</b> <a href='{plink}'>{plink}</a><br>📱 <b>Story:</b> {sok}</p>"
        f"<table cellpadding='6'><tr>"
        f"<td valign='top' align='center'><img src='cid:postimg' width='300' style='border-radius:10px;border:1px solid #ddd'></td>"
        f"<td valign='top' align='center'><img src='cid:storyimg' width='210' style='border-radius:10px;border:1px solid #ddd'></td>"
        f"</tr></table>"
        f"<pre style='white-space:pre-wrap;color:#555;font-size:12px'>{caption}</pre>"
        f"<p style='color:#aaa;font-size:11px'>Los días especiales publican aunque sea día de descanso y no consumen la rotación.</p>",
        pf_local, sf_local, subject=subj
    )
    return post_ok


# ── INSTAGRAM GRAPH API ───────────────────────────────────────────────────
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
def api(path, params, method="POST"):
    data = urllib.parse.urlencode(params).encode()
    hdr  = {"User-Agent": UA}
    if method == "GET":
        req = urllib.request.Request(f"{BASE}/{path}?{data.decode()}", headers=hdr)
    else:
        req = urllib.request.Request(f"{BASE}/{path}", data=data, method="POST", headers=hdr)
    try:
        with urllib.request.urlopen(req) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "body": e.read().decode()}
    except Exception as e:
        # WHY: un fallo de red (URLError/DNS/timeout) NUNCA debe propagar y matar el
        # script. El 2026-07-05 (motor habitat) un URLError al pedir el permalink
        # DESPUÉS de publicar crasheó main() antes de save_state() y causó un post
        # duplicado dos días después. Aquí heredamos la defensa.
        return {"_net_error": str(e)}

def wait_ready(cid):
    for _ in range(20):
        st = api(cid, {"fields": "status_code", "access_token": TOK}, "GET").get("status_code")
        if st in ("FINISHED", "ERROR", "EXPIRED"): return st
        time.sleep(4)
    return "TIMEOUT"

def publish_image(url, caption=None, story=False):
    ensure_creds()
    p = {"image_url": url, "access_token": TOK}
    if story:   p["media_type"] = "STORIES"
    if caption: p["caption"]    = caption
    c = api(f"{IGID}/media", p); cid = c.get("id")
    if not cid: return {"error": c}
    if wait_ready(cid) != "FINISHED": return {"error": "container not ready"}
    r = api(f"{IGID}/media_publish", {"creation_id": cid, "access_token": TOK})
    mid = r.get("id")
    if not mid: return {"error": r}
    # El post YA está publicado (tenemos mid). El permalink es informativo: si su
    # fetch falla (red), devolvemos igualmente el id para que el caller marque el
    # post como OK y persista el estado — así no se republica al día siguiente.
    perma = api(mid, {"fields": "permalink", "access_token": TOK}, "GET")
    return {"id": mid, "permalink": perma.get("permalink")}


# ── EMAIL RESUMEN ─────────────────────────────────────────────────────────
def email_summary(html, post_path, story_path, subject):
    pw = _secret("MANZANOS_SMTP_PASSWORD")
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"]    = "assistant@manzanosenterprises.com"
    msg["To"]      = "victor@manzanos.com"
    msg.attach(MIMEText(html, "html", "utf-8"))
    for cid, path in (("postimg", post_path), ("storyimg", story_path)):
        try:
            with open(path, "rb") as f: img = MIMEImage(f.read())
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=os.path.basename(path))
            msg.attach(img)
        except Exception as e: print("attach failed", path, e)
    with smtplib.SMTP_SSL("manzanosenterprises-com.correoseguro.dinaserver.com", 465,
                          context=ssl.create_default_context()) as srv:
        srv.login("assistant@manzanosenterprises.com", pw)
        srv.send_message(msg)


# ── IDEMPOTENCIA SERVER-SIDE (evita post duplicado aunque falle el estado) ─
def caption_body(cap):
    """Cuerpo del caption sin las líneas de hashtags (estable frente a rotación)."""
    lines = []
    for ln in (cap or "").split("\n"):
        toks = ln.split()
        if toks and all(t.startswith("#") for t in toks):
            continue
        lines.append(ln)
    return "\n".join(lines).strip()

def latest_post_body():
    """Cuerpo (sin hashtags) del último post del feed, o None si no se puede leer.
    Fail-open: ante cualquier error de red devuelve None y NO bloquea la publicación."""
    ensure_creds()
    r = api(f"{IGID}/media", {"fields": "caption", "limit": "1", "access_token": TOK}, "GET")
    data = r.get("data") if isinstance(r, dict) else None
    if not data:
        return None
    return caption_body(data[0].get("caption"))


# ── CAPTION ROTATION (anti-spam hashtags) ─────────────────────────────────
def rotate_caption(cap):
    body, tags = [], []
    for ln in cap.split("\n"):
        toks = ln.split()
        if toks and all(t.startswith("#") for t in toks):
            tags.extend(toks)
        else:
            body.append(ln)
    if not tags:
        return cap
    brand = [t for t in tags if t.lower() == H.lower()]
    rest  = [t for t in tags if t.lower() != H.lower()]
    random.shuffle(rest)
    k = min(len(rest), random.randint(4, 8))
    chosen = brand + rest[:k]
    random.shuffle(chosen)
    return "\n".join(body).rstrip() + "\n" + " ".join(chosen)


# ── MAIN ──────────────────────────────────────────────────────────────────
def main():
    s = state()

    # Día especial US/Florida: publica SIEMPRE ese día (aunque toque descanso)
    # y termina — la rotación normal no avanza.
    hol = special_day(datetime.date.today())
    if hol:
        publish_special_day(s, hol)
        return

    real_items = real_collect()
    do_real    = bool(real_items) and s.get("since_real", 0) >= REAL_EVERY
    real_path  = real_items[0][0] if real_items else None
    real_cap   = real_items[0][1] if real_items else None

    pf, cap = POSTS[s["post"] % len(POSTS)]
    cap = rotate_caption(cap)
    sf  = STORY_FILES[s["story"] % len(STORY_FILES)]
    post_url  = f"{RAW}/posts/{pf}"
    story_url = f"{RAW}/stories/{sf}"

    if do_real:
        print(f"NEXT = FOTO REAL: {os.path.basename(real_path)}  (since_real={s.get('since_real',0)} ≥ {REAL_EVERY})")
        print(f"--- CAPTION ---\n{real_cap}\n---  (story: {sf})")
    else:
        print(f"NEXT = POST MARCA: {pf}\nSTORY: {sf}\n--- CAPTION ---\n{cap}\n---  (real en {REAL_EVERY - s.get('since_real',0)} posts)")

    if DRY:
        print("DRY RUN — nada publicado.")
        return

    today = str(datetime.date.today())
    if os.environ.get("FORCE") != "1" and datetime.date.today().toordinal() % CYCLE_DIV != CYCLE_DAY:
        print(f"Día de descanso ({today}) — Art's Golf Cars publica cuando ordinal%{CYCLE_DIV}=={CYCLE_DAY}.")
        return
    if s.get("last_date") == today:
        print(f"Ya se publicó hoy ({today}).")
        return
    # Idempotencia server-side: si el post de marca de hoy YA es el último del feed
    # (p. ej. el estado se perdió/corrompió), NO republicar — solo re-sincronizar el
    # estado y salir. Defensa extra contra duplicados. Solo para posts de marca (la
    # foto real cambia de imagen cada vez). Fail-open ante error de red.
    if not do_real:
        body_today = caption_body(cap)
        if body_today and latest_post_body() == body_today:
            print("Post de hoy YA es el último del feed (idempotencia API) — re-sincronizo estado, no republico.")
            s["last_date"] = today
            s["post"] += 1
            s["since_real"] = s.get("since_real", 0) + 1
            save_state(s)
            return
    if datetime.datetime.now().hour < 14 and random.random() < 0.40:
        print("Aplazo a franja posterior (rompe patrón horario).")
        return
    time.sleep(random.randint(30, 480))  # jitter

    # ── Publicar POST ──────────────────────────────────────────────────────
    is_real = False
    if do_real:
        try:
            h = hashlib.sha1(open(real_path, "rb").read()).hexdigest()[:8]
            base, ext = os.path.splitext(os.path.basename(real_path))
            url = gh_upload(real_path, f"{base}-{h}{ext.lower()}")
            time.sleep(5)
            pr = publish_image(url, caption=real_cap)
            # WHY: id basta — el post YA está publicado aunque el fetch del permalink
            # falle por red; sin esto se publicaba TAMBIÉN el post de marca (duplicado)
            if pr.get("permalink") or pr.get("id"):
                is_real = True; cap = real_cap; post_url = url
            else:
                print("Foto real falló, fallback a marca:", json.dumps(pr)[:200])
                pr = publish_image(post_url, caption=cap)
        except Exception as e:
            print("EXCEPCIÓN foto real, fallback a marca:", e)
            pr = publish_image(post_url, caption=cap)
    else:
        pr = publish_image(post_url, caption=cap)

    # WHY: persistir el estado JUSTO cuando el post está confirmado publicado
    # (tenemos permalink o id), ANTES de publicar el story / enviar el email. Si
    # algún paso posterior crashea (red, etc.), last_date ya está guardado y el post
    # NO se republicará al día siguiente. `id` cuenta como OK aunque falte permalink.
    post_ok = bool(pr.get("permalink") or pr.get("id"))
    if post_ok:
        s["last_date"] = today
        if is_real:
            archive_real(real_path); s["since_real"] = 0
        else:
            s["post"] += 1
            s["since_real"] = s.get("since_real", 0) + 1
        save_state(s)

    time.sleep(random.randint(20, 120))  # gap humano antes del story
    sr = publish_image(story_url, story=True)
    story_ok = bool(sr.get("permalink") or sr.get("id"))
    if story_ok:
        s["story"] += 1
        save_state(s)

    plink = (pr.get("permalink")
             or (f"publicado (id {pr.get('id')}, permalink no disponible)" if pr.get("id")
                 else "ERROR: " + json.dumps(pr)[:220]))
    sok   = "publicada ✅" if story_ok else ("ERROR: " + json.dumps(sr)[:220])
    print("post:", plink, "(real)" if is_real else "(marca)")
    print("story:", sok)

    subj = ("📲 Instagram — Art's Golf Cars"
            if post_ok else
            "⚠️ FALLO al publicar — Instagram Art's Golf Cars (revisar)")
    post_path  = real_path if is_real else os.path.join(LOCAL, "posts", pf)
    story_path = os.path.join(LOCAL, "stories", sf)
    kind = "Foto real (drop folder)" if is_real else f"Post {s['post']}/{len(POSTS)}"
    email_summary(
        f"<p>Publicado hoy en <b>@agolfcars</b> · <b>{kind}</b>:</p>"
        f"<p>📸 <b>Post:</b> <a href='{plink}'>{plink}</a><br>📱 <b>Story:</b> {sok}</p>"
        f"<table cellpadding='6'><tr>"
        f"<td valign='top' align='center'><div style='color:#888;font-size:11px;letter-spacing:1px'>POST</div>"
        f"<img src='cid:postimg' width='300' style='border-radius:10px;border:1px solid #ddd'></td>"
        f"<td valign='top' align='center'><div style='color:#888;font-size:11px;letter-spacing:1px'>STORY</div>"
        f"<img src='cid:storyimg' width='210' style='border-radius:10px;border:1px solid #ddd'></td>"
        f"</tr></table>"
        f"<p style='color:#888;font-size:12px'>Caption:</p>"
        f"<pre style='white-space:pre-wrap;color:#555;font-size:12px'>{cap}</pre>"
        f"<p style='color:#aaa;font-size:11px'>Cadencia cada 2 días (ordinal%2==0) · rotación automática.</p>",
        post_path, story_path, subject=subj
    )



# ── ERP SOCIAL HUB (agolfcars.com/erp → vista Social) ─────────────────────
# El equipo puede BLOQUEAR tarjetas o CORREGIR captions desde el ERP; este motor
# consulta esos controles justo antes de publicar. Fail-open: sin red, sin
# secreto o con respuesta rara → la rotación sigue intacta. (2026-08-04)
def _hub_controls():
    import os as _os, json as _json, subprocess as _sp, urllib.request as _ur, urllib.parse as _up
    try:
        sec = _sp.check_output([_os.path.expanduser("~/Code/CyberSecurity/scripts/secrets.sh"),
                                "get", "AGC_SOCIAL_SYNC_SECRET"], timeout=15).decode().strip()
        if not sec:
            return set(), {}
        q = _up.urlencode({"handle": "agolfcars", "secret": sec})
        req = _ur.Request("https://agolfcars.com/api/social-sync.php?" + q,
                          headers={"User-Agent": "Mozilla/5.0 (social-engine)"})
        with _ur.urlopen(req, timeout=8) as r:
            d = _json.load(r)
        ov = d.get("overrides") or {}
        return set(d.get("blocked") or []), (ov if isinstance(ov, dict) else {})
    except Exception:
        return set(), {}

_HUB_BLOCKED, _HUB_OVERRIDES = (set(), {}) if os.environ.get("DRY") == "1" else _hub_controls()
if _HUB_BLOCKED or _HUB_OVERRIDES:
    def _hub_tuples(lst):
        kept = [(f, _HUB_OVERRIDES.get(f, c)) for f, c in lst if f not in _HUB_BLOCKED]
        return kept or lst  # nunca vaciar una baraja entera
    POSTS[:] = _hub_tuples(POSTS)
    STORIES[:] = _hub_tuples(STORIES)
    STORY_FILES[:] = [fn for fn, _ in STORIES]

if __name__ == "__main__":
    main()
