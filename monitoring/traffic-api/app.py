"""API pública e anônima do mapa de tráfego.

Lê o Loki (logs do Apache + SSH com GeoIP) e devolve só dados agregados:
países, cidades (coordenadas arredondadas), contagens e eventos recentes SEM IP, usuário ou caminho.
Só biblioteca padrão do Python. Escuta em 127.0.0.1:9300 (o Apache faz o proxy de /api/).
"""
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from countries import code_for

LOKI = os.environ.get("LOKI_URL", "http://127.0.0.1:3100")
LISTEN = os.environ.get("LISTEN", "127.0.0.1:9300")
SERVER = {
    "name": os.environ.get("SERVER_NAME", "Servidor"),
    "city": os.environ.get("SERVER_CITY", "Ashburn, EUA"),
    "lat": float(os.environ.get("SERVER_LAT", "39.0438")),
    "lon": float(os.environ.get("SERVER_LON", "-77.4874")),
}
SEL = '{job=~"apache|ssh", result!="sucesso"}'
RANGES = {"1h": 3600, "6h": 6 * 3600, "24h": 86400, "7d": 7 * 86400}
STEPS = {"1h": 60, "6h": 300, "24h": 900, "7d": 3 * 3600}
TTL = 15

_cache = {}
_lock = threading.Lock()


def loki(path, params, timeout=25):
    url = f"{LOKI}{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=timeout) as r:
        body = json.load(r)
    if body.get("status") != "success":
        raise RuntimeError(body)
    return body["data"]["result"]


def instant(q):
    return loki("/loki/api/v1/query", {"query": q, "time": str(time.time_ns())})


def kind(job):
    return "ssh" if job == "ssh" else "http"


def num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def traffic(rng):
    sec = RANGES[rng]
    w = f"[{rng}]"
    now = time.time()

    countries = {}
    for r in instant(f"sum by (job, geoip_country_name, geoip_continent_code) "
                     f"(count_over_time({SEL}{w}))"):
        m = r["metric"]
        name = m.get("geoip_country_name") or "Desconhecido"
        code = code_for(name) or "??"
        c = countries.setdefault(name, {"code": code, "name": name,
                                        "continent": m.get("geoip_continent_code") or "", "http": 0, "ssh": 0})
        c[kind(m.get("job"))] += int(num(r["value"][1]))

    places = {}
    for r in instant(f"sum by (job, geoip_country_name, geoip_city_name, geoip_location_latitude, "
                     f"geoip_location_longitude) (count_over_time({SEL}{w}))"):
        m = r["metric"]
        lat, lon = m.get("geoip_location_latitude"), m.get("geoip_location_longitude")
        if lat in (None, "") or lon in (None, ""):
            continue
        lat, lon = round(num(lat), 1), round(num(lon), 1)
        key = (lat, lon)
        p = places.setdefault(key, {"lat": lat, "lon": lon, "city": m.get("geoip_city_name") or "",
                                    "code": code_for(m.get("geoip_country_name")),
                                    "country": m.get("geoip_country_name") or "", "http": 0, "ssh": 0})
        p[kind(m.get("job"))] += int(num(r["value"][1]))

    status = {}
    for r in instant(f'sum by (status_class) (count_over_time({{job="apache"}}{w}))'):
        status[r["metric"].get("status_class", "?")] = int(num(r["value"][1]))

    rate = {"http": 0.0, "ssh": 0.0}
    for r in instant(f"sum by (job) (count_over_time({SEL}[5m]))"):
        rate[kind(r["metric"].get("job"))] = round(num(r["value"][1]) / 5, 2)

    step = STEPS[rng]
    start = int((now - sec) // step * step)
    series = {"http": [], "ssh": []}
    res = loki("/loki/api/v1/query_range", {
        "query": f"sum by (job) (count_over_time({SEL}[{step}s]))",
        "start": str(start * 10**9), "end": str(int(now) * 10**9), "step": str(step)})
    for r in res:
        series[kind(r["metric"].get("job"))] = [[int(t), int(num(v))] for t, v in r["values"]]

    clist = sorted(countries.values(), key=lambda c: -(c["http"] + c["ssh"]))
    plist = sorted(places.values(), key=lambda p: -(p["http"] + p["ssh"]))[:250]
    conts = {}
    for c in clist:
        k = c["continent"] or "??"
        cc = conts.setdefault(k, {"code": k, "http": 0, "ssh": 0})
        cc["http"] += c["http"]
        cc["ssh"] += c["ssh"]
    return {
        "updated": int(now), "range": rng, "step": step, "server": SERVER,
        "totals": {"http": sum(c["http"] for c in clist), "ssh": sum(c["ssh"] for c in clist),
                   "countries": len([c for c in clist if c["name"] != "Desconhecido"]),
                   "places": len(places)},
        "rate_per_min": rate, "status": status, "series": series,
        "countries": clist, "places": plist,
        "continents": sorted(conts.values(), key=lambda c: -(c["http"] + c["ssh"])),
    }


def events(limit):
    now = time.time_ns()
    res = loki("/loki/api/v1/query_range", {
        "query": SEL, "start": str(now - 30 * 60 * 10**9), "end": str(now),
        "limit": str(limit), "direction": "backward"})
    out = []
    for s in res:
        m = s["stream"]
        for ts, line in s["values"]:
            lat, lon = m.get("geoip_location_latitude"), m.get("geoip_location_longitude")
            e = {"t": int(ts) // 10**6, "type": kind(m.get("job")),
                 "code": code_for(m.get("geoip_country_name")), "country": m.get("geoip_country_name") or "",
                 "city": m.get("geoip_city_name") or "",
                 "lat": round(num(lat), 1) if lat else None, "lon": round(num(lon), 1) if lon else None}
            if e["type"] == "http":
                e["status"] = m.get("status") or ""
                e["method"] = (m.get("method") or "")[:10]
            out.append(e)
    out.sort(key=lambda e: -e["t"])
    return {"updated": int(time.time()), "events": out[:limit]}


def cached(key, fn):
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < TTL:
            return hit[1]
    data = fn()
    with _lock:
        _cache[key] = (time.time(), data)
    return data


class Handler(BaseHTTPRequestHandler):
    server_version = "trafego-api"

    def log_message(self, *a):
        pass

    def send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=10")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path == "/api/trafego":
                rng = q.get("range", ["24h"])[0]
                if rng not in RANGES:
                    return self.send(400, {"error": "range inválido"})
                return self.send(200, cached(("t", rng), lambda: traffic(rng)))
            if u.path == "/api/eventos":
                limit = max(1, min(int(q.get("limit", ["60"])[0]), 300))
                return self.send(200, cached(("e", limit), lambda: events(limit)))
            if u.path == "/api/saude":
                return self.send(200, {"ok": True})
            return self.send(404, {"error": "não encontrado"})
        except Exception as exc:  # noqa: BLE001
            return self.send(502, {"error": "falha ao consultar os logs", "detail": type(exc).__name__})


if __name__ == "__main__":
    host, port = LISTEN.rsplit(":", 1)
    ThreadingHTTPServer((host, int(port)), Handler).serve_forever()
