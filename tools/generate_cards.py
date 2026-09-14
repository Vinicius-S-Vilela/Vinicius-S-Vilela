#!/usr/bin/env python3
"""
Generates the GitHub stat cards as SVG files inside this repository, so the
README never depends on a third-party service that can rate-limit or go down.

Runs on GitHub Actions with the default GITHUB_TOKEN — no personal token, no
external dependencies (standard library only).

    GH_USER=Vinicius-S-Vilela GITHUB_TOKEN=xxx python3 tools/generate_cards.py

Use --mock to render the cards with sample data (for local preview).
"""
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import date, timedelta

USER = os.environ.get("GH_USER", "Vinicius-S-Vilela")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
MOCK = "--mock" in sys.argv
PLACEHOLDER = "--placeholder" in sys.argv

# ---------------------------------------------------------------- palette
GREEN = "#3FB950"
ORANGE = "#ED8B00"
TEXT = "#7D8590"
DIM = "#6E7681"
BORDER = "#30363D"
FONT = "'Segoe UI',Ubuntu,'Helvetica Neue',Helvetica,Arial,sans-serif"

LANG_COLORS = {
    "Java": "#B07219", "TypeScript": "#3178C6", "JavaScript": "#F1E05A",
    "Python": "#3572A5", "HTML": "#E34C26", "CSS": "#563D7C",
    "SCSS": "#C6538C", "Shell": "#89E051", "Dockerfile": "#384D54",
    "PLpgSQL": "#336790", "TSQL": "#E38C00", "Jupyter Notebook": "#DA5B0B",
}
FALLBACK_COLORS = ["#3FB950", "#58A6FF", "#ED8B00", "#BC8CFF", "#F78166",
                   "#39C5CF", "#DB6D28", "#8B949E"]


