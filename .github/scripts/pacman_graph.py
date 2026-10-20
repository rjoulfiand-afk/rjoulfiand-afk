import argparse
import datetime as dt
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
    "obsidian": dict(
        card_a="#090d16",
        card_b="#070a12",
        tile="#0f172a",
        tile_edge="#1e293b",
        levels=["#0e7490", "#06b6d4", "#10b981", "#f59e0b"],
        accent="#38bdf8",
        wall="#06b6d4",
        glow="#22d3ee",
        text="#f8fafc",
        muted="#64748b",
    )
}

GHOSTS = [
    ("blinky", "#ff2a2a", "#ff8080", "CHASE"),
    ("pinky", "#ff5ecb", "#ffa8e8", "AMBUSH"),
    ("inky", "#a78bfa", "#c4b5fd", "PATROL"),
    ("clyde", "#ff9100", "#ffc266", "RANDOM"),
]

S, G = 16, 4
P = S + G
DIRS = [(0, -1), (-1, 0), (0, 1), (1, 0)]
RELEASE = [0, 6, 14, 24]
K_READY = 16
K_END = 26


def num(x, n=2):
    s = f"{x:.{n}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def kt(x):
    return num(min(1.0, max(0.0, x)), 5)


def hex2rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


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


def get_today_utc():
    return dt.datetime.now(dt.timezone.utc).date()


