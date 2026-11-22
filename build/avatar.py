"""Muñequito pixeleado de jugador (estilo videojuego retro, diseño propio del sitio).

Busto de frente: casco con careta, cara genérica, hombreras y jersey con el número.
svg(numero, uniforme, size, title, seed) -> <svg> en línea (no necesita archivos de imagen).
"""
import zlib

# Uniforme por equipo.
#   h=casco, hd=detalle del casco (franja/cuerno), hm=careta, j=jersey, s=hombros/mangas, ss=franja de la manga,
#   n=número, no=contorno del número, deco='horn' (cuerno de borrego), 'stripe' (franja al centro) o 'logo'
BASE = dict(h='#0033A0', hd='#FFFFFF', hm='#9AA0A6', j='#0033A0', s='#0033A0', ss='#FFFFFF', n='#FFFFFF', no=None, deco='stripe')
UNI = {
    # Fotos enviadas por Aidan (temporada 2026)
    'TIG': dict(h='#C9A646', hd='#1F4FC1', hm='#1F4FC1', j='#1F4FC1', s='#C9A646', ss='#FFFFFF', n='#FFFFFF', no='#C9A646', deco='logo', p='#C9A646', g='#FFFFFF'),
    'PUE': dict(h='#1F4FD8', hd='#FFFFFF', hm='#1F4FD8', j='#151515', s='#1F4FD8', ss='#151515', n='#1F4FD8', no='#FFFFFF', deco='horn', p='#151515', g='#1F4FD8'),
    'PUM': dict(h='#B8964A', hd='#1B2448', hm='#1B2448', j='#1B2448', s='#1B2448', ss='#B8964A', n='#C8A24A', no=None, deco='logo', p='#1B2448', g='#1B2448'),
    'AGU': dict(h='#C8202A', hd='#FFFFFF', hm='#FFFFFF', j='#C8202A', s='#C8202A', ss='#FFFFFF', n='#FFFFFF', no=None, deco='stripe', p='#C8202A', g='#151515', arm='#151515'),
    'BUR': dict(h='#F4F4F2', hd='#6B2235', hm='#F4F4F2', j='#F4F4F2', s='#F4F4F2', ss='#6B2235', n='#6B2235', no=None, deco='logo', p='#F4F4F2', g='#F4F4F2'),
    'GDL': dict(h='#F4F4F2', hd='#1F55C9', hm='#F4F4F2', j='#1F55C9', s='#1F55C9', ss='#F4F4F2', n='#FFFFFF', no=None, deco='horn', p='#1F55C9', g='#F4F4F2'),
    'LAN': dict(h='#E8502A', hd='#151515', hm='#151515', j='#151515', s='#151515', ss='#151515', n='#FFFFFF', no='#E8502A', deco='logo', p='#151515', g='#E8502A', visor=True),
    'CEM': dict(h='#F4F4F2', hd='#2A3BD6', hm='#2A3BD6', j='#F4F4F2', s='#F4F4F2', ss='#2A3BD6', n='#2A3BD6', no=None, deco='horn', p='#F4F4F2', g='#F4F4F2'),
    'CCM': dict(h='#B9C0C8', hd='#1F5BD6', hm='#F4F4F2', j='#1F5BD6', s='#1F5BD6', ss='#1F5BD6', n='#F4F4F2', no=None, deco='horn_only', p='#1F5BD6', g='#151515', visor=True, metal=True),
    'MTY': dict(h='#F4F4F2', hd='#1F55D0', hm='#1F55D0', j='#1F55D0', s='#1F55D0', ss='#1F55D0', n='#F4F4F2', no=None, deco='horn_only', p='#1F55D0', g='#151515', arm='#151515'),
    'UDL': dict(h='#1E6B45', hd='#F4F4F2', hm='#F4F4F2', j='#1E6B45', s='#1E6B45', ss='#1E6B45', n='#F4F4F2', no='#E85A2A', deco='logo', p='#1E6B45', g='#151515', arm='#151515'),
    'UVM': dict(h='#F4F4F2', hd='#D42A2A', hm='#F4F4F2', j='#D42A2A', s='#D42A2A', ss='#D42A2A', n='#F4F4F2', no=None, deco='stripe', p='#F4F4F2', g='#F4F4F2'),
    'LAC': dict(h='#D9601E', hd='#F4F4F2', hm='#151515', j='#F4F4F2', s='#F4F4F2', ss='#F4F4F2', n='#F05A28', no=None, deco='logo', p='#B8BBB9', g='#F4F4F2'),
    'CET': dict(h='#151515', hd='#D9A520', hm='#151515', j='#151515', s='#151515', ss='#151515', n='#F2C318', no=None, deco='logo', p='#151515', g='#151515'),
}
NAC = {"PAC": "#1B2A5C", "PSA": "#0B6B3A", "FRA": "#B3202A", "HAL": "#0E4C92", "BUH": "#7A1F3D", "TSA": "#1F4E9A", "PAN": "#D9581F", "LQR": "#B8901C",
       "TEC": "#A51C30", "ULM": "#3B7DBF", "UIW": "#C8102E", "ASU": "#9E1B32", "UAT": "#1F5FAE", "UCH": "#4B2E83", "ITS": "#0053A0", "UAC": "#1B3F8B",
       "UCJ": "#2E7D32", "UBC": "#00723F"}
