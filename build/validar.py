"""Revisión automática de la hoja antes de publicar (no detiene nada: deja un reporte).

Revisa que los marcadores cuadren con las anotaciones, que no haya jugadas sin nombre o con espacios de más,
y que los récords de la tabla de la Nacional cuadren con sus juegos (contando los triunfos por default).
El reporte queda en build/data/validacion.md y en el resumen de cada corrida de GitHub Actions.
"""
import csv, io, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate as G

TIPOS = {'td carrera', 'td pase', 'td defensivo', 'td regreso', 'td', 'fg', 'safety'}
EXTRAS = {'', 'pat bueno', 'pat fallado', '2 pts bueno', '2 pts fallado'}


def rows(name, local):
    try:
        R = list(csv.reader(io.StringIO(G.fetch(name, local))))
    except Exception:
        return [], {}
    if not R:
        return [], {}
    H = [G.norm(h) for h in R[0]]
    return R[1:], {h: i for i, h in enumerate(H)}


def run(local=None):
    msgs = []
    v = lambda r, c, n: (r[c[n]] if n in c and c[n] < len(r) else '')
    # marcadores de 14 Grandes y Nacional
    score = {}
    for name in ('juegos', 'njuegos'):
        R, c = rows(name, local)
        wk = 'semana' if 'semana' in c else 'ronda'
        for r in R:
            if G.norm(v(r, c, 'estado')) != 'final':
                continue
            w = v(r, c, wk).strip().upper()
            a, h = v(r, c, 'visitante').strip().upper(), v(r, c, 'local').strip().upper()
            try:
                score[(w, a, h)] = (int(v(r, c, 'pts visitante')), int(v(r, c, 'pts local')))
            except ValueError:
                msgs.append(f'Marcador vacío o inválido en un juego marcado como Final: {w} {a} en {h}')
    # anotaciones
    R, c = rows('anotaciones', local)
    pts = {}
    for i, r in enumerate(R, start=2):
        w, a, h = v(r, c, 'semana').strip().upper(), v(r, c, 'visitante').strip().upper(), v(r, c, 'local').strip().upper()
        if not (w and a and h):
            continue
        t, k, x = v(r, c, 'equipo').strip().upper(), G.norm(v(r, c, 'tipo')), G.norm(v(r, c, 'extra'))
        j = v(r, c, 'jugador')
        if not j.strip():
            msgs.append(f'Fila {i} de Anotaciones: jugada sin jugador ({w} {a} en {h}, {k or "sin tipo"}).')
        elif j != ' '.join(j.split()):
            msgs.append(f'Fila {i} de Anotaciones: el nombre "{j}" tiene espacios de más (el sitio ya los limpia).')
        if k not in TIPOS:
            msgs.append(f'Fila {i} de Anotaciones: tipo de jugada desconocido "{v(r, c, "tipo")}".')
        if x not in EXTRAS:
            msgs.append(f'Fila {i} de Anotaciones: extra desconocido "{v(r, c, "extra")}".')
        if k == 'td carrera' and v(r, c, 'pase de').strip():
            msgs.append(f'Fila {i} de Anotaciones: dice TD carrera pero trae "Pase de" ({j.strip()}).')
        p = 6 if k.startswith('td') else 3 if k == 'fg' else 2 if k == 'safety' else 0
        p += (1 if x == 'pat bueno' else 2 if x == '2 pts bueno' else 0) if k.startswith('td') else 0
        d = pts.setdefault((w, a, h), {a: 0, h: 0})
        if t in d:
            d[t] += p
        else:
            msgs.append(f'Fila {i} de Anotaciones: el equipo "{t}" no juega en {a} en {h}.')
    for key, d in pts.items():
        s = score.get(key)
        if not s:
            continue
        w, a, h = key
        if (d[a], d[h]) != s and w in ('CF', 'SF', 'F'):
            msgs.append(f'Anotaciones de {w} {a} en {h} suman {d[a]}-{d[h]} pero el marcador es {s[0]}-{s[1]}.')
    # tabla de la Nacional contra sus juegos (+ triunfos por default)
    R, c = rows('ntabla', local)
    rec = {}
    for (w, a, h), (sa, sh) in score.items():
        if not w.isdigit():
            continue
        rec.setdefault(a, [0, 0]); rec.setdefault(h, [0, 0])
        rec[a][0 if sa > sh else 1] += 1
        rec[h][0 if sh > sa else 1] += 1
    for r in R:
        k = v(r, c, 'clave').strip().upper()
        if not k:
            continue
        try:
            gw, gl = int(v(r, c, 'g') or 0), int(v(r, c, 'p') or 0)
            dft = int(v(r, c, 'g por default') or 0)
        except ValueError:
            continue
        cw, cl = rec.get(k, [0, 0])
        if (gw, gl) != (cw + dft, cl):
            msgs.append(f'Nacional_Tabla: {k} tiene {gw}-{gl}, pero sus juegos dan {cw}-{cl} más {dft} por default.')
    out = '# Revisión de la hoja\n\n' + ('\n'.join(f'- {m}' for m in msgs) if msgs else 'Todo cuadra.') + '\n'
    fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'validacion.md')
    if not os.path.exists(fp) or open(fp, encoding='utf-8').read() != out:
        open(fp, 'w', encoding='utf-8').write(out)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write(out)
    print(f'revisión de la hoja: {len(msgs)} avisos')
    return msgs


if __name__ == '__main__':
    local = sys.argv[sys.argv.index('--local') + 1] if '--local' in sys.argv else None
    for m in run(local):
        print(' -', m)
