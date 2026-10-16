#!/usr/bin/env python3
"""Generates assets/generated/*.svg from public GitHub pages. Stdlib only, no token needed."""
import re, html, os, sys, urllib.request, textwrap, collections
from datetime import date, timedelta

USER = os.environ.get("GH_USER", "HarshKuro")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "generated")
os.makedirs(OUT, exist_ok=True)

BG="#0a0c10"; PANEL="#0d1017"; LINE="#1c2230"; TXT="#e6ebf5"; DIM="#7d8799"; AC="#7df9ff"
SANS="Inter,'Segoe UI','Helvetica Neue',Arial,sans-serif"
MONO="'JetBrains Mono','Fira Code',Consolas,'Courier New',monospace"
esc = lambda s: html.escape(s, quote=True)

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (profile-readme-bot)"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

def fade_in(begin, total=4.0, dur=.5):
    """SMIL fade-in that degrades to fully visible where animation is unsupported."""
    b = min(begin / total, .95); e = min((begin + dur) / total, 1.0)
    return f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{b:.3f};{e:.3f}" dur="{total}s" begin="0s" fill="freeze"/>'

def head(w, h): return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'

# ---------------- contributions ----------------
def contributions():
    t = get(f"https://github.com/users/{USER}/contributions")
    cells = {}
    for m in re.finditer(r'data-date="([\d-]+)"\s+id="(contribution-day-component-\d+-\d+)"\s+data-level="(\d)"', t):
        cells[m.group(2)] = {"date": date.fromisoformat(m.group(1)), "level": int(m.group(3)), "n": 0}
    for m in re.finditer(r'for="(contribution-day-component-\d+-\d+)"[^>]*>\s*([^<]*)', t):
        cid, txt = m.group(1), m.group(2)
        n = re.match(r"(\d+) contribution", txt.strip())
        if cid in cells: cells[cid]["n"] = int(n.group(1)) if n else 0
    if not cells: raise SystemExit("no contribution data parsed")
    days = []
    for cid, c in cells.items():
        r, w = int(cid.split("-")[-2]), int(cid.split("-")[-1])
        days.append({**c, "row": r, "col": w})
    days.sort(key=lambda d: d["date"])
    return days

def streaks(days):
    counts = {d["date"]: d["n"] for d in days}
    ds = sorted(counts)
    longest = cur = 0
    for d in ds:
        cur = cur + 1 if counts[d] > 0 else 0
        longest = max(longest, cur)
    cur = 0; i = len(ds) - 1
    if i >= 0 and counts[ds[i]] == 0: i -= 1   # today may not be done yet
    while i >= 0 and counts[ds[i]] > 0: cur += 1; i -= 1
    return cur, longest

def contrib_svg(days):
    cell, gap, left, top = 14, 3, 40, 58
    cols = max(d["col"] for d in days) + 1
    W = left + cols * (cell + gap) + 24; H = top + 7 * (cell + gap) + 50
    colors = ["#131822", "#12475a", "#1b8fa6", "#3fd0e6", "#a8fbff"]
    total = sum(d["n"] for d in days)
    s = [head(W, H)]
    s.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="10" fill="{PANEL}" stroke="{LINE}"/>')
    s.append(f'<text x="28" y="32" font-family="{MONO}" font-size="12" letter-spacing="4" fill="{DIM}">{total:,} CONTRIBUTIONS  ·  LAST 12 MONTHS</text>')
    seen = set(); last_x = -99
    for d in days:
        key = (d["date"].year, d["date"].month)
        if d["row"] == 0 and key not in seen and (d["date"].day <= 7 or d["col"] == 0):
            if d["col"] - last_x < 3: continue
            seen.add(key); last_x = d["col"]
            s.append(f'<text x="{left + d["col"]*(cell+gap)}" y="{top-8}" font-family="{MONO}" font-size="10" fill="{DIM}">{d["date"].strftime("%b").upper()}</text>')
    for i, lab in [(1, "MON"), (3, "WED"), (5, "FRI")]:
        s.append(f'<text x="28" y="{top + i*(cell+gap) + 11}" text-anchor="end" font-family="{MONO}" font-size="9" fill="{DIM}">{lab}</text>')
    for d in days:
        x = left + d["col"] * (cell + gap); y = top + d["row"] * (cell + gap)
        b = d["col"] * 0.035
        s.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{colors[d["level"]]}"><title>{d["n"]} on {d["date"].isoformat()}</title>{fade_in(b)}</rect>')
    sw = 3
    s.append(f'<rect x="{left}" y="{top-4}" width="{sw}" height="{7*(cell+gap)+4}" fill="{AC}" opacity=".5"><animate attributeName="x" values="{left};{left+cols*(cell+gap)};{left}" dur="9s" begin="2.5s" repeatCount="indefinite"/></rect>')
    lx = W - 28 - 5 * 18 - 90
    s.append(f'<text x="{lx}" y="{H-18}" font-family="{MONO}" font-size="10" fill="{DIM}">LESS</text>')
    for i, c in enumerate(colors):
        s.append(f'<rect x="{lx+34+i*18}" y="{H-28}" width="12" height="12" rx="3" fill="{c}"/>')
    s.append(f'<text x="{lx+34+5*18+4}" y="{H-18}" font-family="{MONO}" font-size="10" fill="{DIM}">MORE</text></svg>')
    open(os.path.join(OUT, "contrib.svg"), "w").write("\n".join(s))

