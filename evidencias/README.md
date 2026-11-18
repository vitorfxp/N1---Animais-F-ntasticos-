# Evidências da N1

Coletadas em **18/11/2026** no servidor `manager1` (Debian 12, Hetzner).
IP público, chaves e senhas foram substituídos por placeholders antes de versionar.

| Arquivo | O que prova |
| --- | --- |
| `ansible-version.txt` | versão do Ansible e inventário resolvido a partir do `.env` |
| `ansible-run.txt` | execução completa do `playbook.yml` (tarefas e `PLAY RECAP`) |
| `ansible-idempotencia.txt` | segunda execução com `changed=0` |
| `docker-stacks.txt` | `docker ps`, `docker compose ls`, `docker service ls`, versões |
| `http-https.txt` | VirtualHosts do Apache, certificados, endpoints HTTP/HTTPS e TLS |
| `img/site.png` | tela do site publicado em HTTPS |
| `img/radar.png` | tela do radar de tráfego |
| `img/grafana.png` | Grafana no ar (tela de login) |

> O Uptime Kuma é uma SPA que não renderiza em navegador headless; a evidência dele é o
> `http-https.txt` (HTTP 200) e o `docker-stacks.txt` (serviço `1/1`).

## Como reproduzir

```bash
cd ansible
ansible-playbook playbook.yml | tee ../evidencias/ansible-run.txt

ssh root@<SERVER_IP> 'docker ps -a; docker compose ls; docker service ls' \
  > ../evidencias/docker-stacks.txt

bash ../scripts/coletar-evidencias.sh   # opcional: gera http-https.txt
```

## Observações

- O site e o radar escutam apenas em `127.0.0.1`; quem publica é o Apache do host.
- O certificado de `manager01hetzner` está expirado (renovar antes da banca).
- O Traefik está em `0/0` réplicas; o TLS é do Apache.
