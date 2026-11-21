#!/usr/bin/env python3
"""Página de la LFA (/lfa/): tabla, juegos, equipos, draft desde la ONEFA e historia del Tazón México.

Lee las pestañas LFA_Equipos y LFA_Juegos de la hoja. Mientras no haya juegos de la temporada nueva,
muestra la tabla final de la temporada anterior. La página también se actualiza sola en el navegador
(marcadores en vivo) leyendo la misma hoja.

Uso: python3 build/lfa.py [--local DIR]

EN PAUSA: la sección está oculta (no se publica ni aparece en el menú). Para activarla, agregar
el paso al workflow y el link "LFA" al menú.
"""
import csv, io, json, os, re, sys, html, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate as G

e = html.escape
SEASON = 2027
G.GID.update({'lfa_juegos': 702700001, 'lfa_equipos': 702700002})
G.HEADER = G.HEADER.replace('<a class="on" href="/#tabla">', '<a href="/#tabla">').replace('<a href="/lfa/">', '<a class="on" href="/lfa/">', 1)

COLOR = {'CAU': '#B08D2C', 'DIN': '#2E7D32', 'GAL': '#2B2B2B', 'MEX': '#8B1E3F', 'OSO': '#1F3A68', 'RAP': '#5B2C83', 'REY': '#1565C0', 'TOR': '#A31F24'}
SHORT = {'CAU': 'Caudillos', 'DIN': 'Dinos', 'GAL': 'Gallos Negros', 'MEX': 'Mexicas', 'OSO': 'Osos', 'RAP': 'Raptors', 'REY': 'Reyes', 'TOR': 'Toros'}
PREV = {'season': 2026, 'note': 'Temporada regular 2026 (7 equipos). Desempate: duelo directo.',
        'table': [['CAU', 5, 1, 187, 91], ['OSO', 5, 1, 169, 102], ['DIN', 4, 2, 159, 127], ['RAP', 3, 3, 145, 158],
                  ['REY', 2, 4, 117, 119], ['GAL', 1, 5, 89, 158], ['MEX', 1, 5, 76, 187]],
        'playoffs': [['Semifinal', '30 may 2026', 'RAP', 23, 25, 'CAU'], ['Semifinal', '30 may 2026', 'DIN', 5, 33, 'OSO'],
                     ['Tazón México IX', '7 jun 2026', 'OSO', 12, 24, 'CAU']]}
TAZON = [('I', 2016, 'Mayas', '29-13', 'Raptors', 'CDMX'), ('II', 2017, 'Mayas', '24-18', 'Dinos', 'CDMX'),
         ('III', 2018, 'Mexicas', '', 'Raptors', 'CDMX'), ('IV', 2019, 'Condors', '20-16', 'Raptors', 'CDMX'),
         ('V', 2022, 'Fundidores', '18-14', 'Gallos Negros', 'Tijuana'), ('VI', 2023, 'Caudillos', '19-0', 'Dinos', 'Chihuahua'),
         ('VII', 2024, 'Caudillos', '34-14', 'Raptors', 'Querétaro'), ('VIII', 2025, 'Mexicas', '13-12', 'Osos', 'Puebla'),
         ('IX', 2026, 'Caudillos', '24-12', 'Osos', 'Chihuahua')]
DRAFT = [(1, 'REY', 'Joseph Cortés', 'DL', 'Borregos Puebla', 'borregos-puebla'), (2, 'GAL', 'Roberto Villalón', 'OL', 'Aztecas UDLAP', 'aztecas-udlap'),
         (3, 'RAP', 'Daniel Díaz', 'WR', 'Linces UVM', 'linces-uvm'), (4, 'DIN', 'Steven Zambrano', 'OL', 'Borregos Monterrey', 'borregos-monterrey'),
         (5, 'CAU', 'Alonso Meraz', 'DB', 'Borregos CEM', 'borregos-cem'), (6, 'OSO', 'Pablo Treviño', 'DE', 'Auténticos Tigres', 'autenticos-tigres'),
         (7, 'MEX', 'Jonathan Castañeda', 'WR', 'Borregos CEM', 'borregos-cem')]

