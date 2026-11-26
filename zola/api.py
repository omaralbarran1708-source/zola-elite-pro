"""Cliente de API-Football (v3) con caché persistente y normalización de datos.

Siguiendo la documentación oficial:
- `fixtures?ids=` trae en 1 consulta eventos, alineaciones, estadísticas y jugadores.
- Partidos en juego: 1 consulta por minuto; el resto: 1 al día.
- Los logos no gastan cuota, pero se recomienda guardarlos (lo hace zola.logos).
Cada respuesta se guarda en la base de datos: si la app se reinicia no se vuelve
a gastar la cuota, y si la API falla se usa el último dato guardado.
"""
from __future__ import annotations

import json
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests

from .model import TeamForm
from .store import get_store

BASE = "https://v3.football.api-sports.io"
TIMEZONE = "America/Lima"
BOOKMAKER_BET365 = 8
LIVE_STATUSES = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"}
DONE_STATUSES = {"FT", "AET", "PEN", "AWD", "WO"}


class ApiError(Exception):
    pass


class FootballApi:
    def __init__(self, key: str, session: requests.Session | None = None):
        self.key = (key or "").strip()
        self.session = session or requests.Session()
        self.remaining: int | None = None
        self.calls = 0
        self._mem: dict = {}

    @property
    def enabled(self) -> bool:
        return bool(self.key)

    def _get(self, path: str, **params) -> list:
        if not self.enabled:
            raise ApiError("Falta la API key de API-Football")
        r = self.session.get(f"{BASE}/{path}", headers={"x-apisports-key": self.key}, params=params, timeout=20)
        self.calls += 1
        rem = r.headers.get("x-ratelimit-requests-remaining")
        if rem is not None and rem.isdigit():
            self.remaining = int(rem)
        if r.status_code == 429:
            raise ApiError("Límite de consultas por minuto alcanzado; reintenta en un momento")
        if r.status_code != 200:
            raise ApiError(f"API-Football respondió {r.status_code}")
        data = r.json()
        errors = data.get("errors")
        if errors:
            msg = "; ".join(f"{v}" for v in (errors.values() if isinstance(errors, dict) else errors))
            raise ApiError(msg or "Error de API-Football")
        return data.get("response", [])

    def _budget_ttl(self, base: float) -> float:
        """Plan con pocas consultas (p. ej. 100/día): reparte lo que queda hasta medianoche."""
        if self.remaining is None or self.remaining > 1000:
            return base
        now = datetime.now()
        left = 86400 - (now.hour * 3600 + now.minute * 60 + now.second)
        spare = max(1.0, self.remaining * 0.5)          # guarda la mitad para detalles y cuotas
        return min(3600.0, max(base, left / spare))

    def _fetch(self, path: str, ttl: float, **params) -> list:
        """Consulta con caché en memoria + base de datos. Si la API falla, devuelve lo último guardado."""
        key = path + "?" + json.dumps(params, sort_keys=True)
        now = time.time()
        hit = self._mem.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
        st = get_store()
        blocked = st.cache_get("blocked:" + key, 24 * 3600)
        if blocked is not None:      # el plan no permite esta consulta: no gastar llamadas
            stale = st.cache_get(key, 10 ** 12)
            if stale is not None:
                return stale
            raise ApiError(blocked)
        cached = st.cache_get(key, ttl)
        if cached is not None:
            self._mem[key] = (now, cached)
            return cached
        try:
            data = self._get(path, **params)
        except ApiError as e:
            if any(w in str(e).lower() for w in ("plan", "access", "not have")):
                st.cache_put("blocked:" + key, str(e))
            stale = st.cache_get(key, 10 ** 12)
            if stale is not None:
                return stale
            raise
        self._mem[key] = (now, data)
        st.cache_put(key, data)
        return data

    # ---------- partidos ----------
    def fixtures(self, date_str: str, live: bool) -> list[dict]:
        if live:
            res = self._fetch("fixtures", self._budget_ttl(45), live="all", timezone=TIMEZONE)
        else:
            today = datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()
            ttl = self._budget_ttl(60) if date_str == today else (6 * 3600 if date_str < today else 3 * 3600)
            res = self._fetch("fixtures", ttl, date=date_str, timezone=TIMEZONE)
        items = [normalize_fixture(x) for x in res]
        get_store().upsert_fixtures(items)
        return items

    def detail(self, fixture_id: int, status_hint: str = "NS") -> dict:
        """Partido completo en 1 consulta: datos, eventos, estadísticas, alineaciones y jugadores."""
        ttl = self._budget_ttl(45) if status_hint in LIVE_STATUSES else (30 * 86400 if status_hint in DONE_STATUSES else 3600)
        res = self._fetch("fixtures", ttl, id=str(fixture_id), timezone=TIMEZONE)
        if not res:
            return {}
        item = res[0]
        fx = normalize_fixture(item)
        get_store().upsert_fixtures([fx])
        return {
            "fixture": fx,
            "events": [normalize_event(e) for e in item.get("events") or []],
            "stats": normalize_statistics(item.get("statistics") or []),
            "lineups": normalize_lineups(item.get("lineups") or []),
        }

    def fixture(self, fixture_id: int) -> dict | None:
        d = self.detail(fixture_id, "LIVE")
        return d.get("fixture") if d else None

    def events(self, fixture_id: int) -> list[dict]:
        return self.detail(fixture_id, "LIVE").get("events", [])

    def statistics(self, fixture_id: int) -> dict:
        return self.detail(fixture_id, "LIVE").get("stats", {"home": {}, "away": {}})

    def team_form(self, team_id: int, league_id: int, season: int) -> TeamForm:
        return normalize_team_stats(self._fetch("teams/statistics", 12 * 3600, team=team_id, league=league_id, season=season))

    def standings(self, league_id: int, season: int) -> list[dict]:
        return normalize_standings(self._fetch("standings", 3 * 3600, league=league_id, season=season))

    def odds(self, fixture_id: int) -> dict:
        res = self._fetch("odds", 3600, fixture=fixture_id, bookmaker=BOOKMAKER_BET365)
        if not res:
            res = self._fetch("odds", 3600, fixture=fixture_id)
        return parse_prematch_odds(res)

    def live_odds(self, fixture_id: int) -> dict:
        return parse_live_odds(self._fetch("odds/live", self._budget_ttl(60), fixture=fixture_id))

    def league_results(self, league_id: int, season: int) -> list[dict]:
        """Resultados terminados de la temporada (1 consulta para toda la liga, cada 6 h)."""
        res = self._fetch("fixtures", 6 * 3600, league=league_id, season=season, status="FT-AET-PEN", timezone=TIMEZONE)
        items = [normalize_fixture(x) for x in res]
        get_store().upsert_fixtures(items)
        out = []
        for f in items:
            try:
                d = date.fromisoformat((f["kickoff"] or "")[:10])
            except ValueError:
                continue
            out.append({"date": d, "home": f["home"], "away": f["away"], "hg": f["home_goals"], "ag": f["away_goals"]})
        return out

    def head_to_head(self, home_id: int, away_id: int) -> list[dict]:
        res = self._fetch("fixtures/headtohead", 24 * 3600, h2h=f"{home_id}-{away_id}", last=6, timezone=TIMEZONE)
        return [normalize_fixture(x) for x in res]

    def fixtures_by_ids(self, ids: tuple) -> list[dict]:
        res = self._fetch("fixtures", 120, ids="-".join(str(i) for i in ids), timezone=TIMEZONE)
        items = [normalize_fixture(x) for x in res]
        get_store().upsert_fixtures(items)
        return items

    def topscorers(self, league_id: int, season: int) -> list[dict]:
        return normalize_topscorers(self._fetch("players/topscorers", 12 * 3600, league=league_id, season=season))


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


