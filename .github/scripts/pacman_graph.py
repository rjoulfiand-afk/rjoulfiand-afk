#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pac-Man Cyberpunk Arcade + 8-Bit Tactical Commando (Precision 1-to-1 Destruction & Smooth Walk)
Authentic Developer Metrics, Zero AI Slop, 100% Native Vector Animation
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
        card_a="#0d1117", card_b="#06080d", tile="#131722", tile_edge="#1f2638",
        levels=["#4c1d95", "#7e22ce", "#a855f7", "#e9d5ff"],
        accent="#a855f7", wall="#a855f7", glow="#c084fc", text="#f5f3ff", muted="#94a3b8"
    )
}

GHOSTS = [
    ("blinky", "#ff2a2a", "#ff8080"),
    ("pinky", "#ff5ecb", "#ffa8e8"),
    ("inky", "#00e5ff", "#80f2ff"),
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

# ==================== SPRITE RETRO COMMANDO ====================
def render_arcade_commando_sprite():
    return '''
    <!-- Drop Shadow Ground -->
    <ellipse cx="0" cy="2" rx="15" ry="4.5" fill="#000000" opacity="0.6"/>

    <!-- Combat Boots -->
    <rect x="-9" y="-8" width="7" height="8" rx="2" fill="#38211b"/>
    <rect x="2" y="-8" width="7" height="8" rx="2" fill="#38211b"/>
    <rect x="-9.5" y="-2" width="8" height="2.5" rx="1" fill="#180e0b"/>
    <rect x="1.5" y="-2" width="8" height="2.5" rx="1" fill="#180e0b"/>

    <!-- Camo Pants -->
    <rect x="-10" y="-22" width="8" height="15" rx="2" fill="#4d5a3c"/>
    <rect x="2" y="-22" width="8" height="15" rx="2" fill="#4d5a3c"/>
    <rect x="-8" y="-17" width="4" height="5" fill="#343e28"/>
    <rect x="4" y="-14" width="4" height="4" fill="#677951"/>
    <rect x="-3" y="-21" width="6" height="5" fill="#303925"/>

    <!-- Torso & Military Jacket -->
    <rect x="-13" y="-39" width="26" height="19" rx="4" fill="#4d5a3c"/>
    <rect x="-11" y="-36" width="6" height="5" fill="#343e28"/>
    <rect x="4" y="-37" width="7" height="6" fill="#677951"/>
    <rect x="-4" y="-30" width="8" height="6" fill="#303925"/>
    <rect x="4" y="-28" width="6" height="5" fill="#343e28"/>

    <!-- Red & White Military Ribbon / Badge -->
    <rect x="4" y="-35" width="4.5" height="2.5" rx="0.5" fill="#ef4444"/>
    <rect x="4" y="-32.5" width="4.5" height="1.8" rx="0.5" fill="#ffffff"/>

    <!-- Brown Tactical Gloves -->
    <rect x="-12" y="-29" width="5.5" height="5.5" rx="1.5" fill="#713f2f"/>
    <rect x="7" y="-27" width="5.5" height="5.5" rx="1.5" fill="#713f2f"/>

    <!-- Assault Rifle Upright (Aiming Upwards) -->
    <g transform="rotate(-68 2 -32)">
      <!-- Gun Body -->
      <rect x="-16" y="-33" width="30" height="5" rx="1.5" fill="#1f2937"/>
      <rect x="-10" y="-28" width="4.5" height="6" rx="1" fill="#111827"/>
      <rect x="5" y="-28" width="4" height="7" rx="1" fill="#374151"/>
      <!-- Long Barrel & Flash Hider -->
      <rect x="14" y="-34" width="12" height="3" fill="#111827"/>
      <rect x="26" y="-35.5" width="3" height="6" rx="1" fill="#4b5563"/>
    </g>

    <!-- Hair (Auburn Tufts) -->
    <rect x="-12" y="-50" width="4.5" height="9" rx="2" fill="#78350f"/>
    <rect x="7.5" y="-50" width="4.5" height="9" rx="2" fill="#78350f"/>
    <rect x="-13" y="-45" width="3" height="5" fill="#58250a"/>
    <rect x="10" y="-45" width="3" height="5" fill="#58250a"/>

    <!-- Chibi Face & Tone -->
    <rect x="-9" y="-50" width="18" height="12" rx="2.5" fill="#fed7aa"/>
    <!-- Cheeks Blush -->
    <rect x="-9" y="-43" width="3.5" height="3" rx="1" fill="#fca5a5" opacity="0.6"/>
    <rect x="5.5" y="-43" width="3.5" height="3" rx="1" fill="#fca5a5" opacity="0.6"/>
    <!-- Eyes -->
    <rect x="-6" y="-46" width="4" height="4" rx="0.8" fill="#0f172a"/>
    <rect x="2" y="-46" width="4" height="4" rx="0.8" fill="#0f172a"/>
    <rect x="-5" y="-47" width="1.8" height="1.8" fill="#ffffff"/>
    <rect x="3" y="-47" width="1.8" height="1.8" fill="#ffffff"/>
    <!-- Confident Smile -->
    <rect x="-2" y="-40" width="4" height="1.8" rx="0.8" fill="#b45309"/>

    <!-- Helmet Doreng Camo -->
    <rect x="-14" y="-62" width="28" height="16" rx="7" fill="#4d5a3c"/>
    <rect x="-15.5" y="-51" width="31" height="4" rx="2" fill="#343e28"/>
    <!-- Camo spots on helmet -->
    <rect x="-9" y="-60" width="7" height="6" rx="1.5" fill="#303925"/>
    <rect x="3" y="-61" width="8" height="7" rx="1.5" fill="#677951"/>
    <rect x="-12" y="-55" width="5" height="4" rx="1" fill="#677951"/>
    <rect x="7" y="-55" width="6" height="4" rx="1" fill="#303925"/>
    <!-- Highlight Dapples on Helmet -->
    <circle cx="-3" cy="-59" r="1.5" fill="#d9f99d"/>
    <circle cx="1" cy="-57" r="1.2" fill="#ffffff" opacity="0.85"/>
    <circle cx="6" cy="-58" r="1.3" fill="#d9f99d"/>
    '''

# ==================== 8-BIT CYBER COMMANDO STRIKER (PRECISION 1-TO-1 DESTRUCTION) ====================
def build_soldier_shooter_svg(days, user):
    W = max(d.col for d in days) + 1
    cellset = {(d.col, d.row) for d in days}
    active_days = [d for d in days if d.count > 0]
    total_commits = sum(d.count for d in days)

    x0, y0 = 58, 102
    gw = W * P - G
    Wt, Ht = x0 + gw + 36, 430
    cxp = lambda c: x0 + c * P + S / 2
    cyp = lambda r: y0 + r * P + S / 2

    # Ambil 6 target aktif unik yang tersebar luas dari awal, tengah, hingga akhir tahun
    sorted_active = sorted(active_days, key=lambda d: d.col)
    if len(sorted_active) >= 6:
        raw_targets = [
            sorted_active[0],
            sorted_active[len(sorted_active) // 5],
            sorted_active[(len(sorted_active) * 2) // 5],
            sorted_active[(len(sorted_active) * 3) // 5],
            sorted_active[(len(sorted_active) * 4) // 5],
            sorted_active[-1]
        ]
    else:
        raw_targets = sorted_active if sorted_active else [Day("2026-10-01", 45, 3, 5, 3)]

    # Pastikan setiap target punya kolom berbeda agar perjalanan tentara jauh dan jelas
    seen = set()
    targets = []
    for t in raw_targets:
        if t.col not in seen:
            seen.add(t.col)
            targets.append(t)
    targets = targets if targets else raw_targets

    shots_count = len(targets)
    # 2.1 detik per target: 0.85s jalan mulus, 0.45s bidik/tembak, 0.25s peluru terbang & hancur, 0.55s jeda
    step_sec = 2.1
    shooting_duration = shots_count * step_sec
    victory_sec = 3.6
    T = shooting_duration + victory_sec

    # Runway tentara dibuat lapang di bawah grid
    rail_y = y0 + 7 * P + 96
    mid_col_x = cxp(W // 2)

    L = PALETTES["purple"]["levels"]

    cell_defs = []
    for i, c in enumerate(L, 1):
        cell_defs.append(f'<linearGradient id="scg{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{mix(c, "#ffffff", .35)}"/><stop offset=".55" stop-color="{c}"/><stop offset="1" stop-color="{mix(c, "#000000", .32)}"/></linearGradient>')
        halo = f'<rect x="-11.5" y="-11.5" width="23" height="23" rx="7.5" fill="{c}" opacity="{.25 if i >= 3 else .15}"/>'
        cell_defs.append(f'<g id="scell{i}">{halo}<rect x="-8" y="-8" width="16" height="16" rx="4.6" fill="url(#scg{i})"/><rect x="-7.5" y="-7.5" width="15" height="15" rx="4.1" fill="none" stroke="#fff" stroke-opacity=".25"/><rect x="-5.2" y="-6.3" width="10.4" height="1.5" rx=".75" fill="#fff" opacity=".45"/></g>')

    svg_parts = []
    svg_parts.append(f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wt} {Ht}" width="{Wt}" height="{Ht}" role="img" shape-rendering="geometricPrecision">
  <defs>
    <linearGradient id="arc_bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#06080d"/>
    </linearGradient>
    <radialGradient id="amb_glow1" cx="20%" cy="20%" r="50%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#a855f7" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="amb_glow2" cx="80%" cy="80%" r="50%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="#38bdf8" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="arc_bd" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.85"/>
      <stop offset="50%" stop-color="#38bdf8" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#a855f7" stop-opacity="0.85"/>
    </linearGradient>
    <linearGradient id="runway_gantry" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="60%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#020617"/>
    </linearGradient>
    <filter id="bullet_glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="2.5" result="b1"/>
      <feMerge>
        <feMergeNode in="b1"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    <filter id="bubble_shadow" x="-30%" y="-30%" width="160%" height="160%">
      <feDropShadow dx="0" dy="5" stdDeviation="4" flood-color="#000000" flood-opacity="0.6"/>
    </filter>
    {''.join(cell_defs)}
  </defs>

  <style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .hd_tag {{ font-size: 11px; font-weight: 800; letter-spacing: 0.12em; fill: #a855f7; }}
    .hd_title {{ font-size: 19px; font-weight: 800; letter-spacing: 0.04em; fill: #ffffff; }}
    .badge_txt {{ font-size: 11.5px; font-weight: 700; fill: #e2e8f0; }}
  </style>

  <!-- Ambient Stage Body & Soft Neon Blobs -->
  <rect width="{Wt}" height="{Ht}" rx="18" fill="url(#arc_bg)"/>
  <rect width="{Wt}" height="{Ht}" rx="18" fill="url(#amb_glow1)"/>
  <rect width="{Wt}" height="{Ht}" rx="18" fill="url(#amb_glow2)"/>
  <rect x="1" y="1" width="{Wt - 2}" height="{Ht - 2}" rx="17" fill="none" stroke="url(#arc_bd)" stroke-width="1.6"/>

  <!-- Sleek Top Header HUD (Zero Gimmick Coins) -->
  <g transform="translate(38, 34)">
    <text class="hd_tag" x="0" y="12">▶ TACTICAL RECON UNIT</text>
    <text class="hd_title" x="0" y="34">8-BIT CYBER COMMANDO : COMMIT STRIKER</text>
  </g>

  <!-- Right Clean Authentic Badge -->
  <g transform="translate({Wt - 230}, 36)">
    <rect x="0" y="0" width="192" height="34" rx="8" fill="#131722" stroke="#2a334d" stroke-width="1.2"/>
    <circle cx="16" cy="17" r="4.5" fill="#22c55e"/>
    <text class="badge_txt" x="28" y="21"><tspan font-weight="800" fill="#a855f7">{total_commits}</tspan> Commits Verified</text>
  </g>

  <!-- Grid Dasar (Empty Tiles) -->
''')

    tiles = []
    for c, r in sorted(cellset):
        tx = x0 + c * P
        ty = y0 + r * P
        tiles.append(f'<rect x="{num(tx)}" y="{num(ty)}" width="{S}" height="{S}" rx="4.6" fill="{PALETTES["purple"]["tile"]}" stroke="{PALETTES["purple"]["tile_edge"]}" stroke-width="0.8"/>')
    svg_parts.append("  " + "".join(tiles) + "\n")

    # Render Kotak Kontribusi & 1-TO-1 DESTRUCTION SHATTER PHYSICS
    target_cells = {(t.col, t.row): i for i, t in enumerate(targets)}
    for d in active_days:
        cx, cy = cxp(d.col), cyp(d.row)
        lvl_color = L[min(3, max(0, d.level - 1))]
        
        t_idx = target_cells.get((d.col, d.row), None)
        if t_idx is not None:
            # Waktu persis saat peluru tiba dan menghancurkan kotak ini
            t_hit = (t_idx * step_sec + 1.35) / T
            k0 = max(0.001, t_hit - 0.015)
            k1 = t_hit
            k2 = min(0.999, t_hit + 0.018)
            k3 = min(0.999, t_hit + 0.065)
            k_end_shatter = (shooting_duration + 0.2) / T

            kts_box = f"0;{kt(k0)};{kt(k1)};{kt(k2)};{kt(k_end_shatter)};1"
            kts_shard = f"0;{kt(k0)};{kt(k1)};{kt(k3)};{kt(k_end_shatter)};1"
            
            # KOTAK HANCUR LEBUR SAAT DITEMBAK: Normal -> Kena Hit -> Pecah -> Lenyap Total
            anim = f'''
    <g transform="translate({num(cx)} {num(cy)})">
      <!-- Kotak Induk: Flash Putih Lalu Lenyap (Hancur) -->
      <g>
        <animateTransform attributeName="transform" type="scale" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_box}" values="1 1; 1 1; 1.45 1.45; 0 0; 0 0; 1 1"/>
        <animate attributeName="opacity" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_box}" values="1; 1; 1; 0; 0; 1"/>
        <use href="#scell{d.level}"/>
      </g>
      
      <!-- 4 Puing Pecahan yang Terlempar ke 4 Arah Diagonal -->
      <g opacity="0">
        <animate attributeName="opacity" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_shard}" values="0; 0; 1; 0; 0; 0"/>
        <!-- Puing 1 (Kiri Atas) -->
        <rect x="-3" y="-3" width="5" height="5" rx="1.5" fill="{lvl_color}">
          <animateTransform attributeName="transform" type="translate" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_shard}" values="0 0; 0 0; -15 -15; -22 -22; 0 0; 0 0"/>
        </rect>
        <!-- Puing 2 (Kanan Atas) -->
        <rect x="0" y="-3" width="5" height="5" rx="1.5" fill="{lvl_color}">
          <animateTransform attributeName="transform" type="translate" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_shard}" values="0 0; 0 0; 15 -15; 22 -22; 0 0; 0 0"/>
        </rect>
        <!-- Puing 3 (Kiri Bawah) -->
        <rect x="-3" y="0" width="5" height="5" rx="1.5" fill="{lvl_color}">
          <animateTransform attributeName="transform" type="translate" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_shard}" values="0 0; 0 0; -15 15; -22 22; 0 0; 0 0"/>
        </rect>
        <!-- Puing 4 (Kanan Bawah) -->
        <rect x="0" y="0" width="5" height="5" rx="1.5" fill="{lvl_color}">
          <animateTransform attributeName="transform" type="translate" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_shard}" values="0 0; 0 0; 15 15; 22 22; 0 0; 0 0"/>
        </rect>
      </g>

      <!-- Floating XP Combat Text -->
      <text x="0" y="-14" font-size="10.5" font-weight="900" fill="#38bdf8" text-anchor="middle" opacity="0">
        +{d.count} XP
        <animate attributeName="opacity" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_shard}" values="0; 0; 1; 0; 0; 0"/>
        <animate attributeName="y" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_shard}" values="-6; -6; -20; -24; -6; -6"/>
      </text>
    </g>'''
            svg_parts.append(anim)
        else:
            svg_parts.append(f'    <g transform="translate({num(cx)} {num(cy)})"><use href="#scell{d.level}"/></g>')

    # Ground Runway Platform
    platform_top = rail_y - 6
    svg_parts.append(f'''
  <!-- Tactical Ground Runway Platform -->
  <rect x="{x0 - 14}" y="{platform_top}" width="{gw + 28}" height="32" rx="6" fill="url(#runway_gantry)" stroke="#334155" stroke-width="1.5"/>
  <line x1="{x0 - 10}" y1="{platform_top + 2}" x2="{x0 + gw + 10}" y2="{platform_top + 2}" stroke="#a855f7" stroke-width="1.4" stroke-dasharray="14 8" opacity="0.8"/>
  <!-- Glowing Marker Lights -->
  <circle cx="{x0 + 10}" cy="{platform_top + 16}" r="3" fill="#38bdf8"/>
  <circle cx="{x0 + gw // 3}" cy="{platform_top + 16}" r="3" fill="#a855f7"/>
  <circle cx="{x0 + 2 * (gw // 3)}" cy="{platform_top + 16}" r="3" fill="#a855f7"/>
  <circle cx="{x0 + gw - 10}" cy="{platform_top + 16}" r="3" fill="#38bdf8"/>
''')

    # RUTE JALAN TENTARA YANG BENAR-BENAR MULUS (0.85s Jalan Santai, Gak Ada Loncat/Teleport)
    pos_frames = []
    key_times = []
    soldier_xs = [cxp(t.col) for t in targets]

    # Titik awal
    cur_x = soldier_xs[0]
    for i, target_x in enumerate(soldier_xs):
        t_step_start = (i * step_sec) / T
        # Durasi jalan 0.85 detik yang mulus menuju target_x
        t_walk_done = (i * step_sec + 0.85) / T
        # Berhenti, bidik & tembak (0.85s -> 1.70s)
        t_fire_done = (i * step_sec + 1.70) / T

        key_times.extend([t_step_start, t_walk_done, t_fire_done])
        # Bergerak dari cur_x ke target_x secara mulus
        pos_frames.extend([f"{num(cur_x)} {rail_y}", f"{num(target_x)} {rail_y}", f"{num(target_x)} {rail_y}"])
        cur_x = target_x

    # Selesai menembak: Berjalan mulus ke tengah panggung untuk Selebrasi
    t_victory_walk = (shooting_duration + 0.9) / T
    key_times.extend([t_victory_walk, 1.0])
    pos_frames.extend([f"{num(mid_col_x)} {rail_y}", f"{num(mid_col_x)} {rail_y}"])

    key_times_str = ";".join(kt(t) for t in [0.0] + key_times[1:-1] + [1.0])
    pos_str = ";".join(pos_frames)

    # 1 PELURU EMAS KELUAR DARI SENAPAN MENUJU 1 KOTAK (KOORDINAT MUTLAK BEBAS SALAH)
    for i, target in enumerate(targets):
        sx = cxp(target.col)
        ty = cyp(target.row)
        t_fire = (i * step_sec + 1.10) / T
        t_impact = (i * step_sec + 1.35) / T
        t_end = (i * step_sec + 1.40) / T
        kts_bullet = f"0;{kt(t_fire)};{kt(t_impact)};{kt(t_end)};1"

        # Titik moncong senapan saat tentara berada di sx
        muzzle_x = sx + 8
        muzzle_y = rail_y - 38

        svg_parts.append(f'''
  <!-- 1 Peluru Emas Khusus untuk Kotak Kolom {target.col} -->
  <g opacity="0">
    <animate attributeName="opacity" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_bullet}" values="0; 1; 1; 0; 0"/>
    <g>
      <animateTransform attributeName="transform" type="translate" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_bullet}" values="{num(muzzle_x)} {num(muzzle_y)}; {num(muzzle_x)} {num(muzzle_y)}; {num(sx)} {num(ty)}; {num(sx)} {num(ty)}; {num(muzzle_x)} {num(muzzle_y)}"/>
      <!-- Proyektil Kapsul Emas + Lidah Api -->
      <ellipse cx="0" cy="0" rx="3" ry="6.5" fill="#fde047" filter="url(#bullet_glow)"/>
      <path d="M-2.5 3.5 L2.5 3.5 L0 10.5 Z" fill="#ea580c"/>
    </g>
  </g>

  <!-- 1 Selongsong Kuningan Terlontar ke Kiri -->
  <g opacity="0">
    <animate attributeName="opacity" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_bullet}" values="0; 1; 0; 0; 0"/>
    <g transform="translate({num(sx - 5)} {num(rail_y - 32)})">
      <animateTransform attributeName="transform" type="translate" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_bullet}" values="0 0; -14 12; -22 26; 0 0; 0 0"/>
      <rect x="-1.5" y="-3" width="3" height="5.5" rx="1" fill="#eab308" transform="rotate(35)"/>
    </g>
  </g>''')

    commando_art = render_arcade_commando_sprite()

    # White Comic Speech Bubble di Akhir: MENGAMBANG PAS DI ATAS HELM (y = -98)
    t_bubble_in = (shooting_duration + 0.95) / T
    t_bubble_out = 0.985
    kts_bubble = f"0;{kt(t_bubble_in)};{kt(t_bubble_in + 0.025)};{kt(t_bubble_out)};1"

    bubble_svg = f'''
    <!-- White Comic Speech Bubble Mengambang Presisi di Atas Helm -->
    <g transform="translate(0 -98)" opacity="0">
      <animate attributeName="opacity" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_bubble}" values="0; 0; 1; 1; 0"/>
      <animateTransform attributeName="transform" type="scale" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{kts_bubble}" values="0.3; 0.3; 1; 1; 0.3"/>
      
      <!-- Balon Obrolan Putih Komik dengan Ekor ke Bawah -->
      <path d="M -80 -24 H 80 A 10 10 0 0 1 90 -14 V 12 A 10 10 0 0 1 80 22 H 6 L 0 32 L -6 22 H -80 A 10 10 0 0 1 -90 12 V -14 A 10 10 0 0 1 -80 -24 Z" fill="#ffffff" stroke="#cbd5e1" stroke-width="2" filter="url(#bubble_shadow)"/>
      <text x="0" y="-3" font-size="11.5" font-weight="900" fill="#0f172a" text-anchor="middle">Yeayy, all cleared!</text>
      <text x="0" y="13" font-size="10" font-weight="800" fill="#7c3aed" text-anchor="middle">MISSION COMPLETE 🎉</text>
    </g>
    '''

    svg_parts.append(f'''
  <!-- Prajurit Cyber Commando dengan Animasi Melangkah Mulus -->
  <g transform="translate({num(soldier_xs[0])} {rail_y})">
    <animateTransform attributeName="transform" type="translate" dur="{num(T,2)}s" repeatCount="indefinite" keyTimes="{key_times_str}" values="{pos_str}"/>
    
    <!-- Animasi Marching Bobbing Kaki Saat Melangkah -->
    <g>
      <animateTransform attributeName="transform" type="translate" dur="0.32s" repeatCount="indefinite" values="0 0; 0 -3; 0 0; 0 -2; 0 0"/>
      {commando_art}
      
      <!-- Muzzle Flash Api Tembakan -->
      <g transform="translate(13 -42)" opacity="0">
        <animate attributeName="opacity" dur="{num(step_sec,2)}s" repeatCount="indefinite" keyTimes="0;0.50;0.55;0.62;1" values="0; 0; 1; 0; 0"/>
        <circle r="7.5" fill="#fde047" filter="url(#bullet_glow)"/>
        <circle r="3.5" fill="#ffffff"/>
      </g>

      {bubble_svg}
    </g>
  </g>
