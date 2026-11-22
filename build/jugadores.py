#!/usr/bin/env python3
"""Perfil de cada jugador: /jugadores/<equipo>/<jugador>/ y el índice /jugadores/.

Fuentes:
  - Roster (nombre, número, posición): ROSTERS dentro de site/index.html (Guía ONEFA de Lucio Trucíos).
  - Edad, estatura y peso: build/data/fisico_2026.csv (rosters publicados por los equipos, cruzados con el roster).
  - Estadísticas de la temporada en curso: pestañas Lideres, Jugadores y Nacional_Lideres de la hoja.
  - Temporadas pasadas: build/data/historial_jugadores.csv (se llena al cerrar cada temporada con --guardar).

También agrega edad/estatura/peso y el link al perfil en la tabla de roster de cada página de equipo.

Uso: python3 build/jugadores.py [--local DIR] [--guardar]
"""
import csv, io, json, os, re, sys, html, unicodedata, datetime, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate as G
import avatar as AV

e = html.escape
SITE, URL, YEAR = G.SITE, G.URL, G.YEAR
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
G.HEADER = G.HEADER.replace('<a class="on" href="/#tabla">', '<a href="/#tabla">').replace('<a href="/jugadores/">', '<a class="on" href="/jugadores/">')
G.GID.update({'lideres': 1908116186, 'estrellas': 1355832789, 'nlideres': 1049818250})

# Tono de piel indicado por Aidan para el muñequito (equipo, número)
SKIN_FIX = {('LAC', 3), ('MTY', 78), ('GDL', 2), ('CEM', 0)}

POS = {'QB': 'Quarterback', 'RB': 'Corredor', 'FB': 'Fullback', 'WR': 'Receptor', 'TE': 'Ala cerrada', 'PB': 'H-back', 'HB': 'H-back',
       'OL': 'Línea ofensiva', 'DL': 'Línea defensiva', 'DE': 'Ala defensiva', 'DT': 'Tackle defensivo', 'NT': 'Nose tackle',
       'LB': 'Apoyador', 'CB': 'Esquinero', 'S': 'Profundo', 'FS': 'Profundo libre', 'SS': 'Profundo fuerte', 'DB': 'Back defensivo',
       'K': 'Pateador', 'P': 'Despejador'}
CAT = {'QB': ('Pase', [('YDS', 'yds de pase'), ('TD', 'TD')]), 'WR': ('Recepción', [('YDS', 'yds de recepción'), ('REC', 'recepciones'), ('TD', 'TD')]),
       'RB': ('Acarreo', [('YDS', 'yds por tierra'), ('TD', 'TD')]), 'YM': ('Yardas totales', [('YDS', 'yds totales')]),
       'PT': ('Puntos', [('PTS', 'puntos')]), 'TK': ('Tackles', [('TACK', 'tackles')]), 'IN': ('Intercepciones', [('INT', 'intercepciones')]),
       'SK': ('Sacks', [('SACK', 'sacks')]), 'FG': ('Goles de campo', [('FG', 'goles de campo'), ('PTS', 'puntos')])}
HIST_COLS = ['Temporada', 'Liga', 'Equipo', 'Numero', 'Jugador', 'Categoria', 'Lugar', 'YDS', 'REC', 'TD', 'TACK', 'INT', 'SACK', 'PTS', 'FG']


def slug(x):
    x = unicodedata.normalize('NFD', x.lower())
    x = ''.join(c for c in x if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '-', x).strip('-')


def toks(x):
    return set(slug(x).split('-')) - {'de', 'la', 'del', 'y'}


def same(a, b):
    A, B = toks(a), toks(b)
    return len(A & B) >= min(2, len(A), len(B))


# ---------------------------------------------------------------- equipos
NAC_HTML = open(os.path.join(SITE, 'nacional', 'index.html'), encoding='utf-8').read()
NTEAMS = {t['k']: t for t in json.loads(re.search(r'let TEAMS=(\[.*?\]),CUT', NAC_HTML).group(1))}
NSLUG = {'PAC': 'pumas-acatlan', 'PSA': 'potros-salvajes', 'FRA': 'frailes-ut', 'HAL': 'halcones-uv', 'BUH': 'buhos-guinda', 'TSA': 'toros-salvajes',
         'PAN': 'panteras-siglo-21', 'LQR': 'leones-queretaro', 'TEC': 'tecos-uag', 'ULM': 'lobos-ulm', 'UIW': 'cardinals-uiw', 'ASU': 'red-wolves-asu',
         'UAT': 'correcaminos-uat', 'UCH': 'aguilas-uach', 'ITS': 'potros-itson', 'UAC': 'lobos-uadec', 'UCJ': 'indios-uacj', 'UBC': 'cimarrones-uabc'}
NNAME = {'PAC': 'Pumas Acatlán', 'PSA': 'Potros Salvajes', 'FRA': 'Frailes UT', 'HAL': 'Halcones UV', 'BUH': 'Búhos Guinda', 'TSA': 'Toros Salvajes',
         'PAN': 'Panteras Siglo 21', 'LQR': 'Leones Querétaro', 'TEC': 'Tecos UAG', 'ULM': 'Lobos ULM', 'UIW': 'Cardinals UIW', 'ASU': 'Red Wolves ASU',
         'UAT': 'Correcaminos UAT', 'UCH': 'Águilas UACH', 'ITS': 'Potros ITSON', 'UAC': 'Lobos UAdeC', 'UCJ': 'Indios UACJ', 'UBC': 'Cimarrones UABC'}
ROSTERS = json.loads(re.search(r'const ROSTERS=(\{.*?\});', G.MAIN).group(1))


def team(liga, k):
    if liga == '14G':
        return {'k': k, 'n': G.TEAMS[k]['n'], 'slug': G.SLUG[k], 'img': f'/img/{k}.png', 'url': f'/equipos/{G.SLUG[k]}/', 'conf': '14 Grandes'}
    t = NTEAMS.get(k, {'n': k, 's': ''})
    return {'k': k, 'n': NNAME.get(k, t['n']), 'slug': NSLUG.get(k) or slug(f"{t['n']} {t['s']}"), 'img': f'/img/N_{k}.png', 'url': '/nacional/#equipos', 'conf': 'Conferencia Nacional', 'school': t.get('s', '')}


