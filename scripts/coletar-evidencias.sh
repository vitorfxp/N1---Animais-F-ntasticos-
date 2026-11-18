#!/usr/bin/env bash
# Coleta as evidências da N1 a partir do servidor definido no .env.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
OUT="${1:-evidencias}"
mkdir -p "$OUT"
SSH=(ssh -i "${SERVER_SSH_KEY/#\~/$HOME}" "${SERVER_USER:-root}@${SERVER_IP}")

"${SSH[@]}" bash -s > "$OUT/http-https.txt" <<'REMOTE'
echo "# Apache — VirtualHosts"; apache2ctl -S 2>&1
echo; echo "# Certificados"; certbot certificates 2>/dev/null | grep -E "Certificate Name|Domains|Expiry"
echo; echo "# Endpoints (código HTTP)"
for u in https://animaisfantasticos.infinitymais.com.br/ https://radarenchant.infinitymais.com.br/ \
         https://radarenchant.infinitymais.com.br/api/saude https://grafana.infinitymais.com.br/api/health \
         https://kuma.infinitymais.com.br/ http://animaisfantasticos.infinitymais.com.br/; do
  printf "%-62s %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' "$u")"
done
echo; echo "# Serviços internos"
for u in http://127.0.0.1:8090/ http://127.0.0.1:8091/ http://127.0.0.1:9300/api/saude \
         http://127.0.0.1:9090/-/healthy http://127.0.0.1:3100/ready http://127.0.0.1:3000/api/health; do
  printf "%-42s %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' "$u")"
done
echo; echo "# TLS do site"
echo | openssl s_client -connect animaisfantasticos.infinitymais.com.br:443 \
  -servername animaisfantasticos.infinitymais.com.br 2>/dev/null | openssl x509 -noout -subject -issuer -dates
REMOTE

"${SSH[@]}" bash -s > "$OUT/docker-stacks.txt" <<'REMOTE'
echo "# host"; hostname; . /etc/os-release; echo "$PRETTY_NAME"
echo; echo "# docker version"; docker version --format '{{.Server.Version}}'
echo; echo "# docker compose version"; docker compose version
echo; echo "# docker ps"; docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo; echo "# docker compose ls"; docker compose ls
echo; echo "# docker service ls"; docker service ls
REMOTE

sed -i "s/${SERVER_IP}/<SERVER_IP>/g" "$OUT"/*.txt
echo "evidências em $OUT/"
