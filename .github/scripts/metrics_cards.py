#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cyberpunk Developer Metrics & Activity Suite
Exact Match Foto 2 Edition:
  1. metrics-header.svg (Equalizer bars ılıı DEVELOPER METRICS & ACTIVITY ıılı)
  2. streak-stats.svg (Full-Width 840px: 535 Total | 270° Speedometer Gauge | 7 Longest)
  3. activity-graph.svg (Full-Width 840px: Rixsan Joulfiand, 535 Contribs, 91 Active, 125 Best Week, 125 PEAK sonar ping, Clean Ticker)
  4. github-stats.svg (Half-Width 405px: Title "Stats", 5 Metrics, Glowing White Octocat with Cyan/Purple Ring)
  5. top-langs.svg (Half-Width 405px: Title "Most Used Languages", 6-Planet Orbiting Solar System, 6 Language Bars)
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.request

USERNAME = "rjoulfiand-afk"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

DIST_DIR = os.path.join(os.getcwd(), "dist")
os.makedirs(DIST_DIR, exist_ok=True)

# -------------------------------------------------------------
# 1. SHARED CYBERPUNK STYLES (SAFE & ANTI-BUG GITHUB CAMO)
# -------------------------------------------------------------
COMMON_DEFS = """
  <defs>
    <!-- Dot Matrix Grid Background -->
    <pattern id="dot-grid" width="16" height="16" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="0.75" fill="#a855f7" opacity="0.10" />
    </pattern>

    <!-- Deep Cyber Gradient Base -->
    <linearGradient id="card-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0c0e18" />
      <stop offset="50%" stop-color="#080911" />
      <stop offset="100%" stop-color="#040508" />
    </linearGradient>

    <!-- Animated Running Laser Border -->
    <linearGradient id="laser-border" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8">
        <animate attributeName="stop-color" values="#38bdf8;#c084fc;#a855f7;#38bdf8" dur="8s" repeatCount="indefinite" />
      </stop>
      <stop offset="50%" stop-color="#a855f7">
        <animate attributeName="stop-color" values="#a855f7;#38bdf8;#c084fc;#a855f7" dur="8s" repeatCount="indefinite" />
      </stop>
      <stop offset="100%" stop-color="#c084fc">
        <animate attributeName="stop-color" values="#c084fc;#a855f7;#38bdf8;#c084fc" dur="8s" repeatCount="indefinite" />
      </stop>
    </linearGradient>

    <!-- Aurora Radial Center -->
    <radialGradient id="center-aurora" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#7e22ce" stop-opacity="0.20" />
      <stop offset="100%" stop-color="#7e22ce" stop-opacity="0.0" />
    </radialGradient>
  </defs>
"""

def cyber_frame(w, h):
    return f"""
    <rect x="1" y="1" width="{w-2}" height="{h-2}" rx="14" fill="url(#card-bg)" stroke="#1a2032" stroke-width="1.2" />
    <rect x="1" y="1" width="{w-2}" height="{h-2}" rx="14" fill="url(#dot-grid)" />
    <rect x="1" y="1" width="{w-2}" height="{h-2}" rx="14" fill="none" stroke="url(#laser-border)" stroke-width="1.2" opacity="0.8" />
    <!-- Tactical Corner Accents -->
    <path d="M 4 16 L 4 4 L 16 4" fill="none" stroke="#38bdf8" stroke-width="2" />
    <path d="M {w-16} 4 L {w-4} 4 L {w-4} 16" fill="none" stroke="#38bdf8" stroke-width="2" />
    <path d="M 4 {h-16} L 4 {h-4} L 16 {h-4}" fill="none" stroke="#a855f7" stroke-width="2" />
    <path d="M {w-16} {h-4} L {w-4} {h-4} L {w-4} {h-16}" fill="none" stroke="#a855f7" stroke-width="2" />
    """

