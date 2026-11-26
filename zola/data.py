"""Capa de datos: une API-Football (o demo) con el modelo."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from . import demo, fdco, strength
from .api import ApiError, FootballApi
from .model import LiveState, TeamForm
from .ratings import Ratings, fit
from .store import get_store
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
    lambdas: tuple | None = None
    rho: float | None = None
    source: str = ""
    ratings_info: dict | None = None
    lineups: list = field(default_factory=list)


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
        return items, None
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
            state=build_state(match, events, stats), lineups=demo.LINEUPS.get(fid, []),
        )

    fid = match["fixture_id"]
    started = is_live(match["status_short"]) or is_finished(match["status_short"])

    def safe(fn, default, label):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            if "plan" in msg.lower() or "access" in msg.lower():
                msg = "no incluido en el plan gratis de la API"
            warnings.append(f"{label}: {msg}")
            return default

    league, season = match.get("league_id"), match.get("season")
    results = safe(lambda: api.league_results(league, season), [], "Resultados de la liga") if league and season else []
    results = merge_results(results, get_store().league_results(league, season))
    if len(results) < 40 and league in fdco.LEAGUE_CODES:     # plan gratis: temporada actual desde football-data
        try:
            ko = date.fromisoformat((match.get("kickoff") or "")[:10])
        except ValueError:
            ko = date.today()
        alt = fdco.results_for_match(league, match["home"], match["away"], ko)
        if len(alt) > len(results):
            results = alt
            warnings = [w for w in warnings if not w.startswith("Resultados de la liga")]
    ratings = ratings_for(league, season, results)
    lambdas = rho = None
    source = ""
    info = None
    if ratings.has(match["home"], 4) and ratings.has(match["away"], 4):
        lambdas, rho = ratings.lambdas(match["home"], match["away"]), ratings.rho
        source = f"Ratings de la temporada ({ratings.n_matches} partidos)"
        info = ratings_info(ratings, match["home"], match["away"])
        home_form = form_from_results(results, match["home"])
        away_form = form_from_results(results, match["away"])
    else:
        home_form = safe(lambda: api.team_form(match["home_id"], league, season), TeamForm(), "Stats local")
        away_form = safe(lambda: api.team_form(match["away_id"], league, season), TeamForm(), "Stats visita")
    events, stats, lineups = [], {"home": {}, "away": {}}, []
    soon = False
    try:
        ko = datetime.fromisoformat(match.get("kickoff") or "")
        soon = (ko - datetime.now(ko.tzinfo)).total_seconds() < 90 * 60
    except (TypeError, ValueError):
        pass
    if started or soon:   # 1 sola consulta: eventos + estadísticas + alineaciones
        det = safe(lambda: api.detail(fid, match["status_short"]), {}, "Detalle del partido")
        events, lineups = det.get("events", []), det.get("lineups", [])
        stats = det.get("stats") or stats
    if is_live(match["status_short"]):
        odds = safe(lambda: api.live_odds(fid), {}, "Cuotas en vivo")
    elif is_finished(match["status_short"]):
        odds = {}
    else:
        odds = safe(lambda: api.odds(fid), {}, "Cuotas")
    if lambdas is None:   # sin historial: Elo (ClubElo) y, si no, goles deducidos de las cuotas
        try:
            intl = not strength.COUNTRY.get(match.get("country") or "")
            eh = strength.elo_of(match["home"], None if intl else match.get("country"))
            ea = strength.elo_of(match["away"], None if intl else match.get("country"))
            if eh and ea:
                lambdas = strength.elo_lambdas(eh, ea)
                source = f"Rating Elo (ClubElo: {eh:.0f} vs {ea:.0f})"
        except Exception:
            pass
    if lambdas is None and odds and not is_live(match["status_short"]):
        imp = strength.implied_lambdas(odds)
        if imp:
            lambdas, source = imp, "Goles esperados deducidos de las cuotas"
    if lambdas is not None:
        warnings = [w for w in warnings if not w.startswith(("Stats local", "Stats visita", "Resultados de la liga"))]
    return MatchDetail(home_form, away_form, events, stats, odds, build_state(match, events, stats), warnings,
                       lambdas=lambdas, rho=rho, source=source, ratings_info=info, lineups=lineups)


def merge_results(a: list, b: list) -> list:
    seen, out = set(), []
    for r in list(a) + list(b):
        k = (r["date"], r["home"], r["away"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


_RATINGS_CACHE: dict = {}
LAST_RATINGS: dict = {}   # (liga, temporada) -> Ratings más reciente (para pronósticos rápidos)


def ratings_for(league, season, results: list) -> Ratings:
    """Ajusta (y guarda) los ratings de una liga con sus resultados."""
    if not results:
        return Ratings()
    key = (league, season, len(results))
    if key not in _RATINGS_CACHE:
        rows = [(r["date"], r["home"], r["away"], r["hg"], r["ag"]) for r in results]
        _RATINGS_CACHE[key] = fit(rows)
    LAST_RATINGS[(league, season)] = _RATINGS_CACHE[key]
    return _RATINGS_CACHE[key]


def ratings_info(r: Ratings, home: str, away: str) -> dict:
    teams = list(r.attack)
    att_rank = {t: i + 1 for i, t in enumerate(sorted(teams, key=lambda t: -r.attack[t]))}
    def_rank = {t: i + 1 for i, t in enumerate(sorted(teams, key=lambda t: r.defense[t]))}
    side = lambda t: {"attack": round(r.attack[t], 3), "defense": round(r.defense[t], 3),
                      "attack_rank": att_rank[t], "defense_rank": def_rank[t], "games": r.games.get(t, 0)}
    return {"home": side(home), "away": side(away), "teams": len(teams), "home_adv": round(r.home_adv, 3),
            "rho": round(r.rho, 3), "matches": r.n_matches}


def form_from_results(results: list, team: str) -> TeamForm:
    """Promedios y forma (últimos 5) calculados con los resultados de la liga."""
    mine = sorted([r for r in results if team in (r["home"], r["away"])], key=lambda r: r["date"])
    home = [r for r in mine if r["home"] == team]
    away = [r for r in mine if r["away"] == team]
    avg = lambda xs: sum(xs) / len(xs) if xs else None
    form = "".join("W" if gf > ga else "D" if gf == ga else "L" for gf, ga in
                   ((r["hg"], r["ag"]) if r["home"] == team else (r["ag"], r["hg"]) for r in mine[-5:]))
    return TeamForm(gf_home=avg([r["hg"] for r in home]), ga_home=avg([r["ag"] for r in home]), gp_home=len(home),
                    gf_away=avg([r["ag"] for r in away]), ga_away=avg([r["hg"] for r in away]), gp_away=len(away), form=form)


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
