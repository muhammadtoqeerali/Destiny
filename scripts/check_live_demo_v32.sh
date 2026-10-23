#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-https://destiny-amber-phi.vercel.app}"
[[ "$BASE" =~ ^https://[A-Za-z0-9.-]+$ ]] || { echo 'ERROR: Supply an HTTPS origin, without path/query'; exit 1; }
for path in /doctor /admin/login; do
  printf '%s: ' "$path"
  response="$(curl --connect-timeout 10 --max-time 25 -sS -L -o /dev/null -w '%{http_code} %{url_effective}' "$BASE$path")"
  printf '%s\n' "$response"
  [[ "$response" == '200 '* ]] || { echo 'ERROR: Production route not healthy'; exit 1; }
done
printf 'INFO: Admin interaction and deployment SHA must still be verified manually using a browser/Vercel.\n'
printf 'INFO: This HTTP-only health check does not prove authentication, chart interaction or version identity.\n'
