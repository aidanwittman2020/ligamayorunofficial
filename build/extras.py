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


def line(p, role):
    m = p['mb']
    if role == 'pase':
        v = m['passing']
        return f"{n0(v.get('YDS'))} yds de pase · {n0(v.get('TD'))} TD"
    if role == 'tierra':
        v = m['rushing']
        return f"{n0(v.get('YDS'))} yds por tierra · {n0(v.get('TD'))} TD"
    if role == 'aire':
        v = m['receiving']
        return f"{n0(v.get('REC'))} recepciones · {n0(v.get('YDS'))} yds · {n0(v.get('TD'))} TD"
    v = m['tackles']
    s = f"{n0(v.get('TAC'))} tackles"
    if v.get('SACKS'):
        s += f" · {n0(v['SACKS'])} sack" + ("" if v['SACKS'] == 1 else "s")
    if m.get('ints', {}).get('INT'):
        s += f" · {n0(m['ints']['INT'])} INT"
    return s


def team_leaders(P):
    """Mejor pasador, corredor, receptor y tackleador de cada equipo según FBA Stats (temporada regular)."""
    L = {}
    for k in G.TEAMS:
        ps = [p for p in P if p['liga'] == '14G' and p['team'] == k and p.get('mb')]
        out = []
        for role, cat, col in ROLES:
            c = [p for p in ps if cat in p['mb'] and (p['mb'][cat].get(col) or 0) > 0]
            if not c:
                continue
            b = max(c, key=lambda p: p['mb'][cat].get(col) or 0)
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
        x = LES.get((p['team'], p['n'])) if p['liga'] == '14G' else None
        if x and (not x[2] or G.norm(x[2]).split()[0] == G.norm(p['name']).split()[0]):
            p['les'] = x[:2]


def badge(les):
    if not les:
        return ''
    return f'<span class="inj" title="{e(les[1])}">{e(les[0])}</span>'


# ---------------------------------------------------------------- portada y fichas de equipo
def patch_home(L, LES):
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
    if M2 != M:
        open(fp, 'w', encoding='utf-8').write(M2)
        return 1
    return 0


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
    return (p.get('mb', {}).get(cat) or {}).get(col) or 0


def pick(P, pos, n, key, used):
    c = [p for p in P if p['liga'] == '14G' and p['pos'] in pos and p.get('mb') and key(p)[0] > 0 and id(p) not in used]
    c.sort(key=key, reverse=True)
    r = c[:n]
    used.update(id(p) for p in r)
    return r


