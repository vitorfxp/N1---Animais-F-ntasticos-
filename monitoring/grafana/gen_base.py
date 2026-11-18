"""Adapta os dashboards da base (github.com/guisosi/Tamoai-Infra) para este servidor.

Entrada:  ./base/*.json  (cópias originais da base)
Saída:    ./dashboards/0-mapa-de-trafego.json   <- "Nimbus | Mapa de calor" (Caddy/CrowdSec -> Apache/SSH)
          ./dashboards/5-host-node-exporter.json <- "Node Exporter Full" (grafana.com 1860, rfmoz)
          ./dashboards/6-containers-cadvisor.json <- "cAdvisor Docker Insights" (grafana.com 19908)

Mantém layout, tipos de painel e estilo da base; troca as consultas, a paleta (a mesma do site
https://animaisfantasticos.infinitymais.com.br) e a identidade ("Radar").
Uso: python3 gen_base.py
"""
import copy
import json
import os
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(AQUI, "base")
OUT = os.path.join(AQUI, "dashboards")
SITE = "https://animaisfantasticos.infinitymais.com.br"

# ------------------------------------------------------------------ paleta (igual ao site)
SSH, SSH_ESC = "#E5303B", "#8E1F25"
HTTP, HTTP_ESC = "#3E63DD", "#22377E"
VERDE, AMBAR, OURO, NEUTRO = "#1F9D55", "#F5A623", "#E8C468", "#5B5853"

CORES = {
    # verdes
    "green": VERDE, "#7EB26D": VERDE, "#299C46": VERDE, "#73BF69": VERDE, "rgba(50, 172, 45, 0.97)": VERDE,
    "dark-green": "#14693A", "semi-dark-green": "#178049",
    # vermelhos
    "red": SSH, "#E24D42": SSH, "#F2495C": SSH, "#D9314D": SSH, "#BF1B00": SSH, "rgba(245, 54, 54, 0.9)": SSH,
    "dark-red": SSH_ESC, "#890F02": SSH_ESC, "semi-dark-red": "#B3242D",
    # laranjas / amarelos
    "orange": AMBAR, "#EF843C": AMBAR, "#EAB839": AMBAR, "#D97706": AMBAR, "rgba(237, 129, 40, 0.89)": AMBAR,
    "yellow": OURO, "dark-orange": "#C9821A",
    # azuis
    "blue": HTTP, "#3274D9": HTTP, "#5794F2": HTTP, "#56B5CA": HTTP, "#1F78C1": HTTP,
    "dark-blue": HTTP_ESC, "#0A437C": HTTP_ESC, "#052B51": "#16213F", "semi-dark-blue": "#2C4BB0",
    # roxos -> neutro quente (o site não usa roxo)
    "purple": NEUTRO, "#8F3BB8": NEUTRO, "#6D1F62": "#3A2F31", "#B993FF": OURO,
}


def recolorir(o):
    if isinstance(o, dict):
        return {k: recolorir(v) for k, v in o.items()}
    if isinstance(o, list):
        return [recolorir(v) for v in o]
    if isinstance(o, str) and o in CORES:
        return CORES[o]
    return o


def paineis(d):
    def walk(ps):
        for p in ps:
            yield p
            yield from walk(p.get("panels", []))
    return list(walk(d["panels"]))


def ler(nome):
    with open(os.path.join(BASE, nome), encoding="utf-8") as f:
        return json.load(f)


def salvar(nome, d):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, nome), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print("ok", nome)


LINKS = [
    {"type": "dashboards", "tags": ["radar"], "asDropdown": True, "title": "Radar", "includeVars": False, "keepTime": True},
    {"type": "link", "title": "Site ao vivo", "url": SITE, "targetBlank": True, "icon": "external link", "tags": []},
]


