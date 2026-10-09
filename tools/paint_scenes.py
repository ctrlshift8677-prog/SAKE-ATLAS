"""產生各縣的水墨風景（透明背景 webp），放在 static/scenes/。只需在新增場景時執行。"""
import math, random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1040, 600
OUT = Path(__file__).resolve().parent.parent / "static" / "scenes"
SUMI = (48, 62, 72)
PINK = (214, 140, 150)


def vnoise(n, scale, seed, octaves=4, persistence=0.5):
    """1D 分形雜訊，範圍約 -1..1。"""
    r = np.random.default_rng(seed)
    out = np.zeros(n)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        k = max(2, int(n / scale * 2 ** o))
        pts = r.uniform(-1, 1, k + 2)
        xs = np.linspace(0, k, n)
        out += amp * np.interp(xs, np.arange(k + 2), pts)
        tot += amp
        amp *= persistence
    return out / tot


def noise2d(seed, s=6):
    r = np.random.default_rng(seed)
    small = r.uniform(0, 1, (H // s + 2, W // s + 2))
    im = Image.fromarray((small * 255).astype(np.uint8)).resize((W + 2 * s, H + 2 * s), Image.BICUBIC)
    return np.asarray(im, dtype=float)[:H, :W] / 255


class Canvas:
    def __init__(self, seed):
        self.rgb = np.zeros((H, W, 3))
        self.a = np.zeros((H, W))
        self.seed = seed
        self.tex = 0.7 + 0.3 * noise2d(seed + 99, 5)
        self.fine = 0.8 + 0.2 * noise2d(seed + 77, 2)

    def ink(self, alpha, color=SUMI, texture=True):
        alpha = np.clip(alpha, 0, 1)
        if texture:
            alpha = alpha * self.tex * self.fine
        c = np.array(color, float)
        self.rgb = c * alpha[..., None] + self.rgb * (1 - alpha[..., None])
        self.a = alpha + self.a * (1 - alpha)

    def erase(self, amount):
        self.a *= 1 - np.clip(amount, 0, 1)

    def save(self, path):
        a = np.clip(self.a, 0, 1)
        a = 1 - (1 - a) ** 1.75          # 墨色加深，讓每一幅在字卡上看得出來
        rgb = np.where(a[..., None] > 0, self.rgb / np.maximum(a[..., None], 1e-6), 0)
        im = Image.fromarray(np.dstack([rgb, a * 255]).clip(0, 255).astype(np.uint8), "RGBA")
        im.save(path, "WEBP", quality=78, alpha_quality=60, method=6)


Y = np.arange(H)[:, None].astype(float)
X = np.arange(W)[None, :].astype(float)


def streaks(seed, scale=7):
    """垂直的乾筆紋理（皴）。"""
    return 0.72 + 0.28 * (vnoise(W, scale, seed, 3) * 0.5 + 0.5)[None, :]


def fill_below(c, ridge, alpha, fade, edge=1.5, edge_px=3, color=SUMI, snow=None, stop=None, seed=0):
    d = Y - ridge[None, :]
    body = np.where(d >= 0, np.exp(-d / fade), 0)
    rim = np.where((d >= 0) & (d < edge_px), (edge - 1) * (1 - d / edge_px), 0)
    aa = np.where((d < 0) & (d > -1.2), (1 + d / 1.2), 0)
    a = alpha * (body + rim + aa) * streaks(seed + 5)
    if stop is not None:
        a *= np.clip((stop - Y) / 40, 0, 1)
    if snow is not None:
        line, jag = snow
        sl = line + jag[None, :]
        cap = (Y < sl) & (d > edge_px * 0.6)
        a = np.where(cap, a * 0.08, a)
    c.ink(a, color)


def ridge_line(x0, y_base, amp, scale, seed, octaves=5, sharp=False):
    n = vnoise(W, scale, seed, octaves)
    if sharp:
        n = 1 - np.abs(vnoise(W, scale, seed, octaves)) * 2
    return y_base - amp * n


def mountains(c, y, amp, alpha, fade, seed, scale=260, sharp=False, snow=None, stop=None):
    ridge = ridge_line(0, y, amp, scale, seed, sharp=sharp)
    sn = None
    if snow:
        line, depth = snow
        sn = (np.maximum(ridge + depth * 0.4, line + 18 * vnoise(W, 18, seed + 3, 3)), np.zeros(W))
        sn = (0, np.minimum(ridge + depth * (0.6 + 0.4 * vnoise(W, 14, seed + 4, 3)), np.where(ridge < line, ridge + depth, ridge)))
    fill_below(c, ridge, alpha, fade, snow=sn, stop=stop, seed=seed)
    return ridge


def cone(c, cx, base, h, w, alpha, fade, seed, snow=0.0, skew=0.0, flat=0.04):
    t = np.clip(1 - np.abs(X[0] - cx) / w, 0, 1)
    t = np.where(X[0] < cx, t * (1 - skew) + t ** 2 * skew, t)
    prof = np.minimum(t ** 1.55, 1 - flat)
    ridge = base - h * prof + 2.5 * vnoise(W, 40, seed, 3)
    ridge = np.where(t > 0.002, ridge, base + 4000)
    sn = None
    if snow:
        jag = 14 * vnoise(W, 10, seed + 2, 3) + 26 * np.abs(np.sin(X[0] / 23 + seed)) ** 6
        sn = (0, base - h * (1 - snow) + jag)
    d = Y - ridge[None, :]
    body = np.where(d >= 0, np.exp(-d / fade), 0)
    rim = np.where((d >= 0) & (d < 3), 0.6 * (1 - d / 3), 0)
    aa = np.where((d < 0) & (d > -1.2), (1 + d / 1.2), 0)
    a = alpha * (body + rim + aa) * streaks(seed + 9, 5)
    a *= np.clip((base + 6 - Y) / (h * 0.45), 0, 1) ** 1.2          # 山腳淡入雲霧
    if sn is not None:
        fingers = 34 * np.maximum(0, np.sin(X[0] / 15 + seed)) ** 8 + 18 * np.maximum(0, np.sin(X[0] / 7 + seed * 2)) ** 10
        line = sn[1] + fingers
        cap = (Y < line[None, :]) & (d > 2.5)
        soft = np.clip((line[None, :] - Y) / 4, 0, 1)
        a = np.where(cap, a * (1 - 0.94 * soft), a)
    c.ink(a)
    return cx, base - h * (1 - flat)


def mist(c, y, thick, strength=0.9):
    m = np.exp(-((Y - y) / thick) ** 2)
    c.erase(strength * m * (0.6 + 0.4 * c.tex))


def sea(c, horizon, alpha, seed, density=1.0, bottom=None):
    r = random.Random(seed)
    lay = Image.new("L", (W * 2, H * 2), 0)
    d = ImageDraw.Draw(lay)
    bottom = bottom or H
    rows = int(16 * density)
    for k in range(rows):
        t = (k + 1) / rows
        yy = horizon + (bottom - horizon) * t ** 1.8
        for _ in range(int(2 + 6 * t * density)):
            x = r.uniform(-60, W)
            ln = r.uniform(40, 150) * (0.35 + t)
            amp = 0.6 + 1.4 * t
            ph = r.random() * 6
            pts = [(2 * (x + i * ln / 12), 2 * (yy + amp * math.sin(i / 12 * math.pi + ph))) for i in range(13)]
            d.line(pts, fill=int(255 * min(1, alpha * (0.35 + 0.8 * t))), width=max(2, int(2 + 2 * t)))
    a = np.asarray(lay.resize((W, H), Image.LANCZOS), float) / 255
    c.ink(a)
    c.ink(np.exp(-((Y - horizon) / 1.4) ** 2) * alpha * 0.55)


def islands(c, horizon, seed, count=5, big=60, alpha=0.5, pines=True):
    r = random.Random(seed)
    for i in range(count):
        cx = r.uniform(0.08, 0.92) * W
        w = r.uniform(0.3, 1) * big * 1.7
        h = w * r.uniform(0.22, 0.4)
        t = np.clip(1 - ((X[0] - cx) / w) ** 2, 0, 1)
        top = horizon - h * t ** 0.7 * (1 + 0.22 * vnoise(W, 22, seed + i, 4))
        top = np.where(t > 0.01, top, horizon + 4000)
        dd = Y - top[None, :]
        a = np.where(dd >= 0, np.exp(-dd / (h * 0.55 + 4)), 0) * np.where(Y <= horizon + 1, 1, 0)
        a = a + np.where((dd < 0) & (dd > -1.2), 1 + dd / 1.2, 0)
        c.ink(alpha * r.uniform(0.75, 1) * a * streaks(seed + i, 6))
        refl = np.where((Y > horizon + 3) & (Y < horizon + h * 0.6) & (t[None, :] > 0.15), 0.1 * alpha, 0) * (np.sin(Y * 1.1) > 0.4)
        c.ink(refl)
        if pines and w > 40:
            for _ in range(r.randint(1, 3)):
                px = cx + r.uniform(-w * 0.4, w * 0.4)
                py = float(top[int(min(W - 1, max(0, px)))])
                tree_blob(c, px, py, r.uniform(9, 16), alpha * 0.9)


def tree_blob(c, x, y, h, alpha):
    """一株遠景杉樹：細長、邊緣柔和的墨點。"""
    rx, ry = h * 0.2, h * 0.55
    m = np.exp(-(((X - x) / rx) ** 2 + ((Y - (y - ry)) / ry) ** 2) * 1.6)
    taper = np.clip(1 - np.maximum(0, (y - ry) - Y) / ry * 0.55, 0, 1)
    c.ink(alpha * m * taper)


def cedar(lay, x, base, h, alpha, seed):
    """一株杉：尖頂、往下漸寬、邊緣略帶毛邊。"""
    top = base - h
    y0, y1 = int(max(0, top)), int(min(H, base + 4))
    x0, x1 = int(max(0, x - h * 0.3)), int(min(W, x + h * 0.3))
    if y1 <= y0 or x1 <= x0:
        return
    yy = np.arange(y0, y1)[:, None].astype(float)
    xx = np.arange(x0, x1)[None, :].astype(float)
    t = np.clip((yy - top) / h, 0, 1)
    jit = 1 + 0.18 * np.sin(yy * 1.7 + seed) * np.sin(yy * 0.37 + seed * 3)
    half = h * 0.15 * t ** 0.72 * jit
    m = np.clip((half - np.abs(xx - x)) / 1.1 + 0.5, 0, 1)
    m *= alpha * (1 - 0.3 * t)
    trunk = np.where((np.abs(xx - x) < 0.8) & (yy > base - h * 0.08), alpha * 0.8, 0)
    region = lay[y0:y1, x0:x1]
    lay[y0:y1, x0:x1] = region + (1 - region) * np.maximum(m, trunk)


def trees(c, base_y, x0, x1, seed, count=40, hmin=14, hmax=34, alpha=0.55):
    r = random.Random(seed)
    lay = np.zeros((H, W))
    specs = sorted(((r.uniform(x0, x1) * W, r.uniform(hmin, hmax)) for _ in range(count)), key=lambda p: p[1])
    for x, h in specs:
        base = base_y + r.uniform(-4, 8) + (h - hmin) * 0.3
        cedar(lay, x, base, h, alpha * r.uniform(0.6, 1), r.random() * 10)
    c.ink(np.clip(lay, 0, 0.9) * streaks(seed, 4))
    foot = base_y + (hmax - hmin) * 0.3 + 6
    band = np.clip((Y - foot) / 22, 0, 1) * np.clip((foot + 70 - Y) / 30, 0, 1)
    xw = np.clip((X - (x0 * W - 30)) / 60, 0, 1) * np.clip(((x1 * W + 30) - X) / 60, 0, 1)
    c.erase(band * xw * 0.85)


def reeds(c, x0, x1, base, seed, count=60, alpha=0.45):
    r = random.Random(seed)
    lay = Image.new("L", (W * 2, H * 2), 0)
    d = ImageDraw.Draw(lay)
    for _ in range(count):
        x = r.uniform(x0, x1) * W
        h = r.uniform(40, 120)
        lean = r.uniform(-0.35, 0.25)
        pts = [(2 * (x + lean * h * (i / 8) ** 1.6), 2 * (base - h * i / 8)) for i in range(9)]
        d.line(pts, fill=int(255 * alpha * r.uniform(0.5, 1)), width=2)
        if r.random() < 0.5:
            tx, ty = pts[-1]
            d.line([(tx, ty), (tx + 2 * r.uniform(8, 18), ty + 2 * r.uniform(4, 10))], fill=int(255 * alpha * 0.8), width=2)
    c.ink(np.asarray(lay.resize((W, H), Image.LANCZOS), float) / 255)


def lake(c, top, bottom, seed, alpha=0.18):
    c.erase(np.where((Y > top) & (Y < bottom), 0.92, 0))
    r = random.Random(seed)
    lay = Image.new("L", (W * 2, H * 2), 0)
    d = ImageDraw.Draw(lay)
    for k in range(10):
        t = (k + 1) / 10
        yy = top + (bottom - top) * t ** 1.5
        x = r.uniform(0, W * 0.5)
        d.line([(2 * x, 2 * yy), (2 * (x + r.uniform(W * 0.15, W * 0.5)), 2 * yy)], fill=int(255 * alpha * (0.5 + t)), width=2)
    c.ink(np.asarray(lay.resize((W, H), Image.LANCZOS), float) / 255)


def river(c, top, seed, width_far=6, width_near=150, alpha=0.3, cx=0.5):
    r = random.Random(seed)
    ph = r.uniform(0, 6)
    tt = np.clip((Y - top) / (H - top), 0, 1)
    center = W * cx + 150 * np.sin(tt * 3.0 + ph) * tt ** 0.8 + 50 * np.sin(tt * 6.5 + ph * 2) * tt
    half = (width_far + (width_near - width_far) * tt ** 1.7) / 2
    dist = np.abs(X - center) - half
    soft = 6 + 30 * tt
    water = np.clip(1 - dist / soft, 0, 1) * (Y > top)
    bank = np.where((Y > top) & (dist > 0), np.exp(-dist / (25 + 70 * tt)), 0) * alpha * (0.3 + 0.9 * tt)
    c.ink(bank * streaks(seed + 3, 9))
    c.erase(water * 0.92)
    lay = Image.new("L", (W * 2, H * 2), 0)
    d = ImageDraw.Draw(lay)
    for _ in range(22):
        t = r.uniform(0.2, 1)
        yy = top + (H - top) * t
        cxx = W * cx + 150 * math.sin(t * 3.0 + ph) * t ** 0.8 + 50 * math.sin(t * 6.5 + ph * 2) * t
        hw = (width_far + (width_near - width_far) * t ** 1.7) / 2
        x = cxx + r.uniform(-hw * 0.7, hw * 0.3)
        d.line([(2 * x, 2 * yy), (2 * (x + hw * r.uniform(0.2, 0.5)), 2 * yy)], fill=int(255 * 0.16), width=2)
    c.ink(np.asarray(lay.resize((W, H), Image.LANCZOS), float) / 255)


def smoke(c, x, y, seed, drift=1.0, alpha=0.16, length=260):
    r = random.Random(seed)
    lay = np.zeros((H, W))
    for i in range(40):
        t = i / 39
        px = x + drift * length * t ** 1.5 + r.uniform(-6, 6)
        py = y - length * 0.6 * t + r.uniform(-5, 5)
        rad = 6 + 55 * t
        lay += np.exp(-(((X - px) ** 2 + (Y - py) ** 2) / (2 * rad ** 2))) * alpha * (1 - t * 0.75)
    c.ink(np.clip(lay, 0, 0.3) * (0.7 + 0.3 * c.tex))


def snowfall(c, seed, n=180, alpha=0.26):
    r = random.Random(seed)
    lay = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(lay)
    for _ in range(n):
        x, y = r.uniform(0, W), r.uniform(H * 0.1, H * 0.9)
        rad = r.uniform(1.0, 2.6)
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=int(255 * alpha * r.uniform(0.4, 1)))
    c.ink(np.asarray(lay.filter(ImageFilter.GaussianBlur(0.9)), float) / 255, texture=False)


def waterfall(c, cx, top, bottom, seed, width=24, alpha=0.5, span=300):
    """斷崖與瀑布：崖頂參差，岩面有垂直皴紋，瀑布是留白，底部起霧。回傳崖頂曲線。"""
    ridge = top + 16 * vnoise(W, 50, seed, 4) + 0.0004 * (X[0] - cx) ** 2
    d = Y - ridge[None, :]
    side = np.exp(-((X - cx) / span) ** 4)
    rock = np.where(d >= 0, np.exp(-d / 260) * 0.9 + 0.1, 0) * side
    rock *= np.clip((bottom - Y) / 70, 0, 1)
    vt = 0.55 + 0.45 * (np.abs(vnoise(W, 3, seed + 4, 2)) ** 0.6)[None, :]
    c.ink(alpha * rock * vt * streaks(seed + 2, 6))
    fall_edge = width / 2 + 2 * vnoise(H, 20, seed + 5, 3)[:, None]
    fall = np.clip((fall_edge - np.abs(X - cx)) / 2.5, 0, 1) * (Y > ridge[None, :] - 2)
    c.erase(fall * 0.94)
    lay = Image.new("L", (W * 2, H * 2), 0)
    dr = ImageDraw.Draw(lay)
    r = random.Random(seed)
    for _ in range(10):
        x = cx + r.uniform(-width / 2 + 3, width / 2 - 3)
        dr.line([(2 * x, 2 * (float(ridge[int(cx)]) + 8)), (2 * (x + r.uniform(-1.5, 1.5)), 2 * (bottom - 20))], fill=int(255 * 0.12), width=2)
    c.ink(np.asarray(lay.resize((W, H), Image.LANCZOS), float) / 255)
    c.erase(np.exp(-(((X - cx) / 160) ** 2 + ((Y - bottom + 20) / 50) ** 2)) * 0.95)
    return ridge


def rocks(c, horizon, seed, count=4, alpha=0.5):
    """海中礁岩：尖頂、帶垂直節理，下緣隱入浪花。"""
    r = random.Random(seed)
    for i in range(count):
        cx = r.uniform(0.15, 0.95) * W
        w = r.uniform(30, 90)
        h = w * r.uniform(1.0, 2.0)
        t = np.clip(1 - np.abs(X[0] - cx) / w, 0, 1)
        prof = t ** 0.55 * (1 + 0.18 * vnoise(W, 8, seed + i, 3))
        top = np.where(t > 0, horizon + 40 + i * 6 - h * prof, horizon + 4000)
        dd = Y - top[None, :]
        base = horizon + 40 + i * 6 + r.uniform(20, 40)
        body = np.where(dd >= 0, np.exp(-dd / (h * 0.8)) + 0.15, 0) * np.clip((base - Y) / 24, 0, 1)
        joints = 0.6 + 0.4 * np.abs(np.sin(X / 5 + seed + i)) ** 0.5
        c.ink(alpha * r.uniform(0.7, 1) * body * joints * streaks(seed + i, 3))


def cliff(c, x_edge, top, bottom, seed, side=1, alpha=0.5):
    """海邊柱狀岩壁（例如東尋坊）：側邊參差、帶垂直節理。"""
    edge = x_edge + 26 * vnoise(H, 40, seed, 4)[:, None] + np.clip((Y - top) / (bottom - top), 0, 1) * -40 * side
    dist = (X - edge) * side
    win = np.clip((Y - top) / 18, 0, 1) * np.clip((bottom - Y) / 60, 0, 1)
    top_edge = top + 10 * vnoise(W, 30, seed + 1, 3)[None, :]
    body = np.where((dist > 0) & (Y > top_edge), np.exp(-dist / 90) * 0.9 + 0.25, 0)
    joints = 0.55 + 0.45 * (np.abs(np.sin(X / 7 + seed)) ** 0.4)
    c.ink(alpha * body * win * joints * streaks(seed + 2, 4))


# ───────── 地標（細小、遠景的墨色剪影） ─────────
VERMILION = (186, 66, 44)
GOLD = (176, 142, 72)


def _layer():
    lay = Image.new("L", (W * 2, H * 2), 0)
    return lay, ImageDraw.Draw(lay)


def _ink_layer(c, lay, color=SUMI, blur=0.5):
    a = np.asarray(lay.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(blur)), float) / 255
    c.ink(a, color, texture=False)


