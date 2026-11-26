"""Historial de años anteriores para alimentar la página y que ZOLA aprenda.

Fuentes gratis y abiertas:
- football-data.co.uk: resultados + cuotas de cierre de 19 ligas (temporadas pasadas).
- martj42/international_results (GitHub, CC0): todos los partidos de selecciones desde 1872.
Se guardan en la tabla `history` (Neon) una vez por semana. Con eso:
- el modelo aprende cuánto confiar en el mercado por liga (prueba temporada por temporada),
- se arman campeones y tablas de temporadas anteriores,
- cara a cara sin gastar consultas de la API,
- ratings de selecciones (Mundial, Eliminatorias, Copa América, amistosos).
"""
from __future__ import annotations

import csv
import io
import threading
import time
from datetime import date

import requests

from . import backtest as bt
from .fdco import LEAGUE_CODES, match_name
from .ratings import fit
from .store import get_store

INT_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
SCORERS_URL = "https://raw.githubusercontent.com/martj42/international_results/master/goalscorers.csv"
PAST_SEASONS = 6          # ligas europeas
EXTRA_FROM = 2018         # ligas de un solo archivo (Brasil, Argentina, MLS…)
INT_FROM = "2006-01-01"   # selecciones
REFRESH = 7 * 86400
_state = {"running": False, "msg": ""}
INSERT = ("INSERT INTO history (code, season, day, home, away, hg, ag, oh, od, oa, tournament) "
          "VALUES (?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT (code, day, home, away) DO UPDATE SET "
          "hg=excluded.hg, ag=excluded.ag, oh=excluded.oh, od=excluded.od, oa=excluded.oa")


def _season_label(code: str, d: date) -> str:
    if code in bt.EXTRA_LEAGUES:
        return str(d.year)
    y = d.year if d.month >= 7 else d.year - 1
    return f"{y}/{(y + 1) % 100:02d}"


def _rows_from_csv(code: str, text: str) -> list[tuple]:
    out = []
    for r in bt.parse_csv(text):
        if code in bt.EXTRA_LEAGUES and r["date"].year < EXTRA_FROM:
            continue
        o = r["odds"] or [None, None, None]
        out.append((code, _season_label(code, r["date"]), r["date"].isoformat(), r["home"], r["away"],
                    r["hg"], r["ag"], o[0], o[1], o[2], None))
    return out


def import_leagues(log=print) -> int:
    st, n = get_store(), 0
    today = date.today()
    for code in list(bt.MAIN_LEAGUES) + list(bt.EXTRA_LEAGUES):
        seasons = bt.seasons_for(code, today)
        if code in bt.MAIN_LEAGUES:
            start = today.year if today.month >= 7 else today.year - 1
            seasons = [f"{y % 100:02d}{(y + 1) % 100:02d}" for y in range(start, start - PAST_SEASONS, -1)]
        else:
            seasons = seasons[:1]      # un archivo con todas las temporadas
        for s in seasons:
            try:
                rows = _rows_from_csv(code, bt.fetch_csv(code, s))
                st.xmany(INSERT, rows)
                n += len(rows)
                log(f"{code} {s}: {len(rows)}")
            except Exception as e:
                log(f"{code} {s}: error {e}")
    return n


def import_internationals(log=print) -> int:
    r = requests.get(INT_URL, timeout=40)
    rows = []
    for x in csv.DictReader(io.StringIO(r.text)):
        if x["date"] < INT_FROM or x.get("home_score") in ("", "NA", None):
            continue
        try:
            hg, ag = int(x["home_score"]), int(x["away_score"])
        except ValueError:
            continue
        rows.append(("INT", x["date"][:4], x["date"], x["home_team"], x["away_team"], hg, ag, None, None, None,
                     x.get("tournament")))
    st = get_store()
    for i in range(0, len(rows), 1000):
        st.xmany(INSERT, rows[i:i + 1000])
    log(f"INT: {len(rows)}")
    return len(rows)


def learn_from_history(log=print) -> dict:
    """Prueba el modelo en las 2 últimas temporadas completas de cada liga y guarda el peso del mercado aprendido."""
    st, out = get_store(), {}
    for code in bt.MAIN_LEAGUES:
        seasons = [r["season"] for r in st.q("SELECT DISTINCT season FROM history WHERE code=? ORDER BY season DESC", (code,))]
        ws, stats = [], []
        for s in seasons[1:3]:   # [0] es la temporada en curso
            rows = league_rows(code, s, with_odds=True)
            try:
                res = bt.run_backtest(rows, auto=True)
            except Exception:
                continue
            if res.get("risk"):
                ws.append(res["risk"]["weight"])
                stats.append({"season": s, "n": res["evaluated"], "model": res["systems"]["model"],
                              "market": res["systems"]["market"], "blend": res["systems"]["blend"]})
        if ws:
            out[code] = {"weight": round(sum(ws) / len(ws), 2), "seasons": stats}
            log(f"aprendido {code}: {out[code]['weight']}")
    if out:
        st.kv_set("history_learning", out)
    return out


def league_rows(code: str, season: str, with_odds: bool = False) -> list[dict]:
    rows = get_store().q("SELECT day, home, away, hg, ag, oh, od, oa FROM history WHERE code=? AND season=? ORDER BY day",
                         (code, season))
    out = []
    for r in rows:
        odds = [r["oh"], r["od"], r["oa"]] if r["oh"] and r["od"] and r["oa"] else None
        out.append({"date": date.fromisoformat(r["day"]), "home": r["home"], "away": r["away"], "hg": r["hg"],
                    "ag": r["ag"], "odds": odds, "odds_src": "hist" if odds else None, "ou": None})
    return out


