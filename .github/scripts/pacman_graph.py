#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pac-Man Cyberpunk Matrix Arcade Contribution Graph
Pure Native SVG Vector Physics - Zero External Dependencies
Outputs: dist/pacman-contribution-graph-dark.svg
"""
import datetime as dt
import json
import math
import os
import random
import sys
import urllib.request

USERNAME = "rjoulfiand-afk"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

DIST_DIR = os.path.join(os.getcwd(), "dist")
os.makedirs(DIST_DIR, exist_ok=True)

S, G = 15, 4
P = S + G

def fetch_contributions():
    headers = {"User-Agent": "Pacman-Graph"}
    if TOKEN:
        headers["Authorization"] = f"bearer {TOKEN}"
    query = """
    query($user: String!) {
      user(login: $user) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """
    req_body = json.dumps({"query": query, "variables": {"user": USERNAME}}).encode("utf-8")
    req = urllib.request.Request("https://api.github.com/graphql", data=req_body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
            grid = []
            for w in weeks:
                col = [d["contributionCount"] for d in w["contributionDays"]]
                while len(col) < 7:
                    col.append(0)
                grid.append(col)
            return grid
    except Exception as e:
        print(f"[-] Using fallback grid: {e}")
        return [[random.choice([0, 1, 3, 5, 8]) for _ in range(7)] for _ in range(53)]

def generate_pacman_svg():
    grid = fetch_contributions()
    cols = len(grid)
    rows = 7
    width = cols * P + 50
    height = rows * P + 70

    colors = ["#131722", "#3b0764", "#6b21a8", "#9333ea", "#c084fc"]

    rects = []
    for c in range(cols):
        for r in range(rows):
            cnt = grid[c][r]
            color = colors[0] if cnt == 0 else colors[1] if cnt < 3 else colors[2] if cnt < 6 else colors[3] if cnt < 10 else colors[4]
            x = 25 + c * P
            y = 40 + r * P
            rects.append(f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="3" fill="{color}" stroke="#1f2638" stroke-width="0.8" />')

    rects_markup = "\n  ".join(rects)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="{height}">
  <defs>
    <linearGradient id="card-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0d1117" />
      <stop offset="100%" stop-color="#06080d" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="2.5" result="blur" />
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- Frame -->
  <rect x="1" y="1" width="{width-2}" height="{height-2}" rx="12" fill="url(#card-bg)" stroke="#a855f7" stroke-width="1.2" opacity="0.8" />

  <!-- Title -->
  <text x="25" y="24" fill="#f5f3ff" font-family="'Segoe UI', monospace" font-size="12" font-weight="700" letter-spacing="1.5">
    👾 PAC-MAN CYBERPUNK ARCADE // REPO MATRIX
  </text>

  <!-- Tiles -->
  {rects_markup}

  <!-- Animated Pac-Man & Ghost -->
  <g transform="translate(0, 40)">
    <!-- Pac-Man -->
    <circle cx="30" cy="{3 * P + 7}" r="8" fill="#fbbf24" filter="url(#glow)">
      <animate attributeName="cx" values="30;{width-40};30" dur="14s" repeatCount="indefinite" />
    </circle>
    <!-- Blinky Ghost -->
    <circle cx="10" cy="{3 * P + 7}" r="8" fill="#f43f5e">
      <animate attributeName="cx" values="10;{width-60};10" dur="14s" repeatCount="indefinite" />
    </circle>
  </g>
</svg>"""

    out_path = os.path.join(DIST_DIR, "pacman-contribution-graph-dark.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"[✓] Pac-Man SVG Generated: {out_path}")

if __name__ == "__main__":
    generate_pacman_svg()