# ---------------------------------------------------------------- jugadores
NACP_FILE = os.path.join(DATA, 'nacional_jugadores.csv')


def build_players(fis):
    P = []
    for k, lst in ROSTERS.items():
        for n, name, pos in lst:
            P.append({'liga': '14G', 'team': k, 'n': n, 'name': name, 'pos': pos})
    for r in fis:
        if r['Liga'] == 'NAC':
            P.append({'liga': 'NAC', 'team': r['Equipo'], 'n': int(r['Numero']), 'name': r['Nombre'], 'pos': r['Posicion']})
    # jugadores de la Nacional que ya salieron en las estadísticas (se guardan para que su perfil no desaparezca)
    if os.path.exists(NACP_FILE):
        for r in csv.DictReader(open(NACP_FILE, encoding='utf-8')):
            n = int(r['Numero']) if r['Numero'].isdigit() else None
            if not any(q['liga'] == 'NAC' and q['team'] == r['Equipo'] and q['n'] == n and same(q['name'], r['Jugador']) for q in P):
                P.append({'liga': 'NAC', 'team': r['Equipo'], 'n': n, 'name': r['Jugador'], 'pos': r['Pos']})
    # datos físicos (mismo orden que el roster: equipo + número + nombre)
    idx = {}
    for r in fis:
        idx.setdefault((r['Equipo'], int(r['Numero'])), []).append(r)
    for p in P:
        cand = [r for r in idx.get((p['team'], p['n']), []) if r['Nombre'] == p['name']]
        p['fis'] = cand[0] if cand else None
    return P


def assign_urls(P):
    seen = {}
    for p in P:
        T = team(p['liga'], p['team'])
        base = f"/jugadores/{T['slug']}/{slug(p['name'])}/"
        dup = sum(1 for q in P if q['team'] == p['team'] and q['liga'] == p['liga'] and slug(q['name']) == slug(p['name']))
        p['url'] = base if dup == 1 else base[:-1] + f"-{p['n']}/"
        p['T'] = T
        seen[p['url']] = p


def stats(local, P):
    """Pega las estadísticas de la temporada actual (líderes y 'jugadores a seguir') a cada jugador."""
    rows = []
    for name, liga in (('lideres', '14G'), ('nlideres', 'NAC')):
        try:
            R = list(csv.reader(io.StringIO(G.fetch(name, local))))
        except Exception as ex:
            if name == 'lideres':
                print('No se pudo leer la hoja de líderes; no se cambia nada.', ex)
                sys.exit(0)
            R = []
        if not R:
            continue
        H = [h.strip().upper() for h in R[0]]
        for r in R[1:]:
            if not r or G.norm(r[0]) == 'corte' or len(r) < 5:
                continue
            d = {h: (r[i].strip() if i < len(r) else '') for i, h in enumerate(H)}
            rows.append({'Temporada': str(YEAR), 'Liga': liga, 'Equipo': d.get('EQUIPO', '').upper(), 'Numero': d.get('NUMERO', ''),
                         'Jugador': d.get('JUGADOR', ''), 'Categoria': d.get('CATEGORIA', '').upper(), 'Lugar': d.get('LUGAR', ''),
                         **{c: d.get(c, '') for c in HIST_COLS[7:]}})
    stars = []
    try:
        R = list(csv.reader(io.StringIO(G.fetch('estrellas', local))))
        for r in R[1:]:
            if len(r) >= 5 and r[0].strip():
                stars.append({'Equipo': r[0].strip().upper(), 'Jugador': r[1].strip(), 'Pos': r[2].strip(), 'Numero': r[3].strip(), 'Linea': r[4].strip()})
    except Exception:
        pass
    return rows, stars


def find_player(P, liga, k, n, name):
    try:
        n = int(float(n))
    except (TypeError, ValueError):
        n = None
    c = [p for p in P if p['liga'] == liga and p['team'] == k and p['n'] == n]
    c2 = [p for p in c if same(p['name'], name)]
    if c2:
        return c2[0]
    if len(c) == 1 and liga == '14G':
        return c[0]
    c3 = [p for p in P if p['liga'] == liga and p['team'] == k and same(p['name'], name)]
    return c3[0] if len(c3) == 1 else None


# ---------------------------------------------------------------- Cover Cero (estadísticas completas 14 Grandes)
CC_TEAM = {'MTY': 'MTY', 'CETYS': 'CET', 'PUE': 'PUE', 'CU': 'PUM', 'CEM': 'CEM', 'UAMN': 'LAN', 'AT': 'TIG', 'ABS': 'AGU',
           'UDLA': 'UDL', 'CCM': 'CCM', 'BBS': 'BUR', 'UVM': 'UVM', 'GDL': 'GDL', 'UAC': 'LAC'}
CC_COLS = {'passing': ('Pase', ['JJ', 'COMP', 'INTENT.', '%', 'YDS', 'Y/I', 'TD', 'INT', 'RTG', 'Y/J']),
           'rushing': ('Acarreo', ['JJ', 'ACAR', 'YDS', 'PROM', 'TD', 'Y/J']),
           'receiving': ('Recepción', ['JJ', 'REC', 'YDS', 'PROM', 'TD', 'Y/J']),
           'defense': ('Defensiva', ['JJ', 'TACK', 'SOLO', 'AST', 'SACK', 'TFL', 'INT', 'FF'])}
CC_SHOW = {'passing': [0, 1, 2, 3, 4, 6, 7, 8], 'rushing': [0, 1, 2, 3, 4, 5], 'receiving': [0, 1, 2, 3, 4, 5], 'defense': [0, 1, 4, 5, 6, 7]}


def ccnum(x):
    x = x.strip()
    if x in ('—', '-', ''):
        return None
    return float(x.replace('.', '').replace(',', '.')) if re.match(r'^-?[\d.]+(,\d+)?$', x) else None