''')

    svg_parts.append("</svg>")
    return "".join(svg_parts)

# ==================== ELEGANT NATIVE ACTIVITY GRAPH (NO AI SLOP) ====================
def build_native_activity_svg(days, user):
    day_map = {d.date: d.count for d in days}
    today = dt.date.today()
    start_date = today - dt.timedelta(days=363)
    
    total_year = sum(day_map.get((start_date + dt.timedelta(days=i)).isoformat(), 0) for i in range(364))

    week_totals = []
    week_start_dates = []
    for w in range(52):
        w_start = start_date + dt.timedelta(days=w * 7)
        w_count = sum(day_map.get((w_start + dt.timedelta(days=k)).isoformat(), 0) for k in range(7))
        week_totals.append(w_count)
        week_start_dates.append(w_start)

    max_c = max(max(week_totals), 1)

    W, H = 840, 250
    x_start, x_end = 320, 780
    y_top, y_bottom = 54, 196
    step_x = (x_end - x_start) / 51.0

    pts = []
    for i, cnt in enumerate(week_totals):
        px = x_start + i * step_x
        py = y_bottom - (cnt / max_c) * (y_bottom - y_top)
        pts.append((px, py))

    d_segs = [f"M {num(pts[0][0])} {num(pts[0][1])}"]
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2

        cp1x = p1[0] + (p2[0] - p0[0]) / 6.0
        cp1y = p1[1] + (p2[1] - p0[1]) / 6.0
        cp2x = p2[0] - (p3[0] - p1[0]) / 6.0
        cp2y = p2[1] - (p3[1] - p1[1]) / 6.0

        cp1y = max(y_top, min(y_bottom, cp1y))
        cp2y = max(y_top, min(y_bottom, cp2y))
        d_segs.append(f"C {num(cp1x)} {num(cp1y)}, {num(cp2x)} {num(cp2y)}, {num(p2[0])} {num(p2[1])}")

    line_path = " ".join(d_segs)
    area_path = f"{line_path} L {num(pts[-1][0])} {y_bottom} L {num(pts[0][0])} {y_bottom} Z"

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    date_labels = []
    prev_month = -1
    for i, d_obj in enumerate(week_start_dates):
        if d_obj.month != prev_month and i < 50:
            date_labels.append(f'<text x="{num(pts[i][0])}" y="{y_bottom + 18}" font-size="10.5" font-weight="600" fill="#94a3b8" text-anchor="middle">{month_names[d_obj.month - 1]}</text>')
            prev_month = d_obj.month

    grid_lines = []
    for frac in (0.33, 0.66, 1.0):
        y_pos = y_bottom - frac * (y_bottom - y_top)
        val = int(max_c * frac)
        grid_lines.append(f'<line x1="{x_start}" y1="{num(y_pos)}" x2="{x_end}" y2="{num(y_pos)}" stroke="#1e2638" stroke-width="1" stroke-dasharray="3 4"/>')
        grid_lines.append(f'<text x="{x_end + 12}" y="{num(y_pos + 4)}" font-size="10" font-weight="600" fill="#64748b">{val}</text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">
  <defs>
    <linearGradient id="card_bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0e131d"/>
      <stop offset="100%" stop-color="#06090e"/>
    </linearGradient>
    <linearGradient id="wave_aurora" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#c084fc" stop-opacity="0.55"/>
      <stop offset="50%" stop-color="#7e22ce" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#3b0764" stop-opacity="0.0"/>
    </linearGradient>
    <linearGradient id="border_line" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.85"/>
      <stop offset="50%" stop-color="#6366f1" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="#a855f7" stop-opacity="0.85"/>
    </linearGradient>
    <filter id="laser_glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3.0" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
    .hd_name {{ font-size: 19px; font-weight: 800; letter-spacing: 0.03em; fill: #ffffff; }}
    .hd_user {{ font-size: 11.5px; font-weight: 700; fill: #a855f7; }}
    .st_main {{ font-size: 13.5px; font-weight: 600; fill: #e2e8f0; }}
    .st_sub {{ font-size: 11px; fill: #94a3b8; }}
  </style>

  <!-- Card Body & Border -->
  <rect width="{W}" height="{H}" rx="14" fill="url(#card_bg)"/>
  <rect width="{W}" height="{H}" rx="14" fill="none" stroke="url(#border_line)" stroke-width="1.4"/>

  <!-- Left Authentic Credentials Column -->
  <text class="hd_name" x="34" y="44">Rixsan Joulfiand</text>
  <text class="hd_user" x="34" y="62">@{escape(user)}</text>

  <!-- Credential 1: Total Contributions -->
  <g transform="translate(34, 94)">
    <circle cx="10" cy="10" r="10" fill="#7e22ce" opacity="0.3"/>
    <svg x="2" y="2" width="16" height="16" viewBox="0 0 24 24" fill="#c084fc"><path d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.1-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z"/></svg>
    <text class="st_main" x="30" y="14"><tspan font-weight="700" fill="#a855f7">{total_year}</tspan> Contributions</text>
    <text class="st_sub" x="30" y="28">in the last year</text>
  </g>

  <!-- Credential 2: Architecture & Repositories -->
  <g transform="translate(34, 144)">
    <circle cx="10" cy="10" r="10" fill="#7e22ce" opacity="0.3"/>
    <svg x="2" y="2" width="16" height="16" viewBox="0 0 24 24" fill="#c084fc"><path d="M4 3h16a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zm0 2v14h16V5H4zm3 3h10v2H7V8zm0 4h10v2H7v-2z"/></svg>
    <text class="st_main" x="30" y="14">Public Architectures</text>
    <text class="st_sub" x="30" y="28">Full-Stack Ecosystems</text>
  </g>

  <!-- Credential 3: Engineering Consistency -->
  <g transform="translate(34, 194)">
    <circle cx="10" cy="10" r="10" fill="#7e22ce" opacity="0.3"/>
    <svg x="2" y="2" width="16" height="16" viewBox="0 0 24 24" fill="#c084fc"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm1 14.5h-2v-2h2v2zm0-4h-2V7h2v5.5z"/></svg>
    <text class="st_main" x="30" y="14">Active Engineering</text>
    <text class="st_sub" x="30" y="28">Continuous Development</text>
  </g>

  <!-- Right Chart Section -->
  <text x="{x_end}" y="38" font-size="11" font-weight="700" letter-spacing="0.06em" fill="#a855f7" text-anchor="end">CONTRIBUTIONS IN THE LAST YEAR</text>
  {''.join(grid_lines)}

  <!-- Smooth Aurora Area & Pure Laser Line -->
  <path d="{area_path}" fill="url(#wave_aurora)"/>
  <path d="{line_path}" fill="none" stroke="#a855f7" stroke-width="4.8" opacity="0.4" filter="url(#laser_glow)"/>
  <path d="{line_path}" fill="none" stroke="#f3e8ff" stroke-width="2.4"/>

  {''.join(date_labels)}
</svg>'''
    return svg

