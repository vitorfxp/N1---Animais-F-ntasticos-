#!/usr/bin/env bash
# Inventário dinâmico: lê os endereços do .env na raiz do repositório.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${ENV_FILE:-$DIR/../.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "faltando $ENV_FILE (copie de .env.example)" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

: "${SERVER_IP:?defina SERVER_IP no .env}"

cat <<JSON
{
  "_meta": {
    "hostvars": {
      "manager1": {
        "ansible_host": "${SERVER_IP}",
        "ansible_user": "${SERVER_USER:-root}",
        "ansible_ssh_private_key_file": "${SERVER_SSH_KEY:-~/.ssh/id_ed25519}",
        "ansible_python_interpreter": "/usr/bin/python3"
      }
    }
  },
  "web": {
    "hosts": ["manager1"]
  }
}
JSON