def _roof(d, cx, y, w, h, a, lift=0.35):
    """反翹的屋簷：中間平、兩端微微上揚。"""
    pts = [(2 * (cx - w / 2), 2 * (y - h * lift)), (2 * (cx - w * 0.36), 2 * y), (2 * (cx + w * 0.36), 2 * y),
           (2 * (cx + w / 2), 2 * (y - h * lift)), (2 * (cx + w * 0.18), 2 * (y - h)), (2 * (cx - w * 0.18), 2 * (y - h))]
    d.polygon(pts, fill=a)


def castle(c, cx, base, s=1.0, alpha=0.62, wall=0.14, tiers=4, wings=False, shachi=False):
    """天守：石垣、白壁（wall 越小越白）、深色反翹屋簷。"""
    lay, d = _layer()
    a = int(255 * alpha)
    d.polygon([(2 * (cx - 66 * s), 2 * base), (2 * (cx + 66 * s), 2 * base), (2 * (cx + 50 * s), 2 * (base - 30 * s)), (2 * (cx - 50 * s), 2 * (base - 30 * s))], fill=int(a * 0.42))
    y = base - 30 * s
    sizes = [(104, 15), (84, 13), (66, 12), (50, 11), (38, 10)][:tiers]
    for k, (ww, hh) in enumerate(sizes):
        wall_w = ww * 0.68 * s
        d.rectangle([2 * (cx - wall_w / 2), 2 * (y - 15 * s), 2 * (cx + wall_w / 2), 2 * y], fill=int(a * wall))
        for wx in np.linspace(-wall_w * 0.3, wall_w * 0.3, 3):
            d.rectangle([2 * (cx + wx - 1.5 * s), 2 * (y - 10 * s), 2 * (cx + wx + 1.5 * s), 2 * (y - 6 * s)], fill=int(a * 0.7))
        y -= 15 * s
        _roof(d, cx, y, ww * s, hh * s, a, 0.42)
        if k == 1:
            _roof(d, cx, y - hh * s * 0.35, ww * s * 0.38, hh * s * 0.9, a, 0.3)   # 千鳥破風
        y -= hh * s * 0.72
    if wings:
        for side in (-1, 1):
            wx = cx + side * 95 * s
            d.rectangle([2 * (wx - 20 * s), 2 * (base - 52 * s), 2 * (wx + 20 * s), 2 * (base - 30 * s)], fill=int(a * wall))
            _roof(d, wx, base - 52 * s, 50 * s, 11 * s, a, 0.4)
            d.rectangle([2 * (wx - 28 * s), 2 * (base - 30 * s), 2 * (wx + 28 * s), 2 * base], fill=int(a * 0.36))
    _ink_layer(c, lay, SUMI, 0.6)
    if shachi:
        lay2, d2 = _layer()
        for side in (-1, 1):
            x = cx + side * 8 * s
            d2.polygon([(2 * x, 2 * (y + 2)), (2 * (x + side * 4 * s), 2 * (y - 8 * s)), (2 * (x + side * 1 * s), 2 * (y + 2))], fill=240)
        _ink_layer(c, lay2, GOLD, 0.3)


