/* Radar · tráfego do servidor ao vivo
   Dados: /api/trafego (agregado) e /api/eventos (últimos eventos, sem IP), servidos pela API do
   monitoramento (/root/projeto/monitoring/traffic-api). */
/* global Globe, topojson, matchMedia, getComputedStyle, performance, requestAnimationFrame, ResizeObserver */
(function () {
  'use strict';

  const API = 'api';
  const INTERVALO_TRAFEGO = 20000;
  const INTERVALO_EVENTOS = 5000;
  const reduzido = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];

  const st = {
    periodo: '24h', filtro: 'tudo', modo: 'fluxo', girar: !reduzido,
    dados: null, eventos: [], ultimoT: 0, aoVivo: true, cursor: null,
    porPais: new Map(), max: 1,
  };

  // ------------------------------------------------------------------ formatação
  const nf = new Intl.NumberFormat('pt-BR');
  const nf1 = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 1 });
  const fmt = n => nf.format(Math.round(n || 0));
  const fmtK = n => n >= 1e6 ? nf1.format(n / 1e6) + ' mi' : n >= 1e4 ? nf1.format(n / 1e3) + ' mil' : fmt(n);
  let regioes = null;
  try { regioes = new Intl.DisplayNames(['pt-BR'], { type: 'region' }); } catch { /* navegador antigo */ }
  const nomePais = (code, nome) => {
    if (code && code.length === 2 && regioes) { try { return regioes.of(code); } catch {} }
    return nome || 'Origem desconhecida';
  };
  const CONTINENTES = { AF: 'África', AN: 'Antártida', AS: 'Ásia', EU: 'Europa', NA: 'América do Norte', OC: 'Oceania', SA: 'América do Sul' };
  const hora = (t, seg) => new Date(t).toLocaleTimeString('pt-BR', seg ? undefined : { hour: '2-digit', minute: '2-digit' });
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const contar = d => st.filtro === 'ssh' ? d.ssh : st.filtro === 'http' ? d.http : d.ssh + d.http;
  const tipoDominante = d => (st.filtro === 'http' || (st.filtro === 'tudo' && d.http > d.ssh)) ? 'http' : 'ssh';

  function hexRgb(h) { h = h.replace('#', ''); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)); }
  function misturar(a, b, t, alfa) {
    const x = hexRgb(a), y = hexRgb(b);
    const c = x.map((v, i) => Math.round(v + (y[i] - v) * t));
    return alfa == null ? `rgb(${c})` : `rgba(${c},${alfa})`;
  }

  // número que "rola" até o valor novo
  function rolar(el, para, casas) {
    if (!el) return;
    const de = Number(el.dataset.v || 0);
    el.dataset.v = para;
    const f = casas ? (v => nf1.format(v)) : (v => fmt(v));
    if (reduzido || de === para) { el.textContent = f(para); return; }
    const t0 = performance.now(), dur = 900;
    (function passo(t) {
      const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = f(de + (para - de) * e);
      if (p < 1) requestAnimationFrame(passo);
    })(t0);
  }

  // ------------------------------------------------------------------ globo
  const ALIAS = { // nome no mapa (Natural Earth) -> nome no GeoIP (DB-IP)
    'united states of america': 'united states', 'netherlands': 'the netherlands',
    'dem. rep. congo': 'dr congo', 'congo': 'congo republic', 'dominican rep.': 'dominican republic',
    'bosnia and herz.': 'bosnia and herzegovina', 'central african rep.': 'central african republic',
    'eq. guinea': 'equatorial guinea', 's. sudan': 'south sudan', 'solomon is.': 'solomon islands',
    'falkland is.': 'falkland islands', 'w. sahara': 'western sahara', 'côte d\'ivoire': 'ivory coast',
    'eswatini': 'eswatini', 'macedonia': 'north macedonia', 'bahamas': 'bahamas', 'czechia': 'czechia',
    'timor-leste': 'timor-leste', 'n. cyprus': 'cyprus', 'somaliland': 'somalia',
  };
  const chaveNome = n => (n || '').toLowerCase().replace(/^the /, '');

  let globo = null, paises = [];
  const elGlobo = $('#globo');

  function corPais(f) {
    const d = st.porPais.get(f._chave);
    if (!d || contar(d) === 0) return css('--pais-vazio');
    const t = Math.log1p(contar(d)) / Math.log1p(st.max);
    const tipo = tipoDominante(d);
    const forte = css(tipo === 'ssh' ? '--ssh' : '--http');
    const base = document.documentElement.dataset.theme === 'light' ? '#C9C6C2' : '#2E2A2B';
    return misturar(base, forte, 0.25 + 0.75 * t);
  }

  function rotuloPais(f) {
    const d = st.porPais.get(f._chave);
    const nome = d ? nomePais(d.code, d.name) : f.properties.name;
    if (!d) return `<div class="tooltip-globo"><b>${nome}</b><div class="l"><span>Sem tráfego no período</span></div></div>`;
    return `<div class="tooltip-globo"><b>${nome}</b>
      <div class="l"><span><i class="q ssh"></i> SSH</span><b>${fmt(d.ssh)}</b></div>
      <div class="l"><span><i class="q http"></i> HTTP</span><b>${fmt(d.http)}</b></div></div>`;
  }

  function iniciarGlobo(topo) {
    paises = topojson.feature(topo, topo.objects.countries).features
      .filter(f => f.properties.name !== 'Antarctica');
    paises.forEach(f => {
      const k = chaveNome(f.properties.name);
      f._chave = chaveNome(ALIAS[k] || k);
    });

    globo = new Globe(elGlobo, { animateIn: !reduzido })
      .backgroundColor('rgba(0,0,0,0)')
      .showAtmosphere(true)
      .atmosphereAltitude(0.14)
      .showGraticules(true)
      .polygonsData(paises)
      .polygonCapColor(corPais)
      .polygonSideColor(() => 'rgba(0,0,0,0.25)')
      .polygonStrokeColor(() => document.documentElement.dataset.theme === 'light' ? 'rgba(255,255,255,.55)' : 'rgba(11,11,10,.85)')
      .polygonAltitude(alturaPais)
      .polygonLabel(rotuloPais)
      .polygonsTransitionDuration(reduzido ? 0 : 700)
      .onPolygonHover(h => { globo.polygonAltitude(f => f === h ? alturaPais(f) + 0.012 : alturaPais(f)); })
      // arcos: origem -> servidor
      .arcColor('cor')
      .arcStroke('larg')
      .arcDashLength('tam')
      .arcDashGap('gap')
      .arcDashInitialGap('ini')
      .arcDashAnimateTime('dur')
      .arcAltitudeAutoScale(0.42)
      .arcsTransitionDuration(0)
      // anéis: pulso no servidor e no ponto de origem de cada evento
      .ringColor(d => t => d.servidor ? `rgba(232,196,104,${1 - t})` : misturar(d.cor, d.cor, 0, 1 - t))
      .ringMaxRadius(d => d.raio)
      .ringPropagationSpeed(d => d.vel)
      .ringRepeatPeriod(d => d.periodo)
      // pontos das cidades
      .pointColor('cor')
      .pointAltitude(0.006)
      .pointRadius('raio')
      .pointsMerge(false)
      .pointLabel(d => `<div class="tooltip-globo"><b>${d.cidade || 'Cidade desconhecida'}</b> · ${nomePais(d.code, d.pais)}
        <div class="l"><span><i class="q ssh"></i> SSH</span><b>${fmt(d.ssh)}</b></div>
        <div class="l"><span><i class="q http"></i> HTTP</span><b>${fmt(d.http)}</b></div></div>`)
      // chamadas (pílulas) dos maiores emissores + servidor
      .htmlElement(d => {
        const el = document.createElement('div');
        el.className = 'chamada ' + d.classe;
        el.innerHTML = d.html;
        return el;
      })
      .htmlAltitude(0.02)
      .htmlTransitionDuration(0);

    aplicarTemaGlobo();
    globo.pointOfView({ lat: 30, lng: -30, altitude: 2.6 }, 0);
    const c = globo.controls();
    c.autoRotate = st.girar; c.autoRotateSpeed = 0.35; c.enableDamping = true;
    c.addEventListener('start', () => { c.autoRotate = false; });
    c.addEventListener('end', () => { setTimeout(() => { c.autoRotate = st.girar; }, 4000); });

    new ResizeObserver(() => globo.width(elGlobo.clientWidth).height(elGlobo.clientHeight)).observe(elGlobo);
  }

  function alturaPais(f) {
    if (st.modo !== 'paises') return 0.004;
    const d = st.porPais.get(f._chave);
    if (!d || !contar(d)) return 0.004;
    return 0.006 + 0.16 * Math.log1p(contar(d)) / Math.log1p(st.max);
  }

  function aplicarTemaGlobo() {
    if (!globo) return;
    const claro = document.documentElement.dataset.theme === 'light';
    globo.globeMaterial().color.set(css('--globo'));
    globo.globeMaterial().shininess = 4;
    globo.atmosphereColor(claro ? '#B9B5B0' : '#3A3937');
    globo.polygonsData(paises.slice());
  }

  // ------------------------------------------------------------------ camadas do globo
  let arcosFixos = [], arcosVivos = [], aneisVivos = [];

  function servidor() { return st.dados ? st.dados.server : { lat: 39.04, lon: -77.49 }; }

  function desenharCamadas() {
    if (!globo || !st.dados) return;
    const s = servidor();
    const lugares = st.dados.places.filter(p => contar(p) > 0);
    const maxL = Math.max(1, ...lugares.map(contar));
    const k = p => Math.log1p(contar(p)) / Math.log1p(maxL);

    arcosFixos = st.modo === 'fluxo' ? lugares.slice(0, 60).map(p => {
      const cor = css(tipoDominante(p) === 'ssh' ? '--ssh' : '--http');
      return {
        startLat: p.lat, startLng: p.lon, endLat: s.lat, endLng: s.lon,
        cor: [misturar(cor, cor, 0, 0.05), misturar(cor, cor, 0, 0.35 + 0.5 * k(p))],
        larg: 0.15 + 0.55 * k(p), tam: 0.35, gap: 1.4, ini: Math.random() * 2, dur: 5200 - 3000 * k(p),
      };
    }) : [];
    globo.arcsData(arcosFixos.concat(arcosVivos));

    globo.pointsData(st.modo === 'fluxo' ? lugares.slice(0, 200).map(p => ({
      lat: p.lat, lng: p.lon, raio: 0.18 + 0.55 * k(p), ssh: p.ssh, http: p.http, cidade: p.city, pais: p.country, code: p.code,
      cor: css(tipoDominante(p) === 'ssh' ? '--ssh' : '--http'),
    })) : []);

    const top = lugares.slice(0, 5).map(p => ({
      lat: p.lat, lng: p.lon, classe: tipoDominante(p),
      html: `<span>${p.code || '??'}</span><b>${fmtK(contar(p))}</b>`,
    }));
    top.push({ lat: s.lat, lng: s.lon, classe: 'servidor', html: '<span>Servidor</span>' });
    globo.htmlElementsData(top);

    globo.ringsData([{ lat: s.lat, lng: s.lon, servidor: true, raio: 4.5, vel: 2.2, periodo: 1300 }].concat(aneisVivos));
    globo.polygonsData(paises.slice());
    globo.polygonAltitude(alturaPais);
  }

  // um evento novo: arco "voando" até o servidor + anel na origem
  function lancar(e, atraso) {
    if (!globo || e.lat == null || e.lon == null) return;
    if (st.filtro !== 'tudo' && st.filtro !== e.type) return;
    if (st.modo !== 'fluxo' || reduzido) return;
    const s = servidor();
    const cor = css(e.type === 'ssh' ? '--ssh' : '--http');
    setTimeout(() => {
      const arco = { startLat: e.lat, startLng: e.lon, endLat: s.lat, endLng: s.lon,
        cor: [misturar(cor, cor, 0, 0.2), '#FFFFFF'], larg: 0.9, tam: 0.45, gap: 4, ini: 1, dur: 1700 };
      const anel = { lat: e.lat, lng: e.lon, cor, raio: 2.2, vel: 2, periodo: 9999 };
      arcosVivos.push(arco); aneisVivos.push(anel);
      if (arcosVivos.length > 70) arcosVivos.shift();
      globo.arcsData(arcosFixos.concat(arcosVivos));
      globo.ringsData([{ lat: s.lat, lng: s.lon, servidor: true, raio: 4.5, vel: 2.2, periodo: 1300 }].concat(aneisVivos));
      setTimeout(() => {
        arcosVivos = arcosVivos.filter(a => a !== arco);
        aneisVivos = aneisVivos.filter(a => a !== anel);
        globo.arcsData(arcosFixos.concat(arcosVivos));
        globo.ringsData([{ lat: s.lat, lng: s.lon, servidor: true, raio: 4.5, vel: 2.2, periodo: 1300 }].concat(aneisVivos));
      }, 1800);
    }, atraso);
  }

  // ------------------------------------------------------------------ painéis
  function renderPlacar(d) {
    const t = d.totals, total = t.ssh + t.http || 1;
    const ps = t.ssh / total * 100, ph = 100 - ps;
    $('#barra-ssh').style.width = Math.min(92, Math.max(8, ps)) + '%';
    $('#barra-http').style.width = Math.min(92, Math.max(8, ph)) + '%';
    rolar($('#pct-ssh'), ps, 1); rolar($('#pct-http'), ph, 1);
    $('#total-ssh').textContent = fmt(t.ssh) + ' tentativas';
    $('#total-http').textContent = fmt(t.http) + ' acessos';
    const lider = ps >= 50 ? '<span class="vermelho">SSH</span> domina o tráfego' : '<span class="azul">HTTP</span> lidera o tráfego';
    $('#manchete').innerHTML = lider;
    $('#placar-paises').textContent = `${fmt(t.countries)} países · ${fmt(t.places)} cidades · últimas ${rotuloPeriodo()}`;
    $('#barra').setAttribute('aria-label', `SSH ${nf1.format(ps)}%, HTTP ${nf1.format(ph)}%`);
    $('#leg-ssh').textContent = fmt(t.ssh); $('#leg-http').textContent = fmt(t.http);
    $('#rodape-total').textContent = `${fmt(total)} eventos nas últimas ${rotuloPeriodo()}`;
  }

  const rotuloPeriodo = () => ({ '1h': '1 hora', '6h': '6 horas', '24h': '24 horas', '7d': '7 dias' })[st.periodo];

  function renderEsquerda(d) {
    rolar($('#ritmo-ssh'), d.rate_per_min.ssh, 1);
    rolar($('#ritmo-http'), d.rate_per_min.http, 1);
    rolar($('#num-paises'), d.totals.countries);
    $('#frase-paises').textContent = `nas últimas ${rotuloPeriodo()}, ${fmt(d.totals.places)} cidades diferentes`;

    // gráfico de linhas
    const svg = $('#grafico');
    const sr = d.series, W = 300, H = 140;
    const tempos = [...new Set(sr.ssh.concat(sr.http).map(p => p[0]))].sort((a, b) => a - b);
    const mapa = k => new Map(sr[k].map(p => [p[0], p[1]]));
    const ms = mapa('ssh'), mh = mapa('http');
    const mostrar = { ssh: st.filtro !== 'http', http: st.filtro !== 'ssh' };
    const max = Math.max(1, ...tempos.map(t => Math.max(mostrar.ssh ? ms.get(t) || 0 : 0, mostrar.http ? mh.get(t) || 0 : 0)));
    const x = i => tempos.length < 2 ? W : i / (tempos.length - 1) * W;
    const y = v => H - 6 - v / max * (H - 18);
    const linha = m => tempos.map((t, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(m.get(t) || 0).toFixed(1)}`).join('');
    let out = [0, .5, 1].map(f => `<line class="grade-l" x1="0" x2="${W}" y1="${y(max * f)}" y2="${y(max * f)}"/>`).join('');
    out += [1, .5].map(f => `<text x="0" y="${y(max * f) - 3}" fill="currentColor" stroke="none" font-size="9" opacity=".55">${fmtK(max * f)}</text>`).join('');
    ['ssh', 'http'].forEach(k => {
      if (!mostrar[k] || !tempos.length) return;
      const m = k === 'ssh' ? ms : mh, l = linha(m);
      out += `<path class="area-${k}" d="${l}L${W},${H}L0,${H}Z"/><path class="linha-${k} desenhar" d="${l}"/>`;
      const ult = m.get(tempos[tempos.length - 1]) || 0;
      out += `<circle cx="${W}" cy="${y(ult)}" r="3.5" fill="${css(k === 'ssh' ? '--ssh' : '--http')}" stroke="none"/>`;
    });
    svg.innerHTML = out;
    $('#eixo-ini').textContent = tempos.length ? hora(tempos[0] * 1000) : '–';

    // status HTTP
    const s = d.status;
    $('#status').innerHTML = ['2xx', '3xx', '4xx', '5xx'].map(c =>
      `<div><small>${c}</small><b class="${c === '5xx' && s[c] ? 'vermelho' : ''}">${fmtK(s[c] || 0)}</b></div>`).join('');

    // ranking de países
    const top = d.countries.filter(c => contar(c) > 0).slice(0, 6);
    const maxC = Math.max(1, ...top.map(contar));
    $('#ranking').innerHTML = top.map(c => {
      const ws = (st.filtro === 'http' ? 0 : c.ssh) / maxC * 100, wh = (st.filtro === 'ssh' ? 0 : c.http) / maxC * 100;
      return `<li title="${nomePais(c.code, c.name)}"><span class="mini">${c.code !== '??' ? c.code : '–'}</span>
        <span class="trilha"><i class="s" style="width:${ws}%"></i><i class="h" style="width:${wh}%"></i></span>
        <b>${fmtK(contar(c))}</b></li>`;
    }).join('') || '<li class="vazio">Nada no período</li>';
  }

  function renderRegioes(d) {
    const tot = Math.max(1, d.continents.reduce((a, c) => a + contar(c), 0));
    $('#regioes').innerHTML = d.continents.filter(c => contar(c) > 0).map((c, i) => {
      const n = contar(c), p = n / tot, circ = 2 * Math.PI * 12;
      const ps = c.ssh + c.http ? c.ssh / (c.ssh + c.http) * 100 : 0;
      return `<li style="animation-delay:${i * 60}ms">
        <svg class="anel" viewBox="0 0 30 30"><circle class="fundo-anel" cx="15" cy="15" r="12"/>
          <circle class="frente" cx="15" cy="15" r="12" stroke-dasharray="${circ}" stroke-dashoffset="${circ * (1 - p)}" transform="rotate(-90 15 15)"/>
          <text x="15" y="15">${Math.round(p * 100)}%</text></svg>
        <span>${CONTINENTES[c.code] || 'Desconhecido'}</span>
        <span class="mix"><span class="t"><i class="s" style="width:${ps}%"></i><i class="h" style="width:${100 - ps}%"></i></span>
          <small><span>${Math.round(ps)}% SSH</span><span>${Math.round(100 - ps)}% HTTP</span></small></span>
        <span class="num">${fmtK(n)}<small>eventos</small></span></li>`;
    }).join('') || '<li class="vazio">Sem dados</li>';
  }

  const ICONE = {
    ssh: '<svg viewBox="0 0 24 24"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>',
    http: '<svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  };

  function textoEvento(e) {
    const onde = [e.city, nomePais(e.code, e.country)].filter(Boolean).join(', ') || 'origem desconhecida';
    return e.type === 'ssh' ? `<b>Tentativa SSH</b> de ${onde}` : `<b>${e.method || 'HTTP'} · ${e.status || '?'}</b> de ${onde}`;
  }

  let chipPreenchido = false;
  function renderFeed(novos) {
    const ul = $('#feed');
    const lista = st.eventos.filter(e => st.filtro === 'tudo' || e.type === st.filtro).slice(0, 16);
    const marcados = new Set(novos.map(e => e.t + e.type));
    ul.innerHTML = lista.map(e => `<li class="${marcados.has(e.t + e.type) ? 'novo' : ''}">
      <time>${hora(e.t, true)}</time>
      <span class="circulo ${e.type}">${ICONE[e.type]}</span>
      <p>${textoEvento(e)}</p></li>`).join('') || '<li class="vazio">Nenhum evento nos últimos 30 min.</li>';
    const ult = lista[0];
    if (ult && (novos.length || !chipPreenchido)) {
      chipPreenchido = true;
      const chip = $('#chip');
      $('#chip-cod').textContent = ult.code || '??';
      $('#chip-cod').className = 'mini ' + ult.type;
      $('#chip-texto').innerHTML = `${textoEvento(ult).replace(/<\/?b>/g, '')} · ${hora(ult.t)}`;
      chip.classList.remove('novo'); void chip.offsetWidth; chip.classList.add('novo');
    }
  }

  // ------------------------------------------------------------------ linha do tempo
  let baldes = [];
  function renderLinha(d) {
    const ms = new Map(d.series.ssh.map(p => [p[0], p[1]]));
    const mh = new Map(d.series.http.map(p => [p[0], p[1]]));
    const ini = Math.floor((d.updated - ({ '1h': 3600, '6h': 21600, '24h': 86400, '7d': 604800 })[st.periodo]) / d.step) * d.step;
    baldes = [];
    for (let t = ini; t <= d.updated; t += d.step) baldes.push({ t, ssh: ms.get(t) || 0, http: mh.get(t) || 0 });
    const max = Math.max(1, ...baldes.map(contar));
    $('#barras').innerHTML = baldes.map((b, i) => {
      const hs = (st.filtro === 'http' ? 0 : b.ssh) / max * 100, hh = (st.filtro === 'ssh' ? 0 : b.http) / max * 100;
      return `<i data-i="${i}"><b class="s" style="height:${hs}%"></b><b class="h" style="height:${hh}%"></b></i>`;
    }).join('');
    posicionarCursor();
  }

  function posicionarCursor() {
    const cur = $('#cursor'), n = baldes.length;
    const i = st.aoVivo || st.cursor == null ? n - 1 : st.cursor;
    cur.style.left = n > 1 ? `calc(${i / (n - 1) * 100}% - 1px)` : '100%';
    $$('#barras i').forEach((el, j) => el.classList.toggle('fora', !st.aoVivo && j > i));
    $('#trilho').setAttribute('aria-valuenow', n > 1 ? Math.round(i / (n - 1) * 100) : 100);
    $('#btn-vivo').classList.toggle('ativo', st.aoVivo);
    if (!st.aoVivo && baldes[i]) {
      const b = baldes[i];
      $('#relogio').textContent = hora(b.t * 1000);
      $('#chip-cod').textContent = '⏱'; $('#chip-cod').className = 'mini';
      $('#chip-texto').textContent = `${new Date(b.t * 1000).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })} · ${fmt(b.ssh)} SSH · ${fmt(b.http)} HTTP`;
    }
  }

  function arrastar(ev) {
    const r = $('#trilho').getBoundingClientRect();
    const p = Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width));
    st.cursor = Math.round(p * (baldes.length - 1));
    st.aoVivo = st.cursor >= baldes.length - 1;
    posicionarCursor();
  }
  const trilho = $('#trilho');
  trilho.addEventListener('pointerdown', ev => { trilho.setPointerCapture(ev.pointerId); arrastar(ev); });
  trilho.addEventListener('pointermove', ev => { if (trilho.hasPointerCapture(ev.pointerId)) arrastar(ev); });
  trilho.addEventListener('keydown', ev => {
    if (!['ArrowLeft', 'ArrowRight', 'End'].includes(ev.key)) return;
    ev.preventDefault();
    const n = baldes.length - 1;
    if (ev.key === 'End') { st.aoVivo = true; st.cursor = null; }
    else {
      st.cursor = Math.min(n, Math.max(0, (st.cursor ?? n) + (ev.key === 'ArrowLeft' ? -1 : 1)));
      st.aoVivo = st.cursor >= n;
    }
    posicionarCursor();
  });
  $('#btn-vivo').addEventListener('click', () => { st.aoVivo = true; st.cursor = null; posicionarCursor(); });

  // ------------------------------------------------------------------ dados
  async function buscar(url) {
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    return r.json();
  }

  function indexarPaises(d) {
    st.porPais = new Map(d.countries.map(c => [chaveNome(c.name), c]));
    st.max = Math.max(1, ...d.countries.map(contar));
  }

  function renderTudo() {
    const d = st.dados;
    if (!d) return;
    indexarPaises(d);
    renderPlacar(d); renderEsquerda(d); renderRegioes(d); renderLinha(d);
    desenharCamadas();
    $('#servidor-cidade').textContent = d.server.city;
  }

  let progressoAnim = null;
  function reiniciarProgresso() {
    const el = $('#progresso');
    if (progressoAnim) progressoAnim.cancel();
    progressoAnim = el.animate([{ transform: 'scaleX(1)' }, { transform: 'scaleX(0)' }], { duration: INTERVALO_TRAFEGO, easing: 'linear', fill: 'forwards' });
  }

  async function atualizarTrafego() {
    try {
      st.dados = await buscar(`${API}/trafego?range=${st.periodo}`);
      renderTudo();
      $('#placar-atualizado').textContent = 'ao vivo';
      $('#placar-atualizado').className = 'verde';
    } catch {
      $('#placar-atualizado').textContent = 'sem conexão com os dados, tentando de novo…';
      $('#placar-atualizado').className = 'vermelho';
    }
    reiniciarProgresso();
  }

  async function atualizarEventos(primeira) {
    try {
      const r = await buscar(`${API}/eventos?limit=80`);
      const novos = r.events.filter(e => e.t > st.ultimoT);
      if (r.events.length) st.ultimoT = Math.max(st.ultimoT, r.events[0].t);
      st.eventos = r.events;
      const vivos = primeira ? novos.slice(0, 12) : novos;
      // espalha os novos ao longo do próximo intervalo, na ordem em que chegaram
      vivos.slice().reverse().forEach((e, i, arr) => lancar(e, primeira ? i * 250 : i * (INTERVALO_EVENTOS / Math.max(1, arr.length))));
      renderFeed(primeira ? [] : novos);
    } catch { /* tenta de novo no próximo ciclo */ }
  }

  // ------------------------------------------------------------------ controles
  $$('[data-filtro]').forEach(b => b.addEventListener('click', () => {
    st.filtro = b.dataset.filtro;
    $$('[data-filtro]').forEach(x => { x.classList.toggle('ativo', x === b); x.setAttribute('aria-selected', x === b); });
    renderTudo(); renderFeed([]);
  }));
  $$('[data-periodo]').forEach(b => b.addEventListener('click', () => {
    st.periodo = b.dataset.periodo; st.aoVivo = true; st.cursor = null;
    $$('[data-periodo]').forEach(x => x.classList.toggle('ativo', x === b));
    atualizarTrafego();
  }));
  $$('[data-modo]').forEach(b => b.addEventListener('click', () => {
    st.modo = b.dataset.modo;
    $$('[data-modo]').forEach(x => x.classList.toggle('ativo', x === b));
    arcosVivos = []; aneisVivos = [];
    desenharCamadas();
  }));
  $('#btn-girar').addEventListener('click', ev => {
    st.girar = !st.girar;
    ev.currentTarget.setAttribute('aria-pressed', st.girar);
    ev.currentTarget.lastChild.textContent = st.girar ? ' Girando' : ' Parado';
    if (globo) globo.controls().autoRotate = st.girar;
  });
  $('#zoom-mais').addEventListener('click', () => { const p = globo.pointOfView(); globo.pointOfView({ altitude: Math.max(0.6, p.altitude * 0.75) }, 500); });
  $('#zoom-menos').addEventListener('click', () => { const p = globo.pointOfView(); globo.pointOfView({ altitude: Math.min(4, p.altitude * 1.33) }, 500); });
  $('#btn-tema').addEventListener('click', () => {
    const novo = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', novo);
    document.querySelector('meta[name="theme-color"]').content = novo === 'light' ? '#F1F0EE' : '#0B0B0A';
    try { localStorage.setItem('radar-tema', novo); } catch {}
    aplicarTemaGlobo(); desenharCamadas();
  });
  $('#btn-tela').addEventListener('click', () => {
    if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen().catch(() => {});
  });

  setInterval(() => { if (st.aoVivo) $('#relogio').textContent = new Date().toLocaleTimeString('pt-BR'); }, 1000);

  // ------------------------------------------------------------------ partida
  (async function () {
    try {
      const topo = await buscar('data/countries-110m.json');
      iniciarGlobo(topo);
    } catch {
      elGlobo.innerHTML = '<p class="vazio" style="padding:40px;text-align:center">Não foi possível carregar o globo.</p>';
    }
    await atualizarTrafego();
    await atualizarEventos(true);
    setInterval(atualizarTrafego, INTERVALO_TRAFEGO);
    setInterval(() => atualizarEventos(false), INTERVALO_EVENTOS);
  })();
})();
