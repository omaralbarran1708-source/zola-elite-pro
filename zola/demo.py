"""Datos de demostración (se muestran solo sin API key, y se marcan como DEMO)."""
from .model import TeamForm

_L = "https://media.api-sports.io/football"

MATCHES = [
    {"fixture_id": 9001, "league": "CONMEBOL Libertadores", "league_id": 13, "country": "World", "season": 2026,
     "home": "Palmeiras", "away": "Sporting Cristal", "home_id": 121, "away_id": 2546,
     "home_goals": 1, "away_goals": 1, "minute": 67, "extra": 0, "status_short": "2H", "venue": "Allianz Parque",
     "home_logo": f"{_L}/teams/121.png", "away_logo": f"{_L}/teams/2546.png", "league_logo": f"{_L}/leagues/13.png"},
    {"fixture_id": 9002, "league": "Premier League", "league_id": 39, "country": "England", "season": 2026,
     "home": "Arsenal", "away": "Newcastle", "home_id": 42, "away_id": 34,
     "home_goals": 0, "away_goals": 0, "minute": 0, "extra": 0, "status_short": "NS", "venue": "Emirates Stadium",
     "home_logo": f"{_L}/teams/42.png", "away_logo": f"{_L}/teams/34.png", "league_logo": f"{_L}/leagues/39.png"},
    {"fixture_id": 9003, "league": "UEFA Champions League", "league_id": 2, "country": "World", "season": 2026,
     "home": "Real Madrid", "away": "Manchester City", "home_id": 541, "away_id": 50,
     "home_goals": 2, "away_goals": 1, "minute": 84, "extra": 0, "status_short": "2H", "venue": "Santiago Bernabéu",
     "home_logo": f"{_L}/teams/541.png", "away_logo": f"{_L}/teams/50.png", "league_logo": f"{_L}/leagues/2.png"},
    {"fixture_id": 9004, "league": "Liga 1", "league_id": 281, "country": "Peru", "season": 2026,
     "home": "Alianza Lima", "away": "Universitario", "home_id": 2553, "away_id": 2540,
     "home_goals": 0, "away_goals": 0, "minute": 0, "extra": 0, "status_short": "NS", "venue": "Alejandro Villanueva",
     "home_logo": f"{_L}/teams/2553.png", "away_logo": f"{_L}/teams/2540.png", "league_logo": f"{_L}/leagues/281.png"},
    {"fixture_id": 9005, "league": "CONMEBOL Sudamericana", "league_id": 11, "country": "World", "season": 2026,
     "home": "Boca Juniors", "away": "LDU Quito", "home_id": 451, "away_id": 1158,
     "home_goals": 2, "away_goals": 0, "minute": 90, "extra": 0, "status_short": "FT", "venue": "La Bombonera",
     "home_logo": f"{_L}/teams/451.png", "away_logo": f"{_L}/teams/1158.png", "league_logo": f"{_L}/leagues/11.png"},
]
for m in MATCHES:
    m["flag"] = {"England": "https://media.api-sports.io/flags/gb-eng.svg",
                 "Peru": "https://media.api-sports.io/flags/pe.svg"}.get(m["country"])
    m["match_key"] = f"demo_{m['fixture_id']}"
    m["source"] = "demo"
    m.setdefault("round", "")
    m.setdefault("kickoff", None)