def pagoda(c, cx, base, s=1.0, alpha=0.6, color=SUMI):
    lay, d = _layer()
    a = int(255 * alpha)
    y = base
    for k in range(5):
        ww = (64 - k * 8) * s
        d.rectangle([2 * (cx - ww * 0.28), 2 * (y - 13 * s), 2 * (cx + ww * 0.28), 2 * y], fill=int(a * 0.7))
        y -= 13 * s
        _roof(d, cx, y, ww, 9 * s, a, 0.5)
        y -= 6 * s
    d.line([(2 * cx, 2 * y), (2 * cx, 2 * (y - 34 * s))], fill=a, width=max(2, int(3 * s)))
    for k in range(6):
        yy = y - 6 * s - k * 4.5 * s
        d.line([(2 * (cx - 4 * s), 2 * yy), (2 * (cx + 4 * s), 2 * yy)], fill=a, width=2)
    _ink_layer(c, lay, color)


def torii(c, cx, base, s=1.0, color=VERMILION, alpha=0.85, reflect=True):
    lay, d = _layer()
    a = int(255 * alpha)
    w, h = 120 * s, 120 * s
    for side in (-1, 1):
        x = cx + side * w * 0.33
        d.polygon([(2 * (x - 4 * s), 2 * base), (2 * (x + 4 * s), 2 * base), (2 * (x + 3 * s), 2 * (base - h)), (2 * (x - 3 * s), 2 * (base - h))], fill=a)
    d.rectangle([2 * (cx - w * 0.42), 2 * (base - h * 0.78), 2 * (cx + w * 0.42), 2 * (base - h * 0.72)], fill=a)
    pts = [(2 * (cx - w * 0.62), 2 * (base - h * 1.04)), (2 * (cx - w * 0.5), 2 * (base - h * 0.97)), (2 * (cx + w * 0.5), 2 * (base - h * 0.97)),
           (2 * (cx + w * 0.62), 2 * (base - h * 1.04)), (2 * (cx + w * 0.5), 2 * (base - h * 0.9)), (2 * (cx - w * 0.5), 2 * (base - h * 0.9))]
    d.polygon(pts, fill=a)
    _ink_layer(c, lay, color, 0.4)
    if reflect:
        ref = lay.transpose(Image.FLIP_TOP_BOTTOM)
        off = int(2 * (2 * base - H))
        canvas = Image.new("L", (W * 2, H * 2), 0)
        canvas.paste(ref, (0, off))
        arr = np.asarray(canvas.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2.2)), float) / 255
        arr *= (np.sin(Y * 0.9) > -0.2) * 0.35 * np.clip((base + h * 0.9 - Y) / (h * 0.9), 0, 1)
        c.ink(arr, color, texture=False)


