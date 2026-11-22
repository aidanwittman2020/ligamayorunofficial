#!/usr/bin/env python3
"""Genera páginas estáticas de cada partido y de cada semana a partir del Google Sheet.

Uso:  python3 build/generate.py            (descarga la hoja publicada)
      python3 build/generate.py --local DIR (lee juegos.csv, anotaciones.csv, canales.csv de DIR)

Escribe en site/juegos/... y actualiza site/sitemap.xml. Si la hoja no se puede leer,
no toca nada (la página sigue como estaba).
"""
import csv, io, json, os, re, sys, html, unicodedata, urllib.request, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
URL = 'https://ligamayorunofficial.com'
YEAR = 2026
PUB = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQNVclYf7g5WHDSejO-E_1xVXBF-KC__RWAbeSLafpfFK-5fxjCE2JegKDDBVnqalEEV97cBnF1PMzU/pub?gid={}&single=true&output=csv'
GID = {'juegos': 1243915347, 'anotaciones': 1258472465, 'canales': 1868069815, 'ntabla': 1541467341, 'njuegos': 910175980,
       'lideres': 1908116186, 'estrellas': 1355832789, 'tstats': 1066629721}
e = html.escape

# ---------------------------------------------------------------- datos base del sitio
MAIN = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
TEAMS = {k: {'n': n, 'f': f, 'g': g} for k, n, f, g in re.findall(r"(\w{3}):\{n:'([^']*)',f:'([^']*)',g:'([^']*)'\}", MAIN)}
SHORT = dict(re.findall(r"(\w{3}):'([^']*)'", re.search(r'const SHORT=\{(.*?)\};', MAIN).group(1)))
SLUG = json.loads(re.search(r'const SLUG=(\{.*?\});', MAIN).group(1))
INFO = json.loads(re.search(r'const INFO=(\{.*?\});\n', MAIN, re.S).group(1))
CAN = {k: {'tv': tv, 'lk': ''} for k, tv in re.findall(r"(\w{3}):\{tv:'([^']*)'\}", re.search(r'let CAN=\{(.*?)\};', MAIN).group(1))}
PO_NAME = {'CF': 'Cuartos de final', 'SF': 'Semifinal', 'F': 'Final', 'P': 'Juego pendiente'}
WSLUG = {'CF': 'cuartos-de-final', 'SF': 'semifinales', 'F': 'final', 'P': 'pendientes'}
MESES = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}
DIAS = {'lun': 'lunes', 'mar': 'martes', 'mie': 'miércoles', 'mié': 'miércoles', 'jue': 'jueves', 'vie': 'viernes', 'sab': 'sábado', 'sáb': 'sábado', 'dom': 'domingo'}

# Plantilla: estilos y encabezado de una página de equipo (ya trae el tema del sitio)
TPL = open(os.path.join(SITE, 'equipos', 'borregos-monterrey', 'index.html'), encoding='utf-8').read()
HEAD_COMMON = TPL[:TPL.find('<title>')]
FONTS = re.search(r'(<link rel="preconnect".*?)(?=<style>)', TPL, re.S)
FONTS = FONTS.group(1) if FONTS else ''
STYLE = re.search(r'<style>.*?</style>', TPL, re.S).group(0)
HEADER = re.search(r'<header class="top">.*?</header>', TPL, re.S).group(0)
FOOT = re.search(r'<footer.*?</footer>', TPL, re.S)
FOOT = FOOT.group(0) if FOOT else ''

EXTRA_CSS = '''<style>
.gm-top{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:10px;background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:16px 12px;margin-top:6px}
.gm-t{display:grid;justify-items:center;gap:6px;text-align:center;text-decoration:none;color:inherit}
.gm-t img{width:64px;height:64px;image-rendering:pixelated}
.gm-t b{font-family:var(--display);font-weight:700;font-size:20px;line-height:1.05;text-transform:uppercase}
.gm-t small{font-size:12px;color:var(--muted)}
.gm-t.lose{opacity:.55}
.gm-sc{font-family:var(--display);font-weight:800;font-size:46px;line-height:1;display:flex;gap:10px;align-items:center;font-variant-numeric:tabular-nums}
.gm-sc span.d{font-size:26px;color:var(--muted)}
.gm-st{grid-column:1/-1;text-align:center;font-family:var(--display);font-weight:700;letter-spacing:.06em;text-transform:uppercase;font-size:14px;color:var(--muted)}
.gm-st.live{color:#E5383B}
.gm-h1{font-family:var(--display);font-weight:800;font-size:34px;line-height:1.02;text-transform:uppercase;margin:4px 0 2px;text-wrap:balance}
.gm-meta{color:var(--muted);font-size:14px;margin:0 0 12px}
.wlist{display:grid;gap:8px}
.wg{display:grid;grid-template-columns:1fr auto;gap:4px 10px;align-items:center;background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:10px 12px;text-decoration:none;color:inherit}
.wg:hover{border-color:var(--accent)}
.wg .r{display:flex;align-items:center;gap:8px;font-weight:600}
.wg .r img{width:26px;height:26px;image-rendering:pixelated}
.wg .r.l{opacity:.55}
.wg .s{font-family:var(--display);font-weight:800;font-size:22px;text-align:right;font-variant-numeric:tabular-nums}
.wg .m{grid-column:1/-1;font-size:12px;color:var(--muted);font-family:var(--display);letter-spacing:.05em;text-transform:uppercase}
.wnav{display:flex;flex-wrap:wrap;gap:6px;margin:14px 0}
.wnav a{font-family:var(--display);font-weight:700;font-size:14px;letter-spacing:.04em;text-transform:uppercase;text-decoration:none;padding:6px 10px;border:1px solid var(--line);border-radius:4px;color:var(--ink);background:var(--surface)}
.wnav a.on{background:var(--accent);border-color:var(--accent);color:#fff}
.qs{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--line);border-radius:4px;overflow:hidden;font-variant-numeric:tabular-nums}
.qs th,.qs td{padding:8px 6px;text-align:center;border-bottom:1px solid var(--line);font-size:14px}
.qs th{font-family:var(--display);font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);font-weight:700}
.qs td:first-child,.qs th:first-child{text-align:left;padding-left:12px}
.qs tr:last-child td{border-bottom:0}.qs .tot{font-weight:700}
.plays{display:grid;gap:6px}
.plays .qh{font-family:var(--display);font-weight:700;font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-top:6px}
.plays .pl{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:8px 10px;font-size:14px}
.plays .pl img{width:26px;height:26px;image-rendering:pixelated}
.plays .pl b{display:block;font-size:13px}
.plays .rs{font-family:var(--display);font-weight:800;font-size:18px}
.wb2{display:flex;justify-content:space-between;align-items:center;gap:10px;background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:4px;padding:12px;margin-top:12px}
.wb2 span{display:block;font-family:var(--display);font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.wb2 a{background:var(--accent);color:#fff;text-decoration:none;font-family:var(--display);font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:9px 14px;border-radius:4px;white-space:nowrap}
.more{display:grid;gap:6px;margin-top:8px}
.more a{color:var(--ink)}
</style>'''