FORMS = {
    "Palmeiras": TeamForm(1.9, 0.7, 9, 1.4, 1.0, 9, "WWDWL"),
    "Sporting Cristal": TeamForm(1.6, 0.9, 8, 0.9, 1.6, 8, "WLDLW"),
    "Arsenal": TeamForm(2.2, 0.6, 7, 1.7, 0.9, 6, "WWWDW"),
    "Newcastle": TeamForm(1.8, 1.0, 6, 1.1, 1.5, 7, "LWDWL"),
    "Real Madrid": TeamForm(2.4, 0.8, 7, 1.9, 1.1, 7, "WWWWD"),
    "Manchester City": TeamForm(2.3, 0.7, 7, 1.8, 1.0, 7, "WDWLW"),
    "Alianza Lima": TeamForm(1.7, 0.8, 9, 1.1, 1.2, 9, "WDWWL"),
    "Universitario": TeamForm(1.8, 0.6, 9, 1.3, 0.9, 9, "WWDWW"),
    "Boca Juniors": TeamForm(1.6, 0.8, 8, 1.0, 1.1, 8, "DWWLW"),
    "LDU Quito": TeamForm(2.0, 0.7, 8, 0.8, 1.5, 8, "WLLDW"),
}

EVENTS = {
    9001: [
        {"min": 23, "extra": 0, "team": "Palmeiras", "player": "Estêvão", "assist": "Veiga", "type": "Goal", "detail": "Normal Goal"},
        {"min": 38, "extra": 0, "team": "Sporting Cristal", "player": "Cauteruccio", "assist": "", "type": "Card", "detail": "Yellow Card"},
        {"min": 55, "extra": 0, "team": "Sporting Cristal", "player": "Cauteruccio", "assist": "Yotún", "type": "Goal", "detail": "Normal Goal"},
        {"min": 61, "extra": 0, "team": "Palmeiras", "player": "Rony", "assist": "Endrick", "type": "subst", "detail": "Substitution 1"},
    ],
    9003: [
        {"min": 12, "extra": 0, "team": "Real Madrid", "player": "Vinícius Jr.", "assist": "Bellingham", "type": "Goal", "detail": "Normal Goal"},
        {"min": 44, "extra": 0, "team": "Manchester City", "player": "Haaland", "assist": "De Bruyne", "type": "Goal", "detail": "Normal Goal"},
        {"min": 70, "extra": 0, "team": "Real Madrid", "player": "Mbappé", "assist": "", "type": "Goal", "detail": "Penalty"},
        {"min": 78, "extra": 0, "team": "Manchester City", "player": "Rodri", "assist": "", "type": "Card", "detail": "Red Card"},
    ],
    9005: [
        {"min": 31, "extra": 0, "team": "Boca Juniors", "player": "Cavani", "assist": "", "type": "Goal", "detail": "Normal Goal"},
        {"min": 77, "extra": 0, "team": "Boca Juniors", "player": "Merentiel", "assist": "Zenón", "type": "Goal", "detail": "Normal Goal"},
    ],
}

STATS = {
    9001: {"home": {"possession": 58, "shots": 13, "shots_on_target": 5, "corners": 6, "fouls": 9, "yellow": 1, "red": 0, "xg": 1.42},
           "away": {"possession": 42, "shots": 7, "shots_on_target": 3, "corners": 2, "fouls": 12, "yellow": 2, "red": 0, "xg": 0.71}},
    9003: {"home": {"possession": 46, "shots": 15, "shots_on_target": 7, "corners": 4, "fouls": 10, "yellow": 2, "red": 0, "xg": 2.10},
           "away": {"possession": 54, "shots": 12, "shots_on_target": 4, "corners": 7, "fouls": 8, "yellow": 1, "red": 1, "xg": 1.35}},
    9005: {"home": {"possession": 51, "shots": 14, "shots_on_target": 6, "corners": 5, "fouls": 13, "yellow": 3, "red": 0, "xg": 1.80},
           "away": {"possession": 49, "shots": 8, "shots_on_target": 2, "corners": 3, "fouls": 11, "yellow": 2, "red": 0, "xg": 0.60}},
}

ODDS = {
    9001: {"1": 3.10, "X": 1.85, "2": 6.50, "Over 2.5": 1.95, "Under 2.5": 1.80},  # cuotas en vivo, min 67
    9002: {"1": 1.72, "X": 3.90, "2": 4.75, "Over 2.5": 1.75, "Under 2.5": 2.05, "BTTS Sí": 1.70, "BTTS No": 2.10},
    9003: {"1": 1.08, "X": 8.00, "2": 34.0, "Over 3.5": 2.60, "Under 3.5": 1.45},  # en vivo, min 84
    9004: {"1": 2.60, "X": 3.00, "2": 2.85, "Over 2.5": 2.35, "Under 2.5": 1.57, "BTTS Sí": 2.10, "BTTS No": 1.68},
}


