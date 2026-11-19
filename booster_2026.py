"""One-time post for @agolfcars + the Facebook page: free booster charger loan (Victor, 18-nov-2026: "post it").
Run by hand once. Images: special/booster-charger-2026-*.jpg in the public repo. Idempotent: the marker is claimed
BEFORE publishing (O_EXCL) and released only if Instagram fails. DRY=1 prints what it would do.
"""
import os, sys, json, datetime, smtplib, subprocess
from email.mime.text import MIMEText

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)
import daily_engine as de
import ig_guard

MARK = os.path.join(BASE, ".booster2026_posted")
POST_URL = de.RAW + "/special/booster-charger-2026-post.jpg"
STORY_URL = de.RAW + "/special/booster-charger-2026-story.jpg"
DRY = os.environ.get("DRY") == "1"

CAPTION = """Back for the season and your golf car won't start? After months sitting unused, the batteries may only need a boost.

Borrow one of our battery booster chargers for E-Z-GO and Club Car golf cars, free of charge. Call (863) 439-5431 to reserve one, pick it up at our Dundee store and bring it back the next day.

If your batteries still won't hold a charge, our technicians can test them and walk you through replacement and lithium options.

Art's Golf Cars, 29630 US Hwy 27, Dundee, FL
Details: agolfcars.com/service.html#booster-charger

#ArtsGolfCars #GolfCart #Snowbirds #DundeeFL #PolkCounty #CentralFlorida #GolfCartBatteries #ClubCar #EZGO"""


def mail(subject, html):
    try:
        pw = de._secret("VICTORIA_STERLING_EMAIL_PASSWORD")
        m = MIMEText(html, "html", "utf-8")
        m["Subject"], m["From"], m["To"] = subject, "Victoria Sterling <victoriasterling@manzanos.eu>", "victor@manzanos.com"
        with smtplib.SMTP_SSL("manzanos-eu.correoseguro.dinaserver.com", 465, timeout=120) as s:
            s.login("victoriasterling@manzanos.eu", pw)
            s.sendmail("victoriasterling@manzanos.eu", ["victor@manzanos.com"], m.as_bytes())
    except Exception as e:
        print("email error:", e)


def main():
    today = datetime.date.today()
    assert "—" not in CAPTION
    if DRY:
        print("DRY: would post", POST_URL, "+ story", STORY_URL); print(CAPTION); return 0
    ok, why = ig_guard.host_ok()
    if not ok:
        print("not the publisher Mac:", why); return 0
    try:
        fd = os.open(MARK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, today.isoformat().encode()); os.close(fd)
    except FileExistsError:
        print("already posted (marker present)"); return 0

    r = de.publish_image(POST_URL, CAPTION)
    if not r.get("id"):
        os.remove(MARK)   # WHY: nothing went out, so it can be run again
        print("instagram post FAILED:", json.dumps(r)[:300])
        mail("[Art's IG] Booster charger post FAILED", f"<p>Instagram refused the booster charger post: <code>{json.dumps(r)[:300]}</code>.</p>")
        return 1
    print("instagram post:", r.get("permalink") or r.get("id"))
    fb = de.fb_mirror_post(POST_URL, CAPTION)
    st = de.publish_image(STORY_URL, story=True)
    fbs = de.fb_mirror_story(STORY_URL) if st.get("id") else {"skipped": "ig story failed"}
    with open(MARK, "w") as f:
        json.dump({"date": today.isoformat(), "ig": r, "fb": fb, "story": st, "fb_story": fbs}, f, default=str)
    mail("[Art's IG] Booster charger post published",
         f"<p>Booster charger post published on Instagram and Facebook.</p>"
         f"<p>Instagram: <a href='{r.get('permalink') or ''}'>{r.get('permalink') or r.get('id')}</a><br>"
         f"Facebook: {fb.get('post_id') or fb.get('id') or fb}<br>"
         f"Story IG: {'ok' if st.get('id') else st} · Story FB: {'ok' if (fbs.get('post_id') or fbs.get('id') or fbs.get('success')) else fbs}</p>"
         f"<p><img src='{POST_URL}' width='360'></p>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