def lighthouse(c, cx, base, s=1.0, alpha=0.55):
    lay, d = _layer()
    a = int(255 * alpha)
    h = 110 * s
    d.polygon([(2 * (cx - 13 * s), 2 * base), (2 * (cx + 13 * s), 2 * base), (2 * (cx + 8 * s), 2 * (base - h)), (2 * (cx - 8 * s), 2 * (base - h))], fill=int(a * 0.35))
    d.line([(2 * (cx - 13 * s), 2 * base), (2 * (cx - 8 * s), 2 * (base - h))], fill=a, width=3)
    d.line([(2 * (cx + 13 * s), 2 * base), (2 * (cx + 8 * s), 2 * (base - h))], fill=a, width=3)
    d.rectangle([2 * (cx - 11 * s), 2 * (base - h - 4 * s), 2 * (cx + 11 * s), 2 * (base - h)], fill=a)
    d.rectangle([2 * (cx - 7 * s), 2 * (base - h - 18 * s), 2 * (cx + 7 * s), 2 * (base - h - 4 * s)], fill=int(a * 0.5))
    d.polygon([(2 * (cx - 10 * s), 2 * (base - h - 18 * s)), (2 * (cx + 10 * s), 2 * (base - h - 18 * s)), (2 * cx, 2 * (base - h - 30 * s))], fill=a)
    _ink_layer(c, lay)