def http(url, headers=None, post_data=None, timeout=20):
    req = urllib.request.Request(
        url,
        headers=headers or {"User-Agent": "CyberTelemetry-PacMan/2.0"},
        data=post_data,
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def normalize_rolling_window(items, today):
    """Filter tanggal masa depan dan kunci ke rentang 53 minggu terakhir (dimulai hari Minggu)."""
    valid = {}
    for ds, count, level in items:
        d = dt.date.fromisoformat(ds.split("T")[0])
        if d <= today:
            valid[d] = (int(count), int(level))

    if not valid:
        return []

    end_date = today
    start_365 = end_date - dt.timedelta(days=364)
    grid_start = start_365 - dt.timedelta(days=(start_365.weekday() + 1) % 7)

    out = []
    cur = grid_start
    while cur <= end_date:
        cnt, lvl = valid.get(cur, (0, 0))
        if cnt > 0 and lvl == 0:
            lvl = 1 if cnt <= 2 else (2 if cnt <= 5 else (3 if cnt <= 10 else 4))
        col = (cur - grid_start).days // 7
        row = (cur.weekday() + 1) % 7
        out.append(Day(cur.isoformat(), col, row, cnt, min(4, max(0, lvl))))
        cur += dt.timedelta(days=1)
    return out


def demo_days(seed=42):
    rng = random.Random(seed)
    end = get_today_utc()
    start = end - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    raw, d = [], start
    while d <= end:
        cnt = int(rng.expovariate(0.28)) if rng.random() < 0.48 else 0
        lvl = min(4, max(1, cnt)) if cnt > 0 else 0
        raw.append((d.isoformat(), cnt, lvl))
        d += dt.timedelta(days=1)
    return normalize_rolling_window(raw, end)


def load_days(user):
    today = get_today_utc()
    token = os.environ.get("GITHUB_TOKEN", "")

    # 1. Prioritas Utama: GitHub GraphQL API (100% sinkron dengan metrics_cards.py)
    if token:
        try:
            start_365 = today - dt.timedelta(days=364)
            grid_start = start_365 - dt.timedelta(days=(start_365.weekday() + 1) % 7)
            query = """
            query($user: String!, $from: DateTime!, $to: DateTime!) {
              user(login: $user) {
                contributionsCollection(from: $from, to: $to) {
                  contributionCalendar {
                    weeks {
                      contributionDays {
                        date
                        contributionCount
                        contributionLevel
                      }
                    }
                  }
                }
              }
            }
            """
            lvl_map = {
                "NONE": 0,
                "FIRST_QUARTILE": 1,
                "SECOND_QUARTILE": 2,
                "THIRD_QUARTILE": 3,
                "FOURTH_QUARTILE": 4,
            }
            payload = json.dumps({
                "query": query,
                "variables": {
                    "user": user,
                    "from": grid_start.isoformat() + "T00:00:00Z",
                    "to": today.isoformat() + "T23:59:59Z",
                },
            }).encode("utf-8")
             headers = {
                "User-Agent": "CyberTelemetry-PacMan/2.0",
                "Authorization": f"bearer {token}",
            }
            raw_res = json.loads(http("https://api.github.com/graphql", headers=headers, post_data=payload))
            weeks = raw_res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
            items = []
            for w in weeks:
                for d in w["contributionDays"]:
                    c_cnt = int(d["contributionCount"])
                    c_lvl = lvl_map.get(d.get("contributionLevel", "NONE"), 1 if c_cnt > 0 else 0)
                    items.append((d["date"], c_cnt, c_lvl))
            if items:
                days = normalize_rolling_window(items, today)
                print(f"[OK] Berhasil membaca {len(days)} hari kontribusi dari GraphQL API.")
                return days
        except Exception as e:
            print(f"[WARN] GraphQL API: {e}")

    # 2. Fallback Kedua: Jogruber Contributions API (?y=all + future clipping)
    try:
        raw = http(f"https://github-contributions-api.jogruber.de/v4/{user}?y=all")
        data = json.loads(raw)
        items = [(d["date"], d["count"], d.get("level", 0)) for d in data.get("contributions", [])]
        if items:
            days = normalize_rolling_window(items, today)
            print(f"[OK] Berhasil membaca {len(days)} hari kontribusi asli dari Jogruber API.")
            return days
    except Exception as e:
        print(f"[WARN] Jogruber API: {e}")

    # 3. Fallback Ketiga: GitHub Contributions HTML Scraper
    try:
        html_str = http(f"https://github.com/users/{user}/contributions")
        items = []
        for m in re.finditer(r'<td\b[^>]*data-date="([^"]+)"[^>]*data-level="([^"]+)"', html_str):
            lvl = int(m.group(2))
            items.append((m.group(1), 1 if lvl > 0 else 0, lvl))
        if items:
            days = normalize_rolling_window(items, today)
            print(f"[OK] Scraped {len(days)} hari dari HTML.")
            return days
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
        if k in self.blocked or self.deg[a] - 1 < min(2, self.base[a]) or self.deg[b] - 1 < min(2, self.base[b]):
            return False
        self.blocked.add(k)
        if not self._connected():
            self.blocked.discard(k)
            return False
        self.deg[a] -= 1
        self.deg[b] -= 1
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
                if a not in self.cells or b not in self.cells or not self._try(a, b):
                    break
                self.walls.append(("v" if vert else "h", a, b))

    def wall_path(self, px, py):
        vs, hs = {}, {}
        for o, a, b in self.walls:
            if o == "v":
                vs.setdefault(a[0] + 1, []).append(a[1])
            else:
                hs.setdefault(a[1] + 1, []).append(a[0])
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
                dist[n] = dist[c] + 1
                dq.append(n)
    return dist


def bfs_path(maze, start, goal):
    if start == goal:
        return []
    dq = deque([start])
    parent = {start: None}
    while dq:
        c = dq.popleft()
        if c == goal:
            break
        for n in maze.adj[c]:
            if n not in parent:
                parent[n] = c
                dq.append(n)
    if goal not in parent:
        return []
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
    pac_start = min(free, key=lambda c: (c[0] - cx) ** 2 + (c[1] - 5) ** 2)

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
        min(cells, key=lambda c: (c[0] - cx) ** 2 + (c[1] - 1) ** 2),
        min(cells, key=lambda c: (c[0] - cx - 5) ** 2 + (c[1] - 2) ** 2),
        min(cells, key=lambda c: (c[0] - cx + 5) ** 2 + (c[1] - 2) ** 2),
        min(cells, key=lambda c: (c[0] - cx) ** 2 + (c[1] - 4) ** 2),
    ]
    ghosts = [GhostAI(i, GHOSTS[i][0], ghost_starts[i], RELEASE[i]) for i in range(4)]
    g_pos = [[] for _ in ghosts]

    for t in range(total_steps):
        p_now = pac_path[t]
        p_next = pac_path[min(t + 1, total_steps - 1)]

        for g in ghosts:
            g_pos[g.idx].append(g.cell)
            if t < g.release:
                continue

            all_opts = maze.adj[g.cell]
            opts_no_prev = [n for n in all_opts if n != g.prev] or all_opts
            safe_opts = [
                n
                for n in opts_no_prev
                if n != p_next and n != p_now and (abs(n[0] - p_next[0]) + abs(n[1] - p_next[1]) >= 2)
            ]
            if not safe_opts:
                safe_opts = [n for n in opts_no_prev if n != p_next and n != p_now]
            if not safe_opts:
                safe_opts = [n for n in all_opts if n != p_next and n != p_now]
            if not safe_opts:
                safe_opts = [g.cell]

            if g.name == "blinky":
                dist_p = bfs_all(maze, [p_now])
                nxt = min(safe_opts, key=lambda n: (dist_p.get(n, 999), rng.random()))
            elif g.name == "pinky":
                tg = (p_now[0], 0)
                dist_tg = bfs_all(
                    maze, [tg if tg in cells else min(cells, key=lambda c: (c[0] - tg[0]) ** 2 + c[1] ** 2)]
                )
                nxt = min(safe_opts, key=lambda n: (dist_tg.get(n, 999), rng.random()))
            elif g.name == "inky":
                tg = (p_now[0], 6)
                dist_tg = bfs_all(
                    maze, [tg if tg in cells else min(cells, key=lambda c: (c[0] - tg[0]) ** 2 + (c[1] - 6) ** 2)]
                )
                nxt = min(safe_opts, key=lambda n: (dist_tg.get(n, 999), rng.random()))
            else:
                nxt = rng.choice(safe_opts)

            g.prev = g.cell
            g.cell = nxt

    return dict(pac_pos=pac_path, g_pos=g_pos, eaten=eaten, n=total_steps - 1)