def norm(x):
    return unicodedata.normalize('NFD', str(x or '').strip().lower()).encode('ascii', 'ignore').decode()


def fetch(name, local):
    if local:
        p = os.path.join(local, name + '.csv')
        return open(p, encoding='utf-8').read() if os.path.exists(p) else ''
    req = urllib.request.Request(PUB.format(GID[name]), headers={'User-Agent': 'ligamayorunofficial-build'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8')


def rows_of(text):
    R = [r for r in csv.reader(io.StringIO(text)) if any(x.strip() for x in r)]
    if not R:
        return [], {}
    H = [norm(h) for h in R[0]]
    return R[1:], {h: i for i, h in enumerate(H)}


def num(x):
    x = str(x or '').strip()
    try:
        return int(float(x))
    except ValueError:
        return None


def parse_date(d, t, home):
    m = re.search(r'(\d{1,2})\s+([a-záéíóú]{3})', norm(d))
    if not m or m.group(2) not in MESES:
        return None
    hh, mm = 12, 0
    tm = re.match(r'(\d{1,2}):(\d{2})', str(t).strip())
    if tm:
        hh, mm = int(tm.group(1)), int(tm.group(2))
    dt = datetime.datetime(YEAR, MESES[m.group(2)], int(m.group(1)), hh, mm)
    off = '-06:00'
    if home == 'CET':  # Baja California
        off = '-07:00' if dt < datetime.datetime(YEAR, 11, 1, 2) else '-08:00'
    return dt.strftime('%Y-%m-%dT%H:%M:00') + off


def long_date(d):
    m = re.match(r'\s*([a-záéíóú]{3})\w*\s+(\d{1,2})\s+([a-záéíóú]{3})', norm(d))
    if not m:
        return d
    mes = ['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'][MESES.get(m.group(3), 0)]
    return f"{DIAS.get(m.group(1), m.group(1)).capitalize()} {int(m.group(2))} de {mes}"


def wk_label(w):
    return PO_NAME.get(w) or f'Semana {w}'


def crumb_wl(w):
    return {'P': 'Pendientes', 'CF': 'Cuartos', 'SF': 'Semifinales', 'F': 'Final'}.get(w, f'Semana {w}')


def more_wl(w):
    return {'P': 'Todos los juegos pendientes', 'CF': 'Todos los cuartos de final', 'SF': 'Todas las semifinales', 'F': 'La final'}.get(w, f'Todos los partidos de la semana {w}')


def wk_slug(w):
    return WSLUG.get(w) or f'semana-{w}'


def game_path(g):
    return f"/juegos/{YEAR}/{wk_slug(g['w'])}/{SLUG[g['a']]}-vs-{SLUG[g['h']]}/"


def badge(k, size=64):
    return f'<img src="/img/{k}.png" alt="Escudo de {e(TEAMS[k]["n"])}" width="{size}" height="{size}">'


def crumbs(items):
    """items: [(name, path or None)] — el último es la página actual."""
    parts = []
    for i, (n, p) in enumerate(items):
        if p and i < len(items) - 1:
            parts.append(f'<a href="{p}">{e(n)}</a>')
        else:
            parts.append(f'<span class="cur" aria-current="page">{e(n)}</span>')
    nav = '<nav class="crumbs" aria-label="Ruta">' + '<span class="sep" aria-hidden="true">/</span>'.join(parts) + '</nav>'
    ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': URL + (p or '')} for i, (n, p) in enumerate(items) if p]}
    return nav, ld


def page(title, desc, path, body, ld_list, og_type='website'):
    lds = ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>\n' for x in ld_list)
    return f'''{HEAD_COMMON}<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{URL}{path}">
<meta name="theme-color" content="#111412">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="48x48" href="/icons/favicon-48.png">
<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">
<meta property="og:type" content="{og_type}"><meta property="og:locale" content="es_MX"><meta property="og:site_name" content="Liga Mayor Unofficial">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{URL}{path}"><meta property="og:image" content="{URL}/og.png">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{URL}/og.png">
{lds}{FONTS}{STYLE}
{EXTRA_CSS}
<style>@view-transition{{navigation:auto}}::view-transition-old(root),::view-transition-new(root){{animation-duration:.14s}}header.top{{view-transition-name:top}}</style><script type="speculationrules">{{"prerender":[{{"where":{{"and":[{{"href_matches":"/*"}},{{"not":{{"href_matches":"/*.json"}}}}]}},"eagerness":"moderate"}}]}}</script>
</head>
<body>
{HEADER}
<main class="wrap">
{body}
</main>
{FOOT}
<script>if("serviceWorker" in navigator)addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{{}}));</script>
</body></html>
'''


# ---------------------------------------------------------------- lectura de la hoja
def load(local):
    jr, jc = rows_of(fetch('juegos', local))
    need = ['semana', 'fecha', 'hora', 'visitante', 'pts visitante', 'pts local', 'local', 'estado']
    if not jr or any(n not in jc for n in need):
        raise SystemExit('No se pudo leer la pestaña Juegos; no se cambia nada.')
    v = lambda r, n: (r[jc[n]] if n in jc and jc[n] < len(r) else '').strip()
    G = []
    for r in jr:
        a, h = v(r, 'visitante').upper(), v(r, 'local').upper()
        if a not in TEAMS or h not in TEAMS:
            continue
        st = norm(v(r, 'estado'))
        A, H = num(v(r, 'pts visitante')), num(v(r, 'pts local'))
        fin = st == 'final' and A is not None and H is not None
        G.append({'w': v(r, 'semana').upper(), 'd': v(r, 'fecha'), 't': v(r, 'hora')[:5], 'a': a, 'h': h,
                  'as': A if fin else None, 'hs': H if fin else None, 'fin': fin, 'live': st == 'en vivo',
                  'det': v(r, 'detalle'), 'tv': v(r, 'transmision'), 'lk': v(r, 'link')})
    try:
        cr, cc = rows_of(fetch('canales', local))
        for r in cr:
            k = (r[cc.get('equipo', 0)] if cc.get('equipo', 0) < len(r) else '').strip().upper()
            if k in TEAMS and 'transmision' in cc:
                CAN[k] = {'tv': r[cc['transmision']].strip(), 'lk': r[cc['link']].strip() if 'link' in cc and cc['link'] < len(r) else ''}
    except Exception:
        pass
    PL = {}
    try:
        ar, ac = rows_of(fetch('anotaciones', local))
        av = lambda r, n: (r[ac[n]] if n in ac and ac[n] < len(r) else '').strip()
        for r in ar:
            t, k = av(r, 'equipo').upper(), norm(av(r, 'tipo'))
            if t not in TEAMS or not k:
                continue
            qs = av(r, 'cuarto').upper()
            q = 5 if qs in ('TE', 'OT') else num(qs)
            if not q or not 1 <= q <= 5:
                continue
            x = norm(av(r, 'extra'))
            pts = 6 if k.startswith('td') else 3 if k == 'fg' else 2 if k == 'safety' else 0
            pts += (1 if x == 'pat bueno' else 2 if x == '2 pts bueno' else 0) if k.startswith('td') else 0
            key = (av(r, 'semana').upper(), av(r, 'visitante').upper(), av(r, 'local').upper())
            PL.setdefault(key, []).append({'q': q, 't': t, 'k': k, 'j': av(r, 'jugador'), 'p': av(r, 'pase de'), 'y': av(r, 'yardas'), 'x': x, 'pts': pts})
    except Exception:
        pass
    return G, PL


def standings(G):
    S = {k: {'w': 0, 'l': 0} for k in TEAMS}
    for g in G:
        if g['fin'] and g['w'] not in ('CF', 'SF', 'F'):
            win, lose = (g['a'], g['h']) if g['as'] > g['hs'] else (g['h'], g['a'])
            S[win]['w'] += 1
            S[lose]['l'] += 1
    return S


def watch(g):
    d = CAN.get(g['h'], {})
    tv = g['tv'] or d.get('tv', '')
    lk = g['lk'] or ('' if g['tv'] else d.get('lk', ''))
    return tv, (lk if re.match(r'https?://', lk or '') else '')


def play_text(p):
    yd = f"{p['y']} yd" if p['y'] else ''
    J = e(p['j'])
    k = p['k']
    if k == 'td pase':
        return 'Touchdown · pase', (J or 'TD') + (f", pase{' de ' + yd if yd else ''} de {e(p['p'])}" if p['p'] else (f', pase de {yd}' if yd else ''))
    if k == 'td carrera':
        return 'Touchdown · carrera', (J or 'TD') + (f', carrera de {yd}' if yd else '')
    if k == 'td defensivo':
        return 'Touchdown · defensa', (J or 'TD defensivo') + (f', {yd}' if yd else '')
    if k == 'td regreso':
        return 'Touchdown · regreso', (J or 'TD') + (f', regreso de {yd}' if yd else '')
    if k == 'fg':
        return 'Gol de campo', (J or 'FG') + (f', {yd}' if yd else '')
    if k == 'safety':
        return 'Safety', J or 'Safety'
    return e(p['k']), J


def detail_html(g, P):
    if not P:
        return ''
    nQ = max(4, max(p['q'] for p in P))
    Q = {g['a']: [0] * (nQ + 1), g['h']: [0] * (nQ + 1)}
    for p in P:
        if p['t'] in Q:
            Q[p['t']][p['q']] += p['pts']
    tot = {k: (g['as'] if k == g['a'] else g['hs']) if g['fin'] else sum(Q[k]) for k in Q}
    cols = range(1, nQ + 1)
    row = lambda k: f'<tr><td>{e(SHORT.get(k, k))}</td>' + ''.join(f'<td>{Q[k][q]}</td>' for q in cols) + f'<td class="tot">{tot[k]}</td></tr>'
    h = '<h2 style="font-size:26px;margin-top:22px">Marcador por cuarto</h2><table class="qs"><thead><tr><th>Equipo</th>' + ''.join(f'<th>{"TE" if q == 5 else str(q) + "º"}</th>' for q in cols) + f'<th>Total</th></tr></thead><tbody>{row(g["a"])}{row(g["h"])}</tbody></table>'
    h += '<h2 style="font-size:26px;margin-top:22px">Anotaciones</h2><div class="plays">'
    ra = rh = 0
    last = 0
    qn = {1: '1er cuarto', 2: '2º cuarto', 3: '3er cuarto', 4: '4º cuarto', 5: 'Tiempo extra'}
    ex = {'pat bueno': 'Punto extra bueno', 'pat fallado': 'Punto extra fallado', '2 pts bueno': 'Conversión de 2 buena', '2 pts fallado': 'Conversión de 2 fallada'}
    for p in sorted(P, key=lambda p: p['q']):
        if p['q'] != last:
            h += f'<div class="qh">{qn[p["q"]]}</div>'
            last = p['q']
        if p['t'] == g['a']:
            ra += p['pts']
        else:
            rh += p['pts']
        tt, tx = play_text(p)
        xs = f' · {ex[p["x"]]}' if p['x'] in ex else ''
        h += f'<div class="pl">{badge(p["t"], 26)}<div><b>{e(SHORT.get(p["t"], p["t"]))} · {tt}</b>{tx}{xs}</div><div class="rs">{ra}-{rh}</div></div>'
    return h + '</div>'


LIVE_JS = '''<script>(function(){const U="__CSV__",A="__A__",H="__H__",W="__W__";
const csv=t=>{const R=[];let r=[],f="",q=false;for(let i=0;i<t.length;i++){const c=t[i];if(q){if(c=='"'){if(t[i+1]=='"'){f+='"';i++}else q=false}else f+=c}else if(c=='"')q=true;else if(c==","){r.push(f);f=""}else if(c=="\\n"||c=="\\r"){if(c=="\\r"&&t[i+1]=="\\n")i++;r.push(f);R.push(r);r=[];f=""}else f+=c}if(f!==""||r.length){r.push(f);R.push(r)}return R};
const nm=x=>String(x||"").trim().toLowerCase().normalize("NFD").replace(/[\\u0300-\\u036f]/g,"");
function go(){fetch(U+"&t="+Date.now(),{cache:"no-store"}).then(r=>r.ok?r.text():"").then(t=>{if(!t)return;const R=csv(t).filter(r=>r.some(x=>x.trim()));const Hd=R.shift().map(nm),c=n=>Hd.indexOf(n);
const r=R.find(r=>(r[c("semana")]||"").trim().toUpperCase()===W&&(r[c("visitante")]||"").trim().toUpperCase()===A&&(r[c("local")]||"").trim().toUpperCase()===H);if(!r)return;
const st=nm(r[c("estado")]),a=r[c("pts visitante")].trim(),h=r[c("pts local")].trim(),el=document.getElementById("gm-sc"),s=document.getElementById("gm-st");if(!el||a===""||h==="")return;
if(st==="en vivo"||st==="final"){el.innerHTML=a+'<span class="d">-</span>'+h;s.textContent=st==="final"?"Final":"● En vivo"+((r[c("detalle")]||"").trim()?" · "+r[c("detalle")].trim():"");s.className="gm-st"+(st==="final"?"":" live")}}).catch(()=>{})}
go();setInterval(go,60000)})();</script>'''


def game_page(g, G, PL, S):
    A, H = TEAMS[g['a']], TEAMS[g['h']]
    path = game_path(g)
    wl = wk_label(g['w'])
    I = INFO.get(g['h'])
    stadium = I[1] if I else ''
    city = I[0] if I else ''
    tv, lk = watch(g)
    ld_date = parse_date(g['d'], g['t'], g['h'])
    name = f"{A['n']} vs {H['n']}"
    rec = lambda k: f"{S[k]['w']}-{S[k]['l']}"
    if g['fin']:
        res = f"{g['as']}-{g['hs']}"
        title = f"{A['n']} {g['as']}-{g['hs']} {H['n']}: resultado {wl} · Liga Mayor ONEFA {YEAR}"
        win = A['n'] if g['as'] > g['hs'] else H['n']
        desc = f"Resultado final: {A['n']} {g['as']}, {H['n']} {g['hs']}. Ganó {win}. {wl} de la Liga Mayor ONEFA {YEAR} (14 Grandes), {long_date(g['d']).lower()} en {stadium or 'casa de ' + H['n']}."
        status = 'Final'
    else:
        title = f"{A['n']} vs {H['n']}: horario y dónde ver · {wl} Liga Mayor ONEFA {YEAR}"
        desc = f"{A['n']} visita a {H['n']} el {long_date(g['d']).lower()}{' a las ' + g['t'] + ' h' if g['t'] else ''}{' en ' + stadium if stadium else ''}. {('Transmisión: ' + tv + '. ') if tv else ''}{wl} de la Liga Mayor ONEFA {YEAR}, 14 Grandes."
        status = '● En vivo' if g['live'] else (f"{long_date(g['d'])} · {g['t']} h" if g['t'] else long_date(g['d']))
    aL = g['fin'] and g['as'] < g['hs']
    hL = g['fin'] and g['hs'] < g['as']
    team = lambda k, T, lose, lbl: f'<a class="gm-t{" lose" if lose else ""}" href="/equipos/{SLUG[k]}/">{badge(k)}<b>{e(SHORT.get(k, T["n"]))}</b><small>{lbl} · {rec(k)}</small></a>'
    sc = f'<div class="gm-sc" id="gm-sc"{"" if g["fin"] else " hidden"}>{g["as"] if g["fin"] else ""}<span class="d">-</span>{g["hs"] if g["fin"] else ""}</div>'
    if not g['fin']:
        sc = '<div class="gm-sc" id="gm-sc"><span class="d">VS</span></div>'
    nav, bld = crumbs([('Inicio', '/'), ('14 Grandes', '/#tabla'), (crumb_wl(g['w']), f'/juegos/{YEAR}/{wk_slug(g["w"])}/'), (f"{SHORT.get(g['a'])} vs {SHORT.get(g['h'])}", path)])
    body = nav
    body += f'<h1 class="gm-h1">{e(A["n"])} vs {e(H["n"])}</h1>'
    body += f'<p class="gm-meta">Liga Mayor ONEFA {YEAR} · 14 Grandes · {e(wl)}{(" · " + e(g["det"])) if g["det"] and not g["live"] else ""}</p>'
    body += f'<div class="gm-top">{team(g["a"], A, aL, "Visitante")}{sc}{team(g["h"], H, hL, "Local")}<div class="gm-st{" live" if g["live"] else ""}" id="gm-st">{e(status)}</div></div>'
    if tv:
        lbl = 'Ver transmisión' if g['fin'] else 'Ver partido'
        body += f'<div class="wb2"><div><span>{"Se transmitió por" if g["fin"] else "Dónde ver"}</span><b>{e(tv)}</b></div>{f"<a href=\"{e(lk)}\" target=\"_blank\" rel=\"noopener\">{lbl} ▶</a>" if lk else ""}</div>'
    facts = f'<div><dt>Fecha</dt><dd>{e(long_date(g["d"]))}{" · " + e(g["t"]) + " h" if g["t"] else ""}</dd></div>'
    if stadium:
        facts += f'<div><dt>Estadio</dt><dd>{e(stadium)}</dd></div><div><dt>Sede</dt><dd>{e(city)}</dd></div>'
    body += f'<h2 style="font-size:26px;margin-top:22px">El partido</h2><div class="card"><dl class="facts">{facts}</dl></div>'
    body += detail_html(g, PL.get((g['w'], g['a'], g['h']), []))
    if g['fin']:
        body += f'<p class="sub" style="margin-top:14px">{e(A["n"])} ({rec(g["a"])}) y {e(H["n"])} ({rec(g["h"])}) en la temporada {YEAR} de la Conferencia de los 14 Grandes. <a href="/#tabla">Ver la tabla de posiciones</a> y <a href="/#playoffs">la carrera por los playoffs</a>.</p>'
    body += f'<h2 style="font-size:26px;margin-top:22px">Más</h2><div class="more"><a href="/juegos/{YEAR}/{wk_slug(g["w"])}/">{e(more_wl(g['w']))} →</a><a href="/equipos/{SLUG[g["a"]]}/">Calendario de {e(A["n"])} →</a><a href="/equipos/{SLUG[g["h"]]}/">Calendario de {e(H["n"])} →</a><a href="/#tabla">Tabla de posiciones de la Liga Mayor {YEAR} →</a></div>'
    body += LIVE_JS.replace('__CSV__', PUB.format(GID['juegos'])).replace('__A__', g['a']).replace('__H__', g['h']).replace('__W__', g['w']) if not g['fin'] else ''
    ev = {'@context': 'https://schema.org', '@type': 'SportsEvent', 'name': f"{name} · Liga Mayor ONEFA {YEAR}", 'sport': 'Fútbol americano',
          'description': desc, 'url': URL + path,
          'eventStatus': 'https://schema.org/EventScheduled', 'eventAttendanceMode': 'https://schema.org/OfflineEventAttendanceMode',
          'homeTeam': {'@type': 'SportsTeam', 'name': H['n'], 'url': f"{URL}/equipos/{SLUG[g['h']]}/"},
          'awayTeam': {'@type': 'SportsTeam', 'name': A['n'], 'url': f"{URL}/equipos/{SLUG[g['a']]}/"},
          'competitor': [{'@type': 'SportsTeam', 'name': A['n']}, {'@type': 'SportsTeam', 'name': H['n']}],
          'organizer': {'@type': 'SportsOrganization', 'name': 'ONEFA', 'url': 'https://onefa.org'},
          'image': [f"{URL}/og.png"]}
    if ld_date:
        ev['startDate'] = ld_date
    if stadium:
        ev['location'] = {'@type': 'Place', 'name': stadium, 'address': {'@type': 'PostalAddress', 'addressLocality': city, 'addressCountry': 'MX'}}
    return path, page(title, desc, path, body, [ev, bld], 'article')


def week_card(g, S):
    A, H = g['a'], g['h']
    aL = g['fin'] and g['as'] < g['hs']
    hL = g['fin'] and g['hs'] < g['as']
    meta = 'Final' if g['fin'] else ('En vivo' if g['live'] else (f"{g['d']} · {g['t']} h" if g['t'] else g['d']))
    r = lambda k, sc, l: f'<div class="r{" l" if l else ""}">{badge(k, 26)}{e(TEAMS[k]["n"])}</div><div class="s">{sc if g["fin"] else ""}</div>'
    return f'<a class="wg" href="{game_path(g)}"><div class="m">{e(meta)}</div>{r(A, g["as"], aL)}{r(H, g["hs"], hL)}</a>'


def week_page(w, gs, weeks, S):
    wl = wk_label(w)
    path = f'/juegos/{YEAR}/{wk_slug(w)}/'
    done = [g for g in gs if g['fin']]
    if done and len(done) == len(gs):
        title = f"Resultados Liga Mayor ONEFA {YEAR} · {wl} (14 Grandes)"
        desc = f"Todos los resultados de la {wl.lower()} de la Liga Mayor ONEFA {YEAR}: " + '; '.join(f"{SHORT[g['a']]} {g['as']}-{g['hs']} {SHORT[g['h']]}" for g in gs) + '.'
    else:
        title = f"Liga Mayor ONEFA {YEAR} · {wl}: partidos, horarios, resultados y dónde ver"
        desc = f"Partidos de la {wl.lower()} de la Liga Mayor ONEFA {YEAR} (14 Grandes): " + '; '.join(f"{SHORT[g['a']]} vs {SHORT[g['h']]}" + (f" {g['as']}-{g['hs']}" if g['fin'] else f" ({g['d']} {g['t']})") for g in gs) + '.'
    nav, bld = crumbs([('Inicio', '/'), ('14 Grandes', '/#tabla'), (crumb_wl(w), path)])
    wn = '<nav class="wnav" aria-label="Semanas">' + ''.join(f'<a{" class=\"on\"" if x == w else ""} href="/juegos/{YEAR}/{wk_slug(x)}/">{"S" + x if x not in PO_NAME else {"P": "Pend.", "CF": "Cuartos", "SF": "Semis", "F": "Final"}[x]}</a>' for x in weeks) + '</nav>'
    body = nav + f'<h1 class="gm-h1">Liga Mayor {YEAR} · {e(wl)}</h1><p class="gm-meta">Resultados, horarios y dónde ver los partidos de la Conferencia de los 14 Grandes.</p>'
    body += wn + '<div class="wlist">' + ''.join(week_card(g, S) for g in gs) + '</div>'
    body += f'<p class="sub" style="margin-top:14px"><a href="/#tabla">Ver la tabla de posiciones →</a></p>'
    lst = {'@context': 'https://schema.org', '@type': 'ItemList', 'name': title, 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'url': URL + game_path(g), 'name': f"{TEAMS[g['a']]['n']} vs {TEAMS[g['h']]['n']}"} for i, g in enumerate(gs)]}
    return path, page(title, desc, path, body, [lst, bld])


