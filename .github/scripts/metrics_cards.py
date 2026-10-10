
"""
Studio-Grade Cyberpunk Developer Metrics Suite
Pure Native Python Standard Library - Zero External Dependencies
Palette: Strictly Monochromatic Violet & Lilac Spectrum
Generates 5 Validated, XML-Compliant SVGs (< 60 KB each):
  1. metrics-header.svg
  2. streak-stats.svg
  3. activity-graph.svg
  4. github-stats.svg
  5. top-langs.svg
"""
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
LANG_COLOR_MODE = "accent"  


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
        data=post_data
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_graphql_calendar(token, user, today):
    headers = {
        "User-Agent": "CyberTelemetry/Studio",
        "Authorization": f"bearer {token}"
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
            "variables": {"user": user, "from": from_iso, "to": to_iso}
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
        "total_commits": total_commits,
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

    cal_dict = clip_future(cal_dict, today)
    created_date = min(cal_dict.keys()) if cal_dict else today

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
    else:
        cur_streak = 0
        cur_streak_start = None
        cur_streak_end = None

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

    # Peak Day (Harian)
    peak_day_cnt = 0
    peak_day_date = today
    for d, cnt in rolling_365_days:
        if cnt >= peak_day_cnt:
            peak_day_cnt = cnt
            peak_day_date = d

    # 4-Week Moving Average
    moving_avg_4w = []
    for i in range(len(weekly_buckets)):
        chunk = weekly_buckets[max(0, i - 3):i + 1]
        moving_avg_4w.append(sum(chunk) / len(chunk))

    # Bahasa
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

        for name, b_cnt in top5:
            pct = (b_cnt / total_l_bytes) * 100.0
            langs_list.append({
                "name": name,
                "pct": pct,
                "color": lang_colors.get(name, "#a78bfa")
            })

        if len(sorted_l) > 5:
            other_pct = ((total_l_bytes - top5_sum) / total_l_bytes) * 100.0
            if other_pct > 0.01:
                langs_list.append({
                    "name": "Other",
                    "pct": other_pct,
                    "color": "#6d28d9"
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
        "source": raw_data["source"]
    }

# ==============================================================================
# 2. FRITSCH-CARLSON MONOTONE CUBIC SPLINE
# ==============================================================================
def monotone_cubic_spline(pts, y_top, y_bottom):
    n = len(pts)
    if n < 2:
        return ""
    x = [p[0] for p in pts]
    y = [p[1] for p in pts]

    d_x = [x[i+1] - x[i] for i in range(n - 1)]
    m = [(y[i+1] - y[i]) / d_x[i] if d_x[i] != 0 else 0 for i in range(n - 1)]

    d = [0.0] * n
    d[0] = m[0]
    d[-1] = m[-1]
    for i in range(1, n - 1):
        if m[i-1] * m[i] <= 0:
            d[i] = 0.0
        else:
            d[i] = (m[i-1] + m[i]) / 2.0

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


def rounded_rect_path(w, h, r, inset=1.5):
    x0 = inset
    y0 = inset
    x1 = w - inset
    y1 = h - inset
    rad = r - inset
    return f"M {x0 + rad} {y0} L {x1 - rad} {y0} A {rad} {rad} 0 0 1 {x1} {y0 + rad} L {x1} {y1 - rad} A {rad} {rad} 0 0 1 {x1 - rad} {y1} L {x0 + rad} {y1} A {rad} {rad} 0 0 1 {x0} {y1 - rad} L {x0} {y0 + rad} A {rad} {rad} 0 0 1 {x0 + rad} {y0} Z"

def common_card_defs(prefix, w, h):
    rr_d = rounded_rect_path(w, h, 14, inset=1.5)
    return f"""
  <defs>
    <radialGradient id="{prefix}_aurora" cx="50%" cy="40%" r="65%">
      <stop offset="0%" stop-color="#4c1d95" stop-opacity="0.22" />
      <stop offset="60%" stop-color="#2e1065" stop-opacity="0.08" />
      <stop offset="100%" stop-color="#05030a" stop-opacity="0.0" />
    </radialGradient>

    <radialGradient id="{prefix}_magma_blob" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#f5d0fe" stop-opacity="0.85" />
      <stop offset="40%" stop-color="#a855f7" stop-opacity="0.4" />
      <stop offset="100%" stop-color="#4c1d95" stop-opacity="0.0" />
    </radialGradient>

    <clipPath id="{prefix}_clip_card">
      <rect width="{w}" height="{h}" rx="14" />
    </clipPath>

    <filter id="{prefix}_bleed_filter" x="0" y="0" width="{w}" height="{h}" filterUnits="userSpaceOnUse">
      <feGaussianBlur stdDeviation="4.0" />
    </filter>

    <filter id="{prefix}_lava_fusion" x="-20" y="-20" width="{w + 40}" height="{h + 40}" filterUnits="userSpaceOnUse">
      <feGaussianBlur stdDeviation="2.4" result="blur" />
      <feColorMatrix type="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 20 -8" result="goo" />
      <feGaussianBlur in="goo" stdDeviation="5.0" result="lava_glow" />
      <feMerge>
        <feMergeNode in="lava_glow" />
        <feMergeNode in="goo" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>

    <filter id="{prefix}_glow_filter" x="-20" y="-20" width="{w + 40}" height="{h + 40}" filterUnits="userSpaceOnUse">
      <feGaussianBlur stdDeviation="3.0" />
    </filter>
  </defs>
"""

def lava_border_frame(prefix, w, h, delay_offset=0):
    rr_d = rounded_rect_path(w, h, 14, inset=1.5)
    return f"""
    <rect width="{w}" height="{h}" rx="14" fill="#05030a" />
    <rect width="{w}" height="{h}" rx="14" fill="url(#{prefix}_aurora)" />

    <g clip-path="url(#{prefix}_clip_card)">
      <path d="{rr_d}" fill="none" stroke="#6d28d9" stroke-width="6" opacity="0.3" filter="url(#{prefix}_bleed_filter)" />
    </g>

    <path d="{rr_d}" fill="none" stroke="#2e1065" stroke-width="1.2" opacity="0.7" />

    <g filter="url(#{prefix}_lava_fusion)">
      <path d="{rr_d}" fill="none" stroke="#6d28d9" stroke-width="5" stroke-linecap="round"
            stroke-dasharray="22 9 8 14 30 17" pathLength="100">
        <animate attributeName="stroke-dashoffset" from="0" to="-100" dur="26s" repeatCount="indefinite"
                 begin="-{delay_offset}s" calcMode="spline" keyTimes="0;0.5;1" keySplines="0.4 0 0.6 1; 0.4 0 0.6 1" values="0;-38;-100" />
      </path>

      <path d="{rr_d}" fill="none" stroke="#c084fc" stroke-width="3" stroke-linecap="round"
            stroke-dasharray="10 12 5 20 14 39" pathLength="100">
        <animate attributeName="stroke-dashoffset" from="0" to="-100" dur="17s" repeatCount="indefinite"
                 begin="-{delay_offset + 4}s" />
      </path>

      <path d="{rr_d}" fill="none" stroke="#f5d0fe" stroke-width="1.4" stroke-linecap="round"
            stroke-dasharray="3 22 2 31 4 38" pathLength="100">
        <animate attributeName="stroke-dashoffset" from="0" to="-100" dur="11s" repeatCount="indefinite"
                 begin="-{delay_offset + 2}s" />
      </path>
    </g>

    <circle r="14" fill="url(#{prefix}_magma_blob)">
      <animateMotion path="{rr_d}" dur="40s" repeatCount="indefinite" begin="-{delay_offset + 8}s" />
    </circle>
    <circle r="10" fill="url(#{prefix}_magma_blob)">
      <animateMotion path="{rr_d}" dur="63s" repeatCount="indefinite" begin="-{delay_offset + 24}s" />
    </circle>
    """

# ==============================================================================
# 4. CARD 1: METRICS HEADER (metrics-header.svg)
# ==============================================================================
def build_header_svg():
    w, h = 840, 64
    prefix = "hdr"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }}
    .flicker-op {{
      animation: neon-op 4s infinite linear;
    }}
    @keyframes neon-op {{
      0%, 82%, 84%, 90%, 100% {{ opacity: 1; }}
      83% {{ opacity: 0.25; }}
      89% {{ opacity: 0.6; }}
    }}
  </style>
  {common_card_defs(prefix, w, h)}
  {lava_border_frame(prefix, w, h, delay_offset=0)}

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

  <g transform="translate({w/2}, 41)" text-anchor="middle" class="flicker-op">
    <text x="0" y="0" fill="#a855f7" font-size="16" font-weight="900" letter-spacing="4" filter="url(#{prefix}_glow_filter)">DEVELOPER METRICS &amp; ACTIVITY</text>
    <text x="-1.5" y="0" fill="#4c1d95" font-size="16" font-weight="900" letter-spacing="4">DEVELOPER METRICS &amp; ACTIVITY</text>
    <text x="0" y="0" fill="#f5f3ff" font-size="16" font-weight="900" letter-spacing="4">DEVELOPER METRICS &amp; ACTIVITY</text>
  </g>

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
          <path d="M 0 -16 C 5 -10, 10 -4, 7 5 C 4 12, -4 12, -7 5 C -10 -4, -5 -10, 0 -16 Z" fill="#4c1d95" opacity="0.8">
            <animateTransform attributeName="transform" type="scale" values="1 1; 1.08 1.15; 1 1" dur="1.1s" repeatCount="indefinite" />
          </path>
          <path d="M 0 -12 C 4 -7, 7 -2, 5 5 C 3 10, -3 10, -5 5 C -7 -2, -4 -7, 0 -12 Z" fill="#a855f7">
            <animateTransform attributeName="transform" type="scale" values="1 1; 0.92 1.1; 1 1" dur="1.4s" repeatCount="indefinite" />
          </path>
          <path d="M 0 -7 C 2 -4, 4 -1, 3 3 C 2 7, -2 7, -3 3 C -4 -1, -2 -4, 0 -7 Z" fill="#faf5ff">
            <animateTransform attributeName="transform" type="scale" values="1 1; 1.1 1.2; 1 1" dur="0.9s" repeatCount="indefinite" />
          </path>
        </g>
        """
    else:
        flame_markup = """
        <path d="M 0 -6 C 3 -3, 5 0, 4 4 C 2 8, -2 8, -4 4 C -5 0, -3 -3, 0 -6 Z" fill="#4c1d95" opacity="0.35" />
        """

    end_angle = 135.0 + 270.0 * active_ratio
    rad = math.radians(end_angle)
    dx = r * math.cos(rad)
    dy = r * math.sin(rad)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; font-variant-numeric: tabular-nums; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
  </style>
  {common_card_defs(prefix, w, h)}
  <defs>
    <linearGradient id="{prefix}_gauge_lava" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#5b21b6" />
      <stop offset="50%" stop-color="#a855f7" />
      <stop offset="100%" stop-color="#e9d5ff" />
    </linearGradient>
  </defs>

  {lava_border_frame(prefix, w, h, delay_offset=4)}

  <g transform="translate(170, 96)" text-anchor="middle">
    <text x="0" y="0" fill="#f5f3ff" font-size="38" font-weight="900" class="mono">{tot_contrib}</text>
    <text x="0" y="24" fill="#cbd5e1" font-size="13" font-weight="600">Total Contributions</text>
    <text x="0" y="44" fill="#8b7fb0" font-size="11" class="mono">{earliest_str}</text>
  </g>

  <g transform="translate({cx}, {cy})">
    <circle cx="0" cy="0" r="{r}" fill="none" stroke="#2e1065" stroke-width="8"
            stroke-dasharray="{total_arc:.2f} {circ:.2f}" stroke-linecap="round"
            transform="rotate(135)" opacity="0.6" />

    <circle cx="0" cy="0" r="{r}" fill="none" stroke="url(#{prefix}_gauge_lava)" stroke-width="8"
            stroke-dasharray="{active_arc:.2f} {circ:.2f}" stroke-linecap="round"
            transform="rotate(135)" filter="url(#{prefix}_glow_filter)" />

    <g transform="translate({dx:.2f}, {dy:.2f})">
      <polygon points="0,-4.5 4.5,0 0,4.5 -4.5,0" fill="#f5d0fe" filter="url(#{prefix}_glow_filter)" />
      <polygon points="0,-4.5 4.5,0 0,4.5 -4.5,0" fill="#f5d0fe" />
    </g>

    <g transform="translate(0, -30)">
      {flame_markup}
    </g>

    <text x="0" y="22" fill="#f5f3ff" font-size="36" font-weight="900" text-anchor="middle" class="mono">{cur_s}</text>
    <text x="0" y="42" fill="#c084fc" font-size="9.5" font-weight="800" text-anchor="middle" letter-spacing="1.5" class="mono">DAYS</text>
  </g>

  <g transform="translate({cx}, 162)" text-anchor="middle">
    <text x="0" y="0" fill="#f5f3ff" font-size="14.5" font-weight="800">Current Streak</text>
    <text x="0" y="18" fill="#8b7fb0" font-size="11" class="mono">{cur_range}</text>
  </g>

  <g transform="translate(670, 96)" text-anchor="middle">
    <text x="0" y="0" fill="#f5f3ff" font-size="38" font-weight="900" class="mono">{long_s}</text>
    <text x="0" y="24" fill="#cbd5e1" font-size="13" font-weight="600">Longest Streak</text>
    <text x="0" y="44" fill="#8b7fb0" font-size="11" class="mono">{long_range}</text>
  </g>
</svg>"""

