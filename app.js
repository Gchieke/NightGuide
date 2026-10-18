// NightGuide — city-by-city nightclub discovery
let DATA = { cities: [] };
let activeCity = null;

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function init() {
  const res = await fetch("data/clubs.json");
  DATA = await res.json();
  buildCityBar();
  buildGenreFilter();
  if (DATA.cities.length) selectCity(DATA.cities[0].id);
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
  renderList();
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
  ["search", "filter-genre", "filter-price"].forEach(id => {
    $(id).addEventListener("input", renderList);
    $(id).addEventListener("change", renderList);
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") $("detail").classList.add("hidden");
  });
}

init();
