#!/usr/bin/env python3
"""Art's Golf Cars — refresh diario del long-lived Instagram access token (~60 dias).
Endpoint: GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token
LaunchAgent com.agolfcars.igtokenrefresh, 11:29 cada dia.

Cambios 16-sep-2026 (tras la invalidacion del token por Meta):
- Un rechazo de Meta (HTTPError, p.ej. codigo 190) antes REVENTABA sin escribir en
  token-refresh.log, asi que el fallo solo existia en el stderr de launchd. Ahora se
  registra como FALLO con el mensaje de Meta.
- Antes solo renovaba el Keychain y las copias del VPS (ig.json, ig-accounts.json) se
  quedaban con un token viejo que caducaba solo a los 60 dias. Ahora se sincronizan.
- El token viaja por stdin, no por argv (no aparece en la lista de procesos).
"""
import datetime, json, os, subprocess, sys, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import install_new_token as T   # store_keychain / sync_server / verify_server

LOG = os.path.expanduser("~/agolfcars-social/token-refresh.log")


def log(msg):
    line = f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def main():
    tok = T.sh([T.SECRETS, "get", "AGOLFCARS_IG_ACCESS_TOKEN"]).stdout.strip()
    params = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": tok})
    try:
        with urllib.request.urlopen(f"https://graph.instagram.com/refresh_access_token?{params}", timeout=30) as r:
            body = json.load(r)
    except urllib.error.HTTPError as e:
        log("FALLO · Meta rechaza el token (hay que generar uno nuevo y ejecutar "
            "install_new_token.py) · " + e.read().decode()[:300])
        sys.exit(1)
    except Exception as e:
        log(f"FALLO · red/timeout · {e}")
        sys.exit(1)
    new, exp = body.get("access_token"), body.get("expires_in")
    if not new:
        log("FALLO · " + json.dumps(body)[:300])
        sys.exit(1)
    try:
        T.store_keychain(new)
        T.sync_server(new)          # sufijo fijo .bak-token-last: no acumula copias diarias
        T.verify_server()
    except SystemExit:
        log("FALLO · token renovado en Meta pero no se pudo guardar o sincronizar (ver stdout de launchd)")
        raise
    log(f"OK · nuevo token · expira en {exp}s (~{int(exp)//86400} dias) · Keychain + VPS sincronizados")


if __name__ == "__main__":
    main()
