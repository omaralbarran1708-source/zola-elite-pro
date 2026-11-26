/* ZOLA Elite — interfaz */
"use strict";

// ---------------- utilidades ----------------
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (p, d = 0) => `${(p * 100).toFixed(d)}%`;
const img = (url, name = "") => `/img?u=${encodeURIComponent(url || "")}&n=${encodeURIComponent(name || "")}`;
const ls = {
  get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};
const norm = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const pad = (n) => String(n).padStart(2, "0");
const isoDay = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const todayISO = () => isoDay(new Date());
const addDays = (iso, n) => { const d = new Date(iso + "T12:00:00"); d.setDate(d.getDate() + n); return isoDay(d); };
const WD = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
function dayName(iso) {
  const t = todayISO();
  if (iso === t) return "Hoy";
  if (iso === addDays(t, 1)) return "Mañana";
  if (iso === addDays(t, -1)) return "Ayer";
  const d = new Date(iso + "T12:00:00");
  return WD[d.getDay()];
}
const dayShort = (iso) => { const d = new Date(iso + "T12:00:00"); return `${d.getDate()} ${MES[d.getMonth()]}`; };
const hhmm = (iso) => { if (!iso) return "—"; const d = new Date(iso); return isNaN(d) ? "—" : `${pad(d.getHours())}:${pad(d.getMinutes())}`; };
const FORM_ES = { W: "G", D: "E", L: "P" };
const formHtml = (f) => {
  const s = (f || "").slice(-5);
  if (!s) return '<span class="faint" style="font-size:.74rem">Sin forma</span>';
  return `<div class="form">${[...s].map((c) => `<span class="f${c}" title="${{ W: "Ganó", D: "Empató", L: "Perdió" }[c] || c}">${FORM_ES[c] || c}</span>`).join("")}</div>`;
};
const ZONE = {
  ucl: ["#3b6bff", "Champions / Libertadores"], uel: ["#f59e0b", "Europa League / Sudamericana"],
  uecl: ["#14b8a6", "Conference League"], rel: ["#ef4444", "Descenso"], po: ["#a855f7", "Playoffs"],
  up: ["#1fb556", "Clasificación / ascenso"], oth: ["#6b7280", "Otra zona"],
};
function zoneOf(z) {
  const d = norm(z);
  if (!d) return null;
  if (ZONE[d]) return d;
  if (d.includes("releg") || d.includes("descenso")) return "rel";
  if (d.includes("champions") || d.includes("libertadores")) return "ucl";
  if (d.includes("europa") || d.includes("sudamericana")) return "uel";
  if (d.includes("conference")) return "uecl";
  if (d.includes("play")) return "po";
  if (d.includes("promotion") || d.includes("next round") || d.includes("final")) return "up";
  return "oth";
}
const LEAGUE_PRIORITY = [1, 2, 13, 281, 39, 140, 135, 78, 61, 11, 3, 848, 71, 128, 9, 4];
const TOP_IDS = new Set([39, 140, 135, 78, 61, 2, 3, 848, 13, 11, 1, 9, 4, 281, 71, 128]);
function marketWon(mk, h, a) {
  const t = h + a;
  return ({
    "1": h > a, X: h === a, "2": h < a, "1X": h >= a, X2: h <= a, "12": h !== a,
    "Over 1.5": t > 1, "Under 1.5": t <= 1, "Over 2.5": t > 2, "Under 2.5": t <= 2, "Over 3.5": t > 3, "Under 3.5": t <= 3,
    "BTTS Sí": h > 0 && a > 0, "BTTS No": !(h > 0 && a > 0),
  })[mk];
}
const MK_LABEL = {
  "1": "Gana local", X: "Empate", "2": "Gana visita", "1X": "Local o empate", X2: "Empate o visita", "12": "No hay empate",
  "Over 1.5": "Más de 1.5 goles", "Under 1.5": "Menos de 1.5", "Over 2.5": "Más de 2.5 goles", "Under 2.5": "Menos de 2.5",
  "Over 3.5": "Más de 3.5 goles", "Under 3.5": "Menos de 3.5", "BTTS Sí": "Ambos marcan", "BTTS No": "No marcan ambos",
};

// ---------------- estado ----------------
const S = {
  date: todayISO(), filter: "all", region: "Todas", q: "",
  matches: [], loaded: false, demo: true, notice: null, remaining: null,
  sel: null, detail: null, detailFor: null, tab: "resumen",
  h2h: {}, standings: {}, view: "matches", league: null, mobileDetail: false,
  favs: new Set(ls.get("zola_favs", [])), pins: new Set(ls.get("zola_pins", [])),
  picks: ls.get("zola_picks", []), sim: {},
};
let lastScores = {};