def identidade(d, uid, titulo, tags, descricao, creditos=None):
    d.pop("id", None)
    d.pop("__inputs", None)
    d.pop("__requires", None)
    d.pop("__elements", None)
    d["uid"], d["title"], d["description"] = uid, titulo, descricao
    d["tags"] = ["radar"] + tags
    d["links"] = LINKS + (creditos or [])
    d["editable"] = True
    d["version"] = 1
    return d


# ================================================================== 0. Mapa de tráfego (Nimbus)
LOKI = {"type": "loki", "uid": "loki"}
H = '{job="apache", vhost=~"$vhost"}'
TUDO = '{job=~"apache|ssh", result!="sucesso"}'
S = '{job="ssh", result="falha"}'
RX = (r'| regexp `(?P<c_ip>[0-9a-fA-F:.]+) \S+ \S+ \[[^\]]+\] "(?P<c_method>\S*) ?(?P<c_path>\S*)[^"]*" '
      r'(?P<c_status>\d{3}) (?P<c_size>\S+)(?: "(?P<c_ref>[^"]*)" "(?P<c_ua>[^"]*)")?`')
SRX = r'| regexp `(?:for|user) (?:invalid user )?(?P<c_user>\S*) ?(?:from )?(?P<c_ip>[0-9a-fA-F:.]{7,}) port`'
R = "[$__range]"


def q(expr, legend="", instant=True, ref="A", fmt=None):
    t = {"datasource": LOKI, "editorMode": "code", "expr": expr, "legendFormat": legend, "refId": ref,
         "queryType": "instant" if instant else "range"}
    if fmt:
        t["format"] = fmt
    return t


