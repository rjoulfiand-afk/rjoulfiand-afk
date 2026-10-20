import argparse
import ast
import colorsys
import datetime as dt
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict

USERNAME = "rjoulfiand-afk"
DEFAULT_OUT = "dist"
LANG_COLOR_MODE = "full"

# Palet Fallback Harmonis jika API GitHub tidak mengembalikan warna bahasa
FALLBACK_LANG_PALETTE = [
    "#06b6d4",  # Electric Cyan
    "#8b5cf6",  # Indigo Violet
    "#10b981",  # Emerald Mint
    "#f59e0b",  # Amber Gold
    "#3b82f6",  # Royal Blue
    "#ec4899",  # Rose Pink
]


def get_today_utc():
    return dt.datetime.now(dt.timezone.utc).date()


def parse_iso_date(d_str):
    return dt.date.fromisoformat(d_str.split("T")[0])


def clip_future(cal_dict, today):
    """Filter tanggal masa depan secara deterministik."""
    return {d: cnt for d, cnt in cal_dict.items() if d <= today}


def http_json(url, headers=None, post_data=None):
    req = urllib.request.Request(
        url,
        headers=headers or {"User-Agent": "CyberTelemetry/Studio"},
        data=post_data,
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_graphql_calendar(token, user, today):
    headers = {
        "User-Agent": "CyberTelemetry/Studio",
        "Authorization": f"bearer {token}",
    }

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
    total_commits = u["contributionsCollection"]["totalCommitContributions"]
    total_prs = u["pullRequests"]["totalCount"]
    total_issues = u["issues"]["totalCount"]
    contributed_to = u["repositoriesContributedTo"]["totalCount"]

    cal_dict = {}
    cur_start = created_date
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

    while cur_start <= today:
        cur_end = min(cur_start + dt.timedelta(days=364), today)
        from_iso = cur_start.isoformat() + "T00:00:00Z"
        to_iso = cur_end.isoformat() + "T23:59:59Z"

        q_data = json.dumps({
            "query": cal_query,
            "variables": {"user": user, "from": from_iso, "to": to_iso},
        }).encode("utf-8")

        c_res = http_json("https://api.github.com/graphql", headers, q_data)
        weeks = c_res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for w in weeks:
            for d in w["contributionDays"]:
                day_date = parse_iso_date(d["date"])
                if day_date <= today:
                    cal_dict[day_date] = d["contributionCount"]

        cur_start = cur_end + dt.timedelta(days=1)

    cal_dict = clip_future(cal_dict, today)

    repos_query = """
    query($user: String!, $cursor: String) {
      user(login: $user) {
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, after: $cursor) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
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
            "variables": {"user": user, "cursor": cursor},
        }).encode("utf-8")
        r_res = http_json("https://api.github.com/graphql", headers, r_data)
        rep_data = r_res["data"]["user"]["repositories"]

        for repo in rep_data["nodes"]:
            repo_count += 1
            total_stars += repo["stargazerCount"]
            for edge in repo["languages"]["edges"]:
                lname = edge["node"]["name"]
                lcolor = edge["node"].get("color") or "#06b6d4"
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
        "total_commits": total_commits,
        "total_prs": total_prs,
        "total_issues": total_issues,
        "total_stars": total_stars,
        "contributed_to": contributed_to,
        "lang_bytes": lang_bytes,
        "lang_colors": lang_colors,
        "repo_count": repo_count,
        "source": "GraphQL",
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

    cal_dict = clip_future(cal_dict, today)
    created_date = min(cal_dict.keys()) if cal_dict else today

    # Hitung kontribusi 365 hari terakhir agar konsisten dengan label "(last year)"
    start_365 = today - dt.timedelta(days=364)
    rolling_commits = sum(cnt for dt_k, cnt in cal_dict.items() if dt_k >= start_365)

    repos_url = f"https://api.github.com/users/{user}/repos?per_page=100&type=owner"
    repos = http_json(repos_url)
    total_stars = sum(r.get("stargazers_count", 0) for r in repos if not r.get("fork"))
    lang_bytes = defaultdict(int)
    lang_colors = {}
    repo_count = len([r for r in repos if not r.get("fork")])

    for idx, r in enumerate(repos):
        if not r.get("fork") and r.get("language"):
            lname = r["language"]
            lang_bytes[lname] += 1000
            if lname not in lang_colors:
                lang_colors[lname] = FALLBACK_LANG_PALETTE[len(lang_colors) % len(FALLBACK_LANG_PALETTE)]

    return {
        "calendar": cal_dict,
        "created_date": created_date,
        "total_commits": rolling_commits,
        "total_prs": 0,
        "total_issues": 0,
        "total_stars": total_stars,
        "contributed_to": 0,
        "lang_bytes": lang_bytes,
        "lang_colors": lang_colors,
        "repo_count": repo_count,
        "source": "jogruber",
    }


def process_telemetry(raw_data, today):
    cal_dict = clip_future(raw_data["calendar"], today)
    assert cal_dict, "Calendar dataset cannot be empty"
    assert max(cal_dict.keys()) <= today, f"Future dates detected: max={max(cal_dict.keys())} > today={today}"

    sorted_dates = sorted(cal_dict.keys())
    earliest_date = sorted_dates[0]
    total_all_time = sum(cal_dict.values())

    start_365 = today - dt.timedelta(days=364)
    rolling_365_days = []
    curr = start_365
    while curr <= today:
        rolling_365_days.append((curr, cal_dict.get(curr, 0)))
        curr += dt.timedelta(days=1)

    total_last_year = sum(cnt for _, cnt in rolling_365_days)
    active_days = sum(1 for _, cnt in rolling_365_days if cnt > 0)
    active_pct = round((active_days / 365.0) * 100.0)

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
        cur_streak_end = yesterday
        chk = yesterday
        while chk in cal_dict and cal_dict[chk] > 0:
            cur_streak += 1
            cur_streak_start = chk
            chk -= dt.timedelta(days=1)

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

    weekly_buckets = []
    weekly_date_ranges = []
    for k in range(52):
        w_end = today - dt.timedelta(days=7 * k)
        w_start = w_end - dt.timedelta(days=6)
        w_sum = sum(cal_dict.get(w_start + dt.timedelta(days=d_off), 0) for d_off in range(7))
        weekly_buckets.append(w_sum)
        weekly_date_ranges.append((w_start, w_end))

    weekly_buckets.reverse()
    weekly_date_ranges.reverse()

    best_week = max(weekly_buckets)
    best_week_idx = weekly_buckets.index(best_week)
    best_week_start, best_week_end = weekly_date_ranges[best_week_idx]

    last_7_days_sum = sum(cal_dict.get(today - dt.timedelta(days=i), 0) for i in range(7))
    assert weekly_buckets[-1] == last_7_days_sum, f"Invarian gagal: {weekly_buckets[-1]} != {last_7_days_sum}"

    peak_day_cnt = 0
    peak_day_date = today
    for d, cnt in rolling_365_days:
        if cnt >= peak_day_cnt:
            peak_day_cnt = cnt
            peak_day_date = d

    moving_avg_4w = []
    for i in range(len(weekly_buckets)):
        chunk = weekly_buckets[max(0, i - 3):i + 1]
        moving_avg_4w.append(sum(chunk) / len(chunk))

    exclude_env = os.environ.get("EXCLUDE_LANGS", "")
    excluded = {x.strip().lower() for x in exclude_env.split(",") if x.strip()}

    lang_bytes = raw_data["lang_bytes"]
    lang_colors = raw_data["lang_colors"]
    filtered_langs = {k: v for k, v in lang_bytes.items() if k.lower() not in excluded}
    total_l_bytes = sum(filtered_langs.values())

    langs_list = []
    if total_l_bytes > 0:
        sorted_l = sorted(filtered_langs.items(), key=lambda x: x[1], reverse=True)
        top5 = sorted_l[:5]
        top5_sum = sum(v for _, v in top5)

        for idx, (name, b_cnt) in enumerate(top5):
            pct = (b_cnt / total_l_bytes) * 100.0
            default_col = FALLBACK_LANG_PALETTE[idx % len(FALLBACK_LANG_PALETTE)]
            langs_list.append({
                "name": name,
                "pct": pct,
                "color": lang_colors.get(name, default_col),
            })

        if len(sorted_l) > 5:
            other_pct = ((total_l_bytes - top5_sum) / total_l_bytes) * 100.0
            if other_pct > 0.01:
                langs_list.append({
                    "name": "Other",
                    "pct": other_pct,
                    "color": "#64748b",
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
        "best_week": best_week,
        "best_week_idx": best_week_idx,
        "best_week_start": best_week_start,
        "best_week_end": best_week_end,
        "peak_day_cnt": peak_day_cnt,
        "peak_day_date": peak_day_date,
        "weekly_totals": weekly_buckets,
        "moving_avg_4w": moving_avg_4w,
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
        "source": raw_data["source"],
    }


def monotone_cubic_spline(pts, y_top, y_bottom):
    n = len(pts)
    if n < 2:
        return ""
    x = [p[0] for p in pts]
    y = [p[1] for p in pts]

    d_x = [x[i + 1] - x[i] for i in range(n - 1)]
    m = [(y[i + 1] - y[i]) / d_x[i] if d_x[i] != 0 else 0 for i in range(n - 1)]

    d = [0.0] * n
    d[0] = m[0]
    d[-1] = m[-1]
    for i in range(1, n - 1):
        if m[i - 1] * m[i] <= 0:
            d[i] = 0.0
        else:
            d[i] = (m[i - 1] + m[i]) / 2.0

    for i in range(n - 1):
        if m[i] == 0:
            d[i] = 0.0
            d[i + 1] = 0.0
        else:
            alpha = d[i] / m[i]
            beta = d[i + 1] / m[i]
            dist_sq = alpha * alpha + beta * beta
            if dist_sq > 9.0:
                tau = 3.0 / math.sqrt(dist_sq)
                d[i] = tau * alpha * m[i]
                d[i + 1] = tau * beta * m[i]

    path_tokens = [f"M {x[0]:.2f} {y[0]:.2f}"]
    for i in range(n - 1):
        h = d_x[i]
        cp1x = x[i] + h / 3.0
        cp1y = y[i] + d[i] * h / 3.0
        cp2x = x[i + 1] - h / 3.0
        cp2y = y[i + 1] - d[i + 1] * h / 3.0

        cp1y = max(y_top, min(y_bottom, cp1y))
        cp2y = max(y_top, min(y_bottom, cp2y))
        path_tokens.append(f"C {cp1x:.2f} {cp1y:.2f}, {cp2x:.2f} {cp2y:.2f}, {x[i + 1]:.2f} {y[i + 1]:.2f}")

    return " ".join(path_tokens)


def rounded_rect_path(w, h, r, inset=1.5):
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


def common_card_defs(prefix, w, h):
    return f"""
  <defs>
    <linearGradient id="{prefix}_bg_surface" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#090d16" />
      <stop offset="52%" stop-color="#0d1322" />
      <stop offset="100%" stop-color="#070a12" />
    </linearGradient>

    <radialGradient id="{prefix}_ambient_cyan" cx="18%" cy="15%" r="65%">
      <stop offset="0%" stop-color="#06b6d4" stop-opacity="0.12" />
      <stop offset="60%" stop-color="#0f172a" stop-opacity="0.03" />
      <stop offset="100%" stop-color="#090d16" stop-opacity="0.0" />
    </radialGradient>

    <radialGradient id="{prefix}_ambient_violet" cx="85%" cy="85%" r="60%">
      <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.12" />
      <stop offset="65%" stop-color="#1e1b4b" stop-opacity="0.03" />
      <stop offset="100%" stop-color="#070a12" stop-opacity="0.0" />
    </radialGradient>

    <linearGradient id="{prefix}_inner_bezel" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.38" />
      <stop offset="45%" stop-color="#1e293b" stop-opacity="0.22" />
      <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0.35" />
    </linearGradient>

    <pattern id="{prefix}_dot_grid" width="20" height="20" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="0.75" fill="#334155" opacity="0.32" />
    </pattern>

    <clipPath id="{prefix}_clip_card">
      <rect width="{w}" height="{h}" rx="14" />
    </clipPath>

    <filter id="{prefix}_glow_filter" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2.4" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>
"""


def precision_border_frame(prefix, w, h, delay_offset=0, hero=False):
    rr_outer = rounded_rect_path(w, h, 14, inset=0.75)
    rr_inner = rounded_rect_path(w, h, 14, inset=1.75)
    beam_op = "0.85" if hero else "0.55"
    sec_beam = ""
    if hero:
        sec_beam = f"""
      <path d="{rr_inner}" fill="none" stroke="#f59e0b" stroke-width="1.6" stroke-linecap="round"
            stroke-dasharray="6 94" pathLength="100" opacity="0.75">
        <animate attributeName="stroke-dashoffset" from="0" to="-100" dur="18s" repeatCount="indefinite"
                 begin="-{delay_offset + 9}s" />
      </path>"""

    return f"""
    <!-- Base Obsidian Surface & Ambient Lighting -->
    <rect width="{w}" height="{h}" rx="14" fill="url(#{prefix}_bg_surface)" />
    <rect width="{w}" height="{h}" rx="14" fill="url(#{prefix}_ambient_cyan)" />
    <rect width="{w}" height="{h}" rx="14" fill="url(#{prefix}_ambient_violet)" />
    <rect width="{w}" height="{h}" rx="14" fill="url(#{prefix}_dot_grid)" />

    <!-- Top Specular Glass Reflection -->
    <line x1="24" y1="1.8" x2="{w - 24}" y2="1.8" stroke="#e2e8f0" stroke-opacity="0.16" stroke-width="1" />

    <!-- Dual-Bezel Frame (Safe for both GitHub Light Mode & Dark Mode) -->
    <path d="{rr_outer}" fill="none" stroke="#1e293b" stroke-width="1.5" />
    <path d="{rr_inner}" fill="none" stroke="url(#{prefix}_inner_bezel)" stroke-width="1.1" />

    <!-- Precision Telemetry Laser Beam -->
    <g>
      <path d="{rr_inner}" fill="none" stroke="#22d3ee" stroke-width="1.8" stroke-linecap="round"
            stroke-dasharray="12 88" pathLength="100" opacity="{beam_op}">
        <animate attributeName="stroke-dashoffset" from="0" to="-100" dur="18s" repeatCount="indefinite"
                 begin="-{delay_offset}s" />
      </path>
      <path d="{rr_inner}" fill="none" stroke="#a78bfa" stroke-width="1.4" stroke-linecap="round"
            stroke-dasharray="8 92" pathLength="100" opacity="0.55">
        <animate attributeName="stroke-dashoffset" from="-50" to="-150" dur="18s" repeatCount="indefinite"
                 begin="-{delay_offset}s" />
      </path>{sec_beam}
    </g>
    """


def build_header_svg():
    w, h = 840, 64
    prefix = "hdr"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-label="Developer Metrics &amp; Activity">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
  </style>
  {common_card_defs(prefix, w, h)}
  <defs>
    <linearGradient id="{prefix}_title_grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f8fafc" />
      <stop offset="50%" stop-color="#67e8f9" />
      <stop offset="100%" stop-color="#c4b5fd" />
    </linearGradient>
  </defs>
  {precision_border_frame(prefix, w, h, delay_offset=0, hero=False)}

  <!-- Left Telemetry Status Pill -->
  <g transform="translate(24, 21)">
    <rect x="0" y="0" width="118" height="22" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1" />
    <circle cx="13" cy="11" r="3.5" fill="#10b981">
      <animate attributeName="opacity" values="1;0.35;1" dur="2s" repeatCount="indefinite" />
    </circle>
    <text x="24" y="14.5" fill="#94a3b8" font-size="9.5" font-weight="700" letter-spacing="1" class="mono">TELEMETRY.OS</text>
  </g>

  <!-- Left Spectrum Bars -->
  <g transform="translate(162, 32)">
    <rect x="0" y="-10" width="3.5" height="20" rx="1.75" fill="#06b6d4">
      <animateTransform attributeName="transform" type="scale" values="1 0.35; 1 1.0; 1 0.35" dur="1.2s" repeatCount="indefinite" />
    </rect>
    <rect x="7" y="-14" width="3.5" height="28" rx="1.75" fill="#8b5cf6">
      <animateTransform attributeName="transform" type="scale" values="1 0.85; 1 0.3; 1 0.85" dur="1.5s" repeatCount="indefinite" />
    </rect>
    <rect x="14" y="-8" width="3.5" height="16" rx="1.75" fill="#10b981">
      <animateTransform attributeName="transform" type="scale" values="1 0.4; 1 0.95; 1 0.4" dur="1.1s" repeatCount="indefinite" />
    </rect>
  </g>

  <!-- Center Metallic Title -->
  <g transform="translate({w / 2:.0f}, 38)" text-anchor="middle">
    <text x="0" y="0" fill="url(#{prefix}_title_grad)" font-size="15.5" font-weight="900" letter-spacing="3.8">DEVELOPER METRICS &amp; ACTIVITY</text>
  </g>

  <!-- Right Spectrum Bars -->
  <g transform="translate(660, 32)">
    <rect x="0" y="-8" width="3.5" height="16" rx="1.75" fill="#10b981">
      <animateTransform attributeName="transform" type="scale" values="1 0.45; 1 0.95; 1 0.45" dur="1.1s" repeatCount="indefinite" />
    </rect>
    <rect x="7" y="-14" width="3.5" height="28" rx="1.75" fill="#8b5cf6">
      <animateTransform attributeName="transform" type="scale" values="1 0.3; 1 0.9; 1 0.3" dur="1.5s" repeatCount="indefinite" />
    </rect>
    <rect x="14" y="-10" width="3.5" height="20" rx="1.75" fill="#06b6d4">
      <animateTransform attributeName="transform" type="scale" values="1 0.95; 1 0.35; 1 0.95" dur="1.2s" repeatCount="indefinite" />
    </rect>
  </g>

  <!-- Right Sync Readout -->
  <g transform="translate(702, 21)">
    <rect x="0" y="0" width="114" height="22" rx="6" fill="#0f172a" stroke="#1e293b" stroke-width="1" />
    <text x="57" y="14.5" fill="#38bdf8" font-size="9.5" font-weight="700" text-anchor="middle" letter-spacing="1" class="mono">LIVE STREAM</text>
  </g>
</svg>"""


def build_streak_svg(data):
    w, h = 840, 200
    prefix = "strk"
    cx, cy, r = 420, 96, 54
    circ = 2 * math.pi * r
    total_arc = (270.0 / 360.0) * circ

    cur_s = data["current_streak"]
    long_s = data["longest_streak"]
    tot_contrib = data["total_all_time"]

    active_ratio = (cur_s / max(1, long_s)) if long_s > 0 else 0.0
    active_arc = total_arc * min(1.0, max(0.0, active_ratio))

    if cur_s > 0 and data["current_streak_start"] and data["current_streak_end"]:
        cur_range = f"{data['current_streak_start'].strftime('%b %d')} - {data['current_streak_end'].strftime('%b %d')}"
    else:
        cur_range = "No active streak"

    if long_s > 0 and data["longest_streak_start"] and data["longest_streak_end"]:
        long_range = f"{data['longest_streak_start'].strftime('%b %d')} - {data['longest_streak_end'].strftime('%b %d')}"
    else:
        long_range = "All-time record"

    earliest_str = f"{data['earliest_date'].strftime('%b %d, %Y')} - Present"

    if cur_s > 0:
        flame_markup = """
        <g>
          <path d="M 0 -17 C 6 -10, 11 -3, 7.5 5.5 C 4.5 12, -4.5 12, -7.5 5.5 C -11 -3, -6 -10, 0 -17 Z" fill="#f97316" opacity="0.88">
            <animateTransform attributeName="transform" type="scale" values="1 1; 1.08 1.14; 1 1" dur="1.1s" repeatCount="indefinite" />
          </path>
          <path d="M 0 -12.5 C 4.2 -7, 7.2 -2, 5.2 5 C 3 10, -3 10, -5.2 5 C -7.2 -2, -4.2 -7, 0 -12.5 Z" fill="#fbbf24">
            <animateTransform attributeName="transform" type="scale" values="1 1; 0.94 1.1; 1 1" dur="1.35s" repeatCount="indefinite" />
          </path>
          <path d="M 0 -7.5 C 2.2 -4, 4 -1, 3 3.2 C 2 7, -2 7, -3 3.2 C -4 -1, -2.2 -4, 0 -7.5 Z" fill="#fef3c7">
            <animateTransform attributeName="transform" type="scale" values="1 1; 1.1 1.18; 1 1" dur="0.9s" repeatCount="indefinite" />
          </path>
        </g>
        """
    else:
        flame_markup = """
        <path d="M 0 -7 C 3 -3, 5 0, 4 4 C 2 8, -2 8, -4 4 C -5 0, -3 -3, 0 -7 Z" fill="#475569" opacity="0.45" />
        """

    end_angle = 135.0 + 270.0 * min(1.0, max(0.0, active_ratio))
    rad = math.radians(end_angle)
    dx = r * math.cos(rad)
    dy = r * math.sin(rad)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-label="GitHub Streak Stats">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; font-variant-numeric: tabular-nums; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
  </style>
  {common_card_defs(prefix, w, h)}
  <defs>
    <linearGradient id="{prefix}_gauge_arc" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#06b6d4" />
      <stop offset="55%" stop-color="#10b981" />
      <stop offset="100%" stop-color="#f59e0b" />
    </linearGradient>
    <linearGradient id="{prefix}_div_grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" stop-opacity="0.0" />
      <stop offset="50%" stop-color="#334155" stop-opacity="0.85" />
      <stop offset="100%" stop-color="#1e293b" stop-opacity="0.0" />
    </linearGradient>
  </defs>

  {precision_border_frame(prefix, w, h, delay_offset=3, hero=True)}

  <!-- Vertical Structural Dividers -->
  <line x1="292" y1="24" x2="292" y2="176" stroke="url(#{prefix}_div_grad)" stroke-width="1.2" />
  <line x1="548" y1="24" x2="548" y2="176" stroke="url(#{prefix}_div_grad)" stroke-width="1.2" />

  <!-- Left Bento Panel: Total Contributions -->
  <g transform="translate(154, 88)" text-anchor="middle">
    <rect x="-86" y="-54" width="172" height="20" rx="5" fill="#0f172a" stroke="#1e293b" stroke-width="1" />
    <text x="0" y="-40.5" fill="#38bdf8" font-size="9.5" font-weight="800" letter-spacing="1.2" class="mono">ALL-TIME VOLUME</text>
    <text x="0" y="6" fill="#f8fafc" font-size="38" font-weight="900" class="mono">{tot_contrib}</text>
    <text x="0" y="30" fill="#cbd5e1" font-size="13" font-weight="700">Total Contributions</text>
    <text x="0" y="50" fill="#64748b" font-size="11" class="mono">{earliest_str}</text>
  </g>

  <!-- Center Hero Dial: Current Streak -->
  <g transform="translate({cx}, {cy})">
    <!-- Outer Subtle Ring -->
    <circle cx="0" cy="0" r="64" fill="none" stroke="#1e293b" stroke-width="1" stroke-dasharray="3 5" />

    <!-- Gauge Track -->
    <circle cx="0" cy="0" r="{r}" fill="none" stroke="#1e293b" stroke-width="8.5"
            stroke-dasharray="{total_arc:.2f} {circ:.2f}" stroke-linecap="round"
            transform="rotate(135)" />

    <!-- Active Multi-Accent Progress Arc -->
    <circle cx="0" cy="0" r="{r}" fill="none" stroke="url(#{prefix}_gauge_arc)" stroke-width="8.5"
            stroke-dasharray="{active_arc:.2f} {circ:.2f}" stroke-linecap="round"
            transform="rotate(135)" filter="url(#{prefix}_glow_filter)" />

    <!-- Endpoint Pointer Diamond -->
    <g transform="translate({dx:.2f}, {dy:.2f})">
      <circle cx="0" cy="0" r="5" fill="#fbbf24" filter="url(#{prefix}_glow_filter)" />
      <circle cx="0" cy="0" r="2.5" fill="#ffffff" />
    </g>

    <!-- Animated Flame Icon -->
    <g transform="translate(0, -31)">
      {flame_markup}
    </g>

    <text x="0" y="21" fill="#f8fafc" font-size="35" font-weight="900" text-anchor="middle" class="mono">{cur_s}</text>
    <text x="0" y="40" fill="#10b981" font-size="9.5" font-weight="800" text-anchor="middle" letter-spacing="1.8" class="mono">STREAK DAYS</text>
  </g>

  <g transform="translate({cx}, 163)" text-anchor="middle">
    <text x="0" y="0" fill="#f8fafc" font-size="14" font-weight="800">Current Streak</text>
    <text x="0" y="17" fill="#94a3b8" font-size="11" class="mono">{cur_range}</text>
  </g>

  <!-- Right Bento Panel: Longest Streak -->
  <g transform="translate(686, 88)" text-anchor="middle">
    <rect x="-86" y="-54" width="172" height="20" rx="5" fill="#0f172a" stroke="#1e293b" stroke-width="1" />
    <text x="0" y="-40.5" fill="#fbbf24" font-size="9.5" font-weight="800" letter-spacing="1.2" class="mono">PEAK ENDURANCE</text>
    <text x="0" y="6" fill="#f8fafc" font-size="38" font-weight="900" class="mono">{long_s}</text>
    <text x="0" y="30" fill="#cbd5e1" font-size="13" font-weight="700">Longest Streak</text>
    <text x="0" y="50" fill="#64748b" font-size="11" class="mono">{long_range}</text>
  </g>
</svg>"""


def build_activity_graph_svg(data):
    w, h = 840, 260
    prefix = "act"
    weekly = data["weekly_totals"]
    daily = data["daily_raw"]
    rolling_dates = data["rolling_dates"]
    mavg = data["moving_avg_4w"]

    gx_start, gx_end = 356, 774
    gy_bottom, gy_top = 192, 74
    span_x = gx_end - gx_start
    span_y = gy_bottom - gy_top

    # Tambahkan headroom 22% agar titik puncak & badge tidak pernah menabrak header grafik
    max_raw = max(max(weekly), 1)
    target_max = max(max_raw * 1.22, 10.0)
    mag = 10 ** math.floor(math.log10(target_max)) if target_max > 0 else 1
    frac = target_max / mag
    if frac <= 1.2:
        nice_max = int(1.2 * mag)
    elif frac <= 2.0:
        nice_max = int(2 * mag)
    elif frac <= 3.0:
        nice_max = int(3 * mag)
    elif frac <= 5.0:
        nice_max = int(5 * mag)
    else:
        nice_max = int(10 * mag)

    nice_max = max(nice_max, 10)
    nice_mid = nice_max // 2
    nice_q1 = nice_max // 4
    nice_q3 = (nice_max * 3) // 4

    step_w = span_x / (len(weekly) - 1)
    pts = []
    for i, val in enumerate(weekly):
        px = gx_start + i * step_w
        norm = min(1.0, val / nice_max)
        py = gy_bottom - norm * span_y
        pts.append((px, py))

    spline_d = monotone_cubic_spline(pts, gy_top, gy_bottom)
    area_d = f"{spline_d} L {pts[-1][0]:.2f} {gy_bottom} L {pts[0][0]:.2f} {gy_bottom} Z"

    pts_mavg = []
    for i, val in enumerate(mavg):
        px = gx_start + i * step_w
        norm = min(1.0, val / nice_max)
        py = gy_bottom - norm * span_y
        pts_mavg.append((px, py))
    spline_mavg = monotone_cubic_spline(pts_mavg, gy_top, gy_bottom)

    # Daily Volume Impulse Bars
    micro_bars = []
    step_d = span_x / (len(daily) - 1)
    max_d_raw = max(max(daily), 1)
    peak_d_date = data["peak_day_date"]

    for i, cnt in enumerate(daily):
        if cnt > 0:
            bx = gx_start + i * step_d
            bh = min(span_y * 0.42, (cnt / max_d_raw) * span_y * 0.42)
            by = gy_bottom - bh
            if rolling_dates[i] == peak_d_date:
                micro_bars.append(
                    f'<rect x="{bx - 1.1:.1f}" y="{by:.1f}" width="2.2" height="{bh:.1f}" rx="1.1" fill="#fbbf24" opacity="0.92" />'
                )
            else:
                micro_bars.append(
                    f'<rect x="{bx - 0.8:.1f}" y="{by:.1f}" width="1.6" height="{bh:.1f}" rx="0.8" fill="#38bdf8" opacity="0.25" />'
                )
    micro_bars_markup = "\n  ".join(micro_bars)

    # Node Markers pada titik-titik belok signifikan (setiap 4 minggu + minggu aktif)
    node_dots = []
    for i, (px, py) in enumerate(pts):
        if weekly[i] > 0 and (i % 4 == 0 or i == len(pts) - 1):
            node_dots.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.1" fill="#090d16" stroke="#67e8f9" stroke-width="1.4" />'
            )
    node_dots_markup = "\n  ".join(node_dots)

    # Label Sumbu X (Bulan) & Garis Grid Vertikal
    month_spans = defaultdict(list)
    for i, d in enumerate(rolling_dates):
        m_key = (d.year, d.month)
        month_spans[m_key].append(gx_start + i * step_d)

    x_labels = []
    for (yr, mo), x_coords in month_spans.items():
        mid_x = (x_coords[0] + x_coords[-1]) / 2.0
        if gx_start + 12 <= mid_x <= gx_end - 12:
            m_name = dt.date(yr, mo, 1).strftime("%b")
            x_labels.append(
                f'<text x="{mid_x:.1f}" y="{gy_bottom + 17}" fill="#64748b" font-size="9.5" font-weight="600" text-anchor="middle" class="mono">{m_name}</text>'
            )
        x_labels.append(
            f'<line x1="{x_coords[-1]:.1f}" y1="{gy_top}" x2="{x_coords[-1]:.1f}" y2="{gy_bottom}" stroke="#1e293b" stroke-width="0.9" stroke-dasharray="2 3" />'
        )
    x_labels_markup = "\n  ".join(x_labels)

    best_w_idx = data["best_week_idx"]
    peak_x, peak_y = pts[best_w_idx]
    best_w_val = data["best_week"]
    best_w_range = f"{data['best_week_start'].strftime('%b %d')} - {data['best_week_end'].strftime('%b %d')}"

    # Clamping koordinat X & Y untuk Callout Badge agar anti-tabrakan di tepi kanvas
    badge_x = max(gx_start + 68.0, min(gx_end - 68.0, peak_x))
    badge_y = max(gy_top - 6.0, peak_y - 22.0)

    this_week_x0 = gx_start + (len(daily) - 7) * step_d
    this_week_w = gx_end - this_week_x0

    y_q1 = gy_bottom - 0.25 * span_y
    y_mid = (gy_top + gy_bottom) / 2.0
    y_q3 = gy_bottom - 0.75 * span_y

    ticker_text = (
        f"★ STREAK RECORD: {data['longest_streak']} DAYS   ·   "
        f"◆ ALL-TIME VOLUME: {data['total_all_time']} CONTRIBS   ·   "
        f"● CONSISTENCY: {data['active_days']}/365 ACTIVE DAYS ({data['active_pct']}%)   ·   "
        f"⚡ PEAK DAILY BURST: {data['peak_day_cnt']} ON {data['peak_day_date'].strftime('%b %d').upper()}   ·   "
    )
    single_copy_w = max(820, int(len(ticker_text) * 6.5))
    ticker_dur = max(22.0, single_copy_w / 38.0)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-label="Weekly Activity Velocity Graph">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; font-variant-numeric: tabular-nums; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
  </style>
  {common_card_defs(prefix, w, h)}
  <defs>
    <linearGradient id="{prefix}_chart_area" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#06b6d4" stop-opacity="0.44" />
      <stop offset="55%" stop-color="#3b82f6" stop-opacity="0.16" />
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0.0" />
    </linearGradient>

    <linearGradient id="{prefix}_line_grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="50%" stop-color="#22d3ee" />
      <stop offset="100%" stop-color="#a78bfa" />
    </linearGradient>

    <radialGradient id="{prefix}_peak_spot" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#f59e0b" stop-opacity="0.28" />
      <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.0" />
    </radialGradient>
  </defs>

  {precision_border_frame(prefix, w, h, delay_offset=6, hero=True)}

  <!-- Left Telemetry KPI Column -->
  <g transform="translate(26, 36)">
    <text x="0" y="0" fill="#f8fafc" font-size="16.5" font-weight="900">Rixsan Joulfiand</text>
    <text x="0" y="16" fill="#38bdf8" font-size="11.5" font-weight="700" class="mono">@{USERNAME}</text>

    <!-- Live Status Badge -->
    <g transform="translate(232, -12)">
      <rect x="0" y="0" width="66" height="20" rx="5" fill="#064e3b" fill-opacity="0.45" stroke="#10b981" stroke-opacity="0.5" stroke-width="1" />
      <circle cx="12" cy="10" r="3" fill="#10b981">
        <animate attributeName="opacity" values="1;0.3;1" dur="1.6s" repeatCount="indefinite" />
      </circle>
      <text x="21" y="13.5" fill="#34d399" font-size="9.5" font-weight="800" letter-spacing="0.8" class="mono">ONLINE</text>
    </g>

    <!-- KPI 1: Rolling Year Contributions (Cyan) -->
    <g transform="translate(0, 32)">
      <rect x="0" y="0" width="298" height="42" rx="8" fill="#0f172a" fill-opacity="0.75" stroke="#1e293b" stroke-width="1" />
      <rect x="10" y="9" width="24" height="24" rx="6" fill="#083344" stroke="#06b6d4" stroke-opacity="0.4" stroke-width="1" />
      <path d="M 17 21 L 20 17 L 23 20 L 27 15" fill="none" stroke="#22d3ee" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
      <circle cx="27" cy="15" r="1.5" fill="#67e8f9" />
      <text x="44" y="18" fill="#f8fafc" font-size="12.5" font-weight="800">{data['total_last_year']} Contributions</text>
      <text x="44" y="32" fill="#64748b" font-size="10" class="mono">rolling 365-day velocity</text>
    </g>

    <!-- KPI 2: Active Days Consistency (Emerald) -->
    <g transform="translate(0, 82)">
      <rect x="0" y="0" width="298" height="42" rx="8" fill="#0f172a" fill-opacity="0.75" stroke="#1e293b" stroke-width="1" />
      <rect x="10" y="9" width="24" height="24" rx="6" fill="#064e3b" stroke="#10b981" stroke-opacity="0.4" stroke-width="1" />
      <path d="M 16 21 L 20 25 L 28 17" fill="none" stroke="#34d399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      <text x="44" y="18" fill="#f8fafc" font-size="12.5" font-weight="800">{data['active_days']} Active Days</text>
      <text x="44" y="32" fill="#64748b" font-size="10" class="mono">{data['active_pct']}% consistency ratio</text>
    </g>

    <!-- KPI 3: Best Week Burst (Amber Gold) -->
    <g transform="translate(0, 132)">
      <rect x="0" y="0" width="298" height="42" rx="8" fill="#0f172a" fill-opacity="0.75" stroke="#1e293b" stroke-width="1" />
      <rect x="10" y="9" width="24" height="24" rx="6" fill="#451a03" stroke="#f59e0b" stroke-opacity="0.4" stroke-width="1" />
      <path d="M 23 14 L 18 21 H 22 L 21 28 L 26 21 H 22 Z" fill="#fbbf24" />
      <text x="44" y="18" fill="#f8fafc" font-size="12.5" font-weight="800">{data['best_week']} Peak Weekly Output</text>
      <text x="44" y="32" fill="#64748b" font-size="10" class="mono">week of {data['best_week_start'].strftime('%b %d')}</text>
    </g>
  </g>

  <!-- Right Chart Container Frame -->
  <rect x="{gx_start - 14}" y="24" width="{span_x + 56}" height="{gy_bottom - 24 + 28}" rx="10" fill="#070a12" fill-opacity="0.88" stroke="#1e293b" stroke-width="1.2" />

  <!-- Chart Title & Dual Legend Header -->
  <text x="{gx_start}" y="44" fill="#e2e8f0" font-size="10.5" font-weight="800" letter-spacing="1.2" class="mono">WEEKLY VELOCITY RIDGE</text>

  <g transform="translate({gx_end - 165}, 36)">
    <line x1="0" y1="4" x2="14" y2="4" stroke="#22d3ee" stroke-width="2.2" stroke-linecap="round" />
    <text x="19" y="7.5" fill="#94a3b8" font-size="9" font-weight="600" class="mono">WEEKLY</text>

    <line x1="72" y1="4" x2="86" y2="4" stroke="#a78bfa" stroke-width="1.5" stroke-dasharray="3 2" />
    <text x="91" y="7.5" fill="#94a3b8" font-size="9" font-weight="600" class="mono">4W AVG</text>

    <rect x="138" y="0" width="3.5" height="8" rx="1" fill="#fbbf24" />
    <text x="145" y="7.5" fill="#94a3b8" font-size="9" font-weight="600" class="mono">PEAK</text>
  </g>

  <!-- Cartesian Horizontal Gridlines & Right Y-Axis Labels -->
  <line x1="{gx_start}" y1="{gy_top}" x2="{gx_end}" y2="{gy_top}" stroke="#1e293b" stroke-width="0.9" stroke-dasharray="3 3" />
  <line x1="{gx_start}" y1="{y_q3:.1f}" x2="{gx_end}" y2="{y_q3:.1f}" stroke="#1e293b" stroke-width="0.6" stroke-dasharray="2 4" opacity="0.6" />
  <line x1="{gx_start}" y1="{y_mid:.1f}" x2="{gx_end}" y2="{y_mid:.1f}" stroke="#1e293b" stroke-width="0.9" stroke-dasharray="3 3" />
  <line x1="{gx_start}" y1="{y_q1:.1f}" x2="{gx_end}" y2="{y_q1:.1f}" stroke="#1e293b" stroke-width="0.6" stroke-dasharray="2 4" opacity="0.6" />
  <line x1="{gx_start}" y1="{gy_bottom}" x2="{gx_end}" y2="{gy_bottom}" stroke="#334155" stroke-width="1.1" />

  <text x="{gx_end + 10}" y="{gy_top + 3.5}" fill="#64748b" font-size="9.5" class="mono">{nice_max}</text>
  <text x="{gx_end + 10}" y="{y_q3 + 3.5:.1f}" fill="#475569" font-size="8.5" class="mono">{nice_q3}</text>
  <text x="{gx_end + 10}" y="{y_mid + 3.5:.1f}" fill="#64748b" font-size="9.5" class="mono">{nice_mid}</text>
  <text x="{gx_end + 10}" y="{y_q1 + 3.5:.1f}" fill="#475569" font-size="8.5" class="mono">{nice_q1}</text>
  <text x="{gx_end + 10}" y="{gy_bottom + 3.5}" fill="#64748b" font-size="9.5" class="mono">0</text>

  <!-- Active Week Highlight Band & Peak Floor Spotlight -->
  <rect x="{this_week_x0:.1f}" y="{gy_top}" width="{this_week_w:.1f}" height="{span_y}" fill="#06b6d4" opacity="0.07" />
  <ellipse cx="{peak_x:.1f}" cy="{gy_bottom}" rx="54" ry="18" fill="url(#{prefix}_peak_spot)" />

  <!-- Monthly Vertical Gridlines & Labels -->
  {x_labels_markup}

  <!-- Daily Impulse Bars -->
  {micro_bars_markup}

  <!-- Main Spline Area & Curves -->
  <path d="{area_d}" fill="url(#{prefix}_chart_area)" />
  <path d="{spline_mavg}" fill="none" stroke="#a78bfa" stroke-width="1.4" stroke-dasharray="4 3" opacity="0.85" />
  <path d="{spline_d}" fill="none" stroke="#06b6d4" stroke-width="4.5" opacity="0.28" filter="url(#{prefix}_glow_filter)" />
  <path d="{spline_d}" fill="none" stroke="url(#{prefix}_line_grad)" stroke-width="2.3" stroke-linecap="round" />

  <!-- Data Inflection Node Markers -->
  {node_dots_markup}

  <!-- Traveling Telemetry Photon -->
  <circle r="3.4" fill="#67e8f9" filter="url(#{prefix}_glow_filter)">
    <animateMotion path="{spline_d}" dur="10s" repeatCount="indefinite" />
  </circle>

  <!-- Peak Week Target Reticle & Clamped Callout Badge -->
  <line x1="{peak_x:.2f}" y1="{peak_y:.2f}" x2="{peak_x:.2f}" y2="{gy_bottom}" stroke="#f59e0b" stroke-width="0.9" stroke-dasharray="2 2" opacity="0.55" />
  <line x1="{peak_x:.2f}" y1="{peak_y:.2f}" x2="{badge_x:.2f}" y2="{badge_y + 4:.2f}" stroke="#fbbf24" stroke-width="1.1" opacity="0.85" />

  <circle cx="{peak_x:.2f}" cy="{peak_y:.2f}" r="4" fill="none" stroke="#fbbf24" stroke-width="1.5">
    <animate attributeName="r" from="3.5" to="18" dur="2.2s" repeatCount="indefinite" />
    <animate attributeName="opacity" from="0.95" to="0" dur="2.2s" repeatCount="indefinite" />
  </circle>
  <circle cx="{peak_x:.2f}" cy="{peak_y:.2f}" r="4" fill="#fbbf24" stroke="#090d16" stroke-width="1.4" />

  <g transform="translate({badge_x:.2f}, {badge_y:.2f})">
    <rect x="-66" y="-13" width="132" height="17" rx="4.5" fill="#0f172a" stroke="#f59e0b" stroke-width="1.1" />
    <text x="0" y="-1.5" fill="#fde68a" font-size="8.5" font-weight="800" text-anchor="middle" class="mono">★ {best_w_val} · {best_w_range}</text>
  </g>

  <!-- Current Week Live Node -->
  <circle cx="{pts[-1][0]:.2f}" cy="{pts[-1][1]:.2f}" r="3.2" fill="#10b981">
    <animate attributeName="r" values="2.8;5.5;2.8" dur="1.8s" repeatCount="indefinite" />
  </circle>

  <!-- Bottom Hardware Telemetry Ticker -->
  <g transform="translate(0, {h - 24})">
    <rect x="12" y="0" width="{w - 24}" height="19" rx="5" fill="#060911" stroke="#1e293b" stroke-width="0.9" />
    <svg x="20" y="0" width="{w - 40}" height="19" style="overflow: hidden;">
      <g>
        <animateTransform attributeName="transform" type="translate" from="0 0" to="-{single_copy_w} 0" dur="{ticker_dur:.1f}s" repeatCount="indefinite" />
        <text x="0" y="13" fill="#94a3b8" font-size="9.2" font-weight="600" class="mono" textLength="{single_copy_w}" lengthAdjust="spacing">
          {ticker_text}
        </text>
        <text x="{single_copy_w}" y="13" fill="#94a3b8" font-size="9.2" font-weight="600" class="mono" textLength="{single_copy_w}" lengthAdjust="spacing">
          {ticker_text}
        </text>
      </g>
    </svg>
  </g>
</svg>"""


def build_github_stats_svg(data):
    w, h = 405, 248
    prefix = "stats"
    commits = data["total_commits"]
    prs = data["total_prs"]
    issues = data["total_issues"]
    stars = data["total_stars"]
    contrib_to = data["contributed_to"]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-label="GitHub Core Statistics">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; font-variant-numeric: tabular-nums; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
  </style>
  {common_card_defs(prefix, w, h)}
  <defs>
    <linearGradient id="{prefix}_octo_arc" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#06b6d4" />
      <stop offset="55%" stop-color="#8b5cf6" />
      <stop offset="100%" stop-color="#10b981" />
    </linearGradient>

    <linearGradient id="{prefix}_tail_fade" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.85" />
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0.0" />
    </linearGradient>
  </defs>

  {precision_border_frame(prefix, w, h, delay_offset=9, hero=False)}

  <!-- Card Header -->
  <g transform="translate(22, 32)">
    <rect x="0" y="-11" width="3.5" height="14" rx="1.75" fill="#06b6d4" />
    <text x="10" y="0" fill="#f8fafc" font-size="14" font-weight="800" letter-spacing="0.4">System Telemetry &amp; Stats</text>
  </g>

  <!-- 5 Metric Rows -->
  <g transform="translate(22, 66)">
    <!-- Row 1: Stars (Amber Gold) -->
    <g transform="translate(0, 0)">
      <rect x="0" y="-14" width="218" height="24" rx="6" fill="#0f172a" fill-opacity="0.65" stroke="#1e293b" stroke-width="0.9" />
      <circle cx="14" cy="-2" r="7.5" fill="#451a03" />
      <path d="M 14 -6.5 L 15.4 -3.2 L 18.8 -3.2 L 16.1 -1.1 L 17.1 2.1 L 14 0.1 L 10.9 2.1 L 11.9 -1.1 L 9.2 -3.2 L 12.6 -3.2 Z" fill="#fbbf24" />
      <text x="28" y="1.5" fill="#cbd5e1" font-size="11" font-weight="500">Total Stars Earned</text>
      <text x="208" y="1.5" fill="#f8fafc" font-size="12" font-weight="800" text-anchor="end" class="mono">{stars}</text>
    </g>

    <!-- Row 2: Commits (Electric Cyan) -->
    <g transform="translate(0, 32)">
      <rect x="0" y="-14" width="218" height="24" rx="6" fill="#0f172a" fill-opacity="0.65" stroke="#1e293b" stroke-width="0.9" />
      <circle cx="14" cy="-2" r="7.5" fill="#083344" />
      <circle cx="14" cy="-2" r="3.2" fill="none" stroke="#22d3ee" stroke-width="1.6" />
      <line x1="8" y1="-2" x2="10.8" y2="-2" stroke="#22d3ee" stroke-width="1.5" />
      <line x1="17.2" y1="-2" x2="20" y2="-2" stroke="#22d3ee" stroke-width="1.5" />
      <text x="28" y="1.5" fill="#cbd5e1" font-size="11" font-weight="500">Commits (last year)</text>
      <text x="208" y="1.5" fill="#f8fafc" font-size="12" font-weight="800" text-anchor="end" class="mono">{commits}</text>
    </g>

    <!-- Row 3: PRs (Indigo Violet) -->
    <g transform="translate(0, 64)">
      <rect x="0" y="-14" width="218" height="24" rx="6" fill="#0f172a" fill-opacity="0.65" stroke="#1e293b" stroke-width="0.9" />
      <circle cx="14" cy="-2" r="7.5" fill="#2e1065" />
      <path d="M 11.5 -5.5 A 1.4 1.4 0 1 0 11.5 -2.7 A 1.4 1.4 0 0 0 11.5 -5.5 M 11.5 0.5 A 1.4 1.4 0 1 0 11.5 3.3 A 1.4 1.4 0 0 0 11.5 0.5 M 16.5 -5.5 A 1.4 1.4 0 1 0 16.5 -2.7 A 1.4 1.4 0 0 0 16.5 -5.5 M 12.2 -2.7 V 0.5 M 16.5 -2.7 V -0.5 C 16.5 0.8 15.5 1.8 14.2 1.8 H 12.8" fill="none" stroke="#c084fc" stroke-width="1.2" />
      <text x="28" y="1.5" fill="#cbd5e1" font-size="11" font-weight="500">Total Pull Requests</text>
      <text x="208" y="1.5" fill="#f8fafc" font-size="12" font-weight="800" text-anchor="end" class="mono">{prs}</text>
    </g>

    <!-- Row 4: Issues (Emerald Mint) -->
    <g transform="translate(0, 96)">
      <rect x="0" y="-14" width="218" height="24" rx="6" fill="#0f172a" fill-opacity="0.65" stroke="#1e293b" stroke-width="0.9" />
      <circle cx="14" cy="-2" r="7.5" fill="#064e3b" />
      <circle cx="14" cy="-2" r="4.5" fill="none" stroke="#34d399" stroke-width="1.3" />
      <circle cx="14" cy="-2" r="1.5" fill="#34d399" />
      <text x="28" y="1.5" fill="#cbd5e1" font-size="11" font-weight="500">Total Issues Reported</text>
      <text x="208" y="1.5" fill="#f8fafc" font-size="12" font-weight="800" text-anchor="end" class="mono">{issues}</text>
    </g>

    <!-- Row 5: Contributed To (Sky Blue) -->
    <g transform="translate(0, 128)">
      <rect x="0" y="-14" width="218" height="24" rx="6" fill="#0f172a" fill-opacity="0.65" stroke="#1e293b" stroke-width="0.9" />
      <circle cx="14" cy="-2" r="7.5" fill="#172554" />
      <path d="M 10.5 -5.5 H 17.5 V 1.5 H 10.5 Z M 12.5 -3.5 H 15.5 V -0.5 H 12.5 Z" fill="#60a5fa" />
      <text x="28" y="1.5" fill="#cbd5e1" font-size="11" font-weight="500">Repos Contributed To</text>
      <text x="208" y="1.5" fill="#f8fafc" font-size="12" font-weight="800" text-anchor="end" class="mono">{contrib_to}</text>
    </g>
  </g>

  <!-- Right Orbital Octocat Radar -->
  <g transform="translate(324, 136)">
    <circle cx="0" cy="0" r="52" fill="none" stroke="#1e293b" stroke-width="0.9" />
    <circle cx="0" cy="0" r="44" fill="none" stroke="#334155" stroke-width="1.1" stroke-dasharray="4 6">
      <animateTransform attributeName="transform" type="rotate" from="360 0 0" to="0 0 0" dur="22s" repeatCount="indefinite" />
    </circle>

    <circle cx="0" cy="0" r="37" fill="none" stroke="url(#{prefix}_octo_arc)" stroke-width="2.6"
            stroke-dasharray="28 72" pathLength="100" stroke-linecap="round" filter="url(#{prefix}_glow_filter)">
      <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="12s" repeatCount="indefinite" />
    </circle>

    <g>
      <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="9s" repeatCount="indefinite" />
      <path d="M 44 0 A 44 44 0 0 0 32 -30" fill="none" stroke="url(#{prefix}_tail_fade)" stroke-width="2" stroke-linecap="round" />
      <circle cx="44" cy="0" r="2.2" fill="#38bdf8" filter="url(#{prefix}_glow_filter)" />
    </g>

    <circle cx="0" cy="0" r="28" fill="#090d16" stroke="#1e293b" stroke-width="1.4" />

    <g transform="scale(1.18) translate(-12, -12)">
      <path fill="#f8fafc" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
    </g>
  </g>
</svg>"""


def build_top_langs_svg(data):
    w, h = 405, 248
    prefix = "langs"
    langs = data["languages"]

    spec_w = 361.0
    spec_segments = []
    seg_x = 22.0
    for idx, l in enumerate(langs):
        sw = max(3.0, (l["pct"] / 100.0) * (spec_w - max(0, len(langs) - 1) * 2.5))
        color = l["color"] if LANG_COLOR_MODE == "full" else FALLBACK_LANG_PALETTE[idx % len(FALLBACK_LANG_PALETTE)]
        spec_segments.append(f'<rect x="{seg_x:.1f}" y="46" width="{sw:.1f}" height="6" rx="2.5" fill="{color}" />')
        seg_x += sw + 2.5
    spec_markup = "\n  ".join(spec_segments)

    cx_orb, cy_orb = 90.0, 152.0
    planets_markup = []
    for idx, l in enumerate(langs[:6]):
        r_orbit = 20.0 + 9.4 * idx
        r_planet = min(8.5, max(2.8, 3.0 + math.sqrt(l["pct"]) * 0.65))
        period = 8.0 + 4.0 * idx
        init_phase = (idx * 62) % 360
        body_color = l["color"] if LANG_COLOR_MODE == "full" else FALLBACK_LANG_PALETTE[idx % len(FALLBACK_LANG_PALETTE)]

        planets_markup.append(f"""
        <!-- Orbit {idx + 1} Ring -->
        <circle cx="{cx_orb:.1f}" cy="{cy_orb:.1f}" r="{r_orbit:.1f}" fill="none" stroke="#1e293b" stroke-width="0.9" stroke-dasharray="2 3" />
        <g transform="translate({cx_orb:.1f}, {cy_orb:.1f})">
          <g>
            <animateTransform attributeName="transform" type="rotate" from="{init_phase} 0 0" to="{init_phase + 360} 0 0" dur="{period:.1f}s" repeatCount="indefinite" />
            <path d="M {r_orbit:.1f} 0 A {r_orbit:.1f} {r_orbit:.1f} 0 0 0 {r_orbit * 0.82:.1f} {-r_orbit * 0.57:.1f}" fill="none" stroke="{body_color}" stroke-width="1.4" opacity="0.45" stroke-linecap="round" />
            <circle cx="{r_orbit:.1f}" cy="0" r="{r_planet:.1f}" fill="{body_color}" />
            <circle cx="{r_orbit:.1f}" cy="0" r="{r_planet + 1.3:.1f}" fill="none" stroke="#f8fafc" stroke-width="0.7" opacity="0.45" />
          </g>
        </g>
        """)

    track_w = 158.0
    rows_markup = []
    y_pos = 84.0
    for idx, l in enumerate(langs[:6]):
        bar_len = max(4.0, (l["pct"] / 100.0) * track_w)
        rank_no = f"0{idx + 1}"
        l_col = l["color"]
        rank_bg = (
            f'<rect x="184" y="{y_pos - 13:.1f}" width="199" height="23" rx="5" fill="#0f172a" stroke="#1e293b" stroke-width="0.8" />'
            if idx == 0
            else ""
        )

        row = f"""
        {rank_bg}
        <g transform="translate(190, {y_pos:.1f})">
          <text x="0" y="0" fill="#64748b" font-size="9.5" font-weight="700" class="mono">{rank_no}</text>
          <circle cx="18" cy="-3.5" r="3.4" fill="{l_col}" />
          <text x="26" y="0" fill="#f8fafc" font-size="11.5" font-weight="600">{l['name']}</text>
          <text x="186" y="0" fill="#94a3b8" font-size="10" font-weight="700" class="mono" text-anchor="end">{l['pct']:.1f}%</text>

          <rect x="26" y="5" width="{track_w:.0f}" height="4.2" rx="2.1" fill="#0f172a" />

          <clipPath id="{prefix}_shimmer_clip_{idx}">
            <rect x="26" y="5" width="{bar_len:.1f}" height="4.2" rx="2.1" />
          </clipPath>

          <g clip-path="url(#{prefix}_shimmer_clip_{idx})">
            <rect x="26" y="5" width="{bar_len:.1f}" height="4.2" fill="{l_col}" />
            <rect x="-30" y="5" width="24" height="4.2" fill="#ffffff" opacity="0.38">
              <animate attributeName="x" from="26" to="{26 + bar_len + 30:.1f}" dur="3.2s" repeatCount="indefinite" begin="{idx * 0.35:.2f}s" />
            </rect>
          </g>
        </g>
        """
        rows_markup.append(row)
        y_pos += 25.5

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}" role="img" aria-label="Most Used Programming Languages">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; font-variant-numeric: tabular-nums; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
  </style>
  {common_card_defs(prefix, w, h)}

  {precision_border_frame(prefix, w, h, delay_offset=12, hero=False)}

  <!-- Card Header -->
  <g transform="translate(22, 32)">
    <rect x="0" y="-11" width="3.5" height="14" rx="1.75" fill="#8b5cf6" />
    <text x="10" y="0" fill="#f8fafc" font-size="14" font-weight="800" letter-spacing="0.4">Language Distribution</text>
  </g>

  <!-- Multi-Color Proportional Spectrum Bar -->
  {spec_markup}

  <!-- Left Orbital Language Telemetry -->
  <g>
    <circle cx="{cx_orb:.1f}" cy="{cy_orb:.1f}" r="14" fill="#083344" stroke="#06b6d4" stroke-width="1.2" filter="url(#{prefix}_glow_filter)">
      <animate attributeName="r" values="13; 14.5; 13" dur="3s" repeatCount="indefinite" />
    </circle>
    <circle cx="{cx_orb:.1f}" cy="{cy_orb:.1f}" r="9.5" fill="#090d16" />
    <text x="{cx_orb:.1f}" y="{cy_orb + 3.2:.1f}" fill="#38bdf8" font-size="8.5" font-weight="900" text-anchor="middle" class="mono">&lt;/&gt;</text>

    {"".join(planets_markup)}
  </g>

  <!-- Right Language Breakdown Rows -->
  {"".join(rows_markup)}
</svg>"""


def run_selftest():
    print("=================== RUNNING SELFTEST ===================")
    today = dt.date(2026, 10, 4)

    # Test 1: Future dates clipped + 7 streak days up to yesterday
    synth_cal = {}
    for d_off in range(1, 40):
        synth_cal[today + dt.timedelta(days=d_off)] = 0
    synth_cal[today] = 0
    for d_off in range(1, 8):
        synth_cal[today - dt.timedelta(days=d_off)] = 5
    synth_cal[today - dt.timedelta(days=8)] = 0

    synth_raw = {
        "calendar": clip_future(synth_cal, today),
        "created_date": today - dt.timedelta(days=60),
        "total_commits": 35,
        "total_prs": 0,
        "total_issues": 0,
        "total_stars": 0,
        "contributed_to": 0,
        "lang_bytes": {"Python": 5000, "PHP": 2000},
        "lang_colors": {"Python": "#3572a5", "PHP": "#4f5b93"},
        "repo_count": 2,
        "source": "selftest",
    }
    t1 = process_telemetry(synth_raw, today)
    assert t1["current_streak"] == 7, f"Test 1 Failed: streak expected 7, got {t1['current_streak']}"
    assert t1["total_last_year"] == 35, f"Test 1 Failed: count expected 35, got {t1['total_last_year']}"
    print("[PASS] Test 1: clip_future + grace period streak = 7")

    # Test 2: Invarian Mingguan
    last_7_sum = sum(synth_raw["calendar"].get(today - dt.timedelta(days=i), 0) for i in range(7))
    assert t1["weekly_totals"][-1] == last_7_sum, "Test 2 Failed: weekly[-1] invariant mismatch"
    assert max(t1["weekly_totals"]) == t1["best_week"], "Test 2 Failed: max(weekly) != best_week"
    print("[PASS] Test 2: Weekly bucket invariants verified")

    # Test 3: AST Inspection - Validasi nol konstanta mock di fungsi builder SVG
    forbidden_nums = {int(x) if "." not in x else float(x) for x in ["326", "262", "125", "81", "88.85"]}
    card_funcs = {
        "build_header_svg",
        "build_streak_svg",
        "build_activity_graph_svg",
        "build_github_stats_svg",
        "build_top_langs_svg",
    }
    with open(__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=__file__)

    for item in tree.body:
        if isinstance(item, ast.FunctionDef) and item.name in card_funcs:
            for node in ast.walk(item):
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    assert node.value not in forbidden_nums, (
                        f"Test 3 Failed: Hardcoded mock number {node.value} detected in function {item.name}"
                    )
    print("[PASS] Test 3: AST scan confirms zero mock constants in SVG card builders")

    # Test 4: Validasi XML, Dual-Bezel Contrast Surface & Ukuran di Bawah 60 KB
    test_cards = {
        "hdr": build_header_svg(),
        "strk": build_streak_svg(t1),
        "act": build_activity_graph_svg(t1),
        "stats": build_github_stats_svg(t1),
        "langs": build_top_langs_svg(t1),
    }

    for name, svg_code in test_cards.items():
        ET.fromstring(svg_code)
        size_kb = len(svg_code.encode("utf-8")) / 1024.0
        assert size_kb < 60.0, f"Card {name} exceeds 60 KB limit ({size_kb:.1f} KB)"
        assert "#090d16" in svg_code.lower(), f"Card {name} missing Obsidian base surface #090d16"
        assert "#1e293b" in svg_code.lower(), f"Card {name} missing Light/Dark structural bezel #1e293b"

    print("[PASS] Test 4: Multi-Accent Telemetry & Dual-Bezel Surface audit passed 100%")
    print("=================== [SELFTEST PASSED 100%] ===================")


def main():
    parser = argparse.ArgumentParser(description="Obsidian Titanium Developer Metrics Generator")
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

    lang_summary_items = [f"{l['name']} ({l['pct']:.1f}%)" for l in telemetry["languages"]]
    lang_summary_str = ", ".join(lang_summary_items)

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
    print(f"Top Languages Detected  : {lang_summary_str}")
    print("=========================================================\n")

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    cards = {
        "metrics-header.svg": build_header_svg(),
        "streak-stats.svg": build_streak_svg(telemetry),
        "activity-graph.svg": build_activity_graph_svg(telemetry),
        "github-stats.svg": build_github_stats_svg(telemetry),
        "top-langs.svg": build_top_langs_svg(telemetry),
    }

    for fname, svg_content in cards.items():
        out_file = os.path.join(out_dir, fname)
        ET.fromstring(svg_content)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(svg_content.strip())
        size_kb = os.path.getsize(out_file) / 1024.0
        print(f"[✓] Generated: {out_file} ({size_kb:.1f} KB)")
        assert size_kb < 60.0, f"File {fname} exceeds 60 KB limit: {size_kb:.1f} KB"

    print("[🚀] All 5 studio-grade metrics cards successfully generated and verified!")


if __name__ == "__main__":
    main()