CSS = '''<style>
.lnav{position:sticky;top:0;z-index:5;display:flex;gap:6px;overflow-x:auto;background:var(--bg);padding:8px 0;margin:0 0 4px;scrollbar-width:none}
.lnav a{flex:none;font-family:var(--display);font-weight:700;font-size:14px;letter-spacing:.04em;text-transform:uppercase;text-decoration:none;padding:6px 10px;border:1px solid var(--line);border-radius:4px;color:var(--ink);background:var(--surface)}
.lch{display:inline-grid;place-items:center;width:32px;height:32px;border-radius:4px;color:#fff;font-family:var(--display);font-weight:800;font-size:13px;letter-spacing:.02em;flex:none}
.lt{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--line);border-radius:4px;overflow:hidden;font-variant-numeric:tabular-nums}
.lt th,.lt td{padding:8px 6px;border-bottom:1px solid var(--line);font-size:14px;text-align:right}
.lt th{font-family:var(--display);font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.lt td.tm,.lt th.tm{text-align:left}.lt td.tm div{display:flex;align-items:center;gap:8px;font-weight:600}
.lt tr.q td{background:color-mix(in srgb,var(--good) 7%,transparent)}
.lg{display:grid;gap:8px}
.lgm{display:grid;grid-template-columns:1fr auto;gap:4px 10px;align-items:center;background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:10px 12px}
.lgm .m{grid-column:1/-1;display:flex;justify-content:space-between;font-size:12px;color:var(--muted);font-family:var(--display);letter-spacing:.05em;text-transform:uppercase}
.lgm .r{display:flex;align-items:center;gap:8px;font-weight:600}.lgm .r.l,.lgm .s.l{opacity:.55}
.lgm .s{font-family:var(--display);font-weight:800;font-size:24px;text-align:right}
.lgm .live{color:var(--bad);font-weight:700}
.tcs{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:8px}
.tc{background:var(--surface);border:1px solid var(--line);border-radius:4px;padding:12px;display:grid;grid-template-columns:auto 1fr;gap:4px 10px}
.tc b{font-size:15px}.tc dl{grid-column:1/-1;margin:6px 0 0;display:grid;grid-template-columns:auto 1fr;gap:2px 10px;font-size:13px}
.tc dt{color:var(--muted)}.tc dd{margin:0}
.tc.tbd{border-style:dashed;color:var(--muted)}
.note{font-size:12px;color:var(--muted);margin-top:10px}
@media (max-width:480px){.lt .hm{display:none}.lt th,.lt td{padding:8px 4px;font-size:13px}.lt .lch{width:28px;height:28px;font-size:12px}}
</style>'''


def chip(k, name=''):
    return f'<span class="lch" style="background:{COLOR.get(k, "#555")}" title="{e(name)}">{e(k)}</span>'


def load(local):
    def rows(n):
        try:
            R = [r for r in csv.reader(io.StringIO(G.fetch(n, local))) if any(x.strip() for x in r)]
        except Exception as ex:
            print('No se pudo leer', n, ex)
            sys.exit(0)
        if not R:
            return []
        H = [G.norm(h) for h in R[0]]
        return [{h: (r[i].strip() if i < len(r) else '') for i, h in enumerate(H)} for r in R[1:]]
    teams = [t for t in rows('lfa_equipos') if t.get('clave')]
    games = []
    for r in rows('lfa_juegos'):
        a, h = r.get('visitante', '').upper(), r.get('local', '').upper()
        if not a or not h:
            continue
        games.append({'r': r.get('ronda', '').upper().replace('SEMANA', '').strip(), 'd': r.get('fecha', ''), 't': r.get('hora', ''), 'a': a, 'h': h,
                      'as': G.num(r.get('pts visitante')), 'hs': G.num(r.get('pts local')), 'e': G.norm(r.get('estado')), 'det': r.get('detalle', '')})
    return teams, games