def arch_bridge(c, x0, x1, deck, n=5, rise=34, alpha=0.6):
    lay, d = _layer()
    a = int(255 * alpha)
    span = (x1 - x0) / n
    for k in range(n):
        xa, xb = x0 + k * span, x0 + (k + 1) * span
        pts = [(2 * (xa + (xb - xa) * t), 2 * (deck - rise * math.sin(math.pi * t))) for t in np.linspace(0, 1, 30)]
        d.line(pts, fill=a, width=6)
        d.line([(p[0], p[1] + 12) for p in pts], fill=int(a * 0.5), width=3)
        for t in np.linspace(0.1, 0.9, 7):
            x = xa + (xb - xa) * t
            y = deck - rise * math.sin(math.pi * t)
            d.line([(2 * x, 2 * y), (2 * x, 2 * (y + 8))], fill=int(a * 0.6), width=2)
        if k < n:
            d.polygon([(2 * (xb - 9), 2 * (deck + 26)), (2 * (xb + 9), 2 * (deck + 26)), (2 * (xb + 5), 2 * deck), (2 * (xb - 5), 2 * deck)], fill=int(a * 0.75))
    _ink_layer(c, lay)


def shimenawa(c, x0, y0, x1, y1, sag=22, alpha=0.6):
    lay, d = _layer()
    pts = [(2 * (x0 + (x1 - x0) * t), 2 * (y0 + (y1 - y0) * t + sag * math.sin(math.pi * t))) for t in np.linspace(0, 1, 40)]
    d.line(pts, fill=int(255 * alpha), width=7)
    for t in np.linspace(0.15, 0.85, 6):
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + sag * math.sin(math.pi * t)
        d.line([(2 * x, 2 * y), (2 * x, 2 * (y + 14))], fill=int(255 * alpha * 0.7), width=2)
    _ink_layer(c, lay)


def nori_poles(c, horizon, seed, alpha=0.5):
    r = random.Random(seed)
    lay, d = _layer()
    for row in range(9):
        t = (row + 1) / 9
        y = horizon + 10 + (H - horizon - 20) * t ** 1.6
        h = 8 + 60 * t
        gap = 10 + 46 * t
        x = r.uniform(-gap, 0)
        while x < W:
            d.line([(2 * x, 2 * (y - h)), (2 * (x + r.uniform(-1, 1)), 2 * y)], fill=int(255 * alpha * (0.4 + 0.6 * t)), width=max(2, int(1 + 3 * t)))
            x += gap * r.uniform(0.8, 1.2)
    _ink_layer(c, lay)


def plum_branch(c, seed, alpha=0.75):
    r = random.Random(seed)
    lay, d = _layer()
    blossoms_pts = []
    def grow(x, y, ang, length, width, depth):
        steps = 4
        for _ in range(steps):
            ang += r.uniform(-0.45, 0.45)
            nx, ny = x + math.cos(ang) * length / steps, y + math.sin(ang) * length / steps
            d.line([(2 * x, 2 * y), (2 * nx, 2 * ny)], fill=int(255 * alpha), width=max(2, int(width)))
            if depth > 0 and r.random() < 0.55:
                grow(nx, ny, ang + r.choice((-1, 1)) * r.uniform(0.5, 1.0), length * 0.55, width * 0.6, depth - 1)
            if width < 6:
                blossoms_pts.append((nx, ny))
            x, y = nx, ny
            width *= 0.85
    grow(W * 1.02, H * 0.18, math.pi * 0.92, 520, 16, 3)
    _ink_layer(c, lay, SUMI, 0.6)
    lay2, d2 = _layer()
    for (x, y) in blossoms_pts:
        for _ in range(r.randint(1, 3)):
            bx, by = x + r.uniform(-10, 10), y + r.uniform(-8, 8)
            rad = r.uniform(3.5, 6.5)
            d2.ellipse([2 * (bx - rad), 2 * (by - rad), 2 * (bx + rad), 2 * (by + rad)], fill=int(255 * r.uniform(0.45, 0.8)))
    _ink_layer(c, lay2, PINK, 0.8)


