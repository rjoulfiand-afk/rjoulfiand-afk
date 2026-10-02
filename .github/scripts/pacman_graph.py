#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pac-Man Cyberpunk Matrix Arcade Generator
=========================================
Simulator game Pac-Man berbasis kontribusi GitHub asli:
- AI Klasik (Blinky, Pinky, Inky, Clyde) dengan mode Scatter/Chase/Frightened.
- Efek Visual Sangar: Dual-Layer Neon Glow, CRT Scanlines, Particle Echoes,
  dan Odometer counter real-time.
- Standard Library Python murni (100% kompatibel di GitHub Actions).
"""
from __future__ import annotations

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

# --------------------------------------------------------------------------- #
# Palet & Tema Cyberpunk
# --------------------------------------------------------------------------- #
PALETTES = {
    "purple": dict(
        card_a="#0d1117", card_b="#06080d", tile="#121620", tile_edge="#1a2130",
        levels=["#4c1d95", "#7e22ce", "#a855f7", "#e9d5ff"],
        accent="#a855f7", wall="#a855f7", glow="#c084fc", text="#f5f3ff", muted="#94a3b8"
    ),
    "cyan": dict(
        card_a="#0d1117", card_b="#050d12", tile="#111922", tile_edge="#172635",
        levels=["#155e75", "#0891b2", "#22d3ee", "#a5f3fc"],
        accent="#22d3ee", wall="#06b6d4", glow="#38bdf8", text="#ecfeff", muted="#94a3b8"
    ),
}

GHOSTS = [  # nama, warna dasar, warna highlight neon
    ("blinky", "#ff2a2a", "#ff8080"),
    ("pinky", "#ff5ecb", "#ffa8e8"),
    ("inky", "#00e5ff", "#80f2ff"),
    ("clyde", "#ff9100", "#ffc266"),
]

# --------------------------------------------------------------------------- #
# Geometri Grid
# --------------------------------------------------------------------------- #
S, G = 16, 4          # ukuran kotak, celah antar kotak
P = S + G             # pitch
DIRS = [(0, -1), (-1, 0), (0, 1), (1, 0)]   # Atas, Kiri, Bawah, Kanan
ANGLE = {(1, 0): 0, (0, 1): 90, (-1, 0): 180, (0, -1): 270}
PUPIL = {(1, 0): (1.2, 0.0), (-1, 0): (-1.2, 0.0), (0, -1): (0.0, -1.3), (0, 1): (0.0, 1.3)}

K_READY = 18          # intro ticks ("READY!")
K_END = 28            # outro ticks ("LEVEL CLEAR")
FRIGHT_TICKS = 56
BLINK_TICKS = 14
RELEASE = [0, 8, 20, 34]
SCHEDULE = [("s", 26), ("c", 90), ("s", 22), ("c", 100), ("s", 18), ("c", 10 ** 9)]

def num(x, n=2):
    s = f"{x:.{n}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s

def kt(x):
    return num(min(1.0, max(0.0, x)), 5)

def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

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

LEVEL_MAP = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

def http(url, data=None, headers=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def fetch_graphql(user, token):
    query = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
      totalContributions weeks{contributionDays{date weekday contributionCount contributionLevel}}}}}}"""
    body = json.dumps({"query": query, "variables": {"login": user}}).encode()
    raw = http("https://api.github.com/graphql", body, {
        "Authorization": f"bearer {token}", "Content-Type": "application/json",
        "User-Agent": "pacman-contribution-arcade"})
    data = json.loads(raw)
    if data.get("errors") or not data.get("data", {}).get("user"):
        raise RuntimeError(f"GraphQL error: {data.get('errors')}")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = []
    for ci, wk in enumerate(cal["weeks"]):
        for d in wk["contributionDays"]:
            days.append(Day(d["date"], ci, d["weekday"], d["contributionCount"],
                            LEVEL_MAP.get(d["contributionLevel"], 0)))
    return days

