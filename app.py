"""ZOLA Elite — interfaz Streamlit (estilo marcador en vivo)."""
from __future__ import annotations

import base64
import json
import os
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from zola.api import FootballApi
from zola.data import filter_matches, league_standings, list_matches, match_detail, settle_history
from zola.db import History
from zola.logos import logo, prefetch
from zola.model import kelly_fraction, predict
from zola.status import STATUS_LABEL, TOP_LEAGUE_IDS, is_finished, is_live

APP_DIR = Path(__file__).resolve().parent
CFG_PATH = APP_DIR / ".zola_cfg.json"
DB_PATH = Path(os.getenv("ZOLA_DB_PATH", APP_DIR / "zola_history.db"))
LOGO_PATH = APP_DIR / "zola_logo.png"
LIMA = ZoneInfo("America/Lima")
LEAGUE_PRIORITY = [1, 2, 13, 281, 39, 140, 135, 78, 61, 11, 3, 848, 71, 128, 9, 4]
WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

st.set_page_config(page_title="ZOLA Elite", page_icon="⚽", layout="wide", initial_sidebar_state="collapsed")


# ================= configuración =================
def load_cfg() -> dict:
    cfg = {"api_football_key": "", "favs": []}
    if CFG_PATH.exists():
        try:
            cfg.update(json.loads(CFG_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


def save_cfg() -> None:
    try:
        CFG_PATH.write_text(json.dumps(ss.cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


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
ss.setdefault("day_offset", 0)
ss.setdefault("league_pick", None)
ss.setdefault("favs", set(ss.cfg.get("favs", [])))

api_key = secret_key() or ss.cfg.get("api_football_key", "")
api = get_api(api_key)
history = get_history()
DEMO = not api.enabled

# ================= estilos =================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root{--bg:#0e1015;--panel:#171a21;--panel2:#1f232c;--hover:#232835;--line:#272c37;--text:#eceff5;--muted:#8b93a6;
--brand:#2f6bff;--brand2:#1f4fd8;--green:#16a34a;--green2:#22c55e;--red:#ef4444;--orange:#f59e0b;--gold:#facc15;--teal:#14b8a6;}
html,body,.stApp,button,input,textarea,[class*="css"]{font-family:'Inter',system-ui,sans-serif !important;}
.stApp{background:var(--bg);}
[data-testid="stHeader"]{background:transparent;height:0;}
[data-testid="stToolbar"]{display:none;}
.block-container{max-width:1400px;padding-top:.8rem;padding-bottom:2rem;}
.muted{color:var(--muted);}
.band{margin-bottom:.6rem;background:linear-gradient(90deg,var(--brand2),var(--brand));border-radius:16px;padding:.7rem 1rem;display:flex;align-items:center;gap:12px;}
.band img{width:40px;height:40px;object-fit:contain;border-radius:10px;background:rgba(255,255,255,.08);}
.band .t{font-size:1.45rem;font-weight:900;color:#fff;letter-spacing:-.02em;}
.band .s{font-size:.75rem;color:rgba(255,255,255,.75);font-weight:600;}
.band .chip{margin-left:auto;background:rgba(255,255,255,.14);color:#fff;border-radius:999px;padding:.3rem .75rem;font-size:.75rem;font-weight:700;display:flex;gap:6px;align-items:center;}
.dot{width:8px;height:8px;border-radius:50%;display:inline-block;}
.ticker{display:flex;gap:8px;overflow-x:auto;padding:.55rem .1rem .35rem;scrollbar-width:thin;}
.ticker .lbl{flex:none;display:flex;align-items:center;gap:6px;background:var(--brand);color:#fff;font-weight:800;font-size:.78rem;border-radius:999px;padding:.35rem .8rem;}
.tk{flex:none;display:flex;align-items:center;gap:7px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:.35rem .65rem;font-size:.82rem;font-weight:800;}
.tk .st{color:var(--red);font-size:.72rem;}
.tk img{width:20px;height:20px;object-fit:contain;}
.tk .sc{color:var(--red);}
[class*="st-key-pane_"]{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:.8rem .8rem 1rem;}
.lhead{display:flex;align-items:center;gap:10px;padding:.7rem .4rem .45rem;margin-top:.3rem;border-top:1px solid var(--line);}
.lhead .lg{width:30px;height:30px;object-fit:contain;}
.lhead .nm{font-weight:800;font-size:.88rem;line-height:1.15;}
.lhead .ct{display:flex;align-items:center;gap:5px;color:var(--muted);font-size:.78rem;font-weight:500;}
.lhead .ct img{width:14px;height:10px;object-fit:cover;border-radius:2px;}
.lhead .cnt{margin-left:auto;background:var(--panel2);border-radius:999px;padding:.12rem .55rem;font-size:.72rem;font-weight:700;color:var(--muted);}
.lhead .cnt b{color:var(--red);}
.mrow{display:grid;grid-template-columns:52px 1fr 26px 44px;gap:8px;align-items:center;padding:.5rem .4rem;border-radius:10px;}
.mrow.sel{background:rgba(47,107,255,.14);box-shadow:inset 3px 0 0 var(--brand);}
.mtime{font-size:.75rem;color:var(--muted);text-align:center;line-height:1.35;font-weight:600;}
.mtime .lv{color:var(--red);font-weight:800;}
.mteams{display:flex;flex-direction:column;gap:4px;min-width:0;}
.tl{display:flex;align-items:center;gap:8px;min-width:0;font-size:.9rem;}
.tl img{width:18px;height:18px;object-fit:contain;flex:none;}
.tl span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tl.w span{font-weight:800;}
.msc{display:flex;flex-direction:column;gap:4px;text-align:right;font-weight:800;font-size:.9rem;}
.msc.lv{color:var(--red);}
.badge{display:inline-block;border-radius:6px;padding:.05rem .4rem;font-size:.6rem;font-weight:800;background:rgba(250,204,21,.14);color:var(--gold);}
.pulse{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--red);margin-right:4px;vertical-align:middle;animation:pl 1.4s infinite;}
@keyframes pl{0%{box-shadow:0 0 0 0 rgba(239,68,68,.7)}70%{box-shadow:0 0 0 6px rgba(239,68,68,0)}100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}}
[class*="st-key-row_"]{position:relative;gap:0 !important;}
[class*="st-key-row_"]:hover .mrow{background:var(--hover);}
[class*="st-key-row_"] .stElementContainer:not([class*="st-key-open_"]):not([class*="st-key-fav_"]){pointer-events:none;}
[class*="st-key-row_"] [class*="st-key-open_"]{position:absolute;top:0;left:0;bottom:0;width:calc(100% - 52px) !important;height:100% !important;z-index:5;margin:0;}
[class*="st-key-open_"] .stButton,[class*="st-key-open_"] button,[class*="st-key-pick_"] .stButton,[class*="st-key-pick_"] button{width:100%;height:100%;opacity:0;cursor:pointer;}
[class*="st-key-row_"] [class*="st-key-fav_"]{position:absolute;right:6px;top:50%;transform:translateY(-50%);width:38px !important;z-index:6;margin:0;}
[class*="st-key-fav_"] button{width:36px !important;height:36px !important;min-height:36px !important;padding:0 !important;border-radius:50% !important;background:transparent !important;border:1px solid var(--line) !important;color:var(--muted) !important;font-size:1rem !important;}
[class*="st-key-fav_"] button:hover{border-color:var(--gold) !important;color:var(--gold) !important;}
[class*="st-key-fav_on_"] button{color:var(--gold) !important;border-color:rgba(250,204,21,.5) !important;}
[class*="st-key-lg_"]{position:relative;gap:0 !important;}
[class*="st-key-lg_"] .stElementContainer:not([class*="st-key-pick_"]){pointer-events:none;}
[class*="st-key-lg_"] [class*="st-key-pick_"]{position:absolute;inset:0;width:100% !important;height:100% !important;z-index:5;margin:0;}
[class*="st-key-lg_"]:hover .litem{background:var(--hover);}
.litem{display:flex;align-items:center;gap:10px;padding:.5rem .55rem;border-radius:10px;}
.litem.sel{background:rgba(47,107,255,.14);box-shadow:inset 3px 0 0 var(--brand);}
.litem img{width:26px;height:26px;object-fit:contain;}
.litem .nm{font-weight:700;font-size:.88rem;}
.litem .ct{color:var(--muted);font-size:.75rem;}
.litem .n{margin-left:auto;color:var(--muted);font-size:.75rem;font-weight:700;}
.dnav{display:flex;align-items:center;justify-content:center;font-weight:800;color:var(--brand);font-size:.95rem;height:38px;border:1px solid var(--line);border-radius:10px;}
.dhead{display:flex;align-items:center;gap:10px;font-weight:800;font-size:.92rem;}
.dhead img{width:30px;height:30px;object-fit:contain;}
.dteams{display:grid;grid-template-columns:1fr 1.1fr 1fr;align-items:center;margin:1.1rem 0 .4rem;}
.dt{display:flex;flex-direction:column;align-items:center;gap:8px;text-align:center;}
.dt img{width:70px;height:70px;object-fit:contain;}
.dt .nm{font-weight:800;font-size:.98rem;}
.dc{text-align:center;}
.dc .big{font-size:2.6rem;font-weight:900;letter-spacing:-.02em;line-height:1.05;}
.dc .tm{font-size:1.6rem;font-weight:800;}
.dc .sub{color:var(--muted);font-size:.85rem;font-weight:600;margin-top:.2rem;}
.dc .lv{color:var(--red);font-weight:800;}
.prog{height:3px;border-radius:9px;background:var(--line);margin:.5rem auto 0;width:120px;overflow:hidden;}
.prog div{height:100%;background:var(--red);}
.form{display:flex;gap:3px;justify-content:center;}
.form span{width:20px;height:20px;border-radius:5px;font-size:.62rem;font-weight:800;display:flex;align-items:center;justify-content:center;color:#fff;}
.fW{background:var(--green);} .fD{background:#6b7280;} .fL{background:var(--red);}
.box{background:var(--panel2);border-radius:14px;padding:.9rem 1rem;margin-top:.8rem;}
.box h5{margin:0;font-size:.95rem;font-weight:800;}
.box .s{color:var(--muted);font-size:.78rem;margin:.1rem 0 .7rem;}
.vote{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;}
.vote div{display:flex;align-items:center;justify-content:space-between;border:1px solid var(--line);border-radius:999px;padding:.45rem .9rem;font-weight:800;}
.vote div img{width:22px;height:22px;object-fit:contain;}
.vote div.top{border-color:var(--brand);background:rgba(47,107,255,.16);}
.odds{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;}
.odds div{display:flex;justify-content:space-between;align-items:center;border:1px solid var(--line);border-radius:10px;padding:.5rem .8rem;font-size:.88rem;}
.odds div b{font-weight:800;}
.up{color:var(--green2);font-size:.7rem;margin-left:4px;} .dn{color:var(--red);font-size:.7rem;margin-left:4px;}
.pick{display:flex;align-items:center;gap:12px;}
.pick .ic{font-size:1.5rem;}
.pick .v{font-size:1.05rem;font-weight:900;}
.pick .e{margin-left:auto;text-align:right;font-weight:900;font-size:1.1rem;}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;}
.kpi{background:var(--panel2);border-radius:12px;padding:.65rem .75rem;}
.kpi .l{font-size:.7rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.03em;}
.kpi .v{font-size:1.25rem;font-weight:900;margin-top:.1rem;}
.kpi .t{height:4px;border-radius:9px;background:var(--line);margin-top:.4rem;overflow:hidden;}
.kpi .t div{height:100%;background:var(--brand);}
.scr{display:grid;grid-template-columns:40px 1fr 40px;gap:10px;align-items:center;font-size:.86rem;margin-bottom:.35rem;}
.scr .t{height:7px;border-radius:9px;background:var(--line);overflow:hidden;}
.scr .t div{height:100%;background:var(--brand);border-radius:9px;}
.scr.top .t div{background:var(--green2);}
.bar{margin-bottom:.75rem;}
.bar-top{display:flex;justify-content:space-between;font-size:.84rem;margin-bottom:.25rem;}
.bar-top span{color:var(--muted);font-weight:600;}
.track{display:flex;gap:3px;height:7px;}
.track div{height:100%;border-radius:9px;}
.fh{background:var(--brand);} .fa{background:var(--orange);}
.ev{display:grid;grid-template-columns:44px 24px 1fr;gap:6px;align-items:center;padding:.5rem .2rem;border-bottom:1px solid var(--line);font-size:.87rem;}
.ev:last-child{border-bottom:none;}
.ev .m{font-weight:800;color:var(--muted);}
.ev.away{direction:rtl;} .ev.away>*{direction:ltr;text-align:right;}
table.tbl{width:100%;border-collapse:collapse;font-size:.84rem;}
.tbl th{color:var(--muted);font-weight:700;font-size:.72rem;text-align:center;padding:.45rem .3rem;border-bottom:1px solid var(--line);}
.tbl th.l,.tbl td.l{text-align:left;}
.tbl td{text-align:center;padding:.42rem .3rem;border-bottom:1px solid var(--line);}
.tbl tr.hl td{background:rgba(47,107,255,.12);}
.tbl td.rk{position:relative;width:34px;font-weight:700;}
.tbl td.rk i{position:absolute;left:0;top:18%;bottom:18%;width:3px;border-radius:3px;}
.tbl td.tm{display:flex;align-items:center;gap:8px;font-weight:600;}
.tbl td.tm img{width:20px;height:20px;object-fit:contain;}
.tbl td.pts{font-weight:900;}
.tbl .form{justify-content:center;} .tbl .form span{width:18px;height:18px;font-size:.58rem;}
.zone-leg{display:flex;flex-wrap:wrap;gap:14px;margin-top:.6rem;font-size:.75rem;color:var(--muted);}
.zone-leg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:middle;}
.lpage{display:flex;align-items:center;gap:14px;}
.lpage img{width:56px;height:56px;object-fit:contain;}
.lpage .nm{font-size:1.35rem;font-weight:900;}
.lpage .ct{display:flex;gap:6px;align-items:center;color:var(--muted);font-size:.85rem;}
.lpage .ct img{width:18px;height:13px;object-fit:cover;border-radius:2px;}
.ai{line-height:1.6;font-size:.92rem;}
.empty{text-align:center;padding:2.2rem 1rem;color:var(--muted);}
.empty .i{font-size:2rem;}
.foot{color:var(--muted);font-size:.75rem;margin-top:1.4rem;text-align:center;}
div[data-baseweb="tab-list"]{gap:2px;border-bottom:1px solid var(--line);}
button[data-baseweb="tab"]{font-weight:700 !important;padding:.5rem .8rem !important;}
.stButton>button{border-radius:10px !important;font-weight:700 !important;}
[class*="st-key-dnav_"] button p{font-size:1.5rem !important;line-height:1;}
.tbl,.tbl tr,.tbl td,.tbl th{border-left:none !important;border-right:none !important;background:transparent;}
[class*="st-key-dnav_"] button{height:38px;min-height:38px;border:1px solid var(--line) !important;background:transparent !important;color:var(--brand) !important;font-size:1.1rem !important;}
@media (max-width:900px){.dt img{width:52px;height:52px;} .dc .big{font-size:2rem;} .kpis{grid-template-columns:repeat(2,1fr);} .vote div{padding:.4rem .55rem;font-size:.85rem;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ================= helpers =================
def L(url, name=""):
    return logo(url, name)


def kickoff(m):
    try:
        return datetime.fromisoformat(m["kickoff"]).astimezone(LIMA)
    except Exception:
        return None


def day_label(d: date) -> str:
    t = datetime.now(LIMA).date()
    if d == t:
        return "Hoy"
    if d == t + timedelta(days=1):
        return "Mañana"
    if d == t - timedelta(days=1):
        return "Ayer"
    return f"{WEEKDAYS[d.weekday()]} {d.strftime('%d/%m')}"


def status_cell(m):
    s = m["status_short"]
    k = kickoff(m)
    hhmm = k.strftime("%H:%M") if k else ""
    if s == "HT":
        return f'<div class="mtime">{hhmm}<br><span class="lv">ET</span></div>'
    if is_live(s):
        extra = f"+{m['extra']}" if m.get("extra") else ""
        return f'<div class="mtime">{hhmm}<br><span class="lv">{m["minute"]}{extra}\'</span></div>'
    if is_finished(s):
        return f'<div class="mtime">{hhmm}<br>Final</div>'
    if s in {"PST", "CANC", "ABD"}:
        return f'<div class="mtime">{hhmm}<br><span class="lv">{STATUS_LABEL.get(s, s)[:5]}</span></div>'
    return f'<div class="mtime">{hhmm or "—"}<br>-</div>'


def match_row(m, sel):
    s = m["status_short"]
    started = is_live(s) or is_finished(s)
    hw = started and m["home_goals"] > m["away_goals"]
    aw = started and m["away_goals"] > m["home_goals"]
    sc = (f'<div class="msc{" lv" if is_live(s) else ""}"><span>{m["home_goals"]}</span><span>{m["away_goals"]}</span></div>'
          if started else '<div class="msc"></div>')
    return f"""<div class="mrow{' sel' if sel else ''}">{status_cell(m)}<div class="mteams">
      <div class="tl{' w' if hw else ''}"><img src="{L(m.get('home_logo'), m['home'])}"><span>{escape(m['home'])}</span></div>
      <div class="tl{' w' if aw else ''}"><img src="{L(m.get('away_logo'), m['away'])}"><span>{escape(m['away'])}</span></div>
      </div>{sc}<div></div></div>"""


def cname(m):
    c = m.get("country") or ""
    return "Internacional" if c in ("", "World") else c


def flag_html(m):
    c = m.get("country") or ""
    if c in ("", "World"):
        return '<span class="ct">Internacional</span>'
    img = f'<img src="{L(m.get("flag"), c)}">' if m.get("flag") else ""
    return f'<span class="ct">{img}{escape(c)}</span>'


def group_by_league(matches):
    groups = {}
    for m in matches:
        groups.setdefault(m.get("league_id") or m["league"], []).append(m)

    def prio(ms):
        lid = ms[0].get("league_id")
        live = any(is_live(x["status_short"]) for x in ms)
        p = LEAGUE_PRIORITY.index(lid) if lid in LEAGUE_PRIORITY else (50 if lid in TOP_LEAGUE_IDS else 100)
        return (0 if live else 1, p, ms[0]["league"])
    return sorted(groups.values(), key=prio)


def form_html(form, size=""):
    f = (form or "")[-5:]
    if not f:
        return '<span class="muted" style="font-size:.75rem">—</span>'
    return '<div class="form">' + "".join(f'<span class="f{c}">{ {"W": "G", "D": "E", "L": "P"}.get(c, c)}</span>' for c in f) + "</div>"


def zone_color(z: str) -> str:
    z = (z or "").lower()
    if any(k in z for k in ("champions", "libertadores", "promotion -", "1/8", "final")):
        return "var(--brand)"
    if "europa" in z or "sudamericana" in z:
        return "var(--orange)"
    if "conference" in z:
        return "var(--teal)"
    if "releg" in z or "descenso" in z:
        return "var(--red)"
    if "promotion" in z or "play" in z:
        return "var(--green2)"
    return "transparent"


def standings_html(groups, highlight=()):
    if not groups:
        return ""
    out = []
    zones = {}
    for g in groups:
        rows = []
        for r in g["rows"]:
            zc = zone_color(r["zone"])
            if r["zone"]:
                zones.setdefault(r["zone"], zc)
            hl = " hl" if r["team"] in highlight else ""
            rows.append(f"""<tr class="{hl.strip()}"><td class="rk"><i style="background:{zc}"></i>{r['rank']}</td>
              <td class="l tm"><img src="{L(r['logo'], r['team'])}">{escape(r['team'])}</td>
              <td>{r['played']}</td><td>{r['win']}</td><td>{r['draw']}</td><td>{r['lose']}</td>
              <td>{r['diff']:+d}</td><td>{r['gf']}:{r['ga']}</td><td>{form_html(r['form'])}</td><td class="pts">{r['points']}</td></tr>""")
        title = f"<div class='muted' style='font-weight:700;font-size:.8rem;margin:.6rem 0 .2rem'>{escape(g['name'])}</div>" if len(groups) > 1 else ""
        out.append(title + f"""<table class="tbl"><thead><tr><th>#</th><th class="l">Equipo</th><th>PJ</th><th>G</th><th>E</th>
          <th>P</th><th>DG</th><th>Goles</th><th>Últimos 5</th><th>PTS</th></tr></thead><tbody>{''.join(rows)}</tbody></table>""")
    legend = "".join(f'<span><i style="background:{c}"></i>{escape(z)}</span>' for z, c in zones.items() if c != "transparent")
    return "".join(out) + (f'<div class="zone-leg">{legend}</div>' if legend else "")


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
      <div class="track"><div class="fh" style="width:{hw:.1f}%"></div><div style="flex:1;background:var(--line)"></div><div class="fa" style="width:{aw:.1f}%"></div></div></div>"""


DETAIL_ES = {"Normal Goal": "Gol", "Own Goal": "Autogol", "Penalty": "Gol de penal", "Missed Penalty": "Penal fallado",
             "Yellow Card": "Amarilla", "Red Card": "Roja", "Second Yellow card": "Doble amarilla",
             "Goal cancelled": "Gol anulado (VAR)", "Penalty confirmed": "Penal confirmado (VAR)"}


def event_html(e, m):
    icon = {"Goal": "⚽", "Card": "🟨", "subst": "🔁", "Var": "📺"}.get(e["type"], "•")
    if e["type"] == "Card" and ("Red" in e["detail"] or "Second Yellow" in e["detail"]):
        icon = "🟥"
    if e["type"] == "Goal" and e["detail"] == "Missed Penalty":
        icon = "❌"
    extra = f"+{e['extra']}" if e.get("extra") else ""
    sub = escape("Cambio" if e["type"] == "subst" else DETAIL_ES.get(e["detail"], e["detail"]))
    if e["type"] == "Goal" and e.get("assist"):
        sub += f" · asist. {escape(e['assist'])}"
    if e["type"] == "subst" and e.get("assist"):
        sub = f"↔ {escape(e['assist'])}"
    side = "away" if e["team"] == m["away"] else ""
    return f"""<div class="ev {side}"><div class="m">{e['min']}{extra}'</div><div>{icon}</div>
      <div><b>{escape(e['player'] or e['team'])}</b><br><span class="muted" style="font-size:.76rem">{sub}</span></div></div>"""


def empty(icon, text):
    st.markdown(f'<div class="empty"><div class="i">{icon}</div>{text}</div>', unsafe_allow_html=True)


def toggle_fav(key):
    if key in ss.favs:
        ss.favs.discard(key)
    else:
        ss.favs.add(key)
    ss.cfg["favs"] = sorted(ss.favs)
    if CFG_PATH.exists():
        save_cfg()


# ================= cabecera =================
dot = "var(--green2)" if not DEMO else "var(--gold)"
estado = "API en línea" + (f" · {api.remaining}" if api.remaining is not None else "") if not DEMO else "Modo demo"
st.markdown(f"""<div class="band"><img src="{brand_logo()}"><div><div class="t">ZOLA Elite</div>
  <div class="s">Marcadores en vivo y pronósticos</div></div>
  <div class="chip"><span class="dot" style="background:{dot}"></span>{estado}</div></div>""", unsafe_allow_html=True)

h1, h2, h3 = st.columns([2.2, 3, 1.1], vertical_alignment="center")
with h1:
    section = st.segmented_control("Sección", ["⚽ Partidos", "🏆 Ligas", "📒 Historial"], default="⚽ Partidos",
                                   label_visibility="collapsed", key="section") or "⚽ Partidos"
with h2:
    search = st.text_input("Buscar", placeholder="🔍  Buscar equipo, liga o país", label_visibility="collapsed")
with h3:
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
                    save_cfg()
                elif CFG_PATH.exists():
                    CFG_PATH.unlink()
                st.rerun()
        auto = st.toggle("Actualizar en vivo cada 60 s", value=ss.get("auto", True), key="auto")

today = datetime.now(LIMA).date()
day = today + timedelta(days=ss.day_offset)


# ================= carga de datos =================
def load_day(live_only=False):
    items, notice = list_matches(api, "En vivo" if live_only else "Hoy", day)
    return items, notice


def ticker(items):
    live = [m for m in items if is_live(m["status_short"])][:14]
    if not live:
        return
    chips = "".join(
        f'<div class="tk"><span class="st"><span class="pulse"></span>{"ET" if m["status_short"] == "HT" else str(m["minute"]) + chr(39)}</span>'
        f'<img src="{L(m.get("home_logo"), m["home"])}"><span class="sc">{m["home_goals"]} - {m["away_goals"]}</span>'
        f'<img src="{L(m.get("away_logo"), m["away"])}"></div>' for m in live)
    st.markdown(f'<div class="ticker"><span class="lbl">🔥 En vivo</span>{chips}</div>', unsafe_allow_html=True)


# ================= vista PARTIDOS =================
def view_matches():
    items, notice = load_day()
    prefetch([(m.get(k), m.get(n) or "") for m in items[:120] for k, n in
              (("home_logo", "home"), ("away_logo", "away"), ("league_logo", "league"), ("flag", "country"))])
    try:
        settle_history(history, items, api)
    except Exception:
        pass
    ticker(items)
    if notice:
        st.info(notice, icon="ℹ️")

    base = filter_matches(items, ss.get("bucket") or "Todas", search)
    n_live = sum(is_live(m["status_short"]) for m in base)
    n_fin = sum(is_finished(m["status_short"]) for m in base)
    n_up = len(base) - n_live - n_fin
    n_fav = sum(m["match_key"] in ss.favs for m in base)

    left, right = st.columns([1, 1.25], gap="medium")
    with left:
        with st.container(key="pane_list"):
            c1, c2, c3 = st.columns([1, 2.4, 1], vertical_alignment="center")
            if c1.button("‹", key="dnav_prev", width="stretch"):
                ss.day_offset -= 1; st.rerun()
            c2.markdown(f'<div class="dnav">📅 {day_label(day)}</div>', unsafe_allow_html=True)
            if c3.button("›", key="dnav_next", width="stretch"):
                ss.day_offset += 1; st.rerun()

            labels = {"Todos": f"Todos ({len(base)})", "En vivo": f"🔴 En vivo ({n_live})", "Próximos": f"Próximos ({n_up})",
                      "Terminados": f"Terminados ({n_fin})", "Favoritos": f"⭐ ({n_fav})"}
            status = st.pills("Estado", list(labels), format_func=labels.get, default="Todos",
                              label_visibility="collapsed", key="status") or "Todos"
            st.pills("Región", ["Top", "Europa", "Sudamérica", "Internacional", "Todas"], default="Todas",
                     label_visibility="collapsed", key="bucket")

            if status == "En vivo":
                matches = [m for m in base if is_live(m["status_short"])]
            elif status == "Próximos":
                matches = [m for m in base if not is_live(m["status_short"]) and not is_finished(m["status_short"])]
            elif status == "Terminados":
                matches = [m for m in base if is_finished(m["status_short"])]
            elif status == "Favoritos":
                matches = [m for m in base if m["match_key"] in ss.favs]
            else:
                matches = base

            keys = [m["match_key"] for m in matches]
            if ss.selected_key not in keys:
                first = next((m for m in matches if is_live(m["status_short"])), matches[0] if matches else None)
                ss.selected_key = first["match_key"] if first else None

            if not matches:
                empty("🏟️", "No hay partidos con estos filtros." + ("<br>Marca partidos con ☆ para verlos aquí." if status == "Favoritos" else ""))
            with st.container(height=760, border=False):
                for ms in group_by_league(matches):
                    m0 = ms[0]
                    nl = sum(is_live(x["status_short"]) for x in ms)
                    cnt = f"<b>{nl}</b>/{len(ms)}" if nl else str(len(ms))
                    demo = ' <span class="badge">DEMO</span>' if m0.get("source") == "demo" else ""
                    st.markdown(f"""<div class="lhead"><img class="lg" src="{L(m0.get('league_logo'), m0['league'])}">
                      <div><div class="nm">{escape(m0['league'])}{demo}</div>{flag_html(m0)}</div><span class="cnt">{cnt}</span></div>""",
                                unsafe_allow_html=True)
                    for m in ms:
                        k = m["match_key"]
                        with st.container(key=f"row_{k}"):
                            st.markdown(match_row(m, k == ss.selected_key), unsafe_allow_html=True)
                            if st.button("Ver", key=f"open_{k}"):
                                ss.selected_key = k; st.rerun()
                            fav = k in ss.favs
                            if st.button("★" if fav else "☆", key=f"fav_{'on_' if fav else ''}{k}", help="Favorito"):
                                toggle_fav(k); st.rerun()

    with right:
        match = next((m for m in matches if m["match_key"] == ss.selected_key), None)
        with st.container(key="pane_detail"):
            if not match:
                empty("👈", "Elige un partido para ver el análisis.")
            else:
                detail = match_detail(api, match)
                pred = predict(match["home"], match["away"], detail.home_form, detail.away_form, detail.state, detail.odds)
                render_detail(match, detail, pred)


def render_detail(m, detail, pred):
    s = m["status_short"]
    live, done = is_live(s), is_finished(s)
    k = kickoff(m)
    if live:
        extra = f"+{m['extra']}" if m.get("extra") else ""
        center = (f'<div class="big">{m["home_goals"]} - {m["away_goals"]}</div><div class="sub lv"><span class="pulse"></span>'
                  f'{"Entretiempo" if s == "HT" else str(m["minute"]) + extra + "′"}</div>'
                  f'<div class="prog"><div style="width:{min(100, (m["minute"] or 0) / 90 * 100):.0f}%"></div></div>')
    elif done:
        center = f'<div class="big">{m["home_goals"]} - {m["away_goals"]}</div><div class="sub">{STATUS_LABEL.get(s, s)}</div>'
    else:
        when = day_label(k.date()) if k else ""
        center = f'<div class="tm">{k.strftime("%H:%M") if k else "—"}</div><div class="sub">{when}</div>'
    rnd = f" · {escape(m['round'])}" if m.get("round") else ""
    st.markdown(f"""<div class="dhead"><img src="{L(m.get('league_logo'), m['league'])}"><div>{escape(m['league'])}
        <div class="muted" style="font-size:.75rem;font-weight:500">{escape(m.get('country') or '')}{rnd}</div></div></div>
      <div class="dteams">
        <div class="dt"><img src="{L(m.get('home_logo'), m['home'])}"><div class="nm">{escape(m['home'])}</div>{form_html(detail.home_form.form)}</div>
        <div class="dc">{center}</div>
        <div class="dt"><img src="{L(m.get('away_logo'), m['away'])}"><div class="nm">{escape(m['away'])}</div>{form_html(detail.away_form.form)}</div>
      </div>""", unsafe_allow_html=True)
    if m.get("venue"):
        st.markdown(f"<div class='muted' style='text-align:center;font-size:.78rem'>🏟️ {escape(m['venue'])}</div>", unsafe_allow_html=True)

    if not done:
        vals = [("h", pred.home_win), ("x", pred.draw), ("a", pred.away_win)]
        top = max(v for _, v in vals)
        ic = {"h": f'<img src="{L(m.get("home_logo"), m["home"])}">', "x": "<span>X</span>",
              "a": f'<img src="{L(m.get("away_logo"), m["away"])}">'}
        vote = "".join(f'<div class="{"top" if v == top else ""}">{ic[k_]}<span>{v:.0%}</span></div>' for k_, v in vals)
        st.markdown(f"""<div class="box"><h5>¿Quién gana?</h5><div class="s">Según el modelo ZOLA · {pred.confidence.lower()} confianza</div>
          <div class="vote">{vote}</div></div>""", unsafe_allow_html=True)

    if detail.odds and all(detail.odds.get(x) for x in ("1", "X", "2")):
        def cell(mk, lbl):
            edge = pred.markets[mk] * detail.odds[mk] - 1
            arrow = '<span class="up">▲</span>' if edge > 0.03 else ('<span class="dn">▼</span>' if edge < -0.03 else "")
            return f'<div><span class="muted">{lbl}</span><b>{detail.odds[mk]:.2f}{arrow}</b></div>'
        st.markdown(f"""<div class="box"><h5>Cuotas · resultado final</h5><div class="s">▲ el modelo ve valor · ▼ cuota baja para su probabilidad</div>
          <div class="odds">{cell('1', '1')}{cell('X', 'X')}{cell('2', '2')}</div></div>""", unsafe_allow_html=True)

    for w in detail.warnings:
        st.caption(f"⚠️ {w}")

    t1, t2, t3, t4, t5 = st.tabs(["Pronóstico", "Estadísticas", "Clasificación", "Cuotas", "Simulador"])
    with t1:
        st.markdown(f'<div class="box ai">{ai_summary(m, pred)}</div>', unsafe_allow_html=True)
        if not done:
            st.markdown(f'<div class="box">{pick_html(pred, detail)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="kpis" style="margin-top:.8rem">' + "".join(
            f'<div class="kpi"><div class="l">{lbl}</div><div class="v">{v:.0%}</div><div class="t"><div style="width:{v*100:.0f}%"></div></div></div>'
            for lbl, v in [("+1.5 goles", pred.over15), ("+2.5 goles", pred.over25), ("+3.5 goles", pred.over35),
                           ("Ambos marcan", pred.btts)]) + "</div>", unsafe_allow_html=True)
        top = pred.top_scores[:6]
        mx = max((p for _, p in top), default=1) or 1
        st.markdown('<div class="box"><h5 style="margin-bottom:.6rem">Marcadores más probables</h5>' + "".join(
            f'<div class="scr{" top" if i == 0 else ""}"><b>{sc}</b><div class="t"><div style="width:{p/mx*100:.0f}%"></div></div>'
            f'<span class="muted" style="text-align:right">{p:.0%}</span></div>' for i, (sc, p) in enumerate(top)) + "</div>",
            unsafe_allow_html=True)
        if not done and st.button("💾 Guardar pronóstico en mi historial", width="stretch"):
            saved = history.save(m, pred, pred.best_bet)
            st.toast("Guardado ✅" if saved else "Ya lo tenías guardado con este marcador")

    with t2:
        h, a_ = detail.stats.get("home", {}), detail.stats.get("away", {})
        if not h and not a_ and not detail.events:
            empty("⏳", "Las estadísticas aparecen cuando empieza el partido.")
        else:
            rows = [("Posesión", "possession", True), ("Goles esperados (xG)", "xg", False), ("Tiros", "shots", False),
                    ("Tiros al arco", "shots_on_target", False), ("Córners", "corners", False), ("Faltas", "fouls", False),
                    ("Amarillas", "yellow", False), ("Rojas", "red", False)]
            st.markdown('<div class="box">' + "".join(stat_bar(lbl, h.get(k_), a_.get(k_), pct) for lbl, k_, pct in rows) + "</div>",
                        unsafe_allow_html=True)
            if detail.events:
                evs = sorted(detail.events, key=lambda e: (e["min"], e.get("extra") or 0), reverse=True)
                st.markdown('<div class="box"><h5 style="margin-bottom:.3rem">Minuto a minuto</h5>' +
                            "".join(event_html(e, m) for e in evs) + "</div>", unsafe_allow_html=True)

    with t3:
        groups, err = league_standings(api, m.get("league_id"), m.get("season"), m.get("source") == "demo")
        if err:
            st.caption(err)
        if groups:
            st.markdown(f'<div class="box" style="overflow-x:auto">{standings_html(groups, (m["home"], m["away"]))}</div>',
                        unsafe_allow_html=True)
        else:
            empty("📋", "Esta competición no tiene tabla de posiciones.")

    with t4:
        if not detail.odds:
            empty("💤", "No hay cuotas disponibles para este partido.")
        else:
            rows = [{"Mercado": v["market"], "Cuota": v["odd"], "Modelo": v["prob"] * 100, "Casa": v["implied"] * 100,
                     "Ventaja": v["edge"] * 100, "Valor": "✅" if v["edge"] >= 0.03 and v["prob"] >= 0.30 else ""}
                    for v in pred.value_bets]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
                "Cuota": st.column_config.NumberColumn(format="%.2f"),
                "Modelo": st.column_config.ProgressColumn("Prob. modelo", format="%.0f%%", min_value=0, max_value=100),
                "Casa": st.column_config.NumberColumn("Prob. casa", format="%.0f%%"),
                "Ventaja": st.column_config.NumberColumn(format="%+.1f%%")})
            st.caption("**Ventaja** = probabilidad del modelo × cuota − 1. Positiva = el modelo ve valor.")

    with t5:
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
        col = "var(--green2)" if ev > 0 else "var(--red)"
        st.markdown(f"""<div class="kpis">
          <div class="kpi"><div class="l">Prob. modelo</div><div class="v">{p:.1%}</div></div>
          <div class="kpi"><div class="l">Valor esperado</div><div class="v" style="color:{col}">{ev:+.1%}</div></div>
          <div class="kpi"><div class="l">Stake ¼ Kelly</div><div class="v">S/{stake:.2f}</div></div>
          <div class="kpi"><div class="l">Si acierta</div><div class="v">S/{stake * (odd - 1):.2f}</div></div></div>""",
                    unsafe_allow_html=True)
        if ev <= 0:
            st.caption("Con esta cuota la apuesta pierde a la larga según el modelo; por eso el stake sugerido es 0.")


def ai_summary(m, pred):
    if is_finished(m["status_short"]):
        return (f"Terminó <b>{escape(m['home'])} {m['home_goals']}-{m['away_goals']} {escape(m['away'])}</b>. "
                "Revisa en Historial si tu pronóstico acertó.")
    fav = max(pred.home_win, pred.draw, pred.away_win)
    lead = "El empate es lo más probable" if pred.winner == "Empate" else f"<b>{escape(pred.winner)}</b> es favorito"
    parts = [f"{lead} ({fav:.0%}). Marcador final más probable: <b>{pred.best_score}</b>.",
             f"Goles esperados en 90′: {escape(m['home'])} <b>{pred.lam_home:.2f}</b> · {escape(m['away'])} <b>{pred.lam_away:.2f}</b>.",
             f"<span class='muted'>{pred.data_quality}" + (" · " + " · ".join(escape(n) for n in pred.notes) if pred.notes else "") + "</span>"]
    return "<br>".join(parts)


def pick_html(pred, detail):
    bb = pred.best_bet
    if not bb:
        return ('<div class="pick"><div class="ic">🛑</div><div><div class="muted" style="font-size:.72rem;font-weight:700">RECOMENDACIÓN</div>'
                '<div class="v">No apostar</div><div class="muted" style="font-size:.8rem">Ningún mercado tiene suficiente probabilidad o valor.</div></div></div>')
    if bb["kind"] == "valor":
        return (f'<div class="pick"><div class="ic">🎯</div><div><div class="muted" style="font-size:.72rem;font-weight:700">APUESTA DE VALOR</div>'
                f'<div class="v">{bb["market"]} @ {bb["odd"]:.2f}</div><div class="muted" style="font-size:.8rem">Modelo {bb["prob"]:.0%} vs casa {1/bb["odd"]:.0%}</div></div>'
                f'<div class="e" style="color:var(--green2)">+{bb["edge"]:.0%}<div class="muted" style="font-size:.7rem">ventaja</div></div></div>')
    note = "Sin cuotas para medir valor." if not detail.odds else "La cuota actual no ofrece valor."
    return (f'<div class="pick"><div class="ic">📌</div><div><div class="muted" style="font-size:.72rem;font-weight:700">JUGADA MÁS PROBABLE</div>'
            f'<div class="v">{bb["market"]}</div><div class="muted" style="font-size:.8rem">{note}</div></div><div class="e">{bb["prob"]:.0%}</div></div>')


# ================= vista LIGAS =================
def view_leagues():
    items, notice = load_day()
    if notice:
        st.info(notice, icon="ℹ️")
    comps = {}
    for m in filter_matches(items, "Todas", search):
        lid = m.get("league_id") or m["league"]
        comps.setdefault(lid, {"m": m, "n": 0})["n"] += 1
    order = sorted(comps.values(), key=lambda c: (LEAGUE_PRIORITY.index(c["m"].get("league_id"))
                                                  if c["m"].get("league_id") in LEAGUE_PRIORITY else 99, c["m"]["league"]))
    if not order:
        empty("🏆", "No hay competiciones con partidos este día.")
        return
    ids = [c["m"].get("league_id") or c["m"]["league"] for c in order]
    if ss.league_pick not in ids:
        ss.league_pick = ids[0]

    left, right = st.columns([1, 2.2], gap="medium")
    with left:
        with st.container(key="pane_comps"):
            st.markdown(f"<div style='font-weight:800;margin-bottom:.4rem'>Competiciones · {day_label(day)}</div>", unsafe_allow_html=True)
            with st.container(height=760, border=False):
                for c in order:
                    m0 = c["m"]
                    lid = m0.get("league_id") or m0["league"]
                    with st.container(key=f"lg_{lid}"):
                        st.markdown(f"""<div class="litem{' sel' if lid == ss.league_pick else ''}"><img src="{L(m0.get('league_logo'), m0['league'])}">
                          <div><div class="nm">{escape(m0['league'])}</div><div class="ct">{escape(cname(m0))}</div></div>
                          <span class="n">{c['n']}</span></div>""", unsafe_allow_html=True)
                        if st.button("Ver", key=f"pick_{lid}"):
                            ss.league_pick = lid; st.rerun()
    with right:
        m0 = comps[ss.league_pick]["m"]
        with st.container(key="pane_league"):
            season = m0.get("season")
            st.markdown(f"""<div class="lpage"><img src="{L(m0.get('league_logo'), m0['league'])}"><div>
              <div class="nm">{escape(m0['league'])}</div><div class="ct">{('<img src="' + L(m0.get('flag'), m0.get('country') or '') + '">') if m0.get('flag') else ''}
              {escape(cname(m0))}{f' · Temporada {season}/{season + 1}' if season else ''}</div></div></div>""", unsafe_allow_html=True)
            t1, t2 = st.tabs(["Clasificación", f"Partidos · {day_label(day)}"])
            with t1:
                groups, err = league_standings(api, m0.get("league_id"), season, m0.get("source") == "demo")
                if err:
                    st.caption(err)
                if groups:
                    st.markdown(f'<div style="overflow-x:auto">{standings_html(groups)}</div>', unsafe_allow_html=True)
                else:
                    empty("📋", "Sin tabla de posiciones para esta competición.")
            with t2:
                ms = [m for m in items if (m.get("league_id") or m["league"]) == ss.league_pick]
                st.markdown("".join(match_row(m, False) for m in ms), unsafe_allow_html=True)


# ================= vista HISTORIAL =================
def view_history():
    s_ = history.summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Guardados", s_["total"])
    c2.metric("Resueltos", s_["settled"])
    c3.metric("Acierto", f"{s_['hit_rate']:.0%}" if s_["hit_rate"] is not None else "—")
    c4.metric("Unidades", f"{s_['units']:+.2f}" if s_["bets_with_odds"] else "—")
    df = history.recent(50)
    if df.empty:
        empty("📒", "Aún no guardas pronósticos.<br>Abre un partido y usa «Guardar pronóstico».")
        return
    df["Res."] = df["pick_won"].map({1: "✅", 0: "❌"}).fillna("⏳")
    df["Partido"] = df["home"] + " vs " + df["away"]
    show = df[["Res.", "ts", "league", "Partido", "score_at_pick", "pick_market", "pick_odd", "predicted_score", "final_score"]].rename(columns={
        "ts": "Fecha", "league": "Liga", "score_at_pick": "Al guardar", "pick_market": "Jugada", "pick_odd": "Cuota",
        "predicted_score": "Pronóstico", "final_score": "Final"})
    st.dataframe(show, hide_index=True, width="stretch")


# ================= router =================
def router():
    if section.endswith("Ligas"):
        view_leagues()
    elif section.endswith("Historial"):
        view_history()
    else:
        view_matches()


if ss.get("auto", True) and section.endswith("Partidos"):
    st.fragment(run_every=60)(router)()
else:
    router()

st.markdown('<div class="foot">ZOLA Elite · Las probabilidades son estimaciones, no garantías. Apuesta con responsabilidad · +18</div>',
            unsafe_allow_html=True)
