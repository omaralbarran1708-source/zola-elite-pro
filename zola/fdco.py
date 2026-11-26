"""Resultados de la temporada actual desde football-data.co.uk (gratis), para cuando el plan
gratuito de API-Football no da acceso a la temporada en curso. Traduce nombres de equipos."""
from __future__ import annotations

import difflib
import re
import time
import unicodedata
from datetime import date

import requests

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
    toks = " ".join(t for t in full.split() if t not in STOP) or full
    return ALIASES.get(toks, toks)


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


OPENFOOTBALL = {39: "en.1", 40: "en.2", 140: "es.1", 141: "es.2", 135: "it.1", 78: "de.1", 61: "fr.1", 88: "nl.1",
                94: "pt.1", 144: "be.1", 203: "tr.1", 179: "sco.1", 71: "br.1"}
OF_URL = "https://raw.githubusercontent.com/openfootball/football.json/master/{season}/{code}.json"


def openfootball(league_id: int, ref: date) -> list[dict]:
    """Respaldo: resultados de openfootball/football.json (dominio público, CC0)."""
    code = OPENFOOTBALL.get(league_id)
    if not code:
        return []
    y = ref.year if (ref.month >= 7 or code == "br.1") else ref.year - 1
    season = str(y) if code == "br.1" else f"{y}-{(y + 1) % 100:02d}"
    try:
        r = requests.get(OF_URL.format(season=season, code=code), timeout=15)
        ms = r.json().get("matches", []) if r.status_code == 200 else []
    except Exception:
        return []
    out = []
    for m in ms:
        ft = (m.get("score") or {}).get("ft") if isinstance(m.get("score"), dict) else None
        if not ft or len(ft) != 2:
            continue
        try:
            d = date.fromisoformat(m["date"])
        except (KeyError, ValueError):
            continue
        out.append({"date": d, "home": m["team1"], "away": m["team2"], "hg": int(ft[0]), "ag": int(ft[1])})
    return out


def season_code(league_id: int, ref: date) -> str:
    code = LEAGUE_CODES[league_id]
    if code in bt.EXTRA_LEAGUES:
        return str(ref.year)
    y = ref.year if ref.month >= 7 else ref.year - 1
    return f"{y % 100:02d}{(y + 1) % 100:02d}"


# football-data.org (plan gratis con token: temporada actual de 12 competiciones, 10 consultas/min)
FDORG = {39: "PL", 40: "ELC", 140: "PD", 135: "SA", 78: "BL1", 61: "FL1", 88: "DED", 94: "PPL", 71: "BSA",
         2: "CL", 4: "EC", 1: "WC"}


def fdorg(league_id: int) -> list[dict]:
    import os
    token, comp = os.getenv("FOOTBALL_DATA_TOKEN", ""), FDORG.get(league_id)
    if not token or not comp:
        return []
    try:
        r = requests.get(f"https://api.football-data.org/v4/competitions/{comp}/matches",
                         params={"status": "FINISHED"}, headers={"X-Auth-Token": token}, timeout=15)
        ms = r.json().get("matches", []) if r.status_code == 200 else []
    except Exception:
        return []
    out = []
    for m in ms:
        ft = ((m.get("score") or {}).get("fullTime") or {})
        if ft.get("home") is None or ft.get("away") is None:
            continue
        try:
            d = date.fromisoformat(m["utcDate"][:10])
        except (KeyError, ValueError):
            continue
        out.append({"date": d, "home": (m.get("homeTeam") or {}).get("name", ""),
                    "away": (m.get("awayTeam") or {}).get("name", ""), "hg": int(ft["home"]), "ag": int(ft["away"])})
    return out


def covers(league_id) -> bool:
    return league_id in LEAGUE_CODES or league_id in OPENFOOTBALL or league_id in FDORG


def results(league_id: int, ref: date | None = None) -> list[dict]:
    """La fuente gratis con más partidos de la temporada actual: football-data.org, football-data.co.uk u openfootball."""
    if not covers(league_id):
        return []
    ref = ref or date.today()
    key = (league_id, ref.year if ref.month >= 7 else ref.year - 1)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < 6 * 3600:
        return hit[1]
    out = []
    if league_id in LEAGUE_CODES:
        code, season = LEAGUE_CODES[league_id], season_code(league_id, ref)
        try:
            rows = bt.parse_csv(bt.fetch_csv(code, season), season if code in bt.EXTRA_LEAGUES else None)
            out = [{"date": r["date"], "home": r["home"], "away": r["away"], "hg": r["hg"], "ag": r["ag"]} for r in rows]
        except Exception:
            out = []
    for alt_fn in (lambda: fdorg(league_id), lambda: openfootball(league_id, ref)):
        alt = alt_fn()
        if len(alt) > len(out):
            out = alt
    _CACHE[key] = (time.time(), out)
    return out


def results_for_match(league_id: int, home: str, away: str, ref: date | None = None) -> list[dict]:
    """Resultados con los nombres de los dos equipos traducidos a los de API-Football (o [] si no se encuentran)."""
    rs = results(league_id, ref)
    if len(rs) < 60:        # inicio de temporada: sumar la temporada anterior (el decaimiento le da menos peso)
        from datetime import timedelta
        prev = results(league_id, (ref or date.today()) - timedelta(days=365))
        rs = prev + rs
    if not rs:
        return []
    teams = sorted({r["home"] for r in rs} | {r["away"] for r in rs})
    h, a = match_name(home, teams), match_name(away, teams)
    if not h or not a or h == a:
        return []
    ren = {h: home, a: away}
    return [{**r, "home": ren.get(r["home"], r["home"]), "away": ren.get(r["away"], r["away"])} for r in rs]
