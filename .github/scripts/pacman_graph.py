#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pac-Man Cyberpunk Matrix + 8-Bit Cyber Tank & BBTAN Reclining Commando Striker
Pure Native SVG Vector Physics - Zero External Dependencies
"""
import argparse
import datetime as dt
import json
import math
import os
import random
import re
import sys
import urllib.request

PALETTES = {
    "purple": dict(
        card_a="#0d1117", card_b="#06080d", tile="#131722", tile_edge="#1f2638",
        levels=["#3b0764", "#6b21a8", "#9333ea", "#c084fc"],
        accent="#a855f7", glow="#c084fc", text="#f5f3ff", muted="#94a3b8"
    )
}

S, G = 15, 4
P = S + G

def num(x, n=2):
    s = f"{x:.{n}f}"
    if "." in s: s = s.rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s

def kt(x): return num(min(1.0, max(0.0, x)), 5)

# ==============================================================================
# DATA FETCHER (GRAPHQL + PUBLIC SCRAPING FALLBACK)
# ==============================================================================
def fetch_contributions(username, token=None):
    if token:
        try:
            query = """
            query($user: String!) {
              user(login: $user) {
                contributionsCollection {
                  contributionCalendar {
                    totalContributions
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
            }"""
            req = urllib.request.Request(
                "https://api.github.com/graphql",
                data=json.dumps({"query": query, "variables": {"user": username}}).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}", "User-Agent": "PacmanGraphGen"}
            )
            with urllib.request.urlopen(req, timeout=12) as res:
                data = json.loads(res.read().decode("utf-8"))
                cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
                weeks = []
                lvl_map = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
                for w in cal["weeks"]:
                    days = []
                    for d in w["contributionDays"]:
                        days.append({
                            "date": d["date"],
                            "count": d["contributionCount"],
                            "level": lvl_map.get(d["contributionLevel"], 0)
                        })
                    if days: weeks.append(days)
                return {"total": cal["totalContributions"], "weeks": weeks}
        except Exception as e:
            sys.stderr.write(f"GraphQL warning: {e}. Falling back to public feed.\n")

    try:
        url = f"https://github.com/users/{username}/contributions"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as res:
            html = res.read().decode("utf-8")
        
        m_tot = re.search(r'([0-9,]+)\s+contributions?\s+in\s+the\s+last\s+year', html)
        total = int(m_tot.group(1).replace(",", "")) if m_tot else 1342
        
        days_found = []
        for d_m in re.finditer(r'data-date="([^"]+)"[^>]*data-level="([0-9])"', html):
            date, lvl = d_m.group(1), int(d_m.group(2))
            cnt = 1 if lvl > 0 else 0
            cnt_m = re.search(r'([0-9]+)\s+contribution', d_m.group(0))
            if cnt_m: cnt = int(cnt_m.group(1))
            days_found.append({"date": date, "count": cnt, "level": lvl})
        
        if days_found:
            weeks, cur = [], []
            for d in days_found:
                dt_obj = dt.datetime.strptime(d["date"], "%Y-%m-%d")
                wday = (dt_obj.weekday() + 1) % 7
                if wday == 0 and cur:
                    weeks.append(cur)
                    cur = []
                cur.append(d)
            if cur: weeks.append(cur)
            return {"total": total, "weeks": weeks}
    except Exception as e:
        sys.stderr.write(f"Scraper warning: {e}. Using deterministic fallback.\n")

    random.seed(42)
    weeks = []
    base = dt.date.today() - dt.timedelta(days=364)
    for w in range(52):
        days = []
        for d in range(7):
            cur_d = base + dt.timedelta(days=w * 7 + d)
            cnt = random.choices([0, 2, 5, 11, 23], weights=[0.45, 0.25, 0.15, 0.1, 0.05])[0]
            lvl = 0 if cnt == 0 else (1 if cnt < 4 else (2 if cnt < 9 else (3 if cnt < 18 else 4)))
            days.append({"date": cur_d.strftime("%Y-%m-%d"), "count": cnt, "level": lvl})
        weeks.append(days)
    return {"total": 1342, "weeks": weeks}

# ==============================================================================
# CYBER TANK & BBTAN MULTI-BALL RICOCHET COMMANDO GENERATOR
# ==============================================================================
def build_soldier_shooter_svg(data, palette):
    pal = PALETTES.get(palette, PALETTES["purple"])
    raw_weeks = data["weeks"][-36:] if len(data["weeks"]) >= 36 else data["weeks"]
    total_commits = data.get("total", 1342)

    gw = len(raw_weeks)
    width = 920
    height = 430
    grid_ox = 75
    grid_oy = 70
    RUNWAY_Y = 340  # Super lega!

    TANK_X = 540
    TANK_Y = RUNWAY_Y
    CHAIR_X = 260
    CHAIR_Y = RUNWAY_Y

    T_TOTAL = 18.0

    # Kumpulkan target kotak aktif
    all_targets = []
    for c, col in enumerate(raw_weeks):
        for r, day in enumerate(col):
            lvl = day.get("level", 0)
            if lvl > 0:
                tx = grid_ox + c * P + S // 2
                ty = grid_oy + r * P + S // 2
                all_targets.append({"c": c, "r": r, "lvl": lvl, "x": tx, "y": ty})

    if len(all_targets) < 20:
        for extra_c in range(2, gw - 2, 2):
            for extra_r in [1, 3, 5]:
                tx = grid_ox + extra_c * P + S // 2
                ty = grid_oy + extra_r * P + S // 2
                all_targets.append({"c": extra_c, "r": extra_r, "lvl": 2, "x": tx, "y": ty})

    # Sort secara spasial
    all_targets.sort(key=lambda t: (t["c"], t["r"]))
    max_targets = min(28, len(all_targets))
    step = len(all_targets) / max_targets
    targets = [all_targets[int(i * step)] for i in range(max_targets)]
    N_TARGETS = len(targets)

    css = [
        f".card-bg {{ fill: {pal['card_a']}; }}",
        f".glow-border {{ stroke: {pal['accent']}; stroke-width: 1.5; fill: none; }}",
        f".text-head {{ fill: {pal['text']}; font-family: 'Courier New', monospace; font-weight: bold; font-size: 14px; letter-spacing: 2px; }}",
        f".text-stat {{ fill: {pal['glow']}; font-family: 'Courier New', monospace; font-size: 12px; }}",
        f".runway {{ stroke: {pal['tile_edge']}; stroke-dasharray: 4 6; stroke-width: 2; }}",
        f".runway-glow {{ stroke: {pal['accent']}; stroke-width: 1; opacity: 0.3; }}",
    ]

    # 1. Animasi Tentara: Bawa Peluru -> Isi Tank -> Jalan ke Kursi -> Rebahan -> Lompat Senang
    soldier_kf = f"""
    @keyframes commandoStory {{
      /* 0s - 1.5s: Berjalan bawa peluru ke Tank di X={TANK_X - 45} */
      0% {{ transform: translate({CHAIR_X}px, {RUNWAY_Y}px); }}
      8.33% {{ transform: translate({TANK_X - 45}px, {RUNWAY_Y}px); }}
      /* 1.5s - 2.8s: Masukkan peluru ke tank hatch */
      15.55% {{ transform: translate({TANK_X - 45}px, {RUNWAY_Y}px); }}
      /* 2.8s - 5.2s: Jalan santai ke kursi */
      28.88% {{ transform: translate({CHAIR_X}px, {RUNWAY_Y}px); }}
      /* 5.2s - 14.2s: Rebahan di kursi (posisi tepat di kursi) */
      78.88% {{ transform: translate({CHAIR_X}px, {RUNWAY_Y}px); }}
      /* 14.5s - 17.5s: Lompat kegirangan selebrasi! */
      81.0% {{ transform: translate({CHAIR_X + 20}px, {RUNWAY_Y}px); }}
      97.2% {{ transform: translate({CHAIR_X + 20}px, {RUNWAY_Y}px); }}
      100% {{ transform: translate({CHAIR_X}px, {RUNWAY_Y}px); }}
    }}
    .soldier-actor {{
      animation: commandoStory {T_TOTAL}s infinite ease-in-out;
    }}
    """
    css.append(soldier_kf)

    # State Pergantian Tampilan Tentara (Bawa Peluru -> Rebahan -> Lompat Senang)
    css.append(f"""
    /* Mode Bawa Peluru & Jalan */
    @keyframes showWalkCarry {{
      0%, 28.5% {{ opacity: 1; }}
      28.6%, 100% {{ opacity: 0; }}
    }}
    .state-walk {{ animation: showWalkCarry {T_TOTAL}s infinite; }}

    /* Mode Rebahan Chill di Kursi Pantai */
    @keyframes showRecline {{
      0%, 28.5% {{ opacity: 0; }}
      28.6%, 78.8% {{ opacity: 1; }}
      78.9%, 100% {{ opacity: 0; }}
    }}
    .state-recline {{ animation: showRecline {T_TOTAL}s infinite; }}

    /* Mode Lompat Senang (Happy Jump & Smile) */
    @keyframes showVictoryJump {{
      0%, 78.8% {{ opacity: 0; }}
      78.9%, 98.0% {{ opacity: 1; }}
      98.1%, 100% {{ opacity: 0; }}
    }}
    @keyframes happyBouncing {{
      0%, 100% {{ transform: translateY(0px); }}
      50% {{ transform: translateY(-16px); }}
    }}
    .state-jump {{
      animation: showVictoryJump {T_TOTAL}s infinite;
    }}
    .jumping-figure {{
      animation: happyBouncing 0.4s infinite ease-in-out;
    }}
    """)

    # 2. Animasi Tank Recoil & Muzzle Blast (Tembak di t=2.6s ~ 14.44%)
    css.append(f"""
    @keyframes tankRecoil {{
      0%, 14.0% {{ transform: translate(0px, 0px); }}
      14.7% {{ transform: translate(-6px, 1px); }}
      16.5% {{ transform: translate(0px, 0px); }}
      100% {{ transform: translate(0px, 0px); }}
    }}
    .tank-barrel {{ animation: tankRecoil {T_TOTAL}s infinite ease-out; }}

    @keyframes muzzleFlash {{
      0%, 14.2% {{ opacity: 0; transform: scale(0.1); }}
      14.6% {{ opacity: 1; transform: scale(1.6); }}
      15.5%, 100% {{ opacity: 0; transform: scale(0.2); }}
    }}
    .muzzle-blast {{
      animation: muzzleFlash {T_TOTAL}s infinite ease-out;
      transform-origin: {TANK_X + 22}px {TANK_Y - 38}px;
    }}
    """)

    # 3. Animasi Drone Helikopter Drop Kursi Santai
    css.append(f"""
    @keyframes heliFlight {{
      0%, 16.0% {{ transform: translate(-100px, 160px); opacity: 0; }}
      18.0% {{ opacity: 1; }}
      30.0%, 33.0% {{ transform: translate({CHAIR_X}px, 255px); opacity: 1; }}
      42.0% {{ transform: translate({width + 100}px, 180px); opacity: 1; }}
      42.1%, 100% {{ opacity: 0; }}
    }}
    .heli-unit {{ animation: heliFlight {T_TOTAL}s infinite ease-in-out; }}

    @keyframes rotorFast {{
      0% {{ transform: scaleX(1); }}
      50% {{ transform: scaleX(0.05); }}
      100% {{ transform: scaleX(1); }}
    }}
    .heli-rotor {{ animation: rotorFast 0.08s infinite linear; transform-origin: center; }}

    @keyframes chairDrop {{
      0%, 30.0% {{ opacity: 0; transform: translateY(-40px); }}
      33.0%, 97.0% {{ opacity: 1; transform: translateY(0px); }}
      100% {{ opacity: 0; }}
    }}
    .chair-placed {{ animation: chairDrop {T_TOTAL}s infinite ease-out; }}
    """)

    # 4. Mekanisme BBTAN Multi-Ball Ricochet (Peluru Bertambah & Mantul-mantul)
    # Peluru 1 meluncur dari Tank Muzzle -> membelah jadi Ball 2, 3, 4, 5, 6, 7, 8
    # Setiap peluru menghancurkan satu set kotak secara berurutan
    bullet_elements = []
    shatter_elements = []

    # Buat 8 Ball Bouncers dengan rute ricochet masing-masing
    N_BALLS = 8
    ball_start_times = [2.7, 3.8, 4.8, 5.8, 6.7, 7.6, 8.5, 9.4] # Tiap tabrakan melahirkan peluru baru!
    ball_colors = ["#facc15", "#38bdf8", "#ec4899", "#a855f7", "#4ade80", "#f97316", "#e879f9", "#ffffff"]

    # Alokasi target ke masing-masing bola yang mantul
    target_hit_schedule = {}
    for i, tgt in enumerate(targets):
        b_idx = i % N_BALLS
        hit_time = ball_start_times[b_idx] + (i // N_BALLS) * 1.35 + 0.35
        target_hit_schedule[(tgt["c"], tgt["r"])] = (i, hit_time, tgt)

    # Generate Animasi Bouncing untuk Setiap Bola
    MUZZLE_X = TANK_X + 22
    MUZZLE_Y = TANK_Y - 38

    for b in range(N_BALLS):
        b_name = f"bbtan_ball_{b}"
        t_birth = ball_start_times[b]
        t_end = 14.2 # Semua bola selesai saat panggung bersih

        # Ambil titik-titik tabrakan kotak untuk bola ini
        assigned_targets = [tgt for (k, (idx, htime, tgt)) in target_hit_schedule.items() if idx % N_BALLS == b]
        
        # Buat lintasan pantul (Muzzle / Spawn -> Target 1 -> Wall -> Target 2 -> Wall...)
        pts = [(MUZZLE_X if b == 0 else targets[b-1]["x"], MUZZLE_Y if b == 0 else targets[b-1]["y"])]
        for at in assigned_targets:
            pts.append((at["x"], at["y"]))
            # Titik pantul dinding kotak
            wall_x = random.choice([grid_ox + 10, grid_ox + gw * P - 10])
            wall_y = random.choice([grid_oy + 5, grid_oy + 7 * P - 5])
            pts.append((wall_x, wall_y))

        # CSS Keyframes untuk bola mantul
        bk = [f"@keyframes {b_name} {{"]
        bk.append(f"  0%, {kt((t_birth - 0.05) / T_TOTAL * 100)}% {{ opacity: 0; transform: translate({pts[0][0]}px, {pts[0][1]}px); }}")
        bk.append(f"  {kt(t_birth / T_TOTAL * 100)}% {{ opacity: 1; transform: translate({pts[0][0]}px, {pts[0][1]}px); }}")

        dur = t_end - t_birth
        for step_i, (px, py) in enumerate(pts[1:]):
            cur_t = t_birth + ((step_i + 1) / len(pts[1:])) * dur
            bk.append(f"  {kt(cur_t / T_TOTAL * 100)}% {{ opacity: 1; transform: translate({px}px, {py}px); }}")

        bk.append(f"  {kt(t_end / T_TOTAL * 100)}%, 100% {{ opacity: 0; transform: translate({pts[-1][0]}px, {pts[-1][1]}px); }}")
        bk.append("}")
        css.append("\n".join(bk))

        b_color = ball_colors[b]
        bullet_elements.append(
            f'<g style="animation: {b_name} {T_TOTAL}s infinite linear;">'
            f'  <circle cx="0" cy="0" r="4.5" fill="{b_color}" filter="url(#glow)"/>'
            f'  <circle cx="0" cy="0" r="2" fill="#ffffff"/>'
            f'</g>'
        )

    # Generate Animasi Shatter (Hancur Total & Serpihan Puing) untuk Setiap Kotak
    for (c, r), (idx, th, tgt) in target_hit_schedule.items():
        bx, by = tgt["x"], tgt["y"]
        box_kf = f"shatter_box_{idx}"
        sbk = [f"@keyframes {box_kf} {{"]
        sbk.append(f"  0%, {kt((th - 0.02) / T_TOTAL * 100)}% {{ transform: scale(1); opacity: 1; }}")
        sbk.append(f"  {kt(th / T_TOTAL * 100)}% {{ transform: scale(1.4); opacity: 1; }}")
        sbk.append(f"  {kt((th + 0.05) / T_TOTAL * 100)}%, {kt(17.5 / T_TOTAL * 100)}% {{ transform: scale(0); opacity: 0; }}")
        sbk.append(f"  100% {{ transform: scale(1); opacity: 1; }}")
        sbk.append("}")
        css.append("\n".join(sbk))

        shards_kf = f"shards_burst_{idx}"
        shk = [f"@keyframes {shards_kf} {{"]
        shk.append(f"  0%, {kt((th - 0.01) / T_TOTAL * 100)}% {{ opacity: 0; transform: scale(0); }}")
        shk.append(f"  {kt(th / T_TOTAL * 100)}% {{ opacity: 1; transform: scale(1); }}")
        shk.append(f"  {kt((th + 0.3) / T_TOTAL * 100)}% {{ opacity: 0.9; transform: scale(1.6); }}")
        shk.append(f"  {kt((th + 0.5) / T_TOTAL * 100)}%, 100% {{ opacity: 0; transform: scale(2.0); }}")
        shk.append("}")
        css.append("\n".join(shk))

        sh_color = pal["levels"][tgt["lvl"] - 1]
        shatter_elements.append(
            f'<g style="animation: {shards_kf} {T_TOTAL}s infinite ease-out; transform-origin: {bx}px {by}px;">'
            f'  <rect x="{bx - 7}" y="{by - 7}" width="4" height="4" rx="1" fill="{sh_color}"/>'
            f'  <rect x="{bx + 4}" y="{by - 7}" width="4" height="4" rx="1" fill="#facc15"/>'
            f'  <rect x="{bx - 7}" y="{by + 4}" width="4" height="4" rx="1" fill="{pal["glow"]}"/>'
            f'  <rect x="{bx + 4}" y="{by + 4}" width="4" height="4" rx="1" fill="{sh_color}"/>'
            f'</g>'
        )

    # Render Grid Matriks Kontribusi
    grid_rects = []
    for c, col in enumerate(raw_weeks):
        for r, day in enumerate(col):
            x = grid_ox + c * P
            y = grid_oy + r * P
            lvl = day.get("level", 0)

            # Slot dasar gelap
            grid_rects.append(f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="3" fill="{pal["tile"]}" stroke="{pal["tile_edge"]}" stroke-width="1"/>')

            if (c, r) in target_hit_schedule:
                idx, th, tgt = target_hit_schedule[(c, r)]
                color = pal["levels"][lvl - 1]
                grid_rects.append(
                    f'<g style="animation: shatter_box_{idx} {T_TOTAL}s infinite; transform-origin: {x + S//2}px {y + S//2}px;">'
                    f'  <rect x="{x}" y="{y}" width="{S}" height="{S}" rx="3" fill="{color}" stroke="{pal["accent"]}" stroke-width="0.8"/>'
                    f'</g>'
                )
            elif lvl > 0:
                color = pal["levels"][lvl - 1]
                grid_rects.append(f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="3" fill="{color}" stroke="{pal["accent"]}" stroke-width="0.8"/>')

    # ==========================================================================
    # VECTOR ASSETS: TANK, HELICOPTER, CHAIR, SOLDIER STATES
    # ==========================================================================
    # 1. Cyber Tank
    tank_svg = f"""
    <g transform="translate({TANK_X}, {TANK_Y})">
      <!-- Shadow -->
      <ellipse cx="0" cy="5" rx="38" ry="7" fill="#000000" opacity="0.5"/>
      <!-- Tracks / Roda Rantai -->
      <rect x="-34" y="-8" width="68" height="14" rx="7" fill="#111827" stroke="#374151" stroke-width="1.5"/>
      <circle cx="-24" cy="-1" r="4" fill="#4b5563"/>
      <circle cx="-12" cy="-1" r="4" fill="#4b5563"/>
      <circle cx="0" cy="-1" r="4" fill="#4b5563"/>
      <circle cx="12" cy="-1" r="4" fill="#4b5563"/>
      <circle cx="24" cy="-1" r="4" fill="#4b5563"/>
      <!-- Badan Tank / Armored Hull -->
      <polygon points="-30,-8 30,-8 24,-20 -24,-20" fill="#312e81" stroke="#4f46e5" stroke-width="1"/>
      <!-- Lampu Indikator Cyan -->
      <rect x="-18" y="-16" width="36" height="3" rx="1.5" fill="#00e5ff" filter="url(#glow)"/>
      <!-- Kubah Turret & Meriam Laras Panjang (Recoil Effect) -->
      <g class="tank-barrel">
        <rect x="-14" y="-28" width="28" height="10" rx="4" fill="#1e1b4b" stroke="#6366f1" stroke-width="1"/>
        <!-- Laras Mengarah Diagonal ke Grid (Sudut -38 Derajat) -->
        <g transform="rotate(-38, 0, -23)">
          <rect x="6" y="-26" width="36" height="6" rx="2" fill="#0f172a" stroke="#38bdf8" stroke-width="1"/>
          <!-- Muzzle Brake -->
          <rect x="38" y="-28" width="6" height="10" rx="1.5" fill="#facc15" filter="url(#glow)"/>
        </g>
      </g>
      <!-- Hatch Masuk Peluru -->
      <rect x="-18" y="-25" width="8" height="4" rx="1" fill="#4338ca"/>
      <!-- Muzzle Flash Starburst -->
      <g class="muzzle-blast" transform="translate(22, -38)">
        <polygon points="0,-14 4,-4 14,0 4,4 0,14 -4,4 -14,0 -4,-4" fill="#facc15" filter="url(#glow)"/>
        <circle cx="0" cy="0" r="5" fill="#ffffff"/>
      </g>
    </g>
    """

    # 2. Helikopter Mini Drop Kursi
    heli_svg = """
    <g class="heli-unit">
      <!-- Baling-Baling Utama -->
      <line x1="-30" y1="-28" x2="30" y2="-28" stroke="#38bdf8" stroke-width="3" class="heli-rotor" filter="url(#glow)"/>
      <rect x="-2" y="-28" width="4" height="6" fill="#1e293b"/>
      <!-- Bodi Mini Helikopter Taktis -->
      <ellipse cx="0" cy="-14" rx="20" ry="11" fill="#1e1b4b" stroke="#a855f7" stroke-width="1.5"/>
      <!-- Kaca Kokpit Cyan -->
      <path d="M 6 -20 Q 18 -14 14 -8 L 4 -8 Z" fill="#00e5ff" filter="url(#glow)"/>
      <!-- Ekor & Baling-Baling Belakang -->
      <line x1="-20" y1="-14" x2="-38" y2="-17" stroke="#312e81" stroke-width="3"/>
      <rect x="-41" y="-22" width="3" height="10" rx="1" fill="#38bdf8" class="heli-rotor"/>
      <!-- Winch Cable Menurunkan Kursi -->
      <line x1="0" y1="-3" x2="0" y2="40" stroke="#facc15" stroke-width="1.5" stroke-dasharray="2 2"/>
    </g>
    """

    # 3. Kursi Santai Pantai / Lounge Chair
    chair_svg = f"""
    <g transform="translate({CHAIR_X}, {CHAIR_Y})" class="chair-placed">
      <!-- Shadow Kursi -->
      <ellipse cx="6" cy="4" rx="22" ry="5" fill="#000000" opacity="0.4"/>
      <!-- Rangka Kursi Santai (Reclined Wood / Metal Frame) -->
      <line x1="-16" y1="2" x2="22" y2="2" stroke="#64748b" stroke-width="2.5"/>
      <line x1="-16" y1="2" x2="-4" y2="-22" stroke="#cbd5e1" stroke-width="3"/>
      <line x1="-4" y1="-22" x2="24" y2="-12" stroke="#cbd5e1" stroke-width="3"/>
      <line x1="-12" y1="2" x2="6" y2="-18" stroke="#64748b" stroke-width="2"/>
      <!-- Kain Matras Ungu Cyberpunk -->
      <line x1="-3" y1="-22" x2="23" y2="-12" stroke="#c084fc" stroke-width="4" stroke-linecap="round" filter="url(#glow)"/>
      <line x1="-3" y1="-22" x2="23" y2="-12" stroke="#a855f7" stroke-width="2" stroke-linecap="round"/>
      <!-- Bantal Mini -->
      <circle cx="-1" cy="-21" r="3.5" fill="#facc15"/>
    </g>
    """

    # 4. Tiga State Karakter Tentara:
    # A. State Jalan Membawa Peluru Artileri
    soldier_walk_svg = """
    <g class="state-walk">
      <!-- Shadow -->
      <ellipse cx="0" cy="3" rx="10" ry="3.5" fill="#000000" opacity="0.4"/>
      <!-- Boots & Legs -->
      <rect x="-6" y="-6" width="5" height="7" rx="1" fill="#1e1b4b"/>
      <rect x="2" y="-6" width="5" height="7" rx="1" fill="#1e1b4b"/>
      <!-- Torso -->
      <rect x="-6" y="-20" width="13" height="15" rx="2.5" fill="#312e81"/>
      <rect x="-3" y="-18" width="8" height="11" rx="1" fill="#4f46e5"/>
      <!-- Helm & Visor -->
      <rect x="-5" y="-32" width="12" height="11" rx="3" fill="#1e1b4b"/>
      <rect x="0" y="-29" width="8" height="4" rx="1.5" fill="#00e5ff" filter="url(#glow)"/>
      <!-- Tangan Mengangkat Peluru Artileri Emas -->
      <g transform="translate(6, -18) rotate(-20)">
        <polygon points="0,-4 14,-2 14,4 0,2" fill="#facc15" filter="url(#glow)"/>
        <rect x="0" y="-3" width="12" height="6" rx="2" fill="#eab308"/>
        <circle cx="12" cy="0" r="2.5" fill="#ffffff"/>
      </g>
    </g>
    """

    # B. State Duduk Rebahan Santai di Kursi (Pake Kacamata Hitam Chill)
    soldier_recline_svg = """
    <g class="state-recline" transform="translate(4, -12)">
      <!-- Tubuh Rebahan di Matras Kursi -->
      <g transform="rotate(18, 0, 0)">
        <!-- Kaki Santai Menyilang -->
        <rect x="8" y="-2" width="14" height="5" rx="2" fill="#4338ca"/>
        <rect x="18" y="-4" width="6" height="5" rx="1.5" fill="#1e1b4b"/>
        <!-- Badan Bersandar Santai -->
        <rect x="-8" y="-8" width="17" height="12" rx="3" fill="#312e81"/>
        <!-- Helm Nyender di Bantal -->
        <rect x="-16" y="-12" width="12" height="11" rx="3" fill="#1e1b4b"/>
        <!-- Kacamata Hitam Thug Life / Chill Shades -->
        <rect x="-12" y="-9" width="9" height="3.5" rx="1" fill="#00e5ff" filter="url(#glow)"/>
        <!-- Tangan Santai di Belakang Kepala -->
        <circle cx="-8" cy="-11" r="3" fill="#fbbf24"/>
      </g>
      <!-- Ikon Zzz / Musik Santai Melayang -->
      <text x="-12" y="-24" font-family="'Courier New', monospace" font-size="11" font-weight="bold" fill="#38bdf8" filter="url(#glow)">♪ CHILL ♪</text>
    </g>
    """

    # C. State Lompat-Lompat Gembira Tersenyum (Victory Celebration)
    soldier_victory_svg = """
    <g class="state-jump">
      <g class="jumping-figure">
        <!-- Shadow Dinamis Mengikuti Lompatan -->
        <ellipse cx="0" cy="5" rx="12" ry="4" fill="#000000" opacity="0.3"/>
        <!-- Kaki Melayang Riang -->
        <rect x="-8" y="-14" width="5" height="11" rx="1.5" fill="#4338ca" transform="rotate(-15)"/>
        <rect x="4" y="-14" width="5" height="11" rx="1.5" fill="#4338ca" transform="rotate(15)"/>
        <rect x="-11" y="-4" width="6" height="5" rx="1" fill="#1e1b4b"/>
        <rect x="6" y="-4" width="6" height="5" rx="1" fill="#1e1b4b"/>
        <!-- Torso -->
        <rect x="-7" y="-28" width="15" height="15" rx="3" fill="#312e81"/>
        <rect x="-4" y="-25" width="9" height="10" rx="1.5" fill="#4f46e5"/>
        <!-- Kedua Tangan Diangkat ke Atas Penuh Kegirangan -->
        <rect x="-12" y="-36" width="4" height="14" rx="2" fill="#fbbf24" transform="rotate(-25)"/>
        <rect x="9" y="-36" width="4" height="14" rx="2" fill="#fbbf24" transform="rotate(25)"/>
        <!-- Wajah Ceria Tersenyum Lebar (≧▽≦) -->
        <circle cx="0.5" cy="-35" r="7.5" fill="#fbbf24"/>
        <!-- Mata Tersenyum Bahagia -->
        <path d="M -4 -36 Q -2 -39 0 -36" stroke="#0f172a" stroke-width="1.5" fill="none"/>
        <path d="M 1 -36 Q 3 -39 5 -36" stroke="#0f172a" stroke-width="1.5" fill="none"/>
        <!-- Senyum Lebar Terbuka -->
        <path d="M -2.5 -33 Q 0.5 -30 3.5 -33 Z" fill="#ef4444"/>
        <!-- Helm Terangkat ke Atas -->
        <path d="M -8 -40 Q 0.5 -46 9 -40 Z" fill="#1e1b4b" stroke="#a855f7" stroke-width="1"/>
        <!-- Ikon Bintang & Selebrasi Melayang -->
        <text x="0" y="-52" text-anchor="middle" font-family="'Segoe UI', sans-serif" font-size="14" font-weight="900" fill="#facc15" filter="url(#glow)">★ YEAYY! ALL CLEARED! ★</text>
      </g>
    </g>
    """

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
  <defs>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2.5" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <filter id="drop-shadow" x="-30%" y="-30%" width="160%" height="160%">
      <feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="#000000" flood-opacity="0.35"/>
    </filter>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{pal['card_a']}"/>
      <stop offset="100%" stop-color="{pal['card_b']}"/>
    </linearGradient>
    <style>
      {chr(10).join(css)}
    </style>
  </defs>

  <!-- Arcade Stage Chassis -->
  <rect x="2" y="2" width="{width - 4}" height="{height - 4}" rx="14" fill="url(#bgGrad)"/>
  <rect x="2" y="2" width="{width - 4}" height="{height - 4}" rx="14" class="glow-border"/>

  <!-- Sleek Header HUD -->
  <g transform="translate(30, 40)">
    <circle cx="8" cy="-5" r="4" fill="{pal['accent']}" filter="url(#glow)"/>
    <text x="22" y="0" class="text-head">CYBER TANK &amp; BBTAN RICOCHET // CHILL COMMANDO</text>
    <text x="{width - 85}" y="0" text-anchor="end" class="text-stat">COMMITS: {total_commits} | RICOCHET: ACTIVE</text>
  </g>

  <!-- Matriks Kontribusi (Arena BBTAN Brick Breaker) -->
  <g id="contribution-grid">
    {''.join(grid_rects)}
  </g>

  <!-- Serpihan Puing Kotak Hancur -->
  <g id="shatter-fragments">
    {''.join(shatter_elements)}
  </g>

  <!-- Peluru BBTAN Bouncing Ricochet Balls (+1 Setiap Tabrakan!) -->
  <g id="bullets-layer">
    {''.join(bullet_elements)}
  </g>

  <!-- Platform Landasan Tempur (Jarak Lega) -->
  <line x1="40" y1="{RUNWAY_Y + 4}" x2="{width - 40}" y2="{RUNWAY_Y + 4}" class="runway"/>
  <line x1="40" y1="{RUNWAY_Y + 4}" x2="{width - 40}" y2="{RUNWAY_Y + 4}" class="runway-glow"/>

  <!-- Helikopter Mini Drop Kursi -->
  {heli_svg}

  <!-- Kursi Santai Pantai -->
  {chair_svg}

  <!-- Cyber Tank -->
  {tank_svg}

  <!-- Aktor Tentara Multiverse (Jalan Bawa Peluru -> Rebahan Chill -> Lompat Senang) -->
  <g class="soldier-actor">
    {soldier_walk_svg}
    {soldier_recline_svg}
    {soldier_victory_svg}
  </g>
</svg>"""
    return svg

# ==============================================================================
# PAC-MAN GENERATOR
# ==============================================================================
def build_pacman_svg(data, palette):
    pal = PALETTES.get(palette, PALETTES["purple"])
    raw_weeks = data["weeks"][-36:] if len(data["weeks"]) >= 36 else data["weeks"]
    gw = len(raw_weeks)
    width = 920
    height = 260
    ox, oy = 75, 60

    rects = []
    for c, col in enumerate(raw_weeks):
        for r, day in enumerate(col):
            x = ox + c * P
            y = oy + r * P
            lvl = day.get("level", 0)
            fill_c = pal["tile"] if lvl == 0 else pal["levels"][lvl - 1]
            stroke = pal["tile_edge"] if lvl == 0 else pal["accent"]
            rects.append(f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="3" fill="{fill_c}" stroke="{stroke}" stroke-width="0.8"/>')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
  <defs>
    <filter id="glow-pac" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2" result="blur" />
      <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
    </filter>
    <linearGradient id="bgGradPac" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{pal['card_a']}"/>
      <stop offset="100%" stop-color="{pal['card_b']}"/>
    </linearGradient>
    <style>
      .pac-head {{ fill: {pal['text']}; font-family: 'Courier New', monospace; font-weight: bold; font-size: 14px; letter-spacing: 2px; }}
      .pac-stat {{ fill: {pal['glow']}; font-family: 'Courier New', monospace; font-size: 12px; }}
      @keyframes pacmanWalk {{
        0% {{ transform: translate({ox - 10}px, {oy + 3 * P}px); }}
        50% {{ transform: translate({ox + (gw - 2) * P}px, {oy + 3 * P}px); }}
        100% {{ transform: translate({ox - 10}px, {oy + 3 * P}px); }}
      }}
      @keyframes pacChomp {{
        0%, 100% {{ d: path('M 0 0 L 10 -7 A 12 12 0 1 1 10 7 Z'); }}
        50% {{ d: path('M 0 0 L 12 0 A 12 12 0 1 1 12 0 Z'); }}
      }}
      .pacman-sprite {{ animation: pacmanWalk 12s infinite linear; }}
      .pacman-body {{ fill: #facc15; animation: pacChomp 0.3s infinite ease-in-out; }}
    </style>
  </defs>
  <rect x="2" y="2" width="{width - 4}" height="{height - 4}" rx="14" fill="url(#bgGradPac)" stroke="{pal['accent']}" stroke-width="1.5"/>
  <g transform="translate(30, 36)">
    <circle cx="8" cy="-5" r="4" fill="{pal['accent']}" filter="url(#glow-pac)"/>
    <text x="22" y="0" class="pac-head">PAC-MAN ARCADE // CONTRIB MATRIX</text>
    <text x="{width - 85}" y="0" text-anchor="end" class="pac-stat">SCORE: {data.get('total', 1342) * 10}</text>
  </g>
  <g id="pac-grid">{''.join(rects)}</g>
  <g class="pacman-sprite">
    <path class="pacman-body" d="M 0 0 L 10 -7 A 12 12 0 1 1 10 7 Z" filter="url(#glow-pac)"/>
  </g>
</svg>"""
    return svg

# ==============================================================================
# MAIN DRIVER
# ==============================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="rjoulfiand-afk")
    parser.add_argument("--palette", default="purple")
    parser.add_argument("--out", default="dist")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    os.makedirs(args.out, exist_ok=True)

    print(f"[*] Fetching live contributions for {args.user}...")
    data = fetch_contributions(args.user, token)

    # 1. Top: Pac-Man Cyberpunk Matrix
    pacman_svg = build_pacman_svg(data, args.palette)
    with open(os.path.join(args.out, "pacman-contribution-graph-dark.svg"), "w", encoding="utf-8") as f:
        f.write(pacman_svg)
    print(" -> Saved dist/pacman-contribution-graph-dark.svg")

    # 2. Bottom: Cyber Tank & BBTAN Reclining Commando Striker
    soldier_svg = build_soldier_shooter_svg(data, args.palette)
    with open(os.path.join(args.out, "soldier-contribution-graph-dark.svg"), "w", encoding="utf-8") as f:
        f.write(soldier_svg)
    print(" -> Saved dist/soldier-contribution-graph-dark.svg")

    print("[✔] Finished generating all vector assets cleanly!")

if __name__ == "__main__":
    main()
