#!/usr/bin/env python3
"""One-time Black Friday 2026 post for @agolfcars + the Facebook page (Victor, 17-nov-2026).

Runs from LaunchAgent com.agolfcars.bf2026 on Wednesday 18-nov-2026 (11:00 and 12:30 ET as a retry; moved from Friday by Victor).
WHY 11:00: the regular engine's first slot that day is 13:41; its feed guard sees a post today and skips,
so Friday shows the Black Friday post instead of the rotation card (Nov 18 is a posting day, ordinal%2==0).
Same offer and wording as the website pop-up (bf-popup.js). Images: special/black-friday-2026-*.jpg in the
public repo. Idempotent: the marker is claimed BEFORE publishing (O_EXCL) and released only if Instagram fails.
DRY=1 prints what it would do. After 20-nov it does nothing (unload the LaunchAgent then).
"""
import os, sys, json, datetime, smtplib, subprocess
from email.mime.text import MIMEText

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)
import daily_engine as de
import ig_guard

FIRST_DAY, LAST_DAY = datetime.date(2026, 11, 18), datetime.date(2026, 11, 20)  # WHY: a sleeping Mac may run it late; give it up to two extra days
MARK = os.path.join(BASE, ".bf2026_posted")
POST_URL = de.RAW + "/special/black-friday-2026-post.jpg"
STORY_URL = de.RAW + "/special/black-friday-2026-story.jpg"
DRY = os.environ.get("DRY") == "1"

CAPTION = """Black Friday special pricing in store, now through November 30.

Golf cars starting at $8,699: Evolution D5 Ranger 2+2 Plus. D5 Ranger 4 Plus from $9,699.

Visit us at 29630 US Hwy 27, Dundee, FL, or call (863) 439-5431.

In-store cash prices, while supplies last. Striping +$200. Dealer fee, preparation and sales tax not included.

#ArtsGolfCars #BlackFriday #GolfCarts #EvolutionGolfCarts #DundeeFL #PolkCounty #CentralFlorida #GolfCartLife"""


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
    if not (FIRST_DAY <= today <= LAST_DAY) and os.environ.get("FORCE") != "1":
        print(f"{today}: outside {FIRST_DAY}..{LAST_DAY}, nothing to do"); return 0
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
        os.remove(MARK)   # WHY: nothing went out, so the 12:30 run may try again
        print("instagram post FAILED:", json.dumps(r)[:300])
        mail("[Art's IG] Black Friday post FAILED", f"<p>Instagram refused the Black Friday post: <code>{json.dumps(r)[:300]}</code>. The 12:30 run will retry.</p>")
        return 1
    print("instagram post:", r.get("permalink") or r.get("id"))
    fb = de.fb_mirror_post(POST_URL, CAPTION)
    st = de.publish_image(STORY_URL, story=True)
    fbs = de.fb_mirror_story(STORY_URL) if st.get("id") else {"skipped": "ig story failed"}
    with open(MARK, "w") as f:
        json.dump({"date": today.isoformat(), "ig": r, "fb": fb, "story": st, "fb_story": fbs}, f, default=str)
    mail("[Art's IG] Black Friday post published",
         f"<p>Black Friday post published on Instagram and Facebook.</p>"
         f"<p>Instagram: <a href='{r.get('permalink') or ''}'>{r.get('permalink') or r.get('id')}</a><br>"
         f"Facebook: {fb.get('post_id') or fb.get('id') or fb}<br>"
         f"Story IG: {'ok' if st.get('id') else st} · Story FB: {'ok' if (fbs.get('post_id') or fbs.get('id') or fbs.get('success')) else fbs}</p>"
         f"<p><img src='{POST_URL}' width='360'></p>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
