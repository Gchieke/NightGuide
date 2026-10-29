// NightGuide — city-by-city nightclub discovery
let DATA = { cities: [] };
let EVENTS = { cities: [] };
let activeCity = null;
let activeView = "clubs"; // "clubs" | "tonight"

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
    const startCity = new URLSearchParams(location.search).get("city");
    selectCity(DATA.cities.some(c => c.id === startCity) ? startCity : DATA.cities[0].id);
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
  if (activeView === "tonight") renderEvents();
  else renderList();
}

// ---------- Tonight / events view ----------

function setView(v) {
  activeView = v;
  $("view-clubs").classList.toggle("active", v === "clubs");
  $("view-tonight").classList.toggle("active", v === "tonight");
  $("view-clubs").setAttribute("aria-selected", v === "clubs");
  $("view-tonight").setAttribute("aria-selected", v === "tonight");
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

function eventRow(e) {
  const club = activeCity.clubs[e.clubIndex];
  const clubLabel = club ? club.name : e.clubName;
  return `
    <div class="event-row">
      <div>
        <div class="event-name">${esc(e.name)}</div>
        <div class="event-meta">
          ${e.localTime ? `<span class="event-time">🕐 ${esc(fmtTime(e.localTime))}</span>` : ""}
          <span>📍 <button class="event-club-btn" data-club="${e.clubIndex}">${esc(clubLabel)}</button></span>
          ${e.venue && club && e.venue !== club.name ? `<span>· ${esc(e.venue)}</span>` : ""}
        </div>
      </div>
      ${e.url ? `<a class="tickets-btn" href="${esc(e.url)}" target="_blank" rel="noopener">🎟 Tickets</a>` : ""}
    </div>`;
}

function fallbackClubs() {
  // The view is never dead: list the city's clubs with their regular hours.
  return `
    <div class="events-fallback-title">No ticketed events listed — the regulars are still open</div>
    ${activeCity.clubs.map((k, i) => `
      <button class="fallback-club" data-club="${i}">
        <span class="fname">${esc(k.name)}</span>
        <span class="fhours">${esc(k.hours || "")}</span>
      </button>`).join("")}`;
}

function renderEvents() {
  const view = $("events-view");
  if (!activeCity) { view.innerHTML = ""; return; }
  const { timezone, events } = cityEvents();
  const today = cityTodayISO(timezone || undefined);
  const weekEnd = addDaysISO(today, 7);
  const byTime = (a, b) => (a.localDate < b.localDate ? -1 : a.localDate > b.localDate ? 1 : (a.localTime || "") < (b.localTime || "") ? -1 : 1);
  const tonight = events.filter(e => e.localDate === today).sort(byTime);
  const week = events.filter(e => e.localDate > today && e.localDate <= weekEnd).sort(byTime);

  let html = "";
  html += `<div><div class="events-section-title">⚡ Tonight<span class="date-sub">${esc(fmtDateLabel(today))} · ${esc(activeCity.name)} local time</span></div>`;
  html += tonight.length
    ? tonight.map(eventRow).join("")
    : `<div class="events-empty"><div class="big">No ticketed events found for tonight</div><p>Ticketmaster has nothing listed at these venues today — but the clubs are still open.</p></div>`;
  html += `</div>`;
  if (week.length) {
    html += `<div><div class="events-section-title">📅 This week<span class="date-sub">Upcoming ticketed events</span></div>`;
    html += week.map(eventRow).join("") + `</div>`;
  }
  html += fallbackClubs();
  view.innerHTML = html;
  view.querySelectorAll("[data-club]").forEach(el => {
    el.onclick = () => {
      const k = activeCity.clubs[+el.dataset.club];
      if (k) showDetail(k);
    };
  });
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
    </article>`).join("");
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
  $("view-tonight").onclick = () => setView("tonight");
  ["search", "filter-genre", "filter-price"].forEach(id => {
    $(id).addEventListener("input", renderList);
    $(id).addEventListener("change", renderList);
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") $("detail").classList.add("hidden");
  });
}

init();