def pac_d(r, deg):
    a = math.radians(deg)
    return f"M0 0L{num(r * math.cos(a))} {num(-r * math.sin(a))}A{num(r)} {num(r)} 0 1 0 {num(r * math.cos(a))} {num(r * math.sin(a))}Z"


def _skirt(up, down):
    segs = [down, up, down, up, down, up]
    xs = [9, 6, 3, 0, -3, -6, -9]
    d = "M-9 7V0A9 9 0 0 1 9 0V7"
    for i, c in enumerate(segs):
        d += f"Q{num((xs[i] + xs[i + 1]) / 2)} {c} {xs[i + 1]} 7"
    return d + "Z"


GHOST_A, GHOST_B = _skirt(2.5, 11.5), _skirt(11.5, 2.5)


def rounded_rect_path(w, h, r, inset=1.5):
    x0, y0 = inset, inset
    x1, y1 = w - inset, h - inset
    rad = max(1.0, r - inset)
    return (
        f"M {num(x0 + rad)} {num(y0)} L {num(x1 - rad)} {num(y0)} "
        f"A {num(rad)} {num(rad)} 0 0 1 {num(x1)} {num(y0 + rad)} L {num(x1)} {num(y1 - rad)} "
        f"A {num(rad)} {num(rad)} 0 0 1 {num(x1 - rad)} {num(y1)} L {num(x0 + rad)} {num(y1)} "
        f"A {num(rad)} {num(rad)} 0 0 1 {num(x0)} {num(y1 - rad)} L {num(x0)} {num(y0 + rad)} "
        f"A {num(rad)} {num(rad)} 0 0 1 {num(x0 + rad)} {num(y0)} Z"
    )


