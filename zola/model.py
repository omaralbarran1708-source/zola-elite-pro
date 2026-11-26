"""Modelo de predicción: Poisson con corrección Dixon-Coles + ajuste en vivo.

Pre-partido
    La fuerza de cada equipo sale de sus promedios reales de goles a favor y en
    contra (local/visita) en la temporada, encogidos hacia el promedio de la liga
    cuando hay pocos partidos jugados (evita que 2 partidos definan todo).

En vivo
    Se modelan solo los goles que faltan: tasa por minuto × minutos restantes,
    mezclando la tasa previa con lo que está pasando en el partido (xG o tiros al
    arco), y ajustando por marcador (quien pierde ataca más) y tarjetas rojas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

LEAGUE_HOME_AVG = 1.45   # goles promedio del local en ligas top
LEAGUE_AWAY_AVG = 1.15   # goles promedio de la visita
SHRINK_GAMES = 6         # partidos "virtuales" de promedio de liga
DC_RHO = -0.08           # corrección Dixon-Coles para marcadores bajos
MAX_GOALS = 10
MATCH_MINUTES = 94       # 90 + descuento promedio
XG_PER_SHOT_ON_TARGET = 0.30


@dataclass
class TeamForm:
    """Promedios de temporada de un equipo (de /teams/statistics)."""
    gf_home: float | None = None   # goles a favor por partido jugando de local
    ga_home: float | None = None
    gp_home: int = 0
    gf_away: float | None = None
    ga_away: float | None = None
    gp_away: int = 0
    form: str = ""                 # ej. "WWDLW"

    @property
    def has_data(self) -> bool:
        return (self.gp_home + self.gp_away) > 0


@dataclass
class LiveState:
    minute: int = 0
    status: str = "NS"
    home_goals: int = 0
    away_goals: int = 0
    home_red: int = 0
    away_red: int = 0
    home_xg: float | None = None
    away_xg: float | None = None
    home_sot: int | None = None    # tiros al arco
    away_sot: int | None = None


@dataclass
class Prediction:
    lam_home: float
    lam_away: float
    home_win: float
    draw: float
    away_win: float
    over15: float
    over25: float
    over35: float
    btts: float
    top_scores: list = field(default_factory=list)
    best_score: str = "0-0"
    winner: str = "Empate"
    confidence: str = "Baja"
    data_quality: str = "Sin datos"
    markets: dict = field(default_factory=dict)
    value_bets: list = field(default_factory=list)
    best_bet: dict | None = None
    notes: list = field(default_factory=list)
    matrix: list = field(default_factory=list)   # P(marcador final) 0..5 x 0..5
    model_1x2: list = field(default_factory=list)   # [1, X, 2] solo modelo
    market_1x2: list = field(default_factory=list)  # [1, X, 2] implícito de la casa (sin margen)
    blend_weight: float = 0.0                       # peso del mercado en la probabilidad final
    source: str = ""                                # de dónde salen los goles esperados


def _shrink(rate: float | None, games: int, prior: float) -> float:
    if rate is None or games <= 0:
        return prior
    return (games * rate + SHRINK_GAMES * prior) / (games + SHRINK_GAMES)


def expected_goals(home: TeamForm, away: TeamForm) -> tuple[float, float]:
    """Goles esperados en 90' para local y visita."""
    h_att = _shrink(home.gf_home, home.gp_home, LEAGUE_HOME_AVG) / LEAGUE_HOME_AVG
    h_def = _shrink(home.ga_home, home.gp_home, LEAGUE_AWAY_AVG) / LEAGUE_AWAY_AVG
    a_att = _shrink(away.gf_away, away.gp_away, LEAGUE_AWAY_AVG) / LEAGUE_AWAY_AVG
    a_def = _shrink(away.ga_away, away.gp_away, LEAGUE_HOME_AVG) / LEAGUE_HOME_AVG
    lam_h = LEAGUE_HOME_AVG * h_att * a_def
    lam_a = LEAGUE_AWAY_AVG * a_att * h_def
    # forma reciente: ±4 % como máximo
    lam_h *= 1 + 0.04 * _form_score(home.form)
    lam_a *= 1 + 0.04 * _form_score(away.form)
    return max(0.15, lam_h), max(0.10, lam_a)