def load_cc():
    fp = os.path.join(DATA, 'covercero_2026.txt')
    out = []
    if not os.path.exists(fp):
        return out
    for ln in open(fp, encoding='utf-8'):
        if not ln.strip() or ln.startswith('#'):
            continue
        f = ln.rstrip('\n').split('|')
        m = re.match(r'^(.*?) #(\d+) · (\w+)$', f[1])
        if not m or f[2] not in CC_TEAM:
            continue
        out.append({'cat': f[0], 'name': m.group(1), 'n': int(m.group(2)), 'pos': m.group(3), 'team': CC_TEAM[f[2]], 'v': [ccnum(x) for x in f[3:]]})
    return out


# mismo jugador escrito distinto en Cover Cero y en el roster
CC_ALIAS = {('PUE', 8, 'Alonso Barrenchea'): 'Alonso Barrenechea Romay', ('LAN', 1, 'Hiram Palomino'): 'Iram Palomino',
            ('BUR', 13, 'Rodrigo Espinosa'): 'Rodrigo Daniel Espinoza Vite', ('UVM', 5, 'Emanuel Burgos'): 'Emmanuel Burgos Vargas',
            ('LAN', 18, 'Emmanuel Premio'): 'Tonathiu Premio', ('LAN', 2, 'Manuel Rivera'): 'Roberto Rivera',
            ('LAN', 3, 'Diego Vargas'): 'Diego Salvador', ('LAN', 6, 'Rafael Jaime'): 'Rafael Dupre'}


# correcciones confirmadas por el usuario: (equipo, número, categoría) -> {índice de columna: valor}
CC_FIX = {('GDL', 90, 'defense'): {0: 8},      # Ander Wittman jugó 8 de 9 partidos
          }


def attach_cc(P, cc):
    hit = 0
    for r in cc:
        r['name'] = CC_ALIAS.get((r['team'], r['n'], r['name']), r['name'])
    for p in P:
        p['cc'] = {}
    for r in cc:
        p = find_player(P, '14G', r['team'], r['n'], r['name'])
        if p:
            v = list(r['v'])
            for i, x in CC_FIX.get((p['team'], p['n'], r['cat']), {}).items():
                v[i] = x
            p['cc'][r['cat']] = v
            hit += 1
    return hit


def fmtv(v, dec):
    if v is None:
        return '—'
    if dec or v != int(v):
        return f'{v:.1f}'
    return f'{int(v):,}'


def cc_tables(cc, hide=None):
    out = ''
    for cat in ('passing', 'rushing', 'receiving', 'defense'):
        if cat not in cc:
            continue
        lbl, cols = CC_COLS[cat]
        idx = [i for i in CC_SHOW[cat] if cols[i] not in (hide or {}).get(cat, ())]
        dec = {'%', 'Y/I', 'RTG', 'Y/J', 'PROM'}
        out += (f'<div class="c"><div class="ct">{lbl}</div><div class="tbl-box"><table class="cc"><thead><tr>' + ''.join(f'<th>{cols[i]}</th>' for i in idx) +
                '</tr></thead><tbody><tr>' + ''.join(f'<td>{fmtv(cc[cat][i], cols[i] in dec)}</td>' for i in idx) + '</tr></tbody></table></div></div>')
    return out


def cc_summary(cc):
    parts = []
    if 'passing' in cc:
        v = cc['passing']; parts.append(f'{int(v[4]):,} yds de pase, {int(v[6])} TD')
    if 'rushing' in cc:
        v = cc['rushing']; parts.append(f'{int(v[2]):,} yds por tierra, {int(v[4])} TD')
    if 'receiving' in cc:
        v = cc['receiving']; parts.append(f'{int(v[1])} rec., {int(v[2]):,} yds, {int(v[4])} TD')
    if 'defense' in cc:
        v = cc['defense']; d = [f'{int(v[1])} tackleadas'] + [f'{x:g} {t}' for x, t in ((v[4], 'sacks'), (v[6], 'INT')) if x]
        parts.append(', '.join(d))
    return ' · '.join(parts)


# ---------------------------------------------------------------- FBA Stats completo (publicado por Modo Blitz)
MB_TEAM = {'CETYS': 'CET', 'IPN AGS': 'AGU', 'IPN BURROS': 'BUR', 'CCM': 'CCM', 'CEM': 'CEM', 'GDL': 'GDL', 'MTY': 'MTY', 'PUE': 'PUE',
           'UAMN': 'LAN', 'UANC': 'LAC', 'UANL': 'TIG', 'UDLAP': 'UDL', 'UNAM': 'PUM', 'UVM': 'UVM'}
MB_SHOW = {'passing': ('Pase', [('JJ', 'JJ'), ('COMP', 'COMP'), ('INT', 'INTENT.'), ('PCT', '%'), ('YDS', 'YDS'), ('TD', 'TD'), ('INTC', 'INT'), ('YDS/J', 'Y/J'), ('SACS', 'CAPT.')]),
           'rushing': ('Acarreo', [('JJ', 'JJ'), ('ACA', 'ACAR'), ('YDS', 'YDS'), ('PROM', 'PROM'), ('TD', 'TD'), ('1y10', '1y10'), ('FUM', 'BS')]),
           'receiving': ('Recepción', [('JJ', 'JJ'), ('REC', 'REC'), ('YDS', 'YDS'), ('PROM', 'PROM'), ('TD', 'TD'), ('1y10', '1y10')]),
           'tackles': ('Defensiva', [('JJ', 'JJ'), ('TAC', 'TACK'), ('SACKS', 'SACK'), ('FR', 'BR')]),
           'ints': ('Intercepciones', [('JJ', 'JJ'), ('INT', 'INT'), ('YDS', 'YDS')]),
           'kickers': ('Pateo', [('JJ', 'JJ'), ('PAT', 'PAT'), ('FG 10-30', 'GC 10-30'), ('FG 31-45', 'GC 31-45'), ('FG 46+', 'GC 46+'), ('PTS', 'PTS')])}


# correcciones confirmadas por el usuario sobre los datos de FBA
MB_FIX = {}


