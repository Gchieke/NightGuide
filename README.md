# NightGuide 🌃

**Know before you go.** A worldwide nightclub discovery guide — browse clubs city by city, with hours, DJ lineups, dress codes, entry rules, and prices.

## Launch cities

New York · Miami · Las Vegas · London · Berlin · Paris · Amsterdam · Ibiza · Dubai · Lagos · Johannesburg · São Paulo · Tokyo · Bangkok · Sydney

## How it works

A mobile-first static web app. Club data lives in `data/clubs.json` — curated from public sources, one entry per club:

```json
{
  "name": "fabric",
  "area": "Farringdon",
  "genres": ["techno", "house"],
  "hours": "Sat 11pm–6am",
  "dressCode": "Come as you are",
  "entry": "Advance tickets recommended",
  "prices": "£10–£35",
  "priceTier": 2,
  "age": "18+",
  "djs": ["Craig Richards", "Terry Francis"],
  "description": "..."
}
```

## Roadmap

- [ ] All 15 launch cities populated
- [ ] Live deploy
- [ ] Supabase backend (clubs/events tables, user favorites, reviews)
- [ ] Venue self-service (clubs claim and update their own listings)
- [ ] Native apps (Capacitor, iOS + Android)

Club details change — hours, lineups, and prices should always be verified with the venue before heading out.
