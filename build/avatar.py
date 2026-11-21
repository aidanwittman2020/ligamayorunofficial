"""Muñequito pixeleado de jugador: uniforme con los colores del equipo y su número.

svg(numero, uniforme) -> <svg> en línea (no necesita archivos de imagen).
"""

# Uniforme genérico por equipo: j=jersey, n=número, h=casco, p=pantalón, t=franja/calcetas
UNI = {
    'TIG': dict(j='#0A2A66', n='#F2B705', h='#F2B705', p='#F2B705', t='#0A2A66'),
    'PUM': dict(j='#0B2A6F', n='#C9A227', h='#C9A227', p='#C9A227', t='#0B2A6F'),
    'MTY': dict(j='#0033A0', n='#FFFFFF', h='#0033A0', p='#FFFFFF', t='#0033A0'),
    'GDL': dict(j='#0033A0', n='#FFFFFF', h='#0033A0', p='#FFFFFF', t='#0033A0'),
    'PUE': dict(j='#0033A0', n='#FFFFFF', h='#0033A0', p='#FFFFFF', t='#0033A0'),
    'CEM': dict(j='#0033A0', n='#FFFFFF', h='#0033A0', p='#FFFFFF', t='#0033A0'),
    'CCM': dict(j='#0033A0', n='#FFFFFF', h='#0033A0', p='#FFFFFF', t='#0033A0'),
    'BUR': dict(j='#FFFFFF', n='#7A1F3D', h='#FFFFFF', p='#7A1F3D', t='#7A1F3D'),
    'AGU': dict(j='#7A1F3D', n='#FFFFFF', h='#FFFFFF', p='#FFFFFF', t='#7A1F3D'),
    'UDL': dict(j='#00704A', n='#FFFFFF', h='#00704A', p='#FFFFFF', t='#F47920'),
    'UVM': dict(j='#C8102E', n='#FFFFFF', h='#C8102E', p='#FFFFFF', t='#C8102E'),
    'LAN': dict(j='#E35205', n='#FFFFFF', h='#E35205', p='#FFFFFF', t='#111111'),
    'LAC': dict(j='#FFFFFF', n='#E35205', h='#E35205', p='#E35205', t='#E35205'),
    'CET': dict(j='#0A2A66', n='#F2B705', h='#F2B705', p='#FFFFFF', t='#F2B705'),
}
NAC = {"PAC": "#1B2A5C", "PSA": "#0B6B3A", "FRA": "#B3202A", "HAL": "#0E4C92", "BUH": "#7A1F3D", "TSA": "#1F4E9A", "PAN": "#D9581F", "LQR": "#B8901C",
       "TEC": "#A51C30", "ULM": "#3B7DBF", "UIW": "#C8102E", "ASU": "#9E1B32", "UAT": "#1F5FAE", "UCH": "#4B2E83", "ITS": "#0053A0", "UAC": "#1B3F8B",
       "UCJ": "#2E7D32", "UBC": "#00723F"}
NAC_NUM = {'UCH': '#F2B705', 'LQR': '#111111', 'PAN': '#111111'}


def uniform(liga, k):
    if liga == '14G' and k in UNI:
        return UNI[k]
    c = NAC.get(k, '#444444')
    n = NAC_NUM.get(k, '#FFFFFF')
    return dict(j=c, n=n, h=c, p='#FFFFFF', t=c)


# Números 3x5
DIG = {'0': ['111', '101', '101', '101', '111'], '1': ['010', '110', '010', '010', '111'], '2': ['111', '001', '111', '100', '111'],
       '3': ['111', '001', '011', '001', '111'], '4': ['101', '101', '111', '001', '001'], '5': ['111', '100', '111', '001', '111'],
       '6': ['111', '100', '111', '101', '111'], '7': ['111', '001', '010', '010', '010'], '8': ['111', '101', '111', '101', '111'],
       '9': ['111', '101', '111', '001', '111']}

