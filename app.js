// NightGuide — city-by-city nightclub discovery
let DATA = { cities: [] };
let EVENTS = { cities: [] };
let activeCity = null;
let activeView = "clubs"; // "clubs" | "coming-up"

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function init() {
  const res = await fetch("data/clubs.json");
  DATA = await res.json();
  try {
    const eres = await fetch("data/events.json");
    if (eres.ok) EVENTS = await eres.json();
  } catch (e) { /* events are optional; the view degrades gracefully */ }
  buildCityBar();
  buildGenreFilter();
  if (DATA.cities.length) {
    const params = new URLSearchParams(location.search);
    const startCity = params.get("city");
    selectCity(DATA.cities.some(c => c.id === startCity) ? startCity : DATA.cities[0].id);
    // Deep links from city pages: ?city=<id>&view=coming-up
    // ("tonight" is accepted as a legacy alias for the old view name.)
    const startView = params.get("view");
    if (["coming-up", "comingup", "events", "tonight"].includes(startView)) setView("coming-up");
  }
  wireEvents();
}

function buildCityBar() {
  const bar = $("city-bar");
  bar.innerHTML = "";
  DATA.cities.forEach(c => {
    const b = document.createElement("button");
    b.className = "city-btn";
    b.textContent = `${c.flag || ""} ${c.name}`.trim();
    b.dataset.city = c.id;
    b.onclick = () => selectCity(c.id);
    bar.appendChild(b);
  });
}

function buildGenreFilter() {
  const genres = new Set();
  DATA.cities.forEach(c => c.clubs.forEach(k => (k.genres || []).forEach(g => genres.add(g))));
  const sel = $("filter-genre");
  [...genres].sort().forEach(g => {
    const o = document.createElement("option");
    o.value = g; o.textContent = g;
    sel.appendChild(o);
  });
}

