"""Cliente de API-Football (v3) con caché en memoria y normalización de datos.

El plan gratis de API-Football da ~100 solicitudes al día, así que todo se
cachea: partidos 60 s, eventos/estadísticas 45 s en vivo, estadísticas de
temporada de cada equipo 12 h.
"""
from __future__ import annotations

import time
from functools import wraps

import requests

from .model import TeamForm

BASE = "https://v3.football.api-sports.io"
TIMEZONE = "America/Lima"
BOOKMAKER_BET365 = 8


class ApiError(Exception):
    pass


def ttl_cache(seconds: int):
    def deco(fn):
        store: dict = {}

        @wraps(fn)
        def wrapper(self, *args):
            key = (self.key, args)
            hit = store.get(key)
            now = time.time()
            if hit and now - hit[0] < seconds:
                return hit[1]
            val = fn(self, *args)
            store[key] = (now, val)
            return val

        wrapper.cache_clear = store.clear
        return wrapper
    return deco


class FootballApi:
    def __init__(self, key: str, session: requests.Session | None = None):
        self.key = (key or "").strip()
        self.session = session or requests.Session()
        self.remaining: int | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.key)

    def _get(self, path: str, **params) -> list:
        if not self.enabled:
            raise ApiError("Falta la API key de API-Football")
        r = self.session.get(f"{BASE}/{path}", headers={"x-apisports-key": self.key},
                             params=params, timeout=20)
        rem = r.headers.get("x-ratelimit-requests-remaining")
        if rem is not None and rem.isdigit():
            self.remaining = int(rem)
        if r.status_code != 200:
            raise ApiError(f"API-Football respondió {r.status_code}")
        data = r.json()
        errors = data.get("errors")
        if errors:
            msg = "; ".join(f"{v}" for v in (errors.values() if isinstance(errors, dict) else errors))
            raise ApiError(msg or "Error de API-Football")
        return data.get("response", [])

    # ---------- partidos ----------
    @ttl_cache(60)
    def fixtures(self, date_str: str, live: bool) -> list[dict]:
        params = {"timezone": TIMEZONE}
        if live:
            params["live"] = "all"
        else:
            params["date"] = date_str
        return [normalize_fixture(x) for x in self._get("fixtures", **params)]

    @ttl_cache(45)
    def fixture(self, fixture_id: int) -> dict | None:
        res = self._get("fixtures", id=fixture_id, timezone=TIMEZONE)
        return normalize_fixture(res[0]) if res else None

    @ttl_cache(45)
    def events(self, fixture_id: int) -> list[dict]:
        return [normalize_event(e) for e in self._get("fixtures/events", fixture=fixture_id)]

    @ttl_cache(45)
    def statistics(self, fixture_id: int) -> dict:
        return normalize_statistics(self._get("fixtures/statistics", fixture=fixture_id))

    @ttl_cache(12 * 3600)
    def team_form(self, team_id: int, league_id: int, season: int) -> TeamForm:
        res = self._get("teams/statistics", team=team_id, league=league_id, season=season)
        return normalize_team_stats(res)

    @ttl_cache(3600)
    def standings(self, league_id: int, season: int) -> list[dict]:
        return normalize_standings(self._get("standings", league=league_id, season=season))

    @ttl_cache(10 * 60)
    def odds(self, fixture_id: int) -> dict:
        res = self._get("odds", fixture=fixture_id, bookmaker=BOOKMAKER_BET365)
        if not res:
            res = self._get("odds", fixture=fixture_id)
        return parse_prematch_odds(res)

    @ttl_cache(3600)
    def standings(self, league_id: int, season: int) -> list[dict]:
        return normalize_standings(self._get("standings", league=league_id, season=season))

    @ttl_cache(60)
    def live_odds(self, fixture_id: int) -> dict:
        return parse_live_odds(self._get("odds/live", fixture=fixture_id))


# ---------- normalizadores (puros, testeables) ----------

