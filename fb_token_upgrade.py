#!/usr/bin/env python3
"""Upgrade the Arts Golf Cars FB Page token with comment permissions (17-nov-2026).
Reads the short user token from the clipboard (copied from Graph API Explorer), the app
secret from the Keychain, exchanges it for a permanent Page token, checks its scopes and
only then saves it. Never prints a token. Keeps the previous one as AGOLFCARS_FB_PAGE_TOKEN_PREV.
"""
import json, subprocess, sys, urllib.parse, urllib.request
S="/Users/victor/Code/CyberSecurity/scripts/secrets.sh"; G="https://graph.facebook.com/v21.0"
PAGE="1241311492399979"
NEED={"pages_read_engagement","pages_manage_posts","pages_read_user_content","pages_manage_engagement"}
def sec(n): return subprocess.run(["bash",S,"get",n],capture_output=True,text=True).stdout.strip()
def setsec(n,v): subprocess.run(["bash",S,"set",n],input=v+"\n",text=True,check=True,capture_output=True)
def get(u):
    try:
        with urllib.request.urlopen(u,timeout=30) as r: return json.load(r)
    except urllib.error.HTTPError as e: sys.exit("Meta: "+e.read().decode()[:300])
ut=subprocess.check_output(["pbpaste"]).decode().strip()
if not ut.startswith("EAA"): sys.exit(f"Clipboard does not hold a user token (len {len(ut)}). Nothing changed.")
app=sec("AGOLFCARS_META_APP_ID"); key=sec("AGOLFCARS_META_APP_SECRET")
ll=get(f"{G}/oauth/access_token?"+urllib.parse.urlencode({"grant_type":"fb_exchange_token","client_id":app,"client_secret":key,"fb_exchange_token":ut}))["access_token"]
pt=get(f"{G}/{PAGE}?"+urllib.parse.urlencode({"fields":"access_token,name","access_token":ll})).get("access_token")
if not pt: sys.exit("No Page token returned (was the Arts Golf Cars page ticked?). Nothing changed.")
d=get(f"{G}/debug_token?"+urllib.parse.urlencode({"input_token":pt,"access_token":f"{app}|{key}"}))["data"]
sc=set(d.get("scopes",[])); miss=NEED-sc
print("scopes:",sorted(sc),"expires_at:",d.get("expires_at"),"valid:",d.get("is_valid"))
if miss or not d.get("is_valid"): sys.exit(f"Missing scopes {sorted(miss)}. Nothing changed.")
old=sec("AGOLFCARS_FB_PAGE_TOKEN")
if old: setsec("AGOLFCARS_FB_PAGE_TOKEN_PREV",old)
setsec("AGOLFCARS_FB_PAGE_TOKEN",pt)
if sec("AGOLFCARS_FB_PAGE_TOKEN")!=pt: sys.exit("Keychain write failed; previous token kept in _PREV.")
subprocess.run(["pbcopy"],input=b"")
print("OK: new Page token saved, clipboard cleared.")