def _form_score(form: str) -> float:
    """-1..1 según los últimos 5 resultados (W=1, D=0, L=-1)."""
    last = (form or "")[-5:]
    if not last:
        return 0.0
    pts = {"W": 1, "D": 0, "L": -1}
    return sum(pts.get(c, 0) for c in last) / len(last)


def _poisson(lam: float, n: int = MAX_GOALS) -> np.ndarray:
    k = np.arange(n + 1)
    fact = np.array([math.factorial(int(i)) for i in k], dtype=float)
    return np.exp(-lam) * lam ** k / fact


def score_matrix(lam_h: float, lam_a: float, rho: float = DC_RHO) -> np.ndarray:
    """Matriz P[i, j] de goles (local i, visita j) con corrección Dixon-Coles."""
    m = np.outer(_poisson(lam_h), _poisson(lam_a))
    if rho:
        m[0, 0] *= 1 - lam_h * lam_a * rho
        m[0, 1] *= 1 + lam_h * rho
        m[1, 0] *= 1 + lam_a * rho
        m[1, 1] *= 1 - rho
    m = np.clip(m, 0, None)
    return m / m.sum()


def _remaining_fraction(state: LiveState) -> float:
    if state.status in {"FT", "AET", "PEN", "AWD", "WO"}:
        return 0.0
    if state.status == "HT":
        return 1 - _cum_rate(46) / _cum_rate(MATCH_MINUTES)
    if state.status in {"NS", "TBD", "PST"} or not state.minute:
        return 1.0
    if state.status in {"ET", "BT", "P"}:
        return 0.0 if state.status == "P" else max(0.0, (122 - state.minute) / MATCH_MINUTES)
    return max(0.02, 1 - _cum_rate(state.minute) / _cum_rate(MATCH_MINUTES))


def _cum_rate(t: float) -> float:
    """Goles acumulados esperados hasta el minuto t (la tasa sube durante el partido:
    ~45 % de los goles en el 1er tiempo y ~55 % en el 2do)."""
    t = min(max(t, 0), MATCH_MINUTES)
    return 0.8 * t + 0.2 * t * t / MATCH_MINUTES


def live_adjust(lam_h: float, lam_a: float, state: LiveState) -> tuple[float, float, list]:
    """Goles esperados *restantes* según el estado del partido."""
    notes = []
    frac = _remaining_fraction(state)
    if frac <= 0:
        return 0.0, 0.0, ["Partido terminado"]
    rem_h, rem_a = lam_h * frac, lam_a * frac
    minute = state.minute or 0
    if minute >= 15:
        in_h = state.home_xg if state.home_xg is not None else (
            state.home_sot * XG_PER_SHOT_ON_TARGET if state.home_sot is not None else None)
        in_a = state.away_xg if state.away_xg is not None else (
            state.away_sot * XG_PER_SHOT_ON_TARGET if state.away_sot is not None else None)
        if in_h is not None and in_a is not None:
            w = minute / (minute + 45)   # el partido pesa más a medida que avanza
            played = min(minute, MATCH_MINUTES)
            rate_h = (1 - w) * lam_h / MATCH_MINUTES + w * in_h / played
            rate_a = (1 - w) * lam_a / MATCH_MINUTES + w * in_a / played
            rem_h = rate_h * MATCH_MINUTES * frac
            rem_a = rate_a * MATCH_MINUTES * frac
            src = "xG" if state.home_xg is not None else "tiros al arco"
            notes.append(f"Ritmo en vivo según {src} (peso {w:.0%})")
    diff = state.home_goals - state.away_goals
    if diff:
        trailing_boost, leading_cut = 1.12, 0.90
        if diff > 0:
            rem_h *= leading_cut; rem_a *= trailing_boost
        else:
            rem_h *= trailing_boost; rem_a *= leading_cut
        notes.append("Ajuste por marcador: quien pierde ataca más")
    for _ in range(state.home_red):
        rem_h *= 0.70; rem_a *= 1.20
    for _ in range(state.away_red):
        rem_a *= 0.70; rem_h *= 1.20
    if state.home_red or state.away_red:
        notes.append("Ajuste por tarjetas rojas")
    return rem_h, rem_a, notes


