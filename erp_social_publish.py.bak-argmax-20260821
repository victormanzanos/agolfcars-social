#!/usr/bin/env python3
"""Art's Golf Cars — ERP → Instagram bridge for @artsgolfcars.

Publishes the posts Laura (or any authorized user) queues in the ERP Social
section. She writes a caption in the ERP, optionally references a photo, and sets
the status to **Scheduled**; this routine picks it up, publishes it to Instagram,
and writes the permalink back into the ERP (status -> Posted). If she gives no
photo, her words become an on-brand text card.

Flow:
  1. SSH -> `social-cli.php queue` reads erp_social_posts rows that are
     platform=instagram, status=scheduled, due (no schedule = ASAP), not posted.
  2. Build a PUBLIC image URL:
       - image_url given  -> use it (site images are gate-exempt, so public);
                             relative paths are resolved against agolfcars.com.
       - no image_url     -> render a branded text card from the caption and push
                             it to the public repo (raw.githubusercontent URL).
  3. Publish via the Instagram Graph API (reuses daily_engine's proven publisher).
  4. SSH -> `social-cli.php mark <id> posted|failed [permalink]` writes the result.
  5. Email a summary to Laura + Victor.

NEVER uses the paid Anthropic API. All network/API failures are caught so one bad
post never blocks the rest. DRY=1 previews without publishing / marking / emailing.
"""
import os, sys, json, ssl, smtplib, subprocess, shlex, base64, hashlib, time
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# Reuse the proven publisher + card generator from the daily engine.
from daily_engine import publish_image, ensure_creds, caption_body, RAW, REPO, H
from make_agolfcars import make_text_card

LOCAL   = os.path.expanduser("~/agolfcars-social")
SECRETS = os.path.expanduser("~/Code/CyberSecurity/scripts/secrets.sh")
VPS     = "agolfcars@82.98.166.134"
CLI     = "/home/agolfcars/www/api/social-cli.php"   # CLI-only bridge helper
SITE    = "https://agolfcars.com"
DRY     = os.environ.get("DRY") == "1"

# Notify both Laura and Victor when something is published.
MAIL_TO = ["laura@manzanos.com", "victor@manzanos.com"]


def secret(name):
    return subprocess.check_output([SECRETS, "get", name]).decode().strip()


