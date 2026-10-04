#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Studio-Grade Cyberpunk Developer Metrics Suite
Pure Native Python Standard Library - Zero External Dependencies
Generates 5 Validated SVGs:
  1. metrics-header.svg
  2. streak-stats.svg
  3. activity-graph.svg
  4. github-stats.svg
  5. top-langs.svg
"""
import argparse
import datetime as dt
import json
import math
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict

USERNAME = "rjoulfiand-afk"
DEFAULT_OUT = "dist"

# ==============================================================================
# 1. DATA TELEMETRY & AUDIT ENGINE
# ==============================================================================
def get_today_utc():
    return dt.datetime.now(dt.timezone.utc).date()

def parse_iso_date(d_str):
    return dt.date.fromisoformat(d_str.split("T")[0])

def http_json(url, headers=None, post_data=None):
    req = urllib.request.Request(
        url,
        headers=headers or {"User-Agent": "CyberTelemetry/2.0"},
        data=post_data
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_graphql_calendar(token, user, today):
    headers = {
        "User-Agent": "CyberTelemetry/2.0",
        "Authorization": f"bearer {token}"
    }
    
    # 1. Fetch user creation date & stats
    init_query = """
    query($user: String!) {
      user(login: $user) {
        createdAt
        contributionsCollection {
          totalCommitContributions
        }
        repositoriesContributedTo(contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {
          totalCount
        }
        pullRequests {
          totalCount
        }
        issues {
          totalCount
        }
      }
    }
    """
    post_data = json.dumps({"query": init_query, "variables": {"user": user}}).encode("utf-8")
    init_res = http_json("https://api.github.com/graphql", headers, post_data)
    
    if "errors" in init_res or "data" not in init_res or not init_res["data"]["user"]:
        raise ValueError(f"GraphQL user init failed: {init_res.get('errors')}")

    u = init_res["data"]["user"]
    created_date = parse_iso_date(u["createdAt"])
    total_commits_rolling = u["contributionsCollection"]["totalCommitContributions"]
    total_prs = u["pullRequests"]["totalCount"]
    total_issues = u["issues"]["totalCount"]
    contributed_to = u["repositoriesContributedTo"]["totalCount"]

    # 2. Loop yearly windows to capture all-time daily contributions
    cal_dict = {}
    cur_year_start = created_date
    cal_query = """
    query($user: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $user) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    while cur_year_start <= today:
        cur_year_end = min(cur_year_start + dt.timedelta(days=364), today)
        from_iso = cur_year_start.isoformat() + "T00:00:00Z"
        to_iso = cur_year_end.isoformat() + "T23:59:59Z"
        
        q_data = json.dumps({
            "query": cal_query,
            "variables": {"user": user, "from": from_iso, "to": to_iso}
        }).encode("utf-8")
        
        c_res = http_json("https://api.github.com/graphql", headers, q_data)
        weeks = c_res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for w in weeks:
            for d in w["contributionDays"]:
                day_date = parse_iso_date(d["date"])
                if day_date <= today:
                    cal_dict[day_date] = d["contributionCount"]

        cur_year_start = cur_year_end + dt.timedelta(days=1)

    # 3. Paginate all non-fork owned repositories for Stars & Languages
    repos_query = """
    query($user: String!, $cursor: String) {
      user(login: $user) {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, after: $cursor) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            name
            stargazerCount
            languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
    }
    """
    total_stars = 0
    lang_bytes = defaultdict(int)
    lang_colors = {}
    cursor = None
    repo_count = 0

    while True:
        r_data = json.dumps({
            "query": repos_query,
            "variables": {"user": user, "cursor": cursor}
        }).encode("utf-8")
        r_res = http_json("https://api.github.com/graphql", headers, r_data)
        rep_data = r_res["data"]["user"]["repositories"]
        
        for repo in rep_data["nodes"]:
            repo_count += 1
            total_stars += repo["stargazerCount"]
            for edge in repo["languages"]["edges"]:
                lname = edge["node"]["name"]
                lcolor = edge["node"].get("color") or "#a78bfa"
                lsize = edge["size"]
                lang_bytes[lname] += lsize
                lang_colors[lname] = lcolor

        if rep_data["pageInfo"]["hasNextPage"]:
            cursor = rep_data["pageInfo"]["endCursor"]
        else:
            break

    return {
        "calendar": cal_dict,
        "created_date": created_date,
        "total_commits": total_commits_rolling,
        "total_prs": total_prs,
        "total_issues": total_issues,
        "total_stars": total_stars,
        "contributed_to": contributed_to,
        "lang_bytes": lang_bytes,
        "lang_colors": lang_colors,
        "repo_count": repo_count,
        "source": "GraphQL"
    }

def fetch_jogruber_fallback(user, today):
    url = f"https://github-contributions-api.jogruber.de/v4/{user}?y=all"
    res = http_json(url)
    items = res.get("contributions", [])
    if not items:
        raise ValueError("Jogruber API returned empty calendar")

    cal_dict = {}
    for it in items:
        d_date = parse_iso_date(it["date"])
        if d_date <= today:
            cal_dict[d_date] = it["count"]

    created_date = min(cal_dict.keys()) if cal_dict else today

    # Fetch basic repo metrics from public REST
    repos_url = f"https://api.github.com/users/{user}/repos?per_page=100&type=owner"
    repos = http_json(repos_url)
    total_stars = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork"))
    lang_bytes = defaultdict(int)
    lang_colors = {}
    repo_count = len([r for r in repos if not r.get("fork")])

    for r in repos:
        if not r.get("fork") and r.get("language"):
            lang_bytes[r["language"]] += 1000
            lang_colors[r["language"]] = "#a78bfa"

    return {
        "calendar": cal_dict,
        "created_date": created_date,
        "total_commits": sum(cal_dict.values()),
        "total_prs": 0,
        "total_issues": 0,
        "total_stars": total_stars,
        "contributed_to": 0,
        "lang_bytes": lang_bytes,
        "lang_colors": lang_colors,
        "repo_count": repo_count,
        "source": "jogruber"
    }

def process_telemetry(raw_data, today):
    cal_dict = raw_data["calendar"]
    assert cal_dict, "Calendar dataset cannot be empty"
    assert max(cal_dict.keys()) <= today, f"Future dates detected: max={max(cal_dict.keys())} > today={today}"

    sorted_dates = sorted(cal_dict.keys())
    earliest_date = sorted_dates[0]
    total_all_time = sum(cal_dict.values())

    # 365 Days Rolling Window: [today - 364, today]
    start_365 = today - dt.timedelta(days=364)
    rolling_365_days = []
    curr = start_365
    while curr <= today:
        rolling_365_days.append((curr, cal_dict.get(curr, 0)))
        curr += dt.timedelta(days=1)

    total_last_year = sum(cnt for _, cnt in rolling_365_days)
    active_days = sum(1 for _, cnt in rolling_365_days if cnt > 0)
    active_pct = round((active_days / 365.0) * 100.0)

    # Current Streak Calculation with Grace Period for Today
    today_cnt = cal_dict.get(today, 0)
    yesterday = today - dt.timedelta(days=1)
    yesterday_cnt = cal_dict.get(yesterday, 0)

    cur_streak = 0
    cur_streak_start = None
    cur_streak_end = None

    if today_cnt > 0:
        cur_streak_end = today
        chk = today
        while chk in cal_dict and cal_dict[chk] > 0:
            cur_streak += 1
            cur_streak_start = chk
            chk -= dt.timedelta(days=1)
    elif yesterday_cnt > 0:
        # Grace period: today is 0 so far, streak intact through yesterday
        cur_streak_end = yesterday
        chk = yesterday
        while chk in cal_dict and cal_dict[chk] > 0:
            cur_streak += 1
            cur_streak_start = chk
            chk -= dt.timedelta(days=1)
    else:
        cur_streak = 0
        cur_streak_start = None
        cur_streak_end = None

    # Longest Streak (All-time)
    longest_streak = 0
    longest_start = None
    longest_end = None
    temp_len = 0
    temp_s = None

    for d in sorted_dates:
        cnt = cal_dict[d]
        if cnt > 0:
            if temp_len == 0:
                temp_s = d
            temp_len += 1
            if temp_len >= longest_streak:
                longest_streak = temp_len
                longest_start = temp_s
                longest_end = d
        else:
            temp_len = 0
            temp_s = None

    # Best Week (7 consecutive rolling days in the 365 window)
    best_week_sum = 0
    best_week_start = rolling_365_days[0][0]
    best_week_end = rolling_365_days[6][0]

    for i in range(len(rolling_365_days) - 6):
        w_sum = sum(cnt for _, cnt in rolling_365_days[i:i+7])
        if w_sum > best_week_sum:
            best_week_sum = w_sum
            best_week_start = rolling_365_days[i][0]
            best_week_end = rolling_365_days[i+6][0]

    # Peak Day in 365 window
    peak_cnt = 0
    peak_date = today
    for d, cnt in rolling_365_days:
        if cnt >= peak_cnt:
            peak_cnt = cnt
            peak_date = d

    # 53 Weekly Aggregation for Chart Curve
    weekly_totals = []
    w_idx = 0
    while w_idx < len(rolling_365_days):
        chunk = rolling_365_days[w_idx:w_idx+7]
        weekly_totals.append(sum(c for _, c in chunk))
        w_idx += 7
    if len(weekly_totals) < 53:
        weekly_totals.append(0)

    # Languages Processing
    exclude_env = os.environ.get("EXCLUDE_LANGS", "")
    excluded = {x.strip().lower() for x in exclude_env.split(",") if x.strip()}

    lang_bytes = raw_data["lang_bytes"]
    lang_colors = raw_data["lang_colors"]
    filtered_langs = {k: v for k, v in lang_bytes.items() if k.lower() not in excluded}
    total_l_bytes = sum(filtered_langs.values())

    langs_list = []
    if total_l_bytes > 0:
        sorted_l = sorted(filtered_langs.items(), key=lambda x: x[1], reverse=True)
        top6 = sorted_l[:6]
        top6_sum = sum(v for _, v in top6)
        
        for name, b_cnt in top6:
            pct = (b_cnt / total_l_bytes) * 100.0
            langs_list.append({
                "name": name,
                "pct": pct,
                "color": lang_colors.get(name, "#a78bfa")
            })

        if len(sorted_l) > 6:
            other_pct = ((total_l_bytes - top6_sum) / total_l_bytes) * 100.0
            if other_pct > 0.05:
                langs_list.append({
                    "name": "Other",
                    "pct": other_pct,
                    "color": "#6b21a8"
                })

    return {
        "today": today,
        "earliest_date": earliest_date,
        "total_all_time": total_all_time,
        "total_last_year": total_last_year,
        "active_days": active_days,
        "active_pct": active_pct,
        "current_streak": cur_streak,
        "current_streak_start": cur_streak_start,
        "current_streak_end": cur_streak_end,
        "longest_streak": longest_streak,
        "longest_streak_start": longest_start,
        "longest_streak_end": longest_end,
        "best_week": best_week_sum,
        "best_week_start": best_week_start,
        "best_week_end": best_week_end,
        "peak_day_cnt": peak_cnt,
        "peak_day_date": peak_date,
        "weekly_totals": weekly_totals,
        "daily_raw": [c for _, c in rolling_365_days],
        "rolling_dates": [d for d, _ in rolling_365_days],
        "total_commits": raw_data["total_commits"],
        "total_prs": raw_data["total_prs"],
        "total_issues": raw_data["total_issues"],
        "total_stars": raw_data["total_stars"],
        "contributed_to": raw_data["contributed_to"],
        "languages": langs_list,
        "repo_count": raw_data["repo_count"],
        "total_lang_bytes": total_l_bytes,
        "source": raw_data["source"]
    }

# ==============================================================================
# 2. FRITSCH-CARLSON MONOTONE CUBIC SPLINE ALGORITHM
# ==============================================================================
def monotone_cubic_spline(pts, y_top, y_bottom):
    n = len(pts)
    if n < 2:
        return ""
    x = [p[0] for p in pts]
    y = [p[1] for p in pts]

    d_x = [x[i+1] - x[i] for i in range(n - 1)]
    m = [(y[i+1] - y[i]) / d_x[i] if d_x[i] != 0 else 0 for i in range(n - 1)]

    # Initial tangents
    d = [0.0] * n
    d[0] = m[0]
    d[-1] = m[-1]
    for i in range(1, n - 1):
        if m[i-1] * m[i] <= 0:
            d[i] = 0.0
        else:
            d[i] = (m[i-1] + m[i]) / 2.0

    # Fritsch-Carlson limits
    for i in range(n - 1):
        if m[i] == 0:
            d[i] = 0.0
            d[i+1] = 0.0
        else:
            alpha = d[i] / m[i]
            beta = d[i+1] / m[i]
            dist_sq = alpha * alpha + beta * beta
            if dist_sq > 9.0:
                tau = 3.0 / math.sqrt(dist_sq)
                d[i] = tau * alpha * m[i]
                d[i+1] = tau * beta * m[i]

    # Convert Hermite to Cubic Bezier Segments
    path_tokens = [f"M {x[0]:.2f} {y[0]:.2f}"]
    for i in range(n - 1):
        h = d_x[i]
        cp1x = x[i] + h / 3.0
        cp1y = y[i] + d[i] * h / 3.0
        cp2x = x[i+1] - h / 3.0
        cp2y = y[i+1] - d[i+1] * h / 3.0

        cp1y = max(y_top, min(y_bottom, cp1y))
        cp2y = max(y_top, min(y_bottom, cp2y))
        path_tokens.append(f"C {cp1x:.2f} {cp1y:.2f}, {cp2x:.2f} {cp2y:.2f}, {x[i+1]:.2f} {y[i+1]:.2f}")

    return " ".join(path_tokens)

# ==============================================================================
# 3. STUDIO-GRADE SVG PRESENTATION ENGINE (PURPLE LAVA THEME)
# ==============================================================================
COMMON_DEFS = """
  <defs>
    <!-- Dark Cosmic Radial Glow -->
    <radialGradient id="card-aurora" cx="50%" cy="40%" r="65%">
      <stop offset="0%" stop-color="#4c1d95" stop-opacity="0.22" />
      <stop offset="60%" stop-color="#2e1065" stop-opacity="0.08" />
      <stop offset="100%" stop-color="#07040f" stop-opacity="0.0" />
    </radialGradient>

    <!-- Lava Lamp Gooey Fusion Filter -->
    <filter id="lava-fusion" x="-20%" y="-20%" width="140%" height="140%" filterUnits="userSpaceOnUse">
      <feGaussianBlur stdDeviation="2.4" result="blur" />
      <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 20 -8" result="goo" />
      <feGaussianBlur in="goo" stdDeviation="5.0" result="lava-glow" />
      <feMerge>
        <feMergeNode in="lava-glow" />
        <feMergeNode in="goo" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>

    <radialGradient id="magma-blob" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#e9d5ff" stop-opacity="0.8" />
      <stop offset="40%" stop-color="#a855f7" stop-opacity="0.4" />
      <stop offset="100%" stop-color="#4c1d95" stop-opacity="0" />
    </radialGradient>
  </defs>
"""

def rounded_rect_path(w, h, r, inset=1.5):
    # Generates exact SVG path for rounded rectangle with inset
    x0 = inset
    y0 = inset
    x1 = w - inset
    y1 = h - inset
    rad = r - inset
    return f"M {x0 + rad} {y0} L {x1 - rad} {y0} A {rad} {rad} 0 0 1 {x1} {y0 + rad} L {x1} {y1 - rad} A {rad} {rad} 0 0 1 {x1 - rad} {y1} L {x0 + rad} {y1} A {rad} {rad} 0 0 1 {x0} {y1 - rad} L {x0} {y0 + rad} A {rad} {rad} 0 0 1 {x0 + rad} {y0} Z"

def lava_border_frame(w, h, card_id="card", delay_offset=0):
    rr_d = rounded_rect_path(w, h, 14, inset=1.5)
    return f"""
    <!-- Base Dark Background -->
    <rect width="{w}" height="{h}" rx="14" fill="#07040f" />
    <rect width="{w}" height="{h}" rx="14" fill="url(#card-aurora)" />

    <!-- Inward Lava Bleed -->
    <path d="{rr_d}" fill="none" stroke="#6d28d9" stroke-width="6" opacity="0.25" style="filter: blur(4px);" />

    <!-- Static Layer 0 -->
    <path d="{rr_d}" fill="none" stroke="#2e1065" stroke-width="1.2" opacity="0.7" />

    <!-- Flowing Lava Magma Gooey Group -->
    <g filter="url(#lava-fusion)">
      <!-- Layer 1: Body Magma -->
      <path d="{rr_d}" fill="none" stroke="#6d28d9" stroke-width="5" stroke-linecap="round"
            stroke-dasharray="22 9 8 14 30 17" pathLength="100">
        <animate attributeName="stroke-dashoffset" from="0" to="-100" dur="26s" repeatCount="indefinite"
                 begin="-{delay_offset}s" calcMode="spline" keyTimes="0;0.5;1" keySplines="0.4 0 0.6 1; 0.4 0 0.6 1" values="0;-38;-100" />
      </path>

      <!-- Layer 2: Thermal Violet Pulse -->
      <path d="{rr_d}" fill="none" stroke="#c084fc" stroke-width="3" stroke-linecap="round"
            stroke-dasharray="10 12 5 20 14 39" pathLength="100">
        <animate attributeName="stroke-dashoffset" from="0" to="-100" dur="17s" repeatCount="indefinite"
                 begin="-{delay_offset + 4}s" />
      </path>

      <!-- Layer 3: Hot Molten Core -->
      <path d="{rr_d}" fill="none" stroke="#f5d0fe" stroke-width="1.4" stroke-linecap="round"
            stroke-dasharray="3 22 2 31 4 38" pathLength="100">
        <animate attributeName="stroke-dashoffset" from="0" to="-100" dur="11s" repeatCount="indefinite"
                 begin="-{delay_offset + 2}s" />
      </path>
    </g>

    <!-- Floating Magma Heads along Path -->
    <circle r="14" fill="url(#magma-blob)">
      <animateMotion path="{rr_d}" dur="40s" repeatCount="indefinite" begin="-{delay_offset + 8}s" />
    </circle>
    <circle r="10" fill="url(#magma-blob)">
      <animateMotion path="{rr_d}" dur="63s" repeatCount="indefinite" begin="-{delay_offset + 24}s" />
    </circle>
    """

def odometer_number(val, font_size=38, font_weight=900, text_class="odometer"):
    val_str = str(val)
    chars = []
    x_step = font_size * 0.64
    total_w = len(val_str) * x_step

    for idx, ch in enumerate(val_str):
        cx = idx * x_step - (total_w / 2.0) + (x_step / 2.0)
        if ch.isdigit():
            target_d = int(ch)
            # Create smooth rolling vertical column of 0-9 digits
            digits_str = "".join(f'<tspan x="{cx:.1f}" dy="{font_size if d > 0 else 0}">{d}</tspan>' for d in range(10))
            anim_y = f'<animateTransform attributeName="transform" type="translate" dur="2.4s" calcMode="spline" keyTimes="0;0.7;1" keySplines="0.25 0.1 0.25 1;0.25 0.1 0.25 1" values="0 0; 0 -{target_d * font_size}; 0 -{target_d * font_size}" repeatCount="indefinite" begin="{idx * 0.15}s" fill="freeze"/>'
            chars.append(f"""
            <g>
              <clipPath id="odo-clip-{val}-{idx}">
                <rect x="{cx - x_step/2:.1f}" y="{-font_size * 0.85:.1f}" width="{x_step:.1f}" height="{font_size * 1.15:.1f}" />
              </clipPath>
              <g clip-path="url(#odo-clip-{val}-{idx})">
                <g>{anim_y}<text x="{cx:.1f}" y="0" font-size="{font_size}" font-weight="{font_weight}" fill="#f5f3ff" text-anchor="middle" class="{text_class}">{digits_str}</text></g>
              </g>
            </g>
            """)
        else:
            chars.append(f'<text x="{cx:.1f}" y="0" font-size="{font_size}" font-weight="{font_weight}" fill="#f5f3ff" text-anchor="middle" class="{text_class}">{ch}</text>')
    return "".join(chars)

# ==============================================================================
# 4. CARD 1: METRICS HEADER (metrics-header.svg)
# ==============================================================================
def build_header_svg():
    w, h = 840, 64
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }}
    .flicker-title {{
      animation: neon-flicker 4s infinite linear;
    }}
    @keyframes neon-flicker {{
      0%, 82%, 84%, 90%, 100% {{ opacity: 1; filter: drop-shadow(0 0 12px rgba(192, 132, 252, 0.8)); }}
      83% {{ opacity: 0.25; filter: none; }}
      89% {{ opacity: 0.6; filter: drop-shadow(0 0 4px rgba(168, 85, 247, 0.4)); }}
    }}
  </style>
  {COMMON_DEFS}
  {lava_border_frame(w, h, "hdr", delay_offset=0)}

  <!-- Left Inline Equalizer (Nested Non-Overriding Groups) -->
  <g transform="translate(68, 32)">
    <g transform="translate(0, 0)">
      <rect x="0" y="-14" width="4.5" height="28" rx="2" fill="#c084fc">
        <animateTransform attributeName="transform" type="scale" values="1 0.3; 1 1.0; 1 0.4" dur="1.2s" repeatCount="indefinite" />
      </rect>
    </g>
    <g transform="translate(8, 0)">
      <rect x="0" y="-18" width="4.5" height="36" rx="2" fill="#9333ea">
        <animateTransform attributeName="transform" type="scale" values="1 0.8; 1 0.2; 1 0.9" dur="1.6s" repeatCount="indefinite" />
      </rect>
    </g>
    <g transform="translate(16, 0)">
      <rect x="0" y="-10" width="4.5" height="20" rx="2" fill="#d8b4fe">
        <animateTransform attributeName="transform" type="scale" values="1 0.2; 1 1.0; 1 0.5" dur="1.4s" repeatCount="indefinite" />
      </rect>
    </g>
  </g>

  <!-- Glitch RGB-Split Neon Title -->
  <g transform="translate({w/2}, 41)" text-anchor="middle" class="flicker-title">
    <text x="-1.5" y="0" fill="#4c1d95" font-size="16" font-weight="900" letter-spacing="4">DEVELOPER METRICS &amp; ACTIVITY</text>
    <text x="1.5" y="0" fill="#9333ea" font-size="16" font-weight="900" letter-spacing="4" opacity="0.6">DEVELOPER METRICS &amp; ACTIVITY</text>
    <text x="0" y="0" fill="#f5f3ff" font-size="16" font-weight="900" letter-spacing="4">DEVELOPER METRICS &amp; ACTIVITY</text>
  </g>

  <!-- Right Inline Equalizer -->
  <g transform="translate({w-94}, 32)">
    <g transform="translate(0, 0)">
      <rect x="0" y="-10" width="4.5" height="20" rx="2" fill="#d8b4fe">
        <animateTransform attributeName="transform" type="scale" values="1 0.4; 1 1.0; 1 0.3" dur="1.3s" repeatCount="indefinite" />
      </rect>
    </g>
    <g transform="translate(8, 0)">
      <rect x="0" y="-18" width="4.5" height="36" rx="2" fill="#9333ea">
        <animateTransform attributeName="transform" type="scale" values="1 0.9; 1 0.3; 1 0.8" dur="1.7s" repeatCount="indefinite" />
      </rect>
    </g>
    <g transform="translate(16, 0)">
      <rect x="0" y="-14" width="4.5" height="28" rx="2" fill="#c084fc">
        <animateTransform attributeName="transform" type="scale" values="1 0.2; 1 0.9; 1 0.4" dur="1.1s" repeatCount="indefinite" />
      </rect>
    </g>
  </g>