def load_mb():
    fp = os.path.join(DATA, 'modoblitz_2026.txt')
    out, cat, cols = [], None, []
    if not os.path.exists(fp):
        return out
    for ln in open(fp, encoding='utf-8'):
        ln = ln.rstrip('\n')
        if ln.startswith('#') and '|' in ln:
            cat, *cols = ln[1:].split('|')
            continue
        if not ln.strip() or ln.startswith('#'):
            continue
        f = ln.split('|')
        if f[1] not in MB_TEAM:
            continue
        v = {c: (float(x) if x not in ('', 'None') else None) for c, x in zip(cols, f[3:])}
        out.append({'cat': 'tackles' if cat == 'sacks' else cat, 'n': int(f[0]), 'team': MB_TEAM[f[1]], 'name': f[2], 'v': v})
    return out


def attach_mb(P, mb):
    hit = 0
    for p in P:
        p['mb'] = {}
    for r in mb:
        name = CC_ALIAS.get((r['team'], r['n'], r['name']), r['name'])
        p = find_player(P, '14G', r['team'], r['n'], name or '-')
        if p and r['cat'] not in p['mb']:
            v = dict(r['v'])
            v.update(MB_FIX.get((p['team'], p['n'], r['cat']), {}))
            p['mb'][r['cat']] = v
            hit += 1
    return hit


def mb_tables(mb):
    out = ''
    for cat, (lbl, cols) in MB_SHOW.items():
        if cat not in mb:
            continue
        v = mb[cat]
        def f(k):
            x = v.get(k)
            if x is None:
                return '—'
            if k == 'PCT':
                return f'{x * 100:.1f}'
            return f'{x:.1f}' if k in ('PROM', 'YDS/J') else f'{int(x):,}'
        out += (f'<div class="c"><div class="ct">{lbl}</div><div class="tbl-box"><table class="cc"><thead><tr>' + ''.join(f'<th>{t}</th>' for k, t in cols) +
                '</tr></thead><tbody><tr>' + ''.join(f'<td>{f(k)}</td>' for k, t in cols) + '</tr></tbody></table></div></div>')
    return out


def attach(P, rows, stars, hist):
    for p in P:
        p['seasons'] = {}
        p['star'] = ''
    extra = []
    for r in hist + rows:
        p = find_player(P, r['Liga'], r['Equipo'], r['Numero'], r['Jugador'])
        if not p and r['Liga'] == 'NAC' and r['Equipo'] in NTEAMS and r['Jugador']:
            # jugador de la Nacional sin roster: se crea su perfil con lo que dicen las estadísticas
            n = int(float(r['Numero'])) if re.match(r'^\d+(\.0)?$', r['Numero'] or '') else None
            p = {'liga': 'NAC', 'team': r['Equipo'], 'n': n, 'name': r['Jugador'], 'pos': {'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TK': 'LB', 'SK': 'DL', 'IN': 'DB', 'FG': 'K'}.get(r['Categoria'], ''), 'fis': None, 'seasons': {}, 'star': ''}
            P.append(p)
            extra.append(p)
        if not p:
            continue
        p['seasons'].setdefault(r['Temporada'], {'team': r['Equipo'], 'liga': r['Liga'], 'cats': {}})['cats'][r['Categoria']] = r
    for s in stars:
        p = find_player(P, '14G', s['Equipo'], s['Numero'], s['Jugador'])
        if p:
            p['star'] = s['Linea']
            # FBA Stats es la base: la línea de "jugador a seguir" también cuenta como estadística FBA del perfil
            cats = p['seasons'].setdefault(str(YEAR), {'team': p['team'], 'liga': p['liga'], 'cats': {}})['cats']
            for cat, d in star_cats(s['Linea']).items():
                if cat not in cats:
                    cats[cat] = dict({'Liga': p['liga'], 'Equipo': p['team'], 'Numero': str(p['n']), 'Jugador': p['name'], 'Categoria': cat, 'Lugar': '', 'Temporada': str(YEAR)}, **d)
    return extra


def star_cats(line):
    """'810 yds de pase · 8 TD' -> {'QB': {'YDS': '810', 'TD': '8'}}; igual para tierra, recepción, tackles, sacks e INT."""
    n = lambda x: x.replace(',', '')
    out = {}
    m = re.search(r'([\d,]+) yds de pase · (\d+) TD', line)
    if m:
        out['QB'] = {'YDS': n(m.group(1)), 'TD': m.group(2)}
    m = re.search(r'([\d,]+) yds por tierra · (\d+) TD', line)
    if m:
        out['RB'] = {'YDS': n(m.group(1)), 'TD': m.group(2)}
    m = re.search(r'(\d+) recepciones · ([\d,]+) yds · (\d+) TD', line)
    if m:
        out['WR'] = {'REC': m.group(1), 'YDS': n(m.group(2)), 'TD': m.group(3)}
    m = re.search(r'([\d,]+) yds totales', line)
    if m:
        out['YM'] = {'YDS': n(m.group(1))}
    m = re.search(r'(\d+) tackles', line)
    if m:
        out['TK'] = {'TACK': m.group(1)}
    m = re.search(r'(\d+) sacks?', line)
    if m:
        out['SK'] = {'SACK': m.group(1)}
    m = re.search(r'(\d+) INT', line)
    if m:
        out['IN'] = {'INT': m.group(1)}
    return out


