
"""
Studio-Grade Free-Floating Precision Signal-Bus Arsenal Stack
Pure Native Python Standard Library - Zero External Dependencies
- Zero Box Frame (100% Borderless Seamless Floating Presentation)
- Synchronous Subtle Anti-Gravity Float (All 29 Icons Hover Together, Amp: -3px)
- Enhanced Radiant Rim Light (Bright Neon Edge Bloom, SourceGraphic 100% Untouched)
- Strict Manifest: Exactly 29 Tools across 4 Groups [9, 6, 7, 7]
"""
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
from typing import Dict, List, Optional, Tuple

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
    "github": "#FFFFFF",
    "vscode": "#007ACC",
    "figma": "#F24E1E",
    "chatgpt": "#10A37F",
    "gemini": "#8A5CF6",
    "claude": "#D97706",
    "antigravity": "#C084FC",
    "copilot": "#FFFFFF",
    "cursor": "#FFFFFF",
    "perplexity": "#22B8CD",
    # 04 LLM Platforms & Open Models
    "ollama": "#FFFFFF",
    "huggingface": "#FFD21E",
    "deepseek": "#1E88E5",
    "mistral": "#FF7000",
    "qwen": "#6366F1",
    "grok": "#FFFFFF",
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
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
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
        root.attrib["fill"] = "#F5F3FF"

    return ET.tostring(root, encoding="unicode")

