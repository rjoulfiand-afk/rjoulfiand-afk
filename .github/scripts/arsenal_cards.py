#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Studio-Grade Signal-Bus Arsenal Stack (Master Level 1 & 2)
Pure Native Python Standard Library - Zero External Dependencies
Palette: Monochromatic Violet & Lilac Chrome with Dynamic Brand Ignition Cascade
Canvas: 840 x 708 viewBox (Justified Grid, PCB Bus Architecture, 3-Phase Ignition)
CLI Options:
  --out DIR         Output directory (default: dist)
  --selftest        Run offline unit selftest suite (fail-closed exit 1)
  --sync-icons      Download, pin, and lock all 29 icons to .github/assets/icons/
  --now ISO8601     Fix build timestamp for deterministic rendering
"""
import argparse
import ast
import base64
import colorsys
import datetime as dt
import hashlib
import json
import math
import os
import pathlib
import random
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import escape
from typing import Dict, List, Optional, Tuple

try:
    from metrics_cards import common_card_defs, lava_border_frame
except ImportError:
    sys.path.insert(0, str(pathlib.Path(__file__).parent.resolve()))
    try:
        from metrics_cards import common_card_defs, lava_border_frame
    except ImportError:
        def common_card_defs(prefix, w, h):
            return f"""<defs><filter id="{prefix}_glow_filter"><feGaussianBlur stdDeviation="3.0"/></filter></defs>"""
        def lava_border_frame(prefix, w, h, delay_offset=0):
            return f"""<rect width="{w}" height="{h}" rx="14" fill="#05030a"/>"""

# ==============================================================================
# CONFIG & MANIFEST
# ==============================================================================
CYCLE_S = 13.0
COMET_S = 4.8
REST_MODE = "duotone"  # "duotone" | "muted"
BRAND_BLOOM = True
PARTICLES = 12
LIMIT_KB = 340
OUT_NAME = "arsenal-stack.svg"
ICONS_DIR = pathlib.Path(".github/assets/icons")
LOCK_FILE = ICONS_DIR / "icons.lock"

# Pinned upstream library versions
DEVICON_VER = "v2.16.0"
LOBE_VER = "v1.27.0"
DEVICON_BASE = f"https://cdn.jsdelivr.net/gh/devicons/devicon@{DEVICON_VER}/icons"
LOBE_BASE = f"https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@{LOBE_VER}/icons"
LOBE_PNG_BASE = f"https://cdn.jsdelivr.net/npm/@lobehub/icons-static-png@{LOBE_VER}/dark"

@dataclass(frozen=True)
class ToolItem:
    key: str
    name: str
    url: str
    is_mono: bool
    fallback_png: Optional[str] = None

@dataclass(frozen=True)
class ToolGroup:
    title: str
    tint: str
    items: Tuple[ToolItem, ...]

MANIFEST: Tuple[ToolGroup, ...] = (
    ToolGroup(
        title="Languages & Core Technologies",
        tint="#a855f7",
        items=(
            ToolItem("php", "PHP", f"{DEVICON_BASE}/php/php-original.svg", False),
            ToolItem("laravel", "Laravel", f"{DEVICON_BASE}/laravel/laravel-original.svg", False),
            ToolItem("html5", "HTML5", f"{DEVICON_BASE}/html5/html5-original.svg", False),
            ToolItem("css3", "CSS3", f"{DEVICON_BASE}/css3/css3-original.svg", False),
            ToolItem("javascript", "JavaScript", f"{DEVICON_BASE}/javascript/javascript-original.svg", False),
            ToolItem("typescript", "TypeScript", f"{DEVICON_BASE}/typescript/typescript-original.svg", False),
            ToolItem("react", "React Native", f"{DEVICON_BASE}/react/react-original.svg", False),
            ToolItem("python", "Python", f"{DEVICON_BASE}/python/python-original.svg", False),
            ToolItem("jupyter", "Jupyter", f"{DEVICON_BASE}/jupyter/jupyter-original-wordmark.svg", False),
        )
    ),
    ToolGroup(
        title="Database & Development Environment",
        tint="#8b5cf6",
        items=(
            ToolItem("mysql", "MySQL", f"{DEVICON_BASE}/mysql/mysql-original-wordmark.svg", False),
            ToolItem("postgresql", "PostgreSQL", f"{DEVICON_BASE}/postgresql/postgresql-original.svg", False),
            ToolItem("git", "Git", f"{DEVICON_BASE}/git/git-original.svg", False),
            ToolItem("github", "GitHub", "https://cdn.simpleicons.org/github/white", True),
            ToolItem("vscode", "VS Code", f"{DEVICON_BASE}/vscode/vscode-original.svg", False),
            ToolItem("figma", "Figma", f"{DEVICON_BASE}/figma/figma-original.svg", False),
        )
    ),
    ToolGroup(
        title="AI Coding Assistants & Agents",
        tint="#e879f9",
        items=(
            ToolItem("chatgpt", "ChatGPT", f"{LOBE_BASE}/openai.svg", True, f"{LOBE_PNG_BASE}/openai.png"),
            ToolItem("gemini", "Gemini", f"{LOBE_BASE}/gemini-color.svg", False),
            ToolItem("claude", "Claude", f"{LOBE_BASE}/claude-color.svg", False),
            ToolItem("antigravity", "Antigravity", f"{LOBE_BASE}/antigravity-color.svg", False),
            ToolItem("copilot", "GitHub Copilot", f"{LOBE_BASE}/githubcopilot.svg", True, f"{LOBE_PNG_BASE}/githubcopilot.png"),
            ToolItem("cursor", "Cursor", f"{LOBE_BASE}/cursor.svg", True, f"{LOBE_PNG_BASE}/cursor.png"),
            ToolItem("perplexity", "Perplexity", f"{LOBE_BASE}/perplexity-color.svg", False),
        )
    ),
    ToolGroup(
        title="LLM Platforms & Open Models",
        tint="#c084fc",
        items=(
            ToolItem("ollama", "Ollama", f"{LOBE_BASE}/ollama.svg", True, f"{LOBE_PNG_BASE}/ollama.png"),
            ToolItem("huggingface", "Hugging Face", f"{LOBE_BASE}/huggingface-color.svg", False),
            ToolItem("deepseek", "DeepSeek", f"{LOBE_BASE}/deepseek-color.svg", False),
            ToolItem("mistral", "Mistral AI", f"{LOBE_BASE}/mistral-color.svg", False),
            ToolItem("qwen", "Qwen", f"{LOBE_BASE}/qwen-color.svg", False),
            ToolItem("grok", "Grok", f"{LOBE_BASE}/grok.svg", True, f"{LOBE_PNG_BASE}/grok.png"),
            ToolItem("llama", "Meta Llama", f"{LOBE_BASE}/meta-color.svg", False),
        )
    ),
)

ALL_ITEMS: List[ToolItem] = [it for g in MANIFEST for it in g.items]
TOTAL_TOOLS = len(ALL_ITEMS)  # 29
TOTAL_GROUPS = len(MANIFEST)  # 4

# Optical weight tuning multipliers
OPTICAL_SCALE = {
    "mysql": 1.15,
    "jupyter": 1.18,
    "postgresql": 1.05,
    "antigravity": 1.10,
    "huggingface": 1.08,
    "deepseek": 1.05,
    "react": 1.05,
}

# ==============================================================================
# ICON PIPELINE & COLOR AUDIT
# ==============================================================================
def normalize_svg_content(raw_svg: str, is_mono: bool) -> str:
    s = re.sub(r'<\?xml[^>]*\?>', '', raw_svg, flags=re.DOTALL)
    s = re.sub(r'<!DOCTYPE[^>]*>', '', s, flags=re.DOTALL)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.DOTALL)
    s = re.sub(r'<title>.*?</title>', '', s, flags=re.DOTALL)
    s = re.sub(r'<metadata>.*?</metadata>', '', s, flags=re.DOTALL)
    s = s.strip()

    if "viewBox" not in s and "<svg" in s:
        w_m = re.search(r'width=["\']([0-9.]+)p?x?["\']', s)
        h_m = re.search(r'height=["\']([0-9.]+)p?x?["\']', s)
        if w_m and h_m:
            w_v = float(w_m.group(1))
            h_v = float(h_m.group(1))
            s = re.sub(r'<svg\b', f'<svg viewBox="0 0 {w_v} {h_v}"', s, count=1)

    if is_mono:
        s = s.replace("currentColor", "#f5f3ff")
        s = re.sub(r'fill=["\'](#000|#000000|black|#111|#111111)["\']', 'fill="#f5f3ff"', s)

    return s

def extract_brand_hex(svg_raw: str, default_hex: str) -> str:
    hexes = re.findall(r'#[0-9a-fA-F]{6}', svg_raw)
    counts = {}
    for h in hexes:
        hl = h.lower()
        r, g, b = int(hl[1:3], 16)/255.0, int(hl[3:5], 16)/255.0, int(hl[5:7], 16)/255.0
        h_deg, s, v = colorsys.rgb_to_hsv(r, g, b)
        # Skip pure black, white, or low-saturation greys
        if v < 0.15 or (s < 0.20 and v > 0.85):
            continue
        counts[hl] = counts.get(hl, 0) + 1

    if not counts:
        return default_hex
    return max(counts.items(), key=lambda x: x[1])[0]

def sync_icons(dest_dir: pathlib.Path = ICONS_DIR):
    dest_dir.mkdir(parents=True, exist_ok=True)
    print("================== SYNCING & LOCKING ICONS ==================")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SignalBusSync/2.0"}
    lock_data = {}

    for item in ALL_ITEMS:
        svg_target = dest_dir / f"{item.key}.svg"
        png_target = dest_dir / f"{item.key}.png"

        try:
            req = urllib.request.Request(item.url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read()
            text = content.decode("utf-8", errors="replace")
            norm_svg = normalize_svg_content(text, item.is_mono)
            ET.fromstring(norm_svg)
            with open(svg_target, "w", encoding="utf-8") as f:
                f.write(norm_svg)
            sha = hashlib.sha256(norm_svg.encode("utf-8")).hexdigest()
            lock_data[f"{item.key}.svg"] = sha
            print(f"[✓] {item.key:14} -> {svg_target.name} ({len(norm_svg)/1024:.1f} KB)")
        except Exception as e:
            if item.fallback_png:
                try:
                    req_p = urllib.request.Request(item.fallback_png, headers=headers)
                    with urllib.request.urlopen(req_p, timeout=15) as resp_p:
                        p_content = resp_p.read()
                    with open(png_target, "wb") as pf:
                        pf.write(p_content)
                    sha_p = hashlib.sha256(p_content).hexdigest()
                    lock_data[f"{item.key}.png"] = sha_p
                    print(f"[✓] {item.key:14} -> FALLBACK {png_target.name} ({len(p_content)/1024:.1f} KB)")
                    continue
                except Exception as ep:
                    print(f"[!] FAILED fallback for {item.key}: {ep}", file=sys.stderr)
            print(f"[-] ERROR syncing {item.key}: {e}", file=sys.stderr)
            sys.exit(1)

    with open(LOCK_FILE, "w", encoding="utf-8") as lf:
        json.dump(lock_data, lf, indent=2, sort_keys=True)
    print(f"[🚀] All 29 manifest icons synced and written to {LOCK_FILE}!")

def load_icons(dest_dir: pathlib.Path = ICONS_DIR) -> Tuple[Dict[str, Tuple[str, str]], Dict[str, str]]:
    if not LOCK_FILE.is_file():
        raise FileNotFoundError(f"Missing {LOCK_FILE}. Jalankan 'python3 .github/scripts/arsenal_cards.py --sync-icons' terlebih dahulu.")

    with open(LOCK_FILE, "r", encoding="utf-8") as lf:
        lock_data = json.load(lf)

    icons: Dict[str, Tuple[str, str]] = {}
    brand_colors: Dict[str, str] = {}

    for item in ALL_ITEMS:
        svg_path = dest_dir / f"{item.key}.svg"
        png_path = dest_dir / f"{item.key}.png"

        if svg_path.is_file():
            with open(svg_path, "r", encoding="utf-8") as f:
                content = f.read()
            ET.fromstring(content)
            sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if lock_data.get(svg_path.name) != sha:
                raise ValueError(f"Checksum mismatch for {svg_path.name}! Jalankan --sync-icons.")
            b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
            icons[item.key] = ("image/svg+xml", b64)
            brand_colors[item.key] = extract_brand_hex(content, "#c084fc")
        elif png_path.is_file():
            with open(png_path, "rb") as f:
                p_bytes = f.read()
            assert p_bytes[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG signature for {item.key}"
            sha_p = hashlib.sha256(p_bytes).hexdigest()
            if lock_data.get(png_path.name) != sha_p:
                raise ValueError(f"Checksum mismatch for {png_path.name}! Jalankan --sync-icons.")
            b64 = base64.b64encode(p_bytes).decode("ascii")
            icons[item.key] = ("image/png", b64)
            brand_colors[item.key] = "#c084fc"
        else:
            raise FileNotFoundError(f"Missing icon file: {svg_path}. Jalankan --sync-icons.")

    return icons, brand_colors

# ==============================================================================
# GEOMETRY & TIMELINE ENGINE (LEVEL 1 & 2)
# ==============================================================================
@dataclass
class TileLayout:
    item: ToolItem
    x: float
    y: float
    w: float
    h: float
    cx: float
    cy: float
    rail_y: float
    delay: float
    t_peak: float
    brand_color: str

@dataclass
class GroupLayout:
    group: ToolGroup
    panel_y: float
    rail_y: float
    tiles: List[TileLayout]
    s_b: float
    l_b: float

def compute_layout_and_timeline(brand_colors: Dict[str, str]) -> List[GroupLayout]:
    panel_tops = [76.0, 226.0, 376.0, 526.0]
    S0, SD, D = 0.40, 2.60, COMET_S
    y0, y1 = 66.0, 656.0

    groups_layout: List[GroupLayout] = []

    for b, grp in enumerate(MANIFEST):
        top_y = panel_tops[b]
        rail_y = top_y + 130.0  # 206, 356, 506, 656
        n_tiles = len(grp.items)

        # Level 1.1: Justified Width Calculation
        # (748 - 8 * (n - 1)) / n
        tile_w = (748.0 - 8.0 * (n_tiles - 1)) / n_tiles
        tile_h = 84.0

        s_b = S0 + SD * ((rail_y - y0) / (y1 - y0))
        l_b = s_b + 0.15

        tiles_list: List[TileLayout] = []
        for i, item in enumerate(grp.items):
            tile_x = 46.0 + i * (tile_w + 8.0)
            tile_y = top_y + 38.0
            cx = tile_x + (tile_w / 2.0)
            cy = tile_y + (tile_h / 2.0)
            t_peak = l_b + D * ((cx - 46.0) / 748.0)
            tile_delay = max(0.0, t_peak - 0.12)

            tiles_list.append(TileLayout(
                item=item,
                x=tile_x,
                y=tile_y,
                w=tile_w,
                h=tile_h,
                cx=cx,
                cy=cy,
                rail_y=rail_y,
                delay=tile_delay,
                t_peak=t_peak,
                brand_color=brand_colors.get(item.key, grp.tint)
            ))

        # Assert tile terakhir tepat berujung di x=794
        last_t = tiles_list[-1]
        assert abs((last_t.x + last_t.w) - 794.0) < 0.01, f"Justified grid error in group {b+1}"

        groups_layout.append(GroupLayout(
            group=grp,
            panel_y=top_y,
            rail_y=rail_y,
            tiles=tiles_list,
            s_b=s_b,
            l_b=l_b
        ))

    return groups_layout

# ==============================================================================
# SVG RENDERER: MASTER SIGNAL-BUS ARSENAL
# ==============================================================================
def build_arsenal_svg(icons_map: Dict[str, Tuple[str, str]], brand_colors: Dict[str, str], now_dt: dt.datetime) -> str:
    w, h = 840, 708
    prefix = "arsn"
    groups = compute_layout_and_timeline(brand_colors)

    icon_defs = []
    for item in ALL_ITEMS:
        mime, b64 = icons_map[item.key]
        opt_s = OPTICAL_SCALE.get(item.key, 1.0)
        box_dim = round(32.0 * opt_s, 1)
        offset = round((40.0 - box_dim) / 2.0, 1)
        icon_defs.append(
            f'<image id="{prefix}_ic_{item.key}" x="{offset}" y="{offset}" width="{box_dim}" height="{box_dim}" '
            f'preserveAspectRatio="xMidYMid meet" href="data:{mime};base64,{b64}" />'
        )
    icons_defs_markup = "\n    ".join(icon_defs)

    rng = random.Random(2026)
    dust_particles = []
    for _ in range(PARTICLES):
        px = rng.uniform(40.0, 800.0)
        py = rng.uniform(80.0, 640.0)
        pr = rng.uniform(0.8, 1.5)
        p_dur = rng.uniform(18.0, 30.0)
        p_del = rng.uniform(0.0, 13.0)
        p_color = rng.choice(["#d8b4fe", "#a855f7", "#c084fc"])
        dust_particles.append(
            f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{pr:.1f}" fill="{p_color}" opacity="0.25">'
            f'<animate attributeName="cy" from="{py:.1f}" to="{py - 60.0:.1f}" dur="{p_dur:.1f}s" '
            f'begin="-{p_del:.1f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;0.28;0" dur="{p_dur:.1f}s" '
            f'begin="-{p_del:.1f}s" repeatCount="indefinite"/>'
            f'</circle>'
        )
    dust_markup = "\n  ".join(dust_particles)

    panels_markup = []
    rails_markup = []
    tiles_markup = []
    comets_markup = []

    for b, gl in enumerate(groups):
        py = gl.panel_y
        ry = gl.rail_y
        cnt = len(gl.tiles)
        safe_title = escape(gl.group.title)
        tint = gl.group.tint
        idx_str = f"0{b+1}"

        # Level 1.2: Header dots (1 dot per tool)
        dots = []
        for d_i, t in enumerate(gl.tiles):
            dx = 720.0 - (cnt - 1 - d_i) * 7.0
            dots.append(
                f'<circle cx="{dx:.1f}" cy="{py + 20:.1f}" r="2.0" fill="#2e1065" class="hdr-dot">'
                f'<animate attributeName="fill" values="#2e1065;{t.brand_color};#2e1065" dur="{CYCLE_S}s" '
                f'begin="{t.t_peak:.2f}s" repeatCount="indefinite" />'
                f'</circle>'
            )
        dots_markup = "".join(dots)

        panels_markup.append(f"""
    <!-- Panel {b+1}: {safe_title} -->
    <rect x="30" y="{py}" width="780" height="140" rx="16" fill="url(#{prefix}_panel_grad)" stroke="url(#{prefix}_panel_stroke_{b})" stroke-width="1" />
    <line x1="38" y1="{py+1}" x2="802" y2="{py+1}" stroke="#e9d5ff" stroke-opacity="0.10" stroke-width="1" />
    
    <!-- Level 2.2: Top Accent Sweep -->
    <path d="M 54 {py+1} H 180" stroke="{tint}" stroke-width="2" stroke-linecap="round" opacity="0.4" />
    
    <!-- Panel Header: Index Chip & Title -->
    <rect x="46" y="{py+10}" width="20" height="20" rx="5" fill="#1f1138" stroke="{tint}" stroke-opacity="0.4" />
    <text x="56" y="{py+24}" fill="{tint}" font-size="9.5" font-weight="800" text-anchor="middle" class="mono">{idx_str}</text>
    <text x="74" y="{py+25}" fill="#e9d5ff" font-size="13" font-weight="800">{safe_title}</text>
    
    <!-- Dots & Count -->
    {dots_markup}
    <text x="794" y="{py+24}" fill="#8b7fb0" font-size="9.5" text-anchor="end" class="mono grp-cnt">{cnt} tools</text>
    <line x1="46" y1="{py+32}" x2="794" y2="{py+32}" stroke="#a855f7" stroke-opacity="0.10" stroke-dasharray="3 3" />
        """)

        # Level 1.5: Chamfered Branch & PCB Ruler Rail
        rails_markup.append(f"""
    <!-- Rail for Panel {b+1} -->
    <path d="M 22 {ry - 10} L 32 {ry} H 46" fill="none" stroke="#2e1065" stroke-width="1.6" />
    <line x1="46" y1="{ry}" x2="794" y2="{ry}" stroke="#2e1065" stroke-width="1.6" />
    <line x1="46" y1="{ry}" x2="794" y2="{ry}" stroke="#4c1d95" stroke-width="1.4" stroke-dasharray="2 6" />
    
    <!-- Source Port Ring & Hub Pad -->
    <circle cx="46" cy="{ry}" r="4.5" fill="#05030a" stroke="{tint}" stroke-width="1.4" />
    <circle cx="46" cy="{ry}" r="1.8" fill="#f5d0fe" />
    
    <!-- B1 Two-Layer Fix: Source Port Ripple -->
    <g transform="translate(46, {ry})">
      <circle class="anim-ripple" r="3.2" fill="none" stroke="#f5d0fe" stroke-width="1.2" style="--d:{gl.s_b:.2f}s" />
    </g>

    <!-- Terminal Diamond -->
    <g transform="translate(794, {ry})">
      <polygon points="0,-4.5 4.5,0 0,4.5 -4.5,0" fill="#6d28d9" />
      <polygon class="anim-lit-op" points="0,-4.5 4.5,0 0,4.5 -4.5,0" fill="#f5d0fe" style="--d:{gl.l_b + COMET_S - 0.1:.2f}s" />
    </g>
        """)

        for t in gl.tiles:
            tx, ty, tw, th, tcx = t.x, t.y, t.w, t.h, t.cx
            d_s = f"{t.delay:.2f}s"
            key = t.item.key
            name = escape(t.item.name)
            b_col = t.brand_color

            rails_markup.append(f"""
    <!-- Stub & PCB Via on Rail -->
    <line x1="{tcx}" y1="{ty + th}" x2="{tcx}" y2="{ry}" stroke="#4c1d95" stroke-width="1.2" />
    <circle cx="{tcx}" cy="{ry}" r="2.6" fill="#140a2b" stroke="#6d28d9" stroke-width="1" />
    <circle cx="{tcx}" cy="{ry}" r="1.2" fill="#6d28d9" />
    <g transform="translate({tcx}, {ry})">
      <circle class="anim-lit-op" r="3.2" fill="#f5d0fe" style="--d:{d_s}" />
      <circle class="anim-ripple" r="3.2" fill="none" stroke="#f5d0fe" stroke-width="1.2" style="--d:{d_s}" />
    </g>
            """)

            # Level 1.3: 8-Layer Tile Anatomy (B1 Fix: Static translate outer, relative anim inner)
            plate_cx = tw / 2.0
            ticks_d = f"M 5 9 V 5 H 9 M {tw-9} 5 H {tw-5} V 9 M {tw-5} {th-9} V {th-5} H {tw-9} M 9 {th-5} H 5 V {th-9}"
            lbl_len_attr = f'textLength="{tw - 10:.0f}" lengthAdjust="spacingAndGlyphs"' if len(t.item.name) >= 12 else ''

            tiles_markup.append(f"""
    <g transform="translate({tx:.1f}, {ty:.1f})">
      <!-- 1. Contact Shadow -->
      <ellipse cx="{plate_cx:.1f}" cy="{th + 4}" rx="{tw/2 - 4:.1f}" ry="8" fill="#05030a" opacity="0.6" />
      
      <!-- 2. Body Rect & 3. Bevel Stroke -->
      <rect x="0" y="0" width="{tw:.1f}" height="{th}" rx="13" fill="url(#{prefix}_tile_body)" stroke="url(#{prefix}_tile_bevel)" stroke-width="1" />
      
      <!-- 4. Top Specular & 5. Corner Ticks -->
      <line x1="12" y1="1" x2="{tw - 12:.1f}" y2="1" stroke="#e9d5ff" stroke-opacity="0.15" stroke-width="1" />
      <path d="{ticks_d}" fill="none" stroke="{tint}" stroke-opacity="0.35" stroke-width="1.2" />

      <!-- Floor Bloom -->
      <ellipse class="anim-lit-op" cx="{plate_cx:.1f}" cy="68" rx="34" ry="14" fill="{b_col}" opacity="0.25" data-brand="true" style="--d:{d_s}" />

      <!-- 6. Icon Plate -->
      <circle cx="{plate_cx:.1f}" cy="31" r="23" fill="url(#{prefix}_plate_grad)" stroke="{tint}" stroke-opacity="0.25" stroke-width="1" />
      
      <!-- Lit Rim Frame -->
      <rect class="anim-lit-rim" x="0" y="0" width="{tw:.1f}" height="{th}" rx="13" fill="none" stroke="#c084fc" stroke-width="1.6" style="--d:{d_s}" />

      <!-- Level 2.4: Settle Lift Group (Two-Layer Transform Pattern) -->
      <g class="anim-lift" style="--d:{d_s}">
        <!-- 7. Icon Dual-Layer -->
        <g transform="translate({plate_cx - 20:.1f}, 11)">
          <g class="ico-s">
            <g class="anim-lit-inv" style="--d:{d_s}">
              <use href="#{prefix}_ic_{key}" filter="url(#{prefix}_duo)" />
            </g>
            <g class="anim-lit-op" style="--d:{d_s}">
              <use href="#{prefix}_ic_{key}" />
            </g>
          </g>
        </g>
        <!-- 8. Label -->
        <text class="lbl anim-lit-lbl" x="{plate_cx:.1f}" y="73" text-anchor="middle" {lbl_len_attr} style="--d:{d_s}">{name}</text>
      </g>
    </g>
            """)

        # B1 Fix: Comet in two-layer group (outer translate, inner relative anim)
        comets_markup.append(f"""
    <!-- Comet for Panel {b+1} -->
    <g transform="translate(0, {ry})">
      <g class="anim-comet" style="--cd:{gl.l_b:.2f}s">
        <line x1="-70" y1="0" x2="0" y2="0" stroke="url(#{prefix}_comet_tail)" stroke-width="2.2" stroke-linecap="round" />
        <circle cx="0" cy="0" r="12" fill="url(#{prefix}_comet_glow)" />
        <circle cx="0" cy="0" r="3.2" fill="#f5d0fe" />
      </g>
    </g>
        """)

    footer_str = f"synced {now_dt.strftime('%Y-%m-%d %H:%M UTC')}"
    counts_str = f"{TOTAL_TOOLS} tools / {TOTAL_GROUPS} groups"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-labelledby="{prefix}_title {prefix}_desc">
  <title id="{prefix}_title">Core Tech Stack &amp; Arsenal - Rixsan Joulfiand</title>
  <desc id="{prefix}_desc">Languages &amp; Core Technologies: PHP, Laravel, HTML5, CSS3, JavaScript, TypeScript, React Native, Python, Jupyter. Database &amp; Development Environment: MySQL, PostgreSQL, Git, GitHub, VS Code, Figma. AI Coding Assistants &amp; Agents: ChatGPT, Gemini, Claude, Antigravity, GitHub Copilot, Cursor, Perplexity. LLM Platforms &amp; Open Models: Ollama, Hugging Face, DeepSeek, Mistral AI, Qwen, Grok, Meta Llama.</desc>
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
    
    .flicker-op {{ animation: arsn-neon-op 4s infinite linear; }}
    @keyframes arsn-neon-op {{
      0%, 82%, 84%, 90%, 100% {{ opacity: 1; }}
      83% {{ opacity: 0.25; }}
      89% {{ opacity: 0.6; }}
    }}

    /* B2 Fix: Base opacity 0 & animation-fill-mode both for zero startup flashes */
    .anim-lit-op {{
      opacity: 0;
      animation: arsn-lit-op {CYCLE_S}s infinite ease-out;
      animation-delay: var(--d);
      animation-fill-mode: both;
    }}
    .anim-lit-inv {{
      opacity: 1;
      animation: arsn-lit-inv {CYCLE_S}s infinite ease-out;
      animation-delay: var(--d);
      animation-fill-mode: both;
    }}
    .anim-lift {{
      transform: translateY(0);
      animation: arsn-lit-lift {CYCLE_S}s infinite cubic-bezier(.2,.9,.2,1.15);
      animation-delay: var(--d);
      animation-fill-mode: both;
    }}
    .anim-lit-lbl {{
      fill: #8b7fb0;
      animation: arsn-lit-lbl {CYCLE_S}s infinite ease-out;
      animation-delay: var(--d);
      animation-fill-mode: both;
    }}
    .anim-lit-rim {{
      opacity: 0;
      animation: arsn-lit-rim {CYCLE_S}s infinite ease-out;
      animation-delay: var(--d);
      animation-fill-mode: both;
    }}
    .anim-ripple {{
      opacity: 0;
      transform: scale(1);
      transform-origin: center;
      transform-box: fill-box;
      animation: arsn-ripple {CYCLE_S}s infinite ease-out;
      animation-delay: var(--d);
      animation-fill-mode: both;
    }}

    @keyframes arsn-lit-op {{
      0% {{ opacity: 0; }}
      0.9% {{ opacity: 1; }}
      5.5% {{ opacity: 1; }}
      18% {{ opacity: 0; }}
      100% {{ opacity: 0; }}
    }}
    @keyframes arsn-lit-inv {{
      0% {{ opacity: 1; }}
      0.9% {{ opacity: 0.15; }}
      5.5% {{ opacity: 0.15; }}
      18% {{ opacity: 1; }}
      100% {{ opacity: 1; }}
    }}
    @keyframes arsn-lit-lift {{
      0% {{ transform: translateY(0); }}
      0.9% {{ transform: translateY(-3px); }}
      5.5% {{ transform: translateY(-3px); }}
      18% {{ transform: translateY(0); }}
      100% {{ transform: translateY(0); }}
    }}
    @keyframes arsn-lit-lbl {{
      0% {{ fill: #8b7fb0; }}
      0.9% {{ fill: #f5f3ff; }}
      5.5% {{ fill: #f5f3ff; }}
      18% {{ fill: #8b7fb0; }}
      100% {{ fill: #8b7fb0; }}
    }}
    @keyframes arsn-lit-rim {{
      0% {{ opacity: 0; }}
      0.9% {{ opacity: 0.9; }}
      5.5% {{ opacity: 0.9; }}
      18% {{ opacity: 0; }}
      100% {{ opacity: 0; }}
    }}
    /* B3 Fix: Transform scale instead of CSS r for cross-browser Safari support */
    @keyframes arsn-ripple {{
      0% {{ transform: scale(1); opacity: 0.9; }}
      6.5% {{ transform: scale(5); opacity: 0; }}
      100% {{ transform: scale(5); opacity: 0; }}
    }}

    /* B1 Fix: Relative translation in animated children */
    .anim-spine {{
      opacity: 0;
      transform: translateY(0);
      animation: arsn-spine-down {CYCLE_S}s infinite linear;
      animation-delay: 0.40s;
      animation-fill-mode: both;
    }}
    @keyframes arsn-spine-down {{
      0% {{ transform: translateY(0); opacity: 0; }}
      0.5% {{ opacity: 1; }}
      19.9% {{ transform: translateY(590px); opacity: 1; }}
      20.2% {{ transform: translateY(590px); opacity: 0; }}
      100% {{ transform: translateY(590px); opacity: 0; }}
    }}

    .anim-comet {{
      opacity: 0;
      transform: translateX(46px);
      animation: arsn-comet-travel {CYCLE_S}s infinite linear;
      animation-delay: var(--cd);
      animation-fill-mode: both;
    }}
    @keyframes arsn-comet-travel {{
      0% {{ transform: translateX(46px); opacity: 0; }}
      1.2% {{ opacity: 1; }}
      35% {{ opacity: 1; }}
      37% {{ transform: translateX(794px); opacity: 0; }}
      100% {{ transform: translateX(794px); opacity: 0; }}
    }}

    .anim-glint {{
      opacity: 0;
      transform: translateX(-240px) rotate(-20deg);
      animation: arsn-glint-pass {CYCLE_S}s infinite linear;
    }}
    @keyframes arsn-glint-pass {{
      0%, 70.7% {{ transform: translateX(-240px) rotate(-20deg); opacity: 0; }}
      72% {{ opacity: 0.10; }}
      82% {{ opacity: 0.10; }}
      83.8%, 100% {{ transform: translateX(1100px) rotate(-20deg); opacity: 0; }}
    }}

    .lbl {{ font-size: 9.5px; font-weight: 600; fill: #8b7fb0; }}

    @media (max-width: 640px) {{
      .lbl {{ display: none; }}
      .hdr-dot {{ display: none; }}
      .ico-s {{ transform: scale(1.35) translateY(5px); transform-box: fill-box; transform-origin: center; }}
      .ftr-txt {{ display: none; }}
    }}
    @media (max-width: 440px) {{
      .ico-s {{ transform: scale(1.4) translateY(6px); transform-box: fill-box; transform-origin: center; }}
      .hdr-txt {{ font-size: 13px !important; letter-spacing: 2px !important; }}
      .grp-cnt {{ display: none; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      * {{ animation: none !important; }}
      .anim-lit-op {{ opacity: 1 !important; }}
      .anim-lit-inv {{ opacity: 0.15 !important; }}
    }}
  </style>

  {common_card_defs(prefix, w, h)}
  <defs>
    <!-- Duotone Matrix & Gradient Map Filter -->
    <filter id="{prefix}_duo" color-interpolation-filters="sRGB">
      <feColorMatrix type="matrix" values="0.2126 0.7152 0.0722 0 0  0.2126 0.7152 0.0722 0 0  0.2126 0.7152 0.0722 0 0  0 0 0 1 0" result="gray" />
      <feComponentTransfer in="gray" result="duo">
        <feFuncR type="table" tableValues="0.576 0.753 0.961" />
        <feFuncG type="table" tableValues="0.200 0.518 0.953" />
        <feFuncB type="table" tableValues="0.918 0.988 1.000" />
      </feComponentTransfer>
    </filter>

    <linearGradient id="{prefix}_panel_grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#140a2b" stop-opacity="0.85" />
      <stop offset="100%" stop-color="#0b0618" stop-opacity="0.85" />
    </linearGradient>

    <linearGradient id="{prefix}_tile_body" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1a0f33" />
      <stop offset="100%" stop-color="#0b0618" />
    </linearGradient>

    <linearGradient id="{prefix}_tile_bevel" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.40" />
      <stop offset="100%" stop-color="#2e1065" stop-opacity="0.15" />
    </linearGradient>

    <radialGradient id="{prefix}_plate_grad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#241446" />
      <stop offset="100%" stop-color="#120a26" />
    </radialGradient>

    <radialGradient id="{prefix}_comet_glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#f5d0fe" stop-opacity="0.9" />
      <stop offset="40%" stop-color="#c084fc" stop-opacity="0.4" />
      <stop offset="100%" stop-color="#a855f7" stop-opacity="0.0" />
    </radialGradient>

    <linearGradient id="{prefix}_comet_tail" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.0" />
      <stop offset="60%" stop-color="#c084fc" stop-opacity="0.6" />
      <stop offset="100%" stop-color="#f5d0fe" stop-opacity="1.0" />
    </linearGradient>

    <linearGradient id="{prefix}_glint_grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f5d0fe" stop-opacity="0.0" />
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0.10" />
      <stop offset="100%" stop-color="#e9d5ff" stop-opacity="0.0" />
    </linearGradient>

    <linearGradient id="{prefix}_spine_tail" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#6d28d9" stop-opacity="0.0" />
      <stop offset="70%" stop-color="#c084fc" stop-opacity="0.6" />
      <stop offset="100%" stop-color="#f5d0fe" stop-opacity="1.0" />
    </linearGradient>

    <clipPath id="{prefix}_glint_clip">
      <rect x="0" y="0" width="{w}" height="{h}" rx="14" />
    </clipPath>

    <!-- Group Stroke Tint Gradients -->
    <linearGradient id="{prefix}_panel_stroke_0" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.35" /><stop offset="100%" stop-color="#a855f7" stop-opacity="0.08" />
    </linearGradient>
    <linearGradient id="{prefix}_panel_stroke_1" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.35" /><stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.08" />
    </linearGradient>
    <linearGradient id="{prefix}_panel_stroke_2" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#e879f9" stop-opacity="0.35" /><stop offset="100%" stop-color="#e879f9" stop-opacity="0.08" />
    </linearGradient>
    <linearGradient id="{prefix}_panel_stroke_3" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#c084fc" stop-opacity="0.35" /><stop offset="100%" stop-color="#c084fc" stop-opacity="0.08" />
    </linearGradient>

    <!-- 29 Vendored Icons in Defs -->
    {icons_defs_markup}
  </defs>

  {lava_border_frame(prefix, w, h, delay_offset=20)}

  <!-- Ambient Dust Particles -->
  {dust_markup}

  <!-- Header -->
  <g transform="translate(68, 30)">
    <g transform="translate(0, 0)">
      <rect x="0" y="-12" width="4.5" height="24" rx="2" fill="#c084fc">
        <animateTransform attributeName="transform" type="scale" values="1 0.3; 1 1.0; 1 0.4" dur="1.2s" repeatCount="indefinite" />
      </rect>
    </g>
    <g transform="translate(8, 0)">
      <rect x="0" y="-16" width="4.5" height="32" rx="2" fill="#9333ea">
        <animateTransform attributeName="transform" type="scale" values="1 0.8; 1 0.2; 1 0.9" dur="1.6s" repeatCount="indefinite" />
      </rect>
    </g>
    <g transform="translate(16, 0)">
      <rect x="0" y="-8" width="4.5" height="16" rx="2" fill="#d8b4fe">
        <animateTransform attributeName="transform" type="scale" values="1 0.2; 1 1.0; 1 0.5" dur="1.4s" repeatCount="indefinite" />
      </rect>
    </g>
  </g>

  <g transform="translate({w/2}, 38)" text-anchor="middle" class="flicker-op">
    <text x="0" y="0" fill="#a855f7" font-size="16" font-weight="900" letter-spacing="4" filter="url(#{prefix}_glow_filter)" class="hdr-txt">CORE TECH STACK &amp; ARSENAL</text>
    <text x="-1.5" y="0" fill="#4c1d95" font-size="16" font-weight="900" letter-spacing="4" class="hdr-txt">CORE TECH STACK &amp; ARSENAL</text>
    <text x="0" y="0" fill="#f5f3ff" font-size="16" font-weight="900" letter-spacing="4" class="hdr-txt">CORE TECH STACK &amp; ARSENAL</text>
  </g>

  <g transform="translate({w-94}, 30)">
    <g transform="translate(0, 0)">
      <rect x="0" y="-8" width="4.5" height="16" rx="2" fill="#d8b4fe">
        <animateTransform attributeName="transform" type="scale" values="1 0.4; 1 1.0; 1 0.3" dur="1.3s" repeatCount="indefinite" />
      </rect>
    </g>
    <g transform="translate(8, 0)">
      <rect x="0" y="-16" width="4.5" height="32" rx="2" fill="#9333ea">
        <animateTransform attributeName="transform" type="scale" values="1 0.9; 1 0.3; 1 0.8" dur="1.7s" repeatCount="indefinite" />
      </rect>
    </g>
    <g transform="translate(16, 0)">
      <rect x="0" y="-12" width="4.5" height="24" rx="2" fill="#c084fc">
        <animateTransform attributeName="transform" type="scale" values="1 0.2; 1 0.9; 1 0.4" dur="1.1s" repeatCount="indefinite" />
      </rect>
    </g>
  </g>

  <!-- Left Signal-Bus Spine & Rotating Core Node -->
  <line x1="22" y1="66" x2="22" y2="656" stroke="#2e1065" stroke-width="2" />
  <line x1="22" y1="66" x2="22" y2="656" stroke="#4c1d95" stroke-width="1.6" stroke-dasharray="2 6" />

  <g transform="translate(22, 66)">
    <circle r="9" fill="none" stroke="#a855f7" stroke-width="1.2" stroke-dasharray="3 3">
      <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="40s" repeatCount="indefinite" />
    </circle>
    <circle r="5" fill="#05030a" stroke="#c084fc" stroke-width="1.2" />
    <circle r="2.4" fill="#f5d0fe" />
  </g>

  <!-- 4 Glass Panels -->
  {"".join(panels_markup)}

  <!-- Rails, Nodes, Stubs -->
  {"".join(rails_markup)}

  <!-- 29 Interactive Justified Tiles -->
  {"".join(tiles_markup)}

  <!-- B1 Fix: Spine Pulse in Two-Layer Static Wrapper -->
  <g transform="translate(22, 66)">
    <g class="anim-spine">
      <line x1="0" y1="-40" x2="0" y2="0" stroke="url(#{prefix}_spine_tail)" stroke-width="3" stroke-linecap="round" />
      <circle cx="0" cy="0" r="3" fill="#f5d0fe" />
    </g>
  </g>

  <!-- Light Comets -->
  {"".join(comets_markup)}

  <!-- Glint Sweep Finale -->
  <g clip-path="url(#{prefix}_glint_clip)">
    <rect class="anim-glint" x="0" y="-50" width="120" height="820" fill="url(#{prefix}_glint_grad)" />
  </g>

  <!-- Footer Strip -->
  <g transform="translate(0, 674)">
    <rect x="30" y="0" width="780" height="24" rx="4" fill="#07040f" stroke="#1f1138" stroke-width="0.8" />
    <text x="44" y="15" fill="#8b7fb0" font-size="9.5" class="mono ftr-txt">{footer_str}</text>
    <text x="796" y="15" fill="#8b7fb0" font-size="9.5" text-anchor="end" class="mono ftr-txt">{counts_str}</text>
  </g>
</svg>"""

