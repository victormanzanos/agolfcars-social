#!/usr/bin/env python3
"""Art's Golf Cars — alta del token de PÁGINA de Facebook (una sola vez).

Convierte el token de usuario de corta duración del Explorador de la Graph API en un
token de PÁGINA permanente (los tokens de página derivados de un token de usuario de
larga duración NO caducan) y lo guarda en el Keychain para que daily_engine.py espeje
cada post de Instagram también en la Página de Facebook.

Lo ejecuta VICTOR en su terminal; los secretos se piden por entrada oculta y NUNCA se
escriben en disco ni pasan por el chat:

    python3 ~/agolfcars-social/fb_setup_token.py

Necesitas dos cosas del navegador (te las indico):
  1) El token de usuario del Explorador de la Graph API (icono de copiar junto al token).
  2) El secreto de la app "Art Golf Cars" (developers.facebook.com -> la app ->
     Configuracion de la aplicacion -> Basica -> "Mostrar" el "Secreto de la aplicacion").
"""
import getpass, json, subprocess, sys, urllib.parse, urllib.request

APP_ID  = "3456742731171661"          # app "Art Golf Cars" (publico, no secreto)
PAGE_ID = "1241311492399979"          # Pagina "Arts Golf Cars" (id de Graph, de /me/accounts)
SECRETS = "/Users/victor/Code/CyberSecurity/scripts/secrets.sh"
GRAPH   = "https://graph.facebook.com/v21.0"


def _get(url):
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def _set_secret(name, value):
    subprocess.run([SECRETS, "set", name, value], check=True)


def _clipboard():
    try:
        return subprocess.check_output(["pbpaste"]).decode().strip()
    except Exception:
        return ""


def main():
    print("== Alta del token de Pagina de Facebook para Art's Golf Cars ==\n")
    # El token de usuario ya lo copiaste del Explorador (Cmd+C): lo tomo del portapapeles.
    user_tok = _clipboard()
    if user_tok.startswith("EAA"):
        print(f"Token de usuario detectado en el portapapeles (len {len(user_tok)}). OK.")
    else:
        user_tok = getpass.getpass("1) Pega el TOKEN DE USUARIO del Explorador (no se vera): ").strip()
    app_sec = getpass.getpass("Pega el SECRETO de la app 'Art Golf Cars' (Mostrar en Ajustes; no se vera): ").strip()
    if not user_tok or not app_sec:
        sys.exit("Faltan datos. Aborto sin tocar nada.")

    # 1) Corta -> larga duracion (60 dias); el token de PAGINA que salga de aqui no caduca.
    q = urllib.parse.urlencode({
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": app_sec,
        "fb_exchange_token": user_tok,
    })
    try:
        ll = _get(f"{GRAPH}/oauth/access_token?{q}")
    except Exception as e:
        sys.exit(f"Error en el intercambio a larga duracion: {e}")
    ll_user = ll.get("access_token")
    if not ll_user:
        sys.exit(f"No se obtuvo token de larga duracion: {json.dumps(ll)[:300]}")

    # 2) Token de PAGINA permanente desde el token de usuario de larga duracion.
    acc = _get(f"{GRAPH}/me/accounts?" + urllib.parse.urlencode(
        {"fields": "name,id,access_token", "access_token": ll_user}))
    pages = acc.get("data", [])
    page = next((p for p in pages if p.get("id") == PAGE_ID), None)
    if not page:
        names = ", ".join(f"{p.get('name')}/{p.get('id')}" for p in pages) or "(ninguna)"
        sys.exit(f"La Pagina {PAGE_ID} no aparece entre las accesibles: {names}\n"
                 "Repite la autorizacion marcando la Pagina 'Arts Golf Cars'.")
    page_tok = page.get("access_token")
    if not page_tok:
        sys.exit("La Pagina no devolvio access_token (permiso pages_manage_posts ausente?).")

    # 3) Verifica que el token de pagina funciona (lee el nombre de la Pagina).
    chk = _get(f"{GRAPH}/{PAGE_ID}?" + urllib.parse.urlencode(
        {"fields": "name", "access_token": page_tok}))
    if chk.get("id") != PAGE_ID:
        sys.exit(f"El token de pagina no verifica: {json.dumps(chk)[:300]}")

    # 4) Guarda en el Keychain (unica copia; nunca en disco ni en el repo).
    _set_secret("AGOLFCARS_FB_PAGE_ID", PAGE_ID)
    _set_secret("AGOLFCARS_FB_PAGE_TOKEN", page_tok)
    _set_secret("AGOLFCARS_META_APP_ID", APP_ID)

    print(f"\n[OK] Pagina verificada: {chk.get('name')} ({PAGE_ID})")
    print("[OK] Guardado en Keychain: AGOLFCARS_FB_PAGE_ID, AGOLFCARS_FB_PAGE_TOKEN, AGOLFCARS_META_APP_ID")
    print("     El motor ya puede espejar Instagram -> Facebook. (Este token de pagina no caduca.)")


if __name__ == "__main__":
    main()