def days_from_dates(items):
    items = sorted(items)
    first = dt.date.fromisoformat(items[0][0])
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)
    out = []
    for ds, count, level in items:
        d = dt.date.fromisoformat(ds)
        out.append(Day(ds, (d - start).days // 7, (d.weekday() + 1) % 7, count, level))
    return out

def scrape_contributions(user):
    html = http(f"https://github.com/users/{user}/contributions", headers={"User-Agent": "Mozilla/5.0"})
    tips = {m.group(1): m.group(2) for m in
            re.finditer(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', html)}
    items = []
    for m in re.finditer(r"<td\b([^>]*)>", html):
        a = dict(re.findall(r'([\w:-]+)="([^"]*)"', m.group(1)))
        if "data-date" not in a:
            continue
        mt = re.search(r"(\d+)\s+contribution", tips.get(a.get("id", ""), ""))
        items.append((a["data-date"], int(mt.group(1)) if mt else 0, int(a.get("data-level", 0))))
    if not items:
        raise RuntimeError("Gagal mengambil data kontribusi publik")
    return days_from_dates(items)

def demo_days(seed):
    rng = random.Random(seed)
    end = dt.date.today()
    start = end - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    raw, d, i = [], start, 0
    while d <= end:
        act = 0.35 + 0.25 * math.sin(i / 18.0)
        c = 1 + int(rng.expovariate(1 / 4.0)) if rng.random() < act else 0
        raw.append((d.isoformat(), c))
        d += dt.timedelta(days=1)
        i += 1
    nz = sorted(c for _, c in raw if c)
    q = [nz[int(len(nz) * f)] for f in (0.25, 0.5, 0.75)] if nz else [1, 2, 3]
    return days_from_dates([(ds, c, 0 if c == 0 else 1 + sum(c > t for t in q)) for ds, c in raw])

def load_days(args):
    token = args.token or os.environ.get("GH_API_TOKEN") or os.environ.get("GITHUB_TOKEN")
    order = ["demo"] if args.demo else (["api", "scrape"] if args.source == "auto" else [args.source])
    err = []
    for src in order:
        try:
            if src == "demo":
                return demo_days(args.seed), "demo"
            if src == "api":
                if not token:
                    raise RuntimeError("Token kosong")
                return fetch_graphql(args.user, token), "graphql"
            if src == "scrape":
                return scrape_contributions(args.user), "scrape"
        except Exception as e:
            err.append(f"{src}: {e}")
    raise SystemExit("Gagal memuat kontribusi: " + " | ".join(err))

# --------------------------------------------------------------------------- #
# Generator Labirin
# --------------------------------------------------------------------------- #
class Maze:
    def __init__(self, cells, rng, density):
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
    def _key(a, b):
        return (a, b) if a < b else (b, a)

    def _nb(self, c):
        for d in DIRS:
            n = (c[0] + d[0], c[1] + d[1])
            if n in self.cells:
                yield n

    def _connected(self):
        start = next(iter(self.cells))
        seen, dq = {start}, deque([start])
        while dq:
            c = dq.popleft()
            for n in self._nb(c):
                if n not in seen and self._key(c, n) not in self.blocked:
                    seen.add(n)
                    dq.append(n)
        return len(seen) == len(self.cells)

    def _try(self, a, b):
        k = self._key(a, b)
        if k in self.blocked:
            return False
        for c in (a, b):
            if self.deg[c] - 1 < min(2, self.base[c]):
                return False
        self.blocked.add(k)
        if not self._connected():
            self.blocked.discard(k)
            return False
        self.deg[a] -= 1
        self.deg[b] -= 1
        return True

    def _grow(self, target):
        rng, tries = self.rng, 0
        cells = sorted(self.cells)
        while len(self.blocked) < target and tries < 6000:
            tries += 1
            c = rng.choice(cells)
            length = rng.choice([2, 3, 3, 4, 5])
            vertical = rng.random() < 0.5
            for i in range(length):
                a = (c[0], c[1] + i) if vertical else (c[0] + i, c[1])
                b = (a[0] + 1, a[1]) if vertical else (a[0], a[1] + 1)
                if a not in self.cells or b not in self.cells or not self._try(a, b):
                    break
                self.walls.append(("v" if vertical else "h", a, b))

    def wall_path(self, px, py):
        vs, hs = {}, {}
        for o, a, b in self.walls:
            if o == "v":
                vs.setdefault(a[0] + 1, []).append(a[1])
            else:
                hs.setdefault(a[1] + 1, []).append(a[0])
        d = []
        for X, rows in sorted(vs.items()):
            for lo, hi in _runs(rows):
                d.append(f"M{num(px(X))} {num(py(lo))}V{num(py(hi + 1))}")
        for Y, cols in sorted(hs.items()):
            for lo, hi in _runs(cols):
                d.append(f"M{num(px(lo))} {num(py(Y))}H{num(px(hi + 1))}")
        return "".join(d)

def _runs(vals):
    vals = sorted(set(vals))
    out, lo, prev = [], vals[0], vals[0]
    for v in vals[1:]:
        if v != prev + 1:
            out.append((lo, prev))
            lo = v
        prev = v
    out.append((lo, prev))
    return out

# --------------------------------------------------------------------------- #
# AI Simulasi Permainan
# --------------------------------------------------------------------------- #
class Ghost:
    def __init__(self, idx, name, cell, release, scatter):
        self.idx, self.name, self.cell, self.start = idx, name, cell, cell
        self.prev, self.mode, self.release, self.scatter = None, "n", release, scatter
        self.dir, self.released = (1, 0), False

def bfs_all(maze, sources):
    dist = {s: 0 for s in sources}
    dq = deque(sources)
    while dq:
        c = dq.popleft()
        for n in maze.adj[c]:
            if n not in dist:
                dist[n] = dist[c] + 1
                dq.append(n)
    return dist

def phase_at(t):
    acc = 0
    for ph, dur in SCHEDULE:
        acc += dur
        if t < acc:
            return ph
    return "c"

def simulate(maze, pellets, power, rng, W):
    cells = maze.cells
    cx = W // 2

    def nearest(target, used, pool):
        best = None
        for c in pool:
            if c in used:
                continue
            d = (c[0] - target[0]) ** 2 + (c[1] - target[1]) ** 2
            if best is None or (d, c) < best:
                best = (d, c)
        return best[1]

    free = [c for c in cells if c not in pellets] or list(cells)
    used = set()
    pac = nearest((cx, 5), used, free)
    used.add(pac)
    offs = [(0, 2), (-1, 3), (1, 3), (0, 3)]
    corners = [(W + 2, -2), (-2, -2), (W + 2, 9), (-2, 9)]
    ghosts = []
    for i, (name, _, _) in enumerate(GHOSTS):
        c = nearest((cx + offs[i][0], offs[i][1]), used, cells)
        used.add(c)
        ghosts.append(Ghost(i, name, c, RELEASE[i], corners[i]))
    home = nearest((cx, 3), set(), cells)
    dist_home = bfs_all(maze, [home])

    left = set(pellets)
    pdir, power_timer, chain, idle, force_scatter = (1, 0), 0, 0, 0, -1
    last_eat, last_trig = 0, -999

    pac_pos, pac_dirs = [], []
    g_pos = [[] for _ in ghosts]
    g_modes = [[] for _ in ghosts]
    g_dirs = [[] for _ in ghosts]
    eaten, popups = [], []
    blinky = ghosts[0]
    held = set()

    min_ticks = 0 if pellets else 60
    for t in range(4000):
        if not left and t >= min_ticks:
            break
        if power_timer > 0:
            power_timer -= 1
            if power_timer == 0:
                for g in ghosts:
                    if g.mode == "f":
                        g.mode = "n"
        if left and t - last_eat >= 26 and t - last_trig >= 56:
            force_scatter, last_trig = t + 30, t
        if left and t - last_eat >= 120 and power_timer == 0:
            power_timer, chain, last_eat = FRIGHT_TICKS, 0, t
            for g in ghosts:
                if g.mode == "n" and g.released:
                    g.mode, g.prev = "f", None

        pac_pos.append(pac)
        for g in ghosts:
            g_pos[g.idx].append(g.cell)
            g_modes[g.idx].append("b" if g.mode == "f" and power_timer <= BLINK_TICKS else g.mode)

        # Navigasi Pac-Man
        dangerous = [g for g in ghosts if g.mode == "n"]
        gd = bfs_all(maze, [g.cell for g in dangerous]) if dangerous else {}
        def gdist(c):
            return gd.get(c, 99)

        frightened = [g for g in ghosts if g.mode == "f"]
        non_power = left - power

        def cost(n):
            c = 1.0
            d = gdist(n)
            if d <= 3:
                c += (60, 30, 9, 2.5)[d]
            if n in power and n in left:
                c += 14
            return c

        dist, first = {pac: 0.0}, {}
        pq = [(0.0, pac)]
        while pq:
            d, c = heapq.heappop(pq)
            if d > dist[c]:
                continue
            for n in maze.adj[c]:
                nd = d + cost(n)
                if nd < dist.get(n, 1e9):
                    dist[n] = nd
                    first[n] = n if c == pac else first[c]
                    heapq.heappush(pq, (nd, n))

        rev = (pac[0] - pdir[0], pac[1] - pdir[1])
        fwd = (pac[0] + pdir[0], pac[1] + pdir[1])
        cands = []

        def add(score, cell):
            f = first.get(cell)
            if f is None or gdist(f) < 2:
                return
            if f == rev:
                score += 0.6
            elif f == fwd:
                score -= 0.15
            cands.append((score, f))

        if frightened and power_timer > 6:
            for g in frightened:
                if g.cell in dist and dist[g.cell] <= min(10, power_timer * 0.9):
                    add(dist[g.cell] - 4, g.cell)
        targets = non_power if non_power else (left & power)
        for p in targets:
            if p in dist:
                add(dist[p], p)
        if non_power and dangerous and gdist(pac) <= 6:
            for p in left & power:
                if p in dist and dist[p] <= 12:
                    add(dist[p] - 7, p)

        if cands:
            pac_new = min(cands, key=lambda x: x[0])[1]
        else:
            safe = [n for n in maze.adj[pac] if gdist(n) >= 2]
            pac_new = max(safe, key=lambda n: (gdist(n), n == fwd)) if safe else pac
        moved = pac_new != pac
        pac_old = pac
        if moved:
            pdir = (pac_new[0] - pac[0], pac_new[1] - pac[1])
            idle = 0
        else:
            idle += 1
            if idle >= 5:
                force_scatter, idle = t + 24, 0

        # Memakan Hantu dalam Mode Takut
        held.clear()
        def eat_ghost(g):
            nonlocal chain
            g.mode, g.prev = "e", None
            held.add(g.idx)
            pts = 200 * (2 ** min(chain, 3))
            chain += 1
            popups.append((t, pac_new, pts))

        for g in ghosts:
            if g.mode == "f" and g.cell == pac_new:
                eat_ghost(g)

        # Navigasi Hantu
        phase = "s" if force_scatter > t else phase_at(t)
        for g in ghosts:
            old = g.cell
            if g.idx in held:
                g_dirs[g.idx].append(g.dir)
                continue
            if g.mode == "n" and not g.released:
                if t >= g.release:
                    g.released = True
                else:
                    g_dirs[g.idx].append(g.dir)
                    continue
            nxt = None
            if g.mode == "e":
                if g.cell == home:
                    if abs(home[0] - pac_new[0]) + abs(home[1] - pac_new[1]) >= 3:
                        g.mode, g.prev = "n", None
                else:
                    nxt = min(maze.adj[g.cell], key=lambda n: dist_home[n])
            elif g.mode == "f":
                if t % 2 == 0:
                    opts = [n for n in maze.adj[g.cell] if n != g.prev] or maze.adj[g.cell]
                    nxt = rng.choice(opts)
            else:
                if (t + 2 * g.idx) % 6 != 5:
                    banned = {pac_new} | {o.cell for o in ghosts if o is not g}
                    if moved:
                        banned |= {pac_old} if (g.cell[0] - pac_old[0], g.cell[1] - pac_old[1]) not in [(-pdir[0], -pdir[1])] else set()
                    opts = [n for n in maze.adj[g.cell] if n != g.prev and n not in banned] or [n for n in maze.adj[g.cell] if n not in banned]
                    if opts:
                        if phase == "s":
                            tg = g.scatter
                        elif g.name == "blinky":
                            tg = pac_new
                        elif g.name == "pinky":
                            tg = (pac_new[0] + 4 * pdir[0], pac_new[1] + 4 * pdir[1])
                        elif g.name == "inky":
                            px_, py_ = pac_new[0] + 2 * pdir[0], pac_new[1] + 2 * pdir[1]
                            tg = (2 * px_ - blinky.cell[0], 2 * py_ - blinky.cell[1])
                        else:
                            far = (pac_new[0] - g.cell[0]) ** 2 + (pac_new[1] - g.cell[1]) ** 2 > 64
                            tg = pac_new if far else g.scatter
                        nxt = min(opts, key=lambda n: (n[0] - tg[0]) ** 2 + (n[1] - tg[1]) ** 2)
            if nxt is not None and nxt != old:
                g.prev, g.cell = old, nxt
                g.dir = (nxt[0] - old[0], nxt[1] - old[1])
            g_dirs[g.idx].append(g.dir)

        for g in ghosts:
            if g.mode == "f" and g.cell == pac_new:
                eat_ghost(g)

        pac = pac_new
        pac_dirs.append(pdir)
        if pac in left:
            left.discard(pac)
            last_eat = t
            eaten.append((t, pac))
            if pac in power:
                power_timer, chain = FRIGHT_TICKS, 0
                for g in ghosts:
                    if g.mode == "n" and g.released:
                        g.mode, g.prev = "f", None
    else:
        raise RuntimeError("Simulasi melebihi batas waktu")

    pac_pos.append(pac)
    for g in ghosts:
        g_pos[g.idx].append(g.cell)
    return dict(pac_pos=pac_pos, pac_dirs=pac_dirs, g_pos=g_pos, g_modes=g_modes, g_dirs=g_dirs,
                eaten=eaten, popups=popups, home=home, n=len(pac_dirs))

# --------------------------------------------------------------------------- #
# SMIL Helpers & Bentuk Vektor
# --------------------------------------------------------------------------- #
def rle(seq, N):
    kts, vals = [0.0], [seq[0]]
    for i in range(1, N):
        if seq[i] != seq[i - 1]:
            kts.append(i / N)
            vals.append(seq[i])
    return kts, vals

def discrete(attr, seq, N, T, transform=None):
    kts, vals = rle(seq, N)
    if len(vals) == 1:
        return ""
    tag = "animateTransform" if transform else "animate"
    ttype = f' type="{transform}"' if transform else ""
    return (f'<{tag} attributeName="{attr}"{ttype} calcMode="discrete" dur="{num(T, 3)}s" '
            f'repeatCount="indefinite" keyTimes="{";".join(kt(k) for k in kts)}" values="{";".join(vals)}"/>')

def pad(arr, head, tail):
    return [arr[0]] * head + list(arr) + [arr[-1]] * tail

def pac_d(r, deg):
    a = math.radians(deg)
    x, y = r * math.cos(a), r * math.sin(a)
    return f"M0 0L{num(x)} {num(-y)}A{num(r)} {num(r)} 0 1 0 {num(x)} {num(y)}Z"

def _skirt(up, down):
    segs = [down, up, down, up, down, up]
    xs = [9, 6, 3, 0, -3, -6, -9]
    d = "M-9 7V0A9 9 0 0 1 9 0V7"
    for i, c in enumerate(segs):
        d += f"Q{num((xs[i] + xs[i + 1]) / 2)} {c} {xs[i + 1]} 7"
    return d + "Z"

GHOST_A = _skirt(2.5, 11.5)
GHOST_B = _skirt(11.5, 2.5)

def rrect(x, y, w, h, r):
    return (f"M{num(x + r)} {num(y)}h{num(w - 2 * r)}a{num(r)} {num(r)} 0 0 1 {num(r)} {num(r)}"
            f"v{num(h - 2 * r)}a{num(r)} {num(r)} 0 0 1 {num(-r)} {num(r)}h{num(-(w - 2 * r))}"
            f"a{num(r)} {num(r)} 0 0 1 {num(-r)} {num(-r)}v{num(-(h - 2 * r))}a{num(r)} {num(r)} 0 0 1 {num(r)} {num(-r)}z")

def pick_power(pellets, W):
    out = []
    for q in range(4):
        lo, hi = q * W / 4, (q + 1) * W / 4
        # Cari level >= 2, jika tidak ada fallback ke level >= 1
        pool = [(d.count, -c[0], c) for c, d in pellets.items() if lo <= c[0] < hi and d.level >= 2]
        if not pool:
            pool = [(d.count, -c[0], c) for c, d in pellets.items() if lo <= c[0] < hi and d.level >= 1]
        if pool:
            out.append(max(pool)[2])
    return set(out)

# --------------------------------------------------------------------------- #
# Renderer SVG Utama (Dengan Efek Neon Glow & Cyberpunk HUD)
# --------------------------------------------------------------------------- #
def build_svg(days, args):
    pal = PALETTES[args.theme]
    W = max(d.col for d in days) + 1
    cellset = {(d.col, d.row) for d in days}
    for d in days:
        if d.count > 0 and d.level == 0:
            d.level = 1
    pellets = {(d.col, d.row): d for d in days if d.count > 0}
    total = sum(d.count for d in days)

    x0, y0 = 58, 114
    gw, gh = W * P - G, 7 * P - G
    Wt, Ht = x0 + gw + 36, 388
    cxp = lambda c: x0 + c * P + S / 2
    cyp = lambda r: y0 + r * P + S / 2

    power = pick_power(pellets, W)
    for attempt in range(12):
        rng = random.Random(args.seed + attempt * 101)
        maze = Maze(cellset, rng, args.density)
        try:
            sim = simulate(maze, pellets, power, rng, W)
            break
        except RuntimeError:
            pass
    else:
        raise SystemExit("Simulasi gagal setelah 12 percobaan")

    Np = sim["n"]
    N = K_READY + Np + K_END
    tick = min(args.tick, args.max_duration / N)
    tick = max(tick, 0.055)
    T = N * tick

    def tm(k, off=0.0):
        return (K_READY + k + off) / N

    L = pal["levels"]
    defs = []
    # Gradient background & glow lighting
    defs.append(f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{pal["card_a"]}"/>'
                f'<stop offset="1" stop-color="{pal["card_b"]}"/></linearGradient>')
    defs.append(f'<radialGradient id="blob1"><stop offset="0" stop-color="{pal["glow"]}" stop-opacity=".35"/>'
                f'<stop offset="1" stop-color="{pal["glow"]}" stop-opacity="0"/></radialGradient>')
    defs.append(f'<radialGradient id="blob2"><stop offset="0" stop-color="{L[2]}" stop-opacity=".25"/>'
                f'<stop offset="1" stop-color="{L[2]}" stop-opacity="0"/></radialGradient>')
    defs.append(f'<linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{pal["accent"]}" stop-opacity=".85"/>'
                f'<stop offset=".5" stop-color="{pal["accent"]}" stop-opacity=".15"/>'
                f'<stop offset="1" stop-color="{pal["accent"]}" stop-opacity=".65"/></linearGradient>')
    defs.append(f'<linearGradient id="ttl" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffffff"/>'
                f'<stop offset="1" stop-color="{L[3]}"/></linearGradient>')

    # Dual-layer neon glow filter
    defs.append(f'<filter id="glow" filterUnits="userSpaceOnUse" x="0" y="0" width="{Wt}" height="{Ht}">'
                f'<feGaussianBlur stdDeviation="3.2" result="blur1"/><feGaussianBlur stdDeviation="1.2" result="blur2"/>'
                f'<feMerge><feMergeNode in="blur1"/><feMergeNode in="blur2"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')

    # Tekstur CRT Cyber Scanline
    defs.append('<pattern id="crt" width="100" height="4" patternUnits="userSpaceOnUse">'
                '<line x1="0" y1="0" x2="100" y2="0" stroke="#a855f7" stroke-opacity="0.04" stroke-width="1"/></pattern>')

    for i, c in enumerate(L, 1):
        defs.append(f'<linearGradient id="cg{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{mix(c, "#ffffff", .35)}"/>'
                    f'<stop offset=".55" stop-color="{c}"/><stop offset="1" stop-color="{mix(c, "#000000", .32)}"/></linearGradient>')
        halo = f'<rect x="-11.5" y="-11.5" width="23" height="23" rx="7.5" fill="{c}" opacity="{.25 if i >= 3 else .15}"/>'
        defs.append(f'<g id="cell{i}">{halo}<rect x="-8" y="-8" width="16" height="16" rx="4.6" fill="url(#cg{i})"/>'
                    f'<rect x="-7.5" y="-7.5" width="15" height="15" rx="4.1" fill="none" stroke="#fff" stroke-opacity=".25"/>'
                    f'<rect x="-5.2" y="-6.3" width="10.4" height="1.5" rx=".75" fill="#fff" opacity=".45"/></g>')

    defs.append('<radialGradient id="pacg" cx=".36" cy=".3" r=".85"><stop offset="0" stop-color="#fffbeb"/>'
                '<stop offset=".45" stop-color="#fbbf24"/><stop offset="1" stop-color="#d97706"/></radialGradient>')
    defs.append('<radialGradient id="halo-pac"><stop offset="0" stop-color="#fbbf24" stop-opacity=".48"/><stop offset="1" stop-color="#fbbf24" stop-opacity="0"/></radialGradient>')
    defs.append('<linearGradient id="gfright" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#60a5fa"/><stop offset="1" stop-color="#1e40af"/></linearGradient>')

    for i, (name, c, lt) in enumerate(GHOSTS):
        defs.append(f'<linearGradient id="gg{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{lt}"/><stop offset=".45" stop-color="{c}"/>'
                    f'<stop offset="1" stop-color="{mix(c, "#000000", .35)}"/></linearGradient>')
        defs.append(f'<radialGradient id="halo{i}"><stop offset="0" stop-color="{c}" stop-opacity=".45"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>')
    defs.append('<clipPath id="odo"><rect x="0" y="-21" width="15" height="27"/></clipPath>')

    style = (
        'text{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace}'
        f'.ti{{font-size:21px;font-weight:800;letter-spacing:.04em;fill:url(#ttl)}}.su{{font-size:12px;fill:{pal["muted"]}}}'
        f'.mo,.wd{{font-size:10.5px;fill:{pal["muted"]}}}.hl{{font-size:11px;font-weight:700;letter-spacing:.08em;fill:{pal["accent"]}}}'
        f'.nu{{font-size:24px;font-weight:800;fill:{pal["text"]}}}.lg1{{font-size:11.5px;font-weight:700;fill:{pal["text"]}}}'
        f'.lg2{{font-size:10.5px;fill:{pal["muted"]}}}.ar{{font-weight:900;letter-spacing:.22em}}'
        '@media (max-width:760px){.spr{transform:scale(1.25)}}'
        '@media (max-width:640px){.wd,.lg2{display:none}.ti{font-size:27px}.su{font-size:15px}.hl{font-size:14px}.lg1{font-size:14px}.spr{transform:scale(1.55)}}'
        '@media (max-width:440px){.mo,.su{display:none}.ti{font-size:32px}.spr{transform:scale(1.8)}}'
    )

    out = []
    A = out.append
    A(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {Wt} {Ht}" '
      f'width="{Wt}" height="{Ht}" role="img" aria-labelledby="t d" shape-rendering="geometricPrecision">')
    A(f'<title id="t">{escape(args.title)}</title><desc id="d">Pac-Man chomping {len(pellets)} active days '
      f'({total} total commits) for @{escape(args.user)}</desc>')
    A(f'<style>{style}</style><defs>{"".join(defs)}</defs>')

    # Kartu dasar & CRT scanlines
    A(f'<rect width="{Wt}" height="{Ht}" rx="18" fill="url(#bg)"/>')
    A(f'<rect width="{Wt}" height="{Ht}" rx="18" fill="url(#crt)"/>')
    A(f'<ellipse cx="{num(Wt * .12)}" cy="20" rx="{num(Wt * .30)}" ry="120" fill="url(#blob1)"/>')
    A(f'<ellipse cx="{num(Wt * .92)}" cy="{Ht - 30}" rx="{num(Wt * .25)}" ry="110" fill="url(#blob2)"/>')
    A(f'<rect x=".75" y=".75" width="{Wt - 1.5}" height="{Ht - 1.5}" rx="17.3" fill="none" stroke="url(#bd)" stroke-width="1.6"/>')

    # Header & Arcade HUD Badge
    A(f'<g transform="translate(46 38)"><circle r="16" fill="url(#halo-pac)"/><path fill="url(#pacg)" d="{pac_d(10, 36)}">'
      f'<animate attributeName="d" dur=".45s" repeatCount="indefinite" values="{pac_d(10, 36)};{pac_d(10, 3)};{pac_d(10, 36)}"/></path>'
      f'<circle cx="17" cy="0" r="2.4" fill="{L[3]}"/><circle cx="26" cy="0" r="2.4" fill="{L[2]}" opacity=".75"/></g>')
    A(f'<text class="ti" x="86" y="44">{escape(args.title)}</text>')
    A(f'<text class="su" x="86" y="66">@{escape(args.user)} &bull; ARCHITECT LEVEL &bull; MATRIX XP RUNNER</text>')

    # Label Bulan & Hari
    by_col = {}
    for d in days:
        by_col.setdefault(d.col, d.date)
    last_col, last_m = -9, None
    mnames = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    for c in range(W):
        if c not in by_col:
            continue
        m = int(by_col[c][5:7])
        if m != last_m and c - last_col >= 3:
            A(f'<text class="mo" x="{num(x0 + c * P)}" y="{y0 - 17}">{mnames[m - 1]}</text>')
            last_col = c
        last_m = m
    for r, nm in ((1, "Sen"), (3, "Rab"), (5, "Jum")):
        A(f'<text class="wd" x="{x0 - 16}" y="{num(cyp(r) + 3.6)}" text-anchor="end">{nm}</text>')

    # Dinding Labirin Neon Berpendar
    A(f'<g filter="url(#glow)" fill="none"><rect x="{x0 - 9}" y="{y0 - 9}" width="{gw + 18}" height="{gh + 18}" rx="13" stroke="{pal["accent"]}" stroke-width="2.2"/>'
      f'<rect x="{x0 - 4.5}" y="{y0 - 4.5}" width="{gw + 9}" height="{gh + 9}" rx="9" stroke="{pal["accent"]}" stroke-opacity=".4" stroke-width="1"/></g>')
    wp = maze.wall_path(lambda X: x0 + X * P - G / 2, lambda Y: y0 + Y * P - G / 2)
    flash_t0 = tm(Np, 2)
    fl_k = [0.0] + [flash_t0 + i * (1.6 / N) for i in range(1, 9)]
    flash_vals = [pal["wall"]] + [("#ffffff" if i % 2 else pal["wall"]) for i in range(1, 9)]
    flash = (f'<animate attributeName="stroke" calcMode="discrete" dur="{num(T, 3)}s" repeatCount="indefinite" '
             f'keyTimes="{";".join(kt(k) for k in fl_k)}" values="{";".join(flash_vals)}"/>')
    A(f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">'
      f'<path d="{wp}" stroke="{pal["glow"]}" stroke-opacity=".65" stroke-width="4.2" filter="url(#glow)"/>'
      f'<path d="{wp}" stroke="{pal["wall"]}" stroke-width="1.8">{flash}</path></g>')

    # Petak Dasar
    tiles = "".join(rrect(x0 + c * P, y0 + r * P, S, S, 4.6) for (c, r) in sorted(cellset))
    A(f'<path d="{tiles}" fill="{pal["tile"]}" stroke="{pal["tile_edge"]}" stroke-width="1"/>')

    # Sel Kontribusi
    eat_time = {}
    level_events = {1: [], 2: [], 3: [], 4: []}
    counter_events = []
    cum = 0
    for (k, cell) in sim["eaten"]:
        d = pellets[cell]
        te = tm(k, 0.5)
        eat_time[cell] = te
        level_events[d.level].append(te)
        cum += d.count
        counter_events.append((te, cum))
    p1, p2 = 0.9 / N, 2.3 / N
    cells_svg = []
    for cell, d in sorted(pellets.items()):
        c, r = cell
        te = eat_time[cell]
        s = (1 + c * (K_READY - 8) / W) / N
        dd = 4 / N
        kts = [0, s, s + dd, te, te + p1, te + p2, 1]
        sc = "0.2;0.2;1;1;1.4;0;0"
        op = "0;0;1;1;1;0;0"
        ring = ""
        pulse = ""
        if cell in power:
            ring = (f'<rect x="-9" y="-9" width="18" height="18" rx="5.5" fill="none" stroke="{L[3]}" stroke-width="1.8">'
                    f'<animate attributeName="opacity" values=".9;0" dur="1.2s" repeatCount="indefinite"/>'
                    f'<animateTransform attributeName="transform" type="scale" values="1;1.95" dur="1.2s" repeatCount="indefinite"/></rect>')
            pulse = ('<animateTransform attributeName="transform" type="scale" values="1;1.18;1" dur=".85s" repeatCount="indefinite"/>')
        kts_s = ";".join(kt(x) for x in kts)
        cells_svg.append(
            f'<g transform="translate({num(cxp(c))} {num(cyp(r))})"><g>'
            f'<animateTransform attributeName="transform" type="scale" dur="{num(T, 3)}s" repeatCount="indefinite" keyTimes="{kts_s}" values="{sc}"/>'
            f'<animate attributeName="opacity" dur="{num(T, 3)}s" repeatCount="indefinite" keyTimes="{kts_s}" values="{op}"/>'
            f'{ring}<g>{pulse}<use href="#cell{d.level}"/></g></g></g>')
    A("".join(cells_svg))

    # Aktor (Pacman & Monsters)
    DUR = num(T, 3)
    def posvals(arr):
        return ";".join(f"{num(x, 1)} {num(y, 1)}" for x, y in arr)

    def lagged(arr, k):
        return ([arr[0]] * k + list(arr))[:len(arr)]

    def mover(vals, inner, init):
        return (f'<g transform="translate({num(init[0], 1)} {num(init[1], 1)})">'
                f'<animateTransform attributeName="transform" type="translate" dur="{DUR}s" repeatCount="indefinite" values="{vals}"/>{inner}</g>')

    # Pac-Man dengan highlight 3D & mata
    px_pos = pad([(cxp(c), cyp(r)) for c, r in sim["pac_pos"]], K_READY, K_END)
    rot = pad([str(0 if d == (-1, 0) else ANGLE[d]) for d in sim["pac_dirs"]], K_READY, K_END)
    flip = pad(["-1 1" if d == (-1, 0) else "1 1" for d in sim["pac_dirs"]], K_READY, K_END)
    p_open, p_shut = pac_d(9.6, 38), pac_d(9.6, 3)
    pac_core = (f'<circle r="19" fill="url(#halo-pac)"/><g>{discrete("transform", rot, N, T, "rotate")}'
                f'<g>{discrete("transform", flip, N, T, "scale")}'
                f'<path fill="url(#pacg)" stroke="#fff3b0" stroke-opacity=".7" stroke-width=".9" d="{p_open}">'
                f'<animate attributeName="d" dur=".24s" repeatCount="indefinite" values="{p_open};{p_shut};{p_open}"/></path>'
                f'<path d="M-5.4 -5.6A7.6 7.6 0 0 1 -0.8 -8" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="1.6" stroke-linecap="round"/>'
                f'<circle cx="1.9" cy="-5.1" r="1.6" fill="#2b1a00"/><circle cx="1.4" cy="-5.7" r=".6" fill="#fff"/></g></g>')
    pac_echo = "".join(mover(posvals(lagged(px_pos, k)), f'<circle r="{r}" fill="#fbbf24" opacity="{o}"/>', px_pos[0])
                       for k, r, o in ((5, 4.2, .09), (3, 5.6, .16), (1, 7.2, .24)))
    pacs = mover(posvals(px_pos), f'<g class="spr">{pac_core}</g>', px_pos[0])

    # Monsters dengan siluet khusus yang sangar
    def ghost_extras(name, col, lt):
        dark = mix(col, "#000000", .45)
        edge = f'stroke="{lt}" stroke-opacity=".7" stroke-width=".9" stroke-linejoin="round"'
        if name == "blinky":   # Iblis: Tanduk tajam + alis merah menyala
            return (f'<path d="M-7.6 -5L-9.2 -14.2L-2.6 -8.6ZM7.6 -5L9.2 -14.2L2.6 -8.6Z" fill="{dark}" {edge}/>',
                    '<path d="M-7.2 -6.8L-1.2 -4M7.2 -6.8L1.2 -4" stroke="#ff0000" stroke-width="2" stroke-linecap="round" fill="none"/>')
        if name == "pinky":    # Cyber-Feline: Telinga neon kucing
            return (f'<path d="M-8.8 -3L-8 -13L-1.4 -7.6ZM8.8 -3L8 -13L1.4 -7.6Z" fill="{col}" {edge}/>'
                    '<path d="M-7.4 -5.4L-7.1 -10.2L-3.8 -7.6ZM7.4 -5.4L7.1 -10.2L3.8 -7.6Z" fill="#ffe4f8"/>', "")
        if name == "inky":     # Cyber-Alien: Antena pemancar menyala
            return (f'<path d="M0 -8L0 -14.2" stroke="{col}" stroke-width="1.8" stroke-linecap="round"/>'
                    f'<circle cy="-15.4" r="2.6" fill="{lt}"><animate attributeName="r" values="2.4;3.4;2.4" dur=".8s" repeatCount="indefinite"/>'
                    f'<animate attributeName="opacity" values="1;.4;1" dur=".8s" repeatCount="indefinite"/></circle>', "")
        return (f'<path d="M-5.6 -7L-4.6 -14.4L-1.8 -8.8L0 -16L1.8 -8.8L4.6 -14.4L5.6 -7Z" fill="{lt}" {edge}/>', "")

    face = ('<circle cx="-3.2" cy="-2.4" r="1.9" fill="{c}"/><circle cx="3.2" cy="-2.4" r="1.9" fill="{c}"/>'
            '<path d="M-6 4.4l1.9-2l1.9 2l1.9-2l1.9 2l1.9-2l1.9 2" fill="none" stroke="{c}" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round"/>')
    wave = (f'<animate attributeName="d" dur=".52s" repeatCount="indefinite" values="{GHOST_A};{GHOST_B};{GHOST_A}"/>')
    gloss = '<path d="M-6.6 -4.4A7 7 0 0 1 -1.2 -8.1" fill="none" stroke="#fff" stroke-opacity=".65" stroke-width="1.6" stroke-linecap="round"/>'

    ghost_svgs, ghost_echo = [], []
    for g_i, (name, col, lt) in enumerate(GHOSTS):
        gp = pad([(cxp(c), cyp(r)) for c, r in sim["g_pos"][g_i]], K_READY, K_END)
        modes = pad(sim["g_modes"][g_i], K_READY, K_END)
        dirs = pad(sim["g_dirs"][g_i], K_READY, K_END)
        vn = ["1" if m == "n" else "0" for m in modes]
        vf = ["1" if m in "fb" else "0" for m in modes]
        vb = ["1" if m == "b" else "0" for m in modes]
        ve = ["1" if m in "ne" else "0" for m in modes]
        pup = [f"{num(PUPIL[d][0])} {num(PUPIL[d][1])}" for d in dirs]
        behind, front = ghost_extras(name, col, lt)
        bob = (f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -1.2;0 0" dur=".52s" '
               f'begin="-{num(g_i * .13)}s" repeatCount="indefinite"/>')
        art = (
            f'<g class="spr"><g>{bob}'
            f'<circle r="18" fill="url(#halo{g_i})">{discrete("opacity", vn, N, T)}</circle>'
            f'<g opacity="{vn[0]}">{discrete("opacity", vn, N, T)}{behind}'
            f'<path fill="url(#gg{g_i})" stroke="{lt}" stroke-opacity=".55" stroke-width=".9" d="{GHOST_A}">{wave}</path>{gloss}</g>'
            f'<g opacity="{vf[0]}">{discrete("opacity", vf, N, T)}<circle r="16" fill="#3b82f6" opacity=".25"/>'
            f'<path fill="url(#gfright)" stroke="#93c5fd" stroke-opacity=".7" stroke-width=".9" d="{GHOST_A}">{wave}</path>{face.format(c="#ffe6c7")}</g>'
            f'<g opacity="{vb[0]}">{discrete("opacity", vb, N, T)}<path fill="#f8fafc" d="{GHOST_A}">{wave}'
            f'<animate attributeName="opacity" calcMode="discrete" dur=".32s" repeatCount="indefinite" values="1;0"/></path>{face.format(c="#ef4444")}</g>'
            f'<g opacity="{ve[0]}">{discrete("opacity", ve, N, T)}<ellipse cx="-3.4" cy="-2.2" rx="2.9" ry="3.5" fill="#fff"/>'
            f'<ellipse cx="3.4" cy="-2.2" rx="2.9" ry="3.5" fill="#fff"/>'
            f'<g transform="translate({pup[0].split()[0]} {pup[0].split()[1]})">{discrete("transform", pup, N, T, "translate")}'
            f'<circle cx="-3.4" cy="-2.2" r="1.8" fill="#0f172a"/><circle cx="3.4" cy="-2.2" r="1.8" fill="#0f172a"/>'
            f'<circle cx="-3.9" cy="-2.9" r=".6" fill="#fff"/><circle cx="2.9" cy="-2.9" r=".6" fill="#fff"/></g></g>'
            f'<g opacity="{vn[0]}">{discrete("opacity", vn, N, T)}{front}</g>'
            f'</g></g>')
        ghost_svgs.append(mover(posvals(gp), art, gp[0]))
        echo_op = [".24" if m == "n" else "0" for m in modes]
        ghost_echo.append(mover(posvals(lagged(gp, 2)),
                                f'<circle r="6.8" fill="{col}" opacity="{echo_op[0]}">{discrete("opacity", echo_op, N, T)}</circle>', gp[0]))

    fade = (f'<animate attributeName="opacity" dur="{DUR}s" repeatCount="indefinite" '
            f'keyTimes="0;{kt(2 / N)};{kt(1 - 2.5 / N)};1" values="0;1;1;0"/>')
    A(f'<g>{fade}{pac_echo}{"".join(ghost_echo)}{"".join(ghost_svgs)}{pacs}</g>')

    # Skor Floating Text Saat Makan Hantu
    pop = []
    for (k, cell, pts) in sim["popups"]:
        c, r = cell
        t0, t1 = tm(k, 1), tm(k, 11)
        x, y = cxp(c), cyp(r)
        pop.append(
            f'<text x="0" y="0" text-anchor="middle" font-size="12" font-weight="900" fill="#22d3ee" stroke="#050d18" stroke-width="3.5" paint-order="stroke" opacity="0">'
            f'<animate attributeName="opacity" calcMode="discrete" dur="{num(T, 3)}s" repeatCount="indefinite" keyTimes="0;{kt(t0)};{kt(t1)}" values="0;1;0"/>'
            f'<animateTransform attributeName="transform" type="translate" dur="{num(T, 3)}s" repeatCount="indefinite" keyTimes="0;{kt(t0)};{kt(t1)};1" '
            f'values="{num(x)} {num(y)};{num(x)} {num(y)};{num(x)} {num(y - 14)};{num(x)} {num(y - 14)}"/>+{pts}</text>')
    A("".join(pop))

    # Banner READY & LEVEL CLEAR
    gx, gy = x0 + gw / 2, y0 + gh / 2
    def banner(label, color, w, kts_, vals_):
        return (f'<g opacity="0"><animate attributeName="opacity" calcMode="discrete" dur="{num(T, 3)}s" repeatCount="indefinite" '
                f'keyTimes="{";".join(kt(k) for k in kts_)}" values="{";".join(vals_)}"/>'
                f'<rect x="{num(gx - w / 2)}" y="{num(gy - 21)}" width="{w}" height="42" rx="21" fill="#060913" fill-opacity=".9" stroke="{color}" stroke-width="1.8"/>'
                f'<text class="ar" x="{num(gx)}" y="{num(gy + 7.5)}" text-anchor="middle" font-size="22" fill="{color}">{label}</text></g>')

    ready_k = [0.0, 3 / N, 5 / N, 7 / N, 9 / N, (K_READY - 1) / N]
    A(banner("READY!", "#facc15", 176, ready_k, ["1", "0", "1", "0", "1", "0"]))
    clear_k = [0.0, tm(Np, 1.5)] + [tm(Np, 1.5 + 4 * i) for i in range(1, 5)]
    A(banner("LEVEL CLEAR", pal["accent"], 266, clear_k[:2] + [clear_k[2]], ["0", "1", "1"]))

    # HUD Odometer Counter
    D = max(3, len(str(total)))
    xr = Wt - 28
    ox = xr - (D * 15 + (D // 3) * 8)
    A(f'<text class="hl" x="{num(xr)}" y="34" text-anchor="end">TOTAL CONTRIBUTIONS</text>')
    odo = [f'<g transform="translate({num(ox)} 68)">']
    ordered, x = [], 0.0
    for p in range(D - 1, -1, -1):
        ordered.append((p, x))
        x += 15
        if p % 3 == 0 and p != 0:
            ordered.append((None, x))
            x += 8
    for p, xx in ordered:
        if p is None:
            odo.append(f'<text class="nu" x="{num(xx + 2)}" y="0" opacity=".6">,</text>')
            continue
        seq, last = [(0.0, 0)], 0
        for te, cu in counter_events:
            dgt = (cu // 10 ** p) % 10
            if dgt != last:
                seq.append((te, dgt))
                last = dgt
        final = (total // 10 ** p) % 10
        digits = "".join(f'<text class="nu" x="7.5" y="{k * 28}" text-anchor="middle">{k}</text>' for k in range(10))
        anim = ""
        if len(seq) > 1:
            anim = (f'<animateTransform attributeName="transform" type="translate" calcMode="discrete" dur="{num(T, 3)}s" repeatCount="indefinite" '
                    f'keyTimes="{";".join(kt(a) for a, _ in seq)}" values="{";".join(f"0 {-28 * b}" for _, b in seq)}"/>')
        odo.append(f'<g transform="translate({num(xx)} 0)"><g clip-path="url(#odo)"><g transform="translate(0 {-28 * final})">{anim}{digits}</g></g></g>')
    odo.append("</g>")
    A("".join(odo))

    # Bar Kontribusi Matrix
    by_level_days = {i: [d for d in pellets.values() if d.level == i] for i in range(1, 5)}
    active = [i for i in range(1, 5) if by_level_days[i]]
    bx, bw, by_, bh = x0 - 9, gw + 18, 298, 14
    gap = 5
    avail = bw - gap * (len(active) - 1)
    ndays = sum(len(by_level_days[i]) for i in active) or 1
    raw_w = {i: max(0.08, len(by_level_days[i]) / ndays) for i in active}
    norm = sum(raw_w.values())
    A(f'<text class="hl" x="{bx}" y="{by_ - 10}">CONTRIBUTION ENERGY METER</text>')
    cx_ = bx
    bar = []
    delta = 0.9 / N
    for i in active:
        w = avail * raw_w[i] / norm
        ev = level_events[i]
        n = len(ev)
        kts_ = [0.0]
        vals_ = ["0"]
        for k_, te in enumerate(ev):
            kts_ += [te, te + delta]
            vals_ += [num(w * k_ / n, 2), num(w * (k_ + 1) / n, 2)]
        kts_.append(1.0)
        vals_.append(num(w, 2))
        col = L[i - 1]
        bar.append(
            f'<g transform="translate({num(cx_, 2)} {by_})"><rect width="{num(w, 2)}" height="{bh}" rx="7" fill="{col}" opacity=".16"/>'
            f'<rect width="{num(w, 2)}" height="{bh}" rx="7" fill="none" stroke="{col}" stroke-opacity=".45"/>'
            f'<rect width="{num(w, 2)}" height="{bh}" rx="7" fill="url(#cg{i})">'
            f'<animate attributeName="width" dur="{num(T, 3)}s" repeatCount="indefinite" keyTimes="{";".join(kt(k) for k in kts_)}" values="{";".join(vals_)}"/></rect></g>')
        cx_ += w + gap
    A("".join(bar))

    # Legenda Level
    names = ["Low", "Medium", "High", "Supernova"]
    colw = bw / 4
    for i in range(1, 5):
        lx = bx + (i - 1) * colw
        ds = by_level_days[i]
        A(f'<g transform="translate({num(lx)} {by_ + bh + 26})"><rect width="12" height="12" y="-10" rx="3.5" fill="url(#cg{i})"/>'
          f'<text class="lg1" x="19" y="0">{names[i - 1]}</text>'
          f'<text class="lg2" x="19" y="16">{len(ds)} days, {sum(d.count for d in ds)} commits</text></g>')

    A("</svg>")
    stats = dict(weeks=W, cells=len(cellset), pellets=len(pellets), power=len(power), total=total,
                 ticks=N, tick=tick, duration=T, walls=len(maze.walls), ghosts_eaten=len(sim["popups"]))
    return "".join(out), stats, sim, maze

def main():
    ap = argparse.ArgumentParser(description="Pac-Man Cyberpunk Matrix Arcade Generator")
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "octocat"))
    ap.add_argument("--token", default=None)
    ap.add_argument("--source", choices=["auto", "api", "scrape", "demo"], default="auto")
    ap.add_argument("--demo", action="store_true", help="Pakai data demo acak")
    ap.add_argument("--out", default="dist")
    ap.add_argument("--theme", choices=sorted(PALETTES), default="purple")
    ap.add_argument("--title", default="Chomping XP")
    ap.add_argument("--tick", type=float, default=0.072, help="Kecepatan gerak (detik per langkah)")
    ap.add_argument("--max-duration", type=float, default=52.0, help="Durasi maksimal 1 game")
    ap.add_argument("--density", type=float, default=0.25, help="Kepadatan labirin")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    days, src = load_days(args)
    svg, st, _, _ = build_svg(days, args)
    ET.fromstring(svg)  # Validasi XML keras: jika invalid, gagal sebelum nulis file
    os.makedirs(args.out, exist_ok=True)
    for name in ("pacman-contribution-graph-dark.svg", "pacman-contribution-graph.svg"):
        with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
            f.write(svg)
    print(f"[SUCCESS] {st['pellets']} hari aktif, {st['total']} kontribusi, {st['power']} power pellets | "
          f"{st['ticks']} ticks @ {st['tick']:.3f}s = {st['duration']:.1f}s/cycle -> {args.out}/")

if __name__ == "__main__":
    main()
