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
    'TIG': dict(h='#C9A646', hd='#1F4FC1', hm='#1F4FC1', j='#1F4FC1', s='#C9A646', ss='#FFFFFF', n='#FFFFFF', no='#C9A646', deco='logo'),
    'PUE': dict(h='#1F4FD8', hd='#FFFFFF', hm='#1F4FD8', j='#151515', s='#1F4FD8', ss='#151515', n='#1F4FD8', no='#FFFFFF', deco='horn'),
    # Aproximados (pendientes de foto)
    'PUM': dict(h='#C9A227', hd='#0B2A6F', hm='#0B2A6F', j='#0B2A6F', s='#0B2A6F', ss='#C9A227', n='#C9A227', no=None, deco='stripe'),
    'MTY': dict(BASE, deco='horn'),
    'GDL': dict(BASE, deco='horn'),
    'CEM': dict(BASE, deco='horn'),
    'CCM': dict(BASE, deco='horn'),
    'BUR': dict(h='#FFFFFF', hd='#7A1F3D', hm='#7A1F3D', j='#FFFFFF', s='#FFFFFF', ss='#7A1F3D', n='#7A1F3D', no=None, deco='stripe'),
    'AGU': dict(h='#FFFFFF', hd='#7A1F3D', hm='#7A1F3D', j='#7A1F3D', s='#7A1F3D', ss='#FFFFFF', n='#FFFFFF', no=None, deco='stripe'),
    'UDL': dict(h='#00704A', hd='#F47920', hm='#FFFFFF', j='#00704A', s='#00704A', ss='#F47920', n='#FFFFFF', no='#F47920', deco='stripe'),
    'UVM': dict(h='#C8102E', hd='#FFFFFF', hm='#9AA0A6', j='#C8102E', s='#C8102E', ss='#FFFFFF', n='#FFFFFF', no=None, deco='stripe'),
    'LAN': dict(h='#E35205', hd='#111111', hm='#111111', j='#E35205', s='#E35205', ss='#111111', n='#FFFFFF', no='#111111', deco='stripe'),
    'LAC': dict(h='#E35205', hd='#FFFFFF', hm='#9AA0A6', j='#FFFFFF', s='#FFFFFF', ss='#E35205', n='#E35205', no=None, deco='stripe'),
    'CET': dict(h='#F2B705', hd='#0A2A66', hm='#0A2A66', j='#0A2A66', s='#0A2A66', ss='#F2B705', n='#F2B705', no=None, deco='stripe'),
}
NAC = {"PAC": "#1B2A5C", "PSA": "#0B6B3A", "FRA": "#B3202A", "HAL": "#0E4C92", "BUH": "#7A1F3D", "TSA": "#1F4E9A", "PAN": "#D9581F", "LQR": "#B8901C",
       "TEC": "#A51C30", "ULM": "#3B7DBF", "UIW": "#C8102E", "ASU": "#9E1B32", "UAT": "#1F5FAE", "UCH": "#4B2E83", "ITS": "#0053A0", "UAC": "#1B3F8B",
       "UCJ": "#2E7D32", "UBC": "#00723F"}
NAC_NUM = {'UCH': '#F2B705', 'LQR': '#111111', 'PAN': '#111111'}

SKIN = ['#F2CBA8', '#E3B08A', '#CF9870', '#B57A52', '#9C6440']   # de tez clara a morena
HAIR = ['#2A1C14', '#3B2A1E', '#1E1712']


def uniform(liga, k):
    if liga == '14G' and k in UNI:
        return UNI[k]
    c = NAC.get(k, '#444444')
    return dict(h=c, hd='#FFFFFF', hm='#9AA0A6', j=c, s=c, ss='#FFFFFF', n=NAC_NUM.get(k, '#FFFFFF'), no=None, deco='stripe')


DIG = {'0': ['111', '101', '101', '101', '111'], '1': ['010', '110', '010', '010', '111'], '2': ['111', '001', '111', '100', '111'],
       '3': ['111', '001', '011', '001', '111'], '4': ['101', '101', '111', '001', '001'], '5': ['111', '100', '111', '001', '111'],
       '6': ['111', '100', '111', '101', '111'], '7': ['111', '001', '010', '010', '010'], '8': ['111', '101', '111', '101', '111'],
       '9': ['111', '101', '111', '001', '111']}

W, H = 32, 32
OUT = '#141414'


def shade(c, f):
    c = c.lstrip('#')
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    if f > 1:
        r, g, b = (min(255, int(x + (255 - x) * (f - 1))) for x in (r, g, b))
    else:
        r, g, b = (int(x * f) for x in (r, g, b))
    return '#%02X%02X%02X' % (r, g, b)


def svg(num, u, size=132, title='', seed=''):
    G = [[None] * W for _ in range(H)]

    def px(x, y, c):
        if 0 <= x < W and 0 <= y < H:
            G[y][x] = c

    def row(y, x0, x1, c):
        for x in range(x0, x1 + 1):
            px(x, y, c)

    hsh = zlib.crc32(seed.encode('utf-8'))
    skin = SKIN[hsh % len(SKIN)]
    hair = HAIR[(hsh >> 4) % len(HAIR)]
    sk2 = shade(skin, .86)

    # ---- hombros y jersey (filas 17-31)
    j, s = u['j'], u['s']
    widths = {17: (9, 22), 18: (6, 25), 19: (4, 27), 20: (3, 28)}
    for y in range(17, H):
        x0, x1 = widths.get(y, (2, 29))
        row(y, x0, x1, j)
    for y in range(17, 25):                    # hombreras/mangas
        x0, x1 = widths.get(y, (2, 29))
        for x in range(x0, x1 + 1):
            if x <= 8 or x >= 23:
                px(x, y, s)
    if u['ss'] and u['ss'] != s:               # franja de la manga
        for y in (22, 23):
            for x in list(range(2, 8)) + list(range(24, 30)):
                if G[y][x]:
                    px(x, y, u['ss'])
    for y in range(25, H):                     # costados un poco más oscuros
        for x in (2, 3, 28, 29):
            px(x, y, shade(j, .8))
    row(17, 12, 19, shade(j, .75)); row(18, 13, 18, shade(j, .75))   # cuello del jersey
    row(15, 13, 18, sk2); row(16, 13, 18, sk2); row(17, 14, 17, sk2)  # cuello

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
    elif deco == 'horn':                       # cuerno de borrego a los lados
        for (x, y) in [(8, 5), (8, 6), (8, 7), (9, 8), (10, 8), (10, 7), (9, 4), (10, 4)]:
            px(x, y, u['hd']); px(W - 1 - x, y, u['hd'])
        for y in range(1, 5):
            px(15, y, u['hd']); px(16, y, u['hd'])
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
    m = u['hm']                                # careta (solo la parte de abajo)
    for y in range(10, 16):
        px(10, y, m); px(21, y, m)
    row(12, 10, 21, m)
    row(14, 10, 21, m)
    px(15, 15, m); px(16, 15, m)

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
    return (f'<svg class="pxp" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{size}" height="{size}" '
            f'shape-rendering="crispEdges" role="img" aria-label="{title}">{t}{"".join(rects)}</svg>')