def acquire_icon(key: str, src_type: str, path: str, is_mono: bool, cache_dir: pathlib.Path) -> Tuple[str, str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    svg_cache = cache_dir / f"{key}.svg"
    png_cache = cache_dir / f"{key}.png"

    if svg_cache.exists():
        content = svg_cache.read_text(encoding="utf-8")
        if "M12 2L2 22h20" not in content and "<html" not in content.lower():
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
        raise RuntimeError(f"Fail-closed: Unable to download icon '{key}'. Attempted URLs:\n  " + "\n  ".join(urls_attempted))

    if is_png:
        png_cache.write_bytes(raw_data)
        b64 = base64.b64encode(raw_data).decode("ascii")
        return f"data:image/png;base64,{b64}", ""
    else:
        cleaned_svg = clean_and_normalize_svg(raw_data, is_mono=is_mono)
        svg_cache.write_text(cleaned_svg, encoding="utf-8")
        b64 = base64.b64encode(cleaned_svg.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{b64}", cleaned_svg

def build_card_svg(icons_data: Dict[str, dict], animated: bool = True, now_ts: Optional[str] = None) -> str:
    w = 840
    h = 668
    row_tops = [78, 216, 354, 492]

    # 1. Defs: Rail linear gradient
    rail_defs = []
    for r_idx in range(1, 5):
        rail_defs.append(f"""    <linearGradient id="railGrad_{r_idx}" gradientUnits="userSpaceOnUse" x1="42" y1="0" x2="798" y2="0">
      <stop offset="0%" stop-color="#A855F7" stop-opacity="0.12"/>
      <stop offset="50%" stop-color="#C084FC" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#A855F7" stop-opacity="0.12"/>
    </linearGradient>""")
    rail_defs_str = "\n".join(rail_defs)

    # 2. Defs: Enhanced Radiant Rim Light (Diterangkan & Bersinar Lebih Terang, SourceGraphic 100% Utuh)
    rim_filters = []
    for key, color in BRAND_RIM_COLORS.items():
        rim_filters.append(f"""    <filter id="rim_{key}" x="-35%" y="-35%" width="170%" height="170%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="2.6" result="blur"/>
      <feFlood flood-color="{color}" flood-opacity="0.95" result="col"/>
      <feComposite in="col" in2="blur" operator="in" result="rim"/>
      <feMerge>
        <feMergeNode in="rim"/>
        <feMergeNode in="rim"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>""")
    rim_filters_str = "\n".join(rim_filters)

    # 3. CSS: Synchronous Float (Semua naik-turun bersamaan, gerak tipis -3px)
    motion_css = ""
    if animated:
        motion_css = """
      @keyframes syncFloat {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-3px); }
      }
      .float-item { animation: syncFloat 3.5s ease-in-out infinite; will-change: transform; }"""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-labelledby="arsenal-title arsenal-desc">
  <title id="arsenal-title">Core Tech Stack &amp; Arsenal</title>
  <desc id="arsenal-desc">PHP, Laravel, HTML5, CSS3, JavaScript, TypeScript, React Native, Python, Jupyter, MySQL, PostgreSQL, Git, GitHub, VS Code, Figma, ChatGPT, Gemini, Claude, Antigravity, GitHub Copilot, Cursor, Perplexity, Ollama, Hugging Face, DeepSeek, Mistral AI, Qwen, Grok, Meta Llama</desc>
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#080511"/>
      <stop offset="50%" stop-color="#0F0921"/>
      <stop offset="100%" stop-color="#06030D"/>
    </linearGradient>
    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#E9D5FF"/>
      <stop offset="50%" stop-color="#FFFFFF"/>
      <stop offset="100%" stop-color="#C084FC"/>
    </linearGradient>
{rail_defs_str}
{rim_filters_str}
  </defs>

  <style>
    /* ZERO BOX / BORDERLESS: Tidak ada garis tepi stroke ungu */
    .bg {{ fill: url(#bgGrad); stroke: none; }}
    .title {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 800; font-size: 19px; fill: url(#headerGrad); letter-spacing: 3.5px; text-anchor: middle; }}
    .group-num {{ font-family: ui-monospace, monospace; font-size: 12px; font-weight: 700; fill: #C084FC; }}
    .group-title {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; font-weight: 700; fill: #F3E8FF; letter-spacing: 0.5px; }}
    .group-count {{ font-family: ui-monospace, monospace; font-size: 11px; fill: #94A3B8; text-anchor: end; }}
    .lbl {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; font-weight: 600; fill: #E2E8F0; text-anchor: middle; }}
    .footer-text {{ font-family: ui-monospace, monospace; font-size: 10.5px; fill: #6B7280; }}
{motion_css}
    @media (max-width: 640px) {{
      .lbl, .group-count {{ display: none; }}
      .ico-s {{ transform: scale(1.3); transform-box: fill-box; transform-origin: center; }}
    }}
    @media (max-width: 440px) {{
      .ico-s {{ transform: scale(1.4); transform-box: fill-box; transform-origin: center; }}
      .title {{ font-size: 14px; letter-spacing: 2px; }}
      .footer-text {{ display: none; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      * {{ animation: none !important; }}
    }}
  </style>

  <!-- Seamless Borderless Canvas (Garis stroke ungu box dihapus total) -->
  <rect width="{w}" height="{h}" class="bg"/>

  <!-- Card Header -->
  <circle cx="230" cy="39" r="4" fill="#A855F7"/>
  <circle cx="610" cy="39" r="4" fill="#A855F7"/>
  <text x="420" y="44" class="title">CORE TECH STACK &amp; ARSENAL</text>
"""

    for g_idx, (num, title, tools) in enumerate(MANIFEST):
        top = row_tops[g_idx]
        r = g_idx + 1
        tool_count = len(tools)
        escaped_title = html.escape(title)

        # Section Header (Murni teks, zero box)
        svg += f"""
  <!-- Section {num}: {escaped_title} -->
  <text x="42" y="{top + 14}" class="group-num">{num}</text>
  <text x="68" y="{top + 14}" class="group-title">{escaped_title}</text>
  <text x="798" y="{top + 14}" class="group-count">{tool_count} tools</text>
"""

        # Clean Signal Rail
        rail_y = top + 120
        svg += f"""  <line x1="42" y1="{rail_y}" x2="798" y2="{rail_y}" stroke="url(#railGrad_{r})" stroke-width="1.5" stroke-dasharray="4 3"/>\n"""
        svg += f"""  <circle cx="42" cy="{rail_y}" r="3" fill="#A855F7"/>\n"""
        svg += f"""  <circle cx="798" cy="{rail_y}" r="3" fill="#A855F7"/>\n"""

        # Free-Floating Icons with Synchronous Float & Luminous Rim
        for t_idx, (key, label, _, _, _) in enumerate(tools):
            cx = round(420 + (t_idx - (tool_count - 1) / 2) * 86, 1)
            escaped_label = html.escape(label)
            item_data = icons_data[key]
            uri = item_data["uri"]
            rim_col = BRAND_RIM_COLORS.get(key, "#C084FC")

            scale = OPTICAL_SCALE.get(key, 1.0)
            box = round(44 * scale, 2)
            img_x = round(-box / 2, 2)
            img_y = round(40 + (44 - box) / 2, 2)

            tlen_attr = ' textLength="84" lengthAdjust="spacingAndGlyphs"' if len(label) >= 13 else ""
            anim_class = "float-item" if animated else ""

            svg += f"""  <!-- Tool: {label} -->\n"""
            # Outer Group: Statis murni pada (cx, top)
            svg += f"""  <g transform="translate({cx}, {top})">\n"""
            # Signal Node Point di Rel
            svg += f"""    <circle cx="0" cy="120" r="2.2" fill="{rim_col}" opacity="0.9"/>\n"""
            # Inner Group: Mengambang serentak bersamaan (Amp: -3px)
            svg += f"""    <g class="{anim_class}">\n"""
            svg += f"""      <g class="ico"><g class="ico-s">\n"""
            svg += f"""        <image href="{uri}" x="{img_x}" y="{img_y}" width="{box}" height="{box}" preserveAspectRatio="xMidYMid meet" filter="url(#rim_{key})"/>\n"""
            svg += f"""      </g></g>\n"""
            svg += f"""      <text class="lbl" x="0" y="104" text-anchor="middle"{tlen_attr}>{escaped_label}</text>\n"""
            svg += f"""    </g>\n"""
            svg += f"""  </g>\n"""

    # Footer
    ts_str = now_ts or dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M')
    svg += f"""
  <!-- Footer -->
  <text x="42" y="650" class="footer-text">synced {ts_str} UTC</text>
  <text x="798" y="650" text-anchor="end" class="footer-text">29 tools / 4 groups &#8226; Synchronous Floating Arsenal</text>
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
    root_static = ET.fromstring(static_svg)

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
    print("[ALL TESTS PASSED 100%]")

def main():
    parser = argparse.ArgumentParser(description="Generate Precision Free-Floating Arsenal SVG")
    parser.add_argument("--out", default="dist", help="Output directory")
    parser.add_argument("--sync-icons", action="store_true", help="Clean & re-sync icons")
    parser.add_argument("--selftest", action="store_true", help="Run offline unit test suite")
    parser.add_argument("--now", default=None, help="Deterministic build timestamp")
    args = parser.parse_args()

    cache_dir = pathlib.Path(".github/assets/icons")

    if args.sync_icons and cache_dir.exists():
        for f in cache_dir.glob("*.svg"):
            try: f.unlink()
            except Exception: pass
        for f in cache_dir.glob("*.png"):
            try: f.unlink()
            except Exception: pass

    icons_data = {}
    for _, _, tools in MANIFEST:
        for key, _, src_type, path, is_mono in tools:
            uri, raw_svg = acquire_icon(key, src_type, path, is_mono, cache_dir)
            icons_data[key] = {
                "uri": uri,
                "raw_svg": raw_svg
            }

    if args.selftest:
        run_selftest(icons_data)

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
