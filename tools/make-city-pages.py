#!/usr/bin/env python3
"""Generate static per-city SEO pages for NightGuide from data/clubs.json.

Writes cities/<slug>/index.html for every city (full club details rendered
server-side so Google can read them), and regenerates sitemap.xml including
the city URLs. Run from the repo root:  python3 tools/make-city-pages.py
"""
import html
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://nightguide.club"
TODAY = "2026-10-29"

# Pretty URL slugs per city id (clubs.json ids are compact for the app).
SLUGS = {
    "london": "london", "lagos": "lagos", "dubai": "dubai", "nyc": "new-york",
    "berlin": "berlin", "ibiza": "ibiza", "miami": "miami", "vegas": "las-vegas",
    "paris": "paris", "amsterdam": "amsterdam", "tokyo": "tokyo",
    "bangkok": "bangkok", "saopaulo": "sao-paulo", "joburg": "johannesburg",
    "sydney": "sydney", "barcelona": "barcelona", "rome": "rome",
    "prague": "prague", "lisbon": "lisbon", "losangeles": "los-angeles",
    "neworleans": "new-orleans", "seoul": "seoul", "singapore": "singapore",
    "bali": "bali", "mexicocity": "mexico-city", "abuja": "abuja",
}
COUNTRY_NAME = {
    "US": "United States", "GB": "United Kingdom", "DE": "Germany",
    "FR": "France", "NL": "Netherlands", "ES": "Spain",
    "AE": "United Arab Emirates", "NG": "Nigeria", "ZA": "South Africa",
    "BR": "Brazil", "JP": "Japan", "TH": "Thailand", "AU": "Australia",
    "IT": "Italy", "CZ": "Czechia", "PT": "Portugal", "KR": "South Korea",
    "SG": "Singapore", "ID": "Indonesia", "MX": "Mexico",
}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return s or "club"


def load_country_codes():
    text = (ROOT / "tools" / "fetch-events.py").read_text(encoding="utf-8")
    block = re.search(r"CITY_COUNTRY\s*=\s*\{(.*?)\}", text, re.S).group(1)
    return dict(re.findall(r'"(\w+)":\s*"(\w+)"', block))


CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#070310;color:#f2edf9;font-family:Inter,system-ui,sans-serif;line-height:1.55}
a{color:#7be9ff}
.wrap{max-width:820px;margin:0 auto;padding:0 18px 48px}
.brand{display:flex;align-items:center;gap:10px;padding:22px 0 6px;text-decoration:none}
.brand .moon{font-size:26px}
.brand .name{font-family:Anton,Impact,sans-serif;font-size:26px;letter-spacing:2px;color:#fff;text-transform:uppercase}
.brand .name span{color:#ff7ad9}
.crumbs{font-size:13px;color:#a99fc4;margin:4px 0 18px}
.crumbs a{color:#a99fc4}
h1{font-family:Anton,Impact,sans-serif;font-weight:400;font-size:40px;line-height:1.1;margin:8px 0 6px;text-transform:uppercase;letter-spacing:1px}
.sub{color:#cfc4ea;font-size:16px;margin:0 0 14px}
.intro{color:#e6def7;font-size:16px}
.cta{display:inline-block;margin:14px 10px 6px 0;padding:12px 20px;border-radius:999px;background:linear-gradient(90deg,#ff3ea5,#7b2ff7);color:#fff;font-weight:700;text-decoration:none}
.cta.ghost{background:none;border:1px solid #7b2ff7;color:#e6def7}
h2.sec{font-family:Anton,Impact,sans-serif;font-weight:400;font-size:24px;letter-spacing:1px;text-transform:uppercase;margin:34px 0 12px}
.club{border:1px solid #2c1e52;border-radius:16px;padding:18px 18px 8px;margin:0 0 16px;background:linear-gradient(180deg,#120826,#0b0518)}
.club h3{font-family:Anton,Impact,sans-serif;font-weight:400;font-size:22px;letter-spacing:.5px;margin:0 0 2px;text-transform:uppercase}
.club .area{color:#a99fc4;font-size:14px;margin:0 0 8px}
.chips{margin:0 0 10px}
.chip{display:inline-block;border:1px solid #3d2a75;border-radius:999px;padding:2px 10px;font-size:12px;color:#cfc4ea;margin:0 6px 6px 0;text-transform:capitalize}
.club p.desc{margin:0 0 10px;color:#e6def7}
dl{display:grid;grid-template-columns:110px 1fr;gap:4px 12px;margin:0 0 12px;font-size:14px}
dt{color:#a99fc4;font-weight:600}
dd{margin:0;color:#f2edf9}
dd ul{margin:0;padding-left:16px}
.citygrid{display:flex;flex-wrap:wrap;gap:8px}
.citygrid a{border:1px solid #3d2a75;border-radius:999px;padding:6px 14px;text-decoration:none;color:#e6def7;font-size:14px}
.faq dt{font-size:16px;color:#fff;margin-top:14px}
.faq dd{font-size:15px;color:#e6def7;margin:4px 0 0}
footer{border-top:1px solid #2c1e52;margin-top:36px;padding-top:16px;color:#a99fc4;font-size:13px}
"""


def club_article(club, city_name):
    rows = []
    if club.get("hours"):
        rows.append(("Hours", esc(club["hours"])))
    if club.get("djs"):
        lis = "".join(f"<li>{esc(d)}</li>" for d in club["djs"])
        rows.append(("DJs & nights", f"<ul>{lis}</ul>"))
    if club.get("dressCode"):
        rows.append(("Dress code", esc(club["dressCode"])))
    if club.get("entry"):
        rows.append(("Entry", esc(club["entry"])))
    if club.get("prices"):
        rows.append(("Prices", esc(club["prices"])))
    if club.get("age"):
        rows.append(("Age policy", esc(club["age"])))
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    genres = "".join(f'<span class="chip">{esc(g)}</span>' for g in club.get("genres", []))
    tier = "$" * int(club.get("priceTier") or 0)
    meta = esc(club.get("area", ""))
    if tier:
        meta = f"{meta} · {tier}" if meta else tier
    return f"""<article class="club" id="{slugify(club['name'])}">
<h3>{esc(club['name'])}</h3>
<p class="area">{meta} · {esc(city_name)}</p>
<p class="chips">{genres}</p>
<p class="desc">{esc(club.get('description', ''))}</p>
<dl>{dl}</dl>
</article>"""


def city_page(city, all_cities, codes):
    cid = city["id"]
    slug = SLUGS[cid]
    name = city["name"]
    iso = codes.get(cid, "")
    country = COUNTRY_NAME.get(iso, "")
    clubs = city["clubs"]
    n = len(clubs)
    url = f"{BASE}/cities/{slug}/"
    title = f"Best Nightclubs in {name} — Hours, Dress Codes & Entry Prices | NightGuide"
    top_names = ", ".join(c["name"] for c in clubs[:3])
    desc = (f"The {n} best nightclubs in {name}: opening hours, DJs, dress codes, "
            f"entry prices and house rules for {top_names} and more. Know before you go.")
    genre_counts = Counter(g for c in clubs for g in c.get("genres", []))
    top_genres = ", ".join(g for g, _ in genre_counts.most_common(4))
    intro = (f"Planning a night out in {esc(name)}? NightGuide lists {n} of the city's "
             f"best nightclubs — including {esc(top_names)} — with the details that decide "
             f"a night: opening hours, resident DJs and regular nights, dress codes, entry "
             f"prices and house rules. The sounds of {esc(name)} right now: {esc(top_genres)}. "
             f"Listings are curated from public sources; hours and lineups change, so check "
             f"the club before you head out.")
    others = []
    for c in all_cities:
        if c["id"] == cid:
            continue
        others.append(f'<a href="{BASE}/cities/{SLUGS[c["id"]]}/">{esc(c.get("flag", ""))} {esc(c["name"])}</a>')
    others_html = "\n".join(others)
    articles = "\n".join(club_article(c, name) for c in clubs)
    faq = [
        (f"What are the best nightclubs in {name}?",
         f"NightGuide's curated list for {name} includes {top_names} among its {n} listed "
         f"clubs. Each listing above shows hours, DJs, dress code, entry prices and rules "
         f"so you can compare before you go."),
        (f"What time do nightclubs in {name} close?",
         f"Closing times vary by venue and by night. Every listing on this page shows that "
         f"club's typical opening hours, so you can plan your night around them."),
        (f"Is there a dress code for clubs in {name}?",
         f"Most {name} clubs set their own policy, from come-as-you-are to smart dress. "
         f"Each NightGuide listing includes the club's stated dress code."),
    ]
    faq_html = "\n".join(f"<dt>{esc(q)}</dt><dd>{esc(a)}</dd>" for q, a in faq)
    item_list = {
        "@type": "ItemList",
        "name": f"Best nightclubs in {name}",
        "numberOfItems": n,
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "item": {
                    "@type": "NightClub",
                    "name": c["name"],
                    "description": c.get("description", ""),
                    "priceRange": "$" * int(c.get("priceTier") or 1),
                    "address": {
                        "@type": "PostalAddress",
                        "addressLocality": name,
                        "addressRegion": c.get("area", ""),
                        "addressCountry": iso,
                    },
                    "url": f"{url}#{slugify(c['name'])}",
                },
            }
            for i, c in enumerate(clubs)
        ],
    }
    faq_ld = {
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq
        ],
    }
    ld = {"@context": "https://schema.org", "@graph": [item_list, faq_ld]}
    place = f"{name}, {country}" if country else name
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="NightGuide">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{BASE}/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{BASE}/og-image.png">
<link rel="icon" type="image/png" sizes="512x512" href="/favicon.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<meta name="theme-color" content="#070310">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
<script type="application/ld+json">
{json.dumps(ld, indent=1, ensure_ascii=False)}
</script>
</head>
<body>
<div class="wrap">
<a class="brand" href="{BASE}/"><span class="moon">🌙</span><span class="name">Night<span>Guide</span></span></a>
<p class="crumbs"><a href="{BASE}/">Home</a> › City guides › {esc(name)}</p>
<h1>Best nightclubs in {esc(name)}</h1>
<p class="sub">{esc(city.get('flag', ''))} {esc(place)} · {n} clubs · hours, DJs, dress codes, entry prices & rules</p>
<p class="intro">{intro}</p>
<a class="cta" href="{BASE}/?city={cid}">Open {esc(name)} in the interactive guide</a>
<a class="cta ghost" href="{BASE}/">What's on tonight</a>
<h2 class="sec">The {n} clubs</h2>
{articles}
<h2 class="sec">{esc(name)} nightlife FAQ</h2>
<dl class="faq">
{faq_html}
</dl>
<h2 class="sec">More city guides</h2>
<div class="citygrid">
{others_html}
</div>
<footer>
<p>Club details are curated from public sources. Hours, lineups and prices change — check the club before heading out.</p>
<p><a href="{BASE}/">NightGuide home</a> · <a href="{BASE}/privacy.html">Privacy Policy</a> · <a href="{BASE}/terms.html">Terms of Use</a></p>
</footer>
</div>
<script data-goatcounter="https://nightguide.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>
</body>
</html>
"""


def write_sitemap(cities):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    def url(loc, lastmod, freq, prio):
        lines.extend(["  <url>", f"    <loc>{loc}</loc>",
                      f"    <lastmod>{lastmod}</lastmod>",
                      f"    <changefreq>{freq}</changefreq>",
                      f"    <priority>{prio}</priority>", "  </url>"])
    url(f"{BASE}/", TODAY, "daily", "1.0")
    for c in cities:
        url(f"{BASE}/cities/{SLUGS[c['id']]}/", TODAY, "monthly", "0.8")
    url(f"{BASE}/privacy.html", "2026-10-18", "yearly", "0.3")
    url(f"{BASE}/terms.html", "2026-10-18", "yearly", "0.3")
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    data = json.loads((ROOT / "data" / "clubs.json").read_text(encoding="utf-8"))
    cities = data["cities"]
    codes = load_country_codes()
    missing = [c["id"] for c in cities if c["id"] not in SLUGS]
    if missing:
        raise SystemExit(f"Missing slugs for: {missing}")
    for city in cities:
        out = ROOT / "cities" / SLUGS[city["id"]] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(city_page(city, cities, codes), encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)} ({len(city['clubs'])} clubs)")
    write_sitemap(cities)
    print(f"sitemap.xml regenerated with {len(cities)} city URLs")


if __name__ == "__main__":
    main()