# ---------------------------------------------------------------- páginas
CSS = '''<style>
.ph{display:grid;grid-template-columns:auto 1fr;gap:14px;align-items:center;background:var(--head);color:var(--head-ink);border-radius:4px;padding:16px;margin-top:6px}
.ph .av{background:linear-gradient(#DDE7DF,#C7D8CB);border-radius:4px;padding:10px 8px 6px;display:grid;place-items:end center}
.ph .sub2{display:flex;flex-direction:column;align-items:flex-start;gap:3px}.ph .sub2 span{padding-left:1px}.ph .tl{display:inline-flex;align-items:center;gap:5px;text-decoration:none}.ph .tl img{width:24px;height:24px;image-rendering:pixelated}
@media (max-width:420px){.ph .av svg{width:96px;height:auto}.ph h1{font-size:30px}}
.ph .num{font-family:var(--display);font-size:54px;line-height:1;color:#3DBE73}
.ph h1{font-family:var(--display);font-weight:800;font-size:34px;line-height:1.02;text-transform:uppercase;margin:0;text-wrap:balance}
.ph .sub2{opacity:.75;font-size:14px;margin-top:4px}
.ph a{color:inherit}
.pf{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:12px}
.pf div{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:10px;text-align:center}
.pf b{display:block;font-family:var(--display);font-weight:800;font-size:28px;line-height:1.05}
.pf span{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.pf small{display:block;font-size:12px;color:var(--muted)}
@media (max-width:480px){.pf{grid-template-columns:repeat(2,1fr)}}
.st{display:grid;gap:8px;margin-top:8px}
.st .c{background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:4px;padding:10px 12px}
.st .c .ct{margin:0 0 6px;font-family:var(--display);font-weight:700;font-size:15px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.st .v{display:flex;flex-wrap:wrap;gap:14px}
.st .v b{font-family:var(--display);font-weight:800;font-size:28px;line-height:1}
.st .v span{font-size:12px;color:var(--muted);display:block}
.st .rnk{font-size:13px;margin-top:6px;font-weight:600}
.qs td{white-space:normal}
.st .tbl-box{margin:0}table.cc{width:100%}table.cc th,table.cc td{text-align:center;font-variant-numeric:tabular-nums}table.cc td{font-family:var(--display);font-weight:800;font-size:20px}
.pl2{display:grid;gap:6px}
.pl2 a{display:grid;grid-template-columns:42px 1fr auto;gap:10px;align-items:center;background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:8px 10px;text-decoration:none;color:inherit}
.pl2 a:hover{border-color:var(--accent)}
.pl2 .n{font-family:var(--display);font-weight:800;font-size:22px;color:var(--accent);text-align:center}
.pl2 small{color:var(--muted);font-size:12px;display:block}
.tg{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px}
.tg a{display:flex;gap:8px;align-items:center;background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:8px;text-decoration:none;color:inherit;font-weight:600;font-size:14px}
.tg img{width:30px;height:30px;image-rendering:pixelated}
.srch{width:100%;font:inherit;font-size:16px;padding:10px 12px;border:1px solid var(--line);border-radius:4px;background:var(--surface);color:var(--ink);margin:8px 0}
.note{font-size:12px;color:var(--muted);margin-top:14px}
table.roster th:nth-child(n+3),table.roster td:nth-child(n+3){text-align:right}table.roster td.team a{color:inherit}table.roster td.num{color:var(--muted);font-variant-numeric:tabular-nums}
@media (max-width:420px){table.roster th,table.roster td{padding-left:5px;padding-right:5px}table.roster td.team{font-size:14px}}
</style>'''


def phys(p):
    f = p.get('fis')
    if not f or f['Estado'] in ('Pendiente', 'Discrepancia'):
        return None, None, None
    obs = f['Observaciones'].lower()
    sus = f['Estado'] == 'Dato sospechoso'
    age = f['Edad'] if f['Edad'].isdigit() and int(f['Edad']) >= 18 else None
    h = f['Estatura'] if f['Estatura'] and not (sus and 'estatura' in obs) else None
    w = f['Peso'] if f['Peso'] and not (sus and 'peso' in obs) else None
    return age, h, w


def ft(h):
    inch = float(h) * 100 / 2.54
    return f"{int(inch // 12)}'{round(inch % 12)}\""


def stat_cards(season, conf):
    out = []
    for c, r in sorted(season['cats'].items(), key=lambda x: list(CAT).index(x[0]) if x[0] in CAT else 99):
        if c not in CAT:
            continue
        lbl, cols = CAT[c]
        vals = ''.join(f'<div><b>{int(float(r[k])):,}</b><span>{t}</span></div>'.replace(',', ',') for k, t in cols if re.match(r'^\d+(\.\d+)?$', r.get(k) or ''))
        lugar = r.get('Lugar', '')
        rk = f'<div class="rnk">{lugar}º lugar en {lbl.lower()} de {conf}</div>' if lugar.isdigit() else ''
        out.append(f'<div class="c"><div class="ct">{e(lbl)}</div><div class="v">{vals}</div>{rk}</div>')
    return ''.join(out)


def summary(season):
    parts = []
    for c, r in season['cats'].items():
        if c in CAT:
            for k, t in CAT[c][1]:
                if re.match(r'^\d+', r.get(k) or '') and not (k == 'TD' and any(t2 == 'TD' for t2 in [p.split(' ', 1)[1] for p in parts])):
                    parts.append(f'{int(float(r[k])):,} {t}')
    return ' · '.join(dict.fromkeys(parts))


