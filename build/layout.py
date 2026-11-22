"""Pone el mismo encabezado y el layout compartido (site/layout.css) en todas las páginas del sitio.

Se corre al final, después de generate.py y jugadores.py: reemplaza el <header class="top"> de cada
página por el encabezado único (menú de compu + botones 14 Grandes / Nacional) y enlaza /layout.css.
La página de inicio (site/index.html) ya trae su propio encabezado; solo se le enlaza el CSS.
"""
import os
import re

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'site')
CSS_V = '7'
LINK = f'<link rel="stylesheet" href="/layout.css?v={CSS_V}" id="lay">'

MENU_14 = [('Inicio', '/#inicio'), ('Tabla', '/#tabla'), ('Juegos', '/#juegos'), ('Playoffs', '/#playoffs'), ('Equipos', '/#equipos'),
           ('Líderes', '/#stats'), ('Jugadores', '/jugadores/'), ('Historia', '/historia/')]
MENU_NAC = [('Inicio', '/nacional/#inicio'), ('Tabla', '/nacional/#tabla'), ('Juegos', '/nacional/#juegos'), ('Playoffs', '/nacional/#playoffs'), ('Equipos', '/nacional/#equipos'),
            ('Líderes', '/nacional/#stats'), ('Jugadores', '/jugadores/'), ('Historia', '/historia/')]

FIT_JS = '''<script id="fit-nav">(function(){const n=document.getElementById('topnav');if(!n)return;
function fit(){if(innerWidth<769){n.style.gap='';return}n.style.gap='';let g=parseFloat(getComputedStyle(n).columnGap)||28;
while(n.scrollWidth>n.clientWidth+1&&g>8){g-=2;n.style.gap=g+'px'}}
fit();addEventListener('resize',fit);document.fonts&&document.fonts.ready.then(fit)})();</script>'''

NAC_JS = '''<script id="lay-nac">(function(){const ok=['inicio','mas','tabla','juegos','equipos','stats','playoffs','info'];
function sync(){const t=typeof tab!=='undefined'?tab:'';document.querySelectorAll('#topnav a').forEach(a=>{const h=a.getAttribute('href');a.classList.toggle('on',h==='/nacional/#'+t)})}
addEventListener('hashchange',()=>{const h=location.hash.slice(1);if(ok.includes(h)){tab=h;autoTab=false;document.getElementById('sheet')&&(document.getElementById('sheet').hidden=true);render();scrollTo(0,0)}sync()});
try{const r0=render;render=function(){r0.apply(this,arguments);sync()}}catch(e){}
sync()})();</script>'''


def header(path):
    nac = path.startswith('nacional/')
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
            new = new.replace('</head>', LINK + '</head>', 1)
            if rel != 'index.html':
                new = re.sub(r'<header class="top".*?</header>', lambda m: header(rel), new, count=1, flags=re.S)
            new = re.sub(r'<script id="fit-nav">.*?</script>', '', new, flags=re.S)
            new = new.replace('</body>', FIT_JS + '</body>', 1)
            if rel == 'nacional/index.html':
                new = re.sub(r'<script id="lay-nac">.*?</script>', '', new, flags=re.S)
                new = new.replace('</body>', NAC_JS + '</body>', 1)
            if new != h:
                open(fp, 'w', encoding='utf-8').write(new)
                n += 1
    print(f'layout: {n} páginas actualizadas')


if __name__ == '__main__':
    main()