def season_page(weeks, byw):
    path = f'/juegos/{YEAR}/'
    title = f"Calendario y resultados Liga Mayor ONEFA {YEAR} · 14 Grandes"
    desc = f"Calendario completo y resultados de la temporada {YEAR} de la Liga Mayor ONEFA, Conferencia de los 14 Grandes, semana por semana."
    nav, bld = crumbs([('Inicio', '/'), ('14 Grandes', '/#tabla'), (f'Calendario {YEAR}', path)])
    body = nav + f'<h1 class="gm-h1">Calendario y resultados {YEAR}</h1><p class="gm-meta">Liga Mayor ONEFA · Conferencia de los 14 Grandes</p>'
    for w in weeks:
        body += f'<h2 style="font-size:24px;margin-top:20px"><a href="/juegos/{YEAR}/{wk_slug(w)}/" style="color:inherit;text-decoration:none">{e(wk_label(w))} →</a></h2><div class="wlist">' + ''.join(week_card(g, None) for g in byw[w]) + '</div>'
    return path, page(title, desc, path, body, [bld])


def write(path, content):
    f = os.path.join(SITE, path.strip('/'), 'index.html')
    os.makedirs(os.path.dirname(f), exist_ok=True)
    old = open(f, encoding='utf-8').read() if os.path.exists(f) else None
    if old != content:
        open(f, 'w', encoding='utf-8').write(content)
        return True
    return False


