"""Resultados de la temporada actual desde football-data.co.uk (gratis), para cuando el plan
gratuito de API-Football no da acceso a la temporada en curso. Traduce nombres de equipos."""
from __future__ import annotations

import difflib
import re
import time
import unicodedata
from datetime import date

from zola import backtest as bt

LEAGUE_CODES = {39: "E0", 40: "E1", 140: "SP1", 141: "SP2", 135: "I1", 78: "D1", 61: "F1", 88: "N1",
                94: "P1", 144: "B1", 203: "T1", 179: "SC0",
                128: "ARG", 71: "BRA", 262: "MEX", 253: "USA", 98: "JPN", 113: "SWE", 103: "NOR"}

ALIASES = {
    "manchester united": "man united", "manchester city": "man city", "nottingham forest": "nott m forest",
    "wolverhampton wanderers": "wolves", "wolverhampton": "wolves", "sheffield united": "sheffield united",
    "atletico madrid": "ath madrid", "athletic bilbao": "ath bilbao", "athletic club": "ath bilbao",
    "real betis": "betis", "real sociedad": "sociedad", "celta vigo": "celta", "rayo vallecano": "vallecano",
    "espanyol": "espanol", "deportivo alaves": "alaves", "bayern munchen": "bayern munich",
    "borussia monchengladbach": "m gladbach", "bayer leverkusen": "leverkusen", "eintracht frankfurt": "ein frankfurt",
    "borussia dortmund": "dortmund", "vfb stuttgart": "stuttgart", "paris saint germain": "paris sg",
    "inter": "inter", "ac milan": "milan", "as roma": "roma", "hellas verona": "verona",
    "sporting cp": "sp lisbon", "sporting clube de portugal": "sp lisbon", "fc porto": "porto", "sc braga": "sp braga",
    "vitoria guimaraes": "guimaraes", "psv eindhoven": "psv eindhoven", "az alkmaar": "az alkmaar",
    "olympique marseille": "marseille", "olympique lyonnais": "lyon", "stade brestois 29": "brest",
}
STOP = {"fc", "cf", "afc", "sc", "ac", "club", "cd", "ud", "sd", "rc", "ssc", "as", "1", "fk", "sk", "sv", "vfl",
        "tsg", "bk", "if", "ff", "de", "the", "calcio", "1899", "1846", "04", "05", "1909"}
_CACHE: dict = {}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    full = " ".join(s.split())
    if full in ALIASES:
        return ALIASES[full]
    toks = [t for t in full.split() if t not in STOP]
    return " ".join(toks) or full


def match_name(api_name: str, candidates: list[str]) -> str | None:
    """Nombre de football-data que corresponde a un equipo de API-Football."""
    nc = {norm(c): c for c in candidates}
    n = norm(api_name)
    if n in nc:
        return nc[n]
    for k, c in nc.items():                       # contenido: "brighton" ⊂ "brighton hove albion"
        if k and (k in n or n in k) and min(len(k), len(n)) >= 4:
            return c
    best = difflib.get_close_matches(n, list(nc), n=1, cutoff=0.82)
    return nc[best[0]] if best else None


def season_code(league_id: int, ref: date) -> str:
    code = LEAGUE_CODES[league_id]
    if code in bt.EXTRA_LEAGUES:
        return str(ref.year)
    y = ref.year if ref.month >= 7 else ref.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


def results(league_id: int, ref: date | None = None) -> list[dict]:
    if league_id not in LEAGUE_CODES:
        return []
    ref = ref or date.today()
    code, season = LEAGUE_CODES[league_id], season_code(league_id, ref)
    key = (code, season)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < 6 * 3600:
        return hit[1]
    try:
        rows = bt.parse_csv(bt.fetch_csv(code, season), season if code in bt.EXTRA_LEAGUES else None)
    except Exception:
        rows = []
    out = [{"date": r["date"], "home": r["home"], "away": r["away"], "hg": r["hg"], "ag": r["ag"]} for r in rows]
    _CACHE[key] = (time.time(), out)
    return out


def results_for_match(league_id: int, home: str, away: str, ref: date | None = None) -> list[dict]:
    """Resultados con los nombres de los dos equipos traducidos a los de API-Football (o [] si no se encuentran)."""
    rs = results(league_id, ref)
    if not rs:
        return []
    teams = sorted({r["home"] for r in rs} | {r["away"] for r in rs})
    h, a = match_name(home, teams), match_name(away, teams)
    if not h or not a or h == a:
        return []
    ren = {h: home, a: away}
    return [{**r, "home": ren.get(r["home"], r["home"]), "away": ren.get(r["away"], r["away"])} for r in rs]