def player_page(p, P):
    T = p['T']
    age, h, w = phys(p)
    pos = POS.get(p['pos'], p['pos'])
    nav, ld_b = G.crumbs([('Inicio', '/'), ('Jugadores', '/jugadores/'), (T['n'], f"/jugadores/{T['slug']}/"), (p['name'], None)])
    num = f'<div class="num">#{p["n"]}</div>' if p['n'] is not None else ''
    POSES = {'QB': ('ball_up', 'ball_r', 'two_hands'), 'WR': ('ball_up', 'ball_r', 'ball_l', 'tuck'), 'TE': ('tuck', 'ball_r', 'ball_up'),
             'RB': ('tuck', 'ball_r', 'ball_l', 'two_hands'), 'FB': ('tuck', 'two_hands'), 'PB': ('tuck', 'ball_r'), 'HB': ('tuck', 'ball_r')}
    ops = POSES.get(p['pos'])
    pose = ops[zlib.crc32(p['name'].encode('utf-8')) % len(ops)] if ops else None
    BIG = {'OL', 'DL', 'OT', 'OG', 'C', 'DT', 'DE', 'NT', 'G', 'T'}
    SKILL = {'QB', 'WR', 'CB', 'S', 'DB', 'FS', 'SS', 'K', 'P', 'LS', 'KR'}
    build = 'big' if p['pos'] in BIG else 'skill' if p['pos'] in SKILL else 'mid'
    av = AV.svg(p['n'], AV.uniform(p['liga'], p['team']), 112, seed=p['name'], pose=pose, build=build, skin=AV.SKIN_DARK if (p['team'], p['n']) in SKIN_FIX else None, title=f'Muñequito con el uniforme de {e(T["n"])}' + (f' y el número {p["n"]}' if p['n'] is not None else ''))
    head = (f'<div class="ph"><div class="av">{av}</div><div>{num}'
            f'<h1>{e(p["name"])}</h1><div class="sub2"><a class="tl" href="{T["url"]}"><img src="{T["img"]}" alt="" width="24" height="24">{e(T["n"])}</a><span>{e(pos) if pos else "Jugador"} · {T["conf"]}</span></div></div></div>')
    tiles = [(age or '—', 'Edad', 'años' if age else ''), (h or '—', 'Estatura', ft(h) if h else ''), (w or '—', 'Peso', f'{round(int(w) * 2.2046)} lb' if w else ''), (e(p['pos'] or '—'), 'Posición', '')]
    if not h:
        tiles[1] = (('#' + str(p['n'])) if p['n'] is not None else '—', 'Número', '')
    body = nav + head + '<div class="pf">' + ''.join(f'<div><b>{v}</b>{f"<small>{s}</small>" if s else ""}<span>{l}</span></div>' for v, l, s in tiles) + '</div>'
    cur = p['seasons'].get(str(YEAR))
    body += f'<h2 style="font-size:26px;margin-top:22px">Temporada {YEAR}</h2>'
    if cur and cur['cats']:
        body += f'<p class="gm-meta">Temporada regular · FBA Stats (Uriel González). Si está entre los primeros lugares, se indica en cada categoría.</p><div class="st">{stat_cards(cur, "los 14 Grandes" if T["conf"] == "14 Grandes" else "la Conferencia Nacional")}</div>'
    if p.get('star'):
        body += f'<div class="card" style="margin-top:8px"><b>Jugador a seguir de {e(T["n"])}:</b> {e(p["star"])}</div>'
    mb = p.get('mb') or {}
    if mb:
        body += f'<h3 style="font-size:20px;margin:18px 0 0">Estadísticas completas {YEAR}</h3><p class="gm-meta">Temporada regular · FBA Stats. JJ = juegos jugados.</p><div class="st">{mb_tables(mb)}</div>'
    # Cover Cero solo para lo que FBA Stats no trae
    fcats = set(cur['cats']) if cur else set()
    tapado = {'passing': 'QB' in fcats or 'passing' in mb, 'rushing': 'RB' in fcats or 'rushing' in mb, 'receiving': 'WR' in fcats or 'receiving' in mb,
              'defense': bool(fcats & {'TK', 'IN', 'SK'}) or 'tackles' in mb or 'ints' in mb}
    # columnas que ya muestra FBA; de Cover Cero solo se enseña lo demás. Si FBA trae la categoría completa, se omite la de Cover Cero.
    hide = {'passing': {'YDS', 'TD', 'Y/I', 'RTG', 'Y/J'} if 'QB' in fcats else set(), 'rushing': {'YDS', 'TD', 'PROM', 'Y/J'} if 'RB' in fcats else set(),
            'receiving': {'YDS', 'REC', 'TD', 'PROM', 'Y/J'} if 'WR' in fcats else set(),
            'defense': {c for f, c in (('TK', 'TACK'), ('SK', 'SACK'), ('IN', 'INT')) if f in fcats}}
    if 'tackles' in mb:
        hide['defense'] |= {'TACK', 'SACK', 'JJ'}
    if 'ints' in mb:
        hide['defense'] |= {'INT', 'JJ'}
    ccall = {k: v for k, v in (p.get('cc') or {}).items() if not (k in ('passing', 'rushing', 'receiving') and k in mb)}
    if 'defense' in ccall and not [i for i in CC_SHOW['defense'] if CC_COLS['defense'][1][i] not in hide['defense'] and CC_COLS['defense'][1][i] != 'JJ']:
        ccall.pop('defense')
    ccx = {k: v for k, v in ccall.items() if not tapado[k]}
    if ccall:
        ttl = f'Más estadísticas {YEAR}' if (fcats or mb) else f'Estadísticas {YEAR}'
        body += f'<h3 style="font-size:20px;margin:18px 0 0">{ttl}</h3><p class="gm-meta">Temporada regular · Cover Cero, solo lo que FBA no publica.</p><div class="st">{cc_tables(ccall, hide)}</div>'
    if not (cur and cur['cats']) and not p.get('star') and not ccall and not mb:
        body += f'<p class="gm-meta">Sin estadísticas individuales publicadas en {YEAR}.</p>'
    hist = sorted(p['seasons'].items(), reverse=True)
    if ccx and str(YEAR) not in p['seasons']:
        hist = [(str(YEAR), {'liga': p['liga'], 'team': p['team'], 'cats': {}})] + hist
    hs = lambda y, s: ' · '.join(x for x in [summary(s), cc_summary(ccx) if y == str(YEAR) else ''] if x)
    if hist:
        body += '<h2 style="font-size:26px;margin-top:22px">Historial</h2><div class="tbl-box"><table class="qs"><thead><tr><th>Temporada</th><th>Equipo</th><th>Estadísticas</th></tr></thead><tbody>' + ''.join(
            f'<tr><td>{y}</td><td>{e(team(s["liga"], s["team"])["n"])}</td><td>{e(hs(y, s)) or "—"}</td></tr>' for y, s in hist) + '</tbody></table></div>'
    mates = [q for q in P if q is not p and q['liga'] == p['liga'] and q['team'] == p['team'] and q['pos'] == p['pos']][:12]
    if mates:
        body += f'<h2 style="font-size:24px;margin-top:22px">Otros {e(p["pos"])} de {e(T["n"])}</h2><div class="pl2">' + ''.join(
            f'<a href="{q["url"]}"><span class="n">{q["n"] if q["n"] is not None else ""}</span><span>{e(q["name"])}</span><small>{e(q["pos"])}</small></a>' for q in mates) + '</div>'
    body += f'<div class="more" style="margin-top:14px"><a href="/jugadores/{T["slug"]}/">Roster completo de {e(T["n"])} →</a><a href="{T["url"]}">Página de {e(T["n"])} →</a><a href="/jugadores/">Todos los jugadores →</a></div>'
    src = []
    if p['liga'] == '14G':
        src.append('Nombre, número y posición: Guía ONEFA 2026 de Lucio Trucíos (@luciotrucios)')
    if age or h or w:
        src.append('edad, estatura y peso: rosters publicados por los equipos')
    if ccall:
        src.append('otras estadísticas: Cover Cero (<a href="https://covercero.com.mx/estadisticas-2026/" rel="noopener">covercero.com.mx</a>)')
    if p['seasons'] or p.get('mb'):
        src.append('estadísticas: Uriel González (FBA Stats), publicadas también por <a href="https://www.modoblitz.com/estadisticas-onefa" rel="noopener">Modo Blitz</a>')
    txt = "; ".join(src)
    body += f'<p class="note">{txt[:1].upper() + txt[1:]}. ¿Ves un dato equivocado? <a href="/#info">Avísanos</a>.</p>'
    title = f"{p['name']} · {pos} de {T['n']} | Liga Mayor Unofficial" if pos else f"{p['name']} · {T['n']} | Liga Mayor Unofficial"
    bits = [x for x in [pos and f'{pos} de {T["n"]}', p['n'] is not None and f'#{p["n"]}', age and f'{age} años', h and f'{h} m', w and f'{w} kg'] if x]
    desc = f"{p['name']}: " + ', '.join(bits) + f". Perfil, estadísticas y temporadas en la Liga Mayor ONEFA {YEAR}."
    person = {'@context': 'https://schema.org', '@type': 'Person', 'name': p['name'], 'url': URL + p['url'],
              'memberOf': {'@type': 'SportsTeam', 'name': T['n'], 'sport': 'Fútbol americano'}}
    if h:
        person['height'] = {'@type': 'QuantitativeValue', 'value': float(h), 'unitCode': 'MTR'}
    if w:
        person['weight'] = {'@type': 'QuantitativeValue', 'value': int(w), 'unitCode': 'KGM'}
    return G.page(title, desc, p['url'], CSS + body, [ld_b, person], og_type='profile')