def sitemap(paths):
    p = os.path.join(SITE, 'sitemap.xml')
    s = open(p, encoding='utf-8').read()
    keep = re.findall(r'<url>.*?</url>', s, re.S)
    keep = [u for u in keep if '/juegos/' not in u]
    today = datetime.date.today().isoformat()
    old = {m.group(1): m.group(2) for m in re.finditer(r'<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>', s)}
    new = []
    for path, changed in paths:
        loc = URL + path
        lm = today if changed or loc not in old else old[loc]
        new.append(f'<url><loc>{loc}</loc><lastmod>{lm}</lastmod></url>')
    out = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(keep + new) + '\n</urlset>\n'
    if out != s:
        open(p, 'w', encoding='utf-8').write(out)


# ---------------------------------------------------------------- versión HTML (sin JavaScript) de la portada y la Nacional
PRE_A, PRE_B = '<!--PRE-->', '<!--/PRE-->'


def tie_sort(rows, games, key_w='w', key_pa='pa'):
    """Ordena por victorias; empate de dos = juego directo; si no, menos puntos en contra."""
    rows = sorted(rows, key=lambda r: (-r[key_w], r[key_pa]))
    out, i = [], 0
    while i < len(rows):
        j = i
        while j < len(rows) and rows[j][key_w] == rows[i][key_w] and rows[j]['l'] == rows[i]['l']:
            j += 1
        tie = rows[i:j]
        ks = {r['k'] for r in tie}
        def h2h(k):
            n = 0
            for a, h, sa, sh in games:
                if k in (a, h) and (h if k == a else a) in ks and sa != sh:
                    my, ot = (sa, sh) if k == a else (sh, sa)
                    n += 1 if my > ot else -1
            return n
        out += sorted(tie, key=lambda r: (-h2h(r['k']), r[key_pa]))
        i = j
    return out


