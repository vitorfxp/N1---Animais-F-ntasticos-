#!/bin/bash
# Troca a senha do usuário admin do Grafana (a senha não aparece na tela nem fica no histórico).
# Uso: bash /root/projeto/monitoring/scripts/trocar-senha-grafana.sh
set -euo pipefail
read -rsp "Nova senha do admin do Grafana: " P1; echo
read -rsp "Repita a senha: " P2; echo
if [ "$P1" != "$P2" ] || [ ${#P1} -lt 12 ]; then
  echo "Senhas diferentes ou com menos de 12 caracteres. Nada foi alterado." >&2
  exit 1
fi
grafana cli --homepath /usr/share/grafana --config /etc/grafana/grafana.ini \
  admin reset-admin-password "$P1" >/dev/null 2>&1 \
  && echo "SENHA-GRAFANA-OK" || { echo "Falhou ao trocar a senha." >&2; exit 1; }