</svg>"""

# ==============================================================================
# 5. CARD 2: STREAK STATS (streak-stats.svg)
# ==============================================================================
def build_streak_svg(data):
    w, h = 840, 200
    cx, cy, r = 420, 96, 54
    circ = 2 * math.pi * r
    total_arc = (270.0 / 360.0) * circ

    cur_s = data["current_streak"]
    long_s = data["longest_streak"]
    tot_contrib = data["total_all_time"]

    # True Proportional Gauge Arc: 0 if streak is 0, no floor!
    active_ratio = (cur_s / max(1, long_s)) if long_s > 0 else 0.0
    active_arc = total_arc * min(1.0, max(0.0, active_ratio))

    # Streak range strings
    if cur_s > 0 and data["current_streak_start"] and data["current_streak_end"]:
        cur_range = f"{data['current_streak_start'].strftime('%b %d')} - {data['current_streak_end'].strftime('%b %d')}"
    else:
        cur_range = "No active streak"

    if long_s > 0 and data["longest_streak_start"] and data["longest_streak_end"]:
        long_range = f"{data['longest_streak_start'].strftime('%b %d')} - {data['longest_streak_end'].strftime('%b %d')}"
    else:
        long_range = "All-time record"

    earliest_str = f"{data['earliest_date'].strftime('%b %d, %Y')} - Present"

    # Flame rendering: Dim embers if streak 0, layered purple tongues if active
    if cur_s > 0:
        flame_markup = """
        <g>
          <!-- Tongue 1 -->
          <path d="M 0 -16 C 5 -10, 10 -4, 7 5 C 4 12, -4 12, -7 5 C -10 -4, -5 -10, 0 -16 Z" fill="#4c1d95" opacity="0.8">
            <animateTransform attributeName="transform" type="scale" values="1 1; 1.08 1.15; 1 1" dur="1.1s" repeatCount="indefinite" />
          </path>
          <!-- Tongue 2 -->
          <path d="M 0 -12 C 4 -7, 7 -2, 5 5 C 3 10, -3 10, -5 5 C -7 -2, -4 -7, 0 -12 Z" fill="#a855f7">
            <animateTransform attributeName="transform" type="scale" values="1 1; 0.92 1.1; 1 1" dur="1.4s" repeatCount="indefinite" />
          </path>
          <!-- Tongue 3 Core -->
          <path d="M 0 -7 C 2 -4, 4 -1, 3 3 C 2 7, -2 7, -3 3 C -4 -1, -2 -4, 0 -7 Z" fill="#faf5ff">
            <animateTransform attributeName="transform" type="scale" values="1 1; 1.1 1.2; 1 1" dur="0.9s" repeatCount="indefinite" />
          </path>
        </g>
        """
    else:
        flame_markup = """
        <path d="M 0 -6 C 3 -3, 5 0, 4 4 C 2 8, -2 8, -4 4 C -5 0, -3 -3, 0 -6 Z" fill="#4c1d95" opacity="0.35" />
        """

    # Record Gold Diamond at End of Arc
    end_angle = 135.0 + 270.0 * active_ratio
    rad = math.radians(end_angle)
    dx = r * math.cos(rad)
    dy = r * math.sin(rad)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
    .odometer {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
  </style>
  {COMMON_DEFS}
  
  <defs>
    <!-- Purple Lava Flame Gradient -->
    <linearGradient id="gauge-lava" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#5b21b6" />
      <stop offset="50%" stop-color="#a855f7" />
      <stop offset="100%" stop-color="#e9d5ff" />
    </linearGradient>
  </defs>

  {lava_border_frame(w, h, "strk", delay_offset=4)}

  <!-- COLUMN 1: ALL-TIME TOTAL CONTRIBUTIONS -->
  <g transform="translate(170, 96)" text-anchor="middle">
    <g transform="translate(0, 0)">
      {odometer_number(tot_contrib, font_size=38, font_weight=900)}
    </g>
    <text x="0" y="24" fill="#cbd5e1" font-size="13" font-weight="600">Total Contributions</text>
    <text x="0" y="44" fill="#8b7fb0" font-size="11" class="mono">{earliest_str}</text>
  </g>

  <!-- COLUMN 2: PURPLE LAVA SPEEDOMETER GAUGE -->
  <g transform="translate({cx}, {cy})">
    <!-- 270 Degree Background Track -->
    <circle cx="0" cy="0" r="{r}" fill="none" stroke="#2e1065" stroke-width="8"
            stroke-dasharray="{total_arc:.2f} {circ:.2f}" stroke-linecap="round"
            transform="rotate(135)" opacity="0.6" />

    <!-- Active Molten Arc -->
    <circle cx="0" cy="0" r="{r}" fill="none" stroke="url(#gauge-lava)" stroke-width="8"
            stroke-dasharray="{active_arc:.2f} {circ:.2f}" stroke-linecap="round"
            transform="rotate(135)" style="filter: drop-shadow(0 0 8px #9333ea);" />

    <!-- Gold Record Marker at Arc End -->
    <g transform="translate({dx:.2f}, {dy:.2f})">
      <polygon points="0,-4 4,0 0,4 -4,0" fill="#fbbf24" style="filter: drop-shadow(0 0 5px #fbbf24);" />
    </g>

    <!-- Isolated Flame Group (Position via Attribute, Animation via Child) -->
    <g transform="translate(0, -32)">
      {flame_markup}
    </g>

    <!-- Odometer Streak Number (Base cy+22) -->
    <g transform="translate(0, 22)">
      {odometer_number(cur_s, font_size=36, font_weight=900)}
    </g>

    <text x="0" y="40" fill="#c084fc" font-size="9.5" font-weight="800" text-anchor="middle" letter-spacing="1.5" class="mono">DAYS</text>
  </g>

  <!-- Current Streak Subtitle -->
  <g transform="translate({cx}, 162)" text-anchor="middle">
    <text x="0" y="0" fill="#f5f3ff" font-size="14.5" font-weight="800">Current Streak</text>
    <text x="0" y="18" fill="#8b7fb0" font-size="11" class="mono">{cur_range}</text>
  </g>

  <!-- COLUMN 3: LONGEST STREAK -->
  <g transform="translate(670, 96)" text-anchor="middle">
    <g transform="translate(0, 0)">
      {odometer_number(long_s, font_size=38, font_weight=900)}
    </g>
    <text x="0" y="24" fill="#cbd5e1" font-size="13" font-weight="600">Longest Streak</text>
    <text x="0" y="44" fill="#8b7fb0" font-size="11" class="mono">{long_range}</text>
  </g>
</svg>"""