# ---------------- repos ----------------
def repo_list():
    repos = []; page = 1
    while page <= 6:
        t = get(f"https://github.com/{USER}?tab=repositories&page={page}")
        items = re.findall(r'<li[^>]*itemprop="owns"[^>]*>(.*?)</li>', t, re.S)
        if not items: break
        for it in items:
            n = re.search(r'itemprop="name codeRepository"[^>]*>\s*([^<]+)', it)
            l = re.search(r'itemprop="programmingLanguage">([^<]+)', it)
            s = re.search(r'href="/[^"/]+/[^"/]+/stargazers"[^>]*>(.*?)</a>', it, re.S)
            st = re.sub(r"[^\d]", "", re.sub(r"<[^>]+>", "", s.group(1))) if s else ""
            repos.append({"name": n.group(1).strip() if n else "", "lang": l.group(1) if l else None,
                          "fork": "Forked from" in it, "stars": int(st) if st else 0})
        page += 1
    return [r for r in repos if r["name"] and r["name"].lower() != USER.lower()]

def pinned():
    t = get(f"https://github.com/{USER}")
    out = []
    for b in re.split(r'<div class="pinned-item-list-item', t)[1:]:
        n = re.search(r'<span class="repo"[^>]*>\s*([^<]+)', b)
        d = re.search(r'pinned-item-desc[^>]*>\s*(.*?)\s*</p>', b, re.S)
        l = re.search(r'itemprop="programmingLanguage">([^<]+)', b)
        s = re.search(r'/stargazers"[^>]*>(.*?)</a>', b, re.S)
        st = re.sub(r"[^\d]", "", re.sub(r"<[^>]+>", "", s.group(1))) if s else ""
        if n: out.append({"name": n.group(1).strip(), "desc": html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", "", d.group(1)))) if d else "", "lang": l.group(1) if l else "", "stars": int(st) if st else 0})
    return out

def repos_svg(pins):
    if not pins: return
    n = len(pins); W = 1000; gap = 14; cw = (W - gap * (n - 1)) / n; H = 150
    s = [head(W, H)]
    for i, p in enumerate(pins):
        x = i * (cw + gap)
        s.append(f'<rect x="{x+.5}" y=".5" width="{cw-1}" height="{H-1}" rx="10" fill="{PANEL}" stroke="{LINE}"/>')
        s.append(f'<rect x="{x}" y="0" width="{cw}" height="2" fill="{AC}" opacity=".6"><animate attributeName="opacity" values=".6;.1;.6" dur="{3+i}s" repeatCount="indefinite"/></rect>')
        name = p["name"] if len(p["name"]) <= 30 else p["name"][:29] + "…"
        s.append(f'<text x="{x+20}" y="36" font-family="{SANS}" font-weight="600" font-size="15" fill="{TXT}">{esc(name)}</text>')
        lines = textwrap.wrap(p["desc"] or "No description yet.", 40)[:2]
        if len(textwrap.wrap(p["desc"] or "", 40)) > 2: lines[-1] = lines[-1][:37] + "…"
        for j, l in enumerate(lines):
            s.append(f'<text x="{x+20}" y="{64+j*18}" font-family="{SANS}" font-size="12.5" fill="{DIM}">{esc(l)}</text>')
        s.append(f'<circle cx="{x+24}" cy="{H-26}" r="4" fill="{AC}"/><text x="{x+36}" y="{H-22}" font-family="{MONO}" font-size="11" letter-spacing="1" fill="#9fb0c8">{esc(p["lang"] or "—")}</text>')
        s.append(f'<text x="{x+cw-20}" y="{H-22}" text-anchor="end" font-family="{MONO}" font-size="11" fill="#9fb0c8">★ {p["stars"]}</text>')
    s.append("</svg>")
    open(os.path.join(OUT, "repos.svg"), "w").write("\n".join(s))

def langs_svg(repos):
    c = collections.Counter(r["lang"] for r in repos if r["lang"] and not r["fork"])
    tot = sum(c.values())
    if not tot: return
    top = c.most_common(6); rest = tot - sum(v for _, v in top)
    if rest > 0: top.append(("Other", rest))
    pal = ["#7df9ff", "#5cc8ff", "#6c8cff", "#8f7bff", "#b07cff", "#d58cff", "#4b5a78"]
    W, H = 1000, 150
    s = [head(W, H), f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="10" fill="{PANEL}" stroke="{LINE}"/>',
         f'<text x="28" y="34" font-family="{MONO}" font-size="12" letter-spacing="4" fill="{DIM}">LANGUAGES  ·  BY REPOSITORY</text>']
    x = 28; bw = W - 56
    for i, (name, v) in enumerate(top):
        w = bw * v / tot
        s.append(f'<rect x="{x:.1f}" y="52" width="{max(w-2,1):.1f}" height="10" rx="3" fill="{pal[i]}">{fade_in(i*.2)}</rect>')
        x += w
    for i, (name, v) in enumerate(top):
        cx = 28 + (i % 4) * 240; cy = 96 + (i // 4) * 28
        s.append(f'<circle cx="{cx+4}" cy="{cy-4}" r="4" fill="{pal[i]}"/><text x="{cx+16}" y="{cy}" font-family="{SANS}" font-size="13" fill="{TXT}">{esc(name)}</text><text x="{cx+16+len(name)*7.4+8}" y="{cy}" font-family="{MONO}" font-size="11" fill="{DIM}">{v/tot*100:.0f}%</text>')
    s.append("</svg>")
    open(os.path.join(OUT, "langs.svg"), "w").write("\n".join(s))

def stats_svg(days, repos):
    total = sum(d["n"] for d in days); active = sum(1 for d in days if d["n"] > 0)
    cur, longest = streaks(days); best = max(d["n"] for d in days)
    own = [r for r in repos if not r["fork"]]
    stars = sum(r["stars"] for r in own)
    lc = collections.Counter(r["lang"] for r in own if r["lang"])
    top = lc.most_common(1)[0][0] if lc else "—"
    m = [("CONTRIBUTIONS", f"{total:,}", "last 12 months"), ("CURRENT STREAK", str(cur), "days"), ("LONGEST STREAK", str(longest), "days  ·  12 months"), ("ACTIVE DAYS", str(active), f"of {len(days)}"),
         ("REPOSITORIES", str(len(own)), "original, public"), ("STARS EARNED", str(stars), "across repos"), ("BEST DAY", str(best), "contributions"), ("TOP LANGUAGE", top, "by repository")]
    W, H = 1000, 262; cw = W / 4
    s = [head(W, H), f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="10" fill="{PANEL}" stroke="{LINE}"/>',
         f'<rect x="20" y="{H/2}" width="{W-40}" height="1" fill="{LINE}"/>']
    for i in range(1, 4): s.append(f'<rect x="{i*cw}" y="24" width="1" height="{H-48}" fill="{LINE}"/>')
    for i, (lab, val, sub) in enumerate(m):
        c, r = i % 4, i // 4; x = c * cw + 28; y = 26 + r * (H / 2)
        size = 40 if len(val) <= 5 else 30
        s.append(f'<g>{fade_in(i*.15)}'
                 f'<text x="{x}" y="{y+16}" font-family="{MONO}" font-size="10.5" letter-spacing="3" fill="{AC}">{lab}</text>'
                 f'<text x="{x}" y="{y+64}" font-family="{SANS}" font-weight="200" font-size="{size}" fill="{TXT}">{esc(val)}</text>'
                 f'<text x="{x}" y="{y+84}" font-family="{MONO}" font-size="10.5" fill="{DIM}">{esc(sub)}</text></g>')
    s.append("</svg>")
    open(os.path.join(OUT, "stats.svg"), "w").write("\n".join(s))

if __name__ == "__main__":
    days = contributions(); contrib_svg(days)
    repos = repo_list(); stats_svg(days, repos); langs_svg(repos)
    try: repos_svg(pinned())
    except Exception as e: print("pinned failed:", e, file=sys.stderr)
    print("ok", len(days), "days,", len(repos), "repos")