# ---------------------------------------------------------------- api
def rest(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"User-Agent": "profile-cards", "Accept": "application/vnd.github+json",
                 **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def graphql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"User-Agent": "profile-cards", "Content-Type": "application/json",
                 "Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


CONTRIB_QUERY = """
query($login:String!) {
  user(login:$login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""


def collect():
    """Everything the three cards need, in one shot."""
    user = rest(f"/users/{USER}")
    repos, page = [], 1
    while True:
        chunk = rest(f"/users/{USER}/repos?per_page=100&page={page}&type=owner")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1

    own = [r for r in repos if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in own)
    forks = sum(r.get("forks_count", 0) for r in own)

    langs = {}
    for r in own:
        try:
            for name, size in rest(f"/repos/{USER}/{r['name']}/languages").items():
                langs[name] = langs.get(name, 0) + size
        except urllib.error.HTTPError:
            continue

    contrib = graphql(CONTRIB_QUERY, {"login": USER})["user"]["contributionsCollection"]
    days = [(d["date"], d["contributionCount"])
            for w in contrib["contributionCalendar"]["weeks"]
            for d in w["contributionDays"]]

    return {
        "followers": user.get("followers", 0),
        "repos": len(own),
        "stars": stars,
        "forks": forks,
        "commits": contrib["totalCommitContributions"],
        "prs": contrib["totalPullRequestContributions"],
        "issues": contrib["totalIssueContributions"],
        "total_contrib": contrib["contributionCalendar"]["totalContributions"],
        "days": days,
        "langs": langs,
    }


def mock():
    today = date.today()
    days = [((today - timedelta(days=i)).isoformat(), 1 if i < 4 or 20 < i < 26 else 0)
            for i in range(364, -1, -1)]
    return {"followers": 2, "repos": 6, "stars": 2, "forks": 1, "commits": 89,
            "prs": 4, "issues": 1, "total_contrib": 94, "days": days,
            "langs": {"Java": 420000, "TypeScript": 260000, "Python": 150000,
                      "HTML": 70000, "CSS": 46000, "Dockerfile": 4000}}


# ---------------------------------------------------------------- streaks
def streaks(days):
    """(current, longest, longest_range) from an ordered list of (date, count)."""
    longest = cur = 0
    best_start = best_end = run_start = None
    for d, c in days:
        if c > 0:
            cur += 1
            if run_start is None:
                run_start = d
            if cur > longest:
                longest, best_start, best_end = cur, run_start, d
        else:
            cur = 0
            run_start = None
    # a streak that is still alive may end today or yesterday
    current, i = 0, len(days) - 1
    if days and days[-1][1] == 0:
        i -= 1                       # today hasn't been counted yet
    while i >= 0 and days[i][1] > 0:
        current += 1
        i -= 1
    return current, longest, (best_start, best_end)


def pretty(iso):
    if not iso:
        return ""
    y, m, d = iso.split("-")
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{months[int(m) - 1]} {int(d)}"


def human(n):
    return f"{n/1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


# ---------------------------------------------------------------- svg
def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def frame(w, h, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" fill="none" role="img" aria-label="{esc(title)}">\n'
            f'  <rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="8" '
            f'fill="#00000000" stroke="{BORDER}"/>\n'
            f'  <text x="25" y="34" font-family="{FONT}" font-size="17" font-weight="600" '
            f'fill="{GREEN}">{esc(title)}</text>\n{body}\n</svg>\n')


def stats_card(d):
    rows = [("Total Stars Earned", d["stars"]), ("Total Forks", d["forks"]),
            ("Public Repositories", d["repos"]), ("Followers", d["followers"]),
            ("Commits (last 12 months)", d["commits"]),
            ("Pull Requests", d["prs"]), ("Issues", d["issues"])]
    body, y = [], 72
    for label, value in rows:
        body.append(
            f'  <text x="25" y="{y}" font-family="{FONT}" font-size="14" fill="{TEXT}">{esc(label)}</text>\n'
            f'  <text x="425" y="{y}" font-family="{FONT}" font-size="14" font-weight="700" '
            f'fill="{GREEN}" text-anchor="end">{human(value)}</text>')
        y += 27
    return frame(450, y + 4, f"{USER.split('-')[0]}'s GitHub Stats", "\n".join(body))


def langs_card(d, top=8):
    items = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:top]
    total = sum(v for _, v in items) or 1
    x, bar = 25, []
    for i, (name, size) in enumerate(items):
        w = (size / total) * 400
        color = LANG_COLORS.get(name, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])
        bar.append(f'  <rect x="{x:.1f}" y="56" width="{max(w,2):.1f}" height="10" fill="{color}"/>')
        x += w
    body = ["  <clipPath id=\"b\"><rect x=\"25\" y=\"56\" width=\"400\" height=\"10\" rx=\"5\"/></clipPath>",
            "  <g clip-path=\"url(#b)\">", *bar, "  </g>"]
    y = 96
    for i, (name, size) in enumerate(items):
        col = 25 if i % 2 == 0 else 235
        color = LANG_COLORS.get(name, FALLBACK_COLORS[i % len(FALLBACK_COLORS)])
        pct = size / total * 100
        body.append(
            f'  <circle cx="{col + 5}" cy="{y - 5}" r="5" fill="{color}"/>\n'
            f'  <text x="{col + 18}" y="{y}" font-family="{FONT}" font-size="13" fill="{TEXT}">'
            f'{esc(name)} <tspan fill="{DIM}">{pct:.1f}%</tspan></text>')
        if i % 2 == 1:
            y += 26
    if len(items) % 2 == 1:
        y += 26
    return frame(450, y + 6, "Most Used Languages", "\n".join(body))


def streak_card(d):
    cur, longest, (s, e) = streaks(d["days"])
    first = d["days"][0][0] if d["days"] else ""
    last = d["days"][-1][0] if d["days"] else ""
    cols = [(human(d["total_contrib"]), "Total Contributions", f"{pretty(first)} – {pretty(last)}", TEXT),
            (human(cur), "Current Streak", pretty(last) if cur else "—", GREEN),
            (human(longest), "Longest Streak", f"{pretty(s)} – {pretty(e)}" if longest else "—", TEXT)]
    body, W = [], 520
    for i, (num, label, sub, color) in enumerate(cols):
        cx = 87 + i * 173
        body.append(
            f'  <text x="{cx}" y="76" font-family="{FONT}" font-size="30" font-weight="700" '
            f'fill="{color}" text-anchor="middle">{esc(num)}</text>\n'
            f'  <text x="{cx}" y="100" font-family="{FONT}" font-size="13" font-weight="600" '
            f'fill="{TEXT}" text-anchor="middle">{esc(label)}</text>\n'
            f'  <text x="{cx}" y="120" font-family="{FONT}" font-size="11" '
            f'fill="{DIM}" text-anchor="middle">{esc(sub)}</text>')
    for i in (1, 2):
        x = 0.5 + i * 173
        body.append(f'  <line x1="{x}" y1="48" x2="{x}" y2="132" stroke="{BORDER}"/>')
    if cur:
        body.append(f'  <circle cx="260" cy="48" r="4" fill="{ORANGE}"/>')
    return frame(W, 150, "Contribution Streak", "\n".join(body))


def placeholder_card(title, w=450, h=120):
    return frame(w, h, title,
        f'  <text x="25" y="70" font-family="{FONT}" font-size="14" fill="{TEXT}">'
        f'Generating on the first workflow run…</text>\n'
        f'  <text x="25" y="94" font-family="{FONT}" font-size="12" fill="{DIM}">'
        f'Actions → Generate Profile Cards → Run workflow</text>')


def main():
    if PLACEHOLDER:
        os.makedirs(OUT, exist_ok=True)
        for name, title, w in (("stats", f"{USER.split('-')[0]}'s GitHub Stats", 450),
                               ("langs", "Most Used Languages", 450),
                               ("streak", "Contribution Streak", 520)):
            with open(os.path.join(OUT, f"{name}.svg"), "w", encoding="utf-8") as fh:
                fh.write(placeholder_card(title, w))
            print(f"wrote placeholder assets/{name}.svg")
        return
    data = mock() if MOCK else collect()
    os.makedirs(OUT, exist_ok=True)
    for name, svg in (("stats", stats_card(data)),
                      ("langs", langs_card(data)),
                      ("streak", streak_card(data))):
        with open(os.path.join(OUT, f"{name}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"wrote assets/{name}.svg")


if __name__ == "__main__":
    main()
