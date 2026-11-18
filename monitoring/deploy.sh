#!/bin/bash
# Sobe/atualiza a stack de observabilidade e liga o Grafana do host a ela.
# Uso: bash /root/projeto/monitoring/deploy.sh
set -euo pipefail
cd "$(dirname "$0")"
BASE="$(pwd)"
ENV_FILE="$BASE/../.env"
set -a; . "$ENV_FILE"; set +a

mkdir -p textfile geoip
chmod +x scripts/*.sh
bash scripts/docker-state.sh

# GeoIP (DB-IP City Lite) - baixa na primeira vez
[ -s geoip/dbip-city-lite.mmdb ] || bash scripts/update-geoip.sh

# Crons: estado dos containers (1/min) e GeoIP (todo dia 3)
echo "* * * * * root $BASE/scripts/docker-state.sh >/dev/null 2>&1" > /etc/cron.d/monitoring-docker-state
echo "17 4 3 * * root $BASE/scripts/update-geoip.sh >/dev/null 2>&1" > /etc/cron.d/monitoring-geoip
chmod 644 /etc/cron.d/monitoring-docker-state /etc/cron.d/monitoring-geoip

# Prometheus não expande variáveis: renderiza o arquivo a partir do .env.
envsubst < prometheus/prometheus.yml.tmpl > prometheus/prometheus.yml

docker compose --env-file "$ENV_FILE" up -d --remove-orphans

# ---------------- Grafana (instalado no host via apt)
# Configuração como código, igual à base do Tamoai-Infra (variáveis GF_*).
install -d /etc/systemd/system/grafana-server.service.d
install -m 600 grafana/grafana.env /etc/grafana/projeto.env
cat > /etc/systemd/system/grafana-server.service.d/projeto.conf <<'EOF'
[Service]
EnvironmentFile=/etc/grafana/projeto.env
EOF
systemctl daemon-reload

# Provisionamento: datasources + dashboards. Os JSON ficam versionados aqui e são copiados
# para uma pasta que o usuário grafana consegue ler (ele não tem acesso a /root).
install -m 644 grafana/provisioning/datasources/*.yaml /etc/grafana/provisioning/datasources/
install -m 644 grafana/provisioning/dashboards/projeto.yaml /etc/grafana/provisioning/dashboards/projeto.yaml
install -d -o grafana -g grafana -m 755 /var/lib/grafana/dashboards/projeto
rm -f /var/lib/grafana/dashboards/projeto/*.json
install -o grafana -g grafana -m 644 grafana/dashboards/*.json /var/lib/grafana/dashboards/projeto/
install -m 644 grafana/assets/* /usr/share/grafana/public/img/   # imagens usadas nos paineis HTML
systemctl restart grafana-server

# Recarrega config do Prometheus caso já estivesse rodando
sleep 5
curl -s -X POST http://127.0.0.1:9090/-/reload || true
echo "OK"
