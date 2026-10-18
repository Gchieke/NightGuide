# NightGuide — App Store & Google Play Listing

Bundle ID (both stores): `app.nightguide`
Privacy policy URL: https://nightguide.club/privacy.html
Support URL: https://nightguide.club

## Apple App Store

- **Name:** NightGuide — Nightclub Guide (28 chars max — this is 28)
- **Subtitle:** Know before you go. 144 clubs. (30 chars max — this is 30)
- **Category:** Travel (primary), Entertainment (secondary)
- **Keywords:** nightlife,clubs,club guide,nightlife guide,dj,travel,going out,party
- **Description:**

Know before you go.

NightGuide is a worldwide nightclub guide for travelers and locals. Browse 144 real
clubs across 15 cities — New York, Miami, Las Vegas, London, Berlin, Paris,
Amsterdam, Ibiza, Dubai, Lagos, Johannesburg, São Paulo, Tokyo, Bangkok, Sydney —
with the details that matter before a night out:

- Hours and regular nights
- DJ lineups and music genres
- Dress codes
- Entry rules and guestlist info
- Prices in local currency
- What's on tonight, with ticket links

Mobile-first and searchable, so you can plan the night from the taxi, the airport,
or the hotel lobby.

NightGuide is free. Club details change — always verify hours, lineups, and prices
with the venue before heading out.

- **Review notes for Apple:** No account required — the app opens straight into the
  guide. No in-app purchases. The app lists real nightclubs (venues that serve
  alcohol); no mature imagery. Suggest **17+** rating; the IARC questionnaire will
  confirm.

## Google Play

- **Title:** NightGuide — Nightclub Guide
- **Short description (80 chars):** 144 clubs across 15 cities — hours, DJs, dress codes, entry rules, prices.
- **Full description:** (same as App Store description above)
- **Category:** Travel & Local
- **Tags:** nightlife, clubs, travel, going out, dj
- **Content rating:** 17+ (complete the IARC questionnaire in Play Console — the
  alcohol/nightlife references drive this)
- **Data safety:** v1 collects **no data** — no accounts, no analytics, static app.
  Declare "no data collected" in the Data safety form. Revisit this when venue
  accounts or paid tiers ship.

## Screenshots needed (both stores)

Capture on real devices or simulators at these sizes:
- iPhone 6.7" (1290×2796): 3–10 screenshots — home screen with the city grid,
  a club list with prices, a club detail (hours / DJs / dress code / entry rules),
  the "What's on tonight" feed
- iPhone 6.5" (1242×2688): same set (App Store requires both if supporting those sizes)
- Android phone (1080×1920 min): 2–8 screenshots

## Feature graphic (Google Play, required)

1024×500 PNG — NightGuide wordmark + tagline "Know before you go" on the neon-noir
theme (#0d0d14 background, neon accents from the app).

---

# George's launch checklist

## 1. Developer accounts — ONE enrollment covers both apps

You do not enroll twice. The same Apple Developer membership and the same Play
Console account publish both MoveMate and NightGuide.
- [ ] **Apple Developer Program** — $99/year at developer.apple.com/programs/enroll
  (or the Apple Developer app → Account tab). Enroll as **Individual**: your legal
  name becomes the seller name on the App Store. Needs: Apple ID with 2FA, legal
  name matching your ID, a credit/debit card. Approval usually 1–2 days. Grab the
  **Team ID** (10-char code) from developer.apple.com/account — needed for the
  `APPLE_TEAM_ID` repo secret.
- [ ] **Google Play Console** — $25 one-time at play.google.com/console. Needs:
  Google account, government ID + address/phone for identity verification.
  - ⚠️ **Plan for this:** apps from a new **personal** Play Console account can't
    publish to production until they pass a **closed test with at least 12 testers
    opted in for 14 straight days** — this gate applies per app, so NightGuide
    needs its own 14-day test even after MoveMate's. Recruit testers (friends,
    family, club-goers) as soon as the account exists.

## 2. CI workflows (status as of 2026-10-18)

- [x] `build-android.yml` — already moved to `.github/workflows/` and live. One fix
  still needed: `java-version: 17` → `21` (Capacitor needs 21; 17 fails with
  `invalid source release: 21`). Edit via the github.com pencil icon → commit to
  main. (The redundant `android-actions/setup-android` step that corrupted the
  runner's SDK was already removed.)
- [ ] Move `build-ios.yml` + `export-options.plist` from `.github/pending-workflows/`
  to `.github/workflows/` (same pencil-icon flow) to kick off the iPhone build.
  `build-ios.yml` is already safe: secrets are gated via job-level `env`
  (GitHub rejects `secrets` in `if:` conditions).

## 3. Signing (one-time setup, then CI handles every build)

- [ ] Android: generate an upload keystore (command is in build-android.yml's header),
  add the 4 `ANDROID_*` secrets to the NightGuide repo settings. Next push to main →
  signed AAB artifact.
- [ ] iOS: in Apple Developer → Certificates, Identifiers & Profiles: create an App ID
  for `app.nightguide`, a Distribution certificate, and an App Store provisioning
  profile. Add the 4 `APPLE_*` secrets to the NightGuide repo. Next push to main →
  signed IPA artifact.

## 4. Store listings

- [ ] App Store Connect (appstoreconnect.apple.com): create the app, paste the listing
  above, upload screenshots + 1024×1024 app icon (generated in
  ios/App/App/Assets.xcassets).
- [ ] Play Console: create the app, complete the listing, content rating questionnaire,
  data safety form (declare: **no data collected** in v1), upload the AAB to the
  **internal testing** track first.

## 5. When monetization ships (later — bookmark this)

George's rule: paid tiers and venue fees priced in **local currency** at locally
affordable levels. When venue accounts / featured placements / premium tiers land:
- Add the in-app purchase / paid-subscription declarations to both listings and
  update the Data safety + privacy nutrition labels (accounts, payment data).
- Play's Payments policy: digital goods must use Google Play Billing (15–30% fee —
  factor it into the local-currency pricing).
