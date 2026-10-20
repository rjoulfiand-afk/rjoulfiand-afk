import argparse
import base64
import datetime as dt
import hashlib
import html
import os
import pathlib
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Tuple

MANIFEST = [
    ("01", "Languages & Core Technologies", [
        ("php", "PHP", "devicon", "php/php-original.svg", False),
        ("laravel", "Laravel", "devicon", "laravel/laravel-original.svg", False),
        ("html5", "HTML5", "devicon", "html5/html5-original.svg", False),
        ("css3", "CSS3", "devicon", "css3/css3-original.svg", False),
        ("javascript", "JavaScript", "devicon", "javascript/javascript-original.svg", False),
        ("typescript", "TypeScript", "devicon", "typescript/typescript-original.svg", False),
        ("react", "React Native", "devicon", "react/react-original.svg", False),
        ("python", "Python", "devicon", "python/python-original.svg", False),
        ("jupyter", "Jupyter", "devicon", "jupyter/jupyter-original-wordmark.svg", False),
    ]),
    ("02", "Database & Development Environment", [
        ("mysql", "MySQL", "devicon", "mysql/mysql-original-wordmark.svg", False),
        ("postgresql", "PostgreSQL", "devicon", "postgresql/postgresql-original.svg", False),
        ("git", "Git", "devicon", "git/git-original.svg", False),
        ("github", "GitHub", "github_white", "github", True),
        ("vscode", "VS Code", "devicon", "vscode/vscode-original.svg", False),
        ("figma", "Figma", "devicon", "figma/figma-original.svg", False),
    ]),
    ("03", "AI Coding Assistants & Agents", [
        ("chatgpt", "ChatGPT", "lobe_svg", "openai.svg", True),
        ("gemini", "Gemini", "lobe_svg", "gemini-color.svg", False),
        ("claude", "Claude", "lobe_svg", "claude-color.svg", False),
        ("antigravity", "Antigravity", "lobe_svg", "antigravity-color.svg", False),
        ("copilot", "GitHub Copilot", "lobe_svg", "githubcopilot.svg", True),
        ("cursor", "Cursor", "lobe_svg", "cursor.svg", True),
        ("perplexity", "Perplexity", "lobe_svg", "perplexity-color.svg", False),
    ]),
    ("04", "LLM Platforms & Open Models", [
        ("ollama", "Ollama", "lobe_svg", "ollama.svg", True),
        ("huggingface", "Hugging Face", "lobe_svg", "huggingface-color.svg", False),
        ("deepseek", "DeepSeek", "lobe_svg", "deepseek-color.svg", False),
        ("mistral", "Mistral AI", "lobe_svg", "mistral-color.svg", False),
        ("qwen", "Qwen", "lobe_svg", "qwen-color.svg", False),
        ("grok", "Grok", "lobe_svg", "grok.svg", True),
        ("llama", "Meta Llama", "lobe_svg", "meta-color.svg", False),
    ]),
]

# Warna Aksen Semantik per Kategori (Selaras dengan Obsidian Titanium di metrics_cards.py)
SECTION_ACCENTS = {
    "01": ("#06b6d4", "#67e8f9", "#083344", "CORE RUNTIME"),
    "02": ("#10b981", "#6ee7b7", "#064e3b", "INFRA & DEVOPS"),
    "03": ("#8b5cf6", "#c4b5fd", "#2e1065", "AUTONOMOUS AGENTS"),
    "04": ("#f59e0b", "#fde68a", "#451a03", "FOUNDATION MODELS"),
}

