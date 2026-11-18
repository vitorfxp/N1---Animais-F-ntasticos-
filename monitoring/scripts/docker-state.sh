#!/bin/bash
# Exporta o estado dos containers (inclusive PARADOS) para o node-exporter (textfile collector).
# Roda pelo cron a cada minuto. cAdvisor só enxerga containers rodando; este script cobre os parados.
set -u
DIR="$(cd "$(dirname "$0")/.." && pwd)/textfile"
OUT="$DIR/docker.prom"
TMP="$OUT.$$"
mkdir -p "$DIR"

esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

gen() {
  echo "# HELP docker_daemon_up Docker respondendo (1) ou não (0)"
  echo "# TYPE docker_daemon_up gauge"
  if ! timeout 20 docker info >/dev/null 2>&1; then
    echo "docker_daemon_up 0"
    return 0
  fi
  echo "docker_daemon_up 1"

  echo "# HELP docker_container_running Container de compose rodando (1) ou parado (0)"
  echo "# TYPE docker_container_running gauge"
  echo "# HELP docker_container_restarts Total de restarts do container"
  echo "# TYPE docker_container_restarts counter"
  echo "# HELP docker_container_healthy Healthcheck: 1 saudável, 0 unhealthy, -1 sem healthcheck/iniciando"
  echo "# TYPE docker_container_healthy gauge"
  echo "# HELP docker_container_exit_code Último exit code do container"
  echo "# TYPE docker_container_exit_code gauge"
  # Só containers de docker compose (ignora containers avulsos/antigos de "docker run")
  for id in $(docker ps -aq --filter label=com.docker.compose.project); do
    docker inspect --format '{{.Name}}|{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{.State.Running}}|{{.RestartCount}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.State.ExitCode}}|{{.State.Status}}' "$id"
  done | while IFS='|' read -r name project service running restarts health exitcode status; do
    name="${name#/}"
    [ "$project" = "monitoring" ] && continue
    # sem o label "status" para a série não mudar de identidade quando o container para
    l="name=\"$(esc "$name")\",project=\"$(esc "$project")\",service=\"$(esc "$service")\""
    [ "$running" = "true" ] && r=1 || r=0
    case "$health" in healthy) h=1 ;; unhealthy) h=0 ;; *) h=-1 ;; esac
    echo "docker_container_running{$l} $r"
    echo "docker_container_restarts{$l} $restarts"
    echo "docker_container_healthy{$l} $h"
    echo "docker_container_exit_code{$l} $exitcode"
  done

  if [ "$(docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null)" = "active" ]; then
    echo "# HELP docker_swarm_service_replicas_running Réplicas rodando do serviço swarm"
    echo "# TYPE docker_swarm_service_replicas_running gauge"
    echo "# HELP docker_swarm_service_replicas_desired Réplicas desejadas do serviço swarm"
    echo "# TYPE docker_swarm_service_replicas_desired gauge"
    docker service ls --format '{{.Name}}|{{.Replicas}}' | while IFS='|' read -r svc rep; do
      rep="${rep%% *}"; run="${rep%/*}"; des="${rep#*/}"
      echo "docker_swarm_service_replicas_running{service=\"$(esc "$svc")\"} ${run:-0}"
      echo "docker_swarm_service_replicas_desired{service=\"$(esc "$svc")\"} ${des:-0}"
    done
  fi

}

{
  gen
  echo "# HELP docker_state_last_run_timestamp Última execução deste script"
  echo "# TYPE docker_state_last_run_timestamp gauge"
  echo "docker_state_last_run_timestamp $(date +%s)"
} > "$TMP" && mv "$TMP" "$OUT"
chmod 644 "$OUT"
