#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Studio-Grade Signal-Bus Arsenal Stack
Pure Native Python Standard Library - Zero External Dependencies
Palette: Monochromatic Violet & Lilac Chrome with Dynamic Brand Ignition Cascade
Generates 1 Validated, XML-Compliant Animated SVG: dist/arsenal-stack.svg (< 300 KB)
CLI Options:
  --out DIR         Output directory (default: dist)
  --selftest        Run offline unit selftest suite (fail-closed exit 1)
  --sync-icons      Download and vendor all 29 icons to .github/assets/icons/
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

# Import visual chrome dari metrics_cards jika ada di direktori yang sama
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
CYCLE_S = 12.0
COMET_S = 4.8
REST_MODE = "duotone"  # "duotone" | "muted"
PARTICLES = 12
LIMIT_KB = 300
OUT_NAME = "arsenal-stack.svg"
ICONS_DIR = pathlib.Path(".github/assets/icons")

DEVICON_BASE = "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons"
LOBE_BASE = "https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons"
LOBE_PNG_BASE = "https://cdn.jsdelivr.net/npm/@lobehub/icons-static-png@latest/dark"

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
    items: Tuple[ToolItem, ...]

MANIFEST: Tuple[ToolGroup, ...] = (
    ToolGroup(
        title="Languages & Core Technologies",
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
TOTAL_TOOLS = len(ALL_ITEMS)  # 29 tools
TOTAL_GROUPS = len(MANIFEST)  # 4 groups

# ==============================================================================
# ICON PIPELINE & NORMALIZATION
# ==============================================================================
def normalize_svg_content(raw_svg: str, is_mono: bool) -> str:
    s = re.sub(r'<\?xml[^>]*\?>', '', raw_svg, flags=re.DOTALL)
    s = re.sub(r'<!DOCTYPE[^>]*>', '', s, flags=re.DOTALL)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.DOTALL)
    s = re.sub(r'<title>.*?</title>', '', s, flags=re.DOTALL)
    s = re.sub(r'<metadata>.*?</metadata>', '', s, flags=re.DOTALL)
    s = s.strip()

    if "viewBox" not in s and "<svg" in s:
        w_match = re.search(r'width=["\']([0-9.]+)p?x?["\']', s)
        h_match = re.search(r'height=["\']([0-9.]+)p?x?["\']', s)
        if w_match and h_match:
            w_val = float(w_match.group(1))
            h_val = float(h_match.group(1))
            s = re.sub(r'<svg\b', f'<svg viewBox="0 0 {w_val} {h_val}"', s, count=1)

    if is_mono:
        s = s.replace("currentColor", "#f5f3ff")
        s = re.sub(r'fill=["\'](#000|#000000|black|#111|#111111)["\']', 'fill="#f5f3ff"', s)

    return s

def sync_icons(dest_dir: pathlib.Path = ICONS_DIR):
    dest_dir.mkdir(parents=True, exist_ok=True)
    print("================== SYNCING ARSENAL ICONS ==================")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SignalBusSync/1.0"}

    for item in ALL_ITEMS:
        svg_target = dest_dir / f"{item.key}.svg"
        png_target = dest_dir / f"{item.key}.png"

        if svg_target.is_file() and svg_target.stat().st_size > 50:
            continue
        if png_target.is_file() and png_target.stat().st_size > 50:
            continue

        try:
            req = urllib.request.Request(item.url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read()
            text = content.decode("utf-8", errors="replace")
            norm_svg = normalize_svg_content(text, item.is_mono)
            ET.fromstring(norm_svg)
            with open(svg_target, "w", encoding="utf-8") as f:
                f.write(norm_svg)
            print(f"[✓] {item.key:14} -> {svg_target.name} ({len(norm_svg)/1024:.1f} KB)")
        except Exception as e:
            if item.fallback_png:
                try:
                    req_p = urllib.request.Request(item.fallback_png, headers=headers)
                    with urllib.request.urlopen(req_p, timeout=15) as resp_p:
                        p_content = resp_p.read()
                    with open(png_target, "wb") as pf:
                        pf.write(p_content)
                    print(f"[✓] {item.key:14} -> FALLBACK {png_target.name} ({len(p_content)/1024:.1f} KB)")
                    continue
                except Exception as ep:
                    print(f"[!] FAILED fallback for {item.key}: {ep}", file=sys.stderr)
            print(f"[-] ERROR syncing {item.key}: {e}", file=sys.stderr)
            sys.exit(1)

    print("[🚀] All 29 manifest icons successfully synced and verified offline!")

def load_icons(dest_dir: pathlib.Path = ICONS_DIR) -> Dict[str, Tuple[str, str]]:
    missing = [
        item.key for item in ALL_ITEMS
        if not (dest_dir / f"{item.key}.svg").is_file() and not (dest_dir / f"{item.key}.png").is_file()
    ]
    if missing:
        print(f"[*] Missing {len(missing)} vendored icons. Running auto-sync...")
        sync_icons(dest_dir)

    icons: Dict[str, Tuple[str, str]] = {}
    for item in ALL_ITEMS:
        svg_path = dest_dir / f"{item.key}.svg"
        png_path = dest_dir / f"{item.key}.png"

        if svg_path.is_file():
            with open(svg_path, "r", encoding="utf-8") as f:
                content = f.read()
            ET.fromstring(content)
            b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
            icons[item.key] = ("image/svg+xml", b64)
        elif png_path.is_file():
            with open(png_path, "rb") as f:
                p_bytes = f.read()
            assert p_bytes[:8] == b"\x89PNG\r\n\x1a\n", f"Invalid PNG signature for {item.key}"
            b64 = base64.b64encode(p_bytes).decode("ascii")
            icons[item.key] = ("image/png", b64)
        else:
            raise FileNotFoundError(f"Missing vendored icon: {svg_path}. Run with --sync-icons first.")
    return icons

# ==============================================================================
# GEOMETRY & TIMELINE ENGINE
# ==============================================================================
@dataclass
class TileLayout:
    item: ToolItem
    x: float
    y: float
    cx: float
    cy: float
    rail_y: float
    delay: float
    t_peak: float

@dataclass
class GroupLayout:
    group: ToolGroup
    panel_y: float
    rail_y: float
    tiles: List[TileLayout]
    s_b: float
    l_b: float

def compute_layout_and_timeline() -> List[GroupLayout]:
    panel_tops = [72.0, 204.0, 336.0, 468.0]
    S0, SD, D = 0.40, 2.60, 4.80
    y0, y1 = 66.0, 584.0

    groups_layout: List[GroupLayout] = []

    for b, grp in enumerate(MANIFEST):
        top_y = panel_tops[b]
        rail_y = top_y + 116.0
        n_tiles = len(grp.items)

        if n_tiles == 9:
            x0 = 46.0
        elif n_tiles == 6:
            x0 = 172.0
        elif n_tiles == 7:
            x0 = 130.0
        else:
            x0 = (840.0 - (n_tiles * 76.0 + (n_tiles - 1) * 8.0)) / 2.0

        s_b = S0 + SD * ((rail_y - y0) / (y1 - y0))
        l_b = s_b + 0.15

        tiles_list: List[TileLayout] = []
        for i, item in enumerate(grp.items):
            tile_x = x0 + i * (76.0 + 8.0)
            tile_y = top_y + 26.0
            cx = tile_x + 38.0
            cy = tile_y + 39.0
            t_peak = l_b + D * ((cx - 46.0) / 748.0)
            tile_delay = max(0.0, t_peak - 0.12)

            tiles_list.append(TileLayout(
                item=item,
                x=tile_x,
                y=tile_y,
                cx=cx,
                cy=cy,
                rail_y=rail_y,
                delay=tile_delay,
                t_peak=t_peak
            ))

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
# SVG RENDERER: SIGNAL-BUS ARSENAL
# ==============================================================================
def build_arsenal_svg(icons_map: Dict[str, Tuple[str, str]], now_dt: dt.datetime) -> str:
    w, h = 840, 640
    prefix = "arsn"
    groups = compute_layout_and_timeline()

    icon_defs = []
    for item in ALL_ITEMS:
        mime, b64 = icons_map[item.key]
        icon_defs.append(
            f'<image id="{prefix}_ic_{item.key}" width="40" height="40" '
            f'preserveAspectRatio="xMidYMid meet" href="data:{mime};base64,{b64}" />'
        )
    icons_defs_markup = "\n    ".join(icon_defs)

    rng = random.Random(2026)
    dust_particles = []
    for _ in range(PARTICLES):
        px = rng.uniform(40.0, 800.0)
        py = rng.uniform(80.0, 580.0)
        pr = rng.uniform(0.8, 1.5)
        p_dur = rng.uniform(18.0, 30.0)
        p_del = rng.uniform(0.0, 12.0)
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
        # XML-Safe escaped title
        safe_title = escape(gl.group.title)

        panels_markup.append(f"""
    <!-- Panel {b+1}: {safe_title} -->
    <rect x="30" y="{py}" width="780" height="124" rx="14" fill="url(#{prefix}_panel_grad)" stroke="#a855f7" stroke-opacity="0.14" stroke-width="1" />
    <line x1="38" y1="{py+1}" x2="802" y2="{py+1}" stroke="#e9d5ff" stroke-opacity="0.10" stroke-width="1" />
    <circle cx="46" cy="{py+12}" r="2.2" fill="#c084fc">
      <animate attributeName="opacity" values="1;0.3;1" dur="2.4s" repeatCount="indefinite" begin="{b*0.5:.1f}s" />
    </circle>
    <text x="54" y="{py+16}" fill="#a855f7" font-size="12.5" font-weight="800">{safe_title}</text>
    <text x="794" y="{py+16}" fill="#8b7fb0" font-size="9.5" text-anchor="end" class="mono grp-cnt">{cnt} tools</text>
    <line x1="46" y1="{py+21}" x2="794" y2="{py+21}" stroke="#a855f7" stroke-opacity="0.10" stroke-dasharray="3 3" />
        """)

        rails_markup.append(f"""
    <!-- Rail & Branch for Panel {b+1} -->
    <line x1="22" y1="{ry}" x2="46" y2="{ry}" stroke="#2e1065" stroke-width="1.4" />
    <line x1="46" y1="{ry}" x2="794" y2="{ry}" stroke="#2e1065" stroke-width="1.4" />
    <line x1="46" y1="{ry}" x2="794" y2="{ry}" stroke="#4c1d95" stroke-width="1.4" stroke-dasharray="2 6" />
    
    <!-- Source Port Ring -->
    <circle cx="46" cy="{ry}" r="4" fill="#05030a" stroke="#a855f7" stroke-width="1.4" />
    <circle cx="46" cy="{ry}" r="1.8" fill="#f5d0fe" />
    <circle cx="46" cy="{ry}" r="4" fill="none" stroke="#f5d0fe" stroke-width="1.2" class="lit-ripple" style="--d:{gl.s_b:.2f}s" />

    <!-- Terminal Diamond -->
    <g transform="translate(794, {ry})">
      <polygon points="0,-4.5 4.5,0 0,4.5 -4.5,0" fill="#6d28d9" />
      <polygon points="0,-4.5 4.5,0 0,4.5 -4.5,0" fill="#f5d0fe" class="lit-op" style="--d:{gl.l_b + COMET_S - 0.1:.2f}s" />
    </g>
        """)

        for t in gl.tiles:
            tx, ty, tcx = t.x, t.y, t.cx
            d_s = f"{t.delay:.2f}s"
            key = t.item.key
            name = escape(t.item.name)

            lbl_len_attr = 'textLength="68" lengthAdjust="spacingAndGlyphs"' if len(t.item.name) >= 12 else ''

            rails_markup.append(f"""
    <line x1="{tcx}" y1="{ty + 78}" x2="{tcx}" y2="{ry}" stroke="#4c1d95" stroke-width="1.2" />
    <circle cx="{tcx}" cy="{ry}" r="2" fill="#6d28d9" />
    <circle cx="{tcx}" cy="{ry}" r="3.2" fill="#f5d0fe" class="lit-op" style="--d:{d_s}" />
    <circle cx="{tcx}" cy="{ry}" r="2" fill="none" stroke="#f5d0fe" stroke-width="1.2" class="lit-ripple" style="--d:{d_s}" />
            """)

            tiles_markup.append(f"""
    <g class="tile" transform="translate({tx:.1f}, {ty:.1f})" style="--d:{d_s}">
      <rect x="0" y="0" width="76" height="78" rx="12" fill="#0d0820" stroke="#a855f7" stroke-opacity="0.18" stroke-width="1" />
      <rect x="0" y="0" width="76" height="78" rx="12" fill="url(#{prefix}_tile_grad)" />
      <line x1="8" y1="1" x2="68" y2="1" stroke="#e9d5ff" stroke-opacity="0.12" stroke-width="1" />
      <ellipse cx="38" cy="74" rx="32" ry="14" fill="url(#{prefix}_floor_glow)" opacity="0.12" />
      <ellipse cx="38" cy="74" rx="32" ry="14" fill="url(#{prefix}_floor_glow)" class="lit-op" />
      <rect x="0" y="0" width="76" height="78" rx="12" fill="none" stroke="#c084fc" stroke-width="1.5" class="lit-rim" />
      <g class="lift lit-lift">
        <g transform="translate(18, 12)">
          <g class="ico-s">
            <g class="base lit-inv"><use href="#{prefix}_ic_{key}" filter="url(#{prefix}_duo)" /></g>
            <g class="color lit-op"><use href="#{prefix}_ic_{key}" /></g>
          </g>
        </g>
        <text class="lbl lit-lbl" x="38" y="68" text-anchor="middle" {lbl_len_attr}>{name}</text>
      </g>
    </g>
            """)

        comets_markup.append(f"""
    <!-- Comet for Panel {b+1} -->
    <g class="comet-rail" transform="translate(46, {ry})" style="--cd:{gl.l_b:.2f}s">
      <line x1="-70" y1="0" x2="0" y2="0" stroke="url(#{prefix}_comet_tail)" stroke-width="2" stroke-linecap="round" />
      <circle cx="0" cy="0" r="10" fill="url(#{prefix}_comet_glow)" />
      <circle cx="0" cy="0" r="3.2" fill="#f5d0fe" />
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

    .lit-op {{ animation: arsn-lit-op {CYCLE_S}s infinite ease-out; animation-delay: var(--d); }}
    .lit-inv {{ animation: arsn-lit-inv {CYCLE_S}s infinite ease-out; animation-delay: var(--d); }}
    .lit-lift {{ animation: arsn-lit-lift {CYCLE_S}s infinite ease-out; animation-delay: var(--d); }}
    .lit-lbl {{ animation: arsn-lit-lbl {CYCLE_S}s infinite ease-out; animation-delay: var(--d); }}
    .lit-rim {{ animation: arsn-lit-rim {CYCLE_S}s infinite ease-out; animation-delay: var(--d); opacity: 0; }}
    .lit-ripple {{ animation: arsn-ripple {CYCLE_S}s infinite ease-out; animation-delay: var(--d); opacity: 0; transform-origin: center; }}

    @keyframes arsn-lit-op {{
      0% {{ opacity: 0; }}
      1% {{ opacity: 1; }}
      6% {{ opacity: 1; }}
      20% {{ opacity: 0; }}
      100% {{ opacity: 0; }}
    }}
    @keyframes arsn-lit-inv {{
      0% {{ opacity: 1; }}
      1% {{ opacity: 0.15; }}
      6% {{ opacity: 0.15; }}
      20% {{ opacity: 1; }}
      100% {{ opacity: 1; }}
    }}
    @keyframes arsn-lit-lift {{
      0% {{ transform: translateY(0); }}
      1% {{ transform: translateY(-3px); }}
      6% {{ transform: translateY(-3px); }}
      20% {{ transform: translateY(0); }}
      100% {{ transform: translateY(0); }}
    }}
    @keyframes arsn-lit-lbl {{
      0% {{ fill: #8b7fb0; }}
      1% {{ fill: #f5f3ff; }}
      6% {{ fill: #f5f3ff; }}
      20% {{ fill: #8b7fb0; }}
      100% {{ fill: #8b7fb0; }}
    }}
    @keyframes arsn-lit-rim {{
      0% {{ opacity: 0; }}
      1% {{ opacity: 0.9; }}
      6% {{ opacity: 0.9; }}
      20% {{ opacity: 0; }}
      100% {{ opacity: 0; }}
    }}
    @keyframes arsn-ripple {{
      0% {{ r: 3.2px; opacity: 0.9; }}
      7.5% {{ r: 18px; opacity: 0; }}
      100% {{ r: 18px; opacity: 0; }}
    }}

    .spine-pulse {{
      animation: arsn-spine-down {CYCLE_S}s infinite linear;
      animation-delay: 0.40s;
    }}
    @keyframes arsn-spine-down {{
      0% {{ transform: translateY(66px); opacity: 0; }}
      0.5% {{ opacity: 1; }}
      21.6% {{ transform: translateY(584px); opacity: 1; }}
      22% {{ transform: translateY(584px); opacity: 0; }}
      100% {{ transform: translateY(584px); opacity: 0; }}
    }}

    .comet-rail {{
      animation: arsn-comet-travel {CYCLE_S}s infinite linear;
      animation-delay: var(--cd);
    }}
    @keyframes arsn-comet-travel {{
      0% {{ transform: translate(46px, 0); opacity: 0; }}
      1.5% {{ opacity: 1; }}
      38% {{ opacity: 1; }}
      40% {{ transform: translate(794px, 0); opacity: 0; }}
      100% {{ transform: translate(794px, 0); opacity: 0; }}
    }}

    .glint-sweep {{
      animation: arsn-glint-pass {CYCLE_S}s infinite linear;
    }}
    @keyframes arsn-glint-pass {{
      0%, 71% {{ transform: translateX(-240px) rotate(-20deg); opacity: 0; }}
      73% {{ opacity: 0.10; }}
      88% {{ opacity: 0.10; }}
      90%, 100% {{ transform: translateX(1080px) rotate(-20deg); opacity: 0; }}
    }}

    .lbl {{ font-size: 9px; font-weight: 600; fill: #8b7fb0; }}

    @media (max-width: 640px) {{
      .lbl {{ display: none; }}
      .ico-s {{ transform: scale(1.4) translateY(6px); transform-box: fill-box; transform-origin: center; }}
      .ftr-txt {{ display: none; }}
    }}
    @media (max-width: 440px) {{
      .ico-s {{ transform: scale(1.5) translateY(6px); transform-box: fill-box; transform-origin: center; }}
      .hdr-txt {{ font-size: 13px !important; letter-spacing: 2px !important; }}
      .grp-cnt {{ display: none; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      * {{ animation: none !important; }}
      .lit-op {{ opacity: 1 !important; }}
      .lit-inv {{ opacity: 0.15 !important; }}
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
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.07" />
      <stop offset="100%" stop-color="#a855f7" stop-opacity="0.0" />
    </linearGradient>

    <linearGradient id="{prefix}_tile_grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.10" />
      <stop offset="100%" stop-color="#a855f7" stop-opacity="0.0" />
    </linearGradient>

    <radialGradient id="{prefix}_floor_glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#6d28d9" stop-opacity="0.90" />
      <stop offset="100%" stop-color="#6d28d9" stop-opacity="0.0" />
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

    <!-- 29 Vendored Icons Embedded Once in Defs -->
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

  <!-- Left Signal-Bus Spine -->
  <line x1="22" y1="66" x2="22" y2="584" stroke="#2e1065" stroke-width="1.4" />
  <line x1="22" y1="66" x2="22" y2="584" stroke="#4c1d95" stroke-width="1.4" stroke-dasharray="2 6" />

  <!-- Core Node Source at Top of Spine -->
  <circle cx="22" cy="66" r="4" fill="#05030a" stroke="#a855f7" stroke-width="1.4" />
  <circle cx="22" cy="66" r="2" fill="#f5d0fe" />

  <!-- 4 Glass Panels -->
  {"".join(panels_markup)}

  <!-- Rails, Nodes, Stubs -->
  {"".join(rails_markup)}

  <!-- 29 Interactive Tiles -->
  {"".join(tiles_markup)}

  <!-- Spine Pulse Down -->
  <g class="spine-pulse" transform="translate(22, 66)">
    <line x1="0" y1="-32" x2="0" y2="0" stroke="url(#{prefix}_spine_tail)" stroke-width="2.6" stroke-linecap="round" />
    <circle cx="0" cy="0" r="2.8" fill="#f5d0fe" />
  </g>

  <!-- Light Comets -->
  {"".join(comets_markup)}

  <!-- Full-Card Glint Sweep -->
  <g clip-path="url(#{prefix}_glint_clip)">
    <rect class="glint-sweep" x="0" y="-50" width="120" height="750" fill="url(#{prefix}_glint_grad)" />
  </g>

  <!-- Footer Strip -->
  <g transform="translate(0, 604)">
    <rect x="30" y="0" width="780" height="24" rx="4" fill="#07040f" stroke="#1f1138" stroke-width="0.8" />
    <text x="44" y="15" fill="#8b7fb0" font-size="9.5" class="mono ftr-txt">{footer_str}</text>
    <text x="796" y="15" fill="#8b7fb0" font-size="9.5" text-anchor="end" class="mono ftr-txt">{counts_str}</text>
  </g>
</svg>"""

# ==============================================================================
# SELFTEST & LINT PIPELINE
# ==============================================================================
def run_selftest():
    print("=================== RUNNING ARSENAL SELFTEST ===================")
    
    # 1. Manifest guard
    assert len(ALL_ITEMS) == 29, f"Test 1 Failed: Expected 29 items, got {len(ALL_ITEMS)}"
    group_lens = [len(g.items) for g in MANIFEST]
    assert group_lens == [9, 6, 7, 7], f"Test 1 Failed: Expected [9, 6, 7, 7], got {group_lens}"
    print("[PASS] Test 1: Manifest guard (29 tools in exact 4 groups)")

    # 2. Icon files check
    icons_map = load_icons()
    for item in ALL_ITEMS:
        assert item.key in icons_map, f"Test 2 Failed: Missing icon {item.key}"
    print("[PASS] Test 2: Vendored icons verified (29 files present & valid)")

    # 3. Deterministic Render & XML Validation
    fixed_now = dt.datetime(2026, 10, 4, 12, 0, 0, tzinfo=dt.timezone.utc)
    svg_1 = build_arsenal_svg(icons_map, fixed_now)
    root = ET.fromstring(svg_1)
    
    for tag in ["script", "foreignObject", "a"]:
        assert len(root.findall(f".//{tag}")) == 0, f"Test 3 Failed: Disallowed tag <{tag}> found"
    
    no_image_svg = re.sub(r'<image\b[^>]*>', '', svg_1)
    forbidden_urls = re.findall(r'https?://[^\s"\'<>]+', no_image_svg)
    for u in forbidden_urls:
        assert u == "http://www.w3.org/2000/svg", f"Test 3 Failed: External URL found: {u}"
    print("[PASS] Test 3: XML valid, isolated and zero external dependencies")

    # 4. Palette Audit on Chrome
    hex_matches = re.findall(r"#[0-9a-fA-F]{6}", no_image_svg)
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

    # 5. Timeline Lint
    groups = compute_layout_and_timeline()
    for gl in groups:
        assert 0.0 <= gl.s_b < CYCLE_S, f"s_b out of bounds: {gl.s_b}"
        assert 0.0 <= gl.l_b < CYCLE_S, f"l_b out of bounds: {gl.l_b}"
        prev_t = -1.0
        for t in gl.tiles:
            assert 0.0 <= t.delay < CYCLE_S, f"tile delay out of bounds: {t.delay}"
            assert t.t_peak > prev_t, f"t_peak not monotonic: {t.t_peak} <= {prev_t}"
            prev_t = t.t_peak
    print("[PASS] Test 5: Timeline lint passed (monotonic cascade within 12s)")

    # 6. Determinism Check
    svg_2 = build_arsenal_svg(icons_map, fixed_now)
    assert hashlib.sha256(svg_1.encode("utf-8")).hexdigest() == hashlib.sha256(svg_2.encode("utf-8")).hexdigest()
    print("[PASS] Test 6: Determinism verified (identical sha256 bytes)")

    # 7. Budget Checks
    size_kb = len(svg_1.encode("utf-8")) / 1024.0
    anim_nodes = len(re.findall(r'<animate|<animateTransform|class="[^"]*(?:lit-|pulse|comet|glint)[^"]*"', svg_1))
    assert size_kb < LIMIT_KB, f"File size {size_kb:.1f} KB exceeds {LIMIT_KB} KB limit"
    assert anim_nodes <= 450, f"Animated elements count {anim_nodes} exceeds 450 limit"
    print(f"[PASS] Test 7: Budget checks passed ({size_kb:.1f} KB < {LIMIT_KB} KB, {anim_nodes} anim elements <= 450)")

    # 8. AST Inspection
    forbidden_nums = {int(x) for x in ["95", "99", "1000"]}
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=__file__)
    for item in tree.body:
        if isinstance(item, ast.FunctionDef) and item.name == "build_arsenal_svg":
            for node in ast.walk(item):
                if isinstance(node, ast.Constant) and isinstance(node.value, int):
                    assert node.value not in forbidden_nums, f"Mock number {node.value} in builder AST"
    print("[PASS] Test 8: AST inspection confirms zero mock statistics")
    print("=================== [ARSENAL SELFTEST PASSED 100%] ===================")

# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Studio-Grade Signal-Bus Arsenal Generator")
    parser.add_argument("--out", default="dist", help="Output directory")
    parser.add_argument("--selftest", action="store_true", help="Execute offline unit selftest suite")
    parser.add_argument("--sync-icons", action="store_true", help="Fetch and vendor all 29 manifest icons")
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

    icons_map = load_icons()
    svg_content = build_arsenal_svg(icons_map, now_dt)

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
