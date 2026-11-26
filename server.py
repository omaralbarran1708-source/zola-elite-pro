"""ZOLA Elite — servidor web (API JSON + interfaz)."""
from __future__ import annotations

import base64
import os
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from zola import backtest as bt
from zola import demo
from zola.api import FootballApi
from zola.data import LAST_RATINGS, build_state, list_matches, match_detail
from zola.logos import _path_for, crest_svg, logo
from zola.model import predict
from zola.status import STATUS_LABEL, bucket_of, is_finished, is_live

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
LIMA = ZoneInfo("America/Lima")
ALLOWED_IMG_HOSTS = {"media.api-sports.io", "media-1.api-sports.io", "media-2.api-sports.io", "media-3.api-sports.io",
                     "media-4.api-sports.io"}

api = FootballApi(os.getenv("API_FOOTBALL_KEY", ""))
app = FastAPI(title="ZOLA Elite", docs_url=None, redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1000)


def _today() -> date:
    return datetime.now(LIMA).date()


def _slim(m: dict) -> dict:
    out = {k: m.get(k) for k in (
        "match_key", "fixture_id", "kickoff", "league", "league_id", "season", "round", "country", "league_logo", "flag",
        "home", "away", "home_id", "away_id", "home_logo", "away_logo", "home_goals", "away_goals", "minute", "extra",
        "status_short", "venue", "source")}
    s = m.get("status_short", "NS")
    out["live"] = is_live(s)
    out["finished"] = is_finished(s)
    out["status_label"] = STATUS_LABEL.get(s, s)
    out["buckets"] = sorted(bucket_of(m))
    return out


def _find_match(key: str, day: date) -> dict | None:
    if key.startswith("demo_"):
        items, _ = list_matches(api, "Hoy", day)
        return next((m for m in items if m["match_key"] == key), None)
    try:
        fid = int(key.split("_", 1)[1])
    except (IndexError, ValueError):
        return None
    return api.fixture(fid)


@app.get("/api/status")
def status():
    return {"demo": not api.enabled, "remaining": api.remaining, "now": datetime.now(LIMA).isoformat()}


@app.get("/api/matches")
def matches(day: str | None = Query(None, alias="date"), live: bool = False):
    try:
        d = date.fromisoformat(day) if day else _today()
    except ValueError:
        raise HTTPException(400, "Fecha inválida")
    items, notice = list_matches(api, "En vivo" if live else "Hoy", d)
    return {"date": d.isoformat(), "demo": not api.enabled, "notice": notice, "remaining": api.remaining,
            "matches": [_slim(m) for m in items]}


@app.get("/api/quick")
def quick(day: str | None = Query(None, alias="date")):
    """Probabilidades 1X2 rápidas para la lista (sin gastar consultas: demo o ligas ya analizadas)."""
    try:
        d = date.fromisoformat(day) if day else _today()
    except ValueError:
        raise HTTPException(400, "Fecha inválida")
    items, _ = list_matches(api, "Hoy", d)
    out = {}
    for m in items:
        if is_finished(m["status_short"]):
            continue
        st = build_state(m, [], {})
        if m.get("source") == "demo":
            p = predict(m["home"], m["away"], demo.FORMS.get(m["home"], demo.TeamForm()),
                        demo.FORMS.get(m["away"], demo.TeamForm()), state=st, market_weight=0)
        else:
            r = LAST_RATINGS.get((m.get("league_id"), m.get("season")))
            if not r or not (r.has(m["home"], 4) and r.has(m["away"], 4)):
                continue
            p = predict(m["home"], m["away"], demo.TeamForm(), demo.TeamForm(), state=st,
                        lambdas=r.lambdas(m["home"], m["away"]), rho=r.rho, market_weight=0)
        out[m["match_key"]] = [round(p.home_win, 3), round(p.draw, 3), round(p.away_win, 3)]
    return {"probs": out}


@app.get("/api/match/{key}")
def match(key: str, day: str | None = Query(None, alias="date")):
    d = date.fromisoformat(day) if day else _today()
    m = _find_match(key, d)
    if not m:
        raise HTTPException(404, "Partido no encontrado")
    det = match_detail(api, m)
    pred = predict(m["home"], m["away"], det.home_form, det.away_form, det.state, det.odds,
                   lambdas=det.lambdas, rho=det.rho, source=det.source)
    p = asdict(pred)
    return {
        "match": _slim(m),
        "prediction": p,
        "forms": {"home": asdict(det.home_form), "away": asdict(det.away_form)},
        "stats": det.stats, "events": det.events, "odds": det.odds,
        "state": asdict(det.state), "warnings": det.warnings, "remaining": api.remaining,
        "ratings": det.ratings_info,
    }