def ideal_page(P, J):
    used = set()
    OFF = [('QB', pick(P, {'QB'}, 1, lambda p: (val(p, 'passing', 'YDS'), val(p, 'passing', 'TD')), used), lambda p: line(p, 'pase')),
           ('RB', pick(P, {'RB', 'FB', 'HB'}, 2, lambda p: (val(p, 'rushing', 'YDS'), val(p, 'rushing', 'TD')), used), lambda p: line(p, 'tierra')),
           ('WR', pick(P, {'WR'}, 3, lambda p: (val(p, 'receiving', 'YDS'), val(p, 'receiving', 'TD')), used), lambda p: line(p, 'aire')),
           ('TE', pick(P, {'TE', 'PB', 'HB'}, 1, lambda p: (val(p, 'receiving', 'YDS'), val(p, 'receiving', 'TD')), used), lambda p: line(p, 'aire'))]
    dl = lambda p: f"{n0(val(p, 'tackles', 'SACKS'))} sacks · {n0(val(p, 'tackles', 'TAC'))} tackles"
    db = lambda p: f"{n0(val(p, 'ints', 'INT'))} INT" + (f" · {n0(val(p, 'tackles', 'TAC'))} tackles" if val(p, 'tackles', 'TAC') else '')
    DEF = [('DL', pick(P, {'DL', 'DE', 'DT', 'NT'}, 4, lambda p: (val(p, 'tackles', 'SACKS'), val(p, 'tackles', 'TAC')), used), dl),
           ('LB', pick(P, {'LB'}, 3, lambda p: (val(p, 'tackles', 'TAC'), val(p, 'tackles', 'SACKS')), used), lambda p: line(p, 'defensa')),
           ('DB', pick(P, {'CB', 'S', 'DB', 'FS', 'SS'}, 4, lambda p: (val(p, 'ints', 'INT'), val(p, 'tackles', 'TAC')), used), db)]
    ST = [('K', pick(P, {'K', 'P'}, 1, lambda p: (val(p, 'kickers', 'PTS'), 0), used), lambda p: f"{n0(val(p, 'kickers', 'PTS'))} puntos · {n0(val(p, 'kickers', 'PAT'))} PAT")]

    def grid(title, groups):
        cards = ''
        for pos, ps, fn in groups:
            for p in ps:
                cards += (f'<a class="xi" href="{p["url"]}"><div class="xa">{avatar(p, J)}</div><div><span class="xp">{pos}</span><b>{e(p["name"])}</b>{badge(p.get("les"))}'
                          f'<small>{e(p["T"]["n"])} · #{p["n"]}</small><em>{e(fn(p))}</em></div></a>')
        return f'<h2 style="font-size:26px;margin-top:22px">{title}</h2><div class="xig">{cards}</div>'

    path = f'/equipo-ideal-{YEAR}/'
    nav, ld_b = G.crumbs([('Inicio', '/'), (f'Equipo ideal {YEAR}', None)])
    body = nav + f'<h1 class="gm-h1">Equipo ideal {YEAR} de los 14 Grandes</h1>'
    body += ('<p class="gm-meta">Selección automática con los números de la temporada regular (FBA Stats). No es un premio oficial de la ONEFA: '
             'se escoge al líder de cada posición según la posición del roster.</p>')
    body += grid('Ofensiva', OFF) + grid('Defensiva', DEF) + grid('Equipos especiales', ST)
    body += ('<div class="card" style="margin-top:14px"><b>¿Cómo se escoge?</b><ul class="pv"><li>QB, RB, WR y TE: más yardas en su categoría (desempate por TD).</li>'
             '<li>Línea defensiva: más sacks (desempate por tackles). Linebackers: más tackles. Secundaria: más intercepciones (desempate por tackles).</li>'
             '<li>Pateador: más puntos.</li><li>No hay línea ofensiva porque no existen estadísticas públicas de linieros ofensivos.</li></ul></div>')
    body += '<p class="note">Estadísticas: Uriel González (FBA Stats), publicadas también por <a href="https://www.modoblitz.com/estadisticas-onefa" rel="noopener">Modo Blitz</a>. Posiciones: Guía ONEFA 2026 de Lucio Trucíos.</p>'
    return path, G.page(f'Equipo ideal {YEAR} de la Liga Mayor ONEFA (14 Grandes) | Liga Mayor Unofficial',
                        f'El equipo ideal de los 14 Grandes {YEAR} según las estadísticas de la temporada regular: QB, corredores, receptores, línea defensiva, linebackers y secundaria.',
                        path, J.CSS + body, [ld_b])


def prospects_page(P, J):
    CATS = [('passing', 'YDS', 'pase', 10), ('rushing', 'YDS', 'tierra', 15), ('receiving', 'YDS', 'aire', 15), ('tackles', 'TAC', 'defensa', 20),
            ('tackles', 'SACKS', 'defensa', 10), ('ints', 'INT', 'defensa', 10)]
    top = {}
    ps14 = [p for p in P if p['liga'] == '14G' and p.get('mb')]
    for cat, col, role, n in CATS:
        r = sorted([p for p in ps14 if val(p, cat, col) > 0], key=lambda p: val(p, cat, col), reverse=True)[:n]
        for i, p in enumerate(r):
            top.setdefault(id(p), (p, role, i + 1, cat, col))
    rows = []
    for p, role, rk, cat, col in top.values():
        age, h, w = J.phys(p)
        if not age or int(age) < 22:
            continue
        lbl = {('passing', 'YDS'): 'en yardas de pase', ('rushing', 'YDS'): 'en yardas por tierra', ('receiving', 'YDS'): 'en yardas por recepción',
               ('tackles', 'TAC'): 'en tackles', ('tackles', 'SACKS'): 'en sacks', ('ints', 'INT'): 'en intercepciones'}[(cat, col)]
        rows.append((rk, p, age, h, w, f'{rk}.º de la liga {lbl}', line(p, role) if role != 'defensa' or col == 'TAC' else (f"{n0(val(p, cat, col))} " + ('sacks' if col == 'SACKS' else 'INT'))))
    rows.sort(key=lambda x: (x[0], -int(x[2])))
    tr = ''.join(f'<tr><td class="team"><a href="{p["url"]}">{e(p["name"])}</a>{badge(p.get("les"))}<small style="display:block;color:var(--muted)">{e(p["T"]["n"])} · #{p["n"]}</small></td>'
                 f'<td><span class="abbr">{e(p["pos"])}</span></td><td class="num">{age}</td><td class="num">{h or ""}</td><td class="num">{w or ""}</td>'
                 f'<td>{e(rk_)}<small style="display:block;color:var(--muted)">{e(ln)}</small></td></tr>' for _, p, age, h, w, rk_, ln in rows)
    path = f'/prospectos-{YEAR}/'
    nav, ld_b = G.crumbs([('Inicio', '/'), (f'Prospectos {YEAR}', None)])
    body = nav + f'<h1 class="gm-h1">Prospectos {YEAR}: veteranos con números de élite</h1>'
    body += ('<p class="gm-meta">Jugadores de 22 años o más que están entre los líderes de los 14 Grandes en alguna categoría de FBA Stats. '
             'Son candidatos naturales a dar el salto al fútbol profesional.</p>')
    body += ('<div class="card" style="margin:8px 0 12px"><b>Ojo:</b> no es una lista oficial ni sabemos en qué año de elegibilidad va cada jugador. '
             'La edad sale de los rosters publicados por los equipos y sirve solo como aproximación.</div>')
    body += f'<div class="tbl-box"><table class="roster"><thead><tr><th>Jugador</th><th>Pos.</th><th>Edad</th><th>Est.</th><th>Peso</th><th>Por qué</th></tr></thead><tbody>{tr}</tbody></table></div>'
    body += '<p class="note">Estadísticas: Uriel González (FBA Stats). Edad, estatura (m) y peso (kg): rosters publicados por los equipos.</p>'
    return path, G.page(f'Prospectos {YEAR} de la Liga Mayor ONEFA: veteranos líderes en estadísticas | Liga Mayor Unofficial',
                        f'Jugadores de 22 años o más entre los líderes estadísticos de los 14 Grandes {YEAR}: edad, estatura, peso y números.', path, J.CSS + body, [ld_b])


