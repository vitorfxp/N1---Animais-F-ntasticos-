"""Gera os dashboards do Grafana (JSON) em ./dashboards.
Uso: python3 gen_dashboards.py
"""
import json
import os

DS = {"type": "prometheus", "uid": "prometheus"}
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboards")

# paleta do Radar (igual ao site e aos dashboards da base)
GREEN, ORANGE, RED, BLUE = "#1F9D55", "#F5A623", "#E5303B", "#3E63DD"


class Layout:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.row_h = 0
        self.next_id = 1

    def pos(self, w, h):
        if self.x + w > 24:
            self.x = 0
            self.y += self.row_h
            self.row_h = 0
        g = {"x": self.x, "y": self.y, "w": w, "h": h}
        self.x += w
        self.row_h = max(self.row_h, h)
        return g

    def newline(self):
        if self.x:
            self.x = 0
            self.y += self.row_h
            self.row_h = 0

    def pid(self):
        self.next_id += 1
        return self.next_id


def tgt(expr, legend="", ref="A", instant=False, fmt="time_series"):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": ref}
    if instant:
        t.update({"instant": True, "range": False, "format": fmt})
    else:
        t.update({"range": True, "format": fmt})
    return t


def thresholds(*steps):
    """steps: (value_or_None, color)"""
    return {"mode": "absolute", "steps": [{"value": v, "color": c} for v, c in steps]}


def vmap(pairs):
    """pairs: {valor: (texto, cor)}"""
    return [{"type": "value", "options": {str(k): {"text": t, "color": c, "index": i}
                                           for i, (k, (t, c)) in enumerate(pairs.items())}}]


UPDOWN = vmap({1: ("NO AR", GREEN), 0: ("FORA", RED)})
RUNSTOP = vmap({1: ("RODANDO", GREEN), 0: ("PARADO", RED)})
ACTIVE = vmap({1: ("ATIVO", GREEN), 0: ("FALHOU / PARADO", RED)})
YESNO = vmap({1: ("SIM", GREEN), 0: ("NÃO", RED)})


def row(L, title):
    L.newline()
    p = {"type": "row", "title": title, "collapsed": False, "id": L.pid(),
         "gridPos": L.pos(24, 1), "panels": []}
    L.newline()
    return p


def stat(L, title, targets, w=4, h=4, unit="none", th=None, mappings=None, color_mode="background",
         text_mode="auto", decimals=None, desc="", graph=False, orientation="auto", calc="lastNotNull"):
    p = {
        "type": "stat", "title": title, "id": L.pid(), "datasource": DS, "description": desc,
        "gridPos": L.pos(w, h), "targets": targets,
        "fieldConfig": {"defaults": {"unit": unit, "mappings": mappings or [],
                                     "thresholds": th or thresholds((None, GREEN)),
                                     "color": {"mode": "thresholds"}}, "overrides": []},
        "options": {"reduceOptions": {"calcs": [calc], "fields": "", "values": False},
                    "colorMode": color_mode, "graphMode": "area" if graph else "none",
                    "textMode": text_mode, "justifyMode": "center", "orientation": orientation,
                    "wideLayout": True, "showPercentChange": False},
    }
    if decimals is not None:
        p["fieldConfig"]["defaults"]["decimals"] = decimals
    return p


def ts(L, title, targets, w=12, h=8, unit="none", stack=False, desc="", th=None, maxv=None, minv=None,
       fill=10, legend_calcs=("lastNotNull", "max")):
    d = {"unit": unit, "color": {"mode": "palette-classic"},
         "custom": {"drawStyle": "line", "lineWidth": 1, "fillOpacity": fill, "showPoints": "never",
                    "spanNulls": False, "stacking": {"mode": "normal" if stack else "none", "group": "A"},
                    "thresholdsStyle": {"mode": "line+area" if th else "off"}},
         "thresholds": th or thresholds((None, GREEN))}
    if maxv is not None:
        d["max"] = maxv
    if minv is not None:
        d["min"] = minv
    return {
        "type": "timeseries", "title": title, "id": L.pid(), "datasource": DS, "description": desc,
        "gridPos": L.pos(w, h), "targets": targets,
        "fieldConfig": {"defaults": d, "overrides": []},
        "options": {"legend": {"displayMode": "table", "placement": "right", "showLegend": True,
                               "calcs": list(legend_calcs)},
                    "tooltip": {"mode": "multi", "sort": "desc"}},
    }


