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
       'lideres': 1908116186, 'estrellas': 1355832789, 'tstats': 1066629721, 'lesiones': 777000001}
e = html.escape

# ---------------------------------------------------------------- datos base del sitio
MAIN = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
# Nombres completos de la Nacional (para no confundir Potros ITSON / Potros Salvajes, Lobos ULM / Lobos UAdeC, etc.)
NFULL = {'PAC': 'Pumas Acatlán', 'PSA': 'Potros Salvajes UAEMéx', 'FRA': 'Frailes Tepeyac', 'HAL': 'Halcones UV', 'BUH': 'Búhos Guinda IPN',
         'TSA': 'Toros Salvajes Chapingo', 'PAN': 'Panteras Siglo 21', 'LQR': 'Leones Anáhuac Querétaro', 'TEC': 'Tecos UAG', 'ULM': 'Lobos ULM',
         'UIW': 'Cardinals UIW', 'ASU': 'Red Wolves ASU', 'UAT': 'Correcaminos UAT', 'UCH': 'Águilas UACH', 'ITS': 'Potros ITSON', 'UAC': 'Lobos UAdeC',
         'UCJ': 'Indios UACJ', 'UBC': 'Cimarrones UABC'}
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


def page(title, desc, path, body, ld_list, og_type='website', og_img=None):
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
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{URL}{path}"><meta property="og:image" content="{URL}{og_img or '/og.png'}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{URL}{og_img or '/og.png'}">
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
                  'det': v(r, 'detalle'), 'tv': v(r, 'transmision'), 'lk': v(r, 'link'), 'ya': num(v(r, 'yds visitante')), 'yh': num(v(r, 'yds local'))})
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
            q = 9 if qs in ('', '?') else 5 if qs in ('TE', 'OT') else num(qs)
            if not q or not (1 <= q <= 5 or q == 9):
                continue
            x = norm(av(r, 'extra'))
            pts = 6 if k.startswith('td') else 3 if k == 'fg' else 2 if k == 'safety' else 0
            pts += (1 if x == 'pat bueno' else 2 if x == '2 pts bueno' else 0) if k.startswith('td') else 0
            key = (av(r, 'semana').upper(), av(r, 'visitante').upper(), av(r, 'local').upper())
            PL.setdefault(key, []).append({'q': q, 't': t, 'k': k, 'j': ' '.join(av(r, 'jugador').split()) or 'Sin nombre en la crónica', 'p': ' '.join(av(r, 'pase de').split()), 'y': av(r, 'yardas'), 'x': x, 'pts': pts})
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
    if k == 'td':
        return 'Touchdown', J or 'TD'
    return e(p['k']), J


def detail_html(g, P):
    if not P:
        return ''
    nQ = max(4, max([p['q'] for p in P if p['q'] <= 5] or [4]))
    Q = {g['a']: [0] * (nQ + 1), g['h']: [0] * (nQ + 1)}
    for p in P:
        if p['t'] in Q and p['q'] <= 5:
            Q[p['t']][p['q']] += p['pts']
    tot = {k: (g['as'] if k == g['a'] else g['hs']) if g['fin'] else sum(Q[k]) for k in Q}
    cols = range(1, nQ + 1)
    row = lambda k: f'<tr><td>{e(SHORT.get(k, k))}</td>' + ''.join(f'<td>{Q[k][q]}</td>' for q in cols) + f'<td class="tot">{tot[k]}</td></tr>'
    h = '<h2 style="font-size:26px;margin-top:22px">Marcador por cuarto</h2><table class="qs"><thead><tr><th>Equipo</th>' + ''.join(f'<th>{"TE" if q == 5 else str(q) + "º"}</th>' for q in cols) + f'<th>Total</th></tr></thead><tbody>{row(g["a"])}{row(g["h"])}</tbody></table>'
    if any(p['q'] == 9 for p in P):
        h += '<p class="sub" style="margin-top:6px">Algunas anotaciones no tienen cuarto confirmado en las crónicas, así que los cuartos no suman el marcador final.</p>'
    h += '<h2 style="font-size:26px;margin-top:22px">Anotaciones</h2><div class="plays">'
    ra = rh = 0
    last = 0
    qn = {1: '1er cuarto', 2: '2º cuarto', 3: '3er cuarto', 4: '4º cuarto', 5: 'Tiempo extra', 9: 'Cuarto sin confirmar'}
    ex = {'pat bueno': 'Punto extra bueno', 'pat fallado': 'Punto extra fallado', '2 pts bueno': 'Conversión de 2 buena', '2 pts fallado': 'Conversión de 2 fallada'}
    for p in (list(P) if any(p['q'] == 9 for p in P) else sorted(P, key=lambda p: p['q'])):
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


