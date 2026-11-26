from fastapi.testclient import TestClient

from server import app

c = TestClient(app)


def test_matches_and_detail_demo():
    j = c.get("/api/matches").json()
    assert j["demo"] and len(j["matches"]) >= 5
    m = next(x for x in j["matches"] if x["live"])
    d = c.get(f"/api/match/{m['match_key']}").json()
    p = d["prediction"]
    assert abs(p["home_win"] + p["draw"] + p["away_win"] - 1) < 1e-6
    assert len(p["matrix"]) == 6


def test_standings_h2h_results():
    assert c.get("/api/standings?league=39").json()["groups"]
    assert len(c.get("/api/h2h?key=demo_9002").json()["matches"]) == 5
    r = c.get("/api/results?ids=demo_9005").json()["results"]
    assert r["demo_9005"]["finished"]


def test_img_only_allows_api_sports():
    r = c.get("/img?u=https://evil.example/x.png&n=Test FC")
    assert r.headers["content-type"].startswith("image/svg")


def test_spa_fallback():
    r = c.get("/ligas")
    assert r.status_code == 200 and "ZOLA" in r.text