def timeline(L, title, targets, mappings, w=24, h=8, desc=""):
    return {
        "type": "state-timeline", "title": title, "id": L.pid(), "datasource": DS, "description": desc,
        "gridPos": L.pos(w, h), "targets": targets,
        "fieldConfig": {"defaults": {"mappings": mappings, "color": {"mode": "thresholds"},
                                     "thresholds": thresholds((None, RED), (1, GREEN)),
                                     "custom": {"fillOpacity": 80, "lineWidth": 0}}, "overrides": []},
        "options": {"mergeValues": True, "showValue": "never", "alignValue": "left", "rowHeight": 0.85,
                    "legend": {"showLegend": False}, "tooltip": {"mode": "single"}},
    }


def table(L, title, targets, rename, hide=(), w=24, h=8, overrides=None, desc="", sort=None):
    excl = {k: True for k in ("Time", "__name__", "job", "instance") + tuple(hide)}
    tr = [{"id": "merge", "options": {}},
          {"id": "organize", "options": {"excludeByName": excl, "renameByName": rename}}]
    if sort:
        tr.append({"id": "sortBy", "options": {"sort": [{"field": sort[0], "desc": sort[1]}]}})
    return {
        "type": "table", "title": title, "id": L.pid(), "datasource": DS, "description": desc,
        "gridPos": L.pos(w, h), "targets": targets, "transformations": tr,
        "fieldConfig": {"defaults": {"custom": {"align": "auto", "cellOptions": {"type": "auto"}}},
                        "overrides": overrides or []},
        "options": {"showHeader": True, "cellHeight": "sm"},
    }


def col_override(name, unit=None, mappings=None, th=None, cell="color-background", decimals=None):
    props = [{"id": "custom.cellOptions", "value": {"type": cell, "mode": "basic"}}]
    if unit:
        props.append({"id": "unit", "value": unit})
    if mappings:
        props.append({"id": "mappings", "value": mappings})
    if th:
        props.append({"id": "thresholds", "value": th})
        props.append({"id": "color", "value": {"mode": "thresholds"}})
    if decimals is not None:
        props.append({"id": "decimals", "value": decimals})
    return {"matcher": {"id": "byName", "options": name}, "properties": props}


def dashboard(uid, title, panels, tags, refresh="30s", time_from="now-6h", desc=""):
    return {
        "uid": uid, "title": "Radar | " + title, "description": desc, "tags": ["radar", "monitoramento"] + tags,
        "timezone": "browser", "schemaVersion": 39, "version": 1, "editable": True,
        "refresh": refresh, "time": {"from": time_from, "to": "now"},
        "graphTooltip": 1, "panels": panels, "templating": {"list": []}, "annotations": {"list": []},
        "links": [{"type": "dashboards", "tags": ["radar"], "asDropdown": True,
                   "title": "Radar", "includeVars": False, "keepTime": True},
                  {"type": "link", "title": "Site ao vivo", "url": "https://radarenchant.infinitymais.com.br",
                   "targetBlank": True, "icon": "external link", "tags": []}],
    }