def inject(path, html_):
    f = os.path.join(SITE, path)
    s = open(f, encoding='utf-8').read()
    a, b = s.find(PRE_A), s.find(PRE_B)
    if a < 0 or b < 0:
        return False
    new = s[:a + len(PRE_A)] + html_ + s[b:]
    if new != s:
        open(f, 'w', encoding='utf-8').write(new)
        return True
    return False


RLBL = {'P': 'Pend.', 'CF': 'Cuartos', 'SF': 'Semis', 'F': 'Final'}


def patch_team_calendars(G):
    """Calendario de cada ficha desde la pestaña Juegos (temporada regular + playoffs), ligado por partido y no por fila."""
    n = 0
    for k, sl in SLUG.items():
        fp = os.path.join(SITE, 'equipos', sl, 'index.html')
        if not os.path.exists(fp):
            continue
        h = open(fp, encoding='utf-8').read()
        rows = ''
        for g in G:
            if k not in (g['a'], g['h']):
                continue
            home = g['h'] == k
            o = g['a'] if home else g['h']
            lbl = RLBL.get(g['w'], 'S' + g['w'])
            if g['fin']:
                me, ot = (g['hs'], g['as']) if home else (g['as'], g['hs'])
                W = 'G' if me > ot else 'P'
                res = f'<span class="res {W}">{W} {me}-{ot}</span>'
            else:
                d = g['d'][:1].upper() + g['d'][1:]
                res = f'<span style="color:var(--muted)">{e(d)} · {e(g["t"])} h</span>'
            rows += (f'<tr data-m="{g["w"]}-{g["a"]}-{g["h"]}"><td class="pos">{lbl}</td><td class="team"><div class="tname"><img class="badge" src="/img/{o}.png" alt="Escudo de {e(TEAMS[o]["n"])}" width="28" height="28" style="width:28px;height:28px">'
                     f'<span>{"vs" if home else "en"} <a href="/equipos/{SLUG[o]}/">{e(TEAMS[o]["n"])}</a></span></div></td><td class="r">{res}</td></tr>')
        new = re.sub(r'(<table class="sched">.*?<tbody>).*?(</tbody>)', lambda m: m.group(1) + rows + m.group(2), h, count=1, flags=re.S)
        new = new.replace("""document.querySelector('tr[data-gid="'+id+'"] td.r')""", """document.querySelector('tr[data-m="'+(r[SW]||'').trim().toUpperCase()+'-'+a+'-'+h+'"] td.r')""")
        if new != h:
            open(fp, 'w', encoding='utf-8').write(new)
            n += 1
    return n