def normalize_fixture(item: dict) -> dict:
    fx = item.get("fixture", {}) or {}
    teams = item.get("teams", {}) or {}
    league = item.get("league", {}) or {}
    goals = item.get("goals", {}) or {}
    status = fx.get("status", {}) or {}
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}
    return {
        "match_key": f"af_{fx.get('id')}",
        "fixture_id": fx.get("id"),
        "kickoff": fx.get("date"),
        "league": league.get("name", "Sin liga"),
        "league_id": league.get("id"),
        "season": league.get("season"),
        "round": league.get("round", ""),
        "country": league.get("country", ""),
        "league_logo": league.get("logo"),
        "flag": league.get("flag"),
        "home": home.get("name", "Local"),
        "away": away.get("name", "Visita"),
        "home_id": home.get("id"),
        "away_id": away.get("id"),
        "home_logo": home.get("logo"),
        "away_logo": away.get("logo"),
        "home_goals": goals.get("home") or 0,
        "away_goals": goals.get("away") or 0,
        "minute": status.get("elapsed") or 0,
        "extra": status.get("extra") or 0,
        "status_short": status.get("short", "NS"),
        "venue": (fx.get("venue") or {}).get("name", "") or "",
        "source": "api_football",
    }


def normalize_event(e: dict) -> dict:
    t = e.get("time", {}) or {}
    return {
        "min": t.get("elapsed") or 0,
        "extra": t.get("extra") or 0,
        "team": (e.get("team") or {}).get("name", ""),
        "team_id": (e.get("team") or {}).get("id"),
        "player": (e.get("player") or {}).get("name") or "",
        "assist": (e.get("assist") or {}).get("name") or "",
        "type": e.get("type", ""),
        "detail": e.get("detail", ""),
    }


STAT_KEYS = {
    "Ball Possession": "possession",
    "Total Shots": "shots",
    "Shots on Goal": "shots_on_target",
    "Corner Kicks": "corners",
    "Fouls": "fouls",
    "Yellow Cards": "yellow",
    "Red Cards": "red",
    "expected_goals": "xg",
    "Passes %": "pass_acc",
    "Goalkeeper Saves": "saves",
}


def _num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip().replace("%", "")
    try:
        return float(s) if "." in s else int(s)
    except ValueError:
        return None


def normalize_statistics(res: list) -> dict:
    out = {"home": {}, "away": {}}
    for side, block in zip(("home", "away"), res[:2]):
        for s in block.get("statistics", []) or []:
            key = STAT_KEYS.get(s.get("type"))
            if key:
                out[side][key] = _num(s.get("value"))
    return out


def _avg(goals: dict, kind: str, where: str):
    try:
        v = goals[kind]["average"][where]
        return float(v) if v not in (None, "") else None
    except (KeyError, TypeError, ValueError):
        return None


def normalize_team_stats(res) -> TeamForm:
    if not res:
        return TeamForm()
    data = res if isinstance(res, dict) else res[0]
    played = (data.get("fixtures") or {}).get("played") or {}
    goals = data.get("goals") or {}
    return TeamForm(
        gf_home=_avg(goals, "for", "home"), ga_home=_avg(goals, "against", "home"),
        gp_home=played.get("home") or 0,
        gf_away=_avg(goals, "for", "away"), ga_away=_avg(goals, "against", "away"),
        gp_away=played.get("away") or 0,
        form=data.get("form") or "",
    )


def _map_value(bet_name: str, value: str, handicap=None) -> str | None:
    name = (bet_name or "").lower()
    v = str(value)
    if name in {"match winner", "fulltime result", "1x2"}:
        return {"Home": "1", "Draw": "X", "Away": "2"}.get(v)
    if name in {"double chance"}:
        return {"Home/Draw": "1X", "Draw/Away": "X2", "Home/Away": "12"}.get(v)
    if name in {"goals over/under", "over/under", "match goals"}:
        line = f"{v} {handicap}".strip() if handicap else v
        parts = line.split()
        if len(parts) == 2 and parts[0] in {"Over", "Under"} and parts[1] in {"1.5", "2.5", "3.5"}:
            return f"{parts[0]} {parts[1]}"
    if name in {"both teams score", "both teams to score"}:
        return {"Yes": "BTTS Sí", "No": "BTTS No"}.get(v)
    return None