def y2027_page(J):
    path = '/2027/'
    nav, ld_b = G.crumbs([('Inicio', '/'), ('Qué cambia en 2027', None)])
    t14 = sorted([v['n'] for k, v in G.TEAMS.items() if k != 'CET'] + ['Leones Anáhuac Querétaro'])
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
         'tackles': ['JJ', 'TAC', 'SACKS', 'FR'], 'ints': ['INT', 'YDS'], 'kickers': ['PAT', 'PTS']}


def stats_json(P, J):
    out = []
    for p in P:
        if p['liga'] != '14G':
            continue
        age, h, w = J.phys(p)
        mb = {c: [p['mb'][c].get(k) for k in ks] for c, ks in SKEYS.items() if c in (p.get('mb') or {})}
        if not (mb or age or h or w):
            continue
        out.append([p['name'], p['team'], p['T']['n'], p['pos'], p['n'], int(age) if age else None, float(h) if h else None, int(w) if w else None, p['url'], mb])
    js = json.dumps({'keys': SKEYS, 'p': out}, ensure_ascii=False, separators=(',', ':'))
    fp = os.path.join(SITE, 'jugadores', 'stats.json')
    if not os.path.exists(fp) or open(fp, encoding='utf-8').read() != js:
        open(fp, 'w', encoding='utf-8').write(js)


