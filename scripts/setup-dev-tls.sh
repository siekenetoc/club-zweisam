#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

CA_FILE="caddy-root.crt"
NICKNAME="Caddy Local Authority"
MODE_INSTALL_SYSTEM=0
MODE_INSTALL_DEPS=0

usage() {
  cat <<'EOF'
Usage: scripts/setup-dev-tls.sh [OPTION]

Ohne Option: exportiert caddy-root.crt und zeigt die manuellen Schritte.
  --system        CA systemweit installieren (curl/wget, sudo nötig)
  --install-deps  libnss3-tools (certutil) per apt installieren (sudo nötig)
  --all           beides: Abhängigkeiten + systemweite CA + Browser-NSS
EOF
}

for arg in "$@"; do
  case "$arg" in
    --system) MODE_INSTALL_SYSTEM=1 ;;
    --install-deps) MODE_INSTALL_DEPS=1 ;;
    --all) MODE_INSTALL_SYSTEM=1; MODE_INSTALL_DEPS=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unbekannte Option: $arg" >&2; usage; exit 1 ;;
  esac
done

docker compose exec -T caddy cat /data/caddy/pki/authorities/local/root.crt > "$CA_FILE"
chmod 0644 "$CA_FILE"
echo "Caddy-Root-CA exportiert: $CA_FILE"
echo

if [ "$MODE_INSTALL_DEPS" = 1 ]; then
  echo "Installiere libnss3-tools (enthält certutil)..."
  sudo apt-get update
  sudo apt-get install -y libnss3-tools
fi

if [ "$MODE_INSTALL_SYSTEM" = 1 ]; then
  echo "Installiere CA systemweit (curl, wget, OpenSSL)..."
  sudo install -m 0644 "$CA_FILE" /usr/local/share/ca-certificates/club-zweisam-caddy.crt
  sudo update-ca-certificates
  echo "System-CA-Store aktualisiert."
else
  echo "Systemweit für curl/wget (sudo nötig):"
  echo "  sudo install -m 0644 $CA_FILE /usr/local/share/ca-certificates/club-zweisam-caddy.crt"
  echo "  sudo update-ca-certificates"
fi
echo

import_nss_db() {
  local db_path="$1"
  local label="$2"
  if certutil -d "sql:$db_path" -L -n "$NICKNAME" >/dev/null 2>&1; then
    echo "  vorhanden: $label"
    return 0
  fi
  if certutil -d "sql:$db_path" -A -t "C,," -n "$NICKNAME" -i "$CA_FILE" >/dev/null 2>&1; then
    echo "  importiert: $label"
    return 0
  fi
  echo "  FEHLER: Import fehlgeschlagen für $label (Browser geschlossen?)" >&2
  return 1
}

if command -v certutil >/dev/null 2>&1; then
  if pgrep -x firefox >/dev/null 2>&1 || pgrep -x chrome >/dev/null 2>&1; then
    echo "Hinweis: Firefox/Chrome laufen. Für den NSS-Import bitte vorher beenden."
  fi

  mkdir -p "$HOME/.pki/nssdb"
  import_nss_db "$HOME/.pki/nssdb" "Chrome/Chromium" || true

  for base in "$HOME/.mozilla/firefox" "$HOME/snap/firefox/common/.mozilla/firefox"; do
    [ -d "$base" ] || continue
    find "$base" -maxdepth 2 -type d -name '*.default*' 2>/dev/null | while IFS= read -r profile; do
      import_nss_db "$profile" "Firefox: $profile" || true
    done
  done
  echo "Browser danach vollständig neu starten."
else
  echo "certutil fehlt (Paket: libnss3-tools, nicht 'certutil')."
  echo "Installieren mit:"
  echo "  sudo apt-get install libnss3-tools"
  echo "Oder die CA in den Browsern per UI importieren:"
  echo "  Firefox: Einstellungen -> Datenschutz & Sicherheit -> Zertifikate ->"
  echo "           Zertifikate anzeigen -> Zertifizierungsstellen -> Importieren"
  echo "  Chrome:  Einstellungen -> Datenschutz und Sicherheit -> Sicherheit ->"
  echo "           Zertifikate verwalten -> Zertifizierungsstellen -> Importieren"
fi

echo
if [ "$MODE_INSTALL_SYSTEM" = 1 ]; then
  echo "Prüfe Systemvertrauen:"
  if curl -sS -o /dev/null -w "  curl: HTTP %{http_code}\n" https://club-zweisam.localhost/; then
    echo "  curl vertraut der CA."
  else
    echo "  curl-Fehler: CA noch nicht im Systemstore oder Proxy dazwischen." >&2
  fi
else
  echo "Prüfen:"
  echo "  curl -I https://club-zweisam.localhost/"
  echo "  wget --spider https://club-zweisam.localhost/"
  echo "  Ohne Systeminstallation: curl --cacert $CA_FILE https://club-zweisam.localhost/"
fi