def _fnum(x):
    x = str(x or '').replace(',', '').strip()
    try:
        return float(x) if '.' in x else int(x)
    except ValueError:
        return None


def refresh_embedded(local):
    """Escribe en el HTML los datos y cortes vigentes de la hoja (lo que ve Google y quien abre sin conexión)."""
    main_p = os.path.join(SITE, 'index.html')
    M = open(main_p, encoding='utf-8').read()
    M0 = M
    # estadísticas por equipo
    try:
        tr, tc = rows_of(fetch('tstats', local))
        F = [('J', 'juegos'), ('rush', 'yds tierra'), ('pass', 'yds aire'), ('tot', 'yds totales'), ('ypg', 'yds por juego'), ('fd', 'primeros y diez'),
             ('to', 'perdidas de balon'), ('rushA', 'yds permitidas tierra'), ('passA', 'yds permitidas aire'), ('totA', 'yds permitidas'),
             ('yapg', 'yds permitidas por juego'), ('pen', 'castigos'), ('penY', 'yds de castigo')]
        T, cut = {}, ''
        for r in tr:
            k = r[0].strip().upper()
            if norm(k) == 'corte':
                cut = (r[1] if len(r) > 1 else '').strip()
            elif k in TEAMS:
                T[k] = {a: _fnum(r[tc[b]]) if b in tc and tc[b] < len(r) else None for a, b in F}
        if len(T) >= 10 and cut:
            js = json.dumps(T, ensure_ascii=False)
            M = re.sub(r"let TSTATS=\{.*?\}\},TSTATS_CUT='[^']*'", lambda m: f"let TSTATS={js},TSTATS_CUT='{cut}'", M, count=1, flags=re.S)
            for sl in SLUG.values():
                fp = os.path.join(SITE, 'equipos', sl, 'index.html')
                h = open(fp, encoding='utf-8').read()
                h2 = re.sub(r"let T=\{.*?\}\},CUT='[^']*'", lambda m: f"let T={js},CUT='{cut}'", h, count=1, flags=re.S)
                if h2 != h:
                    open(fp, 'w', encoding='utf-8').write(h2)
    except Exception as ex:
        print('aviso tstats:', ex)
    # líderes individuales (FBA Stats)
    try:
        lr, lc = rows_of(fetch('lideres', local))
        LCAT = json.loads(re.search(r'const LCAT=(\{.*?\});', M).group(1))
        cut, st = '', []
        for key, (cid, t, u, cols) in LCAT.items():
            rows = []
            for r in lr:
                g = lambda n: (r[lc[n]] if n in lc and lc[n] < len(r) else '').strip()
                if norm(g('categoria')) == 'corte':
                    cut = g('jugador') or cut
                if g('categoria').upper() != key or g('equipo').upper() not in TEAMS or not g('jugador'):
                    continue
                vals = [_fnum(g(c.lower())) for c in cols]
                if any(v is None for v in vals):
                    continue
                rows.append((_fnum(g('lugar')) or 99, [g('jugador'), g('equipo').upper(), _fnum(g('numero'))] + vals))
            if rows:
                st.append({'id': cid, 't': t, 'u': u, 'cols': cols, 'rows': [x for _, x in sorted(rows, key=lambda y: y[0])]})
        if len(st) >= 5 and cut:
            M = re.sub(r"let STATS_CUTOFF='[^']*';\nlet STATS=\[.*?\];\n", lambda m: f"let STATS_CUTOFF='{cut}';\nlet STATS={json.dumps(st, ensure_ascii=False)};\n", M, count=1, flags=re.S)
    except Exception as ex:
        print('aviso lideres:', ex)
    # jugadores a seguir (pestaña Jugadores): portada (INFO) y fichas
    try:
        er, ec = rows_of(fetch('estrellas', local))
        S = {}
        for r in er:
            g = lambda n: (r[ec[n]] if n in ec and ec[n] < len(r) else '').strip()
            k = g('equipo').upper()
            if k in TEAMS and g('jugador'):
                S.setdefault(k, []).append([g('jugador'), g('posicion'), _fnum(g('numero')), g('estadistica')])
        m = re.search(r'const INFO=(\{.*?\});\n', M, re.S)
        I = json.loads(m.group(1))
        for k, L in S.items():
            if k in I and len(I[k]) > 4:
                I[k][4] = L
        M = M[:m.start(1)] + json.dumps(I, ensure_ascii=False) + M[m.end(1):]
        for k, L in S.items():
            fp = os.path.join(SITE, 'equipos', SLUG[k], 'index.html')
            h = open(fp, encoding='utf-8').read()
            cards = ''.join(f'<div class="star"><span class="jn num">#{x[2] if x[2] is not None else ""}</span><div><b>{e(x[0])}</b><div class="loc">{e(x[1])}</div><div class="sl">{e(x[3])}</div></div></div>' for x in L)
            star = r'<div class="star"><span class="jn num">[^<]*</span><div><b>[^<]*</b><div class="loc">[^<]*</div><div class="sl">[^<]*</div></div></div>'
            h2 = re.sub(r'(<div class="stars" id="stars" data-k="' + k + r'">)(?:' + star + r')*', lambda mm: mm.group(1) + cards, h, count=1)
            if h2 != h:
                open(fp, 'w', encoding='utf-8').write(h2)
    except Exception as ex:
        print('aviso estrellas:', ex)
    if M != M0:
        open(main_p, 'w', encoding='utf-8').write(M)
    # Nacional: tabla oficial y su corte
    try:
        np_ = os.path.join(SITE, 'nacional', 'index.html')
        N = open(np_, encoding='utf-8').read()
        tr, tc = rows_of(fetch('ntabla', local))
        cut, out = '', []
        for r in tr:
            g = lambda n: (r[tc[n]] if n in tc and tc[n] < len(r) else '').strip()
            if norm(r[0]) == 'corte':
                cut = (r[1] if len(r) > 1 else '').strip()
                continue
            if not g('clave'):
                continue
            out.append({'g': g('grupo'), 'k': g('clave').upper(), 'n': g('equipo'), 's': g('escuela'), 'w': _fnum(g('g')) or 0, 'l': _fnum(g('p')) or 0, 'pf': _fnum(g('pf')) or 0, 'pa': _fnum(g('pc')) or 0})
        if len(out) >= 15 and cut:
            N2 = re.sub(r"let TEAMS=\[.*?\],CUT='[^']*'", lambda m: f"let TEAMS={json.dumps(out, ensure_ascii=False)},CUT='{cut}'", N, count=1, flags=re.S)
            if N2 != N:
                open(np_, 'w', encoding='utf-8').write(N2)
    except Exception as ex:
        print('aviso nacional:', ex)


