#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Studio-Grade Free-Floating Signal-Bus Arsenal Stack
Pure Native Python Standard Library - Zero External Dependencies
- 100% Free-Floating Icons (No bounding box/tiles)
- Auto-Contrast Dark Icons (GitHub, ChatGPT, Ollama, Grok, Copilot shine bright white/teal)
- Smooth GPU Wave Levitation
- Exactly 29 Tools across 4 Architectural Groups [9, 6, 7, 7]
"""
import argparse
import base64
import datetime as dt
import os
import pathlib
import re
import sys
import urllib.request
from typing import Dict, List, Tuple

GROUPS = [
    ("01", "Languages & Core Technologies", [
        ("php", "PHP", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/php/php-original.svg"),
        ("laravel", "Laravel", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/laravel/laravel-original.svg"),
        ("html5", "HTML5", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/html5/html5-original.svg"),
        ("css3", "CSS3", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/css3/css3-original.svg"),
        ("javascript", "JavaScript", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/javascript/javascript-original.svg"),
        ("typescript", "TypeScript", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/typescript/typescript-original.svg"),
        ("react", "React Native", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/react/react-original.svg"),
        ("python", "Python", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/python/python-original.svg"),
        ("jupyter", "Jupyter", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/jupyter/jupyter-original.svg"),
    ]),
    ("02", "Database & Development Environment", [
        ("mysql", "MySQL", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/mysql/mysql-original.svg"),
        ("postgresql", "PostgreSQL", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/postgresql/postgresql-original.svg"),
        ("git", "Git", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/git/git-original.svg"),
        ("github", "GitHub", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/github/github-original.svg"),
        ("vscode", "VS Code", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/vscode/vscode-original.svg"),
        ("figma", "Figma", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/figma/figma-original.svg"),
    ]),
    ("03", "AI Coding Assistants & Agents", [
        ("chatgpt", "ChatGPT", "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/openai.svg"),
        ("gemini", "Gemini", "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/google/google-original.svg"),
        ("claude", "Claude", "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/anthropic.svg"),
        ("antigravity", "Antigravity", "BUILTIN"),
        ("copilot", "GitHub Copilot", "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/githubcopilot.svg"),
        ("cursor", "Cursor", "BUILTIN"),
        ("perplexity", "Perplexity", "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/perplexity.svg"),
    ]),
    ("04", "LLM Platforms & Open Models", [
        ("ollama", "Ollama", "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/ollama.svg"),
        ("huggingface", "Hugging Face", "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/huggingface.svg"),
        ("deepseek", "DeepSeek", "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/deepseek.svg"),
        ("mistral", "Mistral AI", "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/mistral.svg"),
        ("qwen", "Qwen", "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/qwen.svg"),
        ("grok", "Grok", "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/x.svg"),
        ("llama", "Meta Llama", "https://cdn.jsdelivr.net/gh/simple-icons/simple-icons@develop/icons/meta.svg"),
    ]),
]

BUILTIN_SVGS = {
    "antigravity": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#C084FC" d="M12 2L2 22h20L12 2zm0 4.5l6.5 13h-13L12 6.5z"/><circle cx="12" cy="14" r="2.5" fill="#38BDF8"/></svg>""",
    "cursor": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#FFFFFF" d="M12 2L3 7v10l9 5 9-5V7l-9-5zm0 2.2l6.8 3.8-6.8 3.8-6.8-3.8L12 4.2zM5 8.7l6 3.3v6.7l-6-3.3V8.7zm8 10V12l6-3.3v6.7l-6 3.3z"/></svg>""",
}

# Daftar ikon monochrome hitam yang harus diubah jadi PUTIH TERANG (#FFFFFF) agar menyala di dark mode
DARK_ICONS_TO_WHITE = {"github", "chatgpt", "copilot", "ollama", "grok", "cursor"}