JS = r'''<script>
const LFA_B='https://docs.google.com/spreadsheets/d/e/2PACX-1vQNVclYf7g5WHDSejO-E_1xVXBF-KC__RWAbeSLafpfFK-5fxjCE2JegKDDBVnqalEEV97cBnF1PMzU/pub?single=true&output=csv&gid=';
const COLOR=__COLOR__,PREV=__PREV__;let TEAMS=__TEAMS__,GAMES=__GAMES__;
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const nm=s=>String(s||'').normalize('NFD').replace(/[̀-ͯ]/g,'').trim().toLowerCase();
const tn=k=>(TEAMS.find(t=>t.clave===k)||{equipo:k}).equipo;
const chip=k=>`<span class="lch" style="background:${COLOR[k]||'#555'}">${esc(k)}</span>`;
function csv(t){return t.split(/\r?\n/).filter(l=>l.trim()).map(l=>{const o=[];let f='',q=false;for(let i=0;i<l.length;i++){const c=l[i];if(q){if(c=='"'){if(l[i+1]=='"'){f+='"';i++}else q=false}else f+=c}else if(c=='"')q=true;else if(c==','){o.push(f);f=''}else f+=c}o.push(f);return o})}
const fin=g=>g.e==='final'&&g.as!==null&&g.hs!==null,live=g=>/vivo/.test(g.e);
const RN={SF:'Semifinal',F:'Tazón México'};
function table(){const reg=GAMES.filter(g=>/^\d+$/.test(g.r)&&fin(g));if(!reg.length)return null;
  const T={};TEAMS.forEach(t=>T[t.clave]={k:t.clave,w:0,l:0,pf:0,pa:0});
  reg.forEach(g=>{const A=T[g.a],H=T[g.h];if(!A||!H)return;A.pf+=g.as;A.pa+=g.hs;H.pf+=g.hs;H.pa+=g.as;if(g.as>g.hs){A.w++;H.l++}else if(g.hs>g.as){H.w++;A.l++}});
  const rows=Object.values(T);
  const h2h=(x,grp)=>reg.filter(g=>grp.includes(g.a)&&grp.includes(g.h)&&(g.a===x||g.h===x)).reduce((s,g)=>s+((g.a===x?g.as>g.hs:g.hs>g.as)?1:0),0);
  rows.sort((a,b)=>b.w-a.w||a.l-b.l);const out=[];for(let i=0;i<rows.length;){let j=i;while(j<rows.length&&rows[j].w===rows[i].w&&rows[j].l===rows[i].l)j++;const grp=rows.slice(i,j).map(r=>r.k);out.push(...rows.slice(i,j).sort((a,b)=>h2h(b.k,grp)-h2h(a.k,grp)||a.pa-b.pa));i=j}return out}
function renderTabla(){const el=document.getElementById('l-tabla');if(!el)return;const t=table();
  const rows=t?t.map(r=>[r.k,r.w,r.l,r.pf,r.pa]):PREV.table;
  el.innerHTML=`<p class="gm-meta">${t?'Temporada '+__SEASON__+' · pasan los 4 primeros a semifinales.':esc(PREV.note)+' La tabla '+__SEASON__+' aparece aquí con el primer resultado.'}</p><div class="tbl-box"><table class="lt"><thead><tr><th>#</th><th class="tm">Equipo</th><th>G-P</th><th>PF</th><th>PC</th><th class="hm">Dif</th></tr></thead><tbody>${rows.map((r,i)=>`<tr class="${i<4?'q':''}"><td>${i+1}</td><td class="tm"><div>${chip(r[0])}${esc(tn(r[0]))}</div></td><td>${r[1]}-${r[2]}</td><td>${r[3]}</td><td>${r[4]}</td><td class="hm">${r[3]-r[4]>0?'+':''}${r[3]-r[4]}</td></tr>`).join('')}</tbody></table></div>`}
function gm(g){const f=fin(g),lv=live(g),p=f||lv,aw=f&&g.as>g.hs,hw=f&&g.hs>g.as;
  return`<div class="lgm"><div class="m"><span>${RN[g.r]||'Semana '+esc(g.r)}${g.d?' · '+esc(g.d):''}</span><span class="${lv?'live':''}">${lv?'● En vivo'+(g.det?' · '+esc(g.det):''):f?'Final':esc(g.t?g.t+' h':'')}</span></div>
  <div class="r ${f&&!aw?'l':''}">${chip(g.a)}${esc(tn(g.a))}</div><div class="s ${f&&!aw?'l':''}">${p?(g.as??0):''}</div><div class="r ${f&&!hw?'l':''}">${chip(g.h)}${esc(tn(g.h))}</div><div class="s ${f&&!hw?'l':''}">${p?(g.hs??0):''}</div></div>`}
function renderJuegos(){const el=document.getElementById('l-juegos');if(!el)return;
  if(!GAMES.length){el.innerHTML=`<p class="gm-meta">El calendario ${__SEASON__} se publica aquí en cuanto la LFA lo anuncie.</p><h3 style="margin-top:12px">Playoffs ${PREV.season}</h3><div class="lg">${PREV.playoffs.map(p=>gm({r:p[0]==='Semifinal'?'SF':'F',d:p[1],a:p[2],as:p[3],hs:p[4],h:p[5],e:'final'})).join('')}</div>`;return}
  const rs=[...new Set(GAMES.map(g=>g.r))];el.innerHTML=rs.map(r=>`<h3 style="margin-top:12px">${RN[r]||'Semana '+esc(r)}</h3><div class="lg">${GAMES.filter(g=>g.r===r).map(gm).join('')}</div>`).join('')}
async function loadLFA(){try{const [j,t]=await Promise.all([702700001,702700002].map(g=>fetch(LFA_B+g+'&t='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.text():'')));
  if(t){const R=csv(t),H=R.shift().map(nm);const ts=R.map(r=>Object.fromEntries(H.map((h,i)=>[h,(r[i]||'').trim()]))).filter(x=>x.clave);if(ts.length)TEAMS=ts}
  if(j){const R=csv(j),H=R.shift().map(nm),c=n=>H.indexOf(n),n2=x=>{x=String(x||'').trim();return x===''||isNaN(+x)?null:+x};
    GAMES=R.map(r=>({r:(r[c('ronda')]||'').trim().toUpperCase().replace(/^S(EMANA)?\s*(?=\d)/,''),d:(r[c('fecha')]||'').trim(),t:(r[c('hora')]||'').trim(),a:(r[c('visitante')]||'').trim().toUpperCase(),h:(r[c('local')]||'').trim().toUpperCase(),as:n2(r[c('pts visitante')]),hs:n2(r[c('pts local')]),e:nm(r[c('estado')]),det:(r[c('detalle')]||'').trim()})).filter(g=>g.a&&g.h)}
  }catch(e){}renderTabla();renderJuegos()}
renderTabla();renderJuegos();loadLFA();(function tick(){setTimeout(()=>loadLFA().finally(tick),GAMES.some(live)?20000:60000)})();
</script>'''