def final_score_matrix(lam_h: float, lam_a: float, state: LiveState, rho: float = DC_RHO) -> np.ndarray:
    """Distribución del marcador FINAL (goles actuales + restantes)."""
    n = MAX_GOALS
    full = np.zeros((n + 1, n + 1))
    gh, ga = min(state.home_goals, n), min(state.away_goals, n)
    if lam_h <= 0 and lam_a <= 0:
        full[gh, ga] = 1.0
        return full
    in_play = state.minute and state.minute > 0
    rem = score_matrix(lam_h, lam_a, rho=0 if in_play else rho)
    for i in range(n + 1 - gh):
        for j in range(n + 1 - ga):
            full[gh + i, ga + j] += rem[i, j]
    return full / full.sum()


def implied_probs(odds: dict) -> dict:
    """Probabilidades implícitas sin margen de la casa (por mercado agrupado)."""
    groups = [("1", "X", "2"), ("Over 2.5", "Under 2.5"), ("BTTS Sí", "BTTS No"), ("Over 1.5", "Under 1.5")]
    out = {}
    for g in groups:
        vals = {k: 1 / odds[k] for k in g if odds.get(k)}
        if len(vals) == len(g):
            s = sum(vals.values())
            out.update({k: v / s for k, v in vals.items()})
    return out


def kelly_fraction(p: float, odd: float) -> float:
    if odd <= 1:
        return 0.0
    return max(0.0, (p * odd - 1) / (odd - 1))


MARKET_WEIGHT = 0.35   # peso del mercado al combinar (el backtest permite comparar)


def blend_matrix(m: np.ndarray, target: tuple[float, float, float]) -> np.ndarray:
    """Reescala la matriz para que 1/X/2 sumen lo indicado, manteniendo la forma dentro de cada zona."""
    i, j = np.indices(m.shape)
    out = m.copy()
    for mask, t in ((i > j, target[0]), (i == j, target[1]), (i < j, target[2])):
        cur = m[mask].sum()
        if cur > 0:
            out[mask] = m[mask] * (t / cur)
    return out / out.sum()


