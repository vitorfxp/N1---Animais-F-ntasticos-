#!/bin/bash
# Baixa/atualiza o banco GeoIP gratuito "DB-IP City Lite" (formato MMDB, sem cadastro).
# Licença CC BY 4.0 -> atribuição "IP Geolocation by DB-IP" (https://db-ip.com) no site e nos dashboards.
# Roda pelo cron todo dia 3 do mês.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)/geoip"
mkdir -p "$DIR"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
for m in "$(date +%Y-%m)" "$(date -d "$(date +%Y-%m-15) -1 month" +%Y-%m)"; do
  if curl -fsSL -o "$TMP/db.mmdb.gz" "https://download.db-ip.com/free/dbip-city-lite-$m.mmdb.gz"; then
    gunzip -f "$TMP/db.mmdb.gz"
    # sanidade: arquivo MMDB válido termina com o marcador de metadados
    if [ "$(stat -c %s "$TMP/db.mmdb")" -gt 50000000 ] && grep -aq "MaxMind.com" "$TMP/db.mmdb"; then
      install -m 644 "$TMP/db.mmdb" "$DIR/dbip-city-lite.mmdb"
      echo "GeoIP atualizado: dbip-city-lite-$m"
      # promtail lê o banco só na partida
      docker restart mon-promtail >/dev/null 2>&1 || true
      exit 0
    fi
  fi
done
echo "Falha ao baixar o GeoIP" >&2
exit 1