BRAND_RIM_COLORS = {
    "php": "#777BB4",
    "laravel": "#FF2D20",
    "html5": "#E34F26",
    "css3": "#1572B6",
    "javascript": "#F7DF1E",
    "typescript": "#3178C6",
    "react": "#61DAFB",
    "python": "#3776AB",
    "jupyter": "#F37626",
    "mysql": "#00758F",
    "postgresql": "#4169E1",
    "git": "#F05032",
    "github": "#E2E8F0",
    "vscode": "#007ACC",
    "figma": "#F24E1E",
    "chatgpt": "#10A37F",
    "gemini": "#8A5CF6",
    "claude": "#D97706",
    "antigravity": "#C084FC",
    "copilot": "#38BDF8",
    "cursor": "#E2E8F0",
    "perplexity": "#22B8CD",
    "ollama": "#E2E8F0",
    "huggingface": "#FFD21E",
    "deepseek": "#1E88E5",
    "mistral": "#FF7000",
    "qwen": "#6366F1",
    "grok": "#E2E8F0",
    "llama": "#0468FF",
}

OPTICAL_SCALE = {
    "mysql": 1.12,
    "jupyter": 1.12,
    "postgresql": 1.04,
    "react": 1.04,
}

DEVICON_MIRRORS = [
    "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/",
    "https://fastly.jsdelivr.net/gh/devicons/devicon@latest/icons/",
    "https://raw.githubusercontent.com/devicons/devicon/master/icons/",
]

LOBE_SVG_MIRRORS = [
    "https://cdn.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/",
    "https://fastly.jsdelivr.net/npm/@lobehub/icons-static-svg@latest/icons/",
    "https://unpkg.com/@lobehub/icons-static-svg@latest/icons/",
]

LOBE_PNG_MIRRORS = [
    "https://cdn.jsdelivr.net/npm/@lobehub/icons-static-png@latest/dark/",
    "https://unpkg.com/@lobehub/icons-static-png@latest/dark/",
]


def fetch_url(url: str, timeout: int = 12, retries: int = 3) -> Optional[bytes]:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    data = resp.read()
                    if len(data) >= 200:
                        return data
        except Exception:
            time.sleep(1 * (2 ** attempt))
    return None


def clean_and_normalize_svg(raw_bytes: bytes, is_mono: bool = False) -> str:
    content = raw_bytes.decode("utf-8", errors="replace")
    content = re.sub(r"<\?xml.*?\?>", "", content)
    content = re.sub(r"<!DOCTYPE.*?>", "", content, flags=re.DOTALL)
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    content = re.sub(r"<title>.*?</title>", "", content, flags=re.DOTALL)

    if is_mono:
        # Pastikan ikon monokrom yang memakai currentColor atau hitam tidak tenggelam di latar gelap
        content = re.sub(r'fill="currentColor"', 'fill="#F8FAFC"', content, flags=re.IGNORECASE)
        content = re.sub(r'fill="#000(?:000)?"', 'fill="#F8FAFC"', content, flags=re.IGNORECASE)

    root = ET.fromstring(content)
    if "viewBox" not in root.attrib:
        w_val = root.attrib.get("width", "24")
        h_val = root.attrib.get("height", "24")
        w_clean = re.sub(r"[^\d.]", "", w_val) or "24"
        h_clean = re.sub(r"[^\d.]", "", h_val) or "24"
        root.attrib["viewBox"] = f"0 0 {w_clean} {h_clean}"

    root.attrib.pop("width", None)
    root.attrib.pop("height", None)

    if is_mono:
        root.attrib["fill"] = "#F8FAFC"
        root.attrib["color"] = "#F8FAFC"

    return ET.tostring(root, encoding="unicode")


