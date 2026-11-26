"""Prueba del modelo con partidos reales ya jugados (walk-forward).

Para cada partido de la temporada, el modelo solo "ve" los resultados anteriores
a esa fecha, predice, y luego se compara con lo que pasó y con las cuotas de
cierre de las casas. Datos gratuitos de football-data.co.uk (resultados + cuotas).
"""
from __future__ import annotations

import csv
import io
import math
import time
from datetime import date, datetime

import numpy as np
import requests

from .model import score_matrix
from .ratings import fit

MAIN_LEAGUES = {
    "E0": "Premier League", "E1": "Championship", "SP1": "LaLiga", "SP2": "LaLiga 2", "I1": "Serie A",
    "D1": "Bundesliga", "F1": "Ligue 1", "N1": "Eredivisie", "P1": "Primeira Liga", "B1": "Bélgica Pro League",
    "T1": "Süper Lig", "SC0": "Escocia Premiership",
}
EXTRA_LEAGUES = {
    "ARG": "Argentina Liga Profesional", "BRA": "Brasileirão Serie A", "MEX": "Liga MX", "USA": "MLS",
    "JPN": "J1 League", "SWE": "Allsvenskan", "NOR": "Eliteserien",
}
SOURCE_URL = "football-data.co.uk"
_CACHE: dict = {}
CACHE_SECONDS = 12 * 3600


def seasons_for(code: str, today: date | None = None) -> list[str]:
    today = today or date.today()
    if code in EXTRA_LEAGUES:
        return [str(y) for y in range(today.year, today.year - 4, -1)]
    start = today.year if today.month >= 7 else today.year - 1
    return [f"{(y) % 100:02d}{(y + 1) % 100:02d}" for y in range(start, start - 4, -1)]


def fetch_csv(code: str, season: str, session: requests.Session | None = None) -> str:
    key = (code, season if code in MAIN_LEAGUES else "all")
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    path = f"mmz4281/{season}/{code}.csv" if code in MAIN_LEAGUES else f"new/{code}.csv"
    sess = session or requests.Session()
    last = None
    for base in ("https://www.football-data.co.uk/", "http://www.football-data.co.uk/"):
        try:
            r = sess.get(base + path, timeout=25, headers={"User-Agent": "ZOLA-Elite/1.0"})
            if r.status_code == 200 and len(r.content) > 200:
                text = r.content.decode("utf-8-sig", errors="replace")
                if "Date" in text[:300]:
                    _CACHE[key] = (time.time(), text)
                    return text
            last = f"respuesta {r.status_code}"
        except Exception as e:  # SSL, red
            last = str(e)
    raise RuntimeError(f"No se pudo descargar {path} ({last})")