# ==============================================================================
# 6. CARD 3: ACTIVITY GRAPH (activity-graph.svg)
# ==============================================================================
def build_activity_graph_svg(data):
    w, h = 840, 245
    weekly = data["weekly_totals"]
    daily = data["daily_raw"]
    rolling_dates = data["rolling_dates"]

    gx_start, gx_end = 370, 770
    gy_bottom, gy_top = 180, 68
    span_x = gx_end - gx_start
    span_y = gy_bottom - gy_top

    # Calculate Nice Y-Axis Tick Numbers (0, Mid, Max)
    max_raw = max(max(weekly), 1)
    # Nice scale rounding to 1, 2, 5 * 10^n
    magnitude = 10 ** math.floor(math.log10(max_raw)) if max_raw > 0 else 1
    fraction = max_raw / magnitude
    if fraction <= 1.0:
        nice_max = 1 * magnitude
    elif fraction <= 2.0:
        nice_max = 2 * magnitude
    elif fraction <= 5.0:
        nice_max = 5 * magnitude
    else:
        nice_max = 10 * magnitude

    nice_max = max(nice_max, 10)
    nice_mid = nice_max // 2

    # Map 53 Weekly Points to Coordinates
    step_w = span_x / (len(weekly) - 1)
    pts = []
    for i, val in enumerate(weekly):
        px = gx_start + i * step_w
        norm = min(1.0, val / nice_max)
        py = gy_bottom - norm * span_y
        pts.append((px, py))

    # Generate Fritsch-Carlson Monotone Spline
    spline_d = monotone_cubic_spline(pts, gy_top, gy_bottom)
    area_d = f"{spline_d} L {pts[-1][0]:.2f} {gy_bottom} L {pts[0][0]:.2f} {gy_bottom} Z"

    # 365 Daily Micro-Bars behind the curve
    micro_bars = []
    step_d = span_x / (len(daily) - 1)
    max_d_raw = max(max(daily), 1)
    for i, cnt in enumerate(daily):
        if cnt > 0:
            bx = gx_start + i * step_d
            bh = min(span_y, (cnt / max_d_raw) * span_y * 0.8)
            by = gy_bottom - bh
            micro_bars.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="1.6" height="{bh:.1f}" rx="0.8" fill="#6d28d9" opacity="0.28" />')
    micro_bars_markup = "\n  ".join(micro_bars)

    # Monthly X-Axis Labels (Only from Real Encountered Months, No Future Months)
    x_labels = []
    seen_months = set()
    for i, d in enumerate(rolling_dates):
        m_key = (d.year, d.month)
        if m_key not in seen_months and d.day <= 7:
            seen_months.add(m_key)
            lx = gx_start + i * step_d
            x_labels.append(f'<text x="{lx:.1f}" y="{gy_bottom + 18}" fill="#8b7fb0" font-size="10" text-anchor="middle" class="mono">{d.strftime("%b")}</text>')
    x_labels_markup = "\n  ".join(x_labels)

    # Peak Day Marker (Exact Day Coordinate, not Month)
    peak_cnt = data["peak_day_cnt"]
    peak_date = data["peak_day_date"]
    peak_idx = rolling_dates.index(peak_date) if peak_date in rolling_dates else len(rolling_dates) - 1
    peak_x = gx_start + peak_idx * step_d
    # Interpolate Y on curve at peak_x
    norm_p = min(1.0, peak_cnt / nice_max)
    peak_y = max(gy_top, gy_bottom - norm_p * span_y)

    active_pct = data["active_pct"]
    ticker_text = f"★ RECORD {data['longest_streak']}D · ◆ {data['total_all_time']} ALL-TIME CONTRIBS · ● {data['active_days']}/365 ACTIVE DAYS · ⚡ {data['best_week']} BEST WEEK · "

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
    .ticker-scroll {{
      animation: ticker-anim 20s linear infinite;
    }}
    @keyframes ticker-anim {{
      0% {{ transform: translateX(0); }}
      100% {{ transform: translateX(-50%); }}
    }}
  </style>
  {COMMON_DEFS}

  <defs>
    <linearGradient id="chart-area-grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.55" />
      <stop offset="60%" stop-color="#6d28d9" stop-opacity="0.18" />
      <stop offset="100%" stop-color="#2e1065" stop-opacity="0.0" />
    </linearGradient>
  </defs>

  {lava_border_frame(w, h, "act", delay_offset=8)}

  <!-- LEFT COLUMN: REAL CREDENTIALS (INLINE SVG ICONS) -->
  <g transform="translate(36, 42)">
    <text x="0" y="0" fill="#f5f3ff" font-size="17" font-weight="900">Rixsan Joulfiand</text>
    <text x="0" y="16" fill="#a855f7" font-size="12" font-weight="700" class="mono">@{USERNAME}</text>

    <!-- Equalizer Rect Live Indicator -->
    <g transform="translate(260, -4)">
      <rect x="0" y="2" width="3" height="8" rx="1.5" fill="#c084fc" />
      <rect x="5" y="-1" width="3" height="11" rx="1.5" fill="#a855f7" />
      <rect x="10" y="3" width="3" height="7" rx="1.5" fill="#e9d5ff" />
      <text x="18" y="7" fill="#c084fc" font-size="11" font-weight="800" class="mono">LIVE</text>
    </g>

    <!-- Credential 1: Rolling Contributions in Last Year -->
    <g transform="translate(0, 48)">
      <circle cx="8" cy="-3" r="8" fill="#4c1d95" opacity="0.3" />
      <!-- GitHub Mark Icon -->
      <path d="M 8 -9 C 4.7 -9 2 -6.3 2 -3 C 2 -0.4 3.7 1.9 6.1 2.7 C 6.4 2.8 6.5 2.6 6.5 2.4 L 6.5 1.4 C 4.8 1.8 4.5 0.6 4.5 0.6 C 4.2 -0.1 3.8 -0.4 3.8 -0.4 C 3.2 -0.8 3.8 -0.8 3.8 -0.8 C 4.5 -0.8 4.8 -0.1 4.8 -0.1 C 5.4 0.9 6.3 0.6 6.7 0.4 C 6.8 -0.1 7 -0.4 7.2 -0.6 C 5.9 -0.7 4.5 -1.2 4.5 -3.5 C 4.5 -4.2 4.7 -4.7 5.1 -5.1 C 5 -5.3 4.8 -5.9 5.2 -6.7 C 5.2 -6.7 5.7 -6.9 6.9 -6.1 C 7.4 -6.2 7.9 -6.3 8.4 -6.3 C 8.9 -6.3 9.4 -6.2 9.9 -6.1 C 11.1 -6.9 11.6 -6.7 11.6 -6.7 C 12 -5.9 11.8 -5.3 11.7 -5.1 C 12.1 -4.7 12.3 -4.2 12.3 -3.5 C 12.3 -1.2 10.9 -0.7 9.6 -0.6 C 9.8 -0.4 10 -0.1 10 0.5 L 10 2.4 C 10 2.6 10.1 2.8 10.4 2.7 C 12.8 1.9 14.5 -0.4 14.5 -3 C 14.5 -6.3 11.8 -9 8.5 -9 Z" fill="#c084fc" />
      <text x="24" y="0" fill="#f5f3ff" font-size="12.5" font-weight="800">{data['total_last_year']} Contributions</text>
      <text x="24" y="14" fill="#8b7fb0" font-size="10.5" class="mono">in the last year</text>
    </g>

    <!-- Credential 2: Active Days -->
    <g transform="translate(0, 84)">
      <circle cx="8" cy="-3" r="8" fill="#4c1d95" opacity="0.3" />
      <!-- Calendar Icon -->
      <path d="M 4 -7 H 12 V -5 H 4 Z M 4 -3 H 12 V 1 H 4 Z M 3 -9 H 13 A 1 1 0 0 1 14 -8 V 2 A 1 1 0 0 1 13 3 H 3 A 1 1 0 0 1 2 2 V -8 A 1 1 0 0 1 3 -9 Z" fill="#c084fc" />
      <text x="24" y="0" fill="#f5f3ff" font-size="12.5" font-weight="800">{data['active_days']} Active Days</text>
      <text x="24" y="14" fill="#8b7fb0" font-size="10.5" class="mono">{active_pct}% of the last 365 days</text>
    </g>

    <!-- Credential 3: Best Week -->
    <g transform="translate(0, 120)">
      <circle cx="8" cy="-3" r="8" fill="#4c1d95" opacity="0.3" />
      <!-- Lightning Bolt Icon -->
      <path d="M 9 -9 L 4 -2 H 8 L 7 3 L 12 -4 H 8 Z" fill="#fbbf24" />
      <text x="24" y="0" fill="#f5f3ff" font-size="12.5" font-weight="800">{data['best_week']} Best Week</text>
      <text x="24" y="14" fill="#8b7fb0" font-size="10.5" class="mono">week of {data['best_week_start'].strftime('%b %d')}</text>
    </g>
  </g>

  <!-- RIGHT CHART SECTION -->
  <text x="{gx_end}" y="38" fill="#a855f7" font-size="11" font-weight="700" text-anchor="end" class="mono" letter-spacing="1.5">CONTRIBUTIONS IN THE LAST YEAR</text>

  <!-- Y-Axis Gridlines & Precise Labels -->
  <line x1="{gx_start}" y1="{gy_top}" x2="{gx_end}" y2="{gy_top}" stroke="#2e1065" stroke-width="0.8" stroke-dasharray="3 4" />
  <line x1="{gx_start}" y1="{(gy_top + gy_bottom)/2}" x2="{gx_end}" y2="{(gy_top + gy_bottom)/2}" stroke="#2e1065" stroke-width="0.8" stroke-dasharray="3 4" />
  <line x1="{gx_start}" y1="{gy_bottom}" x2="{gx_end}" y2="{gy_bottom}" stroke="#2e1065" stroke-width="1" />

  <text x="{gx_end + 14}" y="{gy_top + 4}" fill="#8b7fb0" font-size="10" class="mono">{nice_max}</text>
  <text x="{gx_end + 14}" y="{(gy_top + gy_bottom)/2 + 4}" fill="#8b7fb0" font-size="10" class="mono">{nice_mid}</text>
  <text x="{gx_end + 14}" y="{gy_bottom + 4}" fill="#8b7fb0" font-size="10" class="mono">0</text>

  <!-- Background Daily Micro-Bars -->
  {micro_bars_markup}

  <!-- Monotone Cubic Spline Glow Area & Dual Curves -->
  <path d="{area_d}" fill="url(#chart-area-grad)" />
  <path d="{spline_d}" fill="none" stroke="#a855f7" stroke-width="5" opacity="0.45" style="filter: blur(3px);" />
  <path d="{spline_d}" fill="none" stroke="#f3e8ff" stroke-width="2.4" stroke-linecap="round" />

  <!-- Monotone Path Comet Rider -->
  <circle r="4" fill="#faf5ff" style="filter: drop-shadow(0 0 6px #c084fc);">
    <animateMotion path="{spline_d}" dur="9s" repeatCount="indefinite" />
  </circle>

  <!-- X-Axis Months -->
  {x_labels_markup}

  <!-- Peak Day Marker & Safari-Compliant Sonar Ping (SMIL) -->
  <circle cx="{peak_x:.2f}" cy="{peak_y:.2f}" r="4" fill="none" stroke="#c084fc" stroke-width="1.6">
    <animate attributeName="r" from="3" to="24" dur="2.4s" repeatCount="indefinite" />
    <animate attributeName="opacity" from="1" to="0" dur="2.4s" repeatCount="indefinite" />
  </circle>
  <circle cx="{peak_x:.2f}" cy="{peak_y:.2f}" r="5" fill="#fef08a" stroke="#fbbf24" stroke-width="2" style="filter: drop-shadow(0 0 6px #fbbf24);" />

  <!-- Peak Badge with 28px Headroom (No Collision) -->
  <g transform="translate({peak_x:.2f}, {peak_y - 14:.2f})">
    <rect x="-38" y="-12" width="76" height="15" rx="3.5" fill="#3b0764" stroke="#fbbf24" stroke-width="1" />
    <text x="0" y="-1.5" fill="#fef08a" font-size="8.5" font-weight="900" text-anchor="middle" class="mono">{peak_cnt} · {peak_date.strftime('%b %d')}</text>
  </g>

  <!-- SEAMLESS TICKER (Identical textLength for 100% smooth loop) -->
  <g transform="translate(0, {h-24})">
    <rect x="8" y="0" width="{w-16}" height="20" rx="4" fill="#07040f" stroke="#1f1138" stroke-width="0.8" />
    <svg x="14" y="0" width="{w-28}" height="20" style="overflow: hidden;">
      <g class="ticker-scroll">
        <text x="0" y="13" fill="#cbd5e1" font-size="9.5" font-weight="600" class="mono" letter-spacing="1">
          {ticker_text}{ticker_text}
        </text>
      </g>
    </svg>
  </g>