# Busto 28 x 26 (del torso para arriba). O contorno, H casco, S franja/hombreras, V hueco de la careta, M careta, J jersey, A costado
BODY = [
    '..........OOOOOOOO..........',
    '........OOHHHHSSHHHHOO......',
    '.......OHHHHHHSSHHHHHHO.....',
    '......OHHHHHHHSSHHHHHHHO....',
    '......OHHHHHHHSSHHHHHHHO....',
    '......OHHHHHHHHHHHHHHHHO....',
    '......OHHHVVVVVVVVVVVVHO....',
    '......OHHMMMMMMMMMMMMMMO....',
    '......OHHVVMVVVVVVVVMVVO....',
    '......OHHMMMMMMMMMMMMMMO....',
    '.......OHOVVVMVVVVMVVVO.....',
    '........OOOOMMMMMMMMOO......',
    '...OOOOOOOOOOOOOOOOOOOOOOO..',
    '..OSSSSSSJJJJJJJJJJSSSSSSSO.',
    '.OSSSSSSSJJJJJJJJJJSSSSSSSSO',
    '.OAAJJJJJJJJJJJJJJJJJJJJJAAO',
    '.OAAJJJJJJJJJJJJJJJJJJJJJAAO',
    '.OAAJJJJJJJJJJJJJJJJJJJJJAAO',
    '.OAAJJJJJJJJJJJJJJJJJJJJJAAO',
    '.OAAJJJJJJJJJJJJJJJJJJJJJAAO',
    '.OAAJJJJJJJJJJJJJJJJJJJJJAAO',
    '.OAAJJJJJJJJJJJJJJJJJJJJJAAO',
    '.OAAJJJJJJJJJJJJJJJJJJJJJAAO',
    '.OAAJJJJJJJJJJJJJJJJJJJJJAAO',
    '.OAAJJJJJJJJJJJJJJJJJJJJJAAO',
    '.OAAJJJJJJJJJJJJJJJJJJJJJAAO',
]
NUM_X, NUM_W, NUM_Y, SCALE = 4, 21, 15, 2


def shade(h, f=0.78):
    h = h.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return '#%02X%02X%02X' % (int(r * f), int(g * f), int(b * f))


def svg(num, u, size=132, title=''):
    col = {'O': '#111111', 'H': u['h'], 'V': '#1B1B1B', 'M': '#9AA0A6', 'J': u['j'], 'S': u['t'], 'A': shade(u['j'])}
    W, H = len(BODY[0]), len(BODY)
    grid = [list(r) for r in BODY]
    rects = []
    for y, row in enumerate(grid):
        x = 0
        while x < W:
            ch = row[x]
            if ch == '.':
                x += 1
                continue
            x2 = x
            while x2 + 1 < W and row[x2 + 1] == ch:
                x2 += 1
            rects.append(f'<rect x="{x}" y="{y}" width="{x2 - x + 1}" height="1" fill="{col[ch]}"/>')
            x = x2 + 1
    # número en el pecho, al doble de tamaño
    st = '' if num is None else str(num)[-2:]
    if st:
        w = (len(st) * 3 + (len(st) - 1)) * SCALE
        x0 = NUM_X + (NUM_W - w) // 2
        for i, d in enumerate(st):
            for yy, bits in enumerate(DIG[d]):
                for xx, b in enumerate(bits):
                    if b == '1':
                        rects.append(f'<rect x="{x0 + (i * 4 + xx) * SCALE}" y="{NUM_Y + yy * SCALE}" width="{SCALE}" height="{SCALE}" fill="{u["n"]}"/>')
    t = f'<title>{title}</title>' if title else ''
    return (f'<svg class="pxp" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{size}" height="{round(size * H / W)}" '
            f'shape-rendering="crispEdges" role="img" aria-label="{title}">{t}{"".join(rects)}</svg>')