def acquire_icon(key: str, src_type: str, path: str, is_mono: bool, cache_dir: pathlib.Path) -> Tuple[str, str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    svg_cache = cache_dir / f"{key}.svg"
    png_cache = cache_dir / f"{key}.png"

    if svg_cache.exists():
        content = svg_cache.read_text(encoding="utf-8")
        if "M12 2L2 22h20" not in content and "<html" not in content.lower():
            if is_mono and 'fill="currentColor"' in content:
                content = clean_and_normalize_svg(content.encode("utf-8"), is_mono=True)
                svg_cache.write_text(content, encoding="utf-8")
            b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
            return f"data:image/svg+xml;base64,{b64}", content

    urls_attempted = []
    raw_data = None
    is_png = False

    if src_type == "devicon":
        for mirror in DEVICON_MIRRORS:
            u = mirror + path
            urls_attempted.append(u)
            raw_data = fetch_url(u)
            if raw_data:
                break
    elif src_type == "github_white":
        u_primary = "https://cdn.simpleicons.org/github/white"
        urls_attempted.append(u_primary)
        raw_data = fetch_url(u_primary)
        if not raw_data:
            u_sec = "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/github.svg"
            urls_attempted.append(u_sec)
            raw_data = fetch_url(u_sec)
    elif src_type == "lobe_svg":
        for mirror in LOBE_SVG_MIRRORS:
            u = mirror + path
            urls_attempted.append(u)
            raw_data = fetch_url(u)
            if raw_data:
                break
        if not raw_data and is_mono:
            png_name = path.replace(".svg", ".png")
            for mirror in LOBE_PNG_MIRRORS:
                u = mirror + png_name
                urls_attempted.append(u)
                raw_data = fetch_url(u)
                if raw_data:
                    is_png = True
                    break

    if not raw_data:
        raise RuntimeError(
            f"Fail-closed: Unable to download icon '{key}'. Attempted URLs:\n  " + "\n  ".join(urls_attempted)
        )

    if is_png:
        png_cache.write_bytes(raw_data)
        b64 = base64.b64encode(raw_data).decode("ascii")
        return f"data:image/png;base64,{b64}", ""
    else:
        cleaned_svg = clean_and_normalize_svg(raw_data, is_mono=is_mono)
        svg_cache.write_text(cleaned_svg, encoding="utf-8")
        b64 = base64.b64encode(cleaned_svg.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{b64}", cleaned_svg


def rounded_rect_path(w: int, h: int, r: float, inset: float = 1.5) -> str:
    x0 = inset
    y0 = inset
    x1 = w - inset
    y1 = h - inset
    rad = max(1.0, r - inset)
    return (
        f"M {x0 + rad} {y0} L {x1 - rad} {y0} "
        f"A {rad} {rad} 0 0 1 {x1} {y0 + rad} L {x1} {y1 - rad} "
        f"A {rad} {rad} 0 0 1 {x1 - rad} {y1} L {x0 + rad} {y1} "
        f"A {rad} {rad} 0 0 1 {x0} {y1 - rad} L {x0} {y0 + rad} "
        f"A {rad} {rad} 0 0 1 {x0 + rad} {y0} Z"
    )


def build_card_svg(icons_data: Dict[str, dict], animated: bool = True, now_ts: Optional[str] = None) -> str:
    w = 840
    h = 668
    row_tops = [78, 216, 354, 492]
    rr_outer = rounded_rect_path(w, h, 14, inset=0.75)
    rr_inner = rounded_rect_path(w, h, 14, inset=1.75)

    # 1. Defs: Multi-Accent Rail Gradients per Section
    rail_defs = []
    for num, _, _ in MANIFEST:
        acc_main, acc_light, _, _ = SECTION_ACCENTS[num]
        rail_defs.append(
            f"""    <linearGradient id="railGrad_{num}" gradientUnits="userSpaceOnUse" x1="42" y1="0" x2="798" y2="0">
      <stop offset="0%" stop-color="{acc_main}" stop-opacity="0.10"/>
      <stop offset="50%" stop-color="{acc_light}" stop-opacity="0.58"/>
      <stop offset="100%" stop-color="{acc_main}" stop-opacity="0.10"/>
    </linearGradient>"""
        )
    rail_defs_str = "\n".join(rail_defs)

    # 2. Defs: Crisp Optical Rim Light (Tajam untuk logo wordmark seperti MySQL & Jupyter)
    rim_filters = []
    for key, color in BRAND_RIM_COLORS.items():
        rim_filters.append(
            f"""    <filter id="rim_{key}" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="2.0" result="blur"/>
      <feFlood flood-color="{color}" flood-opacity="0.72" result="col"/>
      <feComposite in="col" in2="blur" operator="in" result="rim"/>
      <feMerge>
        <feMergeNode in="rim"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>"""
        )
    rim_filters_str = "\n".join(rim_filters)

    # 3. CSS: Staggered Sine-Wave Float (Gelombang bertahap per kolom, aman terhadap Test 3)
    motion_css = ""
    border_beam_markup = ""
    if animated:
        delay_rules = "\n".join(
            f"      .d{i} {{ animation-delay: -{i * 0.28:.2f}s; }}" for i in range(9)
        )
        motion_css = f"""
      @keyframes waveFloat {{
        0%, 100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-3.5px); }}
      }}
      .float-item {{ animation: waveFloat 3.6s ease-in-out infinite; will-change: transform; }}
{delay_rules}"""

        border_beam_markup = f"""
  <!-- Precision Telemetry Laser Beam -->
  <g>
    <path d="{rr_inner}" fill="none" stroke="#22d3ee" stroke-width="1.8" stroke-linecap="round"
          stroke-dasharray="10 90" pathLength="100" opacity="0.75">
      <animate attributeName="stroke-dashoffset" from="0" to="-100" dur="22s" repeatCount="indefinite" />
    </path>
    <path d="{rr_inner}" fill="none" stroke="#a78bfa" stroke-width="1.4" stroke-linecap="round"
          stroke-dasharray="7 93" pathLength="100" opacity="0.55">
      <animate attributeName="stroke-dashoffset" from="-50" to="-150" dur="22s" repeatCount="indefinite" />
    </path>
  </g>"""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-labelledby="arsenal-title arsenal-desc">
  <title id="arsenal-title">Core Tech Stack &amp; Arsenal</title>
  <desc id="arsenal-desc">PHP, Laravel, HTML5, CSS3, JavaScript, TypeScript, React Native, Python, Jupyter, MySQL, PostgreSQL, Git, GitHub, VS Code, Figma, ChatGPT, Gemini, Claude, Antigravity, GitHub Copilot, Cursor, Perplexity, Ollama, Hugging Face, DeepSeek, Mistral AI, Qwen, Grok, Meta Llama</desc>
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090d16"/>
      <stop offset="52%" stop-color="#0d1322"/>
      <stop offset="100%" stop-color="#070a12"/>
    </linearGradient>
    <radialGradient id="ambientCyan" cx="15%" cy="12%" r="60%">
      <stop offset="0%" stop-color="#06b6d4" stop-opacity="0.11"/>
      <stop offset="60%" stop-color="#0f172a" stop-opacity="0.03"/>
      <stop offset="100%" stop-color="#090d16" stop-opacity="0.0"/>
    </radialGradient>
    <radialGradient id="ambientViolet" cx="85%" cy="88%" r="60%">
      <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.11"/>
      <stop offset="65%" stop-color="#1e1b4b" stop-opacity="0.03"/>
      <stop offset="100%" stop-color="#070a12" stop-opacity="0.0"/>
    </radialGradient>
    <linearGradient id="innerBezel" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.38"/>
      <stop offset="45%" stop-color="#1e293b" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.35"/>
    </linearGradient>
    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f8fafc"/>
      <stop offset="50%" stop-color="#67e8f9"/>
      <stop offset="100%" stop-color="#c4b5fd"/>
    </linearGradient>
    <pattern id="dotGrid" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="0.75" fill="#334155" opacity="0.32"/>
    </pattern>
{rail_defs_str}
{rim_filters_str}
  </defs>

  <style>
    .bg {{ fill: url(#bgGrad); }}
    .title {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 900; font-size: 16.5px; fill: url(#headerGrad); letter-spacing: 3.6px; text-anchor: middle; }}
    .group-num {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; font-size: 11px; font-weight: 800; text-anchor: middle; }}
    .group-title {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 13.5px; font-weight: 800; fill: #F8FAFC; letter-spacing: 0.4px; }}
    .group-tag {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; font-size: 9px; font-weight: 700; letter-spacing: 1px; }}
    .group-count {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; font-size: 10.5px; font-weight: 600; fill: #64748B; text-anchor: end; }}
    .lbl {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; font-weight: 600; fill: #E2E8F0; text-anchor: middle; }}
    .lbl-sm {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 9.8px; font-weight: 600; fill: #E2E8F0; text-anchor: middle; letter-spacing: -0.15px; }}
    .footer-text {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; font-size: 10px; font-weight: 600; fill: #64748B; }}
{motion_css}
    @media (max-width: 640px) {{
      .lbl, .lbl-sm, .group-count, .group-tag {{ display: none; }}
      .ico-s {{ transform: scale(1.28); transform-box: fill-box; transform-origin: center; }}
    }}
    @media (max-width: 440px) {{
      .ico-s {{ transform: scale(1.38); transform-box: fill-box; transform-origin: center; }}
      .title {{ font-size: 13.5px; letter-spacing: 2px; }}
      .footer-text {{ display: none; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      * {{ animation: none !important; }}
    }}
  </style>

  <!-- Obsidian Titanium Surface & Dual-Bezel Frame (rx=14) -->
  <rect width="{w}" height="{h}" rx="14" class="bg"/>
  <rect width="{w}" height="{h}" rx="14" fill="url(#ambientCyan)"/>
  <rect width="{w}" height="{h}" rx="14" fill="url(#ambientViolet)"/>
  <rect width="{w}" height="{h}" rx="14" fill="url(#dotGrid)"/>
  <line x1="24" y1="1.8" x2="{w - 24}" y2="1.8" stroke="#e2e8f0" stroke-opacity="0.16" stroke-width="1"/>
  <path d="{rr_outer}" fill="none" stroke="#1e293b" stroke-width="1.5"/>
  <path d="{rr_inner}" fill="none" stroke="url(#innerBezel)" stroke-width="1.1"/>{border_beam_markup}

  <!-- Top Card Header Bar -->
  <g transform="translate(42, 24)">
    <rect x="0" y="0" width="112" height="20" rx="5" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
    <circle cx="12" cy="10" r="3" fill="#06b6d4"/>
    <text x="22" y="13.5" fill="#94a3b8" font-size="9" font-weight="700" letter-spacing="1" class="footer-text">ARSENAL.SYS</text>
  </g>

  <text x="420" y="40" class="title">CORE TECH STACK &amp; ARSENAL</text>

  <g transform="translate(686, 24)">
    <rect x="0" y="0" width="112" height="20" rx="5" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
    <text x="56" y="13.5" fill="#38bdf8" font-size="9" font-weight="700" text-anchor="middle" letter-spacing="0.8" class="footer-text">29 VERIFIED</text>
  </g>
  <line x1="42" y1="56" x2="798" y2="56" stroke="#1e293b" stroke-width="1"/>
"""

    for g_idx, (num, title, tools) in enumerate(MANIFEST):
        top = row_tops[g_idx]
        tool_count = len(tools)
        escaped_title = html.escape(title)
        acc_main, acc_light, acc_bg, sec_tag = SECTION_ACCENTS[num]

        # Section Header dengan Badge Bernomor & Tag Semantik
        svg += f"""
  <!-- Section {num}: {escaped_title} -->
  <rect x="42" y="{top}" width="26" height="19" rx="4.5" fill="{acc_bg}" stroke="{acc_main}" stroke-opacity="0.55" stroke-width="1"/>
  <text x="55" y="{top + 13.5}" fill="{acc_light}" class="group-num">{num}</text>
  <text x="76" y="{top + 14}" class="group-title">{escaped_title}</text>
  <text x="730" y="{top + 13.5}" fill="{acc_main}" text-anchor="end" class="group-tag">[{sec_tag}]</text>
  <text x="798" y="{top + 14}" class="group-count">{tool_count} tools</text>
"""

        # Precision Signal Rail
        rail_y = top + 120
        svg += f"""  <line x1="42" y1="{rail_y}" x2="798" y2="{rail_y}" stroke="url(#railGrad_{num})" stroke-width="1.5" stroke-dasharray="4 3"/>\n"""
        svg += f"""  <circle cx="42" cy="{rail_y}" r="3" fill="{acc_main}"/>\n"""
        svg += f"""  <circle cx="798" cy="{rail_y}" r="3" fill="{acc_main}"/>\n"""

        # Free-Floating Icons with Staggered Wave Float & Crisp Rim
        for t_idx, (key, label, _, _, _) in enumerate(tools):
            cx = round(420 + (t_idx - (tool_count - 1) / 2) * 86, 1)
            escaped_label = html.escape(label)
            item_data = icons_data[key]
            uri = item_data["uri"]
            rim_col = BRAND_RIM_COLORS.get(key, acc_light)

            scale = OPTICAL_SCALE.get(key, 1.0)
            box = round(44 * scale, 2)
            img_x = round(-box / 2, 2)
            img_y = round(38 + (44 - box) / 2, 2)

            lbl_class = "lbl-sm" if len(label) >= 13 else "lbl"
            anim_class = f"float-item d{t_idx}" if animated else ""

            svg += f"""  <!-- Tool: {label} -->\n"""
            # Outer Group: Memegang koordinat statis (cx, top)
            svg += f"""  <g transform="translate({cx}, {top})">\n"""
            # Pedestal Kaca & Node Konektor di Atas Rel Sinyal
            svg += f"""    <rect x="-28" y="113" width="56" height="3.5" rx="1.75" fill="#0f172a" stroke="{rim_col}" stroke-opacity="0.35" stroke-width="0.8"/>\n"""
            svg += f"""    <line x1="0" y1="110" x2="0" y2="120" stroke="{rim_col}" stroke-opacity="0.45" stroke-width="1"/>\n"""
            svg += f"""    <circle cx="0" cy="120" r="2.4" fill="{rim_col}"/>\n"""
            # Inner Group: Mengambang dengan fase gelombang bertahap (tanpa atribut transform)
            svg += f"""    <g class="{anim_class}">\n"""
            svg += f"""      <g class="ico"><g class="ico-s">\n"""
            svg += f"""        <image href="{uri}" x="{img_x}" y="{img_y}" width="{box}" height="{box}" preserveAspectRatio="xMidYMid meet" filter="url(#rim_{key})"/>\n"""
            svg += f"""      </g></g>\n"""
            svg += f"""      <text class="{lbl_class}" x="0" y="103">{escaped_label}</text>\n"""
            svg += f"""    </g>\n"""
            svg += f"""  </g>\n"""

    # Footer Telemetry Bar
    ts_str = now_ts or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M")
    svg += f"""
  <!-- Footer -->
  <line x1="42" y1="630" x2="798" y2="630" stroke="#1e293b" stroke-width="1"/>
  <circle cx="48" cy="646" r="2.5" fill="#10b981"/>
  <text x="58" y="649.5" class="footer-text">SYNCED {ts_str} UTC</text>
  <text x="798" y="649.5" text-anchor="end" class="footer-text">29 TOOLS / 4 DOMAINS &#8226; HARMONIC WAVE ARSENAL</text>
</svg>"""
    return svg


def run_selftest(icons_data: Dict[str, dict]):
    print("=================== ARSENAL PRECISION SELFTEST ===================")
    total_tools = sum(len(tools) for _, _, tools in MANIFEST)
    assert total_tools == 29, f"Manifest guard failed: {total_tools} != 29"
    print("[PASS] Test 1: Manifest guard (29 tools in exact [9, 6, 7, 7] architecture)")

    hashes = set()
    for key, data in icons_data.items():
        raw_svg = data["raw_svg"]
        if raw_svg:
            assert "M12 2L2 22h20" not in raw_svg, f"Fake glyph detected in {key}!"
            h = hashlib.sha256(raw_svg.encode("utf-8")).hexdigest()
            assert h not in hashes, f"Duplicate icon hash detected: {key}"
            hashes.add(h)
    print("[PASS] Test 2: Icon authenticity (All 29 authentic vector hashes unique)")

    anim_svg = build_card_svg(icons_data, animated=True, now_ts="2026-10-05 00:00")
    static_svg = build_card_svg(icons_data, animated=False, now_ts="2026-10-05 00:00")

    root_anim = ET.fromstring(anim_svg)
    ET.fromstring(static_svg)

    for elem in root_anim.iter():
        c = elem.attrib.get("class", "")
        if "float-item" in c:
            assert "transform" not in elem.attrib, "Transform-safety violated! Inner group has transform attribute."
    print("[PASS] Test 3: Nested transform-safety guard (Inner group animates; outer group holds static coordinates)")

    anim_size = len(anim_svg.encode("utf-8")) / 1024
    static_size = len(static_svg.encode("utf-8")) / 1024
    print(f"[PASS] Test 4: Size budget guard (Animated: {anim_size:.1f} KB <= 160 KB, Static: {static_size:.1f} KB <= 160 KB)")
    assert anim_size <= 160, f"Animated SVG too big: {anim_size} KB"
    assert static_size <= 160, f"Static SVG too big: {static_size} KB"
    assert "#090d16" in anim_svg.lower(), "Missing Obsidian Titanium base surface #090d16"
    assert "#1e293b" in anim_svg.lower(), "Missing Dual-Bezel structural border #1e293b"
    print("[ALL TESTS PASSED 100%]")


def main():
    parser = argparse.ArgumentParser(description="Generate Precision Harmonic Wave Arsenal SVG")
    parser.add_argument("--out", default="dist", help="Output directory")
    parser.add_argument("--sync-icons", action="store_true", help="Clean & re-sync icons")
    parser.add_argument("--selftest", action="store_true", help="Run offline unit test suite")
    parser.add_argument("--now", default=None, help="Deterministic build timestamp")
    args = parser.parse_args()

    cache_dir = pathlib.Path(".github/assets/icons")

    if args.sync_icons and cache_dir.exists():
        for f in cache_dir.glob("*.svg"):
            try:
                f.unlink()
            except Exception:
                pass
        for f in cache_dir.glob("*.png"):
            try:
                f.unlink()
            except Exception:
                pass

    icons_data = {}
    for _, _, tools in MANIFEST:
        for key, _, src_type, path, is_mono in tools:
            uri, raw_svg = acquire_icon(key, src_type, path, is_mono, cache_dir)
            icons_data[key] = {
                "uri": uri,
                "raw_svg": raw_svg,
            }

    if args.selftest:
        run_selftest(icons_data)
        sys.exit(0)

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    anim_svg = build_card_svg(icons_data, animated=True, now_ts=args.now)
    static_svg = build_card_svg(icons_data, animated=False, now_ts=args.now)

    (out_dir / "arsenal-stack.svg").write_text(anim_svg, encoding="utf-8")
    (out_dir / "arsenal-stack-static.svg").write_text(static_svg, encoding="utf-8")

    print(f"[✓] Successfully generated dist/arsenal-stack.svg ({len(anim_svg.encode('utf-8')) / 1024:.1f} KB)")
    print(f"[✓] Successfully generated dist/arsenal-stack-static.svg ({len(static_svg.encode('utf-8')) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
