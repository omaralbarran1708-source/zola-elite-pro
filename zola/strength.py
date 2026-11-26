"""Fuerza de los equipos cuando no hay historial de la temporada:
1) goles esperados deducidos de las cuotas (idea de penaltyblog: goal_expectancy),
2) rating Elo de ClubElo.com (gratis, clubes europeos)."""
from __future__ import annotations

import csv
import io
import time
from datetime import date

import numpy as np
import requests

from .model import DC_RHO, score_matrix

_GRID = np.round(np.arange(0.15, 3.81, 0.05), 3)
_TABLE: list | None = None


def _table():
    """Tabla precalculada (λ_local, λ_visita) → (P1, PX, P2, P+2.5)."""
    global _TABLE
    if _TABLE is None:
        rows = []
        for lh in _GRID:
            for la in _GRID:
                m = score_matrix(float(lh), float(la), DC_RHO)
                i, j = np.indices(m.shape)
                rows.append((lh, la, m[i > j].sum(), m[i == j].sum(), m[i < j].sum(), m[(i + j) > 2].sum()))
        _TABLE = np.array(rows)
    return _TABLE


def fair_probs(odds: dict, keys) -> list[float] | None:
    try:
        inv = [1 / float(odds[k]) for k in keys]
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None
    s = sum(inv)
    return [x / s for x in inv] if s > 0 else None


def implied_lambdas(odds: dict) -> tuple[float, float] | None:
    """Goles esperados que reproducen las cuotas 1X2 (y Más/Menos 2.5 si existen)."""
    p = fair_probs(odds or {}, ("1", "X", "2"))
    if not p:
        return None
    ou = fair_probs(odds, ("over25", "under25")) or fair_probs(odds, ("Over 2.5", "Under 2.5"))
    t = _table()
    err = (t[:, 2] - p[0]) ** 2 + (t[:, 3] - p[1]) ** 2 + (t[:, 4] - p[2]) ** 2
    if ou:
        err = err + (t[:, 5] - ou[0]) ** 2
    else:  # sin línea de goles: suave preferencia por ~2.6 goles totales
        err = err + 0.002 * (t[:, 0] + t[:, 1] - 2.6) ** 2
    k = int(np.argmin(err))
    return float(t[k, 0]), float(t[k, 1])


# ---------------- ClubElo ----------------
_ELO: dict = {"ts": 0, "rows": []}
COUNTRY = {"England": "ENG", "Spain": "ESP", "Italy": "ITA", "Germany": "GER", "France": "FRA", "Netherlands": "NED",
           "Portugal": "POR", "Belgium": "BEL", "Turkey": "TUR", "Scotland": "SCO", "Greece": "GRE", "Austria": "AUT",
           "Switzerland": "SUI", "Denmark": "DEN", "Sweden": "SWE", "Norway": "NOR", "Czech-Republic": "CZE",
           "Poland": "POL", "Croatia": "CRO", "Ukraine": "UKR", "Russia": "RUS", "Serbia": "SRB", "Romania": "ROM",
           "Hungary": "HUN", "Cyprus": "CYP", "Israel": "ISR", "Bulgaria": "BUL", "Slovakia": "SVK", "Slovenia": "SVN"}


def elo_table() -> list[dict]:
    age = time.time() - _ELO["ts"]
    if age < (12 * 3600 if _ELO["rows"] else 1800):   # si falló, no reintentar en 30 min
        return _ELO["rows"]
    _ELO["ts"] = time.time()
    try:
        r = requests.get(f"http://api.clubelo.com/{date.today().isoformat()}", timeout=8)
        rows = [{"club": x["Club"], "country": x["Country"], "elo": float(x["Elo"])}
                for x in csv.DictReader(io.StringIO(r.text)) if x.get("Elo")]
        if rows:
            _ELO.update(ts=time.time(), rows=rows)
    except Exception:
        pass
    return _ELO["rows"]


def elo_of(team: str, country: str | None = None) -> float | None:
    from .fdco import match_name
    rows = elo_table()
    code = COUNTRY.get(country or "")
    pool = [x for x in rows if not code or x["country"] == code]
    name = match_name(team, [x["club"] for x in pool])
    return next((x["elo"] for x in pool if x["club"] == name), None) if name else None


def elo_lambdas(elo_h: float, elo_a: float, home_adv: float = 65, total: float = 2.65) -> tuple[float, float]:
    """Convierte la diferencia de Elo en goles esperados (misma expectativa de puntos)."""
    e = 1 / (1 + 10 ** (-(elo_h - elo_a + home_adv) / 400))
    best, be = (total / 2, total / 2), 9.0
    for s in np.arange(-2.2, 2.21, 0.02):
        lh, la = max(0.15, (total + s) / 2), max(0.15, (total - s) / 2)
        m = score_matrix(lh, la, DC_RHO)
        i, j = np.indices(m.shape)
        exp = m[i > j].sum() + 0.5 * m[i == j].sum()
        if abs(exp - e) < be:
            best, be = (lh, la), abs(exp - e)
    return round(best[0], 3), round(best[1], 3)
