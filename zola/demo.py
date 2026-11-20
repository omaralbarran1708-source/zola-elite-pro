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
