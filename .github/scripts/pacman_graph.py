
"""
Pac-Man Cyberpunk Matrix Arcade & Elegant Real-Time Activity Graph Generator
Clean, Authentic Developer Credentials, Zero AI Slop
"""
import argparse
import datetime as dt
import heapq
import json
import math
import os
import random
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass
from html import escape

PALETTES = {
    "purple": dict(
        card_a="#0d1117", card_b="#06080d", tile="#131722", tile_edge="#2a1b40",  
        levels=["#4c1d95", "#7e22ce", "#a855f7", "#e9d5ff"],
        accent="#a855f7", wall="#a855f7", glow="#c084fc", text="#f5f3ff", muted="#94a3b8"
    )
}

GHOSTS = [
    ("blinky", "#ff2a2a", "#ff8080"),
    ("pinky", "#ff5ecb", "#ffa8e8"),
    ("inky", "#a78bfa", "#c4b5fd"),  # Inky jadi lilac/ungu lembut (bukan cyan lagi)
    ("clyde", "#ff9100", "#ffc266"),
]

S, G = 16, 4
P = S + G
DIRS = [(0, -1), (-1, 0), (0, 1), (1, 0)]
RELEASE = [0, 6, 14, 24]
K_READY = 16
K_END = 26

def num(x, n=2):
    s = f"{x:.{n}f}"
    if "." in s: s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s

def kt(x): return num(min(1.0, max(0.0, x)), 5)

def hex2rgb(h):
    h = h.lstrip("#")
    if len(h) == 3: h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def mix(a, b, t):
    ra, rb = hex2rgb(a), hex2rgb(b)
    return "#%02x%02x%02x" % tuple(round(ra[i] + (rb[i] - ra[i]) * t) for i in range(3))

@dataclass
class Day:
    date: str
    col: int
    row: int
    count: int
    level: int