# ---- más partidos de demo (horarios relativos a hoy, hora de Lima) ----
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

_LIMA = ZoneInfo("America/Lima")


def _ko(hh, mm, days=0):
    d = datetime.now(_LIMA).date() + timedelta(days=days)
    return datetime.combine(d, time(hh, mm), _LIMA).isoformat()


_EXTRA = [
    (9006, "LaLiga", 140, "Spain", "Barcelona", 529, "Sevilla", 536, 0, 0, 0, "NS", _ko(14, 0), "Estadi Olímpic"),
    (9007, "Bundesliga", 78, "Germany", "Bayern München", 157, "Borussia Dortmund", 165, 3, 1, 90, "FT", _ko(9, 30), "Allianz Arena"),
    (9008, "Serie A", 135, "Italy", "Inter", 505, "AC Milan", 489, 0, 0, 0, "NS", _ko(14, 45), "San Siro"),
    (9009, "Premier League", 39, "England", "Liverpool", 40, "Manchester United", 33, 1, 0, 52, "2H", _ko(10, 0), "Anfield"),
    (9010, "Liga 1", 281, "Peru", "Sporting Cristal", 2546, "FBC Melgar", None, 0, 0, 0, "NS", _ko(20, 0), "Estadio Nacional"),
]
_LOGOS = {281: 281, 140: 140, 78: 78, 135: 135, 39: 39}
for fid, lg, lid, ctry, h, hid, a, aid, hg, ag, mn, st, ko, ven in _EXTRA:
    MATCHES.append({
        "fixture_id": fid, "match_key": f"demo_{fid}", "source": "demo", "round": "", "kickoff": ko,
        "league": lg, "league_id": lid, "country": ctry, "season": 2026,
        "home": h, "away": a, "home_id": hid, "away_id": aid, "home_goals": hg, "away_goals": ag,
        "minute": mn, "extra": 0, "status_short": st, "venue": ven,
        "home_logo": f"{_L}/teams/{hid}.png" if hid else None, "away_logo": f"{_L}/teams/{aid}.png" if aid else None,
        "league_logo": f"{_L}/leagues/{lid}.png",
    })
for m, ko in zip(MATCHES[:5], [_ko(16, 0), _ko(13, 0), _ko(14, 0), _ko(18, 30), _ko(11, 0)]):
    m["kickoff"] = ko

FORMS.update({
    "Barcelona": TeamForm(2.6, 0.8, 6, 2.1, 1.2, 6, "WWLWW"),
    "Sevilla": TeamForm(1.3, 1.2, 6, 1.0, 1.6, 6, "DLWLD"),
    "Bayern München": TeamForm(2.9, 0.7, 6, 2.3, 1.0, 6, "WWWDW"),
    "Borussia Dortmund": TeamForm(2.0, 1.0, 6, 1.5, 1.4, 6, "WLWDW"),
    "Inter": TeamForm(2.1, 0.7, 6, 1.6, 1.0, 6, "WWDWW"),
    "AC Milan": TeamForm(1.8, 0.9, 6, 1.4, 1.2, 6, "WDWLW"),
    "Liverpool": TeamForm(2.3, 0.8, 6, 1.8, 1.1, 6, "WWWLW"),
    "Manchester United": TeamForm(1.5, 1.2, 6, 1.1, 1.6, 6, "LDWLW"),
    "FBC Melgar": TeamForm(1.6, 0.9, 9, 0.9, 1.4, 9, "WDLWD"),
})
STATS[9009] = {"home": {"possession": 61, "shots": 11, "shots_on_target": 5, "corners": 6, "fouls": 7, "yellow": 1, "red": 0, "xg": 1.55},
               "away": {"possession": 39, "shots": 5, "shots_on_target": 1, "corners": 2, "fouls": 11, "yellow": 3, "red": 0, "xg": 0.42}}