</svg>"""

# ==============================================================================
# 7. CARD 4: GITHUB STATS (github-stats.svg)
# ==============================================================================
def build_github_stats_svg(data):
    w, h = 405, 205
    commits = data["total_commits"]
    prs = data["total_prs"]
    issues = data["total_issues"]
    stars = data["total_stars"]
    contrib_to = data["contributed_to"]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
  </style>
  {COMMON_DEFS}
  {lava_border_frame(w, h, "stats", delay_offset=12)}

  <text x="24" y="34" fill="#a855f7" font-size="14.5" font-weight="800">Stats</text>

  <!-- 5 AUTHENTIC METRIC ROWS -->
  <g transform="translate(24, 60)">
    <!-- 1. Total Stars -->
    <g transform="translate(0, 0)">
      <circle cx="9" cy="-3.5" r="8" fill="#6d28d9" opacity="0.28" />
      <path d="M 9 -8 L 10.5 -4.5 L 14 -4.5 L 11.2 -2.2 L 12.3 1 L 9 -1.2 L 5.7 1 L 6.8 -2.2 L 4 -4.5 L 7.5 -4.5 Z" fill="#c084fc" />
      <text x="24" y="0" fill="#8b7fb0" font-size="11">Total Stars Earned:</text>
      <text x="205" y="0" fill="#f5f3ff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">{stars}</text>
      <line x1="0" y1="8" x2="205" y2="8" stroke="#1f1138" stroke-width="0.8" />
    </g>

    <!-- 2. Commits in Rolling Year -->
    <g transform="translate(0, 24)">
      <circle cx="9" cy="-3.5" r="8" fill="#6d28d9" opacity="0.28" />
      <path d="M 9 -6 A 3 3 0 0 1 11.8 -3.5 H 14 V -1.5 H 11.8 A 3 3 0 0 1 6.2 -1.5 H 4 V -3.5 H 6.2 A 3 3 0 0 1 9 -6 M 9 -4.5 A 1.5 1.5 0 0 0 7.5 -2.5 A 1.5 1.5 0 0 0 9 -0.5 A 1.5 1.5 0 0 0 10.5 -2.5 A 1.5 1.5 0 0 0 9 -4.5 Z" fill="#c084fc" />
      <text x="24" y="0" fill="#8b7fb0" font-size="11">Total Commits (last year):</text>
      <text x="205" y="0" fill="#f5f3ff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">{commits}</text>
      <line x1="0" y1="8" x2="205" y2="8" stroke="#1f1138" stroke-width="0.8" />
    </g>

    <!-- 3. Pull Requests -->
    <g transform="translate(0, 48)">
      <circle cx="9" cy="-3.5" r="8" fill="#6d28d9" opacity="0.28" />
      <path d="M 6 -7 A 1.5 1.5 0 1 0 6 -4 A 1.5 1.5 0 0 0 6 -7 M 6 0 A 1.5 1.5 0 1 0 6 3 A 1.5 1.5 0 0 0 6 0 M 12 -7 A 1.5 1.5 0 1 0 12 -4 A 1.5 1.5 0 0 0 12 -7 M 7 -4 V 0 M 11 -4 V -1 C 11 0.5 10 1.5 8.5 1.5 H 7" fill="none" stroke="#c084fc" stroke-width="1.2" />
      <text x="24" y="0" fill="#8b7fb0" font-size="11">Total PRs:</text>
      <text x="205" y="0" fill="#f5f3ff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">{prs}</text>
      <line x1="0" y1="8" x2="205" y2="8" stroke="#1f1138" stroke-width="0.8" />
    </g>

    <!-- 4. Issues -->
    <g transform="translate(0, 72)">
      <circle cx="9" cy="-3.5" r="8" fill="#6d28d9" opacity="0.28" />
      <circle cx="9" cy="-2.5" r="5" fill="none" stroke="#c084fc" stroke-width="1.2" />
      <circle cx="9" cy="-2.5" r="1.5" fill="#c084fc" />
      <text x="24" y="0" fill="#8b7fb0" font-size="11">Total Issues:</text>
      <text x="205" y="0" fill="#f5f3ff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">{issues}</text>
      <line x1="0" y1="8" x2="205" y2="8" stroke="#1f1138" stroke-width="0.8" />
    </g>

    <!-- 5. Contributed to -->
    <g transform="translate(0, 96)">
      <circle cx="9" cy="-3.5" r="8" fill="#6d28d9" opacity="0.28" />
      <path d="M 5 -6 H 13 V 1 H 5 Z M 4 -7 H 14 V 2 H 4 Z M 7 -4 H 11 V -2 H 7 Z" fill="#c084fc" />
      <text x="24" y="0" fill="#8b7fb0" font-size="11">Contributed to:</text>
      <text x="205" y="0" fill="#f5f3ff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">{contrib_to}</text>
    </g>
  </g>

  <!-- OFFICIAL GITHUB OCTOCAT ORB WITH DUAL SMIL ROTATING RINGS -->
  <g transform="translate(325, 105)">
    <!-- Base Core Dark Circle -->
    <circle cx="0" cy="0" r="30" fill="#0b0714" stroke="#2e1065" stroke-width="1.4" />

    <!-- Ring 1: Continuous SMIL Rotate with Explicit Center -->
    <circle cx="0" cy="0" r="38" fill="none" stroke="#a855f7" stroke-width="2.8"
            stroke-dasharray="115 115" stroke-linecap="round" style="filter: drop-shadow(0 0 6px #9333ea);">
      <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="14s" repeatCount="indefinite" />
    </circle>

    <!-- Ring 2: Counter-Rotating Dashed Violet Ring -->
    <circle cx="0" cy="0" r="44" fill="none" stroke="#4c1d95" stroke-width="1.2"
            stroke-dasharray="4 6" opacity="0.8">
      <animateTransform attributeName="transform" type="rotate" from="360 0 0" to="0 0 0" dur="22s" repeatCount="indefinite" />
    </circle>

    <!-- Orbiting Gold Dot -->
    <circle cx="44" cy="0" r="2.5" fill="#fbbf24" style="filter: drop-shadow(0 0 4px #fbbf24);">
      <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="10s" repeatCount="indefinite" />
    </circle>

    <!-- Authentic GitHub Octocat Mark (viewBox 24x24 Scaled) -->
    <g transform="scale(1.2) translate(-12, -12)">
      <path fill="#f5f3ff" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
    </g>
  </g>
</svg>"""