def team_list_page(T, ps):
    nav, ld_b = G.crumbs([('Inicio', '/'), ('Jugadores', '/jugadores/'), (T['n'], None)])
    path = f"/jugadores/{T['slug']}/"
    rows = ''
    for p in sorted(ps, key=lambda q: (q['n'] if q['n'] is not None else 999)):
        age, h, w = phys(p)
        rows += f'<tr><td class="pos num">{p["n"] if p["n"] is not None else ""}</td><td class="team"><a href="{p["url"]}">{e(p["name"])}</a></td><td><span class="abbr">{e(p["pos"])}</span></td><td class="num">{age or ""}</td><td class="num">{h or ""}</td><td class="num">{w or ""}</td></tr>'
    body = nav + f'<h1 class="gm-h1">Jugadores de {e(T["n"])} {YEAR}</h1><p class="gm-meta">{len(ps)} jugadores · {T["conf"]}. Pica un nombre para ver su perfil.</p>'
    body += f'<div class="tbl-box"><table class="roster"><thead><tr><th>#</th><th>Nombre</th><th>Pos.</th><th>Edad</th><th>Est.</th><th>Peso</th></tr></thead><tbody>{rows}</tbody></table></div><p class="note" style="margin-top:6px">Estatura en metros y peso en kilos.</p>'
    body += f'<div class="more" style="margin-top:14px"><a href="{T["url"]}">Página de {e(T["n"])} →</a><a href="/jugadores/">Todos los equipos →</a></div>'
    body += '<p class="note">Roster: Guía ONEFA 2026 de Lucio Trucíos. Edad, estatura y peso: rosters publicados por los equipos.</p>' if T['conf'] == '14 Grandes' else '<p class="note">Edad, estatura y peso: rosters publicados por los equipos. Estadísticas: Uriel González (FBA Stats).</p>'
    return path, G.page(f"Roster {T['n']} {YEAR}: jugadores, edad, estatura y peso | Liga Mayor Unofficial",
                        f"Los {len(ps)} jugadores de {T['n']} en la Liga Mayor ONEFA {YEAR} con número, posición, edad, estatura y peso.", path, CSS + body, [ld_b])


def index_page(P, teams):
    nav, ld_b = G.crumbs([('Inicio', '/'), ('Jugadores', None)])
    idx = [[p['name'], p['T']['n'], p['pos'], p['n'] if p['n'] is not None else '', p['url']] for p in P]
    g = lambda conf: '<div class="tg">' + ''.join(f'<a href="/jugadores/{T["slug"]}/"><img src="{T["img"]}" alt="" width="30" height="30">{e(T["n"])}</a>' for T in teams if T['conf'] == conf) + '</div>'
    body = nav + f'<h1 class="gm-h1">Jugadores de la Liga Mayor {YEAR}</h1><p class="gm-meta">Perfil de {len(P)} jugadores de los 14 Grandes y la Conferencia Nacional: número, posición, edad, estatura, peso y estadísticas.</p>'
    body += '<input id="q" class="srch" type="search" placeholder="Busca un jugador por nombre, número o posición" aria-label="Buscar jugador"><div id="res" class="pl2"></div>'
    body += '<h2 style="font-size:26px;margin-top:18px">14 Grandes</h2>' + g('14 Grandes')
    body += '<h2 style="font-size:26px;margin-top:18px">Conferencia Nacional</h2>' + g('Conferencia Nacional')
    body += '<p class="note">De la Conferencia Nacional solo hay perfil de los líderes estadísticos y de Águilas UACH, porque los demás equipos no publican roster.</p>'
    body += ('<script>const J=' + json.dumps(idx, ensure_ascii=False) + ''';
const nz=s=>String(s).normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
const q=document.getElementById('q'),res=document.getElementById('res');
q.addEventListener('input',()=>{const t=nz(q.value.trim());if(t.length<2){res.innerHTML='';return}
const ws=t.split(/\\s+/);const m=J.filter(j=>{const s=nz(j[0]+' '+j[1]+' '+j[2]+' #'+j[3]);return ws.every(w=>s.includes(w))}).slice(0,30);
res.innerHTML=m.map(j=>`<a href="${j[4]}"><span class="n">${j[3]}</span><span>${j[0].replace(/</g,'&lt;')}<small>${j[1]}</small></span><small>${j[2]}</small></a>`).join('')||'<p class="gm-meta">Sin resultados.</p>'});</script>''')
    return '/jugadores/', G.page(f'Jugadores de la Liga Mayor ONEFA {YEAR}: perfiles, estatura, peso y estadísticas | Liga Mayor Unofficial',
                                 f'Busca a cualquier jugador de los 14 Grandes y la Conferencia Nacional {YEAR}: número, posición, edad, estatura, peso y estadísticas.', '/jugadores/', CSS + body, [ld_b])