# título na base -> (novo título, consultas, cor fixa opcional, unidade opcional, descrição)
MAPA = {
    "Requisições no período": ("Acessos HTTP no período", [q(f"sum(count_over_time({H}{R}))")], HTTP, None,
                               "Requisições registradas nos logs de acesso do Apache."),
    "IPs distintos": ("IPs distintos (HTTP)", [q(f"count(sum by (c_ip) (count_over_time({H} {RX} {R})))")], NEUTRO, None, ""),
    "Países observados": ("Países de origem", [q(f"count(sum by (geoip_country_name) (count_over_time({TUDO}{R})))")],
                          VERDE, None, "HTTP + tentativas de SSH."),
    "Respostas 4xx": ("Respostas 4xx", [q(f'sum(count_over_time({{job="apache", vhost=~"$vhost", status_class="4xx"}}{R}))')],
                      AMBAR, None, ""),
    "Respostas 5xx": ("Respostas 5xx", [q(f'sum(count_over_time({{job="apache", vhost=~"$vhost", status_class="5xx"}}{R}))')],
                      SSH_ESC, None, ""),
    "Corpo das respostas": ("Tentativas SSH no período", [q(f"sum(count_over_time({S}{R}))")], SSH, "short",
                            "Senhas erradas, usuários inválidos e conexões de bots na porta 22."),
    "Fluxo de acessos": ("Fluxo de tráfego até o servidor", [], None, None,
                         "Linhas de cada origem (cidade) até o servidor. Vermelho = SSH, azul = HTTP."),
    "Países · top 10": ("Países · top 10", [q(f"topk(10, sum by (geoip_country_name) (count_over_time({TUDO}{R})))",
                                              "{{geoip_country_name}}")], None, None, ""),
    "Cobertura GeoIP": ("Cobertura GeoIP", [q(f'100 * sum(count_over_time({TUDO} | geoip_location_latitude!="" {R})) '
                                              f"/ sum(count_over_time({TUDO}{R}))")], VERDE, None,
                        "Parte dos eventos com localização encontrada no DB-IP."),
    "Requisições por segundo": ("Requisições por segundo", [q(f"sum(rate({H}{R}))")], HTTP, None, ""),
    "Países por acessos": ("Países por acessos HTTP", [q(f"topk(10, sum by (geoip_country_name) (count_over_time({H}{R})))",
                                                         "{{geoip_country_name}}")], None, None, ""),
    "Cidades por acessos": ("Cidades por eventos", [q(f"topk(10, sum by (geoip_country_name, geoip_city_name) "
                                                      f"(count_over_time({TUDO}{R})))", fmt="table")], None, None, ""),
    "IPs por acessos": ("IPs por acessos HTTP", [q(f"topk(15, sum by (c_ip) (count_over_time({H} {RX} {R})))", "{{c_ip}}")],
                        None, None, ""),
    "HTTP por código": ("HTTP por código", [q(f"sum by (status) (count_over_time({H}[$__interval]))", "{{status}}", False)],
                        None, None, ""),
    "Distribuição de status HTTP": ("Distribuição de status HTTP",
                                    [q(f"sum by (status_class) (count_over_time({H}{R}))", "{{status_class}}")], None, None, ""),
    "Métodos HTTP": ("Métodos HTTP", [q(f"sum by (method) (count_over_time({H}{R}))", "{{method}}")], None, None, ""),
    "Latência · mediana e P95": ("Tentativas SSH por segundo", [q(f"sum(rate({S}[$__rate_interval]))", "Tentativas/s", False)],
                                 SSH, "reqps", "O log do Apache (formato combined) não tem latência; no lugar, o ritmo de ataques SSH."),
    "Bytes de resposta por segundo": ("Bytes de resposta por segundo",
                                      [q(f'sum(rate({H} {RX} | c_size=~"[0-9]+" | unwrap c_size [$__rate_interval]))',
                                         "Bytes/s", False)], HTTP, None, ""),
    "Erros HTTP · proporção por intervalo": ("Erros HTTP · proporção por intervalo", [
        q(f'100 * sum(count_over_time({{job="apache", vhost=~"$vhost", status_class=~"4xx|5xx"}}[$__interval])) '
          f"/ sum(count_over_time({H}[$__interval]))", "% 4xx+5xx", False)], None, None, ""),
    "Caminhos mais acessados": ("Caminhos mais acessados", [q(f"topk(15, sum by (c_path) (count_over_time({H} {RX} {R})))",
                                                              fmt="table")], None, None, ""),
    "Domínios por acessos": ("Sites (vhosts) por acessos", [q(f"topk(10, sum by (vhost) (count_over_time({H}{R})))",
                                                              fmt="table")], None, None, ""),
    "IPs com respostas 4xx / 5xx": ("IPs com respostas 4xx / 5xx", [q(
        f'topk(10, sum by (c_ip, c_status) (count_over_time({H} {RX} | c_status=~"[45].." {R})))', fmt="table")], None, None, ""),
    "Referências de acesso · top 10": ("Referências de acesso · top 10", [q(
        f'topk(10, sum by (c_ref) (count_over_time({H} {RX} | c_ref!="" | c_ref!="-" {R})))', fmt="table")], None, None, ""),
    "User-Agent · top 10": ("User-Agent · top 10", [q(f'topk(10, sum by (c_ua) (count_over_time({H} {RX} | c_ua!="" {R})))',
                                                      fmt="table")], None, None, ""),
    "Acessos por hora": ("Eventos por hora · HTTP x SSH", [q(f"sum by (job) (count_over_time({TUDO}[1h]))", "{{job}}", False)],
                         None, None, ""),
    "Últimos acessos · até 300 registros": ("Últimos eventos · até 300 registros", [
        {"datasource": LOKI, "editorMode": "code", "expr": TUDO + ' | job=~"$tipo"', "queryType": "range", "refId": "A",
         "maxLines": 300}], None, None, ""),
    # ---- seção CrowdSec da base -> SSH
    "Coleta do CrowdSec": ("Tentativas SSH", [q(f"sum(count_over_time({S}{R}))")], SSH, "short", ""),
    "Decisões ativas": ("IPs atacando via SSH", [q(f"count(sum by (c_ip) (count_over_time({S} {SRX} {R})))")], SSH_ESC, "short", ""),
    "Cenários disparados no período": ("Usuários tentados", [q(f"count(sum by (c_user) (count_over_time({S} {SRX} {R})))")],
                                       NEUTRO, "short", "Nomes de usuário diferentes usados pelos bots."),
    "Buckets em processamento": ("Logins SSH aceitos", [q(f'sum(count_over_time({{job="ssh", result="sucesso"}}{R}))')],
                                 VERDE, "short", "Entradas legítimas (chave ou senha corretas)."),
    "Disparos por cenário": ("Tentativas SSH por país", [q(
        f"topk(8, sum by (geoip_country_name) (count_over_time({S}[$__interval])))", "{{geoip_country_name}}", False)],
        None, "short", ""),
    "Decisões ativas por ação": ("HTTP x SSH por intervalo", [q(f"sum by (job) (count_over_time({TUDO}[$__interval]))",
                                                                "{{job}}", False)], None, "short", ""),
    "Processamento de logs": ("Logs recebidos por segundo (Promtail)", [q(f"sum by (job) (rate({{job=~\"apache|ssh\"}}[$__rate_interval]))",
                                                                          "{{job}}", False)], None, "short", ""),
    "Decisões ativas por origem": ("Usuários mais tentados no SSH", [q(
        f"topk(10, sum by (c_user) (count_over_time({S} {SRX} {R})))", "{{c_user}}")], None, "short", ""),
}

