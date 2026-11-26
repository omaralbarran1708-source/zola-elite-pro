/* ZOLA — interfaz */
"use strict";

// ================= utilidades =================
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
  return WD[new Date(iso + "T12:00:00").getDay()];
}
const dayShort = (iso) => { const d = new Date(iso + "T12:00:00"); return `${d.getDate()} ${MES[d.getMonth()]}`; };
const hhmm = (iso) => { if (!iso) return "—"; const d = new Date(iso); return isNaN(d) ? "—" : `${pad(d.getHours())}:${pad(d.getMinutes())}`; };
const formHtml = (f) => {
  const s = (f || "").slice(-5);
  if (!s) return '<span class="faint" style="font-size:.76rem">Sin forma</span>';
  return `<div class="form">${[...s].map((c) => `<span class="f${c}" title="${{ W: "Ganó", D: "Empató", L: "Perdió" }[c] || c}">${{ W: "G", D: "E", L: "P" }[c] || c}</span>`).join("")}</div>`;
};
const ZONE = {
  ucl: ["#2f55f5", "Champions / Libertadores"], uel: ["#f08c00", "Europa League / Sudamericana"],
  uecl: ["#0ea5a4", "Conference League"], rel: ["#e5383b", "Descenso"], po: ["#9b51e0", "Playoffs"],
  up: ["#14a44d", "Clasificación / ascenso"], oth: ["#8b93a4", "Otra zona"],
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
  return ({ "1": h > a, X: h === a, "2": h < a, "1X": h >= a, X2: h <= a, "12": h !== a,
    "Over 1.5": t > 1, "Under 1.5": t <= 1, "Over 2.5": t > 2, "Under 2.5": t <= 2, "Over 3.5": t > 3, "Under 3.5": t <= 3,
    "BTTS Sí": h > 0 && a > 0, "BTTS No": !(h > 0 && a > 0) })[mk];
}
const MK_LABEL = {
  "1": "Gana local", X: "Empate", "2": "Gana visita", "1X": "Local o empate", X2: "Empate o visita", "12": "No hay empate",
  "Over 1.5": "Más de 1.5 goles", "Under 1.5": "Menos de 1.5", "Over 2.5": "Más de 2.5 goles", "Under 2.5": "Menos de 2.5",
  "Over 3.5": "Más de 3.5 goles", "Under 3.5": "Menos de 3.5", "BTTS Sí": "Ambos marcan", "BTTS No": "No marcan ambos",
};
const fmtSeason = (s) => (s && s.length === 4 && !/^20/.test(s)) ? `20${s.slice(0, 2)}/${s.slice(2)}` : (s || "");
const countryName = (m) => (!m.country || m.country === "World") ? "Internacional" : m.country;
const CHEV = '<svg class="chev" width="14" height="14" viewBox="0 0 24 24"><path fill="currentColor" d="M12 8l6 6-1.4 1.4L12 10.8l-4.6 4.6L6 14z"/></svg>';

// ================= estado =================
const S = {
  date: todayISO(), status: null, region: "Todas", ltab: "all", q: "",
  matches: [], loaded: false, demo: true, notice: null, remaining: null, quick: {},
  sel: null, detail: null, detailFor: null, tab: "resumen",
  h2h: {}, standings: {}, view: "matches", league: null, mobileDetail: false,
  favs: new Set(ls.get("zola_favs", [])), pins: new Set(ls.get("zola_pins", [])),
  collapsed: new Set(), showProbs: ls.get("zola_probs", true), votes: ls.get("zola_votes", {}),
  picks: ls.get("zola_picks", []), sim: {}, bt: { leagues: null, league: "E0", season: null, weight: 35, thr: 5, res: null, loading: false, err: null },
};
let lastScores = {};

async function getJSON(url) {
  const r = await fetch(url, { headers: { Accept: "application/json" } });
  let j = null;
  try { j = await r.json(); } catch {}
  if (!r.ok) throw new Error((j && (j.error || j.detail)) || `Error ${r.status}`);
  return j;
}
function toast(html, cls = "", ms = 3800) {
  const el = document.createElement("div");
  el.className = `toast ${cls}`;
  el.innerHTML = html;
  $("#toasts").appendChild(el);
  setTimeout(() => { el.style.transition = ".3s"; el.style.opacity = 0; setTimeout(() => el.remove(), 300); }, ms);
}
function emptyHtml(icon, title, sub = "") { return `<div class="empty"><div class="i">${icon}</div><b>${title}</b>${sub}</div>`; }