// ---------------- API ----------------
async function getJSON(url) {
  const r = await fetch(url, { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

// ---------------- notificaciones ----------------
function toast(html, cls = "", ms = 3800) {
  const el = document.createElement("div");
  el.className = `toast ${cls}`;
  el.innerHTML = html;
  $("#toasts").appendChild(el);
  setTimeout(() => { el.style.transition = ".3s"; el.style.opacity = 0; setTimeout(() => el.remove(), 300); }, ms);
}

// ---------------- datos ----------------
async function loadMatches({ quiet = false } = {}) {
  if (!quiet) { S.loaded = false; renderView(); }
  try {
    const j = await getJSON(`/api/matches?date=${S.date}`);
    detectGoals(j.matches);
    S.matches = j.matches; S.demo = j.demo; S.notice = j.notice; S.remaining = j.remaining;
  } catch (e) {
    S.matches = S.matches || []; S.notice = "No se pudo conectar con el servidor. Reintentando…";
  }
  S.loaded = true;
  updateChip();
  renderTicker();
  if (S.view === "matches") {
    ensureSelection();
    if (quiet) { renderList(); renderRail(); } else renderView();
    if (S.sel && (S.detailFor !== S.sel || !S.detail)) loadDetail(S.sel);
  } else if (!quiet) renderView();
  settlePicks();
}

function detectGoals(list) {
  const next = {};
  for (const m of list) {
    next[m.match_key] = [m.home_goals, m.away_goals];
    const prev = lastScores[m.match_key];
    if (!prev || !m.live) continue;
    if (m.home_goals > prev[0] || m.away_goals > prev[1]) {
      const home = m.home_goals > prev[0];
      toast(`<img src="${img(home ? m.home_logo : m.away_logo, home ? m.home : m.away)}"> <span>⚽ ¡Gol de <b>${esc(home ? m.home : m.away)}</b>! ${esc(m.home)} ${m.home_goals}-${m.away_goals} ${esc(m.away)}</span>`, "goal", 6000);
      setTimeout(() => { const r = $(`.mrow[data-key="${CSS.escape(m.match_key)}"]`); if (r) r.classList.add("flash"); }, 50);
    }
  }
  lastScores = next;
}

async function loadDetail(key, { quiet = false } = {}) {
  if (!key) return;
  if (!quiet) { S.detail = null; S.detailFor = key; renderDetail(); }
  try {
    const j = await getJSON(`/api/match/${encodeURIComponent(key)}?date=${S.date}`);
    if (S.sel !== key) return;
    S.detail = j; S.detailFor = key;
    if (j.remaining != null) { S.remaining = j.remaining; updateChip(); }
    if (quiet) renderDetail({ keepTab: true }); else renderDetail();
  } catch (e) {
    if (!quiet) { $("#detail") && ($("#detail").innerHTML = emptyHtml("⚠️", "No se pudo cargar el partido", "Intenta de nuevo en unos segundos.")); }
  }
}

async function loadH2H(key) {
  if (S.h2h[key]) return;
  S.h2h[key] = { loading: true };
  try { S.h2h[key] = await getJSON(`/api/h2h?key=${encodeURIComponent(key)}&date=${S.date}`); }
  catch { S.h2h[key] = { matches: [], error: "No disponible" }; }
  if (S.tab === "h2h" && S.sel === key) renderTab();
}

async function loadStandings(leagueId, season, demo) {
  const k = `${leagueId}_${season}`;
  if (S.standings[k]) return S.standings[k];
  S.standings[k] = { loading: true };
  try { S.standings[k] = await getJSON(`/api/standings?league=${leagueId}&season=${season || ""}&demo=${demo ? 1 : 0}`); }
  catch { S.standings[k] = { groups: [], error: "No disponible" }; }
  return S.standings[k];
}

// ---------------- filtros ----------------
function filtered() {
  const q = norm(S.q);
  return S.matches.filter((m) => {
    if (S.region !== "Todas" && !(m.buckets || []).includes(S.region)) return false;
    if (q && !norm(`${m.home} ${m.away} ${m.league} ${m.country}`).includes(q)) return false;
    if (S.filter === "live") return m.live;
    if (S.filter === "upcoming") return !m.live && !m.finished;
    if (S.filter === "finished") return m.finished;
    if (S.filter === "favs") return S.favs.has(m.match_key) || S.pins.has(String(m.league_id));
    return true;
  });
}
function groupByLeague(list) {
  const g = new Map();
  for (const m of list) {
    const k = m.league_id ?? m.league;
    if (!g.has(k)) g.set(k, []);
    g.get(k).push(m);
  }
  const arr = [...g.values()];
  arr.forEach((ms) => ms.sort((a, b) => (b.live - a.live) || (a.finished - b.finished) || String(a.kickoff).localeCompare(String(b.kickoff))));
  const prio = (ms) => {
    const id = ms[0].league_id;
    const pinned = S.pins.has(String(id)) ? 0 : 1;
    const live = ms.some((x) => x.live) ? 0 : 1;
    const p = LEAGUE_PRIORITY.includes(id) ? LEAGUE_PRIORITY.indexOf(id) : (TOP_IDS.has(id) ? 50 : 100);
    return [pinned, live, p, ms[0].league];
  };
  return arr.sort((a, b) => {
    const pa = prio(a), pb = prio(b);
    for (let i = 0; i < pa.length; i++) { if (pa[i] < pb[i]) return -1; if (pa[i] > pb[i]) return 1; }
    return 0;
  });
}
function ensureSelection() {
  const list = filtered();
  if (S.sel && S.matches.some((m) => m.match_key === S.sel)) return;
  const pick = list.find((m) => m.live) || list.find((m) => !m.finished) || list[0];
  S.sel = pick ? pick.match_key : null;
}
const byKey = (k) => S.matches.find((m) => m.match_key === k);

// ---------------- render: comunes ----------------
function emptyHtml(icon, title, sub = "") {
  return `<div class="empty"><div class="i">${icon}</div><b>${title}</b>${sub}</div>`;
}
function updateChip() {
  const c = $("#apichip");
  c.classList.toggle("ok", !S.demo);
  c.querySelector("span").textContent = S.demo ? "Modo demo" : `En vivo${S.remaining != null ? ` · ${S.remaining} consultas` : ""}`;
}
function renderTicker() {
  const live = S.matches.filter((m) => m.live);
  const el = $("#ticker");
  if (!live.length) {
    el.innerHTML = `<span class="tk-lbl" style="background:var(--panel2);color:var(--muted)">Sin partidos en vivo</span><span class="tk-empty">${S.date === todayISO() ? "Te avisaremos aquí cuando empiece uno." : "Estás viendo otro día."}</span>`;
    return;
  }
  el.innerHTML = `<span class="tk-lbl"><span class="pulse" style="background:#fff"></span>${live.length} en vivo</span>` + live.map((m) => `
    <a class="tk" href="#/partido/${encodeURIComponent(m.match_key)}" title="${esc(m.home)} vs ${esc(m.away)} · ${esc(m.league)}">
      <span class="m">${m.status_short === "HT" ? "ET" : `${m.minute}'`}</span>
      <img src="${img(m.home_logo, m.home)}" alt=""><span class="s">${m.home_goals}-${m.away_goals}</span><img src="${img(m.away_logo, m.away)}" alt="">
    </a>`).join("");
}
function statusCell(m) {
  const t = hhmm(m.kickoff);
  if (m.status_short === "HT") return `<div class="mt">${t}<br><span class="lv">ET</span></div>`;
  if (m.live) return `<div class="mt">${t}<br><span class="lv">${m.minute}${m.extra ? "+" + m.extra : ""}'</span></div>`;
  if (m.finished) return `<div class="mt">${t}<br>Final</div>`;
  if (["PST", "CANC", "ABD", "SUSP"].includes(m.status_short)) return `<div class="mt">${t}<br><span class="lv">${esc(m.status_label).slice(0, 6)}</span></div>`;
  return `<div class="mt">${t}<br>-</div>`;
}
function matchRow(m) {
  const started = m.live || m.finished;
  const hw = started && m.home_goals > m.away_goals, aw = started && m.away_goals > m.home_goals;
  const fav = S.favs.has(m.match_key);
  return `<div class="mrow${m.match_key === S.sel ? " sel" : ""}" data-key="${esc(m.match_key)}" data-act="open" role="button" tabindex="0">
    ${statusCell(m)}
    <div class="mteams">
      <div class="tl${hw ? " w" : ""}"><img src="${img(m.home_logo, m.home)}" alt="" loading="lazy"><span>${esc(m.home)}</span></div>
      <div class="tl${aw ? " w" : ""}"><img src="${img(m.away_logo, m.away)}" alt="" loading="lazy"><span>${esc(m.away)}</span></div>
    </div>
    <div class="msc${m.live ? " lv" : ""}">${started ? `<span>${m.home_goals}</span><span>${m.away_goals}</span>` : ""}</div>
    <button class="star${fav ? " on" : ""}" data-act="fav" data-key="${esc(m.match_key)}" aria-label="Favorito" title="${fav ? "Quitar de favoritos" : "Agregar a favoritos"}">${fav ? "★" : "☆"}</button>
  </div>`;
}
const countryName = (m) => (!m.country || m.country === "World") ? "Internacional" : m.country;
function leagueHead(ms) {
  const m = ms[0], nl = ms.filter((x) => x.live).length, pin = S.pins.has(String(m.league_id));
  return `<div class="lg-head">
    <img src="${img(m.league_logo, m.league)}" alt="" loading="lazy">
    <div><div class="nm" data-act="league" data-id="${m.league_id}">${esc(m.league)}${m.source === "demo" ? '<span class="demo-tag">DEMO</span>' : ""}</div>
      <div class="ct">${m.flag ? `<img src="${img(m.flag, m.country)}" alt="">` : "🌐"}${esc(countryName(m))}</div></div>
    <span class="cnt">${nl ? `<b>${nl}</b>/` : ""}${ms.length}</span>
    <button class="pin${pin ? " on" : ""}" data-act="pin" data-id="${m.league_id}" title="${pin ? "Desfijar liga" : "Fijar liga arriba"}">📌</button>
  </div>`;
}

// ---------------- vista PARTIDOS ----------------
function viewMatches() {
  const app = $("#app");
  app.innerHTML = `
    ${S.notice ? `<div class="notice">ℹ️ ${esc(S.notice)}</div>` : ""}
    <div class="layout three${S.mobileDetail ? " show-detail" : ""}" id="layout">
      <section class="card list-col" aria-label="Partidos">
        <div class="dates" id="dates"></div>
        <div class="filters" id="filters"></div>
        <div class="regions" id="regions"></div>
        <div class="mlist" id="mlist"></div>
      </section>
      <section class="card detail-col sticky" id="detail" aria-label="Detalle del partido"></section>
      <aside class="rail sticky" id="rail"></aside>
    </div>`;
  renderDates(); renderList(); renderDetail(); renderRail();
}
function renderDates() {
  const el = $("#dates"); if (!el) return;
  const days = [-2, -1, 0, 1, 2, 3, 4].map((n) => addDays(todayISO(), n));
  if (!days.includes(S.date)) days.splice(3, 1, S.date);
  el.innerHTML = `<button class="arrow" data-act="day" data-n="-1" aria-label="Día anterior">‹</button>
    <div class="dstrip">${days.map((d) => `<button class="dchip${d === S.date ? " on" : ""}" data-act="date" data-d="${d}"><b>${dayName(d)}</b><span>${dayShort(d)}</span></button>`).join("")}</div>
    <button class="arrow" data-act="day" data-n="1" aria-label="Día siguiente">›</button>
    <label class="dcal" title="Elegir fecha">📅<input type="date" id="dpick" value="${S.date}"></label>`;
  $("#dpick").addEventListener("change", (e) => e.target.value && setDate(e.target.value));
}
function renderList() {
  const el = $("#mlist"); if (!el) return;
  const base = S.matches.filter((m) => S.region === "Todas" || (m.buckets || []).includes(S.region))
    .filter((m) => !S.q || norm(`${m.home} ${m.away} ${m.league} ${m.country}`).includes(norm(S.q)));
  const n = { all: base.length, live: base.filter((m) => m.live).length, upcoming: base.filter((m) => !m.live && !m.finished).length,
    finished: base.filter((m) => m.finished).length, favs: base.filter((m) => S.favs.has(m.match_key) || S.pins.has(String(m.league_id))).length };
  $("#filters").innerHTML = [["all", "Todos"], ["live", "En vivo"], ["upcoming", "Próximos"], ["finished", "Terminados"], ["favs", "★ Favoritos"]]
    .map(([k, l]) => `<button class="pill${k === "live" ? " live" : ""}${S.filter === k ? " on" : ""}" data-act="filter" data-f="${k}">${k === "live" && n.live ? '<span class="pulse"></span>' : ""}${l}<span class="n">${n[k]}</span></button>`).join("");
  $("#regions").innerHTML = ["Todas", "Top", "Europa", "Sudamérica", "Internacional"]
    .map((r) => `<button class="pill${S.region === r ? " on" : ""}" data-act="region" data-r="${r}">${r === "Top" ? "⭐ Top" : r}</button>`).join("");
  if (!S.loaded) { el.innerHTML = Array.from({ length: 8 }, () => '<div class="skrow"><div class="sk a"></div><div class="sk b"></div><div class="sk c"></div></div>').join(""); return; }
  const list = filtered();
  if (!list.length) {
    const msg = S.filter === "favs" ? ["⭐", "Aún no tienes favoritos", "Toca ☆ en un partido o 📌 en una liga."] :
      S.filter === "live" ? ["📺", "No hay partidos en vivo", "Revisa los próximos o cambia de día."] :
      ["🏟️", "No hay partidos con estos filtros", "Prueba con «Todas» o cambia la fecha."];
    el.innerHTML = emptyHtml(...msg); return;
  }
  const st = el.scrollTop;
  el.innerHTML = groupByLeague(list).map((ms) => leagueHead(ms) + ms.map(matchRow).join("")).join("");
  el.scrollTop = st;
}

// ---------------- detalle ----------------
const TABS = [["resumen", "Resumen"], ["pronostico", "Pronóstico"], ["stats", "Estadísticas"], ["eventos", "Eventos"],
  ["h2h", "Cara a cara"], ["tabla", "Clasificación"], ["cuotas", "Cuotas"], ["sim", "Simulador"]];

function renderDetail({ keepTab = false } = {}) {
  const el = $("#detail"); if (!el) return;
  if (!S.sel) { el.innerHTML = emptyHtml("👈", "Elige un partido", "Verás el pronóstico, estadísticas y más."); return; }
  const m0 = byKey(S.sel);
  const d = S.detail && S.detailFor === S.sel ? S.detail : null;
  if (!d) {
    el.innerHTML = `<div class="pad"><div class="sk" style="height:28px;width:60%"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin:24px 0"><div class="sk" style="height:110px"></div><div class="sk" style="height:110px"></div><div class="sk" style="height:110px"></div></div>
      <div class="sk" style="height:46px;margin-bottom:10px"></div><div class="sk" style="height:180px"></div></div>`;
    return;
  }
  const m = { ...d.match, ...(m0 ? { home_goals: m0.home_goals, away_goals: m0.away_goals, minute: m0.minute, status_short: m0.status_short, live: m0.live, finished: m0.finished } : {}) };
  const fav = S.favs.has(m.match_key);
  let center;
  if (m.live) {
    const min = m.status_short === "HT" ? "Entretiempo" : `${m.minute}${m.extra ? "+" + m.extra : ""}′`;
    center = `<div class="big">${m.home_goals}<span class="sep">-</span>${m.away_goals}</div><div class="lvmin"><span class="pulse"></span>${min}</div>
      <div class="prog"><div style="width:${Math.min(100, (m.minute || 0) / 90 * 100)}%"></div></div>`;
  } else if (m.finished) {
    center = `<div class="big">${m.home_goals}<span class="sep">-</span>${m.away_goals}</div><div class="when">${esc(m.status_label)}</div>`;
  } else {
    const k = m.kickoff ? new Date(m.kickoff) : null;
    center = `<div class="kick">${hhmm(m.kickoff)}</div><div class="when">${k ? `${dayName(isoDay(k))} · ${dayShort(isoDay(k))}` : ""}</div>
      ${k ? `<div class="countdown" data-countdown="${k.getTime()}"></div>` : ""}`;
  }
  el.innerHTML = `
    <div class="dhead">
      <button class="back" data-act="back" aria-label="Volver">←</button>
      <img src="${img(m.league_logo, m.league)}" alt="">
      <div><div class="nm" data-act="league" data-id="${m.league_id}">${esc(m.league)}${m.source === "demo" ? '<span class="demo-tag">DEMO</span>' : ""}</div>
        <div class="sub">${esc(countryName(m))}${m.round ? " · " + esc(m.round) : ""}</div></div>
      <div class="acts">
        <button class="${fav ? "on" : ""}" data-act="fav" data-key="${esc(m.match_key)}" title="Favorito">${fav ? "★" : "☆"}</button>
        <button data-act="share" title="Copiar enlace">🔗</button>
      </div>
    </div>
    <div class="score">
      <div class="team"><img src="${img(m.home_logo, m.home)}" alt=""><div class="nm">${esc(m.home)}</div>${formHtml(d.forms.home.form)}</div>
      <div class="center">${center}</div>
      <div class="team"><img src="${img(m.away_logo, m.away)}" alt=""><div class="nm">${esc(m.away)}</div>${formHtml(d.forms.away.form)}</div>
    </div>
    ${m.venue ? `<div class="venue">🏟️ ${esc(m.venue)}</div>` : '<div style="height:10px"></div>'}
    <div class="tabs" role="tablist">${TABS.map(([k, l]) => `<button class="tab${S.tab === k ? " on" : ""}" data-act="tab" data-t="${k}" role="tab">${l}</button>`).join("")}</div>
    <div class="tabbody" id="tabbody"></div>`;
  tickCountdowns();
  renderTab(keepTab);
}

function renderTab() {
  const el = $("#tabbody"); if (!el || !S.detail) return;
  const d = S.detail, m = { ...d.match, ...(byKey(S.sel) || {}) }, p = d.prediction;
  const fn = { resumen: tabResumen, pronostico: tabPronostico, stats: tabStats, eventos: tabEventos, h2h: tabH2H, tabla: tabTabla, cuotas: tabCuotas, sim: tabSim }[S.tab] || tabResumen;
  el.innerHTML = fn(m, d, p);
  if (S.tab === "sim") bindSim(m, d, p);
}

function voteBox(m, p) {
  const vals = [["h", p.home_win], ["x", p.draw], ["a", p.away_win]];
  const top = Math.max(...vals.map((v) => v[1]));
  const ic = { h: `<img src="${img(m.home_logo, m.home)}" alt="">`, x: "<span>X</span>", a: `<img src="${img(m.away_logo, m.away)}" alt="">` };
  return `<div class="box"><h4>¿Quién gana?</h4><div class="s">Probabilidad del modelo ZOLA · <span class="conf ${p.confidence}">Confianza ${p.confidence.toLowerCase()}</span></div>
    <div class="vote">${vals.map(([k, v]) => `<div class="${v === top ? "top" : ""}"><i style="width:${(v * 100).toFixed(1)}%"></i>${ic[k]}<span>${pct(v)}</span></div>`).join("")}</div></div>`;
}
function oddsBox(d, p) {
  const o = d.odds || {};
  if (!(o["1"] && o.X && o["2"])) return "";
  const cell = (k, l) => {
    const edge = p.markets[k] * o[k] - 1;
    const ar = edge > 0.03 ? '<span class="up">▲</span>' : edge < -0.03 ? '<span class="dn">▼</span>' : "";
    return `<div><span class="muted">${l}</span><b>${o[k].toFixed(2)}${ar}</b></div>`;
  };
  return `<div class="box"><h4>Cuotas · resultado final</h4><div class="s">▲ el modelo ve valor · ▼ la cuota paga poco para su probabilidad</div>
    <div class="odds3">${cell("1", "1")}${cell("X", "X")}${cell("2", "2")}</div></div>`;
}
function pickBox(m, d, p) {
  if (m.finished) {
    const saved = S.picks.find((x) => x.key === m.match_key);
    return `<div class="box"><div class="pick"><div class="ic">🏁</div><div><div class="t">Partido terminado</div>
      <div class="v">${esc(m.home)} ${m.home_goals}-${m.away_goals} ${esc(m.away)}</div>
      <div class="x">${saved ? (saved.result === "won" ? "✅ Acertaste tu pronóstico" : saved.result === "lost" ? "❌ Tu pronóstico no se cumplió" : "Tu pronóstico se está cerrando…") : "Pronóstico del modelo: " + esc(p.best_score)}</div></div></div></div>`;
  }
  const bb = p.best_bet;
  let inner;
  if (!bb) inner = `<div class="ic">🛑</div><div><div class="t">Recomendación</div><div class="v">No apostar</div><div class="x">Ningún mercado tiene suficiente probabilidad o valor.</div></div>`;
  else if (bb.kind === "valor") inner = `<div class="ic">🎯</div><div><div class="t">Apuesta de valor</div><div class="v">${esc(MK_LABEL[bb.market] || bb.market)} @ ${bb.odd.toFixed(2)}</div>
      <div class="x">Modelo ${pct(bb.prob)} vs casa ${pct(1 / bb.odd)}</div></div><div class="e" style="color:var(--green)">+${pct(bb.edge)}<small>ventaja</small></div>`;
  else inner = `<div class="ic">📌</div><div><div class="t">Jugada más probable</div><div class="v">${esc(MK_LABEL[bb.market] || bb.market)}</div>
      <div class="x">${Object.keys(d.odds || {}).length ? "La cuota actual no ofrece valor." : "Sin cuotas para medir valor."}</div></div><div class="e">${pct(bb.prob)}<small>prob.</small></div>`;
  const saved = S.picks.some((x) => x.key === m.match_key);
  return `<div class="box"><div class="pick">${inner}</div>
    <div style="margin-top:12px"><button class="btn ${saved ? "" : "primary"} block" data-act="savepick" ${saved ? "disabled" : ""}>${saved ? "✓ Guardado en Mis pronósticos" : "💾 Guardar en Mis pronósticos"}</button></div></div>`;
}
function aiText(m, p) {
  if (m.finished) return `Terminó <b>${esc(m.home)} ${m.home_goals}-${m.away_goals} ${esc(m.away)}</b>. El modelo esperaba <b>${esc(p.best_score)}</b>.`;
  const fav = Math.max(p.home_win, p.draw, p.away_win);
  const lead = p.winner === "Empate" ? "El <b>empate</b> es lo más probable" : `<b>${esc(p.winner)}</b> es favorito`;
  return `${lead} (${pct(fav)}). Marcador final más probable: <b>${esc(p.best_score)}</b>.<br>
    Goles esperados en 90′: ${esc(m.home)} <b>${p.lam_home.toFixed(2)}</b> · ${esc(m.away)} <b>${p.lam_away.toFixed(2)}</b>.
    <div class="notes"><span>📊 ${esc(p.data_quality)}</span>${(p.notes || []).map((n) => `<span>${esc(n)}</span>`).join("")}</div>`;
}
function tabResumen(m, d, p) {
  return `${m.finished ? "" : voteBox(m, p)}${oddsBox(d, p)}${pickBox(m, d, p)}
    <div class="box ai"><h4 style="margin-bottom:6px">Análisis ZOLA</h4>${aiText(m, p)}</div>
    <div class="kpis">${[["+1.5 goles", p.over15], ["+2.5 goles", p.over25], ["+3.5 goles", p.over35], ["Ambos marcan", p.btts]]
      .map(([l, v]) => `<div class="kpi"><div class="l">${l}</div><div class="v">${pct(v)}</div><div class="t"><div style="width:${(v * 100).toFixed(0)}%"></div></div></div>`).join("")}</div>
    ${d.warnings && d.warnings.length ? `<div class="notes">${d.warnings.map((w) => `<span>⚠️ ${esc(w)}</span>`).join("")}</div>` : ""}`;
}
function tabPronostico(m, d, p) {
  const mx = p.matrix || [];
  const max = Math.max(...mx.flat(), 0.0001);
  const cur = [m.home_goals || 0, m.away_goals || 0];
  const cells = mx.map((row, i) => `<div class="h">${i}</div>` + row.map((v, j) => {
    const a = Math.min(1, v / max);
    const curCls = (m.live && i === cur[0] && j === cur[1]) ? " cur" : "";
    return `<div class="c${curCls}" style="background:rgba(59,107,255,${(0.07 + a * 0.85).toFixed(2)});color:${a > 0.55 ? "#fff" : "var(--text)"}" title="${esc(m.home)} ${i}-${j} ${esc(m.away)}: ${pct(v, 1)}">${v >= 0.005 ? pct(v) : ""}</div>`;
  }).join("")).join("");
  const markets = ["1", "X", "2", "1X", "X2", "Over 1.5", "Over 2.5", "Over 3.5", "BTTS Sí", "BTTS No"];
  const top = (p.top_scores || []).slice(0, 6), tmax = Math.max(...top.map((t) => t[1]), 0.0001);
  return `<div class="box"><h4>Mapa de marcadores finales</h4><div class="s">Filas: goles de ${esc(m.home)} · columnas: goles de ${esc(m.away)}${m.live ? " · borde dorado = marcador actual" : ""}</div>
      <div class="heat"><div></div>${[0, 1, 2, 3, 4, 5].map((j) => `<div class="h">${j}</div>`).join("")}${cells}</div></div>
    <div class="box"><h4>Mercados</h4><div class="s">Probabilidad estimada de cada mercado</div>
      ${markets.map((k) => `<div class="mk"><span>${esc(MK_LABEL[k])}</span><div class="t"><div style="width:${(p.markets[k] * 100).toFixed(1)}%"></div></div><b>${pct(p.markets[k])}</b></div>`).join("")}</div>
    <div class="box"><h4>Marcadores más probables</h4><div class="s">Resultado final</div>
      ${top.map(([sc, v], i) => `<div class="scr${i === 0 ? " top" : ""}"><b>${esc(sc)}</b><div class="t"><div style="width:${(v / tmax * 100).toFixed(0)}%"></div></div><span class="muted" style="text-align:right">${pct(v)}</span></div>`).join("")}</div>`;
}
function statBar(label, h, a, isPct) {
  if (h == null && a == null) return "";
  h = h || 0; a = a || 0;
  const tot = (h + a) || 1;
  const f = (v) => isPct ? `${Math.round(v)}%` : (Number.isInteger(v) ? v : v.toFixed(2));
  return `<div class="stat"><div class="top"><b class="${h > a ? "lead" : ""}">${f(h)}</b><span>${label}</span><b class="${a > h ? "leada" : ""}">${f(a)}</b></div>
    <div class="bars"><div class="half" style="justify-content:flex-end"><div class="bh" style="width:${h / tot * 100}%"></div></div><div class="half"><div class="ba" style="width:${a / tot * 100}%"></div></div></div></div>`;
}
function tabStats(m, d) {
  const h = d.stats.home || {}, a = d.stats.away || {};
  const fh = d.forms.home, fa = d.forms.away;
  const season = `<div class="box"><h4>Promedios de la temporada</h4><div class="s">${esc(m.home)} como local · ${esc(m.away)} como visita</div>
    ${statBar("Goles a favor por partido", fh.gf_home, fa.gf_away)}${statBar("Goles en contra por partido", fh.ga_home, fa.ga_away)}
    ${statBar("Partidos jugados", fh.gp_home, fa.gp_away)}</div>`;
  if (!Object.keys(h).length && !Object.keys(a).length) {
    return `${season}${emptyHtml("⏳", "Estadísticas del partido", "Aparecen cuando empieza el partido.")}`;
  }
  const rows = [["Posesión", "possession", true], ["Goles esperados (xG)", "xg"], ["Tiros totales", "shots"], ["Tiros al arco", "shots_on_target"],
    ["Córners", "corners"], ["Atajadas", "saves"], ["Precisión de pases", "pass_acc", true], ["Faltas", "fouls"], ["Amarillas", "yellow"], ["Rojas", "red"]];
  return `<div class="box"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <span style="display:flex;gap:8px;align-items:center;font-weight:800"><img src="${img(m.home_logo, m.home)}" style="width:22px;height:22px;object-fit:contain">${esc(m.home)}</span>
      <span style="display:flex;gap:8px;align-items:center;font-weight:800">${esc(m.away)}<img src="${img(m.away_logo, m.away)}" style="width:22px;height:22px;object-fit:contain"></span></div>
      ${rows.map(([l, k, pc]) => statBar(l, h[k], a[k], pc)).join("")}</div>${season}`;
}
const DETAIL_ES = { "Normal Goal": "Gol", "Own Goal": "Autogol", Penalty: "Penal", "Missed Penalty": "Penal fallado", "Yellow Card": "Amarilla",
  "Red Card": "Roja", "Second Yellow card": "Doble amarilla", "Goal cancelled": "Gol anulado (VAR)", "Penalty confirmed": "Penal confirmado (VAR)" };
function tabEventos(m, d) {
  const evs = [...(d.events || [])].sort((a, b) => (a.min - b.min) || ((a.extra || 0) - (b.extra || 0)));
  if (!evs.length) return emptyHtml("⏱️", "Sin eventos todavía", m.live || m.finished ? "" : "Los goles, tarjetas y cambios aparecen en vivo.");
  let h = 0, a = 0, htShown = false;
  const out = [];
  for (const e of evs) {
    if (!htShown && e.min > 45) { out.push(`<div class="ev-sep"><span>Entretiempo · ${h}-${a}</span></div>`); htShown = true; }
    const home = e.team === m.home;
    let ico = { Goal: "⚽", Card: "🟨", subst: "🔁", Var: "📺" }[e.type] || "•";
    if (e.type === "Card" && /Red|Second Yellow/.test(e.detail)) ico = "🟥";
    if (e.type === "Goal" && e.detail === "Missed Penalty") ico = "❌";
    let sc = "";
    if (e.type === "Goal" && e.detail !== "Missed Penalty") { home ? h++ : a++; sc = `<span class="sc">${h}-${a}</span>`; }
    const sub = e.type === "subst" ? (e.assist ? `↔ ${esc(e.assist)}` : "Cambio") :
      `${esc(DETAIL_ES[e.detail] || e.detail)}${e.type === "Goal" && e.assist ? ` · asist. ${esc(e.assist)}` : ""}`;
    const who = `<div class="who"><b>${esc(e.player || e.team)}</b><small>${sub}</small></div>`;
    const side = home ? `<div class="side l">${sc}${who}<span class="ico">${ico}</span></div><div class="min">${e.min}${e.extra ? "+" + e.extra : ""}'</div><div></div>`
      : `<div></div><div class="min">${e.min}${e.extra ? "+" + e.extra : ""}'</div><div class="side"><span class="ico">${ico}</span>${who}${sc}</div>`;
    out.push(`<div class="ev">${side}</div>`);
  }
  if (m.finished) out.push(`<div class="ev-sep"><span>Final · ${m.home_goals}-${m.away_goals}</span></div>`);
  return `<div class="box"><div class="tline">${out.reverse().join("")}</div></div>`;
}
function tabH2H(m) {
  const st = S.h2h[m.match_key];
  if (!st) { loadH2H(m.match_key); return `<div class="sk" style="height:220px"></div>`; }
  if (st.loading) return `<div class="sk" style="height:220px"></div>`;
  const list = st.matches || [];
  if (!list.length) return emptyHtml("🤝", "Sin enfrentamientos previos", st.error ? esc(st.error) : "");
  let w = 0, dr = 0, l = 0;
  for (const x of list) {
    const hg = x.home === m.home ? x.home_goals : x.away_goals, ag = x.home === m.home ? x.away_goals : x.home_goals;
    hg > ag ? w++ : hg === ag ? dr++ : l++;
  }
  const t = list.length;
  return `<div class="box"><h4>Últimos ${t} cruces${list[0].source === "demo" ? '<span class="demo-tag">DEMO</span>' : ""}</h4><div class="s">Resultados entre ambos equipos</div>
    <div class="h2hsum"><div><b style="color:var(--brand)">${w}</b><span>${esc(m.home)}</span></div><div><b>${dr}</b><span>Empates</span></div><div><b style="color:var(--orange)">${l}</b><span>${esc(m.away)}</span></div></div>
    <div class="h2hbar"><div style="width:${w / t * 100}%;background:var(--brand)"></div><div style="width:${dr / t * 100}%;background:var(--grey)"></div><div style="width:${l / t * 100}%;background:var(--orange)"></div></div>
    ${list.map((x) => `<div class="h2hrow"><span class="d">${x.kickoff ? new Date(x.kickoff).toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "2-digit" }) : ""}</span>
      <span class="t r"><span>${esc(x.home)}</span><img src="${img(x.home_logo, x.home)}" alt=""></span>
      <span class="r">${x.home_goals}-${x.away_goals}</span>
      <span class="t"><img src="${img(x.away_logo, x.away)}" alt=""><span>${esc(x.away)}</span></span></div>`).join("")}</div>`;
}
function standingsTable(groups, highlight = []) {
  const zones = new Map();
  const html = groups.map((g) => `${groups.length > 1 ? `<div class="sec-title" style="margin-top:12px">${esc(g.name)}</div>` : ""}
    <div class="tblwrap"><table class="tbl"><thead><tr><th>#</th><th class="l">Equipo</th><th>PJ</th><th>G</th><th>E</th><th>P</th><th>DG</th><th>Goles</th><th>Últimos 5</th><th>PTS</th></tr></thead><tbody>
    ${g.rows.map((r) => {
      const z = zoneOf(r.zone || r.description);
      if (z) zones.set(z, ZONE[z]);
      return `<tr class="${highlight.includes(r.team) ? "hl" : ""}"><td class="rk"><i style="background:${z ? ZONE[z][0] : "transparent"}"></i>${r.rank}</td>
        <td class="l"><span class="tm"><img src="${img(r.logo, r.team)}" alt="" loading="lazy">${esc(r.team)}</span></td>
        <td>${r.played}</td><td>${r.win}</td><td>${r.draw}</td><td>${r.lose}</td><td>${r.diff > 0 ? "+" : ""}${r.diff}</td><td>${r.gf}:${r.ga}</td><td>${formHtml(r.form)}</td><td class="pts">${r.points}</td></tr>`;
    }).join("")}</tbody></table></div>`).join("");
  const leg = [...zones.values()].map(([c, l]) => `<span><i style="background:${c}"></i>${l}</span>`).join("");
  return html + (leg ? `<div class="legend">${leg}</div>` : "");
}
function tabTabla(m) {
  const k = `${m.league_id}_${m.season}`;
  const st = S.standings[k];
  if (!st) { loadStandings(m.league_id, m.season, m.source === "demo").then(() => { if (S.tab === "tabla") renderTab(); }); return `<div class="sk" style="height:300px"></div>`; }
  if (st.loading) return `<div class="sk" style="height:300px"></div>`;
  if (!st.groups || !st.groups.length) return emptyHtml("📋", "Sin tabla de posiciones", "Esta competición no tiene tabla (o no está disponible).");
  return `<div class="box">${m.source === "demo" ? '<div class="s">Tabla de ejemplo (DEMO)</div>' : ""}${standingsTable(st.groups, [m.home, m.away])}</div>`;
}
function tabCuotas(m, d, p) {
  const vb = p.value_bets || [];
  if (!vb.length) return emptyHtml("💤", "No hay cuotas para este partido", m.finished ? "El partido ya terminó." : "La casa aún no publica cuotas.");
  return `<div class="box"><h4>Cuotas vs. modelo</h4><div class="s">Ventaja = probabilidad del modelo × cuota − 1. Positiva = el modelo ve valor.</div>
    <div class="tblwrap"><table class="tbl otbl"><thead><tr><th>Mercado</th><th>Cuota</th><th>Prob. modelo</th><th>Prob. casa</th><th>Ventaja</th></tr></thead><tbody>
    ${vb.map((v) => `<tr><td>${esc(MK_LABEL[v.market] || v.market)}${v.edge >= 0.03 && v.prob >= 0.3 ? '<span class="vtag">VALOR</span>' : ""}</td><td><b>${v.odd.toFixed(2)}</b></td>
      <td>${pct(v.prob)}</td><td class="muted">${pct(v.implied)}</td><td class="${v.edge > 0 ? "edge-pos" : "edge-neg"}">${v.edge > 0 ? "+" : ""}${pct(v.edge, 1)}</td></tr>`).join("")}
    </tbody></table></div></div>`;
}
function tabSim(m, d, p) {
  const s = S.sim;
  const bb = p.best_bet || {};
  if (!s.key || s.key !== m.match_key) Object.assign(s, { key: m.match_key, mk: p.markets[bb.market] != null ? bb.market : "1", bank: s.bank || 500 });
  const odd = s.odd && s.mkFor === s.mk ? s.odd : (d.odds[s.mk] || +(1 / Math.max(p.markets[s.mk], 0.01)).toFixed(2));
  const mks = Object.keys(p.markets);
  return `<div class="box"><h4>Elige un mercado</h4><div class="s">Toca uno para simular la apuesta</div>
    <div class="mktgrid">${mks.map((k) => `<button class="mktbtn${k === s.mk ? " on" : ""}" data-act="simmk" data-mk="${esc(k)}"><small>${esc(MK_LABEL[k] || k)}</small><b>${pct(p.markets[k])}</b>${d.odds[k] ? ` <span class="muted" style="font-size:.75rem">@${d.odds[k].toFixed(2)}</span>` : ""}</button>`).join("")}</div>
    <div class="simgrid">
      <div class="field"><label>Cuota</label><input type="number" id="simOdd" min="1.01" step="0.05" value="${(+odd).toFixed(2)}"></div>
      <div class="field"><label>Bankroll (S/)</label><input type="number" id="simBank" min="10" step="50" value="${s.bank}"></div>
      <div class="field"><label>Riesgo</label><select id="simRisk"><option value="0.25">Prudente (¼ Kelly)</option><option value="0.5">Medio (½ Kelly)</option><option value="1">Agresivo (Kelly)</option></select></div>
    </div>
    <div class="kpis" id="simOut"></div><div class="s" id="simNote" style="margin:0"></div></div>`;
}
function bindSim(m, d, p) {
  const s = S.sim;
  const risk = $("#simRisk"); risk.value = String(s.risk || 0.25);
  const calc = () => {
    const odd = parseFloat($("#simOdd").value) || 1.01, bank = parseFloat($("#simBank").value) || 0, r = parseFloat(risk.value);
    s.odd = odd; s.mkFor = s.mk; s.bank = bank; s.risk = r;
    const pr = p.markets[s.mk], ev = pr * odd - 1, k = odd > 1 ? Math.max(0, (pr * odd - 1) / (odd - 1)) : 0;
    const stake = Math.round(bank * k * r * 100) / 100;
    $("#simOut").innerHTML = [["Prob. modelo", pct(pr, 1)], ["Valor esperado", `<span style="color:${ev > 0 ? "var(--green)" : "var(--red)"}">${ev > 0 ? "+" : ""}${pct(ev, 1)}</span>`],
      ["Stake sugerido", `S/${stake.toFixed(2)}`], ["Ganancia si acierta", `S/${(stake * (odd - 1)).toFixed(2)}`]]
      .map(([l, v]) => `<div class="kpi" style="background:var(--panel)"><div class="l">${l}</div><div class="v">${v}</div></div>`).join("");
    $("#simNote").textContent = ev <= 0 ? "Con esta cuota la apuesta pierde a la larga según el modelo, por eso el stake sugerido es 0." :
      `Por cada S/100 apostados a largo plazo, el modelo espera ganar S/${(ev * 100).toFixed(2)}. La cuota justa sería ${(1 / pr).toFixed(2)}.`;
  };
  ["#simOdd", "#simBank"].forEach((id) => $(id).addEventListener("input", calc));
  risk.addEventListener("change", calc);
  calc();
}

// ---------------- columna derecha ----------------
function renderRail() {
  const el = $("#rail"); if (!el) return;
  if (!S.loaded) { el.innerHTML = '<div class="card pad"><div class="sk" style="height:160px"></div></div>'; return; }
  const pool = S.matches.filter((m) => !m.finished);
  const feat = [...pool].sort((a, b) => (b.live - a.live) || ((LEAGUE_PRIORITY.indexOf(a.league_id) + 1 || 99) - (LEAGUE_PRIORITY.indexOf(b.league_id) + 1 || 99)))[0];
  const live = S.matches.filter((m) => m.live).slice(0, 6);
  const done = S.picks.filter((x) => x.result), won = done.filter((x) => x.result === "won").length;
  el.innerHTML = `
    ${feat ? `<div class="card feat"><div class="sec-title">🔥 Destacado</div>
      <div class="lg"><img src="${img(feat.league_logo, feat.league)}" alt="">${esc(feat.league)}</div>
      <div class="row" data-act="open" data-key="${esc(feat.match_key)}">
        <div><img src="${img(feat.home_logo, feat.home)}" alt=""><div class="n">${esc(feat.home)}</div></div>
        <div>${feat.live ? `<div class="big" style="font-size:1.7rem">${feat.home_goals}-${feat.away_goals}</div><div class="lvmin" style="font-size:.78rem"><span class="pulse"></span>${feat.minute}'</div>` : `<div class="kick" style="font-size:1.25rem">${hhmm(feat.kickoff)}</div><div class="when" style="font-size:.74rem">${dayName(S.date)}</div>`}</div>
        <div><img src="${img(feat.away_logo, feat.away)}" alt=""><div class="n">${esc(feat.away)}</div></div>
      </div><button class="btn primary block" style="margin-top:12px" data-act="open" data-key="${esc(feat.match_key)}">Ver pronóstico</button></div>` : ""}
    ${live.length ? `<div class="card"><div class="sec-title pad" style="margin:0;padding-bottom:6px"><span class="pulse"></span>En vivo ahora <small>${S.matches.filter((m) => m.live).length}</small></div>
      ${live.map((m) => `<div class="mini" data-act="open" data-key="${esc(m.match_key)}"><img src="${img(m.home_logo, m.home)}" alt=""><span>${esc(m.home)}</span><span class="muted">vs</span><span>${esc(m.away)}</span><span class="res" style="color:var(--red)">${m.home_goals}-${m.away_goals}</span></div>`).join("")}</div>` : ""}
    <div class="card"><div class="sec-title pad" style="margin:0;padding-bottom:4px">🎯 Mis pronósticos <small><a href="#/mis-pronosticos" style="color:var(--brand)">Ver todo</a></small></div>
      <div class="pad" style="padding-top:4px">${S.picks.length ? `<div class="kpis" style="grid-template-columns:1fr 1fr;margin:0">
        <div class="kpi"><div class="l">Guardados</div><div class="v">${S.picks.length}</div></div>
        <div class="kpi"><div class="l">Acierto</div><div class="v">${done.length ? pct(won / done.length) : "—"}</div></div></div>` :
        '<span class="muted" style="font-size:.84rem">Guarda un pronóstico desde la pestaña Resumen y aquí verás si aciertas.</span>'}</div></div>`;
}

// ---------------- vista LIGAS ----------------
async function viewLeagues() {
  const app = $("#app");
  if (!S.loaded) { app.innerHTML = '<div class="card pad"><div class="sk" style="height:300px"></div></div>'; return; }
  const comps = new Map();
  for (const m of S.matches) {
    const k = String(m.league_id ?? m.league);
    if (!comps.has(k)) comps.set(k, { m, n: 0, live: 0 });
    const c = comps.get(k); c.n++; if (m.live) c.live++;
  }
  const order = [...comps.entries()].sort((a, b) => {
    const pa = S.pins.has(a[0]) ? 0 : 1, pb = S.pins.has(b[0]) ? 0 : 1;
    if (pa !== pb) return pa - pb;
    const ia = LEAGUE_PRIORITY.indexOf(a[1].m.league_id), ib = LEAGUE_PRIORITY.indexOf(b[1].m.league_id);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a[1].m.league.localeCompare(b[1].m.league);
  });
  if (!order.length) { app.innerHTML = `<div class="card">${emptyHtml("🏆", "No hay competiciones este día", "Cambia la fecha en Partidos.")}</div>`; return; }
  if (!S.league || !comps.has(S.league)) S.league = order[0][0];
  const sel = comps.get(S.league).m;
  app.innerHTML = `
    <div class="sec-title" style="font-size:1.05rem">Competiciones · ${dayName(S.date)} ${dayShort(S.date)} <small>${order.length} con partidos</small></div>
    <div class="lgrid" style="margin-bottom:16px">${order.map(([k, c]) => `<button class="litem${k === S.league ? " on" : ""}" data-act="league" data-id="${esc(k)}">
      <img src="${img(c.m.league_logo, c.m.league)}" alt=""><div><div class="nm">${esc(c.m.league)}</div><div class="ct">${esc(countryName(c.m))}</div></div>
      <span class="n">${c.live ? `<span style="color:var(--red)">${c.live} en vivo</span> · ` : ""}${c.n}</span></button>`).join("")}</div>
    <div class="card">
      <div class="lpage"><img class="lg" src="${img(sel.league_logo, sel.league)}" alt=""><div>
        <div class="nm">${esc(sel.league)}${sel.source === "demo" ? '<span class="demo-tag">DEMO</span>' : ""}</div>
        <div class="ct">${sel.flag ? `<img src="${img(sel.flag, sel.country)}" alt="">` : "🌐"}${esc(countryName(sel))}${sel.season ? ` · Temporada ${sel.season}/${sel.season + 1}` : ""}</div></div>
        <button class="btn" style="margin-left:auto" data-act="pin" data-id="${sel.league_id}">${S.pins.has(String(sel.league_id)) ? "📌 Fijada" : "📌 Fijar arriba"}</button></div>
      <div style="display:grid;grid-template-columns:minmax(0,1.6fr) minmax(300px,1fr);gap:16px;padding:0 16px 16px" class="lgcols">
        <div><div class="sec-title">Clasificación</div><div id="lgTable"><div class="sk" style="height:300px"></div></div></div>
        <div><div class="sec-title">Partidos · ${dayName(S.date)}</div><div class="card" style="overflow:hidden">${S.matches.filter((m) => String(m.league_id ?? m.league) === S.league).map(matchRow).join("")}</div></div>
      </div></div>`;
  if (window.innerWidth < 900 && location.hash.split("/").length > 2) setTimeout(() => $(".lpage")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  const st = await loadStandings(sel.league_id, sel.season, sel.source === "demo");
  const t = $("#lgTable");
  if (t) t.innerHTML = st.groups && st.groups.length ? standingsTable(st.groups) : emptyHtml("📋", "Sin tabla de posiciones", "Esta competición no tiene tabla disponible.");
}

// ---------------- vista MIS PRONÓSTICOS ----------------
function savePicks() { ls.set("zola_picks", S.picks); updatePicksBadge(); }
function updatePicksBadge() {
  const pend = S.picks.filter((x) => !x.result).length;
  const b = $("#picksBadge"); b.hidden = !pend; b.textContent = pend;
}
async function settlePicks() {
  const pend = S.picks.filter((x) => !x.result);
  if (!pend.length) return;
  let changed = false;
  // primero con los partidos ya cargados
  for (const x of pend) {
    const m = byKey(x.key);
    if (m && m.finished) { settleOne(x, m); changed = true; }
  }
  const still = S.picks.filter((x) => !x.result).map((x) => x.key).slice(0, 20);
  if (still.length) {
    try {
      const j = await getJSON(`/api/results?ids=${encodeURIComponent(still.join(","))}`);
      for (const x of S.picks) { const m = j.results[x.key]; if (!x.result && m && m.finished) { settleOne(x, m); changed = true; } }
    } catch {}
  }
  if (changed) { savePicks(); if (S.view === "picks") viewPicks(); else if (S.view === "matches") renderRail(); }
}
function settleOne(x, m) {
  x.final = `${m.home_goals}-${m.away_goals}`;
  const w = marketWon(x.market, m.home_goals, m.away_goals);
  x.result = w === undefined ? "void" : (w ? "won" : "lost");
  toast(`${x.result === "won" ? "✅" : "❌"} ${esc(x.home)} ${x.final} ${esc(x.away)} · ${esc(MK_LABEL[x.market] || x.market)}`);
}
function viewPicks() {
  const app = $("#app");
  const done = S.picks.filter((x) => x.result === "won" || x.result === "lost");
  const won = done.filter((x) => x.result === "won").length;
  const withOdd = done.filter((x) => x.odd);
  const units = withOdd.reduce((s, x) => s + (x.result === "won" ? x.odd - 1 : -1), 0);
  // curva de unidades
  let acc = 0;
  const pts = [0, ...withOdd.sort((a, b) => a.savedAt - b.savedAt).map((x) => (acc += x.result === "won" ? x.odd - 1 : -1))];
  const mn = Math.min(...pts, 0), mx = Math.max(...pts, 1);
  const W = 600, H = 80;
  const path = pts.map((v, i) => `${i ? "L" : "M"}${(i / Math.max(pts.length - 1, 1)) * W},${H - ((v - mn) / (mx - mn || 1)) * (H - 10) - 5}`).join(" ");
  app.innerHTML = `
    <div class="sec-title" style="font-size:1.05rem">🎯 Mis pronósticos <small>Se guardan en este navegador y se cierran solos al terminar el partido</small></div>
    <div class="pstats">
      <div class="kpi"><div class="l">Guardados</div><div class="v">${S.picks.length}</div></div>
      <div class="kpi"><div class="l">Resueltos</div><div class="v">${done.length}</div></div>
      <div class="kpi"><div class="l">Acierto</div><div class="v">${done.length ? pct(won / done.length) : "—"}</div><div class="t"><div style="width:${done.length ? won / done.length * 100 : 0}%"></div></div></div>
      <div class="kpi"><div class="l">Unidades</div><div class="v" style="color:${units >= 0 ? "var(--green)" : "var(--red)"}">${withOdd.length ? (units >= 0 ? "+" : "") + units.toFixed(2) : "—"}</div></div>
    </div>
    ${withOdd.length > 1 ? `<div class="card pad" style="margin-bottom:14px"><div class="sec-title">Evolución (1 unidad por apuesta)</div>
      <svg class="spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"><line x1="0" x2="${W}" y1="${H - ((0 - mn) / (mx - mn || 1)) * (H - 10) - 5}" y2="${H - ((0 - mn) / (mx - mn || 1)) * (H - 10) - 5}" stroke="var(--line2)" stroke-dasharray="4"/>
      <path d="${path}" fill="none" stroke="${units >= 0 ? "var(--green)" : "var(--red)"}" stroke-width="2.5" vector-effect="non-scaling-stroke"/></svg></div>` : ""}
    <div class="card">${S.picks.length ? `<div class="prow muted" style="font-size:.72rem;font-weight:800;border-top:0"><span></span><span>PARTIDO</span><span>JUGADA</span><span>CUOTA</span><span class="hide-m">RESULTADO</span><span></span></div>` +
      [...S.picks].reverse().map((x) => `<div class="prow">
        <span class="st">${x.result === "won" ? "✅" : x.result === "lost" ? "❌" : x.result === "void" ? "➖" : "⏳"}</span>
        <div class="tms" data-act="gopick" data-key="${esc(x.key)}" data-date="${esc(x.date)}" style="cursor:pointer">
          <span><img src="${img(x.home_logo, x.home)}" alt="">${esc(x.home)}</span><span><img src="${img(x.away_logo, x.away)}" alt="">${esc(x.away)}</span>
          <small class="muted">${esc(x.league)} · ${new Date(x.savedAt).toLocaleDateString("es-PE", { day: "2-digit", month: "short" })}${x.scoreAt && x.scoreAt !== "0-0" ? ` · guardado con ${esc(x.scoreAt)}` : ""}</small></div>
        <span><b>${esc(MK_LABEL[x.market] || x.market)}</b><br><small class="muted">${pct(x.prob)} · pron. ${esc(x.predicted)}</small></span>
        <span>${x.odd ? x.odd.toFixed(2) : "—"}</span>
        <span class="hide-m"><b>${x.final || "—"}</b></span>
        <button class="del" data-act="delpick" data-key="${esc(x.key)}" title="Borrar">✕</button></div>`).join("")
      : emptyHtml("🎯", "Aún no guardas pronósticos", "Abre un partido y toca «Guardar en Mis pronósticos».")}</div>`;
}

// ---------------- buscador ----------------
function renderSuggest() {
  const box = $("#suggest"), q = norm(S.q);
  if (!q || q.length < 2) { box.hidden = true; return; }
  const teams = new Map(), leagues = new Map();
  for (const m of S.matches) {
    for (const [n, l] of [[m.home, m.home_logo], [m.away, m.away_logo]]) if (norm(n).includes(q) && !teams.has(n)) teams.set(n, { l, m });
    if (norm(m.league).includes(q) && !leagues.has(m.league)) leagues.set(m.league, m);
  }
  const t = [...teams.entries()].slice(0, 6), lg = [...leagues.entries()].slice(0, 4);
  if (!t.length && !lg.length) { box.innerHTML = `<div class="sg muted">Sin resultados para «${esc(S.q)}» este día</div>`; box.hidden = false; return; }
  box.innerHTML = (t.length ? '<div class="sgh">Equipos</div>' + t.map(([n, { l, m }]) => `<div class="sg" data-act="open" data-key="${esc(m.match_key)}"><img src="${img(l, n)}" alt="">${esc(n)}<small>${esc(m.home)} vs ${esc(m.away)}</small></div>`).join("") : "") +
    (lg.length ? '<div class="sgh">Ligas</div>' + lg.map(([n, m]) => `<div class="sg" data-act="league" data-id="${m.league_id}"><img src="${img(m.league_logo, n)}" alt="">${esc(n)}<small>${esc(countryName(m))}</small></div>`).join("") : "");
  box.hidden = false;
}

// ---------------- router y acciones ----------------
function setNav() { $$("[data-nav]").forEach((a) => a.classList.toggle("on", a.dataset.nav === S.view)); }
function renderView() {
  setNav();
  if (S.view === "leagues") viewLeagues();
  else if (S.view === "picks") viewPicks();
  else viewMatches();
}
function route() {
  const h = decodeURIComponent(location.hash.slice(1) || "/");
  const parts = h.split("/").filter(Boolean);
  if (parts[0] === "ligas") { S.view = "leagues"; if (parts[1]) S.league = parts[1]; }
  else if (parts[0] === "mis-pronosticos") S.view = "picks";
  else {
    S.view = "matches";
    if (parts[0] === "partido" && parts[1]) {
      if (S.sel !== parts[1]) { S.sel = parts[1]; S.tab = "resumen"; loadDetail(S.sel); }
      S.mobileDetail = true;
    } else S.mobileDetail = false;
  }
  renderView();
  window.scrollTo({ top: 0 });
}
function setDate(d) {
  S.date = d; S.sel = null; S.detail = null; S.detailFor = null; lastScores = {};
  if (S.view !== "matches") { S.loaded = false; }
  loadMatches();
}
function openMatch(key) {
  $("#suggest").hidden = true;
  if (S.view !== "matches" || location.hash !== `#/partido/${encodeURIComponent(key)}`) location.hash = `#/partido/${encodeURIComponent(key)}`;
  else route();
}
document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-act]");
  if (!t) { if (!e.target.closest(".search")) $("#suggest").hidden = true; return; }
  const a = t.dataset.act;
  if (a === "open") { e.preventDefault(); openMatch(t.dataset.key); }
  else if (a === "fav") {
    e.stopPropagation();
    const k = t.dataset.key;
    S.favs.has(k) ? S.favs.delete(k) : S.favs.add(k);
    ls.set("zola_favs", [...S.favs]);
    toast(S.favs.has(k) ? "★ Agregado a favoritos" : "Quitado de favoritos", "", 1800);
    renderList(); if (S.sel === k) renderDetail({ keepTab: true });
    if (S.view === "leagues") viewLeagues();
  } else if (a === "pin") {
    e.stopPropagation();
    const id = String(t.dataset.id);
    S.pins.has(id) ? S.pins.delete(id) : S.pins.add(id);
    ls.set("zola_pins", [...S.pins]);
    toast(S.pins.has(id) ? "📌 Liga fijada arriba" : "Liga desfijada", "", 1800);
    S.view === "leagues" ? viewLeagues() : renderList();
  } else if (a === "filter") { S.filter = t.dataset.f; renderList(); }
  else if (a === "region") { S.region = t.dataset.r; renderList(); }
  else if (a === "date") setDate(t.dataset.d);
  else if (a === "day") setDate(addDays(S.date, +t.dataset.n));
  else if (a === "tab") {
    S.tab = t.dataset.t;
    $$(".tab").forEach((b) => b.classList.toggle("on", b.dataset.t === S.tab));
    renderTab();
  } else if (a === "league") { $("#suggest").hidden = true; location.hash = `#/ligas/${t.dataset.id}`; }
  else if (a === "back") { history.length > 1 ? history.back() : (location.hash = "#/"); }
  else if (a === "share") {
    navigator.clipboard?.writeText(location.href).then(() => toast("🔗 Enlace copiado", "", 1800), () => {});
  } else if (a === "savepick") {
    const d = S.detail; if (!d) return;
    const m = { ...d.match, ...(byKey(S.sel) || {}) }, p = d.prediction, bb = p.best_bet;
    const market = bb ? bb.market : (p.winner === "Empate" ? "X" : p.winner === m.home ? "1" : "2");
    S.picks.push({ key: m.match_key, date: S.date, league: m.league, home: m.home, away: m.away, home_logo: m.home_logo, away_logo: m.away_logo,
      market, prob: p.markets[market], odd: bb && bb.odd ? bb.odd : (d.odds[market] || null), predicted: p.best_score,
      scoreAt: `${m.home_goals || 0}-${m.away_goals || 0}`, savedAt: Date.now(), result: null, final: null });
    savePicks(); toast(`💾 Guardado: ${esc(MK_LABEL[market] || market)}`); renderTab(); renderRail();
  } else if (a === "delpick") {
    S.picks = S.picks.filter((x) => x.key !== t.dataset.key); savePicks(); viewPicks();
  } else if (a === "gopick") {
    if (t.dataset.date && t.dataset.date !== S.date) { S.date = t.dataset.date; S.loaded = false; }
    location.hash = `#/partido/${encodeURIComponent(t.dataset.key)}`;
    if (!S.loaded) loadMatches();
  } else if (a === "simmk") {
    S.sim.mk = t.dataset.mk; S.sim.odd = null; renderTab();
  }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement !== $("#q")) { e.preventDefault(); $("#q").focus(); }
  if (e.key === "Escape") { $("#suggest").hidden = true; $("#q").blur(); }
  if (e.key === "Enter" && e.target.classList?.contains("mrow")) openMatch(e.target.dataset.key);
});
$("#q").addEventListener("input", (e) => {
  S.q = e.target.value;
  renderSuggest();
  if (S.view === "matches") renderList();
});
$("#themeBtn").addEventListener("click", () => {
  const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = t; ls.set("zola_theme", t);
  $("#themeBtn").textContent = t === "dark" ? "🌙" : "☀️";
});
window.addEventListener("hashchange", route);