POLL_JS = """<style>.poll{display:grid;gap:8px}.poll-q{font-weight:800;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.poll-b{display:grid;grid-template-columns:1fr 1fr;gap:8px}.poll-b button{font:inherit;font-weight:700;font-size:14px;border:1px solid var(--line);background:var(--bg);color:var(--ink);border-radius:2px;min-height:44px;cursor:pointer}
.poll-r{display:flex;justify-content:space-between;font-size:14px}.poll-bar{display:flex;height:8px;border-radius:2px;overflow:hidden;background:var(--line)}.poll-bar i:first-child{background:#3DBE73}.poll-bar i:last-child{background:#8A939B}.poll-n{font-size:13px;color:var(--muted)}</style>
<script>(function(){const POST='https://docs.google.com/forms/d/1kA7h-L9z0Lgt-Fkn5NOM3oef0m5Hq4NjxcTR78WUbmk/formResponse',E=['entry.276666447','entry.1627804977'],
CSV='https://docs.google.com/spreadsheets/d/e/2PACX-1vQNVclYf7g5WHDSejO-E_1xVXBF-KC__RWAbeSLafpfFK-5fxjCE2JegKDDBVnqalEEV97cBnF1PMzU/pub?gid=931332467&single=true&output=csv';
let V={},MY={};try{MY=JSON.parse(localStorage.getItem('lmu-votes')||'{}')}catch(e){}
const esc=x=>String(x??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function draw(){document.querySelectorAll('[data-poll]').forEach(el=>{const id=el.dataset.poll,a=el.dataset.a,h=el.dataset.h,na=el.dataset.na,nh=el.dataset.nh,v=V[id]||{},my=MY[id];
 if(!my){el.innerHTML=`<span class="poll-q">¿Quién crees que gana?</span><div class="poll-b"><button type="button" data-vote="${a}">${esc(na)}</button><button type="button" data-vote="${h}">${esc(nh)}</button></div><span class="poll-n">Vota para ver qué piensa la afición</span>`;return}
 const x=v[a]||0,y=v[h]||0,T=x+y||1,pa=Math.round(x/T*100);
 el.innerHTML=`<span class="poll-q">Así va la afición</span><div class="poll-r"><span>${esc(na)} <b>${pa}%</b></span><span><b>${100-pa}%</b> ${esc(nh)}</span></div><div class="poll-bar"><i style="width:${pa}%"></i><i style="width:${100-pa}%"></i></div><span class="poll-n">Tu voto: ${esc(my===a?na:nh)}</span>`})}
document.addEventListener('click',e=>{const b=e.target.closest('[data-vote]');if(!b)return;const p=b.closest('[data-poll]'),id=p.dataset.poll,k=b.dataset.vote;if(MY[id])return;MY[id]=k;
 try{localStorage.setItem('lmu-votes',JSON.stringify(MY))}catch(_){}(V[id]=V[id]||{})[k]=(V[id][k]||0)+1;draw();
 try{fetch(POST,{method:'POST',mode:'no-cors',body:new URLSearchParams({[E[0]]:id,[E[1]]:k})})}catch(_){}});
fetch(CSV+'&t='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.text():'').then(t=>{t.split(/\\r?\\n/).slice(1).forEach(l=>{const c=l.split(',');const id=(c[0]||'').trim(),k=(c[1]||'').trim();if(id&&k)(V[id]=V[id]||{})[k]=+c[2]||0});
 Object.keys(MY).forEach(id=>{const k=MY[id];if(k&&!(V[id]&&V[id][k]))(V[id]=V[id]||{})[k]=1});draw()}).catch(()=>{});draw()})();</script>"""