def ssh(remote_cmd, timeout=90):
    """Run a command on the VPS over SSH. Returns (rc, stdout, stderr)."""
    env = {**os.environ, "SSHPASS": secret("AGOLFCARS_SSH_PASSWORD")}
    p = subprocess.run(
        ["sshpass", "-e", "ssh", "-o", "StrictHostKeyChecking=accept-new", VPS, remote_cmd],
        capture_output=True, text=True, env=env, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def fetch_queue():
    rc, out, err = ssh("php " + CLI + " queue")
    if rc != 0:
        raise RuntimeError("queue query failed: " + (err or out)[:300])
    return json.loads(out or "[]")


def mark(post_id, status, permalink=None):
    if DRY:
        print("  [DRY] would mark %s -> %s (%s)" % (post_id, status, permalink))
        return
    cmd = "php %s mark %d %s" % (CLI, int(post_id), status)
    if permalink:
        cmd += " " + shlex.quote(permalink)
    rc, out, err = ssh(cmd)
    if rc != 0:
        print("  ! mark failed for %s: %s" % (post_id, (err or out)[:200]))


def upload_card_to_repo(local_path, remote_name):
    """Push a generated card to the public repo under erp/ and return its raw URL."""
    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    remote_path = "erp/" + remote_name
    sha = None
    probe = subprocess.run(["gh", "api", "/repos/%s/contents/%s" % (REPO, remote_path)],
                           capture_output=True, text=True)
    if probe.returncode == 0:
        try:    sha = json.loads(probe.stdout).get("sha")
        except Exception: sha = None
    args = ["gh", "api", "--method", "PUT", "/repos/%s/contents/%s" % (REPO, remote_path),
            "-f", "message=ERP social card " + remote_name, "-f", "content=" + content_b64]
    if sha:
        args += ["-f", "sha=" + sha]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("gh upload failed: " + r.stderr.strip()[:300])
    return "%s/%s" % (RAW, remote_path)


def with_brand_hashtag(caption):
    """Keep Laura's words; guarantee the brand hashtag is present for the IG caption."""
    cap = (caption or "").strip()
    if H.lower() not in cap.lower():
        cap = (cap + "\n\n" + H).strip() if cap else H
    return cap


def image_for(post):
    """Return a PUBLIC image URL for the post, generating a text card if needed."""
    img = (post.get("image_url") or "").strip()
    if img:
        if img.startswith("http://") or img.startswith("https://"):
            return img
        return SITE + "/" + img.lstrip("/")   # relative -> absolute (site images are gate-exempt)
    # No image -> branded text card from the caption body (hashtags stripped for the card).
    story = post.get("kind") == "story"
    body = caption_body(post.get("caption")) or "Art's Golf Cars"
    tag = hashlib.sha1(("%s|%s" % (post["id"], body)).encode()).hexdigest()[:8]
    name = "erp-%s-%s.jpg" % (post["id"], tag)
    local = make_text_card(body, name, story=story)
    if DRY:
        return "(dry) %s/erp/%s" % (RAW, name)   # built the card locally, skip the public push
    return upload_card_to_repo(local, name)


def publish_one(post):
    kind = post.get("kind") or "post"
    story = kind == "story"
    caption = None if story else with_brand_hashtag(post.get("caption"))
    url = image_for(post)
    print("  post #%s (%s) img=%s" % (post["id"], kind, url))
    if DRY:
        print("    [DRY] caption:", (caption or "(story, no caption)")[:120])
        return {"id": post["id"], "ok": True, "permalink": "(dry-run)", "url": url,
                "caption": caption, "created_by": post.get("created_by")}
    r = publish_image(url, caption=caption, story=story)
    ok = bool(r.get("permalink") or r.get("id"))
    permalink = r.get("permalink") or (("published (id %s)" % r.get("id")) if r.get("id") else None)
    mark(post["id"], "posted" if ok else "failed", r.get("permalink"))
    return {"id": post["id"], "ok": ok, "permalink": permalink, "url": url,
            "caption": caption, "created_by": post.get("created_by"),
            "error": None if ok else json.dumps(r)[:300]}


def email_summary(results):
    if DRY or not results:
        return
    pw = secret("MANZANOS_SMTP_PASSWORD")
    rows = ""
    for r in results:
        status = ("✅ <a href='%s'>%s</a>" % (r["permalink"], r["permalink"])) if r["ok"] else \
                 ("❌ FAILED: %s" % (r.get("error") or ""))
        rows += ("<tr><td valign='top' style='padding:6px 10px;color:#888'>#%s</td>"
                 "<td valign='top' style='padding:6px 10px'>%s<br>"
                 "<span style='color:#999;font-size:12px'>%s</span></td></tr>") % (
                    r["id"], status, (r.get("caption") or "(story)")[:160])
    html = ("<p>Posts published to <b>@artsgolfcars</b> from the ERP Social queue "
            "(scheduled by the team):</p>"
            "<table cellpadding='0' cellspacing='0' style='font-family:Arial'>%s</table>"
            "<p style='color:#aaa;font-size:12px'>To post more, add a post in the ERP → "
            "Social Media and set its status to <b>Scheduled</b>.</p>") % rows
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "📲 Instagram — %d post(s) published from the ERP" % len(results)
    msg["From"] = "assistant@manzanosenterprises.com"
    msg["To"] = ", ".join(MAIL_TO)
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP_SSL("manzanosenterprises-com.correoseguro.dinaserver.com", 465,
                          context=ssl.create_default_context()) as srv:
        srv.login("assistant@manzanosenterprises.com", pw)
        srv.send_message(msg)


def main():
    try:
        queue = fetch_queue()
    except Exception as e:
        print("Cannot read ERP social queue:", e)
        return
    if not queue:
        print("Nothing scheduled in the ERP social queue.")
        return
    print("%d post(s) to publish%s." % (len(queue), " [DRY RUN]" if DRY else ""))
    results = []
    for post in queue:
        try:
            results.append(publish_one(post))
        except Exception as e:
            print("  ! error on post #%s: %s" % (post.get("id"), e))
            try:
                mark(post["id"], "failed")
            except Exception:
                pass
            results.append({"id": post.get("id"), "ok": False, "permalink": None,
                            "caption": post.get("caption"), "error": str(e)[:300]})
        time.sleep(2)
    try:
        email_summary([r for r in results if not DRY])
    except Exception as e:
        print("email summary failed (non-fatal):", e)
    ok = sum(1 for r in results if r["ok"])
    print("Done: %d ok, %d failed." % (ok, len(results) - ok))


if __name__ == "__main__":
    main()