def _date(s: str) -> date | None:
    s = (s or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _f(row: dict, *keys) -> float | None:
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            try:
                x = float(v)
                if x > 1.0:
                    return x
            except ValueError:
                pass
    return None


def parse_csv(text: str, season: str | None = None) -> list[dict]:
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        r = {k.strip() if k else k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        if season and "Season" in r and r.get("Season") and not str(r["Season"]).startswith(season):
            continue
        d = _date(r.get("Date"))
        home = r.get("HomeTeam") or r.get("Home")
        away = r.get("AwayTeam") or r.get("Away")
        hg = r.get("FTHG") if r.get("FTHG") not in (None, "") else r.get("HG")
        ag = r.get("FTAG") if r.get("FTAG") not in (None, "") else r.get("AG")
        if not (d and home and away) or hg in (None, "") or ag in (None, ""):
            continue
        try:
            hg, ag = int(float(hg)), int(float(ag))
        except ValueError:
            continue
        triples = [("PSCH", "PSCD", "PSCA"), ("AvgCH", "AvgCD", "AvgCA"), ("B365CH", "B365CD", "B365CA"),
                   ("PSH", "PSD", "PSA"), ("AvgH", "AvgD", "AvgA"), ("B365H", "B365D", "B365A")]
        odds, src = None, None
        for t in triples:
            o = [_f(r, k) for k in t]
            if all(o):
                odds, src = o, t[0].rstrip("H")
                break
        ou = None
        for over, under in (("PC>2.5", "PC<2.5"), ("AvgC>2.5", "AvgC<2.5"), ("B365C>2.5", "B365C<2.5"),
                            ("P>2.5", "P<2.5"), ("Avg>2.5", "Avg<2.5"), ("B365>2.5", "B365<2.5")):
            o = [_f(r, over), _f(r, under)]
            if all(o):
                ou = o
                break
        rows.append({"date": d, "home": home, "away": away, "hg": hg, "ag": ag, "odds": odds, "odds_src": src, "ou": ou})
    rows.sort(key=lambda x: x["date"])
    return rows


def _fair(odds):
    inv = [1 / o for o in odds]
    s = sum(inv)
    return [x / s for x in inv]


def _outcome(hg, ag):
    return 0 if hg > ag else (1 if hg == ag else 2)


def run_backtest(rows: list[dict], warmup: int | None = None, market_weight: float = 0.35,
                 value_threshold: float = 0.05, min_prob: float = 0.25, half_life: float = 120) -> dict:
    n_all = len(rows)
    if n_all < 40:
        raise ValueError("Muy pocos partidos jugados para probar (mínimo 40).")
    warmup = warmup if warmup is not None else max(40, int(n_all * 0.25))
    names = ("model", "market", "blend", "base")
    acc = {k: {"n": 0, "hit": 0, "ll": 0.0, "brier": 0.0} for k in names}
    bets = {k: {"bets": 0, "won": 0, "units": 0.0, "series": [0.0]} for k in ("model", "blend")}
    ou = {"n": 0, "hit": 0, "ll": 0.0, "mkt_ll": 0.0, "mkt_n": 0}
    calib = np.zeros((10, 3))  # suma p, suma observado, conteo
    sample = []
    skipped = 0
    ratings, fitted_at, fitted_n = None, None, -1

    for idx in range(warmup, n_all):
        r = rows[idx]
        past = [x for x in rows[:idx] if x["date"] < r["date"]]
        if len(past) < 30:
            skipped += 1
            continue
        if ratings is None or (r["date"] - fitted_at).days >= 4 or len(past) - fitted_n >= 12:
            ratings = fit([(x["date"], x["home"], x["away"], x["hg"], x["ag"]) for x in past],
                          ref=r["date"], half_life=half_life)
            fitted_at, fitted_n = r["date"], len(past)
        if not (ratings.has(r["home"], 3) and ratings.has(r["away"], 3)):
            skipped += 1
            continue
        lh, la = ratings.lambdas(r["home"], r["away"])
        m = score_matrix(lh, la, ratings.rho)
        i, j = np.indices(m.shape)
        pm = [float(m[i > j].sum()), float(m[i == j].sum()), float(m[i < j].sum())]
        p_over = float(m[(i + j) > 2].sum())
        res = _outcome(r["hg"], r["ag"])
        onehot = [1.0 if k == res else 0.0 for k in range(3)]
        tot = [sum(1 for x in past if _outcome(x["hg"], x["ag"]) == k) for k in range(3)]
        pb = [(t + 1) / (len(past) + 3) for t in tot]
        probs = {"model": pm, "base": pb}
        if r["odds"]:
            pk = _fair(r["odds"])
            probs["market"] = pk
            probs["blend"] = [(1 - market_weight) * a + market_weight * b for a, b in zip(pm, pk)]
        for k, p in probs.items():
            a = acc[k]
            a["n"] += 1
            a["hit"] += int(int(np.argmax(p)) == res)
            a["ll"] += -math.log(max(p[res], 1e-9))
            a["brier"] += sum((p[t] - onehot[t]) ** 2 for t in range(3))
        for t in range(3):
            b = min(9, int(pm[t] * 10))
            calib[b] += (pm[t], onehot[t], 1)
        over = (r["hg"] + r["ag"]) > 2
        ou["n"] += 1
        ou["hit"] += int((p_over > 0.5) == over)
        ou["ll"] += -math.log(max(p_over if over else 1 - p_over, 1e-9))
        if r["ou"]:
            fo = _fair(r["ou"])
            ou["mkt_ll"] += -math.log(max(fo[0] if over else fo[1], 1e-9))
            ou["mkt_n"] += 1

        pick = None
        if r["odds"]:
            for k in ("model", "blend"):
                p = probs[k]
                edges = [p[t] * r["odds"][t] - 1 for t in range(3)]
                t = int(np.argmax(edges))
                if edges[t] >= value_threshold and p[t] >= min_prob:
                    b = bets[k]
                    b["bets"] += 1
                    win = t == res
                    b["won"] += int(win)
                    b["units"] += (r["odds"][t] - 1) if win else -1
                    b["series"].append(round(b["units"], 3))
                    if k == "blend":
                        pick = {"outcome": "1X2"[t], "odd": r["odds"][t], "edge": round(edges[t], 3), "won": win}
        sample.append({
            "date": r["date"].isoformat(), "home": r["home"], "away": r["away"], "score": f"{r['hg']}-{r['ag']}",
            "result": "1X2"[res], "model": [round(x, 3) for x in pm], "market": [round(x, 3) for x in probs.get("market", [])],
            "odds": r["odds"], "hit": int(np.argmax(probs.get("blend", pm))) == res, "pick": pick,
        })

    def summ(a):
        n = a["n"]
        return None if not n else {"n": n, "accuracy": a["hit"] / n, "logloss": a["ll"] / n, "brier": a["brier"] / n}

    out_bets = {}
    for k, b in bets.items():
        out_bets[k] = {"bets": b["bets"], "won": b["won"], "units": round(b["units"], 2),
                       "roi": (b["units"] / b["bets"]) if b["bets"] else None,
                       "hit_rate": (b["won"] / b["bets"]) if b["bets"] else None, "series": b["series"][-400:]}
    cal = [{"bin": f"{k * 10}-{k * 10 + 10}%", "pred": calib[k, 0] / calib[k, 2], "obs": calib[k, 1] / calib[k, 2],
            "n": int(calib[k, 2])} for k in range(10) if calib[k, 2] > 0]
    src = next((r["odds_src"] for r in rows if r["odds_src"]), None)
    return {
        "matches": n_all, "evaluated": acc["model"]["n"], "warmup": warmup, "skipped": skipped,
        "first": rows[0]["date"].isoformat(), "last": rows[-1]["date"].isoformat(),
        "systems": {k: summ(acc[k]) for k in names}, "betting": out_bets,
        "over25": {"n": ou["n"], "accuracy": ou["hit"] / ou["n"] if ou["n"] else None,
                   "logloss": ou["ll"] / ou["n"] if ou["n"] else None,
                   "market_logloss": ou["mkt_ll"] / ou["mkt_n"] if ou["mkt_n"] else None},
        "calibration": cal, "sample": sample[-30:][::-1], "odds_source": src,
        "params": {"market_weight": market_weight, "value_threshold": value_threshold, "half_life_days": half_life},
    }