# ---------------------------------------------------------------- 1. Aplicações
def apps():
    L = Layout()
    P = [row(L, "Situação agora")]
    P.append(stat(L, "Aplicações FORA do ar", [tgt("count(probe_success == 0) or vector(0)")], w=6,
                  th=thresholds((None, GREEN), (1, RED)),
                  desc="Quantos endpoints (HTTP/TCP) estão falhando na checagem do blackbox exporter."))
    P.append(stat(L, "Aplicações no ar", [tgt("count(probe_success == 1) or vector(0)")], w=6,
                  th=thresholds((None, BLUE))))
    P.append(stat(L, "Disponibilidade média (24h)",
                  [tgt("avg(avg_over_time(probe_success[24h]))")], w=6, unit="percentunit", decimals=2,
                  th=thresholds((None, RED), (0.99, ORANGE), (0.999, GREEN))))
    P.append(stat(L, "Certificado SSL que vence primeiro",
                  [tgt("min((probe_ssl_earliest_cert_expiry - time()) / 86400)")], w=6, unit="d", decimals=0,
                  th=thresholds((None, RED), (7, ORANGE), (21, GREEN)),
                  desc="Dias até expirar o certificado HTTPS mais próximo do vencimento."))
    P.append(stat(L, "Status por aplicação", [tgt("probe_success", "{{app}}")], w=24, h=5,
                  mappings=UPDOWN, th=thresholds((None, RED), (1, GREEN)), text_mode="value_and_name"))
    P.append(row(L, "Histórico"))
    P.append(timeline(L, "Linha do tempo de disponibilidade (vermelho = fora do ar)",
                      [tgt("probe_success", "{{app}}")], UPDOWN, h=9))
    P.append(ts(L, "Tempo de resposta", [tgt("probe_duration_seconds", "{{app}}")], unit="s",
                th=thresholds((None, GREEN), (2, ORANGE), (5, RED))))
    P.append(ts(L, "Código HTTP retornado", [tgt('probe_http_status_code{job="probe_http"}', "{{app}}")],
                desc="0 = sem resposta (timeout, conexão recusada, erro de DNS/TLS).", fill=0))
    P.append(row(L, "Resumo"))
    P.append(table(L, "Disponibilidade por aplicação", [
        tgt("probe_success", "", "A", True, "table"),
        tgt("avg_over_time(probe_success[1h])", "", "B", True, "table"),
        tgt("avg_over_time(probe_success[24h])", "", "C", True, "table"),
        tgt("avg_over_time(probe_success[7d])", "", "D", True, "table"),
        tgt("probe_duration_seconds", "", "E", True, "table"),
        tgt('probe_http_status_code{job="probe_http"}', "", "F", True, "table"),
    ], rename={"app": "Aplicação", "Value #A": "Agora", "Value #B": "1h", "Value #C": "24h",
               "Value #D": "7 dias", "Value #E": "Resposta", "Value #F": "HTTP"},
        overrides=[
            col_override("Agora", mappings=UPDOWN, th=thresholds((None, RED), (1, GREEN))),
            *[col_override(c, unit="percentunit", decimals=2,
                           th=thresholds((None, RED), (0.99, ORANGE), (0.999, GREEN))) for c in ("1h", "24h", "7 dias")],
            col_override("Resposta", unit="s", cell="auto"),
            col_override("HTTP", cell="auto"),
        ], h=9, desc="Alvo checado = coluna instance (oculta)."))
    return dashboard("mon-apps", "1. Aplicações", P, ["aplicacoes"],
                     desc="Aplicação indisponível: checagens HTTP/TCP do blackbox exporter.")