EVENTS[9009] = [
    {"min": 34, "extra": 0, "team": "Liverpool", "player": "Salah", "assist": "Szoboszlai", "type": "Goal", "detail": "Normal Goal"},
    {"min": 41, "extra": 0, "team": "Manchester United", "player": "Casemiro", "assist": "", "type": "Card", "detail": "Yellow Card"},
]
ODDS.update({
    9006: {"1": 1.45, "X": 4.80, "2": 6.50, "Over 2.5": 1.50, "Under 2.5": 2.55, "BTTS Sí": 1.80, "BTTS No": 1.95},
    9008: {"1": 2.05, "X": 3.40, "2": 3.60, "Over 2.5": 1.95, "Under 2.5": 1.85, "BTTS Sí": 1.75, "BTTS No": 2.00},
    9009: {"1": 1.25, "X": 5.25, "2": 13.0, "Over 2.5": 2.40, "Under 2.5": 1.55},
    9010: {"1": 1.75, "X": 3.40, "2": 4.80, "Over 2.5": 2.20, "Under 2.5": 1.65},
})


def _row(rank, team, tid, p, w, d, l, gf, ga, form, zone=""):
    return {"rank": rank, "team": team, "team_id": tid, "logo": f"{_L}/teams/{tid}.png" if tid else None, "played": p,
            "win": w, "draw": d, "lose": l, "gf": gf, "ga": ga, "diff": gf - ga, "points": w * 3 + d,
            "form": form, "zone": zone}


# Tablas de ejemplo (DEMO, no son reales)
STANDINGS = {
    39: [{"name": "Premier League", "rows": [
        _row(1, "Arsenal", 42, 12, 9, 2, 1, 25, 8, "WWWDW", "Champions League"),
        _row(2, "Manchester City", 50, 12, 8, 2, 2, 27, 12, "WDWLW", "Champions League"),
        _row(3, "Liverpool", 40, 12, 8, 1, 3, 24, 14, "WLWWW", "Champions League"),
        _row(4, "Chelsea", 49, 12, 7, 3, 2, 22, 11, "DWWDW", "Champions League"),
        _row(5, "Newcastle", 34, 12, 6, 3, 3, 18, 13, "LWDWL", "Europa League"),
        _row(6, "Aston Villa", 66, 12, 6, 2, 4, 17, 15, "WLWDL", "Conference League"),
        _row(7, "Tottenham", 47, 12, 5, 3, 4, 19, 17, "DLWWL"),
        _row(8, "Manchester United", 33, 12, 5, 2, 5, 15, 16, "LWLDW"),
        _row(18, "Leeds", 63, 12, 2, 3, 7, 10, 22, "LLDLW", "Relegation"),
    ]}],
    281: [{"name": "Liga 1 · Clausura", "rows": [
        _row(1, "Universitario", 2540, 15, 11, 3, 1, 28, 7, "WWDWW", "Libertadores"),
        _row(2, "Alianza Lima", 2553, 15, 10, 3, 2, 26, 11, "WDWWL", "Libertadores"),
        _row(3, "Sporting Cristal", 2546, 15, 9, 3, 3, 30, 15, "WLDLW", "Libertadores"),
        _row(4, "UTC Cajamarca", 2539, 15, 8, 4, 3, 22, 14, "DWWLW", "Sudamericana"),
        _row(5, "FBC Melgar", None, 15, 7, 4, 4, 20, 16, "WDLWD", "Sudamericana"),
        _row(6, "ADT", None, 15, 6, 4, 5, 17, 17, "LDWWL"),
        _row(17, "Alianza Atlético", None, 15, 2, 4, 9, 9, 24, "LLDLL", "Relegation"),
    ]}],
}