function selectCity(id) {
  activeCity = DATA.cities.find(c => c.id === id);
  document.querySelectorAll(".city-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.city === id));
  updateEventsToggle();
  if (activeView === "coming-up") {
    // A city with no upcoming events has no events view at all.
    if (!upcomingEvents().length) { setView("clubs"); return; }
    renderEvents();
  }
  else renderList();
}

// ---------- Coming up / events view ----------

// The "Coming up" toggle only exists for cities that actually have
// upcoming events — no empty section, no dead end.
function updateEventsToggle() {
  const btn = $("view-coming-up");
  if (btn) btn.classList.toggle("hidden", !upcomingEvents().length);
}

function setView(v) {
  if (v === "tonight") v = "coming-up"; // legacy alias
  if (v === "coming-up" && !upcomingEvents().length) v = "clubs";
  activeView = v;
  $("view-clubs").classList.toggle("active", v === "clubs");
  $("view-coming-up").classList.toggle("active", v === "coming-up");
  $("view-clubs").setAttribute("aria-selected", v === "clubs");
  $("view-coming-up").setAttribute("aria-selected", v === "coming-up");
  const clubsMode = v === "clubs";
  ["search", "filter-genre", "filter-price"].forEach(id => {
    const el = $(id);
    const wrap = el.closest(".search-row, .filters");
    if (wrap) wrap.classList.toggle("hidden", !clubsMode);
  });
  $("club-list").classList.toggle("hidden", !clubsMode);
  $("events-view").classList.toggle("hidden", clubsMode);
  if (clubsMode) renderList();
  else renderEvents();
  window.scrollTo(0, 0);
}

// "Today" in the city's own timezone — not the visitor's.
function cityTodayISO(tz) {
  try {
    return new Intl.DateTimeFormat("en-CA", {
      timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit"
    }).format(new Date());
  } catch (e) { return new Date().toISOString().slice(0, 10); }
}

function addDaysISO(iso, n) {
  const d = new Date(iso + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function fmtTime(t) {
  if (!t) return "";
  const m = t.match(/^(\d{1,2}):(\d{2})/);
  if (!m) return t;
  let h = +m[1];
  const ap = h >= 12 ? "PM" : "AM";
  h = h % 12 || 12;
  return `${h}:${m[2]} ${ap}`;
}

function fmtDateLabel(iso) {
  const d = new Date(iso + "T12:00:00Z");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
}

function cityEvents() {
  const c = (EVENTS.cities || []).find(x => x.cityId === (activeCity && activeCity.id));
  return { timezone: (c && c.timezone) || "", events: (c && c.events) || [] };
}

// Upcoming = today through the next 30 days, in the city's own timezone.
// Past events are never presented as upcoming.
function upcomingEvents() {
  if (!activeCity) return [];
  const { timezone, events } = cityEvents();
  const today = cityTodayISO(timezone || undefined);
  const end = addDaysISO(today, 30);
  const byTime = (a, b) => (a.localDate < b.localDate ? -1 : a.localDate > b.localDate ? 1 : (a.localTime || "") < (b.localTime || "") ? -1 : 1);
  return events.filter(e => e.localDate >= today && e.localDate <= end).sort(byTime);
}

function eventRow(e) {
  // Label an event by its own name and its REAL venue (e.venue, as listed
  // by the ticket seller) — never by a nearby club it was matched to.
  // e.g. YAEGER is at Kantine am Berghain, not Berghain; Webster Hall
  // shows are concerts at Webster Hall, not club nights.
  const venue = e.venue || e.clubName || "";
  return `
    <div class="event-row">
      <div>
        <div class="event-name">${esc(e.name)}</div>
        <div class="event-meta">
          <span>📅 ${esc(fmtDateLabel(e.localDate))}</span>
          ${e.localTime ? `<span class="event-time">🕐 ${esc(fmtTime(e.localTime))}</span>` : ""}
          ${venue ? `<span>📍 ${esc(venue)}</span>` : ""}
        </div>
      </div>
      ${e.url ? `<a class="tickets-btn" href="${esc(e.url)}" target="_blank" rel="noopener">🎟 Tickets</a>` : ""}
    </div>`;
}

function renderEvents() {
  const view = $("events-view");
  if (!activeCity) { view.innerHTML = ""; return; }
  const upcoming = upcomingEvents();
  if (!upcoming.length) {
    // Hidden entirely for cities with nothing coming up — the toggle is
    // hidden too (see updateEventsToggle), so this is just a guard.
    view.innerHTML = "";
    return;
  }
  view.innerHTML = `<div><div class="events-section-title">📅 Coming up<span class="date-sub">Next 30 days · ${esc(activeCity.name)} local time</span></div>`
    + upcoming.map(eventRow).join("") + `</div>`;
}

function filteredClubs() {
  if (!activeCity) return [];
  const q = $("search").value.trim().toLowerCase();
  const genre = $("filter-genre").value;
  const price = $("filter-price").value;
  return activeCity.clubs.filter(k => {
    if (genre && !(k.genres || []).includes(genre)) return false;
    if (price && String(k.priceTier) !== price) return false;
    if (q) {
      const hay = [k.name, k.area, ...(k.genres || []), k.description || ""].join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function priceLabel(tier) {
  return "$".repeat(tier || 1);
}

// Directions are built only from fields that exist in the data (club name,
// area, city name) — never a fabricated address. Address and website render
// only when those fields are present on the club record.
function mapsUrl(k) {
  const q = [k.name, k.area, activeCity ? activeCity.name : ""].filter(Boolean).join(" ");
  return "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(q);
}

function clubActions(k) {
  const links = [`<a class="action-btn directions-btn" href="${esc(mapsUrl(k))}" target="_blank" rel="noopener">📍 Directions</a>`];
  if (k.website) links.push(`<a class="action-btn website-btn" href="${esc(k.website)}" target="_blank" rel="noopener">🌐 Website</a>`);
  return `
    ${k.address ? `<div class="club-address">📍 ${esc(k.address)}</div>` : ""}
    <div class="club-actions">${links.join("")}</div>`;
}

function renderList() {
  const list = $("club-list");
  const clubs = filteredClubs();
  const rc = $("result-count");
  if (rc) rc.textContent = clubs.length
    ? `${clubs.length} spot${clubs.length === 1 ? "" : "s"} · ${activeCity?.name || ""}`
    : "";
  if (!clubs.length) {
    list.innerHTML = `<div class="empty">No clubs match your filters in ${esc(activeCity?.name || "")}.</div>`;
    return;
  }
  list.innerHTML = clubs.map((k, i) => `
    <article class="club-card" data-idx="${i}" tabindex="0">
      <h3>${esc(k.name)}</h3>
      <div class="club-area">${esc(k.area)}</div>
      <div class="genre-tags">${(k.genres || []).map(g => `<span class="genre-tag">${esc(g)}</span>`).join("")}</div>
      <div class="club-meta">
        <span>${esc(k.hours || "")}</span>
        <span class="price-tier">${priceLabel(k.priceTier)}</span>
      </div>
      ${clubActions(k)}
    </article>`).join("");
  list.querySelectorAll(".club-actions a").forEach(a =>
    a.addEventListener("click", e => e.stopPropagation()));
  list.querySelectorAll(".club-card").forEach(card => {
    const open = () => showDetail(clubs[+card.dataset.idx]);
    card.onclick = open;
    card.onkeydown = e => { if (e.key === "Enter") open(); };
  });
}

function showDetail(k) {
  const djs = (k.djs && k.djs.length)
    ? `<ul>${k.djs.map(d => `<li>${esc(d)}</li>`).join("")}</ul>` : "<p>Check the club's channels for this week's lineup.</p>";
  $("detail-body").innerHTML = `
    <div class="detail-hero">
      <h2>${esc(k.name)}</h2>
      <div class="area">${esc(k.area)} · ${esc(activeCity.name)}</div>
      <div class="genre-tags" style="margin-top:10px">${(k.genres || []).map(g => `<span class="genre-tag">${esc(g)}</span>`).join("")}</div>
    </div>
    ${clubActions(k)}
    <div class="info-grid">
      <div class="info-card"><h4>🕐 Hours</h4><p>${esc(k.hours || "—")}</p></div>
      <div class="info-card"><h4>🎧 DJs & Nights</h4>${djs}</div>
      <div class="info-card"><h4>👔 Dress Code</h4><p>${esc(k.dressCode || "—")}</p></div>
      <div class="info-card"><h4>🚪 Entry & Rules</h4><p>${esc(k.entry || "—")}</p>${k.age ? `<p>Age: ${esc(k.age)}</p>` : ""}</div>
      <div class="info-card"><h4>💰 Prices</h4><p>${esc(k.prices || "—")}</p></div>
      <div class="info-card"><h4>✨ Vibe</h4><p>${esc(k.description || "")}</p></div>
    </div>
    <p class="verified">Details curated from public sources · verify before heading out</p>`;
  $("detail").classList.remove("hidden");
  window.scrollTo(0, 0);
}

function wireEvents() {
  $("btn-back").onclick = () => $("detail").classList.add("hidden");
  $("view-clubs").onclick = () => setView("clubs");
  $("view-coming-up").onclick = () => setView("coming-up");
  ["search", "filter-genre", "filter-price"].forEach(id => {
    $(id).addEventListener("input", renderList);
    $(id).addEventListener("change", renderList);
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") $("detail").classList.add("hidden");
  });
}

init();