# ==================== PAC-MAN ARCADE ENGINE ====================
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

    # 1. Generate Pac-Man SVGs
    pacman_svg = build_svg(days, args.user, args.title)
    for fn in ("pacman-contribution-graph-dark.svg", "pacman-contribution-graph.svg"):
        with open(os.path.join(args.out, fn), "w", encoding="utf-8") as f:
            f.write(pacman_svg)
    print(f"[SUCCESS] Pac-Man SVGs berhasil dibuat di {args.out}/")

    # 2. Generate 8-Bit Cyber Commando Striker SVG (Precision 1-to-1 Destruction)
    soldier_svg = build_soldier_shooter_svg(days, args.user)
    with open(os.path.join(args.out, "soldier-contribution-graph-dark.svg"), "w", encoding="utf-8") as f:
        f.write(soldier_svg)
    print(f"[SUCCESS] Arcade Commando Striker SVG dibuat di {args.out}/soldier-contribution-graph-dark.svg")

    # 3. Generate Clean, Elegant Activity Graph (No AI Slop)
    activity_svg = build_native_activity_svg(days, args.user)
    with open(os.path.join(args.out, "activity-graph.svg"), "w", encoding="utf-8") as f:
        f.write(activity_svg)
    print(f"[SUCCESS] Elegant Activity Graph SVG dibuat di {args.out}/activity-graph.svg")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