def run_import(force: bool = False, log=lambda *_: None) -> None:
    st = get_store()
    if _state["running"] or not st.ok:
        return
    info = st.kv_get("history_import", {}) or {}
    if not force and time.time() - info.get("ts", 0) < REFRESH:
        return
    _state["running"] = True
    try:
        _state["msg"] = "importando ligas"
        n = import_leagues(log)
        _state["msg"] = "importando selecciones"
        try:
            n += import_internationals(log)
        except Exception as e:
            log(f"INT error {e}")
        _state["msg"] = "aprendiendo"
        learn_from_history(log)
        st.kv_set("history_import", {"ts": time.time(), "rows": n})
    finally:
        _state.update(running=False, msg="")


def start_background():
    threading.Thread(target=run_import, daemon=True).start()


# ---------------- consultas para la página ----------------
def code_for(league_id) -> str | None:
    return LEAGUE_CODES.get(league_id)


def past_seasons(league_id, limit: int = 6) -> list[dict]:
    """Campeón, subcampeón y datos de cada temporada anterior (tabla calculada con los resultados)."""
    code = code_for(league_id)
    if not code:
        return []
    st = get_store()
    seasons = [r["season"] for r in st.q("SELECT DISTINCT season FROM history WHERE code=? ORDER BY season DESC", (code,))]
    out = []
    for s in seasons[1:limit + 1]:
        rows = st.q("SELECT home, away, hg, ag FROM history WHERE code=? AND season=?", (code, s))
        if len(rows) < 50:
            continue
        tb: dict = {}
        for r in rows:
            for t, gf, ga in ((r["home"], r["hg"], r["ag"]), (r["away"], r["ag"], r["hg"])):
                e = tb.setdefault(t, {"team": t, "pj": 0, "pts": 0, "gf": 0, "gc": 0, "g": 0})
                e["pj"] += 1; e["gf"] += gf; e["gc"] += ga
                e["pts"] += 3 if gf > ga else (1 if gf == ga else 0); e["g"] += int(gf > ga)
        table = sorted(tb.values(), key=lambda e: (-e["pts"], -(e["gf"] - e["gc"]), -e["gf"]))
        goals = sum(r["hg"] + r["ag"] for r in rows)
        out.append({"season": s, "champion": table[0], "runner_up": table[1], "last": table[-1],
                    "top_attack": max(table, key=lambda e: e["gf"]), "matches": len(rows),
                    "goals_avg": round(goals / len(rows), 2),
                    "home_win": round(sum(r["hg"] > r["ag"] for r in rows) / len(rows), 3),
                    "table": table[:6]})
    return out


def h2h(league_id, home: str, away: str, limit: int = 8) -> list[dict]:
    """Últimos cruces entre dos equipos en el historial guardado (sin gastar la API)."""
    st = get_store()
    codes = [code_for(league_id)] if code_for(league_id) else []
    codes.append("INT")
    for code in codes:
        names = [r["t"] for r in st.q("SELECT DISTINCT home AS t FROM history WHERE code=?", (code,))]
        h, a = match_name(home, names), match_name(away, names)
        if not h or not a or h == a:
            continue
        rows = st.q("""SELECT day, home, away, hg, ag, tournament FROM history WHERE code=? AND
                       ((home=? AND away=?) OR (home=? AND away=?)) ORDER BY day DESC LIMIT ?""",
                    (code, h, a, a, h, limit))
        ren = {h: home, a: away}
        return [{"date": r["day"], "home": ren.get(r["home"], r["home"]), "away": ren.get(r["away"], r["away"]),
                 "home_goals": r["hg"], "away_goals": r["ag"], "league": r["tournament"] or "",
                 "source": "historial"} for r in rows]
    return []


_INT_CACHE: dict = {}


def national_ratings():
    """Ratings de selecciones (últimos 4 años, con decaimiento de 1 año)."""
    hit = _INT_CACHE.get("r")
    if hit and time.time() - hit[0] < 12 * 3600:
        return hit[1]
    since = date(date.today().year - 4, 1, 1).isoformat()
    rows = get_store().q("SELECT day, home, away, hg, ag FROM history WHERE code='INT' AND day>=?", (since,))
    if len(rows) < 200:
        return None
    r = fit([(date.fromisoformat(x["day"]), x["home"], x["away"], x["hg"], x["ag"]) for x in rows], half_life=365)
    _INT_CACHE["r"] = (time.time(), r)
    return r


def national_lambdas(home: str, away: str):
    r = national_ratings()
    if not r:
        return None
    names = list(r.attack)
    h, a = match_name(home, names), match_name(away, names)
    if not h or not a or h == a or not (r.has(h, 5) and r.has(a, 5)):
        return None
    return r.lambdas(h, a), r.rho, r.n_matches


def status() -> dict:
    st = get_store()
    info = st.kv_get("history_import", {}) or {}
    try:
        counts = {r["code"]: int(r["n"]) for r in st.q("SELECT code, COUNT(*) AS n FROM history GROUP BY code")}
    except Exception:
        counts = {}
    return {"rows": sum(counts.values()), "by_code": counts, "last_import": info.get("ts"),
            "running": _state["running"], "step": _state["msg"],
            "learned": st.kv_get("history_learning", {}) or {}}