# ---------------------------------------------------------------- 2. Containers
def containers():
    L = Layout()
    P = [row(L, "Situação agora")]
    P.append(stat(L, "Containers PARADOS", [tgt("count(docker_container_running == 0) or vector(0)")],
                  th=thresholds((None, GREEN), (1, RED)),
                  desc="Containers de docker compose que não estão rodando (exited/created/dead)."))
    P.append(stat(L, "Serviços swarm sem réplicas",
                  [tgt("count(docker_swarm_service_replicas_running < docker_swarm_service_replicas_desired) or vector(0)")],
                  th=thresholds((None, GREEN), (1, RED)),
                  desc="Serviços do Docker Swarm rodando menos réplicas do que o desejado."))
    P.append(stat(L, "Containers unhealthy", [tgt("count(docker_container_healthy == 0) or vector(0)")],
                  th=thresholds((None, GREEN), (1, RED))))
    P.append(stat(L, "Restarts na última hora",
                  [tgt("sum(clamp_min(delta(docker_container_restarts[1h]), 0)) or vector(0)")],
                  th=thresholds((None, GREEN), (1, ORANGE), (5, RED)), decimals=0))
    P.append(stat(L, "Docker daemon", [tgt("docker_daemon_up")], mappings=UPDOWN,
                  th=thresholds((None, RED), (1, GREEN))))
    P.append(stat(L, "Idade da coleta de estado", [tgt("time() - docker_state_last_run_timestamp")], unit="s",
                  decimals=0, th=thresholds((None, GREEN), (180, RED)),
                  desc="Se passar de 3 min, o cron de /root/projeto/monitoring/scripts/docker-state.sh parou."))
    P.append(stat(L, "Containers (docker compose)", [tgt("docker_container_running", "{{name}}")], w=12, h=5,
                  mappings=RUNSTOP, th=thresholds((None, RED), (1, GREEN)), text_mode="value_and_name"))
    P.append(stat(L, "Serviços swarm (réplicas rodando)",
                  [tgt("docker_swarm_service_replicas_running", "{{service}}")], w=12, h=5,
                  th=thresholds((None, RED), (1, GREEN)), text_mode="value_and_name", decimals=0))
    P.append(row(L, "Histórico"))
    P.append(timeline(L, "Linha do tempo (vermelho = parado / réplicas faltando)", [
        tgt("docker_container_running", "{{name}}", "A"),
        tgt("docker_swarm_service_replicas_running >= bool docker_swarm_service_replicas_desired",
            "swarm: {{service}}", "B"),
    ], RUNSTOP, h=8))
    P.append(ts(L, "Restarts acumulados", [tgt("docker_container_restarts", "{{name}}")], w=12, fill=0))
    P.append(ts(L, "Exit code dos containers", [tgt("docker_container_exit_code", "{{name}}")], w=12, fill=0,
                desc="0 = saída normal. 137 = morto por OOM/kill. 1/2/255 = erro da aplicação."))
    P.append(row(L, "Uso de recursos por container (cAdvisor)"))
    P.append(ts(L, "CPU por container (% de 1 núcleo)",
                [tgt('sum by (name) (rate(container_cpu_usage_seconds_total{name!=""}[2m])) * 100', "{{name}}")],
                unit="percent"))
    P.append(ts(L, "Memória por container",
                [tgt('sum by (name) (container_memory_working_set_bytes{name!=""})', "{{name}}")], unit="bytes"))
    P.append(ts(L, "Rede recebida por container",
                [tgt('sum by (name) (rate(container_network_receive_bytes_total{name!=""}[2m]))', "{{name}}")],
                unit="Bps"))
    P.append(ts(L, "Rede enviada por container",
                [tgt('sum by (name) (rate(container_network_transmit_bytes_total{name!=""}[2m]))', "{{name}}")],
                unit="Bps"))
    P.append(row(L, "Detalhe"))
    P.append(table(L, "Estado dos containers", [
        tgt("docker_container_running", "", "A", True, "table"),
        tgt("docker_container_healthy", "", "B", True, "table"),
        tgt("docker_container_restarts", "", "C", True, "table"),
        tgt("docker_container_exit_code", "", "D", True, "table"),
    ], rename={"name": "Container", "project": "Projeto compose", "service": "Serviço", "status": "Status",
               "Value #A": "Rodando", "Value #B": "Health", "Value #C": "Restarts", "Value #D": "Exit code"},
        overrides=[
            col_override("Rodando", mappings=RUNSTOP, th=thresholds((None, RED), (1, GREEN))),
            col_override("Health", mappings=vmap({1: ("saudável", GREEN), 0: ("UNHEALTHY", RED),
                                                  -1: ("sem healthcheck", "text")}),
                         th=thresholds((None, "transparent"), (0, RED), (1, GREEN))),
        ], h=7, sort=("Rodando", False)))
    return dashboard("mon-containers", "2. Containers", P, ["containers"],
                     desc="Container parado, réplicas faltando, restarts e consumo por container.")