def gassho(c, base, xs, s=1.0, alpha=0.5, snow=True):
    """合掌造：陡峭的茅草屋頂（垂直草紋），白牆，屋脊帶雪。"""
    lay, d = _layer()
    a = int(255 * alpha)
    for x in xs:
        w, h = 86 * s, 92 * s
        d.polygon([(2 * (x - w / 2), 2 * (base - h * 0.28)), (2 * x, 2 * (base - h)), (2 * (x + w / 2), 2 * (base - h * 0.28))], fill=a)
        d.rectangle([2 * (x - w * 0.4), 2 * (base - h * 0.28), 2 * (x + w * 0.4), 2 * base], fill=int(a * 0.22))
        d.rectangle([2 * (x - w * 0.4), 2 * (base - h * 0.06), 2 * (x + w * 0.4), 2 * base], fill=int(a * 0.5))
    thatch = Image.new("L", (W * 2, H * 2), 0)
    _ink_layer(c, lay, SUMI, 0.9)
    # 茅草紋理：讓屋頂有垂直的草束
    c.a *= 1 - 0.25 * (np.abs(np.sin(X / 2.3)) > 0.82) * (Y < base) * (Y > base - 92 * s)
    if snow:
        lay2, d2 = _layer()
        for x in xs:
            w, h = 86 * s, 92 * s
            d2.polygon([(2 * (x - w * 0.16), 2 * (base - h * 0.8)), (2 * x, 2 * (base - h * 1.01)), (2 * (x + w * 0.16), 2 * (base - h * 0.8))], fill=255)
        c.a *= 1 - 0.8 * np.asarray(lay2.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.5)), float) / 255


def spit(c, x0, x1, y, h, alpha, seed):
    """沙嘴上的松林帶（三保松原）：低矮、深色、柔和。"""
    t = np.clip((X[0] - x0) / (x1 - x0), 0, 1)
    prof = np.sin(np.pi * t) ** 0.6
    ridge = np.where((X[0] > x0) & (X[0] < x1), y - h * prof * (1 + 0.25 * vnoise(W, 14, seed, 4)), 4000)
    fill_below(c, ridge, alpha, h * 0.7 + 4, edge=1.6, seed=seed, stop=y + 14)


def pine(c, x, base, h, seed, alpha=0.6):
    """松：彎曲的樹幹，層層橫向的松葉團。"""
    r = random.Random(seed)
    lay, d = _layer()
    a = int(255 * alpha)
    pts, cx, cy = [], x, base
    for k in range(8):
        cx += r.uniform(-8, 10)
        cy -= h / 8
        pts.append((cx, cy))
    d.line([(2 * x, 2 * base)] + [(2 * px, 2 * py) for px, py in pts], fill=a, width=7)
    for k, (px, py) in enumerate(pts[2:], start=2):
        if k % 2 == 0:
            w = h * r.uniform(0.25, 0.45)
            side = r.choice((-1, 1))
            fx = px + side * w * 0.4
            d.ellipse([2 * (fx - w), 2 * (py - w * 0.18), 2 * (fx + w), 2 * (py + w * 0.12)], fill=int(a * 0.85))
    _ink_layer(c, lay, SUMI, 0.9)


def dunes(c, y, seed, alpha=0.3):
    for k in range(3):
        base = y + k * 48
        ridge = base - 24 * np.sin(X[0] / (170 + 50 * k) + seed + k * 1.7) - 8 * vnoise(W, 220, seed + k, 3)
        fill_below(c, ridge, alpha * (0.45 + 0.25 * k), 16 + 8 * k, edge=2.4, edge_px=2, seed=seed + k)


def whirl(c, cx, cy, seed, turns=2.6, rad=110, alpha=0.32):
    lay = Image.new("L", (W * 2, H * 2), 0)
    d = ImageDraw.Draw(lay)
    for j in range(4):
        pts = []
        for i in range(300):
            t = i / 299
            a = t * turns * 2 * math.pi + j * 1.57
            rr = rad * (0.08 + 0.92 * t)
            pts.append((2 * (cx + rr * math.cos(a)), 2 * (cy + rr * math.sin(a) * 0.36)))
        d.line(pts, fill=int(255 * alpha * (1 - j * 0.18)), width=2)
    c.ink(np.asarray(lay.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6)), float) / 255)


def terraces(c, top, seed, alpha=0.2):
    for k in range(5):
        y = top + k * (H - top) / 5.2
        ridge = y - 6 * np.sin(X[0] / (220 + 30 * k) + seed + k) - 3 * vnoise(W, 160, seed + k, 3)
        fill_below(c, ridge, alpha * (0.5 + 0.12 * k), 10 + 4 * k, edge=2.0, edge_px=2, seed=seed + k)


def blossoms(c, seed, ridge, n=420):
    """沿著山稜散開的櫻花：細小、淡、成團。"""
    r = random.Random(seed)
    lay = Image.new("L", (W * 2, H * 2), 0)
    d = ImageDraw.Draw(lay)
    centers = [r.uniform(0.05, 0.95) * W for _ in range(14)]
    for _ in range(n):
        cx = r.choice(centers) + r.gauss(0, 40)
        if not 0 <= cx < W:
            continue
        cy = float(ridge[int(cx)]) + abs(r.gauss(0, 26)) + 4
        rad = r.uniform(1.6, 4.2)
        d.ellipse([2 * (cx - rad), 2 * (cy - rad), 2 * (cx + rad), 2 * (cy + rad)], fill=int(255 * r.uniform(0.18, 0.4)))
    c.ink(np.asarray(lay.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.1)), float) / 255, PINK)


def meoto(c, s):
    """夫婦岩：一大一小兩塊岩石，以注連繩相連。"""
    for cx, w, h, a in ((420, 70, 150, 0.55), (600, 46, 90, 0.5)):
        t = np.clip(1 - np.abs(X[0] - cx) / w, 0, 1)
        top = np.where(t > 0, 470 - h * t ** 0.5 * (1 + 0.12 * vnoise(W, 6, s + cx, 3)), 4000)
        dd = Y - top[None, :]
        body = np.where(dd >= 0, np.exp(-dd / (h * 0.9)) + 0.2, 0) * np.clip((500 - Y) / 30, 0, 1)
        c.ink(a * body * streaks(s + cx, 3))
    shimenawa(c, 440, 352, 600, 405, 18)
    torii(c, 420, 322, 0.22, SUMI, 0.6, reflect=False)


# ───────── 各縣構圖 ─────────
def far(c, s, y=250, amp=60, a=0.16, snow=None, sharp=False):
    mountains(c, y, amp, a, 120, s, 300, sharp=sharp, snow=snow)


