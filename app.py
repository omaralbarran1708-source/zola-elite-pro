"""ZOLA Elite — interfaz Streamlit."""
from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from zola.api import FootballApi
from zola.data import filter_matches, list_matches, match_detail, settle_history
from zola.db import History
from zola.logos import logo, prefetch
from zola.model import kelly_fraction, predict
from zola.status import STATUS_LABEL, TOP_LEAGUE_IDS, is_finished, is_live

APP_DIR = Path(__file__).resolve().parent
CFG_PATH = APP_DIR / ".zola_cfg.json"
DB_PATH = Path(os.getenv("ZOLA_DB_PATH", APP_DIR / "zola_history.db"))
LOGO_PATH = APP_DIR / "zola_logo.png"
LIMA = ZoneInfo("America/Lima")

# orden de prioridad de ligas en la lista
LEAGUE_PRIORITY = [1, 2, 13, 281, 39, 140, 135, 78, 61, 11, 3, 848, 71, 128, 9, 4]

st.set_page_config(page_title="ZOLA Elite", page_icon="⚽", layout="wide", initial_sidebar_state="collapsed")


# ---------------- configuración ----------------
def load_cfg() -> dict:
    cfg = {"api_football_key": ""}
    if CFG_PATH.exists():
        try:
            cfg.update(json.loads(CFG_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


def save_cfg(cfg: dict) -> None:
    CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def secret_key() -> str:
    try:
        v = st.secrets.get("API_FOOTBALL_KEY", "")
    except Exception:
        v = ""
    return v or os.getenv("API_FOOTBALL_KEY", "")


@st.cache_resource
def get_history() -> History:
    return History(DB_PATH)


@st.cache_resource
def get_api(key: str) -> FootballApi:
    return FootballApi(key)


@st.cache_data
def brand_logo() -> str:
    if LOGO_PATH.exists():
        return "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode()
    return ""


ss = st.session_state
if "cfg" not in ss:
    ss.cfg = load_cfg()
ss.setdefault("selected_key", None)

api_key = secret_key() or ss.cfg.get("api_football_key", "")
api = get_api(api_key)
history = get_history()

# ---------------- estilos ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root{
  --bg:#070d1a; --panel:#0d1628; --panel2:#111d33; --line:#1b2b48; --text:#eaf1ff; --muted:#8ea3c4;
  --blue:#3b82f6; --green:#22c55e; --orange:#f97316; --red:#ef4444; --gold:#f5b301;
}
html, body, .stApp, [class*="css"], button, input, textarea {font-family:'Inter',system-ui,sans-serif !important;}
.stApp{background:radial-gradient(1200px 600px at 10% -10%, #10254a 0%, transparent 60%), radial-gradient(900px 500px at 110% 0%, #13213d 0%, transparent 55%), var(--bg);}
[data-testid="stHeader"]{background:transparent;height:0;}
[data-testid="stToolbar"]{display:none;}
.block-container{max-width:1440px;padding-top:1.1rem;padding-bottom:2rem;}
.muted{color:var(--muted);}
.topbar{display:flex;align-items:center;gap:14px;}
.topbar img{width:46px;height:46px;object-fit:contain;border-radius:12px;}
.brand-title{font-size:1.55rem;font-weight:900;letter-spacing:-.02em;line-height:1;}
.brand-title span{background:linear-gradient(90deg,#60a5fa,#22c55e);-webkit-background-clip:text;color:transparent;}
.brand-sub{color:var(--muted);font-size:.8rem;margin-top:4px;}
.chips{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;align-items:center;height:100%;}
.chip{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:.32rem .7rem;border:1px solid var(--line);background:rgba(17,29,51,.7);font-weight:600;font-size:.78rem;color:var(--text);}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;}
.lhead{display:flex;align-items:center;gap:8px;margin:.9rem 0 .35rem;font-weight:800;font-size:.82rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;}
.lhead img{width:20px;height:20px;object-fit:contain;}
.lhead .n{margin-left:auto;font-weight:600;text-transform:none;letter-spacing:0;}
.mrow{display:grid;grid-template-columns:54px 1fr auto;gap:10px;align-items:center;background:var(--panel);border:1px solid var(--line);
  border-radius:14px;padding:.6rem .75rem;transition:all .15s ease;}
[class*="st-key-card_"]:hover .mrow{border-color:#2d4b7c;background:#0f1b31;transform:translateY(-1px);}
[class*="st-key-card_"] .stElementContainer:not(:has(.stButton)){pointer-events:none;}
.mrow.sel{border-color:var(--blue);background:linear-gradient(90deg,rgba(59,130,246,.16),rgba(13,22,40,1) 70%);}
.mtime{font-size:.78rem;font-weight:700;color:var(--muted);text-align:center;line-height:1.2;}
.mtime.live{color:var(--red);}
.mteams{display:flex;flex-direction:column;gap:5px;min-width:0;}
.tline{display:flex;align-items:center;gap:8px;min-width:0;}
.tline img{width:20px;height:20px;object-fit:contain;flex:none;}
.tline .nm{font-weight:600;font-size:.9rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tline.win .nm{font-weight:800;}
.mscore{display:flex;flex-direction:column;gap:5px;font-weight:900;font-size:.92rem;text-align:right;min-width:18px;}
.mscore.live{color:var(--red);}
.badge{display:inline-block;border-radius:6px;padding:.05rem .4rem;font-size:.62rem;font-weight:800;}
.b-demo{background:rgba(245,179,1,.15);color:var(--gold);}
.pulse{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--red);margin-right:4px;animation:pl 1.4s infinite;}
@keyframes pl{0%{box-shadow:0 0 0 0 rgba(239,68,68,.7)}70%{box-shadow:0 0 0 7px rgba(239,68,68,0)}100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}}
[class*="st-key-card_"]{position:relative;gap:0 !important;margin-bottom:.4rem;}
[class*="st-key-card_"] .stElementContainer:has(.stButton){position:absolute;inset:0;z-index:5;margin:0;width:100% !important;height:100% !important;}
[class*="st-key-card_"] .stButton, [class*="st-key-card_"] .stButton button{width:100%;height:100%;opacity:0;cursor:pointer;}
.hero{position:relative;overflow:hidden;background:linear-gradient(135deg,#0f2246 0%,#0d1628 55%,#0e2a22 120%);border:1px solid var(--line);border-radius:22px;padding:1.2rem 1.3rem 1rem;}
.hero-top{display:flex;justify-content:center;align-items:center;gap:8px;color:var(--muted);font-size:.82rem;font-weight:600;}
.hero-top img{width:20px;height:20px;object-fit:contain;}
.hero-grid{display:grid;grid-template-columns:1fr auto 1fr;gap:12px;align-items:center;margin-top:.8rem;}
.hteam{display:flex;flex-direction:column;align-items:center;text-align:center;gap:8px;}
.hteam img{width:78px;height:78px;object-fit:contain;filter:drop-shadow(0 8px 18px rgba(0,0,0,.45));}
.hteam .nm{font-weight:800;font-size:1.1rem;line-height:1.2;}
.form{display:flex;gap:4px;justify-content:center;}
.form span{width:18px;height:18px;border-radius:5px;font-size:.62rem;font-weight:800;display:flex;align-items:center;justify-content:center;color:#fff;}
.fW{background:var(--green);} .fD{background:#64748b;} .fL{background:var(--red);}
.hcenter{text-align:center;min-width:170px;}
.big{font-size:3.1rem;font-weight:900;letter-spacing:-.03em;line-height:1;}
.big.vs{font-size:2rem;color:var(--muted);}
.hstatus{margin-top:.45rem;font-size:.82rem;font-weight:700;}
.hstatus.live{color:var(--red);}
.prog{height:4px;border-radius:9px;background:rgba(148,163,184,.18);margin:.55rem auto 0;width:150px;overflow:hidden;}
.prog div{height:100%;background:var(--red);}
.verdict{display:inline-block;margin-top:.6rem;border-radius:999px;padding:.32rem .85rem;background:rgba(34,197,94,.13);color:#4ade80;border:1px solid rgba(34,197,94,.35);font-weight:800;font-size:.85rem;}
.venue{color:var(--muted);font-size:.75rem;text-align:center;margin-top:.8rem;}
.p3{margin-top:1rem;}
.p3-lbl{display:flex;justify-content:space-between;font-size:.78rem;color:var(--muted);font-weight:600;margin-bottom:.35rem;}
.p3-lbl b{color:var(--text);font-size:1rem;}
.p3-bar{display:flex;height:12px;border-radius:999px;overflow:hidden;gap:3px;}
.p3-bar div{height:100%;}
.c1{background:var(--blue);} .cX{background:#64748b;} .c2{background:var(--orange);}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:1rem;}
.ai{background:linear-gradient(135deg,rgba(59,130,246,.13),rgba(34,197,94,.07));border:1px solid var(--line);border-radius:16px;padding:1rem 1.1rem;line-height:1.6;font-size:.93rem;}
.ai h4{margin:0 0 .4rem;font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:#60a5fa;}
.pick{display:flex;align-items:center;gap:12px;background:var(--panel2);border:1px solid var(--line);border-radius:14px;padding:.75rem .9rem;margin:.7rem 0;}
.pick .ic{font-size:1.4rem;}
.pick .t{font-size:.72rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.05em;}
.pick .v{font-size:1.05rem;font-weight:900;}
.pick .e{margin-left:auto;text-align:right;font-weight:800;}
.kpis{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;}
.kpis.k4{grid-template-columns:repeat(4,1fr);}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:.75rem .85rem;}
.kpi .l{font-size:.72rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.04em;}
.kpi .v{font-size:1.35rem;font-weight:900;margin-top:.15rem;}
.kpi .t{height:5px;border-radius:9px;background:rgba(148,163,184,.18);margin-top:.45rem;overflow:hidden;}
.kpi .t div{height:100%;background:linear-gradient(90deg,var(--blue),var(--green));}
.sc-row{display:grid;grid-template-columns:44px 1fr 48px;gap:10px;align-items:center;font-size:.86rem;margin-bottom:.4rem;}
.sc-row b{font-weight:800;}
.sc-row .t{height:8px;border-radius:9px;background:rgba(148,163,184,.15);overflow:hidden;}
.sc-row .t div{height:100%;background:var(--blue);border-radius:9px;}
.sc-row.top .t div{background:var(--green);}
.sec{font-weight:800;font-size:.95rem;margin:.2rem 0 .6rem;}
.bar{margin-bottom:.75rem;}
.bar-top{display:flex;justify-content:space-between;font-size:.84rem;margin-bottom:.25rem;}
.bar-top span{color:var(--muted);font-weight:600;}
.track{display:flex;gap:3px;width:100%;height:8px;}
.track div{height:100%;border-radius:9px;}
.fh{background:var(--blue);} .fa{background:var(--orange);}
.ev{display:grid;grid-template-columns:46px 26px 1fr;gap:6px;align-items:center;padding:.5rem .2rem;border-bottom:1px solid var(--line);font-size:.88rem;}
.ev:last-child{border-bottom:none;}
.ev-min{font-weight:800;color:var(--muted);}
.ev .who{font-weight:700;}
.ev.away{direction:rtl;} .ev.away > *{direction:ltr;text-align:right;}
.stButton>button{border-radius:12px !important;font-weight:700 !important;}
div[data-baseweb="tab-list"]{gap:4px;}
button[data-baseweb="tab"]{font-weight:700 !important;}
[data-testid="stPopover"] button{border-radius:999px !important;}
.empty{text-align:center;padding:2.5rem 1rem;color:var(--muted);border:1px dashed var(--line);border-radius:16px;}
.empty .i{font-size:2rem;}
.foot{color:var(--muted);font-size:.75rem;margin-top:1.4rem;text-align:center;}
@media (max-width:900px){
  .hteam img{width:56px;height:56px;} .big{font-size:2.3rem;} .hcenter{min-width:110px;}
  .kpis.k4{grid-template-columns:repeat(2,1fr);}
}</style>
""", unsafe_allow_html=True)


# ---------------- helpers ----------------
def L(url, name):
    """src del logo (descargado y cacheado en el servidor, o escudo generado)."""
    return logo(url, name)


def kickoff_hhmm(m):
    try:
        return datetime.fromisoformat(m["kickoff"]).astimezone(LIMA).strftime("%H:%M")
    except Exception:
        return ""


def time_cell(m):
    s = m["status_short"]
    if s == "HT":
        return '<div class="mtime live">ET</div>'
    if is_live(s):
        extra = f"+{m['extra']}" if m.get("extra") else ""
        return f'<div class="mtime live"><span class="pulse"></span>{m["minute"]}{extra}\'</div>'
    if is_finished(s):
        return '<div class="mtime">Final</div>'
    return f'<div class="mtime">{kickoff_hhmm(m) or STATUS_LABEL.get(s, s)}</div>'


def match_row(m, selected):
    s = m["status_short"]
    started = is_live(s) or is_finished(s)
    hw = started and m["home_goals"] > m["away_goals"]
    aw = started and m["away_goals"] > m["home_goals"]
    score = (f'<div class="mscore{" live" if is_live(s) else ""}"><span>{m["home_goals"]}</span><span>{m["away_goals"]}</span></div>'
             if started else '<div class="mscore"></div>')
    return f"""<div class="mrow{' sel' if selected else ''}">{time_cell(m)}
      <div class="mteams">
        <div class="tline{' win' if hw else ''}"><img src="{L(m.get('home_logo'), m['home'])}"><span class="nm">{escape(m['home'])}</span></div>
        <div class="tline{' win' if aw else ''}"><img src="{L(m.get('away_logo'), m['away'])}"><span class="nm">{escape(m['away'])}</span></div>
      </div>{score}</div>"""


def group_by_league(matches):
    groups = {}
    for m in matches:
        groups.setdefault((m["league"], m.get("country", "")), []).append(m)

    def prio(item):
        (_, _), ms = item
        lid = ms[0].get("league_id")
        has_live = any(is_live(x["status_short"]) for x in ms)
        p = LEAGUE_PRIORITY.index(lid) if lid in LEAGUE_PRIORITY else (50 if lid in TOP_LEAGUE_IDS else 100)
        return (0 if has_live else 1, p, ms[0]["league"])
    return sorted(groups.items(), key=prio)


def form_html(form):
    f = (form or "")[-5:]
    if not f:
        return '<div class="form muted" style="font-size:.75rem">Sin forma</div>'
    return '<div class="form">' + "".join(f'<span class="f{c}">{ {"W": "G", "D": "E", "L": "P"}.get(c, c)}</span>' for c in f) + "</div>"


def stat_bar(label, h, a, pct=False):
    if h is None and a is None:
        return ""
    h, a = h or 0, a or 0
    tot = (h + a) or 1
    def fmt(v):
        if pct:
            return f"{v:.0f}%"
        return f"{v:.2f}" if isinstance(v, float) and not float(v).is_integer() else f"{v:.0f}"
    hw = max(h / tot * 100, 2) if h else 0
    aw = max(a / tot * 100, 2) if a else 0
    return f"""<div class="bar"><div class="bar-top"><b>{fmt(h)}</b><span>{label}</span><b>{fmt(a)}</b></div>
      <div class="track"><div class="fh" style="width:{hw:.1f}%"></div><div style="flex:1"></div><div class="fa" style="width:{aw:.1f}%"></div></div></div>"""


DETAIL_ES = {
    "Normal Goal": "Gol", "Own Goal": "Autogol", "Penalty": "Gol de penal", "Missed Penalty": "Penal fallado",
    "Yellow Card": "Amarilla", "Red Card": "Roja", "Second Yellow card": "Doble amarilla",
    "Goal cancelled": "Gol anulado (VAR)", "Penalty confirmed": "Penal confirmado (VAR)",
}


def event_html(e, m):
    icon = {"Goal": "⚽", "Card": "🟨", "subst": "🔁", "Var": "📺"}.get(e["type"], "•")
    if e["type"] == "Card" and ("Red" in e["detail"] or "Second Yellow" in e["detail"]):
        icon = "🟥"
    if e["type"] == "Goal" and e["detail"] == "Missed Penalty":
        icon = "❌"
    extra = f"+{e['extra']}" if e.get("extra") else ""
    detail = "Cambio" if e["type"] == "subst" else DETAIL_ES.get(e["detail"], e["detail"])
    sub = escape(detail)
    if e["type"] == "Goal" and e.get("assist"):
        sub += f" · asist. {escape(e['assist'])}"
    if e["type"] == "subst" and e.get("assist"):
        sub = f"↔ {escape(e['assist'])}"
    side = "away" if e["team"] == m["away"] else ""
    return f"""<div class="ev {side}"><div class="ev-min">{e['min']}{extra}'</div><div>{icon}</div>
      <div><span class="who">{escape(e['player'] or e['team'])}</span><br><span class="muted" style="font-size:.78rem">{sub}</span></div></div>"""


def empty(icon, text):
    st.markdown(f'<div class="empty"><div class="i">{icon}</div>{text}</div>', unsafe_allow_html=True)


# ---------------- barra superior ----------------
top_l, top_m, top_r = st.columns([2.2, 2.4, 1.6], vertical_alignment="center")
with top_l:
    st.markdown(f"""<div class="topbar"><img src="{brand_logo()}"><div>
      <div class="brand-title">ZOLA <span>Elite</span></div>
      <div class="brand-sub">Pronósticos con datos reales · Poisson + Dixon-Coles</div></div></div>""", unsafe_allow_html=True)
with top_m:
    search = st.text_input("Buscar", placeholder="🔍  Buscar equipo, liga o país", label_visibility="collapsed")
with top_r:
    c_a, c_b = st.columns([1.3, 1], vertical_alignment="center")
    with c_a:
        dot = "var(--green)" if api.enabled else "var(--gold)"
        txt = "API en línea" if api.enabled else "Modo demo"
        rem = f" · {api.remaining}" if api.remaining is not None else ""
        st.markdown(f'<div class="chips"><span class="chip"><span class="dot" style="background:{dot}"></span>{txt}{rem}</span></div>',
                    unsafe_allow_html=True)
    with c_b:
        with st.popover("⚙️ Ajustes", width="stretch"):
            if secret_key():
                st.success("API key cargada desde el servidor.")
            else:
                st.markdown("**API-Football**")
                k = st.text_input("API key", value=ss.cfg.get("api_football_key", ""), type="password",
                                  help="Gratis en dashboard.api-football.com (100 consultas/día).")
                remember = st.checkbox("Recordar en este equipo", value=CFG_PATH.exists())
                if st.button("Guardar", type="primary", width="stretch"):
                    ss.cfg["api_football_key"] = k.strip()
                    if remember:
                        save_cfg(ss.cfg)
                    elif CFG_PATH.exists():
                        CFG_PATH.unlink()
                    st.rerun()
            st.caption("Los datos en vivo se actualizan solos cada 60 s si activas «Auto».")

# ---------------- filtros ----------------
today = datetime.now(LIMA).date()
f1, f2, f3 = st.columns([2.1, 3.4, 1.2], vertical_alignment="center")
with f1:
    view = st.segmented_control("Vista", ["🔴 En vivo", "Hoy", "Mañana", "📅 Fecha"], default="Hoy",
                                label_visibility="collapsed", key="view") or "Hoy"
with f2:
    bucket = st.pills("Competición", ["⭐ Top", "Europa", "Sudamérica", "Internacional", "Todas"], default="⭐ Top",
                      label_visibility="collapsed", key="bucket") or "Todas"
    bucket = bucket.replace("⭐ ", "")
with f3:
    auto = st.toggle("Auto", value=view.endswith("En vivo"), help="Actualiza cada 60 segundos")

day = today
if view == "Mañana":
    day = today + timedelta(days=1)
elif view.endswith("Fecha"):
    day = st.date_input("Fecha", value=today, format="DD/MM/YYYY")
view_key = "En vivo" if view.endswith("En vivo") else view


# ---------------- contenido ----------------
def main_content():
    items, notice = list_matches(api, view_key, day)
    matches = filter_matches(items, bucket, search)
    prefetch([(m.get(k), m[n]) for m in matches[:80] for k, n in
              (("home_logo", "home"), ("away_logo", "away"), ("league_logo", "league"))])
    try:
        settle_history(history, items, api)
    except Exception:
        pass
    if notice:
        st.info(notice, icon="ℹ️")

    keys = [m["match_key"] for m in matches]
    if ss.selected_key not in keys:
        live_first = next((m for m in matches if is_live(m["status_short"])), None)
        ss.selected_key = (live_first or (matches[0] if matches else {})).get("match_key")

    left, right = st.columns([1, 1.85], gap="large")
    with left:
        live_n = sum(is_live(m["status_short"]) for m in matches)
        st.markdown(f"<div style='font-weight:800'>{len(matches)} partidos"
                    + (f" <span style='color:var(--red)'>· <span class='pulse'></span>{live_n} en vivo</span>" if live_n else "")
                    + "</div>", unsafe_allow_html=True)
        if not matches:
            empty("🏟️", "No hay partidos con estos filtros.<br>Prueba con «Todas» o cambia de fecha.")
        with st.container(height=820, border=False):
            for (league, country), ms in group_by_league(matches):
                demo = '<span class="badge b-demo">DEMO</span>' if ms[0].get("source") == "demo" else ""
                st.markdown(f"""<div class="lhead"><img src="{L(ms[0].get('league_logo'), league)}">{escape(league)}
                    <span class="muted" style="text-transform:none;font-weight:500">{escape(country if country not in ('World', '') else '')}</span>
                    {demo}<span class="n">{len(ms)}</span></div>""", unsafe_allow_html=True)
                for m in ms:
                    sel = m["match_key"] == ss.selected_key
                    with st.container(key=f"card_{m['match_key']}"):
                        st.markdown(match_row(m, sel), unsafe_allow_html=True)
                        if st.button("Ver", key=f"open_{m['match_key']}"):
                            ss.selected_key = m["match_key"]
                            st.rerun()

    with right:
        match = next((m for m in matches if m["match_key"] == ss.selected_key), None)
        if not match:
            empty("👈", "Elige un partido para ver el análisis.")
            return
        with st.spinner("Analizando partido…"):
            detail = match_detail(api, match)
            pred = predict(match["home"], match["away"], detail.home_form, detail.away_form, detail.state, detail.odds)
        render_detail(match, detail, pred)


def render_detail(m, detail, pred):
    s = m["status_short"]
    live, done = is_live(s), is_finished(s)
    started = live or done
    if live:
        extra = f"+{m['extra']}" if m.get("extra") else ""
        status = f'<div class="hstatus live"><span class="pulse"></span>{"Entretiempo" if s == "HT" else str(m["minute"]) + extra + "′"}</div>'
        pct = min(100, (m["minute"] or 0) / 90 * 100)
        status += f'<div class="prog"><div style="width:{pct:.0f}%"></div></div>'
    elif done:
        status = f'<div class="hstatus muted">{STATUS_LABEL.get(s, s)}</div>'
    else:
        status = f'<div class="hstatus muted">{kickoff_hhmm(m) or STATUS_LABEL.get(s, s)}</div>'
    center = f'<div class="big">{m["home_goals"]} – {m["away_goals"]}</div>' if started else '<div class="big vs">VS</div>'
    verdict = ("Empate" if pred.winner == "Empate" else f"Gana {pred.winner}") + f" · {pred.best_score}"
    rnd = f" · {escape(m['round'])}" if m.get("round") else ""
    st.markdown(f"""<div class="hero">
      <div class="hero-top"><img src="{L(m.get('league_logo'), m['league'])}">{escape(m['league'])}{rnd}</div>
      <div class="hero-grid">
        <div class="hteam"><img src="{L(m.get('home_logo'), m['home'])}"><div class="nm">{escape(m['home'])}</div>{form_html(detail.home_form.form)}</div>
        <div class="hcenter">{center}{status}{'' if done else f'<div class="verdict">🔮 {escape(verdict)}</div>'}</div>
        <div class="hteam"><img src="{L(m.get('away_logo'), m['away'])}"><div class="nm">{escape(m['away'])}</div>{form_html(detail.away_form.form)}</div>
      </div>
      <div class="p3">
        <div class="p3-lbl"><span>1 · Local <b>{pred.home_win:.0%}</b></span><span>Empate <b>{pred.draw:.0%}</b></span><span><b>{pred.away_win:.0%}</b> Visita · 2</span></div>
        <div class="p3-bar"><div class="c1" style="width:{pred.home_win*100:.1f}%"></div><div class="cX" style="width:{pred.draw*100:.1f}%"></div><div class="c2" style="width:{pred.away_win*100:.1f}%"></div></div>
      </div>
      {f'<div class="venue">🏟️ {escape(m["venue"])}</div>' if m.get("venue") else ''}
    </div>""", unsafe_allow_html=True)

    for w in detail.warnings:
        st.caption(f"⚠️ {w}")

    t1, t2, t3, t4, t5 = st.tabs(["🔮 Pronóstico", "📊 En vivo", "💰 Cuotas", "🧮 Simulador", "📒 Historial"])

    with t1:
        a, b = st.columns([1.15, 1], gap="large")
        with a:
            st.markdown(f'<div class="ai"><h4>Análisis ZOLA</h4>{ai_summary(m, pred)}</div>', unsafe_allow_html=True)
            st.markdown(pick_html(pred, detail), unsafe_allow_html=True)
            if not done:
                if st.button("💾 Guardar en mi historial", width="stretch"):
                    saved = history.save(m, pred, pred.best_bet)
                    st.toast("Predicción guardada ✅" if saved else "Ya la tenías guardada con este marcador")
        with b:
            st.markdown('<div class="kpis">' + "".join(
                f'<div class="kpi"><div class="l">{lbl}</div><div class="v">{v:.0%}</div><div class="t"><div style="width:{v*100:.0f}%"></div></div></div>'
                for lbl, v in [("Más de 1.5", pred.over15), ("Más de 2.5", pred.over25),
                               ("Más de 3.5", pred.over35), ("Ambos marcan", pred.btts)]) + "</div>", unsafe_allow_html=True)
            st.markdown('<div class="sec" style="margin-top:1rem">Marcadores más probables</div>', unsafe_allow_html=True)
            top = pred.top_scores[:6]
            mx = max((p for _, p in top), default=1) or 1
            st.markdown("".join(
                f'<div class="sc-row{" top" if i == 0 else ""}"><b>{sc}</b><div class="t"><div style="width:{p/mx*100:.0f}%"></div></div>'
                f'<span class="muted" style="text-align:right">{p:.0%}</span></div>' for i, (sc, p) in enumerate(top)),
                unsafe_allow_html=True)

    with t2:
        h, a_ = detail.stats.get("home", {}), detail.stats.get("away", {})
        if not h and not a_ and not detail.events:
            empty("⏳", "Las estadísticas y eventos aparecen cuando empieza el partido.")
        else:
            c1, c2 = st.columns(2, gap="large")
            with c1:
                st.markdown(f"<div class='sec'><span style='color:var(--blue)'>●</span> {escape(m['home'])} &nbsp; "
                            f"<span style='color:var(--orange)'>●</span> {escape(m['away'])}</div>", unsafe_allow_html=True)
                rows = [("Posesión", "possession", True), ("xG (goles esperados)", "xg", False), ("Tiros", "shots", False),
                        ("Tiros al arco", "shots_on_target", False), ("Córners", "corners", False),
                        ("Faltas", "fouls", False), ("Amarillas", "yellow", False), ("Rojas", "red", False)]
                st.markdown("".join(stat_bar(lbl, h.get(k), a_.get(k), pct) for lbl, k, pct in rows), unsafe_allow_html=True)
            with c2:
                st.markdown("<div class='sec'>Minuto a minuto</div>", unsafe_allow_html=True)
                evs = sorted(detail.events, key=lambda e: (e["min"], e.get("extra") or 0), reverse=True)
                st.markdown('<div class="panel" style="padding:.3rem .8rem">' +
                            ("".join(event_html(e, m) for e in evs) or "<span class='muted'>Sin eventos.</span>") + "</div>",
                            unsafe_allow_html=True)

    with t3:
        if not detail.odds:
            empty("💤", "No hay cuotas disponibles para este partido.")
        else:
            rows = [{"Mercado": v["market"], "Cuota": v["odd"], "Modelo": v["prob"] * 100,
                     "Casa": v["implied"] * 100, "Ventaja": v["edge"] * 100,
                     "Valor": "✅" if v["edge"] >= 0.03 and v["prob"] >= 0.30 else ""}
                    for v in pred.value_bets]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
                "Cuota": st.column_config.NumberColumn(format="%.2f"),
                "Modelo": st.column_config.ProgressColumn("Prob. modelo", format="%.0f%%", min_value=0, max_value=100),
                "Casa": st.column_config.NumberColumn("Prob. casa", format="%.0f%%"),
                "Ventaja": st.column_config.NumberColumn(format="%+.1f%%"),
            })
            st.caption("**Ventaja** = probabilidad del modelo × cuota − 1. Si es positiva, el modelo ve valor. "
                       "**Prob. casa** = lo que implica la cuota, sin el margen de la casa.")

    with t4:
        bb = pred.best_bet or {}
        markets = list(pred.markets)
        default_mk = bb.get("market") if bb.get("market") in markets else "1"
        c1, c2, c3 = st.columns(3)
        mk = c1.selectbox("Mercado", markets, index=markets.index(default_mk))
        odd_default = float(detail.odds.get(mk) or round(1 / max(pred.markets[mk], 0.01), 2))
        odd = c2.number_input("Cuota", min_value=1.01, value=max(1.01, odd_default), step=0.05, key=f"odd_{m['match_key']}_{mk}")
        bank = c3.number_input("Bankroll (S/)", min_value=10.0, value=500.0, step=50.0)
        p = pred.markets[mk]
        stake = round(bank * kelly_fraction(p, odd) / 4, 2)
        ev = p * odd - 1
        col = "var(--green)" if ev > 0 else "var(--red)"
        st.markdown(f"""<div class="kpis k4">
          <div class="kpi"><div class="l">Prob. modelo</div><div class="v">{p:.1%}</div></div>
          <div class="kpi"><div class="l">Valor esperado</div><div class="v" style="color:{col}">{ev:+.1%}</div></div>
          <div class="kpi"><div class="l">Stake (¼ Kelly)</div><div class="v">S/{stake:.2f}</div></div>
          <div class="kpi"><div class="l">Ganancia si acierta</div><div class="v">S/{stake * (odd - 1):.2f}</div></div>
        </div>""", unsafe_allow_html=True)
        if ev <= 0:
            st.caption("Con esta cuota la apuesta pierde a la larga según el modelo, por eso el stake sugerido es 0.")

    with t5:
        s_ = history.summary()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Guardadas", s_["total"])
        c2.metric("Resueltas", s_["settled"])
        c3.metric("Acierto", f"{s_['hit_rate']:.0%}" if s_["hit_rate"] is not None else "—")
        c4.metric("Unidades", f"{s_['units']:+.2f}" if s_["bets_with_odds"] else "—")
        df = history.recent(30)
        if df.empty:
            empty("📒", "Aún no guardas predicciones.<br>Usa «Guardar en mi historial» en la pestaña Pronóstico.")
        else:
            df["Res."] = df["pick_won"].map({1: "✅", 0: "❌"}).fillna("⏳")
            df["Partido"] = df["home"] + " vs " + df["away"]
            show = df[["Res.", "ts", "Partido", "score_at_pick", "pick_market", "pick_odd", "predicted_score", "final_score"]].rename(columns={
                "ts": "Fecha", "score_at_pick": "Al guardar", "pick_market": "Jugada", "pick_odd": "Cuota",
                "predicted_score": "Pronóstico", "final_score": "Final"})
            st.dataframe(show, hide_index=True, width="stretch")


def ai_summary(m, pred):
    if is_finished(m["status_short"]):
        return (f"Terminó <b>{escape(m['home'])} {m['home_goals']}–{m['away_goals']} {escape(m['away'])}</b>. "
                f"Revisa en Historial si tu predicción acertó.")
    fav = max(pred.home_win, pred.draw, pred.away_win)
    lead = "El empate es lo más probable" if pred.winner == "Empate" else f"<b>{escape(pred.winner)}</b> es favorito"
    parts = [f"{lead} ({fav:.0%}). Marcador final más probable: <b>{pred.best_score}</b>.",
             f"Goles esperados en 90′: {escape(m['home'])} <b>{pred.lam_home:.2f}</b> · {escape(m['away'])} <b>{pred.lam_away:.2f}</b>.",
             f"Confianza <b>{pred.confidence}</b> · {pred.data_quality}."]
    if pred.notes:
        parts.append("<span class='muted' style='font-size:.82rem'>" + " · ".join(escape(n) for n in pred.notes) + "</span>")
    return "<br>".join(parts)


def pick_html(pred, detail):
    bb = pred.best_bet
    if not bb:
        return ('<div class="pick"><div class="ic">🛑</div><div><div class="t">Recomendación</div>'
                '<div class="v">No apostar</div><div class="muted" style="font-size:.8rem">Ningún mercado tiene suficiente probabilidad o valor.</div></div></div>')
    if bb["kind"] == "valor":
        return (f'<div class="pick" style="border-color:rgba(34,197,94,.45)"><div class="ic">🎯</div><div><div class="t">Apuesta de valor</div>'
                f'<div class="v">{bb["market"]} @ {bb["odd"]:.2f}</div><div class="muted" style="font-size:.8rem">Modelo {bb["prob"]:.0%} vs casa {1/bb["odd"]:.0%}</div></div>'
                f'<div class="e" style="color:var(--green)">+{bb["edge"]:.0%}<div class="muted" style="font-size:.7rem">ventaja</div></div></div>')
    note = "Sin cuotas para medir valor." if not detail.odds else "La cuota actual no ofrece valor."
    return (f'<div class="pick"><div class="ic">📌</div><div><div class="t">Jugada más probable</div>'
            f'<div class="v">{bb["market"]}</div><div class="muted" style="font-size:.8rem">{note}</div></div>'
            f'<div class="e">{bb["prob"]:.0%}</div></div>')


if auto:
    st.fragment(run_every=60)(main_content)()
else:
    main_content()

st.markdown('<div class="foot">ZOLA Elite · Las probabilidades son estimaciones estadísticas, no garantías. '
            'Apuesta con responsabilidad · +18</div>', unsafe_allow_html=True)