def http(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "pacman-arcade"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def days_from_dates(items):
    items = sorted(items)
    first = dt.date.fromisoformat(items[0][0])
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)
    out = []
    for ds, count, level in items:
        d = dt.date.fromisoformat(ds)
        out.append(Day(ds, (d - start).days // 7, (d.weekday() + 1) % 7, count, level))
    return out

def demo_days(seed=42):
    rng = random.Random(seed)
    end = dt.date.today()
    start = end - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    raw, d = [], start
    while d <= end:
        cnt = int(rng.expovariate(0.28)) if rng.random() < 0.48 else 0
        lvl = min(4, max(1, cnt)) if cnt > 0 else 0
        raw.append((d.isoformat(), cnt, lvl))
        d += dt.timedelta(days=1)
    return days_from_dates(raw)

def load_days(user):
    try:
        raw = http(f"https://github-contributions-api.jogruber.de/v4/{user}")
        data = json.loads(raw)
        items = [(d["date"], d["count"], d["level"]) for d in data.get("contributions", [])]
        if items:
            print(f"[OK] Berhasil membaca {len(items)} hari kontribusi asli dari API.")
            return days_from_dates(items)
    except Exception as e:
        print(f"[WARN] API: {e}")

    try:
        html = http(f"https://github.com/users/{user}/contributions")
        items = []
        for m in re.finditer(r'<td\b[^>]*data-date="([^"]+)"[^>]*data-level="([^"]+)"', html):
            items.append((m.group(1), 1 if int(m.group(2)) > 0 else 0, int(m.group(2))))
        if items:
            print(f"[OK] Scraped {len(items)} hari dari HTML.")
            return days_from_dates(items)
    except Exception as e:
        print(f"[WARN] Scraper: {e}")

    print("[INFO] Fallback to active matrix calendar.")
    return demo_days(42)

class Maze:
    def __init__(self, cells, rng, density=0.20):
        self.cells = set(cells)
        self.rng = rng
        self.blocked = set()
        self.base = {c: sum((c[0] + d[0], c[1] + d[1]) in self.cells for d in DIRS) for c in self.cells}
        self.deg = dict(self.base)
        self.walls = []
        total = sum(self.base.values()) // 2
        self._grow(int(total * density))
        self.adj = {c: [n for n in self._nb(c) if self._key(c, n) not in self.blocked] for c in self.cells}

    @staticmethod
    def _key(a, b): return (a, b) if a < b else (b, a)
    def _nb(self, c):
        for d in DIRS:
            n = (c[0] + d[0], c[1] + d[1])
            if n in self.cells: yield n

    def _connected(self):
        start = next(iter(self.cells))
        seen, dq = {start}, deque([start])
        while dq:
            c = dq.popleft()
            for n in self._nb(c):
                if n not in seen and self._key(c, n) not in self.blocked:
                    seen.add(n); dq.append(n)
        return len(seen) == len(self.cells)

    def _try(self, a, b):
        k = self._key(a, b)
        if k in self.blocked or self.deg[a] - 1 < min(2, self.base[a]) or self.deg[b] - 1 < min(2, self.base[b]):
            return False
        self.blocked.add(k)
        if not self._connected():
            self.blocked.discard(k); return False
        self.deg[a] -= 1; self.deg[b] -= 1
        return True

    def _grow(self, target):
        cells = sorted(self.cells)
        tries = 0
        while len(self.blocked) < target and tries < 4000:
            tries += 1
            c = self.rng.choice(cells)
            vert = self.rng.random() < 0.5
            for i in range(self.rng.choice([2, 3])):
                a = (c[0], c[1] + i) if vert else (c[0] + i, c[1])
                b = (a[0] + 1, a[1]) if vert else (a[0], a[1] + 1)
                if a not in self.cells or b not in self.cells or not self._try(a, b): break
                self.walls.append(("v" if vert else "h", a, b))

    def wall_path(self, px, py):
        vs, hs = {}, {}
        for o, a, b in self.walls:
            if o == "v": vs.setdefault(a[0] + 1, []).append(a[1])
            else: hs.setdefault(a[1] + 1, []).append(a[0])
        d = []
        for X, rows in sorted(vs.items()):
            rows = sorted(set(rows))
            lo, prev = rows[0], rows[0]
            for v in rows[1:]:
                if v != prev + 1:
                    d.append(f"M{num(px(X))} {num(py(lo))}V{num(py(prev + 1))}")
                    lo = v
                prev = v
            d.append(f"M{num(px(X))} {num(py(lo))}V{num(py(prev + 1))}")
        for Y, cols in sorted(hs.items()):
            cols = sorted(set(cols))
            lo, prev = cols[0], cols[0]
            for v in cols[1:]:
                if v != prev + 1:
                    d.append(f"M{num(px(lo))} {num(py(Y))}H{num(px(prev + 1))}")
                    lo = v
                prev = v
            d.append(f"M{num(px(lo))} {num(py(Y))}H{num(px(prev + 1))}")
        return "".join(d)

class GhostAI:
    def __init__(self, idx, name, cell, release):
        self.idx, self.name, self.cell = idx, name, cell
        self.prev = None
        self.release = release

def bfs_all(maze, sources):
    dist = {s: 0 for s in sources}
    dq = deque(sources)
    while dq:
        c = dq.popleft()
        for n in maze.adj[c]:
            if n not in dist:
                dist[n] = dist[c] + 1; dq.append(n)
    return dist

def bfs_path(maze, start, goal):
    if start == goal: return []
    dq = deque([start])
    parent = {start: None}
    while dq:
        c = dq.popleft()
        if c == goal: break
        for n in maze.adj[c]:
            if n not in parent:
                parent[n] = c; dq.append(n)
    if goal not in parent: return []
    path, cur = [], goal
    while cur != start:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return path

def simulate(maze, pellets, rng, W):
    cells = maze.cells
    cx = W // 2
    free = [c for c in cells if c not in pellets] or list(cells)
    pac_start = min(free, key=lambda c: (c[0]-cx)**2 + (c[1]-5)**2)

    left = set(pellets)
    pac_path = [pac_start]
    eaten = []
    cur_p = pac_start

    while left:
        dist = bfs_all(maze, [cur_p])
        target = min(left, key=lambda p: dist.get(p, 9999))
        step_nodes = bfs_path(maze, cur_p, target)
        for node in step_nodes:
            pac_path.append(node)
            cur_p = node
            if cur_p in left:
                left.discard(cur_p)
                eaten.append((len(pac_path) - 1, cur_p, pellets[cur_p].level))

    total_steps = len(pac_path)
    ghost_starts = [
        min(cells, key=lambda c: (c[0]-cx)**2 + (c[1]-1)**2),
        min(cells, key=lambda c: (c[0]-cx-5)**2 + (c[1]-2)**2),
        min(cells, key=lambda c: (c[0]-cx+5)**2 + (c[1]-2)**2),
        min(cells, key=lambda c: (c[0]-cx)**2 + (c[1]-4)**2),
    ]
    ghosts = [GhostAI(i, GHOSTS[i][0], ghost_starts[i], RELEASE[i]) for i in range(4)]
    g_pos = [[] for _ in ghosts]

    for t in range(total_steps):
        p_now = pac_path[t]
        p_next = pac_path[min(t + 1, total_steps - 1)]

        for g in ghosts:
            g_pos[g.idx].append(g.cell)
            if t < g.release: continue

            all_opts = maze.adj[g.cell]
            opts_no_prev = [n for n in all_opts if n != g.prev] or all_opts
            safe_opts = [n for n in opts_no_prev if n != p_next and n != p_now and (abs(n[0]-p_next[0]) + abs(n[1]-p_next[1]) >= 2)]
            if not safe_opts: safe_opts = [n for n in opts_no_prev if n != p_next and n != p_now]
            if not safe_opts: safe_opts = [n for n in all_opts if n != p_next and n != p_now]
            if not safe_opts: safe_opts = [g.cell]

            if g.name == "blinky":
                dist_p = bfs_all(maze, [p_now])
                nxt = min(safe_opts, key=lambda n: (dist_p.get(n, 999), rng.random()))
            elif g.name == "pinky":
                tg = (p_now[0], 0)
                dist_tg = bfs_all(maze, [tg if tg in cells else min(cells, key=lambda c: (c[0]-tg[0])**2 + c[1]**2)])
                nxt = min(safe_opts, key=lambda n: (dist_tg.get(n, 999), rng.random()))
            elif g.name == "inky":
                tg = (p_now[0], 6)
                dist_tg = bfs_all(maze, [tg if tg in cells else min(cells, key=lambda c: (c[0]-tg[0])**2 + (c[1]-6)**2)])
                nxt = min(safe_opts, key=lambda n: (dist_tg.get(n, 999), rng.random()))
            else:
                nxt = rng.choice(safe_opts)

            g.prev = g.cell
            g.cell = nxt

    return dict(pac_pos=pac_path, g_pos=g_pos, eaten=eaten, n=total_steps - 1)

def pac_d(r, deg):
    a = math.radians(deg)
    return f"M0 0L{num(r*math.cos(a))} {num(-r*math.sin(a))}A{num(r)} {num(r)} 0 1 0 {num(r*math.cos(a))} {num(r*math.sin(a))}Z"

def _skirt(up, down):
    segs = [down, up, down, up, down, up]
    xs = [9, 6, 3, 0, -3, -6, -9]
    d = "M-9 7V0A9 9 0 0 1 9 0V7"
    for i, c in enumerate(segs): d += f"Q{num((xs[i] + xs[i + 1]) / 2)} {c} {xs[i + 1]} 7"
    return d + "Z"

GHOST_A, GHOST_B = _skirt(2.5, 11.5), _skirt(11.5, 2.5)

def build_svg(days, user, title):
    W = max(d.col for d in days) + 1
    cellset = {(d.col, d.row) for d in days}
    pellets = {(d.col, d.row): d for d in days if d.count > 0}
    total = sum(d.count for d in days)
    total_pellets = len(pellets)

    rng = random.Random(7)
    maze = Maze(cellset, rng, 0.20)
    sim = simulate(maze, pellets, rng, W)

    x0, y0 = 58, 114
    gw, gh = W * P - G, 7 * P - G
    Wt, Ht = x0 + gw + 36, 396
    cxp = lambda c: x0 + c * P + S / 2
    cyp = lambda r: y0 + r * P + S / 2

    N = K_READY + sim["n"] + K_END
    T = N * 0.22
    tm = lambda k, off=0.0: (K_READY + k + off) / N
    L = PALETTES["purple"]["levels"]

    defs = [
        f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PALETTES["purple"]["card_a"]}"/><stop offset="1" stop-color="{PALETTES["purple"]["card_b"]}"/></linearGradient>',
        f'<radialGradient id="blob1"><stop offset="0" stop-color="{PALETTES["purple"]["glow"]}" stop-opacity=".35"/><stop offset="1" stop-color="{PALETTES["purple"]["glow"]}" stop-opacity="0"/></radialGradient>',
        f'<radialGradient id="blob2"><stop offset="0" stop-color="{L[2]}" stop-opacity=".25"/><stop offset="1" stop-color="{L[2]}" stop-opacity="0"/></radialGradient>',
        f'<linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{PALETTES["purple"]["accent"]}" stop-opacity=".85"/><stop offset=".5" stop-color="{PALETTES["purple"]["accent"]}" stop-opacity=".15"/><stop offset="1" stop-color="{PALETTES["purple"]["accent"]}" stop-opacity=".65"/></linearGradient>',
        f'<linearGradient id="ttl" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="{L[3]}"/></linearGradient>',
        f'<filter id="glow" filterUnits="userSpaceOnUse" x="0" y="0" width="{Wt}" height="{Ht}"><feGaussianBlur stdDeviation="3.2" result="b1"/><feGaussianBlur stdDeviation="1.2" result="b2"/><feMerge><feMergeNode in="b1"/><feMergeNode in="b2"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        '<pattern id="crt" width="100" height="4" patternUnits="userSpaceOnUse"><line x1="0" y1="0" x2="100" y2="0" stroke="#a855f7" stroke-opacity="0.04" stroke-width="1"/></pattern>',
        '<radialGradient id="pacg" cx=".36" cy=".3" r=".85"><stop offset="0" stop-color="#fffbeb"/><stop offset=".45" stop-color="#fbbf24"/><stop offset="1" stop-color="#d97706"/></radialGradient>',
        '<radialGradient id="halo-pac"><stop offset="0" stop-color="#fbbf24" stop-opacity=".5"/><stop offset="1" stop-color="#fbbf24" stop-opacity="0"/></radialGradient>',
    ]
    for i, c in enumerate(L, 1):
        defs.append(f'<linearGradient id="cg{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{mix(c, "#ffffff", .35)}"/><stop offset=".55" stop-color="{c}"/><stop offset="1" stop-color="{mix(c, "#000000", .32)}"/></linearGradient>')
        halo = f'<rect x="-11.5" y="-11.5" width="23" height="23" rx="7.5" fill="{c}" opacity="{.25 if i >= 3 else .15}"/>'
        defs.append(f'<g id="cell{i}">{halo}<rect x="-8" y="-8" width="16" height="16" rx="4.6" fill="url(#cg{i})"/><rect x="-7.5" y="-7.5" width="15" height="15" rx="4.1" fill="none" stroke="#fff" stroke-opacity=".25"/><rect x="-5.2" y="-6.3" width="10.4" height="1.5" rx=".75" fill="#fff" opacity=".45"/></g>')

    for i, (name, c, lt) in enumerate(GHOSTS):
        defs.append(f'<linearGradient id="gg{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{lt}"/><stop offset=".45" stop-color="{c}"/><stop offset="1" stop-color="{mix(c, "#000000", .35)}"/></linearGradient>')
        defs.append(f'<radialGradient id="halo{i}"><stop offset="0" stop-color="{c}" stop-opacity=".45"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>')

    style = (
        'text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}'
        f'.ti{{font-size:21px;font-weight:800;letter-spacing:.04em;fill:url(#ttl)}}.su{{font-size:12px;fill:{PALETTES["purple"]["muted"]}}}'
        f'.mo,.wd{{font-size:10.5px;fill:{PALETTES["purple"]["muted"]}}}.hl{{font-size:11px;font-weight:700;letter-spacing:.08em;fill:{PALETTES["purple"]["accent"]}}}'
        f'.nu{{font-size:24px;font-weight:800;fill:{PALETTES["purple"]["text"]}}}.lg1{{font-size:11.5px;font-weight:700;fill:{PALETTES["purple"]["text"]}}}'
        f'.lg2{{font-size:10px;fill:{PALETTES["purple"]["muted"]}}}.ar{{font-weight:900;letter-spacing:.22em}}'
        '@media(max-width:760px){.spr{transform:scale(1.25)}}'
        '@media(max-width:640px){.wd,.lg2{display:none}.ti{font-size:27px}.su{font-size:15px}.hl{font-size:14px}.lg1{font-size:14px}.spr{transform:scale(1.55)}}'
        '@media(max-width:440px){.mo,.su{display:none}.ti{font-size:32px}.spr{transform:scale(1.8)}}'
    )

    A = []
    A.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wt} {Ht}" width="{Wt}" height="{Ht}" role="img" shape-rendering="geometricPrecision">')
    A.append(f'<title>{escape(title)}</title><style>{style}</style><defs>{"".join(defs)}</defs>')
    A.append(f'<rect width="{Wt}" height="{Ht}" rx="18" fill="url(#bg)"/><rect width="{Wt}" height="{Ht}" rx="18" fill="url(#crt)"/>')
    A.append(f'<ellipse cx="{num(Wt * .12)}" cy="20" rx="{num(Wt * .3)}" ry="120" fill="url(#blob1)"/><ellipse cx="{num(Wt * .92)}" cy="{Ht - 30}" rx="{num(Wt * .25)}" ry="110" fill="url(#blob2)"/>')
    A.append(f'<rect x=".75" y=".75" width="{Wt - 1.5}" height="{Ht - 1.5}" rx="17.3" fill="none" stroke="url(#bd)" stroke-width="1.6"/>')

    # Header HUD
    A.append(f'<g transform="translate(46 38)"><circle r="16" fill="url(#halo-pac)"/><path fill="url(#pacg)" d="{pac_d(10, 36)}"><animate attributeName="d" dur=".45s" repeatCount="indefinite" values="{pac_d(10, 36)};{pac_d(10, 3)};{pac_d(10, 36)}"/></path><circle cx="17" cy="0" r="2.4" fill="{L[3]}"/><circle cx="26" cy="0" r="2.4" fill="{L[2]}" opacity=".75"/></g>')
    A.append(f'<text class="ti" x="86" y="44">{escape(title)}</text><text class="su" x="86" y="66">@{escape(user)} | ARCHITECT LEVEL | MATRIX XP RUNNER</text>')

    # Grid Dasar
    tiles = "".join(f"M{num(x0 + c * P + 4.6)} {num(y0 + r * P)}h{num(S - 9.2)}a4.6 4.6 0 0 1 4.6 4.6v{num(S - 9.2)}a4.6 4.6 0 0 1 -4.6 4.6h{num(-(S - 9.2))}a4.6 4.6 0 0 1 -4.6 -4.6v{num(-(S - 9.2))}a4.6 4.6 0 0 1 4.6 -4.6z" for (c, r) in sorted(cellset))
    A.append(f'<path d="{tiles}" fill="{PALETTES["purple"]["tile"]}" stroke="{PALETTES["purple"]["tile_edge"]}" stroke-width="1"/>')

    # Labirin Neon
    wp = maze.wall_path(lambda X: x0 + X * P - G / 2, lambda Y: y0 + Y * P - G / 2)
    A.append(f'<g fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="{wp}" stroke="{PALETTES["purple"]["glow"]}" stroke-opacity=".65" stroke-width="4.2" filter="url(#glow)"/><path d="{wp}" stroke="{PALETTES["purple"]["wall"]}" stroke-width="1.8"/></g>')

    # Sel Kontribusi
    eat_time = {cell: tm(t_eat, 0.5) for t_eat, cell, _ in sim["eaten"]}
    for cell, d in sorted(pellets.items()):
        c, r = cell
        te = eat_time.get(cell, None)
        if te is not None:
            t0 = max(0.001, min(0.985, te))
            t1 = min(0.992, t0 + 0.004)
            t2 = min(0.999, t0 + 0.012)
            kts = f"0;{kt(t0)};{kt(t1)};{kt(t2)};1"
            scale_anim = f'<animateTransform attributeName="transform" type="scale" dur="{num(T,3)}s" repeatCount="indefinite" keyTimes="{kts}" values="1;1;1.35;0;0"/>'
            opacity_anim = f'<animate attributeName="opacity" dur="{num(T,3)}s" repeatCount="indefinite" keyTimes="{kts}" values="1;1;1;0;0"/>'
        else:
            scale_anim, opacity_anim = '', ''

        A.append(f'<g transform="translate({num(cxp(c))} {num(cyp(r))})"><g>{scale_anim}{opacity_anim}<use href="#cell{d.level}"/></g></g>')

    # Pergerakan Pac-Man
    pad_arr = lambda arr: [arr[0]]*K_READY + list(arr) + [arr[-1]]*K_END
    px_pos = pad_arr([(cxp(c), cyp(r)) for c, r in sim["pac_pos"]])
    pos_str = ";".join(f"{num(x,1)} {num(y,1)}" for x, y in px_pos)

    p_open, p_shut = pac_d(9.6, 38), pac_d(9.6, 3)
    pac_art = f'<circle r="19" fill="url(#halo-pac)"/><path fill="url(#pacg)" stroke="#fff3b0" stroke-opacity=".7" stroke-width=".9" d="{p_open}"><animate attributeName="d" dur=".32s" repeatCount="indefinite" values="{p_open};{p_shut};{p_open}"/></path><path d="M-5.4 -5.6A7.6 7.6 0 0 1 -0.8 -8" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="1.6" stroke-linecap="round"/><circle cx="1.9" cy="-5.1" r="1.6" fill="#2b1a00"/><circle cx="1.4" cy="-5.7" r=".6" fill="#fff"/>'
    A.append(f'<g transform="translate({num(px_pos[0][0],1)} {num(px_pos[0][1],1)})"><animateTransform attributeName="transform" type="translate" dur="{num(T,3)}s" repeatCount="indefinite" values="{pos_str}"/><g class="spr">{pac_art}</g></g>')

    # Pergerakan 4 Hantu
    for g_i, (name, col, lt) in enumerate(GHOSTS):
        gp = pad_arr([(cxp(c), cyp(r)) for c, r in sim["g_pos"][g_i]])
        g_str = ";".join(f"{num(x,1)} {num(y,1)}" for x, y in gp)
        wave = f'<animate attributeName="d" dur=".48s" repeatCount="indefinite" values="{GHOST_A};{GHOST_B};{GHOST_A}"/>'
        face = '<circle cx="-3.2" cy="-2.4" r="1.8" fill="#fff"/><circle cx="3.2" cy="-2.4" r="1.8" fill="#fff"/><circle cx="-3.4" cy="-2.4" r="1.1" fill="#0f172a"/><circle cx="3.4" cy="-2.4" r="1.1" fill="#0f172a"/>'
        gh_art = f'<circle r="18" fill="url(#halo{g_i})"/><path fill="url(#gg{g_i})" stroke="{lt}" stroke-opacity=".55" stroke-width=".9" d="{GHOST_A}">{wave}</path>{face}'
        A.append(f'<g transform="translate({num(gp[0][0],1)} {num(gp[0][1],1)})"><animateTransform attributeName="transform" type="translate" dur="{num(T,3)}s" repeatCount="indefinite" values="{g_str}"/><g class="spr">{gh_art}</g></g>')

    xr = Wt - 28
    A.append(f'<text class="hl" x="{num(xr)}" y="34" text-anchor="end">TOTAL CONTRIBUTIONS</text><text class="nu" x="{num(xr)}" y="68" text-anchor="end">{total}</text>')

    # Progress Bar Mini-Bar
    bx, bw, by_, bh = x0 - 9, gw + 18, 304, 15
    A.append(f'<text class="hl" x="{bx}" y="{by_ - 11}">CONTRIBUTION ENERGY METER (REAL-TIME HARVESTER)</text>')
    A.append(f'<g transform="translate({bx + bw - 190} {by_ - 20})">'
             f'<rect x="0" y="0" width="9" height="9" rx="2" fill="{L[0]}"/>'
             f'<rect x="14" y="0" width="9" height="9" rx="2" fill="{L[1]}"/>'
             f'<rect x="28" y="0" width="9" height="9" rx="2" fill="{L[2]}"/>'
             f'<rect x="42" y="0" width="9" height="9" rx="2" fill="{L[3]}"/>'
             f'<text class="lg2" x="58" y="8">XP TIERS</text></g>')

    A.append(f'<rect x="{bx}" y="{by_}" width="{bw}" height="{bh}" rx="7.5" fill="#0c1017" stroke="#1f283d" stroke-width="1.2"/>')

    if total_pellets > 0:
        seg_w = bw / total_pellets
        sw = max(2.0, seg_w - 1.2)
        for i in range(total_pellets):
            sx = bx + i * seg_w
            A.append(f'<rect x="{num(sx,2)}" y="{by_ + 2}" width="{num(sw,2)}" height="{bh - 4}" rx="2" fill="#131824" stroke="#1d2436" stroke-width="0.6"/>')

        for k, (t_eat, cell, lvl) in enumerate(sim["eaten"]):
            sx = bx + k * seg_w
            col = L[min(3, max(0, lvl - 1))]
            te = tm(t_eat, 0.5)
            t0 = max(0.001, min(0.994, te))
            t1 = min(0.998, t0 + 0.003)
            anim = f'<animate attributeName="opacity" dur="{num(T,3)}s" repeatCount="indefinite" keyTimes="0;{kt(t0)};{kt(t1)};1" values="0;0;1;1"/>'
            A.append(f'<rect x="{num(sx,2)}" y="{by_ + 2}" width="{num(sw,2)}" height="{bh - 4}" rx="2" fill="{col}" opacity="0">{anim}</rect>')

        head_pos = [bx] * K_READY
        cur_e = 0
        for step in range(sim["n"]):
            while cur_e < total_pellets and sim["eaten"][cur_e][0] <= step: cur_e += 1
            head_pos.append(bx + (cur_e / total_pellets) * bw)
        head_pos += [bx + bw] * K_END
        head_str = ";".join(f"{num(x, 1)} {num(by_ + bh/2, 1)}" for x in head_pos)
        A.append(f'<g transform="translate({bx} {by_ + bh/2})"><animateTransform attributeName="transform" type="translate" dur="{num(T,3)}s" repeatCount="indefinite" values="{head_str}"/><circle r="6" fill="#fbbf24" filter="url(#glow)"/><circle r="3" fill="#ffffff"/></g>')

    A.append("</svg>")
    return "".join(A)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="rjoulfiand-afk")
    ap.add_argument("--title", default="Chomping XP")
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()

    days = load_days(args.user)
    os.makedirs(args.out, exist_ok=True)

    # Generate Pac-Man SVGs
    pacman_svg = build_svg(days, args.user, args.title)
    for fn in ("pacman-contribution-graph-dark.svg", "pacman-contribution-graph.svg"):
        with open(os.path.join(args.out, fn), "w", encoding="utf-8") as f:
            f.write(pacman_svg)
    print(f"[SUCCESS] Pac-Man SVGs berhasil dibuat di {args.out}/")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
