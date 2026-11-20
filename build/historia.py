#!/usr/bin/env python3
"""Páginas de cada final ONEFA y ficha de historia en la página de cada equipo.

Lee los datos de site/historia/index.html (la fuente es esa página) y escribe:
  - site/historia/finales/<año>/index.html
  - la sección "Historia" de site/equipos/<equipo>/index.html (entre <!--HIST--> y <!--/HIST-->)
  - las URLs de las finales en site/sitemap.xml

Uso: python3 build/historia.py
"""
import os, re, html, json, datetime, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate as G  # plantillas del sitio (encabezado, estilos, pie)

e = html.escape
SITE, URL = G.SITE, G.URL
H = open(os.path.join(SITE, 'historia', 'index.html'), encoding='utf-8').read()

# ---------------------------------------------------------------- datos de la página de historia
BADGE, SLUGOF = {}, {}
for m in re.finditer(r'<div class="tname"><img class="badge" src="/img/([A-Z_]+)\.png"[^>]*>(?:<a href="/equipos/([a-z-]+)/">)?([^<]+)', H):
    BADGE.setdefault(m.group(3), m.group(1))
    if m.group(2):
        SLUGOF.setdefault(m.group(3), m.group(2))
TEAMNAME = {v: k for k, v in SLUGOF.items()}


def section(k):
    a = H.index(f'id="h-{k}"')
    b = H.find('<section class="hsec"', a + 10)
    return H[a:b if b > 0 else len(H)]


def strip(x):
    return re.sub(r'<[^>]+>', '', x).strip()


FINALS = []
for m in re.finditer(r'<tr><td class="pos num">(\d{4})</td><td class="team">(.*?)</td><td class="ru">(.*?)</td><td class="r num">(.*?)</td></tr>', section('onefa')):
    y, champ, ru, sc = m.groups()
    note = re.search(r"<div class='nt'>(.*?)</div>", ru)
    ru_name = strip(re.sub(r"<div class='nt'>.*?</div>", '', ru))
    score = strip(sc)
    if not re.match(r'\d+-\d+$', score):
        continue
    FINALS.append({'y': int(y), 'c': strip(champ), 'r': ru_name, 's': score, 'note': strip(note.group(1)) if note else ''})
FINALS.sort(key=lambda f: f['y'])


def titles_in(k):
    out = []
    for m in re.finditer(r'<tr><td class="pos num">(\d{4})[a-z]?</td><td class="team">(.*?)</td>', section(k)):
        h = re.search(r'href="/equipos/([a-z-]+)/"', m.group(2))
        if h:
            out.append((int(m.group(1)), h.group(1)))
    return out


ANTES, NAC, OTRAS = titles_in('antes'), titles_in('nacional'), titles_in('otras')


def bimg(name, size=64):
    f = BADGE.get(name)
    return f'<img src="/img/{f}.png" alt="Escudo de {e(name)}" width="{size}" height="{size}" style="image-rendering:pixelated">' if f else f'<span style="width:{size}px;height:{size}px;display:inline-block"></span>'


def tlink(name, inner):
    s = SLUGOF.get(name)
    return f'<a class="gm-t" href="/equipos/{s}/">{inner}</a>' if s else f'<div class="gm-t">{inner}</div>'


# ---------------------------------------------------------------- páginas de finales
def final_page(i, f):
    y, c, r, s = f['y'], f['c'], f['r'], f['s']
    a, b = s.split('-')
    nth = sum(1 for x in FINALS if x['c'] == c and x['y'] <= y)
    path = f'/historia/finales/{y}/'
    nav, ld_b = G.crumbs([('Inicio', '/'), ('Historia', '/historia/'), ('Finales ONEFA', '/historia/#onefa'), (str(y), None)])
    top = ('<style>.gm-top>*{min-width:0}.gm-t b{font-size:17px;overflow-wrap:break-word}.gm-sc{font-size:40px}</style>'
           f'<div class="gm-top">{tlink(c, bimg(c) + f"<b>{e(c)}</b><small>Campeón</small>")}'
           f'<div class="gm-sc"><span>{a}</span><span class="d">–</span><span>{b}</span></div>'
           f'{tlink(r, bimg(r) + f"<b>{e(r)}</b><small>Subcampeón</small>")}'
           f'<div class="gm-st">Final {y}{" · " + e(f["note"]) if f["note"] else ""}</div></div>')
    ord_ = {1: 'primer', 2: 'segundo', 3: 'tercer', 4: 'cuarto', 5: 'quinto', 6: 'sexto', 7: 'séptimo', 8: 'octavo', 9: 'noveno', 10: 'décimo'}
    nth_txt = f'su {ord_[nth]} título' if nth in ord_ else f'su título número {nth}'
    txt = f'<p>{e(c)} venció {a}-{b} a {e(r)} en la final de {y} y se llevó {nth_txt} de la Liga Mayor en la era ONEFA (desde 1978).</p>'
    if f['note']:
        txt += f'<p class="gm-meta">Nota: {e(f["note"])}.</p>'
    same = [x for x in FINALS if {x['c'], x['r']} == {c, r} and x['y'] != y]
    rel = ''
    if same:
        rel = f'<h2 style="font-size:24px;margin-top:22px">Otras finales entre {e(c)} y {e(r)}</h2><div class="more">' + ''.join(
            f'<a href="/historia/finales/{x["y"]}/">{x["y"]}: {e(x["c"])} {x["s"]} {e(x["r"])}</a>' for x in same) + '</div>'
    prev_ = FINALS[i - 1] if i > 0 else None
    next_ = FINALS[i + 1] if i + 1 < len(FINALS) else None
    pn = '<div class="wnav">' + (f'<a href="/historia/finales/{prev_["y"]}/">← Final {prev_["y"]}</a>' if prev_ else '') + \
         '<a href="/historia/#onefa">Todos los campeones</a>' + (f'<a href="/historia/finales/{next_["y"]}/">Final {next_["y"]} →</a>' if next_ else '') + '</div>'
    allf = '<h2 style="font-size:24px;margin-top:22px">Todas las finales ONEFA</h2><div class="wnav">' + ''.join(
        f'<a href="/historia/finales/{x["y"]}/"{" class=\"on\"" if x["y"] == y else ""}>{x["y"]}</a>' for x in reversed(FINALS)) + '</div>'
    body = nav + f'<h1 class="gm-h1">Final ONEFA {y}: {e(c)} {a}-{b} {e(r)}</h1><p class="gm-meta">Campeonato de la Liga Mayor de fútbol americano universitario</p>' + top + txt + pn + rel + allf
    title = f'Final ONEFA {y}: {c} {a}-{b} {r} | Liga Mayor Unofficial'
    desc = f'{c} venció {a}-{b} a {r} en la final de la Liga Mayor ONEFA {y}. Marcador, campeón, subcampeón y todas las finales desde 1978.'
    ld = {'@context': 'https://schema.org', '@type': 'SportsEvent', 'name': f'Final Liga Mayor ONEFA {y}', 'sport': 'Fútbol americano',
          'startDate': str(y), 'eventStatus': 'https://schema.org/EventScheduled',
          'competitor': [{'@type': 'SportsTeam', 'name': c}, {'@type': 'SportsTeam', 'name': r}],
          'description': f'{c} {a}-{b} {r}', 'url': URL + path}
    return path, G.page(title, desc, path, body, [ld_b, ld], og_type='article')