NAC_NUM = {'UCH': '#F2B705', 'LQR': '#111111', 'PAN': '#111111'}

SKIN = ['#F2CBA8', '#E3B08A', '#CF9870', '#B57A52', '#9C6440']   # de tez clara a morena
HAIR = ['#2A1C14', '#3B2A1E', '#1E1712']
SKIN_DARK = '#6E4630'   # para los jugadores que Aidan indicó (ver SKIN_FIX en jugadores.py)


def uniform(liga, k):
    if liga == '14G' and k in UNI:
        return UNI[k]
    c = NAC.get(k, '#444444')
    return dict(h=c, hd='#FFFFFF', hm='#9AA0A6', j=c, s=c, ss='#FFFFFF', n=NAC_NUM.get(k, '#FFFFFF'), no=None, deco='stripe')


DIG = {'0': ['111', '101', '101', '101', '111'], '1': ['010', '110', '010', '010', '111'], '2': ['111', '001', '111', '100', '111'],
       '3': ['111', '001', '011', '001', '111'], '4': ['101', '101', '111', '001', '001'], '5': ['111', '100', '111', '001', '111'],
       '6': ['111', '100', '111', '101', '111'], '7': ['111', '001', '010', '010', '010'], '8': ['111', '101', '111', '101', '111'],
       '9': ['111', '101', '111', '001', '111']}

W, H = 32, 38
OUT = '#141414'


def shade(c, f):
    c = c.lstrip('#')
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    if f > 1:
        r, g, b = (min(255, int(x + (255 - x) * (f - 1))) for x in (r, g, b))
    else:
        r, g, b = (int(x * f) for x in (r, g, b))
    return '#%02X%02X%02X' % (r, g, b)