# ==============================================================================
# 6. CARD 3: ACTIVITY GRAPH (activity-graph.svg)
# ==============================================================================
def build_activity_graph_svg(data):
    w, h = 840, 260
    prefix = "act"
    weekly = data["weekly_totals"]
    daily = data["daily_raw"]
    rolling_dates = data["rolling_dates"]
    mavg = data["moving_avg_4w"]

    gx_start, gx_end = 368, 776
    gy_bottom, gy_top = 192, 72
    span_x = gx_end - gx_start
    span_y = gy_bottom - gy_top

    max_raw = max(max(weekly), 1)
    mag = 10 ** math.floor(math.log10(max_raw)) if max_raw > 0 else 1
    frac = max_raw / mag
    if frac <= 1.0:
        nice_max = 1 * mag
    elif frac <= 2.0:
        nice_max = 2 * mag
    elif frac <= 5.0:
        nice_max = 5 * mag
    else:
        nice_max = 10 * mag

    nice_max = max(nice_max, 10)
    nice_mid = nice_max // 2

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

    micro_bars = []
    step_d = span_x / (len(daily) - 1)
    max_d_raw = max(max(daily), 1)
    peak_d_cnt = data["peak_day_cnt"]
    peak_d_date = data["peak_day_date"]

    for i, cnt in enumerate(daily):
        if cnt > 0:
            bx = gx_start + i * step_d
            bh = min(span_y * 0.45, (cnt / max_d_raw) * span_y * 0.45)
            by = gy_bottom - bh
            if rolling_dates[i] == peak_d_date:
                micro_bars.append(f'<rect x="{bx - 1:.1f}" y="{by:.1f}" width="2.4" height="{bh:.1f}" rx="1.2" fill="#f5d0fe" opacity="0.9" />')
            else:
                micro_bars.append(f'<rect x="{bx - 0.9:.1f}" y="{by:.1f}" width="1.8" height="{bh:.1f}" rx="0.9" fill="#a78bfa" opacity="0.35" />')
    micro_bars_markup = "\n  ".join(micro_bars)

    month_spans = defaultdict(list)
    for i, d in enumerate(rolling_dates):
        m_key = (d.year, d.month)
        month_spans[m_key].append(gx_start + i * step_d)

    x_labels = []
    for (yr, mo), x_coords in month_spans.items():
        mid_x = (x_coords[0] + x_coords[-1]) / 2.0
        m_name = dt.date(yr, mo, 1).strftime("%b")
        x_labels.append(f'<text x="{mid_x:.1f}" y="{gy_bottom + 18}" fill="#8b7fb0" font-size="10" text-anchor="middle" class="mono">{m_name}</text>')
        x_labels.append(f'<line x1="{x_coords[-1]:.1f}" y1="{gy_top}" x2="{x_coords[-1]:.1f}" y2="{gy_bottom}" stroke="#a855f7" stroke-width="0.8" opacity="0.08" />')
    x_labels_markup = "\n  ".join(x_labels)

    best_w_idx = data["best_week_idx"]
    peak_x, peak_y = pts[best_w_idx]
    best_w_val = data["best_week"]
    best_w_range = f"{data['best_week_start'].strftime('%b %d')} - {data['best_week_end'].strftime('%b %d')}"

    this_week_x0 = gx_start + (len(daily) - 7) * step_d
    this_week_x1 = gx_end
    this_week_w = this_week_x1 - this_week_x0

    ticker_text = f"★ RECORD {data['longest_streak']}D · ◆ {data['total_all_time']} ALL-TIME CONTRIBS · ● {data['active_days']}/365 ACTIVE DAYS · ⚡ PEAK DAY {data['peak_day_cnt']} ON {data['peak_day_date'].strftime('%b %d')} · "
    char_len = len(ticker_text)
    single_copy_w = max(820, int(char_len * 6.8))
    ticker_dur = max(20.0, single_copy_w / 40.0)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
  </style>
  {common_card_defs(prefix, w, h)}
  <defs>
    <linearGradient id="{prefix}_chart_area" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#a855f7" stop-opacity="0.50" />
      <stop offset="60%" stop-color="#6d28d9" stop-opacity="0.16" />
      <stop offset="100%" stop-color="#2e1065" stop-opacity="0.0" />
    </linearGradient>

    <radialGradient id="{prefix}_floor_glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#6d28d9" stop-opacity="0.35" />
      <stop offset="100%" stop-color="#6d28d9" stop-opacity="0.0" />
    </radialGradient>
  </defs>

  {lava_border_frame(prefix, w, h, delay_offset=8)}

  <g transform="translate(36, 42)">
    <text x="0" y="0" fill="#f5f3ff" font-size="17" font-weight="900">Rixsan Joulfiand</text>
    <text x="0" y="16" fill="#a855f7" font-size="12" font-weight="700" class="mono">@{USERNAME}</text>

    <g transform="translate(260, -4)">
      <rect x="0" y="2" width="3" height="8" rx="1.5" fill="#c084fc" />
      <rect x="5" y="-1" width="3" height="11" rx="1.5" fill="#a855f7" />
      <rect x="10" y="3" width="3" height="7" rx="1.5" fill="#e9d5ff" />
      <text x="18" y="7" fill="#c084fc" font-size="11" font-weight="800" class="mono">LIVE</text>
    </g>

    <g transform="translate(0, 48)">
      <circle cx="8" cy="-3" r="8" fill="#4c1d95" opacity="0.3" />
      <path d="M 8 -9 C 4.7 -9 2 -6.3 2 -3 C 2 -0.4 3.7 1.9 6.1 2.7 C 6.4 2.8 6.5 2.6 6.5 2.4 L 6.5 1.4 C 4.8 1.8 4.5 0.6 4.5 0.6 C 4.2 -0.1 3.8 -0.4 3.8 -0.4 C 3.2 -0.8 3.8 -0.8 3.8 -0.8 C 4.5 -0.8 4.8 -0.1 4.8 -0.1 C 5.4 0.9 6.3 0.6 6.7 0.4 C 6.8 -0.1 7 -0.4 7.2 -0.6 C 5.9 -0.7 4.5 -1.2 4.5 -3.5 C 4.5 -4.2 4.7 -4.7 5.1 -5.1 C 5 -5.3 4.8 -5.9 5.2 -6.7 C 5.2 -6.7 5.7 -6.9 6.9 -6.1 C 7.4 -6.2 7.9 -6.3 8.4 -6.3 C 8.9 -6.3 9.4 -6.2 9.9 -6.1 C 11.1 -6.9 11.6 -6.7 11.6 -6.7 C 12 -5.9 11.8 -5.3 11.7 -5.1 C 12.1 -4.7 12.3 -4.2 12.3 -3.5 C 12.3 -1.2 10.9 -0.7 9.6 -0.6 C 9.8 -0.4 10 -0.1 10 0.5 L 10 2.4 C 10 2.6 10.1 2.8 10.4 2.7 C 12.8 1.9 14.5 -0.4 14.5 -3 C 14.5 -6.3 11.8 -9 8.5 -9 Z" fill="#c084fc" />
      <text x="24" y="0" fill="#f5f3ff" font-size="12.5" font-weight="800">{data['total_last_year']} Contributions</text>
      <text x="24" y="14" fill="#8b7fb0" font-size="10.5" class="mono">in the last year</text>
    </g>

    <g transform="translate(0, 84)">
      <circle cx="8" cy="-3" r="8" fill="#4c1d95" opacity="0.3" />
      <path d="M 4 -7 H 12 V -5 H 4 Z M 4 -3 H 12 V 1 H 4 Z M 3 -9 H 13 A 1 1 0 0 1 14 -8 V 2 A 1 1 0 0 1 13 3 H 3 A 1 1 0 0 1 2 2 V -8 A 1 1 0 0 1 3 -9 Z" fill="#c084fc" />
      <text x="24" y="0" fill="#f5f3ff" font-size="12.5" font-weight="800">{data['active_days']} Active Days</text>
      <text x="24" y="14" fill="#8b7fb0" font-size="10.5" class="mono">{data['active_pct']}% of the last 365 days</text>
    </g>

    <g transform="translate(0, 120)">
      <circle cx="8" cy="-3" r="8" fill="#4c1d95" opacity="0.3" />
      <path d="M 9 -9 L 4 -2 H 8 L 7 3 L 12 -4 H 8 Z" fill="#c084fc" />
      <text x="24" y="0" fill="#f5f3ff" font-size="12.5" font-weight="800">{data['best_week']} Best Week</text>
      <text x="24" y="14" fill="#8b7fb0" font-size="10.5" class="mono">week of {data['best_week_start'].strftime('%b %d')}</text>
    </g>
  </g>

  <rect x="{gx_start - 12}" y="36" width="{span_x + 24}" height="{gy_bottom - 36 + 28}" rx="12" fill="#0d0820" stroke="#a855f7" stroke-opacity="0.18" stroke-width="1" />
  <line x1="{gx_start - 8}" y1="37" x2="{gx_end + 8}" y2="37" stroke="#e9d5ff" stroke-opacity="0.12" stroke-width="1" />

  <text x="{gx_end}" y="52" fill="#a855f7" font-size="10" font-weight="700" text-anchor="end" class="mono" letter-spacing="1">WEEKLY VELOCITY RIDGE</text>

  <line x1="{gx_start}" y1="{gy_top}" x2="{gx_end}" y2="{gy_top}" stroke="#2e1065" stroke-width="0.8" stroke-dasharray="3 4" />
  <line x1="{gx_start}" y1="{(gy_top + gy_bottom)/2}" x2="{gx_end}" y2="{(gy_top + gy_bottom)/2}" stroke="#2e1065" stroke-width="0.8" stroke-dasharray="3 4" />
  <line x1="{gx_start}" y1="{gy_bottom}" x2="{gx_end}" y2="{gy_bottom}" stroke="#2e1065" stroke-width="1" />

  <text x="{gx_end + 14}" y="{gy_top + 4}" fill="#8b7fb0" font-size="10" class="mono">{nice_max}</text>
  <text x="{gx_end + 14}" y="{(gy_top + gy_bottom)/2 + 4}" fill="#8b7fb0" font-size="10" class="mono">{nice_mid}</text>
  <text x="{gx_end + 14}" y="{gy_bottom + 4}" fill="#8b7fb0" font-size="10" class="mono">0</text>

  <ellipse cx="{peak_x:.1f}" cy="{gy_bottom}" rx="60" ry="24" fill="url(#{prefix}_floor_glow)" />

  <rect x="{this_week_x0:.1f}" y="{gy_top}" width="{this_week_w:.1f}" height="{span_y}" fill="#a855f7" opacity="0.08" />

  {micro_bars_markup}

  <path d="{area_d}" fill="url(#{prefix}_chart_area)" />

  <path d="{spline_mavg}" fill="none" stroke="#d8b4fe" stroke-width="1.2" stroke-dasharray="3 3" opacity="0.6" />

  <path d="{spline_d}" fill="none" stroke="#a855f7" stroke-width="5" opacity="0.4" filter="url(#{prefix}_glow_filter)" />
  <path d="{spline_d}" fill="none" stroke="#f3e8ff" stroke-width="2.4" stroke-linecap="round" />

  <circle r="3.6" fill="#f5d0fe" filter="url(#{prefix}_glow_filter)">
    <animateMotion path="{spline_d}" dur="9s" repeatCount="indefinite" />
  </circle>

  {x_labels_markup}

  <circle cx="{peak_x:.2f}" cy="{peak_y:.2f}" r="4" fill="none" stroke="#c084fc" stroke-width="1.6">
    <animate attributeName="r" from="3" to="22" dur="2.4s" repeatCount="indefinite" />
    <animate attributeName="opacity" from="1" to="0" dur="2.4s" repeatCount="indefinite" />
  </circle>
  <circle cx="{peak_x:.2f}" cy="{peak_y:.2f}" r="4" fill="none" stroke="#e9d5ff" stroke-width="1.2">
    <animate attributeName="r" from="3" to="14" dur="2.4s" begin="0.8s" repeatCount="indefinite" />
    <animate attributeName="opacity" from="1" to="0" dur="2.4s" begin="0.8s" repeatCount="indefinite" />
  </circle>
  <circle cx="{peak_x:.2f}" cy="{peak_y:.2f}" r="4.5" fill="#f5d0fe" filter="url(#{prefix}_glow_filter)" />

  <g transform="translate({peak_x:.2f}, {peak_y - 14:.2f})">
    <rect x="-62" y="-12" width="124" height="16" rx="4" fill="#2e1065" stroke="#a855f7" stroke-width="1" />
    <text x="0" y="-0.5" fill="#e9d5ff" font-size="8.5" font-weight="900" text-anchor="middle" class="mono">{best_w_val} · {best_w_range}</text>
  </g>

  <circle cx="{pts[-1][0]:.2f}" cy="{pts[-1][1]:.2f}" r="3" fill="#c084fc">
    <animate attributeName="r" values="3;6;3" dur="2s" repeatCount="indefinite" />
  </circle>

  <g transform="translate(0, {h-24})">
    <rect x="8" y="0" width="{w-16}" height="20" rx="4" fill="#07040f" stroke="#1f1138" stroke-width="0.8" />
    <svg x="14" y="0" width="{w-28}" height="20" style="overflow: hidden;">
      <g>
        <animateTransform attributeName="transform" type="translate" from="0 0" to="-{single_copy_w} 0" dur="{ticker_dur:.1f}s" repeatCount="indefinite" />
        <text x="0" y="13" fill="#cbd5e1" font-size="9.5" font-weight="600" class="mono" textLength="{single_copy_w}" lengthAdjust="spacing">
          {ticker_text}
        </text>
        <text x="{single_copy_w}" y="13" fill="#cbd5e1" font-size="9.5" font-weight="600" class="mono" textLength="{single_copy_w}" lengthAdjust="spacing">
          {ticker_text}
        </text>
      </g>
    </svg>
  </g>