# ---------------------------------------------------------------- tablas de roster en las páginas de equipo
def patch_team_pages(P):
    n = 0
    for k, s in G.SLUG.items():
        fp = os.path.join(SITE, 'equipos', s, 'index.html')
        if not os.path.exists(fp):
            continue
        h = open(fp, encoding='utf-8').read()
        ps = [p for p in P if p['liga'] == '14G' and p['team'] == k]
        rows = ''
        for p in ps:
            age, ht, w = phys(p)
            rows += f'<tr><td class="pos num">{p["n"]}</td><td class="team"><a href="{p["url"]}">{e(p["name"])}</a></td><td><span class="abbr">{e(p["pos"])}</span></td><td class="num">{age or ""}</td><td class="num">{ht or ""}</td><td class="num">{w or ""}</td></tr>'
        tbl = f'<table class="roster"><thead><tr><th>#</th><th>Nombre</th><th>Pos.</th><th>Edad</th><th>Est.</th><th>Peso</th></tr></thead><tbody>{rows}</tbody></table>'
        new = re.sub(r'<table class="roster">.*?</table>', lambda m: tbl, h, count=1, flags=re.S)
        new = new.replace('table.roster th:nth-child(3),table.roster td:nth-child(3){text-align:right}',
                          'table.roster th:nth-child(n+3),table.roster td:nth-child(n+3){text-align:right}table.roster td.team a{color:inherit}')
        if '/jugadores/' + s + '/' not in new.split('<table class="roster">')[1]:
            new = new.replace('</table></div></details>', '</table></div><p class="credit" style="margin-top:6px"><a href="/jugadores/' + s + '/">Ver perfiles de los jugadores →</a> Edad, estatura y peso: rosters publicados por los equipos.</p></details>', 1)
        if new != h:
            open(fp, 'w', encoding='utf-8').write(new)
            n += 1
    return n


def main():
    local = None
    if '--local' in sys.argv:
        local = sys.argv[sys.argv.index('--local') + 1]
    fis = list(csv.DictReader(open(os.path.join(DATA, 'fisico_2026.csv'), encoding='utf-8')))
    hp = os.path.join(DATA, 'historial_jugadores.csv')
    hist = list(csv.DictReader(open(hp, encoding='utf-8'))) if os.path.exists(hp) else []
    hist = [r for r in hist if r['Temporada'] != str(YEAR)]
    P = build_players(fis)
    rows, stars = stats(local, P)
    if '--guardar' in sys.argv and rows:
        with open(hp, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, HIST_COLS)
            w.writeheader()
            w.writerows(hist + rows)
        print(f'Temporada {YEAR} guardada en el historial ({len(rows)} renglones).')
    assign_urls(P)
    extra = attach(P, rows, stars, hist)
    print(f"FBA (Modo Blitz): {attach_mb(P, load_mb())} renglones ligados a un perfil")
    cc = load_cc()
    print(f"Cover Cero: {attach_cc(P, cc)}/{len(cc)} renglones ligados a un perfil")
    assign_urls(P)
    out = []
    for p in P:
        out.append((p['url'], G.write(p['url'], player_page(p, P))))
    teams = []
    for key in dict.fromkeys((p['liga'], p['team']) for p in P):
        T = team(*key)
        teams.append(T)
        path, h = team_list_page(T, [p for p in P if (p['liga'], p['team']) == key])
        out.append((path, G.write(path, h)))
    teams.sort(key=lambda T: (T['conf'] != '14 Grandes', slug(T['n'])))
    path, h = index_page(P, teams)
    out.append((path, G.write(path, h)))
    # limpiar perfiles que ya no existen
    keep = {u for u, _ in out}
    root = os.path.join(SITE, 'jugadores')
    for d, _, files in os.walk(root, topdown=False):
        rel = '/' + os.path.relpath(d, SITE).replace(os.sep, '/') + '/'
        if 'index.html' in files and rel not in keep:
            os.remove(os.path.join(d, 'index.html'))
        if os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
    nac = sorted({(p['team'], '' if p['n'] is None else str(p['n']), p['name'], p['pos']) for p in P if p['liga'] == 'NAC' and not p.get('fis')})
    with open(NACP_FILE, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Equipo', 'Numero', 'Jugador', 'Pos'])
        w.writerows(nac)
    # datos físicos para el roster desplegable de la portada
    dj = {}
    for p in P:
        if p['liga'] != '14G':
            continue
        age, h, w = phys(p)
        if age or h or w:
            dj.setdefault(p['team'], {})[f"{p['n']}|{slug(p['name'])}"] = [int(age) if age else None, h, int(w) if w else None]
    jp = os.path.join(SITE, 'jugadores', 'datos.json')
    js = json.dumps(dj, ensure_ascii=False, separators=(',', ':'))
    if not os.path.exists(jp) or open(jp, encoding='utf-8').read() != js:
        open(jp, 'w', encoding='utf-8').write(js)
    nt = patch_team_pages(P)
    # sitemap
    sp = os.path.join(SITE, 'sitemap.xml')
    sm = open(sp, encoding='utf-8').read()
    urls = [u for u in re.findall(r'<url>.*?</url>', sm, re.S) if '/jugadores/' not in u]
    old = {m.group(1): m.group(2) for m in re.finditer(r'<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>', sm)}
    today = datetime.date.today().isoformat()
    for u, ch in out:
        loc = URL + u
        urls.append(f'<url><loc>{loc}</loc><lastmod>{today if ch or loc not in old else old[loc]}</lastmod></url>')
    new = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(urls) + '\n</urlset>\n'
    if new != sm:
        open(sp, 'w', encoding='utf-8').write(new)
    print(f'{len(P)} jugadores ({len(extra)} de la Nacional sin roster), {sum(c for _, c in out)} páginas cambiaron, {nt} páginas de equipo actualizadas')


if __name__ == '__main__':
    main()
