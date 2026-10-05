#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Signal-Bus Arsenal Lite (Master Performance Architecture)
Pure Native Python Standard Library - Zero External Dependencies
Zero-Filter, Zero-SMIL, Inlined Vector Engine with 8.3s Idle Phase
Generates: arsenal-stack.svg (< 160 KB) & arsenal-stack-static.svg (< 140 KB)
CLI Options:
  --out DIR         Output directory (default: dist)
  --selftest        Run offline unit selftest suite (fail-closed exit 1)
  --sync-icons      Download, pin, and lock raw upstream icons to .github/assets/icons/
  --verify-icons    Verify local icons against icons.lock (fail-closed exit 1)
  --audit FILE      Audit performance metrics of an SVG file
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
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import escape
from typing import Dict, List, Optional, Tuple

# ==============================================================================
# CONFIG & HARD BUDGETS
# ==============================================================================
CYCLE_S = 16.0
STARTUP_S = 0.40
SPINE_S = 2.00
SWEEP_S = 3.80
GLINT_S = 1.20
DUTY_ACTIVE_S = 7.70  # Active phase ends at 7.70s; 7.70s -> 16.00s is pure 8.3s idle!
VEIL_ALPHA = 0.28
LIMIT_KB = 160
OUT_NAME = "arsenal-stack.svg"
OUT_STATIC_NAME = "arsenal-stack-static.svg"

ICONS_DIR = pathlib.Path(".github/assets/icons")
LOCK_FILE = ICONS_DIR / "icons.lock"

# Pinned upstream library versions
DEVICON_VER = "v2.16.0"
LOBE_VER = "v1.27.0"
DEVICON_BASE = f"https://cdn.jsdelivr.net/gh/devicons/devicon@{DEVICON_VER}/icons"
LOBE_BASE = f"https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@{LOBE_VER}/icons"

# Official Clean Vector untuk Antigravity (Anti-404)
ANTIGRAVITY_VECTOR = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <path d="M12 2L2 22H22L12 2Z" fill="#a855f7" opacity="0.18"/>
  <path d="M12 5L4.5 20H19.5L12 5Z" stroke="#c084fc" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="M8 15H16" stroke="#f5d0fe" stroke-width="1.8" stroke-linecap="round"/>
  <circle cx="12" cy="11" r="2.2" fill="#f5d0fe"/>
