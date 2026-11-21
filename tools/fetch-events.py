#!/usr/bin/env python3
"""Fetch ticketed events from Ticketmaster for NightGuide clubs.

Strategy (v2, 2026-11-21): the shared Ticketmaster connector key has a
per-user request limit that a full 377-club sweep keeps hitting (429s,
zero usable data for days). Ticketmaster keyword search matches venue
names, so there is no single broad city query that surfaces events at
our specific venues — the savings have to come from searching fewer
venues per night, more cleverly:

- Every night: each city's first two clubs (the curated lists lead with
  the flagship venues) plus any club that produced an event last run.
- Plus a rotating slice of 2 more clubs per city per night, so the
  whole list is covered every few nights (events are fetched 14 days
  out, so rotation never misses an event before it happens).
- Results MERGE with the previous file per club: a club that was
  searched successfully tonight has its old events replaced; a club
  whose search failed (e.g. rate-limited) keeps its still-upcoming
  events. One bad night no longer means a stale or wiped site.
- If the night is a total quota wipeout (zero successful searches),
  the previous file is kept untouched and the run fails loudly.

Polite by design: ~0.6s between API calls, per-club errors are logged
and skipped, the run never crashes on a single failure.
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
STATE_JSON = ROOT / "tools" / "rotation-state.json"
TM = "/opt/hatch/bin/ticketmaster"

FLAGSHIP_PER_CITY = 2     # first N clubs in each city, searched nightly
ROTATION_PER_CITY = 2     # additional clubs per city, rotated nightly
SLEEP_S = 0.6             # politeness between API calls
QUOTA_STORM_LIMIT = 15    # consecutive rate-limits before aborting early

CITY_COUNTRY = {
    "nyc": "US", "miami": "US", "vegas": "US",
    "london": "GB", "berlin": "DE", "paris": "FR", "amsterdam": "NL",
    "ibiza": "ES", "dubai": "AE", "lagos": "NG", "joburg": "ZA",
    "saopaulo": "BR", "tokyo": "JP", "bangkok": "TH", "sydney": "AU",
    "barcelona": "ES", "rome": "IT", "prague": "CZ", "lisbon": "PT",
    "losangeles": "US", "neworleans": "US", "seoul": "KR",
    "singapore": "SG", "bali": "ID", "mexicocity": "MX", "abuja": "NG",
    "kingston": "JM", "montegobay": "JM", "sanjuan": "PR",
    "santodomingo": "DO", "puntacana": "DO", "nassau": "BS",
    "portofspain": "TT", "bridgetown": "BB", "havana": "CU",
    "oranjestad": "AW", "maldives": "MV",
    "capetown": "ZA", "durban": "ZA", "addisababa": "ET",
    "washingtondc": "US",
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
    "barcelona": "Europe/Madrid", "rome": "Europe/Rome",
    "prague": "Europe/Prague", "lisbon": "Europe/Lisbon",
    "losangeles": "America/Los_Angeles", "neworleans": "America/Chicago",
    "seoul": "Asia/Seoul", "singapore": "Asia/Singapore",
    "bali": "Asia/Makassar", "mexicocity": "America/Mexico_City",
    "abuja": "Africa/Lagos",
    "kingston": "America/Jamaica", "montegobay": "America/Jamaica",
    "sanjuan": "America/Puerto_Rico",
    "santodomingo": "America/Santo_Domingo",
    "puntacana": "America/Santo_Domingo", "nassau": "America/Nassau",
    "portofspain": "America/Port_of_Spain",
    "bridgetown": "America/Barbados", "havana": "America/Havana",
    "oranjestad": "America/Aruba", "maldives": "Indian/Maldives",
    "capetown": "Africa/Johannesburg", "durban": "Africa/Johannesburg",
    "addisababa": "Africa/Addis_Ababa",
    "washingtondc": "America/New_York",
}

# Normalized club-name -> extra venue-name fragments that count as a match.
# Add entries here when spot-checks reveal a venue listed under another name.
ALIASES = {
    # e.g. "ministryofsound": ["ministryofsoundclub"],
}

# Statuses we never want to show (event isn't happening).
DEAD_STATUSES = {"cancelled", "postponed"}

# Affiliate tracking for ticket links. Empty = links go out exactly as
# Ticketmaster provides them. Once approved for an affiliate program (e.g.
# Ticketmaster via Impact), set this to the full query-string fragment the
# program gives you, e.g. "utm_source=nightguide&utm_medium=affiliate" —
# the daily sweep then tags every ticket URL automatically.
TM_AFFILIATE_TAG = ""


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


def affiliate_url(url):
    """Append TM_AFFILIATE_TAG to a ticket URL; no-op when the tag is empty."""
    if not url or not TM_AFFILIATE_TAG:
        return url
    base, sep, frag = url.partition("#")
    joiner = "&" if "?" in base else "?"
    return f"{base}{joiner}{TM_AFFILIATE_TAG}{sep}{frag}"


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
    # The connector wraps failures in an envelope like
    # {"ok": false, "status": 429, "error": "..."} with exit code 0 and no
    # "_embedded" key. A successful Ticketmaster reply has no "ok" key, so
    # only an explicit false means the broker failed — without this check a
    # rate-limit reply is silently read as "zero events".
    if isinstance(data, dict) and data.get("ok") is False:
        return None, f"broker error {data.get('status')}: {str(data.get('error', ''))[:120]}"
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
        "url": affiliate_url(ev.get("url", "")),
        "source": "ticketmaster",
    }


def load_previous():
    """Previous events.json as {cityId: [event, ...]}; {} if unreadable."""
    if not EVENTS_JSON.exists():
        return {}
    try:
        prev = json.loads(EVENTS_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {c.get("cityId"): c.get("events", []) for c in prev.get("cities", [])}


def load_state():
    try:
        return json.loads(STATE_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pick_clubs(clubs, prev_events, offset):
    """Club indices to search tonight for one city.

    Flagships (list head) + last run's producers + a rotating slice.
    Returns (indices_in_order, rotating_indices).
    """
    n = len(clubs)
    picked = []
    for i in range(min(FLAGSHIP_PER_CITY, n)):
        picked.append(i)
    producer_names = {e.get("clubName") for e in prev_events}
    for i, club in enumerate(clubs):
        if club.get("name") in producer_names and i not in picked:
            picked.append(i)
    rotating = []
    if n > len(picked):
        start = offset % n
        for k in range(n):
            i = (start + k) % n
            if i not in picked:
                rotating.append(i)
            if len(rotating) >= ROTATION_PER_CITY:
                break
    return picked + rotating, rotating


def main():
    clubs_data = json.loads(CLUBS_JSON.read_text(encoding="utf-8"))
    today = date.today()
    start = (today - timedelta(days=1)).isoformat()   # catch tonight everywhere
    end = (today + timedelta(days=14)).isoformat()
    prev_by_city = load_previous()
    state = load_state()

    out_cities = []
    total_events = 0
    total_searches = 0
    ok_searches = 0
    errors = 0
    consecutive_limits = 0
    aborted = False

    for city in clubs_data["cities"]:
        cid = city["id"]
        cc = CITY_COUNTRY.get(cid)
        if not cc:
            log(f"[{cid}] no country code mapping, skipped")
            continue
        city_name = city["name"]
        clubs = city["clubs"]
        prev_events = prev_by_city.get(cid, [])
        offset = int(state.get(cid, 0) or 0)
        indices, rotating = pick_clubs(clubs, prev_events, offset)

        fresh = []
        seen = set()
        searched_ok = set()
        rotating_ok = False
        for idx in indices:
            if aborted:
                break
            name = clubs[idx].get("name", "")
            evs, err = tm_search(name, city_name, cc, start, end)
            total_searches += 1
            time.sleep(SLEEP_S)
            if err:
                errors += 1
                if "rate" in err or "429" in err or "limit" in err:
                    consecutive_limits += 1
                log(f"[{cid}] {name}: skipped ({err})")
                if consecutive_limits >= QUOTA_STORM_LIMIT:
                    log(f"Quota storm: {consecutive_limits} consecutive "
                        f"rate-limits — aborting the run early.")
                    aborted = True
                continue
            consecutive_limits = 0
            ok_searches += 1
            searched_ok.add(idx)
            if idx in rotating:
                rotating_ok = True
            for ev in evs:
                eid = ev.get("id", "")
                if not eid or eid in seen:
                    continue
                rec = to_record(ev, name, idx)
                if rec and rec["localDate"]:
                    seen.add(eid)
                    fresh.append(rec)

        # Advance the rotation only if this city's slice actually ran.
        if rotating_ok and clubs:
            state[cid] = (offset + ROTATION_PER_CITY) % len(clubs)

        # Merge: previous events survive unless their club was searched
        # successfully tonight (fresh results replace them) or the event
        # has fallen out of the window.
        merged = list(fresh)
        merged_ids = {e["id"] for e in merged}
        for e in prev_events:
            if e.get("clubIndex") in searched_ok:
                continue
            if not (start <= (e.get("localDate") or "") <= end):
                continue
            if e.get("id") in merged_ids:
                continue
            merged.append(e)
            merged_ids.add(e.get("id"))
        merged.sort(key=lambda e: (e["localDate"], e["localTime"] or ""))
        total_events += len(merged)
        log(f"[{cid}] {city_name}: {len(fresh)} fresh, {len(merged)} total "
            f"after merge ({len(indices)} clubs searched)")
        out_cities.append({
            "cityId": cid,
            "timezone": CITY_TIMEZONE.get(cid, ""),
            "events": merged,
        })
        if aborted:
            # Remaining cities keep their previous events untouched.
            for rest in clubs_data["cities"]:
                rid = rest["id"]
                if rid in {c["cityId"] for c in out_cities} or rid == cid:
                    continue
                kept = [e for e in prev_by_city.get(rid, [])
                        if start <= (e.get("localDate") or "") <= end]
                total_events += len(kept)
                out_cities.append({
                    "cityId": rid,
                    "timezone": CITY_TIMEZONE.get(rid, ""),
                    "events": kept,
                })
            break

    # Total-wipeout guard: if not one search succeeded, this run learned
    # nothing — keep the previous file exactly as it was and fail loudly.
    if ok_searches == 0:
        log("REFUSING to overwrite events.json: 0 successful searches "
            "(quota wipeout). Keeping the previous file.")
        return 1

    # Order cities as in clubs.json for a stable file.
    order = {c["id"]: i for i, c in enumerate(clubs_data["cities"])}
    out_cities.sort(key=lambda c: order.get(c["cityId"], 999))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cities": out_cities,
    }
    EVENTS_JSON.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    STATE_JSON.write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
    log(f"DONE: {total_events} events across {len(out_cities)} cities "
        f"({ok_searches}/{total_searches} searches ok, {errors} errored). "
        f"Wrote {EVENTS_JSON}")


if __name__ == "__main__":
    sys.exit(main())