// ================= datos =================
async function loadMatches({ quiet = false } = {}) {
  if (!quiet) { S.loaded = false; if (S.view === "matches") renderList(); }
  try {
    const j = await getJSON(`/api/matches?date=${S.date}`);
    detectGoals(j.matches);
    S.matches = j.matches; S.demo = j.demo; S.notice = j.notice; S.remaining = j.remaining;
  } catch {
    S.notice = "No se pudo conectar con el servidor. Reintentando…";
  }
  S.loaded = true;
  updateChip(); renderTicker();
  if (S.view === "matches") {
    ensureSelection();
    if (quiet) { renderList(); renderRail(); } else renderView();
    if (S.sel && (S.detailFor !== S.sel || !S.detail)) loadDetail(S.sel);
  } else if (!quiet) renderView();
  loadQuick();
  settlePicks();
}
async function loadQuick() {
  try { const j = await getJSON(`/api/quick?date=${S.date}`); S.quick = j.probs || {}; if (S.view === "matches" && S.showProbs) renderList(); } catch {}
}
function detectGoals(list) {
  const next = {};
  for (const m of list) {
    next[m.match_key] = [m.home_goals, m.away_goals];
    const prev = lastScores[m.match_key];
    if (!prev || !m.live) continue;
    if (m.home_goals > prev[0] || m.away_goals > prev[1]) {
      const home = m.home_goals > prev[0];
      toast(`<img src="${img(home ? m.home_logo : m.away_logo, home ? m.home : m.away)}"><span>⚽ ¡Gol de <b>${esc(home ? m.home : m.away)}</b>! ${esc(m.home)} ${m.home_goals}-${m.away_goals} ${esc(m.away)}</span>`, "goal", 6000);
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
    renderDetail();
  } catch (e) {
    if (!quiet && $("#detail")) $("#detail").innerHTML = emptyHtml("⚠️", "No se pudo cargar el partido", esc(e.message));
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
  if (S.standings[k] && !S.standings[k].loading) return S.standings[k];
  S.standings[k] = { loading: true };
  try { S.standings[k] = await getJSON(`/api/standings?league=${leagueId}&season=${season || ""}&demo=${demo ? 1 : 0}`); }
  catch { S.standings[k] = { groups: [], error: "No disponible" }; }
  return S.standings[k];
}

// ================= filtros =================
const baseList = () => S.matches
  .filter((m) => S.region === "Todas" || (m.buckets || []).includes(S.region))
  .filter((m) => !S.q || norm(`${m.home} ${m.away} ${m.league} ${m.country}`).includes(norm(S.q)));
const isFav = (m) => S.favs.has(m.match_key) || S.pins.has(String(m.league_id));
function filtered() {
  return baseList().filter((m) => {
    if (S.ltab === "favs" && !isFav(m)) return false;
    if (S.status === "live") return m.live;
    if (S.status === "finished") return m.finished;
    if (S.status === "upcoming") return !m.live && !m.finished;
    return true;
  });
}
function groupByLeague(list) {
  const g = new Map();
  for (const m of list) { const k = m.league_id ?? m.league; if (!g.has(k)) g.set(k, []); g.get(k).push(m); }
  const arr = [...g.values()];
  arr.forEach((ms) => ms.sort((a, b) => (b.live - a.live) || (a.finished - b.finished) || String(a.kickoff).localeCompare(String(b.kickoff))));
  const prio = (ms) => {
    const id = ms[0].league_id;
    const p = LEAGUE_PRIORITY.includes(id) ? LEAGUE_PRIORITY.indexOf(id) : (TOP_IDS.has(id) ? 50 : 100);
    return [S.pins.has(String(id)) ? 0 : 1, ms.some((x) => x.live) ? 0 : 1, p, ms[0].league];
  };
  return arr.sort((a, b) => { const pa = prio(a), pb = prio(b); for (let i = 0; i < 4; i++) { if (pa[i] < pb[i]) return -1; if (pa[i] > pb[i]) return 1; } return 0; });
}
function ensureSelection() {
  if (S.sel && S.matches.some((m) => m.match_key === S.sel)) return;
  const list = filtered();
  const pick = list.find((m) => m.live) || list.find((m) => !m.finished) || list[0];
  S.sel = pick ? pick.match_key : null;
}
const byKey = (k) => S.matches.find((m) => m.match_key === k);

// ================= comunes =================
function updateChip() {
  const c = $("#apichip");
  c.classList.toggle("ok", !S.demo);
  c.querySelector("span").textContent = S.demo ? "Modo demo" : `Datos en vivo${S.remaining != null ? ` · ${S.remaining}` : ""}`;
}
function renderTicker() {
  const live = S.matches.filter((m) => m.live);
  const lbl = $("#trendLbl");
  let list;
  if (live.length) { lbl.className = "trend-lbl live"; lbl.innerHTML = `<span class="pulse" style="background:#fff"></span>${live.length} en vivo`; list = live; }
  else {
    lbl.className = "trend-lbl"; lbl.textContent = "🔥 Destacados";
    list = S.matches.filter((m) => !m.finished).sort((a, b) => ((LEAGUE_PRIORITY.indexOf(a.league_id) + 1 || 99) - (LEAGUE_PRIORITY.indexOf(b.league_id) + 1 || 99)) || String(a.kickoff).localeCompare(String(b.kickoff))).slice(0, 16);
  }
  $("#ticker").innerHTML = list.length ? list.map((m) => `<a class="tk" href="#/partido/${encodeURIComponent(m.match_key)}" title="${esc(m.home)} vs ${esc(m.away)} · ${esc(m.league)}">
      ${m.live ? `<span class="m lv">${m.status_short === "HT" ? "ET" : m.minute + "'"}</span>` : `<span class="m">${hhmm(m.kickoff)}</span>`}
      <img src="${img(m.home_logo, m.home)}" alt="">${m.live ? `<span class="s">${m.home_goals}-${m.away_goals}</span>` : '<span class="dash">-</span>'}<img src="${img(m.away_logo, m.away)}" alt=""></a>`).join("")
    : `<span class="muted" style="font-size:.85rem">No hay partidos para ${dayName(S.date).toLowerCase()}.</span>`;
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
  const q = S.showProbs && S.quick[m.match_key];
  const mx = q ? Math.max(...q) : 0;
  const probs = q ? `<div class="mp" title="Probabilidad del modelo: 1 · X · 2">${q.map((v) => `<span class="${v === mx ? "top" : ""}">${pct(v)}</span>`).join("")}</div>` : "<div></div>";
  return `<div class="mrow${m.match_key === S.sel ? " sel" : ""}" data-key="${esc(m.match_key)}" data-act="open" role="button" tabindex="0">
    ${statusCell(m)}
    <div class="mteams">
      <div class="tl${hw ? " w" : ""}"><img src="${img(m.home_logo, m.home)}" alt="" loading="lazy"><span>${esc(m.home)}</span></div>
      <div class="tl${aw ? " w" : ""}"><img src="${img(m.away_logo, m.away)}" alt="" loading="lazy"><span>${esc(m.away)}</span></div>
    </div>${probs}
    <div class="msc${m.live ? " lv" : ""}">${started ? `<span>${m.home_goals}</span><span>${m.away_goals}</span>` : ""}</div>
    <button class="star${fav ? " on" : ""}" data-act="fav" data-key="${esc(m.match_key)}" aria-label="Favorito" title="${fav ? "Quitar de favoritos" : "Agregar a favoritos"}">${fav ? "★" : "☆"}</button>
  </div>`;
}
function leagueHead(ms) {
  const m = ms[0], nl = ms.filter((x) => x.live).length, id = String(m.league_id ?? m.league), col = S.collapsed.has(id);
  return `<div class="lgh${col ? " collapsed" : ""}">
    <img class="lg" src="${img(m.league_logo, m.league)}" alt="" loading="lazy">
    <div style="min-width:0"><div class="nm" data-act="league" data-id="${esc(id)}">${esc(m.league)}${m.source === "demo" ? '<span class="demo-tag">DEMO</span>' : ""}</div>
      <div class="ct">${m.flag ? `<img src="${img(m.flag, m.country)}" alt="">` : "🌐"}${esc(countryName(m))}</div></div>
    <span class="cnt">${nl ? `<b>${nl}</b>/` : ""}${ms.length}</span>
    <button class="circ pin${S.pins.has(id) ? " on" : ""}" data-act="pin" data-id="${esc(id)}" title="Fijar liga arriba">📌</button>
    <button class="circ" data-act="collapse" data-id="${esc(id)}" title="${col ? "Mostrar" : "Ocultar"} partidos">${CHEV}</button>
  </div>`;
}

// ================= vista RESULTADOS =================
function viewMatches() {
  $("#app").innerHTML = `
    <div class="crumb">Fútbol hoy · resultados en vivo, calendario y pronósticos de las principales ligas</div>
    ${S.notice ? `<div class="notice">ℹ️ ${esc(S.notice)}</div>` : ""}
    <div class="layout${S.mobileDetail ? " show-detail" : ""}" id="layout">
      <section class="card list-col" aria-label="Partidos">
        <div class="ltabs" id="ltabs"></div>
        <div class="fbar" id="fbar"></div>
        <div class="regions" id="regions"></div>
        <div class="mlist" id="mlist"></div>
      </section>
      <section class="card detail-col sticky" id="detail" aria-label="Partido"></section>
      <aside class="rail sticky" id="rail"></aside>
    </div>`;
  renderList(); renderDetail(); renderRail();
}
function renderList() {
  const el = $("#mlist"); if (!el) return;
  $("#ltabs").innerHTML = [["all", "Todos"], ["favs", "Favoritos"], ["comps", "Competiciones"]]
    .map(([k, l]) => `<button class="ltab${S.ltab === k ? " on" : ""}" data-act="ltab" data-t="${k}">${l}</button>`).join("") +
    `<div class="datenav"><button data-act="day" data-n="-1" aria-label="Día anterior">‹</button>
      <label class="dlabel">${dayName(S.date) === "Hoy" || dayName(S.date) === "Mañana" || dayName(S.date) === "Ayer" ? dayName(S.date) : `${dayName(S.date)} ${dayShort(S.date)}`}<input type="date" id="dpick" value="${S.date}" aria-label="Elegir fecha"></label>
      <button data-act="day" data-n="1" aria-label="Día siguiente">›</button></div>`;
  $("#dpick").addEventListener("change", (e) => e.target.value && setDate(e.target.value));
  const base = baseList().filter((m) => S.ltab !== "favs" || isFav(m));
  const n = { live: base.filter((m) => m.live).length, finished: base.filter((m) => m.finished).length, upcoming: base.filter((m) => !m.live && !m.finished).length };
  $("#fbar").innerHTML = `
    <button class="chip live${S.status === "live" ? " on" : ""}" data-act="status" data-s="live">${n.live ? '<span class="pulse"></span>' : ""}En vivo (${n.live})</button>
    <button class="chip${S.status === "finished" ? " on" : ""}" data-act="status" data-s="finished">Terminados</button>
    <button class="chip${S.status === "upcoming" ? " on" : ""}" data-act="status" data-s="upcoming">Próximos</button>
    <label class="toggle${S.showProbs ? " on" : ""}" data-act="probs" title="Mostrar probabilidades del modelo">Probabilidades <span class="switch"></span></label>`;
  $("#regions").innerHTML = ["Todas", "Top", "Europa", "Sudamérica", "Internacional"]
    .map((r) => `<button class="rchip${S.region === r ? " on" : ""}" data-act="region" data-r="${r}">${r === "Top" ? "⭐ Top" : r}</button>`).join("");
  if (!S.loaded) { el.innerHTML = Array.from({ length: 8 }, () => '<div class="skrow"><div class="sk a"></div><div class="sk b"></div><div class="sk c"></div></div>').join(""); return; }
  const list = filtered();
  if (S.ltab === "comps") {
    const groups = groupByLeague(list);
    el.innerHTML = groups.length ? groups.map((ms) => {
      const m = ms[0], nl = ms.filter((x) => x.live).length;
      return `<div class="lgh" style="position:static;cursor:pointer" data-act="league" data-id="${esc(String(m.league_id ?? m.league))}"><img class="lg" src="${img(m.league_logo, m.league)}" alt="">
        <div><div class="nm">${esc(m.league)}</div><div class="ct">${m.flag ? `<img src="${img(m.flag, m.country)}" alt="">` : "🌐"}${esc(countryName(m))}</div></div>
        <span class="cnt">${nl ? `<b>${nl}</b>/` : ""}${ms.length}</span><span class="circ">›</span></div>`;
    }).join("") : emptyHtml("🏆", "No hay competiciones con estos filtros");
    return;
  }
  if (!list.length) {
    const msg = S.ltab === "favs" ? ["⭐", "Aún no tienes favoritos", "Toca ☆ en un partido o 📌 en una liga."] :
      S.status === "live" ? ["📺", "No hay partidos en vivo", "Revisa los próximos o cambia de día."] :
      ["🏟️", "No hay partidos con estos filtros", "Prueba con «Todas» o cambia la fecha."];
    el.innerHTML = emptyHtml(...msg); return;
  }
  const st = el.scrollTop;
  el.innerHTML = groupByLeague(list).map((ms) => {
    const id = String(ms[0].league_id ?? ms[0].league);
    return leagueHead(ms) + (S.collapsed.has(id) ? "" : ms.map(matchRow).join(""));
  }).join("");
  el.scrollTop = st;
}

// ================= detalle =================
const TABS = [["resumen", "Resumen"], ["pronostico", "Pronóstico"], ["stats", "Estadísticas"], ["eventos", "Eventos"],
  ["h2h", "Cara a cara"], ["tabla", "Clasificación"], ["cuotas", "Cuotas"], ["sim", "Simulador"]];

function renderDetail() {
  const el = $("#detail"); if (!el) return;
  if (!S.sel) { el.innerHTML = emptyHtml("👈", "Elige un partido", "Verás el pronóstico, estadísticas y más."); return; }
  const m0 = byKey(S.sel);
  const d = S.detail && S.detailFor === S.sel ? S.detail : null;
  if (!d) {
    el.innerHTML = `<div class="pad"><div class="sk" style="height:28px;width:55%"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;margin:26px 0"><div class="sk" style="height:110px"></div><div class="sk" style="height:110px"></div><div class="sk" style="height:110px"></div></div>
      <div class="sk" style="height:120px;margin-bottom:12px"></div><div class="sk" style="height:80px"></div></div>`;
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
    center = `<div class="kick">${hhmm(m.kickoff)}</div><div class="when">${k ? (dayName(isoDay(k)).length > 3 ? dayName(isoDay(k)) : `${dayName(isoDay(k))} ${dayShort(isoDay(k))}`) : ""}</div>
      ${k ? `<div class="countdown" data-countdown="${k.getTime()}"></div>` : ""}`;
  }
  el.innerHTML = `
    <div class="dhead">
      <button class="circ back" data-act="back" aria-label="Volver">←</button>
      <img src="${img(m.league_logo, m.league)}" alt="">
      <div><div class="nm" data-act="league" data-id="${esc(String(m.league_id ?? m.league))}">${esc(m.league)}${m.source === "demo" ? '<span class="demo-tag">DEMO</span>' : ""}</div>
        <div class="sub">${esc(countryName(m))}${m.round ? " · " + esc(m.round) : ""}</div></div>
      <div class="acts">
        <button class="star${fav ? " on" : ""}" data-act="fav" data-key="${esc(m.match_key)}" title="Favorito">${fav ? "★" : "☆"}</button>
        <button class="circ" data-act="share" title="Copiar enlace">🔗</button>
      </div>
    </div>
    <div class="score">
      <div class="team"><img src="${img(m.home_logo, m.home)}" alt=""><div class="nm">${esc(m.home)}</div>${formHtml(d.forms.home.form)}</div>
      <div class="center">${center}</div>
      <div class="team"><img src="${img(m.away_logo, m.away)}" alt=""><div class="nm">${esc(m.away)}</div>${formHtml(d.forms.away.form)}</div>
    </div>
    ${m.venue ? `<div class="venue">🏟️ ${esc(m.venue)}</div>` : '<div style="height:8px"></div>'}
    ${m.finished ? "" : voteBox(m, d.prediction)}
    ${oddsRow(d, d.prediction)}
    <div class="tabs" role="tablist">${TABS.map(([k, l]) => `<button class="tab${S.tab === k ? " on" : ""}" data-act="tab" data-t="${k}" role="tab">${l}</button>`).join("")}</div>
    <div class="tabbody" id="tabbody"></div>`;
  tickCountdowns();
  renderTab();
}
function voteBox(m, p) {
  const mine = S.votes[m.match_key];
  const vals = [["1", p.home_win], ["X", p.draw], ["2", p.away_win]];
  const top = Math.max(...vals.map((v) => v[1]));
  const ic = { "1": `<img src="${img(m.home_logo, m.home)}" alt="">`, X: "<span>X</span>", "2": `<img src="${img(m.away_logo, m.away)}" alt="">` };
  if (!mine) {
    return `<div class="inner"><h4>¿Quién gana? <span class="ico">🏆</span></h4><div class="s">Vota y compara con el modelo ZOLA</div>
      <div class="vote">${vals.map(([k]) => `<button class="vbtn" data-act="vote" data-v="${k}" title="${k === "1" ? esc(m.home) : k === "2" ? esc(m.away) : "Empate"}">${ic[k]}</button>`).join("")}</div></div>`;
  }
  const agree = vals.find((v) => v[1] === top)[0] === mine;
  return `<div class="inner"><h4>¿Quién gana? <span class="conf ${p.confidence}" style="margin-left:6px">Confianza ${p.confidence.toLowerCase()}</span><span class="ico">🏆</span></h4>
    <div class="s">Probabilidad del modelo ZOLA · tu voto está resaltado</div>
    <div class="vote done">${vals.map(([k, v]) => `<button class="vbtn${k === mine ? " mine" : ""}" data-act="vote" data-v="${k}"><i style="width:${(v * 100).toFixed(1)}%"></i>${ic[k]}<span>${pct(v)}</span></button>`).join("")}</div>
    <div class="vnote">${agree ? "✅ Coincides con el favorito del modelo." : "🤔 Vas contra el favorito del modelo."} <a href="#" data-act="unvote" style="color:var(--brand-ink);font-weight:700">Cambiar voto</a></div></div>`;
}
function oddsRow(d, p) {
  const o = d.odds || {};
  if (!(o["1"] && o.X && o["2"])) return "";
  const cell = (k) => {
    const edge = p.markets[k] * o[k] - 1;
    const ar = edge > 0.03 ? '<span class="up" title="El modelo ve valor">▲</span>' : edge < -0.03 ? '<span class="dn" title="Paga poco para su probabilidad">▼</span>' : "";
    return `<div><span class="muted">${k}</span><b>${o[k].toFixed(2)}${ar}</b></div>`;
  };
  return `<div class="oddsrow"><div class="hd"><span>Cuotas · resultado final</span><span class="bk">${d.match.live ? "EN VIVO" : "bet365"}</span></div>
    <div class="odds3">${cell("1")}${cell("X")}${cell("2")}</div><div class="oddsnote">▲ el modelo ve valor · ▼ la cuota paga poco para su probabilidad</div></div>`;
}
function renderTab() {
  const el = $("#tabbody"); if (!el || !S.detail) return;
  const d = S.detail, m = { ...d.match, ...(byKey(S.sel) || {}) }, p = d.prediction;
  const fn = { resumen: tabResumen, pronostico: tabPronostico, stats: tabStats, eventos: tabEventos, h2h: tabH2H, tabla: tabTabla, cuotas: tabCuotas, sim: tabSim }[S.tab] || tabResumen;
  el.innerHTML = fn(m, d, p);
  if (S.tab === "sim") bindSim(m, d, p);
}
function pickBox(m, d, p) {
  if (m.finished) {
    const saved = S.picks.find((x) => x.key === m.match_key);
    return `<div class="box"><div class="pick"><div class="ic">🏁</div><div><div class="t">Partido terminado</div>
      <div class="v">${esc(m.home)} ${m.home_goals}-${m.away_goals} ${esc(m.away)}</div>
      <div class="x">${saved ? (saved.result === "won" ? "✅ Acertaste tu pronóstico" : saved.result === "lost" ? "❌ Tu pronóstico no se cumplió" : "Cerrando tu pronóstico…") : "El modelo esperaba " + esc(p.best_score)}</div></div></div></div>`;
  }
  const bb = p.best_bet;
  let inner;
  if (!bb) inner = `<div class="ic">🛑</div><div><div class="t">Recomendación</div><div class="v">No apostar</div><div class="x">Ningún mercado tiene suficiente probabilidad o valor.</div></div>`;
  else if (bb.kind === "valor") inner = `<div class="ic">🎯</div><div><div class="t">Apuesta de valor</div><div class="v">${esc(MK_LABEL[bb.market] || bb.market)} @ ${bb.odd.toFixed(2)}</div>
      <div class="x">ZOLA ${pct(bb.prob)} vs casa ${pct(bb.implied)}</div></div><div class="e" style="color:var(--green)">+${pct(bb.edge)}<small>ventaja</small></div>`;
  else inner = `<div class="ic">📌</div><div><div class="t">Jugada más probable</div><div class="v">${esc(MK_LABEL[bb.market] || bb.market)}</div>
      <div class="x">${Object.keys(d.odds || {}).length ? "La cuota actual no ofrece valor." : "Sin cuotas para medir valor."}</div></div><div class="e">${pct(bb.prob)}<small>prob.</small></div>`;
  const saved = S.picks.some((x) => x.key === m.match_key);
  return `<div class="box"><div class="pick">${inner}</div>
    <div style="margin-top:14px"><button class="btn ${saved ? "" : "primary"} block" data-act="savepick" ${saved ? "disabled" : ""}>${saved ? "✓ Guardado en Mis pronósticos" : "💾 Guardar en Mis pronósticos"}</button></div></div>`;
}
function aiText(m, p) {
  if (m.finished) return `Terminó <b>${esc(m.home)} ${m.home_goals}-${m.away_goals} ${esc(m.away)}</b>. El modelo esperaba <b>${esc(p.best_score)}</b>.`;
  const fav = Math.max(p.home_win, p.draw, p.away_win);
  const lead = p.winner === "Empate" ? "El <b>empate</b> es lo más probable" : `<b>${esc(p.winner)}</b> es favorito`;
  return `${lead} (${pct(fav)}). Marcador final más probable: <b>${esc(p.best_score)}</b>.<br>
    Goles esperados en 90′: ${esc(m.home)} <b>${p.lam_home.toFixed(2)}</b> · ${esc(m.away)} <b>${p.lam_away.toFixed(2)}</b>.
    <div class="notes"><span>📊 ${esc(p.source || p.data_quality)}</span>${(p.notes || []).map((n) => `<span>${esc(n)}</span>`).join("")}</div>`;
}
function compareBox(p) {
  if (!p.market_1x2 || !p.market_1x2.length) return "";
  const rows = [["Modelo", p.model_1x2], ["Mercado", p.market_1x2], [`ZOLA final`, [p.home_win, p.draw, p.away_win]]];
  return `<div class="box"><h4>Modelo vs. mercado</h4><div class="s">ZOLA combina su modelo con la casa (${pct(p.blend_weight)} mercado). Compara en «Probar modelo» qué funciona mejor.</div>
    <div class="cmp3"><span></span><span class="h">1</span><span class="h">X</span><span class="h">2</span>
    ${rows.map(([l, v]) => { const mx = Math.max(...v); return `<span class="r">${l}</span>${v.map((x) => `<span class="c${x === mx ? " hi" : ""}">${pct(x)}</span>`).join("")}`; }).join("")}</div></div>`;
}
function strengthBox(m, d) {
  const r = d.ratings; if (!r) return "";
  const side = (s, name, logo) => `<div class="sb"><div class="tn"><img src="${img(logo, name)}" alt="">${esc(name)}</div>
    <div class="row"><span class="muted">Ataque</span><b>#${s.attack_rank} de ${r.teams} · ${s.attack.toFixed(2)}</b></div>
    <div class="row"><span class="muted">Defensa</span><b>#${s.defense_rank} de ${r.teams} · ${s.defense.toFixed(2)}</b></div>
    <div class="row"><span class="muted">Partidos</span><b>${s.games}</b></div></div>`;
  return `<div class="box"><h4>Fuerza en la temporada</h4><div class="s">Ratings del motor (1.00 = promedio; ataque alto y defensa baja es mejor) · localía ×${r.home_adv.toFixed(2)} · ${r.matches} partidos</div>
    <div class="strength">${side(r.home, m.home, m.home_logo)}${side(r.away, m.away, m.away_logo)}</div></div>`;
}
function tabResumen(m, d, p) {
  return `${pickBox(m, d, p)}<div class="box ai"><h4 style="margin-bottom:6px">Análisis ZOLA</h4>${aiText(m, p)}</div>
    ${compareBox(p)}
    <div class="kpis">${[["+1.5 goles", p.over15], ["+2.5 goles", p.over25], ["+3.5 goles", p.over35], ["Ambos marcan", p.btts]]
      .map(([l, v]) => `<div class="kpi"><div class="l">${l}</div><div class="v">${pct(v)}</div><div class="t"><div style="width:${(v * 100).toFixed(0)}%"></div></div></div>`).join("")}</div>
    ${strengthBox(m, d)}
    ${d.warnings && d.warnings.length ? `<div class="notes">${d.warnings.map((w) => `<span>⚠️ ${esc(w)}</span>`).join("")}</div>` : ""}`;
}
function tabPronostico(m, d, p) {
  const mx = p.matrix || [];
  const max = Math.max(...mx.flat(), 0.0001);
  const cells = mx.map((row, i) => `<div class="h">${i}</div>` + row.map((v, j) => {
    const a = Math.min(1, v / max);
    const cur = m.live && i === m.home_goals && j === m.away_goals ? " cur" : "";
    return `<div class="c${cur}" style="background:rgba(47,85,245,${(0.06 + a * 0.82).toFixed(2)});color:${a > 0.55 ? "#fff" : "var(--text)"}" title="${esc(m.home)} ${i}-${j} ${esc(m.away)}: ${pct(v, 1)}">${v >= 0.005 ? pct(v) : ""}</div>`;
  }).join("")).join("");
  const markets = ["1", "X", "2", "1X", "X2", "Over 1.5", "Over 2.5", "Over 3.5", "BTTS Sí", "BTTS No"];
  const top = (p.top_scores || []).slice(0, 6), tmax = Math.max(...top.map((t) => t[1]), 0.0001);
  return `<div class="box"><h4>Mapa de marcadores finales</h4><div class="s">Filas: goles de ${esc(m.home)} · columnas: goles de ${esc(m.away)}${m.live ? " · borde dorado = marcador actual" : ""}</div>
      <div class="heat"><div></div>${[0, 1, 2, 3, 4, 5].map((j) => `<div class="h">${j}</div>`).join("")}${cells}</div></div>
    <div class="box"><h4>Mercados</h4><div class="s">Probabilidad estimada por ZOLA</div>
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
    <div class="bars"><div class="half"><div class="bh" style="width:${h / tot * 100}%"></div></div><div class="half"><div class="ba" style="width:${a / tot * 100}%"></div></div></div></div>`;
}
function tabStats(m, d) {
  const h = d.stats.home || {}, a = d.stats.away || {}, fh = d.forms.home, fa = d.forms.away;
  const season = `<div class="box"><h4>Promedios de la temporada</h4><div class="s">${esc(m.home)} de local · ${esc(m.away)} de visita</div>
    ${statBar("Goles a favor por partido", fh.gf_home, fa.gf_away)}${statBar("Goles en contra por partido", fh.ga_home, fa.ga_away)}${statBar("Partidos jugados", fh.gp_home, fa.gp_away)}</div>`;
  if (!Object.keys(h).length && !Object.keys(a).length) return `${season}${emptyHtml("⏳", "Estadísticas del partido", "Aparecen cuando empieza el partido.")}`;
  const rows = [["Posesión", "possession", true], ["Goles esperados (xG)", "xg"], ["Tiros totales", "shots"], ["Tiros al arco", "shots_on_target"],
    ["Córners", "corners"], ["Atajadas", "saves"], ["Precisión de pases", "pass_acc", true], ["Faltas", "fouls"], ["Amarillas", "yellow"], ["Rojas", "red"]];
  return `<div class="box"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
      <span style="display:flex;gap:8px;align-items:center;font-weight:800"><img src="${img(m.home_logo, m.home)}" style="width:24px;height:24px;object-fit:contain">${esc(m.home)}</span>
      <span style="display:flex;gap:8px;align-items:center;font-weight:800">${esc(m.away)}<img src="${img(m.away_logo, m.away)}" style="width:24px;height:24px;object-fit:contain"></span></div>
      ${rows.map(([l, k, pc]) => statBar(l, h[k], a[k], pc)).join("")}</div>${season}`;
}
const DETAIL_ES = { "Normal Goal": "Gol", "Own Goal": "Autogol", Penalty: "Penal", "Missed Penalty": "Penal fallado", "Yellow Card": "Amarilla",
  "Red Card": "Roja", "Second Yellow card": "Doble amarilla", "Goal cancelled": "Gol anulado (VAR)", "Penalty confirmed": "Penal confirmado (VAR)" };
function tabEventos(m, d) {
  const evs = [...(d.events || [])].sort((a, b) => (a.min - b.min) || ((a.extra || 0) - (b.extra || 0)));
  if (!evs.length) return emptyHtml("⏱️", "Sin eventos todavía", m.live || m.finished ? "" : "Los goles, tarjetas y cambios aparecen en vivo.");
  let h = 0, a = 0, ht = false;
  const out = [];
  for (const e of evs) {
    if (!ht && e.min > 45) { out.push(`<div class="ev-sep"><span>Entretiempo · ${h}-${a}</span></div>`); ht = true; }
    const home = e.team === m.home;
    let ico = { Goal: "⚽", Card: "🟨", subst: "🔁", Var: "📺" }[e.type] || "•";
    if (e.type === "Card" && /Red|Second Yellow/.test(e.detail)) ico = "🟥";
    if (e.type === "Goal" && e.detail === "Missed Penalty") ico = "❌";
    let sc = "";
    if (e.type === "Goal" && e.detail !== "Missed Penalty") { home ? h++ : a++; sc = `<span class="sc">${h}-${a}</span>`; }
    const sub = e.type === "subst" ? (e.assist ? `↔ ${esc(e.assist)}` : "Cambio") : `${esc(DETAIL_ES[e.detail] || e.detail)}${e.type === "Goal" && e.assist ? ` · asist. ${esc(e.assist)}` : ""}`;
    const who = `<div class="who"><b>${esc(e.player || e.team)}</b><small>${sub}</small></div>`;
    const min = `<div class="min">${e.min}${e.extra ? "+" + e.extra : ""}'</div>`;
    out.push(`<div class="ev">${home ? `<div class="side l">${sc}${who}<span>${ico}</span></div>${min}<div></div>` : `<div></div>${min}<div class="side"><span>${ico}</span>${who}${sc}</div>`}</div>`);
  }
  if (m.finished) out.push(`<div class="ev-sep"><span>Final · ${m.home_goals}-${m.away_goals}</span></div>`);
  return `<div class="box"><div class="tline">${out.reverse().join("")}</div></div>`;
}
function tabH2H(m) {
  const st = S.h2h[m.match_key];
  if (!st) { loadH2H(m.match_key); return '<div class="sk" style="height:220px"></div>'; }
  if (st.loading) return '<div class="sk" style="height:220px"></div>';
  const list = st.matches || [];
  if (!list.length) return emptyHtml("🤝", "Sin enfrentamientos previos", st.error ? esc(st.error) : "");
  let w = 0, dr = 0, l = 0;
  for (const x of list) { const hg = x.home === m.home ? x.home_goals : x.away_goals, ag = x.home === m.home ? x.away_goals : x.home_goals; hg > ag ? w++ : hg === ag ? dr++ : l++; }
  const t = list.length;
  return `<div class="box"><h4>Últimos ${t} cruces${list[0].source === "demo" ? '<span class="demo-tag">DEMO</span>' : ""}</h4><div class="s">Resultados entre ambos equipos</div>
    <div class="h2hsum"><div><b style="color:var(--brand-ink)">${w}</b><span>${esc(m.home)}</span></div><div><b>${dr}</b><span>Empates</span></div><div><b style="color:var(--orange)">${l}</b><span>${esc(m.away)}</span></div></div>
    <div class="h2hbar"><div style="width:${w / t * 100}%;background:var(--brand)"></div><div style="width:${dr / t * 100}%;background:var(--grey)"></div><div style="width:${l / t * 100}%;background:var(--orange)"></div></div>
    ${list.map((x) => `<div class="h2hrow"><span class="d">${x.kickoff ? new Date(x.kickoff).toLocaleDateString("es-PE", { day: "2-digit", month: "short", year: "2-digit" }) : ""}</span>
      <span class="t r"><span>${esc(x.home)}</span><img src="${img(x.home_logo, x.home)}" alt=""></span><span class="r">${x.home_goals}-${x.away_goals}</span>
      <span class="t"><img src="${img(x.away_logo, x.away)}" alt=""><span>${esc(x.away)}</span></span></div>`).join("")}</div>`;
}
function standingsTable(groups, highlight = []) {
  const zones = new Map();
  const html = groups.map((g) => `${groups.length > 1 ? `<div class="sec-title" style="margin-top:12px">${esc(g.name)}</div>` : ""}
    <div class="tblwrap"><table class="tbl"><thead><tr><th>#</th><th class="l">Equipo</th><th>PJ</th><th>G</th><th>E</th><th>P</th><th>DG</th><th>Goles</th><th>Últimos 5</th><th>PTS</th></tr></thead><tbody>
    ${g.rows.map((r) => { const z = zoneOf(r.zone || r.description); if (z) zones.set(z, ZONE[z]);
      return `<tr class="${highlight.includes(r.team) ? "hl" : ""}"><td class="rk"><i style="background:${z ? ZONE[z][0] : "transparent"}"></i>${r.rank}</td>
        <td class="l"><span class="tm"><img src="${img(r.logo, r.team)}" alt="" loading="lazy">${esc(r.team)}</span></td>
        <td>${r.played}</td><td>${r.win}</td><td>${r.draw}</td><td>${r.lose}</td><td>${r.diff > 0 ? "+" : ""}${r.diff}</td><td>${r.gf}:${r.ga}</td><td>${formHtml(r.form)}</td><td class="pts">${r.points}</td></tr>`; }).join("")}
    </tbody></table></div>`).join("");
  const leg = [...zones.values()].map(([c, l]) => `<span><i style="background:${c}"></i>${l}</span>`).join("");
  return html + (leg ? `<div class="legend">${leg}</div>` : "");
}
function tabTabla(m) {
  const k = `${m.league_id}_${m.season}`, st = S.standings[k];
  if (!st) { loadStandings(m.league_id, m.season, m.source === "demo").then(() => { if (S.tab === "tabla") renderTab(); }); return '<div class="sk" style="height:300px"></div>'; }
  if (st.loading) return '<div class="sk" style="height:300px"></div>';
  if (!st.groups || !st.groups.length) return emptyHtml("📋", "Sin tabla de posiciones", "Esta competición no tiene tabla (o no está disponible).");
  return `<div class="box">${m.source === "demo" ? '<div class="s">Tabla de ejemplo (DEMO)</div>' : ""}${standingsTable(st.groups, [m.home, m.away])}</div>`;
}
function tabCuotas(m, d, p) {
  const vb = p.value_bets || [];
  if (!vb.length) return emptyHtml("💤", "No hay cuotas para este partido", m.finished ? "El partido ya terminó." : "La casa aún no publica cuotas.");
  return `<div class="box"><h4>Cuotas vs. ZOLA</h4><div class="s">Ventaja = probabilidad ZOLA × cuota − 1. Positiva = el modelo ve valor.</div>
    <div class="tblwrap"><table class="tbl otbl"><thead><tr><th>Mercado</th><th>Cuota</th><th>Prob. ZOLA</th><th>Prob. casa</th><th>Ventaja</th></tr></thead><tbody>
    ${vb.map((v) => `<tr><td>${esc(MK_LABEL[v.market] || v.market)}${v.edge >= 0.03 && v.prob >= 0.3 ? '<span class="vtag">VALOR</span>' : ""}</td><td><b>${v.odd.toFixed(2)}</b></td>
      <td>${pct(v.prob)}</td><td class="muted">${pct(v.implied)}</td><td class="${v.edge > 0 ? "edge-pos" : "edge-neg"}">${v.edge > 0 ? "+" : ""}${pct(v.edge, 1)}</td></tr>`).join("")}
    </tbody></table></div></div>`;
}
function tabSim(m, d, p) {
  const s = S.sim, bb = p.best_bet || {};
  if (s.key !== m.match_key) Object.assign(s, { key: m.match_key, mk: p.markets[bb.market] != null ? bb.market : "1", odd: null, bank: s.bank || 500 });
  const odd = s.odd && s.mkFor === s.mk ? s.odd : (d.odds[s.mk] || +(1 / Math.max(p.markets[s.mk], 0.01)).toFixed(2));
  return `<div class="box"><h4>Simulador de apuesta</h4><div class="s">Toca un mercado; el stake se calcula con el criterio de Kelly</div>
    <div class="mktgrid">${Object.keys(p.markets).map((k) => `<button class="mktbtn${k === s.mk ? " on" : ""}" data-act="simmk" data-mk="${esc(k)}"><small>${esc(MK_LABEL[k] || k)}</small><b>${pct(p.markets[k])}</b>${d.odds[k] ? ` <span class="muted" style="font-size:.75rem">@${d.odds[k].toFixed(2)}</span>` : ""}</button>`).join("")}</div>
    <div class="simgrid">
      <div class="field"><label>Cuota</label><input type="number" id="simOdd" min="1.01" step="0.05" value="${(+odd).toFixed(2)}"></div>
      <div class="field"><label>Bankroll (S/)</label><input type="number" id="simBank" min="10" step="50" value="${s.bank}"></div>
      <div class="field"><label>Riesgo</label><select id="simRisk"><option value="0.25">Prudente (¼ Kelly)</option><option value="0.5">Medio (½ Kelly)</option><option value="1">Agresivo (Kelly)</option></select></div>
    </div><div class="kpis" id="simOut" style="margin:0"></div><div class="s" id="simNote" style="margin:10px 0 0"></div></div>`;
}
function bindSim(m, d, p) {
  const s = S.sim, risk = $("#simRisk");
  risk.value = String(s.risk || 0.25);
  const calc = () => {
    const odd = parseFloat($("#simOdd").value) || 1.01, bank = parseFloat($("#simBank").value) || 0, r = parseFloat(risk.value);
    Object.assign(s, { odd, mkFor: s.mk, bank, risk: r });
    const pr = p.markets[s.mk], ev = pr * odd - 1, k = odd > 1 ? Math.max(0, (pr * odd - 1) / (odd - 1)) : 0;
    const stake = Math.round(bank * k * r * 100) / 100;
    $("#simOut").innerHTML = [["Prob. ZOLA", pct(pr, 1)], ["Valor esperado", `<span style="color:${ev > 0 ? "var(--green)" : "var(--red)"}">${ev > 0 ? "+" : ""}${pct(ev, 1)}</span>`],
      ["Stake sugerido", `S/${stake.toFixed(2)}`], ["Si acierta", `S/${(stake * (odd - 1)).toFixed(2)}`]]
      .map(([l, v]) => `<div class="kpi" style="background:var(--panel)"><div class="l">${l}</div><div class="v">${v}</div></div>`).join("");
    $("#simNote").textContent = ev <= 0 ? "Con esta cuota la apuesta pierde a la larga según el modelo; por eso el stake sugerido es 0." :
      `A largo plazo, por cada S/100 apostados el modelo espera ganar S/${(ev * 100).toFixed(2)}. Cuota justa: ${(1 / pr).toFixed(2)}.`;
  };
  ["#simOdd", "#simBank"].forEach((id) => $(id).addEventListener("input", calc));
  risk.addEventListener("change", calc);
  calc();
}

// ================= columna derecha =================
function renderRail() {
  const el = $("#rail"); if (!el) return;
  if (!S.loaded) { el.innerHTML = '<div class="card pad"><div class="sk" style="height:160px"></div></div>'; return; }
  const pool = S.matches.filter((m) => !m.finished);
  const feat = [...pool].sort((a, b) => (b.live - a.live) || ((LEAGUE_PRIORITY.indexOf(a.league_id) + 1 || 99) - (LEAGUE_PRIORITY.indexOf(b.league_id) + 1 || 99)))[0];
  const live = S.matches.filter((m) => m.live).slice(0, 6);
  const done = S.picks.filter((x) => x.result === "won" || x.result === "lost"), won = done.filter((x) => x.result === "won").length;
  const bt = S.bt.res;
  el.innerHTML = `
    ${feat ? `<div class="card feat"><div class="sec-title">🔥 Partido destacado</div>
      <div class="lg"><img src="${img(feat.league_logo, feat.league)}" alt="">${esc(feat.league)}</div>
      <div class="row" data-act="open" data-key="${esc(feat.match_key)}">
        <div><img src="${img(feat.home_logo, feat.home)}" alt=""><div class="n">${esc(feat.home)}</div></div>
        <div>${feat.live ? `<div class="big" style="font-size:1.7rem">${feat.home_goals}-${feat.away_goals}</div><div class="lvmin" style="font-size:.8rem"><span class="pulse"></span>${feat.minute}'</div>` : `<div class="kick" style="font-size:1.25rem">${hhmm(feat.kickoff)}</div><div class="muted" style="font-size:.78rem">${dayName(S.date)}</div>`}</div>
        <div><img src="${img(feat.away_logo, feat.away)}" alt=""><div class="n">${esc(feat.away)}</div></div>
      </div><button class="btn primary block" style="margin-top:14px" data-act="open" data-key="${esc(feat.match_key)}">Ver pronóstico</button></div>` : ""}
    ${live.length ? `<div class="card"><div class="sec-title pad" style="margin:0;padding-bottom:8px"><span class="pulse"></span>En vivo ahora <small>${S.matches.filter((m) => m.live).length}</small></div>
      ${live.map((m) => `<div class="mini" data-act="open" data-key="${esc(m.match_key)}"><img src="${img(m.home_logo, m.home)}" alt=""><span>${esc(m.home)}</span><span class="muted">vs</span><span>${esc(m.away)}</span><span class="res" style="color:var(--red)">${m.home_goals}-${m.away_goals}</span></div>`).join("")}</div>` : ""}
    <div class="card pad"><div class="sec-title">🧪 ¿Qué tan bueno es el modelo?</div>
      ${bt ? `<div class="kpis" style="grid-template-columns:1fr 1fr;margin-bottom:10px"><div class="kpi"><div class="l">Acierto 1X2</div><div class="v">${pct(bt.systems.model.accuracy)}</div><div class="d">${esc(bt.league_name)} ${esc(fmtSeason(bt.season))}</div></div>
        <div class="kpi"><div class="l">ROI valor</div><div class="v" style="color:${(bt.betting.blend.roi || 0) >= 0 ? "var(--green)" : "var(--red)"}">${bt.betting.blend.roi != null ? (bt.betting.blend.roi >= 0 ? "+" : "") + pct(bt.betting.blend.roi, 1) : "—"}</div><div class="d">${bt.betting.blend.bets} apuestas</div></div></div>` :
        '<p class="muted" style="margin:0 0 12px;font-size:.85rem;line-height:1.5">Pruébalo con temporadas reales y cuotas de cierre de las casas.</p>'}
      <a class="btn block" href="#/probar">Probar modelo</a></div>
    <div class="card pad"><div class="sec-title">🎯 Mis pronósticos <small><a href="#/mis-pronosticos" style="color:var(--brand-ink)">Ver todo</a></small></div>
      ${S.picks.length ? `<div class="kpis" style="grid-template-columns:1fr 1fr;margin:0"><div class="kpi"><div class="l">Guardados</div><div class="v">${S.picks.length}</div></div>
        <div class="kpi"><div class="l">Acierto</div><div class="v">${done.length ? pct(won / done.length) : "—"}</div></div></div>` :
        '<span class="muted" style="font-size:.85rem">Guarda un pronóstico desde la pestaña Resumen y aquí verás si aciertas.</span>'}</div>`;
}

// ================= vista LIGAS =================
async function viewLeagues() {
  const app = $("#app");
  if (!S.loaded) { app.innerHTML = '<div class="card pad"><div class="sk" style="height:300px"></div></div>'; return; }
  const comps = new Map();
  for (const m of S.matches) { const k = String(m.league_id ?? m.league); if (!comps.has(k)) comps.set(k, { m, n: 0, live: 0 }); const c = comps.get(k); c.n++; if (m.live) c.live++; }
  const order = [...comps.entries()].sort((a, b) => {
    const pa = S.pins.has(a[0]) ? 0 : 1, pb = S.pins.has(b[0]) ? 0 : 1;
    if (pa !== pb) return pa - pb;
    const ia = LEAGUE_PRIORITY.indexOf(a[1].m.league_id), ib = LEAGUE_PRIORITY.indexOf(b[1].m.league_id);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a[1].m.league.localeCompare(b[1].m.league);
  });
  if (!order.length) { app.innerHTML = `<div class="card">${emptyHtml("🏆", "No hay competiciones este día", "Cambia la fecha en Resultados.")}</div>`; return; }
  if (!S.league || !comps.has(S.league)) S.league = order[0][0];
  const sel = comps.get(S.league).m;
  app.innerHTML = `<div class="crumb">Competiciones con partidos · ${dayName(S.date)} ${dayShort(S.date)}</div>
    <div class="lgrid" style="margin-bottom:16px">${order.map(([k, c]) => `<button class="litem${k === S.league ? " on" : ""}" data-act="league" data-id="${esc(k)}">
      <img src="${img(c.m.league_logo, c.m.league)}" alt=""><div><div class="nm">${esc(c.m.league)}</div><div class="ct">${esc(countryName(c.m))}</div></div>
      <span class="n">${c.live ? `<span style="color:var(--red)">${c.live} en vivo</span> · ` : ""}${c.n}</span></button>`).join("")}</div>
    <div class="card" id="lgcard">
      <div class="lpage"><img class="lg" src="${img(sel.league_logo, sel.league)}" alt=""><div>
        <div class="nm">${esc(sel.league)}${sel.source === "demo" ? '<span class="demo-tag">DEMO</span>' : ""}</div>
        <div class="ct">${sel.flag ? `<img src="${img(sel.flag, sel.country)}" alt="">` : "🌐"}${esc(countryName(sel))}${sel.season ? ` · Temporada ${sel.season}/${sel.season + 1}` : ""}</div></div>
        <button class="btn" style="margin-left:auto" data-act="pin" data-id="${esc(String(sel.league_id ?? sel.league))}">${S.pins.has(String(sel.league_id)) ? "📌 Fijada" : "📌 Fijar arriba"}</button></div>
      <div class="lgcols">
        <div><div class="sec-title">Clasificación</div><div id="lgTable"><div class="sk" style="height:300px"></div></div></div>
        <div><div class="sec-title">Partidos · ${dayName(S.date)}</div><div style="border:1px solid var(--line);border-radius:14px;overflow:hidden">${S.matches.filter((m) => String(m.league_id ?? m.league) === S.league).map(matchRow).join("")}</div></div>
      </div></div>`;
  if (window.innerWidth < 900 && location.hash.split("/").length > 2) setTimeout(() => $("#lgcard")?.scrollIntoView({ behavior: "smooth" }), 50);
  const st = await loadStandings(sel.league_id, sel.season, sel.source === "demo");
  const t = $("#lgTable");
  if (t) t.innerHTML = st.groups && st.groups.length ? standingsTable(st.groups) : emptyHtml("📋", "Sin tabla de posiciones", "Esta competición no tiene tabla disponible.");
}

// ================= vista PROBAR MODELO =================
async function viewTest() {
  const app = $("#app"), b = S.bt;
  if (!b.leagues) {
    app.innerHTML = '<div class="card pad"><div class="sk" style="height:200px"></div></div>';
    try { const j = await getJSON("/api/backtest/leagues"); b.leagues = j.leagues; } catch { b.leagues = []; }
    if (S.view !== "test") return;
  }
  const lg = b.leagues.find((l) => l.code === b.league) || b.leagues[0];
  if (lg && (!b.season || !lg.seasons.includes(b.season))) b.season = lg.seasons[1] || lg.seasons[0];
  app.innerHTML = `
    <div class="card" style="margin-bottom:14px">
      <div class="bt-hero"><h2>🧪 Probar el modelo con partidos reales</h2>
        <p>ZOLA recorre la temporada partido por partido: antes de cada uno solo usa los resultados anteriores, predice, y luego compara con lo que pasó y con las <b>cuotas de cierre</b> de las casas. Datos gratis de football-data.co.uk.</p></div>
      <div class="bt-form">
        <div class="field"><label>Liga</label><select id="btLeague">${b.leagues.map((l) => `<option value="${l.code}" ${l.code === b.league ? "selected" : ""}>${esc(l.name)}</option>`).join("")}</select></div>
        <div class="field"><label>Temporada</label><select id="btSeason">${(lg ? lg.seasons : []).map((s, i) => `<option value="${s}" ${s === b.season ? "selected" : ""}>${fmtSeason(s)}${i === 0 ? " (en curso)" : ""}</option>`).join("")}</select></div>
        <div class="field"><label>Peso del mercado</label><div class="rng"><input type="range" id="btW" min="0" max="80" step="5" value="${b.weight}"><span id="btWv">${b.weight}%</span></div></div>
        <div class="field"><label>Ventaja mínima para apostar</label><div class="rng"><input type="range" id="btT" min="0" max="15" step="1" value="${b.thr}"><span id="btTv">${b.thr}%</span></div></div>
        <button class="btn primary" data-act="runbt" ${b.loading ? "disabled" : ""}>${b.loading ? "Probando…" : "▶ Probar"}</button>
      </div></div>
    <div id="btOut">${b.loading ? '<div class="card pad"><div class="sk" style="height:260px"></div></div>' : b.err ? `<div class="card">${emptyHtml("⚠️", "No se pudo hacer la prueba", esc(b.err))}</div>` : b.res ? btResults(b.res) : `<div class="card">${emptyHtml("📈", "Elige una liga y temporada", "La prueba tarda unos segundos.")}</div>`}</div>`;
  $("#btLeague").onchange = (e) => { b.league = e.target.value; b.season = null; viewTest(); };
  $("#btSeason").onchange = (e) => { b.season = e.target.value; };
  $("#btW").oninput = (e) => { b.weight = +e.target.value; $("#btWv").textContent = b.weight + "%"; };
  $("#btT").oninput = (e) => { b.thr = +e.target.value; $("#btTv").textContent = b.thr + "%"; };
}
async function runBacktest() {
  const b = S.bt;
  b.loading = true; b.err = null; viewTest();
  try { b.res = await getJSON(`/api/backtest?league=${b.league}&season=${b.season}&weight=${b.weight / 100}&threshold=${b.thr / 100}`); }
  catch (e) { b.err = e.message; b.res = null; }
  b.loading = false;
  if (S.view === "test") viewTest();
}
function lineChart(series, { w = 600, h = 160, colors = ["#2f55f5", "#14a44d"], labels = [] } = {}) {
  const all = series.flat(); if (!all.length) return "";
  const mn = Math.min(0, ...all), mx = Math.max(0.5, ...all);
  const y = (v) => h - 12 - ((v - mn) / (mx - mn || 1)) * (h - 24);
  const paths = series.map((s, k) => `<path d="${s.map((v, i) => `${i ? "L" : "M"}${(i / Math.max(s.length - 1, 1)) * w},${y(v).toFixed(1)}`).join(" ")}" fill="none" stroke="${colors[k]}" stroke-width="2.5" vector-effect="non-scaling-stroke"/>`).join("");
  const leg = labels.map((l, k) => `<span style="display:inline-flex;align-items:center;gap:6px;margin-right:14px"><i style="width:12px;height:3px;background:${colors[k]};display:inline-block;border-radius:2px"></i>${esc(l)}</span>`).join("");
  return `<svg class="chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" style="height:${h}px"><line x1="0" x2="${w}" y1="${y(0)}" y2="${y(0)}" stroke="var(--line2)" stroke-dasharray="4"/>${paths}</svg>
    <div class="muted" style="font-size:.76rem;margin-top:6px">${leg}</div>`;
}
function calibChart(cal) {
  const W = 300, H = 300, P = 30;
  const x = (v) => P + v * (W - P - 10), y = (v) => H - P - v * (H - P - 10);
  const pts = cal.map((c) => `<circle cx="${x(c.pred)}" cy="${y(c.obs)}" r="${Math.max(3, Math.min(10, Math.sqrt(c.n)))}" fill="rgba(47,85,245,.75)"><title>${c.bin}: predijo ${pct(c.pred)} · pasó ${pct(c.obs)} (${c.n})</title></circle>`).join("");
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => `<text x="${x(t)}" y="${H - 10}" font-size="10" text-anchor="middle" fill="var(--muted)">${t * 100}%</text><text x="${P - 6}" y="${y(t) + 3}" font-size="10" text-anchor="end" fill="var(--muted)">${t * 100}%</text>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" class="chart" style="max-width:360px;margin:0 auto">
    <rect x="${P}" y="10" width="${W - P - 10}" height="${H - P - 10}" fill="none" stroke="var(--line2)"/>
    <line x1="${x(0)}" y1="${y(0)}" x2="${x(1)}" y2="${y(1)}" stroke="var(--green)" stroke-dasharray="5"/>${ticks}${pts}</svg>`;
}
function btResults(r) {
  const s = r.systems, rows = [["model", "Modelo ZOLA"], ["blend", "ZOLA + mercado"], ["market", "Casa (cierre)"], ["base", "Base (frecuencias)"]].filter(([k]) => s[k]);
  const best = (key, low) => { const v = rows.map(([k]) => s[k][key]); return low ? Math.min(...v) : Math.max(...v); };
  const bAcc = best("accuracy"), bLL = best("logloss", true), bBr = best("brier", true);
  const m = s.model, mk = s.market, bl = s.blend;
  let verdict;
  if (mk && bl && bl.logloss <= mk.logloss) verdict = `<b>Muy bien:</b> combinado con el mercado, ZOLA predijo mejor que las cuotas de cierre (log-loss ${bl.logloss.toFixed(3)} vs ${mk.logloss.toFixed(3)}).`;
  else if (mk && m.logloss < s.base.logloss) verdict = `ZOLA predice mejor que adivinar con frecuencias (${m.logloss.toFixed(3)} vs ${s.base.logloss.toFixed(3)}), pero <b>las casas siguen siendo más precisas</b> (${mk.logloss.toFixed(3)}). Es normal: las cuotas de cierre son muy eficientes. Usa ZOLA + mercado y apuesta solo con ventaja clara.`;
  else verdict = `En esta temporada el modelo no superó a la referencia. Prueba otra liga, temporada o sube el peso del mercado.`;
  const bet = r.betting.blend, betM = r.betting.model;
  return `
    <div class="verdict"><span class="ic">🧠</span><div>${verdict}<div class="muted" style="font-size:.8rem;margin-top:4px">${esc(r.league_name)} ${esc(fmtSeason(r.season))} · ${r.evaluated} partidos evaluados (los primeros ${r.warmup} solo sirvieron para aprender) · cuotas: ${esc(r.odds_source || "—")}</div></div></div>
    <div class="bt-grid">
      <div class="kpi"><div class="l">Acierto 1X2 · ZOLA</div><div class="v">${pct(m.accuracy, 1)}</div><div class="d">Casa: ${mk ? pct(mk.accuracy, 1) : "—"} · Base: ${pct(s.base.accuracy, 1)}</div></div>
      <div class="kpi"><div class="l">Log-loss (menor = mejor)</div><div class="v">${(bl || m).logloss.toFixed(3)}</div><div class="d">Modelo ${m.logloss.toFixed(3)} · Casa ${mk ? mk.logloss.toFixed(3) : "—"}</div></div>
      <div class="kpi"><div class="l">Apuestas de valor</div><div class="v" style="color:${(bet.units || 0) >= 0 ? "var(--green)" : "var(--red)"}">${bet.bets ? (bet.units >= 0 ? "+" : "") + bet.units.toFixed(2) + " u" : "—"}</div><div class="d">${bet.bets} apuestas · ROI ${bet.roi != null ? pct(bet.roi, 1) : "—"} · acierto ${bet.hit_rate != null ? pct(bet.hit_rate) : "—"}</div></div>
      <div class="kpi"><div class="l">Más de 2.5 goles</div><div class="v">${r.over25.accuracy != null ? pct(r.over25.accuracy, 1) : "—"}</div><div class="d">Log-loss ${r.over25.logloss ? r.over25.logloss.toFixed(3) : "—"}${r.over25.market_logloss ? ` · casa ${r.over25.market_logloss.toFixed(3)}` : ""}</div></div>
    </div>
    <div class="card" style="margin-bottom:14px"><div class="pad" style="padding-bottom:0"><div class="sec-title">Comparación de sistemas</div></div>
      <div class="vs" style="padding:0 16px 10px"><div class="h">Sistema</div><div class="h">Acierto</div><div class="h">Log-loss</div><div class="h">Brier</div><div class="h">Partidos</div>
      ${rows.map(([k, l]) => `<div style="font-weight:700">${l}</div><div class="${s[k].accuracy === bAcc ? "best" : ""}">${pct(s[k].accuracy, 1)}</div><div class="${s[k].logloss === bLL ? "best" : ""}">${s[k].logloss.toFixed(3)}</div><div class="${s[k].brier === bBr ? "best" : ""}">${s[k].brier.toFixed(3)}</div><div>${s[k].n}</div>`).join("")}</div>
      <div class="muted" style="font-size:.76rem;padding:0 16px 14px">Log-loss y Brier miden qué tan buenas son las probabilidades (no solo si acierta al favorito). En verde, el mejor de cada columna.</div></div>
    <div class="two">
      <div class="card pad"><div class="sec-title">Ganancia acumulada (1 unidad por apuesta)</div>
        ${lineChart([betM.series, bet.series], { labels: [`Solo modelo (${betM.bets} ap., ${betM.units >= 0 ? "+" : ""}${betM.units} u)`, `ZOLA + mercado (${bet.bets} ap., ${bet.units >= 0 ? "+" : ""}${bet.units} u)`] })}
        <div class="muted" style="font-size:.76rem;margin-top:8px">Apuesta cuando la ventaja es ≥ ${pct(r.params.value_threshold)} a la cuota de cierre. Rentabilidad pasada no garantiza la futura.</div></div>
      <div class="card pad"><div class="sec-title">Calibración <small>¿lo que dice el % pasa?</small></div>${calibChart(r.calibration)}
        <div class="muted" style="font-size:.76rem;text-align:center">Puntos cerca de la línea verde = probabilidades bien calibradas.</div></div>
    </div>
    <div class="card"><div class="pad" style="padding-bottom:6px"><div class="sec-title">Últimos partidos evaluados</div></div>
      <div class="tblwrap" style="padding:0 16px 16px"><table class="tbl"><thead><tr><th class="l">Fecha</th><th class="l">Partido</th><th>Res.</th><th>ZOLA 1·X·2</th><th>Casa 1·X·2</th><th>Apuesta</th></tr></thead><tbody>
      ${r.sample.map((x) => `<tr><td class="l muted">${x.date.slice(5)}</td><td class="l">${esc(x.home)} - ${esc(x.away)}</td><td><b>${x.score}</b></td>
        <td>${x.model.map((v, i) => `<span style="font-weight:${"1X2"[i] === x.result ? 800 : 400};color:${"1X2"[i] === x.result ? "var(--green)" : "inherit"}">${pct(v)}</span>`).join(" · ")}</td>
        <td class="muted">${x.market.length ? x.market.map((v) => pct(v)).join(" · ") : "—"}</td>
        <td>${x.pick ? `${x.pick.won ? "✅" : "❌"} ${x.pick.outcome} @${x.pick.odd.toFixed(2)}` : '<span class="faint">—</span>'}</td></tr>`).join("")}
      </tbody></table></div></div>`;
}

// ================= vista MIS PRONÓSTICOS =================
function savePicks() { ls.set("zola_picks", S.picks); updatePicksBadge(); }
function updatePicksBadge() { const pend = S.picks.filter((x) => !x.result).length, b = $("#picksBadge"); b.hidden = !pend; b.textContent = pend; }
async function settlePicks() {
  const pend = S.picks.filter((x) => !x.result);
  if (!pend.length) return;
  let changed = false;
  for (const x of pend) { const m = byKey(x.key); if (m && m.finished) { settleOne(x, m); changed = true; } }
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
  const done = S.picks.filter((x) => x.result === "won" || x.result === "lost"), won = done.filter((x) => x.result === "won").length;
  const withOdd = done.filter((x) => x.odd).sort((a, b) => a.savedAt - b.savedAt);
  let acc = 0;
  const series = [0, ...withOdd.map((x) => (acc += x.result === "won" ? x.odd - 1 : -1))];
  $("#app").innerHTML = `
    <div class="crumb">Se guardan en este navegador y se cierran solos cuando termina el partido</div>
    <div class="pstats">
      <div class="kpi"><div class="l">Guardados</div><div class="v">${S.picks.length}</div></div>
      <div class="kpi"><div class="l">Resueltos</div><div class="v">${done.length}</div></div>
      <div class="kpi"><div class="l">Acierto</div><div class="v">${done.length ? pct(won / done.length) : "—"}</div><div class="t"><div style="width:${done.length ? won / done.length * 100 : 0}%"></div></div></div>
      <div class="kpi"><div class="l">Unidades</div><div class="v" style="color:${acc >= 0 ? "var(--green)" : "var(--red)"}">${withOdd.length ? (acc >= 0 ? "+" : "") + acc.toFixed(2) : "—"}</div></div>
    </div>
    ${withOdd.length > 1 ? `<div class="card pad" style="margin-bottom:14px"><div class="sec-title">Evolución (1 unidad por apuesta)</div>${lineChart([series], { h: 110, colors: [acc >= 0 ? "#14a44d" : "#e5383b"] })}</div>` : ""}
    <div class="card">${S.picks.length ? `<div class="prow muted" style="font-size:.72rem;font-weight:800;border-top:0"><span></span><span>PARTIDO</span><span>JUGADA</span><span class="hide-m">CUOTA</span><span class="hide-m">FINAL</span><span></span></div>` +
      [...S.picks].reverse().map((x) => `<div class="prow">
        <span class="st">${x.result === "won" ? "✅" : x.result === "lost" ? "❌" : x.result === "void" ? "➖" : "⏳"}</span>
        <div class="tms" data-act="gopick" data-key="${esc(x.key)}" data-date="${esc(x.date)}" style="cursor:pointer">
          <span><img src="${img(x.home_logo, x.home)}" alt="">${esc(x.home)}</span><span><img src="${img(x.away_logo, x.away)}" alt="">${esc(x.away)}</span>
          <small class="muted">${esc(x.league)} · ${new Date(x.savedAt).toLocaleDateString("es-PE", { day: "2-digit", month: "short" })}${x.scoreAt && x.scoreAt !== "0-0" ? ` · guardado con ${esc(x.scoreAt)}` : ""}</small></div>
        <span><b>${esc(MK_LABEL[x.market] || x.market)}</b><br><small class="muted">${pct(x.prob)} · pron. ${esc(x.predicted)}</small></span>
        <span class="hide-m">${x.odd ? x.odd.toFixed(2) : "—"}</span><span class="hide-m"><b>${x.final || "—"}</b></span>
        <button class="del" data-act="delpick" data-key="${esc(x.key)}" title="Borrar">✕</button></div>`).join("")
      : emptyHtml("🎯", "Aún no guardas pronósticos", "Abre un partido y toca «Guardar en Mis pronósticos».")}</div>`;
}

// ================= buscador =================
function renderSuggest() {
  const box = $("#suggest"), q = norm(S.q);
  if (!q || q.length < 2) { box.hidden = true; return; }
  const teams = new Map(), leagues = new Map();
  for (const m of S.matches) {
    for (const [n, l] of [[m.home, m.home_logo], [m.away, m.away_logo]]) if (norm(n).includes(q) && !teams.has(n)) teams.set(n, { l, m });
    if (norm(m.league).includes(q) && !leagues.has(m.league)) leagues.set(m.league, m);
  }
  const t = [...teams.entries()].slice(0, 6), lg = [...leagues.entries()].slice(0, 4);
  box.innerHTML = (!t.length && !lg.length) ? `<div class="sg muted">Sin resultados para «${esc(S.q)}» este día</div>` :
    (t.length ? '<div class="sgh">Equipos</div>' + t.map(([n, { l, m }]) => `<div class="sg" data-act="open" data-key="${esc(m.match_key)}"><img src="${img(l, n)}" alt="">${esc(n)}<small>${esc(m.home)} vs ${esc(m.away)}</small></div>`).join("") : "") +
    (lg.length ? '<div class="sgh">Ligas</div>' + lg.map(([n, m]) => `<div class="sg" data-act="league" data-id="${esc(String(m.league_id ?? m.league))}"><img src="${img(m.league_logo, n)}" alt="">${esc(n)}<small>${esc(countryName(m))}</small></div>`).join("") : "");
  box.hidden = false;
}

// ================= router y acciones =================
function setNav() { $$("[data-nav]").forEach((a) => a.classList.toggle("on", a.dataset.nav === S.view)); }
function renderView() {
  setNav();
  if (S.view === "leagues") viewLeagues();
  else if (S.view === "picks") viewPicks();
  else if (S.view === "test") viewTest();
  else viewMatches();
}
function route() {
  const parts = decodeURIComponent(location.hash.slice(1) || "/").split("/").filter(Boolean);
  if (parts[0] === "ligas") { S.view = "leagues"; if (parts[1]) S.league = parts[1]; }
  else if (parts[0] === "mis-pronosticos") S.view = "picks";
  else if (parts[0] === "probar") S.view = "test";
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
function setDate(d) { S.date = d; S.sel = null; S.detail = null; S.detailFor = null; S.quick = {}; lastScores = {}; loadMatches(); }
function openMatch(key) {
  $("#suggest").hidden = true;
  const h = `#/partido/${encodeURIComponent(key)}`;
  if (location.hash !== h) location.hash = h; else route();
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
    renderList(); if (S.sel === k) renderDetail();
    if (S.view === "leagues") viewLeagues();
  } else if (a === "pin") {
    e.stopPropagation();
    const id = String(t.dataset.id);
    S.pins.has(id) ? S.pins.delete(id) : S.pins.add(id);
    ls.set("zola_pins", [...S.pins]);
    toast(S.pins.has(id) ? "📌 Liga fijada arriba" : "Liga desfijada", "", 1800);
    S.view === "leagues" ? viewLeagues() : renderList();
  } else if (a === "collapse") {
    e.stopPropagation();
    const id = String(t.dataset.id); S.collapsed.has(id) ? S.collapsed.delete(id) : S.collapsed.add(id); renderList();
  } else if (a === "ltab") { S.ltab = t.dataset.t; renderList(); }
  else if (a === "status") { S.status = S.status === t.dataset.s ? null : t.dataset.s; renderList(); }
  else if (a === "probs") { e.preventDefault(); S.showProbs = !S.showProbs; ls.set("zola_probs", S.showProbs); renderList(); }
  else if (a === "region") { S.region = t.dataset.r; renderList(); }
  else if (a === "day") setDate(addDays(S.date, +t.dataset.n));
  else if (a === "tab") { S.tab = t.dataset.t; $$(".tab").forEach((b) => b.classList.toggle("on", b.dataset.t === S.tab)); renderTab(); }
  else if (a === "league") { e.stopPropagation(); $("#suggest").hidden = true; location.hash = `#/ligas/${t.dataset.id}`; }
  else if (a === "back") { history.length > 1 ? history.back() : (location.hash = "#/"); }
  else if (a === "share") { navigator.clipboard?.writeText(location.href).then(() => toast("🔗 Enlace copiado", "", 1800), () => {}); }
  else if (a === "vote") {
    S.votes[S.sel] = t.dataset.v; ls.set("zola_votes", S.votes); renderDetail();
  } else if (a === "unvote") { e.preventDefault(); delete S.votes[S.sel]; ls.set("zola_votes", S.votes); renderDetail(); }
  else if (a === "savepick") {
    const d = S.detail; if (!d) return;
    const m = { ...d.match, ...(byKey(S.sel) || {}) }, p = d.prediction, bb = p.best_bet;
    const market = bb ? bb.market : (p.winner === "Empate" ? "X" : p.winner === m.home ? "1" : "2");
    S.picks.push({ key: m.match_key, date: S.date, league: m.league, home: m.home, away: m.away, home_logo: m.home_logo, away_logo: m.away_logo,
      market, prob: p.markets[market], odd: bb && bb.odd ? bb.odd : (d.odds[market] || null), predicted: p.best_score,
      scoreAt: `${m.home_goals || 0}-${m.away_goals || 0}`, savedAt: Date.now(), result: null, final: null });
    savePicks(); toast(`💾 Guardado: ${esc(MK_LABEL[market] || market)}`); renderTab(); renderRail();
  } else if (a === "delpick") { S.picks = S.picks.filter((x) => x.key !== t.dataset.key); savePicks(); viewPicks(); }
  else if (a === "gopick") { if (t.dataset.date && t.dataset.date !== S.date) { S.date = t.dataset.date; S.loaded = false; loadMatches(); } location.hash = `#/partido/${encodeURIComponent(t.dataset.key)}`; }
  else if (a === "simmk") { S.sim.mk = t.dataset.mk; S.sim.odd = null; renderTab(); }
  else if (a === "runbt") runBacktest();
  else if (a === "favs-shortcut") { e.preventDefault(); S.ltab = "favs"; location.hash = "#/"; if (S.view === "matches") renderList(); }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "/" && !["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)) { e.preventDefault(); $("#q").focus(); }
  if (e.key === "Escape") { $("#suggest").hidden = true; $("#q").blur(); }
  if (e.key === "Enter" && e.target.classList?.contains("mrow")) openMatch(e.target.dataset.key);
});
$("#q").addEventListener("input", (e) => { S.q = e.target.value; renderSuggest(); if (S.view === "matches") renderList(); });
$("#themeBtn").addEventListener("click", () => {
  const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = t; ls.set("zola_theme", t);
  $("#themeBtn").textContent = t === "dark" ? "☀️" : "🌙";
});
window.addEventListener("hashchange", route);

// ================= relojes =================
function tickCountdowns() {
  $$("[data-countdown]").forEach((el) => {
    const ms = +el.dataset.countdown - Date.now();
    if (ms <= 0) { el.textContent = "Por empezar"; return; }
    const h = Math.floor(ms / 3.6e6), m = Math.floor(ms % 3.6e6 / 6e4), s = Math.floor(ms % 6e4 / 1000);
    el.textContent = h > 47 ? `en ${Math.floor(h / 24)} días` : `${pad(h)}:${pad(m)}:${pad(s)}`;
  });
}
setInterval(tickCountdowns, 1000);
setInterval(() => { if (!document.hidden && (S.date === todayISO() || S.matches.some((m) => m.live))) loadMatches({ quiet: true }); }, 60000);
setInterval(() => { if (document.hidden || S.view !== "matches") return; const m = byKey(S.sel); if (m && m.live) loadDetail(S.sel, { quiet: true }); }, 45000);

// ================= inicio =================
(function init() {
  $("#themeBtn").textContent = document.documentElement.dataset.theme === "dark" ? "☀️" : "🌙";
  updatePicksBadge();
  route();
  loadMatches();
})();