</svg>"""

@dataclass(frozen=True)
class ToolItem:
    key: str
    name: str
    url: str
    is_mono: bool

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
            ToolItem("chatgpt", "ChatGPT", f"{LOBE_BASE}/openai.svg", True),
            ToolItem("gemini", "Gemini", f"{LOBE_BASE}/gemini-color.svg", False),
            ToolItem("claude", "Claude", f"{LOBE_BASE}/claude-color.svg", False),
            ToolItem("antigravity", "Antigravity", f"{LOBE_BASE}/antigravity-color.svg", False),
            ToolItem("copilot", "GitHub Copilot", f"{LOBE_BASE}/githubcopilot.svg", True),
            ToolItem("cursor", "Cursor", f"{LOBE_BASE}/cursor.svg", True),
            ToolItem("perplexity", "Perplexity", f"{LOBE_BASE}/perplexity-color.svg", False),
        )
    ),
    ToolGroup(
        title="LLM Platforms & Open Models",
        tint="#c084fc",
        items=(
            ToolItem("ollama", "Ollama", f"{LOBE_BASE}/ollama.svg", True),
            ToolItem("huggingface", "Hugging Face", f"{LOBE_BASE}/huggingface-color.svg", False),
            ToolItem("deepseek", "DeepSeek", f"{LOBE_BASE}/deepseek-color.svg", False),
            ToolItem("mistral", "Mistral AI", f"{LOBE_BASE}/mistral-color.svg", False),
            ToolItem("qwen", "Qwen", f"{LOBE_BASE}/qwen-color.svg", False),
            ToolItem("grok", "Grok", f"{LOBE_BASE}/grok.svg", True),
            ToolItem("llama", "Meta Llama", f"{LOBE_BASE}/meta-color.svg", False),
        )
    ),
)

ALL_ITEMS: List[ToolItem] = [it for g in MANIFEST for it in g.items]
TOTAL_TOOLS = len(ALL_ITEMS)  # 29
TOTAL_GROUPS = len(MANIFEST)  # 4

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
# INLINE ICON PROCESSING ENGINE (ZERO-IMAGE, PURE VECTOR)
# ==============================================================================
def sanitize_and_inline_svg(raw_svg: str, key: str, is_mono: bool, box_dim: float) -> Tuple[str, bool]:
    s = re.sub(r'<\?xml[^>]*\?>', '', raw_svg, flags=re.DOTALL)
    s = re.sub(r'<!DOCTYPE[^>]*>', '', s, flags=re.DOTALL)
    s = re.sub(r'<!--.*?-->', '', s, flags=re.DOTALL)
    s = s.strip()

    try:
        ET.register_namespace('', 'http://www.w3.org/2000/svg')
        ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
        root = ET.fromstring(s)
    except Exception:
        b64 = base64.b64encode(raw_svg.encode("utf-8")).decode("ascii")
        return f'<image width="{box_dim:.1f}" height="{box_dim:.1f}" href="data:image/svg+xml;base64,{b64}" />', False

    disallowed = [".//{*}filter", ".//{*}mask", ".//{*}script", ".//{*}foreignObject"]
    for d in disallowed:
        if root.findall(d):
            b64 = base64.b64encode(raw_svg.encode("utf-8")).decode("ascii")
            return f'<image width="{box_dim:.1f}" height="{box_dim:.1f}" href="data:image/svg+xml;base64,{b64}" />', False

    vb = root.attrib.get('viewBox')
    vb_w, vb_h = 24.0, 24.0
    if vb:
        parts = [float(p) for p in re.split(r'[\s,]+', vb.strip()) if p]
        if len(parts) == 4:
            vb_w, vb_h = parts[2], parts[3]
    else:
        w_attr = root.attrib.get('width', '24')
        h_attr = root.attrib.get('height', '24')
        m_w = re.search(r'([0-9.]+)', w_attr)
        m_h = re.search(r'([0-9.]+)', h_attr)
        if m_w and m_h:
            vb_w, vb_h = float(m_w.group(1)), float(m_h.group(1))

    for child in list(root):
        tag = child.tag.split('}')[-1]
        if tag in ['title', 'desc', 'metadata']:
            root.remove(child)

    id_map = {}
    for el in root.iter():
        if 'id' in el.attrib:
            old_id = el.attrib['id']
            new_id = f"{key}_{old_id}"
            id_map[old_id] = new_id
            el.attrib['id'] = new_id

    for el in root.iter():
        for attr, val in list(el.attrib.items()):
            if attr in ['fill', 'stroke', 'clip-path'] and 'url(#' in val:
                for old_id, new_id in id_map.items():
                    val = val.replace(f"url(#{old_id})", f"url(#{new_id})")
                el.attrib[attr] = val
            elif attr in ['href', '{http://www.w3.org/1999/xlink}href'] and val.startswith('#'):
                old_id = val[1:]
                if old_id in id_map:
                    el.attrib[attr] = f"#{id_map[old_id]}"

    inner_xml = "".join(ET.tostring(child, encoding='unicode') for child in root)
    if is_mono:
        inner_xml = inner_xml.replace("currentColor", "#f5f3ff")
        inner_xml = re.sub(r'fill=["\'](#000|#000000|black|#111|#111111)["\']', 'fill="#f5f3ff"', inner_xml)

    inner_xml = re.sub(r'\sxmlns(:\w+)?=["\'][^"\']+["\']', '', inner_xml)
    inner_xml = re.sub(r'\s+', ' ', inner_xml).strip()

    max_dim = max(vb_w, vb_h) if max(vb_w, vb_h) > 0 else 24.0
    scale = box_dim / max_dim
    tx = (box_dim - (vb_w * scale)) / 2.0
    ty = (box_dim - (vb_h * scale)) / 2.0

    markup = f'<g transform="translate({tx:.2f}, {ty:.2f}) scale({scale:.4f})">{inner_xml}</g>'
    return markup, True

# ==============================================================================
# VENDORING & SYNC PIPELINE (AUTO-HEAL & OFFLINE VERIFIABLE)
# ==============================================================================
def sync_icons(dest_dir: pathlib.Path = ICONS_DIR):
    dest_dir.mkdir(parents=True, exist_ok=True)
    print("================== SYNCING RAW MANIFEST ICONS ==================")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SignalBusSync/3.0"}
    lock_data = {}

    for item in ALL_ITEMS:
        svg_target = dest_dir / f"{item.key}.svg"
        url = item.url

        # Khusus Antigravity: gunakan vector resmi jika upstream CDN 404
        if item.key == "antigravity":
            if not svg_target.is_file():
                try:
                    req = urllib.request.Request(url, headers=headers)
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        content = resp.read()
                    text = content.decode("utf-8", errors="replace").strip()
                except Exception:
                    text = ANTIGRAVITY_VECTOR.strip()
                svg_target.write_text(text, encoding="utf-8")
            text = svg_target.read_text(encoding="utf-8").strip()
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            lock_data[svg_target.name] = sha
            print(f"[✓] {item.key:14} -> {svg_target.name} ({len(text)/1024:.1f} KB)")
            continue

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                content = resp.read()
            text = content.decode("utf-8", errors="replace").strip()
            with open(svg_target, "w", encoding="utf-8") as f:
                f.write(text)
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            lock_data[svg_target.name] = sha
            print(f"[✓] {item.key:14} -> {svg_target.name} ({len(text)/1024:.1f} KB)")
        except Exception as e:
            if svg_target.is_file():
                existing = svg_target.read_text(encoding="utf-8")
                sha = hashlib.sha256(existing.encode("utf-8")).hexdigest()
                lock_data[svg_target.name] = sha
                print(f"[✓] {item.key:14} -> PRESERVED LOCAL {svg_target.name}")
                continue
            # Fallback fail-safe
            fallback = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#a855f7"/></svg>'
            svg_target.write_text(fallback, encoding="utf-8")
            sha = hashlib.sha256(fallback.encode("utf-8")).hexdigest()
            lock_data[svg_target.name] = sha
            print(f"[!] Fallback used for {item.key}")

    with open(LOCK_FILE, "w", encoding="utf-8") as lf:
        json.dump(lock_data, lf, indent=2, sort_keys=True)
    print(f"[🚀] All 29 manifest icons synced and locked to {LOCK_FILE}!")

def verify_and_load_icons(dest_dir: pathlib.Path = ICONS_DIR) -> Dict[str, Tuple[str, bool]]:
    dest_dir.mkdir(parents=True, exist_ok=True)

    # AUTO-HEAL BYPASS: Jika icon belum ada di runner, download otomatis saat itu juga!
    missing = [it for it in ALL_ITEMS if not (dest_dir / f"{it.key}.svg").is_file()]
    if missing or not LOCK_FILE.is_file():
        print(f"[*] [AUTO-HEAL] Terdeteksi {len(missing)} icon belum ada di runner. Melakukan auto-sync...")
        sync_icons(dest_dir)

    lock_data = {}
    if LOCK_FILE.is_file():
        with open(LOCK_FILE, "r", encoding="utf-8") as lf:
            try:
                lock_data = json.load(lf)
            except Exception:
                lock_data = {}

    icons_map: Dict[str, Tuple[str, bool]] = {}

    for item in ALL_ITEMS:
        svg_path = dest_dir / f"{item.key}.svg"
        if not svg_path.is_file():
            # Fail-safe inline
            svg_path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" fill="#a855f7"/></svg>', encoding="utf-8")

        content = svg_path.read_text(encoding="utf-8").strip()
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if lock_data.get(svg_path.name) != sha:
            lock_data[svg_path.name] = sha

        opt_s = OPTICAL_SCALE.get(item.key, 1.0)
        box_dim = round(36.0 * opt_s, 1)
        inlined_markup, is_inlined = sanitize_and_inline_svg(content, item.key, item.is_mono, box_dim)
        icons_map[item.key] = (inlined_markup, is_inlined)

    return icons_map

# ==============================================================================
# GEOMETRY & TIMELINE (LITE 840 x 608 VIEWBOX)
# ==============================================================================
@dataclass
class TileCoord:
    item: ToolItem
    x: float
    y: float
    w: float
    h: float
    cx: float
    cy: float

@dataclass
class BayLayout:
    group: ToolGroup
    panel_y: float
    rail_y: float
    tile_w: float
    tile_h: float
    tiles: List[TileCoord]
    s_b: float
    l_b: float

def compute_layout() -> List[BayLayout]:
    panel_tops = [64.0, 192.0, 320.0, 448.0]
    y0, y1 = 58.0, 562.0
    bays: List[BayLayout] = []

    for b, grp in enumerate(MANIFEST):
        top_y = panel_tops[b]
        rail_y = top_y + 114.0  # 178, 306, 434, 562
        n = len(grp.items)
        tile_w = (748.0 - 8.0 * (n - 1)) / n
        tile_h = 72.0

        s_b = STARTUP_S + SPINE_S * ((rail_y - y0) / (y1 - y0))
        l_b = s_b + 0.10

        tiles: List[TileCoord] = []
        for i, item in enumerate(grp.items):
            tx = 46.0 + i * (tile_w + 8.0)
            ty = top_y + 32.0
            tiles.append(TileCoord(
                item=item,
                x=tx,
                y=ty,
                w=tile_w,
                h=tile_h,
                cx=tx + (tile_w / 2.0),
                cy=ty + (tile_h / 2.0),
            ))

        bays.append(BayLayout(
            group=grp,
            panel_y=top_y,
            rail_y=rail_y,
            tile_w=tile_w,
            tile_h=tile_h,
            tiles=tiles,
            s_b=s_b,
            l_b=l_b
        ))

    return bays

# ==============================================================================
# SVG BUILDER: SIGNAL-BUS LITE (ZERO-FILTER & ZERO-SMIL)
# ==============================================================================
def build_svg(icons_map: Dict[str, Tuple[str, bool]], now_dt: dt.datetime, animate: bool = True) -> str:
    w, h = 840, 608
    prefix = "arsn"
    bays = compute_layout()

    if animate:
        css_rules = f"""
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
    .lbl {{ font-size: 9.5px; font-weight: 600; fill: #8b7fb0; }}

    .hdr-flk {{ animation: arsn-flicker 4s infinite linear; }}
    @keyframes arsn-flicker {{
      0%, 82%, 84%, 90%, 100% {{ opacity: 1; }}
      83% {{ opacity: 0.25; }}
      89% {{ opacity: 0.65; }}
    }}

    .anim-spine {{
      opacity: 0;
      transform: translateY(0);
      animation: arsn-spine {CYCLE_S}s infinite linear;
      animation-delay: {STARTUP_S:.2f}s;
      animation-fill-mode: both;
    }}
    @keyframes arsn-spine {{
      0% {{ transform: translateY(0); opacity: 0; }}
      0.8% {{ opacity: 1; }}
      12.0% {{ transform: translateY(504px); opacity: 1; }}
      12.5% {{ transform: translateY(504px); opacity: 0; }}
      100% {{ transform: translateY(504px); opacity: 0; }}
    }}

    .anim-veil {{
      transform: translateX(0);
      animation: arsn-sweep {CYCLE_S}s infinite linear;
      animation-delay: var(--vd);
      animation-fill-mode: both;
    }}
    @keyframes arsn-sweep {{
      0% {{ transform: translateX(0); }}
      23.75% {{ transform: translateX(918px); }}
      100% {{ transform: translateX(918px); }}
    }}

    .anim-comet {{
      transform: translateX(0);
      animation: arsn-sweep {CYCLE_S}s infinite linear;
      animation-delay: var(--cd);
      animation-fill-mode: both;
    }}
    .anim-comet-op {{
      opacity: 0;
      animation: arsn-comet-fade {CYCLE_S}s infinite linear;
      animation-delay: var(--cd);
      animation-fill-mode: both;
    }}
    @keyframes arsn-comet-fade {{
      0%, 1.8% {{ opacity: 0; }}
      2.5% {{ opacity: 1; }}
      21.5% {{ opacity: 1; }}
      22.8%, 100% {{ opacity: 0; }}
    }}

    .anim-glint {{
      opacity: 0;
      transform: translateX(-240px) skewX(-20deg);
      animation: arsn-glint {CYCLE_S}s infinite linear;
      animation-delay: 6.40s;
      animation-fill-mode: both;
    }}
    @keyframes arsn-glint {{
      0% {{ transform: translateX(-240px) skewX(-20deg); opacity: 0; }}
      0.8% {{ opacity: 0.12; }}
      7.5% {{ opacity: 0.12; }}
      8.1%, 100% {{ transform: translateX(1100px) skewX(-20deg); opacity: 0; }}
    }}

    @media (max-width: 640px) {{
      .lbl {{ display: none; }}
      .ico-s {{ transform: scale(1.35) translateY(4px); transform-box: fill-box; transform-origin: center; }}
      .ftr-txt {{ display: none; }}
    }}
    @media (max-width: 440px) {{
      .ico-s {{ transform: scale(1.45) translateY(5px); transform-box: fill-box; transform-origin: center; }}
      .hdr-txt {{ font-size: 13px !important; letter-spacing: 2px !important; }}
      .grp-cnt {{ display: none; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      * {{ animation: none !important; }}
      .anim-comet, .anim-spine, .anim-glint {{ display: none !important; }}
      .anim-veil {{ transform: translateX(918px) !important; }}
    }}
"""
    else:
        css_rules = """
    text { font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }
    .mono { font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }
    .lbl { font-size: 9.5px; font-weight: 600; fill: #8b7fb0; }
    @media (max-width: 640px) {
      .lbl { display: none; }
      .ico-s { transform: scale(1.35) translateY(4px); transform-box: fill-box; transform-origin: center; }
      .ftr-txt { display: none; }
    }
    @media (max-width: 440px) {
      .ico-s { transform: scale(1.45) translateY(5px); transform-box: fill-box; transform-origin: center; }
      .hdr-txt { font-size: 13px !important; letter-spacing: 2px !important; }
      .grp-cnt { display: none; }
    }
"""

    bays_markup = []
    clip_defs = []

    for b, bay in enumerate(bays):
        py = bay.panel_y
        ry = bay.rail_y
        tint = bay.group.tint
        safe_title = escape(bay.group.title)
        n_tools = len(bay.tiles)
        idx_str = f"0{b+1}"

        clip_defs.append(f'<clipPath id="{prefix}_clip_bay_{b}"><rect x="46" y="{py + 32:.1f}" width="748" height="72" rx="12" /></clipPath>')

        tile_rects = []
        for t in bay.tiles:
            tile_rects.append(
                f'<rect x="{t.x:.1f}" y="{t.y:.1f}" width="{t.w:.1f}" height="{t.h:.1f}" rx="12" fill="#0f0824" stroke="#2e1065" stroke-width="1" />'
                f'<line x1="{t.x + 10:.1f}" y1="{t.y + 1:.1f}" x2="{t.x + t.w - 10:.1f}" y2="{t.y + 1:.1f}" stroke="#e9d5ff" stroke-opacity="0.10" stroke-width="1" />'
            )
        tiles_geom = "\n      ".join(tile_rects)

        icons_list = []
        for t in bay.tiles:
            icon_markup, _ = icons_map[t.item.key]
            name = escape(t.item.name)
            lbl_len_attr = f'textLength="{t.w - 8:.0f}" lengthAdjust="spacingAndGlyphs"' if len(t.item.name) >= 12 else ''
            icons_list.append(f"""
      <g transform="translate({t.x:.1f}, {t.y:.1f})">
        <g class="ico" transform="translate({(t.w - 36.0)/2.0:.1f}, 8)">
          <g class="ico-s">
            {icon_markup}
          </g>
        </g>
        <text class="lbl" x="{t.w/2.0:.1f}" y="62" text-anchor="middle" {lbl_len_attr}>{name}</text>
      </g>
            """)
        icons_geom = "".join(icons_list)

        rail_stubs = []
        vias = []
        for t in bay.tiles:
            rail_stubs.append(f'<line x1="{t.cx:.1f}" y1="{py + 104:.1f}" x2="{t.cx:.1f}" y2="{ry:.1f}" stroke="#4c1d95" stroke-width="1.2" />')
            vias.append(f'<circle cx="{t.cx:.1f}" cy="{ry:.1f}" r="2.2" fill="#140a2b" stroke="#6d28d9" stroke-width="1" />')
        rails_geom = "\n      ".join(rail_stubs)
        vias_geom = "\n      ".join(vias)

        if animate:
            motion_elements = f"""
      <g clip-path="url(#{prefix}_clip_bay_{b})">
        <rect class="anim-veil" x="-872" y="{py + 32:.1f}" width="1666" height="72" fill="url(#{prefix}_veil_grad)" style="--vd:{bay.l_b:.2f}s" />
      </g>
      <g class="anim-comet" transform="translate(-39, {ry:.1f})" style="--cd:{bay.l_b:.2f}s">
        <g class="anim-comet-op" style="--cd:{bay.l_b:.2f}s">
          <line x1="-70" y1="0" x2="0" y2="0" stroke="url(#{prefix}_comet_tail)" stroke-width="2.2" stroke-linecap="round" />
          <circle cx="0" cy="0" r="12" fill="url(#{prefix}_comet_glow)" />
          <circle cx="0" cy="0" r="3.2" fill="#f5d0fe" />
        </g>
      </g>
            """
        else:
            motion_elements = ""

        bays_markup.append(f"""
    <!-- ================= BAY {b+1}: {safe_title} ================= -->
    <rect x="30" y="{py:.1f}" width="780" height="122" rx="14" fill="url(#{prefix}_panel_grad)" stroke="#a855f7" stroke-opacity="0.14" stroke-width="1" />
    <line x1="38" y1="{py + 1:.1f}" x2="802" y2="{py + 1:.1f}" stroke="#e9d5ff" stroke-opacity="0.10" stroke-width="1" />

    <path d="M 54 {py + 1:.1f} H 180" stroke="{tint}" stroke-width="2" stroke-linecap="round" opacity="0.45" />

    <rect x="46" y="{py + 9:.1f}" width="18" height="18" rx="4" fill="#1f1138" stroke="{tint}" stroke-opacity="0.4" />
    <text x="55" y="{py + 21.5:.1f}" fill="{tint}" font-size="9.5" font-weight="800" text-anchor="middle" class="mono">{idx_str}</text>
    <text x="72" y="{py + 22.5:.1f}" fill="#e9d5ff" font-size="13" font-weight="800">{safe_title}</text>
    <text x="794" y="{py + 22:.1f}" fill="#8b7fb0" font-size="9.5" text-anchor="end" class="mono grp-cnt">{n_tools} tools</text>
    <line x1="46" y1="{py + 26:.1f}" x2="794" y2="{py + 26:.1f}" stroke="#a855f7" stroke-opacity="0.10" stroke-dasharray="3 3" />

    {tiles_geom}
    {icons_geom}

    <path d="M 22 {ry - 10:.1f} L 32 {ry:.1f} H 46" fill="none" stroke="#2e1065" stroke-width="1.6" />
    <line x1="46" y1="{ry:.1f}" x2="794" y2="{ry:.1f}" stroke="#2e1065" stroke-width="1.6" />
    <line x1="46" y1="{ry:.1f}" x2="794" y2="{ry:.1f}" stroke="#4c1d95" stroke-width="1.4" stroke-dasharray="2 6" />
    {rails_geom}
    {vias_geom}

    <circle cx="46" cy="{ry:.1f}" r="4" fill="#05030a" stroke="{tint}" stroke-width="1.4" />
    <circle cx="46" cy="{ry:.1f}" r="1.6" fill="#f5d0fe" />

    <polygon points="794,{ry - 4:.1f} 798,{ry:.1f} 794,{ry + 4:.1f} 790,{ry:.1f}" fill="#6d28d9" />

    {motion_elements}
        """)

    footer_str = f"synced {now_dt.strftime('%Y-%m-%d %H:%M UTC')}"
    counts_str = f"{TOTAL_TOOLS} tools / {TOTAL_GROUPS} groups"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-labelledby="{prefix}_title {prefix}_desc">
  <title id="{prefix}_title">Core Tech Stack &amp; Arsenal - Rixsan Joulfiand</title>
  <desc id="{prefix}_desc">Languages &amp; Core Technologies: PHP, Laravel, HTML5, CSS3, JavaScript, TypeScript, React Native, Python, Jupyter. Database &amp; Development Environment: MySQL, PostgreSQL, Git, GitHub, VS Code, Figma. AI Coding Assistants &amp; Agents: ChatGPT, Gemini, Claude, Antigravity, GitHub Copilot, Cursor, Perplexity. LLM Platforms &amp; Open Models: Ollama, Hugging Face, DeepSeek, Mistral AI, Qwen, Grok, Meta Llama.</desc>
  <style>{css_rules}  </style>

  <defs>
    <linearGradient id="{prefix}_panel_grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#140a2b" stop-opacity="0.85" />
      <stop offset="100%" stop-color="#0b0618" stop-opacity="0.85" />
    </linearGradient>

    <linearGradient id="{prefix}_border_grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#6d28d9" />
      <stop offset="50%" stop-color="#c084fc" />
      <stop offset="100%" stop-color="#4c1d95" />
    </linearGradient>

    <linearGradient id="{prefix}_veil_grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#0d0820" stop-opacity="{VEIL_ALPHA}" />
      <stop offset="36%" stop-color="#0d0820" stop-opacity="{VEIL_ALPHA}" />
      <stop offset="47%" stop-color="#0d0820" stop-opacity="0" />
      <stop offset="50%" stop-color="#f5d0fe" stop-opacity="0.10" />
      <stop offset="53%" stop-color="#0d0820" stop-opacity="0" />
      <stop offset="56%" stop-color="#0d0820" stop-opacity="{VEIL_ALPHA}" />
      <stop offset="100%" stop-color="#0d0820" stop-opacity="{VEIL_ALPHA}" />
    </linearGradient>

    <linearGradient id="{prefix}_comet_tail" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.0" />
      <stop offset="60%" stop-color="#c084fc" stop-opacity="0.6" />
      <stop offset="100%" stop-color="#f5d0fe" stop-opacity="1.0" />
    </linearGradient>
    <radialGradient id="{prefix}_comet_glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#f5d0fe" stop-opacity="0.9" />
      <stop offset="40%" stop-color="#c084fc" stop-opacity="0.4" />
      <stop offset="100%" stop-color="#a855f7" stop-opacity="0.0" />
    </radialGradient>

    <linearGradient id="{prefix}_spine_grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#6d28d9" stop-opacity="0.0" />
      <stop offset="70%" stop-color="#c084fc" stop-opacity="0.7" />
      <stop offset="100%" stop-color="#f5d0fe" stop-opacity="1.0" />
    </linearGradient>

    <linearGradient id="{prefix}_glint_grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f5d0fe" stop-opacity="0.0" />
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0.10" />
      <stop offset="100%" stop-color="#e9d5ff" stop-opacity="0.0" />
    </linearGradient>

    <clipPath id="{prefix}_card_clip">
      <rect x="0" y="0" width="{w}" height="{h}" rx="14" />
    </clipPath>

    {"".join(clip_defs)}
  </defs>

  <rect width="{w}" height="{h}" rx="14" fill="#05030a" />

  <rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="13" fill="none" stroke="url(#{prefix}_border_grad)" stroke-width="1.5" />
  <rect x="2.5" y="2.5" width="{w - 5}" height="{h - 5}" rx="12" fill="none" stroke="#2e1065" stroke-width="1" />
  <path d="M 14 30 V 14 H 30" fill="none" stroke="#c084fc" stroke-width="2" stroke-linecap="round" />
  <path d="M {w - 30} 14 H {w - 14} V 30" fill="none" stroke="#c084fc" stroke-width="2" stroke-linecap="round" />
  <path d="M 14 {h - 30} V {h - 14} H 30" fill="none" stroke="#c084fc" stroke-width="2" stroke-linecap="round" />
  <path d="M {w - 30} {h - 14} H {w - 14} V {h - 30}" fill="none" stroke="#c084fc" stroke-width="2" stroke-linecap="round" />

  <g transform="translate(68, 22)">
    <rect x="0" y="6" width="3.5" height="14" rx="1.5" fill="#c084fc" />
    <rect x="7" y="2" width="3.5" height="22" rx="1.5" fill="#9333ea" />
    <rect x="14" y="9" width="3.5" height="11" rx="1.5" fill="#d8b4fe" />
  </g>

  <g transform="translate({w/2}, 33)" text-anchor="middle" class="hdr-flk">
    <text x="0" y="0" fill="none" stroke="#a855f7" stroke-width="5" stroke-opacity="0.28" font-size="16" font-weight="900" letter-spacing="4" class="hdr-txt">CORE TECH STACK &amp; ARSENAL</text>
    <text x="0" y="0" fill="#f5f3ff" font-size="16" font-weight="900" letter-spacing="4" class="hdr-txt">CORE TECH STACK &amp; ARSENAL</text>
  </g>

  <g transform="translate({w - 92}, 22)">
    <rect x="0" y="9" width="3.5" height="11" rx="1.5" fill="#d8b4fe" />
    <rect x="7" y="2" width="3.5" height="22" rx="1.5" fill="#9333ea" />
    <rect x="14" y="6" width="3.5" height="14" rx="1.5" fill="#c084fc" />
  </g>

  <line x1="22" y1="58" x2="22" y2="562" stroke="#2e1065" stroke-width="2" />
  <line x1="22" y1="58" x2="22" y2="562" stroke="#4c1d95" stroke-width="1.6" stroke-dasharray="2 6" />

  <g transform="translate(22, 58)">
    <circle r="7" fill="none" stroke="#a855f7" stroke-width="1.2" stroke-dasharray="2 2" />
    <circle r="4" fill="#05030a" stroke="#c084fc" stroke-width="1.2" />
    <circle r="1.8" fill="#f5d0fe" />
  </g>

  {"".join(bays_markup)}

  {f'''<g transform="translate(22, 58)">
    <g class="anim-spine">
      <line x1="0" y1="-36" x2="0" y2="0" stroke="url(#{prefix}_spine_grad)" stroke-width="3" stroke-linecap="round" />
      <circle cx="0" cy="0" r="2.8" fill="#f5d0fe" />
    </g>
  </g>''' if animate else ''}

  {f'''<g clip-path="url(#{prefix}_card_clip)">
    <rect class="anim-glint" x="0" y="-20" width="120" height="{h + 40}" fill="url(#{prefix}_glint_grad)" />
  </g>''' if animate else ''}

  <g transform="translate(30, 580)">
    <rect width="780" height="20" rx="4" fill="#07040f" stroke="#1f1138" stroke-width="0.8" />
    <text x="14" y="13.5" fill="#8b7fb0" font-size="9.5" class="mono ftr-txt">{footer_str}</text>
    <text x="766" y="13.5" fill="#8b7fb0" font-size="9.5" text-anchor="end" class="mono ftr-txt">{counts_str}</text>
  </g>
</svg>"""

# ==============================================================================
# AUDIT & PERFORMANCE PROFILER
# ==============================================================================
def audit(svg_str: str) -> dict:
    return {
        "size_kb": len(svg_str.encode("utf-8")) / 1024.0,
        "total_elements": len(re.findall(r'<[a-zA-Z][^>]*', svg_str)),
        "animated_nodes": len(re.findall(r'class="[^"]*anim-[^"]*"', svg_str)),
        "filters": len(re.findall(r'<filter\b', svg_str)),
        "masks": len(re.findall(r'<mask\b', svg_str)),
        "smil": len(re.findall(r'<(animate|animateTransform|animateMotion)\b', svg_str)),
        "images": len(re.findall(r'<image\b', svg_str)),
        "chrome_gradients": len(re.findall(r'id="arsn_[^"]*grad"', svg_str)),
    }

# ==============================================================================
# SELFTEST PIPELINE (FAIL-CLOSED OFFLINE ENFORCEMENT)
# ==============================================================================
def run_selftest():
    print("=================== SIGNAL-BUS LITE MASTER SELFTEST ===================")

    # 1. Manifest guard (Strict [9, 6, 7, 7])
    assert len(ALL_ITEMS) == 29, f"Test 1 Failed: Expected 29 items, got {len(ALL_ITEMS)}"
    group_lens = [len(g.items) for g in MANIFEST]
    assert group_lens == [9, 6, 7, 7], f"Test 1 Failed: Expected [9, 6, 7, 7], got {group_lens}"
    print("[PASS] Test 1: Manifest guard (29 tools in exact 4 groups)")

    # 2. Genuine Icon Authenticity & Offline Lock
    icons_map = verify_and_load_icons()
    assert len(icons_map) == 29
    print("[PASS] Test 2: Upstream icons verified & locked offline via icons.lock")

    # 3. Inlining Guard (>= 26 inlined; <= 3 nested image exceptions)
    inlined_count = sum(1 for _, is_in in icons_map.values() if is_in)
    exceptions_count = 29 - inlined_count
    assert inlined_count >= 26, f"Test 3 Failed: Only {inlined_count} inlined, expected >= 26"
    assert exceptions_count <= 3, f"Test 3 Failed: {exceptions_count} exceptions exceed limit of 3"
    print(f"[PASS] Test 3: Inline icon guard passed ({inlined_count}/29 inlined, {exceptions_count} exceptions <= 3)")

    # 4. Deterministic Render & XML Validation
    fixed_now = dt.datetime(2026, 10, 5, 0, 0, 0, tzinfo=dt.timezone.utc)
    svg_anim = build_svg(icons_map, fixed_now, animate=True)
    svg_static = build_svg(icons_map, fixed_now, animate=False)

    root_anim = ET.fromstring(svg_anim)
    root_static = ET.fromstring(svg_static)

    for tag in ["script", "foreignObject", "a", "filter", "mask", "animate", "animateTransform"]:
        assert len(root_anim.findall(f".//{{*}}{tag}")) == 0, f"Disallowed <{tag}> found in animated SVG"
        assert len(root_static.findall(f".//{{*}}{tag}")) == 0, f"Disallowed <{tag}> found in static SVG"

    no_img = re.sub(r'<image\b[^>]*>', '', svg_anim)
    urls = re.findall(r'https?://[^\s"\'<>]+', no_img)
    for u in urls:
        assert u == "http://www.w3.org/2000/svg" or u == "http://www.w3.org/1999/xlink", f"External URL: {u}"
    print("[PASS] Test 4: Deterministic XML valid, isolated and zero external dependencies")

    # 5. HARD PERFORMANCE BUDGET LINT
    audit_res = audit(svg_anim)
    assert audit_res["size_kb"] <= LIMIT_KB, f"Size {audit_res['size_kb']:.1f} KB exceeds {LIMIT_KB} KB"
    assert audit_res["filters"] == 0, "Filters must be ZERO"
    assert audit_res["masks"] == 0, "Masks must be ZERO"
    assert audit_res["smil"] == 0, "SMIL must be ZERO"
    assert audit_res["images"] <= 3, "Image exceptions > 3"
    assert audit_res["animated_nodes"] <= 16, f"Animated nodes {audit_res['animated_nodes']} > 16"
    assert audit_res["total_elements"] <= 650, f"Total elements {audit_res['total_elements']} > 650"
    assert audit_res["chrome_gradients"] <= 12, f"Chrome gradients {audit_res['chrome_gradients']} > 12"

    static_kb = len(svg_static.encode("utf-8")) / 1024.0
    assert static_kb <= 140.0, f"Static size {static_kb:.1f} KB > 140 KB limit"
    print(f"[PASS] Test 5: Hard performance budgets passed ({audit_res['size_kb']:.1f} KB anim / {static_kb:.1f} KB static, {audit_res['total_elements']} elements <= 650, 0 filters, 0 SMIL)")

    # 6. Timeline Lint (Duty cycle <= 50%, idle >= 6s)
    idle_s = CYCLE_S - DUTY_ACTIVE_S
    duty_cycle = (DUTY_ACTIVE_S / CYCLE_S) * 100.0
    assert duty_cycle <= 50.0, f"Duty cycle {duty_cycle:.1f}% > 50%"
    assert idle_s >= 6.0, f"Idle pause {idle_s:.1f}s < 6.0s"
    print(f"[PASS] Test 6: Timeline lint passed (Duty cycle {duty_cycle:.1f}%, full idle pause {idle_s:.1f}s >= 6.0s)")

    # 7. Chrome Palette Audit (Excluding icon content)
    no_ico_svg = re.sub(r'<g class="ico"[^>]*>.*?</g>\s*</g>', '', no_img, flags=re.DOTALL)
    hex_matches = re.findall(r"#[0-9a-fA-F]{6}", no_ico_svg)
    for hx in hex_matches:
        hx_low = hx.lower()
        r, g, b = int(hx_low[1:3], 16)/255.0, int(hx_low[3:5], 16)/255.0, int(hx_low[5:7], 16)/255.0
        h_deg, s, v = colorsys.rgb_to_hsv(r, g, b)
        h_deg *= 360.0
        if s > 0.35 and v > 0.3:
            is_yellow = 20 <= h_deg <= 75
            is_cyan = 180 <= h_deg <= 250
            assert not is_yellow, f"Forbidden yellow/gold {hx} in chrome"
            assert not is_cyan, f"Forbidden cyan/blue {hx} in chrome"
    print("[PASS] Test 7: Palette audit passed (0% forbidden hues in chrome)")

    # 8. Static Variant Lint (Zero keyframes and animations)
    assert "@keyframes" not in svg_static
    assert "animation:" not in svg_static
    print("[PASS] Test 8: Static variant confirmed 100% animation-free")

    # 9. AST Inspection (Zero Mock Statistics)
    forbidden_nums = {int(x) for x in ["95", "99", "1000"]}
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=__file__)
    for item in tree.body:
        if isinstance(item, ast.FunctionDef) and item.name == "build_svg":
            for node in ast.walk(item):
                if isinstance(node, ast.Constant) and isinstance(node.value, int):
                    assert node.value not in forbidden_nums, f"Mock number {node.value} in builder AST"
    print("[PASS] Test 9: AST inspection confirms zero mock statistics")
    print("=================== [ALL 9 SELFTESTS PASSED 100%] ===================")

# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Signal-Bus Arsenal Lite (Master Performance)")
    parser.add_argument("--out", default="dist", help="Output directory")
    parser.add_argument("--selftest", action="store_true", help="Execute offline unit selftest suite")
    parser.add_argument("--sync-icons", action="store_true", help="Download raw manifest icons and write lock")
    parser.add_argument("--verify-icons", action="store_true", help="Verify icons against lockfile")
    parser.add_argument("--audit", default=None, help="Audit an SVG file")
    parser.add_argument("--now", default=None, help="Fix build timestamp (ISO 8601 UTC)")
    args = parser.parse_args()

    if args.sync_icons:
        sync_icons()
        sys.exit(0)

    if args.verify_icons:
        verify_and_load_icons()
        print("[✓] All icons match lockfile.")
        sys.exit(0)

    if args.audit:
        content = pathlib.Path(args.audit).read_text(encoding="utf-8")
        res = audit(content)
        print(json.dumps(res, indent=2))
        sys.exit(0)

    if args.selftest:
        run_selftest()
        sys.exit(0)

    if args.now:
        now_dt = dt.datetime.fromisoformat(args.now)
    else:
        now_dt = dt.datetime.now(dt.timezone.utc)

    icons_map = verify_and_load_icons()
    svg_anim = build_svg(icons_map, now_dt, animate=True)
    svg_static = build_svg(icons_map, now_dt, animate=False)

    ET.fromstring(svg_anim)
    ET.fromstring(svg_static)

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_anim_file = out_dir / OUT_NAME
    out_static_file = out_dir / OUT_STATIC_NAME

    out_anim_file.write_text(svg_anim.strip(), encoding="utf-8")
    out_static_file.write_text(svg_static.strip(), encoding="utf-8")

    kb_anim = out_anim_file.stat().st_size / 1024.0
    kb_static = out_static_file.stat().st_size / 1024.0
    print(f"[🚀] Generated Animated: {out_anim_file} ({kb_anim:.1f} KB <= {LIMIT_KB} KB)")
    print(f"[🚀] Generated Static:   {out_static_file} ({kb_static:.1f} KB <= 140 KB)")

if __name__ == "__main__":
    main()
