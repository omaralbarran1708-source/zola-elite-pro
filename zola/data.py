"""Capa de datos: une API-Football (o demo) con el modelo."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import demo
from .api import ApiError, FootballApi
from .model import LiveState, TeamForm
from .status import bucket_of, is_finished, is_live


@dataclass
class MatchDetail:
    home_form: TeamForm
    away_form: TeamForm
    events: list
    stats: dict
    odds: dict
    state: LiveState
    warnings: list = field(default_factory=list)


def norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return "".join(ch.lower() for ch in s if ch.isalnum() or ch.isspace()).strip()


def list_matches(api: FootballApi, view: str, day: date) -> tuple[list[dict], str | None]:
    """Devuelve (partidos, aviso). Sin API key usa demo."""
    if not api.enabled:
        def hhmm(m):
            k = m.get("kickoff") or ""
            return k[11:16] if len(k) >= 16 else "15:00"
        items = [{**m, "kickoff": f"{day.isoformat()}T{hhmm(m)}:00-05:00"} for m in demo.MATCHES]
        if view == "En vivo":
            items = [m for m in items if is_live(m["status_short"])]
        return items, "Modo demo: agrega tu API key de API-Football para ver partidos reales."
    try:
        items = api.fixtures(day.isoformat(), view == "En vivo")
    except ApiError as e:
        return [], f"No se pudo leer API-Football: {e}"
    except Exception as e:  # red, timeout, etc.
        return [], f"Error de conexión con API-Football: {e}"
    return items, None


def filter_matches(items: list[dict], bucket: str, search: str, hide_finished: bool = False) -> list[dict]:
    q = norm(search)
    out = []
    for m in items:
        if bucket not in bucket_of(m):
            continue
        if q and q not in norm(f"{m['league']} {m['country']} {m['home']} {m['away']}"):
            continue
        if hide_finished and is_finished(m["status_short"]):
            continue
        out.append(m)
    # en vivo primero, luego por hora, terminados al final
    def key(m):
        s = m["status_short"]
        return (0 if is_live(s) else (2 if is_finished(s) else 1), m.get("kickoff") or "", m["league"])
    return sorted(out, key=key)


def _red_cards(events: list, team: str) -> int:
    return sum(1 for e in events if e["team"] == team and e["type"] == "Card"
               and e["detail"] in {"Red Card", "Second Yellow card", "Second Yellow Card"})


def build_state(match: dict, events: list, stats: dict) -> LiveState:
    h, a = stats.get("home", {}), stats.get("away", {})
    return LiveState(
        minute=match.get("minute") or 0,
        status=match.get("status_short", "NS"),
        home_goals=match.get("home_goals") or 0,
        away_goals=match.get("away_goals") or 0,
        home_red=max(_red_cards(events, match["home"]), h.get("red") or 0),
        away_red=max(_red_cards(events, match["away"]), a.get("red") or 0),
        home_xg=h.get("xg"), away_xg=a.get("xg"),
        home_sot=h.get("shots_on_target"), away_sot=a.get("shots_on_target"),
    )


def match_detail(api: FootballApi, match: dict) -> MatchDetail:
    warnings = []
    if match.get("source") == "demo":
        fid = match["fixture_id"]
        events = demo.EVENTS.get(fid, [])
        stats = demo.STATS.get(fid, {"home": {}, "away": {}})
        return MatchDetail(
            home_form=demo.FORMS.get(match["home"], TeamForm()),
            away_form=demo.FORMS.get(match["away"], TeamForm()),
            events=events, stats=stats, odds=demo.ODDS.get(fid, {}),
            state=build_state(match, events, stats),
        )

    fid = match["fixture_id"]
    started = is_live(match["status_short"]) or is_finished(match["status_short"])

    def safe(fn, default, label):
        try:
            return fn()
        except Exception as e:
            warnings.append(f"{label}: {e}")
            return default

    league, season = match.get("league_id"), match.get("season")
    home_form = safe(lambda: api.team_form(match["home_id"], league, season), TeamForm(), "Stats local")
    away_form = safe(lambda: api.team_form(match["away_id"], league, season), TeamForm(), "Stats visita")
    events = safe(lambda: api.events(fid), [], "Eventos") if started else []
    stats = safe(lambda: api.statistics(fid), {"home": {}, "away": {}}, "Estadísticas") if started else {"home": {}, "away": {}}
    if is_live(match["status_short"]):
        odds = safe(lambda: api.live_odds(fid), {}, "Cuotas en vivo")
    elif is_finished(match["status_short"]):
        odds = {}
    else:
        odds = safe(lambda: api.odds(fid), {}, "Cuotas")
    return MatchDetail(home_form, away_form, events, stats, odds, build_state(match, events, stats), warnings)


def settle_history(history, matches: list[dict], api: FootballApi | None = None, max_lookups: int = 3) -> int:
    """Cierra predicciones cuyos partidos ya terminaron."""
    by_key = {m["match_key"]: m for m in matches}
    n = 0
    lookups = 0
    for row in history.pending():
        m = by_key.get(row["match_key"])
        if m is None and api and api.enabled and row.get("fixture_id") and not str(row["match_key"]).startswith("demo"):
            if lookups >= max_lookups:
                continue
            lookups += 1
            try:
                m = api.fixture(int(row["fixture_id"]))
            except Exception:
                m = None
        if m and is_finished(m["status_short"]):
            n += history.settle(row["match_key"], m["home_goals"], m["away_goals"])
    return n


def league_standings(api: FootballApi, league_id, season, demo_mode: bool) -> tuple[list, str | None]:
    if demo_mode:
        return demo.STANDINGS.get(league_id, []), None
    if not league_id or not season:
        return [], None
    try:
        return api.standings(int(league_id), int(season)), None
    except Exception as e:
        return [], f"Clasificación no disponible: {e}"
