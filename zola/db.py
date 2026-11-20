"""Historial de predicciones guardadas (SQLite) con control de aciertos."""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    match_key TEXT NOT NULL,
    fixture_id INTEGER,
    league TEXT, home TEXT, away TEXT,
    minute INTEGER, score_at_pick TEXT,
    pick_market TEXT, pick_prob REAL, pick_odd REAL,
    predicted_score TEXT, winner TEXT, confidence TEXT,
    final_score TEXT, pick_won INTEGER, score_hit INTEGER
)
"""


class History:
    def __init__(self, path: Path | str):
        self.path = str(path)
        with closing(self._conn()) as c:
            c.execute(SCHEMA)
            c.commit()

    def _conn(self):
        return sqlite3.connect(self.path)

    def exists(self, match_key: str, market: str, score: str) -> bool:
        with closing(self._conn()) as c:
            row = c.execute("SELECT 1 FROM predictions WHERE match_key=? AND pick_market=? AND score_at_pick=?",
                            (match_key, market, score)).fetchone()
        return row is not None

    def save(self, match: dict, pred, pick: dict | None) -> bool:
        """Guarda una predicción. Devuelve False si ya existía (evita duplicados)."""
        score = f"{match['home_goals']}-{match['away_goals']}"
        market = (pick or {}).get("market", "—")
        if self.exists(match["match_key"], market, score):
            return False
        with closing(self._conn()) as c:
            c.execute(
                "INSERT INTO predictions(ts, match_key, fixture_id, league, home, away, minute, score_at_pick,"
                " pick_market, pick_prob, pick_odd, predicted_score, winner, confidence) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), match["match_key"], match.get("fixture_id"),
                 match["league"], match["home"], match["away"], match.get("minute") or 0, score,
                 market, (pick or {}).get("prob"), (pick or {}).get("odd"),
                 pred.best_score, pred.winner, pred.confidence))
            c.commit()
        return True

    def pending(self) -> list[dict]:
        with closing(self._conn()) as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM predictions WHERE final_score IS NULL").fetchall()
        return [dict(r) for r in rows]

    def settle(self, match_key: str, home_goals: int, away_goals: int) -> int:
        """Registra el resultado final y calcula si se acertó. Devuelve filas actualizadas."""
        final = f"{home_goals}-{away_goals}"
        n = 0
        with closing(self._conn()) as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT id, pick_market, predicted_score FROM predictions "
                             "WHERE match_key=? AND final_score IS NULL", (match_key,)).fetchall()
            for r in rows:
                won = market_won(r["pick_market"], home_goals, away_goals)
                c.execute("UPDATE predictions SET final_score=?, pick_won=?, score_hit=? WHERE id=?",
                          (final, None if won is None else int(won), int(r["predicted_score"] == final), r["id"]))
                n += 1
            c.commit()
        return n

    def recent(self, limit: int = 20) -> pd.DataFrame:
        with closing(self._conn()) as c:
            return pd.read_sql_query("SELECT * FROM predictions ORDER BY id DESC LIMIT ?", c, params=(limit,))

    def summary(self) -> dict:
        with closing(self._conn()) as c:
            df = pd.read_sql_query("SELECT pick_won, score_hit, pick_odd FROM predictions WHERE final_score IS NOT NULL", c)
            total = c.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        settled = df.dropna(subset=["pick_won"])
        hits = int(settled["pick_won"].sum()) if len(settled) else 0
        with_odds = settled.dropna(subset=["pick_odd"])
        profit = float(sum((o - 1) if w else -1 for w, o in zip(with_odds["pick_won"], with_odds["pick_odd"])))
        return {
            "total": int(total), "settled": len(settled), "hits": hits,
            "hit_rate": hits / len(settled) if len(settled) else None,
            "score_hits": int(df["score_hit"].sum()) if len(df) else 0,
            "units": profit, "bets_with_odds": len(with_odds),
        }


def market_won(market: str, h: int, a: int) -> bool | None:
    t = h + a
    rules = {
        "1": h > a, "X": h == a, "2": h < a,
        "1X": h >= a, "X2": h <= a, "12": h != a,
        "Over 1.5": t > 1, "Under 1.5": t <= 1,
        "Over 2.5": t > 2, "Under 2.5": t <= 2,
        "Over 3.5": t > 3, "Under 3.5": t <= 3,
        "BTTS Sí": h > 0 and a > 0, "BTTS No": not (h > 0 and a > 0),
    }
    return rules.get(market)
