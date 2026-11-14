#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

CA_FILE="caddy-root.crt"
docker compose exec -T caddy cat /data/caddy/pki/authorities/local/root.crt > "$CA_FILE"
chmod 0644 "$CA_FILE"

echo "Caddy-Root-CA exportiert: $CA_FILE"
echo
echo "Systemweit für curl/wget (empfohlen, benötigt sudo):"
echo "  sudo install -m 0644 $CA_FILE /usr/local/share/ca-certificates/club-zweisam-caddy.crt"
echo "  sudo update-ca-certificates"
echo

if [ "${1:-}" = "--system" ]; then
  sudo install -m 0644 "$CA_FILE" /usr/local/share/ca-certificates/club-zweisam-caddy.crt
  sudo update-ca-certificates
  echo "System-CA-Store aktualisiert."
fi

if command -v certutil >/dev/null 2>&1; then
  mkdir -p "$HOME/.pki/nssdb"
  certutil -d "sql:$HOME/.pki/nssdb" -A -t "C,," -n "Caddy Local Authority" -i "$CA_FILE" 2>/dev/null || true
  echo "Chrome/Chromium-NSS-Store: CA importiert (Chrome neu starten)."

  for base in "$HOME/.mozilla/firefox" "$HOME/snap/firefox/common/.mozilla/firefox"; do
    [ -d "$base" ] || continue
    find "$base" -maxdepth 2 -type d -name '*.default*' 2>/dev/null | while IFS= read -r profile; do
      certutil -d "sql:$profile" -A -t "C,," -n "Caddy Local Authority" -i "$CA_FILE" 2>/dev/null || true
      echo "Firefox-Profil importiert: $profile"
    done
  done
else
  echo "certutil fehlt (libnss3-tools). Alternativ die CA in den Browsern per UI importieren:"
  echo "  Firefox: Einstellungen -> Datenschutz & Sicherheit -> Zertifikate ->"
  echo "           Zertifikate anzeigen -> Zertifizierungsstellen -> Importieren"
  echo "  Chrome:  Einstellungen -> Datenschutz und Sicherheit -> Sicherheit ->"
  echo "           Zertifikate verwalten -> Zertifizierungsstellen -> Importieren"
  echo "  CLI-Import: sudo apt install libnss3-tools  (danach dieses Skript erneut ausführen)"
fi

echo
echo "Prüfen:"
echo "  curl -I https://club-zweisam.localhost/"
echo "  wget --spider https://club-zweisam.localhost/"
echo "  Ohne Systeminstallation: curl --cacert $CA_FILE https://club-zweisam.localhost/"