# ==============================================================================
# FASE 4: SELFTEST & VALIDATION PIPELINE
# ==============================================================================
def run_selftest():
    print("=================== RUNNING ARSENAL MASTER SELFTEST ===================")
    
    # 1. Manifest guard (Strict [9, 6, 7, 7])
    assert len(ALL_ITEMS) == 29, f"Test 1 Failed: Expected 29 items, got {len(ALL_ITEMS)}"
    group_lens = [len(g.items) for g in MANIFEST]
    assert group_lens == [9, 6, 7, 7], f"Test 1 Failed: Expected [9, 6, 7, 7], got {group_lens}"
    print("[PASS] Test 1: Manifest guard (29 tools in exact 4 groups)")

    # 2. Icon files & lock validation (Offline guard, zero network)
    icons_map, brand_colors = load_icons()
    for item in ALL_ITEMS:
        assert item.key in icons_map, f"Test 2 Failed: Missing icon {item.key}"
    print("[PASS] Test 2: Vendored icons verified & locked via icons.lock")

    # 3. Deterministic Render & XML Namespace-Aware Validation (B4 Fix)
    fixed_now = dt.datetime(2026, 10, 4, 12, 0, 0, tzinfo=dt.timezone.utc)
    svg_1 = build_arsenal_svg(icons_map, brand_colors, fixed_now)
    root = ET.fromstring(svg_1)
    
    for tag in ["script", "foreignObject", "a"]:
        assert len(root.findall(f".//{{*}}{tag}")) == 0, f"Test 3 Failed: Disallowed tag <{tag}> found in SVG"

    # Self-test proving B4 check actually detects forbidden tags
    mock_svg = '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    mock_root = ET.fromstring(mock_svg)
    assert len(mock_root.findall(".//{*}script")) == 1, "Test 3 Failed: Namespace check failed to catch mock script"
    
    no_image_svg = re.sub(r'<image\b[^>]*>', '', svg_1)
    forbidden_urls = re.findall(r'https?://[^\s"\'<>]+', no_image_svg)
    for u in forbidden_urls:
        assert u == "http://www.w3.org/2000/svg", f"Test 3 Failed: External URL found: {u}"
    print("[PASS] Test 3: Namespace-aware XML valid, isolated and zero external dependencies")

    # 4. Palette Audit on Chrome (data-brand and image excluded)
    no_brand_svg = re.sub(r'<[^>]+data-brand="true"[^>]*>', '', no_image_svg)
    hex_matches = re.findall(r"#[0-9a-fA-F]{6}", no_brand_svg)
    for hx in hex_matches:
        hx_low = hx.lower()
        r, g, b = int(hx_low[1:3], 16)/255.0, int(hx_low[3:5], 16)/255.0, int(hx_low[5:7], 16)/255.0
        h_deg, s, v = colorsys.rgb_to_hsv(r, g, b)
        h_deg *= 360.0
        if s > 0.35 and v > 0.3:
            is_yellow = 20 <= h_deg <= 75
            is_cyan = 180 <= h_deg <= 250
            assert not is_yellow, f"Forbidden yellow/gold {hx} in chrome (hue {h_deg:.1f})"
            assert not is_cyan, f"Forbidden cyan/blue {hx} in chrome (hue {h_deg:.1f})"
    print("[PASS] Test 4: Palette audit passed (0% forbidden hues in chrome)")

    # 5. Timeline Lint (Monotonic & B1/B2 Checks)
    groups = compute_layout_and_timeline(brand_colors)
    for b_idx, gl in enumerate(groups):
        assert 0.0 <= gl.s_b < CYCLE_S, f"s_b out of bounds: {gl.s_b}"
        assert 0.0 <= gl.l_b < CYCLE_S, f"l_b out of bounds: {gl.l_b}"
        expected_sb = [1.02, 1.68, 2.34, 3.00][b_idx]
        assert abs(gl.s_b - expected_sb) < 0.02, f"s_b deviation: {gl.s_b} vs {expected_sb}"
        prev_t = -1.0
        for t in gl.tiles:
            assert 0.0 <= t.delay < CYCLE_S, f"tile delay out of bounds: {t.delay}"
            assert t.t_peak > prev_t, f"t_peak not monotonic: {t.t_peak} <= {prev_t}"
            prev_t = t.t_peak
    print("[PASS] Test 5: Timeline lint passed (monotonic cascade within 13s)")

    # 6. Determinism Check
    svg_2 = build_arsenal_svg(icons_map, brand_colors, fixed_now)
    assert hashlib.sha256(svg_1.encode("utf-8")).hexdigest() == hashlib.sha256(svg_2.encode("utf-8")).hexdigest()
    print("[PASS] Test 6: Determinism verified (identical sha256 bytes)")

    # 7. Budget Checks
    size_kb = len(svg_1.encode("utf-8")) / 1024.0
    anim_nodes = len(re.findall(r'<animate|<animateTransform|class="[^"]*anim-[^"]*"', svg_1))
    assert size_kb < LIMIT_KB, f"File size {size_kb:.1f} KB exceeds {LIMIT_KB} KB limit"
    assert anim_nodes <= 600, f"Animated elements count {anim_nodes} exceeds 600 limit"
    print(f"[PASS] Test 7: Budget checks passed ({size_kb:.1f} KB < {LIMIT_KB} KB, {anim_nodes} anim elements <= 600)")

    # 8. AST Inspection (Zero hardcoded mock statistics)
    forbidden_nums = {int(x) for x in ["95", "99", "1000"]}
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=__file__)
    for item in tree.body:
        if isinstance(item, ast.FunctionDef) and item.name == "build_arsenal_svg":
            for node in ast.walk(item):
                if isinstance(node, ast.Constant) and isinstance(node.value, int):
                    assert node.value not in forbidden_nums, f"Mock number {node.value} in builder AST"
    print("[PASS] Test 8: AST inspection confirms zero mock statistics")
    print("=================== [MASTER SELFTEST PASSED 100%] ===================")

# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Studio-Grade Signal-Bus Arsenal Generator (Master Level)")
    parser.add_argument("--out", default="dist", help="Output directory")
    parser.add_argument("--selftest", action="store_true", help="Execute offline unit selftest suite")
    parser.add_argument("--sync-icons", action="store_true", help="Fetch, pin, and lock all 29 manifest icons")
    parser.add_argument("--now", default=None, help="Fix build timestamp (ISO 8601 UTC)")
    args = parser.parse_args()

    if args.sync_icons:
        sync_icons()
        sys.exit(0)

    if args.selftest:
        run_selftest()
        sys.exit(0)

    if args.now:
        now_dt = dt.datetime.fromisoformat(args.now)
    else:
        now_dt = dt.datetime.now(dt.timezone.utc)

    icons_map, brand_colors = load_icons()
    svg_content = build_arsenal_svg(icons_map, brand_colors, now_dt)

    ET.fromstring(svg_content)

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / OUT_NAME

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(svg_content.strip())

    size_kb = out_file.stat().st_size / 1024.0
    print(f"[🚀] Generated: {out_file} ({size_kb:.1f} KB)")
    assert size_kb < LIMIT_KB, f"File size {size_kb:.1f} KB exceeds {LIMIT_KB} KB limit"

if __name__ == "__main__":
    main()