@app.get("/api/standings")
def standings(league: int, season: int | None = None, demo_mode: bool = Query(False, alias="demo")):
    if demo_mode or not api.enabled:
        return {"groups": demo.STANDINGS.get(league, [])}
    if not season:
        return {"groups": []}
    try:
        return {"groups": api.standings(league, season)}
    except Exception as e:
        return {"groups": [], "error": str(e)}


@app.get("/api/h2h")
def h2h(key: str, day: str | None = Query(None, alias="date")):
    d = date.fromisoformat(day) if day else _today()
    m = _find_match(key, d)
    if not m:
        return {"matches": []}
    if m.get("source") == "demo":
        return {"matches": demo.head_to_head(m["home"], m["away"], m.get("home_logo"), m.get("away_logo"))}
    try:
        res = api.head_to_head(int(m["home_id"]), int(m["away_id"]))
        return {"matches": [_slim(x) for x in res if is_finished(x["status_short"])][:6]}
    except Exception as e:
        return {"matches": [], "error": str(e)}


@app.get("/api/results")
def results(ids: str = ""):
    """Estado actual de partidos guardados (para cerrar los pronósticos del usuario)."""
    keys = [k for k in ids.split(",") if k][:20]
    out = {}
    demo_keys = [k for k in keys if k.startswith("demo_")]
    if demo_keys:
        items, _ = list_matches(api, "Hoy", _today())
        for m in items:
            if m["match_key"] in demo_keys:
                out[m["match_key"]] = _slim(m)
    real = tuple(sorted(int(k.split("_", 1)[1]) for k in keys if k.startswith("af_") and k[3:].isdigit()))
    if real and api.enabled:
        try:
            for m in api.fixtures_by_ids(real):
                out[m["match_key"]] = _slim(m)
        except Exception:
            pass
    return {"results": out}


@app.get("/img")
def img(u: str = "", n: str = ""):
    """Logos: se descargan una vez, se guardan y se sirven con caché larga. Si fallan, escudo generado."""
    headers = {"Cache-Control": "public, max-age=604800, immutable"}
    host = urlparse(u).hostname or ""
    if u and host in ALLOWED_IMG_HOSTS:
        uri = logo(u, n)          # descarga y guarda en disco si aún no está
        path = _path_for(u)
        if path.exists():
            data = path.read_bytes()
            mime = uri.split(";")[0][5:] if uri.startswith("data:") else "image/png"
            return Response(data, media_type=mime, headers=headers)
    svg = base64.b64decode(crest_svg(n).split(",", 1)[1])
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


_BT_CACHE: dict = {}


@app.get("/api/backtest/leagues")
def backtest_leagues():
    lg = [{"code": k, "name": v, "seasons": bt.seasons_for(k, _today())} for k, v in bt.MAIN_LEAGUES.items()]
    lg += [{"code": k, "name": v, "seasons": bt.seasons_for(k, _today())} for k, v in bt.EXTRA_LEAGUES.items()]
    return {"leagues": lg, "source": bt.SOURCE_URL}


@app.get("/api/backtest")
def backtest(league: str = "E0", season: str | None = None, weight: float = 0.35, threshold: float = 0.05):
    if league not in bt.MAIN_LEAGUES and league not in bt.EXTRA_LEAGUES:
        raise HTTPException(400, "Liga no disponible")
    season = season or bt.seasons_for(league, _today())[0]
    weight = min(max(weight, 0.0), 1.0)
    threshold = min(max(threshold, 0.0), 0.5)
    key = (league, season, round(weight, 2), round(threshold, 3))
    if key in _BT_CACHE and _BT_CACHE[key][0] > datetime.now().timestamp() - 6 * 3600:
        return _BT_CACHE[key][1]
    try:
        text = bt.fetch_csv(league, season)
    except Exception as e:
        return JSONResponse({"error": f"No se pudieron descargar los datos: {e}"}, status_code=502)
    rows = bt.parse_csv(text, season if league in bt.EXTRA_LEAGUES else None)
    try:
        res = bt.run_backtest(rows, market_weight=weight, value_threshold=threshold)
    except ValueError as e:
        return JSONResponse({"error": str(e), "matches": len(rows)}, status_code=422)
    name = bt.MAIN_LEAGUES.get(league) or bt.EXTRA_LEAGUES.get(league)
    res.update({"league": league, "league_name": name, "season": season})
    _BT_CACHE[key] = (datetime.now().timestamp(), res)
    return res


@app.get("/healthz")
def healthz():
    return {"ok": True}


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/{path:path}")
def spa(path: str):
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})