def build(local):
    teams, games = load(local)
    TN = {t['clave']: t['equipo'] for t in teams}
    nav, ld_b = G.crumbs([('Inicio', '/'), ('LFA', None)])
    body = nav + f'<h1 class="gm-h1">LFA {SEASON}: Liga de Fútbol Americano Profesional</h1>'
    body += f'<p class="gm-meta">Tabla, juegos y marcadores en vivo de la liga profesional de México, los equipos {SEASON} y los jugadores que llegan desde la ONEFA. La temporada se juega en primavera.</p>'
    body += '<nav class="lnav" aria-label="Secciones de la LFA"><a href="#tabla">Tabla</a><a href="#juegos">Juegos</a><a href="#equipos">Equipos</a><a href="#draft">De la ONEFA</a><a href="#historia">Tazón México</a></nav>'
    # tabla y juegos (versión sin JavaScript; el script los reemplaza con lo más nuevo de la hoja)
    rows = ''.join(f'<tr class="{"q" if i < 4 else ""}"><td>{i + 1}</td><td class="tm"><div>{chip(k)}{e(TN.get(k, SHORT.get(k, k)))}</div></td><td>{w}-{l}</td><td>{pf}</td><td>{pa}</td><td class="hm">{"+" if pf - pa > 0 else ""}{pf - pa}</td></tr>'
                   for i, (k, w, l, pf, pa) in enumerate(PREV['table']))
    body += f'<h2 id="tabla" style="font-size:28px;margin-top:18px">Tabla de posiciones</h2><div id="l-tabla"><p class="gm-meta">{e(PREV["note"])}</p><div class="tbl-box"><table class="lt"><thead><tr><th>#</th><th class="tm">Equipo</th><th>G-P</th><th>PF</th><th>PC</th><th class="hm">Dif</th></tr></thead><tbody>{rows}</tbody></table></div></div>'
    body += f'<h2 id="juegos" style="font-size:28px;margin-top:22px">Juegos</h2><div id="l-juegos"><p class="gm-meta">El calendario {SEASON} se publica aquí en cuanto la LFA lo anuncie.</p></div>'
    # equipos
    cards = ''
    for t in teams:
        cap = f'{int(t["capacidad"]):,}' if (t.get('capacidad') or '').isdigit() else '—'
        cards += (f'<div class="tc">{chip(t["clave"], t["equipo"])}<div><b>{e(t["equipo"])}</b><div class="gm-meta" style="margin:0">{e(t.get("ciudad", ""))}</div></div>'
                  f'<dl><dt>Estadio</dt><dd>{e(t.get("estadio") or "—")}</dd><dt>Capacidad</dt><dd>{cap}</dd><dt>Head coach</dt><dd>{e(t.get("head coach") or "—")}</dd></dl></div>')
    cards += '<div class="tc tbd"><span class="lch" style="background:var(--chip);color:var(--muted)">?</span><div><b>Franquicias de expansión</b><div style="font-size:13px">La liga anunció tres equipos nuevos para 2027; Toros Edomex es el primero confirmado. Se han mencionado Mérida, Cancún, Tijuana y un segundo equipo en Monterrey.</div></div></div>'
    body += f'<h2 id="equipos" style="font-size:28px;margin-top:22px">Equipos {SEASON}</h2><div class="tcs">{cards}</div><p class="note">Estadios y head coaches de la temporada 2026; se actualizan cuando los equipos anuncien cambios.</p>'
    # draft
    dr = ''.join(f'<tr><td class="hm">{p}</td><td class="tm"><div>{chip(k, SHORT[k])}<span class="hm">{e(SHORT[k])}</span></div></td><td class="tm"><b>{e(n)}</b><div style="font-size:12px;color:var(--muted)">{pos} · <a href="/equipos/{s}/">{e(sc)}</a></div></td></tr>' for p, k, n, pos, sc, s in DRAFT)
    body += (f'<h2 id="draft" style="font-size:28px;margin-top:22px">De la ONEFA a la LFA</h2><p class="gm-meta">La LFA arma sus equipos con jugadores que terminaron su elegibilidad en la Liga Mayor. Primera ronda del Draft 2026: todos salieron de equipos de los 14 Grandes.</p>'
             f'<div class="tbl-box"><table class="lt"><thead><tr><th class="hm">#</th><th class="tm">Equipo</th><th class="tm">Jugador · posición · equipo ONEFA</th></tr></thead><tbody>{dr}</tbody></table></div>')
    # historia
    tz = ''.join(f'<tr><td class="hm">{n}</td><td>{y}</td><td class="tm"><b>{e(c)}</b></td><td>{s or "—"}</td><td class="tm">{e(r)}</td><td class="tm hm">{e(ci)}</td></tr>' for n, y, c, s, r, ci in reversed(TAZON))
    body += (f'<h2 id="historia" style="font-size:28px;margin-top:22px">Campeones del Tazón México</h2><p class="gm-meta">Caudillos de Chihuahua es el equipo con más títulos (3). Fundidores es hoy Osos de Monterrey. No hubo temporada en 2020 ni 2021.</p>'
             f'<div class="tbl-box"><table class="lt"><thead><tr><th class="hm">Tazón</th><th>Año</th><th class="tm">Campeón</th><th>Final</th><th class="tm">Rival</th><th class="tm hm">Sede</th></tr></thead><tbody>{tz}</tbody></table></div>')
    body += '<p class="note">Sitio no oficial hecho por aficionados; no está afiliado a la LFA. Fuentes: LFA, Wikipedia, Récord, ESPN y ClaroSports. ¿Ves un dato equivocado? <a href="/#info">Avísanos</a>.</p>'
    js = (JS.replace('__COLOR__', json.dumps(COLOR)).replace('__PREV__', json.dumps(PREV, ensure_ascii=False))
          .replace('__TEAMS__', json.dumps(teams, ensure_ascii=False)).replace('__GAMES__', json.dumps(games, ensure_ascii=False)).replace('__SEASON__', str(SEASON)))
    desc = f'LFA {SEASON}: tabla de posiciones, calendario, resultados y marcadores en vivo de la Liga de Fútbol Americano Profesional de México. Equipos, draft desde la ONEFA y campeones del Tazón México.'
    ld = {'@context': 'https://schema.org', '@type': 'SportsOrganization', 'name': 'Liga de Fútbol Americano Profesional (LFA)', 'sport': 'Fútbol americano',
          'member': [{'@type': 'SportsTeam', 'name': t['equipo']} for t in teams]}
    html_ = G.page(f'LFA {SEASON}: tabla, calendario y resultados | Liga Mayor Unofficial', desc, '/lfa/', CSS + body + js, [ld_b, ld])
    ch = G.write('/lfa/', html_)
    sp = os.path.join(G.SITE, 'sitemap.xml')
    sm = open(sp, encoding='utf-8').read()
    if f'<loc>{G.URL}/lfa/</loc>' not in sm:
        sm = sm.replace('</urlset>', f'<url><loc>{G.URL}/lfa/</loc><lastmod>{datetime.date.today().isoformat()}</lastmod></url>\n</urlset>')
        open(sp, 'w', encoding='utf-8').write(sm)
    print('LFA:', len(teams), 'equipos,', len(games), 'juegos,', 'cambió' if ch else 'sin cambios')


if __name__ == '__main__':
    local = sys.argv[sys.argv.index('--local') + 1] if '--local' in sys.argv else None
    build(local)