def download_and_clean_svg(key: str, url: str) -> str:
    if url == "BUILTIN":
        return BUILTIN_SVGS.get(key, "")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
        
        # Bersihkan XML header & comments
        content = re.sub(r"<\?xml.*?\?>", "", content)
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        
        # Berikan warna putih terang untuk ikon yang aslinya hitam agar kontras di background gelap
        if key in DARK_ICONS_TO_WHITE:
            if 'fill="' in content:
                content = re.sub(r'fill="(?:#000(?:000)?|#181717|#24292e|black)"', 'fill="#FFFFFF"', content, flags=re.IGNORECASE)
            else:
                content = re.sub(r'<path', '<path fill="#FFFFFF"', content)
        elif key == "claude":
            # Berikan warna terracotta resmi Claude
            content = re.sub(r'<path', '<path fill="#D97706"', content)
        elif key == "perplexity":
            content = re.sub(r'<path', '<path fill="#22B8CD"', content)
        elif key == "deepseek":
            content = re.sub(r'<path', '<path fill="#1E88E5"', content)
        elif key == "llama":
            content = re.sub(r'<path', '<path fill="#0468FF"', content)
            
        return content.strip()
    except Exception as e:
        print(f"Warning: Failed to fetch {key} ({e}), using fallback.")
        return BUILTIN_SVGS.get("antigravity", "")