def build_svg(days, user, title):
    P_THEME = PALETTES["obsidian"]
    L = P_THEME["levels"]

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
    Wt, Ht = x0 + gw + 36, 372
    cxp = lambda c: x0 + c * P + S / 2
    cyp = lambda r: y0 + r * P + S / 2

    N = K_READY + sim["n"] + K_END
    T = N * 0.22
    tm = lambda k, off=0.0: (K_READY + k + off) / N

    rr_outer = rounded_rect_path(Wt, Ht, 14, inset=0.75)
    rr_inner = rounded_rect_path(Wt, Ht, 14, inset=1.75)

    defs = [
        f'<linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="{P_THEME["card_a"]}"/><stop offset="52%" stop-color="#0d1322"/><stop offset="100%" stop-color="{P_THEME["card_b"]}"/></linearGradient>',
        '<radialGradient id="blob1" cx="15%" cy="15%" r="60%"><stop offset="0%" stop-color="#06b6d4" stop-opacity=".14"/><stop offset="100%" stop-color="#090d16" stop-opacity="0"/></radialGradient>',
        '<radialGradient id="blob2" cx="85%" cy="85%" r="60%"><stop offset="0%" stop-color="#8b5cf6" stop-opacity=".14"/><stop offset="100%" stop-color="#070a12" stop-opacity="0"/></radialGradient>',
        '<linearGradient id="inner_bezel" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#38bdf8" stop-opacity=".38"/><stop offset="45%" stop-color="#1e293b" stop-opacity=".22"/><stop offset="100%" stop-color="#8b5cf6" stop-opacity=".35"/></linearGradient>',
        '<linearGradient id="ttl" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#f8fafc"/><stop offset="50%" stop-color="#67e8f9"/><stop offset="100%" stop-color="#c4b5fd"/></linearGradient>',
        f'<filter id="glow" filterUnits="userSpaceOnUse" x="0" y="0" width="{Wt}" height="{Ht}"><feGaussianBlur stdDeviation="3.0" result="b1"/><feGaussianBlur stdDeviation="1.1" result="b2"/><feMerge><feMergeNode in="b1"/><feMergeNode in="b2"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        '<pattern id="dot_grid" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="0.75" fill="#334155" opacity="0.32"/></pattern>',
        '<radialGradient id="pacg" cx=".36" cy=".3" r=".85"><stop offset="0" stop-color="#fffbeb"/><stop offset=".45" stop-color="#fbbf24"/><stop offset="1" stop-color="#d97706"/></radialGradient>',
        '<radialGradient id="halo-pac"><stop offset="0" stop-color="#fbbf24" stop-opacity=".5"/><stop offset="1" stop-color="#fbbf24" stop-opacity="0"/></radialGradient>',
    ]
    for i, c in enumerate(L, 1):
        defs.append(
            f'<linearGradient id="cg{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{mix(c, "#ffffff", .35)}"/><stop offset=".55" stop-color="{c}"/><stop offset="1" stop-color="{mix(c, "#000000", .32)}"/></linearGradient>'
        )
        halo = f'<rect x="-11.5" y="-11.5" width="23" height="23" rx="7.5" fill="{c}" opacity="{.25 if i >= 3 else .14}"/>'
        defs.append(
            f'<g id="cell{i}">{halo}<rect x="-8" y="-8" width="16" height="16" rx="4.6" fill="url(#cg{i})"/><rect x="-7.5" y="-7.5" width="15" height="15" rx="4.1" fill="none" stroke="#fff" stroke-opacity=".25"/><rect x="-5.2" y="-6.3" width="10.4" height="1.5" rx=".75" fill="#fff" opacity=".45"/></g>'
        )

    for i, (name, c, lt, _) in enumerate(GHOSTS):
        defs.append(
            f'<linearGradient id="gg{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{lt}"/><stop offset=".45" stop-color="{c}"/><stop offset="1" stop-color="{mix(c, "#000000", .35)}"/></linearGradient>'
        )
        defs.append(
            f'<radialGradient id="halo{i}"><stop offset="0" stop-color="{c}" stop-opacity=".45"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>'
        )

    style = (
        "text{font-family:ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,monospace}"
        f'.ti{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:20px;font-weight:900;letter-spacing:.08em;fill:url(#ttl)}}'
        f'.su{{font-size:11.5px;font-weight:600;fill:{P_THEME["muted"]}}}'
        f'.mo,.wd{{font-size:10px;font-weight:600;fill:{P_THEME["muted"]}}}'
        f'.hl{{font-size:10.5px;font-weight:800;letter-spacing:.09em;fill:{P_THEME["accent"]}}}'
        f'.nu{{font-size:25px;font-weight:900;fill:{P_THEME["text"]}}}'
        f'.lg1{{font-size:10.5px;font-weight:700;fill:{P_THEME["text"]}}}'
        f'.lg2{{font-size:9.5px;font-weight:600;fill:{P_THEME["muted"]}}}'
        '.ar{font-size:10px;font-weight:800;letter-spacing:.18em;fill:#fbbf24}'
        '@media(max-width:760px){.spr{transform:scale(1.25)}}'
        '@media(max-width:640px){.wd,.lg2{display:none}.ti{font-size:25px}.su{font-size:14px}.hl{font-size:13px}.lg1{font-size:13px}.spr{transform:scale(1.5)}}'
        '@media(max-width:440px){.mo,.su{display:none}.ti{font-size:28px}.spr{transform:scale(1.75)}}'
    )

    A = []
    A.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wt} {Ht}" width="100%" height="{Ht}" role="img" aria-label="{escape(title)}" shape-rendering="geometricPrecision">'
    )
    A.append(f"<title>{escape(title)}</title><style>{style}</style><defs>{''.join(defs)}</defs>")

    # Obsidian Titanium Surface & Dual-Bezel Frame (rx=14)
    A.append(f'<rect width="{Wt}" height="{Ht}" rx="14" fill="url(#bg)"/>')
    A.append(f'<rect width="{Wt}" height="{Ht}" rx="14" fill="url(#blob1)"/>')
    A.append(f'<rect width="{Wt}" height="{Ht}" rx="14" fill="url(#blob2)"/>')
    A.append(f'<rect width="{Wt}" height="{Ht}" rx="14" fill="url(#dot_grid)"/>')
    A.append(f'<line x1="24" y1="1.8" x2="{Wt - 24}" y2="1.8" stroke="#e2e8f0" stroke-opacity="0.16" stroke-width="1"/>')
    A.append(f'<path d="{rr_outer}" fill="none" stroke="#1e293b" stroke-width="1.5"/>')
    A.append(f'<path d="{rr_inner}" fill="none" stroke="url(#inner_bezel)" stroke-width="1.1"/>')

    # Laser Border Beams
    A.append(
        f'<path d="{rr_inner}" fill="none" stroke="#22d3ee" stroke-width="1.8" stroke-linecap="round" stroke-dasharray="10 90" pathLength="100" opacity="0.8">'
        f'<animate attributeName="stroke-dashoffset" from="0" to="-100" dur="20s" repeatCount="indefinite"/></path>'
    )
    A.append(
        f'<path d="{rr_inner}" fill="none" stroke="#f59e0b" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="6 94" pathLength="100" opacity="0.7">'
        f'<animate attributeName="stroke-dashoffset" from="-50" to="-150" dur="20s" repeatCount="indefinite"/></path>'
    )

    # Header Emblem & Title
    A.append(
        f'<g transform="translate(46 42)"><circle r="16" fill="url(#halo-pac)"/><path fill="url(#pacg)" d="{pac_d(10, 36)}"><animate attributeName="d" dur=".45s" repeatCount="indefinite" values="{pac_d(10, 36)};{pac_d(10, 3)};{pac_d(10, 36)}"/></path><circle cx="17" cy="0" r="2.4" fill="{L[3]}"/><circle cx="26" cy="0" r="2.4" fill="{L[1]}" opacity=".85"/></g>'
    )
    A.append(
        f'<text class="ti" x="88" y="44">{escape(title.upper())}</text>'
        f'<text class="su" x="88" y="65">@{escape(user)} &#8226; AUTONOMOUS BFS LABYRINTH &#8226; 53-WEEK TELEMETRY</text>'
    )

    # Restored Month Labels (.mo) along Top of Grid
    month_cols = {}
    for d in days:
        dt_obj = dt.date.fromisoformat(d.date)
        ym = (dt_obj.year, dt_obj.month)
        if ym not in month_cols:
            month_cols[ym] = (d.col, dt_obj.strftime("%b"))

    last_mx = -999
    for _, (mc, m_str) in sorted(month_cols.items()):
        mx = x0 + mc * P
        if mx - last_mx >= 44 and mx <= x0 + gw - 16:
            A.append(f'<text class="mo" x="{num(mx)}" y="{y0 - 10}">{m_str}</text>')
            last_mx = mx

    # Restored Weekday Labels (.wd) along Left of Grid
    for r_idx, w_lbl in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        A.append(f'<text class="wd" x="{x0 - 10}" y="{num(cyp(r_idx) + 3.5)}" text-anchor="end">{w_lbl}</text>')

    # Base Matrix Tiles
    tiles = "".join(
        f"M{num(x0 + c * P + 4.6)} {num(y0 + r * P)}h{num(S - 9.2)}a4.6 4.6 0 0 1 4.6 4.6v{num(S - 9.2)}a4.6 4.6 0 0 1 -4.6 4.6h{num(-(S - 9.2))}a4.6 4.6 0 0 1 -4.6 -4.6v{num(-(S - 9.2))}a4.6 4.6 0 0 1 4.6 -4.6z"
        for (c, r) in sorted(cellset)
    )
    A.append(f'<path d="{tiles}" fill="{P_THEME["tile"]}" stroke="{P_THEME["tile_edge"]}" stroke-width="1"/>')

    # Electric Cyan Maze Walls
    wp = maze.wall_path(lambda X: x0 + X * P - G / 2, lambda Y: y0 + Y * P - G / 2)
    A.append(
        f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="{wp}" stroke="{P_THEME["glow"]}" stroke-opacity=".55" stroke-width="4.0" filter="url(#glow)"/>'
        f'<path d="{wp}" stroke="{P_THEME["wall"]}" stroke-width="1.8"/></g>'
    )

    # XP Pellets & Harvest Animations
    eat_time = {cell: tm(t_eat, 0.5) for t_eat, cell, _ in sim["eaten"]}
    for cell, d in sorted(pellets.items()):
        c, r = cell
        te = eat_time.get(cell, None)
        if te is not None:
            t0 = max(0.001, min(0.985, te))
            t1 = min(0.992, t0 + 0.004)
            t2 = min(0.999, t0 + 0.012)
            kts = f"0;{kt(t0)};{kt(t1)};{kt(t2)};1"
            scale_anim = f'<animateTransform attributeName="transform" type="scale" dur="{num(T, 3)}s" repeatCount="indefinite" keyTimes="{kts}" values="1;1;1.35;0;0"/>'
            opacity_anim = f'<animate attributeName="opacity" dur="{num(T, 3)}s" repeatCount="indefinite" keyTimes="{kts}" values="1;1;1;0;0"/>'
        else:
            scale_anim, opacity_anim = "", ""

        A.append(
            f'<g transform="translate({num(cxp(c))} {num(cyp(r))})"><g>{scale_anim}{opacity_anim}<use href="#cell{d.level}"/></g></g>'
        )

    # Pac-Man Position + 4-Way Directional Mouth Rotation (Anti-Moonwalk)
    pad_arr = lambda arr: [arr[0]] * K_READY + list(arr) + [arr[-1]] * K_END
    raw_pac = sim["pac_pos"]
    px_pos = pad_arr([(cxp(c), cyp(r)) for c, r in raw_pac])
    pos_str = ";".join(f"{num(x, 1)} {num(y, 1)}" for x, y in px_pos)

    step_angles = []
    cur_deg = 0
    for i in range(len(raw_pac)):
        if i + 1 < len(raw_pac):
            dc = raw_pac[i + 1][0] - raw_pac[i][0]
            dr = raw_pac[i + 1][1] - raw_pac[i][1]
            if dc > 0:
                cur_deg = 0
            elif dc < 0:
                cur_deg = 180
            elif dr > 0:
                cur_deg = 90
            elif dr < 0:
                cur_deg = -90
        step_angles.append(cur_deg)
    padded_angles = [0] * K_READY + step_angles + [step_angles[-1]] * K_END
    rot_str = ";".join(str(a) for a in padded_angles)

    p_open, p_shut = pac_d(9.6, 38), pac_d(9.6, 3)
    pac_art = (
        f'<circle r="19" fill="url(#halo-pac)"/>'
        f'<g><animateTransform attributeName="transform" type="rotate" calcMode="discrete" dur="{num(T, 3)}s" repeatCount="indefinite" values="{rot_str}"/>'
        f'<path fill="url(#pacg)" stroke="#fff3b0" stroke-opacity=".7" stroke-width=".9" d="{p_open}">'
        f'<animate attributeName="d" dur=".32s" repeatCount="indefinite" values="{p_open};{p_shut};{p_open}"/></path></g>'
        f'<path d="M-5.4 -5.6A7.6 7.6 0 0 1 -0.8 -8" fill="none" stroke="#fff" stroke-opacity=".75" stroke-width="1.6" stroke-linecap="round"/>'
        f'<circle cx="1.5" cy="-5.2" r="1.5" fill="#2b1a00"/><circle cx="1.1" cy="-5.7" r=".55" fill="#fff"/>'
    )
    A.append(
        f'<g transform="translate({num(px_pos[0][0], 1)} {num(px_pos[0][1], 1)})">'
        f'<animateTransform attributeName="transform" type="translate" dur="{num(T, 3)}s" repeatCount="indefinite" values="{pos_str}"/>'
        f'<g class="spr">{pac_art}</g></g>'
    )

    # 4 Ghosts with Aligned Forward-Looking Pupils
    for g_i, (name, col, lt, _) in enumerate(GHOSTS):
        gp = pad_arr([(cxp(c), cyp(r)) for c, r in sim["g_pos"][g_i]])
        g_str = ";".join(f"{num(x, 1)} {num(y, 1)}" for x, y in gp)
        wave = f'<animate attributeName="d" dur=".48s" repeatCount="indefinite" values="{GHOST_A};{GHOST_B};{GHOST_A}"/>'
        face = (
            '<circle cx="-3.1" cy="-2.4" r="1.85" fill="#fff"/><circle cx="3.1" cy="-2.4" r="1.85" fill="#fff"/>'
            '<circle cx="-2.5" cy="-2.4" r="1.1" fill="#090d16"/><circle cx="3.7" cy="-2.4" r="1.1" fill="#090d16"/>'
            '<circle cx="-2.8" cy="-2.8" r=".4" fill="#fff"/><circle cx="3.4" cy="-2.8" r=".4" fill="#fff"/>'
        )
        gh_art = f'<circle r="18" fill="url(#halo{g_i})"/><path fill="url(#gg{g_i})" stroke="{lt}" stroke-opacity=".55" stroke-width=".9" d="{GHOST_A}">{wave}</path>{face}'
        A.append(
            f'<g transform="translate({num(gp[0][0], 1)} {num(gp[0][1], 1)})">'
            f'<animateTransform attributeName="transform" type="translate" dur="{num(T, 3)}s" repeatCount="indefinite" values="{g_str}"/>'
            f'<g class="spr">{gh_art}</g></g>'
        )

    # Top-Right Rolling Year Counter Badge
    xr = Wt - 28
    A.append(
        f'<text class="hl" x="{num(xr)}" y="36" text-anchor="end">ROLLING YEAR XP</text>'
        f'<text class="nu" x="{num(xr)}" y="66" text-anchor="end">{total}</text>'
    )

    # Contribution Energy Meter (Real-Time Harvester)
    bx, bw, by_, bh = x0 - 9, gw + 18, 286, 14
    A.append(f'<text class="hl" x="{bx}" y="{by_ - 10}">CONTRIBUTION ENERGY METER (REAL-TIME HARVESTER)</text>')
    A.append(
        f'<g transform="translate({bx + bw - 190} {by_ - 19})">'
        f'<rect x="0" y="0" width="9" height="9" rx="2" fill="{L[0]}"/>'
        f'<rect x="14" y="0" width="9" height="9" rx="2" fill="{L[1]}"/>'
        f'<rect x="28" y="0" width="9" height="9" rx="2" fill="{L[2]}"/>'
        f'<rect x="42" y="0" width="9" height="9" rx="2" fill="{L[3]}"/>'
        f'<text class="lg2" x="58" y="8">XP TIERS</text></g>'
    )

    A.append(f'<rect x="{bx}" y="{by_}" width="{bw}" height="{bh}" rx="7" fill="#060911" stroke="#1e293b" stroke-width="1.2"/>')

    if total_pellets > 0:
        seg_w = bw / total_pellets
        sw = max(2.0, seg_w - 1.2)
        for i in range(total_pellets):
            sx = bx + i * seg_w
            A.append(
                f'<rect x="{num(sx, 2)}" y="{by_ + 2}" width="{num(sw, 2)}" height="{bh - 4}" rx="2" fill="#0f172a" stroke="#1e293b" stroke-width="0.5"/>'
            )

        for k, (t_eat, cell, lvl) in enumerate(sim["eaten"]):
            sx = bx + k * seg_w
            col = L[min(3, max(0, lvl - 1))]
            te = tm(t_eat, 0.5)
            t0 = max(0.001, min(0.994, te))
            t1 = min(0.998, t0 + 0.003)
            anim = f'<animate attributeName="opacity" dur="{num(T, 3)}s" repeatCount="indefinite" keyTimes="0;{kt(t0)};{kt(t1)};1" values="0;0;1;1"/>'
            A.append(
                f'<rect x="{num(sx, 2)}" y="{by_ + 2}" width="{num(sw, 2)}" height="{bh - 4}" rx="2" fill="{col}" opacity="0">{anim}</rect>'
            )

        # Fixed Off-By-One Keyframe Alignment (sim["n"] + 1 steps)
        head_pos = [bx] * K_READY
        cur_e = 0
        for step in range(sim["n"] + 1):
            while cur_e < total_pellets and sim["eaten"][cur_e][0] <= step:
                cur_e += 1
            head_pos.append(bx + (cur_e / total_pellets) * bw)
        head_pos += [bx + bw] * K_END
        head_str = ";".join(f"{num(x, 1)} {num(by_ + bh / 2, 1)}" for x in head_pos)
        A.append(
            f'<g transform="translate({bx} {num(by_ + bh / 2, 1)})">'
            f'<animateTransform attributeName="transform" type="translate" dur="{num(T, 3)}s" repeatCount="indefinite" values="{head_str}"/>'
            f'<circle r="6" fill="#fbbf24" filter="url(#glow)"/><circle r="3" fill="#ffffff"/></g>'
        )

    # Bottom Arcade Telemetry HUD Bar (Restores .lg1 & .ar and eliminates dead bottom space)
    hud_y = 320
    A.append(
        f'<rect x="{bx}" y="{hud_y}" width="{bw}" height="30" rx="7" fill="#060911" stroke="#1e293b" stroke-width="1"/>'
    )
    gx_cursor = bx + 16
    for g_name, g_col, _, g_role in GHOSTS:
        A.append(f'<circle cx="{gx_cursor}" cy="{hud_y + 15}" r="4" fill="{g_col}"/>')
        A.append(f'<text class="lg2" x="{gx_cursor + 9}" y="{hud_y + 18.5}">{g_name.upper()} [{g_role}]</text>')
        gx_cursor += 126

    A.append(f'<text class="ar" x="{num(Wt / 2 + 45)}" y="{hud_y + 19}" text-anchor="middle">&#9733; ARCADE AI ACTIVE</text>')
    A.append(
        f'<text class="lg1" x="{bx + bw - 16}" y="{hud_y + 18.5}" text-anchor="end">'
        f'{total_pellets} ACTIVE DAYS &#8226; {len(maze.walls)} WALLS</text>'
    )

    A.append("</svg>")
    return "".join(A)


def main():
    ap = argparse.ArgumentParser(description="Obsidian Titanium Pac-Man Contribution Arcade")
    ap.add_argument("--user", default="rjoulfiand-afk")
    ap.add_argument("--title", default="Chomping XP")
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()

    days = load_days(args.user)
    os.makedirs(args.out, exist_ok=True)

    pacman_svg = build_svg(days, args.user, args.title)
    ET.fromstring(pacman_svg)

    for fn in ("pacman-contribution-graph-dark.svg", "pacman-contribution-graph.svg"):
        out_path = os.path.join(args.out, fn)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(pacman_svg)
    size_kb = len(pacman_svg.encode("utf-8")) / 1024.0
    print(f"[SUCCESS] Pac-Man SVGs berhasil dibuat di {args.out}/ ({size_kb:.1f} KB)")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)
