#!/bin/bash
# Sobe/atualiza a stack de monitoramento e liga o Grafana do host a ela.
# Uso: bash /root/projeto/monitoring/deploy.sh
set -euo pipefail
cd "$(dirname "$0")"
BASE="$(pwd)"

mkdir -p textfile
chmod +x scripts/docker-state.sh
bash scripts/docker-state.sh

# Cron: estado dos containers a cada minuto
echo "* * * * * root $BASE/scripts/docker-state.sh >/dev/null 2>&1" > /etc/cron.d/monitoring-docker-state
chmod 644 /etc/cron.d/monitoring-docker-state

docker compose up -d

# Provisionamento do Grafana (datasource + dashboards).
# Os JSON ficam versionados aqui e são copiados para uma pasta que o usuário grafana consegue ler.
install -m 644 grafana/provisioning/datasources/prometheus.yaml /etc/grafana/provisioning/datasources/prometheus.yaml
install -m 644 grafana/provisioning/dashboards/projeto.yaml /etc/grafana/provisioning/dashboards/projeto.yaml
install -d -o grafana -g grafana -m 755 /var/lib/grafana/dashboards/projeto
rm -f /var/lib/grafana/dashboards/projeto/*.json
install -o grafana -g grafana -m 644 grafana/dashboards/*.json /var/lib/grafana/dashboards/projeto/
systemctl restart grafana-server

# Recarrega config do Prometheus caso já estivesse rodando
sleep 5
curl -s -X POST http://127.0.0.1:9090/-/reload || true
echo "OK"