# ---------------------------------------------------------------- 3. Recursos
CPU_PCT = '100 * (1 - avg(rate(node_cpu_seconds_total{mode="idle"}[2m])))'
MEM_PCT = "100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)"
DISK_PCT = '100 * (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})'
NCPU = 'count(node_cpu_seconds_total{mode="idle"})'
FS = 'fstype!~"tmpfs|overlay|squashfs|nsfs|ramfs|fuse.*"'
PCT_TH = thresholds((None, GREEN), (75, ORANGE), (90, RED))


def resources():
    L = Layout()
    P = [row(L, "Situação agora")]
    P.append(stat(L, "CPU", [tgt(CPU_PCT)], unit="percent", decimals=1, th=PCT_TH, graph=True))
    P.append(stat(L, "Memória", [tgt(MEM_PCT)], unit="percent", decimals=1, th=PCT_TH, graph=True))
    P.append(stat(L, "Disco /", [tgt(DISK_PCT)], unit="percent", decimals=1,
                  th=thresholds((None, GREEN), (80, ORANGE), (90, RED)), graph=True))
    P.append(stat(L, "Load 5m por núcleo", [tgt(f"node_load5 / {NCPU}")], decimals=2,
                  th=thresholds((None, GREEN), (1, ORANGE), (2, RED)), graph=True))
    P.append(stat(L, "OOM kills (24h)", [tgt("increase(node_vmstat_oom_kill[24h]) or vector(0)")], decimals=0,
                  th=thresholds((None, GREEN), (1, RED)),
                  desc="Processos mortos pelo kernel por falta de memória."))
    P.append(stat(L, "CPU iowait", [tgt('100 * avg(rate(node_cpu_seconds_total{mode="iowait"}[2m]))')],
                  unit="percent", decimals=1, th=thresholds((None, GREEN), (10, ORANGE), (25, RED)), graph=True,
                  desc="CPU parada esperando disco. Alto = disco lento/saturado."))
    P.append(row(L, "CPU e carga"))
    P.append(ts(L, "CPU por modo", [tgt(
        f'sum by (mode) (rate(node_cpu_seconds_total{{mode!="idle"}}[2m])) / scalar({NCPU}) * 100', "{{mode}}")],
        unit="percent", stack=True, maxv=100, minv=0, fill=40))
    P.append(ts(L, "Load average", [tgt("node_load1", "1m", "A"), tgt("node_load5", "5m", "B"),
                                    tgt("node_load15", "15m", "C"), tgt(NCPU, "núcleos", "D")], fill=0))
    P.append(row(L, "Memória"))
    P.append(ts(L, "Memória", [
        tgt("node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes", "usada", "A"),
        tgt("node_memory_Cached_bytes + node_memory_Buffers_bytes", "cache/buffers", "B"),
        tgt("node_memory_MemAvailable_bytes", "disponível", "C"),
        tgt("node_memory_MemTotal_bytes", "total", "D"),
    ], unit="bytes", fill=0))
    P.append(ts(L, "Pressão de recursos (PSI) - tempo travado esperando", [
        tgt("rate(node_pressure_cpu_waiting_seconds_total[2m]) * 100", "CPU", "A"),
        tgt("rate(node_pressure_memory_waiting_seconds_total[2m]) * 100", "Memória", "B"),
        tgt("rate(node_pressure_io_waiting_seconds_total[2m]) * 100", "Disco (IO)", "C"),
    ], unit="percent", fill=0, th=thresholds((None, GREEN), (20, ORANGE), (50, RED)),
        desc="% do tempo em que processos ficaram travados por falta do recurso. Melhor indicador de gargalo."))
    P.append(row(L, "Disco"))
    P.append(ts(L, "Uso dos filesystems", [tgt(
        f"100 * (1 - node_filesystem_avail_bytes{{{FS}}} / node_filesystem_size_bytes{{{FS}}})", "{{mountpoint}}")],
        unit="percent", maxv=100, minv=0, fill=0, th=thresholds((None, GREEN), (80, ORANGE), (90, RED))))
    P.append(ts(L, "Utilização do disco (% ocupado)", [tgt(
        'rate(node_disk_io_time_seconds_total{device!~"loop.*|sr.*|ram.*"}[2m]) * 100', "{{device}}")],
        unit="percent", fill=0, th=thresholds((None, GREEN), (80, ORANGE), (95, RED))))
    P.append(ts(L, "Leitura/escrita no disco", [
        tgt('rate(node_disk_read_bytes_total{device!~"loop.*|sr.*|ram.*"}[2m])', "leitura {{device}}", "A"),
        tgt('rate(node_disk_written_bytes_total{device!~"loop.*|sr.*|ram.*"}[2m])', "escrita {{device}}", "B"),
    ], unit="Bps", fill=0))
    P.append(ts(L, "Espaço livre", [tgt(f"node_filesystem_avail_bytes{{{FS}}}", "{{mountpoint}}")],
                unit="bytes", fill=0))
    P.append(row(L, "Rede"))
    NET = 'device!~"lo|veth.*|br-.*|docker.*|wg.*|vx.*"'
    P.append(ts(L, "Tráfego de rede", [
        tgt(f"rate(node_network_receive_bytes_total{{{NET}}}[2m]) * 8", "entrada {{device}}", "A"),
        tgt(f"rate(node_network_transmit_bytes_total{{{NET}}}[2m]) * 8", "saída {{device}}", "B"),
    ], unit="bps", fill=0))
    P.append(ts(L, "Top 5 containers - memória", [
        tgt('topk(5, sum by (name) (container_memory_working_set_bytes{name!=""}))', "{{name}}")],
        unit="bytes", fill=0))
    return dashboard("mon-resources", "3. Recursos", P, ["recursos"],
                     desc="CPU, memória, disco, rede, OOM e pressão de recursos.")


