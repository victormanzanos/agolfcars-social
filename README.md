# Art's Golf Cars — Instagram engine (@agolfcars)

Motor de publicación automática en Instagram para Art's Golf Cars
(concesionario de carritos de golf en Dundee, FL — nuevos, usados, servicio,
partes y accesorios, financiación, envío nacional). Clonado del motor probado
de @manzanoshabitat / @manzanosmobility.

## Piezas

| Fichero | Qué hace |
|---|---|
| `daily_engine.py` | Publica 1 post + 1 story cada 2 días (ordinal%2==0) vía Instagram Graph API. Idempotente (estado en `.daily_state.json` + check server-side del último caption). `DRY=1` para previsualizar. |
| `make_agolfcars.py` | Convierte imágenes de `raw/` en tarjetas de marca: post 1080x1350 / story 1080x1920, marco doble dorado #C8A96E, logo Art's Golf Cars abajo. |
| `CAPTIONS.md` | Fuente única de posts/stories (captions en INGLÉS). El motor lo re-parsea en cada ejecución. |
| `assets/build_logo.py` | Regenera `assets/logo-agc-gold.png` (badge "A" + wordmark dorado) desde `brand-a-badge.png` de la web. |
| `refresh_token.py` | Renueva el long-lived IG token (~60 días) cada domingo. |
| `com.agolfcars.dailyig.plist` | LaunchAgent del motor (13:41/15:53/18:11/19:47 Madrid = mañana/mediodía Florida). |
| `com.agolfcars.igtokenrefresh.plist` | LaunchAgent del refresh de token (domingo 11:29). |
| `reales/` | Drop folder: fotos reales del concesionario que se intercalan 1 de cada 3 posts (caption opcional en `<nombre>.txt`). |

Las imágenes se publican vía raw URLs del repo público
`github.com/victormanzanos/agolfcars-social` (Instagram Graph API exige
URLs públicas).

## ✅ Activado el 2026-07-21

- Credenciales en Keychain: `AGOLFCARS_IG_ACCESS_TOKEN` (long-lived) +
  `AGOLFCARS_IG_ACCOUNT_ID` = 17841447520259580. Verificado `/me` →
  username **agolfcars** ("A Golf Cars"), tipo BUSINESS.
- ⚠️ El handle real de la cuenta es **@agolfcars** (la web enlaza a
  instagram.com/artsgolfcars — no coincide). El hashtag de marca sigue
  siendo #ArtsGolfCars.
- LaunchAgents cargados (`launchctl list | grep agolfcars`).
- Siembra inicial publicada con `seed_publish.py` (una sola vez): tarjeta de
  logo + 6 posts de bienvenida + 7 stories, y `.daily_state.json` sincronizado
  para que la rotación continúe a los 2 días.
- Pendiente manual: FOTO DE PERFIL (la API no permite ponerla) — subir
  `assets/logo-agc-gold.png` o el badge desde la app de Instagram.
- El token se renueva solo (domingos 11:29). Si caduca: regenerar en la Meta
  app y `secrets.sh set AGOLFCARS_IG_ACCESS_TOKEN '<token>'`.

## Contenido nuevo

La tarea programada `agolfcars-ig-content-refresh` (semanal) convierte
las portadas nuevas del blog (`/Users/victor/Code/golf-dealer-platform/agolfcars-website/blog/img/`)
en tarjetas y las añade a `CAPTIONS.md`, para que el feed no se repita.
El blog diario de agolfcars.com genera una portada nueva cada día.

## Reglas de contenido (Constitución Art. I)

- Solo datos reales de agolfcars.com: 3× Club Car Black & Gold Elite Dealer;
  29630 US Hwy 27, Dundee, FL 33838; (863) 439-5431; nuevos y usados; Service
  Center; Parts & Accessories; financiación Sheffield Financial; envío nacional.
- NUNCA inventar precios, modelos, promociones ni disponibilidad.
- OJO marcas: no listar marcas no verificadas (conflicto de lista de marcas
  pendiente de resolver con Laura — Club Car siempre es segura).
- Captions en inglés. Hashtag de marca #ArtsGolfCars siempre.
