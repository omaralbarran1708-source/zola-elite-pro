"""Almacenamiento persistente de ZOLA.

Guarda todo lo que se consulta para no perderlo y para que el modelo aprenda:
- respuestas de API-Football (caché persistente: ahorra consultas tras reiniciar)
- partidos y resultados (historial que alimenta los ratings)
- logos (los logos no gastan cuota, pero la API pide guardarlos de nuestro lado)
- predicciones del modelo antes y durante cada partido (para medir y aprender)

Usa Postgres si existe DATABASE_URL (p. ej. Neon, gratis y permanente); si no,
un archivo SQLite local.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
                      default=lambda o: o.isoformat() if isinstance(o, (date, datetime)) else str(o))


class Store:
    def __init__(self, url: str | None = None, path: str | None = None):
        self.url = url
        self.pg = bool(url and url.startswith(("postgres://", "postgresql://")))
        self.path = path or str(ROOT / "zola_data.db")
        self._local = threading.local()
        self._lock = threading.Lock()
        self.ok = True
        self.error = None
        try:
            self._init()
        except Exception as e:  # sin base de datos la app sigue funcionando
            self.ok = False
            self.error = str(e)

    # ---------- conexión ----------
    def _conn(self):
        c = getattr(self._local, "conn", None)
        if c is not None:
            return c
        if self.pg:
            import psycopg
            c = psycopg.connect(self.url, autocommit=True, connect_timeout=10)
        else:
            c = sqlite3.connect(self.path, check_same_thread=False, timeout=15)
            c.execute("PRAGMA journal_mode=WAL")
        self._local.conn = c
        return c

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.pg else sql

    def _exec(self, sql: str, params=(), fetch=False, retry=True):
        try:
            c = self._conn()
            if self.pg:
                with c.cursor() as cur:
                    cur.execute(self._sql(sql), params)
                    if fetch:
                        cols = [d.name for d in cur.description] if cur.description else []
                        return [dict(zip(cols, r)) for r in cur.fetchall()]
                    return None
            with self._lock:
                cur = c.execute(sql, params)
                if fetch:
                    cols = [d[0] for d in cur.description] if cur.description else []
                    return [dict(zip(cols, r)) for r in cur.fetchall()]
                c.commit()
                return None
        except Exception:
            # conexión caída (Neon duerme tras inactividad): reconectar una vez
            self._local.conn = None
            if retry:
                return self._exec(sql, params, fetch, retry=False)
            raise

    def xmany(self, sql, rows: list) -> None:
        """Inserta muchas filas de una vez (importación de historial)."""
        if not rows:
            return
        c = self._conn()
        if self.pg:
            with c.cursor() as cur:
                cur.executemany(self._sql(sql), rows)
        else:
            with self._lock:
                c.executemany(sql, rows)
                c.commit()

    def q(self, sql, params=()):
        return self._exec(sql, params, fetch=True)

    def x(self, sql, params=()):
        self._exec(sql, params)

    def _init(self):
        blob = "BYTEA" if self.pg else "BLOB"
        stmts = [
            "CREATE TABLE IF NOT EXISTS api_cache (k TEXT PRIMARY KEY, data TEXT NOT NULL, ts DOUBLE PRECISION NOT NULL)",
            """CREATE TABLE IF NOT EXISTS fixtures (
                fixture_id BIGINT PRIMARY KEY, league_id BIGINT, season INTEGER, day TEXT, kickoff TEXT,
                home TEXT, away TEXT, home_id BIGINT, away_id BIGINT, home_goals INTEGER, away_goals INTEGER,
                status TEXT, data TEXT, updated DOUBLE PRECISION)""",
            "CREATE INDEX IF NOT EXISTS ix_fix_league ON fixtures (league_id, season)",
            "CREATE INDEX IF NOT EXISTS ix_fix_day ON fixtures (day)",
            f"CREATE TABLE IF NOT EXISTS logos (url TEXT PRIMARY KEY, mime TEXT, data {blob}, ts DOUBLE PRECISION)",
            """CREATE TABLE IF NOT EXISTS predictions (
                fixture_id TEXT NOT NULL, kind TEXT NOT NULL, minute INTEGER NOT NULL, ts DOUBLE PRECISION,
                league_id BIGINT, home TEXT, away TEXT, score TEXT, data TEXT,
                PRIMARY KEY (fixture_id, kind, minute))""",
            "CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT, ts DOUBLE PRECISION)",
            """CREATE TABLE IF NOT EXISTS history (
                code TEXT NOT NULL, season TEXT, day TEXT NOT NULL, home TEXT NOT NULL, away TEXT NOT NULL,
                hg INTEGER, ag INTEGER, oh DOUBLE PRECISION, od DOUBLE PRECISION, oa DOUBLE PRECISION,
                tournament TEXT, PRIMARY KEY (code, day, home, away))""",
            "CREATE INDEX IF NOT EXISTS ix_hist_code ON history (code, season)",
        ]
        for s in stmts:
            self.x(s)

    # ---------- caché de API ----------
    def cache_get(self, key: str, max_age: float):
        if not self.ok:
            return None
        try:
            rows = self.q("SELECT data, ts FROM api_cache WHERE k=?", (key,))
        except Exception:
            return None
        if rows and time.time() - rows[0]["ts"] < max_age:
            return json.loads(rows[0]["data"])
        return None

    def cache_put(self, key: str, data) -> None:
        if not self.ok:
            return
        try:
            self.x("INSERT INTO api_cache (k, data, ts) VALUES (?, ?, ?) "
                   "ON CONFLICT (k) DO UPDATE SET data=excluded.data, ts=excluded.ts", (key, _json(data), time.time()))
        except Exception:
            pass

    # ---------- partidos ----------
    def upsert_fixtures(self, items: list[dict]) -> None:
        if not self.ok:
            return
        now = time.time()
        for m in items:
            if not m.get("fixture_id") or m.get("source") == "demo":
                continue
            try:
                self.x("""INSERT INTO fixtures (fixture_id, league_id, season, day, kickoff, home, away, home_id, away_id,
                          home_goals, away_goals, status, data, updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                          ON CONFLICT (fixture_id) DO UPDATE SET home_goals=excluded.home_goals, away_goals=excluded.away_goals,
                          status=excluded.status, data=excluded.data, kickoff=excluded.kickoff, day=excluded.day, updated=excluded.updated""",
                       (int(m["fixture_id"]), m.get("league_id"), m.get("season"), (m.get("kickoff") or "")[:10], m.get("kickoff"),
                        m.get("home"), m.get("away"), m.get("home_id"), m.get("away_id"), m.get("home_goals"), m.get("away_goals"),
                        m.get("status_short"), _json(m), now))
            except Exception:
                pass

    def league_results(self, league_id, season) -> list[dict]:
        if not self.ok or not league_id:
            return []
        try:
            rows = self.q("SELECT day, home, away, home_goals, away_goals FROM fixtures WHERE league_id=? AND season=? "
                          "AND status IN ('FT','AET','PEN')", (league_id, season))
        except Exception:
            return []
        out = []
        for r in rows:
            try:
                out.append({"date": date.fromisoformat(r["day"]), "home": r["home"], "away": r["away"],
                            "hg": int(r["home_goals"]), "ag": int(r["away_goals"])})
            except (TypeError, ValueError):
                pass
        return out

    def fixture(self, fixture_id) -> dict | None:
        if not self.ok:
            return None
        try:
            rows = self.q("SELECT data FROM fixtures WHERE fixture_id=?", (int(fixture_id),))
            return json.loads(rows[0]["data"]) if rows else None
        except Exception:
            return None

    # ---------- logos ----------
    def logo_get(self, url: str):
        if not self.ok:
            return None
        try:
            rows = self.q("SELECT mime, data FROM logos WHERE url=?", (url,))
            return (rows[0]["mime"], bytes(rows[0]["data"])) if rows else None
        except Exception:
            return None

    def logo_put(self, url: str, mime: str, data: bytes) -> None:
        if not self.ok:
            return
        try:
            self.x("INSERT INTO logos (url, mime, data, ts) VALUES (?,?,?,?) ON CONFLICT (url) DO NOTHING",
                   (url, mime, data, time.time()))
        except Exception:
            pass

    # ---------- predicciones (para aprender) ----------
    def log_prediction(self, match: dict, kind: str, minute: int, payload: dict) -> None:
        if not self.ok:
            return
        try:
            self.x("""INSERT INTO predictions (fixture_id, kind, minute, ts, league_id, home, away, score, data)
                      VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT (fixture_id, kind, minute) DO UPDATE SET
                      ts=excluded.ts, score=excluded.score, data=excluded.data""",
                   (match["match_key"], kind, int(minute or 0), time.time(), match.get("league_id"), match.get("home"),
                    match.get("away"), f"{match.get('home_goals') or 0}-{match.get('away_goals') or 0}", _json(payload)))
        except Exception:
            pass

    def timeline(self, match_key: str) -> list[dict]:
        if not self.ok:
            return []
        try:
            rows = self.q("SELECT kind, minute, score, data FROM predictions WHERE fixture_id=? ORDER BY kind DESC, minute",
                          (match_key,))
        except Exception:
            return []
        return [{"kind": r["kind"], "minute": r["minute"], "score": r["score"], **json.loads(r["data"])} for r in rows]

    def settled_pre_predictions(self) -> list[dict]:
        """Predicciones previas al partido cuyo resultado final ya está guardado."""
        if not self.ok:
            return []
        try:
            rows = self.q("""SELECT p.fixture_id, p.league_id, p.data, f.home_goals, f.away_goals FROM predictions p
                             JOIN fixtures f ON p.fixture_id = 'af_' || CAST(f.fixture_id AS TEXT)
                             WHERE p.kind='pre' AND f.status IN ('FT','AET','PEN')""")
        except Exception:
            return []
        out = []
        for r in rows:
            d = json.loads(r["data"])
            d.update(fixture_id=r["fixture_id"], league_id=r["league_id"], hg=r["home_goals"], ag=r["away_goals"])
            out.append(d)
        return out

    # ---------- clave/valor ----------
    def kv_get(self, k: str, default=None):
        if not self.ok:
            return default
        try:
            rows = self.q("SELECT v FROM kv WHERE k=?", (k,))
            return json.loads(rows[0]["v"]) if rows else default
        except Exception:
            return default

    def kv_set(self, k: str, v) -> None:
        if not self.ok:
            return
        try:
            self.x("INSERT INTO kv (k, v, ts) VALUES (?,?,?) ON CONFLICT (k) DO UPDATE SET v=excluded.v, ts=excluded.ts",
                   (k, _json(v), time.time()))
        except Exception:
            pass

    def stats(self) -> dict:
        out = {"backend": "postgres" if self.pg else "sqlite", "ok": self.ok}
        if not self.ok:
            out["error"] = self.error
            return out
        for t in ("fixtures", "logos", "predictions", "api_cache"):
            try:
                out[t] = int(self.q(f"SELECT COUNT(*) AS n FROM {t}")[0]["n"])
            except Exception:
                out[t] = None
        try:
            out["finished"] = int(self.q("SELECT COUNT(*) AS n FROM fixtures WHERE status IN ('FT','AET','PEN')")[0]["n"])
        except Exception:
            pass
        return out


_STORE: Store | None = None


def get_store() -> Store:
    global _STORE
    if _STORE is None:
        _STORE = Store(os.getenv("DATABASE_URL") or None, os.getenv("ZOLA_DATA_PATH") or None)
    return _STORE


def set_store(s: Store) -> None:
    global _STORE
    _STORE = s