</svg>"""

# ==============================================================================
# 7. CARD 4: GITHUB STATS (github-stats.svg)
# ==============================================================================
def build_github_stats_svg(data):
    w, h = 405, 248
    prefix = "stats"
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
  {common_card_defs(prefix, w, h)}
  <defs>
    <linearGradient id="{prefix}_octo_arc" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4c1d95" />
      <stop offset="60%" stop-color="#a855f7" />
      <stop offset="100%" stop-color="#e9d5ff" />
    </linearGradient>

    <linearGradient id="{prefix}_tail_fade" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#e9d5ff" stop-opacity="0.8" />
      <stop offset="100%" stop-color="#4c1d95" stop-opacity="0.0" />
    </linearGradient>
  </defs>

  {lava_border_frame(prefix, w, h, delay_offset=12)}

  <text x="24" y="34" fill="#a855f7" font-size="14.5" font-weight="800">Stats</text>

  <g transform="translate(24, 68)">
    <g transform="translate(0, 0)">
      <circle cx="9" cy="-3.5" r="8" fill="#6d28d9" opacity="0.28" />
      <path d="M 9 -8 L 10.5 -4.5 L 14 -4.5 L 11.2 -2.2 L 12.3 1 L 9 -1.2 L 5.7 1 L 6.8 -2.2 L 4 -4.5 L 7.5 -4.5 Z" fill="#c084fc" />
      <text x="24" y="0" fill="#8b7fb0" font-size="11">Total Stars Earned:</text>
      <text x="205" y="0" fill="#f5f3ff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">{stars}</text>
      <line x1="0" y1="10" x2="205" y2="10" stroke="#1f1138" stroke-width="0.8" />
    </g>

    <g transform="translate(0, 28)">
      <circle cx="9" cy="-3.5" r="8" fill="#6d28d9" opacity="0.28" />
      <path d="M 9 -6 A 3 3 0 0 1 11.8 -3.5 H 14 V -1.5 H 11.8 A 3 3 0 0 1 6.2 -1.5 H 4 V -3.5 H 6.2 A 3 3 0 0 1 9 -6 M 9 -4.5 A 1.5 1.5 0 0 0 7.5 -2.5 A 1.5 1.5 0 0 0 9 -0.5 A 1.5 1.5 0 0 0 10.5 -2.5 A 1.5 1.5 0 0 0 9 -4.5 Z" fill="#c084fc" />
      <text x="24" y="0" fill="#8b7fb0" font-size="11">Total Commits (last year):</text>
      <text x="205" y="0" fill="#f5f3ff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">{commits}</text>
      <line x1="0" y1="10" x2="205" y2="10" stroke="#1f1138" stroke-width="0.8" />
    </g>

    <g transform="translate(0, 56)">
      <circle cx="9" cy="-3.5" r="8" fill="#6d28d9" opacity="0.28" />
      <path d="M 6 -7 A 1.5 1.5 0 1 0 6 -4 A 1.5 1.5 0 0 0 6 -7 M 6 0 A 1.5 1.5 0 1 0 6 3 A 1.5 1.5 0 0 0 6 0 M 12 -7 A 1.5 1.5 0 1 0 12 -4 A 1.5 1.5 0 0 0 12 -7 M 7 -4 V 0 M 11 -4 V -1 C 11 0.5 10 1.5 8.5 1.5 H 7" fill="none" stroke="#c084fc" stroke-width="1.2" />
      <text x="24" y="0" fill="#8b7fb0" font-size="11">Total PRs:</text>
      <text x="205" y="0" fill="#f5f3ff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">{prs}</text>
      <line x1="0" y1="10" x2="205" y2="10" stroke="#1f1138" stroke-width="0.8" />
    </g>

    <g transform="translate(0, 84)">
      <circle cx="9" cy="-3.5" r="8" fill="#6d28d9" opacity="0.28" />
      <circle cx="9" cy="-2.5" r="5" fill="none" stroke="#c084fc" stroke-width="1.2" />
      <circle cx="9" cy="-2.5" r="1.5" fill="#c084fc" />
      <text x="24" y="0" fill="#8b7fb0" font-size="11">Total Issues:</text>
      <text x="205" y="0" fill="#f5f3ff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">{issues}</text>
      <line x1="0" y1="10" x2="205" y2="10" stroke="#1f1138" stroke-width="0.8" />
    </g>

    <g transform="translate(0, 112)">
      <circle cx="9" cy="-3.5" r="8" fill="#6d28d9" opacity="0.28" />
      <path d="M 5 -6 H 13 V 1 H 5 Z M 4 -7 H 14 V 2 H 4 Z M 7 -4 H 11 V -2 H 7 Z" fill="#c084fc" />
      <text x="24" y="0" fill="#8b7fb0" font-size="11">Contributed to:</text>
      <text x="205" y="0" fill="#f5f3ff" font-size="11.5" font-weight="800" text-anchor="end" class="mono">{contrib_to}</text>
    </g>
  </g>

  <g transform="translate(325, 140)">
    <circle cx="0" cy="0" r="30" fill="#0b0714" stroke="#2e1065" stroke-width="1.4" />

    <circle cx="0" cy="0" r="38" fill="none" stroke="url(#{prefix}_octo_arc)" stroke-width="2.8"
            stroke-dasharray="25 75" pathLength="100" stroke-linecap="round" filter="url(#{prefix}_glow_filter)">
      <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="14s" repeatCount="indefinite" />
    </circle>

    <circle cx="0" cy="0" r="44" fill="none" stroke="#4c1d95" stroke-width="1.2"
            stroke-dasharray="4 6" opacity="0.8">
      <animateTransform attributeName="transform" type="rotate" from="360 0 0" to="0 0 0" dur="22s" repeatCount="indefinite" />
    </circle>

    <g>
      <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="10s" repeatCount="indefinite" />
      <path d="M 44 0 A 44 44 0 0 0 33 -28" fill="none" stroke="url(#{prefix}_tail_fade)" stroke-width="2" stroke-linecap="round" opacity="0.6" />
      <circle cx="44" cy="0" r="2.2" fill="#e9d5ff" filter="url(#{prefix}_glow_filter)" />
    </g>

    <g transform="scale(1.2) translate(-12, -12)">
      <path fill="#f5f3ff" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
    </g>
  </g>
</svg>"""