def patch_team_facts(G):
    """Récord, lugar y puntos de temporada regular en el HTML de cada página de equipo (lo que ve Google)."""
    S = {k: {'k': k, 'w': 0, 'l': 0, 'pf': 0, 'pa': 0} for k in TEAMS}
    reg = []
    for g in G:
        if g['fin'] and g['w'] not in ('CF', 'SF', 'F'):
            for k, my, ot in ((g['a'], g['as'], g['hs']), (g['h'], g['hs'], g['as'])):
                S[k]['pf'] += my; S[k]['pa'] += ot
                S[k]['w' if my > ot else 'l'] += 1
            reg.append((g['a'], g['h'], g['as'], g['hs']))
    rows = tie_sort(list(S.values()), reg)
    n = 0
    for i, r in enumerate(rows):
        fp = os.path.join(SITE, 'equipos', SLUG[r['k']], 'index.html')
        if not os.path.exists(fp):
            continue
        h = open(fp, encoding='utf-8').read()
        new = re.sub(r'(<b id="f-rec">)[^<]*', lambda m: m.group(1) + f"{r['w']}-{r['l']}", h)
        new = re.sub(r'(<b id="f-pos">)[^<]*', lambda m: m.group(1) + f"{i + 1}°", new)
        new = re.sub(r'(<b id="f-pf">)[^<]*', lambda m: m.group(1) + str(r['pf']), new)
        new = re.sub(r'(<b id="f-pa">)[^<]*', lambda m: m.group(1) + str(r['pa']), new)
        if new != h:
            open(fp, 'w', encoding='utf-8').write(new)
            n += 1
    return n


def pre_main(G):
    S = {k: {'k': k, 'w': 0, 'l': 0, 'pf': 0, 'pa': 0} for k in TEAMS}
    reg = []
    for g in G:
        if g['fin'] and g['w'] not in ('CF', 'SF', 'F'):
            for k, my, ot in ((g['a'], g['as'], g['hs']), (g['h'], g['hs'], g['as'])):
                S[k]['pf'] += my; S[k]['pa'] += ot
                S[k]['w' if my > ot else 'l'] += 1
            reg.append((g['a'], g['h'], g['as'], g['hs']))
    rows = tie_sort(list(S.values()), reg)
    lw = max([int(g['w']) for g in G if g['fin'] and g['w'].isdigit()] or [0])
    h = [f'<div class="pre"><h2>Tabla de posiciones</h2><p class="sub">Liga Mayor ONEFA {YEAR} · Conferencia de los 14 Grandes · tras la semana {lw}</p>',
         '<div class="tbl-box"><table><thead><tr><th>#</th><th>Equipo</th><th>G-P</th><th>PF</th><th>PC</th><th>Dif</th></tr></thead><tbody>']
    for i, r in enumerate(rows):
        d = r['pf'] - r['pa']
        h.append(f'<tr class="row"><td class="pos">{i + 1}</td><td class="team"><div class="tname">{badge(r["k"], 30)}<span><a href="/equipos/{SLUG[r["k"]]}/" style="color:inherit;text-decoration:none">{e(TEAMS[r["k"]]["n"])}</a></span></div></td><td class="rec">{r["w"]}-{r["l"]}</td><td>{r["pf"]}</td><td>{r["pa"]}</td><td>{"+" if d > 0 else ""}{d}</td></tr>')
        if i == 7:
            h.append('<tr class="cut"><td colspan="6"><div class="cutline"><b>Línea de corte · cuartos de final</b></div></td></tr>')
    h.append('</tbody></table></div>')
    po = [g for g in G if g['w'] in ('CF', 'SF', 'F')]
    def li(g):
        sc = f' {g["as"]}-{g["hs"]}' if g['fin'] else f' · {e(g["d"])} {e(g["t"])} h'
        return f'<li><a href="{game_path(g)}">{e(wk_label(g["w"]))}: {e(TEAMS[g["a"]]["n"])} en {e(TEAMS[g["h"]]["n"])}</a>{sc}</li>'
    if po:
        h.append('<h3>Playoffs</h3><ul>' + ''.join(li(g) for g in po) + '</ul>')
    else:
        cur = [g for g in G if g['w'] == str(lw + 1)] or [g for g in G if g['w'] == str(lw)]
        if cur:
            h.append(f'<h3>Semana {e(cur[0]["w"])}</h3><ul>' + ''.join(li(g) for g in cur) + '</ul>')
    h.append(f'<p class="sub"><a href="/juegos/{YEAR}/">Todos los resultados de la temporada {YEAR}</a> · <a href="/nacional/">Conferencia Nacional</a> · <a href="/historia/">Historia y campeones</a></p></div>')
    return ''.join(h)