def normalize_lineups(res: list) -> list[dict]:
    out = []
    for t in res[:2]:
        team = t.get("team") or {}
        colors = (team.get("colors") or {}).get("player") or {}
        def players(lst):
            ps = []
            for x in lst or []:
                p = x.get("player") or {}
                ps.append({"id": p.get("id"), "name": p.get("name") or "", "number": p.get("number"),
                           "pos": p.get("pos") or "", "grid": p.get("grid")})
            return ps
        out.append({"team": team.get("name", ""), "team_id": team.get("id"), "logo": team.get("logo"),
                    "formation": t.get("formation") or "", "coach": (t.get("coach") or {}).get("name") or "",
                    "color": ("#" + colors["primary"]) if colors.get("primary") else None,
                    "number_color": ("#" + colors["number"]) if colors.get("number") else None,
                    "start": players(t.get("startXI")), "subs": players(t.get("substitutes"))})
    return out


def normalize_topscorers(res: list) -> list[dict]:
    out = []
    for x in res[:20]:
        p = x.get("player") or {}
        st = (x.get("statistics") or [{}])[0]
        out.append({"name": p.get("name", ""), "photo": p.get("photo"), "team": (st.get("team") or {}).get("name", ""),
                    "team_logo": (st.get("team") or {}).get("logo"), "goals": (st.get("goals") or {}).get("total") or 0,
                    "assists": (st.get("goals") or {}).get("assists") or 0,
                    "games": (st.get("games") or {}).get("appearences") or 0})
    return out
