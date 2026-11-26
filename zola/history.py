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
        _state["msg"] = "jugadores y estadios (Transfermarkt)"
        try:
            n += import_transfermarkt(log)
            st.kv_set("tm_done", {"ts": time.time()})
        except Exception as e:
            log(f"TM error {e}")
        _state["msg"] = "aprendiendo"
        learn_from_history(log)
        st.kv_set("history_import", {"ts": time.time(), "rows": n})
    finally:
        _state.update(running=False, msg="")


def start_background():
    threading.Thread(target=run_import, daemon=True).start()


# ---------------- consultas para la página ----------------
def code_for(league_id) -> str | None:
    if league_id in LEAGUE_CODES:
        return LEAGUE_CODES[league_id]
    if league_id in API_HIST_LEAGUES:
        return f"AF{league_id}"
    return None


def past_seasons(league_id, limit: int = 6) -> list[dict]:
    """Campeón, subcampeón y datos de cada temporada anterior (tabla calculada con los resultados)."""
    code = code_for(league_id)
    if not code:
        return []
    st = get_store()
    from .leagues import current_season, label
    cur = label(league_id, current_season(league_id))
    seasons = [r["season"] for r in st.q("SELECT DISTINCT season FROM history WHERE code=? ORDER BY season DESC", (code,))]
    out = []
    for s in [x for x in seasons if x != cur][:limit]:
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


# ---------------- API-Football (plan gratis: temporadas 2022–2024) ----------------
API_HIST_LEAGUES = (281, 13, 11)          # Liga 1 Perú, Libertadores, Sudamericana
API_HIST_SEASONS = (2024, 2023, 2022)
PS_INSERT = ("INSERT INTO players_season (league_id, season, player_id, name, club, club_logo, photo, goals, assists, games, "
             "minutes, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT (league_id, season, player_id) DO UPDATE SET "
             "goals=excluded.goals, assists=excluded.assists, games=excluded.games, minutes=excluded.minutes, club=excluded.club")


def import_api_history(api, log=print) -> int:
    """Liga 1 y copas sudamericanas de temporadas anteriores desde API-Football (pocas consultas, una sola vez)."""
    from .leagues import hist_code, label
    st, n = get_store(), 0
    done = st.kv_get("api_hist_done", {}) or {}
    for lid in API_HIST_LEAGUES:
        for season in API_HIST_SEASONS:
            k = f"{lid}:{season}"
            if done.get(k) or not api.enabled or (api.remaining is not None and api.remaining < 30):
                continue
            try:
                res = api.league_results(lid, season)
                rows = [(hist_code(lid), label(lid, season), r["date"].isoformat(), r["home"], r["away"], r["hg"], r["ag"],
                         None, None, None, None) for r in res]
                st.xmany(INSERT, rows)
                n += len(rows)
                try:
                    sc = api.topscorers(lid, season)
                    st.xmany(PS_INSERT, [(lid, label(lid, season), str(p.get("name")), p.get("name"), p.get("team"),
                                          p.get("team_logo"), p.get("photo"), p.get("goals") or 0, p.get("assists") or 0,
                                          p.get("games") or 0, None, "api") for p in sc])
                except Exception:
                    pass
                done[k] = len(rows)
                st.kv_set("api_hist_done", done)
                log(f"API {k}: {len(rows)}")
            except Exception as e:
                log(f"API {k}: {e}")
    return n


def backfill_dates(api, max_calls: int = 12, log=print) -> int:
    """Usa consultas sobrantes del día para traer resultados de días pasados de esta temporada (todas las ligas)."""
    from datetime import timedelta
    st = get_store()
    cur = st.kv_get("backfill_cursor") or (date.today() - timedelta(days=1)).isoformat()
    if st.kv_get("backfill_reset_v2") is None:        # corrige días saltados mientras la API estaba suspendida
        cur = (date.today() - timedelta(days=1)).isoformat()
        st.kv_set("backfill_reset_v2", True)
    d = date.fromisoformat(cur)
    stop = date(date.today().year, 1, 15)
    n = 0
    while n < max_calls and d >= stop and api.enabled and (api.remaining is None or api.remaining > 45):
        try:
            api.fixtures(d.isoformat(), False)
        except Exception as e:      # API caída o bloqueada: no avanzar, reintentar en la próxima hora
            log(f"backfill {d}: {e}")
            break
        n += 1
        d -= timedelta(days=1)
        st.kv_set("backfill_cursor", d.isoformat())
    return n


# ---------------- Transfermarkt (transfermarkt-datasets, actualizado semanal; congelado jul-2026) ----------------
TM_BASE = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/"
TM_COMPS = {"GB1": 39, "ES1": 140, "IT1": 135, "L1": 78, "FR1": 61, "NL1": 88, "PO1": 94, "BE1": 144, "TR1": 203,
            "SC1": 179, "CL": 2, "EL": 3, "UCOL": 848, "FIWC": 1, "GR1": 197, "DK1": 119, "RU1": 235, "UKR1": 333}