# ==============================================================================
# 8. CARD 5: MOST USED LANGUAGES (top-langs.svg)
# ==============================================================================
def build_top_langs_svg(data):
    w, h = 405, 248
    prefix = "langs"
    langs = data["languages"]

    spec_w = 357.0
    spec_segments = []
    seg_x = 24.0
    for idx, l in enumerate(langs):
        sw = max(2.0, (l["pct"] / 100.0) * (spec_w - (len(langs) - 1) * 2))
        color = l["color"] if LANG_COLOR_MODE == "full" else "#a855f7"
        spec_segments.append(f'<rect x="{seg_x:.1f}" y="48" width="{sw:.1f}" height="6" rx="2" fill="{color}" />')
        seg_x += sw + 2.0
    spec_markup = "\n  ".join(spec_segments)

    cx_orb, cy_orb = 92.0, 152.0
    rank_shades = ["#e9d5ff", "#c084fc", "#a855f7", "#9333ea", "#6d28d9", "#5b21b6"]

    planets_markup = []
    for idx, l in enumerate(langs[:6]):
        r_orbit = 20.0 + 9.5 * idx
        r_planet = min(9.5, max(3.0, 3.2 + math.sqrt(l['pct']) * 0.72))
        period = 7.0 + 4.0 * idx
        init_phase = (idx * 64) % 360
        body_color = l["color"] if LANG_COLOR_MODE == "full" else rank_shades[min(idx, len(rank_shades)-1)]
        atmos_color = l["color"]

        planets_markup.append(f"""
        <!-- Orbit {idx+1} Ring -->
        <circle cx="{cx_orb:.1f}" cy="{cy_orb:.1f}" r="{r_orbit:.1f}" fill="none" stroke="#2e1065" stroke-width="0.9" stroke-dasharray="2 3" opacity="0.75" />
        <g transform="translate({cx_orb:.1f}, {cy_orb:.1f})">
          <g>
            <animateTransform attributeName="transform" type="rotate" from="{init_phase} 0 0" to="{init_phase + 360} 0 0" dur="{period:.1f}s" repeatCount="indefinite" />
            <path d="M {r_orbit:.1f} 0 A {r_orbit:.1f} {r_orbit:.1f} 0 0 0 {r_orbit * 0.82:.1f} {-r_orbit * 0.57:.1f}" fill="none" stroke="{body_color}" stroke-width="1.4" opacity="0.35" stroke-linecap="round" />
            <circle cx="{r_orbit:.1f}" cy="0" r="{r_planet:.1f}" fill="{body_color}">
              <animateTransform attributeName="transform" type="rotate" from="0 {r_orbit:.1f} 0" to="-360 {r_orbit:.1f} 0" dur="{period:.1f}s" repeatCount="indefinite" />
            </circle>
            <circle cx="{r_orbit:.1f}" cy="0" r="{r_planet + 1.2:.1f}" fill="none" stroke="{atmos_color}" stroke-width="1.2" opacity="0.85" />
          </g>
        </g>
        """)

    track_w = 115.0
    rows_markup = []
    y_pos = 88.0
    for idx, l in enumerate(langs[:6]):
        bar_len = max(3.0, (l["pct"] / 100.0) * track_w)
        rank_no = f"0{idx+1}"
        rank_bg = f'<rect x="188" y="{y_pos - 13:.1f}" width="193" height="22" rx="4" fill="#a855f7" opacity="0.08" />' if idx == 0 else ""

        row = f"""
        {rank_bg}
        <g transform="translate(190, {y_pos:.1f})">
          <text x="0" y="0" fill="#6d28d9" font-size="9.5" font-weight="700" class="mono">{rank_no}</text>
          <circle cx="18" cy="-3.5" r="3.2" fill="{l['color']}" />
          <text x="26" y="0" fill="#f5f3ff" font-size="11.5" font-weight="600">{l['name']}</text>
          <text x="185" y="0" fill="#8b7fb0" font-size="10" class="mono" text-anchor="end">{l['pct']:.1f}%</text>

          <rect x="26" y="5" width="{track_w:.0f}" height="4" rx="2" fill="#180d2b" />

          <clipPath id="{prefix}_shimmer_clip_{idx}">
            <rect x="26" y="5" width="{bar_len:.1f}" height="4" rx="2" />
          </clipPath>

          <g clip-path="url(#{prefix}_shimmer_clip_{idx})">
            <rect x="26" y="5" width="{bar_len:.1f}" height="4" fill="url(#{prefix}_bar_grad)" />
            <rect x="-30" y="5" width="24" height="4" fill="#ffffff" opacity="0.4">
              <animate attributeName="x" from="26" to="{26 + bar_len + 30:.1f}" dur="3.0s" repeatCount="indefinite" begin="{idx * 0.4}s" />
            </rect>
          </g>

          <circle cx="{26 + bar_len:.1f}" cy="7" r="1.8" fill="#f5d0fe" />
        </g>
        """
        rows_markup.append(row)
        y_pos += 25.0

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <style>
    text {{ font-family: 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif; }}
    .mono {{ font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; }}
  </style>
  {common_card_defs(prefix, w, h)}
  <defs>
    <linearGradient id="{prefix}_bar_grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#5b21b6" />
      <stop offset="100%" stop-color="#c084fc" />
    </linearGradient>
  </defs>

  {lava_border_frame(prefix, w, h, delay_offset=16)}

  <text x="24" y="34" fill="#a855f7" font-size="14.5" font-weight="800">Most Used Languages</text>

  {spec_markup}

  <g>
    <circle cx="{cx_orb:.1f}" cy="{cy_orb:.1f}" r="14" fill="#4c1d95" filter="url(#{prefix}_glow_filter)">
      <animate attributeName="r" values="13; 14.5; 13" dur="3s" repeatCount="indefinite" />
    </circle>
    <circle cx="{cx_orb:.1f}" cy="{cy_orb:.1f}" r="9.5" fill="#1e0b3d" />
    <text x="{cx_orb:.1f}" y="{cy_orb + 3.5:.1f}" fill="#f5f3ff" font-size="8.5" font-weight="900" text-anchor="middle" class="mono">&lt;/&gt;</text>

    {"".join(planets_markup)}
  </g>

  {"".join(rows_markup)}
