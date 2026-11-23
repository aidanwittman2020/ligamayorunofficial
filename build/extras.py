"""Cosas que se calculan con los perfiles ya armados (lo llama jugadores.py):

- Líderes de cada equipo sacados de FBA Stats (pase, tierra, recepción, defensa) → portada (INFO) y fichas de equipo.
- Estatus de lesión (pestaña Lesiones de la hoja) → perfil, ficha de equipo y portada.
- Páginas: Equipo ideal 2026, Prospectos 2026, Qué cambia en 2027 y el comparador de jugadores (+ stats.json).
"""
import csv, io, json, os, re, zlib

import generate as G
import avatar as AV

SITE, URL, YEAR = G.SITE, G.URL, G.YEAR
e = G.e if hasattr(G, 'e') else (lambda x: str(x).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;'))

ROLES = [('pase', 'passing', 'YDS'), ('tierra', 'rushing', 'YDS'), ('aire', 'receiving', 'YDS'), ('defensa', 'tackles', 'TAC')]


def n0(x):
    return f'{int(x or 0):,}'


def fnum(x):
    try:
        return float(str(x).replace(',', '')) if str(x).strip() not in ('', 'None') else None
    except ValueError:
        return None


def build_xs(P):
    """Estadísticas en un solo formato: 14 Grandes = tablas completas de FBA (p['mb']); Nacional = categorías de líderes FBA."""
    for p in P:
        if p['liga'] == '14G':
            p['xs'] = p.get('mb') or {}
            continue
        cats = (p.get('seasons', {}).get(str(YEAR)) or {}).get('cats', {})
        x = {}
        g = lambda c, k: fnum(cats[c].get(k)) if c in cats else None
        if 'QB' in cats:
            x['passing'] = {'YDS': g('QB', 'YDS'), 'TD': g('QB', 'TD')}
        if 'RB' in cats:
            x['rushing'] = {'YDS': g('RB', 'YDS'), 'TD': g('RB', 'TD')}
        if 'WR' in cats:
            x['receiving'] = {'YDS': g('WR', 'YDS'), 'REC': g('WR', 'REC'), 'TD': g('WR', 'TD')}
        if 'TK' in cats or 'SK' in cats:
            x['tackles'] = {'TAC': g('TK', 'TACK') or g('SK', 'TACK'), 'SACKS': g('SK', 'SACK') or g('TK', 'SACK')}
        if 'IN' in cats:
            x['ints'] = {'INT': g('IN', 'INT')}
        if 'PT' in cats or 'FG' in cats:
            x['kickers'] = {'PTS': g('PT', 'PTS') or g('FG', 'PTS'), 'FG': g('FG', 'FG') or g('PT', 'FG')}
        p['xs'] = {k: v for k, v in x.items() if any(y is not None for y in v.values())}


def line(p, role):
    m = p['xs']
    if role == 'pase':
        v = m['passing']
        return f"{n0(v.get('YDS'))} yds de pase · {n0(v.get('TD'))} TD"
    tdt = f" · {n0(m['tdt']['TD'])} TD totales" if m.get('tdt') else ''
    if role == 'tierra':
        v = m['rushing']
        return f"{n0(v.get('YDS'))} yds por tierra" + (f" · {n0(v.get('TD'))} TD" if v.get('TD') is not None else tdt)
    if role == 'aire':
        v = m['receiving']
        return (f"{n0(v.get('REC'))} recepciones · " if v.get('REC') else '') + f"{n0(v.get('YDS'))} yds" + (f" · {n0(v.get('TD'))} TD" if v.get('TD') is not None else tdt)
    v = m.get('tackles') or {}
    s = f"{n0(v.get('TAC'))} tackles" if v.get('TAC') else ''
    if v.get('SACKS'):
        s += (' · ' if s else '') + f"{n0(v['SACKS'])} sack" + ("" if v['SACKS'] == 1 else "s")
    if m.get('ints', {}).get('INT'):
        s += (' · ' if s else '') + f"{n0(m['ints']['INT'])} INT"
    return s


def team_leaders(P):
    """Mejor pasador, corredor, receptor y tackleador de cada equipo según FBA Stats (temporada regular)."""
    L = {}
    for k in G.TEAMS:
        ps = [p for p in P if p['liga'] == '14G' and p['team'] == k and p.get('xs')]
        out = []
        for role, cat, col in ROLES:
            c = [p for p in ps if cat in p['xs'] and (p['xs'][cat].get(col) or 0) > 0]
            if not c:
                continue
            b = max(c, key=lambda p: p['xs'][cat].get(col) or 0)
            out.append({'p': b, 'role': role, 'line': line(b, role)})
        L[k] = out
    return L


def load_les(local):
    """Pestaña Lesiones: Equipo, Numero, Jugador, Estatus, Nota."""
    try:
        txt = G.fetch('lesiones', local)
    except Exception as ex:
        print('aviso lesiones:', ex)
        return {}
    out = {}
    R = list(csv.reader(io.StringIO(txt)))
    if not R:
        return out
    H = [G.norm(h) for h in R[0]]
    c = lambda n: H.index(n) if n in H else -1
    for r in R[1:]:
        v = lambda n: (r[c(n)].strip() if 0 <= c(n) < len(r) else '')
        k, num, st = v('equipo').upper(), v('numero').lstrip('#'), v('estatus')
        if k and num.isdigit() and st:
            out[(k, int(num))] = (st, v('nota'), v('jugador'))
    return out


def apply_les(P, LES):
    for p in P:
        p['les'] = None
        x = LES.get((p['team'], p['n']))
        if x and (not x[2] or G.norm(x[2]).split()[0] == G.norm(p['name']).split()[0]):
            p['les'] = x[:2]


def badge(les):
    if not les:
        return ''
    return f'<span class="inj" title="{e(les[1])}">{e(les[0])}</span>'


# ---------------------------------------------------------------- portada y fichas de equipo
def lx_data(P):
    """Para Líderes: quién tiene solo TD totales y la lista completa de FBA para no dejar fuera a los empatados."""
    ps = [p for p in P if p['liga'] == '14G' and p.get('mb')]
    tdt = [f"{p['team']}|{p['n']}" for p in ps if p['mb'].get('tdt')]
    more = {}
    for cid, cat, col in (('in', 'ints', 'INT'), ('sk', 'tackles', 'SACKS'), ('tk', 'tackles', 'TAC')):
        r = sorted([p for p in ps if (p['mb'].get(cat) or {}).get(col)], key=lambda p: -p['mb'][cat][col])[:12]
        more[cid] = [[p['name'], p['team'], p['n'], int(p['mb'][cat][col])] for p in r]
    return {'tdt': tdt, 'more': more}


def patch_home(L, LES, P=None):
    fp = os.path.join(SITE, 'index.html')
    M = open(fp, encoding='utf-8').read()
    m = re.search(r'const INFO=(\{.*?\});\n', M, re.S)
    I = json.loads(m.group(1))
    for k, lst in L.items():
        if k in I and len(I[k]) > 4 and lst:
            I[k][4] = [[x['p']['name'], x['p']['pos'], x['p']['n'], x['line'], x['role']] for x in lst]
    M2 = M[:m.start(1)] + json.dumps(I, ensure_ascii=False) + M[m.end(1):]
    les = {f'{k}|{n}': [s, nt] for (k, n), (s, nt, _) in LES.items()}
    M2 = re.sub(r'let LES=\{.*?\};', lambda _: 'let LES=' + json.dumps(les, ensure_ascii=False) + ';', M2, count=1)
    if P is not None:
        M2 = re.sub(r'let LX=\{.*?\};\n', lambda _: 'let LX=' + json.dumps(lx_data(P), ensure_ascii=False, separators=(',', ':')) + ';\n', M2, count=1)
    if M2 != M:
        open(fp, 'w', encoding='utf-8').write(M2)
        return 1
    return 0


def patch_game_pages(L):
    """Jugadores clave (líderes FBA + estatus de lesión) en la página de los partidos por jugarse."""
    n = 0
    root = os.path.join(SITE, 'juegos', str(YEAR))
    for d, _, files in os.walk(root):
        if 'index.html' not in files:
            continue
        fp = os.path.join(d, 'index.html')
        h = open(fp, encoding='utf-8').read()
        m = re.search(r'<!--KP:([A-Z]+):([A-Z]+)-->', h)
        if not m:
            continue
        a, hm = m.group(1), m.group(2)
        by = lambda k, r: next((x for x in L.get(k, []) if x['role'] == r), None)
        cell = lambda x: (f'<a href="{x["p"]["url"]}">{e(x["p"]["name"])}</a>{badge(x["p"].get("les"))}<small>#{x["p"]["n"]} · {e(x["line"])}</small>' if x else '<small>—</small>')
        rows = ''.join(f'<div class="kpg-r"><div>{cell(by(a, r))}</div><span>{LBL[r]}</span><div>{cell(by(hm, r))}</div></div>' for r in ('pase', 'tierra', 'aire', 'defensa'))
        les = [x['p'] for k in (a, hm) for x in L.get(k, []) if x['p'].get('les')]
        note = ''.join(f'<p class="sub" style="margin:8px 0 0"><span class="inj">{e(p["les"][0])}</span> {e(p["name"])}: {e(p["les"][1])}</p>' for p in les)
        blk = (f'<h2 style="font-size:26px;margin-top:22px">Jugadores clave</h2><div class="card kpg"><div class="kpg-r kpg-h"><b>{e(G.TEAMS[a]["n"])}</b><span></span><b>{e(G.TEAMS[hm]["n"])}</b></div>{rows}{note}</div>'
               '<p class="note">Líderes de cada equipo en temporada regular según FBA Stats.</p>')
        h2 = re.sub(r'<!--KP:[A-Z]+:[A-Z]+-->.*?<!--/KP-->', lambda _: m.group(0) + blk + '<!--/KP-->', h, count=1, flags=re.S)
        if h2 != h:
            open(fp, 'w', encoding='utf-8').write(h2)
            n += 1
    return n


STAR_RX = re.compile(r'(<div class="stars" id="stars" data-k="([A-Z]+)">)(?:<div class="star">.*?</div></div></div>)*', re.S)
LBL = {'pase': 'Pase', 'tierra': 'Tierra', 'aire': 'Recepción', 'defensa': 'Defensa'}


def patch_team_stars(L):
    n = 0
    for k, s in G.SLUG.items():
        fp = os.path.join(SITE, 'equipos', s, 'index.html')
        if not os.path.exists(fp) or not L.get(k):
            continue
        h = open(fp, encoding='utf-8').read()
        cards = ''.join(f'<div class="star"><span class="jn num">#{x["p"]["n"]}</span><div><b><a href="{x["p"]["url"]}" style="color:inherit">{e(x["p"]["name"])}</a>{badge(x["p"].get("les"))}</b>'
                        f'<div class="loc">{e(x["p"]["pos"])} · {LBL[x["role"]]}</div><div class="sl">{e(x["line"])}</div></div></div>' for x in L[k])
        h2 = STAR_RX.sub(lambda m: m.group(1) + cards, h, count=1)
        # ya no se leen de la pestaña Jugadores: se quita el script que los reemplazaba en vivo
        h2 = re.sub(r"<script>\(function\(\)\{const el=document\.getElementById\('stars'\).*?</script>", '', h2, count=1, flags=re.S)
        h2 = h2.replace('Los líderes del equipo según las estadísticas de Uriel González (FBA Stats).',
                        'Los líderes del equipo en pase, tierra, recepción y tackles según FBA Stats (Uriel González), temporada regular.')
        if h2 != h:
            open(fp, 'w', encoding='utf-8').write(h2)
            n += 1
    return n


# ---------------------------------------------------------------- páginas nuevas
def avatar(p, J, size=84):
    BIG = {'OL', 'DL', 'OT', 'OG', 'C', 'DT', 'DE', 'NT', 'G', 'T'}
    SKILL = {'QB', 'WR', 'CB', 'S', 'DB', 'FS', 'SS', 'K', 'P', 'LS', 'KR'}
    build = 'big' if p['pos'] in BIG else 'skill' if p['pos'] in SKILL else 'mid'
    POSES = {'QB': ('ball_up', 'ball_r', 'two_hands'), 'WR': ('ball_up', 'ball_r', 'ball_l', 'tuck'), 'TE': ('tuck', 'ball_r', 'ball_up'), 'RB': ('tuck', 'ball_r', 'ball_l', 'two_hands')}
    ops = POSES.get(p['pos'])
    pose = ops[zlib.crc32(p['name'].encode('utf-8')) % len(ops)] if ops else None
    return AV.svg(p['n'], AV.uniform(p['liga'], p['team']), size, seed=p['name'], pose=pose, build=build,
                  skin=AV.SKIN_DARK if (p['team'], p['n']) in J.SKIN_FIX else None, title=f'Muñequito de {e(p["name"])}')


def val(p, cat, col):
    return (p.get('xs', {}).get(cat) or {}).get(col) or 0


def pick(P, pos, n, key, used):
    c = [p for p in P if p['pos'] in pos and p.get('xs') and key(p)[0] > 0 and id(p) not in used]
    c.sort(key=key, reverse=True)
    r = c[:n]
    used.update(id(p) for p in r)
    return r


CONF = {'14G': ('14 Grandes', 'los 14 Grandes', ''), 'NAC': ('Conferencia Nacional', 'la Conferencia Nacional', 'nacional/')}


def conf_switch(base, liga):
    on = lambda l: ' class="on"' if l == liga else ''
    return (f'<div class="cswitch" role="tablist"><a href="{base}"{on("14G")}>14 Grandes</a><a href="{base}nacional/"{on("NAC")}>Nacional</a></div>')


def ideal_page(P, J, liga='14G'):
    used = set()
    P = [p for p in P if p['liga'] == liga]
    OFF = [('QB', pick(P, {'QB'}, 1, lambda p: (val(p, 'passing', 'YDS'), val(p, 'passing', 'TD')), used), lambda p: line(p, 'pase')),
           ('RB', pick(P, {'RB', 'FB', 'HB'}, 2, lambda p: (val(p, 'rushing', 'YDS'), val(p, 'rushing', 'TD')), used), lambda p: line(p, 'tierra')),
           ('WR', pick(P, {'WR'}, 3, lambda p: (val(p, 'receiving', 'YDS'), val(p, 'receiving', 'TD')), used), lambda p: line(p, 'aire')),
           ('TE', pick(P, {'TE', 'PB', 'HB'}, 1, lambda p: (val(p, 'receiving', 'YDS'), val(p, 'receiving', 'TD')), used), lambda p: line(p, 'aire'))]
    dl = lambda p: f"{n0(val(p, 'tackles', 'SACKS'))} sacks" + (f" · {n0(val(p, 'tackles', 'TAC'))} tackles" if val(p, 'tackles', 'TAC') else '')
    db = lambda p: f"{n0(val(p, 'ints', 'INT'))} INT" + (f" · {n0(val(p, 'tackles', 'TAC'))} tackles" if val(p, 'tackles', 'TAC') else '')
    DEF = [('DL', pick(P, {'DL', 'DE', 'DT', 'NT'}, 4, lambda p: (val(p, 'tackles', 'SACKS'), val(p, 'tackles', 'TAC')), used), dl),
           ('LB', pick(P, {'LB'}, 3, lambda p: (val(p, 'tackles', 'TAC'), val(p, 'tackles', 'SACKS')), used), lambda p: line(p, 'defensa')),
           ('DB', pick(P, {'CB', 'S', 'DB', 'FS', 'SS'}, 4, lambda p: (val(p, 'ints', 'INT'), val(p, 'tackles', 'TAC')), used), db)]
    kl = lambda p: ' · '.join(x for x in [val(p, 'kickers', 'PTS') and f"{n0(val(p, 'kickers', 'PTS'))} puntos", val(p, 'kickers', 'PAT') and f"{n0(val(p, 'kickers', 'PAT'))} PAT",
                                           val(p, 'kickers', 'FG') and f"{n0(val(p, 'kickers', 'FG'))} goles de campo"] if x)
    ST = [('K', pick(P, {'K', 'P'}, 1, lambda p: (val(p, 'kickers', 'PTS') or val(p, 'kickers', 'FG'), val(p, 'kickers', 'FG')), used), kl)]

    def grid(title, groups):
        cards = ''
        for pos, ps, fn in groups:
            for p in ps:
                num = f' · #{p["n"]}' if p['n'] is not None else ''
                cards += (f'<a class="xi" href="{p["url"]}"><div class="xa">{avatar(p, J)}</div><div><span class="xp">{pos}</span><b>{e(p["name"])}</b>{badge(p.get("les"))}'
                          f'<small>{e(p["T"]["n"])}{num}</small><em>{e(fn(p))}</em></div></a>')
        return f'<h2 style="font-size:26px;margin-top:22px">{title}</h2><div class="xig">{cards}</div>' if cards else ''

    name, of, sub = CONF[liga]
    path = f'/equipo-ideal-{YEAR}/{sub}'
    nav, ld_b = G.crumbs([('Inicio', '/' if liga == '14G' else '/nacional/'), (f'Equipo ideal {YEAR}' + ('' if liga == '14G' else ' · Nacional'), None)])
    body = nav + f'<h1 class="gm-h1">Equipo ideal {YEAR} de {of}</h1>' + conf_switch(f'/equipo-ideal-{YEAR}/', liga)
    body += ('<p class="gm-meta">Selección automática con los números de la temporada regular (FBA Stats). No es un premio oficial de la ONEFA: '
             'se escoge al líder de cada posición.</p>')
    body += grid('Ofensiva', OFF) + grid('Defensiva', DEF) + grid('Equipos especiales', ST)
    extra = ('<li>En la Nacional solo se publican los primeros lugares de cada categoría, así que algunas posiciones pueden quedar vacías. '
             'Los uniformes de los muñequitos de la Nacional son provisionales.</li>') if liga == 'NAC' else ''
    body += ('<div class="card" style="margin-top:14px"><b>¿Cómo se escoge?</b><ul class="pv"><li>QB, RB, WR y TE: más yardas en su categoría (desempate por TD).</li>'
             '<li>Línea defensiva: más sacks (desempate por tackles). Linebackers: más tackles. Secundaria: más intercepciones (desempate por tackles).</li>'
             f'<li>Pateador: más puntos.</li><li>No hay línea ofensiva porque no existen estadísticas públicas de linieros ofensivos.</li>{extra}</ul></div>')
    body += '<p class="note">Estadísticas: Uriel González (FBA Stats), publicadas también por <a href="https://www.modoblitz.com/estadisticas-onefa" rel="noopener">Modo Blitz</a>.' + (' Posiciones: Guía ONEFA 2026 de Lucio Trucíos.' if liga == '14G' else '') + '</p>'
    return path, G.page(f'Equipo ideal {YEAR} de la Liga Mayor ONEFA ({name}) | Liga Mayor Unofficial',
                        f'El equipo ideal de {of} {YEAR} según las estadísticas de la temporada regular: QB, corredores, receptores, línea defensiva, linebackers y secundaria.',
                        path, J.CSS + body, [ld_b])


AGE_MIN, AGE_MAX = 24, 25
DRAFT_YEAR = YEAR + 1
DRAFT = f'Draft LFA {DRAFT_YEAR}'
POS_ORD = ['QB', 'RB', 'FB', 'WR', 'TE', 'OL', 'DL', 'DE', 'LB', 'CB', 'DB', 'S', 'SS', 'FS', 'K', 'P']


def load_draft(P):
    """build/data/draft_2027.json: declarados elegibles y top 5 por posición (MEXFBA). Liga los nombres con el roster."""
    fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', f'draft_{DRAFT_YEAR}.json')
    for p in P:
        p['draft'] = []
    if not os.path.exists(fp):
        return {'elegibles': [], 'rankings': [], 'elegibles_cc': [], 'fuente': ['', '']}
    D = json.load(open(fp, encoding='utf-8'))
    nz = lambda x: G.norm(x).replace('z', 's').split()

    def find(x, strict=False):
        c = [p for p in P if p['liga'] == x.get('liga') and p['team'] == x['equipo'] and (x.get('numero') is None or p['n'] == x['numero'])
             and all(w in nz(p['name']) for w in nz(x['jugador']))]
        if x.get('numero') is not None and not c and not strict:
            c = [p for p in P if p['liga'] == x.get('liga') and p['team'] == x['equipo'] and p['n'] == x['numero']]
        return c[0] if len(c) == 1 else None
    for x in D['elegibles']:
        x['p'] = find(x)
        if x['p']:
            x['p']['draft'].append(f'Declarado elegible al {DRAFT}')
    for r in D['rankings']:
        for i, x in enumerate(r['lista']):
            x['p'] = find(x)
            if x['p']:
                x['p']['draft'].append(f'Top 5 clase {YEAR} · {r["titulo"]}: #{i + 1}')
    for x in D.setdefault('elegibles_cc', []):
        x['p'] = find(x, True)
        if x['p'] and not x['p']['draft']:
            x['p']['draft'].append(f'En la lista de elegibles al {DRAFT} (Cover Cero)')
    return D


def tname(x):
    if x.get('p'):
        return x['p']['T']['n']
    if x.get('liga') == '14G' and x['equipo'] in G.TEAMS:
        return G.TEAMS[x['equipo']]['n']
    return G.NFULL.get(x['equipo'], x['equipo'])


def draft_card(x, J, pos='', rank=None):
    p = x.get('p')
    if p:
        st = next((line(p, r) for c, r in (('passing', 'pase'), ('rushing', 'tierra'), ('receiving', 'aire'), ('tackles', 'defensa'), ('ints', 'defensa')) if c in (p.get('xs') or {})), '')
        age = J.phys(p)[0]
        meta = ' · '.join(z for z in [p['pos'] or pos, p['n'] is not None and f'#{p["n"]}', age and f'{age} años'] if z)
        return (f'<a class="xi" href="{p["url"]}"><div class="xa">{avatar(p, J)}</div><div>{f"<span class=xp>{rank}</span>" if rank else ""}<b>{e(p["name"])}</b>{badge(p.get("les"))}'
                f'<small>{e(p["T"]["n"])} · {e(meta)}</small>{f"<em>{e(st)}</em>" if st else ""}</div></a>')
    fake = {'liga': x.get('liga') or 'NAC', 'team': x['equipo'], 'n': None, 'name': x['jugador'], 'pos': pos}
    return (f'<div class="xi"><div class="xa">{avatar(fake, J)}</div><div>{f"<span class=xp>{rank}</span>" if rank else ""}<b>{e(x["jugador"])}</b>'
            f'<small>{e(tname(x))}{" · " + pos if pos else ""}</small><em>Sin perfil en el sitio</em></div></div>')


def draft_html(D, J):
    out = ''
    el = D['elegibles']
    if el:
        out += (f'<h2 style="font-size:26px;margin-top:18px">Declarados elegibles al {DRAFT}</h2>'
                f'<p class="gm-meta">Jugadores que ya anunciaron que entran al {DRAFT}.</p><div class="xig">'
                + ''.join(draft_card(x, J, x.get('pos', '')) for x in el) + '</div>')
    rk = [(r, list(enumerate(r['lista']))) for r in D['rankings']]
    rk = [(r, L) for r, L in rk if L]
    if rk:
        out += f'<h2 style="font-size:26px;margin-top:22px">Top 5 clase {YEAR} por posición</h2>'
        for r, L in rk:
            out += f'<h3 style="font-size:19px;margin:14px 0 6px">{e(r["titulo"])}</h3><div class="xig">' + ''.join(draft_card(x, J, r['pos'], f'{i + 1}.º') for i, x in L) + '</div>'
    if out:
        out += f'<p class="note">Declarados y rankings: <a href="{e(D["fuente"][1])}" rel="noopener">{e(D["fuente"][0])}</a>. Números: FBA Stats.</p>'
    shown = {id(x['p']) for x in el + [y for r in D['rankings'] for y in r['lista']] if x.get('p')}
    cc = [x for x in D.get('elegibles_cc', []) if not (x.get('p') and id(x['p']) in shown)]
    if cc:
        out += (f'<h2 style="font-size:26px;margin-top:22px">Lista de elegibles al {DRAFT}</h2>'
                f'<p class="gm-meta">{len(cc)} jugadores más de la Liga Mayor en la lista de elegibles. Los que no tienen perfil aún no aparecen en nuestros rosters.</p>')
        grp = {}
        for x in cc:
            grp.setdefault((x.get('p') or {}).get('pos') or x.get('pos', ''), []).append(x)
        for ps in sorted(grp, key=lambda k: (POS_ORD.index(k) if k in POS_ORD else 99, k)):
            L = sorted(grp[ps], key=lambda x: (not x.get('p'), x['liga'] != '14G', G.norm(x['jugador'])))
            out += f'<h3 style="font-size:19px;margin:14px 0 6px">{e(ps)} <small style="color:var(--muted)">({len(L)})</small></h3><div class="xig">' + ''.join(draft_card(x, J, x.get('pos', '')) for x in L) + '</div>'
        fc = D.get('fuente_cc') or ['', '']
        out += f'<p class="note">Lista de elegibles: <a href="{e(fc[1])}" rel="noopener">{e(fc[0])}</a>. Equipo, número y posición: rosters de los equipos.</p>'
    return out


def prospects_page(P, J, D=None):
    """Una sola página de prospectos (14 Grandes y Nacional juntos)."""
    CATS = [('passing', 'YDS', 'pase', 10), ('rushing', 'YDS', 'tierra', 15), ('receiving', 'YDS', 'aire', 15), ('tackles', 'TAC', 'defensa', 20),
            ('tackles', 'SACKS', 'defensa', 10), ('ints', 'INT', 'defensa', 10)]
    LBL = {('passing', 'YDS'): 'en yardas de pase', ('rushing', 'YDS'): 'en yardas por tierra', ('receiving', 'YDS'): 'en yardas por recepción',
           ('tackles', 'TAC'): 'en tackles', ('tackles', 'SACKS'): 'en sacks', ('ints', 'INT'): 'en intercepciones'}
    rows = []
    for liga, of in (('14G', 'de los 14 Grandes'), ('NAC', 'de la Nacional')):
        top = {}
        ps = [p for p in P if p['liga'] == liga and p.get('xs')]
        for cat, col, role, n in CATS:
            r = sorted([p for p in ps if val(p, cat, col) > 0], key=lambda p: val(p, cat, col), reverse=True)[:n]
            for i, p in enumerate(r):
                top.setdefault(id(p), (p, role, i + 1, cat, col))
        for p, role, rk, cat, col in top.values():
            age, h, w = J.phys(p)
            if not age or not AGE_MIN <= int(age) <= AGE_MAX or p.get('draft'):
                continue   # los que ya salen como elegibles o en el top 5 no se repiten aquí
            ln = line(p, role) if role != 'defensa' or col == 'TAC' else (f"{n0(val(p, cat, col))} " + ('sacks' if col == 'SACKS' else 'INT'))
            rows.append((rk, p, age, h, w, f'{rk}.º {of} {LBL[(cat, col)]}', ln))
    rows.sort(key=lambda x: (x[0], -int(x[2])))
    tr = ''.join(f'<tr><td class="team"><a href="{p["url"]}">{e(p["name"])}</a>{badge(p.get("les"))}<small style="display:block;color:var(--muted)">{e(p["T"]["n"])}{" · #" + str(p["n"]) if p["n"] is not None else ""}</small></td>'
                 f'<td><span class="abbr">{e(p["pos"])}</span></td><td class="num">{age}</td><td class="num">{h or ""}</td><td class="num">{w or ""}</td>'
                 f'<td>{e(rk_)}<small style="display:block;color:var(--muted)">{e(ln)}</small></td></tr>' for _, p, age, h, w, rk_, ln in rows)
    path = f'/prospectos-{YEAR}/'
    nav, ld_b = G.crumbs([('Inicio', '/'), ('Prospectos', None)])
    body = nav + f'<h1 class="gm-h1">Prospectos rumbo al {DRAFT}</h1>'
    body += '<p class="gm-meta">Los mejores prospectos de la Liga Mayor, de los 14 Grandes y de la Conferencia Nacional. La lista crece conforme más jugadores se declaren elegibles.</p>'
    body += draft_html(D or {'elegibles': [], 'rankings': []}, J)
    if tr:
        body += f'<h2 style="font-size:26px;margin-top:22px">Otros veteranos a seguir ({AGE_MIN} y {AGE_MAX} años)</h2>'
        body += ('<div class="card" style="margin:8px 0 12px"><b>Ojo:</b> esta parte no es una lista oficial: son jugadores de '
                 f'{AGE_MIN} y {AGE_MAX} años entre los líderes de FBA Stats. A esa edad la mayoría ya agotó su elegibilidad o terminó la maestría. '
                 'La edad sale de los rosters publicados por los equipos.</div>')
        body += '<div class="tbl-box"><table class="roster"><thead><tr><th>Jugador</th><th>Pos.</th><th>Edad</th><th>Est.</th><th>Peso</th><th>Por qué</th></tr></thead><tbody>' + tr + '</tbody></table></div>'
    body += '<p class="note">Estadísticas: Uriel González (FBA Stats). Edad, estatura (m) y peso (kg): rosters publicados por los equipos.</p>'
    return path, G.page(f'Prospectos al {DRAFT}: elegibles de la Liga Mayor ONEFA | Liga Mayor Unofficial',
                        f'Prospectos de la Liga Mayor ONEFA rumbo al {DRAFT}: declarados elegibles, top 5 por posición, lista completa de elegibles y veteranos líderes en estadísticas.', path, J.CSS + body, [ld_b])


REDIRECT = '<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><link rel="canonical" href="{u}"><meta http-equiv="refresh" content="0;url={u}"><a href="{u}">{u}</a>'


def y2027_page(J):
    path = '/2027/'
    nav, ld_b = G.crumbs([('Inicio', '/'), ('Qué cambia en 2027', None)])
    t14 = sorted([v['n'] for k, v in G.TEAMS.items() if k != 'CET'] + ['Leones Anáhuac Querétaro'], key=lambda x: G.norm(x))
    body = nav + '<h1 class="gm-h1">Qué cambia en la Liga Mayor 2027</h1>'
    body += '<p class="gm-meta">Ascenso y descenso entre los 14 Grandes y la Conferencia Nacional al cerrar la temporada 2026.</p>'
    body += ('<div class="xig2"><div class="card"><span class="xp">Sube</span><h3 style="margin:4px 0">Leones Anáhuac Querétaro</h3>'
             '<p class="sub" style="margin:0">Campeones de la Conferencia Nacional 2026: vencieron 24-21 en tiempo extra a Águilas UACH en la final. '
             'El campeón de la Nacional gana el derecho de jugar en los 14 Grandes la siguiente temporada.</p></div>'
             '<div class="card"><span class="xp dn">Baja</span><h3 style="margin:4px 0">Zorros CETYS</h3>'
             '<p class="sub" style="margin:0">Terminaron últimos de los 14 Grandes con 0-9. El último lugar de la tabla desciende a la Conferencia Nacional.</p></div></div>')
    body += '<h2 style="font-size:26px;margin-top:22px">Los 14 Grandes en 2027</h2><div class="pl2">' + ''.join(f'<span class="tchip">{e(n)}</span>' for n in t14) + '</div>'
    body += ('<p class="sub" style="margin-top:12px">Zorros CETYS había subido para 2025 tras ganar la Conferencia Nacional 2024. '
             'Ver <a href="/nacional/#inicio">la final de la Nacional</a> y <a href="/#tabla">la tabla final de los 14 Grandes</a>.</p>')
    body += ('<p class="note">Fuentes: resultados capturados en este sitio; reglas de ascenso y descenso según '
             '<a href="https://www.clarosports.com/futbol-americano/calendario-completo-onefa-2026/" rel="noopener">Claro Sports</a> y '
             '<a href="https://www.publimetro.com.mx/queretaro/2026/09/01/leones-anahuac-queretaro-apunta-al-campeonato-de-la-conferencia-nacional-de-onefa/" rel="noopener">Publimetro</a>. '
             'Los grupos y el calendario 2027 los anuncia la ONEFA más adelante.</p>')
    return path, G.page('Liga Mayor ONEFA 2027: quién sube y quién baja | Liga Mayor Unofficial',
                        'Leones Anáhuac Querétaro sube a los 14 Grandes y Zorros CETYS baja a la Conferencia Nacional para la temporada 2027 de la Liga Mayor ONEFA.',
                        path, J.CSS + body, [ld_b])


SKEYS = {'passing': ['JJ', 'COMP', 'INT', 'PCT', 'YDS', 'TD', 'INTC'], 'rushing': ['JJ', 'ACA', 'YDS', 'PROM', 'TD'], 'receiving': ['JJ', 'REC', 'YDS', 'PROM', 'TD'],
         'tackles': ['JJ', 'TAC', 'SACKS', 'FR'], 'ints': ['INT', 'YDS'], 'kickers': ['PAT', 'PTS', 'FG'], 'tdt': ['TD']}


def stats_json(P, J):
    out = []
    for p in P:
        age, h, w = J.phys(p)
        mb = {c: [p['xs'][c].get(k) for k in ks] for c, ks in SKEYS.items() if c in (p.get('xs') or {}) and c != 'tdt'}
        # lo que FBA no trae se completa con Cover Cero (mismas columnas)
        cc = p.get('cc') or {}
        pick_ = lambda v, idx: [None if i is None or i >= len(v) else v[i] for i in idx]
        if 'passing' in cc and 'passing' not in mb:
            v = pick_(cc['passing'], [0, 1, 2, 3, 4, 6, 7])
            v[3] = v[3] / 100 if v[3] is not None else None
            mb['passing'] = v
        for c in ('rushing', 'receiving'):
            if c in cc and c not in mb:
                mb[c] = pick_(cc[c], [0, 1, 2, 3, 4])
        if 'defense' in cc:
            if 'tackles' not in mb:
                mb['tackles'] = pick_(cc['defense'], [0, 1, 4, None])
            if 'ints' not in mb and cc['defense'][6]:
                mb['ints'] = [cc['defense'][6], None]
        # TD anotados (tierra + recepción); si FBA solo da el total, se usa ese
        xt = (p.get('xs') or {}).get('tdt')
        tr = (mb.get('rushing') or [None] * 5)[4]
        tc = (mb.get('receiving') or [None] * 5)[4]
        tot = xt['TD'] if xt else ((tr or 0) + (tc or 0) if (tr is not None or tc is not None) else None)
        if tot is not None:
            mb['tdt'] = [tot]
        if not (mb or age or h or w):
            continue
        out.append([p['name'], p['team'], p['T']['n'], p['pos'], p['n'] if p['n'] is not None else '', int(age) if age else None, float(h) if h else None, int(w) if w else None, p['url'], mb, p['liga']])
    js = json.dumps({'keys': SKEYS, 'p': out}, ensure_ascii=False, separators=(',', ':'))
    fp = os.path.join(SITE, 'jugadores', 'stats.json')
    if not os.path.exists(fp) or open(fp, encoding='utf-8').read() != js:
        open(fp, 'w', encoding='utf-8').write(js)


COMPARE_JS = r'''<script>
const nz=s=>String(s).normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();const E=x=>String(x??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const ROWS=[['Físico',[['Edad',p=>p[5],0],['Estatura (m)',p=>p[6]==null?null:Number(p[6]).toFixed(2),0],['Peso (kg)',p=>p[7],0]]],
['Pase',[['Yardas','passing',4],['TD','passing',5],['Completos','passing',1],['Intentos','passing',2],['% completos','passing',3,v=>(v*100).toFixed(1)],['Intercepciones','passing',6,null,1]]],
['Tierra',[['Yardas','rushing',2],['Acarreos','rushing',1],['Promedio','rushing',3,v=>v.toFixed(1)],['TD','rushing',4]]],
['Recepción',[['Yardas','receiving',2],['Recepciones','receiving',1],['Promedio','receiving',3,v=>v.toFixed(1)],['TD','receiving',4]]],
['Defensa',[['Tackles','tackles',1],['Sacks','tackles',2],['Balones recuperados','tackles',3],['Intercepciones','ints',0]]],
['Touchdowns',[['TD anotados (tierra + recepción)','tdt',0]]],
['Pateo',[['Puntos','kickers',1],['PAT','kickers',0],['Goles de campo','kickers',2]]]];
let D=null;const sel=[null,null];
function get(p,r){if(!p)return null;if(typeof r[1]==='function')return r[1](p);const c=p[9][r[1]];return c?c[r[2]]:null}
function draw(){const A=sel[0],B=sel[1],o=document.getElementById('cmp');if(!A&&!B){o.innerHTML='';return}
 let h=`<table class="cmpx"><thead><tr><th>${A?`<a href="${A[8]}">${E(A[0])}</a><small>${E(A[2])} · ${E(A[3])} #${A[4]}</small>`:''}</th><th></th><th>${B?`<a href="${B[8]}">${E(B[0])}</a><small>${E(B[2])} · ${E(B[3])} #${B[4]}</small>`:''}</th></tr></thead><tbody>`;
 for(const[g,rs]of ROWS){const lines=rs.map(r=>{const a=get(A,r),b=get(B,r);if(a==null&&b==null)return'';
  const merged=p=>p&&p[9].tdt&&p[9][r[1]]&&p[9][r[1]][4]==null;if((r[1]==='rushing'||r[1]==='receiving')&&r[2]===4&&(merged(A)||merged(B)))return'';const f=v=>v==null?'—':r[3]?r[3](v):(typeof r[1]==='function'?v:Math.round(v).toLocaleString('es-MX'));
  const lowGood=r[4],win=a!=null&&b!=null&&a!==b&&r[1]!=='function'&&typeof r[1]!=='function'?((a>b)!==!!lowGood?0:1):-1;
  return`<tr><td class="${win===0?'w':''}">${f(a)}</td><th>${r[0]}</th><td class="${win===1?'w':''}">${f(b)}</td></tr>`}).join('');
  if(lines)h+=`<tr class="g"><td colspan="3">${g}</td></tr>`+lines}
 o.innerHTML=h+'</tbody></table><p class="note">Temporada regular · FBA Stats; lo que FBA no publica viene de Cover Cero. En verde, el mejor número de los dos. Si FBA no separa los TD por tierra y por recepción, solo aparece el total.</p>';
 try{history.replaceState(null,'','?a='+encodeURIComponent(A?A[8]:'')+'&b='+encodeURIComponent(B?B[8]:''))}catch(e){}}
function box(i){const q=document.getElementById('q'+i),r=document.getElementById('r'+i);
 q.addEventListener('input',()=>{const t=nz(q.value.trim());if(t.length<2||!D){r.innerHTML='';return}const ws=t.split(/\s+/);
  const m=D.filter(p=>{const s=nz(p[0]+' '+p[2]+' '+p[3]+' #'+p[4]+(p[10]==='NAC'?' nacional':' 14 grandes'));return ws.every(w=>s.includes(w))}).slice(0,8);
  r.innerHTML=m.map((p,j)=>`<button type="button" data-j="${D.indexOf(p)}"><b>${E(p[0])}</b><small>${E(p[2])}${p[10]==='NAC'?' (Nacional)':''} · ${E(p[3])} #${p[4]}</small></button>`).join('')||'<p class="gm-meta">Sin resultados.</p>'});
 r.addEventListener('click',ev=>{const b=ev.target.closest('button');if(!b)return;sel[i]=D[+b.dataset.j];q.value=sel[i][0];r.innerHTML='';draw()})}
fetch('/jugadores/stats.json').then(r=>r.json()).then(j=>{D=j.p;const u=new URLSearchParams(location.search);[u.get('a'),u.get('b')].forEach((x,i)=>{const p=x&&D.find(p=>p[8]===x);if(p){sel[i]=p;document.getElementById('q'+i).value=p[0]}});draw()});
box(0);box(1);
</script>'''


def surname(n):
    t = n.split()
    return t[-2] if len(t) >= 3 else t[-1]


def suggestions(P, local):
    """Comparaciones de un clic: líderes de los dos equipos del próximo partido importante (o los dos mejores de la liga)."""
    try:
        Gm, _ = G.load(local)
    except Exception:
        Gm = []
    nxt = next((g for w in ('F', 'SF', 'CF') for g in Gm if g['w'] == w and not g['fin']), None)
    L = team_leaders(P)
    pairs = []
    for r, lbl in (('pase', 'QB'), ('tierra', 'Corredores'), ('aire', 'Receptores'), ('defensa', 'Defensa')):
        if nxt:
            a = next((x['p'] for x in L.get(nxt['a'], []) if x['role'] == r), None)
            b = next((x['p'] for x in L.get(nxt['h'], []) if x['role'] == r), None)
        else:
            a = b = None
        if a and b:
            pairs.append((lbl, a, b))
    if not pairs:
        return ''
    ttl = 'Rumbo a la final' if nxt and nxt['w'] == 'F' else 'Para el próximo partido'
    return ('<div class="sugg"><span>' + ttl + ':</span>' + ''.join(
        f'<a href="?a={a["url"]}&amp;b={b["url"]}">{e(surname(a["name"]))} vs {e(surname(b["name"]))} <small>{lbl}</small></a>' for lbl, a, b in pairs) + '</div>')


def compare_page(J, P=None, local=None):
    path = '/jugadores/comparar/'
    nav, ld_b = G.crumbs([('Inicio', '/'), ('Jugadores', '/jugadores/'), ('Comparar', None)])
    body = nav + f'<h1 class="gm-h1">Compara a dos jugadores</h1><p class="gm-meta">Escribe dos nombres de los 14 Grandes o de la Conferencia Nacional y ve sus números {YEAR} lado a lado. De la Nacional solo hay números de los líderes de cada categoría.</p>'
    body += ('<div class="cmpp"><div><input id="q0" class="srch" type="search" placeholder="Jugador 1" aria-label="Jugador 1" autocomplete="off"><div id="r0" class="cres"></div></div>'
             '<div><input id="q1" class="srch" type="search" placeholder="Jugador 2" aria-label="Jugador 2" autocomplete="off"><div id="r1" class="cres"></div></div></div>' + suggestions(P or [], local) + '<div id="cmp"></div>')
    body += '<p class="note">Estadísticas: Uriel González (FBA Stats). Edad, estatura y peso: rosters publicados por los equipos.</p>' + COMPARE_JS
    return path, G.page(f'Compara jugadores de la Liga Mayor ONEFA {YEAR} | Liga Mayor Unofficial',
                        f'Compara lado a lado las estadísticas y el físico de dos jugadores de los 14 Grandes y la Conferencia Nacional {YEAR}.', path, J.CSS + body, [ld_b])


def _pre(fp):
    h = open(os.path.join(SITE, fp), encoding='utf-8').read()
    a, b = h.find('<!--PRE-->'), h.find('<!--/PRE-->')
    return h[a + 10:b] if a >= 0 and b > a else ''


def hub_pages(P, J):
    """Páginas reales para lo que la gente escribe a mano (/tabla/, /lideres/, /equipos/) y un 404 propio."""
    out = []
    # /tabla/
    pre = _pre('index.html')
    tbl = re.search(r'<div class="tbl-box">.*?</table></div>', pre, re.S)
    npre = _pre('nacional/index.html')
    ntbl = re.findall(r'<h4 class="br-round">[^<]*</h4><div class="tbl-box">.*?</table></div>', npre, re.S)
    sub = re.search(r'<p class="sub">([^<]*)</p>', pre)
    nav, ld = G.crumbs([('Inicio', '/'), ('Tabla', None)])
    body = nav + f'<h1 class="gm-h1">Tabla de posiciones Liga Mayor ONEFA {YEAR}</h1>'
    body += f'<p class="gm-meta">{sub.group(1) if sub else ""}. <a href="/#tabla">Ver la tabla interactiva con racha y playoffs →</a></p>'
    body += '<h2 style="font-size:26px;margin-top:14px">14 Grandes</h2>' + (tbl.group(0) if tbl else '')
    if ntbl:
        body += '<h2 style="font-size:26px;margin-top:22px">Conferencia Nacional</h2>' + ''.join(ntbl) + '<p class="sub"><a href="/nacional/#tabla">Tabla interactiva de la Nacional →</a></p>'
    out.append(('/tabla/', G.page(f'Tabla de posiciones Liga Mayor ONEFA {YEAR}: 14 Grandes y Conferencia Nacional | Liga Mayor Unofficial',
                                  f'Tabla de posiciones {YEAR} de la Liga Mayor ONEFA: 14 Grandes y Conferencia Nacional, con récord, puntos a favor y en contra.', '/tabla/', J.CSS + body, [ld])))
    # /lideres/
    M = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
    m = re.search(r'let STATS=(\[.*?\]);\n', M, re.S)
    cut = re.search(r"let STATS_CUTOFF='([^']*)'", M)
    st = json.loads(m.group(1)) if m else []
    url = {(p['team'], p['n']): p['url'] for p in P if p['liga'] == '14G'}
    nav, ld = G.crumbs([('Inicio', '/'), ('Líderes', None)])
    body = nav + f'<h1 class="gm-h1">Líderes estadísticos Liga Mayor ONEFA {YEAR}</h1><p class="gm-meta">14 Grandes · temporada regular{" · " + e(cut.group(1)) if cut else ""} · FBA Stats. <a href="/#stats">Ver todos los líderes →</a></p><div class="xig2">'
    LX = lx_data(P)
    for c in st:
        rr = list(c['rows'][:5])
        if rr:
            last = rr[-1][3]
            for x in LX['more'].get(c['id'], []):
                if x[3] == last and not any(y[1] == x[1] and str(y[2]) == str(x[2]) for y in rr):
                    rr.append(x)
        rk = lambda i: (('T-' if sum(1 for y in rr if y[3] == rr[i][3]) > 1 else '') + str(1 + sum(1 for y in rr if y[3] > rr[i][3])))
        ast = lambda r, j: '*' if c['cols'][j] == 'TD' and c['id'] in ('rb', 'wr') and f"{r[1]}|{r[2]}" in LX['tdt'] else ''
        rows = ''.join(f'<tr><td class="pos num">{rk(i)}</td><td class="team">' + (f'<a href="{url[(r[1], r[2])]}">{e(r[0])}</a>' if (r[1], r[2]) in url else e(r[0])) +
                       f'<small style="display:block;color:var(--muted)">{e(G.TEAMS.get(r[1], {"n": r[1]})["n"])}</small></td>' + ''.join(f'<td class="num">{int(v):,}{ast(r, j)}</td>' for j, v in enumerate(r[3:])) + '</tr>' for i, r in enumerate(rr))
        if any(ast(r, j) for r in rr for j in range(len(c['cols']))):
            rows += f'<tr><td colspan="{2 + len(c["cols"])}" style="font-size:12px;color:var(--muted)">* TD totales: FBA no separa tierra y recepción.</td></tr>'
        body += f'<div><h2 style="font-size:20px;margin:10px 0 6px">{e(c["t"])}</h2><div class="tbl-box"><table class="qs"><thead><tr><th>#</th><th>Jugador</th>' + ''.join(f'<th>{e(x)}</th>' for x in c['cols']) + f'</tr></thead><tbody>{rows}</tbody></table></div></div>'
    body += '</div><p class="sub" style="margin-top:12px"><a href="/nacional/#stats">Líderes de la Conferencia Nacional →</a> · <a href="/equipo-ideal-' + str(YEAR) + '/">Equipo ideal →</a></p>'
    out.append(('/lideres/', G.page(f'Líderes estadísticos Liga Mayor ONEFA {YEAR}: pase, tierra, recepción y defensa | Liga Mayor Unofficial',
                                    f'Los líderes de la Liga Mayor ONEFA {YEAR} en yardas de pase, por tierra, recepción, tackles, sacks e intercepciones.', '/lideres/', J.CSS + body, [ld])))
    # /equipos/
    nav, ld = G.crumbs([('Inicio', '/'), ('Equipos', None)])
    t14 = sorted(G.TEAMS.items(), key=lambda x: G.norm(x[1]['n']))
    body = nav + f'<h1 class="gm-h1">Equipos de la Liga Mayor ONEFA {YEAR}</h1><h2 style="font-size:26px;margin-top:14px">14 Grandes</h2><div class="tg">'
    body += ''.join(f'<a href="/equipos/{G.SLUG[k]}/"><img src="/img/{k}.png" alt="" width="30" height="30">{e(v["n"])}</a>' for k, v in t14) + '</div>'
    body += '<h2 style="font-size:26px;margin-top:18px">Conferencia Nacional</h2><div class="tg">' + ''.join(
        f'<a href="/nacional/#equipos"><img src="/img/N_{k}.png" alt="" width="30" height="30">{e(n)}</a>' for k, n in sorted(G.NFULL.items(), key=lambda x: G.norm(x[1]))) + '</div>'
    out.append(('/equipos/', G.page(f'Equipos de la Liga Mayor ONEFA {YEAR}: 14 Grandes y Conferencia Nacional | Liga Mayor Unofficial',
                                    f'Todos los equipos de la Liga Mayor ONEFA {YEAR}: calendario, roster y estadísticas de los 14 Grandes y la Conferencia Nacional.', '/equipos/', J.CSS + body, [ld])))
    # alias que la gente escribe
    for a, u in ((f'juegos/{YEAR}/semifinal', f'/juegos/{YEAR}/semifinales/'), (f'juegos/{YEAR}/cuartos', f'/juegos/{YEAR}/cuartos-de-final/'),
                 ('lideres-2026', '/lideres/'), ('playoffs', '/#playoffs'), ('nacional/tabla', '/nacional/#tabla')):
        fp = os.path.join(SITE, a, 'index.html')
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        open(fp, 'w', encoding='utf-8').write(REDIRECT.format(u=u))
    # 404 propio
    body = ('<h1 class="gm-h1">No encontramos esa página</h1><p class="gm-meta">Puede que el enlace esté mal escrito o que la página ya no exista.</p>'
            '<form action="/jugadores/" method="get" style="margin:12px 0"><input class="srch" name="q" type="search" placeholder="Busca un jugador, equipo o sección" aria-label="Buscar"></form>'
            '<div class="more"><a href="/">Inicio →</a><a href="/tabla/">Tabla de posiciones →</a><a href="/juegos/' + str(YEAR) + '/">Juegos y resultados →</a>'
            '<a href="/lideres/">Líderes →</a><a href="/equipos/">Equipos →</a><a href="/nacional/">Conferencia Nacional →</a><a href="/jugadores/">Jugadores →</a></div>')
    h404 = G.page('Página no encontrada | Liga Mayor Unofficial', 'Página no encontrada.', '/404.html', J.CSS + body, []).replace('<head>', '<head><meta name="robots" content="noindex">', 1)
    open(os.path.join(SITE, '404.html'), 'w', encoding='utf-8').write(h404)
    return out


def pages(P, J, local=None):
    build_xs(P)
    D = load_draft(P)
    out = []
    fp = os.path.join(SITE, 'prospectos-' + str(YEAR), 'nacional', 'index.html')
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, 'w', encoding='utf-8').write(REDIRECT.format(u=f'/prospectos-{YEAR}/'))
    for path, h in (ideal_page(P, J), ideal_page(P, J, 'NAC'), prospects_page(P, J, D), y2027_page(J), compare_page(J, P, local)):
        out.append((path, G.write(path, h)))
    for path, h in hub_pages(P, J):
        out.append((path, G.write(path, h)))
    stats_json(P, J)
    return out
