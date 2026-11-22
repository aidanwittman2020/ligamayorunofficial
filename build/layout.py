"""Pone el mismo encabezado y el layout compartido (site/layout.css) en todas las páginas del sitio.

Se corre al final, después de generate.py y jugadores.py: reemplaza el <header class="top"> de cada
página por el encabezado único (menú de compu + botones 14 Grandes / Nacional) y enlaza /layout.css.
La página de inicio (site/index.html) ya trae su propio encabezado; solo se le enlaza el CSS.
"""
import os
import re

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site')
CSS_V = '11'
LINK = f'<link rel="stylesheet" href="/layout.css?v={CSS_V}" id="lay">'

MENU_14 = [('Inicio', '/#inicio'), ('Tabla', '/#tabla'), ('Juegos', '/#juegos'), ('Playoffs', '/#playoffs'), ('Equipos', '/#equipos'),
           ('Líderes', '/#stats'), ('Jugadores', '/jugadores/'), ('Historia', '/historia/'), ('Más', '/#mas')]
MENU_NAC = [('Inicio', '/nacional/#inicio'), ('Tabla', '/nacional/#tabla'), ('Juegos', '/nacional/#juegos'), ('Playoffs', '/nacional/#playoffs'), ('Equipos', '/nacional/#equipos'),
            ('Líderes', '/nacional/#stats'), ('Jugadores', '/jugadores/'), ('Historia', '/historia/'), ('Más', '/nacional/#mas')]

FIT_JS = '''<script id="fit-nav">(function(){const n=document.getElementById('topnav');if(!n)return;
const hi=n.querySelector('a[href="/historia/"]');
function fit(){n.style.gap='';if(hi)hi.style.display='';if(innerWidth<769)return;let g=parseFloat(getComputedStyle(n).columnGap)||28;
while(n.scrollWidth>n.clientWidth+1&&g>12){g-=2;n.style.gap=g+'px'}
if(n.scrollWidth>n.clientWidth+1&&hi){hi.style.display='none';n.style.gap='';g=parseFloat(getComputedStyle(n).columnGap)||28;while(n.scrollWidth>n.clientWidth+1&&g>12){g-=2;n.style.gap=g+'px'}}}
fit();addEventListener('resize',fit);document.fonts&&document.fonts.ready.then(fit)})();
['pageswap','pagereveal'].forEach(t=>addEventListener(t,e=>{const v=e.viewTransition;if(v){v.ready.catch(()=>{});v.finished.catch(()=>{});v.updateCallbackDone&&v.updateCallbackDone.catch(()=>{})}}));</script>'''

NAC_JS = '''<script id="lay-nac">(function(){const ok=['inicio','mas','tabla','juegos','equipos','stats','playoffs','info'];
function sync(){const t=typeof tab!=='undefined'?tab:'';document.querySelectorAll('#topnav a').forEach(a=>{const h=a.getAttribute('href');a.classList.toggle('on',h==='/nacional/#'+t)})}
addEventListener('hashchange',()=>{const h=location.hash.slice(1);if(ok.includes(h)){tab=h;autoTab=false;document.getElementById('sheet')&&(document.getElementById('sheet').hidden=true);render();scrollTo(0,0)}sync()});
try{const r0=render;render=function(){r0.apply(this,arguments);sync()}}catch(e){}
sync()})();</script>'''


ICONS = {'inicio': '<path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z"/>', 'tabla': '<path d="M4 6h16M4 12h16M4 18h16"/>',
         'juegos': '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
         'equipos': '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/>', 'stats': '<path d="M5 20V11M12 20V5M19 20v-6"/>',
         'mas': '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>'}