def og_image(g, A, H, tv):
    """Imagen para compartir del partido (1200x630): escudos, ronda, fecha y canal o marcador final."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        rel = game_path(g) + 'og.png'
        return rel if os.path.exists(os.path.join(SITE, rel.strip('/'))) else None
    fp_font = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'Roboto.ttf')
    def F(sz, wt=800, wd=75):
        f = ImageFont.truetype(fp_font, sz)
        try:
            f.set_variation_by_axes([wt, wd])
        except Exception:
            pass
        return f
    W, Hh = 1200, 630
    im = Image.new('RGB', (W, Hh), '#0E1511')
    d = ImageDraw.Draw(im)
    d.rectangle([0, Hh - 14, W, Hh], fill='#3DBE73')
    d.text((60, 46), 'LIGA MAYOR UNOFFICIAL', font=F(30, 800, 100), fill='#3DBE73')
    lbl = {'CF': 'CUARTOS DE FINAL', 'SF': 'SEMIFINAL', 'F': 'LA FINAL'}.get(g['w'], wk_label(g['w']).upper())
    d.text((W - 60, 46), f'{lbl} · {YEAR}', font=F(30, 800, 100), fill='#F1F3F2', anchor='ra')
    for i, k in enumerate((g['a'], g['h'])):
        x = 230 if i == 0 else W - 230
        try:
            b = Image.open(os.path.join(SITE, 'img', f'{k}.png')).convert('RGBA').resize((216, 216), Image.NEAREST)
            im.paste(b, (x - 108, 140), b)
        except Exception:
            pass
        nm = SHORT.get(k, TEAMS[k]['n']).upper()
        d.text((x, 384), nm, font=F(46 if len(nm) < 14 else 38), fill='#F1F3F2', anchor='ma')
    if g['fin']:
        d.text((W // 2, 200), f"{g['as']}  -  {g['hs']}", font=F(120), fill='#F1F3F2', anchor='ma')
        win = TEAMS[g['a'] if g['as'] > g['hs'] else g['h']]['n']
        sub = (f'{win.upper()} CAMPEÓN {YEAR}' if g['w'] == 'F' else 'FINAL') + (f" · {g['det'].upper()}" if g.get('det') else '')
        d.text((W // 2, 350), sub, font=F(34), fill='#3DBE73', anchor='ma')
    else:
        d.text((W // 2, 210), 'VS', font=F(110), fill='#F1F3F2', anchor='ma')
        d.text((W // 2, 470), (long_date(g['d']) + (f" · {g['t']} h" if g['t'] else '')).upper(), font=F(40), fill='#F1F3F2', anchor='ma')
        if tv:
            d.text((W // 2, 528), f'TV: {tv}'.upper(), font=F(32, 600), fill='#9FB3A7', anchor='ma')
    rel = game_path(g) + 'og.png'
    out = os.path.join(SITE, rel.strip('/'))
    import io as _io
    buf = _io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    data = buf.getvalue()
    if not os.path.exists(out) or open(out, 'rb').read() != data:
        open(out, 'wb').write(data)
    return rel


def cal_links(g, A, H, stadium, city, ld_date):
    """Botones para guardar el partido en el calendario (Google y archivo .ics para iPhone/Outlook)."""
    if not ld_date or not g['t']:
        return ''
    from urllib.parse import quote
    st = datetime.datetime.fromisoformat(ld_date).astimezone(datetime.timezone.utc)
    en = st + datetime.timedelta(hours=3)
    f = lambda d: d.strftime('%Y%m%dT%H%M%SZ')
    ttl = f"{A['n']} vs {H['n']} · {wk_label(g['w'])} Liga Mayor"
    loc = ', '.join(x for x in [stadium, city] if x)
    url = URL + game_path(g)
    tv, _ = watch(g)
    det = f"{url}" + (f"\nTransmisión: {tv}" if tv else '')
    gc = ('https://calendar.google.com/calendar/render?action=TEMPLATE&text=' + quote(ttl) + f'&dates={f(st)}/{f(en)}'
          + '&details=' + quote(det) + '&location=' + quote(loc))
    esc = lambda x: x.replace('\\', '\\\\').replace(',', '\\,').replace(';', '\\;').replace('\n', '\\n')
    ics = '\r\n'.join(['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//ligamayorunofficial.com//ES', 'BEGIN:VEVENT',
                        f'UID:{g["w"]}-{g["a"]}-{g["h"]}-{YEAR}@ligamayorunofficial.com', f'DTSTAMP:{f(st)}', f'DTSTART:{f(st)}', f'DTEND:{f(en)}',
                        'SUMMARY:' + esc(ttl), 'LOCATION:' + esc(loc), 'DESCRIPTION:' + esc(det), 'URL:' + url, 'END:VEVENT', 'END:VCALENDAR'])
    # archivo .ics real (Safari de iPhone no abre bien los enlaces data:)
    fp = os.path.join(SITE, game_path(g).strip('/'), 'partido.ics')
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    if not os.path.exists(fp) or open(fp, encoding='utf-8', newline='').read() != ics + '\r\n':
        open(fp, 'w', encoding='utf-8', newline='').write(ics + '\r\n')
    return (f'<div class="calb"><span>Agregar al calendario:</span><a href="{e(gc)}" target="_blank" rel="noopener">Google Calendar</a>'
            f'<a href="{game_path(g)}partido.ics">iPhone / Outlook (.ics)</a></div>')


def preview_html(g, G, S, A, H):
    """Previa de partidos de playoffs: camino de cada equipo, cara a cara y datos de contexto (build/data/previas.json)."""
    if g['w'] not in ('CF', 'SF', 'F') or g['fin']:
        return ''
    out = ''
    PW = ['CF', 'SF', 'F']
    def path(k):
        r = []
        for x in G:
            if x is g or not x['fin'] or x['w'] not in PW or PW.index(x['w']) >= PW.index(g['w']) or k not in (x['a'], x['h']):
                continue
            me, op = (x['as'], x['hs']) if x['a'] == k else (x['hs'], x['as'])
            o = x['h'] if x['a'] == k else x['a']
            r.append(f"{'Ganó' if me > op else 'Perdió'} {me}-{op} a {TEAMS[o]['n']} ({ {'CF': 'cuartos', 'SF': 'semifinal'}.get(x['w'], x['w']) })")
        return r
    gp = lambda k: max(1, S[k]['w'] + S[k]['l'])
    pts = {k: [0, 0] for k in (g['a'], g['h'])}
    for x in G:
        if x['fin'] and x['w'] not in PW:
            for k, me, op in ((x['a'], x['as'], x['hs']), (x['h'], x['hs'], x['as'])):
                if k in pts:
                    pts[k][0] += me
                    pts[k][1] += op
    S = {k: dict(S[k], pf=pts[k][0], pa=pts[k][1]) for k in pts}
    rows = [('Récord temporada regular', f"{S[g['a']]['w']}-{S[g['a']]['l']}", f"{S[g['h']]['w']}-{S[g['h']]['l']}"),
            ('Puntos a favor por juego', f"{S[g['a']]['pf'] / gp(g['a']):.1f}", f"{S[g['h']]['pf'] / gp(g['h']):.1f}"),
            ('Puntos en contra por juego', f"{S[g['a']]['pa'] / gp(g['a']):.1f}", f"{S[g['h']]['pa'] / gp(g['h']):.1f}")]
    reg = [x for x in G if x['fin'] and x['w'] not in PW and {x['a'], x['h']} == {g['a'], g['h']}]
    out += f'<h2 style="font-size:26px;margin-top:22px">Previa</h2>'
    out += ('<div class="tbl-box"><table class="qs"><thead><tr><th></th><th>' + e(SHORT.get(g['a'], A['n'])) + '</th><th>' + e(SHORT.get(g['h'], H['n'])) + '</th></tr></thead><tbody>'
            + ''.join(f'<tr><td>{l}</td><td class="num">{a}</td><td class="num">{h}</td></tr>' for l, a, h in rows) + '</tbody></table></div>')
    pa, ph = path(g['a']), path(g['h'])
    if pa or ph:
        out += f'<div class="card" style="margin-top:10px"><b>Camino {"a la final" if g["w"] == "F" else "hasta aquí"}</b><p class="sub" style="margin:6px 0 0"><b>{e(A["n"])}:</b> {e("; ".join(pa) or "—")}</p><p class="sub" style="margin:4px 0 0"><b>{e(H["n"])}:</b> {e("; ".join(ph) or "—")}</p></div>'
    if reg:
        x = reg[-1]
        out += f'<div class="card" style="margin-top:10px"><b>En la temporada regular</b><p class="sub" style="margin:6px 0 0">{e(long_date(x["d"]) if x["w"] == "P" else wk_label(x["w"]))}: {e(TEAMS[x["a"]]["n"])} {x["as"]}, {e(TEAMS[x["h"]]["n"])} {x["hs"]}{(" (" + e(x["det"]) + ")") if x.get("det") else ""}.</p></div>'
    try:
        P = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'previas.json'), encoding='utf-8'))
    except Exception:
        P = {}
    d = P.get(f"{g['w']}|{g['a']}|{g['h']}") or P.get(f"{g['w']}|{g['h']}|{g['a']}")
    if d:
        out += f'<div class="card" style="margin-top:10px"><b>{e(d.get("titulo", "Contexto"))}</b><ul class="pv">' + ''.join(f'<li>{e(x)}</li>' for x in d.get('puntos', [])) + '</ul>'
        if d.get('fuentes'):
            out += '<p class="sub" style="margin:6px 0 0">Fuentes: ' + ', '.join(f'<a href="{e(u)}" rel="noopener" target="_blank">{e(t)}</a>' for t, u in d['fuentes']) + '.</p>'
        out += '</div>'
    return out


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
        if g['w'] == 'F':
            title = f"{win} campeón {YEAR}: {A['n']} {g['as']}-{g['hs']} {H['n']} · Final Liga Mayor ONEFA"
            desc = f"{win} es campeón de la Liga Mayor ONEFA {YEAR}. Final: {A['n']} {g['as']}, {H['n']} {g['hs']}" + (f" ({g['det']})" if g.get('det') else '') + '.'
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
    if g['w'] == 'F' and g['fin']:
        wk = g['a'] if g['as'] > g['hs'] else g['h']
        body += f'<div class="champb"><span>Campeón {YEAR} · Liga Mayor ONEFA</span><b>{e(TEAMS[wk]["n"])}</b></div>'
    body += f'<h1 class="gm-h1">{e(A["n"])} vs {e(H["n"])}</h1>'
    body += f'<p class="gm-meta">Liga Mayor ONEFA {YEAR} · 14 Grandes · {e(wl)}{(" · " + e(g["det"])) if g["det"] and not g["live"] else ""}</p>'
    body += f'<div class="gm-top">{team(g["a"], A, aL, "Visitante")}{sc}{team(g["h"], H, hL, "Local")}<div class="gm-st{" live" if g["live"] else ""}" id="gm-st">{e(status)}</div></div>'
    if tv:
        lbl = 'Ver transmisión' if g['fin'] else 'Ver partido'
        body += f'<div class="wb2"><div><span>{"Se transmitió por" if g["fin"] else "Dónde ver"}</span><b>{e(tv)}</b></div>{f"<a href=\"{e(lk)}\" target=\"_blank\" rel=\"noopener\">{lbl} ▶</a>" if lk else ""}</div>'
    facts = f'<div><dt>Fecha</dt><dd>{e(long_date(g["d"]))}{" · " + e(g["t"]) + " h" if g["t"] else ""}</dd></div>'
    if stadium:
        facts += f'<div><dt>Estadio</dt><dd>{e(stadium)}</dd></div><div><dt>Sede</dt><dd>{e(city)}</dd></div>'
    body += f'<h2 style="font-size:26px;margin-top:22px">El partido</h2><div class="card"><dl class="facts">{facts}</dl>{cal_links(g, A, H, stadium, city, ld_date) if not g["fin"] and not g["live"] else ""}</div>'
    body += preview_html(g, G, S, A, H)
    if not g['fin']:
        # jugadores clave (los llena jugadores.py con FBA y la pestaña Lesiones) y la votación de la afición
        body += f'<!--KP:{g["a"]}:{g["h"]}--><!--/KP-->'
        body += (f'<h2 style="font-size:26px;margin-top:22px">¿Quién gana?</h2><div class="card"><div class="poll" data-poll="G-{g["w"]}-{g["a"]}-{g["h"]}" data-a="{g["a"]}" data-h="{g["h"]}" data-open="1"'
                 f' data-na="{e(A["n"])}" data-nh="{e(H["n"])}"></div></div>' + POLL_JS)
    body += detail_html(g, PL.get((g['w'], g['a'], g['h']), []))
    if g['fin'] and g.get('ya') is not None and g.get('yh') is not None:
        body += (f'<h2 style="font-size:26px;margin-top:22px">Yardas totales</h2><div class="card"><dl class="facts"><div><dt>{e(A["n"])}</dt><dd>{g["ya"]} yardas</dd></div>'
                 f'<div><dt>{e(H["n"])}</dt><dd>{g["yh"]} yardas</dd></div></dl><p class="sub" style="margin:8px 0 0">Fuente: boletín de prensa ONEFA.</p></div>')
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
        ev['endDate'] = (datetime.datetime.fromisoformat(ld_date) + datetime.timedelta(hours=3)).isoformat()
    # Google pide siempre la sede: si no hay estadio registrado, se usa la casa del equipo local
    ev['location'] = {'@type': 'Place', 'name': stadium or f"Casa de {H['n']}", 'address': {'@type': 'PostalAddress', 'addressLocality': city or H['n'], 'addressCountry': 'MX'}}
    ev['performer'] = [{'@type': 'SportsTeam', 'name': A['n']}, {'@type': 'SportsTeam', 'name': H['n']}]
    og = og_image(g, A, H, tv) if g['w'] in ('CF', 'SF', 'F') else None
    if og:
        ev['image'] = [URL + og]
    return path, page(title, desc, path, body, [ev, bld], 'article', og)


def week_card(g, S):
    A, H = g['a'], g['h']
    aL = g['fin'] and g['as'] < g['hs']
    hL = g['fin'] and g['hs'] < g['as']
    meta = 'Final' if g['fin'] else ('En vivo' if g['live'] else (f"{g['d']} · {g['t']} h" if g['t'] else g['d']))
    r = lambda k, sc, l: f'<div class="r{" l" if l else ""}">{badge(k, 26)}{e(TEAMS[k]["n"])}</div><div class="s">{sc if g["fin"] else ""}</div>'
    return f'<a class="wg" href="{game_path(g)}"><div class="m">{e(meta)}</div>{r(A, g["as"], aL)}{r(H, g["hs"], hL)}</a>'


PEND_FROM, PEND = '5', []   # el MTY-TIG de la semana 5 se suspendió por lluvia y pasó a 'Pendientes'


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
    if w == PEND_FROM and PEND:
        body += ''.join(f'<p class="sub" style="margin-top:10px">{e(TEAMS[g["a"]]["n"])} vs {e(TEAMS[g["h"]]["n"])}, de esta semana, se suspendió por lluvia y se reprogramó al {e(long_date(g["d"]).lower())}. '
                        f'<a href="{game_path(g)}">Ver el partido →</a> · <a href="/juegos/{YEAR}/{wk_slug("P")}/">Juegos pendientes →</a></p>' for g in PEND)
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
    """Ordena por victorias; empate de dos = juego directo; con tres o más, menos puntos en contra."""
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
        # igual que la portada: con 2 empatados manda el juego directo; con 3 o más, menos puntos en contra
        out += sorted(tie, key=lambda r: (-h2h(r['k']), r[key_pa])) if len(tie) == 2 else sorted(tie, key=lambda r: r[key_pa])
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


def refresh_raw(G):
    """Copia de los partidos (incluye playoffs) dentro de la portada, para dibujarla al instante sin esperar a la hoja."""
    fp = os.path.join(SITE, 'index.html')
    M = open(fp, encoding='utf-8').read()
    cl = lambda x: str(x if x is not None else '').replace("'", "").replace('|', ' ').replace('\\', '')
    raw = ','.join("'" + '|'.join(cl(x) for x in (g['w'], g['d'], g['t'], g['a'], g['as'] if g['fin'] else '', g['hs'] if g['fin'] else '', g['h'])) + "'" for g in G)
    M2 = re.sub(r"const RAW=\[.*?\];", lambda _: f"const RAW=[\n{raw}];", M, count=1, flags=re.S)
    if M2 != M:
        open(fp, 'w', encoding='utf-8').write(M2)


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
    # jugadores a seguir: ahora los calcula jugadores.py con los datos de FBA (ya no la pestaña Jugadores)
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
            out.append({'g': g('grupo'), 'k': g('clave').upper(), 'n': NFULL.get(g('clave').upper(), g('equipo')), 's': g('escuela'), 'w': _fnum(g('g')) or 0, 'l': _fnum(g('p')) or 0, 'pf': _fnum(g('pf')) or 0, 'pa': _fnum(g('pc')) or 0})
        if len(out) >= 15 and cut:
            N2 = re.sub(r"let TEAMS=\[.*?\],CUT='[^']*'", lambda m: f"let TEAMS={json.dumps(out, ensure_ascii=False)},CUT='{cut}'", N, count=1, flags=re.S)
            if N2 != N:
                open(np_, 'w', encoding='utf-8').write(N2)
    except Exception as ex:
        print('aviso nacional:', ex)


def po_status(k, G, last=None):
    """Estatus de playoffs para la página de equipo (cuando ya hay llave)."""
    po = [g for g in G if g['w'] in ('CF', 'SF', 'F')]
    if not po:
        return ''
    mine = [g for g in po if k in (g['a'], g['h'])]
    if not mine:
        if k == last:
            return f'<b>Desciende a la Conferencia Nacional para {YEAR + 1}</b>: terminó en último lugar de la temporada regular. <a href="/{YEAR + 1}/">Qué cambia en {YEAR + 1} →</a>'
        return f'No clasificó a playoffs en {YEAR}. <a href="/#playoffs">Ver la llave →</a>'
    lbl = {'CF': 'cuartos de final', 'SF': 'semifinales', 'F': 'la final'}
    for g in sorted(mine, key=lambda x: ['CF', 'SF', 'F'].index(x['w'])):
        if not g['fin']:
            o = g['h'] if g['a'] == k else g['a']
            return f'Juega {lbl[g["w"]]} contra {e(TEAMS[o]["n"])}. <a href="{game_path(g)}">Ver la previa del partido →</a>'
        won = (g['as'] > g['hs']) == (g['a'] == k)
        if not won:
            res = 'Finalista 2026' if g['w'] == 'F' else f'Eliminado en {lbl[g["w"]]}'
            o = g['h'] if g['a'] == k else g['a']
            my, ot = (g['as'], g['hs']) if g['a'] == k else (g['hs'], g['as'])
            return f'<b>{res}</b>: perdió {my}-{ot} contra {e(TEAMS[o]["n"])}. <a href="/#playoffs">Ver la llave →</a>'
        if g['w'] == 'F':
            return '<b>Campeón 2026 de los 14 Grandes.</b> <a href="/#playoffs">Ver la llave →</a>'
    return ''


try:
    HIST_EQ = {k: v for k, v in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'historial_equipos.json'), encoding='utf-8')).items() if not k.startswith('_')}
except Exception:
    HIST_EQ = {}


def season_line(k, G, rows, done):
    """Resumen 2026 que va arriba de la descripción del equipo (escrita en pretemporada)."""
    i = next(j for j, r in enumerate(rows) if r['k'] == k)
    r = rows[i]
    parts = [f"{r['w']}-{r['l']} en temporada regular ({i + 1}.º lugar)"]
    po = [g for g in G if g['w'] in ('CF', 'SF', 'F') and k in (g['a'], g['h'])]
    lbl = {'CF': 'cuartos de final', 'SF': 'semifinales', 'F': 'la final'}
    for g in sorted(po, key=lambda x: ['CF', 'SF', 'F'].index(x['w'])):
        o = TEAMS[g['h'] if g['a'] == k else g['a']]['n']
        if not g['fin']:
            parts.append(f"juega {lbl[g['w']]} contra {o}")
            break
        my, ot = (g['as'], g['hs']) if g['a'] == k else (g['hs'], g['as'])
        if my < ot:
            parts.append(('subcampeón: perdió la final ' if g['w'] == 'F' else f"eliminado en {lbl[g['w']]}: ") + f"{my}-{ot} ante {o}")
            break
        if g['w'] == 'F':
            parts.append(f"campeón: ganó la final {my}-{ot} a {o}")
    if done and not po:
        parts.append(f"desciende a la Conferencia Nacional para {YEAR + 1}" if i == len(rows) - 1 else 'no clasificó a playoffs')
    return f'<b>{YEAR}:</b> ' + ' · '.join(parts) + '.'


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
        done = all(g['fin'] for g in G if g['w'] not in ('P', 'CF', 'SF', 'F')) and any(g['w'] in ('CF', 'SF', 'F') for g in G)
        st = po_status(r['k'], G, rows[-1]['k'] if done else None)
        y = season_line(r['k'], G, rows, done)
        hy = HIST_EQ.get(r['k'], {})
        if hy:
            y += ('<span class="yhist">' + ''.join(f'<span><b>{yr}:</b> {e(t)}</span>' for yr, t in sorted(hy.items(), reverse=True))
                  + '<small>Años anteriores: <a href="https://www.clarosports.com/futbol-americano/calendario-completo-onefa-2025/" rel="noopener">Claro Sports</a> y <a href="https://receptor.com.mx/2023/09/17/standings-liga-mayor-onefa-2023/" rel="noopener">Receptor</a>.</small></span>')
        new = re.sub(r'<p class="y26">.*?</p>', '', new, count=1, flags=re.S)
        new = re.sub(r'(<h2 style="font-size:28px;margin-top:22px">El equipo</h2>\s*<div class="card">)', lambda m: m.group(1) + f'<p class="y26">{y}</p>', new, count=1)
        if st:
            new = re.sub(r'<p class="sub" style="margin-top:8px"(?: id="po-st")?>.*?</p>', lambda m: f'<p class="sub" style="margin-top:8px" id="po-st">{st}</p>', new, count=1, flags=re.S)
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
        T.append({'k': k, 'g': v(r, tc, 'grupo'), 'n': NFULL.get(k, v(r, tc, 'equipo') or k), 's': v(r, tc, 'escuela'),
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
    if any(x[0] == 'F' and x[3] is not None for x in po):
        cut = 'Tabla final de temporada regular'
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
    # los pendientes van donde caen por fecha (como en la portada: S9, Pend., S10)
    first = lambda w: min((parse_date(g['d'], g['t'], g['h']) or '9999') for g in G if g['w'] == w)
    if 'P' in order:
        pd_ = first('P')
        i = next((j for j, w in enumerate(reg) if first(w) > pd_), len(reg))
        reg = reg[:i] + ['P'] + reg[i:]
    weeks = reg + [w for w in ('CF', 'SF', 'F') if w in order]
    byw = {w: [g for g in G if g['w'] == w] for w in weeks}
    PEND[:] = [g for g in G if g['w'] == 'P']
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
        refresh_raw(G); refresh_embedded(local)
        M = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
        M2 = re.sub(r'let HISTY=\{.*?\};\n', lambda _: 'let HISTY=' + json.dumps(HIST_EQ, ensure_ascii=False, separators=(',', ':')) + ';\n', M, count=1)
        if M2 != M:
            open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8').write(M2)
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
