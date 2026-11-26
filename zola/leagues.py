"""Directorio de ligas y su historial: partidos anteriores, tabla calculada y temporadas disponibles."""
from __future__ import annotations

import json
from datetime import date

from .fdco import LEAGUE_CODES
from .store import get_store

LOGO = "https://media.api-sports.io/football/leagues/{}.png"
FLAG = "https://media.api-sports.io/flags/{}.svg"
# id API-Football, nombre, país, código de bandera, temporada por año calendario
DIRECTORY = [
    (281, "Liga 1", "Perú", "pe", True), (13, "Copa Libertadores", "Sudamérica", None, True),
    (11, "Copa Sudamericana", "Sudamérica", None, True), (2, "UEFA Champions League", "Europa", None, False),
    (39, "Premier League", "Inglaterra", "gb-eng", False), (140, "LaLiga", "España", "es", False),
    (135, "Serie A", "Italia", "it", False), (78, "Bundesliga", "Alemania", "de", False),
    (61, "Ligue 1", "Francia", "fr", False), (71, "Brasileirão Serie A", "Brasil", "br", True),
    (128, "Liga Profesional", "Argentina", "ar", True), (262, "Liga MX", "México", "mx", False),
    (253, "MLS", "Estados Unidos", "us", True), (88, "Eredivisie", "Países Bajos", "nl", False),
    (94, "Primeira Liga", "Portugal", "pt", False), (40, "Championship", "Inglaterra", "gb-eng", False),
    (141, "LaLiga 2", "España", "es", False), (144, "Pro League", "Bélgica", "be", False),
    (203, "Süper Lig", "Turquía", "tr", False), (179, "Premiership", "Escocia", "gb-sct", False),
    (98, "J1 League", "Japón", "jp", True), (113, "Allsvenskan", "Suecia", "se", True),
    (103, "Eliteserien", "Noruega", "no", True), (3, "UEFA Europa League", "Europa", None, False),
    (1, "Copa del Mundo", "Mundo", None, True),
]
BY_ID = {d[0]: d for d in DIRECTORY}


def calendar_year(league_id) -> bool:
    d = BY_ID.get(league_id)
    return bool(d and d[4])


def hist_code(league_id) -> str:
    return LEAGUE_CODES.get(league_id) or f"AF{league_id}"


def label(league_id, season_int: int) -> str:
    return str(season_int) if calendar_year(league_id) else f"{season_int}/{(season_int + 1) % 100:02d}"


def current_season(league_id, today: date | None = None) -> int:
    t = today or date.today()
    return t.year if calendar_year(league_id) or t.month >= 7 else t.year - 1


def directory() -> list[dict]:
    return [{"league_id": i, "league": n, "country": c, "league_logo": LOGO.format(i), "current_season": current_season(i),
             "flag": FLAG.format(f) if f else None} for i, n, c, f, _ in DIRECTORY]


def _season_int(league_id, lab: str) -> int:
    return int(str(lab)[:4])


def seasons(league_id) -> list[str]:
    st, out = get_store(), set()
    try:
        out |= {r["season"] for r in st.q("SELECT DISTINCT season FROM history WHERE code=?", (hist_code(league_id),))}
        out |= {label(league_id, int(r["season"])) for r in
                st.q("SELECT DISTINCT season FROM fixtures WHERE league_id=? AND season IS NOT NULL", (league_id,))}
    except Exception:
        pass
    out.add(label(league_id, current_season(league_id)))
    return sorted(out, reverse=True)


def matches(league_id, season_label: str | None = None) -> dict:
    """Partidos jugados de una temporada (la fuente con más datos: API guardada o historial)."""
    st = get_store()
    season_label = season_label or label(league_id, current_season(league_id))
    si = _season_int(league_id, season_label)
    api_rows, hist_rows = [], []
    try:
        for r in st.q("SELECT day, kickoff, home, away, home_goals, away_goals, data FROM fixtures WHERE league_id=? AND season=? "
                      "AND status IN ('FT','AET','PEN') ORDER BY kickoff DESC", (league_id, si)):
            d = json.loads(r["data"] or "{}")
            api_rows.append({"date": r["day"], "kickoff": r["kickoff"], "home": r["home"], "away": r["away"],
                             "home_goals": r["home_goals"], "away_goals": r["away_goals"], "round": d.get("round"),
                             "home_logo": d.get("home_logo"), "away_logo": d.get("away_logo"),
                             "match_key": d.get("match_key"), "venue": d.get("venue")})
        for r in st.q("SELECT day, home, away, hg, ag, tournament FROM history WHERE code=? AND season=? ORDER BY day DESC",
                      (hist_code(league_id), season_label)):
            hist_rows.append({"date": r["day"], "kickoff": r["day"] + "T12:00:00", "home": r["home"], "away": r["away"],
                              "home_goals": r["hg"], "away_goals": r["ag"], "round": r["tournament"]})
    except Exception:
        pass
    rows, src = (api_rows, "api") if len(api_rows) >= len(hist_rows) else (hist_rows, "historial")
    return {"season": season_label, "source": src, "matches": rows, "table": table(rows)}


def table(rows: list[dict]) -> list[dict]:
    tb: dict = {}
    for r in sorted(rows, key=lambda x: x["date"]):
        if r["home_goals"] is None or r["away_goals"] is None:
            continue
        for t, logo, gf, ga in ((r["home"], r.get("home_logo"), r["home_goals"], r["away_goals"]),
                                (r["away"], r.get("away_logo"), r["away_goals"], r["home_goals"])):
            e = tb.setdefault(t, {"team": t, "logo": logo, "pj": 0, "g": 0, "e": 0, "p": 0, "gf": 0, "gc": 0, "pts": 0, "form": ""})
            e["pj"] += 1; e["gf"] += gf; e["gc"] += ga
            res = "W" if gf > ga else ("D" if gf == ga else "L")
            e["g" if res == "W" else "e" if res == "D" else "p"] += 1
            e["pts"] += {"W": 3, "D": 1, "L": 0}[res]
            e["form"] = (e["form"] + res)[-5:]
    out = sorted(tb.values(), key=lambda e: (-e["pts"], -(e["gf"] - e["gc"]), -e["gf"], e["team"]))
    for i, e in enumerate(out):
        e["rank"] = i + 1
        e["dg"] = e["gf"] - e["gc"]
    return out