def bottom(path):
    """Barra inferior del celular (la misma de la portada) para las páginas interiores."""
    nac = path.startswith('nacional/') or '/nacional/' in path
    base = '/nacional/' if nac else '/'
    on = 'juegos' if path.startswith('juegos/') else 'equipos' if path.startswith('equipos/') else 'mas'
    items = [('inicio', 'Inicio'), ('tabla', 'Tabla'), ('juegos', 'Juegos'), ('equipos', 'Equipos'), ('stats', 'Líderes'), ('mas', 'Más')]
    return ('<nav class="btm" aria-label="Secciones">' + ''.join(
        f'<a href="{base}#{k}"{" aria-current=\"page\"" if k == on else ""}><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[k]}</svg>{t}</a>' for k, t in items) + '</nav>')


def header(path):
    nac = path.startswith('nacional/') or '/nacional/' in path
    menu = MENU_NAC if nac else MENU_14
    if path.startswith('jugadores/'):
        on = '/jugadores/'
    elif path.startswith('historia/'):
        on = '/historia/'
    elif path.startswith('equipos/'):
        on = '/#equipos'
    elif path.startswith('juegos/'):
        on = '/#juegos'
    elif nac:
        on = '/nacional/#inicio'
    else:
        on = ''
    ON = ' class="on"'
    links = ''.join(f'<a href="{u}"{ON if u == on else ""}>{t}</a>' for t, u in menu)
    srch = ('<a class="hsrch" href="/jugadores/?buscar" aria-label="Buscar jugador" title="Buscar jugador"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2.4" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21"/></svg></a>')
    confs = f'<div class="confs">{srch}<a href="/"{"" if nac else ON}>14 Grandes</a><a href="/nacional/"{ON if nac else ""}>Nacional</a></div>'
    app = ' data-app="1"' if nac else ''
    return (f'<header class="top"{app}><div class="in"><a class="brand" href="/">Liga Mayor <span>Unofficial</span></a>'
            f'<nav class="topnav" id="topnav" aria-label="Secciones">{links}</nav>{confs}</div></header>')


def main():
    n = 0
    for root, _, files in os.walk(SITE):
        for f in files:
            if not f.endswith('.html') or f.startswith('google'):
                continue
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, SITE).replace(os.sep, '/')
            h = open(fp, encoding='utf-8').read()
            new = re.sub(r'<link rel="stylesheet" href="/layout\.css[^"]*" id="lay">', '', h)
            # rendimiento: fuentes sin cursivas que no se usan, preconnect a fonts.gstatic.com y Analytics después de cargar
            new = new.replace('family=Barlow+Condensed:ital,wght@0,500;0,600;0,700;0,800;1,700;1,800', 'family=Barlow+Condensed:wght@500;600;700;800')
            if 'fonts.googleapis.com' in new and 'href="https://fonts.gstatic.com"' not in new:
                new = new.replace('<link rel="preconnect" href="https://fonts.googleapis.com">', '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>', 1)
            new = new.replace('<script async src="https://www.googletagmanager.com/gtag/js?id=G-VFD5Y2D5PC"></script>',
                              '<script>addEventListener(\'load\',()=>setTimeout(()=>{const s=document.createElement(\'script\');s.async=true;s.src=\'https://www.googletagmanager.com/gtag/js?id=G-VFD5Y2D5PC\';document.head.appendChild(s)},1200))</script>')
            new = new.replace('</head>', LINK + '</head>', 1)
            if rel != 'index.html':
                new = re.sub(r'<header class="top".*?</header>', lambda m: header(rel), new, count=1, flags=re.S)
            new = re.sub(r'<script id="fit-nav">.*?</script>', '', new, flags=re.S)
            new = new.replace('</body>', FIT_JS + '</body>', 1)
            new = re.sub(r'<nav class="btm".*?</nav>', '', new, flags=re.S)
            if rel not in ('index.html', 'nacional/index.html') and '</body>' in new:
                new = new.replace('</body>', bottom(rel) + '</body>', 1)
            if rel == 'nacional/index.html':
                new = re.sub(r'<script id="lay-nac">.*?</script>', '', new, flags=re.S)
                new = new.replace('</body>', NAC_JS + '</body>', 1)
            if new != h:
                open(fp, 'w', encoding='utf-8').write(new)
                n += 1
    print(f'layout: {n} páginas actualizadas')


if __name__ == '__main__':
    main()