SCENES = {
    "japan": lambda c, s: (cone(c, 560, 330, 230, 330, 0.36, 170, s, snow=0.32), mist(c, 300, 18, 0.7), sea(c, 340, 0.42, s, 1.2)),
    "hokkaido": lambda c, s: (far(c, s, 260, 70, 0.2, (210, 46), True), mountains(c, 330, 50, 0.28, 120, s + 1, 220, True, (300, 40)), mist(c, 350, 22), snowfall(c, s)),
    "aomori": lambda c, s: (far(c, s, 300, 30, 0.14), cone(c, 640, 330, 200, 280, 0.32, 140, s, snow=0.38), mist(c, 340, 20), castle(c, 300, 520, 0.85, 0.56, 0.12, 3), blossoms(c, s + 2, np.full(W, 470.0), 300), snowfall(c, s, 60)),
    "iwate": lambda c, s: (cone(c, 470, 350, 210, 330, 0.32, 150, s, snow=0.3, skew=0.4), mist(c, 340, 18), trees(c, 520, 0.0, 1.0, s, 60, 26, 70, 0.45)),
    "miyagi": lambda c, s: (far(c, s, 230, 30, 0.12), islands(c, 330, s, 7, 70, 0.48), trees(c, 300, 0.25, 0.45, s + 3, 10, 8, 16, 0.5), sea(c, 330, 0.3, s, 0.9)),
    "akita": lambda c, s: (cone(c, 640, 330, 200, 300, 0.28, 140, s, snow=0.35), mist(c, 330, 20), trees(c, 520, 0.0, 1.0, s, 70, 40, 110, 0.5)),
    "yamagata": lambda c, s: (cone(c, 520, 300, 150, 470, 0.28, 140, s, snow=0.45, flat=0.08), mist(c, 300, 20), mountains(c, 370, 34, 0.2, 60, s + 4, 160), trees(c, 380, 0.0, 0.32, s + 5, 20, 14, 30, 0.4), trees(c, 390, 0.68, 1.0, s + 6, 20, 14, 30, 0.4), river(c, 330, s, 4, 170, 0.3, 0.46)),
    "fukushima": lambda c, s: (cone(c, 560, 300, 190, 300, 0.3, 150, s, snow=0.25, skew=0.6), mist(c, 300, 16), lake(c, 330, 440, s), mountains(c, 470, 20, 0.22, 60, s + 2, 200)),
    "ibaraki": lambda c, s: (cone(c, 470, 330, 150, 200, 0.28, 140, s), cone(c, 600, 330, 135, 180, 0.24, 140, s + 1), mist(c, 330, 16), terraces(c, 410, s)),
    "tochigi": lambda c, s: (cone(c, 520, 320, 200, 290, 0.32, 150, s, snow=0.2), mist(c, 320, 16), lake(c, 340, 450, s), mountains(c, 470, 24, 0.24, 70, s + 2, 200)),
    "gunma": lambda c, s: (far(c, s, 220, 40, 0.12), cone(c, 520, 330, 170, 460, 0.28, 140, s, flat=0.12), mist(c, 330, 18), mountains(c, 430, 40, 0.3, 110, s + 4, 160)),
    "saitama": lambda c, s: (far(c, s, 220, 50, 0.12), mountains(c, 290, 50, 0.2, 100, s + 1, 200), mist(c, 300, 14), mountains(c, 380, 50, 0.3, 110, s + 2, 170), mist(c, 400, 14, 0.6)),
    "chiba": lambda c, s: (sea(c, 300, 0.36, s, 1.2), rocks(c, 300, s + 2, 2, 0.45), cliff(c, 760, 300, 640, s, 1, 0.42), lighthouse(c, 840, 300, 1.0, 0.6), mist(c, 560, 30, 0.5)),
    "tokyo": lambda c, s: (cone(c, 780, 300, 90, 140, 0.16, 90, s, snow=0.35), sea(c, 300, 0.38, s, 1.1)),
    "kanagawa": lambda c, s: (cone(c, 300, 270, 110, 170, 0.18, 100, s, snow=0.35), mountains(c, 300, 40, 0.26, 90, s + 1, 200), mist(c, 300, 14), sea(c, 340, 0.36, s, 1.0)),
    "niigata": lambda c, s: (far(c, s, 250, 80, 0.22, (220, 50), True), mist(c, 290, 18), terraces(c, 390, s, 0.16), snowfall(c, s, 120)),
    "toyama": lambda c, s: (mountains(c, 270, 110, 0.3, 120, s, 200, True, (220, 60)), mist(c, 290, 16), sea(c, 320, 0.38, s, 1.0)),
    "ishikawa": lambda c, s: (cone(c, 420, 280, 140, 330, 0.24, 130, s, snow=0.4, flat=0.1), mist(c, 290, 16), sea(c, 330, 0.36, s, 1.0), islands(c, 330, s + 5, 1, 140, 0.4)),
    "fukui": lambda c, s: (sea(c, 300, 0.32, s, 1.1), rocks(c, 300, s, 5, 0.5), mist(c, 420, 22, 0.35)),
    "yamanashi": lambda c, s: (cone(c, 560, 300, 240, 360, 0.36, 160, s, snow=0.34), mist(c, 300, 14, 0.6), trees(c, 470, 0.0, 0.45, s + 2, 40, 20, 50, 0.42), pagoda(c, 230, 500, 1.6, 0.74, VERMILION), blossoms(c, s + 4, np.full(W, 440.0), 260)),
    "nagano": lambda c, s: (mountains(c, 250, 120, 0.3, 120, s, 180, True, (190, 70)), mist(c, 290, 20), trees(c, 520, 0.0, 1.0, s, 60, 30, 80, 0.48)),
    "gifu": lambda c, s: (mountains(c, 250, 110, 0.28, 120, s, 200, True, (200, 60)), mist(c, 290, 18), trees(c, 400, 0.0, 1.0, s + 3, 40, 20, 50, 0.4), mist(c, 470, 26, 0.5), gassho(c, 560, [300, 520, 740], 1.15), snowfall(c, s, 110)),
    "shizuoka": lambda c, s: (cone(c, 560, 300, 240, 360, 0.36, 160, s, snow=0.34), mist(c, 300, 14, 0.6), sea(c, 340, 0.36, s, 1.0), spit(c, -40, 760, 520, 34, 0.5, s + 5), mist(c, 560, 30, 0.4)),
    "aichi": lambda c, s: (far(c, s, 230, 30, 0.14), mist(c, 250, 14), castle(c, 520, 400, 1.15, 0.62, 0.12, 5, shachi=True), trees(c, 420, 0.0, 0.36, s, 30, 18, 40, 0.42), trees(c, 420, 0.64, 1.0, s + 1, 30, 18, 40, 0.42), mist(c, 460, 30, 0.6)),
    "mie": lambda c, s: (sea(c, 300, 0.34, s, 1.1), rocks(c, 300, s + 11, 0, 0.5), meoto(c, s)),
    "shiga": lambda c, s: (far(c, s, 250, 50, 0.2), mountains(c, 280, 30, 0.22, 50, s + 1, 200), mist(c, 290, 10, 0.5), lake(c, 295, 600, s, 0.2), reeds(c, 0.0, 0.3, 600, s, 70)),
    "kyoto": lambda c, s: (far(c, s, 210, 40, 0.14), mist(c, 240, 20), trees(c, 330, 0.0, 1.0, s, 60, 40, 90, 0.34), mist(c, 380, 22, 0.75), trees(c, 560, 0.0, 1.0, s + 1, 34, 120, 230, 0.55)),
    "osaka": lambda c, s: (far(c, s, 270, 30, 0.12), sea(c, 300, 0.36, s, 1.0)),
    "hyogo": lambda c, s: (mountains(c, 250, 50, 0.18, 90, s, 260), mist(c, 280, 16), castle(c, 520, 420, 1.1, 0.56, 0.06, 5, wings=True), trees(c, 440, 0.0, 1.0, s + 3, 50, 14, 34, 0.4), mist(c, 470, 26, 0.6)),
    "nara": lambda c, s: (far(c, s, 230, 40, 0.14), mist(c, 260, 12, 0.5), blossoms(c, s, mountains(c, 320, 60, 0.15, 70, s + 1, 200)), blossoms(c, s + 9, mountains(c, 420, 40, 0.17, 60, s + 2, 220)), mist(c, 390, 14, 0.5)),
    "wakayama": lambda c, s: (far(c, s, 170, 30, 0.1), waterfall(c, 520, 200, 560, s, 30, 0.58, 300), trees(c, 214, 0.22, 0.78, s, 46, 18, 46, 0.5), trees(c, 600, 0.0, 0.22, s + 1, 10, 60, 130, 0.5), trees(c, 600, 0.8, 1.0, s + 2, 10, 60, 130, 0.5)),
    "tottori": lambda c, s: (cone(c, 640, 260, 150, 260, 0.24, 120, s, snow=0.3), mist(c, 270, 14), dunes(c, 360, s, 0.3)),
    "shimane": lambda c, s: (far(c, s, 260, 40, 0.18), mist(c, 280, 14), lake(c, 300, 600, s, 0.2), islands(c, 300, s, 1, 50, 0.4), reeds(c, 0.72, 1.0, 600, s, 50)),
    "okayama": lambda c, s: (far(c, s, 230, 30, 0.14), mist(c, 250, 12), river(c, 420, s, 40, 220, 0.24, 0.5), castle(c, 520, 400, 1.05, 0.7, 0.78, 4)),
    "hiroshima": lambda c, s: (mountains(c, 250, 70, 0.22, 110, s, 220), mist(c, 280, 14), sea(c, 320, 0.3, s, 0.9), torii(c, 520, 470, 1.25)),
    "yamaguchi": lambda c, s: (mountains(c, 230, 60, 0.2, 100, s, 260), cone(c, 760, 260, 90, 120, 0.2, 80, s + 2, flat=0.1), mist(c, 300, 18), lake(c, 380, 600, s, 0.16), arch_bridge(c, 120, 920, 420, 5, 40, 0.62)),
    "tokushima": lambda c, s: (far(c, s, 240, 30, 0.14), sea(c, 270, 0.3, s, 0.9), whirl(c, 520, 430, s, 2.8, 170, 0.5), whirl(c, 820, 360, s + 1, 2.2, 80, 0.35)),
    "kagawa": lambda c, s: (islands(c, 310, s, 7, 55, 0.42), sea(c, 310, 0.34, s, 1.0)),
    "ehime": lambda c, s: (mountains(c, 260, 120, 0.28, 110, s, 160, True, (210, 40)), mist(c, 290, 16), islands(c, 340, s + 1, 4, 60, 0.4), sea(c, 340, 0.3, s, 0.9)),
    "kochi": lambda c, s: (far(c, s, 220, 40, 0.14), river(c, 250, s, 4, 220, 0.34, 0.4), sea(c, 520, 0.3, s, 0.5)),
    "fukuoka": lambda c, s: (far(c, s, 300, 26, 0.12), sea(c, 330, 0.3, s, 1.0), plum_branch(c, s)),
    "saga": lambda c, s: (far(c, s, 250, 30, 0.14), mist(c, 270, 12), lake(c, 280, 600, s, 0.12), nori_poles(c, 280, s)),
    "nagasaki": lambda c, s: (islands(c, 320, s, 14, 45, 0.45), sea(c, 320, 0.3, s, 1.0)),
    "kumamoto": lambda c, s: (mountains(c, 330, 60, 0.26, 110, s, 320), cone(c, 560, 330, 120, 260, 0.3, 90, s + 1, flat=0.14), smoke(c, 560, 228, s), mist(c, 340, 16), mountains(c, 440, 26, 0.2, 70, s + 2, 260)),
    "oita": lambda c, s: (cone(c, 500, 320, 190, 240, 0.3, 120, s), cone(c, 590, 320, 160, 200, 0.26, 120, s + 1), mist(c, 330, 20), trees(c, 360, 0.0, 1.0, s + 3, 50, 12, 28, 0.36), lake(c, 380, 600, s, 0.18), mist(c, 420, 40, 0.55)),
    "miyazaki": lambda c, s: (waterfall(c, 470, 190, 520, s, 18, 0.6, 260), trees(c, 204, 0.2, 0.75, s, 40, 16, 40, 0.48), river(c, 500, s, 40, 170, 0.22, 0.45)),
    "kagoshima": lambda c, s: (cone(c, 540, 330, 190, 330, 0.34, 140, s, flat=0.12), smoke(c, 540, 152, s, 1.0, 0.18, 300), sea(c, 340, 0.36, s, 1.0)),
    "okinawa": lambda c, s: (islands(c, 340, s, 3, 90, 0.3), sea(c, 340, 0.28, s, 0.8)),
}


def render(slug):
    seed = sum(map(ord, slug)) * 7
    random.seed(seed)
    c = Canvas(seed)
    SCENES[slug](c, seed)
    # 上緣淡出，融進紙面
    c.a *= np.clip(Y / (H * 0.32), 0, 1) ** 0.8
    OUT.mkdir(parents=True, exist_ok=True)
    c.save(OUT / f"{slug}.webp")


if __name__ == "__main__":
    import sys
    for s in (sys.argv[1:] or SCENES):
        render(s)
        print("painted", s)