def svg(num, u, size=132, title='', seed='', pose=None, skin=None, build='mid'):
    G = [[None] * W for _ in range(H)]

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            G[y][x] = c

    def row(y, x0, x1, c):
        for x in range(x0, x1 + 1):
            px(x, y, c)

    hsh = zlib.crc32(seed.encode('utf-8'))
    skin = skin or SKIN[hsh % len(SKIN)]
    hair = HAIR[(hsh >> 4) % len(HAIR)]
    sk2 = shade(skin, .86)

    # ---- medio cuerpo según la complexión de la posición:
    #   'skill' (QB, receptores, defensivos de backfield, pateadores): más delgado, hombreras chicas
    #   'mid'   (corredores, linebackers, alas cerradas): complexión media
    #   'big'   (linieros ofensivos y defensivos): torso y hombreras anchos, brazos gruesos, cuello grueso
    sft = {'skill': 1, 'mid': 0, 'big': -1}.get(build, 0)
    L = lambda x: x + sft              # columnas del lado izquierdo
    R = lambda x: x - sft              # columnas del lado derecho
    j, sl = u['j'], u['s']
    pants, glove = u.get('p') or shade(j, .6), u.get('g') or '#1B1B1B'
    arm = u.get('arm') or skin
    for y in range(16, 33):                       # torso
        a0, a1 = (L(9), R(22)) if y == 16 else (L(8), R(23))
        row(y, a0, a1, j)
    for y in range(17, 33):                       # costados del torso un poco más oscuros
        px(L(8), y, shade(j, .82)); px(R(23), y, shade(j, .82))
    ext = 1 if build == 'big' else 0              # hombreras más grandes en linieros
    row(16, L(7), R(24), sl); row(17, L(5) - ext, R(26) + ext, sl); row(18, L(4) - ext, R(27) + ext, sl); row(19, L(4) - ext, R(27) + ext, sl)
    if build == 'big':
        row(20, L(4) - 1, L(7), sl); row(20, R(24), R(27) + 1, sl)
    for x in list(range(L(4), L(8))) + list(range(R(27), R(23), -1)):   # mangas
        for y in (20, 21):
            px(x, y, sl)
    if u['ss'] and u['ss'] != sl:                 # franja de la manga
        for x in list(range(L(4), L(8))) + list(range(R(27), R(23), -1)):
            px(x, 21, u['ss'])
    axl = [L(4), L(5), L(6)] + ([L(3)] if build == 'big' else [])
    axr = [R(25), R(26), R(27)] + ([R(28)] if build == 'big' else [])
    for y in range(22, 30):                       # brazos
        for x in axl + axr:
            px(x, y, arm)
        px(L(6), y, shade(arm, .85)); px(R(25), y, shade(arm, .85))
    for y in range(30, 33):                       # guantes
        row(y, L(3) - ext, L(6), glove); row(y, R(25), R(28) + ext, glove)
    row(33, L(8), R(23), '#1B1B1B')               # cinturón
    px(15, 33, '#C9C9C9'); px(16, 33, '#C9C9C9')
    for y in range(34, H):                        # pantalón
        row(y, L(8), R(23), pants)
        px(15, y, shade(pants, .8)); px(16, y, shade(pants, .8))
    row(16, 12, 19, shade(j, .7)); row(17, 13, 18, shade(j, .7))   # cuello del jersey
    row(15, 12 if build == 'big' else 13, 19 if build == 'big' else 18, sk2)   # cuello

    # ---- casco (filas 1-14)
    h = u['h']
    hel = {1: (11, 20), 2: (9, 22), 3: (8, 23), 4: (7, 24), 5: (7, 24), 6: (7, 24), 7: (7, 24), 8: (7, 24), 9: (7, 24),
           10: (7, 24), 11: (7, 24), 12: (8, 23), 13: (8, 23), 14: (9, 22), 15: (10, 21)}
    for y, (a, b) in hel.items():
        row(y, a, b, h)
    for y in range(3, 12):                     # sombra a los lados
        px(hel[y][0], y, shade(h, .78)); px(hel[y][1], y, shade(h, .78))
    px(12, 2, shade(h, 1.45)); row(3, 11, 12, shade(h, 1.45)); px(10, 4, shade(h, 1.3))   # brillo
    deco = u.get('deco')
    if deco == 'stripe':
        for y in range(1, 6):
            px(15, y, u['hd']); px(16, y, u['hd'])
    elif deco in ('horn', 'horn_only'):        # cuerno de borrego a los lados
        for (x, y) in [(8, 5), (8, 6), (8, 7), (9, 8), (10, 8), (10, 7), (9, 4), (10, 4), (11, 3), (12, 2), (11, 4)]:
            px(x, y, u['hd']); px(W - 1 - x, y, u['hd'])
        if deco == 'horn':
            for y in range(1, 5):
                px(15, y, u['hd']); px(16, y, u['hd'])
    if u.get('metal'):                         # brillo metálico
        row(2, 13, 18, shade(h, 1.35)); px(21, 4, shade(h, 1.5)); px(22, 5, shade(h, 1.5))
    elif deco == 'logo':                       # logo pequeño a los lados
        for (x, y) in [(8, 5), (9, 5), (8, 6), (9, 6), (9, 7)]:
            px(x, y, u['hd']); px(W - 1 - x, y, u['hd'])

    # ---- cara (dentro del casco)
    for y in range(6, 16):
        row(y, 11, 20, skin)
    row(6, 11, 20, shade(h, .7))               # borde del casco sobre la frente
    row(8, 12, 14, hair); row(8, 17, 19, hair)  # cejas
    px(12, 9, '#FFFFFF'); px(13, 9, '#1A1A1A'); px(18, 9, '#1A1A1A'); px(19, 9, '#FFFFFF')   # ojos
    px(15, 11, sk2); px(16, 11, sk2)           # nariz
    row(13, 14, 17, shade(skin, .62))          # boca
    px(11, 15, sk2); px(20, 15, sk2)
    if u.get('visor'):
        row(9, 11, 20, '#1E1E1E'); row(10, 11, 20, '#2B2B2B')
    m = u['hm']                                # careta: abierta (skill), con barra central (mid) o jaula (big)
    for y in range(10, 16):
        px(10, y, m); px(21, y, m)
    if build == 'big':
        row(11, 10, 21, m); row(13, 10, 21, m); row(15, 10, 21, m)
        for y in range(11, 16):
            px(13, y, m); px(18, y, m)
    elif build == 'skill':
        row(12, 10, 21, m)
        row(14, 10, 12, m); row(14, 19, 21, m)
    else:
        row(12, 10, 21, m)
        row(14, 10, 21, m)
        for y in range(12, 16):
            px(15, y, m); px(16, y, m)
    if build in ('skill', 'mid') and not u.get('visor'):   # pintura bajo los ojos
        px(12, 10, '#1A1A1A'); px(13, 10, '#1A1A1A'); px(18, 10, '#1A1A1A'); px(19, 10, '#1A1A1A')

    # ---- número con contorno (2x)
    st = '' if num is None else str(num)[-2:]
    if st:
        sc = 2
        w = (len(st) * 3 + (len(st) - 1)) * sc
        x0, y0 = (W - w) // 2, 21
        cells = set()
        for i, d in enumerate(st):
            for yy, bits in enumerate(DIG[d]):
                for xx, b in enumerate(bits):
                    if b == '1':
                        for a in range(sc):
                            for c in range(sc):
                                cells.add((x0 + (i * 4 + xx) * sc + a, y0 + yy * sc + c))
        if u.get('no'):
            for (x, y) in cells:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if (x + dx, y + dy) not in cells:
                        px(x + dx, y + dy, u['no'])
        for (x, y) in cells:
            px(x, y, u['n'])

    # ---- poses con balón (jugadores ofensivos)
    BALL = ['..BBBBB..', '.BBWBWBB.', 'BBBWWWBBB', '.BBBBBBB.', '..BBBBB..']
    BALLV = ['.BBB.', 'BBBBB', 'BWBBB', 'BWWBB', 'BWBBB', 'BBBBB', '.BBB.']   # balón parado (de punta)
    glove = u.get('g') or '#1B1B1B'

    def ball(x0, y0, shape=BALL):
        cells = {(x0 + xx, y0 + yy) for yy, r_ in enumerate(shape) for xx, ch in enumerate(r_) if ch != '.'}
        for (x, y) in cells:                   # contorno para que se vea sobre el jersey
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (x + dx, y + dy) not in cells:
                    px(x + dx, y + dy, OUT)
        for yy, r_ in enumerate(shape):
            for xx, ch in enumerate(r_):
                if ch == 'B':
                    px(x0 + xx, y0 + yy, '#8A4726' if yy < len(shape) // 2 + 1 else '#6B3519')
                elif ch == 'W':
                    px(x0 + xx, y0 + yy, '#F4F4F2')

    def clear_arm(side):                       # quita el brazo que cuelga (para doblarlo)
        xs = range(R(24), R(30) + 1) if side == 'r' else range(L(1), L(8))
        for y in range(22, 33):
            for x in xs:
                G[y][x] = None

    if pose in ('ball_r', 'ball_l'):           # balón en la mano, brazo abajo
        ball(R(21) if pose == 'ball_r' else L(2), 27)
        for x in (range(R(25), R(25) + 4) if pose == 'ball_r' else range(L(3), L(3) + 4)):
            for y in (30, 31, 32):
                px(x, y, glove)
    elif pose == 'ball_up':                    # balón en alto junto al casco (brazo derecho doblado)
        clear_arm('r')
        for y in range(10, 22):                # antebrazo hacia arriba
            for x in (R(26), R(26) + 1, R(26) + 2):
                px(x, y, arm)
            px(R(26), y, shade(arm, .85))
        for y in range(16, 22):                # manga
            for x in range(R(24), R(24) + 5):
                px(x, y, sl)
        ball(R(25), 2, BALLV)
        for y in (8, 9, 10):
            row(y, R(25), R(25) + 4, glove)
    elif pose == 'tuck':                       # balón pegado al pecho, bajo el brazo derecho
        clear_arm('r')
        for y in range(22, 27):                # brazo doblado sobre el pecho
            for x in range(R(24), R(24) + 4):
                px(x, y, arm)
        for y in range(22, 26):
            row(y, R(22), R(23), arm)
        ball(15, 23)
        for y in (25, 26, 27):
            row(y, R(21), R(25), glove)
    elif pose == 'two_hands':                  # balón con las dos manos, a la altura de la cintura
        clear_arm('r'); clear_arm('l')
        for y in range(22, 28):
            for x in (L(4), L(5), L(6), R(25), R(26), R(27)):
                px(x, y, arm)
        for y in range(26, 30):
            row(y, L(7), L(9), arm); row(y, R(22), R(24), arm)
        ball(11, 27)
        for y in (28, 29, 30):
            row(y, L(8), 11, glove); row(y, 20, R(23), glove)

    # ---- contorno exterior
    outline = [(x, y) for y in range(H) for x in range(W) if G[y][x] is None and any(
        0 <= x + dx < W and 0 <= y + dy < H and G[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for x, y in outline:
        G[y][x] = OUT

    rects = []
    for y in range(H):
        x = 0
        while x < W:
            c = G[y][x]
            if c is None:
                x += 1
                continue
            x2 = x
            while x2 + 1 < W and G[y][x2 + 1] == c:
                x2 += 1
            rects.append(f'<rect x="{x}" y="{y}" width="{x2 - x + 1}" height="1" fill="{c}"/>')
            x = x2 + 1
    t = f'<title>{title}</title>' if title else ''
    return (f'<svg class="pxp" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{size}" height="{round(size * H / W)}" '
            f'shape-rendering="crispEdges" role="img" aria-label="{title}">{t}{"".join(rects)}</svg>')
