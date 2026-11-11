"""Utilidades de pixel art original para Live Ink (El Jardín). Todo se pinta por código."""
import math, random
from PIL import Image, ImageDraw

def new(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))

def up(img, k=2):
    return img.resize((img.width * k, img.height * k), Image.NEAREST)

def px(img, x, y, c):
    if 0 <= x < img.width and 0 <= y < img.height:
        img.putpixel((int(x), int(y)), c if len(c) == 4 else (*c, 255))

def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))

def outline(img, color=(40, 30, 20, 255), diag=False):
    """Contorno de 1px alrededor de la silueta (estilo pixel art)."""
    w, h = img.size
    src = img.load()
    out = img.copy()
    o = out.load()
    nb = [(1,0),(-1,0),(0,1),(0,-1)] + ([(1,1),(1,-1),(-1,1),(-1,-1)] if diag else [])
    for y in range(h):
        for x in range(w):
            if src[x, y][3] < 128:
                for dx, dy in nb:
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] >= 128:
                        o[x, y] = color
                        break
    return out

def shade_blob(img, circles, ramp, light=(-0.6, -0.8), seed=0, dither=0.18):
    """Rellena la unión de círculos con un ramp de 4-5 tonos, luz desde arriba-izquierda."""
    rnd = random.Random(seed)
    w, h = img.size
    xs = [c[0] for c in circles]; ys = [c[1] for c in circles]
    cx = sum(xs)/len(xs); cy = sum(ys)/len(ys)
    R = max(math.hypot(c[0]-cx, c[1]-cy) + c[2] for c in circles)
    lx, ly = light
    for y in range(h):
        for x in range(w):
            inside = None
            for (ccx, ccy, r) in circles:
                d = math.hypot(x+0.5-ccx, y+0.5-ccy)
                if d <= r:
                    # luz local por círculo (aspecto de "grumos" de hojas)
                    nx = (x+0.5-ccx)/r; ny = (y+0.5-ccy)/r
                    loc = -(nx*lx + ny*ly)  # -1..1
                    if inside is None or loc > inside:
                        inside = loc if inside is None else max(inside, loc*0.7 + inside*0.3)
            if inside is None:
                continue
            g = -((x+0.5-cx)*lx + (y+0.5-cy)*ly)/R
            v = 0.55*inside + 0.45*g
            v += (rnd.random()-0.5)*dither*2
            t = (v + 1)/2
            idx = max(0, min(len(ramp)-1, int(t*len(ramp))))
            px(img, x, y, ramp[idx])

def ellipse_shadow(img, cx, cy, rx, ry, alpha=70):
    for y in range(img.height):
        for x in range(img.width):
            if ((x+0.5-cx)/rx)**2 + ((y+0.5-cy)/ry)**2 <= 1:
                if img.getpixel((x, y))[3] == 0:
                    img.putpixel((x, y), (30, 50, 10, alpha))

def periodic_noise(x, y, size, seed, octaves=((2,1.0),(4,0.5),(8,0.25))):
    """Ruido periódico (tilea sin costuras) construido con senos de periodo entero."""
    rnd = random.Random(seed)
    v = 0
    for (f, a) in octaves:
        for _ in range(2):
            fx = rnd.randint(-f, f); fy = rnd.randint(-f, f)
            if fx == 0 and fy == 0: fx = f
            ph = rnd.random()*math.tau
            v += a*math.sin(math.tau*(fx*x + fy*y)/size + ph)
    return v

def value_noise(size, seed, cells=(4, 8, 16), amps=(1.0, 0.55, 0.3)):
    """Ruido de valor tileable (retícula aleatoria envuelta + interpolación suave)."""
    rnd = random.Random(seed)
    out = [[0.0]*size for _ in range(size)]
    for c, a in zip(cells, amps):
        g = [[rnd.uniform(-1, 1) for _ in range(c)] for _ in range(c)]
        step = size / c
        for y in range(size):
            for x in range(size):
                fx = x / step; fy = y / step
                x0 = int(fx) % c; y0 = int(fy) % c
                x1 = (x0+1) % c; y1 = (y0+1) % c
                tx = fx - int(fx); ty = fy - int(fy)
                tx = tx*tx*(3-2*tx); ty = ty*ty*(3-2*ty)
                v = (g[y0][x0]*(1-tx)+g[y0][x1]*tx)*(1-ty) + (g[y1][x0]*(1-tx)+g[y1][x1]*tx)*ty
                out[y][x] += v*a*2
    return out
