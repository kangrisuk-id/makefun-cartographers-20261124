#!/usr/bin/env python3
"""
The Isle of Lost & Found — a treasure map of an island that does not exist.

Draws one 1024x1024 parchment treasure map with Pillow, deterministically
(fixed seed), and writes it to /output/entry.png (falling back to ./entry.png
next to this script when /output is not writable).

Entry for make.fun's "Charm the Cartographers" bounty.
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont, ImageFilter

SS = 2                      # supersampling factor
W = 1024 * SS               # working canvas
H = 1024 * SS
SEED = 20261124

INK = (58, 36, 18)          # dark brown ink
INK_SOFT = (92, 62, 32)
PARCH = (233, 213, 164)     # parchment
PARCH_LAND = (238, 220, 172)
SEA_WASH = (196, 214, 196)  # pale sage wash for the sea
WATER = (94, 124, 138)      # slate blue for river / lake
WATER_LT = (150, 178, 186)
RED = (158, 44, 30)         # treasure red
GOLD = (146, 106, 32)

rng = random.Random(SEED)

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")


def font(kind, size):
    name = {
        "serif": "LiberationSerif-Regular.ttf",
        "bold": "LiberationSerif-Bold.ttf",
        "italic": "LiberationSerif-Italic.ttf",
        "bolditalic": "LiberationSerif-BoldItalic.ttf",
    }[kind]
    path = os.path.join(FONT_DIR, name)
    if not os.path.exists(path):
        path = "/usr/share/fonts/truetype/liberation/" + name
    return ImageFont.truetype(path, size)


# ---------------------------------------------------------------- parchment
def make_parchment():
    img = Image.new("RGB", (W, H), PARCH)
    px = img.load()
    # gentle blotchy noise
    noise = Image.new("L", (W // 8, H // 8))
    npx = noise.load()
    r = random.Random(SEED + 1)
    for y in range(H // 8):
        for x in range(W // 8):
            npx[x, y] = r.randint(196, 255)
    noise = noise.resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(18))
    npx = noise.load()
    for y in range(H):
        for x in range(W):
            f = npx[x, y] / 255.0
            c = img.getpixel((x, y))
            px[x, y] = tuple(int(v * (0.90 + 0.10 * f)) for v in c)
    # vignette: darker, warmer edges
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-W * 0.28, -H * 0.28, W * 1.28, H * 1.28], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(220))
    dark = Image.new("RGB", (W, H), (198, 168, 116))
    img = Image.composite(img, dark, vig.point(lambda v: 255 - int((255 - v) * 0.55)))
    return img


def draw_stains(d):
    # faint coffee-ring stains, as a much-travelled chart would have
    for (cx, cy, rad) in [(1760, 1660, 120), (1850, 1150, 64)]:
        for k in range(3):
            d.ellipse([cx - rad - k * 3, cy - rad - k * 3, cx + rad + k * 3, cy + rad + k * 3],
                      outline=(176, 140, 82), width=3)


# ---------------------------------------------------------------- geometry
def catmull_rom_closed(points, subdiv=10):
    pts = points[:]
    out = []
    n = len(pts)
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        for j in range(subdiv):
            t = j / subdiv
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    return out


def jitter(points, amp, seed):
    r = random.Random(seed)
    return [(x + r.uniform(-amp, amp), y + r.uniform(-amp, amp)) for (x, y) in points]


def smooth_line(points, subdiv=12):
    # open catmull-rom
    pts = [points[0]] + points[:] + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for j in range(subdiv):
            t = j / subdiv
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    out.append(points[-1])
    return out


COAST_CTRL = [
    (455, 640), (560, 520), (760, 452), (1010, 438), (1240, 452),
    (1335, 520), (1470, 470), (1600, 545), (1668, 760), (1640, 1010),
    (1560, 1240), (1470, 1400), (1330, 1520), (1180, 1580),
    (1090, 1470), (960, 1470), (850, 1590), (660, 1560), (520, 1400),
    (445, 1180), (470, 1040), (430, 900), (420, 760),
]


# ---------------------------------------------------------------- doodles
def mountain(d, cx, cy, s, ink=INK):
    # one peak: two slopes, a snow notch, a shaded side
    d.line([(cx - s, cy + s * 0.72), (cx, cy - s), (cx + s, cy + s * 0.72)],
           fill=ink, width=5, joint="curve")
    d.line([(cx, cy - s), (cx + s * 0.42, cy + s * 0.05)], fill=ink, width=4)
    d.line([(cx - s * 0.22, cy - s * 0.55), (cx, cy - s * 0.78), (cx + s * 0.22, cy - s * 0.55)],
           fill=ink, width=3)


def pine(d, cx, cy, s, ink=INK):
    d.line([(cx, cy), (cx, cy + s * 0.5)], fill=ink, width=4)
    for k, wfrac in enumerate([0.95, 0.7, 0.45]):
        yy = cy + s * (0.28 - 0.30 * k)
        d.line([(cx - s * wfrac * 0.5, yy), (cx, yy - s * 0.42), (cx + s * wfrac * 0.5, yy)],
               fill=ink, width=4, joint="curve")


def palm(d, cx, cy, s, ink=INK):
    # curved trunk, then fronds that arc up and droop at the tips
    trunk = [(cx + s * 0.30 * math.sin(t * 1.1), cy + s * 1.5 * (1 - t)) for t in
             [i / 10 for i in range(11)]]
    d.line(trunk, fill=ink, width=5, joint="curve")
    tx, ty = trunk[-1]
    for dx in (-1.0, -0.55, 0.0, 0.55, 1.0):
        pts = []
        for i in range(9):
            t = i / 8
            x = tx + dx * s * 0.95 * t
            y = ty - s * 0.45 * math.sin(t * math.pi * 0.55) + s * 0.52 * t * t
            pts.append((x, y))
        d.line(pts, fill=ink, width=4, joint="curve")
    d.ellipse([tx - 6, ty - 2, tx + 6, ty + 10], fill=ink)


def dashed_line(d, points, dash=26, gap=16, fill=RED, width=6):
    # draw a polyline as even dashes measured along its length
    total = [0.0]
    for i in range(1, len(points)):
        total.append(total[-1] + math.hypot(points[i][0] - points[i - 1][0],
                                            points[i][1] - points[i - 1][1]))
    seg_start = 0.0
    on = True
    acc = 0.0
    for i in range(1, len(points)):
        seg = total[i] - total[i - 1]
        if seg == 0:
            continue
        pos = 0.0
        while pos < seg:
            step = min((dash if on else gap) - acc, seg - pos)
            if on and step > 0:
                t0, t1 = pos / seg, (pos + step) / seg
                a = (points[i - 1][0] + (points[i][0] - points[i - 1][0]) * t0,
                     points[i - 1][1] + (points[i][1] - points[i - 1][1]) * t0)
                b = (points[i - 1][0] + (points[i][0] - points[i - 1][0]) * t1,
                     points[i - 1][1] + (points[i][1] - points[i - 1][1]) * t1)
                d.line([a, b], fill=fill, width=width)
            acc += step
            pos += step
            if acc >= (dash if on else gap) - 1e-9:
                on = not on
                acc = 0.0
        seg_start = total[i]


def house(d, cx, cy, s, ink=INK):
    d.rectangle([cx - s, cy - s * 0.2, cx + s, cy + s * 0.75], outline=ink, width=4)
    d.line([(cx - s * 1.25, cy - s * 0.2), (cx, cy - s), (cx + s * 1.25, cy - s * 0.2)],
           fill=ink, width=4, joint="curve")
    d.rectangle([cx - s * 0.22, cy + s * 0.15, cx + s * 0.22, cy + s * 0.75], outline=ink, width=3)


def lighthouse(d, cx, cy, s, ink=INK):
    # tapered tower, gallery, lamp room and a little dome; beams out to sea
    top_y, bot_y = cy - s * 0.95, cy + s
    d.polygon([(cx - s * 0.40, bot_y), (cx - s * 0.20, top_y + s * 0.35),
               (cx + s * 0.20, top_y + s * 0.35), (cx + s * 0.40, bot_y)], outline=ink, width=4)
    for f in (0.30, 0.62):
        yy = bot_y - (bot_y - top_y - s * 0.35) * f
        hw = s * (0.40 - 0.20 * f)
        d.line([(cx - hw, yy), (cx + hw, yy)], fill=ink, width=3)
    d.rectangle([cx - s * 0.30, top_y + s * 0.12, cx + s * 0.30, top_y + s * 0.35], outline=ink, width=4)
    d.arc([cx - s * 0.24, top_y - s * 0.22, cx + s * 0.24, top_y + s * 0.14], start=180, end=360, fill=ink, width=4)
    for dy in (-s * 0.55, -s * 0.05):  # the second look, east over the water
        d.line([(cx + s * 0.30, top_y + s * 0.22), (cx + s * 1.5, top_y + s * 0.22 + dy)],
               fill=INK_SOFT, width=3)


def sea_monster(d, cx, cy, s, ink=INK):
    for k in range(3):  # humps
        x = cx - s * 1.2 + k * s * 0.85
        d.arc([x, cy - s * 0.34, x + s * 0.8, cy + s * 0.34], start=180, end=360, fill=ink, width=5)
    hx, hy = cx + s * 1.45, cy - s * 0.10  # head on a curving neck
    neck = [(hx - s * 0.55 + s * 0.55 * t, hy + s * 0.42 - s * 0.55 * t + s * 0.18 * math.sin(t * 3))
            for t in [i / 8 for i in range(9)]]
    d.line(neck, fill=ink, width=5, joint="curve")
    d.ellipse([hx - s * 0.05, hy - s * 0.38, hx + s * 0.52, hy + s * 0.05], outline=ink, width=4)
    d.ellipse([hx + s * 0.13, hy - s * 0.26, hx + s * 0.21, hy - s * 0.18], fill=ink)
    d.arc([hx + s * 0.08, hy - s * 0.16, hx + s * 0.42, hy + s * 0.10], start=20, end=110,
          fill=ink, width=3)  # an apologetic little smile


def ship(d, cx, cy, s, ink=INK):
    d.line([(cx - s, cy + s * 0.55), (cx - s * 0.7, cy + s * 0.95), (cx + s * 0.7, cy + s * 0.95),
            (cx + s, cy + s * 0.55)], fill=ink, width=4, joint="curve")
    d.line([(cx, cy + s * 0.55), (cx, cy - s)], fill=ink, width=4)
    d.polygon([(cx, cy - s), (cx, cy + s * 0.3), (cx + s * 0.62, cy + s * 0.3)], outline=ink, width=4)
    d.polygon([(cx, cy - s * 0.55), (cx, cy + s * 0.3), (cx - s * 0.5, cy + s * 0.3)], outline=ink, width=4)


def compass_rose(d, cx, cy, r, ink=INK):
    for k in range(8):
        ang = math.radians(k * 45)
        long = r if k % 2 == 0 else r * 0.55
        ex, ey = cx + math.cos(ang) * long, cy + math.sin(ang) * long
        px, py = math.cos(ang + math.pi / 2), math.sin(ang + math.pi / 2)
        wdt = r * 0.10 if k % 2 == 0 else r * 0.07
        d.polygon([(cx + px * wdt, cy + py * wdt), (ex, ey), (cx - px * wdt, cy - py * wdt)],
                  fill=ink if k % 2 == 0 else None, outline=ink, width=3)
    d.ellipse([cx - r * 0.16, cy - r * 0.16, cx + r * 0.16, cy + r * 0.16], outline=ink, width=4)
    d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=ink)
    f = font("bold", int(r * 0.34))
    d.text((cx, cy - r - int(r * 0.42)), "N", font=f, fill=ink, anchor="mm")
    d.text((cx, cy + r + int(r * 0.34)), "S", font=f, fill=ink, anchor="mm")
    d.text((cx - r - int(r * 0.30), cy), "W", font=f, fill=ink, anchor="mm")
    d.text((cx + r + int(r * 0.30), cy), "E", font=f, fill=ink, anchor="mm")


def text(d, xy, s, kind, size, fill=INK, anchor="la", spacing=4):
    d.text(xy, s, font=font(kind, size), fill=fill, anchor=anchor, spacing=spacing,
           stroke_width=2, stroke_fill=(238, 222, 178))


# ---------------------------------------------------------------- the map
def build():
    img = make_parchment()
    d = ImageDraw.Draw(img, "RGBA")

    coast = catmull_rom_closed(COAST_CTRL, subdiv=12)
    coast_j = jitter(coast, 3.5, SEED + 7)

    # island mask for clipping sea details
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)
    md.polygon(coast, fill=255)

    # sea wash: gentle sage tint outside the island
    sea = Image.new("RGB", (W, H), SEA_WASH)
    img.paste(Image.blend(img, sea, 0.35), (0, 0), mask.point(lambda v: 255 - v))
    d = ImageDraw.Draw(img, "RGBA")

    draw_stains(d)

    # rhumb lines from the compass rose, faint, under everything else
    ccx, ccy = 1748, 292
    for k in range(16):
        ang = math.radians(k * 22.5)
        ex, ey = ccx + math.cos(ang) * 2600, ccy + math.sin(ang) * 2600
        d.line([(ccx, ccy), (ex, ey)], fill=(120, 92, 50, 36), width=2)

    # shallows: a pale offset outline hugging the coast
    d.line(coast_j + [coast_j[0]], fill=(120, 150, 148, 160), width=26)
    # island body
    d.polygon(coast, fill=PARCH_LAND + (255,))
    # shore ticks (hachures) pointing out to sea
    r = random.Random(SEED + 3)
    for i in range(0, len(coast), 3):
        x, y = coast[i]
        x2, y2 = coast[(i + 6) % len(coast)]
        mx, my = (x + x2) / 2, (y + y2) / 2
        dx, dy = x - mx, y - my
        ln = math.hypot(dx, dy) or 1
        dx, dy = dx / ln, dy / ln
        # outward = away from island centre
        cxm, cym = 1030, 1010
        if (x - cxm) * dx + (y - cym) * dy < 0:
            dx, dy = -dx, -dy
        ln2 = 16 + r.uniform(0, 10)
        d.line([(x, y), (x + dx * ln2, y + dy * ln2)], fill=INK_SOFT + (170,), width=3)
    # coast ink: double line
    d.line(coast_j + [coast_j[0]], fill=INK, width=6, joint="curve")
    inner = catmull_rom_closed([(x * 0.985 + 1030 * 0.015, y * 0.985 + 1010 * 0.015) for (x, y) in COAST_CTRL], subdiv=12)
    d.line(inner + [inner[0]], fill=INK_SOFT + (150,), width=2, joint="curve")

    # waves in the open sea
    r = random.Random(SEED + 5)
    waves = 0
    while waves < 130:
        x, y = r.uniform(90, W - 90), r.uniform(90, H - 90)
        if mask.getpixel((int(x), int(y))):
            continue
        s = r.uniform(13, 24)
        d.arc([x - s, y - s * 0.45, x + s, y + s * 0.45], start=200, end=340,
              fill=(90, 110, 105, 150), width=3)
        waves += 1
    # soundings, as a careful surveyor would leave them
    for (sx, sy, t) in [(300, 860, "5"), (1010, 262, "12"), (1780, 1180, "9"),
                        (880, 1700, "2"), (1230, 250, "7"), (250, 1500, "3")]:
        text(d, (sx, sy), t, "italic", 34, fill=INK_SOFT, anchor="mm")

    # ---- lake and river
    lake = (1300, 960)
    d.ellipse([lake[0] - 128, lake[1] - 74, lake[0] + 128, lake[1] + 74], fill=WATER_LT, outline=INK, width=4)
    d.arc([lake[0] - 70, lake[1] - 26, lake[0] + 10, lake[1] + 26], start=200, end=330, fill=WATER, width=3)
    river = smooth_line([(905, 770), (960, 905), (990, 1085), (975, 1255), (950, 1445)], subdiv=14)
    d.line(river, fill=WATER, width=8, joint="curve")
    d.line(river, fill=WATER_LT, width=3, joint="curve")
    stream = smooth_line([(1420, 975), (1505, 985), (1585, 1000)], subdiv=10)
    d.line(stream, fill=WATER, width=6, joint="curve")

    # ---- terrain glyphs
    for (mx, my, s) in [(905, 730, 78), (815, 770, 54), (995, 772, 50), (860, 688, 44)]:
        mountain(d, mx, my, s)
    r = random.Random(SEED + 9)
    for _ in range(26):  # the Forest of Small Regrets
        x, y = r.uniform(585, 770), r.uniform(1140, 1280)
        pine(d, x, y, r.uniform(30, 46))
    for (hx, hy, s) in [(985, 1185, 42), (1085, 1210, 28)]:  # Hill of Tall Tales
        d.arc([hx - s, hy - s * 0.5, hx + s, hy + s * 0.5], start=180, end=360, fill=INK, width=4)
    for (px, py, s) in [(1400, 1290, 38), (560, 700, 34)]:
        palm(d, px, py, s)

    # ---- buildings
    for (hx, hy, s) in [(930, 1408, 26), (985, 1425, 22), (890, 1430, 20)]:
        house(d, hx, hy, s)
    d.ellipse([955, 1462, 975, 1482], outline=INK, width=4)  # anchor ring at the harbour
    d.line([(965, 1448), (965, 1472)], fill=INK, width=4)
    lighthouse(d, 1608, 985, 62)
    # the Sunken Chapel, awash in the west inlet: two broken columns and a fallen arch
    d.line([(478, 1040), (478, 972)], fill=INK, width=6)
    d.line([(508, 1040), (508, 986)], fill=INK, width=6)
    d.line([(470, 972), (493, 946), (516, 972)], fill=INK, width=4, joint="curve")
    d.line([(486, 930), (486, 952)], fill=INK, width=4)
    d.line([(478, 941), (494, 941)], fill=INK, width=4)
    d.line([(522, 1032), (548, 1018)], fill=INK, width=5)  # a column that gave up
    d.arc([462, 1000, 530, 1052], start=190, end=330, fill=WATER, width=3)
    # smuggler's hammock slung between two palms at the north cove
    palm(d, 1300, 548, 32)
    palm(d, 1396, 553, 32)
    hammock = [(1326 + 52 * t, 600 + 26 * math.sin(math.pi * t)) for t in [i / 10 for i in range(11)]]
    d.line(hammock, fill=INK, width=4, joint="curve")
    # shoals: Dead Men's Discount
    r = random.Random(SEED + 11)
    for _ in range(46):
        x, y = r.gauss(1560, 80), r.gauss(1700, 30)
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=INK_SOFT)

    # ---- the route to the treasure
    route = smooth_line([(950, 1440), (958, 1320), (988, 1242), (1025, 1148)], subdiv=14)
    dashed_line(d, route, dash=27, gap=17, fill=RED, width=6)
    X, Y = 1028, 1140
    d.line([(X - 34, Y - 34), (X + 34, Y + 34)], fill=RED, width=11)
    d.line([(X - 34, Y + 34), (X + 34, Y - 34)], fill=RED, width=11)

    # ---- sea life and company
    sea_monster(d, 1775, 725, 62)
    ship(d, 285, 1175, 58)
    compass_rose(d, ccx, ccy, 118)
    text(d, (ccx + 30, ccy - 118 - 62), "(ish)", "italic", 27, fill=INK_SOFT)

    # ---- labels
    text(d, (1000, 1330), "PORT MISLAID", "bold", 50)
    text(d, (1000, 1388), "(you are here, probably)", "italic", 34, fill=INK_SOFT)
    text(d, (112, 498), "CAPE FORGET-ME-KNOT", "bold", 44)
    text(d, (610, 562), "MOUNT GRUMBLE", "bold", 46)
    text(d, (610, 614), "(it complains about the weather)", "italic", 32, fill=INK_SOFT)
    text(d, (1046, 512), "SMUGGLER'S NAP", "bold", 40)
    text(d, (560, 952), "THE SUNKEN CHAPEL", "bold", 38)
    text(d, (560, 1000), "(services at low tide only)", "italic", 30, fill=INK_SOFT)
    text(d, (480, 1290), "THE FOREST OF", "bold", 40)
    text(d, (480, 1338), "SMALL REGRETS", "bold", 40)
    text(d, (1150, 832), "LAKE MIRROR-MIRROR", "bold", 42)
    text(d, (1300, 1088), "(you, but braver)", "italic", 32, fill=INK_SOFT, anchor="ma")
    text(d, (1560, 1145), "THE LIGHTHOUSE", "bold", 40, anchor="ra")
    text(d, (1560, 1191), "OF SECOND LOOKS", "bold", 40, anchor="ra")
    text(d, (700, 1042), "THE HILL OF", "bold", 40)
    text(d, (700, 1090), "TALL TALES", "bold", 40)
    text(d, (1028, 1262), "CAPT. LEDGER'S", "bold", 37, fill=RED, anchor="ma")
    text(d, (1028, 1306), "LAST DEPOSIT", "bold", 37, fill=RED, anchor="ma")
    text(d, (1300, 1608), "THE SHIVERING SANDS", "bold", 42, anchor="ma")
    text(d, (1300, 1660), "(the crabs hold the towels)", "italic", 30, fill=INK_SOFT, anchor="ma")
    text(d, (1620, 1796), "DEAD MEN'S DISCOUNT", "bold", 42, anchor="ma")
    text(d, (1620, 1848), "(all wrecks final sale)", "italic", 30, fill=INK_SOFT, anchor="ma")
    text(d, (1704, 828), "Barnaby (sorry)", "italic", 33, fill=INK_SOFT)
    text(d, (180, 1470), "The Dozing Deep", "italic", 38, fill=INK_SOFT)
    text(d, (1012, 1002), "R. Rinse", "italic", 30, fill=WATER)

    # ---- title cartouche
    d.rectangle([104, 104, 912, 300], fill=PARCH + (235,), outline=INK, width=5)
    d.rectangle([118, 118, 898, 286], outline=INK_SOFT, width=2)
    text(d, (508, 138), "THE ISLE OF LOST & FOUND", "bold", 62, anchor="ma")
    text(d, (508, 216), "survey'd by Capt. E. Ledger, who mislaid the first copy",
         "italic", 31, fill=INK_SOFT, anchor="ma")

    # ---- legend
    lx, ly = 104, 1584
    d.rectangle([lx, ly, lx + 610, ly + 356], fill=PARCH + (235,), outline=INK, width=5)
    d.rectangle([lx + 14, ly + 14, lx + 596, ly + 342], outline=INK_SOFT, width=2)
    text(d, (lx + 36, ly + 28), "A KEY TO YE CHARTE", "bold", 38)
    rows = [
        ("x", "one (1) fortune, buried deepish"),
        ("dash", "the way in — mind the crabs"),
        ("anchor", "anchorage, safe-ish"),
        ("wave", "wet. do not walk here"),
    ]
    yy = ly + 88
    for key, val in rows:
        gx = lx + 62
        if key == "x":
            d.line([(gx - 13, yy + 4), (gx + 13, yy + 30)], fill=RED, width=6)
            d.line([(gx - 13, yy + 30), (gx + 13, yy + 4)], fill=RED, width=6)
        elif key == "dash":
            d.line([(gx - 24, yy + 17), (gx + 24, yy + 17)], fill=RED, width=6)
        elif key == "anchor":
            d.ellipse([gx - 6, yy - 2, gx + 6, yy + 10], outline=INK, width=4)
            d.line([(gx, yy + 8), (gx, yy + 34)], fill=INK, width=4)
            d.line([(gx - 13, yy + 14), (gx + 13, yy + 14)], fill=INK, width=4)
            d.arc([gx - 16, yy + 18, gx + 16, yy + 44], start=0, end=180, fill=INK, width=4)
        else:
            d.arc([gx - 24, yy + 4, gx, yy + 30], start=200, end=340, fill=WATER, width=4)
            d.arc([gx, yy + 4, gx + 24, yy + 30], start=200, end=340, fill=WATER, width=4)
        text(d, (lx + 130, yy), val, "serif", 32)
        yy += 54
    # scale bar
    bx, by = lx + 36, ly + 356 - 40
    seg = 56
    for k in range(5):
        d.rectangle([bx + k * seg, by, bx + (k + 1) * seg, by + 14],
                    fill=INK if k % 2 == 0 else None, outline=INK, width=2)
    text(d, (bx + 5 * seg + 18, by - 10), "leagues, roughly", "italic", 28, fill=INK_SOFT)

    # ---- frame
    d.rectangle([38, 38, W - 38, H - 38], outline=INK, width=6)
    d.rectangle([62, 62, W - 62, H - 62], outline=INK_SOFT, width=2)
    for (fx, fy) in [(38, 38), (W - 38, 38), (38, H - 38), (W - 38, H - 38)]:
        d.ellipse([fx - 13, fy - 13, fx + 13, fy + 13], outline=INK, width=4)

    img = img.resize((1024, 1024), Image.LANCZOS)
    img = img.quantize(colors=256, method=Image.MEDIANCUT)
    return img


def main():
    img = build()
    out = "/output/entry.png"
    try:
        os.makedirs("/output", exist_ok=True)
        img.save(out, optimize=True)
    except OSError:
        out = os.path.join(HERE, "entry.png")
        img.save(out, optimize=True)
    print("wrote", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