ROWS = {"Visão geral dos acessos": "Visão geral", "Distribuição geográfica": "Distribuição geográfica",
        "HTTP e desempenho": "HTTP e desempenho", "Origens e recursos": "Origens e recursos",
        "CrowdSec · métricas do Prometheus": "SSH · tentativas de acesso"}

FLUXO_JS = r"""// Mapa de fluxo (Business Charts > Maps: JSON > Code). Base: Nimbus / Tamoai-Infra.
// Origem de cada evento -> servidor. Vermelho = tentativas SSH, azul = acessos HTTP.
const destino = { nome: 'Servidor · Ashburn, EUA', coords: [-77.4874, 39.0438] };
const COR = { ssh: '#E5303B', apache: '#3E63DD' };
const ler = (v, i) => typeof v?.get === 'function' ? v.get(i) : v?.[i];
const num = v => v === null || v === undefined || v === '' ? NaN : Number(v);
const grupos = new Map();
let linhasRecebidas = 0;

function juntar(lat, lon, n, pais, cidade, job) {
  lat = num(lat); lon = num(lon); n = num(n);
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || !Number.isFinite(n) || n <= 0 ||
      Math.abs(lat) > 90 || Math.abs(lon) > 180) return;
  const k = `${lat.toFixed(1)}|${lon.toFixed(1)}`;
  const g = grupos.get(k) || { lat, lon, ssh: 0, http: 0, pais: pais || '', cidade: cidade || '' };
  if (job === 'ssh') g.ssh += n; else g.http += n;
  grupos.set(k, g);
}

for (const frame of context.panel.data.series) {
  const campos = frame.fields || [];
  const achar = (...nomes) => campos.find(f => nomes.includes(f.name));
  const lat = achar('geoip_location_latitude'), lon = achar('geoip_location_longitude');
  const pais = achar('geoip_country_name'), cidade = achar('geoip_city_name'), job = achar('job');
  const valor = achar('Value', 'Value #A') || campos.find(f => f.type === 'number' && f !== lat && f !== lon);
  linhasRecebidas += frame.length ?? 0;
  if (lat && lon && valor) {
    for (let i = 0; i < valor.values.length; i++)
      juntar(ler(lat.values, i), ler(lon.values, i), ler(valor.values, i), ler(pais?.values, i), ler(cidade?.values, i), ler(job?.values, i));
  } else {
    for (const f of campos.filter(f => f.type === 'number')) {
      const l = f.labels || {};
      juntar(l.geoip_location_latitude, l.geoip_location_longitude, ler(f.values, f.values.length - 1),
        l.geoip_country_name, l.geoip_city_name, l.job);
    }
  }
}

const origens = [...grupos.values()].map(g => ({ ...g, n: g.ssh + g.http }))
  .sort((a, b) => b.n - a.n).slice(0, 90);
const max = Math.max(1, ...origens.map(o => o.n));
const forca = n => Math.log1p(n) / Math.log1p(max);
const cor = o => o.ssh >= o.http ? COR.ssh : COR.apache;
const fmt = n => Number(n).toLocaleString('pt-BR');
const total = origens.reduce((s, o) => s + o.n, 0);
const nome = o => [o.cidade, o.pais].filter(Boolean).join(' · ') || 'Origem geolocalizada';

return {
  backgroundColor: '#0B0B0A', animation: true, animationDurationUpdate: 800,
  tooltip: {
    trigger: 'item', renderMode: 'richText', backgroundColor: '#121211', borderColor: '#3A3937',
    textStyle: { color: '#FAFAF9', fontSize: 12 },
    formatter: p => {
      if (p.seriesId === 'destino') return `${destino.nome}\n${fmt(total)} eventos das origens exibidas`;
      const o = p.data && p.data.o; if (!o) return '';
      return `${nome(o)}\nSSH: ${fmt(o.ssh)}   HTTP: ${fmt(o.http)}`;
    }
  },
  geo: {
    map: 'world', roam: true, zoom: 1.05, center: [-20, 22],
    top: '5%', bottom: '5%', left: '3%', right: '3%', scaleLimit: { min: 1, max: 12 },
    label: { show: false },
    itemStyle: { areaColor: '#1A1A19', borderColor: '#3A3937', borderWidth: 0.55 },
    emphasis: { label: { show: false }, itemStyle: { areaColor: '#262524' } },
    select: { disabled: true }
  },
  graphic: origens.length ? [] : [{
    type: 'text', left: 'center', top: '85%', silent: true,
    style: { text: linhasRecebidas ? 'Dados sem coordenadas válidas' : 'Sem eventos neste intervalo', fill: '#A19E9A', fontSize: 14 }
  }],
  series: [
    { id: 'rotas', name: 'Tráfego', type: 'lines', coordinateSystem: 'geo', zlevel: 1, polyline: false,
      data: origens.map(o => ({ o, coords: [[o.lon, o.lat], destino.coords],
        lineStyle: { color: cor(o), width: 0.4 + 0.9 * forca(o.n), opacity: 0.12 + 0.3 * forca(o.n) } })),
      lineStyle: { type: 'solid', curveness: 0.22 },
      effect: { show: true, period: 4, trailLength: 0.18, symbol: 'circle', symbolSize: 3.5, color: '#FAFAF9' },
      emphasis: { lineStyle: { width: 1.6, opacity: 0.8 } } },
    { id: 'origens', name: 'Origens', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 2,
      data: origens.map(o => ({ o, value: [o.lon, o.lat, o.n], itemStyle: { color: cor(o) } })),
      symbolSize: v => 4 + 9 * forca(v[2]), showEffectOn: 'emphasis',
      rippleEffect: { period: 4, scale: 2.2, brushType: 'stroke' }, label: { show: false } },
    { id: 'destino', name: 'Servidor', type: 'effectScatter', coordinateSystem: 'geo', zlevel: 3,
      data: [{ name: destino.nome, value: [...destino.coords, total] }], symbolSize: 14, showEffectOn: 'render',
      rippleEffect: { period: 2.6, scale: 4.2, brushType: 'stroke' },
      itemStyle: { color: '#E8C468', shadowBlur: 22, shadowColor: '#E8C468' },
      label: { show: true, formatter: 'SERVIDOR', position: 'right', distance: 12, color: '#1A1405', fontWeight: 700,
        fontSize: 11, backgroundColor: '#E8C468', padding: [5, 8], borderRadius: 5 } }
  ]
};
"""