def parse_prematch_odds(res: list) -> dict:
    out: dict = {}
    for item in res or []:
        for bm in item.get("bookmakers", []) or []:
            for bet in bm.get("bets", []) or []:
                for val in bet.get("values", []) or []:
                    mk = _map_value(bet.get("name"), val.get("value"))
                    odd = _num(val.get("odd"))
                    if mk and odd and mk not in out:
                        out[mk] = float(odd)
            if out:
                return out
    return out


def parse_live_odds(res: list) -> dict:
    out: dict = {}
    for item in res or []:
        for bet in item.get("odds", []) or []:
            for val in bet.get("values", []) or []:
                if val.get("suspended"):
                    continue
                mk = _map_value(bet.get("name"), val.get("value"), val.get("handicap"))
                odd = _num(val.get("odd"))
                if mk and odd and mk not in out:
                    out[mk] = float(odd)
    return out


def zone_of(description: str | None) -> str:
    """Clasifica la zona de la tabla según la descripción de API-Football."""
    d = (description or "").lower()
    if not d:
        return ""
    if "relegation" in d or "descenso" in d:
        return "rel"
    if "champions league" in d or "libertadores" in d:
        return "ucl"
    if "europa league" in d or "sudamericana" in d:
        return "uel"
    if "conference" in d:
        return "uecl"
    if "play" in d:
        return "po"
    if "promotion" in d or "next round" in d or "final" in d:
        return "up"
    return "oth"


def normalize_standings(res: list) -> list[dict]:
    """Devuelve una lista de grupos: [{"name", "rows": [...]}]."""
    groups = []
    for item in res or []:
        for table in (item.get("league") or {}).get("standings") or []:
            rows = []
            for r in table:
                al = r.get("all") or {}
                g = al.get("goals") or {}
                rows.append({
                    "rank": r.get("rank"), "team": (r.get("team") or {}).get("name", ""),
                    "team_id": (r.get("team") or {}).get("id"), "logo": (r.get("team") or {}).get("logo"),
                    "played": al.get("played") or 0, "win": al.get("win") or 0, "draw": al.get("draw") or 0,
                    "lose": al.get("lose") or 0, "gf": g.get("for") or 0, "ga": g.get("against") or 0,
                    "diff": r.get("goalsDiff") or 0, "points": r.get("points") or 0,
                    "form": r.get("form") or "", "description": r.get("description") or "",
                    "zone": zone_of(r.get("description")), "group": r.get("group") or "",
                })
            if rows:
                groups.append({"name": rows[0]["group"], "rows": rows})
    return groups


def normalize_standings(res: list) -> list[dict]:
    """Lista de grupos: [{"name": str, "rows": [...]}]."""
    groups = []
    for item in res or []:
        for table in (item.get("league") or {}).get("standings") or []:
            rows = []
            for r in table:
                al = r.get("all") or {}
                g = al.get("goals") or {}
                team = r.get("team") or {}
                rows.append({
                    "rank": r.get("rank"), "team": team.get("name", ""), "team_id": team.get("id"),
                    "logo": team.get("logo"), "played": al.get("played") or 0, "win": al.get("win") or 0,
                    "draw": al.get("draw") or 0, "lose": al.get("lose") or 0,
                    "gf": g.get("for") or 0, "ga": g.get("against") or 0,
                    "diff": r.get("goalsDiff") or 0, "points": r.get("points") or 0,
                    "form": r.get("form") or "", "zone": r.get("description") or "",
                })
            if rows:
                groups.append({"name": (table[0].get("group") or ""), "rows": rows})
    return groups