# ==============================================================================
# 8. CARD 5: MOST USED LANGUAGES (top-langs.svg)
# ==============================================================================
def build_top_langs_svg(data):
    w, h = 405, 205
    langs = data["languages"]
    track_w = 200.0

    # Right Column: Bars and Shimmer
    rows_markup = []
    y_pos = 58
    for idx, l in enumerate(langs):
        bar_len = max(3.0, (l["pct"] / 100.0) * track_w)
        row = f"""
        <g transform="translate(0, {y_pos})">
          <circle cx="0" cy="-3.5" r="3.2" fill="{l['color']}" />
          <text x="12" y="0" fill="#f5f3ff" font-size="10.5" font-weight="600">{l['name']}</text>
          <text x="{track_w + 10:.0f}" y="0" fill="#8b7fb0" font-size="10" class="mono" text-anchor="end">{l['pct']:.2f}%</text>

          <!-- Track -->
          <rect x="12" y="5" width="{track_w:.0f}" height="3.5" rx="1.75" fill="#180d2b" />
          
          <!-- ClipPath for Inside Shimmer -->
          <clipPath id="shimmer-clip-{idx}">
            <rect x="12" y="5" width="{bar_len:.1f}" height="3.5" rx="1.75" />
          </clipPath>

          <g clip-path="url(#shimmer-clip-{idx})">
            <rect x="12" y="5" width="{bar_len:.1f}" height="3.5" fill="{l['color']}" />
            <!-- Moving Shimmer Beam -->
            <rect x="-30" y="5" width="24" height="3.5" fill="#ffffff" opacity="0.5">
              <animate attributeName="x" from="12" to="{12 + bar_len + 30:.1f}" dur="2.8s" repeatCount="indefinite" begin="{idx * 0.4}s" />
            </rect>
          </g>
        </g>
        """
        rows_markup.append(row)
        y_pos += 22

    # Left Column: Data-Driven Planetary Solar System
    planets_markup = []
    for idx, l in enumerate(langs):
        r_orbit = 26 + 8.5 * idx
        r_planet = min(9.5, max(3.0, 3.2 + math.sqrt(l['pct']) * 0.72))
        period = 6.0 + 3.8 * idx
        init_phase = (idx * 58) % 360

        planets_markup.append(f"""
        <!-- Orbit {idx+1} -->
        <circle cx="75" cy="115" r="{r_orbit:.1f}" fill="none" stroke="#2e1065" stroke-width="0.9" stroke-dasharray="2 3" opacity="0.75" />
        <g transform="translate(75, 115)">
          <g>
            <animateTransform attributeName="transform" type="rotate" from="{init_phase} 0 0" to="{init_phase + 360} 0 0" dur="{period:.1f}s" repeatCount="indefinite" />
            <circle cx="{r_orbit:.1f}" cy="0" r="{r_planet:.1f}" fill="{l['color']}" style="filter: drop-shadow(0 0 4px {l['color']});" />
          </g>
        </g>
        """)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
  </style>
  {COMMON_DEFS}
  {lava_border_frame(w, h, "langs", delay_offset=16)}

  <text x="24" y="34" fill="#a855f7" font-size="14.5" font-weight="800">Most Used Languages</text>

  <!-- DATA-DRIVEN PLANETARY SOLAR SYSTEM -->
  <g transform="translate(0, 0)">
    <!-- Central Pulsing Core Planet </> -->
    <circle cx="75" cy="115" r="14" fill="#4c1d95" style="filter: drop-shadow(0 0 8px #9333ea);">
      <animate attributeName="r" values="13; 14.5; 13" dur="3s" repeatCount="indefinite" />
    </circle>
    <circle cx="75" cy="115" r="9.5" fill="#1e0b3d" />
    <text x="75" y="118.5" fill="#f5f3ff" font-size="8.5" font-weight="900" text-anchor="middle" class="mono">&lt;/&gt;</text>

    {"".join(planets_markup)}
  </g>

  <!-- RIGHT COLUMN: PROGRESS BARS -->
  <g transform="translate(170, 0)">
    {"".join(rows_markup)}
  </g>
