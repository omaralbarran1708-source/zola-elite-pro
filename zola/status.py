"""Estados de partido de API-Football y agrupación de competiciones."""

LIVE_STATUSES = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"}
FINISHED_STATUSES = {"FT", "AET", "PEN", "AWD", "WO"}
NOT_STARTED = {"NS", "TBD", "PST", "CANC", "ABD"}

STATUS_LABEL = {
    "NS": "Por jugar", "TBD": "Por definir", "1H": "1er tiempo", "HT": "Entretiempo",
    "2H": "2do tiempo", "ET": "Prórroga", "BT": "Descanso prórroga", "P": "Penales",
    "LIVE": "En vivo", "INT": "Interrumpido", "SUSP": "Suspendido", "FT": "Final",
    "AET": "Final (prórroga)", "PEN": "Final (penales)", "PST": "Postergado",
    "CANC": "Cancelado", "ABD": "Abandonado", "AWD": "Adjudicado", "WO": "W.O.",
}

# IDs de liga en API-Football
TOP_LEAGUE_IDS = {
    39,   # Premier League
    140,  # LaLiga
    135,  # Serie A
    78,   # Bundesliga
    61,   # Ligue 1
    2,    # Champions League
    3,    # Europa League
    848,  # Conference League
    13,   # Libertadores
    11,   # Sudamericana
    1,    # Mundial
    9,    # Copa América
    4,    # Eurocopa
    281,  # Liga 1 Perú
    71,   # Brasileirão
    128,  # Liga Profesional Argentina
}

EUROPE_COUNTRIES = {
    "England", "Spain", "Italy", "Germany", "France", "Portugal", "Netherlands",
    "Belgium", "Scotland", "Turkey", "Greece", "Austria", "Switzerland", "Denmark",
    "Sweden", "Norway", "Poland", "Czech-Republic", "Croatia", "Serbia", "Ukraine",
    "Russia", "Romania", "Hungary", "Ireland", "Wales", "Europa", "Europe",
}
SOUTH_AMERICA_COUNTRIES = {
    "Peru", "Argentina", "Brazil", "Chile", "Colombia", "Uruguay", "Paraguay",
    "Ecuador", "Bolivia", "Venezuela", "Sudamérica", "South-America",
}
EUROPE_CUP_IDS = {2, 3, 848, 4}
SOUTH_AMERICA_CUP_IDS = {13, 11, 9}


def is_live(status: str) -> bool:
    return status in LIVE_STATUSES


def is_finished(status: str) -> bool:
    return status in FINISHED_STATUSES


def bucket_of(match: dict) -> set:
    """Devuelve los grupos a los que pertenece un partido."""
    lid = match.get("league_id")
    country = match.get("country") or ""
    out = {"Todas"}
    if lid in TOP_LEAGUE_IDS:
        out.add("Top")
    if country in EUROPE_COUNTRIES or lid in EUROPE_CUP_IDS:
        out.add("Europa")
    if country in SOUTH_AMERICA_COUNTRIES or lid in SOUTH_AMERICA_CUP_IDS:
        out.add("Sudamérica")
    if country in {"World", "Internacional"}:
        out.add("Internacional")
    return out