def pre_nac(local):
    tr, tc = rows_of(fetch('ntabla', local))
    jr, jc = rows_of(fetch('njuegos', local))
    if not tr or 'clave' not in tc:
        return None
    v = lambda r, c, n: (r[c[n]] if n in c and c[n] < len(r) else '').strip()
    T, cut = [], ''
    for r in tr:
        if norm(r[0]) == 'corte':
            cut = (r[1] if len(r) > 1 else '').strip(); continue
        k = v(r, tc, 'clave').upper()
        if not k:
            continue
        n = lambda x: int(re.sub(r'[^0-9-]', '', x) or 0)
        T.append({'k': k, 'g': v(r, tc, 'grupo'), 'n': v(r, tc, 'equipo') or k, 's': v(r, tc, 'escuela'),
                  'w': n(v(r, tc, 'g')), 'l': n(v(r, tc, 'p')), 'pf': n(v(r, tc, 'pf')), 'pa': n(v(r, tc, 'pc'))})
    if len(T) < 15:
        return None
    name = {t['k']: t['n'] for t in T}
    games, po = [], []
    for r in jr:
        rd = re.sub(r'^S(EMANA)?\s*(?=\d)', '', v(r, jc, 'ronda').upper())
        a, hh = v(r, jc, 'visitante').upper(), v(r, jc, 'local').upper()
        A, H = num(v(r, jc, 'pts visitante')), num(v(r, jc, 'pts local'))
        fin = norm(v(r, jc, 'estado')) == 'final' and A is not None and H is not None
        if rd.isdigit() and fin:
            games.append((a, hh, A, H))
        elif rd in ('CF', 'SF', 'F') and a in name and hh in name:
            po.append((rd, a, hh, A if fin else None, H if fin else None, v(r, jc, 'fecha'), v(r, jc, 'hora')))
    h = [f'<div class="pre"><h2>Tabla de posiciones</h2><p class="sub">Conferencia Nacional · Liga Mayor ONEFA {YEAR}{" · " + e(cut.lower()) if cut else ""}</p>']
    for grp in [x for x in dict.fromkeys(t['g'] for t in T) if x]:
        rows = tie_sort([t for t in T if t['g'] == grp], games)
        h.append(f'<h4 class="br-round">Grupo {e(grp)}</h4><div class="tbl-box" style="margin-bottom:12px"><table><thead><tr><th>#</th><th>Equipo</th><th>G-P</th><th>PF</th><th>PC</th></tr></thead><tbody>')
        for i, t in enumerate(rows):
            h.append(f'<tr class="row"><td class="pos">{i + 1}</td><td class="team"><div class="tname"><img src="/img/N_{t["k"]}.png" alt="{e(t["n"])}" width="30" height="30"><span>{e(t["n"])}</span></div></td><td class="rec">{t["w"]}-{t["l"]}</td><td>{t["pf"]}</td><td>{t["pa"]}</td></tr>')
        h.append('</tbody></table></div>')
    if po:
        RN = {'CF': 'Cuartos de final', 'SF': 'Semifinal', 'F': 'Final'}
        h.append('<h3>Playoffs</h3><ul>' + ''.join(
            f'<li>{RN[rd]}: {e(name[a])} en {e(name[hh])}' + (f' {A}-{H}' if A is not None else f' · {e(d)} {e(re.sub(r"\s*hrs?$", "", t))}') + '</li>'
            for rd, a, hh, A, H, d, t in po) + '</ul>')
    h.append('<p class="sub"><a href="/">Conferencia de los 14 Grandes</a> · <a href="/historia/">Historia y campeones</a></p></div>')
    return ''.join(h)


def main():
    local = sys.argv[sys.argv.index('--local') + 1] if '--local' in sys.argv else None
    G, PL = load(local)
    S = standings(G)
    order = []
    for g in G:
        if g['w'] not in order:
            order.append(g['w'])
    reg = sorted([w for w in order if w.isdigit()], key=int)
    weeks = reg + [w for w in ('P', 'CF', 'SF', 'F') if w in order]
    byw = {w: [g for g in G if g['w'] == w] for w in weeks}
    out = []
    for g in G:
        p, html_ = game_page(g, G, PL, S)
        out.append((p, write(p, html_)))
    for w in weeks:
        p, html_ = week_page(w, byw[w], weeks, S)
        out.append((p, write(p, html_)))
    p, html_ = season_page(weeks, byw)
    out.append((p, write(p, html_)))
    sitemap(out)
    try:
        print('equipos (récord en HTML):', patch_team_facts(G), '· calendarios:', patch_team_calendars(G))
        refresh_embedded(local)
        changed = inject('index.html', pre_main(G))
        nh = pre_nac(local)
        if nh:
            changed = inject(os.path.join('nacional', 'index.html'), nh) or changed
        print('portada/nacional en HTML:', 'actualizadas' if changed else 'sin cambios')
    except Exception as ex:
        print('aviso: no se pudo generar el HTML de portada/nacional:', ex)
    print(f'{len(out)} páginas, {sum(c for _, c in out)} cambiaron')


if __name__ == '__main__':
    main()
