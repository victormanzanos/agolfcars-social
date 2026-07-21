#!/usr/bin/env bash
# Wrapper para LaunchAgent — refresca el long-lived token de IG (@artsgolfcars).
set -euo pipefail
cd "$(dirname "$0")"
/usr/bin/env python3 refresh_token.py