// ---------------- relojes ----------------
function tickCountdowns() {
  $$("[data-countdown]").forEach((el) => {
    const ms = +el.dataset.countdown - Date.now();
    if (ms <= 0) { el.textContent = "Por empezar"; return; }
    const h = Math.floor(ms / 3.6e6), m = Math.floor(ms % 3.6e6 / 6e4), s = Math.floor(ms % 6e4 / 1000);
    el.textContent = h > 47 ? `Empieza en ${Math.floor(h / 24)} días` : `Empieza en ${h ? h + "h " : ""}${pad(m)}m ${pad(s)}s`;
  });
}
setInterval(tickCountdowns, 1000);
setInterval(() => {
  if (document.hidden) return;
  const live = S.matches.some((m) => m.live);
  if (S.date === todayISO() || live) loadMatches({ quiet: true });
}, 60000);
setInterval(() => {
  if (document.hidden || S.view !== "matches") return;
  const m = byKey(S.sel);
  if (m && m.live) loadDetail(S.sel, { quiet: true });
}, 45000);

// ---------------- inicio ----------------
(function init() {
  const th = ls.get("zola_theme", "dark");
  document.documentElement.dataset.theme = th;
  $("#themeBtn").textContent = th === "dark" ? "🌙" : "☀️";
  updatePicksBadge();
  route();
  loadMatches();
})();