def predict(home_name: str, away_name: str, home: TeamForm, away: TeamForm,
            state: LiveState | None = None, odds: dict | None = None,
            lambdas: tuple[float, float] | None = None, rho: float | None = None,
            source: str = "", market_weight: float = MARKET_WEIGHT) -> Prediction:
    state = state or LiveState()
    if lambdas:
        lam_h, lam_a = lambdas
    else:
        lam_h, lam_a = expected_goals(home, away)
        source = source or ("Estadísticas de temporada" if (home.has_data or away.has_data) else "Promedio de liga")
    rem_h, rem_a, notes = live_adjust(lam_h, lam_a, state)
    m = final_score_matrix(rem_h, rem_a, state, DC_RHO if rho is None else rho)

    i, j = np.indices(m.shape)
    model_1x2 = [float(m[i > j].sum()), float(m[i == j].sum()), float(m[i < j].sum())]
    odds = odds or {}
    fair = implied_probs(odds)
    market_1x2 = [fair["1"], fair["X"], fair["2"]] if all(k in fair for k in ("1", "X", "2")) else []
    w_used = 0.0
    if market_1x2 and _remaining_fraction(state) > 0 and market_weight > 0:
        target = tuple((1 - market_weight) * a + market_weight * b for a, b in zip(model_1x2, market_1x2))
        m = blend_matrix(m, target)
        w_used = market_weight
        notes.append(f"Combinado con el mercado ({market_weight:.0%})")

    i, j = np.indices(m.shape)
    home_win = float(m[i > j].sum())
    draw = float(m[i == j].sum())
    away_win = float(m[i < j].sum())
    total = i + j
    over15 = float(m[total > 1].sum())
    over25 = float(m[total > 2].sum())
    over35 = float(m[total > 3].sum())
    btts = float(m[(i > 0) & (j > 0)].sum())

    flat = [(f"{a}-{b}", float(m[a, b])) for a in range(m.shape[0]) for b in range(m.shape[1])]
    flat.sort(key=lambda x: x[1], reverse=True)
    top = [s for s in flat if s[1] > 0][:8]

    markets = {
        "1": home_win, "X": draw, "2": away_win,
        "1X": home_win + draw, "X2": draw + away_win, "12": home_win + away_win,
        "Over 1.5": over15, "Under 1.5": 1 - over15,
        "Over 2.5": over25, "Under 2.5": 1 - over25,
        "Over 3.5": over35, "Under 3.5": 1 - over35,
        "BTTS Sí": btts, "BTTS No": 1 - btts,
    }

    probs_1x2 = {"home": home_win, "draw": draw, "away": away_win}
    best = max(probs_1x2, key=probs_1x2.get)
    winner = {"home": home_name, "away": away_name, "draw": "Empate"}[best]

    real = bool(lambdas) or (home.has_data and away.has_data)
    quality = source or ("Datos reales" if real else ("Parcial" if (home.has_data or away.has_data) else "Sin datos (promedio de liga)"))
    top_p = max(probs_1x2.values())
    if top_p >= 0.62 and real:
        confidence = "Alta"
    elif top_p >= 0.47 and (real or state.minute >= 60):
        confidence = "Media"
    else:
        confidence = "Baja"
    if not real:
        notes.append("Sin estadísticas de temporada: se usó el promedio de liga")

    value_bets = []
    for mk, odd in odds.items():
        p = markets.get(mk)
        if p is None or not odd or odd <= 1 or p > 0.995 or p < 0.005:
            continue  # mercado ya decidido (la casa lo suspende)
        edge = p * odd - 1
        value_bets.append({
            "market": mk, "prob": p, "odd": odd, "implied": fair.get(mk, 1 / odd),
            "edge": edge, "kelly": kelly_fraction(p, odd),
        })
    value_bets.sort(key=lambda v: v["edge"], reverse=True)

    finished = _remaining_fraction(state) == 0
    best_bet = None
    if not finished:
        positive = [v for v in value_bets if v["edge"] >= 0.03 and v["prob"] >= 0.30]
        if positive:
            best_bet = {**positive[0], "kind": "valor"}
        else:
            candidates = ["1", "X", "2", "Over 2.5", "Under 2.5", "BTTS Sí", "BTTS No", "1X", "X2", "Over 1.5"]
            candidates = [k for k in candidates if markets[k] <= 0.97]  # descarta lo ya decidido
            mk = max(candidates, key=lambda k: markets[k] - (0.12 if k in {"1X", "X2", "Over 1.5"} else 0), default=None)
            if mk and markets[mk] >= 0.55:
                best_bet = {"market": mk, "prob": markets[mk], "kind": "probable"}

    return Prediction(
        lam_home=lam_h, lam_away=lam_a,
        home_win=home_win, draw=draw, away_win=away_win,
        over15=over15, over25=over25, over35=over35, btts=btts,
        top_scores=top, best_score=top[0][0] if top else "0-0",
        winner=winner, confidence=confidence, data_quality=quality,
        markets=markets, value_bets=value_bets, best_bet=best_bet, notes=notes,
        matrix=[[round(float(m[a, b]), 5) for b in range(6)] for a in range(6)],
        model_1x2=model_1x2, market_1x2=market_1x2, blend_weight=w_used, source=quality,
    )