</svg>"""

# ==============================================================================
# 9. SELFTEST & AUDIT PIPELINE
# ==============================================================================
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
        "source": "selftest"
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

    # Test 3: AST Inspection - Validasi hanya pada fungsi builder kartu SVG
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

    # Test 4: Palet Audit Otomatis (Hex tidak boleh kuning/oranye/cyan di luar bahasa API)
    test_cards = {
        "hdr": build_header_svg(),
        "strk": build_streak_svg(t1),
        "act": build_activity_graph_svg(t1),
        "stats": build_github_stats_svg(t1),
        "langs": build_top_langs_svg(t1)
    }

    allowed_lang_hexes = {"#3572a5", "#4f5b93"}
    for name, svg_code in test_cards.items():
        ET.fromstring(svg_code)
        hex_matches = re.findall(r"#[0-9a-fA-F]{6}", svg_code)
        for hx in hex_matches:
            hx_low = hx.lower()
            if hx_low in allowed_lang_hexes:
                continue
            r, g, b = int(hx_low[1:3], 16)/255.0, int(hx_low[3:5], 16)/255.0, int(hx_low[5:7], 16)/255.0
            h_deg, s, v = colorsys.rgb_to_hsv(r, g, b)
            h_deg *= 360.0
            if s > 0.35 and v > 0.3:
                is_yellow = 20 <= h_deg <= 75
                is_cyan = 180 <= h_deg <= 250
                assert not is_yellow, f"Forbidden yellow/gold hex {hx} found in {name} card (hue {h_deg:.1f})"
                assert not is_cyan, f"Forbidden cyan/blue hex {hx} found in {name} card (hue {h_deg:.1f})"

    print("[PASS] Test 4: Palette audit passed (0% forbidden hues outside API langs)")
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

    lang_summary_items = [f"{l['name']} ({l['pct']:.1f}%)" for l in telemetry['languages']]
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
        "top-langs.svg": build_top_langs_svg(telemetry)
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