CABECALHO_MD = f"""<div style="display:flex;align-items:center;gap:14px;padding:4px 2px">
<img src="{SITE}/img/logo.svg" width="34" height="34" alt="">
<div><div style="font-size:20px;font-weight:600;letter-spacing:-.02em">radar · mapa de tráfego</div>
<div style="opacity:.7;font-size:12px">De onde vem o que chega no servidor: acessos HTTP (Apache) em
<b style="color:{HTTP}">azul</b>, tentativas de SSH em <b style="color:{SSH}">vermelho</b>.
Versão pública e animada: <a href="{SITE}" target="_blank">{SITE.replace('https://', '')}</a> ·
GeoIP: <a href="https://db-ip.com" target="_blank">IP Geolocation by DB-IP</a></div></div></div>"""


def mapa_de_trafego():
    d = ler("nimbus-mapa-de-calor.json")
    for p in paineis(d):
        if p["type"] == "row":
            p["title"] = ROWS.get(p.get("title"), p.get("title"))
            continue
        titulo = p.get("title")
        if titulo not in MAPA:
            raise SystemExit(f"painel sem mapeamento: {titulo}")
        novo, alvos, cor, unidade, desc = MAPA[titulo]
        p["title"], p["targets"], p["datasource"] = novo, alvos, LOKI
        p["description"] = desc
        fc = p.setdefault("fieldConfig", {}).setdefault("defaults", {})
        if cor:
            fc["color"] = {"mode": "fixed", "fixedColor": cor}
        if unidade:
            fc["unit"] = unidade
        if p["type"] == "volkovlabs-echarts-panel":
            p["title"] = "Fluxo de tráfego até o servidor"
            p["targets"] = [q(f"topk(150, sum by (job, geoip_location_latitude, geoip_location_longitude, "
                              f"geoip_country_name, geoip_city_name) (count_over_time({TUDO} "
                              f'| geoip_location_latitude!="" {R})))')]
            p["options"]["getOption"] = FLUXO_JS
        # séries HTTP x SSH com as cores do site
        if any("sum by (job)" in t.get("expr", "") for t in p["targets"]):
            fc["color"] = {"mode": "palette-classic"}
            p["fieldConfig"]["overrides"] = [
                {"matcher": {"id": "byName", "options": "ssh"}, "properties": [
                    {"id": "color", "value": {"mode": "fixed", "fixedColor": SSH}},
                    {"id": "displayName", "value": "SSH"}]},
                {"matcher": {"id": "byName", "options": "apache"}, "properties": [
                    {"id": "color", "value": {"mode": "fixed", "fixedColor": HTTP}},
                    {"id": "displayName", "value": "HTTP"}]},
            ]

    # cabeçalho com a marca no topo; empurra tudo 3 linhas para baixo
    for p in d["panels"]:
        p["gridPos"]["y"] += 3
    d["panels"].insert(0, {
        "type": "text", "title": "", "id": 900, "transparent": True,
        "gridPos": {"x": 0, "y": 0, "w": 24, "h": 3},
        "options": {"mode": "html", "content": CABECALHO_MD},
    })

    d["templating"] = {"list": [
        {"name": "vhost", "label": "Site (vhost)", "type": "query", "datasource": LOKI,
         "query": {"label": "vhost", "stream": '{job="apache"}', "type": 1, "refId": "LokiVariableQueryEditor-VariableQuery"},
         "definition": "label_values(vhost)", "includeAll": True, "multi": True, "allValue": ".*",
         "current": {"text": ["All"], "value": ["$__all"]}, "refresh": 2, "sort": 1},
        {"name": "tipo", "label": "Logs de", "type": "custom", "query": "apache,ssh", "includeAll": True, "multi": True,
         "allValue": "apache|ssh", "current": {"text": ["All"], "value": ["$__all"]},
         "options": []},
    ]}
    d["refresh"] = "30s"
    d["time"] = {"from": "now-24h", "to": "now"}
    d = recolorir(d)
    identidade(d, "radar-mapa", "Radar | Mapa de tráfego", ["trafego", "loki", "geoip"],
               "Origem do tráfego que chega no servidor (Apache + SSH) com GeoIP. Adaptado do "
               "'Nimbus | Mapa de calor' do Tamoai-Infra.",
               [{"type": "link", "title": "Base: Tamoai-Infra", "url": "https://github.com/guisosi/Tamoai-Infra",
                 "targetBlank": True, "icon": "doc", "tags": []}])
    return d