def _tm_csv(name: str):
    import gzip
    r = requests.get(TM_BASE + name, timeout=120, stream=True)
    r.raise_for_status()
    r.raw.decode_content = True
    return csv.DictReader(io.TextIOWrapper(gzip.GzipFile(fileobj=r.raw), encoding="utf-8"))


def import_transfermarkt(log=print, top: int = 30) -> int:
    st = get_store()
    clubs = {}
    for c in _tm_csv("clubs.csv.gz"):
        clubs[c.get("club_id")] = c.get("name") or c.get("club_code")
        lid = TM_COMPS.get(c.get("domestic_competition_id"))
        seats = c.get("stadium_seats")
        st.x("INSERT INTO clubs_info (club_id, name, league_id, stadium, seats, coach) VALUES (?,?,?,?,?,?) "
             "ON CONFLICT (club_id) DO UPDATE SET stadium=excluded.stadium, seats=excluded.seats, coach=excluded.coach",
             (c.get("club_id"), clubs[c.get("club_id")], lid, c.get("stadium_name"),
              int(float(seats)) if seats not in (None, "") else None, c.get("coach_name")))
    log(f"TM clubes: {len(clubs)}")
    agg: dict = {}
    for a in _tm_csv("appearances.csv.gz"):
        lid = TM_COMPS.get(a.get("competition_id"))
        if not lid or not a.get("date"):
            continue
        try:
            d = date.fromisoformat(a["date"][:10])
        except ValueError:
            continue
        from .leagues import label
        y = d.year if (d.month >= 7 or lid == 1) else d.year - 1
        k = (lid, label(lid, y) if lid != 1 else str(d.year), a.get("player_id"))
        e = agg.get(k)
        if e is None:
            e = agg[k] = [a.get("player_name"), clubs.get(a.get("player_club_id"), ""), 0, 0, 0, 0]
        e[2] += int(float(a.get("goals") or 0)); e[3] += int(float(a.get("assists") or 0))
        e[4] += 1; e[5] += int(float(a.get("minutes_played") or 0))
    by: dict = {}
    for (lid, season, pid), e in agg.items():
        by.setdefault((lid, season), []).append((pid, e))
    rows = []
    for (lid, season), lst in by.items():
        keep = {pid for pid, _ in sorted(lst, key=lambda x: -x[1][2])[:top]} | \
               {pid for pid, _ in sorted(lst, key=lambda x: -x[1][3])[:top]}
        for pid, e in lst:
            if pid in keep:
                rows.append((lid, season, f"tm{pid}", e[0], e[1], None, None, e[2], e[3], e[4], e[5], "transfermarkt"))
    for i in range(0, len(rows), 1000):
        st.xmany(PS_INSERT, rows[i:i + 1000])
    log(f"TM jugadores: {len(rows)}")
    return len(rows)


def scorers(league_id, season: str | None = None, order: str = "goals", limit: int = 15) -> dict:
    st = get_store()
    seasons_ = [r["season"] for r in st.q("SELECT DISTINCT season FROM players_season WHERE league_id=? ORDER BY season DESC",
                                          (league_id,))]
    if not seasons_:
        return {"seasons": [], "players": []}
    season = season if season in seasons_ else seasons_[0]
    col = "assists" if order == "assists" else "goals"
    rows = st.q(f"SELECT name, club, club_logo, photo, goals, assists, games, minutes FROM players_season "
                f"WHERE league_id=? AND season=? ORDER BY {col} DESC, goals DESC LIMIT ?", (league_id, season, limit))
    return {"seasons": seasons_, "season": season, "players": [
        {"name": r["name"], "team": r["club"], "team_logo": r["club_logo"], "photo": r["photo"], "goals": r["goals"],
         "assists": r["assists"], "games": r["games"], "minutes": r["minutes"]} for r in rows]}


def clubs_of(league_id) -> list[dict]:
    return get_store().q("SELECT name, stadium, seats, coach FROM clubs_info WHERE league_id=? ORDER BY seats DESC", (league_id,))


def ensure_transfermarkt(log=lambda *_: None) -> None:
    st = get_store()
    if st.ok and not st.kv_get("tm_done") and not _state["running"]:
        _state.update(running=True, msg="jugadores y estadios (Transfermarkt)")
        try:
            import_transfermarkt(log)
            st.kv_set("tm_done", {"ts": time.time()})
        except Exception as e:
            st.kv_set("tm_error", str(e))
        finally:
            _state.update(running=False, msg="")