# ---------------------------------------------------------------- 4. Ambiente
def environment():
    L = Layout()
    P = [row(L, "Situação agora")]
    P.append(stat(L, "Serviços do sistema com falha",
                  [tgt('count(node_systemd_unit_state{state="failed"} == 1) or vector(0)')],
                  th=thresholds((None, GREEN), (1, RED))))
    P.append(stat(L, "Coletores fora", [tgt("count(up == 0) or vector(0)")],
                  th=thresholds((None, GREEN), (1, RED)),
                  desc="Prometheus não consegue ler algum exporter (job down)."))
    P.append(stat(L, "Filesystem somente leitura",
                  [tgt(f'count(node_filesystem_readonly{{{FS},mountpoint!~"/boot/efi"}} == 1) or vector(0)')],
                  th=thresholds((None, GREEN), (1, RED)),
                  desc="Disco remontado como read-only costuma indicar erro de disco/filesystem."))
    P.append(stat(L, "Relógio sincronizado (NTP)", [tgt("node_timex_sync_status")], mappings=YESNO,
                  th=thresholds((None, RED), (1, GREEN))))
    P.append(stat(L, "Ligado há", [tgt("time() - node_boot_time_seconds")], unit="s", decimals=0,
                  th=thresholds((None, RED), (3600, GREEN)), color_mode="value",
                  desc="Fica vermelho se o servidor reiniciou na última hora."))
    P.append(stat(L, "Disco / cheio em",
                  [tgt('node_filesystem_avail_bytes{mountpoint="/"} / '
                       'clamp_min(-deriv(node_filesystem_avail_bytes{mountpoint="/"}[6h]), 0.001)')],
                  unit="s", decimals=0, th=thresholds((None, RED), (86400, ORANGE), (604800, GREEN)),
                  desc="Previsão pelo ritmo de crescimento das últimas 6h. Número enorme = disco não está enchendo."))
    P.append(stat(L, "Serviços do sistema (systemd)",
                  [tgt('node_systemd_unit_state{state="active"}', "{{name}}")], w=24, h=5,
                  mappings=ACTIVE, th=thresholds((None, RED), (1, GREEN)), text_mode="value_and_name"))
    P.append(stat(L, "Coletores de métricas", [tgt("up", "{{job}} {{app}}")], w=16, h=4,
                  mappings=UPDOWN, th=thresholds((None, RED), (1, GREEN)), text_mode="value_and_name"))
    P.append(stat(L, "Docker daemon", [tgt("docker_daemon_up")], w=4, mappings=UPDOWN,
                  th=thresholds((None, RED), (1, GREEN))))
    P.append(stat(L, "OOM kills (24h)", [tgt("increase(node_vmstat_oom_kill[24h]) or vector(0)")], w=4,
                  decimals=0, th=thresholds((None, GREEN), (1, RED))))
    P.append(row(L, "Limites do sistema"))
    P.append(stat(L, "Inodes usados (/)", [tgt(
        '100 * (1 - node_filesystem_files_free{mountpoint="/"} / node_filesystem_files{mountpoint="/"})')],
        w=6, unit="percent", decimals=1, th=PCT_TH, graph=True))
    P.append(stat(L, "File descriptors", [tgt("100 * node_filefd_allocated / node_filefd_maximum")], w=6,
                  unit="percent", decimals=2, th=PCT_TH, graph=True))
    P.append(stat(L, "Conntrack (conexões rastreadas)",
                  [tgt("100 * node_nf_conntrack_entries / node_nf_conntrack_entries_limit")], w=6,
                  unit="percent", decimals=1, th=PCT_TH, graph=True,
                  desc="Se encher, o kernel começa a descartar conexões novas."))
    P.append(stat(L, "Processos bloqueados (IO)", [tgt("node_procs_blocked")], w=6, decimals=0,
                  th=thresholds((None, GREEN), (3, ORANGE), (10, RED)), graph=True))
    P.append(row(L, "Histórico"))
    P.append(timeline(L, "Serviços do sistema (vermelho = falhou/parado)",
                      [tgt('node_systemd_unit_state{state="active"}', "{{name}}")], ACTIVE, h=8))
    P.append(timeline(L, "Coletores de métricas (vermelho = sem coleta)", [tgt("up", "{{job}} {{app}}")],
                      UPDOWN, h=8))
    P.append(ts(L, "Erros e descartes de rede", [
        tgt('rate(node_network_receive_errs_total{device!="lo"}[5m]) + rate(node_network_transmit_errs_total{device!="lo"}[5m])',
            "erros {{device}}", "A"),
        tgt('rate(node_network_receive_drop_total{device!="lo"}[5m]) + rate(node_network_transmit_drop_total{device!="lo"}[5m])',
            "drops {{device}}", "B"),
    ], unit="pps", fill=0))
    P.append(ts(L, "Desvio do relógio", [tgt("node_timex_offset_seconds", "offset")], unit="s", fill=0,
                th=thresholds((None, GREEN), (0.5, RED))))
    return dashboard("mon-env", "4. Ambiente", P, ["ambiente"],
                     desc="Serviços do sistema, coletores, NTP, reboot, disco read-only, limites do kernel.")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("1-aplicacoes", apps), ("2-containers", containers),
                     ("3-recursos", resources), ("4-ambiente", environment)]:
        with open(os.path.join(OUT, name + ".json"), "w", encoding="utf-8") as f:
            json.dump(fn(), f, ensure_ascii=False, indent=2)
        print("ok", name)