# -------------------------------------------------------------
# 2. METRICS HEADER (metrics-header.svg)
# -------------------------------------------------------------
def build_header_svg():
    w, h = 840, 64
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    .font-head {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    .bar-anim {{ animation: bar-bounce 1.5s ease-in-out infinite alternate; }}
    @keyframes bar-bounce {{
      0% {{ transform: scaleY(0.4); }}
      100% {{ transform: scaleY(1.0); }}
    }}
  </style>
  {COMMON_DEFS}
  {cyber_frame(w, h)}

  <!-- Left Equalizer Bars ılıı -->
  <g transform="translate(64, 32)">
    <rect x="0" y="-12" width="4" height="24" rx="2" fill="#38bdf8" class="bar-anim" style="animation-delay: 0.1s; transform-origin: bottom;" />
    <rect x="8" y="-18" width="4" height="24" rx="2" fill="#a855f7" class="bar-anim" style="animation-delay: 0.3s; transform-origin: bottom;" />
    <rect x="16" y="-8" width="4" height="24" rx="2" fill="#c084fc" class="bar-anim" style="animation-delay: 0.5s; transform-origin: bottom;" />
    <rect x="24" y="-14" width="4" height="24" rx="2" fill="#38bdf8" class="bar-anim" style="animation-delay: 0.2s; transform-origin: bottom;" />
  </g>

  <!-- Center Glowing Title -->
  <text x="{w/2}" y="39" text-anchor="middle" fill="#ffffff" font-size="16" font-weight="900" letter-spacing="3.5" class="font-head" style="text-shadow: 0 0 12px rgba(168, 85, 247, 0.8), 0 0 20px rgba(56, 189, 248, 0.5);">
    DEVELOPER METRICS &amp; ACTIVITY
  </text>

  <!-- Right Equalizer Bars ıılı -->
  <g transform="translate({w-88}, 32)">
    <rect x="0" y="-14" width="4" height="24" rx="2" fill="#38bdf8" class="bar-anim" style="animation-delay: 0.2s; transform-origin: bottom;" />
    <rect x="8" y="-8" width="4" height="24" rx="2" fill="#c084fc" class="bar-anim" style="animation-delay: 0.5s; transform-origin: bottom;" />
    <rect x="16" y="-18" width="4" height="24" rx="2" fill="#a855f7" class="bar-anim" style="animation-delay: 0.3s; transform-origin: bottom;" />
    <rect x="24" y="-12" width="4" height="24" rx="2" fill="#38bdf8" class="bar-anim" style="animation-delay: 0.1s; transform-origin: bottom;" />
  </g>
</svg>"""

# -------------------------------------------------------------
# 3. STREAK STATS FULL WIDTH (streak-stats.svg)
# -------------------------------------------------------------
def build_streak_svg():
    w, h = 840, 200
    cx, cy, r = 420, 85, 48
    circ = 2 * math.pi * r
    total_arc = (270.0 / 360.0) * circ
    active_arc = total_arc * (6.0 / 7.0) # 6 dari 7 hari

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    .font-main {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    .mono {{ font-family: 'Fira Code', Consolas, monospace; }}
    .flicker {{
      animation: flame-glow 2s infinite alternate;
    }}
    @keyframes flame-glow {{
      0% {{ transform: scale(1); filter: drop-shadow(0 0 3px #f59e0b); }}
      100% {{ transform: scale(1.1); filter: drop-shadow(0 0 9px #ef4444); }}
    }}
  </style>
  {COMMON_DEFS}
  {cyber_frame(w, h)}

  <circle cx="{cx}" cy="{cy}" r="110" fill="url(#center-aurora)" />

  <!-- KOLOM 1: TOTAL CONTRIBUTIONS -->
  <g transform="translate(170, 88)" text-anchor="middle">
    <text x="0" y="0" fill="#ffffff" font-size="38" font-weight="900" class="font-main">535</text>
    <text x="0" y="24" fill="#cbd5e1" font-size="13" font-weight="600" class="font-main">Total Contributions</text>
    <text x="0" y="44" fill="#64748b" font-size="11" class="mono">Nov 17, 2025 - Present</text>
  </g>

  <!-- KOLOM 2: SPEEDOMETER GAUGE 270° DENGAN API -->
  <g transform="translate({cx}, {cy})">
    <circle cx="0" cy="0" r="{r}" fill="none" stroke="#1e2638" stroke-width="7"
            stroke-dasharray="{total_arc} {circ}" stroke-linecap="round"
            transform="rotate(135)" />

    <circle cx="0" cy="0" r="{r}" fill="none" stroke="url(#laser-border)" stroke-width="7"
            stroke-dasharray="{active_arc} {circ}" stroke-linecap="round"
            transform="rotate(135)" style="filter: drop-shadow(0 0 6px #c084fc);" />

    <polygon points="32,32 37,27 32,22 27,27" fill="#fbbf24" style="filter: drop-shadow(0 0 4px #fbbf24);" />

    <g transform="translate(0, -16)" class="flicker">
      <path d="M 0 -8 C 4 -2, 7 2, 5 8 C 3 13, -3 13, -5 8 C -7 2, -4 -3, 0 -8 Z" fill="#f59e0b" />
      <path d="M 0 -2 C 2 2, 4 4, 3 7 C 2 10, -2 10, -3 7 C -4 4, -2 1, 0 -2 Z" fill="#fef08a" />
    </g>

    <text x="0" y="14" fill="#ffffff" font-size="28" font-weight="900" text-anchor="middle" class="font-main">6</text>
    <text x="0" y="26" fill="#a855f7" font-size="9" font-weight="800" text-anchor="middle" letter-spacing="1.5" class="mono">DAYS</text>
  </g>

  <g transform="translate({cx}, 148)" text-anchor="middle">
    <text x="0" y="0" fill="#ffffff" font-size="15" font-weight="800" class="font-main">Current Streak</text>
    <text x="0" y="18" fill="#64748b" font-size="11" class="mono">Sep 27 - Oct 2</text>
  </g>

  <!-- KOLOM 3: LONGEST STREAK -->
  <g transform="translate(670, 88)" text-anchor="middle">
    <text x="0" y="0" fill="#ffffff" font-size="38" font-weight="900" class="font-main">7</text>
    <text x="0" y="24" fill="#cbd5e1" font-size="13" font-weight="600" class="font-main">Longest Streak</text>
    <text x="0" y="44" fill="#64748b" font-size="11" class="mono">Sep 14 - Sep 20</text>
  </g>
</svg>"""

# -------------------------------------------------------------
# 4. ACTIVITY GRAPH & VELOCITY TIMELINE (activity-graph.svg)
# -------------------------------------------------------------
def build_activity_graph_svg():
    w, h = 840, 245
    pts = [8, 14, 28, 12, 18, 38, 24, 45, 32, 58, 62, 125]
    months = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]

    gx_start, gx_end = 370, 770
    gy_bottom, gy_top = 175, 75
    span = gx_end - gx_start
    step = span / (len(pts) - 1)

    coords = []
    for idx, val in enumerate(pts):
        x = gx_start + (idx * step)
        norm = val / 125.0
        y = gy_bottom - (norm * (gy_bottom - gy_top))
        coords.append((x, y))

    path_d = f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"
    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i+1]
        cx1 = x0 + (x1 - x0) * 0.45
        cy1 = y0
        cx2 = x0 + (x1 - x0) * 0.55
        cy2 = y1
        path_d += f" C {cx1:.1f} {cy1:.1f}, {cx2:.1f} {cy2:.1f}, {x1:.1f} {y1:.1f}"

    area_d = path_d + f" L {coords[-1][0]:.1f} {gy_bottom} L {coords[0][0]:.1f} {gy_bottom} Z"
    px, py = coords[-1]

    month_svg = []
    for idx, m in enumerate(months):
        x = gx_start + (idx * step)
        month_svg.append(f'<text x="{x:.1f}" y="{gy_bottom + 18}" fill="#64748b" font-size="9.5" text-anchor="middle" class="mono">{m}</text>')
    months_markup = "\n    ".join(month_svg)

    ticker_text = "★ RECORD 7D   •   ◆ 535 CONTRIBS / YR   •   ● 91/364 ACTIVE DAYS   •   ▶ SHIPPING PRIME NOTES   •   "

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    .font-main {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    .mono {{ font-family: 'Fira Code', Consolas, monospace; }}
    .sonar-ping {{
      animation: ripple-wave 2.2s cubic-bezier(0, 0.2, 0.8, 1) infinite;
      transform-origin: {px:.1f}px {py:.1f}px;
    }}
    @keyframes ripple-wave {{
      0% {{ r: 3px; opacity: 1; }}
      100% {{ r: 26px; opacity: 0; }}
    }}
    .marquee-track {{
      animation: scroll-text 18s linear infinite;
    }}
    @keyframes scroll-text {{
      0% {{ transform: translateX(0); }}
      100% {{ transform: translateX(-50%); }}
    }}
  </style>
  {COMMON_DEFS}
  
  <defs>
    <linearGradient id="wave-fill" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.32" />
      <stop offset="100%" stop-color="#3b0764" stop-opacity="0.0" />
    </linearGradient>
  </defs>

  {cyber_frame(w, h)}

  <!-- PANEL KIRI: PROFIL & METRIK ASLI RIXSAN -->
  <g transform="translate(36, 40)">
    <text x="0" y="0" fill="#ffffff" font-size="17" font-weight="900" class="font-main">Rixsan Joulfiand</text>
    <text x="0" y="16" fill="#a855f7" font-size="12" font-weight="700" class="mono">@rjoulfiand-afk</text>

    <g transform="translate(260, -3)">
      <text x="0" y="0" fill="#38bdf8" font-size="11" font-weight="800" class="mono" letter-spacing="1">ılıı LIVE</text>
    </g>

    <!-- Contributions -->
    <g transform="translate(0, 48)">
      <circle cx="6" cy="-4" r="5" fill="#1e1b4b" stroke="#a855f7" stroke-width="1.2" />
      <text x="20" y="0" fill="#ffffff" font-size="12.5" font-weight="800" class="font-main">535 Contributions</text>
      <text x="20" y="14" fill="#64748b" font-size="10" class="mono">in the last year</text>
    </g>

    <!-- Active Days -->
    <g transform="translate(0, 84)">
      <circle cx="6" cy="-4" r="5" fill="#0f172a" stroke="#38bdf8" stroke-width="1.2" />
      <text x="20" y="0" fill="#ffffff" font-size="12.5" font-weight="800" class="font-main">91 Active Days</text>
      <text x="20" y="14" fill="#64748b" font-size="10" class="mono">25% of the last 364 days</text>
    </g>

    <!-- Best Week -->
    <g transform="translate(0, 120)">
      <circle cx="6" cy="-4" r="5" fill="#311042" stroke="#f43f5e" stroke-width="1.2" />
      <text x="20" y="0" fill="#ffffff" font-size="12.5" font-weight="800" class="font-main">125 Best Week</text>
      <text x="20" y="14" fill="#64748b" font-size="10" class="mono">week of Sep 27</text>
    </g>
  </g>

  <!-- PANEL KANAN: GRAFIK & SUMBU -->
  <text x="{gx_end}" y="36" fill="#a855f7" font-size="10.5" font-weight="700" text-anchor="end" class="mono" letter-spacing="1.5">CONTRIBUTIONS IN THE LAST YEAR</text>

  <line x1="{gx_start}" y1="{gy_top}" x2="{gx_end}" y2="{gy_top}" stroke="#1e2638" stroke-width="0.8" stroke-dasharray="3 3" />
  <line x1="{gx_start}" y1="{(gy_top+gy_bottom)/2}" x2="{gx_end}" y2="{(gy_top+gy_bottom)/2}" stroke="#1e2638" stroke-width="0.8" stroke-dasharray="3 3" />
  <line x1="{gx_start}" y1="{gy_bottom}" x2="{gx_end}" y2="{gy_bottom}" stroke="#1e2638" stroke-width="0.8" />

  <text x="{gx_end + 18}" y="{gy_top + 4}" fill="#64748b" font-size="9.5" class="mono">125</text>
  <text x="{gx_end + 18}" y="{(gy_top+gy_bottom)/2 + 4}" fill="#64748b" font-size="9.5" class="mono">82</text>
  <text x="{gx_end + 18}" y="{gy_bottom + 4}" fill="#64748b" font-size="9.5" class="mono">41</text>

  <path d="{area_d}" fill="url(#wave-fill)" />
  <path d="{path_d}" fill="none" stroke="url(#laser-border)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="filter: drop-shadow(0 0 6px #c084fc);" />

  {months_markup}

  <!-- Sonar Ping Ripple & 125 PEAK Badge -->
  <circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="none" stroke="#c084fc" stroke-width="1.5" class="sonar-ping" />
  <circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="#fef08a" stroke="#f59e0b" stroke-width="2" style="filter: drop-shadow(0 0 6px #f59e0b);" />
  
  <g transform="translate({px:.1f}, {py - 14})">
    <rect x="-26" y="-12" width="52" height="15" rx="4" fill="#3b0764" stroke="#fbbf24" stroke-width="1" />
    <text x="0" y="-1" fill="#fef08a" font-size="8.5" font-weight="900" text-anchor="middle" class="mono">125 PEAK</text>
  </g>

  <!-- MARQUEE TICKER (BERSIH & SEAMLESS) -->
  <g transform="translate(0, {h-24})">
    <rect x="8" y="0" width="{w-16}" height="20" rx="4" fill="#06080e" stroke="#161c28" stroke-width="0.8" />
    <svg x="14" y="0" width="{w-28}" height="20" style="overflow: hidden;">
      <g class="marquee-track">
        <text x="0" y="13" fill="#cbd5e1" font-size="9.5" font-weight="600" class="mono" letter-spacing="1">
          {ticker_text}{ticker_text}
        </text>
      </g>
    </svg>
  </g>
</svg>"""

# -------------------------------------------------------------
# 5. GITHUB STATS DENGAN LOGO OCTOCAT (github-stats.svg)
# -------------------------------------------------------------
def build_github_stats_svg():
    w, h = 405, 205
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    .font-main {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    .mono {{ font-family: 'Fira Code', Consolas, monospace; }}
    .octo-ring {{
      animation: ring-pulse 4s linear infinite;
      transform-origin: 325px 105px;
    }}
    @keyframes ring-pulse {{
      0% {{ transform: rotate(0deg); }}
      100% {{ transform: rotate(360deg); }}
    }}
  </style>
  {COMMON_DEFS}
  {cyber_frame(w, h)}

  <text x="24" y="34" fill="#a855f7" font-size="14" font-weight="800" class="font-main">Stats</text>

  <!-- 5 Metrik Asli -->
  <g transform="translate(24, 60)">
    <g transform="translate(0, 0)">
      <text x="0" y="0" fill="#94a3b8" font-size="11" class="font-main">★  Total Stars Earned:</text>
      <text x="200" y="0" fill="#ffffff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">0</text>
    </g>

    <g transform="translate(0, 24)">
      <text x="0" y="0" fill="#94a3b8" font-size="11" class="font-main">⏱  Total Commits (last year):</text>
      <text x="200" y="0" fill="#ffffff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">262</text>
    </g>

    <g transform="translate(0, 48)">
      <text x="0" y="0" fill="#94a3b8" font-size="11" class="font-main">⑂  Total PRs:</text>
      <text x="200" y="0" fill="#ffffff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">0</text>
    </g>

    <g transform="translate(0, 72)">
      <text x="0" y="0" fill="#94a3b8" font-size="11" class="font-main">ⓘ  Total Issues:</text>
      <text x="200" y="0" fill="#ffffff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">0</text>
    </g>

    <g transform="translate(0, 96)">
      <text x="0" y="0" fill="#94a3b8" font-size="11" class="font-main">⎘  Contributed to (last year):</text>
      <text x="200" y="0" fill="#ffffff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">0</text>
    </g>
  </g>

  <!-- LOGO GITHUB OCTOCAT PUTIH DENGAN CINCIN NEON DI KANAN -->
  <g transform="translate(325, 105)">
    <circle cx="0" cy="0" r="38" fill="none" stroke="#1f293d" stroke-width="3" />
    <circle cx="0" cy="0" r="38" fill="none" stroke="url(#laser-border)" stroke-width="3.5"
            stroke-dasharray="120 120" stroke-linecap="round" class="octo-ring" style="filter: drop-shadow(0 0 6px #c084fc);" />

    <circle cx="0" cy="0" r="30" fill="#0d1117" stroke="#2a354c" stroke-width="1.2" />

    <path d="M 0 -18 C -10 -18, -18 -10, -18 0 C -18 8, -13 15, -6 17.5 C -5 17.7, -4.7 17.1, -4.7 16.5 L -4.7 13.5 C -9.8 14.6, -10.8 11, -10.8 11 C -11.6 9, -12.7 8.5, -12.7 8.5 C -14.4 7.3, -12.6 7.4, -12.6 7.4 C -10.7 7.5, -9.7 9.3, -9.7 9.3 C -8 12.2, -5.3 11.4, -4.3 10.9 C -4.1 9.7, -3.6 8.8, -3 8.3 C -7 7.8, -11.3 6.3, -11.3 -0.7 C -11.3 -2.7, -10.6 -4.3, -9.4 -5.6 C -9.6 -6.1, -10.2 -7.9, -9.2 -10.3 C -9.2 -10.3, -7.7 -10.8, -4.2 -8.4 C -2.7 -8.8, -1.2 -9, 0.3 -9 C 1.8 -9, 3.3 -8.8, 4.8 -8.4 C 8.3 -10.8, 9.8 -10.3, 9.8 -10.3 C 10.8 -7.9, 10.2 -6.1, 10 -5.6 C 11.2 -4.3, 11.9 -2.7, 11.9 -0.7 C 11.9 6.3, 7.6 7.8, 3.5 8.3 C 4.2 8.9, 4.8 10, 4.8 11.7 L 4.8 16.5 C 4.8 17.1, 5.2 17.7, 6.2 17.5 C 13.2 15, 18.2 8, 18.2 0 C 18.2 -10, 10 -18, 0 -18 Z" fill="#ffffff" transform="scale(1.1) translate(0, 0)" />
  </g>
</svg>"""

# -------------------------------------------------------------
# 6. MOST USED LANGUAGES SOLAR SYSTEM (top-langs.svg)
# -------------------------------------------------------------
def build_top_langs_svg():
    w, h = 405, 205
    langs = [
        {"name": "Jupyter Notebook", "pct": 88.85, "color": "#f97316"},
        {"name": "HTML", "pct": 5.04, "color": "#e34c26"},
        {"name": "PHP", "pct": 2.47, "color": "#4f5b93"},
        {"name": "Blade", "pct": 1.93, "color": "#8b5cf6"},
        {"name": "TypeScript", "pct": 0.96, "color": "#3178c6"},
        {"name": "JavaScript", "pct": 0.75, "color": "#f1e05a"}
    ]

    rows = []
    y_pos = 58
    for l in langs:
        bar_w = int((l["pct"] / 100.0) * 110)
        row = f"""
        <g transform="translate(0, {y_pos})">
          <circle cx="0" cy="-3.5" r="3" fill="{l['color']}" />
          <text x="10" y="0" fill="#cbd5e1" font-size="10" font-weight="600" class="font-main">{l['name']}</text>
          <text x="210" y="0" fill="#94a3b8" font-size="10" class="mono" text-anchor="end">{l['pct']:.2f}%</text>
          <rect x="10" y="5" width="200" height="3" rx="1.5" fill="#151b28" />
          <rect x="10" y="5" width="{bar_w}" height="3" rx="1.5" fill="{l['color']}" style="filter: drop-shadow(0 0 3px {l['color']});" />
        </g>
        """
        rows.append(row)
        y_pos += 23

    rows_markup = "\n".join(rows)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    .font-main {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
    .mono {{ font-family: 'Fira Code', Consolas, monospace; }}
    .orbit-1 {{
      animation: spin-cw 7s linear infinite;
      transform-origin: 75px 115px;
    }}
    .orbit-2 {{
      animation: spin-ccw 12s linear infinite;
      transform-origin: 75px 115px;
    }}
    .orbit-3 {{
      animation: spin-cw 18s linear infinite;
      transform-origin: 75px 115px;
    }}
    @keyframes spin-cw {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
    }}
    @keyframes spin-ccw {{
      from {{ transform: rotate(360deg); }}
      to {{ transform: rotate(0deg); }}
    }}
  </style>
  {COMMON_DEFS}
  {cyber_frame(w, h)}

  <text x="24" y="34" fill="#a855f7" font-size="14" font-weight="800" class="font-main">Most Used Languages</text>

  <!-- PLANETARY SOLAR SYSTEM DI SEBELAH KIRI -->
  <g transform="translate(0, 0)">
    <circle cx="75" cy="115" r="14" fill="#8b5cf6" style="filter: drop-shadow(0 0 8px #a855f7);" />
    <circle cx="75" cy="115" r="10" fill="#581c87" />
    <text x="75" y="118" fill="#ffffff" font-size="8" font-weight="900" text-anchor="middle" class="mono">&lt;/&gt;</text>

    <!-- Orbit Ring 1 -->
    <circle cx="75" cy="115" r="28" fill="none" stroke="#252f44" stroke-width="1" stroke-dasharray="2 3" />
    <g class="orbit-1">
      <circle cx="103" cy="115" r="7" fill="#f97316" style="filter: drop-shadow(0 0 5px #f97316);" />
      <circle cx="47" cy="115" r="3.5" fill="#e34c26" />
    </g>

    <!-- Orbit Ring 2 -->
    <circle cx="75" cy="115" r="44" fill="none" stroke="#1d2638" stroke-width="1" stroke-dasharray="3 4" />
    <g class="orbit-2">
      <circle cx="31" cy="115" r="4.5" fill="#4f5b93" />
      <circle cx="119" cy="115" r="3.5" fill="#3178c6" />
    </g>

    <!-- Orbit Ring 3 -->
    <circle cx="75" cy="115" r="58" fill="none" stroke="#151d2c" stroke-width="1" stroke-dasharray="2 4" />
    <g class="orbit-3">
      <circle cx="75" cy="57" r="4" fill="#f1e05a" style="filter: drop-shadow(0 0 4px #f1e05a);" />
    </g>
  </g>

  <!-- DAFTAR 6 BAHASA DI SEBELAH KANAN -->
  <g transform="translate(170, 0)">
    {rows_markup}
  </g>
</svg>"""

# -------------------------------------------------------------
# 7. MAIN RUNNER
# -------------------------------------------------------------
def main():
    cards = {
        "metrics-header.svg": build_header_svg(),
        "streak-stats.svg": build_streak_svg(),
        "activity-graph.svg": build_activity_graph_svg(),
        "github-stats.svg": build_github_stats_svg(),
        "top-langs.svg": build_top_langs_svg()
    }

    for fname, content in cards.items():
        out = os.path.join(DIST_DIR, fname)
        with open(out, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"[✓] Berhasil digenerate: {out}")

    print("[🚀] Seluruh kartu SVG Developer Metrics (Foto 2) berhasil dibuat!")

if __name__ == "__main__":
    main()