COMPARE_JS = r'''<script>
const nz=s=>String(s).normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase();const E=x=>String(x??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const ROWS=[['Físico',[['Edad',p=>p[5],0],['Estatura (m)',p=>p[6],0],['Peso (kg)',p=>p[7],0]]],
['Pase',[['Yardas','passing',4],['TD','passing',5],['Completos','passing',1],['Intentos','passing',2],['% completos','passing',3,v=>(v*100).toFixed(1)],['Intercepciones','passing',6,null,1]]],
['Tierra',[['Yardas','rushing',2],['Acarreos','rushing',1],['Promedio','rushing',3,v=>v.toFixed(1)],['TD','rushing',4]]],
['Recepción',[['Yardas','receiving',2],['Recepciones','receiving',1],['Promedio','receiving',3,v=>v.toFixed(1)],['TD','receiving',4]]],
['Defensa',[['Tackles','tackles',1],['Sacks','tackles',2],['Balones recuperados','tackles',3],['Intercepciones','ints',0]]],
['Pateo',[['Puntos','kickers',1],['PAT','kickers',0]]]];
let D=null;const sel=[null,null];
function get(p,r){if(!p)return null;if(typeof r[1]==='function')return r[1](p);const c=p[9][r[1]];return c?c[r[2]]:null}
function draw(){const A=sel[0],B=sel[1],o=document.getElementById('cmp');if(!A&&!B){o.innerHTML='';return}
 let h=`<table class="cmpx"><thead><tr><th>${A?`<a href="${A[8]}">${E(A[0])}</a><small>${E(A[2])} · ${E(A[3])} #${A[4]}</small>`:''}</th><th></th><th>${B?`<a href="${B[8]}">${E(B[0])}</a><small>${E(B[2])} · ${E(B[3])} #${B[4]}</small>`:''}</th></tr></thead><tbody>`;
 for(const[g,rs]of ROWS){const lines=rs.map(r=>{const a=get(A,r),b=get(B,r);if(a==null&&b==null)return'';const f=v=>v==null?'—':r[3]?r[3](v):(typeof r[1]==='function'?v:Math.round(v).toLocaleString('es-MX'));
  const lowGood=r[4],win=a!=null&&b!=null&&a!==b&&r[1]!=='function'&&typeof r[1]!=='function'?((a>b)!==!!lowGood?0:1):-1;
  return`<tr><td class="${win===0?'w':''}">${f(a)}</td><th>${r[0]}</th><td class="${win===1?'w':''}">${f(b)}</td></tr>`}).join('');
  if(lines)h+=`<tr class="g"><td colspan="3">${g}</td></tr>`+lines}
 o.innerHTML=h+'</tbody></table><p class="note">Temporada regular · FBA Stats. En verde, el mejor número de los dos.</p>';
 try{history.replaceState(null,'','?a='+encodeURIComponent(A?A[8]:'')+'&b='+encodeURIComponent(B?B[8]:''))}catch(e){}}
function box(i){const q=document.getElementById('q'+i),r=document.getElementById('r'+i);
 q.addEventListener('input',()=>{const t=nz(q.value.trim());if(t.length<2||!D){r.innerHTML='';return}const ws=t.split(/\s+/);
  const m=D.filter(p=>{const s=nz(p[0]+' '+p[2]+' '+p[3]+' #'+p[4]);return ws.every(w=>s.includes(w))}).slice(0,8);
  r.innerHTML=m.map((p,j)=>`<button type="button" data-j="${D.indexOf(p)}"><b>${E(p[0])}</b><small>${E(p[2])} · ${E(p[3])} #${p[4]}</small></button>`).join('')||'<p class="gm-meta">Sin resultados.</p>'});
 r.addEventListener('click',ev=>{const b=ev.target.closest('button');if(!b)return;sel[i]=D[+b.dataset.j];q.value=sel[i][0];r.innerHTML='';draw()})}
fetch('/jugadores/stats.json').then(r=>r.json()).then(j=>{D=j.p;const u=new URLSearchParams(location.search);[u.get('a'),u.get('b')].forEach((x,i)=>{const p=x&&D.find(p=>p[8]===x);if(p){sel[i]=p;document.getElementById('q'+i).value=p[0]}});draw()});
box(0);box(1);
</script>'''


def compare_page(J):
    path = '/jugadores/comparar/'
    nav, ld_b = G.crumbs([('Inicio', '/'), ('Jugadores', '/jugadores/'), ('Comparar', None)])
    body = nav + f'<h1 class="gm-h1">Compara a dos jugadores</h1><p class="gm-meta">Escribe dos nombres de los 14 Grandes y ve sus números {YEAR} lado a lado.</p>'
    body += ('<div class="cmpp"><div><input id="q0" class="srch" type="search" placeholder="Jugador 1" aria-label="Jugador 1" autocomplete="off"><div id="r0" class="cres"></div></div>'
             '<div><input id="q1" class="srch" type="search" placeholder="Jugador 2" aria-label="Jugador 2" autocomplete="off"><div id="r1" class="cres"></div></div></div><div id="cmp"></div>')
    body += '<p class="note">Estadísticas: Uriel González (FBA Stats). Edad, estatura y peso: rosters publicados por los equipos.</p>' + COMPARE_JS
    return path, G.page(f'Compara jugadores de la Liga Mayor ONEFA {YEAR} | Liga Mayor Unofficial',
                        f'Compara lado a lado las estadísticas y el físico de dos jugadores de los 14 Grandes {YEAR}.', path, J.CSS + body, [ld_b])


def pages(P, J):
    out = []
    for path, h in (ideal_page(P, J), prospects_page(P, J), y2027_page(J), compare_page(J)):
        out.append((path, G.write(path, h)))
    stats_json(P, J)
    return out