# ---------------------------------------------------------------- ficha de historia de cada equipo
def years_links(ys, finals=False):
    return ', '.join(f'<a href="/historia/finales/{y}/">{y}</a>' if finals else str(y) for y in ys)


def team_card(slug):
    name = TEAMNAME.get(slug)
    champ = [f['y'] for f in FINALS if SLUGOF.get(f['c']) == slug]
    ru = [f['y'] for f in FINALS if SLUGOF.get(f['r']) == slug]
    ant = sorted(y for y, s in ANTES if s == slug)
    nac = sorted(y for y, s in NAC if s == slug)
    otr = sorted(y for y, s in OTRAS if s == slug)
    tiles = [(len(champ), 'Títulos ONEFA'), (len(champ) + len(ru), 'Finales ONEFA jugadas'),
             (max(champ) if champ else '—', 'Último título ONEFA'), (len(ant) + len(nac) + len(otr), 'Otros títulos')]
    lines = []
    if champ:
        lines.append(f'<p><b>Campeón ONEFA:</b> {years_links(champ, True)}</p>')
    if ru:
        lines.append(f'<p><b>Subcampeón ONEFA:</b> {years_links(ru, True)}</p>')
    if ant:
        lines.append(f'<p><b>Campeonato nacional (antes de la ONEFA):</b> {years_links(ant)}</p>')
    if nac:
        lines.append(f'<p><b>Conferencia Nacional:</b> {years_links(nac)}</p>')
    if otr:
        lines.append(f'<p><b>CONADEIP y otras conferencias:</b> {years_links(otr)}</p>')
    if not lines:
        lines.append('<p>Todavía no gana un campeonato de Liga Mayor. Su primer título puede llegar en cualquier temporada.</p>')
    return ('<!--HIST--><h2 style="font-size:28px;margin-top:22px">Historia</h2><div class="card">'
            '<div class="facts4 num">' + ''.join(f'<div><b>{v}</b><span>{l}</span></div>' for v, l in tiles) + '</div>'
            + ''.join(lines) + '<p><a href="/historia/#onefa">Todos los campeones de la Liga Mayor →</a></p></div><!--/HIST-->')


def main():
    out = []
    for i, f in enumerate(FINALS):
        p, h = final_page(i, f)
        out.append((p, G.write(p, h)))
    # fichas de equipos
    ed = os.path.join(SITE, 'equipos')
    nteam = 0
    for slug in sorted(os.listdir(ed)):
        fp = os.path.join(ed, slug, 'index.html')
        if not os.path.exists(fp):
            continue
        s = open(fp, encoding='utf-8').read()
        card = team_card(slug)
        if '<!--HIST-->' in s:
            new = re.sub(r'<!--HIST-->.*?<!--/HIST-->', lambda m: card, s, flags=re.S)
        else:
            anchor = s.find('<h2 style="font-size:28px;margin-top:22px">Otros equipos de los 14 Grandes</h2>')
            if anchor < 0:
                continue
            new = s[:anchor] + card + '\n' + s[anchor:]
        if new != s:
            open(fp, 'w', encoding='utf-8').write(new)
            nteam += 1
    # sitemap: agrega las finales que falten
    sp = os.path.join(SITE, 'sitemap.xml')
    sm = open(sp, encoding='utf-8').read()
    today = datetime.date.today().isoformat()
    add = ''.join(f'<url><loc>{URL}{p}</loc><lastmod>{today}</lastmod></url>\n' for p, _ in out if f'<loc>{URL}{p}</loc>' not in sm)
    if add:
        sm = sm.replace('</urlset>', add + '</urlset>')
        open(sp, 'w', encoding='utf-8').write(sm)
    print(f'{len(out)} finales ({sum(c for _, c in out)} cambiaron), {nteam} fichas de equipo actualizadas')


if __name__ == '__main__':
    main()
