#!/usr/bin/env python3
"""Fetch ticketed events from Ticketmaster for NightGuide clubs.

For each club in data/clubs.json, search Ticketmaster for events at that
venue over the next ~2 weeks, then keep only events whose venue name matches
the club name (normalized). Writes data/events.json.

Polite by design: ~0.3s between API calls, per-club errors are logged and
skipped, the run never crashes on a single failure.
"""
import json
import re
import subprocess
import sys
import time
import unicodedata
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLUBS_JSON = ROOT / "data" / "clubs.json"
EVENTS_JSON = ROOT / "data" / "events.json"
TM = "/opt/hatch/bin/ticketmaster"

CITY_COUNTRY = {
    "nyc": "US", "miami": "US", "vegas": "US",
    "london": "GB", "berlin": "DE", "paris": "FR", "amsterdam": "NL",
    "ibiza": "ES", "dubai": "AE", "lagos": "NG", "joburg": "ZA",
    "saopaulo": "BR", "tokyo": "JP", "bangkok": "TH", "sydney": "AU",
}
CITY_TIMEZONE = {
    "nyc": "America/New_York", "miami": "America/New_York",
    "vegas": "America/Los_Angeles",
    "london": "Europe/London", "berlin": "Europe/Berlin",
    "paris": "Europe/Paris", "amsterdam": "Europe/Amsterdam",
    "ibiza": "Europe/Madrid", "dubai": "Asia/Dubai",
    "lagos": "Africa/Lagos", "joburg": "Africa/Johannesburg",
    "saopaulo": "America/Sao_Paulo", "tokyo": "Asia/Tokyo",
    "bangkok": "Asia/Bangkok", "sydney": "Australia/Sydney",
}

# Normalized club-name -> extra venue-name fragments that count as a match.
# Add entries here when spot-checks reveal a venue listed under another name.
ALIASES = {
    # e.g. "ministryofsound": ["ministryofsoundclub"],
}

# Statuses we never want to show (event isn't happening).
DEAD_STATUSES = {"cancelled", "postponed"}


def log(msg):
    print(msg, flush=True)


def normalize(s):
    """Lowercase, strip accents/punctuation/spaces and a leading 'the'."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def venue_matches(club_name, venue_name):
    cn, vn = normalize(club_name), normalize(venue_name)
    if not cn or not vn:
        return False
    if len(cn) < 4:
        return cn == vn  # tiny names: exact match only, avoid false positives
    if cn in vn or vn in cn:
        return True
    for alias in ALIASES.get(cn, []):
        a = normalize(alias)
        if a and (a in vn or vn in a):
            return True
    return False


def tm_search(keyword, city, country, start, end):
    cmd = [TM, "search-events", "--keyword", keyword, "--city", city,
           "--country-code", country, "--start-date", start, "--end-date", end,
           "--size", "20"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    except Exception as e:  # timeout, missing binary, ...
        return None, f"exec failed: {e}"
    if p.returncode != 0:
        err = (p.stderr or p.stdout or "").strip()
        low = err.lower()
        if "429" in err or "rate" in low or "limit" in low:
            return None, "rate-limited"
        return None, f"exit {p.returncode}: {err[:180]}"
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError:
        return None, "invalid JSON from CLI"
    return data.get("_embedded", {}).get("events", []), None


def to_record(ev, club_name, club_idx):
    dates = ev.get("dates", {}) or {}
    start = dates.get("start", {}) or {}
    status = (dates.get("status", {}) or {}).get("code", "")
    if status in DEAD_STATUSES:
        return None
    venues = (ev.get("_embedded", {}) or {}).get("venues", []) or []
    venue_name = venues[0].get("name", "") if venues else ""
    if not venue_matches(club_name, venue_name):
        return None
    tz = dates.get("timezone") or (venues[0].get("timezone") if venues else "") or ""
    return {
        "id": ev.get("id", ""),
        "name": ev.get("name", ""),
        "clubName": club_name,
        "clubIndex": club_idx,
        "localDate": start.get("localDate", ""),
        "localTime": start.get("localTime") or None,
        "timezone": tz,
        "venue": venue_name,
        "url": ev.get("url", ""),
        "source": "ticketmaster",
    }


def main():
    clubs_data = json.loads(CLUBS_JSON.read_text(encoding="utf-8"))
    today = date.today()
    start = (today - timedelta(days=1)).isoformat()   # catch tonight everywhere
    end = (today + timedelta(days=14)).isoformat()

    out_cities = []
    total_events = 0
    errors = 0
    for city in clubs_data["cities"]:
        cid = city["id"]
        cc = CITY_COUNTRY.get(cid)
        if not cc:
            log(f"[{cid}] no country code mapping, skipped")
            continue
        city_name = city["name"]
        seen = set()
        events = []
        matched = 0
        for idx, club in enumerate(city["clubs"]):
            name = club.get("name", "")
            evs, err = tm_search(name, city_name, cc, start, end)
            time.sleep(0.3)
            if err:
                errors += 1
                log(f"[{cid}] {name}: skipped ({err})")
                continue
            for ev in evs:
                eid = ev.get("id", "")
                if not eid or eid in seen:
                    continue
                rec = to_record(ev, name, idx)
                if rec and rec["localDate"]:
                    seen.add(eid)
                    events.append(rec)
                    matched += 1
        events.sort(key=lambda e: (e["localDate"], e["localTime"] or ""))
        total_events += len(events)
        log(f"[{cid}] {city_name}: {len(events)} events matched")
        out_cities.append({
            "cityId": cid,
            "timezone": CITY_TIMEZONE.get(cid, ""),
            "events": events,
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cities": out_cities,
    }
    EVENTS_JSON.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    log(f"DONE: {total_events} events across {len(out_cities)} cities "
        f"({errors} club searches errored/skipped). Wrote {EVENTS_JSON}")


if __name__ == "__main__":
    sys.exit(main())