def load_all_icons(cache_dir: pathlib.Path) -> Dict[str, str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    icons = {}
    for _, _, tools in GROUPS:
        for key, name, url in tools:
            cache_file = cache_dir / f"{key}.svg"
            if cache_file.exists():
                svg_data = cache_file.read_text(encoding="utf-8")
                # Pastikan ikon gelap tetap putih
                if key in DARK_ICONS_TO_WHITE and ('fill="#000"' in svg_data or 'fill="#181717"' in svg_data or 'fill="black"' in svg_data):
                    svg_data = re.sub(r'fill="(?:#000(?:000)?|#181717|#24292e|black)"', 'fill="#FFFFFF"', svg_data, flags=re.IGNORECASE)
                    cache_file.write_text(svg_data, encoding="utf-8")
            else:
                svg_data = download_and_clean_svg(key, url)
                cache_file.write_text(svg_data, encoding="utf-8")
            
            # Encode ke Data URI base64
            b64 = base64.b64encode(svg_data.encode("utf-8")).decode("ascii")
            icons[key] = f"data:image/svg+xml;base64,{b64}"
    return icons

def generate_svg(icons_map: Dict[str, str], animated: bool = True) -> str:
    w = 840
    h = 708
    
    # CSS Styles: Zero tile boxes, purely smooth floating animation
    anim_css = """
      @keyframes floatWave {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-7px); }
      }
      .wave-item { animation: floatWave 3.5s ease-in-out infinite; will-change: transform; }
    """ if animated else ""
    
    # Generate staggered delays for smooth wave motion
    delay_rules = []
    if animated:
        for i in range(29):
            delay = round((i * 0.18) % 3.0, 2)
            delay_rules.append(f".wave-d{i} {{ animation-delay: {delay}s; }}")
    
    delays_str = "\n".join(delay_rules)
    
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#080511"/>
      <stop offset="50%" stop-color="#0F0921"/>
      <stop offset="100%" stop-color="#06030D"/>
    </linearGradient>
    <linearGradient id="railGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#A855F7" stop-opacity="0.1"/>
      <stop offset="50%" stop-color="#C084FC" stop-opacity="0.6"/>
      <stop offset="100%" stop-color="#A855F7" stop-opacity="0.1"/>
    </linearGradient>
    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#E9D5FF"/>
      <stop offset="50%" stop-color="#FFFFFF"/>
      <stop offset="100%" stop-color="#C084FC"/>
    </linearGradient>
  </defs>

  <style>
    .bg {{ fill: url(#bgGrad); stroke: #2E1065; stroke-width: 1.5; rx: 18px; }}
    .title {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-weight: 800; font-size: 19px; fill: url(#headerGrad); letter-spacing: 3.5px; text-anchor: middle; }}
    .group-num {{ font-family: ui-monospace, monospace; font-size: 11px; font-weight: 700; fill: #C084FC; }}
    .group-title {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 14px; font-weight: 700; fill: #F3E8FF; letter-spacing: 0.5px; }}
    .group-count {{ font-family: ui-monospace, monospace; font-size: 11px; fill: #94A3B8; text-anchor: end; }}
    .tool-label {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11.5px; font-weight: 600; fill: #E2E8F0; text-anchor: middle; }}
    .footer-text {{ font-family: ui-monospace, monospace; font-size: 10.5px; fill: #6B7280; }}
    {anim_css}
    {delays_str}
  </style>

  <!-- Main Background Container -->
  <rect width="{w}" height="{h}" class="bg"/>

  <!-- Card Header -->
  <g transform="translate(420, 48)">
    <circle cx="-190" cy="-5" r="4" fill="#A855F7"/>
    <circle cx="190" cy="-5" r="4" fill="#A855F7"/>
    <text y="0" class="title">CORE TECH STACK &amp; ARSENAL</text>
  </g>
"""
    
    group_y_positions = [72, 218, 364, 510]
    global_tool_idx = 0
    
    for g_idx, (num, title, tools) in enumerate(GROUPS):
        gy = group_y_positions[g_idx]
        tool_count = len(tools)
        
        # Section Header
        svg += f"""
  <!-- Section {num}: {title} -->
  <g transform="translate(42, {gy})">
    <rect x="0" y="0" width="24" height="17" rx="4" fill="#3B0764" stroke="#7E22CE" stroke-width="0.8"/>
    <text x="12" y="12" text-anchor="middle" class="group-num">{num}</text>
    <text x="34" y="13" class="group-title">{title}</text>
    <text x="756" y="13" class="group-count">{tool_count} tools</text>
  </g>
"""
        
        # Circuit Rail (Tumpuan Energi)
        rail_y = gy + 102
        svg += f"""  <line x1="42" y1="{rail_y}" x2="798" y2="{rail_y}" stroke="url(#railGrad)" stroke-width="1.5" stroke-dasharray="4 3"/>\n"""
        svg += f"""  <circle cx="42" cy="{rail_y}" r="3" fill="#A855F7"/>\n"""
        svg += f"""  <circle cx="798" cy="{rail_y}" r="3" fill="#A855F7"/>\n"""
        
        # Free-Floating Tool Items
        spacing = 756 / (tool_count + 1)
        for t_idx, (key, label, _) in enumerate(tools):
            center_x = round(42 + spacing * (t_idx + 1), 1)
            item_y = gy + 32
            anim_class = f"wave-item wave-d{global_tool_idx}" if animated else ""
            
            # Node connection dot on rail
            svg += f"""  <circle cx="{center_x}" cy="{rail_y}" r="2" fill="#C084FC" opacity="0.6"/>\n"""
            
            # Floating Group (Ikon + Label, BEBAS TANPA KOTAK)
            svg += f"""  <g class="{anim_class}" transform="translate({center_x}, {item_y})">\n"""
            # Icon (Diperbesar ke 40x40 agar jernih dan lega)
            svg += f"""    <image href="{icons_map[key]}" x="-20" y="0" width="40" height="40" preserveAspectRatio="xMidYMid meet"/>\n"""
            # Label
            svg += f"""    <text x="0" y="58" class="tool-label">{label}</text>\n"""
            svg += f"""  </g>\n"""
            
            global_tool_idx += 1

    # Footer
    svg += f"""
  <!-- Footer Info -->
  <g transform="translate(42, 680)">
    <text x="0" y="0" class="footer-text">synced {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</text>
    <text x="756" y="0" text-anchor="end" class="footer-text">29 tools / 4 groups • 60 FPS Free-Floating</text>
  </g>
</svg>"""
    return svg

def main():
    parser = argparse.ArgumentParser(description="Generate Free-Floating Arsenal SVG Stack")
    parser.add_argument("--out", default="dist", help="Output directory")
    parser.add_argument("--sync-icons", action="store_true", help="Download and cache icons")
    parser.add_argument("--selftest", action="store_true", help="Run offline validation")
    args = parser.parse_args()

    cache_dir = pathlib.Path(".github/assets/icons")
    icons_map = load_all_icons(cache_dir)

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    anim_svg = generate_svg(icons_map, animated=True)
    static_svg = generate_svg(icons_map, animated=False)

    (out_dir / "arsenal-stack.svg").write_text(anim_svg, encoding="utf-8")
    (out_dir / "arsenal-stack-static.svg").write_text(static_svg, encoding="utf-8")
    print(f"[✓] Generated arsenal-stack.svg ({len(anim_svg.encode('utf-8')) / 1024:.1f} KB)")
    print(f"[✓] Generated arsenal-stack-static.svg ({len(static_svg.encode('utf-8')) / 1024:.1f} KB)")

if __name__ == "__main__":
    main()
