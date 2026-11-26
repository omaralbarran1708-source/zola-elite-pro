"""Ratings de ataque/defensa por equipo (modelo Dixon-Coles con decaimiento temporal).

Se ajustan con los resultados de la temporada:
    goles local  ~ Poisson(M · H · A_local · D_visita)
    goles visita ~ Poisson(M · A_visita · D_local)
Los partidos recientes pesan más (vida media configurable) y cada equipo se
encoge hacia el promedio con unos partidos "virtuales", así 3 resultados no
deciden todo. También se estima rho (corrección de marcadores bajos).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np

HALF_LIFE_DAYS = 120
PRIOR_MATCHES = 4.0


@dataclass
class Ratings:
    attack: dict = field(default_factory=dict)
    defense: dict = field(default_factory=dict)
    games: dict = field(default_factory=dict)
    base: float = 1.15
    home_adv: float = 1.25
    rho: float = -0.08
    n_matches: int = 0

    def has(self, team: str, min_games: int = 3) -> bool:
        return self.games.get(team, 0) >= min_games

    def lambdas(self, home: str, away: str) -> tuple[float, float] | None:
        if home not in self.attack or away not in self.attack:
            return None
        lh = self.base * self.home_adv * self.attack[home] * self.defense[away]
        la = self.base * self.attack[away] * self.defense[home]
        return float(lh), float(la)

    def table(self) -> list[dict]:
        """Ranking de equipos por fuerza (ataque / defensa)."""
        rows = [{"team": t, "attack": round(self.attack[t], 3), "defense": round(self.defense[t], 3),
                 "strength": round(self.attack[t] / self.defense[t], 3), "games": self.games.get(t, 0)}
                for t in self.attack]
        return sorted(rows, key=lambda r: -r["strength"])


def _weights(dates: list[date], ref: date, half_life: float) -> np.ndarray:
    age = np.array([(ref - d).days for d in dates], dtype=float)
    age = np.clip(age, 0, None)
    return 0.5 ** (age / half_life)


def fit(matches: list[tuple], ref: date | None = None, half_life: float = HALF_LIFE_DAYS,
        prior: float = PRIOR_MATCHES, iters: int = 60, estimate_rho: bool = True) -> Ratings:
    """matches: [(fecha, local, visita, goles_local, goles_visita), ...] ya jugados."""
    ms = [m for m in matches if m[3] is not None and m[4] is not None]
    if len(ms) < 6:
        return Ratings(n_matches=len(ms))
    ref = ref or max(m[0] for m in ms)
    teams = sorted({m[1] for m in ms} | {m[2] for m in ms})
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    hi = np.array([idx[m[1]] for m in ms])
    ai = np.array([idx[m[2]] for m in ms])
    hg = np.array([m[3] for m in ms], dtype=float)
    ag = np.array([m[4] for m in ms], dtype=float)
    w = _weights([m[0] for m in ms], ref, half_life)

    A = np.ones(n)
    D = np.ones(n)
    H = 1.25
    M = max(0.3, (w * (hg + ag)).sum() / (2.25 * w.sum()))
    for _ in range(iters):
        # ataque
        exp_h = M * H * D[ai]          # esperado por unidad de ataque del local
        exp_a = M * D[hi]
        num = np.bincount(hi, w * hg, n) + np.bincount(ai, w * ag, n) + prior
        den = np.bincount(hi, w * exp_h, n) + np.bincount(ai, w * exp_a, n) + prior
        A = num / den
        A /= np.exp(np.log(A).mean())
        # defensa (goles recibidos)
        exp_h2 = M * H * A[hi]        # lo que recibe la visita
        exp_a2 = M * A[ai]            # lo que recibe el local
        num = np.bincount(ai, w * hg, n) + np.bincount(hi, w * ag, n) + prior
        den = np.bincount(ai, w * exp_h2, n) + np.bincount(hi, w * exp_a2, n) + prior
        D = num / den
        D /= np.exp(np.log(D).mean())
        # localía y base
        H = float(np.clip((w * hg).sum() / max((w * M * A[hi] * D[ai]).sum(), 1e-9), 0.9, 1.8))
        M = float((w * (hg + ag)).sum() / max((w * (H * A[hi] * D[ai] + A[ai] * D[hi])).sum(), 1e-9))

    rho = -0.08
    if estimate_rho:
        lh = M * H * A[hi] * D[ai]
        la = M * A[ai] * D[hi]
        best, best_ll = rho, -np.inf
        for r in np.arange(-0.2, 0.061, 0.02):
            tau = np.ones_like(lh)
            m00 = (hg == 0) & (ag == 0); m01 = (hg == 0) & (ag == 1)
            m10 = (hg == 1) & (ag == 0); m11 = (hg == 1) & (ag == 1)
            tau[m00] = 1 - lh[m00] * la[m00] * r
            tau[m01] = 1 + lh[m01] * r
            tau[m10] = 1 + la[m10] * r
            tau[m11] = 1 - r
            if (tau <= 0).any():
                continue
            ll = (w * np.log(tau)).sum()
            if ll > best_ll:
                best, best_ll = float(r), ll
        rho = best

    games = {t: int(((hi == i) | (ai == i)).sum()) for t, i in idx.items()}
    return Ratings(attack={t: float(A[i]) for t, i in idx.items()}, defense={t: float(D[i]) for t, i in idx.items()},
                   games=games, base=float(M), home_adv=float(H), rho=rho, n_matches=len(ms))
