"""One-time post for @agolfcars + the Facebook page: 2027 Boca Purebred just arrived (Victor, 25-nov-2026: "new boca cars just arrived today for social media").
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

MARK = os.path.join(BASE, ".boca2027arrival_posted")
POST_URL = de.RAW + "/special/boca-2027-arrival-post.jpg"
STORY_URL = de.RAW + "/special/boca-2027-arrival-story.jpg"
DRY = os.environ.get("DRY") == "1"

CAPTION = """Just arrived at Art's Golf Cars: the new 2027 Boca Purebred. 🚙

Four forward-facing seats with seatbelts, Apple CarPlay and Android Auto, an HD backup camera, phone chargers, a soundbar and LED lighting for evening rides. The lowered chassis stays under 76 inches, so it fits most community tunnels.

In red, white, black and grey, with dark walnut seats. Come see them in Dundee or call (863) 439-5431.

Art's Golf Cars, 29630 US Hwy 27, Dundee, FL
agolfcars.com

#ArtsGolfCars #BocaEV #BocaPurebred #NewGolfCart #GolfCart #DundeeFL #PolkCounty #CentralFlorida #GolfCartLife"""


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
        mail("[Art's IG] Boca 2027 arrival post FAILED", f"<p>Instagram refused the Boca 2027 arrival post: <code>{json.dumps(r)[:300]}</code>.</p>")
        return 1
    print("instagram post:", r.get("permalink") or r.get("id"))
    fb = de.fb_mirror_post(POST_URL, CAPTION)
    st = de.publish_image(STORY_URL, story=True)
    fbs = de.fb_mirror_story(STORY_URL) if st.get("id") else {"skipped": "ig story failed"}
    with open(MARK, "w") as f:
        json.dump({"date": today.isoformat(), "ig": r, "fb": fb, "story": st, "fb_story": fbs}, f, default=str)
    mail("[Art's IG] Boca 2027 arrival post published",
         f"<p>Boca 2027 arrival post published on Instagram and Facebook.</p>"
         f"<p>Instagram: <a href='{r.get('permalink') or ''}'>{r.get('permalink') or r.get('id')}</a><br>"
         f"Facebook: {fb.get('post_id') or fb.get('id') or fb}<br>"
         f"Story IG: {'ok' if st.get('id') else st} · Story FB: {'ok' if (fbs.get('post_id') or fbs.get('id') or fbs.get('success')) else fbs}</p>"
         f"<p><img src='{POST_URL}' width='360'></p>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
