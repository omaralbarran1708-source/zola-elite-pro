"""Aprendizaje con el historial guardado.

Cada vez que alguien abre un partido, ZOLA guarda su predicción (antes del
partido y minuto a minuto en vivo). Cuando el partido termina se compara con el
resultado real y el sistema ajusta cuánto confiar en el mercado vs. el modelo
(el peso que minimiza el error), en total y por liga.
"""
from __future__ import annotations

import math
import time

from .model import MARKET_WEIGHT
from .store import get_store

MIN_SAMPLES = 40
_cache: dict = {"ts": 0.0, "weights": {}}


def record(match: dict, pred, state) -> None:
    st = get_store()
    payload = {
        "model": [round(x, 4) for x in pred.model_1x2], "market": [round(x, 4) for x in pred.market_1x2],
        "final": [round(pred.home_win, 4), round(pred.draw, 4), round(pred.away_win, 4)],
        "lam": [round(pred.lam_home, 3), round(pred.lam_away, 3)], "weight": pred.blend_weight,
        "over25": round(pred.over25, 4), "best": pred.best_score,
    }
    s = match.get("status_short", "NS")
    if s in {"NS", "TBD"}:
        st.log_prediction(match, "pre", 0, payload)
    elif s in {"1H", "HT", "2H", "ET", "BT", "P", "LIVE"}:
        minute = 46 if s == "HT" else int(match.get("minute") or 0)
        st.log_prediction(match, "live", minute, payload)


def _ll(p, k):
    return -math.log(max(p[k], 1e-9))


def evaluate() -> dict:
    rows = get_store().settled_pre_predictions()
    out = {"n": len(rows), "min_samples": MIN_SAMPLES}
    if not rows:
        return out
    acc = {"model": [0, 0.0, 0], "market": [0, 0.0, 0], "final": [0, 0.0, 0]}
    with_mkt = []
    for r in rows:
        res = 0 if r["hg"] > r["ag"] else (1 if r["hg"] == r["ag"] else 2)
        for k in acc:
            p = r.get(k) or []
            if len(p) == 3:
                a = acc[k]
                a[0] += int(max(range(3), key=lambda i: p[i]) == res)
                a[1] += _ll(p, res)
                a[2] += 1
        if len(r.get("model") or []) == 3 and len(r.get("market") or []) == 3:
            with_mkt.append((r["model"], r["market"], res, r.get("league_id")))
    out["systems"] = {k: {"n": v[2], "accuracy": v[0] / v[2], "logloss": v[1] / v[2]} for k, v in acc.items() if v[2]}

    def best_weight(items):
        best, best_ll = MARKET_WEIGHT, float("inf")
        for w10 in range(0, 21):
            w = w10 / 20
            ll = sum(_ll([(1 - w) * a + w * b for a, b in zip(m, k)], res) for m, k, res, _ in items) / len(items)
            if ll < best_ll:
                best, best_ll = w, ll
        return best, best_ll

    weights = {}
    if len(with_mkt) >= MIN_SAMPLES:
        w, ll = best_weight(with_mkt)
        weights["global"] = min(max(w, 0.1), 0.85)
        out["learned"] = {"weight": weights["global"], "logloss": ll, "samples": len(with_mkt)}
    by_league: dict = {}
    for item in with_mkt:
        by_league.setdefault(item[3], []).append(item)
    for lid, items in by_league.items():
        if lid and len(items) >= MIN_SAMPLES:
            weights[str(lid)] = min(max(best_weight(items)[0], 0.1), 0.85)
    if weights:
        get_store().kv_set("market_weights", weights)
    out["weights"] = weights
    return out


def learned_weight(league_id=None) -> float:
    if time.time() - _cache["ts"] > 3600:
        _cache["weights"] = get_store().kv_get("market_weights", {}) or {}
        _cache["ts"] = time.time()
    w = _cache["weights"]
    return float(w.get(str(league_id), w.get("global", MARKET_WEIGHT)))