# ================================================================== 5. Node Exporter Full
def node_exporter():
    d = recolorir(ler("node-exporter-full.json"))
    for v in d["templating"]["list"]:
        if v.get("name") == "job":
            v["current"] = {"text": "node", "value": "node"}
    d.pop("gnetId", None)
    identidade(d, "radar-host", "Radar | Host (Node Exporter Full)", ["linux", "host"],
               "Node Exporter Full (grafana.com/dashboards/1860, por rfmoz) com a paleta do Radar.",
               [{"type": "link", "title": "Original: rfmoz/grafana-dashboards", "url": "https://github.com/rfmoz/grafana-dashboards",
                 "targetBlank": True, "icon": "doc", "tags": []}])
    return d


# ================================================================== 6. cAdvisor
def cadvisor():
    d = recolorir(ler("cadvisor-docker.json"))
    prom = {"type": "prometheus", "uid": "prometheus"}

    def ds(o):
        if isinstance(o, dict):
            if o.get("type") == "prometheus" and "uid" in o:
                o["uid"] = "prometheus"
            for v in o.values():
                ds(v)
        elif isinstance(o, list):
            for v in o:
                ds(v)
    ds(d)
    for p in paineis(d):
        if p["type"] != "row":
            p["datasource"] = prom
        for t in p.get("targets", []):
            e = t.get("expr", "")
            # a base aplica rate() em gauges de memória; aqui o valor direto
            e = re.sub(r"sum\(rate\((container_memory_(?:usage_bytes|cache))\{name=~\"\.\+\"\}\[10m\]\)\) by \(name\)",
                       r'sum(\1{name=~".+"}) by (name)', e)
            e = e.replace("[10m]", "[$__rate_interval]")
            t["expr"], t["datasource"] = e, prom
            if t.get("legendFormat") == "__auto":
                t["legendFormat"] = "{{name}}"
        if p.get("title") == "Running Containers":
            p["title"] = "Containers rodando"
            p.setdefault("fieldConfig", {}).setdefault("defaults", {})["color"] = {"mode": "fixed", "fixedColor": VERDE}
    tr = {"Basic": "Básico", "Memory": "Memória", "I/O": "Disco (I/O)", "Network": "Rede", "Details": "Detalhes",
          "CPU Usage": "Uso de CPU", "Memory Usage": "Uso de memória", "Memory Cached": "Memória em cache",
          "Reads": "Leituras", "Writes": "Escritas", "Received Network Traffic": "Rede recebida",
          "Sent Network Traffic": "Rede enviada", "Container Restarts": "Containers vistos (reinícios)"}
    for p in paineis(d):
        p["title"] = tr.get(p.get("title"), p.get("title"))
    d.pop("gnetId", None)
    identidade(d, "radar-cadvisor", "Radar | Containers (cAdvisor)", ["docker", "containers"],
               "cAdvisor Docker Insights (grafana.com/dashboards/19908) com a paleta do Radar.")
    return d


if __name__ == "__main__":
    salvar("0-mapa-de-trafego.json", mapa_de_trafego())
    salvar("5-host-node-exporter.json", node_exporter())
    salvar("6-containers-cadvisor.json", cadvisor())