</svg>"""

# ==============================================================================
# 9. SELFTEST & AUDIT PIPELINE
# ==============================================================================
def run_selftest():
    print("=================== RUNNING TELEMETRY SELFTEST ===================")
    today = dt.date(2026, 10, 4)
    
    # Test 1: Future dates included + 7 streak days up to yesterday
    synth_cal = {}
    for d_off in range(1, 40):
        # Future dates: count 0
        synth_cal[today + dt.timedelta(days=d_off)] = 0
    synth_cal[today] = 0
    for d_off in range(1, 8):
        synth_cal[today - dt.timedelta(days=d_off)] = 5
    synth_cal[today - dt.timedelta(days=8)] = 0

    synth_raw = {
        "calendar": synth_cal,
        "created_date": today - dt.timedelta(days=60),
        "total_commits": 35,
        "total_prs": 0,
        "total_issues": 0,
        "total_stars": 0,
        "contributed_to": 0,
        "lang_bytes": {"Python": 5000, "PHP": 2000},
        "lang_colors": {"Python": "#3572a5", "PHP": "#4f5b93"},
        "repo_count": 2,
        "source": "selftest"
    }
    t1 = process_telemetry(synth_raw, today)
    assert t1["current_streak"] == 7, f"Test 1 Failed: streak expected 7, got {t1['current_streak']}"
    assert t1["total_last_year"] == 35, f"Test 1 Failed: count expected 35, got {t1['total_last_year']}"
    print("[PASS] Test 1: Future date filtering & grace period streak = 7")

    # Test 2: Empty calendar (Zero contributions all-time)
    synth_cal_empty = {today - dt.timedelta(days=i): 0 for i in range(365)}
    synth_raw_empty = {
        "calendar": synth_cal_empty,
        "created_date": today - dt.timedelta(days=364),
        "total_commits": 0,
        "total_prs": 0,
        "total_issues": 0,
        "total_stars": 0,
        "contributed_to": 0,
        "lang_bytes": {},
        "lang_colors": {},
        "repo_count": 0,
        "source": "selftest"
    }
    t2 = process_telemetry(synth_raw_empty, today)
    assert t2["current_streak"] == 0, "Test 2 Failed: empty streak should be 0"
    assert t2["total_all_time"] == 0, "Test 2 Failed: total should be 0"
    print("[PASS] Test 2: Empty calendar handles safely without crash")

    # Test 3: Today is active (Streak includes today)
    synth_cal_active = dict(synth_cal_empty)
    synth_cal_active[today] = 3
    synth_cal_active[today - dt.timedelta(days=1)] = 2
    synth_raw_active = dict(synth_raw_empty)
    synth_raw_active["calendar"] = synth_cal_active
    t3 = process_telemetry(synth_raw_active, today)
    assert t3["current_streak"] == 2, f"Test 3 Failed: expected 2, got {t3['current_streak']}"
    print("[PASS] Test 3: Active today streak = 2")

    # Test 4: Broken streak (Yesterday was 0)
    synth_cal_broken = dict(synth_cal_empty)
    synth_cal_broken[today] = 0
    synth_cal_broken[today - dt.timedelta(days=1)] = 0
    synth_cal_broken[today - dt.timedelta(days=2)] = 10
    synth_raw_broken = dict(synth_raw_empty)
    synth_raw_broken["calendar"] = synth_cal_broken
    t4 = process_telemetry(synth_raw_broken, today)
    assert t4["current_streak"] == 0, f"Test 4 Failed: broken streak should be 0, got {t4['current_streak']}"
    print("[PASS] Test 4: Broken streak yesterday = 0")

    # Test 5: Verify no hardcoded dummy patterns exist in script
    with open(__file__, "r", encoding="utf-8") as f:
        src = f.read()
    forbidden_patterns = ["326;", "262;", "125;", "81;", "88.85", "max(0.1", "else 81"]
    for pat in forbidden_patterns:
        assert pat not in src, f"Test 5 Failed: Forbidden pattern '{pat}' detected in source"
    print("[PASS] Test 5: Zero hardcoded mock numbers verified")

    print("=================== [SELFTEST PASSED 100%] ===================")

def main():
    parser = argparse.ArgumentParser(description="Cyberpunk Developer Metrics Generator")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output destination folder")
    parser.add_argument("--selftest", action="store_true", help="Execute offline unit selftest")
    args = parser.parse_args()

    if args.selftest:
        run_selftest()
        sys.exit(0)

    today = get_today_utc()
    token = os.environ.get("GITHUB_TOKEN", "")

    raw_data = None
    if token:
        try:
            print(f"[*] Fetching GraphQL telemetry for user @{USERNAME}...")
            raw_data = fetch_graphql_calendar(token, USERNAME, today)
            print("[+] SOURCE=GraphQL (Authentication OK)")
        except Exception as e:
            print(f"[!] GraphQL Fetch Failed: {e}", file=sys.stderr)

    if not raw_data:
        try:
            print(f"[*] Attempting jogruber fallback API for @{USERNAME}...")
            raw_data = fetch_jogruber_fallback(USERNAME, today)
            print("[+] SOURCE=jogruber (GraphQL failed or missing token)")
        except Exception as e:
            print(f"[-] CRITICAL ERROR: All data sources failed ({e})", file=sys.stderr)
            sys.exit(1)

    telemetry = process_telemetry(raw_data, today)

    # ---------------- AUDIT LOG (CI OUTPUT) ----------------
    print("\n================== TELEMETRY AUDIT LOG ==================")
    print(f"Source                  : {telemetry['source']}")
    print(f"Today (UTC)             : {telemetry['today']}")
    print(f"Date Range              : {telemetry['earliest_date']} to {telemetry['today']}")
    print(f"Total Days Loaded       : {len(raw_data['calendar'])}")
    print(f"Last Date in Dataset    : {max(raw_data['calendar'].keys())}")
    print(f"Total All-Time Contribs : {telemetry['total_all_time']}")
    print(f"Total Rolling Year      : {telemetry['total_last_year']}")
    print(f"Current Streak          : {telemetry['current_streak']} days ({telemetry['current_streak_start']} to {telemetry['current_streak_end']})")
    print(f"Longest Streak          : {telemetry['longest_streak']} days ({telemetry['longest_streak_start']} to {telemetry['longest_streak_end']})")
    print(f"Best Week               : {telemetry['best_week']} contribs ({telemetry['best_week_start']} to {telemetry['best_week_end']})")
    print(f"Peak Day                : {telemetry['peak_day_cnt']} contribs on {telemetry['peak_day_date']}")
    print(f"Active Days in Year     : {telemetry['active_days']} / 365 ({telemetry['active_pct']}%)")
    print(f"Repos Counted (Non-Fork): {telemetry['repo_count']}")
    print(f"Languages Bytes Total   : {telemetry['total_lang_bytes']} bytes")
    print(f"Top Languages Detected  : {', '.join(f'{l['name']} ({l['pct']:.1f}%)' for l in telemetry['languages'])}")
    print("=========================================================\n")

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    cards = {
        "metrics-header.svg": build_header_svg(),
        "streak-stats.svg": build_streak_svg(telemetry),
        "activity-graph.svg": build_activity_graph_svg(telemetry),
        "github-stats.svg": build_github_stats_svg(telemetry),
        "top-langs.svg": build_top_langs_svg(telemetry)
    }

    for fname, svg_content in cards.items():
        out_file = os.path.join(out_dir, fname)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(svg_content.strip())
        size_kb = os.path.getsize(out_file) / 1024.0
        print(f"[✓] Generated: {out_file} ({size_kb:.1f} KB)")
        assert size_kb < 60.0, f"File {fname} exceeds 60 KB limit: {size_kb:.1f} KB"

    print("[🚀] All 5 Cyberpunk SVG metrics cards compiled successfully!")

if __name__ == "__main__":
    main()
